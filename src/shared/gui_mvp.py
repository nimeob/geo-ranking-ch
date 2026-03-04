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
        --touch-target-min: 44px;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        background: var(--bg);
        color: var(--ink);
      }
      body.burger-open {
        overflow: hidden;
        touch-action: none;
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
        padding: 0.5rem 0.75rem;
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
      .burger-backdrop {
        position: fixed;
        inset: 0;
        border: 0;
        margin: 0;
        padding: 0;
        background: rgba(15, 23, 42, 0.28);
        z-index: 24;
      }
      .burger-menu[hidden],
      .burger-backdrop[hidden] {
        display: none !important;
      }
      .burger-menu a {
        display: inline-flex;
        align-items: center;
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
      main {
        display: grid;
        grid-template-columns: minmax(300px, 460px) minmax(360px, 1fr);
        gap: 1rem;
        padding: 1rem 1.25rem 1.5rem;
      }
      @media (max-width: 960px) {
        main { grid-template-columns: 1fr; }
      }
      main > section {
        min-width: 0;
      }
      .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.85rem;
        padding: 1rem;
        min-width: 0;
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
      input[type="checkbox"],
      input[type="radio"] {
        width: 1.05rem;
        height: 1.05rem;
        min-width: 1.05rem;
        min-height: 1.05rem;
        margin: 0;
        padding: 0;
      }
      .touch-toggle {
        display: flex;
        align-items: center;
        gap: 0.5rem;
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
      .request-id-row {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        flex-wrap: wrap;
      }
      .request-id-value {
        margin: 0;
        border: 1px solid var(--border);
        background: #f8faff;
        border-radius: 0.45rem;
        padding: 0.25rem 0.5rem;
        font-size: 0.84rem;
      }
      .trace-link-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        text-decoration: none;
        border: 1px solid var(--border);
        color: var(--primary);
        border-radius: 0.45rem;
        padding: 0.28rem 0.5rem;
        font-size: 0.82rem;
        background: #f9fbff;
      }
      .copy-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: #fff;
        color: var(--ink);
        border-color: var(--border);
        padding: 0.35rem 0.55rem;
        font-size: 0.82rem;
      }
      .copy-feedback-error {
        color: var(--danger);
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
        min-width: 0;
      }
      .map-surface {
        position: relative;
        width: 100%;
        min-width: 0;
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
        overflow: hidden;
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
        width: 12px;
        height: 12px;
        border-radius: 50%;
        border: 2px solid rgba(14, 62, 122, 0.55);
        background: rgba(255, 255, 255, 0.65);
        box-shadow: 0 1px 3px rgba(27, 38, 55, 0.18);
        transform: translate(-50%, -50%);
        pointer-events: none;
      }
      .map-surface.has-marker .map-crosshair {
        opacity: 0.28;
      }
      .map-marker {
        position: absolute;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 3px solid rgba(255, 255, 255, 0.95);
        background: #bd2f24;
        box-shadow:
          0 0 0 3px rgba(189, 47, 36, 0.22),
          0 2px 6px rgba(27, 38, 55, 0.22);
        transform: translate(-50%, -50%);
        pointer-events: none;
      }
      .map-user-accuracy {
        position: absolute;
        border-radius: 50%;
        border: 1px solid rgba(40, 96, 181, 0.45);
        background: rgba(40, 96, 181, 0.16);
        transform: translate(-50%, -50%);
        pointer-events: none;
      }
      .map-user-marker {
        position: absolute;
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 2px solid rgba(255, 255, 255, 0.95);
        background: #1f66cf;
        box-shadow:
          0 0 0 3px rgba(31, 102, 207, 0.25),
          0 2px 5px rgba(27, 38, 55, 0.18);
        transform: translate(-50%, -50%);
        pointer-events: none;
      }
      .map-locate-btn {
        background: #ffffff;
        color: #16365f;
        border-color: rgba(27, 38, 55, 0.28);
      }
      .map-locate-btn:hover {
        border-color: rgba(27, 38, 55, 0.42);
        background: #f7fbff;
      }
      .map-locate-btn[disabled] {
        color: var(--muted);
      }
      .map-zoom-controls {
        position: absolute;
        top: 0.55rem;
        right: 0.55rem;
        display: grid;
        gap: 0.35rem;
        z-index: 3;
      }
      .map-zoom-btn {
        width: 2.2rem;
        height: 2.2rem;
        padding: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 0.55rem;
        border: 1px solid rgba(27, 38, 55, 0.2);
        background: rgba(255, 255, 255, 0.94);
        color: #16365f;
        font-size: 1.05rem;
        font-weight: 700;
        line-height: 1;
      }
      .map-zoom-btn:hover {
        background: #ffffff;
        border-color: rgba(27, 38, 55, 0.35);
      }
      .map-zoom-btn:focus-visible {
        outline: 2px solid #91b2ff;
        outline-offset: 1px;
      }
      .map-legend {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        align-items: flex-start;
        gap: 0.35rem 0.6rem;
        line-height: 1.25;
      }
      .map-legend > * {
        min-width: 0;
      }
      .map-legend small {
        color: var(--muted);
        font-size: 0.86rem;
        overflow-wrap: anywhere;
      }
      .map-legend small + small {
        text-align: right;
      }
      .map-legend code {
        font-size: 0.86em;
        overflow-wrap: anywhere;
        word-break: break-word;
      }
      @media (max-width: 680px) {
        .map-legend {
          grid-template-columns: 1fr;
        }
        .map-legend small + small {
          text-align: left;
        }
      }
      @media (max-width: 768px) {
        #burger-btn,
        .burger-menu a,
        button,
        select,
        input:not([type="checkbox"]):not([type="radio"]),
        .trace-link-btn,
        .copy-btn,
        .touch-toggle {
          min-height: var(--touch-target-min);
        }
        .map-zoom-btn {
          width: var(--touch-target-min);
          height: var(--touch-target-min);
        }
      }
      @media (max-width: 520px) {
        .map-surface {
          min-height: 280px;
        }
        .map-crosshair {
          width: 14px;
          height: 14px;
        }
        .map-marker {
          width: 22px;
          height: 22px;
          border-width: 3px;
          box-shadow:
            0 0 0 3px rgba(189, 47, 36, 0.22),
            0 3px 8px rgba(27, 38, 55, 0.26);
        }
        .map-legend {
          gap: 0.25rem;
        }
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
      .grid-3 {
        display: grid;
        gap: 0.65rem;
        grid-template-columns: 1fr 1fr 1fr;
      }
      @media (max-width: 960px) {
        .grid-3 { grid-template-columns: 1fr; }
      }
      .results-filters-sticky {
        position: relative;
        z-index: 0;
      }
      .results-filters-toggle {
        display: none;
      }
      .results-filters-toggle-indicator {
        color: var(--muted);
        font-size: 0.8rem;
      }
      .results-filters-panel {
        display: grid;
        gap: 0;
      }
      .results-filters-actions {
        display: grid;
        gap: 0.6rem;
        margin-top: 0.85rem;
      }
      .results-filters-actions-primary {
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
      }
      .results-filters-actions-secondary {
        display: flex;
        gap: 0.6rem;
        align-items: center;
        flex-wrap: wrap;
      }
      .results-filters-actions .copy-btn {
        min-height: 2rem;
      }
      @media (max-width: 768px) {
        .results-filters-sticky {
          position: sticky;
          top: 0.5rem;
          z-index: 7;
          padding: 0.55rem;
          border: 1px solid var(--border);
          border-radius: 0.72rem;
          background: var(--surface);
          box-shadow: 0 8px 20px rgba(27, 38, 55, 0.08);
          margin-bottom: 0.75rem;
        }
        .results-filters-toggle {
          width: 100%;
          display: inline-flex;
          justify-content: space-between;
          align-items: center;
          background: #fff;
          color: var(--ink);
          border-color: var(--border);
          font-size: 0.86rem;
          padding: 0.42rem 0.56rem;
        }
        .results-filters-shell[data-collapsed="true"] .results-filters-panel {
          display: none;
        }
        .results-filters-shell[data-collapsed="false"] .results-filters-panel {
          margin-top: 0.55rem;
          max-height: min(68svh, 27rem);
          overflow-y: auto;
          overscroll-behavior: contain;
          -webkit-overflow-scrolling: touch;
          --results-filters-action-reserve: calc(var(--touch-target-min) * 2 + 2.6rem);
          padding-bottom: calc(
            env(safe-area-inset-bottom, 0px)
            + var(--results-filters-keyboard-offset, 0px)
            + var(--results-filters-action-reserve)
          );
        }
        .results-filters-actions {
          position: sticky;
          bottom: 0;
          z-index: 1;
          margin-top: 0.75rem;
          margin-bottom: -0.1rem;
          padding-top: 0.45rem;
          padding-bottom: calc(env(safe-area-inset-bottom, 0px) + var(--results-filters-keyboard-offset, 0px));
          border-top: 1px solid rgba(27, 38, 55, 0.09);
          background: linear-gradient(180deg, rgba(255, 255, 255, 0.86) 0%, #fff 35%);
        }
        .results-filters-actions-primary {
          display: grid;
          gap: 0.5rem;
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .results-filters-actions-secondary {
          gap: 0.5rem;
          justify-content: space-between;
        }
        .results-filters-actions .copy-btn {
          min-height: var(--touch-target-min);
        }
        .results-filters-actions-secondary .meta {
          flex: 1 1 100%;
          margin: 0;
        }
      }
      .results-table {
        width: 100%;
        border-collapse: collapse;
      }
      .results-table th,
      .results-table td {
        padding: 0.45rem 0.5rem;
        border-bottom: 1px solid var(--border);
        text-align: left;
        vertical-align: top;
      }
      .results-table th {
        color: var(--muted);
        font-weight: 600;
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.02em;
      }
      .results-table td {
        font-size: 0.86rem;
      }
      .results-table td code {
        font-size: 0.82rem;
      }
      .results-table .actions {
        white-space: nowrap;
      }
      .results-row-actions {
        display: inline-flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.45rem;
      }
      .results-row-actions .copy-btn,
      .results-row-actions .trace-link-btn {
        min-height: 2rem;
        padding: 0.35rem 0.62rem;
      }
      .results-table-shell {
        overflow: auto;
        margin-top: 0.65rem;
        min-height: 12.25rem;
        scroll-margin-top: 5rem;
      }
      .results-empty-cell {
        padding: 0;
      }
      .results-empty-state {
        display: grid;
        gap: 0.5rem;
        align-content: center;
        min-height: 10.5rem;
        padding: 1rem 0.9rem;
      }
      .results-empty-title {
        margin: 0;
        font-size: 0.95rem;
        color: var(--ink);
      }
      .results-empty-copy {
        margin: 0;
        color: var(--muted);
        font-size: 0.86rem;
        line-height: 1.35;
      }
      .results-empty-action {
        justify-self: flex-start;
      }
      .results-loading-state {
        position: relative;
      }
      .results-loading-spinner {
        width: 1.25rem;
        height: 1.25rem;
        border-radius: 999px;
        border: 2px solid #d9e3ff;
        border-top-color: #2f6fed;
        animation: results-loading-spin 0.8s linear infinite;
      }
      .results-error-state {
        border-left: 3px solid #b84c00;
        background: #fff7ed;
        border-radius: 0.45rem;
      }
      @keyframes results-loading-spin {
        from {
          transform: rotate(0deg);
        }
        to {
          transform: rotate(360deg);
        }
      }
      @media (max-width: 768px) {
        .results-table .actions {
          white-space: normal;
        }
        .results-row-actions {
          width: 100%;
          gap: 0.55rem;
        }
        .results-row-actions .copy-btn,
        .results-row-actions .trace-link-btn {
          min-height: var(--touch-target-min);
          padding: 0.5rem 0.78rem;
        }
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
      .session-warning {
        border: 1px solid #f0d8a8;
        border-left: 4px solid #c27a00;
        background: #fff9ed;
        border-radius: 0.55rem;
        color: #7a4a00;
        padding: 0.65rem 0.75rem;
        display: grid;
        gap: 0.55rem;
      }
      .session-warning button {
        justify-self: flex-start;
      }
      .error-view {
        border: 1px solid #f2c6c2;
        border-left: 4px solid var(--danger);
        background: #fff8f8;
        border-radius: 0.55rem;
        color: #7a201a;
        padding: 0.75rem;
        display: grid;
        gap: 0.45rem;
      }
      .error-view-title {
        margin: 0;
        font-size: 0.95rem;
        color: #7a201a;
      }
      .error-view-copy {
        margin: 0;
        font-size: 0.86rem;
        line-height: 1.4;
      }
      .error-view-meta {
        margin: 0;
        font-size: 0.8rem;
        color: #8a3a2f;
      }
      .error-view-retry {
        justify-self: flex-start;
      }
      .trace-timeline {
        margin: 0;
        padding-left: 1.15rem;
        display: grid;
        gap: 0.55rem;
      }
      .trace-event {
        display: grid;
        gap: 0.2rem;
      }
      .trace-event strong {
        font-size: 0.9rem;
      }
      .trace-event-meta {
        color: var(--muted);
        font-size: 0.82rem;
      }
      .trace-event-summary {
        font-size: 0.86rem;
      }
      .trace-event pre {
        margin-top: 0.3rem;
        max-height: 16rem;
        background: #f8faff;
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        padding: 0.5rem;
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
        <div class=\"burger\" id=\"burger-shell\">
          <button id=\"burger-btn\" type=\"button\" aria-haspopup=\"true\" aria-expanded=\"false\" aria-controls=\"burger-menu\" aria-label=\"Navigation umschalten\">☰ Menü</button>
          <div id=\"burger-menu\" class=\"burger-menu\" role=\"menu\" aria-label=\"Hauptnavigation\" aria-hidden=\"true\" hidden>
            <a role=\"menuitem\" href=\"/gui\">Abfrage</a>
            <a role=\"menuitem\" href=\"/history\">Historische Abfragen</a>
            <a role=\"menuitem\" href=\"#input\">Input</a>
            <a role=\"menuitem\" href=\"#map\">Karte</a>
            <a role=\"menuitem\" href=\"#result\">Result-Panel</a>
            <a role=\"menuitem\" href=\"#trace-debug\">Trace-Debug</a>
            <a role=\"menuitem\" id=\"burger-login-link\" href=\"__AUTH_LOGIN_ENDPOINT__\">Login</a>
            <a role=\"menuitem\" id=\"burger-logout-link\" href=\"__AUTH_LOGOUT_ENDPOINT__\">Logout</a>
          </div>
          <button id=\"burger-backdrop\" class=\"burger-backdrop\" type=\"button\" aria-hidden=\"true\" hidden></button>
        </div>
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
            <label>
              Intelligence-Mode
              <select id=\"intelligence-mode\" name=\"intelligence_mode\">
                <option value=\"basic\">basic</option>
                <option value=\"extended\">extended</option>
                <option value=\"risk\">risk</option>
              </select>
            </label>
            <p class=\"meta\">Auth im GUI-Flow läuft session-basiert über Login/Cookie (kein Bearer-Token-Eingabefeld).</p>
            <p class=\"meta\" id=\"auth-login-meta\">Nicht eingeloggt? <a id=\"auth-login-inline\" href=\"__AUTH_LOGIN_ENDPOINT__\">Login starten</a></p>
            <div id="session-expiry-warning" class="session-warning" hidden>
              <span id="session-expiry-warning-text">Session läuft bald ab.</span>
              <button id="session-expiry-warning-login" class="copy-btn" type="button">Jetzt neu anmelden</button>
            </div>
            <label class="touch-toggle">
              Async Mode (optional)
              <input id="async-mode-requested" type="checkbox" />
            </label>
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
              <div id="map-user-accuracy" class="map-user-accuracy" hidden></div>
              <div id="map-user-marker" class="map-user-marker" hidden></div>
              <div class="map-zoom-controls" aria-label="Zoom-Steuerung">
                <button id="map-zoom-in" class="map-zoom-btn" type="button" aria-label="Karte hineinzoomen">+</button>
                <button id="map-zoom-out" class="map-zoom-btn" type="button" aria-label="Karte herauszoomen">−</button>
              </div>
            </div>
            <div class="map-legend">
              <small id="map-view-meta">Zoom 8 · Zentrum 46.818200, 8.227500</small>
              <small id="click-hint">Noch kein Kartenpunkt gewählt.</small>
            </div>
            <div class="map-legend">
              <button id="map-locate-btn" class="copy-btn map-locate-btn" type="button">Aktuelle Position</button>
              <small id="map-location-meta">Noch keine Geräteposition gewählt.</small>
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
          <div class=\"stack\" aria-label=\"Request-ID Debug-Aktionen\">
            <div class=\"request-id-row\">
              <code id=\"request-id-value\" class=\"request-id-value\" aria-live=\"polite\">—</code>
              <a
                id=\"request-trace-link\"
                class=\"trace-link-btn\"
                href=\"#trace-debug\"
                aria-label=\"Trace-Debug für aktuelle Request-ID öffnen\"
                hidden
              >Trace ansehen</a>
              <button
                id=\"request-id-copy-btn\"
                class=\"copy-btn\"
                type=\"button\"
                aria-label=\"Aktuelle Request-ID in die Zwischenablage kopieren\"
                disabled
              >Copy ID</button>
            </div>
            <p class=\"meta\" id=\"request-id-feedback\" aria-live=\"polite\">Noch keine Request-ID vorhanden.</p>
          </div>
          <p class=\"meta\" id=\"input-meta\">Input: —</p>
          <div id="async-job-box" class="placeholder" hidden>
            <p class="meta" style="margin: 0 0 0.35rem;">Async Job (202 Accepted)</p>
            <div class="request-id-row">
              <code id="async-job-id" class="request-id-value">—</code>
              <a id="async-job-link" class="trace-link-btn" href="#" target="_self" rel="noopener noreferrer">Job ansehen</a>
              <a id="async-result-link" class="trace-link-btn" href="#" target="_self" rel="noopener noreferrer" hidden>Result öffnen</a>
            </div>
            <p class="meta" id="async-job-meta">Polling: off</p>
          </div>
          <section id="server-error-view" class="error-view" role="status" aria-live="polite" hidden>
            <h3 id="server-error-title" class="error-view-title">Temporärer Serverfehler (5xx)</h3>
            <p id="server-error-copy" class="error-view-copy">Die Analyse konnte nicht abgeschlossen werden. Bitte Retry versuchen.</p>
            <p id="server-error-meta" class="error-view-meta">Keine technischen Details verfügbar.</p>
            <button id="server-error-retry" class="copy-btn error-view-retry" type="button">Retry ausführen</button>
          </section>
          <div id="error-box" class="error-box" hidden></div>
        </article>

        <article class=\"card\">
          <h2>Kernfaktoren (Top)</h2>
          <ul id=\"core-factors\" class=\"factor-list\">
            <li>Noch keine Faktoren verfügbar.</li>
          </ul>
        </article>

        <article class=\"card\" id=\"results-list\">
          <h2>Ergebnisliste (dev)</h2>
          <p class=\"meta\">Sammelt erfolgreiche Analyse-Ergebnisse in dieser Session, um Varianten schnell zu vergleichen. Sortierung/Filter werden als Query-Params in der URL gespeichert.</p>
          <div id=\"results-filters-shell\" class=\"results-filters-shell results-filters-sticky\" data-collapsed=\"true\">
            <button
              id=\"results-filters-toggle\"
              class=\"results-filters-toggle copy-btn\"
              type=\"button\"
              aria-expanded=\"false\"
              aria-controls=\"results-filters-panel\"
            >
              <span>Filter & Sortierung</span>
              <span id=\"results-filters-toggle-indicator\" class=\"results-filters-toggle-indicator\">Ausgeblendet</span>
            </button>
            <div id=\"results-filters-panel\" class=\"results-filters-panel\" hidden>
              <div class=\"grid-3\" style=\"align-items: end;\">
                <label>
                  Sortierung
                  <select id=\"results-sort\">
                    <option value=\"score\">Score</option>
                    <option value=\"distance_m\">Distanz</option>
                    <option value=\"security_subscore\">Sicherheits-Subscore</option>
                  </select>
                </label>
                <label>
                  Richtung
                  <select id=\"results-dir\">
                    <option value=\"desc\">desc</option>
                    <option value=\"asc\">asc</option>
                  </select>
                </label>
                <label>
                  K.O.-Filter
                  <select id=\"results-ko\">
                    <option value=\"off\">off</option>
                    <option value=\"on\">on</option>
                  </select>
                </label>
              </div>
              <div class=\"grid-3\" style=\"align-items: end; margin-top: 0.65rem;\">
                <label>
                  Min Score
                  <input id=\"results-min-score\" type=\"number\" min=\"0\" max=\"100\" placeholder=\"\" />
                </label>
                <label>
                  Max Distanz (m)
                  <input id=\"results-max-distance\" type=\"number\" min=\"0\" max=\"5000\" placeholder=\"\" />
                </label>
                <label>
                  Min Sicherheits-Subscore
                  <input id=\"results-min-security\" type=\"number\" min=\"0\" max=\"100\" placeholder=\"\" />
                </label>
              </div>
              <div class=\"results-filters-actions\">
                <div class=\"results-filters-actions-primary\">
                  <button id=\"results-apply\" class=\"copy-btn\" type=\"button\">Filter anwenden</button>
                  <button id=\"results-reset\" class=\"copy-btn\" type=\"button\">Filter zurücksetzen</button>
                </div>
                <div class=\"results-filters-actions-secondary\">
                  <button id=\"results-clear\" class=\"copy-btn\" type=\"button\">Liste leeren</button>
                  <span class=\"meta\" id=\"results-meta\">Noch keine Ergebnisse gesammelt.</span>
                </div>
              </div>
            </div>
          </div>
          <div id=\"results-table-shell\" class=\"results-table-shell\">
            <table class=\"results-table\" aria-label=\"Ergebnisliste\">
              <thead>
                <tr>
                  <th>Zeit</th>
                  <th>Input</th>
                  <th>Score</th>
                  <th>Dist (m)</th>
                  <th>Sec</th>
                  <th class=\"actions\">Aktionen</th>
                </tr>
              </thead>
              <tbody id=\"results-body\"></tbody>
            </table>
          </div>
        </article>

        <article class=\"card\" id=\"history\">
          <h2>Historische Abfragen</h2>
          <p class=\"meta\">Letzte Ergebnisse (Deep-Link öffnet eine separate Result-Seite).</p>
          <div id=\"history-shell\" class=\"stack\">
            <div class=\"placeholder\">Lade Historie…</div>
          </div>
        </article>

        <article class=\"card\" id=\"trace-debug\">
          <h2>Trace-Debug-View</h2>
          <form id=\"trace-debug-form\" class=\"stack\">
            <label>
              request_id
              <input id=\"trace-request-id\" type=\"text\" placeholder=\"z. B. req-m8x4...\" />
            </label>
            <div class=\"grid-2\">
              <label>
                lookback_seconds (optional)
                <input id=\"trace-lookback-seconds\" type=\"number\" min=\"60\" max=\"604800\" placeholder=\"172800\" />
              </label>
              <label>
                max_events (optional)
                <input id=\"trace-max-events\" type=\"number\" min=\"1\" max=\"500\" placeholder=\"200\" />
              </label>
            </div>
            <button id=\"trace-submit-btn\" type=\"submit\">Trace laden</button>
          </form>
          <p class=\"pill\" id=\"trace-phase-pill\" data-phase=\"idle\">Trace-Status: idle</p>
          <p class=\"meta\" id=\"trace-meta\">Noch keine Trace-Abfrage gestartet.</p>
          <div id=\"trace-empty-box\" class=\"placeholder\" hidden></div>
          <div id=\"trace-error-box\" class=\"error-box\" hidden></div>
          <ol id=\"trace-timeline\" class=\"trace-timeline\">
            <li>Noch keine Trace-Events geladen.</li>
          </ol>
          <pre id=\"trace-json\">{\n  \"hint\": \"Deep-Link via /gui?view=trace&request_id=<id>\"\n}</pre>
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
      const UI_LOG_COMPONENT = "ui.gui_mvp";
      const UI_SESSION_STORAGE_KEY = "geo-ranking-ui-session-id";
      const JOB_IDS_STORAGE_KEY = "geo-ranking-ui-job-ids";
      const ANALYZE_DRAFT_STORAGE_KEY = "geo-ranking-ui-analyze-draft-v1";
      const SESSION_EXPIRY_WARNING_LEAD_MS = 120000;
      const AUTH_SESSION_POLL_INTERVAL_MS = 60000;
      const TRACE_DEBUG_ENDPOINT = "/debug/trace";
      const ANALYZE_JOBS_ENDPOINT_BASE = "/analyze/jobs";
      const ANALYZE_HISTORY_ENDPOINT = "/analyze/history";
      const AUTH_LOGIN_ENDPOINT = "__AUTH_LOGIN_ENDPOINT__";
      const AUTH_LOGOUT_ENDPOINT = "__AUTH_LOGOUT_ENDPOINT__";
      const AUTH_ME_ENDPOINT = "__AUTH_ME_ENDPOINT__";
      const AUTH_CHECK_CACHE_TTL_MS = 12000;
      const DEV_CLIENT_REQUEST_POLICY = Object.freeze({
        authCheckTimeoutMs: 4000,
        historyTimeoutMs: 12000,
        traceTimeoutMs: 12000,
        getRetries: 1,
        retryDelayMs: 250,
      });
      const SAFE_RETRY_METHODS = new Set(["GET"]);
      const SAFE_RETRY_STATUS_CODES = new Set([408, 429, 500, 502, 503, 504]);
      const RESULTS_LIST_COPY = Object.freeze({
        meta: {
          loading: "Ergebnisliste wird aktualisiert …",
          empty: "Keine sichtbaren Ergebnisse.",
          filtered: "0 Treffer – Filter aktiv.",
          network: "Ergebnisliste aktuell wegen Netzwerkproblem nicht verfügbar.",
          unauthorized: "Ergebnisliste benötigt eine gültige Anmeldung.",
          error: "Ergebnisliste konnte nicht aktualisiert werden. Retry möglich.",
        },
        emptyStates: {
          loading: {
            title: "Ergebnisliste lädt …",
            description: "Neue Ranking-Daten werden geladen. Bitte kurz warten.",
            action: "",
          },
          noData: {
            title: "Keine Daten in der aktuellen Auswahl",
            description: "Für den aktuellen Zeitraum oder die aktive Auswahl liegen keine Einträge vor.",
            action: "Filter zurücksetzen",
          },
          filtered: {
            title: "Keine Treffer mit aktuellen Filtern",
            description: "Es gibt Einträge in der Vision-Liste, aber die aktiven Filter blenden sie aus.",
            action: "Filter zurücksetzen",
          },
          network: {
            title: "Netzwerkproblem beim Laden der Ergebnisliste",
            description: "Die letzte Abfrage konnte wegen eines Netzwerkfehlers nicht geladen werden.",
            action: "Retry ausführen",
          },
          unauthorized: {
            title: "Session abgelaufen",
            description: "Für die Ergebnisliste ist eine gültige Anmeldung erforderlich.",
            action: "Login starten",
          },
          error: {
            title: "Ergebnisliste konnte nicht geladen werden",
            description: "Die letzte Aktualisierung ist fehlgeschlagen. Du kannst die Anfrage direkt erneut starten.",
            action: "Retry ausführen",
          },
        },
      });
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

      const DEV_ERROR_CLASS = Object.freeze({
        AUTH: "AUTH",
        NETWORK: "NETWORK",
        API: "API",
        UI: "UI",
      });
      const DEV_ERROR_CLASS_BY_CODE = Object.freeze({
        timeout: DEV_ERROR_CLASS.NETWORK,
        abort: DEV_ERROR_CLASS.NETWORK,
        network_error: DEV_ERROR_CLASS.NETWORK,
        invalid_json: DEV_ERROR_CLASS.API,
        validation: DEV_ERROR_CLASS.UI,
        unauthorized: DEV_ERROR_CLASS.AUTH,
        forbidden: DEV_ERROR_CLASS.AUTH,
        no_session_cookie: DEV_ERROR_CLASS.AUTH,
        session_not_found: DEV_ERROR_CLASS.AUTH,
        session_expired: DEV_ERROR_CLASS.AUTH,
        no_access_token: DEV_ERROR_CLASS.AUTH,
        no_refresh_token: DEV_ERROR_CLASS.AUTH,
        refresh_grant_error: DEV_ERROR_CLASS.AUTH,
        refresh_http_error: DEV_ERROR_CLASS.AUTH,
        refresh_network_error: DEV_ERROR_CLASS.AUTH,
        refresh_invalid_response: DEV_ERROR_CLASS.AUTH,
        refresh_missing_token: DEV_ERROR_CLASS.AUTH,
        token_error: DEV_ERROR_CLASS.AUTH,
        access_denied: DEV_ERROR_CLASS.AUTH,
        consent_denied: DEV_ERROR_CLASS.AUTH,
      });

      const state = {
        phase: "idle",
        lastRequestId: null,
        lastPayload: null,
        lastError: null,
        lastInput: null,
        coreFactors: [],
        lastAnalyzeRequest: null,
        serverErrorView: {
          visible: false,
          statusCode: null,
          errorCode: "",
          requestId: "",
          requestStartedAt: "",
        },
      };

      const resultsListState = {
        entries: [],
        sortKey: "score",
        sortDir: "desc",
        koFilter: "off",
        minScore: null,
        maxDistance: null,
        minSecurity: null,
        recoveryState: "",
        isLoading: false,
      };

      const resultsFiltersUiState = {
        isMobileViewport: false,
        collapsed: false,
      };

      const traceState = {
        phase: "idle",
        requestId: "",
        apiRequestId: "",
        payload: null,
        error: "",
        emptyMessage: "",
        events: [],
      };

      const mapState = {
        centerLat: INITIAL_MAP_VIEW.lat,
        centerLon: INITIAL_MAP_VIEW.lon,
        zoom: INITIAL_MAP_VIEW.zoom,
        marker: null,
        userLocation: null,
      };

      const authState = {
        authenticated: null,
        authCheckSupported: true,
        userClaims: {},
        checkedAtMs: 0,
        sessionExpiresAtMs: 0,
        warningShownForExpiryMs: 0,
      };

      const formEl = document.getElementById("analyze-form");
      const queryEl = document.getElementById("query");
      const modeEl = document.getElementById("intelligence-mode");
      const submitBtn = document.getElementById("submit-btn");
      const phasePill = document.getElementById("phase-pill");
      const requestMeta = document.getElementById("request-meta");
      const requestIdValueEl = document.getElementById("request-id-value");
      const requestTraceLinkEl = document.getElementById("request-trace-link");
      const requestIdCopyBtnEl = document.getElementById("request-id-copy-btn");
      const requestIdFeedbackEl = document.getElementById("request-id-feedback");
      const inputMeta = document.getElementById("input-meta");
      const historyShell = document.getElementById("history-shell");
      const errorBox = document.getElementById("error-box");
      const serverErrorViewEl = document.getElementById("server-error-view");
      const serverErrorTitleEl = document.getElementById("server-error-title");
      const serverErrorCopyEl = document.getElementById("server-error-copy");
      const serverErrorMetaEl = document.getElementById("server-error-meta");
      const serverErrorRetryBtnEl = document.getElementById("server-error-retry");
      const coreFactorsEl = document.getElementById("core-factors");
      const authLoginMetaEl = document.getElementById("auth-login-meta");
      const authLoginInlineEl = document.getElementById("auth-login-inline");
      const sessionExpiryWarningEl = document.getElementById("session-expiry-warning");
      const sessionExpiryWarningTextEl = document.getElementById("session-expiry-warning-text");
      const sessionExpiryWarningLoginBtnEl = document.getElementById("session-expiry-warning-login");

      const resultsFiltersShellEl = document.getElementById("results-filters-shell");
      const resultsFiltersToggleEl = document.getElementById("results-filters-toggle");
      const resultsFiltersToggleIndicatorEl = document.getElementById("results-filters-toggle-indicator");
      const resultsFiltersPanelEl = document.getElementById("results-filters-panel");
      const resultsSortEl = document.getElementById("results-sort");
      const resultsDirEl = document.getElementById("results-dir");
      const resultsKoEl = document.getElementById("results-ko");
      const resultsMinScoreEl = document.getElementById("results-min-score");
      const resultsMaxDistanceEl = document.getElementById("results-max-distance");
      const resultsMinSecurityEl = document.getElementById("results-min-security");
      const resultsApplyBtnEl = document.getElementById("results-apply");
      const resultsResetBtnEl = document.getElementById("results-reset");
      const resultsClearBtnEl = document.getElementById("results-clear");
      const resultsMetaEl = document.getElementById("results-meta");
      const resultsBodyEl = document.getElementById("results-body");

      const asyncModeRequestedEl = document.getElementById("async-mode-requested");
      const asyncJobBoxEl = document.getElementById("async-job-box");
      const asyncJobIdEl = document.getElementById("async-job-id");
      const asyncJobLinkEl = document.getElementById("async-job-link");
      const asyncResultLinkEl = document.getElementById("async-result-link");
      const asyncJobMetaEl = document.getElementById("async-job-meta");

      const traceFormEl = document.getElementById("trace-debug-form");
      const traceRequestIdEl = document.getElementById("trace-request-id");
      const traceLookbackSecondsEl = document.getElementById("trace-lookback-seconds");
      const traceMaxEventsEl = document.getElementById("trace-max-events");
      const traceSubmitBtn = document.getElementById("trace-submit-btn");
      const tracePhasePill = document.getElementById("trace-phase-pill");
      const traceMetaEl = document.getElementById("trace-meta");
      const traceEmptyBoxEl = document.getElementById("trace-empty-box");
      const traceErrorBoxEl = document.getElementById("trace-error-box");
      const traceTimelineEl = document.getElementById("trace-timeline");
      const traceJsonEl = document.getElementById("trace-json");

      const mapSurface = document.getElementById("map-click-surface");
      const mapTileLayer = document.getElementById("map-tile-layer");
      const mapMarker = document.getElementById("map-click-marker");
      const mapUserAccuracy = document.getElementById("map-user-accuracy");
      const mapUserMarker = document.getElementById("map-user-marker");
      const mapStatus = document.getElementById("map-status");
      const mapViewMeta = document.getElementById("map-view-meta");
      const clickHint = document.getElementById("click-hint");
      const mapLocateBtn = document.getElementById("map-locate-btn");
      const mapLocationMeta = document.getElementById("map-location-meta");
      const mapZoomInBtn = document.getElementById("map-zoom-in");
      const mapZoomOutBtn = document.getElementById("map-zoom-out");

      let mapRenderToken = 0;
      let uiEventSequence = 0;
      let requestIdFeedbackResetHandle = null;
      let authRecoveryRedirectScheduled = false;
      let authSessionPollHandle = null;

      function utcTimestamp() {
        return new Date().toISOString();
      }

      function createUiCorrelationId(prefix) {
        const normalizedPrefix = String(prefix || "ui").replace(/[^a-z0-9_-]/gi, "").toLowerCase() || "ui";
        const randomChunk = Math.random().toString(36).slice(2, 10);
        return `${normalizedPrefix}-${Date.now().toString(36)}-${randomChunk}`;
      }

      function resolveUiSessionId() {
        const fallbackSessionId = createUiCorrelationId("sess");
        if (typeof window === "undefined" || !window.sessionStorage) {
          return fallbackSessionId;
        }

        try {
          const existing = String(window.sessionStorage.getItem(UI_SESSION_STORAGE_KEY) || "").trim();
          if (existing) {
            return existing;
          }

          window.sessionStorage.setItem(UI_SESSION_STORAGE_KEY, fallbackSessionId);
          return fallbackSessionId;
        } catch (error) {
          return fallbackSessionId;
        }
      }

      const uiSessionId = resolveUiSessionId();

      function clearAnalyzeDraft() {
        try {
          if (typeof window !== "undefined" && window.sessionStorage) {
            window.sessionStorage.removeItem(ANALYZE_DRAFT_STORAGE_KEY);
          }
        } catch (error) {
          // ignore
        }
      }

      function persistAnalyzeDraft(reason = "manual") {
        try {
          if (typeof window === "undefined" || !window.sessionStorage) {
            return;
          }

          const draft = {
            query: String(queryEl && queryEl.value ? queryEl.value : "").trim(),
            mode: String(modeEl && modeEl.value ? modeEl.value : "basic").trim() || "basic",
            asyncModeRequested: Boolean(asyncModeRequestedEl && asyncModeRequestedEl.checked),
            savedAt: utcTimestamp(),
            reason: String(reason || "manual").trim() || "manual",
          };

          const hasMeaningfulInput = Boolean(draft.query) || draft.asyncModeRequested || draft.mode !== "basic";
          if (!hasMeaningfulInput) {
            clearAnalyzeDraft();
            return;
          }

          window.sessionStorage.setItem(ANALYZE_DRAFT_STORAGE_KEY, JSON.stringify(draft));
        } catch (error) {
          // ignore
        }
      }

      function restoreAnalyzeDraft() {
        try {
          if (typeof window === "undefined" || !window.sessionStorage) {
            return;
          }
          const raw = String(window.sessionStorage.getItem(ANALYZE_DRAFT_STORAGE_KEY) || "").trim();
          if (!raw) {
            return;
          }

          const parsed = JSON.parse(raw);
          if (!parsed || typeof parsed !== "object") {
            clearAnalyzeDraft();
            return;
          }

          let restored = false;
          const draftQuery = String(parsed.query || "");
          if (queryEl && !String(queryEl.value || "").trim() && draftQuery.trim()) {
            queryEl.value = draftQuery;
            restored = true;
          }

          const draftMode = String(parsed.mode || "").trim().toLowerCase();
          if (modeEl && draftMode) {
            const hasOption = Array.from(modeEl.options || []).some((opt) => String(opt.value || "").trim().toLowerCase() === draftMode);
            if (hasOption) {
              modeEl.value = draftMode;
              restored = true;
            }
          }

          if (asyncModeRequestedEl && typeof parsed.asyncModeRequested === "boolean") {
            asyncModeRequestedEl.checked = parsed.asyncModeRequested;
            restored = true;
          }

          if (restored) {
            const savedAt = formatLocalTime(parsed.savedAt || "") || "unbekannt";
            if (inputMeta) {
              inputMeta.textContent = `Input (wiederhergestellt aus Session-Draft, gespeichert: ${savedAt})`;
            }
            emitUiEvent("ui.session.draft_restored", {
              direction: "internal",
              status: "restored",
            });
          }
        } catch (error) {
          clearAnalyzeDraft();
        }
      }

      function parseSessionExpiryMs(rawValue) {
        const numeric = Number(rawValue);
        if (!Number.isFinite(numeric) || numeric <= 0) {
          return 0;
        }
        if (numeric > 1_000_000_000_000) {
          return Math.round(numeric);
        }
        return Math.round(numeric * 1000);
      }

      function hideSessionExpiryWarning() {
        if (sessionExpiryWarningEl) {
          sessionExpiryWarningEl.hidden = true;
        }
      }

      function showSessionExpiryWarning(expiresAtMs) {
        if (!sessionExpiryWarningEl || !sessionExpiryWarningTextEl) {
          return;
        }
        const remainingMs = Math.max(0, Number(expiresAtMs) - Date.now());
        const remainingSeconds = Math.max(1, Math.ceil(remainingMs / 1000));
        const remainingMinutes = Math.ceil(remainingSeconds / 60);
        const copy = remainingMinutes <= 1
          ? "Session läuft in weniger als 1 Minute ab. Jetzt neu anmelden, damit Eingaben nicht verloren gehen."
          : `Session läuft in ca. ${remainingMinutes} Minuten ab. Jetzt neu anmelden, damit Eingaben nicht verloren gehen.`;
        sessionExpiryWarningTextEl.textContent = copy;
        sessionExpiryWarningEl.hidden = false;
        authState.warningShownForExpiryMs = Number(expiresAtMs);
      }

      function updateSessionExpiryWarning(payload) {
        const nextExpiryMs = parseSessionExpiryMs(payload && payload.session_expires_at);
        authState.sessionExpiresAtMs = nextExpiryMs;

        if (authState.authenticated !== true || nextExpiryMs <= 0) {
          authState.warningShownForExpiryMs = 0;
          hideSessionExpiryWarning();
          return;
        }

        const remainingMs = nextExpiryMs - Date.now();
        if (remainingMs > SESSION_EXPIRY_WARNING_LEAD_MS) {
          hideSessionExpiryWarning();
          return;
        }

        if (authState.warningShownForExpiryMs !== nextExpiryMs) {
          showSessionExpiryWarning(nextExpiryMs);
        }
      }

      function scheduleAuthSessionPolling() {
        if (typeof window === "undefined" || !window.setInterval) {
          return;
        }
        if (authSessionPollHandle) {
          return;
        }
        authSessionPollHandle = window.setInterval(() => {
          void refreshAuthSession({ force: true });
        }, AUTH_SESSION_POLL_INTERVAL_MS);
      }

      function readStoredJobIds() {
        if (typeof window === "undefined" || !window.localStorage) {
          return [];
        }
        try {
          const raw = String(window.localStorage.getItem(JOB_IDS_STORAGE_KEY) || "").trim();
          if (!raw) {
            return [];
          }
          const parsed = JSON.parse(raw);
          if (!Array.isArray(parsed)) {
            return [];
          }
          return parsed.map((item) => String(item || "").trim()).filter(Boolean);
        } catch (error) {
          return [];
        }
      }

      function rememberJobId(jobId) {
        const normalized = String(jobId || "").trim();
        if (!normalized) {
          return;
        }
        if (typeof window === "undefined" || !window.localStorage) {
          return;
        }
        try {
          const existing = readStoredJobIds();
          const next = [normalized, ...existing.filter((id) => id !== normalized)].slice(0, 60);
          window.localStorage.setItem(JOB_IDS_STORAGE_KEY, JSON.stringify(next));
        } catch (error) {
          return;
        }
      }

      function normalizeLogLevel(level) {
        const normalized = String(level || "info").trim().toLowerCase();
        if (normalized === "debug" || normalized === "info" || normalized === "warn" || normalized === "error") {
          return normalized;
        }
        return "info";
      }

      function emitUiEvent(eventName, details = {}) {
        try {
          const eventPayload = {
            ts: utcTimestamp(),
            level: normalizeLogLevel(details.level),
            event: String(eventName || "ui.event.unknown").trim() || "ui.event.unknown",
            trace_id: String(details.traceId || "").trim(),
            request_id: String(details.requestId || "").trim(),
            session_id: String(details.sessionId || uiSessionId || "").trim(),
            component: UI_LOG_COMPONENT,
            event_seq: ++uiEventSequence,
          };

          Object.entries(details || {}).forEach(([key, value]) => {
            if (["level", "traceId", "requestId", "sessionId"].includes(key)) {
              return;
            }
            if (value === undefined) {
              return;
            }
            eventPayload[key] = value;
          });

          console.log(JSON.stringify(eventPayload));
        } catch (error) {
          return;
        }
      }

      function coarseCoord(value) {
        const asNumber = Number(value);
        if (!Number.isFinite(asNumber)) {
          return null;
        }
        return Number(asNumber.toFixed(4));
      }

      function inferInputKind(payload) {
        if (payload && typeof payload === "object" && payload.coordinates) {
          return "coordinates";
        }
        return "query";
      }

      function setPhase(nextPhase, context = {}) {
        const previousPhase = String(state.phase || "idle");
        state.phase = nextPhase;
        const phaseErrorFields = buildDevErrorLogFields(context.errorCode, context.statusCode);

        emitUiEvent("ui.state.transition", {
          level: nextPhase === "error" ? "warn" : "info",
          traceId: context.traceId,
          requestId: context.requestId,
          direction: "ui",
          status: nextPhase,
          previous_phase: previousPhase,
          next_phase: nextPhase,
          trigger: context.trigger || "",
          ...phaseErrorFields,
        });
      }

      function prettyPrint(payload) {
        return JSON.stringify(payload, null, 2);
      }

      function escapeHtml(text) {
        const raw = String(text == null ? "" : text);
        return raw
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
      }

      function formatLocalTime(isoText) {
        const normalized = String(isoText || "").trim();
        if (!normalized) return "";
        const date = new Date(normalized);
        if (Number.isNaN(date.getTime())) return normalized;
        return date.toLocaleString();
      }

      function renderHistoryItems(items) {
        if (!historyShell) return;
        if (!Array.isArray(items) || items.length === 0) {
          historyShell.innerHTML = `<div class="placeholder">Noch keine historischen Results vorhanden.</div>`;
          return;
        }

        const rows = items.map((item) => {
          const resultId = String(item && item.result_id ? item.result_id : "").trim();
          const query = String(item && item.query ? item.query : "").trim() || "(ohne Query)";
          const when = formatLocalTime(item && item.created_at ? item.created_at : "");
          const mode = String(item && item.intelligence_mode ? item.intelligence_mode : "basic").trim();
          const status = String(item && item.status ? item.status : "").trim();

          const href = resultId ? `/results/${encodeURIComponent(resultId)}` : "#";
          const disabledAttr = resultId ? "" : 'aria-disabled="true"';
          const metaParts = [when, mode];
          if (status) metaParts.push(status);

          return `
            <div class="pill" style="justify-content: space-between; width: 100%;">
              <div style="display:flex; flex-direction: column; gap: 0.1rem;">
                <strong style="font-size:0.9rem;">${escapeHtml(query)}</strong>
                <span class="meta">${escapeHtml(metaParts.filter(Boolean).join(" · "))}</span>
              </div>
              <a class="trace-link-btn" href="${href}" ${disabledAttr}>Open</a>
            </div>
          `;
        });

        historyShell.innerHTML = rows.join("\\n");
      }

      async function loadHistory() {
        if (!historyShell) return;
        const isAuthenticated = await refreshAuthSession({ force: false });
        if (!isAuthenticated && authState.authCheckSupported) {
          scheduleReLoginRedirect(401, "no_session_cookie", "");
          return;
        }

        const headers = { "Accept": "application/json", "X-Session-Id": uiSessionId };

        try {
          const historyFetch = await fetchWithTimeoutAndSafeRetry(
            `${ANALYZE_HISTORY_ENDPOINT}?limit=50`,
            {
              method: "GET",
              headers,
            },
            {
              timeoutMs: DEV_CLIENT_REQUEST_POLICY.historyTimeoutMs,
              maxRetries: DEV_CLIENT_REQUEST_POLICY.getRetries,
              retryDelayMs: DEV_CLIENT_REQUEST_POLICY.retryDelayMs,
            }
          );

          if (!historyFetch.ok || !historyFetch.response) {
            if (historyFetch.timedOut) {
              throw new Error(
                `timeout: Historie nach ${Math.max(1, Math.round(historyFetch.timeoutMs / 1000))}s ohne Antwort abgebrochen. Bitte Retry ausführen.`
              );
            }
            throw new Error("network_error: Historie konnte nicht geladen werden. Bitte Retry ausführen.");
          }

          const response = historyFetch.response;
          const data = await response.json();
          if (!response.ok || !data || data.ok !== true) {
            const errCode = data && data.error ? String(data.error) : `http_${response.status}`;
            const fallbackMessage = (data && data.message) || `history fetch failed (${response.status})`;
            const authFailure = resolveAuthFailure(response.status, errCode, fallbackMessage);
            if (authFailure.requiresLoginRecovery) {
              scheduleReLoginRedirect(
                response.status,
                authFailure.errorCode,
                data && data.request_id ? String(data.request_id) : ""
              );
            }
            throw new Error(authFailure.errorMessage);
          }
          renderHistoryItems(data.history);
        } catch (error) {
          historyShell.innerHTML = `<div class="error">Historie konnte nicht geladen werden: ${escapeHtml(
            error instanceof Error ? error.message : "unknown"
          )}</div>`;
        }
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

      function applyPhaseClass(target, phase) {
        if (!target) {
          return;
        }
        target.classList.remove("phase-loading", "phase-success", "phase-error");
        if (phase === "loading") target.classList.add("phase-loading");
        if (phase === "success") target.classList.add("phase-success");
        if (phase === "error" || phase === "unknown") target.classList.add("phase-error");
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

      function getNestedValue(source, path) {
        let current = source;
        for (const key of path) {
          if (!current || typeof current !== "object" || !(key in current)) {
            return null;
          }
          current = current[key];
        }
        return current;
      }

      function getNestedNumber(source, path) {
        const value = getNestedValue(source, path);
        const num = Number(value);
        return Number.isFinite(num) ? num : null;
      }

      function getNestedString(source, path) {
        const value = getNestedValue(source, path);
        if (value == null) {
          return null;
        }
        const text = String(value).trim();
        return text ? text : null;
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

      function normalizeResultsSortKey(value) {
        const normalized = String(value || "score").trim().toLowerCase();
        if (normalized === "distance_m") return "distance_m";
        if (normalized === "security_subscore") return "security_subscore";
        return "score";
      }

      function normalizeResultsSortDir(value) {
        const normalized = String(value || "desc").trim().toLowerCase();
        if (normalized === "asc") return "asc";
        return "desc";
      }

      function normalizeResultsKo(value) {
        const normalized = String(value || "off").trim().toLowerCase();
        if (normalized === "on") return "on";
        return "off";
      }

      function isMobileResultsViewport() {
        if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
          return false;
        }
        return window.matchMedia("(max-width: 768px)").matches;
      }

      function syncResultsFiltersKeyboardInset() {
        if (!resultsFiltersShellEl || typeof window === "undefined") {
          return;
        }

        if (!resultsFiltersUiState.isMobileViewport || !window.visualViewport) {
          resultsFiltersShellEl.style.setProperty("--results-filters-keyboard-offset", "0px");
          return;
        }

        const viewport = window.visualViewport;
        const keyboardInset = Math.max(0, Math.round(window.innerHeight - viewport.height - viewport.offsetTop));
        const clampedInset = Math.min(keyboardInset, 360);
        resultsFiltersShellEl.style.setProperty("--results-filters-keyboard-offset", `${clampedInset}px`);
      }

      function applyResultsFiltersCollapsedState(collapsed) {
        const nextCollapsed = Boolean(collapsed);
        resultsFiltersUiState.collapsed = nextCollapsed;

        if (resultsFiltersShellEl) {
          resultsFiltersShellEl.dataset.collapsed = nextCollapsed ? "true" : "false";
        }
        if (resultsFiltersToggleEl) {
          resultsFiltersToggleEl.setAttribute("aria-expanded", nextCollapsed ? "false" : "true");
        }
        if (resultsFiltersToggleIndicatorEl) {
          resultsFiltersToggleIndicatorEl.textContent = nextCollapsed ? "Ausgeblendet" : "Eingeblendet";
        }
        if (resultsFiltersPanelEl) {
          resultsFiltersPanelEl.hidden = nextCollapsed;
          if (nextCollapsed && document.activeElement && resultsFiltersPanelEl.contains(document.activeElement)) {
            if (resultsFiltersToggleEl) {
              resultsFiltersToggleEl.focus();
            }
          }
        }
      }

      function syncResultsFiltersForViewport() {
        const mobileViewport = isMobileResultsViewport();
        resultsFiltersUiState.isMobileViewport = mobileViewport;

        if (!mobileViewport) {
          applyResultsFiltersCollapsedState(false);
          return;
        }

        const shellState = resultsFiltersShellEl && resultsFiltersShellEl.dataset
          ? String(resultsFiltersShellEl.dataset.collapsed || "")
          : "";
        if (shellState !== "true" && shellState !== "false") {
          applyResultsFiltersCollapsedState(true);
          return;
        }
        applyResultsFiltersCollapsedState(shellState === "true");
      }

      function updateResultsFiltersToggleUi() {
        if (!resultsFiltersToggleEl) {
          return;
        }

        const mobileViewport = isMobileResultsViewport();
        resultsFiltersUiState.isMobileViewport = mobileViewport;
        resultsFiltersToggleEl.hidden = !mobileViewport;

        if (!mobileViewport) {
          applyResultsFiltersCollapsedState(false);
          return;
        }

        applyResultsFiltersCollapsedState(resultsFiltersUiState.collapsed);
      }

      function updateResultsFiltersViewportState() {
        syncResultsFiltersForViewport();
        updateResultsFiltersToggleUi();
        syncResultsFiltersKeyboardInset();
      }

      function toggleResultsFiltersPanel() {
        if (!resultsFiltersUiState.isMobileViewport) {
          return;
        }
        const nextCollapsed = !resultsFiltersUiState.collapsed;
        applyResultsFiltersCollapsedState(nextCollapsed);
        syncResultsFiltersKeyboardInset();
        emitUiEvent("ui.interaction.results_filters.toggle", {
          direction: "human->ui",
          status: nextCollapsed ? "collapsed" : "expanded",
        });
      }

      function handleResultsFiltersEscape(event) {
        if (!event || event.key !== "Escape" || !resultsFiltersUiState.isMobileViewport) {
          return;
        }
        if (!resultsFiltersUiState.collapsed) {
          event.preventDefault();
          applyResultsFiltersCollapsedState(true);
        }
      }

      function updateResultsListDeepLink() {
        if (typeof window === "undefined" || !window.history || !window.location) {
          return;
        }

        const nextUrl = new URL(window.location.href);

        const sortKey = normalizeResultsSortKey(resultsListState.sortKey);
        const sortDir = normalizeResultsSortDir(resultsListState.sortDir);
        const koFilter = normalizeResultsKo(resultsListState.koFilter);

        if (sortKey !== "score") {
          nextUrl.searchParams.set("results_sort", sortKey);
        } else {
          nextUrl.searchParams.delete("results_sort");
        }

        if (sortDir !== "desc") {
          nextUrl.searchParams.set("results_dir", sortDir);
        } else {
          nextUrl.searchParams.delete("results_dir");
        }

        if (koFilter !== "off") {
          nextUrl.searchParams.set("results_ko", koFilter);
        } else {
          nextUrl.searchParams.delete("results_ko");
        }

        if (resultsListState.minScore != null) {
          nextUrl.searchParams.set("results_min_score", String(resultsListState.minScore));
        } else {
          nextUrl.searchParams.delete("results_min_score");
        }

        if (resultsListState.maxDistance != null) {
          nextUrl.searchParams.set("results_max_distance", String(resultsListState.maxDistance));
        } else {
          nextUrl.searchParams.delete("results_max_distance");
        }

        if (resultsListState.minSecurity != null) {
          nextUrl.searchParams.set("results_min_security", String(resultsListState.minSecurity));
        } else {
          nextUrl.searchParams.delete("results_min_security");
        }

        window.history.replaceState({}, "", nextUrl);
      }

      function restoreResultsListDeepLinkInput() {
        if (typeof window === "undefined" || !window.location) {
          return;
        }

        const url = new URL(window.location.href);

        const sortKey = normalizeResultsSortKey(url.searchParams.get("results_sort"));
        const sortDir = normalizeResultsSortDir(url.searchParams.get("results_dir"));
        const koFilter = normalizeResultsKo(url.searchParams.get("results_ko"));

        const minScore = parseBoundedInteger(url.searchParams.get("results_min_score"), { min: 0, max: 100 });
        const maxDistance = parseBoundedInteger(url.searchParams.get("results_max_distance"), { min: 0, max: 5000 });
        const minSecurity = parseBoundedInteger(url.searchParams.get("results_min_security"), { min: 0, max: 100 });

        resultsListState.sortKey = sortKey;
        resultsListState.sortDir = sortDir;
        resultsListState.koFilter = koFilter;
        resultsListState.minScore = minScore;
        resultsListState.maxDistance = maxDistance;
        resultsListState.minSecurity = minSecurity;

        if (resultsSortEl) resultsSortEl.value = sortKey;
        if (resultsDirEl) resultsDirEl.value = sortDir;
        if (resultsKoEl) resultsKoEl.value = koFilter;

        if (resultsMinScoreEl) resultsMinScoreEl.value = minScore == null ? "" : String(minScore);
        if (resultsMaxDistanceEl) resultsMaxDistanceEl.value = maxDistance == null ? "" : String(maxDistance);
        if (resultsMinSecurityEl) resultsMinSecurityEl.value = minSecurity == null ? "" : String(minSecurity);
      }

      function extractResultsListEntry(payload, context = {}) {
        if (!payload || typeof payload !== "object" || !payload.ok) {
          return null;
        }

        const requestId = payload.request_id ? String(payload.request_id).trim() : "";

        const resultBlock = payload.result && typeof payload.result === "object" ? payload.result : null;
        const modulesBlock = resultBlock && resultBlock.data && typeof resultBlock.data === "object" ? resultBlock.data.modules : null;
        if (!modulesBlock || typeof modulesBlock !== "object") {
          return null;
        }

        const matchedAddress =
          getNestedString(payload, ["result", "data", "entity", "matched_address"]) ||
          getNestedString(payload, ["result", "data", "entity", "query"]) ||
          "";

        let suitabilityScore = getNestedNumber(payload, ["result", "data", "modules", "suitability_light", "score"]);
        if (suitabilityScore == null) {
          suitabilityScore = getNestedNumber(payload, ["result", "data", "modules", "summary_compact", "suitability_light", "score"]);
        }

        const suitabilityTraffic =
          getNestedString(payload, ["result", "data", "modules", "suitability_light", "traffic_light"]) ||
          getNestedString(payload, ["result", "data", "modules", "summary_compact", "suitability_light", "traffic_light"]) ||
          "";

        const distanceM = getNestedNumber(payload, [
          "result",
          "data",
          "modules",
          "match",
          "resolution",
          "coordinate_input",
          "resolved",
          "distance_m",
        ]);

        const confidenceLevel =
          getNestedString(payload, ["result", "status", "quality", "confidence", "level"]) || "";

        let riskScore = getNestedNumber(payload, ["result", "data", "modules", "intelligence", "executive_risk_summary", "risk_score"]);
        if (riskScore == null) {
          riskScore = getNestedNumber(payload, ["result", "data", "modules", "summary_compact", "intelligence", "executive_risk", "risk_score"]);
        }

        const riskTraffic =
          getNestedString(payload, ["result", "data", "modules", "intelligence", "executive_risk_summary", "traffic_light"]) ||
          getNestedString(payload, ["result", "data", "modules", "summary_compact", "intelligence", "executive_risk", "traffic_light"]) ||
          "";

        const securitySubscore = riskScore == null ? null : Math.round(clamp(100 - riskScore, 0, 100));

        const ts = utcTimestamp();
        const inputLabel = String(context.inputLabel || "").trim();

        return {
          key: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          ts,
          requestId,
          inputLabel,
          matchedAddress,
          score: suitabilityScore == null ? null : Math.round(suitabilityScore),
          distanceM: distanceM == null ? null : Math.round(distanceM),
          riskScore: riskScore == null ? null : Math.round(riskScore),
          securitySubscore,
          suitabilityTraffic,
          confidenceLevel,
          riskTraffic,
          payload,
        };
      }

      function isResultsEntryKo(entry) {
        if (!entry || typeof entry !== "object") {
          return false;
        }
        if (String(entry.suitabilityTraffic || "").toLowerCase() === "red") {
          return true;
        }
        if (String(entry.riskTraffic || "").toLowerCase() === "red") {
          return true;
        }
        if (String(entry.confidenceLevel || "").toLowerCase() === "low") {
          return true;
        }
        return false;
      }

      function entryPassesNumericFilters(entry) {
        if (resultsListState.minScore != null) {
          const score = Number(entry.score);
          if (!Number.isFinite(score) || score < resultsListState.minScore) {
            return false;
          }
        }
        if (resultsListState.maxDistance != null) {
          const dist = Number(entry.distanceM);
          if (!Number.isFinite(dist) || dist > resultsListState.maxDistance) {
            return false;
          }
        }
        if (resultsListState.minSecurity != null) {
          const sec = Number(entry.securitySubscore);
          if (!Number.isFinite(sec) || sec < resultsListState.minSecurity) {
            return false;
          }
        }
        return true;
      }

      function sortValueForEntry(entry, sortKey) {
        const key = normalizeResultsSortKey(sortKey);
        if (key === "distance_m") {
          const dist = Number(entry.distanceM);
          return Number.isFinite(dist) ? dist : Number.POSITIVE_INFINITY;
        }
        if (key === "security_subscore") {
          const sec = Number(entry.securitySubscore);
          return Number.isFinite(sec) ? sec : Number.NEGATIVE_INFINITY;
        }
        const score = Number(entry.score);
        return Number.isFinite(score) ? score : Number.NEGATIVE_INFINITY;
      }

      function formatResultTime(tsIso) {
        const text = String(tsIso || "").trim();
        if (text.length >= 19 && text.includes("T")) {
          return text.slice(11, 19);
        }
        return text || "—";
      }

      function normalizeResultsRecoveryState(rawValue) {
        const normalized = String(rawValue || "").trim().toLowerCase();
        if (normalized === "network" || normalized === "unauthorized") {
          return normalized;
        }
        return "";
      }

      function setResultsListRecoveryState(nextState) {
        resultsListState.recoveryState = normalizeResultsRecoveryState(nextState);
      }

      function setResultsListLoading(nextValue) {
        resultsListState.isLoading = Boolean(nextValue);
      }

      function hasResultsListRetryContext() {
        return Boolean(
          state.lastAnalyzeRequest
          && state.lastAnalyzeRequest.payload
          && typeof state.lastAnalyzeRequest.payload === "object"
        );
      }

      function resolveResultsRecoveryStateFromAnalyzeResult(result) {
        if (!result || result.ok) {
          return "";
        }

        const statusCode = Number(result.statusCode);
        const errorCode = normalizeErrorCode(result.errorCode);
        if (result.requiresLoginRecovery || statusCode === 401 || statusCode === 403) {
          return "unauthorized";
        }
        if (
          errorCode === "unauthorized"
          || errorCode === "access_denied"
          || errorCode === "consent_denied"
          || errorCode === "session_not_found"
          || errorCode === "no_session_cookie"
        ) {
          return "unauthorized";
        }
        return "";
      }

      function resolveResultsMetaCopy(total, emptyReason) {
        if (emptyReason === "loading") {
          return RESULTS_LIST_COPY.meta.loading;
        }
        if (emptyReason === "network") {
          return RESULTS_LIST_COPY.meta.network;
        }
        if (emptyReason === "unauthorized") {
          return RESULTS_LIST_COPY.meta.unauthorized;
        }
        if (emptyReason === "error") {
          return RESULTS_LIST_COPY.meta.error;
        }
        return total ? RESULTS_LIST_COPY.meta.filtered : RESULTS_LIST_COPY.meta.empty;
      }

      function triggerResultsListLoginRecovery(authReason = "session_expired") {
        const loginUrl = buildLoginRedirectUrl(authReason);
        setAuthState(false, {
          userClaims: {},
          authCheckSupported: true,
        });

        if (typeof window !== "undefined" && window.location && typeof window.location.assign === "function") {
          window.location.assign(loginUrl);
          return true;
        }

        scheduleReLoginRedirect(401, "unauthorized", normalizeTraceRequestId(state.lastRequestId));
        return false;
      }

      async function retryLastAnalyzeRequestFromResultsList() {
        if (!hasResultsListRetryContext() || state.phase === "loading") {
          return false;
        }

        const retryPayload = cloneAnalyzePayload(state.lastAnalyzeRequest.payload);
        if (!retryPayload) {
          return false;
        }

        const retryInputLabel = String(state.lastAnalyzeRequest.inputLabel || state.lastInput || "Retry").trim() || "Retry";
        await startAnalyze(retryPayload, retryInputLabel, {
          trigger: "results_list_empty_retry",
          isRetryAttempt: true,
        });
        return true;
      }

      function resetResultsListFilters() {
        resultsListState.sortKey = "score";
        resultsListState.sortDir = "desc";
        resultsListState.koFilter = "off";
        resultsListState.minScore = null;
        resultsListState.maxDistance = null;
        resultsListState.minSecurity = null;

        if (resultsSortEl) resultsSortEl.value = "score";
        if (resultsDirEl) resultsDirEl.value = "desc";
        if (resultsKoEl) resultsKoEl.value = "off";
        if (resultsMinScoreEl) resultsMinScoreEl.value = "";
        if (resultsMaxDistanceEl) resultsMaxDistanceEl.value = "";
        if (resultsMinSecurityEl) resultsMinSecurityEl.value = "";
      }

      async function handleResultsEmptyStatePrimaryAction(reason) {
        const normalizedReason = String(reason || "filtered").trim().toLowerCase() || "filtered";

        if (normalizedReason === "network" || normalizedReason === "error") {
          const retryTriggered = await retryLastAnalyzeRequestFromResultsList();
          emitUiEvent("ui.interaction.results_list.empty_cta", {
            direction: "human->ui",
            status: retryTriggered ? "retry_triggered" : "retry_unavailable",
            reason: normalizedReason,
          });
          return;
        }

        if (normalizedReason === "unauthorized") {
          const redirected = triggerResultsListLoginRecovery("session_expired");
          emitUiEvent("ui.interaction.results_list.empty_cta", {
            direction: "human->ui",
            status: redirected ? "login_redirect" : "login_recovery_scheduled",
            reason: "unauthorized",
          });
          return;
        }

        resetResultsListFilters();
        setResultsListRecoveryState("");
        updateResultsListDeepLink();
        renderResultsList();
        emitUiEvent("ui.interaction.results_list.empty_cta", {
          direction: "human->ui",
          status: "filters_reset",
          reason: normalizedReason,
        });
      }

      function resolveResultsEmptyState(total) {
        if (resultsListState.isLoading) {
          return {
            reason: "loading",
            title: RESULTS_LIST_COPY.emptyStates.loading.title,
            description: RESULTS_LIST_COPY.emptyStates.loading.description,
            action: RESULTS_LIST_COPY.emptyStates.loading.action,
          };
        }

        const recoveryState = normalizeResultsRecoveryState(resultsListState.recoveryState);
        if (recoveryState === "network") {
          return {
            reason: "network",
            title: RESULTS_LIST_COPY.emptyStates.network.title,
            description: RESULTS_LIST_COPY.emptyStates.network.description,
            action: RESULTS_LIST_COPY.emptyStates.network.action,
          };
        }
        if (recoveryState === "unauthorized") {
          return {
            reason: "unauthorized",
            title: RESULTS_LIST_COPY.emptyStates.unauthorized.title,
            description: RESULTS_LIST_COPY.emptyStates.unauthorized.description,
            action: RESULTS_LIST_COPY.emptyStates.unauthorized.action,
          };
        }
        if (state.phase === "error" && state.lastError && hasResultsListRetryContext()) {
          return {
            reason: "error",
            title: RESULTS_LIST_COPY.emptyStates.error.title,
            description: RESULTS_LIST_COPY.emptyStates.error.description,
            action: RESULTS_LIST_COPY.emptyStates.error.action,
          };
        }
        if (total > 0) {
          return {
            reason: "filtered",
            title: RESULTS_LIST_COPY.emptyStates.filtered.title,
            description: RESULTS_LIST_COPY.emptyStates.filtered.description,
            action: RESULTS_LIST_COPY.emptyStates.filtered.action,
          };
        }
        return {
          reason: "no_data",
          title: RESULTS_LIST_COPY.emptyStates.noData.title,
          description: RESULTS_LIST_COPY.emptyStates.noData.description,
          action: RESULTS_LIST_COPY.emptyStates.noData.action,
        };
      }

      function showResultsEntry(entry) {
        if (!entry || typeof entry !== "object" || !entry.payload) {
          return;
        }

        const requestId = normalizeTraceRequestId(entry.requestId);
        const traceId = requestId || createUiCorrelationId("req");

        state.lastPayload = entry.payload;
        state.lastRequestId = requestId || state.lastRequestId;
        state.lastInput = entry.inputLabel || state.lastInput;
        state.lastError = null;
        clearServerErrorView();
        state.coreFactors = extractCoreFactors(entry.payload);

        setPhase("success", {
          traceId,
          requestId: requestId || state.lastRequestId,
          trigger: "results_list_show",
        });
        renderState();

        try {
          document.getElementById("result").scrollIntoView({ behavior: "smooth", block: "start" });
        } catch (error) {
          // ignore
        }
      }

      function emitResultsListFirstContentfulData(loadMetric, metrics = {}) {
        if (!loadMetric || typeof loadMetric !== "object") {
          return;
        }

        const startedAtMs = Number(loadMetric.startedAtMs);
        if (!Number.isFinite(startedAtMs)) {
          return;
        }

        const requestId = normalizeTraceRequestId(loadMetric.requestId);
        const loadId = String(loadMetric.loadId || createUiCorrelationId("results-load")).trim();
        const traceId = requestId || loadId;
        const trigger = String(loadMetric.trigger || "results_list_load").trim() || "results_list_load";

        const emitMetric = () => {
          const durationMs = Number((performance.now() - startedAtMs).toFixed(3));
          emitUiEvent("ui.results_list.first_contentful_data", {
            traceId,
            requestId,
            direction: "ui",
            status: String(metrics.status || "ready").trim() || "ready",
            trigger,
            load_id: loadId,
            duration_ms: durationMs,
            rows_visible: Number.isFinite(Number(metrics.rowsVisible)) ? Number(metrics.rowsVisible) : 0,
            rows_total: Number.isFinite(Number(metrics.rowsTotal)) ? Number(metrics.rowsTotal) : 0,
          });
        };

        if (typeof window !== "undefined" && window && typeof window.requestAnimationFrame === "function") {
          window.requestAnimationFrame(() => {
            emitMetric();
          });
          return;
        }

        emitMetric();
      }

      function renderResultsList({ loadMetric = null } = {}) {
        if (!resultsBodyEl || !resultsMetaEl) {
          return;
        }

        const total = resultsListState.entries.length;
        let rows = resultsListState.entries.slice();

        if (normalizeResultsKo(resultsListState.koFilter) === "on") {
          rows = rows.filter((entry) => !isResultsEntryKo(entry));
        }

        rows = rows.filter((entry) => entryPassesNumericFilters(entry));

        const sortKey = normalizeResultsSortKey(resultsListState.sortKey);
        const sortDir = normalizeResultsSortDir(resultsListState.sortDir);

        rows.sort((a, b) => {
          const aVal = sortValueForEntry(a, sortKey);
          const bVal = sortValueForEntry(b, sortKey);
          if (aVal !== bVal) {
            return sortDir === "asc" ? aVal - bVal : bVal - aVal;
          }
          return String(a.ts || "").localeCompare(String(b.ts || "")) * (sortDir === "asc" ? 1 : -1);
        });

        resultsBodyEl.textContent = "";

        if (!rows.length) {
          const emptyState = resolveResultsEmptyState(total);

          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = 6;
          td.className = "results-empty-cell";

          const panel = document.createElement("section");
          panel.className = "results-empty-state";
          panel.setAttribute("role", "status");
          panel.setAttribute("aria-live", "polite");

          if (emptyState.reason === "loading") {
            panel.classList.add("results-loading-state");
            const spinner = document.createElement("div");
            spinner.className = "results-loading-spinner";
            spinner.setAttribute("aria-hidden", "true");
            panel.appendChild(spinner);
          }

          if (emptyState.reason === "error") {
            panel.classList.add("results-error-state");
          }

          const title = document.createElement("h3");
          title.className = "results-empty-title";
          title.textContent = emptyState.title;

          const description = document.createElement("p");
          description.className = "results-empty-copy";
          description.textContent = emptyState.description;

          panel.appendChild(title);
          panel.appendChild(description);

          const actionText = String(emptyState.action || "").trim();
          if (actionText) {
            const action = document.createElement("button");
            action.type = "button";
            action.className = "results-empty-action";
            action.textContent = actionText;
            action.addEventListener("click", async () => {
              await handleResultsEmptyStatePrimaryAction(emptyState.reason);
            });
            panel.appendChild(action);
          }
          td.appendChild(panel);
          tr.appendChild(td);
          resultsBodyEl.appendChild(tr);

          resultsMetaEl.textContent = resolveResultsMetaCopy(total, emptyState.reason);
          const loadStatusByReason = {
            filtered: "filtered_empty",
            loading: "loading",
            error: "error",
          };
          emitResultsListFirstContentfulData(loadMetric, {
            status: loadStatusByReason[emptyState.reason] || "empty",
            rowsVisible: 0,
            rowsTotal: total,
          });
          return;
        }

        if (resultsListState.isLoading) {
          resultsMetaEl.textContent = `${rows.length}/${total} angezeigt · Aktualisiere …`;
        } else {
          resultsMetaEl.textContent = `${rows.length}/${total} angezeigt`;
        }

        rows.forEach((entry) => {
          const tr = document.createElement("tr");

          const tdTs = document.createElement("td");
          tdTs.textContent = formatResultTime(entry.ts);
          tr.appendChild(tdTs);

          const tdInput = document.createElement("td");
          const inputText = entry.inputLabel || entry.matchedAddress || "—";
          tdInput.textContent = inputText.length > 80 ? `${inputText.slice(0, 77)}…` : inputText;
          tr.appendChild(tdInput);

          const tdScore = document.createElement("td");
          tdScore.textContent = entry.score == null ? "—" : String(entry.score);
          tr.appendChild(tdScore);

          const tdDist = document.createElement("td");
          tdDist.textContent = entry.distanceM == null ? "—" : String(entry.distanceM);
          tr.appendChild(tdDist);

          const tdSec = document.createElement("td");
          tdSec.textContent = entry.securitySubscore == null ? "—" : String(entry.securitySubscore);
          tr.appendChild(tdSec);

          const tdActions = document.createElement("td");
          tdActions.className = "actions";

          const actionsWrap = document.createElement("div");
          actionsWrap.className = "results-row-actions";

          const showBtn = document.createElement("button");
          showBtn.type = "button";
          showBtn.className = "copy-btn";
          showBtn.textContent = "Anzeigen";
          showBtn.addEventListener("click", () => showResultsEntry(entry));
          actionsWrap.appendChild(showBtn);

          const traceLink = document.createElement("a");
          traceLink.className = "trace-link-btn";
          traceLink.textContent = "Trace";
          traceLink.href = buildGuiTraceDeepLink(entry.requestId);
          traceLink.hidden = !normalizeTraceRequestId(entry.requestId);
          actionsWrap.appendChild(traceLink);

          tdActions.appendChild(actionsWrap);
          tr.appendChild(tdActions);
          resultsBodyEl.appendChild(tr);
        });

        emitResultsListFirstContentfulData(loadMetric, {
          status: "ready",
          rowsVisible: rows.length,
          rowsTotal: total,
        });
      }

      function syncResultsListStateFromControls() {
        if (resultsSortEl) resultsListState.sortKey = normalizeResultsSortKey(resultsSortEl.value);
        if (resultsDirEl) resultsListState.sortDir = normalizeResultsSortDir(resultsDirEl.value);
        if (resultsKoEl) resultsListState.koFilter = normalizeResultsKo(resultsKoEl.value);

        if (resultsMinScoreEl) {
          resultsListState.minScore = parseBoundedInteger(resultsMinScoreEl.value, { min: 0, max: 100 });
        }
        if (resultsMaxDistanceEl) {
          resultsListState.maxDistance = parseBoundedInteger(resultsMaxDistanceEl.value, { min: 0, max: 5000 });
        }
        if (resultsMinSecurityEl) {
          resultsListState.minSecurity = parseBoundedInteger(resultsMinSecurityEl.value, { min: 0, max: 100 });
        }

        updateResultsListDeepLink();
        renderResultsList();
      }

      function applyResultsFiltersFromControls(trigger = "manual") {
        syncResultsListStateFromControls();
        emitUiEvent("ui.interaction.results_filters.apply", {
          direction: "human->ui",
          status: "applied",
          trigger,
        });
      }

      function resetResultsFiltersFromControls(trigger = "manual") {
        resetResultsListFilters();
        updateResultsListDeepLink();
        renderResultsList();
        emitUiEvent("ui.interaction.results_filters.reset", {
          direction: "human->ui",
          status: "reset",
          trigger,
        });
      }

      function addResultsEntry(entry) {
        if (!entry) {
          return;
        }

        setResultsListRecoveryState("");

        const loadMetric = {
          startedAtMs: performance.now(),
          requestId: normalizeTraceRequestId(entry.requestId),
          loadId: createUiCorrelationId("results-load"),
          trigger: "results_entry_added",
        };

        resultsListState.entries.unshift(entry);
        if (resultsListState.entries.length > 60) {
          resultsListState.entries = resultsListState.entries.slice(0, 60);
        }
        renderResultsList({ loadMetric });
      }

      function clearResultsEntries() {
        resultsListState.entries = [];
        setResultsListRecoveryState("");
        setResultsListLoading(false);
        renderResultsList();
      }

      function buildGuiTraceDeepLink(requestId) {
        const normalizedRequestId = normalizeTraceRequestId(requestId);
        if (!normalizedRequestId || typeof window === "undefined" || !window.location) {
          return "#trace-debug";
        }

        const nextUrl = new URL(window.location.href);
        nextUrl.searchParams.set("view", "trace");
        nextUrl.searchParams.set("request_id", normalizedRequestId);
        nextUrl.hash = "#trace-debug";
        return nextUrl.toString();
      }

      function setRequestIdFeedback(message, { isError = false, autoResetMs = 0 } = {}) {
        if (requestIdFeedbackResetHandle) {
          clearTimeout(requestIdFeedbackResetHandle);
          requestIdFeedbackResetHandle = null;
        }

        requestIdFeedbackEl.textContent = message;
        requestIdFeedbackEl.classList.toggle("copy-feedback-error", Boolean(isError));

        if (autoResetMs > 0) {
          requestIdFeedbackResetHandle = setTimeout(() => {
            requestIdFeedbackEl.classList.remove("copy-feedback-error");
            if (state.lastRequestId) {
              requestIdFeedbackEl.textContent = "Trace-Link bereit.";
            } else {
              requestIdFeedbackEl.textContent = "Noch keine Request-ID vorhanden.";
            }
            requestIdFeedbackResetHandle = null;
          }, autoResetMs);
        }
      }

      async function copyTextToClipboard(value) {
        const text = String(value || "").trim();
        if (!text) {
          return false;
        }

        try {
          if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
            await navigator.clipboard.writeText(text);
            return true;
          }
        } catch (error) {
          // fallback below
        }

        try {
          const textarea = document.createElement("textarea");
          textarea.value = text;
          textarea.setAttribute("readonly", "readonly");
          textarea.style.position = "fixed";
          textarea.style.top = "-9999px";
          document.body.appendChild(textarea);
          textarea.focus();
          textarea.select();
          const copied = document.execCommand("copy");
          document.body.removeChild(textarea);
          return Boolean(copied);
        } catch (error) {
          return false;
        }
      }

      async function openTraceFromResultPanel() {
        const requestId = normalizeTraceRequestId(state.lastRequestId);
        if (!requestId) {
          return;
        }

        traceRequestIdEl.value = requestId;
        setRequestIdFeedback("Trace wird geöffnet …");
        document.getElementById("trace-debug").scrollIntoView({ behavior: "smooth", block: "start" });
        await startTraceLookup(requestId, "result_panel_trace_link");
      }

      function renderState() {
        phasePill.textContent = `Status: ${state.phase}`;
        phasePill.dataset.phase = state.phase;
        applyPhaseClass(phasePill, state.phase);

        const currentRequestId = normalizeTraceRequestId(state.lastRequestId);
        if (currentRequestId) {
          requestMeta.textContent = `Letzte Request-ID verfügbar (${currentRequestId}).`;
        } else if (state.phase === "loading") {
          requestMeta.textContent = "Anfrage läuft …";
        } else {
          requestMeta.textContent = "Noch keine Anfrage gesendet.";
        }

        requestIdValueEl.textContent = currentRequestId || "—";
        if (currentRequestId) {
          requestTraceLinkEl.hidden = false;
          requestTraceLinkEl.href = buildGuiTraceDeepLink(currentRequestId);
          requestIdCopyBtnEl.disabled = false;
          if (!requestIdFeedbackEl.classList.contains("copy-feedback-error") && !requestIdFeedbackResetHandle) {
            requestIdFeedbackEl.textContent = "Trace-Link bereit.";
          }
        } else {
          requestTraceLinkEl.hidden = true;
          requestTraceLinkEl.href = "#trace-debug";
          requestIdCopyBtnEl.disabled = true;
          requestIdFeedbackEl.classList.remove("copy-feedback-error");
          requestIdFeedbackEl.textContent = "Noch keine Request-ID vorhanden.";
        }

        inputMeta.textContent = state.lastInput ? `Input: ${state.lastInput}` : "Input: —";

        if (asyncJobBoxEl && asyncJobIdEl && asyncJobLinkEl && asyncResultLinkEl && asyncJobMetaEl) {
          const rawPayload = state.lastPayload && typeof state.lastPayload === "object" ? state.lastPayload : null;
          const jobPayload =
            rawPayload && rawPayload.accepted && rawPayload.job && typeof rawPayload.job === "object"
              ? rawPayload.job
              : null;
          const jobId = jobPayload && jobPayload.job_id ? String(jobPayload.job_id).trim() : "";

          if (jobId) {
            asyncJobBoxEl.hidden = false;
            asyncJobIdEl.textContent = jobId;
            rememberJobId(jobId);

            asyncJobLinkEl.href = `/jobs/${encodeURIComponent(jobId)}`;

            const status = String(jobPayload.status || "").trim().toLowerCase() || "queued";
            const progressRaw = Number(jobPayload.progress_percent);
            const progressPercent = Number.isFinite(progressRaw)
              ? Math.max(0, Math.min(100, Math.round(progressRaw)))
              : null;
            const progressText = progressPercent == null ? "" : ` · ${progressPercent}%`;
            asyncJobMetaEl.textContent = `Status: ${status}${progressText}`;

            const resultId = jobPayload.result_id ? String(jobPayload.result_id).trim() : "";
            if (resultId) {
              asyncResultLinkEl.hidden = false;
              asyncResultLinkEl.href = `/results/${encodeURIComponent(resultId)}`;
            } else {
              asyncResultLinkEl.hidden = true;
              asyncResultLinkEl.href = "#";
            }
          } else {
            asyncJobBoxEl.hidden = true;
            asyncJobIdEl.textContent = "—";
            asyncJobLinkEl.href = "#";
            asyncResultLinkEl.hidden = true;
            asyncResultLinkEl.href = "#";
            asyncJobMetaEl.textContent = "Polling: off";
          }
        }

        const showServerErrorView = Boolean(
          state.serverErrorView
          && state.serverErrorView.visible
          && isServerErrorStatus(state.serverErrorView.statusCode)
        );

        if (serverErrorViewEl) {
          serverErrorViewEl.hidden = !showServerErrorView;
        }
        if (showServerErrorView) {
          if (serverErrorTitleEl) {
            serverErrorTitleEl.textContent = "Temporärer Serverfehler (5xx)";
          }
          if (serverErrorCopyEl) {
            serverErrorCopyEl.textContent = "Die Anfrage konnte wegen eines temporären Serverfehlers nicht abgeschlossen werden. Bitte Retry ausführen.";
          }
          if (serverErrorMetaEl) {
            serverErrorMetaEl.textContent = describeServerErrorMeta(state.serverErrorView);
          }
          if (serverErrorRetryBtnEl) {
            const retryReady = Boolean(
              state.lastAnalyzeRequest
              && state.lastAnalyzeRequest.payload
              && typeof state.lastAnalyzeRequest.payload === "object"
            );
            serverErrorRetryBtnEl.disabled = submitBtn.disabled || !retryReady;
          }
          errorBox.hidden = true;
          errorBox.textContent = "";
        } else if (state.lastError) {
          errorBox.hidden = false;
          errorBox.textContent = state.lastError;
          if (serverErrorRetryBtnEl) {
            serverErrorRetryBtnEl.disabled = true;
          }
        } else {
          errorBox.hidden = true;
          errorBox.textContent = "";
          if (serverErrorRetryBtnEl) {
            serverErrorRetryBtnEl.disabled = true;
          }
        }

        renderCoreFactors();
      }

      function parseBoundedInteger(rawValue, { min, max }) {
        const normalizedRaw = String(rawValue || "").trim();
        if (!normalizedRaw) {
          return null;
        }
        const number = Number(normalizedRaw);
        if (!Number.isFinite(number) || !Number.isInteger(number)) {
          return null;
        }
        if (number < min || number > max) {
          return null;
        }
        return number;
      }

      function normalizeTraceRequestId(rawValue) {
        return String(rawValue || "").trim();
      }

      function describeTraceEmptyReason(reason) {
        const normalized = String(reason || "").trim();
        if (normalized === "request_id_outside_window") {
          return "Für diese request_id liegen nur Events außerhalb des konfigurierten Zeitfensters.";
        }
        if (normalized === "request_id_unknown_or_no_events") {
          return "request_id unbekannt oder noch keine Events vorhanden.";
        }
        return "Für diese request_id wurden keine Timeline-Events gefunden.";
      }

      function setTracePhase(nextPhase, context = {}) {
        const previousPhase = String(traceState.phase || "idle");
        traceState.phase = nextPhase;
        const phaseErrorFields = buildDevErrorLogFields(context.errorCode, context.statusCode);

        emitUiEvent("ui.trace.state.transition", {
          level: nextPhase === "error" || nextPhase === "unknown" ? "warn" : "info",
          traceId: context.traceId,
          requestId: context.requestId,
          direction: "ui",
          status: nextPhase,
          previous_phase: previousPhase,
          next_phase: nextPhase,
          trigger: context.trigger || "",
          ...phaseErrorFields,
        });
      }

      function normalizeTraceEvents(rawEvents) {
        if (!Array.isArray(rawEvents)) {
          return [];
        }

        const normalized = rawEvents
          .filter((event) => event && typeof event === "object")
          .map((event, index) => {
            const tsText = String(event.ts || "").trim();
            const parsedTs = tsText ? Date.parse(tsText) : Number.NaN;
            return {
              key: `${String(event.event || "event")}-${index}`,
              event: String(event.event || "unknown_event"),
              ts: tsText,
              phase: String(event.phase || "unknown"),
              summary: String(event.summary || "kein Summary verfügbar"),
              details: event.details && typeof event.details === "object" ? event.details : {},
              component: String(event.component || ""),
              direction: String(event.direction || ""),
              _sortTs: Number.isFinite(parsedTs) ? parsedTs : Number.POSITIVE_INFINITY,
              _index: index,
            };
          });

        normalized.sort((left, right) => {
          if (left._sortTs !== right._sortTs) {
            return left._sortTs - right._sortTs;
          }
          return left._index - right._index;
        });

        return normalized;
      }

      function renderTraceTimeline() {
        traceTimelineEl.textContent = "";

        if (!traceState.events.length) {
          const fallback = document.createElement("li");
          fallback.textContent = "Keine Timeline-Events verfügbar.";
          traceTimelineEl.appendChild(fallback);
          return;
        }

        traceState.events.forEach((event) => {
          const item = document.createElement("li");
          item.className = "trace-event";

          const title = document.createElement("strong");
          title.textContent = event.event;
          item.appendChild(title);

          const meta = document.createElement("span");
          meta.className = "trace-event-meta";
          const tsText = event.ts || "ts unbekannt";
          const componentText = event.component ? ` · ${event.component}` : "";
          const directionText = event.direction ? ` · ${event.direction}` : "";
          meta.textContent = `${tsText} · phase=${event.phase}${componentText}${directionText}`;
          item.appendChild(meta);

          const summary = document.createElement("span");
          summary.className = "trace-event-summary";
          summary.textContent = event.summary;
          item.appendChild(summary);

          const detailsKeys = Object.keys(event.details || {});
          if (detailsKeys.length > 0) {
            const detailPre = document.createElement("pre");
            detailPre.textContent = prettyPrint(event.details);
            item.appendChild(detailPre);
          }

          traceTimelineEl.appendChild(item);
        });
      }

      function renderTraceState() {
        tracePhasePill.textContent = `Trace-Status: ${traceState.phase}`;
        tracePhasePill.dataset.phase = traceState.phase;
        applyPhaseClass(tracePhasePill, traceState.phase);

        if (traceState.requestId && traceState.apiRequestId) {
          traceMetaEl.textContent = `Trace lookup: ${traceState.requestId} (API request_id: ${traceState.apiRequestId})`;
        } else if (traceState.requestId) {
          traceMetaEl.textContent = `Trace lookup: ${traceState.requestId}`;
        } else if (traceState.phase === "loading") {
          traceMetaEl.textContent = "Trace wird geladen …";
        } else {
          traceMetaEl.textContent = "Noch keine Trace-Abfrage gestartet.";
        }

        if (traceState.emptyMessage) {
          traceEmptyBoxEl.hidden = false;
          traceEmptyBoxEl.textContent = traceState.emptyMessage;
        } else {
          traceEmptyBoxEl.hidden = true;
          traceEmptyBoxEl.textContent = "";
        }

        if (traceState.error) {
          traceErrorBoxEl.hidden = false;
          traceErrorBoxEl.textContent = traceState.error;
        } else {
          traceErrorBoxEl.hidden = true;
          traceErrorBoxEl.textContent = "";
        }

        if (traceState.payload) {
          traceJsonEl.textContent = prettyPrint(traceState.payload);
        }

        renderTraceTimeline();
      }

      function updateTraceDeepLink(requestId) {
        if (typeof window === "undefined" || !window.history || !window.location) {
          return;
        }

        const normalizedRequestId = normalizeTraceRequestId(requestId);
        const nextUrl = new URL(window.location.href);
        if (normalizedRequestId) {
          nextUrl.searchParams.set("view", "trace");
          nextUrl.searchParams.set("request_id", normalizedRequestId);
        } else {
          nextUrl.searchParams.delete("request_id");
          if (nextUrl.searchParams.get("view") === "trace") {
            nextUrl.searchParams.delete("view");
          }
        }

        window.history.replaceState({}, "", nextUrl);
      }

      function restoreTraceDeepLinkInput() {
        if (typeof window === "undefined" || !window.location) {
          return "";
        }

        const url = new URL(window.location.href);
        const fromRequestId = normalizeTraceRequestId(url.searchParams.get("request_id") || "");
        const fromAlias = normalizeTraceRequestId(url.searchParams.get("trace_request_id") || "");
        const requestId = fromRequestId || fromAlias;

        if (requestId) {
          traceRequestIdEl.value = requestId;
        }

        const lookback = parseBoundedInteger(url.searchParams.get("lookback_seconds"), {
          min: 60,
          max: 604800,
        });
        if (lookback != null) {
          traceLookbackSecondsEl.value = String(lookback);
        }

        const maxEvents = parseBoundedInteger(url.searchParams.get("max_events"), {
          min: 1,
          max: 500,
        });
        if (maxEvents != null) {
          traceMaxEventsEl.value = String(maxEvents);
        }

        return requestId;
      }

      function buildTraceLookupUrl(requestId) {
        const normalizedRequestId = normalizeTraceRequestId(requestId);
        const query = new URLSearchParams();
        query.set("request_id", normalizedRequestId);

        const lookbackSeconds = parseBoundedInteger(traceLookbackSecondsEl.value, {
          min: 60,
          max: 604800,
        });
        if (lookbackSeconds != null) {
          query.set("lookback_seconds", String(lookbackSeconds));
        }

        const maxEvents = parseBoundedInteger(traceMaxEventsEl.value, {
          min: 1,
          max: 500,
        });
        if (maxEvents != null) {
          query.set("max_events", String(maxEvents));
        }

        return `${TRACE_DEBUG_ENDPOINT}?${query.toString()}`;
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
        emitUiEvent("ui.output.map_status", {
          level: "warn",
          direction: "ui->human",
          status: "degraded",
          message,
        });
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

      function formatAccuracyMeters(value) {
        const meters = Number(value);
        if (!Number.isFinite(meters) || meters <= 0) {
          return null;
        }
        if (meters >= 1000) {
          return `±${(meters / 1000).toFixed(1)} km`;
        }
        return `±${Math.round(meters)} m`;
      }

      function updateMapLocationMeta(message) {
        if (!mapLocationMeta) {
          return;
        }
        mapLocationMeta.textContent = message;
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

      function metersPerPixel(lat, zoom) {
        const clampedLat = clampLatToMercator(lat);
        const radians = (clampedLat * Math.PI) / 180;
        return (156543.03392 * Math.cos(radians)) / Math.pow(2, zoom);
      }

      function updateUserLocationOverlay() {
        if (!mapUserMarker || !mapUserAccuracy) {
          return;
        }

        const location = mapState.userLocation;
        if (!location) {
          mapUserMarker.hidden = true;
          mapUserAccuracy.hidden = true;
          return;
        }

        const point = centerToContainerPoint(location.lat, location.lon);
        mapUserMarker.hidden = false;
        mapUserMarker.style.left = `${point.x}px`;
        mapUserMarker.style.top = `${point.y}px`;

        const accuracyMeters = Number(location.accuracyMeters);
        if (!Number.isFinite(accuracyMeters) || accuracyMeters <= 0) {
          mapUserAccuracy.hidden = true;
          return;
        }

        const mpp = metersPerPixel(location.lat, mapState.zoom);
        if (!Number.isFinite(mpp) || mpp <= 0) {
          mapUserAccuracy.hidden = true;
          return;
        }

        const radiusPx = clamp(accuracyMeters / mpp, 6, 220);
        const diameterPx = Math.max(12, radiusPx * 2);

        mapUserAccuracy.hidden = false;
        mapUserAccuracy.style.width = `${diameterPx}px`;
        mapUserAccuracy.style.height = `${diameterPx}px`;
        mapUserAccuracy.style.left = `${point.x}px`;
        mapUserAccuracy.style.top = `${point.y}px`;
      }

      function setUserLocation(lat, lon, { accuracyMeters = null, centerMap = false } = {}) {
        const normalizedLat = clampLatToMercator(lat);
        const normalizedLon = Number(lon);
        if (!Number.isFinite(normalizedLat) || !Number.isFinite(normalizedLon)) {
          return false;
        }

        const normalizedAccuracy = Number(accuracyMeters);
        mapState.userLocation = {
          lat: normalizedLat,
          lon: normalizedLon,
          accuracyMeters:
            Number.isFinite(normalizedAccuracy) && normalizedAccuracy >= 0
              ? normalizedAccuracy
              : null,
          updatedAt: utcTimestamp(),
        };

        const accuracyText = formatAccuracyMeters(mapState.userLocation.accuracyMeters);
        updateMapLocationMeta(
          accuracyText
            ? `Geräteposition: ${formatCoord(normalizedLat)}, ${formatCoord(normalizedLon)} (${accuracyText})`
            : `Geräteposition: ${formatCoord(normalizedLat)}, ${formatCoord(normalizedLon)}`
        );

        if (centerMap) {
          setMapCenter(normalizedLat, normalizedLon, { render: true });
        } else {
          updateUserLocationOverlay();
        }
        return true;
      }

      function describeGeolocationError(error) {
        if (!error || typeof error !== "object") {
          return "Standort konnte nicht bestimmt werden.";
        }

        const code = Number(error.code);
        if (code === 1) {
          return "Standortfreigabe wurde abgelehnt. Bitte Berechtigung im Browser erlauben.";
        }
        if (code === 2) {
          return "Standort ist aktuell nicht verfügbar. Bitte Verbindung/GPS prüfen.";
        }
        if (code === 3) {
          return "Standortabfrage hat das Zeitlimit überschritten. Bitte erneut versuchen.";
        }
        return "Standort konnte nicht bestimmt werden.";
      }

      function getCurrentDevicePosition(options) {
        return new Promise((resolve, reject) => {
          navigator.geolocation.getCurrentPosition(resolve, reject, options);
        });
      }

      async function requestDeviceLocation() {
        if (!mapLocateBtn) {
          return;
        }

        if (typeof window !== "undefined" && window.isSecureContext === false) {
          const message = "Geräteposition benötigt HTTPS oder localhost (insecure context erkannt).";
          setMapStatus(message);
          updateMapLocationMeta("Geräteposition nicht verfügbar: nur in sicherem Kontext (HTTPS).");
          return;
        }

        if (typeof navigator === "undefined" || !navigator.geolocation || typeof navigator.geolocation.getCurrentPosition !== "function") {
          const message = "Geolocation wird von diesem Browser nicht unterstützt.";
          setMapStatus(message);
          updateMapLocationMeta("Geräteposition nicht verfügbar: Browser unterstützt Geolocation nicht.");
          return;
        }

        mapLocateBtn.disabled = true;
        mapLocateBtn.textContent = "Suche…";
        updateMapLocationMeta("Standortabfrage läuft …");

        emitUiEvent("ui.interaction.map.device_location.request", {
          direction: "human->ui",
          status: "triggered",
        });

        try {
          const position = await getCurrentDevicePosition({
            enableHighAccuracy: true,
            timeout: 12000,
            maximumAge: 0,
          });

          const latitude = Number(position && position.coords ? position.coords.latitude : Number.NaN);
          const longitude = Number(position && position.coords ? position.coords.longitude : Number.NaN);
          const accuracyMeters = Number(position && position.coords ? position.coords.accuracy : Number.NaN);

          const accepted = setUserLocation(latitude, longitude, {
            accuracyMeters,
            centerMap: true,
          });
          if (!accepted) {
            throw new Error("invalid_coordinates");
          }

          clearMapStatus();
          emitUiEvent("ui.interaction.map.device_location.success", {
            direction: "ui->human",
            status: "ok",
            lat_coarse: coarseCoord(latitude),
            lon_coarse: coarseCoord(longitude),
          });
        } catch (error) {
          const message =
            error instanceof Error && error.message === "invalid_coordinates"
              ? "Standortdaten sind ungültig und konnten nicht verwendet werden."
              : describeGeolocationError(error);
          setMapStatus(message);
          updateMapLocationMeta(message);
          emitUiEvent("ui.interaction.map.device_location.error", {
            level: "warn",
            direction: "ui->human",
            status: "error",
            error_message: message,
          });
        } finally {
          mapLocateBtn.disabled = false;
          mapLocateBtn.textContent = "Aktuelle Position";
        }
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
        updateUserLocationOverlay();
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

      function getMapSurfaceCenterClientPoint() {
        const rect = mapSurface.getBoundingClientRect();
        return {
          x: rect.left + rect.width / 2,
          y: rect.top + rect.height / 2,
        };
      }

      function zoomMapAtSurfaceCenter(delta) {
        const point = getMapSurfaceCenterClientPoint();
        zoomMapAtPoint(delta, point.x, point.y);
      }

      function normalizeWheelZoomDelta(event) {
        const primaryDelta = Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
        if (!Number.isFinite(primaryDelta) || primaryDelta === 0) {
          return 0;
        }

        const modeScale = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 96 : 1;
        const normalized = primaryDelta * modeScale;
        if (Math.abs(normalized) < 2) {
          return 0;
        }
        return normalized < 0 ? 1 : -1;
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
        if (mapSurface) {
          mapSurface.classList.add("has-marker");
        }
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
        emitUiEvent("ui.interaction.map.analyze_trigger", {
          direction: "human->ui",
          status: "triggered",
          input_kind: "coordinates",
          lat_coarse: coarseCoord(lat),
          lon_coarse: coarseCoord(lon),
          trigger: "map_click_or_keyboard",
        });

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
        const touchState = {
          pointers: new Map(),
          pinchActive: false,
          pinchStartDistance: 0,
          pinchStartZoom: mapState.zoom,
          anchorLat: mapState.centerLat,
          anchorLon: mapState.centerLon,
          pinchFrameHandle: null,
          pinchRenderPending: false,
        };
        let suppressNextClick = false;

        function queueClickSuppression(durationMs = 0) {
          suppressNextClick = true;
          window.setTimeout(() => {
            suppressNextClick = false;
          }, Math.max(0, Number(durationMs) || 0));
        }

        function releasePointerCaptureIfHeld(pointerId) {
          if (pointerId == null) {
            return;
          }
          try {
            if (mapSurface.hasPointerCapture(pointerId)) {
              mapSurface.releasePointerCapture(pointerId);
            }
          } catch (error) {
            // ignore (pointer might already be released)
          }
        }

        function isTouchLikePointer(event) {
          const pointerType = String(event && event.pointerType ? event.pointerType : "").toLowerCase();
          return pointerType === "touch" || pointerType === "pen";
        }

        function updateTouchPointer(pointerId, clientX, clientY) {
          touchState.pointers.set(pointerId, {
            pointerId,
            x: Number(clientX),
            y: Number(clientY),
          });
        }

        function pointerDistance(left, right) {
          return Math.hypot(left.x - right.x, left.y - right.y);
        }

        function pointerMidpoint(left, right) {
          return {
            x: (left.x + right.x) / 2,
            y: (left.y + right.y) / 2,
          };
        }

        function getActiveTouchPair() {
          if (touchState.pointers.size < 2) {
            return null;
          }
          const pointers = Array.from(touchState.pointers.values());
          return [pointers[0], pointers[1]];
        }

        function startDrag(pointerId, clientX, clientY, { capturePointer = true } = {}) {
          dragState.active = true;
          dragState.pointerId = pointerId;
          dragState.startX = clientX;
          dragState.startY = clientY;
          const center = centerWorld();
          dragState.startCenterX = center.x;
          dragState.startCenterY = center.y;
          dragState.moved = false;
          mapSurface.classList.add("dragging");
          if (capturePointer) {
            try {
              mapSurface.setPointerCapture(pointerId);
            } catch (error) {
              // ignore
            }
          }
        }

        function stopDrag({ suppressClick = true } = {}) {
          if (!dragState.active) {
            return;
          }
          mapSurface.classList.remove("dragging");
          releasePointerCaptureIfHeld(dragState.pointerId);
          const moved = dragState.moved;
          dragState.active = false;
          dragState.pointerId = null;
          dragState.moved = false;
          if (moved && suppressClick) {
            queueClickSuppression(0);
          }
        }

        function startPinchGesture() {
          const pair = getActiveTouchPair();
          if (!pair) {
            return false;
          }

          const [left, right] = pair;
          const startDistance = pointerDistance(left, right);
          if (!Number.isFinite(startDistance) || startDistance < 14) {
            return false;
          }

          const midpoint = pointerMidpoint(left, right);
          const rect = mapSurface.getBoundingClientRect();
          const rectWidth = Math.max(1, rect.width);
          const rectHeight = Math.max(1, rect.height);
          const x = clamp(midpoint.x - rect.left, 0, rectWidth);
          const y = clamp(midpoint.y - rect.top, 0, rectHeight);
          const anchor = containerPointToLatLon(x, y);

          touchState.pinchActive = true;
          touchState.pinchStartDistance = startDistance;
          touchState.pinchStartZoom = mapState.zoom;
          touchState.anchorLat = anchor.lat;
          touchState.anchorLon = anchor.lon;
          cancelPinchFrame();

          emitUiEvent("ui.interaction.map.pinch_start", {
            direction: "human->ui",
            status: "triggered",
            zoom: mapState.zoom,
          });
          schedulePinchTransform();

          return true;
        }

        function stopPinchGesture({ suppressClick = true } = {}) {
          if (!touchState.pinchActive) {
            return;
          }
          touchState.pinchActive = false;
          cancelPinchFrame();
          renderTiles();
          if (suppressClick) {
            queueClickSuppression(160);
          }
        }

        function applyPinchTransform() {
          if (!touchState.pinchActive) {
            touchState.pinchRenderPending = false;
            return;
          }
          const pair = getActiveTouchPair();
          if (!pair) {
            touchState.pinchRenderPending = false;
            return;
          }

          const [left, right] = pair;
          const currentDistance = pointerDistance(left, right);
          if (!Number.isFinite(currentDistance) || currentDistance < 8 || touchState.pinchStartDistance <= 0) {
            touchState.pinchRenderPending = false;
            return;
          }

          const scale = currentDistance / touchState.pinchStartDistance;
          const zoomFloat = touchState.pinchStartZoom + Math.log2(scale);
          const previousZoom = mapState.zoom;
          const targetZoom = clamp(Math.round(zoomFloat), MIN_ZOOM, MAX_ZOOM);
          const zoomChanged = targetZoom !== previousZoom;
          if (zoomChanged) {
            mapState.zoom = targetZoom;
          }

          const midpoint = pointerMidpoint(left, right);
          const rect = mapSurface.getBoundingClientRect();
          const rectWidth = Math.max(1, rect.width);
          const rectHeight = Math.max(1, rect.height);
          const x = clamp(midpoint.x - rect.left, 0, rectWidth);
          const y = clamp(midpoint.y - rect.top, 0, rectHeight);

          const focusWorld = latLonToWorld(touchState.anchorLat, touchState.anchorLon, mapState.zoom);
          const width = Math.max(1, mapSurface.clientWidth);
          const height = Math.max(1, mapSurface.clientHeight);
          const nextCenterWorldX = focusWorld.x - (x - width / 2);
          const nextCenterWorldY = focusWorld.y - (y - height / 2);

          setMapCenterFromWorld(nextCenterWorldX, nextCenterWorldY, { render: zoomChanged });
          touchState.pinchRenderPending = false;
        }

        function schedulePinchTransform() {
          if (!touchState.pinchActive) {
            return;
          }
          if (touchState.pinchRenderPending) {
            return;
          }
          touchState.pinchRenderPending = true;
          if (touchState.pinchFrameHandle != null) {
            return;
          }
          touchState.pinchFrameHandle = window.requestAnimationFrame(() => {
            touchState.pinchFrameHandle = null;
            applyPinchTransform();
          });
        }

        function cancelPinchFrame() {
          if (touchState.pinchFrameHandle != null) {
            window.cancelAnimationFrame(touchState.pinchFrameHandle);
            touchState.pinchFrameHandle = null;
          }
          touchState.pinchRenderPending = false;
        }

        mapSurface.addEventListener("pointerdown", (event) => {
          const isTouchLike = isTouchLikePointer(event);

          if (isTouchLike) {
            updateTouchPointer(event.pointerId, event.clientX, event.clientY);
            try {
              mapSurface.setPointerCapture(event.pointerId);
            } catch (error) {
              // ignore
            }
          }

          if (event.pointerType === "mouse" && event.button !== 0) {
            return;
          }

          if (isTouchLike && touchState.pointers.size >= 2) {
            stopDrag({ suppressClick: false });
            if (startPinchGesture()) {
              event.preventDefault();
            }
            return;
          }

          startDrag(event.pointerId, event.clientX, event.clientY, {
            capturePointer: !isTouchLike,
          });
        });

        mapSurface.addEventListener("pointermove", (event) => {
          const isTouchLike = isTouchLikePointer(event);

          if (isTouchLike && touchState.pointers.has(event.pointerId)) {
            updateTouchPointer(event.pointerId, event.clientX, event.clientY);

            if (touchState.pinchActive) {
              event.preventDefault();
              schedulePinchTransform();
              return;
            }

            if (touchState.pointers.size >= 2) {
              stopDrag({ suppressClick: false });
              if (startPinchGesture()) {
                event.preventDefault();
                return;
              }
            }
          }

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

        const endPointerInteraction = (event) => {
          const isTouchLike = isTouchLikePointer(event);

          if (isTouchLike && touchState.pointers.has(event.pointerId)) {
            touchState.pointers.delete(event.pointerId);
            releasePointerCaptureIfHeld(event.pointerId);

            if (touchState.pinchActive) {
              if (touchState.pointers.size >= 2) {
                startPinchGesture();
              } else {
                stopPinchGesture({ suppressClick: true });
                const remainingTouches = Array.from(touchState.pointers.values());
                if (remainingTouches.length === 1 && event.type !== "pointercancel") {
                  const remaining = remainingTouches[0];
                  startDrag(remaining.pointerId, remaining.x, remaining.y, {
                    capturePointer: false,
                  });
                }
              }
              return;
            }
          }

          if (dragState.active && event.pointerId === dragState.pointerId) {
            stopDrag({ suppressClick: true });
          }

          releasePointerCaptureIfHeld(event.pointerId);
        };

        mapSurface.addEventListener("pointerup", endPointerInteraction);
        mapSurface.addEventListener("pointercancel", endPointerInteraction);

        mapSurface.addEventListener("click", async (event) => {
          if (suppressNextClick || touchState.pinchActive) {
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
            const direction = normalizeWheelZoomDelta(event);
            if (direction === 0) {
              return;
            }
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
            zoomMapAtSurfaceCenter(1);
            return;
          }
          if (event.key === "-") {
            event.preventDefault();
            zoomMapAtSurfaceCenter(-1);
          }
        });

        if (mapLocateBtn) {
          mapLocateBtn.addEventListener("pointerdown", (event) => {
            event.stopPropagation();
          });
          mapLocateBtn.addEventListener("click", async (event) => {
            event.preventDefault();
            event.stopPropagation();
            await requestDeviceLocation();
            mapSurface.focus();
          });
        }

        if (mapZoomInBtn) {
          mapZoomInBtn.addEventListener("pointerdown", (event) => {
            event.stopPropagation();
          });
          mapZoomInBtn.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            zoomMapAtSurfaceCenter(1);
            mapSurface.focus();
          });
        }
        if (mapZoomOutBtn) {
          mapZoomOutBtn.addEventListener("pointerdown", (event) => {
            event.stopPropagation();
          });
          mapZoomOutBtn.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            zoomMapAtSurfaceCenter(-1);
            mapSurface.focus();
          });
        }

        window.addEventListener("resize", () => {
          renderTiles();
        });

        renderTiles();
      }

      function timeoutSecondsForMode(mode) {
        const normalized = String(mode || "basic").trim().toLowerCase();
        if (normalized === "extended") {
          return 290;
        }
        if (normalized === "risk") {
          return 295;
        }
        return 20;
      }

      function delay(ms) {
        const value = Number(ms);
        const waitMs = Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0;
        if (waitMs <= 0) {
          return Promise.resolve();
        }
        return new Promise((resolve) => {
          window.setTimeout(resolve, waitMs);
        });
      }

      function isSafeRetryMethod(method) {
        const normalizedMethod = String(method || "GET").trim().toUpperCase() || "GET";
        return SAFE_RETRY_METHODS.has(normalizedMethod);
      }

      function shouldRetrySafeRequest(method, statusCode, attemptIndex, maxRetries) {
        if (!isSafeRetryMethod(method)) {
          return false;
        }
        if (attemptIndex >= maxRetries) {
          return false;
        }
        const normalizedStatusCode = Number(statusCode);
        if (!Number.isInteger(normalizedStatusCode)) {
          return false;
        }
        return SAFE_RETRY_STATUS_CODES.has(normalizedStatusCode);
      }

      async function fetchWithTimeoutAndSafeRetry(url, init = {}, options = {}) {
        const method = String(init && init.method ? init.method : "GET").trim().toUpperCase() || "GET";
        const timeoutCandidate = Number(options && options.timeoutMs);
        const timeoutMs = Number.isFinite(timeoutCandidate) && timeoutCandidate > 0
          ? Math.round(timeoutCandidate)
          : 12000;
        const requestedRetries = Number(options && options.maxRetries);
        const maxRetries = isSafeRetryMethod(method) && Number.isFinite(requestedRetries)
          ? Math.max(0, Math.trunc(requestedRetries))
          : 0;
        const retryDelayCandidate = Number(options && options.retryDelayMs);
        const retryDelayMs = Number.isFinite(retryDelayCandidate)
          ? Math.max(0, Math.round(retryDelayCandidate))
          : 0;

        let attemptIndex = 0;
        const startedAt = performance.now();

        while (true) {
          const controller = new AbortController();
          const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);

          let response = null;
          let fetchError = null;
          try {
            response = await fetch(url, {
              ...init,
              method,
              signal: controller.signal,
            });
          } catch (error) {
            fetchError = error;
          } finally {
            clearTimeout(timeoutHandle);
          }

          const timedOut = Boolean(fetchError && fetchError.name === "AbortError");
          if (response) {
            if (shouldRetrySafeRequest(method, response.status, attemptIndex, maxRetries)) {
              attemptIndex += 1;
              await delay(retryDelayMs);
              continue;
            }
            return {
              ok: true,
              response,
              error: null,
              timedOut: false,
              attemptCount: attemptIndex + 1,
              retryCount: attemptIndex,
              timeoutMs,
              durationMs: Number((performance.now() - startedAt).toFixed(3)),
            };
          }

          if ((timedOut || fetchError) && attemptIndex < maxRetries) {
            attemptIndex += 1;
            await delay(retryDelayMs);
            continue;
          }

          return {
            ok: false,
            response: null,
            error: fetchError,
            timedOut,
            attemptCount: attemptIndex + 1,
            retryCount: attemptIndex,
            timeoutMs,
            durationMs: Number((performance.now() - startedAt).toFixed(3)),
          };
        }
      }

      function requestLifecycleStatus(statusCode, errorCode) {
        const normalizedError = String(errorCode || "").toLowerCase();
        if (normalizedError === "timeout" || normalizedError === "abort") {
          return "timeout";
        }
        if (normalizedError === "network_error") {
          return "network_error";
        }
        if (normalizedError === "invalid_json") {
          return "invalid_response";
        }
        if (statusCode >= 200 && statusCode < 400) {
          return "ok";
        }
        if (statusCode >= 400 && statusCode < 500) {
          return "client_error";
        }
        if (statusCode >= 500) {
          return "server_error";
        }
        return "unknown";
      }

      function requestLifecycleLevel(statusCode, errorCode) {
        const normalizedError = String(errorCode || "").toLowerCase();
        if (normalizedError === "timeout" || normalizedError === "abort" || normalizedError === "network_error") {
          return "warn";
        }
        if (normalizedError === "invalid_json") {
          return "error";
        }
        if (statusCode >= 500) {
          return "error";
        }
        if (statusCode >= 400) {
          return "warn";
        }
        return "info";
      }

      function normalizeErrorCode(errorCode) {
        return String(errorCode || "").trim().toLowerCase();
      }

      function resolveDevErrorClass(errorCode, statusCode) {
        const normalizedCode = normalizeErrorCode(errorCode);
        if (normalizedCode && DEV_ERROR_CLASS_BY_CODE[normalizedCode]) {
          return DEV_ERROR_CLASS_BY_CODE[normalizedCode];
        }

        if (normalizedCode.startsWith("refresh_") || normalizedCode.startsWith("idp_")) {
          return DEV_ERROR_CLASS.AUTH;
        }

        const normalizedStatus = Number(statusCode);
        if (Number.isFinite(normalizedStatus)) {
          if (normalizedStatus === 401 || normalizedStatus === 403) {
            return DEV_ERROR_CLASS.AUTH;
          }
          if (normalizedStatus === 0 || normalizedStatus === 408 || normalizedStatus === 504) {
            return DEV_ERROR_CLASS.NETWORK;
          }
          if (normalizedStatus >= 400) {
            return DEV_ERROR_CLASS.API;
          }
        }

        if (!normalizedCode) {
          return "";
        }
        return DEV_ERROR_CLASS.API;
      }

      function buildDevErrorLogFields(errorCode, statusCode) {
        return {
          error_code: normalizeErrorCode(errorCode),
          error_class: resolveDevErrorClass(errorCode, statusCode),
        };
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

      function buildLoginRedirectUrl(authReason) {
        const normalizedReason = normalizeErrorCode(authReason) || "session_recovery";
        const nextPath = typeof window !== "undefined" && window.location
          ? `${window.location.pathname || "/gui"}${window.location.search || ""}${window.location.hash || ""}`
          : "/gui";

        if (typeof URLSearchParams === "undefined") {
          return `${AUTH_LOGIN_ENDPOINT}?next=${encodeURIComponent(nextPath || "/gui")}&reason=${encodeURIComponent(normalizedReason)}`;
        }

        const params = new URLSearchParams();
        params.set("next", nextPath || "/gui");
        params.set("reason", normalizedReason);
        return `${AUTH_LOGIN_ENDPOINT}?${params.toString()}`;
      }

      function updateAuthEntryPoints() {
        const isAuthenticated = authState.authenticated === true;

        if (burgerLoginLink) {
          burgerLoginLink.hidden = isAuthenticated;
          burgerLoginLink.setAttribute("aria-hidden", isAuthenticated ? "true" : "false");
          burgerLoginLink.href = buildLoginRedirectUrl("manual_login");
        }
        if (burgerLogoutLink) {
          burgerLogoutLink.hidden = !isAuthenticated;
          burgerLogoutLink.setAttribute("aria-hidden", isAuthenticated ? "false" : "true");
        }

        if (authLoginMetaEl) {
          authLoginMetaEl.hidden = isAuthenticated;
        }
        if (authLoginInlineEl) {
          authLoginInlineEl.href = buildLoginRedirectUrl("manual_login");
        }
      }

      function setAuthState(
        nextAuthenticated,
        {
          userClaims = {},
          authCheckSupported = true,
          checkedAtMs = Date.now(),
          sessionExpiresAtMs = null,
        } = {}
      ) {
        if (typeof nextAuthenticated === "boolean") {
          authState.authenticated = nextAuthenticated;
        }
        authState.userClaims = userClaims && typeof userClaims === "object" ? userClaims : {};
        authState.authCheckSupported = Boolean(authCheckSupported);
        authState.checkedAtMs = Number.isFinite(checkedAtMs) ? checkedAtMs : Date.now();

        if (Number.isFinite(Number(sessionExpiresAtMs)) && Number(sessionExpiresAtMs) > 0) {
          authState.sessionExpiresAtMs = Number(sessionExpiresAtMs);
        } else if (sessionExpiresAtMs === 0) {
          authState.sessionExpiresAtMs = 0;
          authState.warningShownForExpiryMs = 0;
          hideSessionExpiryWarning();
        }

        if (authState.authenticated !== true) {
          authState.sessionExpiresAtMs = 0;
          authState.warningShownForExpiryMs = 0;
          hideSessionExpiryWarning();
        }

        updateAuthEntryPoints();
      }

      function authCheckIsFresh() {
        if (!Number.isFinite(authState.checkedAtMs) || authState.checkedAtMs <= 0) {
          return false;
        }
        return Date.now() - authState.checkedAtMs <= AUTH_CHECK_CACHE_TTL_MS;
      }

      async function refreshAuthSession({ force = false } = {}) {
        if (!authState.authCheckSupported) {
          updateAuthEntryPoints();
          return authState.authenticated === true;
        }

        if (!force && authCheckIsFresh() && authState.authenticated !== null) {
          return authState.authenticated === true;
        }

        const headers = {
          "Accept": "application/json",
          "X-Session-Id": uiSessionId,
        };

        const authFetch = await fetchWithTimeoutAndSafeRetry(
          AUTH_ME_ENDPOINT,
          {
            method: "GET",
            headers,
            credentials: "include",
          },
          {
            timeoutMs: DEV_CLIENT_REQUEST_POLICY.authCheckTimeoutMs,
            maxRetries: DEV_CLIENT_REQUEST_POLICY.getRetries,
            retryDelayMs: DEV_CLIENT_REQUEST_POLICY.retryDelayMs,
          }
        );

        if (!authFetch.ok || !authFetch.response) {
          updateAuthEntryPoints();
          return authState.authenticated === true;
        }

        const response = authFetch.response;

        if (response.status === 404 || response.status === 405) {
          setAuthState(authState.authenticated === true, {
            userClaims: authState.userClaims,
            authCheckSupported: false,
            sessionExpiresAtMs: 0,
          });
          return authState.authenticated === true;
        }

        let payload = null;
        try {
          payload = await response.json();
        } catch (error) {
          payload = null;
        }

        if (response.ok && payload && payload.ok === true) {
          const sessionExpiresAtMs = parseSessionExpiryMs(payload.session_expires_at);
          setAuthState(true, {
            userClaims: payload.user_claims || {},
            authCheckSupported: true,
            sessionExpiresAtMs,
          });
          updateSessionExpiryWarning(payload);
          return true;
        }

        if (response.status === 401) {
          setAuthState(false, {
            userClaims: {},
            authCheckSupported: true,
            sessionExpiresAtMs: 0,
          });
          return false;
        }

        updateAuthEntryPoints();
        return authState.authenticated === true;
      }

      async function ensureAuthenticatedForAction({ trigger = "auth_guard", requestId = "" } = {}) {
        const authenticated = await refreshAuthSession({ force: true });
        if (authenticated) {
          return true;
        }
        if (!authState.authCheckSupported) {
          return true;
        }

        scheduleReLoginRedirect(401, "no_session_cookie", requestId);
        emitUiEvent("ui.auth.guard.redirect", {
          level: "warn",
          direction: "ui->human",
          status: "redirect",
          trigger,
          requestId,
        });
        return false;
      }

      function scheduleReLoginRedirect(statusCode, errorCode, requestId) {
        if (authRecoveryRedirectScheduled) {
          return;
        }
        authRecoveryRedirectScheduled = true;

        const normalizedErrorCode = normalizeErrorCode(errorCode);
        setAuthState(false, {
          userClaims: {},
          authCheckSupported: true,
        });
        const authReason = resolveAuthRecoveryReason(statusCode, normalizedErrorCode);
        const loginUrl = buildLoginRedirectUrl(authReason);
        const hint = "Session wird neu aufgebaut — Eingaben wurden lokal gesichert. Weiterleitung zum Login…";

        persistAnalyzeDraft("auth_recovery_redirect");
        hideSessionExpiryWarning();

        setPhase("error", {
          trigger: "auth_recovery_redirect",
          requestId: String(requestId || "").trim(),
          errorCode: normalizedErrorCode,
        });
        clearServerErrorView();
        state.lastError = withTechnicalRequestIdHint(hint, requestId);
        renderState();

        if (typeof window === "undefined" || !window.setTimeout || !window.location) {
          authRecoveryRedirectScheduled = false;
          return;
        }

        window.setTimeout(() => {
          window.location.assign(loginUrl);
        }, 400);
      }

      function buildAuthorizationUxErrorMessage(statusCode, fallbackMessage, errorCode) {
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
        return String(fallbackMessage || "Unbekannter Fehler");
      }

      function resolveAuthFailure(statusCode, errorCode, fallbackMessage) {
        const normalizedCode = normalizeErrorCode(errorCode);
        return {
          errorCode: normalizedCode,
          errorMessage: buildAuthorizationUxErrorMessage(statusCode, fallbackMessage, normalizedCode),
          requiresLoginRecovery: isSessionRecoveryRequired(statusCode, normalizedCode),
        };
      }

      function resolveResponseRequestId(response, payload, fallbackRequestId = "") {
        const payloadRequestId = payload && payload.request_id ? String(payload.request_id).trim() : "";
        if (payloadRequestId) {
          return payloadRequestId;
        }

        const responseRequestId =
          response && response.headers
            ? String(
                response.headers.get("X-Request-Id")
                || response.headers.get("x-request-id")
                || response.headers.get("X-Correlation-Id")
                || response.headers.get("x-correlation-id")
                || ""
              ).trim()
            : "";
        if (responseRequestId) {
          return responseRequestId;
        }
        return String(fallbackRequestId || "").trim();
      }

      function withTechnicalRequestIdHint(message, requestId) {
        const normalizedMessage = String(message || "").trim() || "Unbekannter Fehler";
        const normalizedRequestId = normalizeTraceRequestId(requestId);
        if (!normalizedRequestId) {
          return normalizedMessage;
        }
        const requestSuffix = `(request_id: ${normalizedRequestId})`;
        if (normalizedMessage.includes(requestSuffix)) {
          return normalizedMessage;
        }
        return `${normalizedMessage} ${requestSuffix}`;
      }

      function isServerErrorStatus(statusCode) {
        const normalizedStatus = Number(statusCode);
        return Number.isInteger(normalizedStatus) && normalizedStatus >= 500 && normalizedStatus < 600;
      }

      function cloneAnalyzePayload(payload) {
        if (!payload || typeof payload !== "object") {
          return null;
        }
        try {
          return JSON.parse(JSON.stringify(payload));
        } catch (error) {
          return null;
        }
      }

      function setServerErrorView(details = {}) {
        state.serverErrorView = {
          visible: Boolean(details.visible),
          statusCode: Number.isFinite(Number(details.statusCode)) ? Number(details.statusCode) : null,
          errorCode: String(details.errorCode || "").trim(),
          requestId: normalizeTraceRequestId(details.requestId || ""),
          requestStartedAt: String(details.requestStartedAt || "").trim(),
        };
      }

      function clearServerErrorView() {
        setServerErrorView({ visible: false });
      }

      function rememberAnalyzeRequest(payload, inputLabel) {
        const clonedPayload = cloneAnalyzePayload(payload);
        if (!clonedPayload) {
          state.lastAnalyzeRequest = null;
          return;
        }
        state.lastAnalyzeRequest = {
          payload: clonedPayload,
          inputLabel: String(inputLabel || "").trim(),
        };
      }

      function describeServerErrorMeta(viewState = {}) {
        const segments = [];
        const statusCode = Number(viewState.statusCode);
        if (Number.isInteger(statusCode)) {
          segments.push(`HTTP ${statusCode}`);
        }

        const requestTime = formatLocalTime(viewState.requestStartedAt);
        if (requestTime) {
          segments.push(`Request-Zeit: ${requestTime}`);
        }

        const requestId = normalizeTraceRequestId(viewState.requestId);
        if (requestId) {
          segments.push(`request_id: ${requestId}`);
        }

        const errorCode = String(viewState.errorCode || "").trim();
        if (errorCode) {
          segments.push(`error: ${errorCode}`);
        }

        if (!segments.length) {
          return "Keine technischen Details verfügbar.";
        }
        return segments.join(" · ");
      }

      async function runAnalyze(payload, context = {}) {
        const traceId = String(context.traceId || "").trim();
        const requestId = String(context.requestId || "").trim() || createUiCorrelationId("req");
        const inputKind = String(context.inputKind || inferInputKind(payload));

        const headers = { "Content-Type": "application/json" };
        headers["X-Request-Id"] = requestId;
        headers["X-Session-Id"] = uiSessionId;

        emitUiEvent("ui.api.request.start", {
          traceId,
          requestId,
          direction: "ui->api",
          status: "sent",
          route: "/analyze",
          method: "POST",
          input_kind: inputKind,
          auth_present: false,
        });

        const timeoutSeconds = Number(payload && payload.timeout_seconds);
        const timeoutMs = Number.isFinite(timeoutSeconds) && timeoutSeconds > 0
          ? Math.round(timeoutSeconds * 1000) + 1500
          : 25000;

        const controller = new AbortController();
        const timeoutHandle = setTimeout(() => controller.abort(), timeoutMs);
        const startedAt = performance.now();
        const requestStartedAtIso = utcTimestamp();

        let response;
        try {
          response = await fetch("/analyze", {
            method: "POST",
            headers,
            credentials: "include",
            body: JSON.stringify(payload),
            signal: controller.signal,
          });
        } catch (error) {
          const durationMs = Number((performance.now() - startedAt).toFixed(3));
          if (error && error.name === "AbortError") {
            emitUiEvent("ui.api.request.end", {
              level: requestLifecycleLevel(504, "timeout"),
              traceId,
              requestId,
              direction: "api->ui",
              status: requestLifecycleStatus(504, "timeout"),
              route: "/analyze",
              method: "POST",
              status_code: 504,
              duration_ms: durationMs,
              ...buildDevErrorLogFields("timeout", 504),
            });
            throw new Error(
              withTechnicalRequestIdHint(
                `timeout: Anfrage nach ${Math.max(1, Math.round(timeoutMs / 1000))}s ohne Antwort abgebrochen. Bitte Retry ausführen.`,
                requestId
              )
            );
          }

          emitUiEvent("ui.api.request.end", {
            level: requestLifecycleLevel(0, "network_error"),
            traceId,
            requestId,
            direction: "api->ui",
            status: requestLifecycleStatus(0, "network_error"),
            route: "/analyze",
            method: "POST",
            status_code: 0,
            duration_ms: durationMs,
            ...buildDevErrorLogFields("network_error", 0),
          });
          const networkMessage =
            error instanceof Error && String(error.message || "").trim()
              ? String(error.message)
              : "network_error: Anfrage fehlgeschlagen";
          throw new Error(withTechnicalRequestIdHint(networkMessage, requestId));
        } finally {
          clearTimeout(timeoutHandle);
        }

        const durationMs = Number((performance.now() - startedAt).toFixed(3));

        let parsed;
        try {
          parsed = await response.json();
        } catch (error) {
          const responseRequestId = resolveResponseRequestId(response, null, requestId);
          emitUiEvent("ui.api.request.end", {
            level: requestLifecycleLevel(response.status, "invalid_json"),
            traceId,
            requestId: responseRequestId,
            direction: "api->ui",
            status: requestLifecycleStatus(response.status, "invalid_json"),
            route: "/analyze",
            method: "POST",
            status_code: response.status,
            duration_ms: durationMs,
            ...buildDevErrorLogFields("invalid_json", response.status),
          });
          throw new Error(withTechnicalRequestIdHint("Response ist kein gültiges JSON.", responseRequestId));
        }

        const responseRequestId = resolveResponseRequestId(response, parsed, requestId);
        if (!response.ok || !parsed.ok) {
          const errCode = parsed && parsed.error ? String(parsed.error) : `http_${response.status}`;
          const errMsg = parsed && parsed.message ? String(parsed.message) : "Unbekannter Fehler";
          const authFailure = resolveAuthFailure(response.status, errCode, `${errCode}: ${errMsg}`);
          const failingResponse = parsed || { ok: false, error: authFailure.errorCode, message: errMsg };

          emitUiEvent("ui.api.request.end", {
            level: requestLifecycleLevel(response.status, authFailure.errorCode),
            traceId,
            requestId: responseRequestId,
            direction: "api->ui",
            status: requestLifecycleStatus(response.status, authFailure.errorCode),
            route: "/analyze",
            method: "POST",
            status_code: response.status,
            duration_ms: durationMs,
            ...buildDevErrorLogFields(authFailure.errorCode, response.status),
            auth_recovery_required: authFailure.requiresLoginRecovery,
          });

          const serverError = isServerErrorStatus(response.status);
          const unifiedServerErrorMessage = withTechnicalRequestIdHint(
            "Temporärer Serverfehler (5xx). Bitte Retry ausführen.",
            responseRequestId
          );

          return {
            ok: false,
            requestId: responseRequestId,
            response: failingResponse,
            errorMessage: serverError
              ? unifiedServerErrorMessage
              : withTechnicalRequestIdHint(authFailure.errorMessage, responseRequestId),
            errorCode: authFailure.errorCode,
            statusCode: response.status,
            requiresLoginRecovery: authFailure.requiresLoginRecovery,
            isServerError: serverError,
            requestStartedAt: requestStartedAtIso,
          };
        }

        emitUiEvent("ui.api.request.end", {
          level: requestLifecycleLevel(response.status, ""),
          traceId,
          requestId: responseRequestId,
          direction: "api->ui",
          status: requestLifecycleStatus(response.status, ""),
          route: "/analyze",
          method: "POST",
          status_code: response.status,
          duration_ms: durationMs,
        });

        return {
          ok: true,
          requestId: responseRequestId,
          response: parsed,
          errorMessage: null,
          errorCode: "",
          statusCode: response.status,
          isServerError: false,
          requestStartedAt: requestStartedAtIso,
        };
      }

      function buildAnalyzePayload(base) {
        const mode = String(modeEl.value || "basic").trim().toLowerCase() || "basic";
        const asyncRequested = Boolean(asyncModeRequestedEl && asyncModeRequestedEl.checked);

        const options = {
          response_mode: "compact",
        };
        if (asyncRequested) {
          options.async_mode = { requested: true };
        }

        return {
          ...base,
          intelligence_mode: mode,
          timeout_seconds: timeoutSecondsForMode(mode),
          options,
        };
      }

      async function startAnalyze(payload, inputLabel, options = {}) {
        const requestId = createUiCorrelationId("req");
        const traceId = requestId;
        const inputKind = inferInputKind(payload);
        const trigger = String(options.trigger || "analyze_start").trim() || "analyze_start";
        const isRetryAttempt = Boolean(options.isRetryAttempt);

        const authenticated = await ensureAuthenticatedForAction({
          trigger: "analyze_preflight",
          requestId,
        });
        if (!authenticated) {
          setResultsListLoading(false);
          setResultsListRecoveryState("unauthorized");
          renderResultsList();
          emitUiEvent("ui.input.rejected", {
            level: "warn",
            traceId,
            requestId,
            direction: "ui->human",
            status: "auth_required",
            input_kind: inputKind,
          });
          return;
        }

        emitUiEvent("ui.input.accepted", {
          traceId,
          requestId,
          direction: "human->ui",
          status: isRetryAttempt ? "retry_attempt" : "accepted",
          input_kind: inputKind,
          input_label: inputKind,
          intelligence_mode: String(payload && payload.intelligence_mode ? payload.intelligence_mode : "basic"),
        });

        rememberAnalyzeRequest(payload, inputLabel);
        clearServerErrorView();
        setResultsListRecoveryState("");
        setResultsListLoading(true);

        setPhase("loading", {
          traceId,
          requestId,
          trigger,
        });
        state.lastError = null;
        state.lastPayload = { ok: false, loading: true, request: payload };
        state.lastRequestId = requestId;
        state.lastInput = inputLabel;
        state.coreFactors = [];
        submitBtn.disabled = true;
        renderState();
        renderResultsList();

        try {
          const result = await runAnalyze(payload, {
            traceId,
            requestId,
            inputKind,
          });

          setResultsListLoading(false);
          state.lastRequestId = result.requestId || requestId;
          state.lastPayload = result.response;
          setPhase(result.ok ? "success" : "error", {
            traceId,
            requestId: state.lastRequestId,
            trigger: "analyze_result",
            errorCode: result.errorCode || "",
          });

          if (!result.ok && result.isServerError) {
            setServerErrorView({
              visible: true,
              statusCode: result.statusCode,
              errorCode: result.errorCode,
              requestId: state.lastRequestId,
              requestStartedAt: result.requestStartedAt || utcTimestamp(),
            });
            state.lastError = null;
          } else {
            clearServerErrorView();
            state.lastError = result.errorMessage;
          }

          state.coreFactors = result.ok ? extractCoreFactors(result.response) : [];

          if (result.ok) {
            setResultsListRecoveryState("");
          } else if (!result.isServerError) {
            setResultsListRecoveryState(resolveResultsRecoveryStateFromAnalyzeResult(result));
          }

          if (!result.ok && result.requiresLoginRecovery) {
            scheduleReLoginRedirect(result.statusCode, result.errorCode, state.lastRequestId);
          }

          if (result.ok) {
            clearAnalyzeDraft();
            const entry = extractResultsListEntry(result.response, { inputLabel });
            if (entry) {
              addResultsEntry(entry);
              loadHistory();
            } else {
              renderResultsList();
            }
          } else {
            renderResultsList();
          }
        } catch (error) {
          clearServerErrorView();
          setResultsListLoading(false);
          setPhase("error", {
            traceId,
            requestId,
            trigger: "network_or_runtime_error",
            errorCode: "network_error",
          });
          state.lastError = error instanceof Error ? error.message : "Netzwerkfehler";
          state.lastPayload = {
            ok: false,
            error: "network_error",
            message: state.lastError,
          };
          setResultsListRecoveryState("network");
          state.coreFactors = [];
          renderResultsList();
        } finally {
          submitBtn.disabled = false;
          renderState();
        }
      }

      async function retryLastAnalyzeRequestFromServerError() {
        const hasRetryContext = Boolean(
          state.lastAnalyzeRequest
          && state.lastAnalyzeRequest.payload
          && typeof state.lastAnalyzeRequest.payload === "object"
        );
        if (!hasRetryContext || state.phase === "loading") {
          return;
        }

        const retryPayload = cloneAnalyzePayload(state.lastAnalyzeRequest.payload);
        if (!retryPayload) {
          return;
        }

        const retryInputLabel = String(state.lastAnalyzeRequest.inputLabel || state.lastInput || "Retry").trim() || "Retry";

        const retryErrorCode = String(state.serverErrorView && state.serverErrorView.errorCode ? state.serverErrorView.errorCode : "");
        const retryStatusCode = Number(state.serverErrorView && state.serverErrorView.statusCode);
        emitUiEvent("ui.interaction.error_view.retry", {
          direction: "human->ui",
          status: "triggered",
          requestId: normalizeTraceRequestId(state.serverErrorView && state.serverErrorView.requestId),
          status_code: retryStatusCode,
          ...buildDevErrorLogFields(retryErrorCode, retryStatusCode),
        });

        await startAnalyze(retryPayload, retryInputLabel, {
          trigger: "server_error_retry",
          isRetryAttempt: true,
        });
      }

      async function runTraceLookup(traceRequestId, context = {}) {
        const normalizedTraceRequestId = normalizeTraceRequestId(traceRequestId);
        const traceId = String(context.traceId || "").trim() || createUiCorrelationId("trace");
        const requestId = String(context.requestId || "").trim() || createUiCorrelationId("req");
        const endpointUrl = buildTraceLookupUrl(normalizedTraceRequestId);

        const headers = {
          "Accept": "application/json",
          "X-Request-Id": requestId,
          "X-Session-Id": uiSessionId,
        };

        emitUiEvent("ui.trace.request.start", {
          traceId,
          requestId,
          direction: "ui->api",
          status: "sent",
          route: TRACE_DEBUG_ENDPOINT,
          method: "GET",
          trace_request_id: normalizedTraceRequestId,
          auth_present: false,
        });

        const traceFetch = await fetchWithTimeoutAndSafeRetry(
          endpointUrl,
          {
            method: "GET",
            headers,
          },
          {
            timeoutMs: DEV_CLIENT_REQUEST_POLICY.traceTimeoutMs,
            maxRetries: DEV_CLIENT_REQUEST_POLICY.getRetries,
            retryDelayMs: DEV_CLIENT_REQUEST_POLICY.retryDelayMs,
          }
        );

        if (!traceFetch.ok || !traceFetch.response) {
          const errorCode = traceFetch.timedOut ? "timeout" : "network_error";
          const durationMs = Number(traceFetch.durationMs || 0);
          emitUiEvent("ui.trace.request.end", {
            level: requestLifecycleLevel(errorCode === "timeout" ? 504 : 0, errorCode),
            traceId,
            requestId,
            direction: "api->ui",
            status: requestLifecycleStatus(errorCode === "timeout" ? 504 : 0, errorCode),
            route: TRACE_DEBUG_ENDPOINT,
            method: "GET",
            status_code: errorCode === "timeout" ? 504 : 0,
            duration_ms: durationMs,
            ...buildDevErrorLogFields(errorCode, errorCode === "timeout" ? 504 : 0),
            trace_request_id: normalizedTraceRequestId,
          });
          if (errorCode === "timeout") {
            throw new Error(
              withTechnicalRequestIdHint(
                `timeout: Trace-Abfrage nach ${Math.max(1, Math.round(traceFetch.timeoutMs / 1000))}s ohne Antwort abgebrochen. Bitte Retry ausführen.`,
                requestId
              )
            );
          }
          throw new Error(withTechnicalRequestIdHint("network_error: Trace-Abfrage fehlgeschlagen. Bitte Retry ausführen.", requestId));
        }

        const response = traceFetch.response;
        const durationMs = Number(traceFetch.durationMs || 0);

        let parsed;
        try {
          parsed = await response.json();
        } catch (error) {
          const responseRequestId = resolveResponseRequestId(response, null, requestId);
          emitUiEvent("ui.trace.request.end", {
            level: requestLifecycleLevel(response.status, "invalid_json"),
            traceId,
            requestId: responseRequestId,
            direction: "api->ui",
            status: requestLifecycleStatus(response.status, "invalid_json"),
            route: TRACE_DEBUG_ENDPOINT,
            method: "GET",
            status_code: response.status,
            duration_ms: durationMs,
            ...buildDevErrorLogFields("invalid_json", response.status),
            trace_request_id: normalizedTraceRequestId,
          });
          throw new Error(
            withTechnicalRequestIdHint("invalid_json: Trace-Response ist kein gültiges JSON.", responseRequestId)
          );
        }

        const responseRequestId = resolveResponseRequestId(response, parsed, requestId);
        if (!response.ok || !parsed.ok) {
          const errCode = parsed && parsed.error ? String(parsed.error) : `http_${response.status}`;
          const errMsg = parsed && parsed.message ? String(parsed.message) : "Trace-Abfrage fehlgeschlagen";
          const authFailure = resolveAuthFailure(response.status, errCode, `${errCode}: ${errMsg}`);

          emitUiEvent("ui.trace.request.end", {
            level: requestLifecycleLevel(response.status, authFailure.errorCode),
            traceId,
            requestId: responseRequestId,
            direction: "api->ui",
            status: requestLifecycleStatus(response.status, authFailure.errorCode),
            route: TRACE_DEBUG_ENDPOINT,
            method: "GET",
            status_code: response.status,
            duration_ms: durationMs,
            ...buildDevErrorLogFields(authFailure.errorCode, response.status),
            trace_request_id: normalizedTraceRequestId,
          });

          return {
            ok: false,
            requestId: responseRequestId,
            traceRequestId: normalizedTraceRequestId,
            response: parsed || { ok: false, error: authFailure.errorCode, message: errMsg },
            errorCode: authFailure.errorCode,
            statusCode: response.status,
            errorMessage: withTechnicalRequestIdHint(authFailure.errorMessage, responseRequestId),
            requiresLoginRecovery: authFailure.requiresLoginRecovery,
          };
        }

        const tracePayload = parsed && parsed.trace && typeof parsed.trace === "object" ? parsed.trace : {};
        const traceReason = String(tracePayload.reason || "").trim();
        const rawTraceState = String(tracePayload.state || "").trim();
        const events = normalizeTraceEvents(tracePayload.events);

        let phase = "success";
        let emptyMessage = "";
        if (rawTraceState === "empty") {
          if (traceReason === "request_id_unknown_or_no_events" || traceReason === "request_id_outside_window") {
            phase = "unknown";
          } else {
            phase = "empty";
          }
          emptyMessage = describeTraceEmptyReason(traceReason);
        }

        emitUiEvent("ui.trace.request.end", {
          level: requestLifecycleLevel(response.status, ""),
          traceId,
          requestId: responseRequestId,
          direction: "api->ui",
          status: requestLifecycleStatus(response.status, ""),
          route: TRACE_DEBUG_ENDPOINT,
          method: "GET",
          status_code: response.status,
          duration_ms: durationMs,
          trace_request_id: normalizedTraceRequestId,
          timeline_state: rawTraceState || phase,
          timeline_events: events.length,
        });

        return {
          ok: true,
          requestId: responseRequestId,
          traceRequestId: String(parsed.trace_request_id || normalizedTraceRequestId),
          response: parsed,
          statusCode: response.status,
          phase,
          emptyMessage,
          events,
        };
      }

      async function startTraceLookup(rawTraceRequestId, trigger = "trace_submit") {
        const normalizedTraceRequestId = normalizeTraceRequestId(rawTraceRequestId);
        const requestId = createUiCorrelationId("req");
        const traceId = requestId;

        if (!normalizedTraceRequestId) {
          setTracePhase("error", {
            traceId,
            requestId,
            trigger,
            errorCode: "validation",
          });
          traceState.requestId = "";
          traceState.apiRequestId = requestId;
          traceState.payload = {
            ok: false,
            error: "validation",
            message: "request_id darf nicht leer sein",
          };
          traceState.events = [];
          traceState.emptyMessage = "";
          traceState.error = "Bitte eine request_id eingeben.";
          renderTraceState();
          return;
        }

        traceRequestIdEl.value = normalizedTraceRequestId;
        updateTraceDeepLink(normalizedTraceRequestId);

        setTracePhase("loading", {
          traceId,
          requestId,
          trigger,
        });
        traceState.requestId = normalizedTraceRequestId;
        traceState.apiRequestId = requestId;
        traceState.payload = {
          ok: false,
          loading: true,
          request_id: normalizedTraceRequestId,
        };
        traceState.error = "";
        traceState.emptyMessage = "";
        traceState.events = [];
        traceSubmitBtn.disabled = true;
        renderTraceState();

        try {
          const result = await runTraceLookup(normalizedTraceRequestId, {
            traceId,
            requestId,
          });

          traceState.requestId = result.traceRequestId || normalizedTraceRequestId;
          traceState.apiRequestId = result.requestId || requestId;
          traceState.payload = result.response;
          traceState.events = result.ok ? result.events : [];
          traceState.emptyMessage = result.ok ? result.emptyMessage : "";
          traceState.error = result.ok ? "" : result.errorMessage;

          setTracePhase(result.ok ? result.phase : "error", {
            traceId,
            requestId: traceState.apiRequestId,
            trigger,
            errorCode: result.ok ? "" : result.errorCode || "",
          });

          if (!result.ok && result.requiresLoginRecovery) {
            scheduleReLoginRedirect(result.statusCode, result.errorCode, traceState.apiRequestId);
          }
        } catch (error) {
          setTracePhase("error", {
            traceId,
            requestId,
            trigger,
            errorCode: "network_error",
          });
          traceState.apiRequestId = requestId;
          traceState.payload = {
            ok: false,
            error: "network_error",
            message: error instanceof Error ? error.message : "Trace-Abfrage fehlgeschlagen",
          };
          traceState.events = [];
          traceState.emptyMessage = "";
          traceState.error = error instanceof Error ? error.message : "Trace-Abfrage fehlgeschlagen";
        } finally {
          traceSubmitBtn.disabled = false;
          renderTraceState();
        }
      }

      if (queryEl) {
        queryEl.addEventListener("input", () => persistAnalyzeDraft("query_input"));
      }
      if (modeEl) {
        modeEl.addEventListener("change", () => persistAnalyzeDraft("mode_change"));
      }
      if (asyncModeRequestedEl) {
        asyncModeRequestedEl.addEventListener("change", () => persistAnalyzeDraft("async_toggle"));
      }

      formEl.addEventListener("submit", async (event) => {
        event.preventDefault();
        persistAnalyzeDraft("form_submit");

        const query = (queryEl.value || "").trim();
        emitUiEvent("ui.interaction.form.submit", {
          direction: "human->ui",
          status: "triggered",
          input_kind: "query",
          query_length: query.length,
          intelligence_mode: String(modeEl.value || "basic").trim().toLowerCase() || "basic",
          async_mode_requested: Boolean(asyncModeRequestedEl && asyncModeRequestedEl.checked),
        });

        if (!query) {
          setPhase("error", {
            trigger: "validation_error",
            errorCode: "validation",
          });
          clearServerErrorView();
          state.lastError = "Bitte eine Adresse eingeben.";
          state.lastPayload = {
            ok: false,
            error: "validation",
            message: "query darf nicht leer sein",
          };

          emitUiEvent("ui.validation.error", {
            level: "warn",
            direction: "ui->human",
            status: "error",
            field: "query",
            ...buildDevErrorLogFields("validation", 400),
          });

          state.lastInput = null;
          state.coreFactors = [];
          renderState();
          return;
        }

        const payload = buildAnalyzePayload({ query });
        await startAnalyze(payload, `Adresse: ${query}`);
      });

      if (serverErrorRetryBtnEl) {
        serverErrorRetryBtnEl.addEventListener("click", async () => {
          await retryLastAnalyzeRequestFromServerError();
        });
      }

      requestTraceLinkEl.addEventListener("click", async (event) => {
        event.preventDefault();
        await openTraceFromResultPanel();
      });

      requestIdCopyBtnEl.addEventListener("click", async () => {
        const requestId = normalizeTraceRequestId(state.lastRequestId);
        if (!requestId) {
          setRequestIdFeedback("Keine Request-ID zum Kopieren vorhanden.", {
            isError: true,
            autoResetMs: 2400,
          });
          return;
        }

        const copied = await copyTextToClipboard(requestId);
        if (copied) {
          setRequestIdFeedback("Request-ID in die Zwischenablage kopiert.", {
            autoResetMs: 2400,
          });
          emitUiEvent("ui.interaction.request_id.copy", {
            direction: "human->ui",
            status: "copied",
            requestId,
          });
          return;
        }

        setRequestIdFeedback("Copy fehlgeschlagen. Bitte ID manuell markieren.", {
          isError: true,
          autoResetMs: 3200,
        });
        emitUiEvent("ui.interaction.request_id.copy", {
          level: "warn",
          direction: "human->ui",
          status: "copy_failed",
          requestId,
        });
      });

      traceFormEl.addEventListener("submit", async (event) => {
        event.preventDefault();
        const traceRequestId = normalizeTraceRequestId(traceRequestIdEl.value);

        emitUiEvent("ui.interaction.trace.submit", {
          direction: "human->ui",
          status: "triggered",
          trace_request_id: traceRequestId,
        });

        await startTraceLookup(traceRequestId, "trace_form_submit");
      });

      if (resultsFiltersToggleEl) {
        resultsFiltersToggleEl.addEventListener("click", () => {
          toggleResultsFiltersPanel();
        });
      }
      if (resultsFiltersPanelEl) {
        resultsFiltersPanelEl.addEventListener("keydown", handleResultsFiltersEscape);
      }
      if (typeof window !== "undefined") {
        window.addEventListener("resize", updateResultsFiltersViewportState);
        if (window.visualViewport) {
          window.visualViewport.addEventListener("resize", syncResultsFiltersKeyboardInset);
          window.visualViewport.addEventListener("scroll", syncResultsFiltersKeyboardInset);
        }
      }

      if (resultsSortEl) resultsSortEl.addEventListener("change", syncResultsListStateFromControls);
      if (resultsDirEl) resultsDirEl.addEventListener("change", syncResultsListStateFromControls);
      if (resultsKoEl) resultsKoEl.addEventListener("change", syncResultsListStateFromControls);

      if (resultsMinScoreEl) resultsMinScoreEl.addEventListener("change", syncResultsListStateFromControls);
      if (resultsMaxDistanceEl) resultsMaxDistanceEl.addEventListener("change", syncResultsListStateFromControls);
      if (resultsMinSecurityEl) resultsMinSecurityEl.addEventListener("change", syncResultsListStateFromControls);

      if (resultsApplyBtnEl) {
        resultsApplyBtnEl.addEventListener("click", () => {
          applyResultsFiltersFromControls("apply_button");
        });
      }
      if (resultsResetBtnEl) {
        resultsResetBtnEl.addEventListener("click", () => {
          resetResultsFiltersFromControls("reset_button");
        });
      }

      if (resultsClearBtnEl) {
        resultsClearBtnEl.addEventListener("click", () => {
          clearResultsEntries();
          emitUiEvent("ui.interaction.results_list.clear", {
            direction: "human->ui",
            status: "cleared",
          });
        });
      }


      const burgerBtn = document.getElementById("burger-btn");
      const burgerMenu = document.getElementById("burger-menu");
      const burgerBackdrop = document.getElementById("burger-backdrop");
      const burgerLoginLink = document.getElementById("burger-login-link");
      const burgerLogoutLink = document.getElementById("burger-logout-link");
      const burgerItems = burgerMenu
        ? Array.from(burgerMenu.querySelectorAll('a[href]'))
        : [];

      function setBurgerOpen(nextOpen) {
        if (!burgerBtn || !burgerMenu) return;
        burgerMenu.hidden = !nextOpen;
        burgerMenu.setAttribute("aria-hidden", nextOpen ? "false" : "true");
        burgerBtn.setAttribute("aria-expanded", nextOpen ? "true" : "false");
        if (burgerBackdrop) {
          burgerBackdrop.hidden = !nextOpen;
          burgerBackdrop.setAttribute("aria-hidden", nextOpen ? "false" : "true");
        }
        document.body.classList.toggle("burger-open", nextOpen);
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

        if (burgerBackdrop) {
          burgerBackdrop.addEventListener("click", () => {
            closeBurger({ returnFocus: true });
          });
        }

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

      if (sessionExpiryWarningLoginBtnEl) {
        sessionExpiryWarningLoginBtnEl.addEventListener("click", () => {
          persistAnalyzeDraft("session_expiry_warning_login_cta");
          const loginUrl = buildLoginRedirectUrl("session_expiring_soon");
          if (typeof window !== "undefined" && window.location) {
            window.location.assign(loginUrl);
          }
        });
      }

      updateAuthEntryPoints();
      restoreAnalyzeDraft();
      void refreshAuthSession({ force: false });
      scheduleAuthSessionPolling();

      emitUiEvent("ui.session.start", {
        direction: "internal",
        status: "ready",
        route: "/gui",
      });

      restoreResultsListDeepLinkInput();
      updateResultsFiltersViewportState();
      renderResultsList();

      initializeInteractiveMap();
      renderState();
      renderTraceState();
      loadHistory();

      const deepLinkTraceRequestId = restoreTraceDeepLinkInput();
      if (deepLinkTraceRequestId) {
        startTraceLookup(deepLinkTraceRequestId, "trace_deep_link");
      }
    </script>
  </body>
</html>
"""


def render_gui_mvp_html(
    *,
    app_version: str,
    auth_login_endpoint: str = "/auth/login",
    auth_logout_endpoint: str = "/auth/logout",
    auth_me_endpoint: str = "/auth/me",
) -> str:
    """Render das statische GUI-MVP-HTML mit sicher escaped Version."""

    safe_version = escape(app_version or "dev")
    safe_login_endpoint = escape(str(auth_login_endpoint or "/auth/login"), quote=True)
    safe_logout_endpoint = escape(str(auth_logout_endpoint or "/auth/logout"), quote=True)
    safe_me_endpoint = escape(str(auth_me_endpoint or "/auth/me"), quote=True)

    html = _GUI_MVP_HTML_TEMPLATE.replace("__APP_VERSION__", safe_version)
    html = html.replace("__AUTH_LOGIN_ENDPOINT__", safe_login_endpoint)
    html = html.replace("__AUTH_LOGOUT_ENDPOINT__", safe_logout_endpoint)
    html = html.replace("__AUTH_ME_ENDPOINT__", safe_me_endpoint)
    return html
