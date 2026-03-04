#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { devices, webkit } from 'playwright';

const ISSUE_NUMBER = 986;
const PARENT_ISSUE = 975;
const repoRoot = process.cwd();
const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

function parseZoom(metaText) {
  const match = /Zoom\s+(\d+)/i.exec(metaText || '');
  return match ? Number(match[1]) : null;
}

async function readMapMeta(page) {
  const text = ((await page.locator('#map-view-meta').textContent()) || '').trim();
  return {
    text,
    zoom: parseZoom(text),
  };
}

async function pinchMap(page) {
  return page.evaluate(async () => {
    const surface = document.getElementById('map-click-surface');
    if (!surface) {
      throw new Error('map-click-surface not found');
    }

    const rect = surface.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;

    const fire = (type, id, x, y) => {
      const ev = new PointerEvent(type, {
        pointerId: id,
        pointerType: 'touch',
        isPrimary: id === 1,
        clientX: x,
        clientY: y,
        bubbles: true,
        cancelable: true,
      });
      surface.dispatchEvent(ev);
    };

    fire('pointerdown', 1, cx - 32, cy);
    fire('pointerdown', 2, cx + 32, cy);
    fire('pointermove', 1, cx - 118, cy - 6);
    fire('pointermove', 2, cx + 118, cy + 6);
    fire('pointerup', 1, cx - 118, cy - 6);
    fire('pointerup', 2, cx + 118, cy + 6);

    await new Promise((resolve) => setTimeout(resolve, 220));
  });
}

async function panMap(page) {
  return page.evaluate(async () => {
    const surface = document.getElementById('map-click-surface');
    if (!surface) {
      throw new Error('map-click-surface not found');
    }

    const rect = surface.getBoundingClientRect();
    const startX = rect.left + rect.width * 0.52;
    const startY = rect.top + rect.height * 0.55;
    const endX = startX + 94;
    const endY = startY + 42;

    const fire = (type, id, x, y) => {
      const ev = new PointerEvent(type, {
        pointerId: id,
        pointerType: 'touch',
        isPrimary: true,
        clientX: x,
        clientY: y,
        bubbles: true,
        cancelable: true,
      });
      surface.dispatchEvent(ev);
    };

    fire('pointerdown', 1, startX, startY);
    for (let step = 1; step <= 8; step += 1) {
      const x = startX + ((endX - startX) * step) / 8;
      const y = startY + ((endY - startY) * step) / 8;
      fire('pointermove', 1, x, y);
    }
    fire('pointerup', 1, endX, endY);

    await new Promise((resolve) => setTimeout(resolve, 180));
  });
}

async function run() {
  const startedAtUtc = new Date().toISOString();
  const browser = await webkit.launch({ headless: true });
  const context = await browser.newContext({
    ...devices['iPhone 13'],
    locale: 'de-CH',
    geolocation: { latitude: 47.3769, longitude: 8.5417, accuracy: 20 },
    permissions: ['geolocation'],
  });

  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });

  await page.locator('#map-click-surface').waitFor({ state: 'visible', timeout: 20_000 });
  const loginInlineVisible = await page.locator('#auth-login-inline').isVisible();
  const loginBurgerVisible = await page.locator('#burger-login-link').isVisible();

  const beforePinch = await readMapMeta(page);
  await pinchMap(page);
  const afterPinch = await readMapMeta(page);

  const beforePan = await readMapMeta(page);
  await panMap(page);
  const afterPan = await readMapMeta(page);

  await fs.mkdir(outDir, { recursive: true });
  const screenshotPath = path.join(outDir, `issue-986-webkit-ios-${stamp}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await context.close();
  await browser.close();

  const interactionViaZoom =
    Number.isFinite(beforePinch.zoom) && Number.isFinite(afterPinch.zoom) && afterPinch.zoom > beforePinch.zoom;
  const interactionViaPan =
    Number.isFinite(beforePan.zoom) &&
    Number.isFinite(afterPan.zoom) &&
    beforePan.zoom === afterPan.zoom &&
    beforePan.text !== afterPan.text;

  const checks = {
    guiLoad: {
      passed: true,
      detail: '/gui rendered in native WebKit context',
    },
    loginEntrypointVisible: {
      inlineVisible: loginInlineVisible,
      burgerVisible: loginBurgerVisible,
      passed: loginInlineVisible || loginBurgerVisible,
    },
    mapInteraction: {
      pinch: {
        before: beforePinch,
        after: afterPinch,
        passed: interactionViaZoom,
      },
      pan: {
        before: beforePan,
        after: afterPan,
        passed: interactionViaPan,
      },
      passed: interactionViaZoom || interactionViaPan,
      strategy: interactionViaZoom ? 'pinch-zoom' : interactionViaPan ? 'pan' : 'none',
    },
  };

  const ok = Object.values(checks).every((entry) => entry.passed === true);
  const finishedAtUtc = new Date().toISOString();

  const payload = {
    issue: ISSUE_NUMBER,
    parentIssue: PARENT_ISSUE,
    startedAtUtc,
    finishedAtUtc,
    targetUrl: baseUrl,
    runtime: {
      browser: 'playwright-webkit',
      device: 'iPhone 13',
      headless: true,
    },
    checks,
    artifacts: {
      screenshot: path.relative(repoRoot, screenshotPath),
    },
    ok,
  };

  const outJson = path.join(outDir, `issue-986-webkit-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!ok) {
    process.exit(1);
  }
}

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
