#!/usr/bin/env python3
"""Service-neutrale HTML Pages (stdlib-only).

Diese Pages werden sowohl vom API-Service als auch vom UI-Service ausgeliefert.
Sie laden Daten API-first über JSON-Endpunkte.

- /gui/history (legacy: /history) → GET /analyze/history
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
    """Return UI-owned result endpoint base.

    ``api_base_url`` wird absichtlich ignoriert: Result-Permalinks laufen
    browserseitig immer same-origin über den UI-/API-Host, damit
    Host-only-Cookies (``__Host-session``) und Auth-Proxy konsistent bleiben.
    """

    _ = api_base_url
    return "/analyze/results"


def _history_endpoint(api_base_url: str) -> str:
    """Return UI-owned history endpoint.

    ``api_base_url`` bleibt absichtlich ungenutzt, um CORS/Preflight-Probleme
    bei Cross-Origin-Calls aus dem Browser zu vermeiden.
    """

    _ = api_base_url
    return "/analyze/history"


def _auth_login_endpoint(api_base_url: str) -> str:
    """Return UI-owned login entrypoint.

    ``api_base_url`` bleibt absichtlich ungenutzt: der Browser soll sich immer
    über ``/login`` auf der UI-Domain einloggen und nicht direkt den API-Host
    ansurfen.
    """

    _ = api_base_url
    return "/login"


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
      .toolbar-row {
        display: flex;
        gap: 0.65rem;
        flex-wrap: wrap;
        margin-top: 0.85rem;
        align-items: center;
      }
      .toolbar-row .meta { margin-left: auto; }
      .pagination-row {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        align-items: center;
      }
      .pagination-row .meta {
        margin-left: auto;
      }
      .pagination-row button[disabled] {
        opacity: 0.6;
        cursor: not-allowed;
      }
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
          <a role="menuitem" href="/gui/history">Historische Abfragen</a>
        </div>
      </div>
    </header>

    <main>
      <section class="card">
        <h2>Loader</h2>
        <p class="meta">Lädt via <code>GET /analyze/history</code>. Auth läuft über Login/Session-Cookie; optional Tenant-Header via <code>X-Org-Id</code>. Filter + Pagination werden in der UI angewendet.</p>
        <div class="grid-3">
          <label>
            X-Org-Id (Tenant)
            <input id="org-id" type="text" placeholder="default-org" />
          </label>
          <label>
            Page size
            <select id="limit">
              <option value="25">25</option>
              <option value="50" selected>50</option>
              <option value="100">100</option>
              <option value="200">200</option>
            </select>
          </label>
          <label>
            Status-Filter
            <select id="history-status-filter">
              <option value="all">all</option>
              <option value="queued">queued</option>
              <option value="running">running</option>
              <option value="partial">partial</option>
              <option value="succeeded">succeeded</option>
              <option value="failed">failed</option>
              <option value="canceled">canceled</option>
            </select>
          </label>
        </div>
        <div class="grid-3" style="margin-top: 0.65rem;">
          <label>
            Suche (query/result_id/job_id)
            <input id="history-query-filter" type="text" placeholder="z. B. St. Gallen oder res-123" autocomplete="off" />
          </label>
        </div>
        <div class="toolbar-row">
          <button id="load-btn" type="button">Historie laden</button>
          <button id="clear-btn" class="secondary" type="button">Clear</button>
          <span id="status" class="meta">Status: idle</span>
        </div>
        <div id="error" class="error" hidden></div>
      </section>

      <section class="card">
        <h2>Liste</h2>
        <div class="pagination-row" style="margin-bottom: 0.75rem;">
          <button id="history-page-prev" class="secondary" type="button">← Zurück</button>
          <button id="history-page-next" class="secondary" type="button">Weiter →</button>
          <span id="history-page-meta" class="meta">Seite 1</span>
          <span id="history-filter-meta" class="meta">—</span>
        </div>
        <div id="history-list" class="stack"><div class="meta">Noch nicht geladen.</div></div>
      </section>

      <script>
        const ANALYZE_HISTORY_ENDPOINT = __ANALYZE_HISTORY_ENDPOINT_JSON__;
        const AUTH_LOGIN_ENDPOINT = __AUTH_LOGIN_ENDPOINT_JSON__;
        const ORG_STORAGE_KEY = "geo-ranking-ui-org-id";
        const SESSION_RECOVERY_ERROR_CODES = new Set([
          "no_session_cookie",
          "session_not_found",
          "missing_state",
          "missing_session_cookie",
          "state_mismatch",
          "missing_code_verifier",
          "invalid_state",
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
          missing_state: "invalid_state",
          missing_session_cookie: "invalid_state",
          state_mismatch: "invalid_state",
          missing_code_verifier: "invalid_state",
          invalid_state: "invalid_state",
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
        const statusFilterEl = document.getElementById("history-status-filter");
        const queryFilterEl = document.getElementById("history-query-filter");
        const statusEl = document.getElementById("status");
        const loadBtn = document.getElementById("load-btn");
        const clearBtn = document.getElementById("clear-btn");
        const prevPageBtn = document.getElementById("history-page-prev");
        const nextPageBtn = document.getElementById("history-page-next");
        const pageMetaEl = document.getElementById("history-page-meta");
        const filterMetaEl = document.getElementById("history-filter-meta");
        const errorEl = document.getElementById("error");
        const listEl = document.getElementById("history-list");

        const historyState = {
          page: 1,
          limit: 50,
          total: 0,
          rows: [],
          statusFilter: "all",
          queryFilter: "",
          loaded: false,
        };

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
          if (
            normalizedCode === "invalid_state"
            || normalizedCode === "missing_state"
            || normalizedCode === "missing_session_cookie"
            || normalizedCode === "state_mismatch"
            || normalizedCode === "missing_code_verifier"
          ) {
            return "Login-Status ungültig oder abgelaufen — bitte Anmeldung neu starten.";
          }
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
            ? `${window.location.pathname || "/gui/history"}${window.location.search || ""}${window.location.hash || ""}`
            : "/gui/history";

          if (typeof URLSearchParams === "undefined") {
            return `${AUTH_LOGIN_ENDPOINT}?next=${encodeURIComponent(nextPath || "/gui/history")}&reason=${encodeURIComponent(normalizedReason)}`;
          }

          const params = new URLSearchParams();
          params.set("next", nextPath || "/gui/history");
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

        function normalizeLimit(value) {
          const normalized = Number(String(value || "50").trim());
          if (!Number.isFinite(normalized)) return 50;
          if (normalized === 25 || normalized === 50 || normalized === 100 || normalized === 200) {
            return normalized;
          }
          return 50;
        }

        function normalizePage(value) {
          const normalized = Math.trunc(Number(value));
          if (!Number.isFinite(normalized) || normalized < 1) return 1;
          return normalized;
        }

        function canonicalHistoryStatus(value) {
          const normalized = String(value || "").trim().toLowerCase();
          if (!normalized) return "";
          if (normalized === "completed" || normalized === "success") return "succeeded";
          if (normalized === "cancelled") return "canceled";
          return normalized;
        }

        function normalizeStatusFilter(value) {
          const normalized = canonicalHistoryStatus(String(value || "all").trim().toLowerCase()) || "all";
          const allowed = new Set(["all", "queued", "running", "partial", "succeeded", "failed", "canceled"]);
          return allowed.has(normalized) ? normalized : "all";
        }

        function updateControlsFromState() {
          limitEl.value = String(historyState.limit);
          statusFilterEl.value = historyState.statusFilter;
          queryFilterEl.value = historyState.queryFilter;
        }

        function updateDeepLink() {
          if (typeof window === "undefined" || !window.history || !window.location) return;

          const nextUrl = new URL(window.location.href);
          if (historyState.page > 1) nextUrl.searchParams.set("history_page", String(historyState.page));
          else nextUrl.searchParams.delete("history_page");

          if (historyState.limit !== 50) nextUrl.searchParams.set("history_limit", String(historyState.limit));
          else nextUrl.searchParams.delete("history_limit");

          if (historyState.statusFilter !== "all") nextUrl.searchParams.set("history_status", historyState.statusFilter);
          else nextUrl.searchParams.delete("history_status");

          if (historyState.queryFilter) nextUrl.searchParams.set("history_q", historyState.queryFilter);
          else nextUrl.searchParams.delete("history_q");

          window.history.replaceState({}, "", nextUrl);
        }

        function restoreDeepLinkState() {
          if (typeof window === "undefined" || !window.location) return;
          const url = new URL(window.location.href);
          historyState.page = normalizePage(url.searchParams.get("history_page") || "1");
          historyState.limit = normalizeLimit(url.searchParams.get("history_limit") || "50");
          historyState.statusFilter = normalizeStatusFilter(url.searchParams.get("history_status") || "all");
          historyState.queryFilter = String(url.searchParams.get("history_q") || "").trim();
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

          restoreDeepLinkState();
          updateControlsFromState();
        }

        function createUiCorrelationId(prefix = "req") {
          const normalizedPrefix = String(prefix || "req").replace(/[^a-z0-9_-]/gi, "").toLowerCase() || "req";
          const randomChunk = Math.random().toString(36).slice(2, 10);
          return `${normalizedPrefix}-${Date.now().toString(36)}-${randomChunk}`;
        }

        function headersFromInputs(requestId = "") {
          const normalizedRequestId = String(requestId || createUiCorrelationId("req")).trim();
          const headers = { "Accept": "application/json" };
          if (normalizedRequestId) {
            headers["X-Request-Id"] = normalizedRequestId;
            headers["X-Correlation-Id"] = normalizedRequestId;
          }
          const orgId = String(orgEl.value || "").trim();
          if (orgId) headers["X-Org-Id"] = orgId;
          return headers;
        }

        function syncStateFromControls({ resetPage = false } = {}) {
          historyState.limit = normalizeLimit(limitEl.value);
          historyState.statusFilter = normalizeStatusFilter(statusFilterEl.value);
          historyState.queryFilter = String(queryFilterEl.value || "").trim();
          if (resetPage) {
            historyState.page = 1;
          }
        }

        function buildHistoryRequestUrl() {
          const offset = Math.max(0, (historyState.page - 1) * historyState.limit);
          return `${ANALYZE_HISTORY_ENDPOINT}?limit=${encodeURIComponent(String(historyState.limit))}&offset=${encodeURIComponent(String(offset))}`;
        }

        function applyClientFilters(rows) {
          if (!Array.isArray(rows)) return [];

          const normalizedQuery = String(historyState.queryFilter || "").trim().toLowerCase();
          const normalizedStatus = normalizeStatusFilter(historyState.statusFilter);

          return rows.filter((row) => {
            const rowStatus = canonicalHistoryStatus(row && row.status ? String(row.status) : "");
            if (normalizedStatus !== "all" && rowStatus !== normalizedStatus) {
              return false;
            }

            if (!normalizedQuery) {
              return true;
            }

            const haystack = [
              String(row && row.query ? row.query : ""),
              String(row && row.result_id ? row.result_id : ""),
              String(row && row.job_id ? row.job_id : ""),
              rowStatus,
            ]
              .join(" ")
              .toLowerCase();

            return haystack.includes(normalizedQuery);
          });
        }

        function renderRows(rows) {
          if (!Array.isArray(rows) || rows.length === 0) {
            listEl.innerHTML = '<div class="meta">Keine Einträge mit aktuellem Filter auf dieser Seite.</div>';
            return;
          }

          const html = rows.map((row) => {
            const resultId = String(row && row.result_id ? row.result_id : "").trim();
            const query = String(row && row.query ? row.query : "").trim() || "(ohne Query)";
            const when = formatLocalTime(row && row.created_at ? row.created_at : "");
            const mode = String(row && row.intelligence_mode ? row.intelligence_mode : "basic").trim();
            const status = canonicalHistoryStatus(row && row.status ? row.status : "") || "unknown";
            const href = resultId ? `/results/${encodeURIComponent(resultId)}` : "#";
            const openAttrs = resultId ? "" : 'aria-disabled="true" tabindex="-1"';

            const metaParts = [when, mode, status].filter(Boolean);
            const meta = metaParts.join(" · ");

            return `
              <div class="pill">
                <div style="display:flex; flex-direction: column; gap: 0.1rem;">
                  <strong>${escapeHtml(query)}</strong>
                  <span class="meta">${escapeHtml(meta)}</span>
                </div>
                <a href="${href}" ${openAttrs}>Open</a>
              </div>
            `;
          }).join("\n");

          listEl.innerHTML = html;
        }

        function renderPageMeta(filteredCount) {
          const total = Math.max(0, Number(historyState.total) || 0);
          const offset = Math.max(0, (historyState.page - 1) * historyState.limit);
          const hasRows = total > 0;
          const start = hasRows ? offset + 1 : 0;
          const end = hasRows ? Math.min(offset + historyState.limit, total) : 0;
          const totalPages = Math.max(1, Math.ceil(total / historyState.limit));

          pageMetaEl.textContent = `Seite ${historyState.page}/${totalPages} · ${start}-${end} von ${total}`;
          filterMetaEl.textContent = `sichtbar: ${filteredCount}`;

          prevPageBtn.disabled = historyState.page <= 1;
          nextPageBtn.disabled = historyState.page >= totalPages;
        }

        function renderCurrentPage() {
          const filteredRows = applyClientFilters(historyState.rows);
          renderRows(filteredRows);
          renderPageMeta(filteredRows.length);
          updateDeepLink();
        }

        async function loadHistory() {
          setError("");
          persistInputs();
          syncStateFromControls();
          setStatus("loading");

          loadBtn.disabled = true;
          prevPageBtn.disabled = true;
          nextPageBtn.disabled = true;

          const url = buildHistoryRequestUrl();

          let response;
          let parsed;
          const requestId = createUiCorrelationId("req");
          try {
            response = await fetch(url, { method: "GET", headers: headersFromInputs(requestId), credentials: "include" });
            parsed = await response.json();
          } catch (error) {
            setStatus("error");
            setError(error instanceof Error ? error.message : "network_error");
            loadBtn.disabled = false;
            renderPageMeta(0);
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
            renderPageMeta(0);
            return;
          }

          historyState.rows = Array.isArray(parsed.history) ? parsed.history : [];
          historyState.total = Number(parsed.total);
          if (!Number.isFinite(historyState.total) || historyState.total < 0) {
            historyState.total = historyState.rows.length;
          }
          historyState.loaded = true;

          setStatus("success");
          renderCurrentPage();
          loadBtn.disabled = false;
        }

        function resetHistoryView() {
          historyState.page = 1;
          historyState.limit = 50;
          historyState.total = 0;
          historyState.rows = [];
          historyState.statusFilter = "all";
          historyState.queryFilter = "";
          historyState.loaded = false;
          updateControlsFromState();
          updateDeepLink();
          setError("");
          setStatus("idle");
          listEl.innerHTML = '<div class="meta">Noch nicht geladen.</div>';
          renderPageMeta(0);
        }

        loadBtn.addEventListener("click", () => {
          syncStateFromControls({ resetPage: true });
          void loadHistory();
        });

        clearBtn.addEventListener("click", () => {
          resetHistoryView();
        });

        statusFilterEl.addEventListener("change", () => {
          syncStateFromControls();
          if (historyState.loaded) {
            renderCurrentPage();
          } else {
            updateDeepLink();
          }
        });

        queryFilterEl.addEventListener("input", () => {
          syncStateFromControls();
          if (historyState.loaded) {
            renderCurrentPage();
          } else {
            updateDeepLink();
          }
        });

        limitEl.addEventListener("change", () => {
          syncStateFromControls({ resetPage: true });
          if (historyState.loaded) {
            void loadHistory();
          } else {
            updateDeepLink();
          }
        });

        prevPageBtn.addEventListener("click", () => {
          if (historyState.page <= 1) return;
          historyState.page -= 1;
          updateDeepLink();
          void loadHistory();
        });

        nextPageBtn.addEventListener("click", () => {
          const totalPages = Math.max(1, Math.ceil(Math.max(0, Number(historyState.total) || 0) / historyState.limit));
          if (historyState.page >= totalPages) return;
          historyState.page += 1;
          updateDeepLink();
          void loadHistory();
        });

        applyInitialState();
        renderPageMeta(0);
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
    <title>Result __RESULT_ID__ · geo-ranking-ch</title>
    <style>
      :root {
        --bg: #f3f6fb;
        --surface: #ffffff;
        --surface-soft: #f8fbff;
        --ink: #172236;
        --muted: #5f6c81;
        --border: #d8e2f0;
        --primary: #2159d3;
        --primary-soft: #e9f1ff;
        --success: #1b8f4f;
        --warning: #a06400;
        --danger: #b42338;
        --radius: 0.9rem;
        --shadow: 0 10px 28px rgba(15, 25, 40, 0.08);
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
        background: var(--bg);
        color: var(--ink);
        line-height: 1.45;
      }
      header {
        position: sticky;
        top: 0;
        z-index: 10;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        padding: 1rem 1.2rem;
        background: linear-gradient(180deg, #0f2342 0%, #173059 100%);
        color: #fff;
        box-shadow: 0 8px 20px rgba(9, 20, 38, 0.26);
      }
      h1 {
        margin: 0;
        font-size: clamp(1.1rem, 2.4vw, 1.5rem);
        letter-spacing: 0.01em;
      }
      h2 {
        margin: 0;
        font-size: 1.02rem;
      }
      .header-meta {
        margin-top: 0.2rem;
        color: rgba(255, 255, 255, 0.84);
        font-size: 0.84rem;
      }
      code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      }
      main {
        max-width: 1160px;
        margin: 1rem auto 2.2rem;
        padding: 0 0.9rem;
      }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        padding: 1rem;
        margin-bottom: 0.95rem;
      }
      .loader-grid {
        display: grid;
        gap: 0.8rem;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }
      label {
        display: grid;
        gap: 0.35rem;
        font-size: 0.86rem;
        color: var(--muted);
      }
      select, button {
        font: inherit;
      }
      select {
        border: 1px solid var(--border);
        border-radius: 0.55rem;
        background: #fff;
        padding: 0.46rem 0.58rem;
        min-width: 130px;
      }
      .loader-actions {
        margin-top: 0.8rem;
        display: flex;
        gap: 0.65rem;
        flex-wrap: wrap;
        align-items: center;
      }
      button {
        background: var(--primary);
        color: #fff;
        border: 0;
        border-radius: 0.55rem;
        padding: 0.55rem 0.9rem;
        cursor: pointer;
      }
      button:disabled {
        opacity: 0.58;
        cursor: default;
      }
      button:focus-visible,
      a:focus-visible,
      .tab-btn:focus-visible {
        outline: 3px solid #9ac1ff;
        outline-offset: 2px;
      }
      .meta,
      .subtle {
        color: var(--muted);
        font-size: 0.86rem;
      }
      a {
        color: var(--primary);
      }
      .error {
        margin-top: 0.7rem;
        border: 1px solid #efbac5;
        background: #fff5f7;
        color: var(--danger);
        border-radius: 0.65rem;
        padding: 0.7rem;
        white-space: pre-wrap;
      }

      .tabs {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-bottom: 0.95rem;
      }
      .tab-btn {
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 0.36rem 0.76rem;
        background: #fff;
        color: var(--ink);
        font-size: 0.86rem;
      }
      .tab-btn[aria-selected="true"] {
        background: var(--primary-soft);
        color: #10377f;
        border-color: #bdd2ff;
        font-weight: 600;
      }
      .tab-panel[hidden] { display: none; }

      .panel-content {
        display: grid;
        gap: 0.78rem;
      }
      .data-section {
        border: 1px solid var(--border);
        border-radius: 0.8rem;
        background: var(--surface-soft);
        padding: 0.72rem;
      }
      .data-section h3 {
        margin: 0;
        font-size: 0.95rem;
      }
      .data-section .subtle {
        margin: 0.2rem 0 0.55rem;
      }

      .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-bottom: 0.55rem;
      }
      .badge {
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        padding: 0.23rem 0.62rem;
        border: 1px solid transparent;
        background: #eef2f8;
        color: #334155;
      }
      .badge.good { background: #ecfdf3; border-color: #b7ebcb; color: #166534; }
      .badge.warn { background: #fff7e6; border-color: #fbd28b; color: #9a5800; }
      .badge.bad { background: #fff1f2; border-color: #f6c2ca; color: #9f1239; }
      .badge.info { background: #ebf3ff; border-color: #c8dbff; color: #1d4ed8; }

      .table-wrap {
        overflow-x: auto;
        border: 1px solid #dce5f4;
        border-radius: 0.62rem;
        background: #fff;
      }
      table.data-table {
        width: 100%;
        border-collapse: collapse;
        min-width: 420px;
      }
      .data-table th,
      .data-table td {
        padding: 0.48rem 0.58rem;
        border-bottom: 1px solid #e6edf8;
        vertical-align: top;
        text-align: left;
        font-size: 0.86rem;
      }
      .data-table th {
        width: 34%;
        color: #475569;
        font-weight: 600;
        background: #f8fbff;
      }
      .data-table td {
        color: #122238;
      }
      .data-table tr:last-child th,
      .data-table tr:last-child td { border-bottom: 0; }

      .cell-empty { color: #7a879a; }
      .inline-json {
        display: inline-block;
        max-width: 100%;
        white-space: pre-wrap;
        word-break: break-word;
        background: #f8fbff;
        border: 1px solid #d7e4f6;
        border-radius: 0.5rem;
        padding: 0.1rem 0.28rem;
        font-size: 0.78rem;
      }
      pre {
        margin: 0;
        max-height: 32rem;
        overflow: auto;
        background: #f8fbff;
        border: 1px solid var(--border);
        border-radius: 0.7rem;
        padding: 0.75rem;
        font-size: 0.78rem;
      }
      .empty-state {
        border: 1px dashed #ccd8ea;
        border-radius: 0.62rem;
        background: #f9fbff;
        color: #607089;
        padding: 0.65rem;
        font-size: 0.86rem;
      }

      @media (max-width: 760px) {
        header {
          padding: 0.9rem;
          align-items: center;
        }
        .card { padding: 0.85rem; }
        .data-table th,
        .data-table td { padding: 0.42rem 0.5rem; }
      }

      __BURGER_CSS__
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>Result Explorer</h1>
        <p class="header-meta">result_id: <code id="result-id" data-result-id="__RESULT_ID__">__RESULT_ID__</code> · Version __APP_VERSION__</p>
      </div>
      <div class="burger">
        <button id="burger-btn" type="button" aria-haspopup="true" aria-expanded="false" aria-controls="burger-menu" aria-label="Navigation umschalten">☰ Menü</button>
        <div id="burger-menu" class="burger-menu" role="menu" aria-label="Hauptnavigation" hidden>
          <a role="menuitem" href="/gui">Abfrage</a>
          <a role="menuitem" href="/gui/history">Historische Abfragen</a>
        </div>
      </div>
    </header>

    <main>
      <section class="card" aria-labelledby="loader-title">
        <h2 id="loader-title">Daten laden</h2>
        <p class="meta">Quelle: <code>GET /analyze/results/&lt;result_id&gt;</code> mit bestehender Session (same-origin, BFF/OIDC).</p>

        <div class="loader-grid">
          <label>
            Ansicht
            <select id="view-mode" aria-label="Ansichtsmodus auswählen">
              <option value="latest" selected>latest</option>
              <option value="requested">requested</option>
            </select>
          </label>
        </div>

        <div class="loader-actions">
          <button id="load-btn" type="button">Result laden</button>
          <a id="raw-link" class="subtle" href="#" target="_blank" rel="noopener noreferrer">Raw JSON öffnen</a>
          <span id="status" class="subtle" role="status" aria-live="polite">Status: idle</span>
        </div>

        <div id="error" class="error" hidden></div>
      </section>

      <section class="card" aria-labelledby="tabs-title">
        <h2 id="tabs-title">Resultat nach Themen</h2>
        <p class="meta">Lesbare Übersicht mit thematischen Tabs. Leere Datenbereiche werden robust abgefedert.</p>

        <div class="tabs" role="tablist" aria-label="Resultat-Tabs">
          <button id="tab-btn-overview" class="tab-btn" type="button" role="tab" data-tab="overview" aria-selected="true" aria-controls="tab-overview" tabindex="0">Übersicht</button>
          <button id="tab-btn-location" class="tab-btn" type="button" role="tab" data-tab="location" aria-selected="false" aria-controls="tab-location" tabindex="-1">Lage</button>
          <button id="tab-btn-demographics" class="tab-btn" type="button" role="tab" data-tab="demographics" aria-selected="false" aria-controls="tab-demographics" tabindex="-1">Demografie</button>
          <button id="tab-btn-safety" class="tab-btn" type="button" role="tab" data-tab="safety" aria-selected="false" aria-controls="tab-safety" tabindex="-1">Sicherheit</button>
          <button id="tab-btn-housing" class="tab-btn" type="button" role="tab" data-tab="housing" aria-selected="false" aria-controls="tab-housing" tabindex="-1">Preise &amp; Miete</button>
          <button id="tab-btn-education" class="tab-btn" type="button" role="tab" data-tab="education" aria-selected="false" aria-controls="tab-education" tabindex="-1">Bildung</button>
          <button id="tab-btn-transport" class="tab-btn" type="button" role="tab" data-tab="transport" aria-selected="false" aria-controls="tab-transport" tabindex="-1">Verkehr</button>
          <button id="tab-btn-environment" class="tab-btn" type="button" role="tab" data-tab="environment" aria-selected="false" aria-controls="tab-environment" tabindex="-1">Umwelt</button>
          <button id="tab-btn-sources" class="tab-btn" type="button" role="tab" data-tab="sources" aria-selected="false" aria-controls="tab-sources" tabindex="-1">Quellen &amp; Methodik</button>
          <button id="tab-btn-derived" class="tab-btn" type="button" role="tab" data-tab="derived" aria-selected="false" aria-controls="tab-derived" tabindex="-1">Signale / Derived</button>
          <button id="tab-btn-raw" class="tab-btn" type="button" role="tab" data-tab="raw" aria-selected="false" aria-controls="tab-raw" tabindex="-1">Raw JSON</button>
        </div>

        <div id="tab-overview" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-overview" tabindex="0">
          <div id="panel-overview" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-location" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-location" tabindex="0" hidden>
          <div id="panel-location" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-demographics" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-demographics" tabindex="0" hidden>
          <div id="panel-demographics" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-safety" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-safety" tabindex="0" hidden>
          <div id="panel-safety" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-housing" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-housing" tabindex="0" hidden>
          <div id="panel-housing" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-education" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-education" tabindex="0" hidden>
          <div id="panel-education" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-transport" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-transport" tabindex="0" hidden>
          <div id="panel-transport" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-environment" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-environment" tabindex="0" hidden>
          <div id="panel-environment" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-sources" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-sources" tabindex="0" hidden>
          <div id="panel-sources" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-derived" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-derived" tabindex="0" hidden>
          <div id="panel-derived" class="panel-content"><div class="empty-state">Noch nicht geladen.</div></div>
        </div>

        <div id="tab-raw" class="tab-panel" role="tabpanel" aria-labelledby="tab-btn-raw" tabindex="0" hidden>
          <pre id="payload">{
  "hint": "Loading..."
}</pre>
        </div>
      </section>

      <script>
        const RESULT_ID = __RESULT_ID_JSON__;
        const RESULTS_ENDPOINT_BASE = __RESULTS_ENDPOINT_BASE_JSON__;

        const viewModeEl = document.getElementById("view-mode");
        const statusEl = document.getElementById("status");
        const loadBtn = document.getElementById("load-btn");
        const payloadEl = document.getElementById("payload");
        const errorEl = document.getElementById("error");
        const rawLinkEl = document.getElementById("raw-link");

        const panelEls = {
          overview: document.getElementById("panel-overview"),
          location: document.getElementById("panel-location"),
          demographics: document.getElementById("panel-demographics"),
          safety: document.getElementById("panel-safety"),
          housing: document.getElementById("panel-housing"),
          education: document.getElementById("panel-education"),
          transport: document.getElementById("panel-transport"),
          environment: document.getElementById("panel-environment"),
          sources: document.getElementById("panel-sources"),
          derived: document.getElementById("panel-derived"),
          raw: payloadEl,
        };

        const TAB_SEQUENCE = [
          "overview",
          "location",
          "demographics",
          "safety",
          "housing",
          "education",
          "transport",
          "environment",
          "sources",
          "derived",
          "raw",
        ];

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

        function asObject(value) {
          if (!value || typeof value !== "object" || Array.isArray(value)) {
            return {};
          }
          return value;
        }

        function asArray(value) {
          return Array.isArray(value) ? value : [];
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

        function getPath(payload, path, fallback = null) {
          if (!payload || typeof payload !== "object") return fallback;
          let current = payload;
          for (const key of asArray(path)) {
            if (!current || typeof current !== "object" || !(key in current)) {
              return fallback;
            }
            current = current[key];
          }
          return current;
        }

        function firstValue(values, fallback = null) {
          for (const item of asArray(values)) {
            if (hasValue(item)) return item;
          }
          return fallback;
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

        function buildLoginUrl(reason = "session_expired") {
          const next = `${window.location.pathname}${window.location.search}`;
          const params = new URLSearchParams();
          params.set("next", next);
          params.set("reason", reason || "session_expired");
          return `/auth/login?${params.toString()}`;
        }

        function redirectToLogin(reason = "session_expired") {
          const target = buildLoginUrl(reason);
          try {
            window.location.assign(target);
          } catch (error) {
            window.location.href = target;
          }
        }

        function applyInitialState() {
          rawLinkEl.href = buildResultUrl();
        }

        function createUiCorrelationId(prefix = "req") {
          const normalizedPrefix = String(prefix || "req").replace(/[^a-z0-9_-]/gi, "").toLowerCase() || "req";
          const randomChunk = Math.random().toString(36).slice(2, 10);
          return `${normalizedPrefix}-${Date.now().toString(36)}-${randomChunk}`;
        }

        function headersFromInputs(requestId = "") {
          const normalizedRequestId = String(requestId || createUiCorrelationId("req")).trim();
          const headers = { "Accept": "application/json" };
          if (normalizedRequestId) {
            headers["X-Request-Id"] = normalizedRequestId;
            headers["X-Correlation-Id"] = normalizedRequestId;
          }
          return headers;
        }

        const RESULT_LOAD_MAX_RETRIES = 8;
        const RESULT_LOAD_RETRY_DELAY_MS = 1500;

        function delayMs(durationMs) {
          const normalized = Number(durationMs);
          if (!Number.isFinite(normalized) || normalized <= 0) {
            return Promise.resolve();
          }
          return new Promise((resolve) => window.setTimeout(resolve, normalized));
        }

        function isTransientResultNotFound(response, parsed) {
          const statusCode = Number(response && response.status);
          if (statusCode !== 404) {
            return false;
          }

          const errorCode = String(parsed && parsed.error ? parsed.error : "")
            .trim()
            .toLowerCase();
          return errorCode === "not_found" || errorCode === "result_not_found";
        }

        function formatNumber(value, fractionDigits = 2) {
          const parsed = Number(value);
          if (!Number.isFinite(parsed)) return String(value || "");
          if (Number.isInteger(parsed)) return String(parsed);
          return parsed.toFixed(fractionDigits);
        }

        function formatConfidence(confidence) {
          const conf = asObject(confidence);
          if (!Object.keys(conf).length) return "—";
          const score = hasValue(conf.score) ? formatNumber(conf.score, 0) : "?";
          const max = hasValue(conf.max) ? formatNumber(conf.max, 0) : "100";
          const level = hasValue(conf.level) ? String(conf.level) : "unknown";
          return `${score}/${max} (${level})`;
        }

        function badgeClassByValue(value) {
          const normalized = String(value || "").trim().toLowerCase();
          if (["ok", "high", "green", "stable", "active", "succeeded", "pass"].includes(normalized)) return "good";
          if (["medium", "partial", "warn", "warning", "yellow", "attention", "pending"].includes(normalized)) return "warn";
          if (["low", "error", "failed", "critical", "red", "missing", "disabled", "review", "fail"].includes(normalized)) return "bad";
          return "info";
        }

        function renderCellValue(value) {
          if (!hasValue(value)) {
            return '<span class="cell-empty">—</span>';
          }
          if (typeof value === "boolean") {
            return value ? "Ja" : "Nein";
          }
          if (typeof value === "number") {
            return escapeHtml(formatNumber(value));
          }
          if (typeof value === "string") {
            return escapeHtml(value);
          }
          if (Array.isArray(value)) {
            const primitiveOnly = value.every((item) => ["string", "number", "boolean"].includes(typeof item));
            if (primitiveOnly) {
              return escapeHtml(value.map((item) => String(item)).join(", "));
            }
            const preview = prettyPrint(value.slice(0, 4));
            return `<code class="inline-json">${escapeHtml(preview)}</code>`;
          }
          const jsonText = prettyPrint(value);
          const compact = jsonText.length > 420 ? `${jsonText.slice(0, 420)} …` : jsonText;
          return `<code class="inline-json">${escapeHtml(compact)}</code>`;
        }

        function normalizeRows(rows) {
          return asArray(rows)
            .filter((entry) => entry && typeof entry === "object" && hasValue(entry.label))
            .filter((entry) => entry.allowEmpty || hasValue(entry.value))
            .map((entry) => ({
              label: String(entry.label),
              value: entry.value,
            }));
        }

        function renderKeyValueTable(rows, emptyText = "Keine Daten verfügbar.") {
          const normalizedRows = normalizeRows(rows);
          if (!normalizedRows.length) {
            return `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
          }
          const htmlRows = normalizedRows
            .map((row) => `<tr><th scope="row">${escapeHtml(row.label)}</th><td>${renderCellValue(row.value)}</td></tr>`)
            .join("");
          return `<div class="table-wrap"><table class="data-table"><tbody>${htmlRows}</tbody></table></div>`;
        }

        function renderMatrixTable(columns, rows, emptyText = "Keine Daten verfügbar.") {
          const normalizedColumns = asArray(columns).map((entry) => ({
            key: String(entry && entry.key ? entry.key : "").trim(),
            label: String(entry && entry.label ? entry.label : "").trim(),
          })).filter((entry) => entry.key && entry.label);

          const normalizedRows = asArray(rows).filter((row) => row && typeof row === "object");
          if (!normalizedColumns.length || !normalizedRows.length) {
            return `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
          }

          const headHtml = normalizedColumns.map((column) => `<th scope="col">${escapeHtml(column.label)}</th>`).join("");
          const bodyHtml = normalizedRows.map((row) => {
            const cells = normalizedColumns.map((column) => `<td>${renderCellValue(row[column.key])}</td>`).join("");
            return `<tr>${cells}</tr>`;
          }).join("");
          return `<div class="table-wrap"><table class="data-table"><thead><tr>${headHtml}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`;
        }

        function renderBadgeRow(badges) {
          const normalized = asArray(badges)
            .filter((badge) => badge && hasValue(badge.label) && hasValue(badge.value))
            .map((badge) => {
              const cls = badgeClassByValue(badge.value);
              return `<span class="badge ${cls}">${escapeHtml(String(badge.label))}: ${escapeHtml(String(badge.value))}</span>`;
            });

          if (!normalized.length) return "";
          return `<div class="badge-row">${normalized.join("")}</div>`;
        }

        function renderSections(targetEl, sections) {
          const safeSections = asArray(sections).filter((section) => section && typeof section === "object");
          if (!safeSections.length) {
            targetEl.innerHTML = '<div class="empty-state">Keine Daten verfügbar.</div>';
            return;
          }

          const html = safeSections.map((section) => {
            const title = hasValue(section.title) ? String(section.title) : "Bereich";
            const subtitle = hasValue(section.subtitle) ? String(section.subtitle) : "";
            const badges = renderBadgeRow(section.badges || []);

            const tableHtml = section.type === "matrix"
              ? renderMatrixTable(section.columns, section.rows, section.emptyText)
              : renderKeyValueTable(section.rows, section.emptyText);

            const subtitleHtml = subtitle ? `<p class="subtle">${escapeHtml(subtitle)}</p>` : "";

            return `
              <article class="data-section">
                <h3>${escapeHtml(title)}</h3>
                ${subtitleHtml}
                ${badges}
                ${tableHtml}
              </article>
            `;
          }).join("");

          targetEl.innerHTML = html;
        }

        function normalizeGroupedResult(groupedResult) {
          if (!groupedResult || typeof groupedResult !== "object") {
            return { ok: false, reason: "empty", raw: groupedResult };
          }

          const status = asObject(groupedResult.status);
          const data = asObject(groupedResult.data);
          const entity = asObject(data.entity);
          const modules = asObject(data.modules);
          const quality = asObject(status.quality);
          const sourceMeta = asObject(status.source_meta);
          const sourceHealth = asObject(status.source_health);

          const summaryCompact = asObject(firstValue([
            modules.summary_compact,
            getPath(modules, ["summary", "compact"]),
          ]));

          const confidence = asObject(firstValue([
            quality.confidence,
            status.confidence,
            summaryCompact.confidence,
          ]));

          const executiveSummary = asObject(firstValue([
            quality.executive_summary,
            status.executive_summary,
            summaryCompact.executive,
          ]));

          const intelligence = asObject(modules.intelligence);
          const suitability = asObject(firstValue([
            modules.suitability_light,
            summaryCompact.suitability_light,
          ]));

          return {
            ok: Boolean(Object.keys(status).length || Object.keys(data).length),
            raw: groupedResult,
            status,
            data,
            entity,
            modules,
            quality,
            sourceMeta,
            sourceHealth,
            summaryCompact,
            confidence,
            executiveSummary,
            intelligence,
            suitability,
          };
        }

        function renderUnknownFormat(targetEl, groupedResult, message) {
          targetEl.innerHTML = `
            <div class="empty-state">${escapeHtml(message)}</div>
            <pre>${escapeHtml(prettyPrint(groupedResult))}</pre>
          `;
        }

        function renderOverview(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.overview, groupedResult, "Unbekanntes Result-Format.");
            return;
          }

          const entity = normalized.entity;
          const modules = normalized.modules;
          const match = asObject(modules.match);
          const ids = asObject(entity.ids);
          const coords = asObject(entity.coordinates);

          const intelligenceRisk = asObject(firstValue([
            normalized.intelligence.executive_risk_summary,
            getPath(normalized.summaryCompact, ["intelligence", "executive_risk"]),
          ]));

          const sections = [
            {
              title: "Kernaussage",
              subtitle: "Schneller Überblick zu Qualität, Confidence und Gesamteindruck.",
              badges: [
                { label: "Confidence", value: normalized.confidence.level || "unknown" },
                { label: "Verdict", value: normalized.executiveSummary.verdict || "n/a" },
                { label: "Suitability", value: normalized.suitability.traffic_light || "n/a" },
              ],
              rows: [
                { label: "Suchanfrage", value: entity.query },
                { label: "Gematchte Adresse", value: entity.matched_address },
                { label: "Confidence", value: formatConfidence(normalized.confidence), allowEmpty: true },
                { label: "Executive Verdict", value: normalized.executiveSummary.verdict },
                { label: "Executive Hinweis", value: normalized.executiveSummary.recommendation || normalized.executiveSummary.summary },
                { label: "Suitability Score", value: normalized.suitability.score },
                { label: "Suitability Klasse", value: normalized.suitability.classification },
                { label: "Risikoampel", value: intelligenceRisk.traffic_light },
              ],
              emptyText: "Kernaussage aktuell nicht verfügbar.",
            },
            {
              title: "Match & Identifikatoren",
              subtitle: "Technische Kernwerte zur Adressauflösung.",
              rows: [
                { label: "Match Score", value: match.selected_score },
                { label: "Kandidaten", value: match.candidate_count },
                { label: "Feature-ID", value: ids.feature_id },
                { label: "EGID", value: ids.egid },
                { label: "EGRID", value: ids.egrid },
                { label: "Entity-ID", value: ids.entity_id },
                { label: "Koordinaten", value: coords },
              ],
              emptyText: "Keine Match-/ID-Daten vorhanden.",
            },
          ];

          renderSections(panelEls.overview, sections);
        }

        function renderLocation(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.location, groupedResult, "Lage-Daten nicht interpretierbar.");
            return;
          }

          const entity = normalized.entity;
          const modules = normalized.modules;
          const crossSource = asObject(modules.cross_source);
          const coords = asObject(entity.coordinates);
          const admin = asObject(entity.administrative);
          const plzLayer = asObject(crossSource.plz_layer);
          const adminBoundary = asObject(crossSource.admin_boundary);
          const elevation = asObject(crossSource.elevation);
          const osmReverse = asObject(crossSource.osm_reverse);
          const links = asObject(modules.links);

          const sections = [
            {
              title: "Koordinaten",
              rows: [
                { label: "Latitude", value: coords.lat },
                { label: "Longitude", value: coords.lon },
                { label: "LV95 Easting", value: coords.lv95_e },
                { label: "LV95 Northing", value: coords.lv95_n },
              ],
              emptyText: "Keine Koordinaten verfügbar.",
            },
            {
              title: "Administrative Einordnung",
              rows: [
                { label: "Gemeinde", value: admin.gemeinde },
                { label: "Gemeinde BFS", value: admin.gemeinde_bfs },
                { label: "Kanton", value: admin.kanton },
                { label: "Ort", value: admin.ort },
                { label: "PLZ", value: admin.plz_plz6 },
                { label: "Straße", value: admin.strasse_nummer },
              ],
              emptyText: "Keine administrativen Daten verfügbar.",
            },
            {
              title: "Cross-Source Lageprüfung",
              rows: [
                { label: "PLZ-Layer", value: plzLayer },
                { label: "Boundary", value: adminBoundary },
                { label: "Höhenlage", value: elevation.height_m || elevation },
                { label: "OSM Reverse", value: osmReverse },
                { label: "GeoAdmin Karte", value: links.map_geo_admin || normalized.summaryCompact.map },
              ],
              emptyText: "Keine Cross-Source Lageinformationen verfügbar.",
            },
          ];

          renderSections(panelEls.location, sections);
        }

        function renderDemographics(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.demographics, groupedResult, "Demografie-Daten nicht interpretierbar.");
            return;
          }

          const building = asObject(normalized.modules.building);
          const tenants = asObject(getPath(normalized.intelligence, ["tenants_businesses"]));
          const countsByCategory = asObject(tenants.counts_by_category);

          const categoryRows = Object.entries(countsByCategory).slice(0, 20).map(([key, value]) => ({
            metric: key,
            value,
          }));

          const sections = [
            {
              title: "Gebäudeprofil",
              subtitle: "Mangels klassischer Bevölkerungsdaten werden strukturelle Gebäude-Merkmale gezeigt.",
              rows: [
                { label: "Name", value: building.name },
                { label: "Baujahr", value: building.baujahr },
                { label: "Bauperiode", value: building.bauperiode },
                { label: "Wohnungen", value: building.wohnungen },
                { label: "Geschosse", value: building.geschosse },
                { label: "Fläche m²", value: building.flaeche_m2 },
                { label: "Gebäudecodes", value: building.codes },
              ],
              emptyText: "Keine demografisch interpretierbaren Gebäude-Merkmale vorhanden.",
            },
            {
              title: "Nutzungsindikatoren (POI)",
              type: "matrix",
              subtitle: "Annäherung über lokale Nutzungs- und Geschäftsindikatoren.",
              columns: [
                { key: "metric", label: "Kategorie" },
                { key: "value", label: "Anzahl" },
              ],
              rows: categoryRows,
              emptyText: "Keine Nutzungsindikatoren verfügbar.",
            },
          ];

          renderSections(panelEls.demographics, sections);
        }

        function renderSafety(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.safety, groupedResult, "Sicherheitsdaten nicht interpretierbar.");
            return;
          }

          const intelligence = normalized.intelligence;
          const incidents = asObject(intelligence.incidents_timeline);
          const consistency = asObject(intelligence.consistency_checks);
          const executiveRisk = asObject(intelligence.executive_risk_summary);
          const noiseRisk = asObject(intelligence.environment_noise_risk);

          const riskReasons = asArray(executiveRisk.reasons).slice(0, 8).map((entry, index) => ({
            metric: `Grund ${index + 1}`,
            value: entry,
          }));

          const checkRows = asArray(consistency.checks).slice(0, 12).map((check) => ({
            check: check.id || "check",
            result: check.result,
            severity: check.severity,
            confidence: check.confidence,
          }));

          const sections = [
            {
              title: "Executive Risk",
              badges: [
                { label: "Ampel", value: executiveRisk.traffic_light || "n/a" },
                { label: "Status", value: executiveRisk.status || "n/a" },
              ],
              rows: [
                { label: "Risk Score", value: executiveRisk.risk_score },
                { label: "Summary", value: executiveRisk.summary },
                { label: "Modus", value: executiveRisk.mode },
              ],
              emptyText: "Kein Executive-Risk verfügbar.",
            },
            {
              title: "Incidents & Konsistenz",
              rows: [
                { label: "Incidents Status", value: incidents.status },
                { label: "Events gesamt", value: asArray(incidents.events).length },
                { label: "Relevante Events", value: incidents.relevant_event_count },
                { label: "Konsistenz Overall", value: consistency.overall },
                { label: "Konsistenz Risk Score", value: consistency.risk_score },
                { label: "Konsistenz Counts", value: consistency.counts },
                { label: "Noise Risk", value: noiseRisk.level ? `${noiseRisk.level} (${noiseRisk.score})` : noiseRisk.score },
              ],
              emptyText: "Keine Incident-/Konsistenzdaten verfügbar.",
            },
            {
              title: "Risikotreiber",
              type: "matrix",
              columns: [
                { key: "metric", label: "Treiber" },
                { key: "value", label: "Detail" },
              ],
              rows: riskReasons,
              emptyText: "Keine Risikotreiber vorhanden.",
            },
            {
              title: "Konsistenzchecks (Auszug)",
              type: "matrix",
              columns: [
                { key: "check", label: "Check" },
                { key: "result", label: "Result" },
                { key: "severity", label: "Severity" },
                { key: "confidence", label: "Confidence" },
              ],
              rows: checkRows,
              emptyText: "Keine Konsistenzchecks vorhanden.",
            },
          ];

          renderSections(panelEls.safety, sections);
        }

        function renderHousing(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.housing, groupedResult, "Preis-/Mietdaten nicht interpretierbar.");
            return;
          }

          const modules = normalized.modules;
          const building = asObject(modules.building);
          const energy = asObject(modules.energy);
          const market = asObject(firstValue([modules.pricing, modules.market, modules.rent]));

          const sections = [
            {
              title: "Preis-/Mietdaten",
              subtitle: "Direkte Marktpreise liegen oft nicht im API-Payload. Fallback zeigt robuste Gebäudekennzahlen.",
              rows: [
                { label: "Preisindex", value: market.price_index },
                { label: "Mietindex", value: market.rent_index },
                { label: "Median-Miete", value: market.median_rent },
                { label: "Preisquelle", value: market.source },
              ],
              emptyText: "Keine direkten Preis-/Mietdaten vorhanden.",
            },
            {
              title: "Gebäude & Energie als Kostenindikator",
              rows: [
                { label: "Baujahr", value: building.baujahr },
                { label: "Wohnungen", value: building.wohnungen },
                { label: "Energie-Codes", value: energy.codes || energy.raw_codes },
                { label: "Heizungszusammenfassung", value: getPath(energy, ["decoded_summary", "heizung"]) },
                { label: "Warmwasser", value: getPath(energy, ["decoded_summary", "warmwasser"]) },
                { label: "Heating Layer", value: energy.heating_layer },
              ],
              emptyText: "Keine Gebäude-/Energieindikatoren verfügbar.",
            },
          ];

          renderSections(panelEls.housing, sections);
        }

        function renderEducation(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.education, groupedResult, "Bildungsdaten nicht interpretierbar.");
            return;
          }

          const environmentProfile = asObject(getPath(normalized.intelligence, ["environment_profile"]));
          const countsByDomain = asObject(getPath(environmentProfile, ["counts", "by_domain"]));
          const metrics = asObject(environmentProfile.metrics);
          const explainability = asObject(normalized.modules.explainability);

          const schoolFactors = asArray(getPath(explainability, ["base", "factors"], []))
            .concat(asArray(getPath(explainability, ["personalized", "factors"], [])))
            .filter((factor) => String(factor.key || "").toLowerCase().includes("school"))
            .slice(0, 8)
            .map((factor) => ({
              factor: factor.key,
              contribution: factor.contribution,
              reason: factor.reason,
            }));

          const sections = [
            {
              title: "Bildungsnahe Umfeldwerte",
              rows: [
                { label: "Domain education_family", value: countsByDomain.education_family },
                { label: "Family Support Score", value: metrics.family_support_score },
                { label: "Accessibility Score", value: metrics.accessibility_score },
                { label: "POI total", value: getPath(environmentProfile, ["counts", "poi_total"]) },
              ],
              emptyText: "Keine Bildungs-/Familienindikatoren vorhanden.",
            },
            {
              title: "Explainability-Faktoren Bildung",
              type: "matrix",
              columns: [
                { key: "factor", label: "Faktor" },
                { key: "contribution", label: "Contribution" },
                { key: "reason", label: "Begründung" },
              ],
              rows: schoolFactors,
              emptyText: "Keine bildungsbezogenen Explainability-Faktoren im Payload.",
            },
          ];

          renderSections(panelEls.education, sections);
        }

        function renderTransport(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.transport, groupedResult, "Verkehrsdaten nicht interpretierbar.");
            return;
          }

          const match = asObject(normalized.modules.match);
          const environmentProfile = asObject(getPath(normalized.intelligence, ["environment_profile"]));
          const countsByDomain = asObject(getPath(environmentProfile, ["counts", "by_domain"]));
          const metrics = asObject(environmentProfile.metrics);
          const model = asObject(environmentProfile.model);

          const sections = [
            {
              title: "Erreichbarkeit",
              badges: [
                { label: "Model", value: model.id || "n/a" },
                { label: "Status", value: environmentProfile.status || "n/a" },
              ],
              rows: [
                { label: "Transit-Domain", value: countsByDomain.transit },
                { label: "Accessibility Score", value: metrics.accessibility_score },
                { label: "Radius (m)", value: model.radius_m },
                { label: "Distance weighting", value: model.distance_weighting },
              ],
              emptyText: "Keine Verkehrsmetriken verfügbar.",
            },
            {
              title: "Adressauflösung / Match",
              rows: [
                { label: "Match Score", value: match.selected_score },
                { label: "Kandidaten", value: match.candidate_count },
                { label: "Resolution", value: match.resolution },
                { label: "Query parts", value: match.query_parts },
              ],
              emptyText: "Keine Match-/Resolutiondaten verfügbar.",
            },
          ];

          renderSections(panelEls.transport, sections);
        }

        function renderEnvironment(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.environment, groupedResult, "Umweltdaten nicht interpretierbar.");
            return;
          }

          const environmentProfile = asObject(getPath(normalized.intelligence, ["environment_profile"]));
          const noiseRisk = asObject(getPath(normalized.intelligence, ["environment_noise_risk"]));
          const metrics = asObject(environmentProfile.metrics);
          const countsByDomain = asObject(getPath(environmentProfile, ["counts", "by_domain"]));
          const counts = asObject(environmentProfile.counts);
          const crossSource = asObject(normalized.modules.cross_source);
          const elevation = asObject(crossSource.elevation);

          const noiseReasons = asArray(noiseRisk.reasons).slice(0, 8).map((entry, index) => ({
            metric: `Hinweis ${index + 1}`,
            value: entry,
          }));

          const sections = [
            {
              title: "Umfeldprofil",
              badges: [
                { label: "Status", value: environmentProfile.status || "n/a" },
                { label: "Overall", value: metrics.overall_score || "n/a" },
              ],
              rows: [
                { label: "Density Score", value: metrics.density_score },
                { label: "Diversity Score", value: metrics.diversity_score },
                { label: "Quietness Score", value: metrics.quietness_score },
                { label: "Leisure/Green Domain", value: countsByDomain.leisure_green },
                { label: "Nightlife Domain", value: countsByDomain.nightlife },
                { label: "POI Dichte / km²", value: counts.density_per_km2 },
              ],
              emptyText: "Keine Umfeldmetriken verfügbar.",
            },
            {
              title: "Lärm-/Aktivitätsrisiko",
              badges: [
                { label: "Level", value: noiseRisk.level || "n/a" },
                { label: "Ampel", value: noiseRisk.traffic_light || "n/a" },
              ],
              rows: [
                { label: "Noise Score", value: noiseRisk.score },
                { label: "Status", value: noiseRisk.status },
                { label: "Top Indicators", value: asArray(noiseRisk.indicators).slice(0, 4) },
                { label: "Höhenlage", value: elevation.height_m },
              ],
              emptyText: "Keine Noise-Risk-Daten verfügbar.",
            },
            {
              title: "Umwelt-Hinweise",
              type: "matrix",
              columns: [
                { key: "metric", label: "Hinweis" },
                { key: "value", label: "Detail" },
              ],
              rows: noiseReasons,
              emptyText: "Keine zusätzlichen Umwelt-Hinweise.",
            },
          ];

          renderSections(panelEls.environment, sections);
        }

        function renderSources(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.sources, groupedResult, "Quellen-/Methodikdaten nicht interpretierbar.");
            return;
          }

          const sourceHealth = asObject(normalized.sourceHealth);
          const sourceMeta = asObject(normalized.sourceMeta);
          const sourceAttribution = asObject(sourceMeta.source_attribution);
          const sourceClassification = asObject(sourceMeta.source_classification);
          const derivedFrom = asObject(firstValue([sourceMeta.derived_from, sourceMeta.field_provenance]));
          const bySource = asObject(normalized.data.by_source);

          const sourceRows = Object.entries(sourceHealth).map(([source, payload]) => {
            const meta = asObject(payload);
            return {
              source,
              status: meta.status,
              records: meta.records,
              optional: meta.optional,
            };
          });

          const attributionRows = Object.entries(sourceAttribution).map(([domain, sources]) => ({
            domain,
            sources,
          }));

          const derivedRows = Object.entries(derivedFrom).slice(0, 25).map(([fieldPath, meta]) => ({
            field: fieldPath,
            primary_source: asObject(meta).primary_source,
            present: asObject(meta).present,
            authority: asObject(meta).authority,
          }));

          const bySourceRows = Object.entries(bySource).slice(0, 20).map(([source, payload]) => ({
            source,
            groups: Object.keys(asObject(asObject(payload).data)).join(", ") || "—",
            detail: asObject(payload).data,
          }));

          const sections = [
            {
              title: "Source Health",
              type: "matrix",
              columns: [
                { key: "source", label: "Quelle" },
                { key: "status", label: "Status" },
                { key: "records", label: "Records" },
                { key: "optional", label: "Optional" },
              ],
              rows: sourceRows,
              emptyText: "Keine Source-Health-Daten vorhanden.",
            },
            {
              title: "Source Attribution",
              type: "matrix",
              columns: [
                { key: "domain", label: "Domain" },
                { key: "sources", label: "Quellen" },
              ],
              rows: attributionRows,
              emptyText: "Keine Source-Attribution vorhanden.",
            },
            {
              title: "Derived-from / Feldprovenienz",
              type: "matrix",
              columns: [
                { key: "field", label: "Feld" },
                { key: "primary_source", label: "Primary Source" },
                { key: "present", label: "Present" },
                { key: "authority", label: "Authority" },
              ],
              rows: derivedRows,
              emptyText: "Keine Feldprovenienz verfügbar.",
            },
            {
              title: "by_source Projektion",
              type: "matrix",
              columns: [
                { key: "source", label: "Quelle" },
                { key: "groups", label: "Daten-Gruppen" },
                { key: "detail", label: "Detail" },
              ],
              rows: bySourceRows,
              emptyText: "Keine by_source-Daten verfügbar.",
            },
            {
              title: "Source Classification (raw)",
              rows: [
                { label: "source_classification", value: sourceClassification },
              ],
              emptyText: "Keine Source-Classification vorhanden.",
            },
          ];

          renderSections(panelEls.sources, sections);
        }

        function renderDerived(groupedResult) {
          const normalized = normalizeGroupedResult(groupedResult);
          if (!normalized.ok) {
            renderUnknownFormat(panelEls.derived, groupedResult, "Derived-Daten nicht interpretierbar.");
            return;
          }

          const modules = normalized.modules;
          const suitability = asObject(normalized.suitability);
          const explainability = asObject(modules.explainability);
          const confidenceWarnings = asArray(normalized.confidence.warnings);

          const topFactors = asArray(suitability.top_factors).slice(0, 12).map((factor) => ({
            key: factor.key,
            name: factor.name,
            contribution: factor.contribution,
          }));

          const explainabilityRows = asArray(getPath(explainability, ["base", "factors"], []))
            .concat(asArray(getPath(explainability, ["personalized", "factors"], [])))
            .slice(0, 20)
            .map((factor) => ({
              key: factor.key,
              direction: factor.direction,
              weight: factor.weight,
              contribution: factor.contribution,
              reason: factor.reason,
            }));

          const warningRows = confidenceWarnings.map((entry, index) => ({
            metric: `Warnung ${index + 1}`,
            value: entry,
          }));

          const sections = [
            {
              title: "Suitability (abgeleitet)",
              rows: [
                { label: "Status", value: suitability.status },
                { label: "Score", value: suitability.score },
                { label: "Traffic Light", value: suitability.traffic_light },
                { label: "Classification", value: suitability.classification },
              ],
              emptyText: "Keine Suitability-Daten vorhanden.",
            },
            {
              title: "Top-Faktoren",
              type: "matrix",
              columns: [
                { key: "key", label: "Key" },
                { key: "name", label: "Name" },
                { key: "contribution", label: "Contribution" },
              ],
              rows: topFactors,
              emptyText: "Keine Top-Faktoren verfügbar.",
            },
            {
              title: "Explainability Faktoren",
              type: "matrix",
              columns: [
                { key: "key", label: "Faktor" },
                { key: "direction", label: "Richtung" },
                { key: "weight", label: "Gewicht" },
                { key: "contribution", label: "Contribution" },
                { key: "reason", label: "Reason" },
              ],
              rows: explainabilityRows,
              emptyText: "Keine Explainability-Faktoren im Payload.",
            },
            {
              title: "Confidence-Warnungen",
              type: "matrix",
              columns: [
                { key: "metric", label: "Typ" },
                { key: "value", label: "Hinweis" },
              ],
              rows: warningRows,
              emptyText: "Keine Confidence-Warnungen vorhanden.",
            },
          ];

          renderSections(panelEls.derived, sections);
        }

        function renderAllTabs(groupedResult) {
          renderSafe(renderOverview, panelEls.overview, groupedResult, "Übersicht konnte nicht gerendert werden.");
          renderSafe(renderLocation, panelEls.location, groupedResult, "Lage konnte nicht gerendert werden.");
          renderSafe(renderDemographics, panelEls.demographics, groupedResult, "Demografie konnte nicht gerendert werden.");
          renderSafe(renderSafety, panelEls.safety, groupedResult, "Sicherheit konnte nicht gerendert werden.");
          renderSafe(renderHousing, panelEls.housing, groupedResult, "Preise/Miete konnten nicht gerendert werden.");
          renderSafe(renderEducation, panelEls.education, groupedResult, "Bildung konnte nicht gerendert werden.");
          renderSafe(renderTransport, panelEls.transport, groupedResult, "Verkehr konnte nicht gerendert werden.");
          renderSafe(renderEnvironment, panelEls.environment, groupedResult, "Umwelt konnte nicht gerendert werden.");
          renderSafe(renderSources, panelEls.sources, groupedResult, "Quellen/Methodik konnten nicht gerendert werden.");
          renderSafe(renderDerived, panelEls.derived, groupedResult, "Derived konnte nicht gerendert werden.");
        }

        function renderSafe(renderer, targetEl, groupedResult, fallbackLabel) {
          try {
            renderer(groupedResult);
          } catch (error) {
            const message = error instanceof Error ? error.message : "render_error";
            targetEl.innerHTML = `
              <div class="empty-state">${escapeHtml(fallbackLabel)}</div>
              <pre>${escapeHtml(prettyPrint({ error: "render_error", message, result: groupedResult || null }))}</pre>
            `;
          }
        }

        function setActiveTab(tabKey, options = {}) {
          const key = TAB_SEQUENCE.includes(tabKey) ? tabKey : "overview";
          const shouldFocus = Boolean(options.focus);

          TAB_SEQUENCE.forEach((entry) => {
            const panel = document.getElementById(`tab-${entry}`);
            const button = document.getElementById(`tab-btn-${entry}`);
            const isActive = entry === key;
            if (panel) {
              panel.hidden = !isActive;
            }
            if (button) {
              button.setAttribute("aria-selected", isActive ? "true" : "false");
              button.setAttribute("tabindex", isActive ? "0" : "-1");
            }
          });

          if (shouldFocus) {
            const activeButton = document.getElementById(`tab-btn-${key}`);
            if (activeButton && typeof activeButton.focus === "function") {
              activeButton.focus();
            }
          }
        }

        function focusTabByOffset(currentKey, offset) {
          const currentIndex = TAB_SEQUENCE.indexOf(currentKey);
          if (currentIndex < 0) {
            setActiveTab("overview", { focus: true });
            return;
          }
          const nextIndex = (currentIndex + offset + TAB_SEQUENCE.length) % TAB_SEQUENCE.length;
          setActiveTab(TAB_SEQUENCE[nextIndex], { focus: true });
        }

        function focusBoundaryTab(which) {
          if (which === "first") {
            setActiveTab(TAB_SEQUENCE[0], { focus: true });
            return;
          }
          setActiveTab(TAB_SEQUENCE[TAB_SEQUENCE.length - 1], { focus: true });
        }

        function onTabKeyDown(event) {
          const target = event.currentTarget;
          const tabKey = String(target && target.getAttribute("data-tab") || "").trim();
          if (!tabKey) return;

          const key = event.key;
          if (key === "ArrowRight") {
            event.preventDefault();
            focusTabByOffset(tabKey, 1);
            return;
          }
          if (key === "ArrowLeft") {
            event.preventDefault();
            focusTabByOffset(tabKey, -1);
            return;
          }
          if (key === "Home") {
            event.preventDefault();
            focusBoundaryTab("first");
            return;
          }
          if (key === "End") {
            event.preventDefault();
            focusBoundaryTab("last");
            return;
          }
          if (key === "Enter" || key === " ") {
            event.preventDefault();
            setActiveTab(tabKey, { focus: true });
          }
        }

        async function loadResult() {
          setError("");
          setStatus("loading");
          loadBtn.disabled = true;

          const url = buildResultUrl();
          rawLinkEl.href = url;
          const requestId = createUiCorrelationId("req");
          const maxRetries = normalizedViewMode() === "latest" ? RESULT_LOAD_MAX_RETRIES : 0;

          let response;
          let parsed;
          for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
            try {
              response = await fetch(url, { method: "GET", headers: headersFromInputs(requestId), credentials: "include" });
              parsed = await response.json();
            } catch (error) {
              setStatus("error");
              setError(error instanceof Error ? error.message : "network_error");
              payloadEl.textContent = prettyPrint({ ok: false, error: "network_error" });
              loadBtn.disabled = false;
              return;
            }

            payloadEl.textContent = prettyPrint(parsed);

            if (response.ok && parsed && parsed.ok) {
              break;
            }

            const shouldRetry = attempt < maxRetries && isTransientResultNotFound(response, parsed);
            if (!shouldRetry) {
              break;
            }

            const nextAttempt = attempt + 1;
            setStatus(`retrying(${nextAttempt}/${maxRetries})`);
            await delayMs(RESULT_LOAD_RETRY_DELAY_MS);
          }

          if (!response || !response.ok || !parsed || !parsed.ok) {
            setStatus("error");
            if (response && response.status === 401) {
              setError("Session ungültig oder abgelaufen — weiter zur Anmeldung …");
              window.setTimeout(() => redirectToLogin("session_expired"), 250);
            } else {
              const errCode = parsed && parsed.error ? parsed.error : `http_${response ? response.status : 0}`;
              const errMsg = parsed && parsed.message ? parsed.message : "Unbekannter Fehler";
              setError(`${errCode}: ${errMsg}`);
            }
            loadBtn.disabled = false;
            return;
          }

          setStatus("success");
          renderAllTabs(parsed.result);
          loadBtn.disabled = false;
        }

        document.querySelectorAll(".tab-btn").forEach((btn) => {
          btn.addEventListener("click", () => {
            const key = btn.getAttribute("data-tab");
            setActiveTab(String(key || "overview"), { focus: false });
          });
          btn.addEventListener("keydown", onTabKeyDown);
        });

        viewModeEl.addEventListener("change", () => {
          rawLinkEl.href = buildResultUrl();
        });

        loadBtn.addEventListener("click", () => {
          void loadResult();
        });

        applyInitialState();
        setActiveTab("overview", { focus: false });
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
