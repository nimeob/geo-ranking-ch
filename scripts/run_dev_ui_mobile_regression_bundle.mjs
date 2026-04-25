#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const SCRIPT_DIR = path.dirname(SCRIPT_PATH);
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..");

const DEFAULT_BASE_URL = "https://www.dev.georanking.ch/gui";
const DEFAULT_EVIDENCE_DIR = path.join(REPO_ROOT, "artifacts", "dev-ui-mobile", "latest");
const DEFAULT_EVIDENCE_JSON = path.join(DEFAULT_EVIDENCE_DIR, "dev-ui-mobile-regression.json");

const SUITE = [
  {
    id: "issue-1016-mobile-ux",
    issue: 1016,
    script: path.join("scripts", "run_issue_1016_mobile_ux_smoke.mjs"),
    description: "Burger-Menü UX + Pinch-Zoom smoothness",
  },
  {
    id: "issue-981-mobile-e2e",
    issue: 981,
    script: path.join("scripts", "run_issue_981_mobile_smoke.mjs"),
    description: "Mobile map interactions + geolocation fallback",
  },
  {
    id: "issue-1039-mobile-overflow",
    issue: 1039,
    script: path.join("scripts", "run_issue_1039_mobile_overflow_smoke.cjs"),
    description: "Horizontal overflow + core selector reachability",
  },
  {
    id: "issue-986-webkit",
    issue: 986,
    script: path.join("scripts", "run_issue_986_webkit_smoke.mjs"),
    description: "WebKit smoke (with Chromium fallback if native WebKit unavailable)",
  },
];

function printHelp(stream = process.stdout) {
  const lines = [
    "Usage: node scripts/run_dev_ui_mobile_regression_bundle.mjs [options]",
    "",
    "Runs the DEV live mobile-focused GUI smoke bundle and writes a consolidated JSON summary.",
    "",
    "Options:",
    "  --base-url <url>       Target GUI URL (default: https://www.dev.georanking.ch/gui)",
    "  --evidence-json <path> Consolidated bundle output JSON path",
    "  --json-out <path>      Alias for --evidence-json",
    "  --out <path>           Alias for --evidence-json",
    "  --evidence-dir <path>  Directory for per-step JSON outputs",
    "  --screenshot-dir <path>Directory where discovered screenshots are copied",
    "  --headless             Forward compatibility flag to child runners",
    "  --skip-webkit          Skip issue #986 WebKit smoke step",
    "  --dry-run              Do not execute child scripts; emit plan JSON only",
    "  -h, --help             Show this help and exit",
    "",
    "Environment:",
    "  DEV_UI_MOBILE_BASE_URL",
    "  DEV_UI_MOBILE_EVIDENCE_JSON",
    "  DEV_UI_MOBILE_EVIDENCE_DIR",
    "  DEV_UI_MOBILE_SCREENSHOT_DIR",
    "  DEV_UI_BASE_URL (fallback for --base-url)",
    "  BASE_URL (fallback for --base-url)",
  ];
  stream.write(`${lines.join("\n")}\n`);
}

function consumeValue(flag, inlineValue, args, index) {
  const candidate = inlineValue !== null ? inlineValue : args[index + 1];
  const normalized = typeof candidate === "string" ? candidate.trim() : "";
  if (!normalized || normalized.startsWith("-")) {
    throw new Error(`Missing value for ${flag}`);
  }
  return candidate;
}

function parseCliArgs(argv) {
  const options = {
    baseUrl: "",
    evidenceJson: "",
    evidenceDir: "",
    screenshotDir: "",
    headless: false,
    skipWebkit: false,
    dryRun: false,
    helpRequested: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const raw = String(argv[i] || "").trim();
    if (!raw) continue;

    if (raw === "-h" || raw === "--help") {
      options.helpRequested = true;
      continue;
    }

    const eqIdx = raw.indexOf("=");
    const flag = eqIdx >= 0 ? raw.slice(0, eqIdx) : raw;
    const inlineValue = eqIdx >= 0 ? raw.slice(eqIdx + 1) : null;

    switch (flag) {
      case "--base-url":
        options.baseUrl = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--evidence-json":
      case "--json-out":
      case "--out":
        options.evidenceJson = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--evidence-dir":
        options.evidenceDir = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--screenshot-dir":
        options.screenshotDir = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--headless":
        options.headless = true;
        break;
      case "--skip-webkit":
        options.skipWebkit = true;
        break;
      case "--dry-run":
        options.dryRun = true;
        break;
      default:
        throw new Error(`Unknown option: ${flag}`);
    }
  }

  return options;
}

function resolvePathAgainstRepoRoot(rawPath) {
  const value = String(rawPath || "").trim();
  if (!value) return "";
  if (path.isAbsolute(value)) {
    return path.normalize(value);
  }
  return path.resolve(REPO_ROOT, value);
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function toRepoRelative(absOrRelativePath) {
  const raw = String(absOrRelativePath || "").trim();
  if (!raw) return "";
  const abs = path.isAbsolute(raw) ? raw : path.resolve(REPO_ROOT, raw);
  return path.relative(REPO_ROOT, abs);
}

function readJsonIfExists(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function collectScreenshotCandidates(payload) {
  const seen = new Set();

  function visit(value, parentKey = "") {
    if (typeof value === "string") {
      const key = String(parentKey || "").toLowerCase();
      if (key.includes("screenshot")) {
        const trimmed = value.trim();
        if (trimmed) seen.add(trimmed);
      }
      return;
    }

    if (!value || typeof value !== "object") return;

    if (Array.isArray(value)) {
      for (const item of value) {
        visit(item, parentKey);
      }
      return;
    }

    for (const [k, v] of Object.entries(value)) {
      visit(v, k);
    }
  }

  visit(payload);
  return Array.from(seen);
}

function uniqueDestPath(destPath) {
  if (!fs.existsSync(destPath)) return destPath;

  const ext = path.extname(destPath);
  const stem = destPath.slice(0, destPath.length - ext.length);
  for (let i = 1; i < 1000; i += 1) {
    const candidate = `${stem}-${i}${ext}`;
    if (!fs.existsSync(candidate)) return candidate;
  }
  return `${stem}-${Date.now()}${ext}`;
}

function copyScreenshots(stepPayload, screenshotDir) {
  const copied = [];
  const candidates = collectScreenshotCandidates(stepPayload);

  for (const rawCandidate of candidates) {
    const sourceAbs = path.isAbsolute(rawCandidate)
      ? rawCandidate
      : path.resolve(REPO_ROOT, rawCandidate);

    if (!fs.existsSync(sourceAbs)) continue;

    const sourceStat = fs.statSync(sourceAbs);
    if (!sourceStat.isFile()) continue;

    const desiredDest = path.join(screenshotDir, path.basename(sourceAbs));
    const destAbs = uniqueDestPath(desiredDest);
    fs.copyFileSync(sourceAbs, destAbs);

    copied.push({
      source: path.relative(REPO_ROOT, sourceAbs),
      copiedTo: path.relative(REPO_ROOT, destAbs),
    });
  }

  return copied;
}

function runStep({ step, baseUrl, headless, evidenceDir, screenshotDir }) {
  const startedAt = new Date();
  const outputJsonPath = path.join(evidenceDir, `${step.id}.json`);
  const stepArgs = [
    step.script,
    "--base-url",
    baseUrl,
    "--evidence-json",
    outputJsonPath,
  ];
  if (headless) {
    stepArgs.push("--headless");
  }

  const stepEnv = { ...process.env };
  if (step.issue === 1039) {
    stepEnv.ISSUE_1039_EVIDENCE_DIR = screenshotDir;
  }

  const spawnResult = spawnSync("node", stepArgs, {
    cwd: REPO_ROOT,
    stdio: "inherit",
    env: stepEnv,
  });

  const finishedAt = new Date();
  const payload = readJsonIfExists(outputJsonPath);
  const copiedScreenshots = payload ? copyScreenshots(payload, screenshotDir) : [];
  const exitCode = Number.isInteger(spawnResult.status) ? spawnResult.status : (spawnResult.error ? 1 : 0);

  return {
    id: step.id,
    issue: step.issue,
    description: step.description,
    script: step.script,
    command: ["node", ...stepArgs].join(" "),
    startedAtUtc: startedAt.toISOString(),
    finishedAtUtc: finishedAt.toISOString(),
    durationMs: finishedAt.getTime() - startedAt.getTime(),
    outputJson: toRepoRelative(outputJsonPath),
    exitCode,
    ok: exitCode === 0 && Boolean(payload?.ok),
    payloadOk: payload?.ok === true,
    payloadPresent: Boolean(payload),
    payloadSummary: payload
      ? {
          targetUrl: payload.targetUrl || null,
          targetUrlRequested: payload.targetUrlRequested || null,
          baseUrlCanonicalized: payload.baseUrlCanonicalized ?? null,
          baseUrlCanonicalizationReasons: payload.baseUrlCanonicalizationReasons || null,
          limitations: Array.isArray(payload.limitations) ? payload.limitations : [],
          runError: payload.runError || null,
        }
      : null,
    copiedScreenshots,
    error: spawnResult.error ? String(spawnResult.error.message || spawnResult.error) : null,
  };
}

let cliOptions;
try {
  cliOptions = parseCliArgs(process.argv.slice(2));
} catch (error) {
  console.error(`[dev-ui-mobile-regression] ERROR ${error instanceof Error ? error.message : String(error)}`);
  printHelp(process.stderr);
  process.exit(2);
}

if (cliOptions.helpRequested) {
  printHelp();
  process.exit(0);
}

const requestedBaseUrl = String(
  cliOptions.baseUrl
    || process.env.DEV_UI_MOBILE_BASE_URL
    || process.env.DEV_UI_BASE_URL
    || process.env.BASE_URL
    || DEFAULT_BASE_URL,
).trim();
const baseUrl = requestedBaseUrl || DEFAULT_BASE_URL;

const explicitEvidenceJson = resolvePathAgainstRepoRoot(
  cliOptions.evidenceJson || process.env.DEV_UI_MOBILE_EVIDENCE_JSON || "",
);
const explicitEvidenceDir = resolvePathAgainstRepoRoot(
  cliOptions.evidenceDir || process.env.DEV_UI_MOBILE_EVIDENCE_DIR || "",
);

const evidenceJsonPath = explicitEvidenceJson || (explicitEvidenceDir
  ? path.join(explicitEvidenceDir, path.basename(DEFAULT_EVIDENCE_JSON))
  : DEFAULT_EVIDENCE_JSON);
const evidenceDir = explicitEvidenceDir || path.dirname(evidenceJsonPath);
const screenshotDir = resolvePathAgainstRepoRoot(
  cliOptions.screenshotDir || process.env.DEV_UI_MOBILE_SCREENSHOT_DIR || path.join(evidenceDir, "screenshots"),
);

ensureDir(evidenceDir);
ensureDir(screenshotDir);

const selectedSuite = cliOptions.skipWebkit
  ? SUITE.filter((step) => step.issue !== 986)
  : SUITE;

const startedAt = new Date();
const summary = {
  startedAtUtc: startedAt.toISOString(),
  finishedAtUtc: null,
  bundle: "dev-ui-live-mobile-regression",
  dryRun: Boolean(cliOptions.dryRun),
  target: {
    baseUrl,
    requestedBaseUrl,
  },
  config: {
    evidenceJson: toRepoRelative(evidenceJsonPath),
    evidenceDir: toRepoRelative(evidenceDir),
    screenshotDir: toRepoRelative(screenshotDir),
    headless: Boolean(cliOptions.headless),
    skipWebkit: Boolean(cliOptions.skipWebkit),
  },
  suite: [],
  totals: {
    totalSteps: selectedSuite.length,
    okSteps: 0,
    failedSteps: 0,
    copiedScreenshotCount: 0,
  },
  ok: false,
};

if (cliOptions.dryRun) {
  summary.suite = selectedSuite.map((step) => {
    const outputJsonPath = path.join(evidenceDir, `${step.id}.json`);
    const command = [
      "node",
      step.script,
      "--base-url",
      baseUrl,
      "--evidence-json",
      outputJsonPath,
      ...(cliOptions.headless ? ["--headless"] : []),
    ];
    return {
      id: step.id,
      issue: step.issue,
      description: step.description,
      script: step.script,
      outputJson: toRepoRelative(outputJsonPath),
      command: command.join(" "),
      skipped: true,
    };
  });
  summary.ok = true;
} else {
  for (const step of selectedSuite) {
    const stepResult = runStep({
      step,
      baseUrl,
      headless: cliOptions.headless,
      evidenceDir,
      screenshotDir,
    });
    summary.suite.push(stepResult);
  }

  summary.totals.okSteps = summary.suite.filter((item) => item.ok).length;
  summary.totals.failedSteps = summary.suite.filter((item) => !item.ok).length;
  summary.totals.copiedScreenshotCount = summary.suite.reduce(
    (acc, item) => acc + (Array.isArray(item.copiedScreenshots) ? item.copiedScreenshots.length : 0),
    0,
  );
  summary.ok = summary.totals.failedSteps === 0;
}

summary.finishedAtUtc = new Date().toISOString();
fs.writeFileSync(evidenceJsonPath, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
process.stdout.write(`${toRepoRelative(evidenceJsonPath)}\n`);

process.exit(summary.ok ? 0 : 1);
