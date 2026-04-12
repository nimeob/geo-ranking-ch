#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';

const issueNumber = 981;
const scriptRelPath = 'scripts/run_issue_981_mobile_smoke.mjs';
const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const guiStabilityWaitMs = Number.parseInt(process.env.GUI_STABILITY_WAIT_MS || '1200', 10);
const baseUrlProbeTimeoutMs = Number.parseInt(process.env.BASE_URL_PROBE_TIMEOUT_MS || '5000', 10);
const repoRoot = process.cwd();
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

function buildUsage() {
  return [
    `Usage: node ${scriptRelPath}`,
    '',
    'Issue #981 Mobile E2E Smoke.',
    'Prüft iOS/Android Mobile-Map-Interaktionen + Geolocation-Fallback auf /gui.',
    '',
    'Options:',
    '  -h, --help   Show this help and exit.',
    '',
    'Environment:',
    `  BASE_URL=${baseUrl}`,
    `  GUI_STABILITY_WAIT_MS=${guiStabilityWaitMs}`,
    `  BASE_URL_PROBE_TIMEOUT_MS=${baseUrlProbeTimeoutMs}`,
  ].join('\n');
}

function parseCliArgs(argv) {
  const args = Array.isArray(argv) ? argv : [];
  const unknown = [];
  let help = false;

  for (const arg of args) {
    if (arg === '-h' || arg === '--help') {
      help = true;
      continue;
    }
    unknown.push(arg);
  }

  return { help, unknown };
}

const cli = parseCliArgs(process.argv.slice(2));
if (cli.help) {
  console.log(buildUsage());
  process.exit(0);
}
if (cli.unknown.length > 0) {
  console.error(`[issue-${issueNumber}-mobile-e2e-smoke] unknown_cli_args=${cli.unknown.join(',')}`);
  console.error(buildUsage());
  process.exit(2);
}

async function loadChromium() {
  try {
    const playwrightModule = await import('playwright');
    if (playwrightModule?.chromium) {
      return playwrightModule.chromium;
    }
    throw new Error('chromium export missing');
  } catch (error) {
    const normalized = normalizeError(error);
    throw new Error(
      `Playwright Chromium nicht verfügbar. Installiere die Node-Abhängigkeiten mit \`npm ci\` `
      + `und anschließend Browser-Binaries via \`npx playwright install --with-deps chromium\`. `
      + `Ursache: ${normalized.name}: ${normalized.message}`
    );
  }
}

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

class BaseUrlReachabilityError extends Error {
  constructor(message, { targetUrl, reasonCode, hint, cause } = {}) {
    super(message, cause ? { cause } : undefined);
    this.name = 'BaseUrlReachabilityError';
    this.targetUrl = targetUrl || '';
    this.reasonCode = reasonCode || 'unreachable';
    this.hint = hint || '';
  }
}

function compactMessage(message, maxLength = 320) {
  const normalized = String(message || '').replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength)}…`;
}

function isLocalHost(hostname) {
  const host = String(hostname || '').trim().toLowerCase();
  return host === '127.0.0.1' || host === 'localhost' || host === '::1';
}

function classifyConnectivityReason(error) {
  const message = String(error?.message || '');
  const causeCode = String(error?.cause?.code || '');
  const causeName = String(error?.cause?.name || '');
  const raw = `${message} ${causeCode} ${causeName}`.toLowerCase();
  const upper = `${causeCode} ${causeName}`.toUpperCase();

  if (upper.includes('CERT_HAS_EXPIRED') || raw.includes('certificate has expired')) return 'tls_cert_has_expired';
  if (upper.includes('ERR_TLS_CERT_ALTNAME_INVALID') || raw.includes('hostname/ip does not match certificate')) {
    return 'tls_hostname_mismatch';
  }
  if (
    upper.includes('DEPTH_ZERO_SELF_SIGNED_CERT')
    || upper.includes('SELF_SIGNED_CERT_IN_CHAIN')
    || upper.includes('UNABLE_TO_VERIFY_LEAF_SIGNATURE')
    || upper.includes('UNABLE_TO_GET_ISSUER_CERT_LOCALLY')
    || raw.includes('self signed certificate')
    || raw.includes('unable to verify the first certificate')
  ) {
    return 'tls_untrusted_ca';
  }
  if (raw.includes('tls') || raw.includes('certificate')) return 'tls_handshake_failed';

  if (raw.includes('econnrefused') || raw.includes('err_connection_refused')) return 'connection_refused';
  if (raw.includes('enotfound') || raw.includes('name_not_resolved') || raw.includes('err_name_not_resolved')) {
    return 'dns_not_found';
  }
  if (raw.includes('etimedout') || raw.includes('aborted') || raw.includes('timeout')) return 'timeout';
  if (raw.includes('econnreset') || raw.includes('err_connection_reset')) return 'connection_reset';
  return 'unreachable';
}

function buildBaseUrlReachabilityHint(targetUrl, reasonCode) {
  let parsed;
  try {
    parsed = new URL(targetUrl);
  } catch {
    return 'BASE_URL ist ungültig. Bitte vollständige URL inkl. Schema prüfen (z. B. http://127.0.0.1:8877/gui oder https://www.dev.georanking.ch/gui).';
  }

  if (isLocalHost(parsed.hostname)) {
    return [
      `Lokalen GUI-Server starten (Default): HOST=127.0.0.1 PORT=${parsed.port || '8877'} APP_VERSION=dev python3 -m src.web_service`,
      `Danach Smoke erneut ausführen: BASE_URL=\"${targetUrl}\" node scripts/run_issue_981_mobile_smoke.mjs`,
      `reason=${reasonCode}`,
    ].join(' | ');
  }

  if (reasonCode === 'tls_cert_has_expired') {
    return [
      `Ziel-URL nicht erreichbar: ${targetUrl}`,
      'TLS-Zertifikat ist abgelaufen. Zertifikat erneuern und Deploy/LB-Listener neu laden.',
      `reason=${reasonCode}`,
    ].join(' | ');
  }

  if (reasonCode === 'tls_hostname_mismatch') {
    return [
      `Ziel-URL nicht erreichbar: ${targetUrl}`,
      'TLS-Hostname-Mismatch. SAN/CN des Zertifikats gegen die Base-URL prüfen.',
      `reason=${reasonCode}`,
    ].join(' | ');
  }

  if (reasonCode === 'tls_untrusted_ca' || reasonCode === 'tls_handshake_failed') {
    return [
      `Ziel-URL nicht erreichbar: ${targetUrl}`,
      'TLS-Verifikation fehlgeschlagen. Trust-Chain/CA-Bundle und Frontdoor-Zertifikat prüfen.',
      `reason=${reasonCode}`,
    ].join(' | ');
  }

  return [
    `Ziel-URL nicht erreichbar: ${targetUrl}`,
    'Prüfe DNS/TLS/Ingress und ob /gui ohne Auth-Block erreichbar ist.',
    `reason=${reasonCode}`,
  ].join(' | ');
}

async function assertBaseUrlReachable(targetUrl, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Math.max(200, timeoutMs));

  try {
    const response = await fetch(targetUrl, {
      method: 'GET',
      redirect: 'manual',
      signal: controller.signal,
      headers: { Accept: 'text/html,*/*;q=0.8' },
    });

    return {
      ok: true,
      status: response.status,
      finalUrl: String(response.url || targetUrl),
    };
  } catch (error) {
    const reasonCode = classifyConnectivityReason(error);
    const hint = buildBaseUrlReachabilityHint(targetUrl, reasonCode);
    throw new BaseUrlReachabilityError(
      `BASE_URL nicht erreichbar (${reasonCode}): ${targetUrl}. reason=${compactMessage(error?.message || error, 240)}. hint=${hint}`,
      { targetUrl, reasonCode, hint, cause: error }
    );
  } finally {
    clearTimeout(timer);
  }
}

function normalizeError(error) {
  const hint = typeof error?.hint === 'string' ? error.hint : '';
  const reasonCode = typeof error?.reasonCode === 'string' ? error.reasonCode : '';
  const targetUrl = typeof error?.targetUrl === 'string' ? error.targetUrl : '';

  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack || '',
      ...(hint ? { hint } : {}),
      ...(reasonCode ? { reasonCode } : {}),
      ...(targetUrl ? { targetUrl } : {}),
    };
  }
  return {
    name: 'Error',
    message: String(error || 'unknown error'),
    stack: '',
    ...(hint ? { hint } : {}),
    ...(reasonCode ? { reasonCode } : {}),
    ...(targetUrl ? { targetUrl } : {}),
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

async function pinchOnMapSyntheticPointer(page) {
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

    await new Promise((resolve) => setTimeout(resolve, 220));
  });
}

async function pinchOnMapChromiumCdp(page, context) {
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

function pinchIncreasedZoom(before, after) {
  return Number.isFinite(before?.zoom) && Number.isFinite(after?.zoom) && after.zoom > before.zoom;
}

async function runPinchWithFallback(page, context) {
  const before = await readMeta(page);
  await pinchOnMapSyntheticPointer(page);
  const afterSynthetic = await readMeta(page);

  if (pinchIncreasedZoom(before, afterSynthetic)) {
    return {
      before,
      after: afterSynthetic,
      method: 'synthetic_pointer',
      fallbackAttempted: false,
      fallbackUsed: false,
      fallbackError: null,
      passed: true,
    };
  }

  try {
    await pinchOnMapChromiumCdp(page, context);
    const afterCdp = await readMeta(page);
    const passed = pinchIncreasedZoom(before, afterCdp);
    return {
      before,
      after: afterCdp,
      method: passed ? 'chromium_cdp_synthesizePinchGesture' : 'synthetic_pointer',
      fallbackAttempted: true,
      fallbackUsed: passed,
      fallbackError: null,
      passed,
      syntheticResult: afterSynthetic,
    };
  } catch (error) {
    return {
      before,
      after: afterSynthetic,
      method: 'synthetic_pointer',
      fallbackAttempted: true,
      fallbackUsed: false,
      fallbackError: error instanceof Error ? error.message : String(error || 'unknown error'),
      passed: false,
    };
  }
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

  const pinchResult = await runPinchWithFallback(page, context);

  const beforePan = await readMeta(page);
  await panMap(page);
  const afterPan = await readMeta(page);

  const geoSuccess = await geolocSuccess(page);

  const screenshotPath = path.join(outDir, `issue-981-${device.key}-${stamp}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const markerCheck = await setMarkerOrDetectAuthRedirect(page);

  await context.close();

  const geoDenied = await geolocDenied(browser, device);

  const pinchPassed = pinchResult.passed === true;
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
        before: pinchResult.before,
        after: pinchResult.after,
        passed: pinchPassed,
        method: pinchResult.method,
        fallbackAttempted: pinchResult.fallbackAttempted,
        fallbackUsed: pinchResult.fallbackUsed,
        fallbackError: pinchResult.fallbackError,
        syntheticResult: pinchResult.syntheticResult || null,
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
    await assertBaseUrlReachable(baseUrl, baseUrlProbeTimeoutMs);
    const chromium = await loadChromium();
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
    issue: issueNumber,
    parentIssue: 975,
    startedAtUtc,
    finishedAtUtc,
    targetUrl: baseUrl,
    baseUrlProbeTimeoutMs,
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
    issue: issueNumber,
    parentIssue: 975,
    startedAtUtc: finishedAtUtc,
    finishedAtUtc,
    targetUrl: baseUrl,
    baseUrlProbeTimeoutMs,
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
