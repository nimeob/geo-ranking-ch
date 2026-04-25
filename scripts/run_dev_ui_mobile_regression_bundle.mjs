#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const SCRIPT_DIR = path.dirname(SCRIPT_PATH);
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..");

function parseCli(argv) {
  const options = {
    baseUrl: "",
    outputJson: "",
    failFast: false,
    helpRequested: false,
  };

  const consumeValue = (flag, inlineValue, args, index) => {
    const candidate = inlineValue !== null ? inlineValue : args[index + 1];
    const value = String(candidate || "").trim();
    if (!value || value.startsWith("-")) {
      throw new Error(`Missing value for ${flag}`);
    }
    return value;
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
      case "--output-json":
      case "--json-out":
      case "--out":
        options.outputJson = consumeValue(flag, inlineValue, argv, i);
        if (inlineValue === null) i += 1;
        break;
      case "--fail-fast":
        options.failFast = true;
        break;
      default:
        throw new Error(`Unknown option: ${flag}`);
    }
  }

  return options;
}

function printHelp() {
  process.stdout.write(
    [
      "Usage: node scripts/run_dev_ui_mobile_regression_bundle.mjs [options]",
      "",
      "Runs the full mobile-focused GUI regression bundle on /gui against a live dev URL:",
      "- issue 981 (mobile interaction + geolocation)",
      "- issue 986 (webkit/mobile fallback smoke)",
      "- issue 1016 (burger + pinch smoothness)",
      "- issue 1039 (mobile overflow + core selectors)",
      "- issue 1142 (mobile table overflow)",
      "",
      "Options:",
      "  --base-url <url>      target URL (env fallback: DEV_UI_BASE_URL, BASE_URL)",
      "  --output-json <path>  write consolidated report JSON (default in reports/evidence)",
      "  --json-out <path>     alias for --output-json",
      "  --out <path>          alias for --output-json",
      "  --fail-fast           stop after first failing/errored sub-smoke",
      "  -h, --help            show this help",
      "",
      "Output:",
      "  Prints the consolidated JSON report path to stdout.",
    ].join("\n") + "\n"
  );
}

function isoStamp() {
  return new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

function resolveOutputPath(rawPath) {
  const value = String(rawPath || "").trim();
  if (!value) {
    return path.join(REPO_ROOT, "reports", "evidence", `dev-ui-mobile-regression-bundle-${isoStamp()}.json`);
  }
  if (path.isAbsolute(value)) return path.normalize(value);
  return path.resolve(REPO_ROOT, value);
}

function normalizePathMaybe(candidate) {
  const value = String(candidate || "").trim();
  if (!value) return "";
  if (path.isAbsolute(value)) return value;
  return path.resolve(REPO_ROOT, value);
}

function extractReportPath(output) {
  const lines = String(output || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const maybe = normalizePathMaybe(lines[i]);
    if (maybe && fs.existsSync(maybe) && maybe.endsWith(".json")) {
      return maybe;
    }
  }
  return "";
}

function loadJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

function resolveBaseUrl(cliBaseUrl) {
  const raw = String(cliBaseUrl || process.env.DEV_UI_BASE_URL || process.env.BASE_URL || "https://www.dev.georanking.ch").trim();
  return raw || "https://www.dev.georanking.ch";
}

function runOneCheck({ label, command, baseUrl }) {
  const env = {
    ...process.env,
    BASE_URL: baseUrl,
  };

  const completed = spawnSync(command[0], command.slice(1), {
    cwd: REPO_ROOT,
    env,
    encoding: "utf8",
    stdio: "pipe",
  });

  const stdout = String(completed.stdout || "");
  const stderr = String(completed.stderr || "");
  const reportPath = extractReportPath(`${stdout}\n${stderr}`);
  const report = reportPath ? loadJsonSafe(reportPath) : null;
  const ok = Boolean(report && report.ok === true && completed.status === 0);

  return {
    label,
    command,
    exitCode: completed.status,
    signal: completed.signal || null,
    ok,
    reportPath: reportPath || null,
    report,
    stderrTail: stderr.trim().split(/\r?\n/).slice(-30),
    stdoutTail: stdout.trim().split(/\r?\n/).slice(-30),
  };
}

let cli = null;
try {
  cli = parseCli(process.argv.slice(2));
} catch (error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  console.error(`[dev-ui-mobile-regression-bundle] ERROR ${message}`);
  printHelp();
  process.exit(2);
}

if (cli.helpRequested) {
  printHelp();
  process.exit(0);
}

const startedAtUtc = new Date().toISOString();
const baseUrl = resolveBaseUrl(cli.baseUrl);
const checks = [
  {
    label: "issue-981-mobile-smoke",
    command: ["node", "scripts/run_issue_981_mobile_smoke.mjs"],
  },
  {
    label: "issue-986-webkit-smoke",
    command: ["node", "scripts/run_issue_986_webkit_smoke.mjs"],
  },
  {
    label: "issue-1016-mobile-ux-smoke",
    command: ["node", "scripts/run_issue_1016_mobile_ux_smoke.mjs"],
  },
  {
    label: "issue-1039-mobile-overflow-smoke",
    command: ["node", "scripts/run_issue_1039_mobile_overflow_smoke.cjs"],
  },
  {
    label: "issue-1142-mobile-table-overflow-smoke",
    command: ["node", "scripts/run_issue_1142_mobile_table_overflow_smoke.cjs"],
  },
];

const results = [];
for (const check of checks) {
  const result = runOneCheck({ ...check, baseUrl });
  results.push(result);
  const failed = !result.ok;
  if (failed && cli.failFast) {
    break;
  }
}

const finishedAtUtc = new Date().toISOString();
const allPassed = results.length === checks.length && results.every((item) => item.ok);
const report = {
  schemaVersion: "dev-ui-mobile-regression-bundle/v1",
  startedAtUtc,
  finishedAtUtc,
  targetUrl: baseUrl,
  totalChecksPlanned: checks.length,
  totalChecksRun: results.length,
  allPassed,
  checks: results.map((item) => {
    const webkitRuntime = item.label === "issue-986-webkit-smoke" ? item.report?.runtime : null;
    return {
      label: item.label,
      command: item.command.join(" "),
      exitCode: item.exitCode,
      signal: item.signal,
      ok: item.ok,
      reportPath: item.reportPath,
      reportOk: item.report && Object.prototype.hasOwnProperty.call(item.report, "ok") ? Boolean(item.report.ok) : null,
      limitations: Array.isArray(item.report?.limitations) ? item.report.limitations : [],
      webkitNativeActive: webkitRuntime && Object.prototype.hasOwnProperty.call(webkitRuntime, "nativeWebkitActive")
        ? Boolean(webkitRuntime.nativeWebkitActive)
        : null,
      webkitMissingLibrariesCount: Array.isArray(webkitRuntime?.webkitMissingLibraries)
        ? webkitRuntime.webkitMissingLibraries.length
        : null,
      stdoutTail: item.stdoutTail,
      stderrTail: item.stderrTail,
    };
  }),
};

const outputPath = resolveOutputPath(cli.outputJson);
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
process.stdout.write(`${path.relative(REPO_ROOT, outputPath)}\n`);

if (!allPassed) {
  process.exit(1);
}
