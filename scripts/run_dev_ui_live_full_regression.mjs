#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const SCRIPT_DIR = path.dirname(SCRIPT_PATH);
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..");
const LOGIN_START_FALLBACK_SCRIPT = path.join(REPO_ROOT, "scripts", "smoke", "run_login_start_smoke_bundle.sh");

const LEGACY_DEV_UI_HOSTS = new Set(["dev.georanking.ch", "dev.geo-ranking.ch"]);

function parseCliArgs(argv) {
  const options = {
    baseUrl: "",
    username: "",
    password: "",
    maxWaitMs: "",
    logoutSettleMs: "",
    sampleCount: "",
    sampleIntervalMs: "",
    evidenceJson: "",
    screenshotDir: "",
    headless: null,
    forceLoginStartFallback: false,
    helpRequested: false,
  };

  const consumeValue = (currentFlag, inlineValue, args, index) => {
    if (inlineValue !== null) return inlineValue;
    const next = args[index + 1];
    if (typeof next !== "string" || next.startsWith("--")) {
      throw new Error(`Missing value for ${currentFlag}`);
    }
    return next;
  };

  for (let i = 0; i < argv.length; i += 1) {
    const raw = String(argv[i] || "").trim();
    if (!raw) continue;

    if (raw === "-h" || raw === "--help") {
      options.helpRequested = true;
      continue;
    }

    const eqIdx = raw.indexOf("=");
    const flag = eqIdx >= 0 ? raw.slice(0, eqIdx) : raw;
    const inlineValue = eqIdx >= 0 ? raw.slice(eqIdx + 1) : null;

    switch (flag) {
      case "--base-url":
        options.baseUrl = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--username":
        options.username = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--password":
        options.password = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--max-wait-ms":
        options.maxWaitMs = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--logout-settle-ms":
        options.logoutSettleMs = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--pre-login-5xx-sample-count":
        options.sampleCount = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--pre-login-5xx-sample-interval-ms":
        options.sampleIntervalMs = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--evidence-json":
      case "--summary-json":
      case "--json-out":
      case "--out":
        options.evidenceJson = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--screenshot-dir":
        options.screenshotDir = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--headless":
        options.headless = true;
        break;
      case "--headful":
        options.headless = false;
        break;
      case "--fallback-login-start-on-missing-creds":
      case "--fallback-login-start":
        options.forceLoginStartFallback = true;
        break;
      default:
        throw new Error(`Unknown option: ${flag}`);
    }
  }

  return options;
}

function printHelp() {
  const lines = [
    "Usage: node scripts/run_dev_ui_live_full_regression.mjs [options]",
    "",
    "Required params (env var oder CLI):",
    "  DEV_UI_BASE_URL",
    "  DEV_UI_SMOKE_USERNAME",
    "  DEV_UI_SMOKE_PASSWORD",
    "",
    "CLI options:",
    "  --base-url <url>                         DEV_UI_BASE_URL override",
    "  --username <value>                       DEV_UI_SMOKE_USERNAME override",
    "  --password <value>                       DEV_UI_SMOKE_PASSWORD override",
    "  --max-wait-ms <ms>                       DEV_UI_FULL_MAX_WAIT_MS override (default: 120000)",
    "  --logout-settle-ms <ms>                  DEV_UI_FULL_LOGOUT_SETTLE_MS override (default: 10000)",
    "  --pre-login-5xx-sample-count <n>         DEV_UI_FULL_PRE_LOGIN_5XX_SAMPLE_COUNT override (default: 12)",
    "  --pre-login-5xx-sample-interval-ms <ms>  DEV_UI_FULL_PRE_LOGIN_5XX_SAMPLE_INTERVAL_MS override (default: 250)",
    "  --evidence-json <path>                   DEV_UI_FULL_EVIDENCE_JSON override",
    "  --summary-json <path>                    Alias für --evidence-json (legacy compatibility)",
    "  --json-out <path>                        Alias für --evidence-json (legacy compatibility)",
    "  --out <path>                             Alias für --evidence-json (legacy compatibility)",
    "  --screenshot-dir <path>                  DEV_UI_FULL_SCREENSHOT_DIR override",
    "  --headless                               Erzwingt headless Browser-Mode",
    "  --headful                                Erzwingt headful Browser-Mode",
    "  --fallback-login-start                   Degraded mode when credentials are unavailable",
    "  -h, --help                               Diese Hilfe anzeigen",
    "",
    "Optional env vars:",
    "  DEV_UI_FULL_MAX_WAIT_MS",
    "  DEV_UI_FULL_LOGOUT_SETTLE_MS",
    "  DEV_UI_FULL_PRE_LOGIN_5XX_SAMPLE_COUNT",
    "  DEV_UI_FULL_PRE_LOGIN_5XX_SAMPLE_INTERVAL_MS",
    "  DEV_UI_FULL_EVIDENCE_JSON",
    "  DEV_UI_FULL_SCREENSHOT_DIR",
    "  DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS=1    Optional degraded mode when credentials are unavailable",
    "  DEV_UI_FULL_HEADFUL",
  ];
  process.stdout.write(`${lines.join("\n")}\n`);
}

let cliOptions = null;
try {
  cliOptions = parseCliArgs(process.argv.slice(2));
} catch (error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  console.error(`[dev-ui-full-regression] ERROR ${message}`);
  printHelp();
  process.exit(2);
}

if (cliOptions.helpRequested) {
  printHelp();
  process.exit(0);
}

function parsePositiveInt(raw, fallback) {
  const value = Number.parseInt(String(raw || ""), 10);
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

function isTruthy(value) {
  const normalized = String(value || "").trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes" || normalized === "on";
}

function resolvePathAgainstRepoRoot(rawPath) {
  const value = String(rawPath || "").trim();
  if (!value) return "";
  if (path.isAbsolute(value)) {
    return path.normalize(value);
  }
  return path.resolve(REPO_ROOT, value);
}

const RAW_UI_BASE_URL = String(cliOptions.baseUrl || process.env.DEV_UI_BASE_URL || "").trim();
const UI_BASE_URL_NORMALIZATION = normalizeUiBaseUrl(RAW_UI_BASE_URL);
const UI_BASE_URL = UI_BASE_URL_NORMALIZATION.value;
const USERNAME = String(cliOptions.username || process.env.DEV_UI_SMOKE_USERNAME || "").trim();
const PASSWORD = String(cliOptions.password || process.env.DEV_UI_SMOKE_PASSWORD || "").trim();
const MAX_WAIT_MS = parsePositiveInt(cliOptions.maxWaitMs || process.env.DEV_UI_FULL_MAX_WAIT_MS, 120_000);
const LOGOUT_SETTLE_MS = parsePositiveInt(cliOptions.logoutSettleMs || process.env.DEV_UI_FULL_LOGOUT_SETTLE_MS, 10_000);
const PRE_LOGIN_5XX_SAMPLE_COUNT = parsePositiveInt(
  cliOptions.sampleCount || process.env.DEV_UI_FULL_PRE_LOGIN_5XX_SAMPLE_COUNT,
  12,
);
const PRE_LOGIN_5XX_SAMPLE_INTERVAL_MS = parsePositiveInt(
  cliOptions.sampleIntervalMs || process.env.DEV_UI_FULL_PRE_LOGIN_5XX_SAMPLE_INTERVAL_MS,
  250,
);
const EVIDENCE_JSON = String(
  cliOptions.evidenceJson
  || process.env.DEV_UI_FULL_EVIDENCE_JSON
  || "artifacts/dev-ui-full/latest/dev-ui-full-regression.json",
).trim();
const SCREENSHOT_DIR = String(
  cliOptions.screenshotDir
  || process.env.DEV_UI_FULL_SCREENSHOT_DIR
  || "artifacts/dev-ui-full/latest/screenshots",
).trim();
const EVIDENCE_JSON_PATH = resolvePathAgainstRepoRoot(EVIDENCE_JSON);
const SCREENSHOT_DIR_PATH = resolvePathAgainstRepoRoot(SCREENSHOT_DIR);
const HEADLESS = typeof cliOptions.headless === "boolean" ? cliOptions.headless : !isTruthy(process.env.DEV_UI_FULL_HEADFUL);
const LOGIN_START_FALLBACK_ON_MISSING_CREDS = cliOptions.forceLoginStartFallback || isTruthy(
  process.env.DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS
);

const ADDRESS_POOL = [
  "Bahnhofstrasse 1, 8001 Zürich",
  "Marktgasse 1, 9000 St. Gallen",
  "Rue du Rhône 8, 1204 Genève",
  "Bundesplatz 3, 3005 Bern",
  "Via Nassa 5, 6900 Lugano",
];

function fail(message) {
  throw new Error(message);
}

function normalizeUiBaseUrl(rawBaseUrl) {
  const candidate = String(rawBaseUrl || "").trim();
  if (!candidate) {
    return {
      value: "",
      requested: "",
      changed: false,
      reasons: [],
      error: "",
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
      error: "must be an absolute URL (e.g. https://www.dev.georanking.ch)",
    };
  }

  const protocol = String(parsed.protocol || "").toLowerCase();
  if (protocol !== "http:" && protocol !== "https:") {
    return {
      value: candidate,
      requested: candidate,
      changed: false,
      reasons: [],
      error: `unsupported protocol '${protocol || "(missing)"}' (expected http: or https:)`,
    };
  }

  const reasons = [];
  let canonicalHost = String(parsed.hostname || "").trim().toLowerCase();
  if (!canonicalHost) {
    return {
      value: candidate,
      requested: candidate,
      changed: false,
      reasons: [],
      error: "hostname is missing",
    };
  }

  const strippedTrailingDotHost = canonicalHost.replace(/\.+$/, "");
  if (strippedTrailingDotHost !== canonicalHost) {
    canonicalHost = strippedTrailingDotHost;
    reasons.push("trailing_dot");
  }

  if (LEGACY_DEV_UI_HOSTS.has(canonicalHost)) {
    canonicalHost = `www.${canonicalHost}`;
    reasons.push("legacy_dev_non_www");
  }

  parsed.hostname = canonicalHost;
  const normalizedPath = parsed.pathname === "/" ? "" : parsed.pathname;
  const normalized = `${parsed.protocol}//${parsed.host}${normalizedPath}${parsed.search}${parsed.hash}`;

  return {
    value: normalized,
    requested: candidate,
    changed: normalized !== candidate,
    reasons,
    error: "",
  };
}

function inferFallbackEnvName(baseUrl) {
  const normalized = String(baseUrl || "").toLowerCase();
  if (normalized.includes("staging")) {
    return "staging";
  }
  return "dev";
}

function buildLoginStartFallbackCommand(baseUrl) {
  const normalizedBaseUrl = String(baseUrl || "").trim();
  if (!normalizedBaseUrl) {
    return "";
  }

  const envName = inferFallbackEnvName(normalizedBaseUrl);
  return `${LOGIN_START_FALLBACK_SCRIPT} --base-url ${normalizedBaseUrl} --env-name ${envName}`;
}

function tailLines(text, maxLines = 12, maxChars = 8000) {
  const normalized = String(text || "");
  if (!normalized) return "";
  const lines = normalized.split(/\r?\n/).filter((line) => line.length > 0);
  const tail = lines.length <= maxLines ? lines.join("\n") : lines.slice(lines.length - maxLines).join("\n");
  if (tail.length <= maxChars) {
    return tail;
  }
  return tail.slice(tail.length - maxChars);
}

function runLoginStartFallbackBundle(baseUrl) {
  const normalizedBaseUrl = String(baseUrl || "").trim();
  const envName = inferFallbackEnvName(normalizedBaseUrl);
  const args = ["--base-url", normalizedBaseUrl, "--env-name", envName];

  const result = spawnSync(LOGIN_START_FALLBACK_SCRIPT, args, {
    encoding: "utf8",
    cwd: REPO_ROOT,
    env: process.env,
    maxBuffer: 4 * 1024 * 1024,
  });

  return {
    command: `${LOGIN_START_FALLBACK_SCRIPT} ${args.join(" ")}`,
    ok: result.status === 0 && !result.error,
    exitCode: Number.isFinite(result.status) ? result.status : -1,
    stdout: String(result.stdout || ""),
    stderr: String(result.stderr || ""),
    spawnError: result.error ? String(result.error?.message || result.error) : "",
  };
}

function normalizeError(error) {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack || "",
    };
  }

  return {
    name: "Error",
    message: String(error || "unknown error"),
    stack: "",
  };
}

async function loadChromium() {
  try {
    const playwrightModule = await import("playwright");
    const chromium = playwrightModule?.chromium;
    if (!chromium) {
      throw new Error("chromium export missing");
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

function validateRequiredEnv({ allowMissingCredentials = false } = {}) {
  if (!UI_BASE_URL) fail("Missing DEV_UI_BASE_URL");
  if (UI_BASE_URL_NORMALIZATION.error) fail(`Invalid DEV_UI_BASE_URL: ${UI_BASE_URL_NORMALIZATION.error}`);
  if (!allowMissingCredentials) {
    if (!USERNAME) fail("Missing DEV_UI_SMOKE_USERNAME");
    if (!PASSWORD) fail("Missing DEV_UI_SMOKE_PASSWORD");
  }
}

function emitFailureHints(finalError) {
  const errorText = String(finalError || "");
  if (!/^Missing DEV_UI_(BASE_URL|SMOKE_USERNAME|SMOKE_PASSWORD)$/.test(errorText)
    && !errorText.startsWith("Invalid DEV_UI_BASE_URL:")) {
    return;
  }

  if (errorText === "Missing DEV_UI_BASE_URL" || errorText.startsWith("Invalid DEV_UI_BASE_URL:")) {
    console.error("[dev-ui-full-regression] HINT: Setze DEV_UI_BASE_URL (z. B. https://www.dev.georanking.ch) und starte erneut.");
    return;
  }

  const fallbackCommand = buildLoginStartFallbackCommand(UI_BASE_URL);
  if (!fallbackCommand) {
    console.error("[dev-ui-full-regression] HINT: Setze DEV_UI_BASE_URL und starte erneut.");
    return;
  }

  console.error("[dev-ui-full-regression] HINT: Falls Live-Credentials fehlen, nutze Login-Start-Smoke als Fallback:");
  console.error(`[dev-ui-full-regression] HINT: ${fallbackCommand}`);
}

let base = null;
let baseOrigin = "";
let guiPath = "";
let guiUrl = "";
let loginStart = "";

function initializeTargetUrls() {
  base = new URL(UI_BASE_URL);
  baseOrigin = base.origin;
  guiPath = base.pathname.endsWith("/") ? `${base.pathname}gui` : `${base.pathname}/gui`;
  guiUrl = new URL(guiPath, baseOrigin).toString();
  loginStart = new URL(`/login?next=${encodeURIComponent(guiPath)}&reason=dev_ui_full_regression&start=1`, baseOrigin).toString();
}

const checks = [];
const consoleErrors = [];
const pageErrors = [];
const networkLog = [];
const requestFailures = [];

function recordCheck(name, ok, detail = "") {
  checks.push({ name, ok: Boolean(ok), detail: String(detail || "") });
  if (!ok) {
    throw new Error(`CHECK FAILED: ${name} :: ${detail}`);
  }
}

function mkDirFor(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function screenshotName(label) {
  return path.join(SCREENSHOT_DIR_PATH, `${new Date().toISOString().replace(/[:.]/g, "-")}-${label}.png`);
}

async function safeScreenshot(page, label) {
  const shot = screenshotName(label);
  mkDirFor(shot);
  await page.screenshot({ path: shot, fullPage: true });
  return shot;
}

function pickAddress(exclude = "") {
  const choices = ADDRESS_POOL.filter((value) => value !== exclude);
  return choices[Math.floor(Math.random() * choices.length)] || ADDRESS_POOL[0];
}

function isIdpLoginUrl(urlValue) {
  try {
    const parsed = new URL(String(urlValue));
    const host = String(parsed.hostname || "").toLowerCase();
    const pathname = String(parsed.pathname || "").toLowerCase();
    if (!host.includes("auth.")) return false;
    return pathname === "/login" || pathname.endsWith("/login");
  } catch {
    return false;
  }
}

async function locateFirstVisible(page, selectors, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    for (const selector of selectors) {
      const locator = page.locator(selector).first();
      if (await locator.isVisible().catch(() => false)) {
        return locator;
      }
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`Visible selector not found. candidates=${selectors.join(",")}`);
}

async function sampleVisibilitySignal(page, selector, { samples, intervalMs }) {
  const totalSamples = Math.max(1, Number(samples) || 1);
  const waitIntervalMs = Math.max(50, Number(intervalMs) || 50);
  let visibleCount = 0;
  let currentVisibleStreak = 0;
  let maxVisibleStreak = 0;
  const sampleTimeline = [];

  for (let index = 0; index < totalSamples; index += 1) {
    const visible = await page.locator(selector).isVisible().catch(() => false);
    sampleTimeline.push(visible ? 1 : 0);
    if (visible) {
      visibleCount += 1;
      currentVisibleStreak += 1;
      if (currentVisibleStreak > maxVisibleStreak) {
        maxVisibleStreak = currentVisibleStreak;
      }
    } else {
      currentVisibleStreak = 0;
    }

    if (index < totalSamples - 1) {
      await page.waitForTimeout(waitIntervalMs);
    }
  }

  return {
    selector,
    totalSamples,
    intervalMs: waitIntervalMs,
    visibleCount,
    maxVisibleStreak,
    everVisible: visibleCount > 0,
    timeline: sampleTimeline,
  };
}

async function fetchAuthMe(page) {
  return await page.evaluate(async ({ targetUrl }) => {
    try {
      const response = await fetch(targetUrl, {
        method: "GET",
        credentials: "include",
        headers: { "Accept": "application/json" },
      });
      let payload = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      return {
        ok: response.ok,
        status: response.status,
        payload,
      };
    } catch (error) {
      return {
        ok: false,
        status: 0,
        payload: null,
        error: String(error?.message || error),
      };
    }
  }, { targetUrl: new URL("/auth/me", baseOrigin).toString() });
}

async function waitForLoggedOutState(page, timeoutMs) {
  const deadline = Date.now() + Math.max(0, Number(timeoutMs) || 0);
  const observations = [];

  while (Date.now() <= deadline) {
    const logoutUrl = page.url();
    const redirectedToIdpLogin = isIdpLoginUrl(logoutUrl);
    if (redirectedToIdpLogin) {
      return {
        ok: true,
        reason: "idp_login_redirect",
        logoutUrl,
        redirectedToIdpLogin,
        authAfterLogout: null,
        observations,
      };
    }

    const authAfterLogout = await fetchAuthMe(page);
    observations.push({
      ts: new Date().toISOString(),
      logoutUrl,
      authStatus: authAfterLogout?.status ?? null,
      authOk: Boolean(authAfterLogout?.ok),
    });

    if (authAfterLogout?.status === 401) {
      return {
        ok: true,
        reason: "auth_me_401",
        logoutUrl,
        redirectedToIdpLogin,
        authAfterLogout,
        observations,
      };
    }

    await page.waitForTimeout(500);
  }

  const logoutUrl = page.url();
  const redirectedToIdpLogin = isIdpLoginUrl(logoutUrl);
  const authAfterLogout = redirectedToIdpLogin ? null : await fetchAuthMe(page);
  return {
    ok: Boolean(redirectedToIdpLogin || authAfterLogout?.status === 401),
    reason: "timeout",
    logoutUrl,
    redirectedToIdpLogin,
    authAfterLogout,
    observations,
  };
}

function deriveRemainingSeconds(payload) {
  if (!payload || typeof payload !== "object") return null;
  const direct = Number(payload.session_expires_in_seconds);
  if (Number.isFinite(direct) && direct >= 0) return direct;
  const rawExpiry = payload.session_expires_at;
  const expiryMs = Date.parse(String(rawExpiry || ""));
  if (!Number.isFinite(expiryMs)) return null;
  return Math.max(0, Math.floor((expiryMs - Date.now()) / 1000));
}

function hasSyncResponseShape(payload) {
  return Boolean(
    payload
      && payload.ok === true
      && payload.result
      && typeof payload.result === "object"
      && payload.result.data
      && typeof payload.result.data === "object"
      && payload.result.data.modules
      && typeof payload.result.data.modules === "object"
      && payload.result.status
      && typeof payload.result.status === "object"
  );
}

function hasAsyncResponseShape(payload) {
  return Boolean(
    payload
      && payload.ok === true
      && payload.accepted === true
      && payload.job
      && typeof payload.job === "object"
      && typeof payload.job.job_id === "string"
      && payload.job.job_id.trim().length > 0
      && typeof payload.job.status === "string"
      && payload.job.status.trim().length > 0
  );
}

async function waitForActiveResultTab(page, tabKey, timeoutMs) {
  await page.waitForFunction((targetTab) => {
    const btn = document.querySelector(`.tab-btn[data-tab="${targetTab}"]`);
    const panel = document.getElementById(`tab-${targetTab}`);
    if (!btn || !panel) return false;
    return String(btn.getAttribute("aria-selected") || "") === "true" && panel.hidden === false;
  }, tabKey, { timeout: timeoutMs });
}

function isBlockingJobsConsoleError(message) {
  const text = String(message || "").toLowerCase();
  if (!text) return false;
  const touchesJobs = text.includes("/analyze/jobs") || text.includes("analyze/jobs");
  const isCors = text.includes("cors") || text.includes("access-control-allow-origin");
  const isNetworkFail = text.includes("net::err_failed") || text.includes("failed to load resource");
  return touchesJobs && (isCors || isNetworkFail);
}

function normalizeHostname(value) {
  return String(value || "").trim().toLowerCase().replace(/\.+$/, "");
}

function isSameHostname(urlObj, expectedHostname) {
  if (!urlObj || typeof urlObj.hostname !== "string") {
    return false;
  }
  return normalizeHostname(urlObj.hostname) === normalizeHostname(expectedHostname);
}

async function main() {
  const startedAt = new Date().toISOString();
  let browser = null;
  let context = null;
  let page = null;

  let finalError = null;
  let currentJobId = "";
  let firstResultId = "";
  let firstAddress = "";
  let postLoginBootWindowStartedAtEpochMs = 0;
  let firstSyncAnalyzeSubmitAtEpochMs = 0;
  let degradedMode = null;

  try {
    if (UI_BASE_URL_NORMALIZATION.changed && UI_BASE_URL_NORMALIZATION.reasons.length > 0) {
      console.error(
        `[dev-ui-full-regression] INFO: Canonicalized DEV_UI_BASE_URL `
        + `'${UI_BASE_URL_NORMALIZATION.requested}' -> '${UI_BASE_URL}' `
        + `(reasons=${UI_BASE_URL_NORMALIZATION.reasons.join(",")}).`
      );
    }

    const missingCredentials = !USERNAME || !PASSWORD;
    const allowMissingCredentials = LOGIN_START_FALLBACK_ON_MISSING_CREDS && missingCredentials;
    validateRequiredEnv({ allowMissingCredentials });
    initializeTargetUrls();

    if (allowMissingCredentials) {
      const fallbackResult = runLoginStartFallbackBundle(UI_BASE_URL);
      degradedMode = {
        active: true,
        reason: "missing_live_credentials",
        envFlag: "DEV_UI_SMOKE_FALLBACK_LOGIN_START_ON_MISSING_CREDS",
        fallbackEnabled: true,
        fallbackCommand: fallbackResult.command,
        fallbackExitCode: fallbackResult.exitCode,
        fallbackSpawnError: fallbackResult.spawnError,
        fallbackStdoutTail: tailLines(fallbackResult.stdout),
        fallbackStderrTail: tailLines(fallbackResult.stderr),
      };

      recordCheck(
        "fallback.login_start_smoke_bundle_exit_0",
        fallbackResult.ok,
        `exit=${fallbackResult.exitCode} spawn_error=${fallbackResult.spawnError || "none"}`,
      );
    } else {
      const chromium = await loadChromium();

      browser = await chromium.launch({ headless: HEADLESS });
      context = await browser.newContext({
        viewport: { width: 390, height: 844 },
      });
      page = await context.newPage();

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });
    page.on("pageerror", (err) => {
      pageErrors.push(String(err?.message || err));
    });
    page.on("response", async (response) => {
      try {
        const url = new URL(response.url());
        if (!isSameHostname(url, base.hostname)) return;
        if (!url.pathname.startsWith("/analyze") && !url.pathname.startsWith("/auth") && !url.pathname.startsWith("/debug/trace")) return;
        let bodySnippet = "";
        if (response.status() >= 500) {
          bodySnippet = String(await response.text().catch(() => "")).slice(0, 800);
        }
        networkLog.push({
          ts: new Date().toISOString(),
          epochMs: Date.now(),
          status: response.status(),
          method: response.request().method(),
          path: `${url.pathname}${url.search}`,
          bodySnippet,
        });
      } catch {
        // ignore parse errors
      }
    });
    page.on("requestfailed", (request) => {
      try {
        const url = request.url();
        if (!url.includes("/analyze/jobs")) return;
        requestFailures.push({
          ts: new Date().toISOString(),
          url,
          method: request.method(),
          failureText: String(request.failure()?.errorText || ""),
        });
      } catch {
        // ignore parse errors
      }
    });

    const health = await context.request.get(new URL("/healthz", baseOrigin).toString(), { timeout: MAX_WAIT_MS });
    const healthJson = await health.json();
    recordCheck("healthz.status_200", health.status() === 200, `status=${health.status()}`);
    recordCheck("healthz.version_present", Boolean(healthJson?.version), `version=${healthJson?.version || ""}`);

    await page.goto(loginStart, { waitUntil: "domcontentloaded", timeout: MAX_WAIT_MS });
    await page.waitForURL((url) => isIdpLoginUrl(String(url)), { timeout: MAX_WAIT_MS });

    const usernameField = await locateFirstVisible(
      page,
      ['input[name="username"]', '#username', 'input[type="email"]', 'input[name="email"]'],
      MAX_WAIT_MS,
    );
    const passwordField = await locateFirstVisible(
      page,
      ['input[name="password"]', '#password', 'input[type="password"]'],
      MAX_WAIT_MS,
    );

    await usernameField.fill(USERNAME);
    await passwordField.fill(PASSWORD);

    const submitLogin = await locateFirstVisible(
      page,
      ['button[type="submit"]', 'input[type="submit"]', 'button[name="signInSubmitButton"]', 'input[name="signInSubmitButton"]'],
      MAX_WAIT_MS,
    );

    await Promise.all([
      page.waitForURL((url) => {
        try {
          const parsed = new URL(String(url));
          return parsed.origin === baseOrigin && parsed.pathname === guiPath;
        } catch {
          return false;
        }
      }, { timeout: MAX_WAIT_MS }),
      submitLogin.click(),
    ]);

    await page.waitForSelector("#analyze-form", { timeout: MAX_WAIT_MS });
    postLoginBootWindowStartedAtEpochMs = Date.now();
    await safeScreenshot(page, "01-after-login");

    const guiVersionText = await page.locator("header p").first().innerText();
    recordCheck(
      "ui.version_matches_healthz",
      String(guiVersionText || "").includes(String(healthJson.version || "")),
      `header=${guiVersionText}`,
    );

    const authMeInitial = await fetchAuthMe(page);
    recordCheck("auth.me_after_login_200", authMeInitial.status === 200 && authMeInitial.ok, JSON.stringify(authMeInitial));
    const remainingSec = deriveRemainingSeconds(authMeInitial.payload);
    const sessionWarningVisible = await page.locator("#session-expiry-warning").isVisible().catch(() => false);
    if (remainingSec != null && remainingSec > 120) {
      recordCheck("session_warning_hidden_when_remaining_gt_120s", !sessionWarningVisible, `remainingSec=${remainingSec}`);
    }

    const preServerErrorSignal = await sampleVisibilitySignal(page, "#server-error-view", {
      samples: PRE_LOGIN_5XX_SAMPLE_COUNT,
      intervalMs: PRE_LOGIN_5XX_SAMPLE_INTERVAL_MS,
    });
    const preServerErrorBlocking = preServerErrorSignal.maxVisibleStreak >= 3;
    recordCheck(
      "no_immediate_5xx_banner_after_login",
      !preServerErrorBlocking,
      JSON.stringify({
        maxVisibleStreak: preServerErrorSignal.maxVisibleStreak,
        visibleCount: preServerErrorSignal.visibleCount,
        totalSamples: preServerErrorSignal.totalSamples,
        intervalMs: preServerErrorSignal.intervalMs,
        timeline: preServerErrorSignal.timeline,
      }),
    );

    await page.evaluate(() => {
      try {
        window.localStorage.setItem("geo-ranking-ui-analyze-draft-v1", JSON.stringify({
          query: "stale-local-storage",
          mode: "risk",
          asyncModeRequested: true,
          ts: Date.now() - 86_400_000,
          reason: "stale_seed",
        }));
      } catch {
        // ignore
      }
    });
    await page.reload({ waitUntil: "domcontentloaded", timeout: MAX_WAIT_MS });
    await page.waitForSelector("#analyze-form", { timeout: MAX_WAIT_MS });
    const serverErrorAfterReload = await page.locator("#server-error-view").isVisible().catch(() => false);
    recordCheck(
      "stale_local_state_does_not_trigger_5xx_banner",
      !serverErrorAfterReload,
      `server_error_after_reload=${serverErrorAfterReload}`,
    );

    const queryInput = page.locator("#query");
    const modeSelect = page.locator("#intelligence-mode");
    const asyncToggle = page.locator("#async-mode-requested");
    const submitBtn = page.locator("#submit-btn");
    const mapZoomIn = page.locator("#map-zoom-in");
    const mapZoomOut = page.locator("#map-zoom-out");
    const mapLocate = page.locator("#map-locate-btn");
    const filtersToggle = page.locator("#results-filters-toggle");

    const queryVisible = await queryInput.isVisible();
    const modeVisible = await modeSelect.isVisible();
    const submitVisible = await submitBtn.isVisible();
    recordCheck(
      "main_controls_visible",
      queryVisible && modeVisible && submitVisible,
      `query_visible=${queryVisible} mode_visible=${modeVisible} submit_visible=${submitVisible}`,
    );

    await mapZoomIn.click();
    await mapZoomOut.click();
    await mapLocate.click();
    recordCheck("map_buttons_clickable", true, "zoom/locate clicked");

    if (await filtersToggle.isVisible().catch(() => false)) {
      await filtersToggle.click();
      await page.waitForSelector("#results-filters-panel:not([hidden])", { timeout: 10_000 });
      await page.selectOption("#results-sort", "distance_m");
      await page.selectOption("#results-dir", "asc");
      await page.selectOption("#results-ko", "on");
      await page.fill("#results-min-score", "25");
      await page.fill("#results-max-distance", "1200");
      await page.fill("#results-min-security", "10");
      await page.click("#results-apply");
      await page.click("#results-reset");
      await page.click("#results-clear");
      recordCheck("results_filters_toggles_and_buttons_work", true, "toggle/apply/reset/clear clicked");
    }

    firstAddress = pickAddress();
    await queryInput.fill(firstAddress);
    await modeSelect.selectOption("basic");
    await asyncToggle.setChecked(false);

    const syncResponsePromise = page.waitForResponse((resp) => {
      try {
        const url = new URL(resp.url());
        return url.origin === baseOrigin && url.pathname === "/analyze" && resp.request().method() === "POST";
      } catch {
        return false;
      }
    }, { timeout: MAX_WAIT_MS });

    firstSyncAnalyzeSubmitAtEpochMs = Date.now();
    await submitBtn.click();
    const syncResponse = await syncResponsePromise;
    const syncStatus = syncResponse.status();
    const syncPayload = await syncResponse.json().catch(() => null);
    recordCheck("analyze_sync_status_200", syncStatus === 200, `status=${syncStatus}`);
    recordCheck("analyze_sync_payload_ok", Boolean(syncPayload?.ok), JSON.stringify(syncPayload));
    recordCheck("analyze_sync_response_shape_valid", hasSyncResponseShape(syncPayload), JSON.stringify(syncPayload));

    await page.waitForFunction(() => {
      const el = document.getElementById("phase-pill");
      return el && /success/i.test(String(el.textContent || ""));
    }, undefined, { timeout: MAX_WAIT_MS });

    const serverErrorAfterAnalyze = await page.locator("#server-error-view").isVisible().catch(() => false);
    const errorBoxAfterAnalyze = await page.locator("#error-box").isVisible().catch(() => false);
    recordCheck(
      "no_5xx_banner_after_successful_sync_analyze",
      !serverErrorAfterAnalyze,
      `server_error_visible_after_analyze=${serverErrorAfterAnalyze}`,
    );
    recordCheck(
      "no_generic_error_after_successful_sync_analyze",
      !errorBoxAfterAnalyze,
      `error_box_visible_after_analyze=${errorBoxAfterAnalyze}`,
    );

    await page.waitForSelector('#history-shell a[href^="/results/"]', { timeout: MAX_WAIT_MS });
    const firstHistoryHref = await page.locator('#history-shell a[href^="/results/"]').first().getAttribute("href");
    recordCheck("history_contains_result_link", Boolean(firstHistoryHref), `href=${firstHistoryHref || ""}`);
    firstResultId = String(firstHistoryHref || "").replace(/^\/results\//, "").trim();

    await Promise.all([
      page.waitForURL((url) => url.pathname.startsWith("/results/"), { timeout: MAX_WAIT_MS }),
      page.locator('#history-shell a[href^="/results/"]').first().click(),
    ]);
    await page.waitForSelector("#load-btn", { timeout: MAX_WAIT_MS });
    await page.click("#load-btn");
    recordCheck("result_load_button_clickable", true, "clicked #load-btn");

    let resultLoadedAfterRetry = false;
    try {
      await page.waitForFunction(() => {
        const el = document.getElementById("status");
        return el && /Status:\s*(loaded|success|ok)/i.test(String(el.textContent || ""));
      }, undefined, { timeout: MAX_WAIT_MS });
    } catch {
      resultLoadedAfterRetry = true;
      await page.click("#load-btn").catch(() => {});
      await page.waitForFunction(() => {
        const el = document.getElementById("status");
        return el && /Status:\s*(loaded|success|ok)/i.test(String(el.textContent || ""));
      }, undefined, { timeout: MAX_WAIT_MS });
    }
    recordCheck("result_permalink_load_recovers_after_retry", true, `retried=${resultLoadedAfterRetry}`);

    await page.click('.tab-btn[data-tab="sources"]');
    await page.click('.tab-btn[data-tab="derived"]');
    await page.click('.tab-btn[data-tab="raw"]');
    await page.click('.tab-btn[data-tab="overview"]');
    recordCheck("result_tabs_clickable", true, "overview/sources/derived/raw clicked");

    const overviewTabButton = page.locator('.tab-btn[data-tab="overview"]').first();
    const locationTabButton = page.locator('.tab-btn[data-tab="location"]').first();
    const rawTabButton = page.locator('.tab-btn[data-tab="raw"]').first();
    await overviewTabButton.focus();
    await overviewTabButton.press("ArrowRight");
    await waitForActiveResultTab(page, "location", MAX_WAIT_MS);
    await locationTabButton.press("End");
    await waitForActiveResultTab(page, "raw", MAX_WAIT_MS);
    await rawTabButton.press("Home");
    await waitForActiveResultTab(page, "overview", MAX_WAIT_MS);
    recordCheck(
      "result_tabs_keyboard_navigation",
      true,
      "ArrowRight->location, End->raw, Home->overview"
    );

    await page.click("#burger-btn");
    const resultBurgerLinks = await page.locator('#burger-menu a[role="menuitem"]').allTextContents();
    recordCheck("result_page_navigation_links_present", resultBurgerLinks.length >= 2, resultBurgerLinks.join(" | "));

    await Promise.all([
      page.waitForURL((url) => url.pathname.startsWith(guiPath), { timeout: MAX_WAIT_MS }),
      page.locator('#burger-menu a[href="/gui"]').click(),
    ]);
    await page.waitForSelector("#analyze-form", { timeout: MAX_WAIT_MS });

    const asyncAddress = pickAddress(firstAddress);
    await queryInput.fill(asyncAddress);
    await modeSelect.selectOption("extended");
    await asyncToggle.setChecked(true);

    const asyncResponsePromise = page.waitForResponse((resp) => {
      try {
        const url = new URL(resp.url());
        return url.origin === baseOrigin && url.pathname === "/analyze" && resp.request().method() === "POST";
      } catch {
        return false;
      }
    }, { timeout: MAX_WAIT_MS });

    await submitBtn.click();
    const asyncResponse = await asyncResponsePromise;
    const asyncStatus = asyncResponse.status();
    const asyncPayload = await asyncResponse.json().catch(() => null);
    recordCheck("analyze_async_status_202", asyncStatus === 202, `status=${asyncStatus}`);
    recordCheck("analyze_async_response_shape_valid", hasAsyncResponseShape(asyncPayload), JSON.stringify(asyncPayload));
    currentJobId = String(asyncPayload?.job?.job_id || "").trim();
    recordCheck("analyze_async_returns_job_id", Boolean(currentJobId), JSON.stringify(asyncPayload));

    await page.waitForSelector("#async-job-box:not([hidden])", { timeout: MAX_WAIT_MS });
    await page.waitForSelector('#async-job-link[href^="/jobs/"]', { timeout: MAX_WAIT_MS });

    await Promise.all([
      page.waitForURL((url) => url.pathname === `/jobs/${currentJobId}`, { timeout: MAX_WAIT_MS }),
      page.click("#async-job-link"),
    ]);

    await page.waitForSelector("#refresh-btn", { timeout: MAX_WAIT_MS });
    await page.click("#refresh-btn");
    await page.waitForSelector("#notifications-payload", { timeout: MAX_WAIT_MS });
    await page.waitForFunction(() => {
      const text = String(document.getElementById("status")?.textContent || "");
      if (!/status:/i.test(text)) return false;
      if (/loading/i.test(text)) return false;
      return /(queued|running|partial|completed|failed|canceled|error)/i.test(text);
    }, undefined, { timeout: MAX_WAIT_MS });
    await page.waitForFunction(() => {
      const raw = String(document.getElementById("notifications-payload")?.textContent || "").trim();
      if (!raw || /loading/i.test(raw)) return false;
      try {
        const payload = JSON.parse(raw);
        return payload && payload.ok === true && Array.isArray(payload.notifications);
      } catch {
        return false;
      }
    }, undefined, { timeout: MAX_WAIT_MS });

    const jobStatusText = await page.locator("#status").innerText();
    recordCheck("job_page_status_not_stuck_loading", !/loading/i.test(jobStatusText) && /Status:/i.test(jobStatusText), jobStatusText);

    const jobSnapshot = await page.evaluate(() => {
      const statusText = String(document.getElementById("status")?.textContent || "");
      const rawJobHref = String(document.getElementById("raw-job-link")?.getAttribute("href") || "");
      const rawNotificationsHref = String(document.getElementById("raw-notifications-link")?.getAttribute("href") || "");

      function parsePre(id) {
        const text = String(document.getElementById(id)?.textContent || "").trim();
        if (!text) return null;
        try {
          return JSON.parse(text);
        } catch {
          return null;
        }
      }

      const jobPayload = parsePre("job-payload");
      const notificationsPayload = parsePre("notifications-payload");
      return { statusText, rawJobHref, rawNotificationsHref, jobPayload, notificationsPayload };
    });

    const currentJobPayloadId = String(jobSnapshot?.jobPayload?.job?.job_id || "").trim();
    recordCheck(
      "job_page_job_payload_shape_valid",
      Boolean(jobSnapshot?.jobPayload?.ok === true && currentJobPayloadId === currentJobId),
      JSON.stringify(jobSnapshot?.jobPayload || null),
    );
    const notificationsArray = jobSnapshot?.notificationsPayload?.notifications;
    recordCheck(
      "job_notifications_payload_shape_valid",
      Boolean(jobSnapshot?.notificationsPayload?.ok === true && Array.isArray(notificationsArray)),
      JSON.stringify(jobSnapshot?.notificationsPayload || null),
    );

    const rawNotificationsHref = String(jobSnapshot?.rawNotificationsHref || "");
    const rawJobHref = String(jobSnapshot?.rawJobHref || "");
    recordCheck(
      "job_links_same_origin_proxy",
      rawJobHref.startsWith("/analyze/jobs/") && rawNotificationsHref.startsWith("/analyze/jobs/") && rawNotificationsHref.includes("/notifications"),
      JSON.stringify({ rawJobHref, rawNotificationsHref }),
    );

    await page.goto(new URL("/jobs", baseOrigin).toString(), { waitUntil: "domcontentloaded", timeout: MAX_WAIT_MS });
    await page.waitForSelector("#jobs-refresh", { timeout: MAX_WAIT_MS });
    await page.fill("#jobs-add-id", currentJobId);
    await page.click("#jobs-add-btn");
    await page.click("#jobs-refresh");
    await page.waitForFunction((jobId) => {
      const meta = String(document.getElementById("jobs-meta")?.textContent || "");
      const bodyText = String(document.getElementById("jobs-body")?.textContent || "");
      if (/loading/i.test(meta)) return false;
      if (!bodyText.toLowerCase().includes(String(jobId || "").toLowerCase())) return false;
      return /angezeigt|jobs/i.test(meta);
    }, currentJobId, { timeout: MAX_WAIT_MS });
    await page.waitForSelector("#jobs-body tr", { timeout: MAX_WAIT_MS });
    const jobsMeta = await page.locator("#jobs-meta").innerText();
    recordCheck("jobs_list_refresh_ok", /angezeigt|jobs/i.test(jobsMeta) && !/loading/i.test(jobsMeta), jobsMeta);
    const jobsOpenHref = await page.locator(`#jobs-body a[href="/jobs/${encodeURIComponent(currentJobId)}"]`).first().getAttribute("href").catch(() => "");
    recordCheck("jobs_list_open_link_present", String(jobsOpenHref || "").startsWith(`/jobs/${encodeURIComponent(currentJobId)}`), jobsOpenHref || "");

    const blockingJobConsoleErrors = consoleErrors.filter((item) => isBlockingJobsConsoleError(item));
    recordCheck("no_jobs_cors_console_errors", blockingJobConsoleErrors.length === 0, JSON.stringify(blockingJobConsoleErrors.slice(0, 4)));
    const crossOriginJobFailures = requestFailures.filter((item) => String(item.url || "").includes("api.dev.georanking.ch"));
    recordCheck("no_cross_origin_job_request_failures", crossOriginJobFailures.length === 0, JSON.stringify(crossOriginJobFailures.slice(0, 4)));

    await page.goto(guiUrl, { waitUntil: "domcontentloaded", timeout: MAX_WAIT_MS });
    await page.waitForSelector("#burger-btn", { timeout: MAX_WAIT_MS });
    await page.click("#burger-btn");
    await Promise.all([
      page.waitForURL((url) => url.pathname.startsWith("/auth/") || url.pathname.startsWith("/login") || url.pathname.startsWith(guiPath), { timeout: MAX_WAIT_MS }),
      page.click("#burger-logout-link"),
    ]);

    const logoutState = await waitForLoggedOutState(page, LOGOUT_SETTLE_MS);
    recordCheck(
      "auth.me_after_logout_401",
      logoutState.ok,
      JSON.stringify(logoutState),
    );

    await safeScreenshot(page, "99-final-state");

    const immediate5xxWindowEnd = firstSyncAnalyzeSubmitAtEpochMs || Date.now();
    const immediate5xx = networkLog
      .filter((entry) => {
        if (entry.status < 500) return false;
        if (!entry.path.startsWith("/analyze")) return false;
        const atEpoch = Number(entry.epochMs || 0);
        if (!Number.isFinite(atEpoch) || atEpoch <= 0) return false;
        if (postLoginBootWindowStartedAtEpochMs > 0 && atEpoch < postLoginBootWindowStartedAtEpochMs) return false;
        if (immediate5xxWindowEnd > 0 && atEpoch > immediate5xxWindowEnd) return false;
        return true;
      })
      .slice(0, 5);
    recordCheck(
      "no_immediate_analyze_5xx_during_boot",
      immediate5xx.length === 0,
      JSON.stringify({
        postLoginBootWindowStartedAtEpochMs,
        firstSyncAnalyzeSubmitAtEpochMs,
        immediate5xx,
      }),
    );
    }
  } catch (error) {
    finalError = String(error?.message || error);
    if (page) {
      try {
        await safeScreenshot(page, "error");
      } catch {
        // ignore
      }
    }
  } finally {
    if (context) {
      await context.close().catch(() => {});
    }
    if (browser) {
      await browser.close().catch(() => {});
    }
  }

  const finishedAt = new Date().toISOString();
  const summary = {
    ok: !finalError,
    startedAt,
    finishedAt,
    baseUrl: UI_BASE_URL,
    requestedBaseUrl: RAW_UI_BASE_URL,
    baseUrlCanonicalized: UI_BASE_URL_NORMALIZATION.changed,
    baseUrlCanonicalizationReasons: UI_BASE_URL_NORMALIZATION.reasons,
    headless: HEADLESS,
    guiUrl,
    firstAddress,
    firstResultId,
    currentJobId,
    checks,
    failedChecks: checks.filter((item) => !item.ok),
    consoleErrors,
    pageErrors,
    networkLog,
    requestFailures,
    degradedMode,
    error: finalError,
  };

  mkDirFor(EVIDENCE_JSON_PATH);
  fs.writeFileSync(EVIDENCE_JSON_PATH, `${JSON.stringify(summary, null, 2)}\n`, "utf8");

  if (finalError) {
    console.error(`[dev-ui-full-regression] FAILED: ${finalError}`);
    console.error(`[dev-ui-full-regression] Evidence: ${EVIDENCE_JSON_PATH}`);
    emitFailureHints(finalError);
    process.exit(1);
  }

  if (degradedMode?.active) {
    console.log(`[dev-ui-full-regression] PASSED (degraded mode) with ${checks.length} checks`);
  } else {
    console.log(`[dev-ui-full-regression] PASSED with ${checks.length} checks`);
  }
  console.log(`[dev-ui-full-regression] Evidence: ${EVIDENCE_JSON_PATH}`);
}

await main();
