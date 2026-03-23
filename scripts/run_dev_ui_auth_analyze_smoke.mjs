#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';

const repoRoot = process.cwd();
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

const baseOrigin = String(process.env.BASE_URL || 'https://www.dev.georanking.ch').replace(/\/+$/, '');
const guiPath = normalizeGuiPath(process.env.DEV_UI_SMOKE_GUI_PATH || '/gui');
const expectedPostLoginPath = resolveCanonicalGuiSuccessor(guiPath);
const loginReason = String(process.env.DEV_UI_SMOKE_LOGIN_REASON || 'manual_login').trim() || 'manual_login';
const loginStartUrl = `${baseOrigin}/login?next=${encodeURIComponent(guiPath)}&reason=${encodeURIComponent(loginReason)}&start=1`;

const username = String(process.env.DEV_UI_SMOKE_USERNAME || '').trim();
const password = String(process.env.DEV_UI_SMOKE_PASSWORD || '');

const explicitRunMarker = String(process.env.DEV_UI_SMOKE_RUN_ID || '').trim();
const githubRunNumber = String(process.env.GITHUB_RUN_NUMBER || '').trim();
const githubRunAttempt = String(process.env.GITHUB_RUN_ATTEMPT || '').trim() || '1';
const githubRunId = String(process.env.GITHUB_RUN_ID || '').trim();
const runMarkerSource = explicitRunMarker
  ? 'DEV_UI_SMOKE_RUN_ID'
  : githubRunNumber
    ? 'GITHUB_RUN_NUMBER+GITHUB_RUN_ATTEMPT'
    : githubRunId
      ? 'GITHUB_RUN_ID+GITHUB_RUN_ATTEMPT'
      : 'timestamp';
const runMarker =
  explicitRunMarker
  || (githubRunNumber ? `${githubRunNumber}-${githubRunAttempt}` : '')
  || (githubRunId ? `${githubRunId}-${githubRunAttempt}` : '')
  || stamp;
const artifactRunToken = sanitizeFileToken(runMarker) || 'run';

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

function resolveCanonicalGuiSuccessor(pathname) {
  const value = normalizeGuiPath(pathname);
  if (value === '/gui/jobs') return '/jobs';
  if (value.startsWith('/gui/jobs/')) return `/jobs${value.slice('/gui/jobs'.length)}`;
  return value;
}

function sanitizeFileToken(value) {
  return String(value || '')
    .trim()
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}

function buildArtifactPath(extension) {
  return path.join(outDir, `dev-ui-auth-analyze-smoke-${stamp}-${artifactRunToken}.${extension}`);
}

async function loadChromium() {
  try {
    const playwrightModule = await import('playwright');
    const chromium = playwrightModule?.chromium;
    if (!chromium) {
      throw new Error('chromium export missing');
    }
    return chromium;
  } catch (error) {
    const normalized = normalizeError(error);
    throw new Error(
      `Playwright Chromium nicht verfügbar. Installiere die Node-Abhängigkeiten mit \`npm ci\` `
      + `und anschließend Browser-Binaries via \`npx playwright install --with-deps chromium\`. `
      + `Ursache: ${normalized.name}: ${normalized.message}`
    );
  }
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
  if (!Number.isFinite(poolSize) || poolSize <= 0) {
    return 0;
  }

  const normalized = String(marker || '').trim();
  const runTuple = normalized.match(/^(\d+)(?:\D+(\d+))?$/);
  if (runTuple) {
    const primary = Number.parseInt(runTuple[1], 10);
    const attempt = Number.parseInt(runTuple[2] || '1', 10);
    if (Number.isFinite(primary) && Number.isFinite(attempt) && attempt > 0) {
      return Math.abs((primary + attempt - 1) % poolSize);
    }
  }

  const numericChunks = normalized.match(/\d+/g);
  if (numericChunks && numericChunks.length) {
    let rolling = 0;
    for (const chunk of numericChunks) {
      const value = Number.parseInt(chunk, 10);
      if (!Number.isFinite(value)) continue;
      rolling = (rolling * 31 + Math.abs(value)) % poolSize;
    }
    return rolling;
  }

  const digest = crypto.createHash('sha256').update(normalized || stamp, 'utf8').digest('hex');
  const asInt = Number.parseInt(digest.slice(0, 12), 16);
  return Number.isFinite(asInt) ? asInt % poolSize : 0;
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
  }, undefined, { timeout });

  return handle.jsonValue();
}

async function waitForAnalyzeShellVisible(page, timeout) {
  await page.locator('#analyze-form').waitFor({ state: 'visible', timeout });
}

async function ensureAnalyzeShellReady(page, baseOrigin, timeout) {
  const quickProbeTimeout = Math.max(1_000, Math.min(8_000, Math.floor(timeout / 6)));

  try {
    await waitForAnalyzeShellVisible(page, quickProbeTimeout);
    return {
      recovered: false,
      strategy: 'already_visible',
      urlAfterRecovery: page.url(),
    };
  } catch {
    // continue with recovery path
  }

  const analyzeMenuLink = page.locator('a[role="menuitem"][href="/gui"]:visible').first();
  if (await analyzeMenuLink.count()) {
    await Promise.all([
      page.waitForURL(
        (url) => {
          try {
            const parsed = new URL(String(url));
            return parsed.origin === baseOrigin && parsed.pathname === '/gui';
          } catch {
            return false;
          }
        },
        { timeout }
      ),
      analyzeMenuLink.click(),
    ]);

    await waitForAnalyzeShellVisible(page, timeout);
    return {
      recovered: true,
      strategy: 'menuitem_to_gui',
      urlAfterRecovery: page.url(),
    };
  }

  await page.goto(`${baseOrigin}/gui`, { waitUntil: 'domcontentloaded' });
  await waitForAnalyzeShellVisible(page, timeout);
  return {
    recovered: true,
    strategy: 'direct_goto_gui',
    urlAfterRecovery: page.url(),
  };
}

function maskUsername(value) {
  if (!value) return '';
  if (value.length <= 2) return `${value[0] || '*'}*`;
  return `${value[0]}***${value[value.length - 1]}`;
}

async function writeEvidence(payload) {
  await fs.mkdir(outDir, { recursive: true });
  const outJson = buildArtifactPath('json');
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

  const chromium = await loadChromium();
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
  let postLoginUrl = '';
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
  let analyzeShellRecovery = null;
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
            return parsed.origin === baseOrigin && parsed.pathname === expectedPostLoginPath;
          } catch {
            return false;
          }
        },
        { timeout: timeoutMs }
      ),
      submitButton.click(),
    ]);

    postLoginUrl = page.url();
    analyzeShellRecovery = await ensureAnalyzeShellReady(page, baseOrigin, timeoutMs);

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
    const screenshotPath = buildArtifactPath('png');
    await page.screenshot({ path: screenshotPath, fullPage: true });
    screenshotRelPath = path.relative(repoRoot, screenshotPath);
  } finally {
    if (!screenshotRelPath) {
      try {
        await fs.mkdir(outDir, { recursive: true });
        const fallbackScreenshotPath = buildArtifactPath('png');
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

  const loginReturnedToRequestedGuiPath = Boolean(postLoginUrl)
    && postLoginUrl.startsWith(`${baseOrigin}${expectedPostLoginPath}`);

  const checks = {
    loginRedirectToIdP: isIdpLoginUrl(idpLoginUrl),
    loginReturnedToRequestedGuiPath,
    // Backward-compatibility alias for older dashboards/evidence readers.
    loginReturnedToGui: loginReturnedToRequestedGuiPath,
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
      expectedPostLoginPath,
      loginStartUrl,
    },
    runtime: {
      browser: 'playwright-chromium',
      headless,
      timeoutMs,
      runMarker,
      runMarkerSource,
      githubRunNumber,
      githubRunAttempt,
      githubRunId,
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
      runMarkerSource,
    },
    login: {
      idpLoginUrl,
      postLoginUrl,
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
      analyzeShellRecovery,
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
        expectedPostLoginPath,
        loginStartUrl,
      },
      runtime: {
        browser: 'playwright-chromium',
        headless,
        timeoutMs,
        runMarker,
        runMarkerSource,
        githubRunNumber,
        githubRunAttempt,
        githubRunId,
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
