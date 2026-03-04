#!/usr/bin/env python3
"""Service-neutrale HTML Pages (stdlib-only).

Diese Pages werden sowohl vom API-Service als auch vom UI-Service ausgeliefert.
Sie laden Daten API-first über JSON-Endpunkte.

- /history → GET /analyze/history
- /results/<result_id> → GET /analyze/results/<result_id>

Wichtig: Dieses Modul darf *keine* API/UI-spezifischen Module importieren.
"""

from __future__ import annotations

import json
import re
from html import escape

_RESULT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")


def normalize_result_id(raw_value: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        return ""
    if "/" in normalized:
        return ""
    if not _RESULT_ID_RE.match(normalized):
        return ""
    return normalized


def _results_endpoint_base(api_base_url: str) -> str:
    base = str(api_base_url or "").strip().rstrip("/")
    return f"{base}/analyze/results" if base else "/analyze/results"


def _history_endpoint(api_base_url: str) -> str:
    base = str(api_base_url or "").strip().rstrip("/")
    return f"{base}/analyze/history" if base else "/analyze/history"


def _auth_login_endpoint(api_base_url: str) -> str:
    base = str(api_base_url or "").strip().rstrip("/")
    return f"{base}/auth/login" if base else "/auth/login"


_BURGER_CSS = """
      .burger {
        position: relative;
        display: inline-flex;
        justify-content: flex-end;
      }
      #burger-btn {
        background: #fff;
        color: var(--ink);
        border: 1px solid var(--border);
        border-radius: 0.6rem;
        padding: 0.45rem 0.7rem;
        font-size: 0.9rem;
        line-height: 1.2;
        cursor: pointer;
      }
      #burger-btn:focus-visible {
        outline: 2px solid #bcd0ff;
        outline-offset: 1px;
      }
      .burger-menu {
        position: absolute;
        top: calc(100% + 0.45rem);
        right: 0;
        width: min(18rem, calc(100vw - 2rem));
        max-height: min(70vh, 24rem);
        overflow-y: auto;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.75rem;
        padding: 0.4rem;
        box-shadow: 0 12px 28px rgba(27, 38, 55, 0.12);
        display: grid;
        gap: 0.2rem;
        z-index: 30;
      }
      .burger-menu[hidden] {
        display: none !important;
      }
      .burger-menu a {
        text-decoration: none;
        color: var(--primary);
        padding: 0.55rem 0.65rem;
        border-radius: 0.55rem;
        font-size: 0.9rem;
      }
      .burger-menu a:hover,
      .burger-menu a:focus-visible {
        background: #f3f7ff;
        outline: none;
      }
      @media (max-width: 520px) {
        .burger-menu {
          right: auto;
          left: 0;
          width: min(18rem, calc(100vw - 2.5rem));
        }
      }
"""

_BURGER_JS = """
        const burgerBtn = document.getElementById("burger-btn");
        const burgerMenu = document.getElementById("burger-menu");
        const burgerItems = burgerMenu
          ? Array.from(burgerMenu.querySelectorAll('a[href]'))
          : [];

        function setBurgerOpen(nextOpen) {
          if (!burgerBtn || !burgerMenu) return;
          burgerMenu.hidden = !nextOpen;
          burgerBtn.setAttribute("aria-expanded", nextOpen ? "true" : "false");
        }

        function closeBurger(options = {}) {
          const returnFocus = Boolean(options.returnFocus);
          setBurgerOpen(false);
          if (returnFocus && burgerBtn) burgerBtn.focus();
        }

        function toggleBurger() {
          if (!burgerBtn) return;
          const isOpen = burgerBtn.getAttribute("aria-expanded") === "true";
          setBurgerOpen(!isOpen);
        }

        if (burgerBtn && burgerMenu) {
          setBurgerOpen(false);

          burgerBtn.addEventListener("click", () => {
            toggleBurger();
          });

          burgerBtn.addEventListener("keydown", (event) => {
            if (!event) return;
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setBurgerOpen(true);
              if (burgerItems[0]) burgerItems[0].focus();
            }
            if (event.key === "Escape") {
              event.preventDefault();
              closeBurger({ returnFocus: true });
            }
          });

          document.addEventListener(
            "pointerdown",
            (event) => {
              if (!event || !(event.target instanceof Node)) return;
              if (burgerBtn.contains(event.target) || burgerMenu.contains(event.target)) return;
              closeBurger();
            },
            true
          );

          window.addEventListener("keydown", (event) => {
            if (!event || event.key !== "Escape") return;
            if (burgerBtn.getAttribute("aria-expanded") !== "true") return;
            closeBurger({ returnFocus: true });
          });

          burgerMenu.querySelectorAll("a").forEach((link) => {
            link.addEventListener("click", () => closeBurger());
          });
        }
"""

_HISTORY_PAGE_TEMPLATE = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>geo-ranking.ch — Historische Abfragen</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f8fb;
        --surface: #ffffff;
        --ink: #1b2637;
        --muted: #5a6474;
        --border: #d5dbea;
        --primary: #1957d2;
        --danger: #b93a2f;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        background: var(--bg);
        color: var(--ink);
      }
      header {
        background: var(--surface);
        border-bottom: 1px solid var(--border);
        padding: 1rem 1.25rem;
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: baseline;
      }
      header h1 { margin: 0; font-size: 1.05rem; }
      header p { margin: 0; color: var(--muted); font-size: 0.9rem; }
      __BURGER_CSS__

      main {
        padding: 1rem 1.25rem 1.5rem;
        display: grid;
        gap: 1rem;
        max-width: 1100px;
      }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.85rem;
        padding: 1rem;
      }
      .card h2 { margin: 0 0 0.75rem; font-size: 1rem; }
      .meta { font-size: 0.84rem; color: var(--muted); }
      label {
        display: grid;
        gap: 0.3rem;
        font-size: 0.86rem;
        color: var(--muted);
      }
      input, select, button {
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 0.55rem 0.6rem;
        font: inherit;
      }
      button {
        background: var(--primary);
        color: #fff;
        border-color: var(--primary);
        cursor: pointer;
      }
      button.secondary {
        background: #fff;
        color: var(--ink);
        border-color: var(--border);
      }
      .error {
        border: 1px solid rgba(185, 58, 47, 0.35);
        background: rgba(185, 58, 47, 0.08);
        padding: 0.75rem;
        border-radius: 0.65rem;
        color: var(--danger);
        white-space: pre-wrap;
      }
      .grid-3 {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: 1fr 1fr 1fr;
      }
      @media (max-width: 860px) {
        .grid-3 { grid-template-columns: 1fr; }
      }
      .pill {
        display: inline-flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.6rem;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: #f9fbff;
        font-size: 0.86rem;
        padding: 0.35rem 0.75rem;
      }
      .pill strong { font-size: 0.9rem; }
      .pill a {
        text-decoration: none;
        color: var(--primary);
        border: 1px solid var(--border);
        padding: 0.28rem 0.55rem;
        border-radius: 0.55rem;
        background: #fff;
        font-size: 0.85rem;
      }
      .stack { display: grid; gap: 0.65rem; }
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>Historische Abfragen</h1>
        <p>Version __APP_VERSION__</p>
      </div>
      <div class="burger">
        <button id="burger-btn" type="button" aria-haspopup="true" aria-expanded="false" aria-controls="burger-menu" aria-label="Navigation umschalten">☰ Menü</button>
        <div id="burger-menu" class="burger-menu" role="menu" aria-label="Hauptnavigation" hidden>
          <a role="menuitem" href="/gui">Abfrage</a>
          <a role="menuitem" href="/history">Historische Abfragen</a>
        </div>
      </div>
    </header>

    <main>
      <section class="card">
        <h2>Loader</h2>
        <p class="meta">Lädt via <code>GET /analyze/history</code>. Auth läuft über Login/Session-Cookie; optional Tenant-Header via <code>X-Org-Id</code>.</p>
        <div class="grid-3">
          <label>
            X-Org-Id (Tenant)
            <input id="org-id" type="text" placeholder="default-org" />
          </label>
          <label>
            limit
            <select id="limit">
              <option value="25">25</option>
              <option value="50" selected>50</option>
              <option value="100">100</option>
              <option value="200">200</option>
            </select>
          </label>
        </div>
        <div style="display:flex; gap: 0.65rem; flex-wrap: wrap; margin-top: 0.85rem; align-items: center;">
          <button id="load-btn" type="button">Historie laden</button>
          <button id="clear-btn" class="secondary" type="button">Clear</button>
          <span id="status" class="meta">Status: idle</span>
        </div>
        <div id="error" class="error" hidden></div>
      </section>

      <section class="card">
        <h2>Liste</h2>
        <div id="history-list" class="stack"><div class="meta">Noch nicht geladen.</div></div>
      </section>

      <script>
        const ANALYZE_HISTORY_ENDPOINT = __ANALYZE_HISTORY_ENDPOINT_JSON__;
        const AUTH_LOGIN_ENDPOINT = __AUTH_LOGIN_ENDPOINT_JSON__;
        const ORG_STORAGE_KEY = "geo-ranking-ui-org-id";
        const SESSION_RECOVERY_ERROR_CODES = new Set([
          "no_session_cookie",
          "session_not_found",
          "no_access_token",
          "no_refresh_token",
          "refresh_grant_error",
          "refresh_http_error",
          "refresh_network_error",
          "refresh_invalid_response",
          "refresh_missing_token",
          "access_denied",
          "consent_denied",
          "token_error",
          "unauthorized",
        ]);
        const SESSION_REFRESH_ERROR_CODES = new Set([
          "no_refresh_token",
          "refresh_grant_error",
          "refresh_http_error",
          "refresh_network_error",
          "refresh_invalid_response",
          "refresh_missing_token",
        ]);
        const AUTH_RECOVERY_REASON_BY_ERROR_CODE = Object.freeze({
          no_session_cookie: "session_missing",
          session_not_found: "session_missing",
          no_access_token: "session_expired",
          token_error: "session_expired",
          unauthorized: "session_expired",
          no_refresh_token: "refresh_failed",
          refresh_grant_error: "refresh_failed",
          refresh_http_error: "refresh_failed",
          refresh_network_error: "refresh_failed",
          refresh_invalid_response: "refresh_failed",
          refresh_missing_token: "refresh_failed",
          access_denied: "consent_denied",
          consent_denied: "consent_denied",
        });
        const AUTH_RECOVERY_REASON_BY_STATUS = Object.freeze({
          "401": "session_expired",
          "403": "session_expired",
        });

        const orgEl = document.getElementById("org-id");
        const limitEl = document.getElementById("limit");
        const statusEl = document.getElementById("status");
        const loadBtn = document.getElementById("load-btn");
        const clearBtn = document.getElementById("clear-btn");
        const errorEl = document.getElementById("error");
        const listEl = document.getElementById("history-list");
        let authRecoveryRedirectScheduled = false;

        __BURGER_JS__

        function escapeHtml(text) {
          const raw = String(text == null ? "" : text);
          return raw
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#039;");
        }

        function formatLocalTime(isoText) {
          const normalized = String(isoText || "").trim();
          if (!normalized) return "";
          const date = new Date(normalized);
          if (Number.isNaN(date.getTime())) return normalized;
          return date.toLocaleString();
        }

        function setStatus(value) {
          statusEl.textContent = `Status: ${value}`;
        }

        function setError(message) {
          const text = String(message || "").trim();
          if (!text) {
            errorEl.hidden = true;
            errorEl.textContent = "";
            return;
          }
          errorEl.hidden = false;
          errorEl.textContent = text;
        }

        function normalizeErrorCode(errorCode) {
          return String(errorCode || "").trim().toLowerCase();
        }

        function resolveAuthRecoveryReason(statusCode, errorCode) {
          const normalizedCode = normalizeErrorCode(errorCode);
          if (normalizedCode && AUTH_RECOVERY_REASON_BY_ERROR_CODE[normalizedCode]) {
            return AUTH_RECOVERY_REASON_BY_ERROR_CODE[normalizedCode];
          }

          const normalizedStatus = Number(statusCode);
          if (Number.isFinite(normalizedStatus)) {
            const statusKey = String(Math.trunc(normalizedStatus));
            if (AUTH_RECOVERY_REASON_BY_STATUS[statusKey]) {
              return AUTH_RECOVERY_REASON_BY_STATUS[statusKey];
            }
          }

          return "session_recovery";
        }

        function isSessionRecoveryRequired(statusCode, errorCode) {
          const normalizedStatus = Number(statusCode);
          const normalizedCode = normalizeErrorCode(errorCode);
          if (normalizedStatus === 401 || normalizedStatus === 403) {
            return true;
          }
          return SESSION_RECOVERY_ERROR_CODES.has(normalizedCode);
        }

        function buildSessionErrorMessage(statusCode, errorCode, fallbackMessage) {
          const normalizedStatus = Number(statusCode);
          const normalizedCode = normalizeErrorCode(errorCode);
          if (normalizedCode === "access_denied" || normalizedCode === "consent_denied") {
            return "Anmeldung abgebrochen oder verweigert — bitte erneut einloggen.";
          }
          if (isSessionRecoveryRequired(normalizedStatus, normalizedCode)) {
            if (SESSION_REFRESH_ERROR_CODES.has(normalizedCode)) {
              return "Session konnte nicht erneuert werden — bitte erneut einloggen.";
            }
            return "Session ungültig oder abgelaufen — bitte erneut einloggen.";
          }
          if (normalizedStatus === 403) {
            return "Zugriff verweigert — bitte Berechtigungen/Session prüfen.";
          }
          return String(fallbackMessage || `http_${normalizedStatus || 0}`);
        }

        function resolveAuthFailure(statusCode, errorCode, fallbackMessage) {
          const normalizedCode = normalizeErrorCode(errorCode);
          return {
            errorCode: normalizedCode,
            errorMessage: buildSessionErrorMessage(statusCode, normalizedCode, fallbackMessage),
            requiresLoginRecovery: isSessionRecoveryRequired(statusCode, normalizedCode),
          };
        }

        function buildLoginRedirectUrl(authReason) {
          const normalizedReason = normalizeErrorCode(authReason) || "session_recovery";
          const nextPath = typeof window !== "undefined" && window.location
            ? `${window.location.pathname || "/history"}${window.location.search || ""}`
            : "/history";

          if (typeof URLSearchParams === "undefined") {
            return `${AUTH_LOGIN_ENDPOINT}?next=${encodeURIComponent(nextPath || "/history")}&reason=${encodeURIComponent(normalizedReason)}`;
          }

          const params = new URLSearchParams();
          params.set("next", nextPath || "/history");
          params.set("reason", normalizedReason);
          return `${AUTH_LOGIN_ENDPOINT}?${params.toString()}`;
        }

        function scheduleReLoginRedirect(statusCode, errorCode) {
          if (authRecoveryRedirectScheduled) {
            return;
          }
          authRecoveryRedirectScheduled = true;

          if (typeof window === "undefined" || !window.location || !window.setTimeout) {
            authRecoveryRedirectScheduled = false;
            return;
          }

          const authReason = resolveAuthRecoveryReason(statusCode, errorCode);
          const loginUrl = buildLoginRedirectUrl(authReason);
          setError("Session wird neu aufgebaut — Weiterleitung zum Login…");
          window.setTimeout(() => {
            window.location.assign(loginUrl);
          }, 250);
        }

        function persistInputs() {
          try {
            if (typeof window !== "undefined" && window.sessionStorage) {
              const orgId = String(orgEl.value || "").trim();
              if (orgId) window.sessionStorage.setItem(ORG_STORAGE_KEY, orgId);
              else window.sessionStorage.removeItem(ORG_STORAGE_KEY);
            }
          } catch (error) {
            // ignore
          }
        }

        function applyInitialState() {
          try {
            if (typeof window !== "undefined" && window.sessionStorage) {
              const orgId = String(window.sessionStorage.getItem(ORG_STORAGE_KEY) || "").trim();
              if (orgId) orgEl.value = orgId;
            }
          } catch (error) {
            // ignore
          }
          if (!String(orgEl.value || "").trim()) orgEl.value = "default-org";
        }

        function headersFromInputs() {
          const headers = { "Accept": "application/json" };
          const orgId = String(orgEl.value || "").trim();
          if (orgId) headers["X-Org-Id"] = orgId;
          return headers;
        }

        function renderRows(rows) {
          if (!Array.isArray(rows) || rows.length === 0) {
            listEl.innerHTML = '<div class="meta">Keine Einträge.</div>';
            return;
          }

          const html = rows.map((row) => {
            const resultId = String(row && row.result_id ? row.result_id : "").trim();
            const query = String(row && row.query ? row.query : "").trim() || "(ohne Query)";
            const when = formatLocalTime(row && row.created_at ? row.created_at : "");
            const mode = String(row && row.intelligence_mode ? row.intelligence_mode : "basic").trim();
            const status = String(row && row.status ? row.status : "").trim();
            const href = resultId ? `/results/${encodeURIComponent(resultId)}` : "#";

            const metaParts = [when, mode];
            if (status) metaParts.push(status);
            const meta = metaParts.filter(Boolean).join(" · ");

            return `
              <div class="pill">
                <div style="display:flex; flex-direction: column; gap: 0.1rem;">
                  <strong>${escapeHtml(query)}</strong>
                  <span class="meta">${escapeHtml(meta)}</span>
                </div>
                <a href="${href}">Open</a>
              </div>
            `;
          }).join("\n");

          listEl.innerHTML = html;
        }

        async function loadHistory() {
          setError("");
          persistInputs();
          setStatus("loading");
          loadBtn.disabled = true;

          const limit = String(limitEl.value || "50").trim() || "50";
          const url = `${ANALYZE_HISTORY_ENDPOINT}?limit=${encodeURIComponent(limit)}`;

          let response;
          let parsed;
          try {
            response = await fetch(url, { method: "GET", headers: headersFromInputs(), credentials: "include" });
            parsed = await response.json();
          } catch (error) {
            setStatus("error");
            setError(error instanceof Error ? error.message : "network_error");
            loadBtn.disabled = false;
            return;
          }

          if (!response.ok || !parsed || !parsed.ok) {
            setStatus("error");
            const errCode = parsed && parsed.error ? String(parsed.error) : `http_${response.status}`;
            const fallbackMessage = (parsed && parsed.message) ? String(parsed.message) : `http_${response.status}`;
            const authFailure = resolveAuthFailure(response.status, errCode, fallbackMessage);
            setError(authFailure.errorMessage);
            if (authFailure.requiresLoginRecovery) {
              scheduleReLoginRedirect(response.status, authFailure.errorCode);
            }
            loadBtn.disabled = false;
            return;
          }

          setStatus("success");
          renderRows(parsed.history);
          loadBtn.disabled = false;
        }

        loadBtn.addEventListener("click", () => { void loadHistory(); });
        clearBtn.addEventListener("click", () => { listEl.innerHTML = '<div class="meta">Noch nicht geladen.</div>'; });

        applyInitialState();
        void loadHistory();
      </script>
    </main>
  </body>
</html>
"""

_RESULT_TABS_PAGE_TEMPLATE = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>geo-ranking.ch — Result __RESULT_ID__</title>
    <style>
      :root {
        color-scheme: light;
        --bg: #f6f8fb;
        --surface: #ffffff;
        --ink: #1b2637;
        --muted: #5a6474;
        --border: #d5dbea;
        --primary: #1957d2;
        --danger: #b93a2f;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        background: var(--bg);
        color: var(--ink);
      }
      header {
        background: var(--surface);
        border-bottom: 1px solid var(--border);
        padding: 1rem 1.25rem;
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
        align-items: baseline;
      }
      header h1 { margin: 0; font-size: 1.05rem; }
      header p { margin: 0; color: var(--muted); font-size: 0.9rem; }
      __BURGER_CSS__

      main {
        padding: 1rem 1.25rem 1.5rem;
        display: grid;
        gap: 1rem;
        max-width: 1100px;
      }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.85rem;
        padding: 1rem;
      }
      .card h2 { margin: 0 0 0.75rem; font-size: 1rem; }
      .meta { font-size: 0.84rem; color: var(--muted); }
      label {
        display: grid;
        gap: 0.3rem;
        font-size: 0.86rem;
        color: var(--muted);
      }
      input, select, button {
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 0.55rem 0.6rem;
        font: inherit;
      }
      button {
        background: var(--primary);
        color: #fff;
        border-color: var(--primary);
        cursor: pointer;
      }
      button[disabled] { opacity: 0.65; cursor: not-allowed; }
      .error {
        border: 1px solid rgba(185, 58, 47, 0.35);
        background: rgba(185, 58, 47, 0.08);
        padding: 0.75rem;
        border-radius: 0.65rem;
        color: var(--danger);
        white-space: pre-wrap;
      }
      pre {
        margin: 0;
        max-height: 34rem;
        overflow: auto;
        background: #f8faff;
        border: 1px solid var(--border);
        border-radius: 0.65rem;
        padding: 0.75rem;
      }
      code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

      .grid-3 {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: 1fr 1fr 1fr;
      }
      @media (max-width: 860px) {
        .grid-3 { grid-template-columns: 1fr; }
      }

      .tabs {
        display: flex;
        gap: 0.45rem;
        flex-wrap: wrap;
        margin-bottom: 0.75rem;
      }
      .tab-btn {
        background: #fff;
        color: var(--ink);
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 0.35rem 0.75rem;
        cursor: pointer;
        font-size: 0.88rem;
      }
      .tab-btn[data-active="true"] {
        background: #f3f7ff;
        border-color: #c9d8ff;
        color: var(--primary);
      }
      .tab-panel[hidden] { display: none; }

      .kv {
        display: grid;
        gap: 0.35rem;
      }
      .kv-row {
        display: grid;
        grid-template-columns: minmax(160px, 260px) 1fr;
        gap: 0.75rem;
        align-items: baseline;
        border-bottom: 1px dashed rgba(213, 219, 234, 0.75);
        padding: 0.35rem 0;
      }
      @media (max-width: 720px) {
        .kv-row { grid-template-columns: 1fr; }
      }
      .kv-row dt { color: var(--muted); font-size: 0.86rem; }
      .kv-row dd { margin: 0; }
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>Result</h1>
        <p>result_id: <code id="result-id" data-result-id="__RESULT_ID__">__RESULT_ID__</code> · Version __APP_VERSION__</p>
      </div>
      <div class="burger">
        <button id="burger-btn" type="button" aria-haspopup="true" aria-expanded="false" aria-controls="burger-menu" aria-label="Navigation umschalten">☰ Menü</button>
        <div id="burger-menu" class="burger-menu" role="menu" aria-label="Hauptnavigation" hidden>
          <a role="menuitem" href="/gui">Abfrage</a>
          <a role="menuitem" href="/history">Historische Abfragen</a>
        </div>
      </div>
    </header>

    <main>
      <section class="card">
        <h2>Loader</h2>
        <p class="meta">Lädt via <code>GET /analyze/results/&lt;result_id&gt;</code>. Optional: Bearer-Token + Tenant (<code>X-Org-Id</code>).</p>
        <div class="grid-3">
          <label>
            API Token (optional)
            <input id="api-token" type="password" placeholder="Bearer-Token" autocomplete="off" />
          </label>
          <label>
            X-Org-Id (Tenant)
            <input id="org-id" type="text" placeholder="default-org" />
          </label>
          <label>
            view
            <select id="view-mode">
              <option value="latest" selected>latest</option>
              <option value="requested">requested</option>
            </select>
          </label>
        </div>
        <div style="display:flex; gap: 0.65rem; flex-wrap: wrap; margin-top: 0.85rem; align-items: center;">
          <button id="load-btn" type="button">Result laden</button>
          <a id="raw-link" class="meta" href="#" target="_blank" rel="noopener noreferrer">Raw JSON öffnen</a>
          <span id="status" class="meta">Status: idle</span>
        </div>
        <div id="error" class="error" hidden></div>
      </section>

      <section class="card">
        <div class="tabs" role="tablist" aria-label="Result Tabs">
          <button class="tab-btn" type="button" data-tab="overview" data-active="true">Overview</button>
          <button class="tab-btn" type="button" data-tab="sources" data-active="false">Sources / Evidence</button>
          <button class="tab-btn" type="button" data-tab="derived" data-active="false">Generated / Derived</button>
          <button class="tab-btn" type="button" data-tab="raw" data-active="false">Raw JSON</button>
        </div>

        <div id="tab-overview" class="tab-panel">
          <div id="overview" class="meta">Noch nicht geladen.</div>
        </div>

        <div id="tab-sources" class="tab-panel" hidden>
          <div id="sources" class="meta">Noch nicht geladen.</div>
        </div>

        <div id="tab-derived" class="tab-panel" hidden>
          <div id="derived" class="meta">Noch nicht geladen.</div>
        </div>

        <div id="tab-raw" class="tab-panel" hidden>
          <pre id="payload">{\n  "hint": "Loading..."\n}</pre>
        </div>
      </section>

      <script>
        const RESULT_ID = __RESULT_ID_JSON__;
        const RESULTS_ENDPOINT_BASE = __RESULTS_ENDPOINT_BASE_JSON__;
        const TOKEN_STORAGE_KEY = "geo-ranking-ui-api-token";
        const ORG_STORAGE_KEY = "geo-ranking-ui-org-id";

        const tokenEl = document.getElementById("api-token");
        const orgEl = document.getElementById("org-id");
        const viewModeEl = document.getElementById("view-mode");
        const statusEl = document.getElementById("status");
        const loadBtn = document.getElementById("load-btn");
        const payloadEl = document.getElementById("payload");
        const errorEl = document.getElementById("error");
        const rawLinkEl = document.getElementById("raw-link");

        const overviewEl = document.getElementById("overview");
        const sourcesEl = document.getElementById("sources");
        const derivedEl = document.getElementById("derived");

        __BURGER_JS__

        function prettyPrint(value) {
          try {
            return JSON.stringify(value, null, 2);
          } catch (error) {
            return String(value);
          }
        }

        function escapeHtml(text) {
          const raw = String(text == null ? "" : text);
          return raw
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#039;");
        }

        function setStatus(value) {
          statusEl.textContent = `Status: ${value}`;
        }

        function setError(message) {
          const text = String(message || "").trim();
          if (!text) {
            errorEl.hidden = true;
            errorEl.textContent = "";
            return;
          }
          errorEl.hidden = false;
          errorEl.textContent = text;
        }

        function normalizedViewMode() {
          const raw = String(viewModeEl.value || "latest").trim().toLowerCase();
          if (raw === "requested") return "requested";
          return "latest";
        }

        function buildResultUrl() {
          const view = normalizedViewMode();
          const encodedId = encodeURIComponent(RESULT_ID);
          return `${RESULTS_ENDPOINT_BASE}/${encodedId}?view=${encodeURIComponent(view)}`;
        }

        function persistInputs() {
          try {
            if (typeof window !== "undefined" && window.sessionStorage) {
              const token = String(tokenEl.value || "").trim();
              if (token) window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
              else window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);

              const orgId = String(orgEl.value || "").trim();
              if (orgId) window.sessionStorage.setItem(ORG_STORAGE_KEY, orgId);
              else window.sessionStorage.removeItem(ORG_STORAGE_KEY);
            }
          } catch (error) {
            // ignore
          }
        }

        function applyInitialState() {
          try {
            if (typeof window !== "undefined" && window.sessionStorage) {
              const token = String(window.sessionStorage.getItem(TOKEN_STORAGE_KEY) || "").trim();
              if (token) tokenEl.value = token;
              const orgId = String(window.sessionStorage.getItem(ORG_STORAGE_KEY) || "").trim();
              if (orgId) orgEl.value = orgId;
            }
          } catch (error) {
            // ignore
          }
          if (!String(orgEl.value || "").trim()) orgEl.value = "default-org";
          rawLinkEl.href = buildResultUrl();
        }

        function headersFromInputs() {
          const headers = { "Accept": "application/json" };
          const token = String(tokenEl.value || "").trim();
          if (token) headers["Authorization"] = `Bearer ${token}`;
          const orgId = String(orgEl.value || "").trim();
          if (orgId) headers["X-Org-Id"] = orgId;
          return headers;
        }

        function setActiveTab(tabKey) {
          const key = String(tabKey || "overview").trim();
          const mapping = {
            overview: document.getElementById("tab-overview"),
            sources: document.getElementById("tab-sources"),
            derived: document.getElementById("tab-derived"),
            raw: document.getElementById("tab-raw"),
          };
          Object.entries(mapping).forEach(([k, el]) => {
            if (!el) return;
            el.hidden = k !== key;
          });
          document.querySelectorAll(".tab-btn").forEach((btn) => {
            const isActive = btn.getAttribute("data-tab") === key;
            btn.setAttribute("data-active", isActive ? "true" : "false");
          });
        }

        function kvRow(label, value) {
          const safeLabel = escapeHtml(label);
          const safeValue = escapeHtml(value);
          return `<div class="kv-row"><dt>${safeLabel}</dt><dd>${safeValue || "—"}</dd></div>`;
        }

        function asObject(value) {
          if (!value || typeof value !== "object" || Array.isArray(value)) {
            return {};
          }
          return value;
        }

        function hasValue(value) {
          if (value == null) return false;
          if (typeof value === "string") return value.trim().length > 0;
          if (Array.isArray(value)) return value.length > 0;
          if (typeof value === "object") return Object.keys(value).length > 0;
          return true;
        }

        function formatFallback(value, fallback = "—") {
          if (!hasValue(value)) return fallback;
          if (typeof value === "object") return prettyPrint(value);
          return String(value);
        }

        function renderSafe(renderer, targetEl, groupedResult, fallbackLabel) {
          try {
            renderer(groupedResult);
          } catch (error) {
            const message = error instanceof Error ? error.message : "render_error";
            targetEl.innerHTML = `
              <div class="meta">${escapeHtml(fallbackLabel)}</div>
              <pre>${escapeHtml(prettyPrint({ error: "render_error", message, result: groupedResult || null }))}</pre>
            `;
          }
        }

        function renderOverview(groupedResult) {
          if (!groupedResult || typeof groupedResult !== "object") {
            overviewEl.innerHTML = '<div class="meta">No result payload.</div>';
            return;
          }

          const isGrouped = Boolean(groupedResult.status && groupedResult.data);
          if (!isGrouped) {
            overviewEl.innerHTML = `<div class="meta">Unbekanntes Result-Format.</div><pre>${escapeHtml(prettyPrint(groupedResult))}</pre>`;
            return;
          }

          const status = asObject(groupedResult.status);
          const data = asObject(groupedResult.data);
          const entity = asObject(data.entity);
          const modules = asObject(data.modules);
          const summaryCompact = asObject(modules.summary_compact);
          const quality = asObject(status.quality);

          const executiveSummary = status.executive_summary || summaryCompact.executive_summary || "";
          const confidence = status.confidence || quality.confidence || null;
          const coords = entity.coordinates || entity.coords || null;
          const ids = asObject(entity.ids);
          const admin = asObject(entity.administrative || entity.admin);

          const rows = [];
          rows.push(kvRow("Query", formatFallback(entity.query)));
          rows.push(kvRow("Matched address", formatFallback(entity.matched_address)));
          rows.push(kvRow("Confidence", formatFallback(confidence && typeof confidence === "object" ? (confidence.level || confidence.score) : confidence)));
          rows.push(kvRow("Coordinates", formatFallback(coords, "nicht verfügbar")));
          rows.push(kvRow("IDs", formatFallback(ids, "nicht verfügbar")));
          rows.push(kvRow("Administrative", formatFallback(admin, "nicht verfügbar")));

          const headerParts = [];
          if (String(executiveSummary || "").trim()) {
            headerParts.push(`<p style="margin: 0 0 0.75rem;"><strong>Executive summary</strong><br>${escapeHtml(executiveSummary)}</p>`);
          }

          const overviewPayload = {
            executive_summary: executiveSummary || null,
            confidence: confidence || null,
            matched_address: entity.matched_address || null,
            coords: hasValue(coords) ? coords : null,
            ids: hasValue(ids) ? ids : null,
            admin: hasValue(admin) ? admin : null,
            status: status,
          };

          overviewEl.innerHTML = `${headerParts.join("")}<dl class="kv">${rows.join("")}</dl><pre style="margin-top: 0.85rem;">${escapeHtml(prettyPrint(overviewPayload))}</pre>`;
        }

        function renderSources(groupedResult) {
          if (!groupedResult || typeof groupedResult !== "object") {
            sourcesEl.innerHTML = '<div class="meta">No result payload.</div>';
            return;
          }
          const isGrouped = Boolean(groupedResult.status && groupedResult.data);
          if (!isGrouped) {
            sourcesEl.innerHTML = `<pre>${escapeHtml(prettyPrint(groupedResult))}</pre>`;
            return;
          }

          const status = asObject(groupedResult.status);
          const data = asObject(groupedResult.data);
          const payload = {
            sources: status.sources || null,
            source_attribution: status.source_attribution || null,
            source_classification: status.source_classification || null,
            source_health: status.source_health || null,
            source_meta: status.source_meta || null,
            by_source: data.by_source || null,
          };
          sourcesEl.innerHTML = `<pre>${escapeHtml(prettyPrint(payload))}</pre>`;
        }

        function renderDerived(groupedResult) {
          if (!groupedResult || typeof groupedResult !== "object") {
            derivedEl.innerHTML = '<div class="meta">No result payload.</div>';
            return;
          }
          const isGrouped = Boolean(groupedResult.status && groupedResult.data);
          if (!isGrouped) {
            derivedEl.innerHTML = `<pre>${escapeHtml(prettyPrint(groupedResult))}</pre>`;
            return;
          }

          // Derived should focus on computed signals and exclude raw sources + summary views.
          let payload;
          try {
            payload = JSON.parse(JSON.stringify(groupedResult));
          } catch (error) {
            payload = null;
          }

          if (payload && payload.status && typeof payload.status === "object") {
            delete payload.status.sources;
            delete payload.status.source_attribution;
            delete payload.status.source_classification;
            delete payload.status.source_health;
            delete payload.status.source_meta;
            delete payload.status.executive_summary;
          }

          if (payload && payload.data && typeof payload.data === "object") {
            delete payload.data.by_source;
            if (payload.data.modules && typeof payload.data.modules === "object") {
              delete payload.data.modules.summary_compact;
            }
          }

          const hasAnyContent = Boolean(
            payload && typeof payload === "object" && (
              (payload.status && Object.keys(payload.status || {}).length) ||
              (payload.data && Object.keys(payload.data || {}).length)
            )
          );

          derivedEl.innerHTML = `<pre>${escapeHtml(prettyPrint(hasAnyContent ? payload : groupedResult))}</pre>`;
        }

        async function loadResult() {
          setError("");
          persistInputs();
          setStatus("loading");
          loadBtn.disabled = true;

          const url = buildResultUrl();
          rawLinkEl.href = url;

          let response;
          let parsed;
          try {
            response = await fetch(url, { method: "GET", headers: headersFromInputs(), credentials: "include" });
            parsed = await response.json();
          } catch (error) {
            setStatus("error");
            setError(error instanceof Error ? error.message : "network_error");
            payloadEl.textContent = prettyPrint({ ok: false, error: "network_error" });
            loadBtn.disabled = false;
            return;
          }

          payloadEl.textContent = prettyPrint(parsed);

          if (!response.ok || !parsed || !parsed.ok) {
            setStatus("error");
            if (response.status === 401) {
              const hasToken = Boolean(String(tokenEl.value || "").trim());
              setError(hasToken ? "Authorization fehlgeschlagen — Token ungültig oder abgelaufen" : "Bitte Bearer-Token setzen — API erfordert Authentifizierung");
            } else {
              const errCode = parsed && parsed.error ? parsed.error : `http_${response.status}`;
              const errMsg = parsed && parsed.message ? parsed.message : "Unbekannter Fehler";
              setError(`${errCode}: ${errMsg}`);
            }
            loadBtn.disabled = false;
            return;
          }

          setStatus("success");
          const groupedResult = parsed.result;
          renderSafe(renderOverview, overviewEl, groupedResult, "Overview konnte wegen fehlender optionaler Metadaten nicht vollständig gerendert werden.");
          renderSafe(renderSources, sourcesEl, groupedResult, "Sources konnten wegen fehlender optionaler Metadaten nicht vollständig gerendert werden.");
          renderSafe(renderDerived, derivedEl, groupedResult, "Derived konnte wegen fehlender optionaler Metadaten nicht vollständig gerendert werden.");
          loadBtn.disabled = false;
        }

        document.querySelectorAll(".tab-btn").forEach((btn) => {
          btn.addEventListener("click", () => {
            setActiveTab(btn.getAttribute("data-tab"));
          });
        });

        viewModeEl.addEventListener("change", () => {
          rawLinkEl.href = buildResultUrl();
        });

        loadBtn.addEventListener("click", () => {
          void loadResult();
        });

        applyInitialState();
        setActiveTab("overview");
        void loadResult();
      </script>
    </main>
  </body>
</html>
"""


def build_history_page_html(*, app_version: str, api_base_url: str) -> str:
    html = _HISTORY_PAGE_TEMPLATE
    html = html.replace("__APP_VERSION__", escape(app_version or "dev"))
    html = html.replace("__ANALYZE_HISTORY_ENDPOINT_JSON__", json.dumps(_history_endpoint(api_base_url)))
    html = html.replace("__AUTH_LOGIN_ENDPOINT_JSON__", json.dumps(_auth_login_endpoint(api_base_url)))
    html = html.replace("__BURGER_CSS__", _BURGER_CSS)
    html = html.replace("__BURGER_JS__", _BURGER_JS)
    return html


def build_result_tabs_page_html(*, app_version: str, api_base_url: str, result_id: str) -> str:
    normalized_result_id = normalize_result_id(result_id)
    if not normalized_result_id:
        raise ValueError("invalid result_id")

    html = _RESULT_TABS_PAGE_TEMPLATE
    html = html.replace("__APP_VERSION__", escape(app_version or "dev"))
    html = html.replace("__RESULT_ID__", escape(normalized_result_id))
    html = html.replace("__RESULT_ID_JSON__", json.dumps(normalized_result_id))
    html = html.replace("__RESULTS_ENDPOINT_BASE_JSON__", json.dumps(_results_endpoint_base(api_base_url)))
    html = html.replace("__BURGER_CSS__", _BURGER_CSS)
    html = html.replace("__BURGER_JS__", _BURGER_JS)
    return html


__all__ = [
    "build_history_page_html",
    "build_result_tabs_page_html",
    "normalize_result_id",
]
