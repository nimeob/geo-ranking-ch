#!/usr/bin/env node

const fs = require('node:fs/promises');
const path = require('node:path');

const issueNumber = 1039;
const scriptRelPath = 'scripts/run_issue_1039_mobile_overflow_smoke.cjs';
const DEFAULT_BASE_URL = 'http://127.0.0.1:8877/gui';
const DEFAULT_GUI_STABILITY_WAIT_MS = 1200;
const DEFAULT_BASE_URL_PROBE_TIMEOUT_MS = 5000;
const LEGACY_DEV_UI_HOSTS = new Set(['dev.georanking.ch', 'dev.geo-ranking.ch']);
const repoRoot = process.cwd();
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
    'Issue #1039 Mobile Overflow Smoke.',
    'Prüft horizontalen Overflow + Kernfunktionen für mobile und desktop /gui.',
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
    '  ISSUE_1039_EVIDENCE_DIR=<dir>   Optional custom evidence output directory.',
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
    console.error(`[issue-${issueNumber}-mobile-overflow-smoke] ${message}`);
    console.error(buildUsage());
    process.exit(2);
  }
})();
if (cli.help) {
  console.log(buildUsage());
  process.exit(0);
}
if (cli.unknown.length > 0) {
  console.error(`[issue-${issueNumber}-mobile-overflow-smoke] unknown_cli_args=${cli.unknown.join(',')}`);
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
const evidenceDirEnv = String(process.env.ISSUE_1039_EVIDENCE_DIR || '').trim();
const outDir = outputJsonPath
  ? path.dirname(outputJsonPath)
  : evidenceDirEnv
    ? (path.isAbsolute(evidenceDirEnv) ? evidenceDirEnv : path.join(repoRoot, evidenceDirEnv))
    : path.join(repoRoot, 'reports', 'evidence');

class PlaywrightDependencyError extends Error {
  constructor(message, { installHint, cause } = {}) {
    super(message, cause ? { cause } : undefined);
    this.name = 'PlaywrightDependencyError';
    this.installHint = installHint || 'npm ci && npx playwright install --with-deps chromium';
    this.missingDependency = 'playwright';
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

function isLocalHost(hostname) {
  const host = String(hostname || '').trim().toLowerCase();
  return host === '127.0.0.1' || host === 'localhost' || host === '::1';
}

function classifyConnectivityReason(error) {
  const message = String(error?.message || '');
  const causeCode = String(error?.cause?.code || '');
  const causeName = String(error?.cause?.name || '');
  const raw = `${message} ${causeCode} ${causeName}`.toLowerCase();

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
  } catch (_error) {
    return 'BASE_URL ist ungültig. Bitte vollständige URL inkl. Schema prüfen (z. B. http://127.0.0.1:8877/gui oder https://www.dev.georanking.ch/gui).';
  }

  if (isLocalHost(parsed.hostname)) {
    return [
      `Lokalen GUI-Server starten (Default): HOST=127.0.0.1 PORT=${parsed.port || '8877'} APP_VERSION=dev python3 -m src.web_service`,
      `Danach Smoke erneut ausführen: BASE_URL=\"${targetUrl}\" node scripts/run_issue_1039_mobile_overflow_smoke.cjs`,
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
      `BASE_URL nicht erreichbar (${reasonCode}): ${targetUrl}. reason=${compactMessage(error?.message || error, 240)}`,
      { targetUrl, reasonCode, hint, cause: error }
    );
  } finally {
    clearTimeout(timer);
  }
}

function isPlaywrightDependencyError(error) {
  return error instanceof PlaywrightDependencyError || String(error?.name || '') === 'PlaywrightDependencyError';
}

function loadPlaywrightChromium() {
  for (const moduleName of ['playwright', 'playwright-core']) {
    try {
      // eslint-disable-next-line import/no-dynamic-require, global-require
      const playwright = require(moduleName);
      if (playwright && playwright.chromium) {
        return playwright.chromium;
      }
    } catch (_error) {
      // continue
    }
  }

  const installHint = 'npm ci && npx playwright install --with-deps chromium';
  throw new PlaywrightDependencyError(
    `Playwright dependency fehlt oder ist nicht ladbar. hint=${installHint}`,
    { installHint }
  );
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

async function openStableGuiPage(context, stageLabel) {
  const page = await context.newPage();
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
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

function normalizeRunError(error) {
  const normalized = normalizeError(error);
  const payload = {
    ...normalized,
    kind: 'script_error',
    hint: '',
  };

  if (error instanceof BaseUrlReachabilityError) {
    payload.kind = 'base_url_unreachable';
    payload.hint = error.hint || '';
    payload.targetUrl = error.targetUrl || targetUrl;
    payload.reasonCode = error.reasonCode || 'unreachable';
    return payload;
  }

  if (isPlaywrightDependencyError(error)) {
    payload.kind = 'playwright_dependency_missing';
    payload.hint = error.installHint || 'npm ci && npx playwright install --with-deps chromium';
    return payload;
  }

  const messageLower = String(payload.message || '').toLowerCase();
  if (
    messageLower.includes('err_connection_refused') ||
    messageLower.includes('econnrefused') ||
    messageLower.includes('net::err_connection_refused')
  ) {
    payload.kind = 'base_url_unreachable';
    payload.reasonCode = 'connection_refused';
    payload.hint = buildBaseUrlReachabilityHint(targetUrl, 'connection_refused');
  }

  return payload;
}

async function main() {
  const startedAtUtc = new Date().toISOString();
  let browser = null;
  let payload = null;

  try {
    const preflight = await assertBaseUrlReachable(targetUrl, baseUrlProbeTimeoutMs);

    const chromium = loadPlaywrightChromium();
    browser = await chromium.launch({ headless: true });

    const mobile = await captureMobileEvidence(browser);
    const desktop = await captureDesktopEvidence(browser);

    payload = {
      issue: issueNumber,
      targetUrl,
      targetUrlRequested: baseUrl,
      runtime: {
        playwrightDependencyMissing: false,
        playwrightInstallHint: 'npm ci && npx playwright install --with-deps chromium',
        baseUrlReachable: true,
        baseUrlProbeTimeoutMs,
        baseUrlProbeStatus: preflight.status,
        baseUrlProbeFinalUrl: preflight.finalUrl,
        baseUrlCanonicalized: baseUrlNormalization.changed,
        baseUrlCanonicalizationReasons: baseUrlNormalization.reasons,
      },
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
    const normalizedRunError = normalizeRunError(error);
    payload = {
      issue: issueNumber,
      targetUrl,
      targetUrlRequested: baseUrl,
      runtime: {
        playwrightDependencyMissing: normalizedRunError.kind === 'playwright_dependency_missing',
        playwrightInstallHint:
          normalizedRunError.kind === 'playwright_dependency_missing'
            ? normalizedRunError.hint || 'npm ci && npx playwright install --with-deps chromium'
            : 'npm ci && npx playwright install --with-deps chromium',
        baseUrlReachable: normalizedRunError.kind !== 'base_url_unreachable',
        baseUrlProbeTimeoutMs,
        baseUrlCanonicalized: baseUrlNormalization.changed,
        baseUrlCanonicalizationReasons: baseUrlNormalization.reasons,
      },
      checks: {},
      snapshots: {},
      runError: normalizedRunError,
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
  const outJson = outputJsonPath || path.join(outDir, `issue-${issueNumber}-mobile-overflow-smoke-${stamp}.json`);
  await fs.writeFile(outJson, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!payload.ok) {
    process.exit(1);
  }
}

main().catch(async (error) => {
  const outJson = outputJsonPath || path.join(outDir, `issue-${issueNumber}-mobile-overflow-smoke-${stamp}.json`);
  const normalizedRunError = normalizeRunError(error);
  const payload = {
    issue: issueNumber,
    targetUrl,
    targetUrlRequested: baseUrl,
    runtime: {
      playwrightDependencyMissing: normalizedRunError.kind === 'playwright_dependency_missing',
      playwrightInstallHint:
        normalizedRunError.kind === 'playwright_dependency_missing'
          ? normalizedRunError.hint || 'npm ci && npx playwright install --with-deps chromium'
          : 'npm ci && npx playwright install --with-deps chromium',
      baseUrlReachable: normalizedRunError.kind !== 'base_url_unreachable',
      baseUrlProbeTimeoutMs,
      baseUrlCanonicalized: baseUrlNormalization.changed,
      baseUrlCanonicalizationReasons: baseUrlNormalization.reasons,
    },
    startedAtUtc: new Date().toISOString(),
    finishedAtUtc: new Date().toISOString(),
    checks: {},
    snapshots: {},
    runError: normalizedRunError,
    ok: false,
  };

  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(outJson, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(path.relative(repoRoot, outJson));
  process.exit(1);
});
