#!/usr/bin/env node

class CliUsageError extends Error {
  constructor(message) {
    super(message);
    this.name = 'CliUsageError';
  }
}

function fail(message) {
  throw new Error(message);
}

function usageError(message) {
  throw new CliUsageError(message);
}

function printUsage(stream) {
  stream.write(
    [
      'Usage: node scripts/smoke/run_result_tabs_keyboard_probe.mjs --result-url <url>',
      '',
      'Options:',
      '  --result-url <url>  Public /results/<id> URL that should be probed.',
      '  -h, --help          Show this help and exit.',
    ].join('\n') + '\n'
  );
}

function parseArgs(argv) {
  const args = { mode: 'run', resultUrl: '' };

  const consumeValue = (flag, index) => {
    const next = String(argv[index + 1] || '').trim();
    if (!next || next.startsWith('-')) {
      usageError(`missing value for ${flag}`);
    }
    return next;
  };

  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '-h' || token === '--help') {
      args.mode = 'help';
      return args;
    }
    if (token === "--result-url") {
      args.resultUrl = consumeValue('--result-url', i);
      i += 1;
      continue;
    }
    usageError(`unknown option: ${token}`);
  }
  if (!args.resultUrl) {
    usageError('missing --result-url');
  }
  return args;
}

async function fetchResultPageScript(resultUrl) {
  const response = await fetch(resultUrl);
  if (!response.ok) {
    fail(`GET ${resultUrl} failed with HTTP ${response.status}`);
  }
  const html = await response.text();
  const match = html.match(/<script>([\s\S]*?)<\/script>/i);
  if (!match || !match[1]) {
    fail("/results page did not contain inline script block");
  }
  return match[1];
}

class ElementStub {
  constructor(tagName, id = "") {
    this.tagName = String(tagName || "div").toUpperCase();
    this.id = id;
    this.hidden = false;
    this.disabled = false;
    this.value = "";
    this.href = "";
    this.textContent = "";
    this.innerHTML = "";
    this.attributes = new Map();
    this.listeners = new Map();
    this.dataset = {};
  }

  setAttribute(name, value) {
    const key = String(name || "");
    const normalized = String(value ?? "");
    this.attributes.set(key, normalized);
    if (key === "data-tab") {
      this.dataset.tab = normalized;
    }
  }

  getAttribute(name) {
    const key = String(name || "");
    if (!this.attributes.has(key)) {
      return null;
    }
    return this.attributes.get(key);
  }

  addEventListener(type, callback) {
    const key = String(type || "");
    if (!this.listeners.has(key)) {
      this.listeners.set(key, []);
    }
    this.listeners.get(key).push(callback);
  }

  querySelectorAll(_selector) {
    return [];
  }

  contains(node) {
    return node === this;
  }

  dispatch(type, payload = {}) {
    const callbacks = this.listeners.get(String(type || "")) || [];
    for (const callback of callbacks) {
      const event = {
        key: payload.key,
        target: this,
        currentTarget: this,
        defaultPrevented: false,
        preventDefault() {
          this.defaultPrevented = true;
        },
      };
      callback(event);
    }
  }

  focus() {
    return undefined;
  }
}

function createDomHarness() {
  const requiredIds = [
    "view-mode",
    "status",
    "load-btn",
    "payload",
    "error",
    "raw-link",
    "panel-overview",
    "panel-location",
    "panel-demographics",
    "panel-safety",
    "panel-housing",
    "panel-education",
    "panel-transport",
    "panel-environment",
    "panel-sources",
    "panel-derived",
    "tab-overview",
    "tab-location",
    "tab-demographics",
    "tab-safety",
    "tab-housing",
    "tab-education",
    "tab-transport",
    "tab-environment",
    "tab-sources",
    "tab-derived",
    "tab-raw",
    "tab-btn-overview",
    "tab-btn-location",
    "tab-btn-demographics",
    "tab-btn-safety",
    "tab-btn-housing",
    "tab-btn-education",
    "tab-btn-transport",
    "tab-btn-environment",
    "tab-btn-sources",
    "tab-btn-derived",
    "tab-btn-raw",
    "burger-btn",
    "burger-menu",
  ];

  const byId = new Map(requiredIds.map((id) => [id, new ElementStub("div", id)]));

  const viewModeEl = byId.get("view-mode");
  viewModeEl.value = "latest";

  const tabKeys = [
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

  for (const key of tabKeys) {
    const btn = byId.get(`tab-btn-${key}`);
    btn.setAttribute("data-tab", key);
    btn.setAttribute("aria-selected", key === "overview" ? "true" : "false");

    const panel = byId.get(`tab-${key}`);
    panel.hidden = key !== "overview";
  }

  const documentStub = {
    getElementById(id) {
      if (!byId.has(id)) {
        byId.set(id, new ElementStub("div", id));
      }
      return byId.get(id);
    },
    querySelectorAll(selector) {
      if (selector === ".tab-btn") {
        return tabKeys.map((key) => byId.get(`tab-btn-${key}`));
      }
      return [];
    },
    addEventListener() {
      return undefined;
    },
  };

  return { byId, documentStub, tabKeys };
}

function createFetchStub() {
  const groupedPayload = {
    status: {
      quality: {
        confidence: { score: 87, max: 100, level: "high" },
        executive_summary: { verdict: "ok" },
      },
      source_meta: {
        source_attribution: {
          ids: ["geoadmin_gwr"],
        },
      },
      source_health: {
        geoadmin_gwr: { status: "ok", records: 1, optional: false },
      },
    },
    data: {
      entity: {
        query: "Neugasse 1, 9000 St. Gallen",
        matched_address: "Neugasse 1, 9000 St. Gallen",
        coordinates: { lat: 47.42, lon: 9.37 },
        administrative: { gemeinde: "St. Gallen", kanton: "SG" },
        ids: { egid: 1234 },
      },
      modules: {
        match: { selected_score: 0.92, candidate_count: 2 },
        summary_compact: { confidence: { score: 87, max: 100, level: "high" } },
        suitability_light: { status: "ok", score: 0.73, traffic_light: "green" },
        intelligence: {
          executive_risk_summary: { risk_score: 21, traffic_light: "green", status: "ok" },
        },
      },
      by_source: {
        geoadmin_gwr: {
          data: {
            ids: { egid: 1234 },
          },
        },
      },
    },
  };

  return async () => ({
    ok: true,
    status: 200,
    json: async () => ({ ok: true, result: groupedPayload }),
  });
}

function assert(condition, message) {
  if (!condition) {
    fail(message);
  }
}

function panelState(byId, key) {
  return {
    key,
    hidden: Boolean(byId.get(`tab-${key}`).hidden),
    selected: String(byId.get(`tab-btn-${key}`).getAttribute("aria-selected") || ""),
  };
}

async function flush() {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

async function main() {
  const parsed = parseArgs(process.argv);
  if (parsed.mode === 'help') {
    printUsage(process.stdout);
    return;
  }

  const { resultUrl } = parsed;
  const scriptSource = await fetchResultPageScript(resultUrl);

  const { byId, documentStub } = createDomHarness();

  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  const previousFetch = globalThis.fetch;
  const previousNode = globalThis.Node;

  const windowStub = {
    location: {
      pathname: "/results/res-123",
      search: "",
      href: resultUrl,
      assign(next) {
        this.href = String(next || this.href);
      },
    },
    setTimeout,
    addEventListener() {
      return undefined;
    },
  };

  globalThis.window = windowStub;
  globalThis.document = documentStub;
  globalThis.fetch = createFetchStub();
  globalThis.Node = ElementStub;

  try {
    const runner = new Function(scriptSource);
    runner();

    await flush();

    const states = {};
    states.initial = panelState(byId, "overview");

    const overviewBtn = byId.get("tab-btn-overview");
    overviewBtn.dispatch("keydown", { key: "ArrowRight" });
    await flush();
    states.afterArrowRight = panelState(byId, "location");

    const locationBtn = byId.get("tab-btn-location");
    locationBtn.dispatch("keydown", { key: "End" });
    await flush();
    states.afterEnd = panelState(byId, "raw");

    const rawBtn = byId.get("tab-btn-raw");
    rawBtn.dispatch("keydown", { key: "Home" });
    await flush();
    states.afterHome = panelState(byId, "overview");

    const derivedBtn = byId.get("tab-btn-derived");
    derivedBtn.dispatch("click", {});
    await flush();
    states.afterClickDerived = panelState(byId, "derived");

    const statusText = String(byId.get("status").textContent || "");
    assert(statusText.includes("success"), "loadResult should reach success state");

    assert(states.initial.hidden === false && states.initial.selected === "true", "overview should start active");
    assert(states.afterArrowRight.hidden === false && states.afterArrowRight.selected === "true", "ArrowRight should activate location");
    assert(states.afterEnd.hidden === false && states.afterEnd.selected === "true", "End should activate raw");
    assert(states.afterHome.hidden === false && states.afterHome.selected === "true", "Home should activate overview");
    assert(states.afterClickDerived.hidden === false && states.afterClickDerived.selected === "true", "click should activate derived");

    process.stdout.write(`${JSON.stringify({ ok: true, states, statusText })}\n`);
  } finally {
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
    globalThis.fetch = previousFetch;
    globalThis.Node = previousNode;
  }
}

main().catch((error) => {
  if (error instanceof CliUsageError) {
    process.stderr.write(`[result-tabs-keyboard-probe] ERROR: ${error.message}\n`);
    printUsage(process.stderr);
    process.exit(2);
  }
  process.stderr.write(`[result-tabs-keyboard-probe] ${error?.stack || error}\n`);
  process.exit(1);
});
