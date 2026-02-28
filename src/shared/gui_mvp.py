#!/usr/bin/env python3
"""GUI-MVP Shell (BL-20.6) für Adresseingabe, Kartenklick und Result-Panel.

Das Modul liefert bewusst ein schlankes, API-first Frontend ohne externe
Abhängigkeiten. Fachlogik bleibt serverseitig in ``POST /analyze``;
Frontend-Module (Adresseingabe, Kartenklick, Ergebnisdarstellung) sind additiv,
sodass spätere HTML5-/Mobile-Ausbaupfade ohne Rewrite möglich bleiben.
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
      textarea:focus,
      .map-surface:focus {
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
      .map-shell {
        display: grid;
        gap: 0.6rem;
      }
      .map-surface {
        position: relative;
        width: 100%;
        min-height: 260px;
        border: 1px solid var(--border);
        border-radius: 0.65rem;
        cursor: crosshair;
        overflow: hidden;
        background:
          radial-gradient(circle at 24% 36%, rgba(22, 127, 68, 0.18) 0 18%, transparent 22%),
          radial-gradient(circle at 62% 52%, rgba(22, 127, 68, 0.18) 0 22%, transparent 28%),
          linear-gradient(145deg, #d6e7ff, #f4f8ff 50%, #eaf4ff);
      }
      .map-grid {
        position: absolute;
        inset: 0;
        background-image:
          linear-gradient(to right, rgba(12, 55, 117, 0.13) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(12, 55, 117, 0.13) 1px, transparent 1px);
        background-size: 28px 28px;
      }
      .map-outline {
        position: absolute;
        inset: 9% 11% 13% 9%;
        border: 2px solid rgba(10, 72, 40, 0.45);
        border-radius: 18% 24% 20% 18%;
        pointer-events: none;
      }
      .map-marker {
        position: absolute;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 2px solid #fff;
        background: #bd2f24;
        box-shadow: 0 0 0 2px rgba(189, 47, 36, 0.25);
        transform: translate(-50%, -50%);
        pointer-events: none;
      }
      .map-legend {
        display: flex;
        justify-content: space-between;
        gap: 0.6rem;
        flex-wrap: wrap;
      }
      .map-legend small {
        color: var(--muted);
      }
      .factor-list {
        margin: 0;
        padding-left: 1.15rem;
        display: grid;
        gap: 0.45rem;
      }
      .factor-list li {
        font-size: 0.88rem;
        line-height: 1.3;
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
          <h1>geo-ranking.ch — GUI MVP</h1>
          <p>BL-20.6 · Adresse + Kartenklick + Result-Panel · Version __APP_VERSION__</p>
        </div>
        <nav id=\"gui-shell-nav\" aria-label=\"Kernnavigation\">
          <a href=\"#input\">Input</a>
          <a href=\"#map\">Karte</a>
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
            <button id=\"submit-btn\" type=\"submit\">Analyse per Adresse starten</button>
          </form>
          <p class=\"meta\">State-Flow: <code>idle -> loading -> success/error</code>. Kartenklick löst denselben Analyze-Pfad additiv über <code>coordinates</code> aus.</p>
        </article>

        <article class=\"card\" id=\"map\">
          <h2>Karteninteraktion</h2>
          <div class=\"map-shell\">
            <div
              id=\"map-click-surface\"
              class=\"map-surface\"
              role=\"button\"
              tabindex=\"0\"
              aria-label=\"Schweiz-Kartenfläche: klicken um Koordinaten zu analysieren\"
            >
              <div class=\"map-grid\"></div>
              <div class=\"map-outline\"></div>
              <div id=\"map-click-marker\" class=\"map-marker\" hidden></div>
            </div>
            <div class=\"map-legend\">
              <small>Bounds: CH WGS84 (45.8179..47.8084 / 5.9559..10.4921)</small>
              <small id=\"click-hint\">Noch kein Kartenpunkt gewählt.</small>
            </div>
            <div class=\"placeholder\">Klick in die Karte startet sofort eine Analyse über <code>POST /analyze</code> mit <code>coordinates.lat/lon</code> (inkl. <code>snap_mode=ch_bounds</code>).</div>
          </div>
        </article>
      </section>

      <section class=\"stack\" id=\"result\">
        <article class=\"card\">
          <h2>Result-Panel</h2>
          <p class=\"pill\" id=\"phase-pill\" data-phase=\"idle\">Status: idle</p>
          <p class=\"meta\" id=\"request-meta\">Noch keine Anfrage gesendet.</p>
          <p class=\"meta\" id=\"input-meta\">Input: —</p>
          <div id=\"error-box\" class=\"error-box\" hidden></div>
        </article>

        <article class=\"card\">
          <h2>Kernfaktoren (Top)</h2>
          <ul id=\"core-factors\" class=\"factor-list\">
            <li>Noch keine Faktoren verfügbar.</li>
          </ul>
        </article>

        <article class=\"card\">
          <h2>API-Response (JSON)</h2>
          <pre id=\"result-json\">{\n  \"hint\": \"Sende eine Anfrage per Adresse oder Kartenklick.\"\n}</pre>
        </article>
      </section>
    </main>

    <script>
      const CH_BOUNDS = {
        latMin: 45.8179,
        latMax: 47.8084,
        lonMin: 5.9559,
        lonMax: 10.4921,
      };

      const state = {
        phase: "idle",
        lastRequestId: null,
        lastPayload: null,
        lastError: null,
        lastInput: null,
        coreFactors: [],
      };

      const formEl = document.getElementById("analyze-form");
      const queryEl = document.getElementById("query");
      const modeEl = document.getElementById("intelligence-mode");
      const tokenEl = document.getElementById("api-token");
      const submitBtn = document.getElementById("submit-btn");
      const phasePill = document.getElementById("phase-pill");
      const requestMeta = document.getElementById("request-meta");
      const inputMeta = document.getElementById("input-meta");
      const resultJson = document.getElementById("result-json");
      const errorBox = document.getElementById("error-box");
      const coreFactorsEl = document.getElementById("core-factors");

      const mapSurface = document.getElementById("map-click-surface");
      const mapMarker = document.getElementById("map-click-marker");
      const clickHint = document.getElementById("click-hint");

      function prettyPrint(payload) {
        return JSON.stringify(payload, null, 2);
      }

      function formatCoord(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) {
          return "?";
        }
        return num.toFixed(6);
      }

      function clamp(value, min, max) {
        const num = Number(value);
        if (!Number.isFinite(num)) {
          return min;
        }
        if (num < min) return min;
        if (num > max) return max;
        return num;
      }

      function updatePhaseClass(phase) {
        phasePill.classList.remove("phase-loading", "phase-success", "phase-error");
        if (phase === "loading") phasePill.classList.add("phase-loading");
        if (phase === "success") phasePill.classList.add("phase-success");
        if (phase === "error") phasePill.classList.add("phase-error");
      }

      function getNestedArray(source, path) {
        let current = source;
        for (const key of path) {
          if (!current || typeof current !== "object" || !(key in current)) {
            return null;
          }
          current = current[key];
        }
        return Array.isArray(current) ? current : null;
      }

      function extractCoreFactors(payload) {
        const candidates = [
          ["result", "data", "modules", "explainability", "personalized", "factors"],
          ["result", "data", "modules", "explainability", "base", "factors"],
          ["result", "explainability", "personalized", "factors"],
          ["result", "explainability", "base", "factors"],
        ];

        for (const path of candidates) {
          const factors = getNestedArray(payload, path);
          if (!factors || factors.length === 0) {
            continue;
          }

          return factors
            .filter((factor) => factor && typeof factor === "object")
            .map((factor) => {
              const contribution = Number(factor.contribution);
              return {
                key: String(factor.key || "factor"),
                reason: String(factor.reason || "kein reason vorhanden"),
                direction: String(factor.direction || "neutral"),
                source: String(factor.source || "unknown"),
                contribution: Number.isFinite(contribution) ? contribution : null,
              };
            })
            .sort((a, b) => {
              const aAbs = Math.abs(a.contribution == null ? 0 : a.contribution);
              const bAbs = Math.abs(b.contribution == null ? 0 : b.contribution);
              return bAbs - aAbs;
            })
            .slice(0, 4);
        }

        return [];
      }

      function renderCoreFactors() {
        coreFactorsEl.textContent = "";
        if (!state.coreFactors.length) {
          const empty = document.createElement("li");
          empty.textContent = "Noch keine Faktoren verfügbar.";
          coreFactorsEl.appendChild(empty);
          return;
        }

        state.coreFactors.forEach((factor) => {
          const item = document.createElement("li");
          const contributionText =
            factor.contribution == null
              ? "n/a"
              : `${factor.contribution >= 0 ? "+" : ""}${factor.contribution.toFixed(3)}`;
          item.textContent = `${factor.key} (${factor.direction}, ${contributionText}) — ${factor.reason} [${factor.source}]`;
          coreFactorsEl.appendChild(item);
        });
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

        inputMeta.textContent = state.lastInput ? `Input: ${state.lastInput}` : "Input: —";

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

        renderCoreFactors();
      }

      function setMapMarker(lat, lon) {
        const latRatio = (lat - CH_BOUNDS.latMin) / (CH_BOUNDS.latMax - CH_BOUNDS.latMin);
        const lonRatio = (lon - CH_BOUNDS.lonMin) / (CH_BOUNDS.lonMax - CH_BOUNDS.lonMin);
        mapMarker.hidden = false;
        mapMarker.style.left = `${clamp(lonRatio * 100, 0, 100)}%`;
        mapMarker.style.top = `${clamp((1 - latRatio) * 100, 0, 100)}%`;
        clickHint.textContent = `Letzter Klick: lat ${formatCoord(lat)}, lon ${formatCoord(lon)}`;
      }

      function mapEventToCoordinates(event) {
        const rect = mapSurface.getBoundingClientRect();
        const x = clamp(event.clientX - rect.left, 0, rect.width);
        const y = clamp(event.clientY - rect.top, 0, rect.height);
        const xRatio = rect.width > 0 ? x / rect.width : 0.5;
        const yRatio = rect.height > 0 ? y / rect.height : 0.5;

        const lon = CH_BOUNDS.lonMin + xRatio * (CH_BOUNDS.lonMax - CH_BOUNDS.lonMin);
        const lat = CH_BOUNDS.latMax - yRatio * (CH_BOUNDS.latMax - CH_BOUNDS.latMin);
        return { lat, lon };
      }

      function timeoutSecondsForMode(mode) {
        const normalized = String(mode || "basic").trim().toLowerCase();
        if (normalized === "extended") {
          return 30;
        }
        if (normalized === "risk") {
          return 40;
        }
        return 20;
      }

      async function runAnalyze(payload, token) {
        const headers = { "Content-Type": "application/json" };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const timeoutSeconds = Number(payload && payload.timeout_seconds);
        const timeoutMs = Number.isFinite(timeoutSeconds) && timeoutSeconds > 0
          ? Math.round(timeoutSeconds * 1000) + 1500
          : 25000;

        const controller = new AbortController();
        const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

        let response;
        try {
          response = await fetch("/analyze", {
            method: "POST",
            headers,
            body: JSON.stringify(payload),
            signal: controller.signal,
          });
        } catch (error) {
          if (error && error.name === "AbortError") {
            throw new Error(`timeout: Anfrage nach ${Math.max(1, Math.round(timeoutMs / 1000))}s ohne Antwort abgebrochen`);
          }
          throw error;
        } finally {
          clearTimeout(timeoutHandle);
        }

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

      function buildAnalyzePayload(base) {
        const mode = String(modeEl.value || "basic").trim().toLowerCase() || "basic";
        return {
          ...base,
          intelligence_mode: mode,
          timeout_seconds: timeoutSecondsForMode(mode),
          options: {
            response_mode: "compact",
          },
        };
      }

      async function startAnalyze(payload, inputLabel) {
        state.phase = "loading";
        state.lastError = null;
        state.lastPayload = { ok: false, loading: true, request: payload };
        state.lastRequestId = null;
        state.lastInput = inputLabel;
        state.coreFactors = [];
        submitBtn.disabled = true;
        renderState();

        try {
          const result = await runAnalyze(payload, (tokenEl.value || "").trim());
          state.lastRequestId = result.requestId;
          state.lastPayload = result.response;
          state.phase = result.ok ? "success" : "error";
          state.lastError = result.errorMessage;
          state.coreFactors = result.ok ? extractCoreFactors(result.response) : [];
        } catch (error) {
          state.phase = "error";
          state.lastError = error instanceof Error ? error.message : "Netzwerkfehler";
          state.lastPayload = {
            ok: false,
            error: "network_error",
            message: state.lastError,
          };
          state.coreFactors = [];
        } finally {
          submitBtn.disabled = false;
          renderState();
        }
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
          state.lastInput = null;
          state.coreFactors = [];
          renderState();
          return;
        }

        const payload = buildAnalyzePayload({ query });
        await startAnalyze(payload, `Adresse: ${query}`);
      });

      mapSurface.addEventListener("click", async (event) => {
        const { lat, lon } = mapEventToCoordinates(event);
        setMapMarker(lat, lon);
        const payload = buildAnalyzePayload({
          coordinates: {
            lat: Number(lat.toFixed(6)),
            lon: Number(lon.toFixed(6)),
            snap_mode: "ch_bounds",
          },
        });
        await startAnalyze(payload, `Kartenpunkt: ${formatCoord(lat)}, ${formatCoord(lon)}`);
      });

      mapSurface.addEventListener("keydown", async (event) => {
        if (event.key !== "Enter" && event.key !== " ") {
          return;
        }
        event.preventDefault();
        const simulatedEvent = {
          clientX: mapSurface.getBoundingClientRect().left + mapSurface.clientWidth / 2,
          clientY: mapSurface.getBoundingClientRect().top + mapSurface.clientHeight / 2,
        };
        const { lat, lon } = mapEventToCoordinates(simulatedEvent);
        setMapMarker(lat, lon);
        const payload = buildAnalyzePayload({
          coordinates: {
            lat: Number(lat.toFixed(6)),
            lon: Number(lon.toFixed(6)),
            snap_mode: "ch_bounds",
          },
        });
        await startAnalyze(payload, `Kartenpunkt (Keyboard): ${formatCoord(lat)}, ${formatCoord(lon)}`);
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
