#!/usr/bin/env node
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const repoRoot = process.cwd();
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

const devices = [
  {
    key: 'ios-simulator',
    label: 'iOS Safari Simulator (Playwright iPhone 13 profile on Chromium)',
    viewport: { width: 390, height: 844 },
    userAgent:
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    geolocation: { latitude: 47.3769, longitude: 8.5417, accuracy: 22 },
  },
  {
    key: 'android-chrome',
    label: 'Android Chrome Simulator (Playwright Pixel-like mobile profile on Chromium)',
    viewport: { width: 412, height: 915 },
    userAgent:
      'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36',
    geolocation: { latitude: 46.948, longitude: 7.4474, accuracy: 18 },
  },
];

async function readMeta(page) {
  const text = (await page.locator('#map-view-meta').textContent()) || '';
  const m = /Zoom\s+(\d+)/i.exec(text);
  return { text: text.trim(), zoom: m ? Number(m[1]) : null };
}

async function pinchOnMap(page) {
  await page.evaluate(async () => {
    const surface = document.getElementById('map-click-surface');
    if (!surface) throw new Error('map-click-surface not found');

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

    await new Promise((resolve) => setTimeout(resolve, 180));
  });
}

async function panMap(page) {
  const surface = page.locator('#map-click-surface');
  const box = await surface.boundingBox();
  if (!box) throw new Error('map surface bbox missing');

  const sx = box.x + box.width / 2;
  const sy = box.y + box.height / 2;
  await page.mouse.move(sx, sy);
  await page.mouse.down();
  await page.mouse.move(sx + 90, sy + 40, { steps: 10 });
  await page.mouse.up();
  await page.waitForTimeout(160);
}

async function setMarker(page) {
  const surface = page.locator('#map-click-surface');
  const box = await surface.boundingBox();
  if (!box) throw new Error('map surface bbox missing');

  await page.mouse.click(box.x + box.width * 0.55, box.y + box.height * 0.48);
  await page.waitForTimeout(200);
  return page.locator('#map-click-marker').evaluate((el) => !el.hasAttribute('hidden'));
}

async function geolocSuccess(page) {
  await page.locator('#map-locate-btn').click();
  await page.waitForTimeout(300);

  return {
    markerVisible: await page.locator('#map-user-marker').evaluate((el) => !el.hasAttribute('hidden')),
    statusText: ((await page.locator('#map-status').textContent()) || '').trim(),
    locationMeta: ((await page.locator('#map-location-meta').textContent()) || '').trim(),
  };
}

async function geolocDenied(browser, device) {
  const context = await browser.newContext({
    viewport: device.viewport,
    userAgent: device.userAgent,
    isMobile: true,
    hasTouch: true,
    locale: 'de-CH',
  });
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await page.locator('#map-locate-btn').click();
  await page.waitForTimeout(300);

  const result = {
    statusText: ((await page.locator('#map-status').textContent()) || '').trim(),
    locationMeta: ((await page.locator('#map-location-meta').textContent()) || '').trim(),
  };

  await context.close();
  return result;
}

async function runDevice(browser, device) {
  const context = await browser.newContext({
    viewport: device.viewport,
    userAgent: device.userAgent,
    isMobile: true,
    hasTouch: true,
    locale: 'de-CH',
    geolocation: device.geolocation,
    permissions: ['geolocation'],
  });

  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });

  const initial = await readMeta(page);
  await pinchOnMap(page);
  const afterPinch = await readMeta(page);

  const beforePan = await readMeta(page);
  await panMap(page);
  const afterPan = await readMeta(page);

  const markerVisible = await setMarker(page);
  const geoSuccess = await geolocSuccess(page);

  const screenshotPath = path.join(outDir, `issue-981-${device.key}-${stamp}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await context.close();

  const geoDenied = await geolocDenied(browser, device);

  return {
    device: device.label,
    key: device.key,
    checks: {
      pinchZoom: {
        before: initial,
        after: afterPinch,
        passed: Number.isFinite(initial.zoom) && Number.isFinite(afterPinch.zoom) && afterPinch.zoom > initial.zoom,
      },
      panRegression: {
        before: beforePan,
        after: afterPan,
        passed:
          Number.isFinite(beforePan.zoom) &&
          Number.isFinite(afterPan.zoom) &&
          afterPan.zoom === beforePan.zoom &&
          beforePan.text !== afterPan.text,
      },
      markerRegression: {
        markerVisible,
        passed: markerVisible === true,
      },
      geolocationSuccess: {
        ...geoSuccess,
        passed: geoSuccess.markerVisible === true && /Geräteposition:/.test(geoSuccess.locationMeta),
      },
      geolocationDenied: {
        ...geoDenied,
        passed: /(abgelehnt|nicht unterstützt|nicht verfügbar|Zeitlimit|insecure context)/i.test(
          `${geoDenied.statusText} ${geoDenied.locationMeta}`
        ),
      },
    },
    artifacts: {
      screenshot: path.relative(repoRoot, screenshotPath),
    },
  };
}

async function main() {
  const startedAtUtc = new Date().toISOString();
  const browser = await chromium.launch({ headless: true });
  const checks = [];
  for (const device of devices) {
    checks.push(await runDevice(browser, device));
  }
  await browser.close();
  const finishedAtUtc = new Date().toISOString();

  const ok = checks.every((entry) => Object.values(entry.checks).every((check) => check.passed));
  const payload = {
    issue: 981,
    parentIssue: 975,
    startedAtUtc,
    finishedAtUtc,
    targetUrl: baseUrl,
    limitations: [
      'Native Playwright WebKit (Safari engine) konnte auf diesem Runner wegen fehlender System-Libraries nicht gestartet werden; iOS-Check daher als iPhone-Profil-Simulator auf Chromium durchgeführt.',
    ],
    checks,
    ok,
  };

  await fs.mkdir(outDir, { recursive: true });
  const outJson = path.join(outDir, `issue-981-mobile-e2e-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!ok) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
