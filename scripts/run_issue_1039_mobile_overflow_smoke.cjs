#!/usr/bin/env node

const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const issueNumber = 1039;
const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const guiStabilityWaitMs = Number.parseInt(process.env.GUI_STABILITY_WAIT_MS || '1200', 10);
const repoRoot = process.cwd();
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

function normalizeError(error) {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack || '',
    };
  }

  return {
    name: 'Error',
    message: String(error || 'unknown error'),
    stack: '',
  };
}

function isAuthRedirectUrl(url) {
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase();
    const pathname = parsed.pathname.toLowerCase();
    const hasOauthLoginQuery = parsed.searchParams.has('response_type') && parsed.searchParams.has('client_id');
    if (hostname.startsWith('auth.')) return true;
    if (pathname === '/login' && hasOauthLoginQuery) return true;
    return false;
  } catch (_error) {
    return false;
  }
}

async function waitForGuiOrAuthRedirect(page, { stageLabel, selector, timeoutMs }) {
  const currentUrl = page.url();
  if (isAuthRedirectUrl(currentUrl)) {
    throw new Error(
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${currentUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  const guiWait = page
    .locator(selector)
    .waitFor({ state: 'visible', timeout: timeoutMs })
    .then(() => ({ kind: 'gui-ready' }))
    .catch((error) => ({ kind: 'gui-timeout', error }));

  const authWait = page
    .waitForURL((url) => isAuthRedirectUrl(String(url)), { timeout: timeoutMs })
    .then(() => ({ kind: 'auth-redirect' }))
    .catch(() => ({ kind: 'auth-timeout' }));

  const winner = await Promise.race([guiWait, authWait]);

  if (winner.kind === 'auth-redirect') {
    const authUrl = page.url();
    throw new Error(
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${authUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  if (winner.kind === 'gui-ready') {
    return;
  }

  const finalUrl = page.url();
  if (isAuthRedirectUrl(finalUrl)) {
    throw new Error(
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${finalUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  if (winner.kind === 'gui-timeout') {
    const reason = winner.error instanceof Error ? winner.error.message : String(winner.error || 'timeout');
    throw new Error(
      `[${stageLabel}] GUI-Shell nicht bereit: ${selector} nach ${timeoutMs}ms nicht sichtbar (url=${finalUrl}). reason=${reason}`
    );
  }

  throw new Error(`[${stageLabel}] GUI-Shell nicht bereit: ${selector} nach ${timeoutMs}ms nicht sichtbar (url=${finalUrl}).`);
}

async function openStableGuiPage(context, stageLabel) {
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(Math.max(0, guiStabilityWaitMs));

  await waitForGuiOrAuthRedirect(page, {
    stageLabel,
    selector: '#analyze-form',
    timeoutMs: 20_000,
  });

  return page;
}

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
  const page = await openStableGuiPage(context, 'mobile');

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
  const page = await openStableGuiPage(context, 'desktop');

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
  const startedAtUtc = new Date().toISOString();
  let browser = null;
  let payload = null;

  try {
    browser = await chromium.launch({ headless: true });

    const mobile = await captureMobileEvidence(browser);
    const desktop = await captureDesktopEvidence(browser);

    payload = {
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
      runError: null,
      ok:
        mobile.metrics.pageWidth.matches &&
        mobile.functionsProbe.passed &&
        desktop.metrics.pageWidth.matches,
    };
  } catch (error) {
    payload = {
      issue: issueNumber,
      targetUrl: baseUrl,
      checks: {},
      snapshots: {},
      runError: normalizeError(error),
      ok: false,
    };
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  payload.startedAtUtc = startedAtUtc;
  payload.finishedAtUtc = new Date().toISOString();

  await fs.mkdir(outDir, { recursive: true });
  const outJson = path.join(outDir, `issue-${issueNumber}-mobile-overflow-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!payload.ok) {
    process.exit(1);
  }
}

main().catch(async (error) => {
  const outJson = path.join(outDir, `issue-${issueNumber}-mobile-overflow-smoke-${stamp}.json`);
  const payload = {
    issue: issueNumber,
    targetUrl: baseUrl,
    startedAtUtc: new Date().toISOString(),
    finishedAtUtc: new Date().toISOString(),
    checks: {},
    snapshots: {},
    runError: normalizeError(error),
    ok: false,
  };

  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');
  console.log(path.relative(repoRoot, outJson));
  process.exit(1);
});
