#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const repoRoot = process.cwd();
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

const baseOrigin = String(process.env.BASE_URL || 'https://www.dev.georanking.ch').replace(/\/+$/, '');
const guiPath = normalizeGuiPath(process.env.DEV_UI_SMOKE_GUI_PATH || '/gui');
const loginReason = String(process.env.DEV_UI_SMOKE_LOGIN_REASON || 'manual_login').trim() || 'manual_login';
const loginStartUrl = `${baseOrigin}/login?next=${encodeURIComponent(guiPath)}&reason=${encodeURIComponent(loginReason)}&start=1`;

const username = String(process.env.DEV_UI_SMOKE_USERNAME || '').trim();
const password = String(process.env.DEV_UI_SMOKE_PASSWORD || '');
const runMarker =
  String(process.env.DEV_UI_SMOKE_RUN_ID || process.env.GITHUB_RUN_ID || process.env.GITHUB_RUN_NUMBER || stamp).trim() ||
  stamp;

const addressFile = process.env.DEV_UI_SMOKE_ADDRESS_FILE
  ? path.resolve(repoRoot, String(process.env.DEV_UI_SMOKE_ADDRESS_FILE))
  : path.join(repoRoot, 'scripts', 'smoke', 'ch_live_addresses.txt');

const timeoutMs = parsePositiveInt(process.env.DEV_UI_SMOKE_TIMEOUT_MS, 60_000);
const headless = !isTruthy(process.env.DEV_UI_SMOKE_HEADFUL);

function parsePositiveInt(raw, fallback) {
  const value = Number.parseInt(String(raw || ''), 10);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function isTruthy(value) {
  const normalized = String(value || '').trim().toLowerCase();
  return normalized === '1' || normalized === 'true' || normalized === 'yes' || normalized === 'on';
}

function normalizeGuiPath(rawPath) {
  const value = String(rawPath || '').trim() || '/gui';
  return value.startsWith('/') ? value : `/${value}`;
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

function safeJsonParse(raw) {
  if (typeof raw !== 'string' || raw.trim() === '') {
    return null;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function selectAddressIndex(poolSize, marker) {
  const digest = crypto.createHash('sha256').update(String(marker || ''), 'utf8').digest('hex');
  const asInt = Number.parseInt(digest.slice(0, 12), 16);
  return Number.isFinite(asInt) && poolSize > 0 ? asInt % poolSize : 0;
}

async function readAddressPool(filePath) {
  const raw = await fs.readFile(filePath, 'utf8');
  const addresses = raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#'));

  if (!addresses.length) {
    throw new Error(`Adresspool leer: ${filePath}`);
  }
  return addresses;
}

function isIdpLoginUrl(value) {
  try {
    const parsed = new URL(String(value || ''));
    const host = parsed.hostname.toLowerCase();
    const pathname = parsed.pathname.toLowerCase();
    if (!host.includes('auth.')) return false;
    return pathname === '/login' || pathname.endsWith('/login');
  } catch {
    return false;
  }
}

function isAnalyzeRequestUrl(value) {
  try {
    const parsed = new URL(String(value || ''));
    return parsed.pathname === '/analyze' || parsed.pathname.endsWith('/analyze');
  } catch {
    return false;
  }
}

function analyzePayloadCompleteness(payload) {
  const result = payload && typeof payload === 'object' ? payload.result : null;
  const data = result && typeof result === 'object' ? result.data : null;
  const modules = data && typeof data === 'object' ? data.modules : null;

  const hasSuitability = Boolean(
    modules
      && typeof modules === 'object'
      && (modules.suitability_light || (modules.summary_compact && modules.summary_compact.suitability_light))
  );
  const hasMatch = Boolean(modules && typeof modules === 'object' && modules.match);
  const matchedAddress =
    (data && data.entity && (data.entity.matched_address || data.entity.query)) ||
    '';

  const moduleCount = modules && typeof modules === 'object' ? Object.keys(modules).length : 0;

  const complete = Boolean(
    payload
      && payload.ok === true
      && result
      && typeof result === 'object'
      && data
      && typeof data === 'object'
      && modules
      && typeof modules === 'object'
      && moduleCount > 0
      && hasSuitability
      && hasMatch
      && String(matchedAddress || '').trim().length > 0
  );

  return {
    complete,
    moduleCount,
    hasSuitability,
    hasMatch,
    matchedAddress: String(matchedAddress || '').trim(),
    requestId: payload && payload.request_id ? String(payload.request_id) : '',
  };
}

async function locateFirstVisible(page, selectors, timeout) {
  for (const selector of selectors) {
    const visibleLocator = page.locator(`${selector}:visible`).first();
    try {
      await visibleLocator.waitFor({ state: 'visible', timeout: Math.max(1_000, timeout) });
      return visibleLocator;
    } catch {
      // try next selector
    }
  }
  throw new Error(`Kein sichtbares Element für Selektoren gefunden: ${selectors.join(', ')}`);
}

async function collectUiSnapshot(page) {
  return page.evaluate(() => {
    const phaseEl = document.querySelector('#phase-pill');
    const resultsMetaEl = document.querySelector('#results-meta');
    const errorBoxEl = document.querySelector('#error-box');
    const rows = Array.from(document.querySelectorAll('#results-body tr'));
    const nonEmptyRows = rows.filter((row) => {
      const emptyCell = row.querySelector('td.results-empty-cell');
      return !emptyCell;
    });

    return {
      phaseText: phaseEl ? String(phaseEl.textContent || '').trim() : '',
      phaseState: phaseEl ? String(phaseEl.getAttribute('data-phase') || '').trim() : '',
      resultsMetaText: resultsMetaEl ? String(resultsMetaEl.textContent || '').trim() : '',
      errorBoxText:
        errorBoxEl && !errorBoxEl.hasAttribute('hidden') ? String(errorBoxEl.textContent || '').trim() : '',
      resultRowCount: nonEmptyRows.length,
    };
  });
}

async function waitForTerminalUiSignal(page, timeout) {
  const handle = await page.waitForFunction(() => {
    const phaseEl = document.querySelector('#phase-pill');
    const errorBoxEl = document.querySelector('#error-box');
    const rows = Array.from(document.querySelectorAll('#results-body tr'));
    const nonEmptyRows = rows.filter((row) => !row.querySelector('td.results-empty-cell'));

    const phaseState = phaseEl ? String(phaseEl.getAttribute('data-phase') || '').trim().toLowerCase() : '';
    const phaseText = phaseEl ? String(phaseEl.textContent || '').trim().toLowerCase() : '';
    const errorBoxVisible = Boolean(errorBoxEl && !errorBoxEl.hasAttribute('hidden'));

    if (phaseState === 'success' || phaseState === 'error') {
      return {
        reason: `phase_${phaseState}`,
        phaseState,
        phaseText,
        resultRowCount: nonEmptyRows.length,
        errorBoxVisible,
      };
    }

    if (errorBoxVisible) {
      return {
        reason: 'error_box_visible',
        phaseState,
        phaseText,
        resultRowCount: nonEmptyRows.length,
        errorBoxVisible,
      };
    }

    if (nonEmptyRows.length > 0) {
      return {
        reason: 'results_rows_rendered',
        phaseState,
        phaseText,
        resultRowCount: nonEmptyRows.length,
        errorBoxVisible,
      };
    }

    return null;
  }, { timeout });

  return handle.jsonValue();
}

function maskUsername(value) {
  if (!value) return '';
  if (value.length <= 2) return `${value[0] || '*'}*`;
  return `${value[0]}***${value[value.length - 1]}`;
}

async function writeEvidence(payload) {
  await fs.mkdir(outDir, { recursive: true });
  const outJson = path.join(outDir, `dev-ui-auth-analyze-smoke-${stamp}.json`);
  await fs.writeFile(outJson, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(path.relative(repoRoot, outJson));
  return outJson;
}

async function run() {
  const startedAtUtc = new Date().toISOString();

  if (!username || !password) {
    throw new Error(
      'Fehlende Credentials: DEV_UI_SMOKE_USERNAME und DEV_UI_SMOKE_PASSWORD sind für echten Live-Login erforderlich.'
    );
  }

  const addressPool = await readAddressPool(addressFile);
  const addressIndex = selectAddressIndex(addressPool.length, runMarker);
  const selectedAddress = addressPool[addressIndex];

  const browser = await chromium.launch({ headless });
  const context = await browser.newContext({
    locale: 'de-CH',
    viewport: { width: 1536, height: 960 },
  });
  const page = await context.newPage();

  const flowResponses = [];
  page.on('response', (response) => {
    try {
      const url = new URL(response.url());
      if (url.pathname === '/analyze' || url.pathname === '/auth/me' || url.pathname.startsWith('/auth/')) {
        flowResponses.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        });
      }
    } catch {
      // ignore malformed URLs
    }
  });

  let idpLoginUrl = '';
  let finalUrl = '';
  let authMeStatus = null;
  let authMeBody = null;
  let analyzeRequestPayload = null;
  let analyzeResponseBody = null;
  let analyzeResponseStatus = null;
  let analyzeResponseUrl = '';
  let phaseText = '';
  let phaseState = '';
  let resultsMetaText = '';
  let errorBoxText = '';
  let resultRowCount = 0;
  let terminalUiSignal = null;
  let terminalUiSignalTimeout = false;
  let screenshotRelPath = '';

  try {
    await page.goto(loginStartUrl, { waitUntil: 'domcontentloaded' });

    await page.waitForURL((url) => isIdpLoginUrl(String(url)), { timeout: timeoutMs });
    idpLoginUrl = page.url();

    const usernameField = await locateFirstVisible(
      page,
      ['input[name="username"]', '#username', 'input[type="email"]', 'input[name="email"]'],
      timeoutMs
    );
    const passwordField = await locateFirstVisible(
      page,
      ['input[name="password"]', '#password', 'input[type="password"]'],
      timeoutMs
    );

    await usernameField.fill(username);
    await passwordField.fill(password);

    const submitButton = await locateFirstVisible(
      page,
      ['button[type="submit"]', 'input[type="submit"]', 'button[name="signInSubmitButton"]', 'input[name="signInSubmitButton"]'],
      timeoutMs
    );

    await Promise.all([
      page.waitForURL(
        (url) => {
          try {
            const parsed = new URL(String(url));
            return parsed.origin === baseOrigin && parsed.pathname === guiPath;
          } catch {
            return false;
          }
        },
        { timeout: timeoutMs }
      ),
      submitButton.click(),
    ]);

    await page.locator('#analyze-form').waitFor({ state: 'visible', timeout: timeoutMs });

    const authMeEval = await page.evaluate(async () => {
      const response = await fetch('/auth/me', {
        method: 'GET',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      let parsed = null;
      try {
        parsed = await response.json();
      } catch {
        parsed = null;
      }
      return {
        status: response.status,
        body: parsed,
      };
    });
    authMeStatus = authMeEval.status;
    authMeBody = authMeEval.body;

    await page.locator('#query').fill(selectedAddress);
    await page.locator('#intelligence-mode').selectOption('basic');

    const analyzeRequestPromise = page.waitForRequest(
      (request) => request.method() === 'POST' && isAnalyzeRequestUrl(request.url()),
      { timeout: timeoutMs }
    );
    const analyzeResponsePromise = page.waitForResponse(
      (response) => response.request().method() === 'POST' && isAnalyzeRequestUrl(response.url()),
      { timeout: timeoutMs }
    );

    await Promise.all([analyzeRequestPromise, analyzeResponsePromise, page.locator('#submit-btn').click()]);

    const analyzeRequest = await analyzeRequestPromise;
    const analyzeResponse = await analyzeResponsePromise;

    analyzeResponseStatus = analyzeResponse.status();
    analyzeResponseUrl = analyzeResponse.url();

    const requestRaw = analyzeRequest.postData() || '';
    analyzeRequestPayload = safeJsonParse(requestRaw);

    try {
      analyzeResponseBody = await analyzeResponse.json();
    } catch {
      const responseText = await analyzeResponse.text().catch(() => '');
      analyzeResponseBody = safeJsonParse(responseText) || { _raw: responseText.slice(0, 2_000) };
    }

    try {
      terminalUiSignal = await waitForTerminalUiSignal(page, timeoutMs);
    } catch {
      terminalUiSignalTimeout = true;
    }

    const uiSnapshot = await collectUiSnapshot(page);
    phaseText = uiSnapshot.phaseText;
    phaseState = uiSnapshot.phaseState;
    resultsMetaText = uiSnapshot.resultsMetaText;
    errorBoxText = uiSnapshot.errorBoxText;
    resultRowCount = uiSnapshot.resultRowCount;

    finalUrl = page.url();

    await fs.mkdir(outDir, { recursive: true });
    const screenshotPath = path.join(outDir, `dev-ui-auth-analyze-smoke-${stamp}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    screenshotRelPath = path.relative(repoRoot, screenshotPath);
  } finally {
    if (!screenshotRelPath) {
      try {
        await fs.mkdir(outDir, { recursive: true });
        const fallbackScreenshotPath = path.join(outDir, `dev-ui-auth-analyze-smoke-${stamp}.png`);
        await page.screenshot({ path: fallbackScreenshotPath, fullPage: true });
        screenshotRelPath = path.relative(repoRoot, fallbackScreenshotPath);
      } catch {
        // ignore screenshot fallback errors
      }
    }

    await context.close();
    await browser.close();
  }

  const analyzeCompleteness = analyzePayloadCompleteness(analyzeResponseBody);
  const authMeAuthenticated =
    authMeStatus === 200
    && authMeBody
    && typeof authMeBody === 'object'
    && (authMeBody.authenticated === true || authMeBody.ok === true);

  const submittedQuery =
    analyzeRequestPayload && typeof analyzeRequestPayload === 'object' && typeof analyzeRequestPayload.query === 'string'
      ? analyzeRequestPayload.query.trim()
      : '';
  const submittedAddressMatches = submittedQuery === selectedAddress;

  const has401DuringAnalyzeFlow = flowResponses.some((entry) => {
    if (entry.status !== 401) return false;
    return entry.url.includes('/analyze') || entry.url.includes('/auth/me');
  });

  const responseTextForGuards = JSON.stringify(analyzeResponseBody || {}).toLowerCase();
  const sessionExpiredSignals = [
    'session_expired',
    'no_session',
    'idle-fallback',
    'idle_fallback',
    'auth_required',
    'unauthorized',
  ].filter((token) => responseTextForGuards.includes(token));

  const phaseStateNormalized = String(phaseState || '').trim().toLowerCase();
  const phaseTextNormalized = String(phaseText || '').trim().toLowerCase();
  const terminalUiSignalReason = terminalUiSignal && terminalUiSignal.reason ? String(terminalUiSignal.reason) : '';

  const noIdleFallback = resultRowCount > 0 && phaseStateNormalized !== 'idle' && !phaseTextNormalized.includes('idle');

  const checks = {
    loginRedirectToIdP: isIdpLoginUrl(idpLoginUrl),
    loginReturnedToGui: Boolean(finalUrl) && finalUrl.startsWith(`${baseOrigin}${guiPath}`),
    authMeAuthenticated,
    selectedAddressIsSwiss: selectedAddress.includes(',') && /\b\d{4}\b/.test(selectedAddress),
    addressSubmittedExactly: submittedAddressMatches,
    analyzeHttpOk: analyzeResponseStatus === 200,
    analyzePayloadOkFlag: Boolean(analyzeResponseBody && analyzeResponseBody.ok === true),
    analyzePayloadComplete: analyzeCompleteness.complete,
    terminalUiSignalObserved: Boolean(terminalUiSignalReason),
    phaseSuccessOrResultsReady: phaseStateNormalized === 'success' || resultRowCount > 0,
    resultsRendered: resultRowCount > 0,
    noErrorBox: !errorBoxText,
    no401AnalyzeFlow: !has401DuringAnalyzeFlow,
    noSessionExpiredSignals: sessionExpiredSignals.length === 0,
    noIdleFallback,
  };

  const ok = Object.values(checks).every((value) => value === true);

  const payload = {
    startedAtUtc,
    finishedAtUtc: new Date().toISOString(),
    target: {
      baseOrigin,
      guiPath,
      loginStartUrl,
    },
    runtime: {
      browser: 'playwright-chromium',
      headless,
      timeoutMs,
      runMarker,
    },
    credentials: {
      usernameMasked: maskUsername(username),
    },
    addressSelection: {
      file: path.relative(repoRoot, addressFile),
      poolSize: addressPool.length,
      index: addressIndex,
      selectedAddress,
      runMarker,
    },
    login: {
      idpLoginUrl,
      finalUrl,
      authMeStatus,
      authMeAuthenticated,
      authMeBody,
    },
    analyze: {
      requestUrl: analyzeResponseUrl,
      responseStatus: analyzeResponseStatus,
      requestQuery: submittedQuery,
      requestPayload: analyzeRequestPayload,
      responsePayload: analyzeResponseBody,
      completeness: analyzeCompleteness,
    },
    uiState: {
      phaseText,
      phaseState,
      resultsMetaText,
      errorBoxText,
      resultRowCount,
      terminalUiSignal,
      terminalUiSignalTimeout,
    },
    flowResponses,
    guardSignals: {
      sessionExpiredSignals,
    },
    checks,
    artifacts: {
      screenshot: screenshotRelPath,
    },
    ok,
  };

  await writeEvidence(payload);
  return ok;
}

run()
  .then((ok) => {
    if (!ok) {
      process.exit(1);
    }
  })
  .catch(async (error) => {
    const payload = {
      startedAtUtc: new Date().toISOString(),
      finishedAtUtc: new Date().toISOString(),
      target: {
        baseOrigin,
        guiPath,
        loginStartUrl,
      },
      runtime: {
        browser: 'playwright-chromium',
        headless,
        timeoutMs,
        runMarker,
      },
      credentials: {
        usernameMasked: maskUsername(username),
      },
      error: normalizeError(error),
      ok: false,
    };

    await writeEvidence(payload);
    process.exit(1);
  });
