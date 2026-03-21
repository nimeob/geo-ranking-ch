#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const UI_BASE_URL = (process.env.DEV_UI_BASE_URL || "").trim();
const USERNAME = (process.env.DEV_UI_SMOKE_USERNAME || "").trim();
const PASSWORD = (process.env.DEV_UI_SMOKE_PASSWORD || "").trim();
const MAX_WAIT_MS = Number(process.env.DEV_UI_FULL_MAX_WAIT_MS || 120_000);
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

async function fetchAuthMe(apiRequestContext) {
  try {
    const response = await apiRequestContext.get(new URL("/auth/me", baseOrigin).toString(), {
      timeout: MAX_WAIT_MS,
      headers: { Accept: "application/json" },
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    return {
      ok: response.ok(),
      status: response.status(),
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

    const authMeInitial = await fetchAuthMe(context.request);
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
    await page.waitForFunction(() => {
      const el = document.getElementById("status");
      return el && /Status:\s*(loaded|success|ok)/i.test(String(el.textContent || ""));
    }, undefined, { timeout: MAX_WAIT_MS });

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
    const jobStatusText = await page.locator("#status").innerText();
    recordCheck("job_page_loaded", /Status:/i.test(jobStatusText), jobStatusText);

    const rawNotificationsHref = await page.locator("#raw-notifications-link").getAttribute("href");
    recordCheck("job_notifications_link_present", Boolean(rawNotificationsHref && rawNotificationsHref.includes("/notifications")), rawNotificationsHref || "");

    await page.goto(new URL("/jobs", baseOrigin).toString(), { waitUntil: "domcontentloaded", timeout: MAX_WAIT_MS });
    await page.waitForSelector("#jobs-refresh", { timeout: MAX_WAIT_MS });
    await page.fill("#jobs-add-id", currentJobId);
    await page.click("#jobs-add-btn");
    await page.click("#jobs-refresh");
    await page.waitForSelector("#jobs-body tr", { timeout: MAX_WAIT_MS });
    const jobsMeta = await page.locator("#jobs-meta").innerText();
    recordCheck("jobs_list_refresh_ok", /angezeigt|Loading|jobs/i.test(jobsMeta), jobsMeta);

    await page.goto(guiUrl, { waitUntil: "domcontentloaded", timeout: MAX_WAIT_MS });
    await page.waitForSelector("#burger-btn", { timeout: MAX_WAIT_MS });
    await page.click("#burger-btn");
    await Promise.all([
      page.waitForURL((url) => url.pathname.startsWith("/auth/") || url.pathname.startsWith("/login") || url.pathname.startsWith(guiPath), { timeout: MAX_WAIT_MS }),
      page.click("#burger-logout-link"),
    ]);

    // allow redirects to settle
    await page.waitForTimeout(1_500);
    const authAfterLogout = await fetchAuthMe(context.request);
    recordCheck("auth.me_after_logout_401", authAfterLogout.status === 401, JSON.stringify(authAfterLogout));

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
