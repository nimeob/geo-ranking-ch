#!/usr/bin/env node

const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const issueNumber = 1039;
const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const repoRoot = process.cwd();
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

async function collectViewportMetrics(page) {
  return page.evaluate(() => {
    const doc = document.scrollingElement || document.documentElement;
    const main = document.querySelector('main');
    const mapMeta = document.getElementById('map-view-meta');

    return {
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight,
      },
      pageWidth: {
        scrollWidth: doc.scrollWidth,
        clientWidth: doc.clientWidth,
        matches: doc.scrollWidth === doc.clientWidth,
      },
      mainGridColumns: main ? getComputedStyle(main).gridTemplateColumns : '',
      mapMeta: mapMeta ? String(mapMeta.textContent || '').trim() : '',
    };
  });
}

async function readZoom(page) {
  const text = (await page.locator('#map-view-meta').textContent()) || '';
  const match = /Zoom\s+(\d+)/i.exec(text);
  return {
    text: text.trim(),
    zoom: match ? Number(match[1]) : null,
  };
}

async function runMainFunctionsProbe(page) {
  const requiredSelectors = ['#analyze-form', '#map-click-surface', '#result', '#map-zoom-in', '#map-zoom-out'];
  const visibility = {};

  for (const selector of requiredSelectors) {
    const locator = page.locator(selector);
    visibility[selector] = await locator.isVisible();
  }

  const zoomBefore = await readZoom(page);
  await page.locator('#map-zoom-in').click();
  await page.waitForTimeout(120);
  const zoomAfter = await readZoom(page);

  const zoomInteractionOk =
    Number.isFinite(zoomBefore.zoom) &&
    Number.isFinite(zoomAfter.zoom) &&
    zoomAfter.zoom > zoomBefore.zoom;

  return {
    requiredSelectors,
    visibility,
    zoomBefore,
    zoomAfter,
    zoomInteractionOk,
    passed: Object.values(visibility).every(Boolean) && zoomInteractionOk,
  };
}

async function captureMobileEvidence(browser) {
  const context = await browser.newContext({
    viewport: { width: 360, height: 800 },
    locale: 'de-CH',
  });
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(300);

  const metrics = await collectViewportMetrics(page);
  const functionsProbe = await runMainFunctionsProbe(page);

  await fs.mkdir(outDir, { recursive: true });
  const screenshotPath = path.join(outDir, `issue-${issueNumber}-mobile-overflow-${stamp}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await context.close();

  return {
    metrics,
    functionsProbe,
    screenshot: path.relative(repoRoot, screenshotPath),
  };
}

async function captureDesktopEvidence(browser) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: 'de-CH',
  });
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(300);

  const metrics = await collectViewportMetrics(page);

  await fs.mkdir(outDir, { recursive: true });
  const screenshotPath = path.join(outDir, `issue-${issueNumber}-desktop-regression-${stamp}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await context.close();

  return {
    metrics,
    screenshot: path.relative(repoRoot, screenshotPath),
  };
}

async function main() {
  const browser = await chromium.launch({ headless: true });

  const mobile = await captureMobileEvidence(browser);
  const desktop = await captureDesktopEvidence(browser);

  await browser.close();

  const payload = {
    issue: issueNumber,
    targetUrl: baseUrl,
    checks: {
      mobileNoHorizontalScroll: {
        ...mobile.metrics.pageWidth,
        passed: mobile.metrics.pageWidth.matches,
        assertion: 'document.scrollingElement.scrollWidth === document.scrollingElement.clientWidth',
      },
      mainFunctionsReachable: mobile.functionsProbe,
      desktopRegressionNoHorizontalScroll: {
        ...desktop.metrics.pageWidth,
        passed: desktop.metrics.pageWidth.matches,
      },
    },
    snapshots: {
      mobile: {
        viewport: mobile.metrics.viewport,
        mainGridColumns: mobile.metrics.mainGridColumns,
        mapMeta: mobile.metrics.mapMeta,
        screenshot: mobile.screenshot,
      },
      desktop: {
        viewport: desktop.metrics.viewport,
        mainGridColumns: desktop.metrics.mainGridColumns,
        mapMeta: desktop.metrics.mapMeta,
        screenshot: desktop.screenshot,
      },
    },
  };

  payload.ok =
    payload.checks.mobileNoHorizontalScroll.passed &&
    payload.checks.mainFunctionsReachable.passed &&
    payload.checks.desktopRegressionNoHorizontalScroll.passed;

  const outJson = path.join(outDir, `issue-${issueNumber}-mobile-overflow-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!payload.ok) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
