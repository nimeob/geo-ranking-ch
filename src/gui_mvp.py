#!/usr/bin/env python3
"""GUI-MVP Shell (BL-20.6.a) für Grundlayout + stabilen State-Flow.

Das Modul liefert bewusst ein schlankes, API-first Frontend ohne externe
Abhängigkeiten. Die Logik bleibt additiv: spätere Map-/Mobile-Features können
über neue UI-Module ergänzt werden, ohne den bestehenden Analyze-Flow zu brechen.
"""

from __future__ import annotations

from html import escape

_GUI_MVP_HTML_TEMPLATE = """<!doctype html>
<html lang=\"de\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>geo-ranking.ch GUI MVP</title>
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
      }
      .header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        flex-wrap: wrap;
      }
      .brand {
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
      }
      .brand h1 {
        margin: 0;
        font-size: 1.05rem;
      }
      .brand p {
        margin: 0;
        color: var(--muted);
        font-size: 0.9rem;
      }
      nav {
        display: flex;
        gap: 0.5rem;
      }
      nav a {
        text-decoration: none;
        color: var(--primary);
        border: 1px solid var(--border);
        padding: 0.35rem 0.55rem;
        border-radius: 0.5rem;
        font-size: 0.86rem;
      }
      main {
        display: grid;
        grid-template-columns: minmax(300px, 460px) minmax(360px, 1fr);
        gap: 1rem;
        padding: 1rem 1.25rem 1.5rem;
      }
      @media (max-width: 960px) {
        main { grid-template-columns: 1fr; }
      }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.85rem;
        padding: 1rem;
      }
      .card h2 {
        margin: 0 0 0.75rem;
        font-size: 1rem;
      }
      .meta {
        font-size: 0.84rem;
        color: var(--muted);
      }
      .stack {
        display: grid;
        gap: 0.75rem;
      }
      label {
        display: grid;
        gap: 0.3rem;
        font-size: 0.86rem;
        color: var(--muted);
      }
      input,
      select,
      button,
      textarea {
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 0.55rem 0.6rem;
        font: inherit;
      }
      input:focus,
      select:focus,
      button:focus,
      textarea:focus {
        outline: 2px solid #bcd0ff;
        outline-offset: 1px;
      }
      button {
        background: var(--primary);
        color: #fff;
        border-color: var(--primary);
        cursor: pointer;
      }
      button[disabled] {
        opacity: 0.65;
        cursor: not-allowed;
      }
      .grid-2 {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: 1fr 1fr;
      }
      @media (max-width: 520px) {
        .grid-2 { grid-template-columns: 1fr; }
      }
      .pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        border-radius: 999px;
        border: 1px solid var(--border);
        background: #f9fbff;
        font-size: 0.8rem;
        padding: 0.26rem 0.58rem;
      }
      .phase-loading { color: #8b5200; }
      .phase-success { color: var(--success); }
      .phase-error { color: var(--danger); }
      .placeholder {
        background: #f7f9fc;
        border: 1px dashed var(--border);
        border-radius: 0.65rem;
        padding: 0.75rem;
      }
      pre {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 0.84rem;
        max-height: 28rem;
        overflow: auto;
      }
      .error-box {
        border: 1px solid #f2c6c2;
        border-left: 4px solid var(--danger);
        background: #fff8f8;
        border-radius: 0.55rem;
        color: #7a201a;
        padding: 0.65rem 0.75rem;
      }
    </style>
  </head>
  <body>
    <header>
      <div class=\"header-row\">
        <div class=\"brand\">
          <h1>geo-ranking.ch — GUI MVP Shell</h1>
          <p>BL-20.6.a · API-first Layout + State-Flow · Version __APP_VERSION__</p>
        </div>
        <nav id=\"gui-shell-nav\" aria-label=\"Kernnavigation\">
          <a href=\"#input\">Input</a>
          <a href=\"#map\">Map-Platzhalter</a>
          <a href=\"#result\">Result-Panel</a>
        </nav>
      </div>
    </header>

    <main>
      <section class=\"stack\">
        <article class=\"card\" id=\"input\">
          <h2>Adresseingabe</h2>
          <form id=\"analyze-form\" class=\"stack\">
            <label>
              Adresse
              <input id=\"query\" name=\"query\" type=\"text\" placeholder=\"z. B. Bahnhofstrasse 1, 8001 Zürich\" required />
            </label>
            <div class=\"grid-2\">
              <label>
                Intelligence-Mode
                <select id=\"intelligence-mode\" name=\"intelligence_mode\">
                  <option value=\"basic\">basic</option>
                  <option value=\"extended\">extended</option>
                  <option value=\"risk\">risk</option>
                </select>
              </label>
              <label>
                API Token (optional)
                <input id=\"api-token\" type=\"password\" placeholder=\"Bearer-Token für geschützte Deployments\" autocomplete=\"off\" />
              </label>
            </div>
            <button id=\"submit-btn\" type=\"submit\">Analyse starten</button>
          </form>
          <p class=\"meta\">State-Flow: <code>idle -> loading -> success/error</code>. Map-Klick-Handling folgt in BL-20.6.b.</p>
        </article>

        <article class=\"card\" id=\"map\">
          <h2>Karteninteraktion (nächster Schritt)</h2>
          <div class=\"placeholder\">
            Kartenklick ist in <strong>BL-20.6.b</strong> vorgesehen. Der aktuelle Shell reserviert bereits den UI-Platz,
            damit der künftige Klick-Flow additiv integriert werden kann.
          </div>
        </article>
      </section>

      <section class=\"stack\" id=\"result\">
        <article class=\"card\">
          <h2>Result-Panel</h2>
          <p class=\"pill\" id=\"phase-pill\" data-phase=\"idle\">Status: idle</p>
          <p class=\"meta\" id=\"request-meta\">Noch keine Anfrage gesendet.</p>
          <div id=\"error-box\" class=\"error-box\" hidden></div>
        </article>

        <article class=\"card\">
          <h2>API-Response (JSON)</h2>
          <pre id=\"result-json\">{\n  \"hint\": \"Sende eine Anfrage über das Formular links.\"\n}</pre>
        </article>
      </section>
    </main>

    <script>
      const state = {
        phase: "idle",
        lastRequestId: null,
        lastPayload: null,
        lastError: null,
      };

      const formEl = document.getElementById("analyze-form");
      const queryEl = document.getElementById("query");
      const modeEl = document.getElementById("intelligence-mode");
      const tokenEl = document.getElementById("api-token");
      const submitBtn = document.getElementById("submit-btn");
      const phasePill = document.getElementById("phase-pill");
      const requestMeta = document.getElementById("request-meta");
      const resultJson = document.getElementById("result-json");
      const errorBox = document.getElementById("error-box");

      function prettyPrint(payload) {
        return JSON.stringify(payload, null, 2);
      }

      function updatePhaseClass(phase) {
        phasePill.classList.remove("phase-loading", "phase-success", "phase-error");
        if (phase === "loading") phasePill.classList.add("phase-loading");
        if (phase === "success") phasePill.classList.add("phase-success");
        if (phase === "error") phasePill.classList.add("phase-error");
      }

      function renderState() {
        phasePill.textContent = `Status: ${state.phase}`;
        phasePill.dataset.phase = state.phase;
        updatePhaseClass(state.phase);

        if (state.lastRequestId) {
          requestMeta.textContent = `Letzte Request-ID: ${state.lastRequestId}`;
        } else if (state.phase === "loading") {
          requestMeta.textContent = "Anfrage läuft …";
        } else {
          requestMeta.textContent = "Noch keine Anfrage gesendet.";
        }

        if (state.lastError) {
          errorBox.hidden = false;
          errorBox.textContent = state.lastError;
        } else {
          errorBox.hidden = true;
          errorBox.textContent = "";
        }

        if (state.lastPayload) {
          resultJson.textContent = prettyPrint(state.lastPayload);
        }
      }

      async function runAnalyze(payload, token) {
        const headers = { "Content-Type": "application/json" };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch("/analyze", {
          method: "POST",
          headers,
          body: JSON.stringify(payload),
        });

        let parsed;
        try {
          parsed = await response.json();
        } catch (error) {
          throw new Error("Response ist kein gültiges JSON.");
        }

        const requestId = parsed && parsed.request_id ? String(parsed.request_id) : null;
        if (!response.ok || !parsed.ok) {
          const errCode = parsed && parsed.error ? parsed.error : `http_${response.status}`;
          const errMsg = parsed && parsed.message ? parsed.message : "Unbekannter Fehler";
          const richError = `${errCode}: ${errMsg}`;
          const failingResponse = parsed || { ok: false, error: errCode, message: errMsg };
          return { ok: false, requestId, response: failingResponse, errorMessage: richError };
        }

        return { ok: true, requestId, response: parsed, errorMessage: null };
      }

      formEl.addEventListener("submit", async (event) => {
        event.preventDefault();

        const query = (queryEl.value || "").trim();
        if (!query) {
          state.phase = "error";
          state.lastError = "Bitte eine Adresse eingeben.";
          state.lastPayload = {
            ok: false,
            error: "validation",
            message: "query darf nicht leer sein",
          };
          renderState();
          return;
        }

        const payload = {
          query,
          intelligence_mode: modeEl.value || "basic",
          options: {
            response_mode: "compact",
          },
        };

        state.phase = "loading";
        state.lastError = null;
        state.lastPayload = { ok: false, loading: true, request: payload };
        state.lastRequestId = null;
        submitBtn.disabled = true;
        renderState();

        try {
          const result = await runAnalyze(payload, (tokenEl.value || "").trim());
          state.lastRequestId = result.requestId;
          state.lastPayload = result.response;
          state.phase = result.ok ? "success" : "error";
          state.lastError = result.errorMessage;
        } catch (error) {
          state.phase = "error";
          state.lastError = error instanceof Error ? error.message : "Netzwerkfehler";
          state.lastPayload = {
            ok: false,
            error: "network_error",
            message: state.lastError,
          };
        } finally {
          submitBtn.disabled = false;
          renderState();
        }
      });

      renderState();
    </script>
  </body>
</html>
"""


def render_gui_mvp_html(*, app_version: str) -> str:
    """Render das statische GUI-MVP-HTML mit sicher escaped Version."""

    safe_version = escape(app_version or "dev")
    return _GUI_MVP_HTML_TEMPLATE.replace("__APP_VERSION__", safe_version)
