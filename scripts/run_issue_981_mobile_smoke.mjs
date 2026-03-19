#!/usr/bin/env node
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const guiStabilityWaitMs = Number.parseInt(process.env.GUI_STABILITY_WAIT_MS || '1200', 10);
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

function buildBootstrapFailure(device, error) {
  const normalized = normalizeError(error);
  return {
    device: device.label,
    key: device.key,
    checks: {
      bootstrap: {
        stage: 'openStableGuiPage',
        error: normalized.message,
        passed: false,
      },
      overall: {
        passed: false,
      },
    },
    artifacts: {},
    error: normalized,
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
  } catch {
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
  await page.evaluate(async () => {
    const surface = document.getElementById('map-click-surface');
    if (!surface) throw new Error('map-click-surface not found');

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

async function setMarkerOrDetectAuthRedirect(page) {
  await page.evaluate(() => {
    const surface = document.getElementById('map-click-surface');
    if (!surface) throw new Error('map-click-surface not found');

    const rect = surface.getBoundingClientRect();
    const x = rect.left + rect.width * 0.55;
    const y = rect.top + rect.height * 0.48;

    const click = new MouseEvent('click', {
      clientX: x,
      clientY: y,
      bubbles: true,
      cancelable: true,
      button: 0,
    });

    surface.dispatchEvent(click);
  });

  const timeoutMs = 6_000;
  const markerWait = page
    .locator('#map-click-marker')
    .waitFor({ state: 'visible', timeout: timeoutMs })
    .then(() => ({ kind: 'marker-visible' }))
    .catch(() => ({ kind: 'marker-timeout' }));

  const authWait = page
    .waitForURL((url) => isAuthRedirectUrl(String(url)), { timeout: timeoutMs })
    .then(() => ({ kind: 'auth-redirect' }))
    .catch(() => ({ kind: 'auth-timeout' }));

  const winner = await Promise.race([markerWait, authWait]);
  const currentUrl = page.url();
  const redirectedToAuth = isAuthRedirectUrl(currentUrl);

  if (winner.kind === 'marker-visible') {
    return {
      outcome: 'marker-visible',
      markerVisible: true,
      redirectedToAuth,
      finalUrl: currentUrl,
      passed: true,
    };
  }

  if (winner.kind === 'auth-redirect' || redirectedToAuth) {
    return {
      outcome: 'auth-redirect',
      markerVisible: false,
      redirectedToAuth: true,
      finalUrl: currentUrl,
      passed: true,
    };
  }

  const markerVisible = await page
    .locator('#map-click-marker')
    .evaluate((el) => !el.hasAttribute('hidden'))
    .catch(() => false);

  return {
    outcome: markerVisible ? 'marker-visible-delayed' : 'no-marker-no-redirect',
    markerVisible,
    redirectedToAuth: false,
    finalUrl: currentUrl,
    passed: markerVisible,
  };
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
  const page = await openStableGuiPage(context, `${device.key}:geoloc-denied`);
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

  const page = await openStableGuiPage(context, `${device.key}:geoloc-allowed`);

  const initial = await readMeta(page);
  await pinchOnMap(page);
  const afterPinch = await readMeta(page);

  const beforePan = await readMeta(page);
  await panMap(page);
  const afterPan = await readMeta(page);

  const geoSuccess = await geolocSuccess(page);

  const screenshotPath = path.join(outDir, `issue-981-${device.key}-${stamp}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const markerCheck = await setMarkerOrDetectAuthRedirect(page);

  await context.close();

  const geoDenied = await geolocDenied(browser, device);

  const pinchPassed = Number.isFinite(initial.zoom) && Number.isFinite(afterPinch.zoom) && afterPinch.zoom > initial.zoom;
  const panPassed =
    Number.isFinite(beforePan.zoom)
    && Number.isFinite(afterPan.zoom)
    && afterPan.zoom === beforePan.zoom
    && beforePan.text !== afterPan.text;
  const markerPassed = markerCheck.passed === true;
  const geolocationSuccessPassed = geoSuccess.markerVisible === true && /Geräteposition:/.test(geoSuccess.locationMeta);
  const geolocationDeniedPassed = /(abgelehnt|nicht unterstützt|nicht verfügbar|Zeitlimit|insecure context)/i.test(
    `${geoDenied.statusText} ${geoDenied.locationMeta}`
  );
  const touchInteractionPassed = pinchPassed || panPassed;
  const overallPassed = touchInteractionPassed && markerPassed && geolocationSuccessPassed && geolocationDeniedPassed;

  return {
    device: device.label,
    key: device.key,
    checks: {
      pinchZoom: {
        before: initial,
        after: afterPinch,
        passed: pinchPassed,
      },
      panRegression: {
        before: beforePan,
        after: afterPan,
        passed: panPassed,
      },
      markerRegression: {
        outcome: markerCheck.outcome,
        markerVisible: markerCheck.markerVisible,
        redirectedToAuth: markerCheck.redirectedToAuth,
        finalUrl: markerCheck.finalUrl,
        passed: markerPassed,
      },
      geolocationSuccess: {
        ...geoSuccess,
        passed: geolocationSuccessPassed,
      },
      geolocationDenied: {
        ...geoDenied,
        passed: geolocationDeniedPassed,
      },
      touchInteraction: {
        pinchPassed,
        panPassed,
        passed: touchInteractionPassed,
      },
      overall: {
        passed: overallPassed,
      },
    },
    artifacts: {
      screenshot: path.relative(repoRoot, screenshotPath),
    },
  };
}

async function main() {
  const startedAtUtc = new Date().toISOString();
  const checks = [];
  const fatalErrors = [];

  let browser = null;
  try {
    browser = await chromium.launch({ headless: true });

    for (const device of devices) {
      try {
        checks.push(await runDevice(browser, device));
      } catch (error) {
        checks.push(buildBootstrapFailure(device, error));
      }
    }
  } catch (error) {
    fatalErrors.push(normalizeError(error));
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  const finishedAtUtc = new Date().toISOString();
  const ok =
    fatalErrors.length === 0
    && checks.length > 0
    && checks.every((entry) => entry?.checks?.overall?.passed === true);

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
    fatalErrors,
    ok,
  };

  await fs.mkdir(outDir, { recursive: true });
  const outJson = path.join(outDir, `issue-981-mobile-e2e-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!ok) process.exit(1);
}

main().catch(async (error) => {
  const finishedAtUtc = new Date().toISOString();
  const payload = {
    issue: 981,
    parentIssue: 975,
    startedAtUtc: finishedAtUtc,
    finishedAtUtc,
    targetUrl: baseUrl,
    checks: [],
    fatalErrors: [normalizeError(error)],
    ok: false,
  };

  await fs.mkdir(outDir, { recursive: true });
  const outJson = path.join(outDir, `issue-981-mobile-e2e-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');
  console.log(path.relative(repoRoot, outJson));
  process.exit(1);
});
