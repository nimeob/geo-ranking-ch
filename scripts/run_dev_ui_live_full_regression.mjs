#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const UI_BASE_URL = (process.env.DEV_UI_BASE_URL || "").trim();
const USERNAME = (process.env.DEV_UI_SMOKE_USERNAME || "").trim();
const PASSWORD = (process.env.DEV_UI_SMOKE_PASSWORD || "").trim();
const MAX_WAIT_MS = Number(process.env.DEV_UI_FULL_MAX_WAIT_MS || 120_000);
const LOGOUT_SETTLE_MS = Number(process.env.DEV_UI_FULL_LOGOUT_SETTLE_MS || 10_000);
const EVIDENCE_JSON = (process.env.DEV_UI_FULL_EVIDENCE_JSON || "artifacts/dev-ui-full/latest/dev-ui-full-regression.json").trim();
const SCREENSHOT_DIR = (process.env.DEV_UI_FULL_SCREENSHOT_DIR || "artifacts/dev-ui-full/latest/screenshots").trim();

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

if (!UI_BASE_URL) fail("Missing DEV_UI_BASE_URL");
if (!USERNAME) fail("Missing DEV_UI_SMOKE_USERNAME");
if (!PASSWORD) fail("Missing DEV_UI_SMOKE_PASSWORD");

const base = new URL(UI_BASE_URL);
const baseOrigin = base.origin;
const guiPath = base.pathname.endsWith("/") ? `${base.pathname}gui` : `${base.pathname}/gui`;
const guiUrl = new URL(guiPath, baseOrigin).toString();
const loginStart = new URL(`/login?next=${encodeURIComponent(guiPath)}&reason=dev_ui_full_regression&start=1`, baseOrigin).toString();

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
  return path.join(SCREENSHOT_DIR, `${new Date().toISOString().replace(/[:.]/g, "-")}-${label}.png`);
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

function isBlockingJobsConsoleError(message) {
  const text = String(message || "").toLowerCase();
  if (!text) return false;
  const touchesJobs = text.includes("/analyze/jobs") || text.includes("analyze/jobs");
  const isCors = text.includes("cors") || text.includes("access-control-allow-origin");
  const isNetworkFail = text.includes("net::err_failed") || text.includes("failed to load resource");
  return touchesJobs && (isCors || isNetworkFail);
}

async function main() {
  const startedAt = new Date().toISOString();
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
  });
  const page = await context.newPage();

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
      if (!url.origin.endsWith(base.hostname)) return;
      if (!url.pathname.startsWith("/analyze") && !url.pathname.startsWith("/auth") && !url.pathname.startsWith("/debug/trace")) return;
      let bodySnippet = "";
      if (response.status() >= 500) {
        bodySnippet = String(await response.text().catch(() => "")).slice(0, 800);
      }
      networkLog.push({
        ts: new Date().toISOString(),
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

  let finalError = null;
  let currentJobId = "";
  let firstResultId = "";
  let firstAddress = "";

  try {
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

    const preServerErrorVisible = await page.locator("#server-error-view").isVisible().catch(() => false);
    recordCheck("no_immediate_5xx_banner_after_login", !preServerErrorVisible, "server-error-view visible right after login");

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
    recordCheck("stale_local_state_does_not_trigger_5xx_banner", !serverErrorAfterReload, "5xx banner became visible after reload");

    const queryInput = page.locator("#query");
    const modeSelect = page.locator("#intelligence-mode");
    const asyncToggle = page.locator("#async-mode-requested");
    const submitBtn = page.locator("#submit-btn");
    const mapZoomIn = page.locator("#map-zoom-in");
    const mapZoomOut = page.locator("#map-zoom-out");
    const mapLocate = page.locator("#map-locate-btn");
    const filtersToggle = page.locator("#results-filters-toggle");

    recordCheck("main_controls_visible", await queryInput.isVisible() && await modeSelect.isVisible() && await submitBtn.isVisible(), "query/mode/submit missing");

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
    recordCheck("no_5xx_banner_after_successful_sync_analyze", !serverErrorAfterAnalyze, "server-error-view visible after 200 response");
    recordCheck("no_generic_error_after_successful_sync_analyze", !errorBoxAfterAnalyze, "error-box visible after 200 response");

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

    const immediate5xx = networkLog.filter((entry) => entry.status >= 500 && entry.path.startsWith("/analyze")).slice(0, 5);
    recordCheck("no_immediate_analyze_5xx_during_boot", immediate5xx.length === 0, JSON.stringify(immediate5xx));
  } catch (error) {
    finalError = String(error?.message || error);
    try {
      await safeScreenshot(page, "error");
    } catch {
      // ignore
    }
  } finally {
    await context.close();
    await browser.close();
  }

  const finishedAt = new Date().toISOString();
  const summary = {
    ok: !finalError,
    startedAt,
    finishedAt,
    baseUrl: UI_BASE_URL,
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
    error: finalError,
  };

  mkDirFor(EVIDENCE_JSON);
  fs.writeFileSync(EVIDENCE_JSON, `${JSON.stringify(summary, null, 2)}\n`, "utf8");

  if (finalError) {
    console.error(`[dev-ui-full-regression] FAILED: ${finalError}`);
    console.error(`[dev-ui-full-regression] Evidence: ${EVIDENCE_JSON}`);
    process.exit(1);
  }

  console.log(`[dev-ui-full-regression] PASSED with ${checks.length} checks`);
  console.log(`[dev-ui-full-regression] Evidence: ${EVIDENCE_JSON}`);
}

await main();
