#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const issueNumber = 1016;
const scriptRelPath = 'scripts/run_issue_1016_mobile_ux_smoke.mjs';
const DEFAULT_BASE_URL = 'http://127.0.0.1:8877/gui';
const DEFAULT_GUI_STABILITY_WAIT_MS = 1200;
const DEFAULT_BASE_URL_PROBE_TIMEOUT_MS = 5000;
const LEGACY_DEV_UI_HOSTS = new Set(['dev.georanking.ch', 'dev.geo-ranking.ch']);
const scriptPath = fileURLToPath(import.meta.url);
const scriptDir = path.dirname(scriptPath);
const repoRoot = path.resolve(scriptDir, '..');
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

function normalizeUiBaseUrl(rawBaseUrl) {
  const candidate = String(rawBaseUrl || '').trim();
  if (!candidate) {
    return {
      value: '',
      requested: '',
      changed: false,
      reasons: [],
      error: '',
    };
  }

  let parsed;
  try {
    parsed = new URL(candidate);
  } catch {
    return {
      value: candidate,
      requested: candidate,
      changed: false,
      reasons: [],
      error: 'must be an absolute URL (e.g. https://www.dev.georanking.ch/gui)',
    };
  }

  const protocol = String(parsed.protocol || '').toLowerCase();
  if (protocol !== 'http:' && protocol !== 'https:') {
    return {
      value: candidate,
      requested: candidate,
      changed: false,
      reasons: [],
      error: `unsupported protocol '${protocol || '(missing)'}' (expected http: or https:)`,
    };
  }

  const reasons = [];
  let canonicalHost = String(parsed.hostname || '').trim().toLowerCase();
  if (!canonicalHost) {
    return {
      value: candidate,
      requested: candidate,
      changed: false,
      reasons: [],
      error: 'hostname is missing',
    };
  }

  const strippedTrailingDotHost = canonicalHost.replace(/\.+$/, '');
  if (strippedTrailingDotHost !== canonicalHost) {
    canonicalHost = strippedTrailingDotHost;
    reasons.push('trailing_dot');
  }

  if (LEGACY_DEV_UI_HOSTS.has(canonicalHost)) {
    canonicalHost = `www.${canonicalHost}`;
    reasons.push('legacy_dev_non_www');
  }

  parsed.hostname = canonicalHost;
  const normalizedPath = parsed.pathname === '/' ? '' : parsed.pathname;
  const normalized = `${parsed.protocol}//${parsed.host}${normalizedPath}${parsed.search}${parsed.hash}`;

  return {
    value: normalized,
    requested: candidate,
    changed: normalized !== candidate,
    reasons,
    error: '',
  };
}

function buildUsage() {
  return [
    `Usage: node ${scriptRelPath}`,
    '',
    'Issue #1016 Mobile-UX-Smoke.',
    'Prüft Burger-Menü UX + Pinch-Zoom Smoothness auf /gui.',
    '',
    'Options:',
    '  -h, --help              Show this help and exit.',
    `  --base-url <url>       Override BASE_URL (default: ${DEFAULT_BASE_URL})`,
    '  --evidence-json <path> Override JSON evidence output path.',
    '  --json-out <path>      Alias für --evidence-json (legacy compatibility).',
    '  --headless             Accepted for compatibility (runner is always headless).',
    '',
    'Environment:',
    `  BASE_URL=${DEFAULT_BASE_URL}`,
    `  GUI_STABILITY_WAIT_MS=${DEFAULT_GUI_STABILITY_WAIT_MS}`,
    `  BASE_URL_PROBE_TIMEOUT_MS=${DEFAULT_BASE_URL_PROBE_TIMEOUT_MS}`,
  ].join('\n');
}

function parseCliArgs(argv) {
  const args = Array.isArray(argv) ? argv : [];
  const unknown = [];
  const options = {
    help: false,
    baseUrl: '',
    evidenceJson: '',
  };

  const consumeValue = (flag, inlineValue, currentArgs, index) => {
    if (inlineValue !== null) return inlineValue;
    const next = currentArgs[index + 1];
    if (typeof next !== 'string' || next.startsWith('-')) {
      throw new Error(`Missing value for ${flag}`);
    }
    return next;
  };

  for (let i = 0; i < args.length; i += 1) {
    const raw = String(args[i] || '').trim();
    if (!raw) continue;

    if (raw === '-h' || raw === '--help') {
      options.help = true;
      continue;
    }

    const eqIdx = raw.indexOf('=');
    const flag = eqIdx >= 0 ? raw.slice(0, eqIdx) : raw;
    const inlineValue = eqIdx >= 0 ? raw.slice(eqIdx + 1) : null;

    switch (flag) {
      case '--base-url':
        options.baseUrl = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--evidence-json':
      case '--json-out':
        options.evidenceJson = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--headless':
        break;
      default:
        unknown.push(raw);
        break;
    }
  }

  return { ...options, unknown };
}

const cli = (() => {
  try {
    return parseCliArgs(process.argv.slice(2));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error || 'unknown error');
    console.error(`[issue-${issueNumber}-mobile-ux-smoke] ${message}`);
    console.error(buildUsage());
    process.exit(2);
  }
})();
if (cli.help) {
  console.log(buildUsage());
  process.exit(0);
}
if (cli.unknown.length > 0) {
  console.error(`[issue-${issueNumber}-mobile-ux-smoke] unknown_cli_args=${cli.unknown.join(',')}`);
  console.error(buildUsage());
  process.exit(2);
}

const baseUrl = String(cli.baseUrl || process.env.BASE_URL || DEFAULT_BASE_URL).trim() || DEFAULT_BASE_URL;
const baseUrlNormalization = normalizeUiBaseUrl(baseUrl);
const targetUrl = baseUrlNormalization.value || baseUrl;
const guiStabilityWaitMs = Number.parseInt(
  process.env.GUI_STABILITY_WAIT_MS || String(DEFAULT_GUI_STABILITY_WAIT_MS),
  10,
);
const baseUrlProbeTimeoutMs = Number.parseInt(
  process.env.BASE_URL_PROBE_TIMEOUT_MS || String(DEFAULT_BASE_URL_PROBE_TIMEOUT_MS),
  10,
);
const outputJsonPath = (() => {
  const rawPath = String(cli.evidenceJson || '').trim();
  if (!rawPath) return '';
  if (path.isAbsolute(rawPath)) return path.normalize(rawPath);
  return path.resolve(repoRoot, rawPath);
})();

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
      `Danach Smoke erneut ausführen: BASE_URL=\"${targetUrl}\" node scripts/run_issue_1016_mobile_ux_smoke.mjs`,
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
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${currentUrl} (target=${targetUrl}, waitMs=${guiStabilityWaitMs}).`
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
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${authUrl} (target=${targetUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  if (winner.kind === 'gui-ready') {
    return;
  }

  const finalUrl = page.url();
  if (isAuthRedirectUrl(finalUrl)) {
    throw new Error(
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${finalUrl} (target=${targetUrl}, waitMs=${guiStabilityWaitMs}).`
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

async function openStableGuiPage(context) {
  const page = await context.newPage();
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(Math.max(0, guiStabilityWaitMs));

  await waitForGuiOrAuthRedirect(page, {
    stageLabel: 'mobile-ux',
    selector: '#analyze-form',
    timeoutMs: 20_000,
  });

  return page;
}

async function readMetaZoom(page) {
  const text = (await page.locator('#map-view-meta').textContent()) || '';
  const match = /Zoom\s+(\d+)/i.exec(text);
  return {
    text: text.trim(),
    zoom: match ? Number(match[1]) : null,
  };
}

async function runBurgerSmoke(page) {
  const burgerBtn = page.locator('#burger-btn');
  const burgerMenu = page.locator('#burger-menu');
  const burgerBackdrop = page.locator('#burger-backdrop');

  await burgerBtn.click();
  await page.waitForTimeout(120);

  const openState = await page.evaluate(() => ({
    expanded: document.getElementById('burger-btn')?.getAttribute('aria-expanded') || null,
    menuHidden: document.getElementById('burger-menu')?.hasAttribute('hidden') ?? true,
    menuAriaHidden: document.getElementById('burger-menu')?.getAttribute('aria-hidden') || null,
    backdropHidden: document.getElementById('burger-backdrop')?.hasAttribute('hidden') ?? true,
    bodyBurgerOpen: document.body.classList.contains('burger-open'),
  }));

  await burgerBackdrop.click({ position: { x: 2, y: 2 } });
  await page.waitForTimeout(120);

  const closeState = await page.evaluate(() => ({
    expanded: document.getElementById('burger-btn')?.getAttribute('aria-expanded') || null,
    menuHidden: document.getElementById('burger-menu')?.hasAttribute('hidden') ?? false,
    menuAriaHidden: document.getElementById('burger-menu')?.getAttribute('aria-hidden') || null,
    backdropHidden: document.getElementById('burger-backdrop')?.hasAttribute('hidden') ?? false,
    bodyBurgerOpen: document.body.classList.contains('burger-open'),
    activeElementId: document.activeElement?.id || '',
  }));

  const passed =
    openState.expanded === 'true' &&
    openState.menuHidden === false &&
    openState.menuAriaHidden === 'false' &&
    openState.backdropHidden === false &&
    openState.bodyBurgerOpen === true &&
    closeState.expanded === 'false' &&
    closeState.menuHidden === true &&
    closeState.menuAriaHidden === 'true' &&
    closeState.backdropHidden === true &&
    closeState.bodyBurgerOpen === false;

  return {
    openState,
    closeState,
    passed,
  };
}

async function runPinchSmoke(page) {
  const before = await readMetaZoom(page);

  const pinchResult = await page.evaluate(async () => {
    const surface = document.getElementById('map-click-surface');
    if (!surface) throw new Error('map-click-surface not found');

    const longTasks = [];
    let observer = null;
    if (typeof PerformanceObserver !== 'undefined') {
      observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          longTasks.push(Number(entry.duration || 0));
        }
      });
      try {
        observer.observe({ entryTypes: ['longtask'] });
      } catch {
        observer = null;
      }
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

    const rafDeltas = [];
    let previous = performance.now();
    for (let i = 0; i < 10; i += 1) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
      const now = performance.now();
      rafDeltas.push(now - previous);
      previous = now;
    }

    fire('pointerdown', 1, cx - 28, cy);
    fire('pointerdown', 2, cx + 28, cy);

    for (let step = 0; step < 9; step += 1) {
      const offset = 28 + step * 9;
      fire('pointermove', 1, cx - offset, cy - 4);
      fire('pointermove', 2, cx + offset, cy + 4);
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }

    fire('pointerup', 1, cx - 118, cy - 6);
    fire('pointerup', 2, cx + 118, cy + 6);

    await new Promise((resolve) => setTimeout(resolve, 220));

    observer?.disconnect();

    const maxRafDelta = rafDeltas.length ? Math.max(...rafDeltas) : null;
    const maxLongTaskMs = longTasks.length ? Math.max(...longTasks) : 0;

    return {
      maxRafDelta,
      longTaskCount: longTasks.length,
      maxLongTaskMs,
    };
  });

  const after = await readMetaZoom(page);
  const passed =
    Number.isFinite(before.zoom) &&
    Number.isFinite(after.zoom) &&
    after.zoom > before.zoom &&
    Number.isFinite(pinchResult.maxLongTaskMs) &&
    pinchResult.maxLongTaskMs <= 50;

  return {
    before,
    after,
    perf: pinchResult,
    passed,
  };
}

async function main() {
  const startedAtUtc = new Date().toISOString();
  let browser = null;
  let context = null;
  let screenshotPath = '';
  let burger = null;
  let pinch = null;
  let runError = null;

  try {
    await assertBaseUrlReachable(targetUrl, baseUrlProbeTimeoutMs);

    const chromium = await loadChromium();
    browser = await chromium.launch({ headless: true });
    context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      userAgent:
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
      isMobile: true,
      hasTouch: true,
      locale: 'de-CH',
    });

    const page = await openStableGuiPage(context);

    burger = await runBurgerSmoke(page);
    pinch = await runPinchSmoke(page);

    await fs.mkdir(outDir, { recursive: true });
    screenshotPath = path.join(outDir, `issue-${issueNumber}-mobile-ux-${stamp}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
  } catch (error) {
    runError = normalizeError(error);
  } finally {
    if (context) {
      await context.close();
    }
    if (browser) {
      await browser.close();
    }
  }

  const checks =
    runError === null
      ? {
          burgerMenuUx: burger,
          pinchZoomSmoothness: pinch,
        }
      : {
          bootstrap: {
            stage: 'openStableGuiPage',
            error: runError.message,
            passed: false,
          },
        };

  const ok = runError === null && burger?.passed === true && pinch?.passed === true;
  const finishedAtUtc = new Date().toISOString();

  const payload = {
    issue: issueNumber,
    startedAtUtc,
    finishedAtUtc,
    targetUrl,
    targetUrlRequested: baseUrl,
    baseUrlCanonicalized: baseUrlNormalization.changed,
    baseUrlCanonicalizationReasons: baseUrlNormalization.reasons,
    baseUrlProbeTimeoutMs,
    checks,
    artifacts: screenshotPath
      ? {
          screenshot: path.relative(repoRoot, screenshotPath),
        }
      : {},
    runError,
    ok,
  };

  const outJson = outputJsonPath || path.join(outDir, `issue-${issueNumber}-mobile-ux-smoke-${stamp}.json`);
  await fs.mkdir(path.dirname(outJson), { recursive: true });
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!ok) process.exit(1);
}

main().catch(async (error) => {
  const finishedAtUtc = new Date().toISOString();
  const payload = {
    issue: issueNumber,
    startedAtUtc: finishedAtUtc,
    finishedAtUtc,
    targetUrl,
    targetUrlRequested: baseUrl,
    baseUrlCanonicalized: baseUrlNormalization.changed,
    baseUrlCanonicalizationReasons: baseUrlNormalization.reasons,
    baseUrlProbeTimeoutMs,
    checks: {},
    artifacts: {},
    runError: normalizeError(error),
    ok: false,
  };

  const outJson = outputJsonPath || path.join(outDir, `issue-${issueNumber}-mobile-ux-smoke-${stamp}.json`);
  await fs.mkdir(path.dirname(outJson), { recursive: true });
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');
  console.log(path.relative(repoRoot, outJson));
  process.exit(1);
});
