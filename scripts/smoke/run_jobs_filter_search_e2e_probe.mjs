#!/usr/bin/env node

function fail(message) {
  throw new Error(message);
}

function parseArgs(argv) {
  const args = { jobsUrl: "" };
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === "--jobs-url") {
      args.jobsUrl = String(argv[i + 1] || "").trim();
      i += 1;
      continue;
    }
  }
  if (!args.jobsUrl) {
    fail("missing --jobs-url");
  }
  return args;
}

async function fetchJobsPageScript(jobsUrl) {
  const response = await fetch(jobsUrl);
  if (!response.ok) {
    fail(`GET ${jobsUrl} failed with HTTP ${response.status}`);
  }
  const html = await response.text();
  const match = html.match(/<script>([\s\S]*?)<\/script>/i);
  if (!match || !match[1]) {
    fail("/jobs page did not contain inline script block");
  }
  return match[1];
}

class ElementStub {
  constructor(tagName, id = "") {
    this.tagName = String(tagName || "div").toUpperCase();
    this.id = id;
    this.value = "";
    this.href = "";
    this.type = "";
    this.className = "";
    this.colSpan = 1;
    this.listeners = new Map();
    this._children = [];
    this._textContent = "";
  }

  appendChild(child) {
    this._children.push(child);
    return child;
  }

  addEventListener(type, callback) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type).push(callback);
  }

  dispatch(type) {
    for (const callback of this.listeners.get(type) || []) {
      callback({ target: this });
    }
  }

  get children() {
    return this._children;
  }

  get textContent() {
    return this._textContent;
  }

  set textContent(value) {
    this._textContent = String(value ?? "");
    if (this._textContent === "") {
      this._children = [];
    }
  }
}

function decodeJobIdFromUrl(rawUrl) {
  const parsed = new URL(rawUrl, "http://127.0.0.1");
  const parts = parsed.pathname.split("/").filter(Boolean);
  const last = parts.at(-1) || "";
  return decodeURIComponent(last);
}

async function runScenario({ scriptSource, startUrl, storedIds, jobsById, actions }) {
  const requiredIds = [
    "jobs-status",
    "jobs-q",
    "jobs-add-id",
    "jobs-add-btn",
    "jobs-refresh",
    "jobs-clear",
    "api-token",
    "org-id",
    "jobs-meta",
    "jobs-body",
  ];

  const byId = new Map(requiredIds.map((id) => [id, new ElementStub("div", id)]));
  const statusEl = byId.get("jobs-status");
  const queryEl = byId.get("jobs-q");
  statusEl.value = "all";
  queryEl.value = "";

  const localStorageData = new Map();
  localStorageData.set("geo-ranking-ui-job-ids", JSON.stringify(storedIds));

  const fetchCalls = [];
  let currentUrl = String(startUrl);

  const windowStub = {
    location: {
      get href() {
        return currentUrl;
      },
      set href(value) {
        currentUrl = String(value || currentUrl);
      },
    },
    history: {
      replaceState: (_state, _title, nextUrl) => {
        currentUrl = String(nextUrl);
      },
    },
    localStorage: {
      getItem: (key) => (localStorageData.has(key) ? localStorageData.get(key) : null),
      setItem: (key, value) => {
        localStorageData.set(String(key), String(value));
      },
    },
  };

  const documentStub = {
    getElementById: (id) => {
      if (!byId.has(id)) {
        byId.set(id, new ElementStub("div", id));
      }
      return byId.get(id);
    },
    createElement: (tag) => new ElementStub(tag),
  };

  const fetchStub = async (url) => {
    fetchCalls.push(String(url));
    const jobId = decodeJobIdFromUrl(url);
    const job = jobsById[jobId];
    if (!job) {
      return {
        ok: false,
        status: 404,
        json: async () => ({ ok: false, error: "not_found" }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ ok: true, job }),
    };
  };

  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  const previousFetch = globalThis.fetch;

  globalThis.window = windowStub;
  globalThis.document = documentStub;
  globalThis.fetch = fetchStub;

  try {
    const runner = new Function(scriptSource);
    runner();

    const flush = async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
      await new Promise((resolve) => setTimeout(resolve, 0));
    };

    await flush();

    for (const action of actions) {
      if (action.type === "setStatus") {
        statusEl.value = action.value;
        statusEl.dispatch("change");
        await flush();
        continue;
      }
      if (action.type === "setQuery") {
        queryEl.value = action.value;
        queryEl.dispatch("input");
        await flush();
        continue;
      }
      fail(`unknown action type: ${action.type}`);
    }

    const bodyRows = byId.get("jobs-body").children || [];
    const rows = bodyRows
      .map((tr) => {
        const cells = tr.children || [];
        const jobCode = cells[0]?.children?.[0]?.textContent || "";
        const statusText = cells[1]?.textContent || "";
        return {
          jobId: String(jobCode || ""),
          status: String(statusText || ""),
        };
      })
      .filter((row) => row.jobId);

    return {
      currentUrl,
      statusValue: String(statusEl.value || ""),
      queryValue: String(queryEl.value || ""),
      rows,
      fetchCalls,
    };
  } finally {
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
    globalThis.fetch = previousFetch;
  }
}

function assert(condition, message) {
  if (!condition) {
    fail(message);
  }
}

function queryParam(url, key) {
  return new URL(url).searchParams.get(key);
}

async function main() {
  const { jobsUrl } = parseArgs(process.argv);
  const scriptSource = await fetchJobsPageScript(jobsUrl);

  const jobsById = {
    "job-running-1": {
      status: "running",
      progress_percent: 30,
      updated_at: "2026-03-05T02:00:00Z",
      result_id: "",
    },
    "job-failed-1": {
      status: "failed",
      progress_percent: 100,
      updated_at: "2026-03-05T02:01:00Z",
      result_id: "",
    },
    "job-succeeded-1": {
      status: "completed",
      progress_percent: 100,
      updated_at: "2026-03-05T02:02:00Z",
      result_id: "result-123",
    },
  };

  const storedIds = Object.keys(jobsById);

  const scenarioA = await runScenario({
    scriptSource,
    startUrl: `${jobsUrl}?status=completed&q=job-succeeded`,
    storedIds,
    jobsById,
    actions: [],
  });

  assert(scenarioA.statusValue === "succeeded", "legacy status=completed must normalize to succeeded");
  assert(scenarioA.queryValue === "job-succeeded", "legacy q parameter must hydrate query input");
  assert(scenarioA.rows.length === 1, "legacy share-link scenario must render exactly one filtered row");
  assert(scenarioA.rows[0].jobId === "job-succeeded-1", "legacy share-link must keep succeeded job visible");
  assert(scenarioA.rows[0].status === "succeeded", "completed status must be canonicalized to succeeded in table");
  assert(queryParam(scenarioA.currentUrl, "jobs_status") === "succeeded", "URL sync must write jobs_status");
  assert(queryParam(scenarioA.currentUrl, "jobs_q") === "job-succeeded", "URL sync must write jobs_q");

  const scenarioB = await runScenario({
    scriptSource,
    startUrl: jobsUrl,
    storedIds,
    jobsById,
    actions: [
      { type: "setStatus", value: "running" },
      { type: "setStatus", value: "failed" },
      { type: "setStatus", value: "succeeded" },
      { type: "setQuery", value: "job-succeeded" },
    ],
  });

  assert(
    scenarioB.fetchCalls.length >= storedIds.length * 2,
    "status interactions should trigger deterministic refreshes against stored job ids",
  );
  assert(scenarioB.rows.length === 1, "status+query filter must converge to one row");
  assert(scenarioB.rows[0].jobId === "job-succeeded-1", "status+query filter must keep expected job id");
  assert(queryParam(scenarioB.currentUrl, "jobs_status") === "succeeded", "final URL must persist selected status");
  assert(queryParam(scenarioB.currentUrl, "jobs_q") === "job-succeeded", "final URL must persist search query");

  const scenarioC = await runScenario({
    scriptSource,
    startUrl: scenarioB.currentUrl,
    storedIds,
    jobsById,
    actions: [],
  });

  assert(scenarioC.statusValue === "succeeded", "reloaded URL must restore status filter");
  assert(scenarioC.queryValue === "job-succeeded", "reloaded URL must restore search query");
  assert(scenarioC.rows.length === 1, "reloaded URL must render stable filtered result");
  assert(scenarioC.rows[0].jobId === "job-succeeded-1", "reloaded URL must keep same matching job");

  process.stdout.write(
    `${JSON.stringify({
      ok: true,
      scenarios: {
        legacyShareLink: scenarioA,
        interactiveFilterFlow: scenarioB,
        reloadFromShareLink: scenarioC,
      },
    })}\n`,
  );
}

main().catch((error) => {
  process.stderr.write(`[jobs-filter-search-e2e-probe] ${error?.stack || error}\n`);
  process.exit(1);
});
