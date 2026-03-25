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

function parseBooleanEnv(name) {
  const value = String(process.env[name] || '').trim().toLowerCase();
  return value === '1' || value === 'true' || value === 'yes' || value === 'on';
}

const requireNativeWebkit = parseBooleanEnv('REQUIRE_NATIVE_WEBKIT');

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

function extractMissingWebkitLibraries(message) {
  const lines = String(message || '').split(/\r?\n/);
  const libraries = [];
  let inMissingLibrariesSection = false;

  for (const line of lines) {
    if (!inMissingLibrariesSection) {
      if (/Missing libraries:/i.test(line)) {
        inMissingLibrariesSection = true;
      }
      continue;
    }

    if (/^[\s║]*╚/.test(line)) {
      break;
    }

    const matches = line.match(/lib[^\s║]+/g) || [];
    for (const lib of matches) {
      if (!libraries.includes(lib)) {
        libraries.push(lib);
      }
    }
  }

  return libraries;
}

function compactMessage(message, maxLength = 260) {
  const normalized = String(message || '').replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength)}…`;
}

async function launchPreferredBrowser({ requireNativeWebkit }) {
  const installHint = 'npx playwright install --with-deps webkit';

  try {
    return {
      browser: await webkit.launch({ headless: true }),
      runtimeBrowser: 'playwright-webkit',
      limitations: [],
      webkitMissingLibraries: [],
      webkitInstallHint: installHint,
    };
  } catch (error) {
    const normalized = normalizeError(error);
    const webkitMissingLibraries = extractMissingWebkitLibraries(normalized.message);

    if (requireNativeWebkit) {
      const reason =
        webkitMissingLibraries.length > 0
          ? `fehlende WebKit-Libraries: ${webkitMissingLibraries.join(', ')}`
          : compactMessage(normalized.message, 360);
      throw new Error(
        `Native Playwright WebKit ist verpflichtend, konnte aber nicht gestartet werden. reason=${reason}. hint=${installHint}`
      );
    }

    const fallback = await chromium.launch({ headless: true });
    const reason =
      webkitMissingLibraries.length > 0
        ? `fehlende WebKit-Libraries (${webkitMissingLibraries.length}): ${webkitMissingLibraries.slice(0, 8).join(', ')}${webkitMissingLibraries.length > 8 ? ', …' : ''}`
        : compactMessage(normalized.message, 240);

    return {
      browser: fallback,
      runtimeBrowser: 'playwright-chromium-fallback',
      limitations: [
        `Native Playwright WebKit konnte auf diesem Runner nicht gestartet werden (fallback auf Chromium/iPhone-Profil). reason=${reason}. hint=${installHint}`,
      ],
      webkitLaunchError: normalized,
      webkitMissingLibraries,
      webkitInstallHint: installHint,
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

async function pinchMapSyntheticPointer(page) {
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

function pinchIncreasedZoom(before, after) {
  return Number.isFinite(before?.zoom) && Number.isFinite(after?.zoom) && after.zoom > before.zoom;
}

async function pinchMapChromiumCdp(page, context) {
  const surfaceCenter = await page.evaluate(() => {
    const surface = document.getElementById('map-click-surface');
    if (!surface) {
      throw new Error('map-click-surface not found');
    }
    surface.scrollIntoView({ block: 'center', inline: 'center' });
    const rect = surface.getBoundingClientRect();
    const viewportWidth = Math.max(1, window.innerWidth || document.documentElement.clientWidth || 1);
    const viewportHeight = Math.max(1, window.innerHeight || document.documentElement.clientHeight || 1);
    const x = Math.round(Math.min(Math.max(rect.left + rect.width / 2, 2), viewportWidth - 2));
    const y = Math.round(Math.min(Math.max(rect.top + rect.height / 2, 2), viewportHeight - 2));
    return { x, y, viewportWidth, viewportHeight };
  });

  const cdp = await context.newCDPSession(page);
  await cdp.send('Input.synthesizePinchGesture', {
    x: surfaceCenter.x,
    y: surfaceCenter.y,
    scaleFactor: 1.8,
    relativeSpeed: 800,
    gestureSourceType: 'touch',
  });

  await page.waitForTimeout(260);
}

async function runPinchWithFallback(page, context, runtimeBrowser) {
  const before = await readMapMeta(page);
  await pinchMapSyntheticPointer(page);
  const afterSynthetic = await readMapMeta(page);

  if (pinchIncreasedZoom(before, afterSynthetic)) {
    return {
      before,
      after: afterSynthetic,
      passed: true,
      method: 'synthetic_pointer',
      fallbackAttempted: false,
      fallbackUsed: false,
      fallbackError: null,
      syntheticResult: null,
    };
  }

  const canUseCdpFallback = String(runtimeBrowser || '').startsWith('playwright-chromium');
  if (!canUseCdpFallback) {
    return {
      before,
      after: afterSynthetic,
      passed: false,
      method: 'synthetic_pointer',
      fallbackAttempted: false,
      fallbackUsed: false,
      fallbackError: null,
      syntheticResult: null,
    };
  }

  try {
    await pinchMapChromiumCdp(page, context);
    const afterCdp = await readMapMeta(page);
    const passed = pinchIncreasedZoom(before, afterCdp);
    return {
      before,
      after: afterCdp,
      passed,
      method: passed ? 'chromium_cdp_synthesizePinchGesture' : 'synthetic_pointer',
      fallbackAttempted: true,
      fallbackUsed: passed,
      fallbackError: null,
      syntheticResult: afterSynthetic,
    };
  } catch (error) {
    return {
      before,
      after: afterSynthetic,
      passed: false,
      method: 'synthetic_pointer',
      fallbackAttempted: true,
      fallbackUsed: false,
      fallbackError: error instanceof Error ? error.message : String(error || 'unknown error'),
      syntheticResult: null,
    };
  }
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
  const launch = await launchPreferredBrowser({ requireNativeWebkit });
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

    const pinchResult = await runPinchWithFallback(page, context, launch.runtimeBrowser);

    const beforePan = await readMapMeta(page);
    await panMap(page);
    const afterPan = await readMapMeta(page);

    await fs.mkdir(outDir, { recursive: true });
    const screenshotPath = path.join(outDir, `issue-986-webkit-ios-${stamp}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });

    const interactionViaZoom = pinchResult.passed === true;
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
          before: pinchResult.before,
          after: pinchResult.after,
          passed: interactionViaZoom,
          method: pinchResult.method,
          fallbackAttempted: pinchResult.fallbackAttempted,
          fallbackUsed: pinchResult.fallbackUsed,
          fallbackError: pinchResult.fallbackError,
          syntheticResult: pinchResult.syntheticResult,
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
      requireNativeWebkit,
      nativeWebkitActive: launch.runtimeBrowser === 'playwright-webkit',
      webkitMissingLibraries: Array.isArray(launch.webkitMissingLibraries) ? launch.webkitMissingLibraries : [],
      webkitInstallHint: launch.webkitInstallHint || 'npx playwright install --with-deps webkit',
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
        requireNativeWebkit,
        nativeWebkitActive: false,
        webkitMissingLibraries: [],
        webkitInstallHint: 'npx playwright install --with-deps webkit',
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
