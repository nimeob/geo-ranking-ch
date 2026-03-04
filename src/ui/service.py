#!/usr/bin/env python3
"""Minimaler UI-Webservice für BL-31.2.

Stellt das GUI-MVP (`/` und `/gui`) als eigenständigen HTTP-Service bereit,
liefert einen separaten Healthcheck-Endpunkt (`/healthz`) und bietet zwei
Async-freundliche Deep-Link Pages:

- Result-Permalink-Page (`/results/<result_id>`), die Result-Daten über
  `GET /analyze/results/<result_id>` lädt.
- Job-Status/Notification-Page (`/jobs/<job_id>`), die Job-Status + In-App
  Notifications über `GET /analyze/jobs/<job_id>` und
  `GET /analyze/jobs/<job_id>/notifications` lädt.

Hinweis: Die Result-Page ist bewusst minimal (API-first) und soll vor allem
Deep-Link-/Sharing-Workflows für Async-Results abdecken.
"""

from __future__ import annotations

import json
import os
import posixpath
import re
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

from src.shared.gui_mvp import render_gui_mvp_html
from src.shared.ui_pages import build_history_page_html, build_result_tabs_page_html

_RESULT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")

_RESULT_PAGE_TEMPLATE = """<!doctype html>
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
      header a {
        text-decoration: none;
        color: var(--primary);
        border: 1px solid var(--border);
        padding: 0.35rem 0.55rem;
        border-radius: 0.5rem;
        font-size: 0.86rem;
        background: #f9fbff;
      }
      main {
        padding: 1rem 1.25rem 1.5rem;
        display: grid;
        gap: 1rem;
        max-width: 980px;
      }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.85rem;
        padding: 1rem;
      }
      .card h2 { margin: 0 0 0.75rem; font-size: 1rem; }
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
      .grid-2 {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: 1fr 1fr;
      }
      @media (max-width: 720px) {
        .grid-2 { grid-template-columns: 1fr; }
      }
      .meta { font-size: 0.84rem; color: var(--muted); }
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
        max-height: 32rem;
        overflow: auto;
        background: #f8faff;
        border: 1px solid var(--border);
        border-radius: 0.65rem;
        padding: 0.75rem;
      }
      code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>Result-Permalink</h1>
        <p>result_id: <code id="result-id" data-result-id="__RESULT_ID__">__RESULT_ID__</code> · Version __APP_VERSION__</p>
      </div>
      <div>
        <a href="/gui">GUI öffnen</a>
      </div>
    </header>

    <main>
      <section class="card">
        <h2>Loader</h2>
        <p class="meta">Die Seite lädt JSON via <code>GET /analyze/results/&lt;result_id&gt;</code>. Optional kann ein Bearer-Token gesetzt werden (z. B. für geschützte Deployments).</p>
        <div class="grid-2">
          <label>
            API Token (optional)
            <input id="api-token" type="password" placeholder="Bearer-Token" autocomplete="off" />
          </label>
          <label>
            view
            <select id="view-mode">
              <option value="latest">latest</option>
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
        <h2>Response (JSON)</h2>
        <pre id="payload">{
  "hint": "Loading..."
}</pre>
      </section>

      <script>
        const RESULT_ID = __RESULT_ID_JSON__;
        const RESULTS_ENDPOINT_BASE = __RESULTS_ENDPOINT_BASE_JSON__;
        const TOKEN_STORAGE_KEY = "geo-ranking-ui-api-token";

        const tokenEl = document.getElementById("api-token");
        const viewModeEl = document.getElementById("view-mode");
        const statusEl = document.getElementById("status");
        const loadBtn = document.getElementById("load-btn");
        const payloadEl = document.getElementById("payload");
        const errorEl = document.getElementById("error");
        const rawLinkEl = document.getElementById("raw-link");

        function prettyPrint(value) {
          try {
            return JSON.stringify(value, null, 2);
          } catch (error) {
            return String(value);
          }
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

        async function loadResult() {
          setError("");
          setStatus("loading");
          loadBtn.disabled = true;

          const url = buildResultUrl();
          rawLinkEl.href = url;

          const token = String(tokenEl.value || "").trim();
          try {
            if (typeof window !== "undefined" && window.sessionStorage) {
              if (token) {
                window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
              } else {
                window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
              }
            }
          } catch (error) {
            // ignore
          }

          const headers = { "Accept": "application/json" };
          if (token) {
            headers["Authorization"] = `Bearer ${token}`;
          }

          let response;
          let parsed;
          try {
            response = await fetch(url, { method: "GET", headers });
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
          loadBtn.disabled = false;
        }

        function applyInitialStateFromUrl() {
          try {
            const url = new URL(window.location.href);
            const view = String(url.searchParams.get("view") || "").trim().toLowerCase();
            if (view === "requested") {
              viewModeEl.value = "requested";
            }
          } catch (error) {
            // ignore
          }

          try {
            if (typeof window !== "undefined" && window.sessionStorage) {
              const token = String(window.sessionStorage.getItem(TOKEN_STORAGE_KEY) || "").trim();
              if (token) {
                tokenEl.value = token;
              }
            }
          } catch (error) {
            // ignore
          }

          rawLinkEl.href = buildResultUrl();
        }

        loadBtn.addEventListener("click", () => {
          void loadResult();
        });

        viewModeEl.addEventListener("change", () => {
          rawLinkEl.href = buildResultUrl();
        });

        applyInitialStateFromUrl();
        void loadResult();
      </script>
    </main>
  </body>
</html>
"""


_JOB_PAGE_TEMPLATE = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>geo-ranking.ch — Job __JOB_ID__</title>
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
        --success: #1f8a3b;
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
      header a {
        text-decoration: none;
        color: var(--primary);
        border: 1px solid var(--border);
        padding: 0.35rem 0.55rem;
        border-radius: 0.5rem;
        font-size: 0.86rem;
        background: #f9fbff;
      }
      main {
        padding: 1rem 1.25rem 1.5rem;
        display: grid;
        gap: 1rem;
        max-width: 980px;
      }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.85rem;
        padding: 1rem;
      }
      .card h2 { margin: 0 0 0.75rem; font-size: 1rem; }
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
        background: #ffffff;
        color: var(--ink);
        border-color: var(--border);
      }
      button[disabled] { opacity: 0.65; cursor: not-allowed; }
      .grid-2 {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: 1fr 1fr;
      }
      @media (max-width: 720px) {
        .grid-2 { grid-template-columns: 1fr; }
      }
      .meta { font-size: 0.84rem; color: var(--muted); }
      .error {
        border: 1px solid rgba(185, 58, 47, 0.35);
        background: rgba(185, 58, 47, 0.08);
        padding: 0.75rem;
        border-radius: 0.65rem;
        color: var(--danger);
        white-space: pre-wrap;
      }
      .toast {
        margin-top: 0.85rem;
        padding: 0.75rem;
        border-radius: 0.65rem;
        border: 1px solid rgba(31, 138, 59, 0.35);
        background: rgba(31, 138, 59, 0.08);
        color: var(--success);
        display: grid;
        gap: 0.35rem;
      }
      .toast.error {
        border-color: rgba(185, 58, 47, 0.35);
        background: rgba(185, 58, 47, 0.08);
        color: var(--danger);
      }
      pre {
        margin: 0;
        max-height: 32rem;
        overflow: auto;
        background: #f8faff;
        border: 1px solid var(--border);
        border-radius: 0.65rem;
        padding: 0.75rem;
      }
      code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
      .links {
        display: flex;
        gap: 0.65rem;
        flex-wrap: wrap;
        margin-top: 0.85rem;
        align-items: center;
      }
      .links a {
        color: var(--primary);
        text-decoration: none;
        border: 1px solid var(--border);
        background: #f9fbff;
        padding: 0.28rem 0.5rem;
        border-radius: 0.45rem;
        font-size: 0.82rem;
      }
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>Async Job</h1>
        <p>job_id: <code id="job-id" data-job-id="__JOB_ID__">__JOB_ID__</code> · Version __APP_VERSION__</p>
      </div>
      <div>
        <a href="/gui">GUI öffnen</a>
      </div>
    </header>

    <main>
      <section class="card">
        <h2>Loader</h2>
        <p class="meta">Die Seite lädt JSON via <code>GET /analyze/jobs/&lt;job_id&gt;</code> und <code>GET /analyze/jobs/&lt;job_id&gt;/notifications</code>. Optional kann ein Bearer-Token gesetzt werden (z. B. für geschützte Deployments). Tenant-Scope via <code>X-Org-Id</code>.</p>
        <div class="grid-2">
          <label>
            API Token (optional)
            <input id="api-token" type="password" placeholder="Bearer-Token" autocomplete="off" />
          </label>
          <label>
            X-Org-Id (Tenant)
            <input id="org-id" type="text" placeholder="default-org" />
          </label>
        </div>
        <div class="links">
          <button id="refresh-btn" type="button">Refresh</button>
          <button id="toggle-polling-btn" class="secondary" type="button">Polling: on</button>
          <a id="raw-job-link" href="#" target="_blank" rel="noopener noreferrer">Raw Job JSON</a>
          <a id="raw-notifications-link" href="#" target="_blank" rel="noopener noreferrer">Raw Notifications JSON</a>
          <a id="result-page-link" href="#" target="_self" rel="noopener noreferrer" hidden>Result-Page öffnen</a>
          <span id="status" class="meta">Status: idle</span>
        </div>
        <div id="toast" class="toast" hidden></div>
        <div id="error" class="error" hidden></div>
      </section>

      <section class="card">
        <h2>Job Payload (JSON)</h2>
        <pre id="job-payload">{\n  \"hint\": \"Loading...\"\n}</pre>
      </section>

      <section class="card">
        <h2>Notifications Payload (JSON)</h2>
        <pre id="notifications-payload">{\n  \"hint\": \"Loading...\"\n}</pre>
      </section>

      <script>
        const JOB_ID = __JOB_ID_JSON__;
        const JOBS_ENDPOINT_BASE = __JOBS_ENDPOINT_BASE_JSON__;
        const RESULTS_PAGE_BASE = "/results";

        const TOKEN_STORAGE_KEY = "geo-ranking-ui-api-token";
        const ORG_STORAGE_KEY = "geo-ranking-ui-org-id";

        const tokenEl = document.getElementById("api-token");
        const orgEl = document.getElementById("org-id");
        const statusEl = document.getElementById("status");
        const refreshBtn = document.getElementById("refresh-btn");
        const togglePollingBtn = document.getElementById("toggle-polling-btn");
        const jobPayloadEl = document.getElementById("job-payload");
        const notificationsPayloadEl = document.getElementById("notifications-payload");
        const errorEl = document.getElementById("error");
        const toastEl = document.getElementById("toast");
        const rawJobLinkEl = document.getElementById("raw-job-link");
        const rawNotificationsLinkEl = document.getElementById("raw-notifications-link");
        const resultPageLinkEl = document.getElementById("result-page-link");

        let pollingActive = true;
        let pollingDelayMs = 1000;
        let lastNotificationId = "";

        function prettyPrint(value) {
          try {
            return JSON.stringify(value, null, 2);
          } catch (error) {
            return String(value);
          }
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

        function setToast(message, kind = "success") {
          const text = String(message || "").trim();
          if (!text) {
            toastEl.hidden = true;
            toastEl.textContent = "";
            toastEl.classList.remove("error");
            return;
          }
          toastEl.hidden = false;
          toastEl.textContent = text;
          if (kind === "error") {
            toastEl.classList.add("error");
          } else {
            toastEl.classList.remove("error");
          }
        }

        function buildJobUrl() {
          const encodedId = encodeURIComponent(JOB_ID);
          return `${JOBS_ENDPOINT_BASE}/${encodedId}`;
        }

        function buildNotificationsUrl() {
          const encodedId = encodeURIComponent(JOB_ID);
          return `${JOBS_ENDPOINT_BASE}/${encodedId}/notifications?channel=in_app&limit=20`;
        }

        function headersFromInputs() {
          const headers = { "Accept": "application/json" };
          const token = String(tokenEl.value || "").trim();
          if (token) {
            headers["Authorization"] = `Bearer ${token}`;
          }
          const orgId = String(orgEl.value || "").trim();
          if (orgId) {
            headers["X-Org-Id"] = orgId;
          }
          return headers;
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
          if (!String(orgEl.value || "").trim()) {
            orgEl.value = "default-org";
          }

          rawJobLinkEl.href = buildJobUrl();
          rawNotificationsLinkEl.href = buildNotificationsUrl();
        }

        function isTerminalStatus(status) {
          return status === "completed" || status === "failed" || status === "canceled";
        }

        async function fetchJson(url) {
          const headers = headersFromInputs();
          let response;
          try {
            response = await fetch(url, { method: "GET", headers });
          } catch (error) {
            throw new Error(error instanceof Error ? error.message : "network_error");
          }

          let parsed;
          try {
            parsed = await response.json();
          } catch (error) {
            throw new Error(`invalid_json (http_${response.status})`);
          }

          if (!response.ok || !parsed || !parsed.ok) {
            if (response.status === 401) {
              const hasToken = Boolean(headersFromInputs()["Authorization"]);
              throw new Error(hasToken ? "Authorization fehlgeschlagen — Token ungültig oder abgelaufen" : "Bitte Bearer-Token setzen — API erfordert Authentifizierung");
            }
            const errCode = parsed && parsed.error ? parsed.error : `http_${response.status}`;
            const errMsg = parsed && parsed.message ? parsed.message : "Unbekannter Fehler";
            throw new Error(`${errCode}: ${errMsg}`);
          }

          return parsed;
        }

        async function refreshOnce() {
          setError("");
          persistInputs();

          const jobUrl = buildJobUrl();
          const notificationsUrl = buildNotificationsUrl();
          rawJobLinkEl.href = jobUrl;
          rawNotificationsLinkEl.href = notificationsUrl;

          setStatus("loading");
          refreshBtn.disabled = true;

          let jobPayload;
          let notificationsPayload;

          try {
            jobPayload = await fetchJson(jobUrl);
          } catch (error) {
            setStatus("error");
            setError(error instanceof Error ? error.message : String(error));
            refreshBtn.disabled = false;
            return { ok: false };
          }

          try {
            notificationsPayload = await fetchJson(notificationsUrl);
          } catch (error) {
            setStatus("error");
            setError(error instanceof Error ? error.message : String(error));
            refreshBtn.disabled = false;
            jobPayloadEl.textContent = prettyPrint(jobPayload);
            return { ok: false };
          }

          jobPayloadEl.textContent = prettyPrint(jobPayload);
          notificationsPayloadEl.textContent = prettyPrint(notificationsPayload);

          const job = (jobPayload && jobPayload.job) ? jobPayload.job : {};
          const status = String(job.status || "").trim().toLowerCase();
          const resultId = String(job.result_id || "").trim();
          const notifications = Array.isArray(notificationsPayload.notifications) ? notificationsPayload.notifications : [];

          if (resultId) {
            resultPageLinkEl.hidden = false;
            resultPageLinkEl.href = `${RESULTS_PAGE_BASE}/${encodeURIComponent(resultId)}`;
          } else {
            resultPageLinkEl.hidden = true;
            resultPageLinkEl.href = "#";
          }

          let toastMessage = "";
          let toastKind = "success";

          if (notifications.length) {
            const first = notifications[0] || {};
            const templateKey = String(first.template_key || "").trim();
            const notificationId = String(first.notification_id || "").trim();
            const payload = first.payload_json && typeof first.payload_json === "object" ? first.payload_json : {};
            const finishedAt = String(payload.finished_at || "").trim();

            if (notificationId && notificationId !== lastNotificationId) {
              lastNotificationId = notificationId;
            }

            if (templateKey === "async.job.failed") {
              toastKind = "error";
              const errCode = String(payload.error_code || "").trim();
              toastMessage = `Job failed${errCode ? ` (${errCode})` : ""}${finishedAt ? ` · ${finishedAt}` : ""}`;
            } else if (templateKey === "async.job.completed") {
              toastMessage = `Job completed${finishedAt ? ` · ${finishedAt}` : ""}`;
            } else if (templateKey) {
              toastMessage = `Notification: ${templateKey}`;
            }
          }

          if (toastMessage) {
            setToast(toastMessage, toastKind);
          }

          if (isTerminalStatus(status) && notifications.length) {
            setStatus(`${status} (terminal)`);
            refreshBtn.disabled = false;
            return { ok: true, terminal: true };
          }

          setStatus(status || "ok");
          refreshBtn.disabled = false;
          return { ok: true, terminal: false };
        }

        async function pollLoop() {
          if (!pollingActive) return;
          const result = await refreshOnce();
          if (result && result.terminal) {
            pollingActive = false;
            togglePollingBtn.textContent = "Polling: off";
            return;
          }
          pollingDelayMs = Math.min(10000, Math.round(pollingDelayMs * 1.35));
          window.setTimeout(() => { void pollLoop(); }, pollingDelayMs);
        }

        refreshBtn.addEventListener("click", () => {
          pollingDelayMs = 1000;
          void refreshOnce();
        });

        togglePollingBtn.addEventListener("click", () => {
          pollingActive = !pollingActive;
          togglePollingBtn.textContent = pollingActive ? "Polling: on" : "Polling: off";
          if (pollingActive) {
            pollingDelayMs = 1000;
            void pollLoop();
          }
        });

        applyInitialState();
        void pollLoop();
      </script>
    </main>
  </body>
</html>
"""


_JOBS_LIST_PAGE_TEMPLATE = """<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>geo-ranking.ch — Jobs (dev)</title>
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
      header a {
        text-decoration: none;
        color: var(--primary);
        border: 1px solid var(--border);
        padding: 0.35rem 0.55rem;
        border-radius: 0.5rem;
        font-size: 0.86rem;
        background: #f9fbff;
      }
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
      button.danger {
        background: #fff;
        color: var(--danger);
        border-color: rgba(185, 58, 47, 0.35);
      }
      button[disabled] { opacity: 0.65; cursor: not-allowed; }
      .grid-3 {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: 1fr 1fr 1fr;
        align-items: end;
      }
      @media (max-width: 860px) {
        .grid-3 { grid-template-columns: 1fr; }
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
      }
      th, td {
        text-align: left;
        border-bottom: 1px solid var(--border);
        padding: 0.55rem 0.5rem;
        vertical-align: top;
      }
      th { color: var(--muted); font-weight: 600; font-size: 0.82rem; }
      td code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
      .row-actions {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        align-items: center;
      }
      .row-actions a {
        color: var(--primary);
        text-decoration: none;
        border: 1px solid var(--border);
        background: #f9fbff;
        padding: 0.25rem 0.45rem;
        border-radius: 0.45rem;
        font-size: 0.82rem;
      }
      .empty {
        padding: 0.75rem;
        border-radius: 0.65rem;
        border: 1px dashed var(--border);
        background: #f7f9fc;
      }
    </style>
  </head>
  <body>
    <header>
      <div>
        <h1>Jobs (dev)</h1>
        <p>Version __APP_VERSION__ · Liste basiert auf LocalStorage (Browser)</p>
      </div>
      <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
        <a href="/gui">GUI öffnen</a>
        <a href="/history">History</a>
      </div>
    </header>

    <main>
      <section class="card">
        <h2>Controls</h2>
        <p class="meta">Filter/Query werden als URL-Query-Params gespeichert (sharebar). Job-IDs werden lokal gespeichert.</p>
        <div class="grid-3">
          <label>
            Status
            <select id="jobs-status" aria-label="Filter nach Job-Status">
              <option value="all">all</option>
              <option value="queued">queued</option>
              <option value="running">running</option>
              <option value="partial">partial</option>
              <option value="succeeded">succeeded</option>
              <option value="failed">failed</option>
              <option value="canceled">canceled</option>
            </select>
          </label>
          <label>
            Suche (job_id)
            <input id="jobs-q" type="text" placeholder="job-123" autocomplete="off" />
          </label>
          <label>
            Add job_id
            <div style="display:flex; gap:0.5rem;">
              <input id="jobs-add-id" type="text" placeholder="job-123" autocomplete="off" />
              <button id="jobs-add-btn" type="button">Add</button>
            </div>
          </label>
        </div>

        <div class="grid-3" style="margin-top: 0.75rem;">
          <label>
            API Token (optional)
            <input id="api-token" type="password" placeholder="Bearer-Token" autocomplete="off" />
          </label>
          <label>
            X-Org-Id (Tenant)
            <input id="org-id" type="text" placeholder="default-org" />
          </label>
          <div style="display:flex; gap:0.5rem; flex-wrap:wrap; align-items:end;">
            <button id="jobs-refresh" type="button" class="secondary">Refresh</button>
            <button id="jobs-clear" type="button" class="danger">Liste leeren</button>
            <span id="jobs-meta" class="meta">—</span>
          </div>
        </div>
      </section>

      <section class="card">
        <h2>Job-Liste</h2>
        <div style="overflow:auto;">
          <table aria-label="Job-Liste">
            <thead>
              <tr>
                <th>job_id</th>
                <th>status</th>
                <th>progress</th>
                <th>updated</th>
                <th>links</th>
              </tr>
            </thead>
            <tbody id="jobs-body">
              <tr><td colspan="5"><div class="empty">Noch keine Jobs gespeichert. Tipp: starte einen Async-Analyze in /gui oder füge oben eine job_id hinzu.</div></td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <script>
        const JOBS_ENDPOINT_BASE = __JOBS_ENDPOINT_BASE_JSON__;
        const TOKEN_STORAGE_KEY = "geo-ranking-ui-api-token";
        const ORG_STORAGE_KEY = "geo-ranking-ui-org-id";
        const JOB_IDS_STORAGE_KEY = "geo-ranking-ui-job-ids";

        const statusEl = document.getElementById("jobs-status");
        const qEl = document.getElementById("jobs-q");
        const addIdEl = document.getElementById("jobs-add-id");
        const addBtn = document.getElementById("jobs-add-btn");
        const refreshBtn = document.getElementById("jobs-refresh");
        const clearBtn = document.getElementById("jobs-clear");
        const bodyEl = document.getElementById("jobs-body");
        const metaEl = document.getElementById("jobs-meta");

        const tokenEl = document.getElementById("api-token");
        const orgEl = document.getElementById("org-id");

        const state = {
          ids: [],
          status: "all",
          q: "",
          jobs: {},
          phase: "idle",
        };

        function canonicalJobStatus(value) {
          const normalized = String(value || "").trim().toLowerCase();
          if (!normalized) return "";
          if (normalized === "completed" || normalized === "success") return "succeeded";
          if (normalized === "cancelled") return "canceled";
          return normalized;
        }

        function normalizeStatus(value) {
          const normalized = canonicalJobStatus(String(value || "all").trim().toLowerCase()) || "all";
          const allowed = new Set(["all", "queued", "running", "partial", "succeeded", "failed", "canceled"]);
          return allowed.has(normalized) ? normalized : "all";
        }

        function readStoredJobIds() {
          try {
            const raw = window.localStorage.getItem(JOB_IDS_STORAGE_KEY);
            if (!raw) return [];
            const parsed = JSON.parse(raw);
            if (!Array.isArray(parsed)) return [];
            return parsed.map((item) => String(item || "").trim()).filter(Boolean);
          } catch (error) {
            return [];
          }
        }

        function persistStoredJobIds(ids) {
          try {
            window.localStorage.setItem(JOB_IDS_STORAGE_KEY, JSON.stringify(ids));
          } catch (error) {
            // ignore
          }
        }

        function rememberJobId(jobId) {
          const normalized = String(jobId || "").trim();
          if (!normalized) return;
          const next = [normalized, ...state.ids.filter((id) => id !== normalized)].slice(0, 60);
          state.ids = next;
          persistStoredJobIds(next);
        }

        function clearJobIds() {
          state.ids = [];
          persistStoredJobIds([]);
        }

        function updateDeepLink() {
          if (!window.history || !window.location) return;
          const nextUrl = new URL(window.location.href);

          const status = normalizeStatus(state.status);
          const q = String(state.q || "").trim();

          if (status !== "all") nextUrl.searchParams.set("jobs_status", status);
          else nextUrl.searchParams.delete("jobs_status");

          if (q) nextUrl.searchParams.set("jobs_q", q);
          else nextUrl.searchParams.delete("jobs_q");

          window.history.replaceState({}, "", nextUrl);
        }

        function restoreDeepLink() {
          const url = new URL(window.location.href);
          state.status = normalizeStatus(url.searchParams.get("jobs_status"));
          state.q = String(url.searchParams.get("jobs_q") || "").trim();

          statusEl.value = state.status;
          qEl.value = state.q;
        }

        function applyTokenDefaults() {
          try {
            const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
            if (token) tokenEl.value = token;
            const orgId = window.localStorage.getItem(ORG_STORAGE_KEY);
            if (orgId) orgEl.value = orgId;
          } catch (error) {
            // ignore
          }
        }

        function persistTokenInputs() {
          try {
            window.localStorage.setItem(TOKEN_STORAGE_KEY, String(tokenEl.value || "").trim());
            window.localStorage.setItem(ORG_STORAGE_KEY, String(orgEl.value || "").trim());
          } catch (error) {
            // ignore
          }
        }

        function jobUrl(jobId) {
          return `${JOBS_ENDPOINT_BASE}/${encodeURIComponent(jobId)}`;
        }

        async function fetchJob(jobId) {
          const headers = { "Accept": "application/json" };
          const token = String(tokenEl.value || "").trim();
          const orgId = String(orgEl.value || "").trim();
          if (token) headers["Authorization"] = `Bearer ${token}`;
          if (orgId) headers["X-Org-Id"] = orgId;

          const resp = await fetch(jobUrl(jobId), { method: "GET", headers });
          if (!resp.ok) {
            return { ok: false, status: resp.status };
          }
          const payload = await resp.json();
          if (!payload || !payload.ok || !payload.job) {
            return { ok: false, status: resp.status };
          }
          return { ok: true, status: resp.status, job: payload.job };
        }

        function passesSearch(jobId) {
          const q = String(state.q || "").trim().toLowerCase();
          if (!q) return true;
          return String(jobId || "").toLowerCase().includes(q);
        }

        function passesStatus(job) {
          const filter = normalizeStatus(state.status);
          if (filter === "all") return true;
          const status = canonicalJobStatus(job && job.status ? String(job.status).trim().toLowerCase() : "");
          return status === filter;
        }

        function renderTable(rows) {
          bodyEl.textContent = "";

          if (!rows.length) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");
            td.colSpan = 5;
            const box = document.createElement("div");
            box.className = "empty";
            box.textContent = state.ids.length
              ? "Keine Treffer für aktuellen Filter/Suche."
              : "Noch keine Jobs gespeichert. Tipp: starte einen Async-Analyze in /gui oder füge oben eine job_id hinzu.";
            td.appendChild(box);
            tr.appendChild(td);
            bodyEl.appendChild(tr);
            metaEl.textContent = state.ids.length ? `0/${state.ids.length} angezeigt` : "0 jobs";
            return;
          }

          metaEl.textContent = `${rows.length}/${state.ids.length} angezeigt`;

          rows.forEach((row) => {
            const tr = document.createElement("tr");

            const tdId = document.createElement("td");
            const code = document.createElement("code");
            code.textContent = row.jobId;
            tdId.appendChild(code);
            tr.appendChild(tdId);

            const tdStatus = document.createElement("td");
            tdStatus.textContent = row.statusText;
            tr.appendChild(tdStatus);

            const tdProgress = document.createElement("td");
            tdProgress.textContent = row.progressText;
            tr.appendChild(tdProgress);

            const tdUpdated = document.createElement("td");
            tdUpdated.textContent = row.updatedText;
            tr.appendChild(tdUpdated);

            const tdLinks = document.createElement("td");
            const actions = document.createElement("div");
            actions.className = "row-actions";

            const viewLink = document.createElement("a");
            viewLink.href = `/jobs/${encodeURIComponent(row.jobId)}`;
            viewLink.textContent = "Open";
            actions.appendChild(viewLink);

            if (row.resultId) {
              const resultLink = document.createElement("a");
              resultLink.href = `/results/${encodeURIComponent(row.resultId)}`;
              resultLink.textContent = "Result";
              actions.appendChild(resultLink);
            }

            const removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "secondary";
            removeBtn.textContent = "Remove";
            removeBtn.addEventListener("click", () => {
              state.ids = state.ids.filter((id) => id !== row.jobId);
              persistStoredJobIds(state.ids);
              void refresh();
            });
            actions.appendChild(removeBtn);

            tdLinks.appendChild(actions);
            tr.appendChild(tdLinks);

            bodyEl.appendChild(tr);
          });
        }

        async function refresh() {
          persistTokenInputs();

          const filteredIds = state.ids.filter((id) => passesSearch(id));
          if (!filteredIds.length) {
            renderTable([]);
            return;
          }

          metaEl.textContent = "Loading…";

          const results = await Promise.all(
            filteredIds.map(async (jobId) => {
              const fetched = await fetchJob(jobId);
              if (!fetched.ok) {
                return {
                  jobId,
                  statusText: fetched.status === 404 ? "not_found" : `error (${fetched.status})`,
                  progressText: "—",
                  updatedText: "—",
                  resultId: "",
                  _pass: true,
                };
              }

              const job = fetched.job || {};
              const statusText = canonicalJobStatus(String(job.status || "").trim().toLowerCase()) || "queued";
              const progress = Number(job.progress_percent);
              const progressText = Number.isFinite(progress) ? `${Math.round(progress)}%` : "—";
              const updatedText = String(job.updated_at || job.finished_at || job.started_at || job.queued_at || "").trim();
              const resultId = String(job.result_id || "").trim();

              return {
                jobId,
                statusText,
                progressText,
                updatedText,
                resultId,
                _pass: passesStatus(job),
              };
            })
          );

          const visible = results.filter((row) => row._pass);
          renderTable(visible);
        }

        function syncStateFromControls() {
          state.status = normalizeStatus(statusEl.value);
          state.q = String(qEl.value || "").trim();
          updateDeepLink();
        }

        statusEl.addEventListener("change", () => {
          syncStateFromControls();
          void refresh();
        });

        qEl.addEventListener("input", () => {
          syncStateFromControls();
          void refresh();
        });

        addBtn.addEventListener("click", () => {
          rememberJobId(addIdEl.value);
          addIdEl.value = "";
          void refresh();
        });

        refreshBtn.addEventListener("click", () => {
          syncStateFromControls();
          void refresh();
        });

        clearBtn.addEventListener("click", () => {
          clearJobIds();
          void refresh();
        });

        tokenEl.addEventListener("change", persistTokenInputs);
        orgEl.addEventListener("change", persistTokenInputs);

        state.ids = readStoredJobIds();
        restoreDeepLink();
        applyTokenDefaults();
        syncStateFromControls();
        void refresh();
      </script>
    </main>
  </body>
</html>
"""


def _normalize_path(path: str) -> str:
    """Normalisiert doppelte Slashes und entfernt Trailing-Slash (außer Root)."""

    raw = path or "/"
    normalized = posixpath.normpath(raw)
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized == "/.":
        return "/"
    return normalized


def _normalize_result_id(raw_value: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        return ""
    if "/" in normalized:
        return ""
    if not _RESULT_ID_RE.match(normalized):
        return ""
    return normalized


def _normalize_job_id(raw_value: str) -> str:
    normalized = str(raw_value or "").strip()
    if not normalized:
        return ""
    if "/" in normalized:
        return ""
    if not _JOB_ID_RE.match(normalized):
        return ""
    return normalized


def _build_gui_html(*, app_version: str, api_base_url: str) -> str:
    normalized_base_url = api_base_url.rstrip("/") if api_base_url else ""
    # Auth-Entry bleibt UI-owned: Login immer über /login auf der UI-Domain.
    auth_login_url = "/login"
    auth_logout_url = "/auth/logout"
    auth_me_url = "/auth/me"

    html = render_gui_mvp_html(
        app_version=app_version,
        auth_login_endpoint=auth_login_url,
        auth_logout_endpoint=auth_logout_url,
        auth_me_endpoint=auth_me_url,
    )
    if not normalized_base_url:
        return html

    analyze_url = f"{normalized_base_url}/analyze"
    trace_debug_url = f"{normalized_base_url}/debug/trace"
    analyze_jobs_base = f"{normalized_base_url}/analyze/jobs"
    analyze_history_url = f"{normalized_base_url}/analyze/history"

    html = html.replace('fetch("/analyze", {', f"fetch({json.dumps(analyze_url)}, {{")
    html = html.replace(
        'const TRACE_DEBUG_ENDPOINT = "/debug/trace";',
        f"const TRACE_DEBUG_ENDPOINT = {json.dumps(trace_debug_url)};",
    )
    html = html.replace(
        'const ANALYZE_JOBS_ENDPOINT_BASE = "/analyze/jobs";',
        f"const ANALYZE_JOBS_ENDPOINT_BASE = {json.dumps(analyze_jobs_base)};",
    )
    html = html.replace(
        'const ANALYZE_HISTORY_ENDPOINT = "/analyze/history";',
        f"const ANALYZE_HISTORY_ENDPOINT = {json.dumps(analyze_history_url)};",
    )
    return html


def _build_result_permalink_html(*, app_version: str, api_base_url: str, result_id: str) -> str:
    """Rendert eine Result-Page mit Tabs.

    Tabs:
    - Overview
    - Sources / Evidence
    - Generated / Derived
    - Raw JSON

    Die Page lädt JSON asynchron über `GET /analyze/results/<result_id>`.
    """

    normalized_result_id = _normalize_result_id(result_id)
    if not normalized_result_id:
        raise ValueError("invalid result_id")

    return build_result_tabs_page_html(
        app_version=app_version,
        api_base_url=api_base_url,
        result_id=normalized_result_id,
    )


def _build_job_permalink_html(*, app_version: str, api_base_url: str, job_id: str) -> str:
    """Rendert eine minimale Job-Page (Status + Notifications).

    Die Page pollt die Job- und Notification-Endpunkte und zeigt bei terminalen
    Jobs eine UI-Notification inkl. Link zur Result-Page.
    """

    normalized_job_id = _normalize_job_id(job_id)
    if not normalized_job_id:
        raise ValueError("invalid job_id")

    safe_job_id = escape(normalized_job_id)
    normalized_base_url = api_base_url.rstrip("/")
    jobs_endpoint_base = (
        f"{normalized_base_url}/analyze/jobs" if normalized_base_url else "/analyze/jobs"
    )

    html = _JOB_PAGE_TEMPLATE
    html = html.replace("__JOB_ID__", safe_job_id)
    html = html.replace("__APP_VERSION__", escape(app_version))
    html = html.replace("__JOB_ID_JSON__", json.dumps(normalized_job_id))
    html = html.replace("__JOBS_ENDPOINT_BASE_JSON__", json.dumps(jobs_endpoint_base))
    return html


def _build_jobs_list_html(*, app_version: str, api_base_url: str) -> str:
    normalized_base_url = api_base_url.rstrip("/")
    jobs_endpoint_base = (
        f"{normalized_base_url}/analyze/jobs" if normalized_base_url else "/analyze/jobs"
    )

    html = _JOBS_LIST_PAGE_TEMPLATE
    html = html.replace("__APP_VERSION__", escape(app_version))
    html = html.replace("__JOBS_ENDPOINT_BASE_JSON__", json.dumps(jobs_endpoint_base))
    return html


class _UiHandler(BaseHTTPRequestHandler):
    server_version = "geo-ranking-ui/1.0"

    def _send_json(self, payload: dict, *, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str, *, status: int = HTTPStatus.OK) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _build_api_target_url(self, *, request_path: str, raw_query: str) -> str | None:
        normalized_base_url = str(self.server.ui_api_base_url or "").strip().rstrip("/")
        if not normalized_base_url:
            return None
        target_url = f"{normalized_base_url}{request_path}"
        if raw_query:
            target_url = f"{target_url}?{raw_query}"
        return target_url

    @staticmethod
    def _rewrite_upstream_location(
        *,
        location: str,
        api_base_url: str,
        ui_scheme: str = "",
        ui_host: str = "",
    ) -> str:
        normalized_base_url = str(api_base_url or "").strip().rstrip("/")
        rewritten = str(location or "")

        if normalized_base_url and rewritten.startswith(f"{normalized_base_url}/"):
            parsed = urlsplit(rewritten)
            rewritten = urlunsplit(("", "", parsed.path, parsed.query, parsed.fragment))

        # Keep IdP logout roundtrips on the UI host (www):
        # rewrite nested `logout_uri` callback targets from API-host auth paths
        # to `https?://<ui-host>/login`.
        normalized_scheme = str(ui_scheme or "").strip().lower()
        if normalized_scheme not in {"http", "https"}:
            normalized_scheme = ""
        normalized_host = str(ui_host or "").split(",", 1)[0].strip()
        if not rewritten or not normalized_scheme or not normalized_host:
            return rewritten

        parsed_location = urlsplit(rewritten)
        if not parsed_location.query:
            return rewritten

        query_pairs = parse_qsl(parsed_location.query, keep_blank_values=True)
        changed = False
        updated_pairs: list[tuple[str, str]] = []

        for key, value in query_pairs:
            if key != "logout_uri":
                updated_pairs.append((key, value))
                continue

            target_uri = str(value or "").strip()
            parsed_target = urlsplit(target_uri)
            normalized_target_path = (parsed_target.path or "").rstrip("/") or "/"
            target_is_api_host = bool(
                normalized_base_url
                and target_uri.startswith(f"{normalized_base_url}/")
            )
            target_is_auth_login_path = normalized_target_path in {"/auth/login", "/login"}

            if target_is_api_host or target_is_auth_login_path:
                value = urlunsplit((normalized_scheme, normalized_host, "/login", "", ""))
                changed = True

            updated_pairs.append((key, value))

        if not changed:
            return rewritten

        rebuilt_query = urlencode(updated_pairs, doseq=True)
        return urlunsplit(
            (
                parsed_location.scheme,
                parsed_location.netloc,
                parsed_location.path,
                rebuilt_query,
                parsed_location.fragment,
            )
        )

    def _proxy_auth_request(self, *, request_path: str, raw_query: str) -> bool:
        """Proxied ``/auth/*`` calls to API while keeping browser URL on UI host."""

        target_url = self._build_api_target_url(request_path=request_path, raw_query=raw_query)
        if not target_url:
            return False

        upstream_headers: dict[str, str] = {}
        forwarded_cookie = self.headers.get("Cookie")
        if forwarded_cookie:
            upstream_headers["Cookie"] = forwarded_cookie
        forwarded_accept = self.headers.get("Accept")
        if forwarded_accept:
            upstream_headers["Accept"] = forwarded_accept

        forwarded_proto = str(self.headers.get("X-Forwarded-Proto", "") or "").split(",", 1)[0].strip().lower()
        request_scheme = forwarded_proto if forwarded_proto in {"http", "https"} else "http"
        forwarded_host = str(self.headers.get("X-Forwarded-Host", "") or "").split(",", 1)[0].strip()
        request_host = forwarded_host or str(self.headers.get("Host", "") or "").strip()
        if request_host:
            upstream_headers["X-Forwarded-Host"] = request_host
            upstream_headers["X-Forwarded-Proto"] = request_scheme

        class _NoRedirect(urllib_request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, hdrs, newurl):  # noqa: D401
                return None

        req = urllib_request.Request(target_url, method="GET", headers=upstream_headers)
        opener = urllib_request.build_opener(_NoRedirect)
        try:
            upstream_resp = opener.open(req, timeout=15)
        except urllib_error.HTTPError as exc:
            upstream_resp = exc
        except urllib_error.URLError:
            self._send_json(
                {
                    "ok": False,
                    "error": "upstream_unavailable",
                    "message": "auth upstream unavailable",
                },
                status=HTTPStatus.BAD_GATEWAY,
            )
            return True

        body = upstream_resp.read()
        upstream_status = int(getattr(upstream_resp, "status", 0) or upstream_resp.getcode())
        self.send_response(upstream_status)

        hop_by_hop_headers = {
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailer",
            "transfer-encoding",
            "upgrade",
            "content-length",
        }
        for header_name, header_value in upstream_resp.headers.items():
            normalized_name = header_name.lower()
            if normalized_name in hop_by_hop_headers:
                continue
            if normalized_name == "location":
                header_value = self._rewrite_upstream_location(
                    location=header_value,
                    api_base_url=self.server.ui_api_base_url,
                    ui_scheme=request_scheme,
                    ui_host=request_host,
                )
            self.send_header(header_name, header_value)

        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)
        return True

    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        request_path = _normalize_path(parsed.path)

        if request_path in {"/", "/gui"}:
            html = _build_gui_html(
                app_version=self.server.app_version,
                api_base_url=self.server.ui_api_base_url,
            )
            self._send_html(html)
            return

        if request_path == "/login":
            location = "/auth/login"
            if parsed.query:
                location = f"{location}?{parsed.query}"
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if request_path.startswith("/auth/"):
            if self._proxy_auth_request(request_path=request_path, raw_query=parsed.query):
                return
            self._send_json(
                {
                    "ok": False,
                    "error": "auth_proxy_not_configured",
                    "message": "UI auth proxy requires UI_API_BASE_URL",
                },
                status=HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return

        if request_path == "/history":
            html = build_history_page_html(
                app_version=self.server.app_version,
                api_base_url=self.server.ui_api_base_url,
            )
            self._send_html(html)
            return

        if request_path == "/jobs":
            html = _build_jobs_list_html(
                app_version=self.server.app_version,
                api_base_url=self.server.ui_api_base_url,
            )
            self._send_html(html)
            return

        if request_path.startswith("/jobs/"):
            job_id = request_path.removeprefix("/jobs/").strip()
            normalized_job_id = _normalize_job_id(job_id)
            if not normalized_job_id:
                self._send_json(
                    {
                        "ok": False,
                        "error": "not_found",
                        "message": "Unknown job_id",
                    },
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            try:
                html = _build_job_permalink_html(
                    app_version=self.server.app_version,
                    api_base_url=self.server.ui_api_base_url,
                    job_id=normalized_job_id,
                )
            except ValueError:
                self._send_json(
                    {
                        "ok": False,
                        "error": "not_found",
                        "message": "Unknown job_id",
                    },
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            self._send_html(html)
            return

        if request_path.startswith("/results/"):
            result_id = request_path.removeprefix("/results/").strip()
            normalized_result_id = _normalize_result_id(result_id)
            if not normalized_result_id:
                self._send_json(
                    {
                        "ok": False,
                        "error": "not_found",
                        "message": "Unknown result_id",
                    },
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            try:
                html = _build_result_permalink_html(
                    app_version=self.server.app_version,
                    api_base_url=self.server.ui_api_base_url,
                    result_id=normalized_result_id,
                )
            except ValueError:
                self._send_json(
                    {
                        "ok": False,
                        "error": "not_found",
                        "message": "Unknown result_id",
                    },
                    status=HTTPStatus.NOT_FOUND,
                )
                return

            self._send_html(html)
            return

        if request_path in {"/health", "/healthz"}:
            self._send_json(
                {
                    "ok": True,
                    "service": "geo-ranking-ch-ui",
                    "version": self.server.app_version,
                    "api_base_url": self.server.ui_api_base_url or None,
                    "result_permalink": {
                        "path_template": "/results/<result_id>",
                    },
                    "job_permalink": {
                        "path_template": "/jobs/<job_id>",
                    },
                }
            )
            return

        self._send_json(
            {
                "ok": False,
                "error": "not_found",
                "message": f"Unknown endpoint: {request_path}",
            },
            status=HTTPStatus.NOT_FOUND,
        )

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - stdlib signature
        return


class _UiHttpServer(ThreadingHTTPServer):
    def __init__(self, server_address, request_handler_class, *, app_version: str, ui_api_base_url: str):
        super().__init__(server_address, request_handler_class)
        self.app_version = app_version
        self.ui_api_base_url = ui_api_base_url


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    app_version = os.getenv("APP_VERSION", "dev")
    ui_api_base_url = os.getenv("UI_API_BASE_URL", "").strip()

    httpd = _UiHttpServer(
        (host, port),
        _UiHandler,
        app_version=app_version,
        ui_api_base_url=ui_api_base_url,
    )
    print(
        f"[geo-ranking-ch-ui] serving on http://{host}:{port} "
        f"(version={app_version}, api_base_url={ui_api_base_url or '/analyze (relative)'})"
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
