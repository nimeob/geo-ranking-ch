#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium, devices, webkit } from 'playwright';

const ISSUE_NUMBER = 986;
const PARENT_ISSUE = 975;
const repoRoot = process.cwd();
const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const guiStabilityWaitMs = Number.parseInt(process.env.GUI_STABILITY_WAIT_MS || '1200', 10);
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

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

async function waitForGuiOrAuthRedirect(page, { stage, selector, timeoutMs }) {
  const currentUrl = page.url();
  if (isAuthRedirectUrl(currentUrl)) {
    throw new Error(
      `[${stage}] Unerwarteter Redirect auf Auth-Login erkannt: ${currentUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
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
      `[${stage}] Unerwarteter Redirect auf Auth-Login erkannt: ${authUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  if (winner.kind === 'gui-ready') {
    return;
  }

  const finalUrl = page.url();
  if (isAuthRedirectUrl(finalUrl)) {
    throw new Error(
      `[${stage}] Unerwarteter Redirect auf Auth-Login erkannt: ${finalUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  if (winner.kind === 'gui-timeout') {
    const reason = winner.error instanceof Error ? winner.error.message : String(winner.error || 'timeout');
    throw new Error(`[${stage}] GUI-Shell nicht bereit: ${selector} nach ${timeoutMs}ms nicht sichtbar (url=${finalUrl}). reason=${reason}`);
  }

  throw new Error(`[${stage}] GUI-Shell nicht bereit: ${selector} nach ${timeoutMs}ms nicht sichtbar (url=${finalUrl}).`);
}

async function openStableGuiPage(context, stage = 'webkit') {
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(Math.max(0, guiStabilityWaitMs));

  await waitForGuiOrAuthRedirect(page, {
    stage,
    selector: '#map-click-surface',
    timeoutMs: 20_000,
  });

  return page;
}

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

async function launchPreferredBrowser() {
  try {
    return {
      browser: await webkit.launch({ headless: true }),
      runtimeBrowser: 'playwright-webkit',
      limitations: [],
    };
  } catch (error) {
    const fallback = await chromium.launch({ headless: true });
    const normalized = normalizeError(error);
    return {
      browser: fallback,
      runtimeBrowser: 'playwright-chromium-fallback',
      limitations: [
        `Native Playwright WebKit konnte auf diesem Runner nicht gestartet werden (fallback auf Chromium/iPhone-Profil). reason=${normalized.message}`,
      ],
      webkitLaunchError: normalized,
    };
  }
}

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
  const launch = await launchPreferredBrowser();
  const browser = launch.browser;

  const limitations = Array.isArray(launch.limitations) ? [...launch.limitations] : [];
  let context = null;
  let checks = {};
  let artifacts = {};
  let runError = null;

  try {
    context = await browser.newContext({
      ...devices['iPhone 13'],
      locale: 'de-CH',
      geolocation: { latitude: 47.3769, longitude: 8.5417, accuracy: 20 },
      permissions: ['geolocation'],
    });

    const page = await openStableGuiPage(context, launch.runtimeBrowser);
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

    const interactionViaZoom =
      Number.isFinite(beforePinch.zoom) && Number.isFinite(afterPinch.zoom) && afterPinch.zoom > beforePinch.zoom;
    const interactionViaPan =
      Number.isFinite(beforePan.zoom) &&
      Number.isFinite(afterPan.zoom) &&
      beforePan.zoom === afterPan.zoom &&
      beforePan.text !== afterPan.text;

    checks = {
      guiLoad: {
        passed: true,
        detail:
          launch.runtimeBrowser === 'playwright-webkit'
            ? '/gui rendered in native WebKit context'
            : '/gui rendered in Chromium fallback context (iPhone profile)',
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

    artifacts = {
      screenshot: path.relative(repoRoot, screenshotPath),
    };
  } catch (error) {
    runError = normalizeError(error);
    checks = {
      bootstrap: {
        stage: 'openStableGuiPage',
        error: runError.message,
        passed: false,
      },
    };
  } finally {
    if (context) {
      await context.close();
    }
    await browser.close();
  }

  const ok = runError === null && Object.values(checks).every((entry) => entry.passed === true);
  const finishedAtUtc = new Date().toISOString();

  const payload = {
    issue: ISSUE_NUMBER,
    parentIssue: PARENT_ISSUE,
    startedAtUtc,
    finishedAtUtc,
    targetUrl: baseUrl,
    runtime: {
      browser: launch.runtimeBrowser,
      requestedBrowser: 'playwright-webkit',
      device: 'iPhone 13',
      headless: true,
    },
    limitations,
    checks,
    artifacts,
    webkitLaunchError: launch.webkitLaunchError || null,
    runError,
    ok,
  };

  await fs.mkdir(outDir, { recursive: true });
  const outJson = path.join(outDir, `issue-986-webkit-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  return ok;
}

run()
  .then((ok) => {
    if (!ok) {
      process.exit(1);
    }
  })
  .catch(async (error) => {
    const finishedAtUtc = new Date().toISOString();
    const payload = {
      issue: ISSUE_NUMBER,
      parentIssue: PARENT_ISSUE,
      startedAtUtc: finishedAtUtc,
      finishedAtUtc,
      targetUrl: baseUrl,
      runtime: {
        browser: 'unknown',
        requestedBrowser: 'playwright-webkit',
        device: 'iPhone 13',
        headless: true,
      },
      limitations: [],
      checks: {},
      artifacts: {},
      webkitLaunchError: null,
      runError: normalizeError(error),
      ok: false,
    };

    await fs.mkdir(outDir, { recursive: true });
    const outJson = path.join(outDir, `issue-986-webkit-smoke-${stamp}.json`);
    await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');
    console.log(path.relative(repoRoot, outJson));
    process.exit(1);
  });
