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
        min-height: 320px;
        border: 1px solid var(--border);
        border-radius: 0.65rem;
        overflow: hidden;
        background: #dfe8f5;
        cursor: grab;
        touch-action: none;
      }
      .map-surface.dragging {
        cursor: grabbing;
      }
      .map-tile-layer {
        position: absolute;
        inset: 0;
      }
      .map-tile {
        position: absolute;
        width: 256px;
        height: 256px;
        user-select: none;
        -webkit-user-drag: none;
        pointer-events: none;
      }
      .map-crosshair {
        position: absolute;
        left: 50%;
        top: 50%;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        border: 2px solid rgba(14, 62, 122, 0.5);
        transform: translate(-50%, -50%);
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
      .map-status {
        font-size: 0.84rem;
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
              id="map-click-surface"
              class="map-surface"
              role="application"
              tabindex="0"
              aria-label="Interaktive Karte: ziehen zum Verschieben, Mausrad für Zoom, Klick für Koordinatenanalyse"
            >
              <div id="map-tile-layer" class="map-tile-layer" aria-hidden="true"></div>
              <div class="map-crosshair" aria-hidden="true"></div>
              <div id="map-click-marker" class="map-marker" hidden></div>
            </div>
            <div class="map-legend">
              <small id="map-view-meta">Zoom 8 · Zentrum 46.818200, 8.227500</small>
              <small id="click-hint">Noch kein Kartenpunkt gewählt.</small>
            </div>
            <div class="map-legend">
              <small>Tiles: © OpenStreetMap contributors · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">ODbL/Attribution</a></small>
              <small>Analyze-Payload nutzt <code>coordinates.lat/lon</code> + <code>snap_mode=ch_bounds</code>.</small>
            </div>
            <div id="map-status" class="placeholder map-status" hidden></div>
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
      const TILE_SIZE = 256;
      const MIN_ZOOM = 6;
      const MAX_ZOOM = 17;
      const INITIAL_MAP_VIEW = {
        lat: 46.8182,
        lon: 8.2275,
        zoom: 8,
      };

      const state = {
        phase: "idle",
        lastRequestId: null,
        lastPayload: null,
        lastError: null,
        lastInput: null,
        coreFactors: [],
      };

      const mapState = {
        centerLat: INITIAL_MAP_VIEW.lat,
        centerLon: INITIAL_MAP_VIEW.lon,
        zoom: INITIAL_MAP_VIEW.zoom,
        marker: null,
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
      const mapTileLayer = document.getElementById("map-tile-layer");
      const mapMarker = document.getElementById("map-click-marker");
      const mapStatus = document.getElementById("map-status");
      const mapViewMeta = document.getElementById("map-view-meta");
      const clickHint = document.getElementById("click-hint");

      let mapRenderToken = 0;

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

      function clampLatToMercator(lat) {
        return clamp(lat, -85.05112878, 85.05112878);
      }

      function clampMapCenter(lat, lon) {
        return {
          lat: clamp(clampLatToMercator(lat), CH_BOUNDS.latMin - 0.85, CH_BOUNDS.latMax + 0.85),
          lon: clamp(lon, CH_BOUNDS.lonMin - 1.25, CH_BOUNDS.lonMax + 1.25),
        };
      }

      function worldSize(zoom) {
        return TILE_SIZE * Math.pow(2, zoom);
      }

      function lonToWorldX(lon, zoom) {
        return ((lon + 180) / 360) * worldSize(zoom);
      }

      function latToWorldY(lat, zoom) {
        const clampedLat = clampLatToMercator(lat);
        const radians = (clampedLat * Math.PI) / 180;
        const mercator = Math.log(Math.tan(Math.PI / 4 + radians / 2));
        return (0.5 - mercator / (2 * Math.PI)) * worldSize(zoom);
      }

      function worldXToLon(worldX, zoom) {
        return (worldX / worldSize(zoom)) * 360 - 180;
      }

      function worldYToLat(worldY, zoom) {
        const normalized = 0.5 - worldY / worldSize(zoom);
        return (360 / Math.PI) * Math.atan(Math.exp(normalized * 2 * Math.PI)) - 90;
      }

      function latLonToWorld(lat, lon, zoom) {
        return {
          x: lonToWorldX(lon, zoom),
          y: latToWorldY(lat, zoom),
        };
      }

      function wrapWorldDeltaX(delta, size) {
        let wrapped = delta;
        while (wrapped > size / 2) wrapped -= size;
        while (wrapped < -size / 2) wrapped += size;
        return wrapped;
      }

      function centerWorld(zoomOverride) {
        const zoom = Number.isFinite(zoomOverride) ? zoomOverride : mapState.zoom;
        return latLonToWorld(mapState.centerLat, mapState.centerLon, zoom);
      }

      function containerPointToLatLon(x, y) {
        const width = Math.max(1, mapSurface.clientWidth);
        const height = Math.max(1, mapSurface.clientHeight);
        const center = centerWorld();
        const size = worldSize(mapState.zoom);

        let worldX = center.x + (x - width / 2);
        worldX = ((worldX % size) + size) % size;

        const worldY = clamp(center.y + (y - height / 2), 0, size - 1);

        return {
          lat: worldYToLat(worldY, mapState.zoom),
          lon: worldXToLon(worldX, mapState.zoom),
        };
      }

      function centerToContainerPoint(lat, lon) {
        const width = Math.max(1, mapSurface.clientWidth);
        const height = Math.max(1, mapSurface.clientHeight);
        const center = centerWorld();
        const point = latLonToWorld(lat, lon, mapState.zoom);
        const size = worldSize(mapState.zoom);

        const dx = wrapWorldDeltaX(point.x - center.x, size);
        const dy = point.y - center.y;

        return {
          x: width / 2 + dx,
          y: height / 2 + dy,
        };
      }

      function updateMapViewMeta() {
        mapViewMeta.textContent = `Zoom ${mapState.zoom} · Zentrum ${formatCoord(mapState.centerLat)}, ${formatCoord(mapState.centerLon)}`;
      }

      function setMapStatus(message) {
        if (!message) {
          mapStatus.hidden = true;
          mapStatus.textContent = "";
          return;
        }
        mapStatus.hidden = false;
        mapStatus.textContent = message;
      }

      function clearMapStatus() {
        setMapStatus("");
      }

      function normalizeTileX(tileX, zoom) {
        const modulo = Math.pow(2, zoom);
        return ((tileX % modulo) + modulo) % modulo;
      }

      function buildOsmTileUrl(zoom, tileX, tileY) {
        return `https://tile.openstreetmap.org/${zoom}/${tileX}/${tileY}.png`;
      }

      function updateMarkerPosition() {
        if (!mapState.marker) {
          mapMarker.hidden = true;
          return;
        }

        const point = centerToContainerPoint(mapState.marker.lat, mapState.marker.lon);
        mapMarker.hidden = false;
        mapMarker.style.left = `${point.x}px`;
        mapMarker.style.top = `${point.y}px`;
      }

      function renderTiles() {
        const width = Math.max(1, mapSurface.clientWidth);
        const height = Math.max(1, mapSurface.clientHeight);
        const zoom = mapState.zoom;
        const center = centerWorld();

        const topLeftX = center.x - width / 2;
        const topLeftY = center.y - height / 2;

        const minTileX = Math.floor(topLeftX / TILE_SIZE) - 1;
        const maxTileX = Math.floor((topLeftX + width) / TILE_SIZE) + 1;
        const minTileY = Math.floor(topLeftY / TILE_SIZE) - 1;
        const maxTileY = Math.floor((topLeftY + height) / TILE_SIZE) + 1;
        const maxTileIndex = Math.pow(2, zoom) - 1;

        const token = ++mapRenderToken;
        mapTileLayer.textContent = "";

        const fragment = document.createDocumentFragment();
        let tileCount = 0;
        let loaded = 0;
        let failed = 0;

        const maybeFinalize = () => {
          if (token !== mapRenderToken) {
            return;
          }
          if (loaded + failed < tileCount) {
            return;
          }
          if (tileCount > 0 && loaded === 0 && failed > 0) {
            setMapStatus("Karten-Tiles konnten nicht geladen werden. Analyse via coordinates.lat/lon bleibt verfügbar.");
            return;
          }
          clearMapStatus();
        };

        for (let tileX = minTileX; tileX <= maxTileX; tileX += 1) {
          for (let tileY = minTileY; tileY <= maxTileY; tileY += 1) {
            if (tileY < 0 || tileY > maxTileIndex) {
              continue;
            }

            tileCount += 1;
            const img = document.createElement("img");
            img.className = "map-tile";
            img.alt = "";
            img.decoding = "async";
            img.loading = "eager";
            img.draggable = false;
            img.style.left = `${tileX * TILE_SIZE - topLeftX}px`;
            img.style.top = `${tileY * TILE_SIZE - topLeftY}px`;
            img.width = TILE_SIZE;
            img.height = TILE_SIZE;

            img.addEventListener(
              "load",
              () => {
                loaded += 1;
                maybeFinalize();
              },
              { once: true }
            );
            img.addEventListener(
              "error",
              () => {
                failed += 1;
                maybeFinalize();
              },
              { once: true }
            );

            img.src = buildOsmTileUrl(zoom, normalizeTileX(tileX, zoom), tileY);
            fragment.appendChild(img);
          }
        }

        mapTileLayer.appendChild(fragment);
        updateMapViewMeta();
        updateMarkerPosition();
        maybeFinalize();
      }

      function setMapCenter(lat, lon, { render = true } = {}) {
        const bounded = clampMapCenter(lat, lon);
        mapState.centerLat = bounded.lat;
        mapState.centerLon = bounded.lon;
        if (render) {
          renderTiles();
        }
      }

      function setMapCenterFromWorld(worldX, worldY, { render = true } = {}) {
        const size = worldSize(mapState.zoom);
        const wrappedX = ((worldX % size) + size) % size;
        const clampedY = clamp(worldY, 0, size - 1);
        setMapCenter(worldYToLat(clampedY, mapState.zoom), worldXToLon(wrappedX, mapState.zoom), { render });
      }

      function panMapByPixels(dx, dy) {
        const center = centerWorld();
        setMapCenterFromWorld(center.x - dx, center.y - dy, { render: true });
      }

      function zoomMapAtPoint(delta, clientX, clientY) {
        const targetZoom = clamp(mapState.zoom + delta, MIN_ZOOM, MAX_ZOOM);
        if (targetZoom === mapState.zoom) {
          return;
        }

        const rect = mapSurface.getBoundingClientRect();
        const x = clamp(clientX - rect.left, 0, rect.width);
        const y = clamp(clientY - rect.top, 0, rect.height);

        const focus = containerPointToLatLon(x, y);
        mapState.zoom = targetZoom;

        const focusWorld = latLonToWorld(focus.lat, focus.lon, targetZoom);
        const width = Math.max(1, mapSurface.clientWidth);
        const height = Math.max(1, mapSurface.clientHeight);
        const nextCenterWorldX = focusWorld.x - (x - width / 2);
        const nextCenterWorldY = focusWorld.y - (y - height / 2);

        setMapCenterFromWorld(nextCenterWorldX, nextCenterWorldY, { render: true });
      }

      function setMapMarker(lat, lon) {
        mapState.marker = {
          lat: clampLatToMercator(lat),
          lon,
        };
        updateMarkerPosition();
        clickHint.textContent = `Letzter Klick: lat ${formatCoord(lat)}, lon ${formatCoord(lon)}`;
      }

      function mapEventToCoordinates(event) {
        const rect = mapSurface.getBoundingClientRect();
        const x = clamp(event.clientX - rect.left, 0, rect.width);
        const y = clamp(event.clientY - rect.top, 0, rect.height);
        return containerPointToLatLon(x, y);
      }

      async function analyzeFromMap(lat, lon, inputLabel) {
        const payload = buildAnalyzePayload({
          coordinates: {
            lat: Number(lat.toFixed(6)),
            lon: Number(lon.toFixed(6)),
            snap_mode: "ch_bounds",
          },
        });
        await startAnalyze(payload, inputLabel);
      }

      function initializeInteractiveMap() {
        const dragState = {
          active: false,
          pointerId: null,
          startX: 0,
          startY: 0,
          startCenterX: 0,
          startCenterY: 0,
          moved: false,
        };
        let suppressNextClick = false;

        mapSurface.addEventListener("pointerdown", (event) => {
          if (event.button !== 0) {
            return;
          }
          dragState.active = true;
          dragState.pointerId = event.pointerId;
          dragState.startX = event.clientX;
          dragState.startY = event.clientY;
          const center = centerWorld();
          dragState.startCenterX = center.x;
          dragState.startCenterY = center.y;
          dragState.moved = false;
          mapSurface.classList.add("dragging");
          mapSurface.setPointerCapture(event.pointerId);
        });

        mapSurface.addEventListener("pointermove", (event) => {
          if (!dragState.active || event.pointerId !== dragState.pointerId) {
            return;
          }
          const dx = event.clientX - dragState.startX;
          const dy = event.clientY - dragState.startY;
          if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
            dragState.moved = true;
          }
          setMapCenterFromWorld(dragState.startCenterX - dx, dragState.startCenterY - dy, { render: true });
        });

        const endDrag = (event) => {
          if (!dragState.active || event.pointerId !== dragState.pointerId) {
            return;
          }
          mapSurface.classList.remove("dragging");
          mapSurface.releasePointerCapture(event.pointerId);
          dragState.active = false;
          if (dragState.moved) {
            suppressNextClick = true;
            setTimeout(() => {
              suppressNextClick = false;
            }, 0);
          }
        };

        mapSurface.addEventListener("pointerup", endDrag);
        mapSurface.addEventListener("pointercancel", endDrag);

        mapSurface.addEventListener("click", async (event) => {
          if (suppressNextClick) {
            return;
          }
          const { lat, lon } = mapEventToCoordinates(event);
          setMapMarker(lat, lon);
          await analyzeFromMap(lat, lon, `Kartenpunkt: ${formatCoord(lat)}, ${formatCoord(lon)}`);
        });

        mapSurface.addEventListener(
          "wheel",
          (event) => {
            event.preventDefault();
            const direction = event.deltaY < 0 ? 1 : -1;
            zoomMapAtPoint(direction, event.clientX, event.clientY);
          },
          { passive: false }
        );

        mapSurface.addEventListener("keydown", async (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            const lat = mapState.centerLat;
            const lon = mapState.centerLon;
            setMapMarker(lat, lon);
            await analyzeFromMap(lat, lon, `Kartenpunkt (Keyboard): ${formatCoord(lat)}, ${formatCoord(lon)}`);
            return;
          }

          if (event.key === "ArrowUp") {
            event.preventDefault();
            panMapByPixels(0, -90);
            return;
          }
          if (event.key === "ArrowDown") {
            event.preventDefault();
            panMapByPixels(0, 90);
            return;
          }
          if (event.key === "ArrowLeft") {
            event.preventDefault();
            panMapByPixels(-90, 0);
            return;
          }
          if (event.key === "ArrowRight") {
            event.preventDefault();
            panMapByPixels(90, 0);
            return;
          }
          if (event.key === "+" || event.key === "=") {
            event.preventDefault();
            const rect = mapSurface.getBoundingClientRect();
            zoomMapAtPoint(1, rect.left + rect.width / 2, rect.top + rect.height / 2);
            return;
          }
          if (event.key === "-") {
            event.preventDefault();
            const rect = mapSurface.getBoundingClientRect();
            zoomMapAtPoint(-1, rect.left + rect.width / 2, rect.top + rect.height / 2);
          }
        });

        window.addEventListener("resize", () => {
          renderTiles();
        });

        renderTiles();
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

      initializeInteractiveMap();
      renderState();
    </script>
  </body>
</html>
"""


def render_gui_mvp_html(*, app_version: str) -> str:
    """Render das statische GUI-MVP-HTML mit sicher escaped Version."""

    safe_version = escape(app_version or "dev")
    return _GUI_MVP_HTML_TEMPLATE.replace("__APP_VERSION__", safe_version)
