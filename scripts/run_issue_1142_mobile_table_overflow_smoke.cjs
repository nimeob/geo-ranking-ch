#!/usr/bin/env node

const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const { execFileSync, spawn } = require('node:child_process');

const issueNumber = 1142;
const scriptRelPath = 'scripts/run_issue_1142_mobile_table_overflow_smoke.cjs';
const DEFAULT_BASELINE_REF = 'HEAD~1';
const DEFAULT_REMOTE_TIMEOUT_MS = 10000;

function buildUsage() {
  return [
    `Usage: node ${scriptRelPath}`,
    '',
    'Issue #1142 Mobile Table Overflow Harness.',
    'Vergleicht CSS-basierte Tabellen-Overflow-Metriken zwischen Baseline und aktuellem Stand.',
    '',
    'Options:',
    '  -h, --help              Show this help and exit.',
    `  --baseline-ref <ref>   Override baseline git ref (default: ${DEFAULT_BASELINE_REF})`,
    '  --evidence-json <path> Override JSON evidence output path.',
    '  --json-out <path>      Alias für --evidence-json (legacy compatibility).',
    '  --base-url <url>       Optional deployed GUI URL (e.g. https://www.dev.georanking.ch/gui).',
    '  --headless             Accepted for compatibility (runner is always headless).',
    '',
    'Environment:',
    `  ISSUE_1142_BASELINE_REF=${DEFAULT_BASELINE_REF}   Optional baseline git ref for CSS comparison.`,
    '  ISSUE_1142_BASE_URL=<url>    Optional deployed GUI URL when --base-url is omitted.',
    `  ISSUE_1142_REMOTE_TIMEOUT_MS=${DEFAULT_REMOTE_TIMEOUT_MS}    Timeout for remote HTML fetch in ms.`,
  ].join('\n');
}

function parseCliArgs(argv) {
  const args = Array.isArray(argv) ? argv : [];
  const unknown = [];
  const options = {
    help: false,
    baselineRef: '',
    evidenceJson: '',
    baseUrl: '',
  };

  const consumeValue = (flag, inlineValue, currentArgs, index) => {
    const candidate = inlineValue !== null ? inlineValue : currentArgs[index + 1];
    const normalized = typeof candidate === 'string' ? candidate.trim() : '';
    if (!normalized || normalized.startsWith('-')) {
      throw new Error(`Missing value for ${flag}`);
    }
    return candidate;
  };

  for (let i = 0; i < args.length; i += 1) {
    const raw = String(args[i] || '').trim();
    if (!raw) continue;

    if (raw === '-h' || raw === '--help') {
      options.help = true;
      continue;
    }

    const eqIdx = raw.indexOf('=');
    const flag = eqIdx >= 0 ? raw.slice(0, eqIdx) : raw;
    const inlineValue = eqIdx >= 0 ? raw.slice(eqIdx + 1) : null;

    switch (flag) {
      case '--baseline-ref':
        options.baselineRef = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--evidence-json':
      case '--json-out':
        options.evidenceJson = consumeValue(flag, inlineValue, args, i);
        if (inlineValue === null) i += 1;
        break;
      case '--headless':
      case '--base-url':
        if (flag === '--base-url') {
          options.baseUrl = consumeValue(flag, inlineValue, args, i);
          if (inlineValue === null) i += 1;
        }
        break;
      default:
        unknown.push(raw);
        break;
    }
  }

  return { ...options, unknown };
}

const cli = (() => {
  try {
    return parseCliArgs(process.argv.slice(2));
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error || 'unknown error');
    console.error(`[issue-${issueNumber}-mobile-overflow-harness] ${message}`);
    console.error(buildUsage());
    process.exit(2);
  }
})();
if (cli.help) {
  console.log(buildUsage());
  process.exit(0);
}
if (cli.unknown.length > 0) {
  console.error(`[issue-${issueNumber}-mobile-overflow-harness] unknown_cli_args=${cli.unknown.join(',')}`);
  console.error(buildUsage());
  process.exit(2);
}

const repoRoot = path.resolve(__dirname, '..');
const outputJsonPath = (() => {
  const rawPath = String(cli.evidenceJson || '').trim();
  if (!rawPath) return '';
  if (path.isAbsolute(rawPath)) return path.normalize(rawPath);
  return path.resolve(repoRoot, rawPath);
})();
const outDir = outputJsonPath ? path.dirname(outputJsonPath) : path.join(repoRoot, 'reports', 'evidence');

function loadPlaywrightChromium() {
  for (const modName of ['playwright-core', 'playwright']) {
    try {
      // eslint-disable-next-line import/no-dynamic-require, global-require
      const mod = require(modName);
      if (mod && mod.chromium) return mod.chromium;
    } catch (_error) {
      // ignore
    }
  }
  throw new Error(
    'Weder "playwright-core" noch "playwright" verfügbar. Bitte z. B. `npm i -D playwright-core` ausführen.'
  );
}

function extractStyleBlock(html) {
  const match = html.match(/<style>([\s\S]*?)<\/style>/i);
  if (!match) throw new Error('Kein <style>-Block im GUI-HTML gefunden');
  return match[1];
}

function buildHarnessHtml(css, { withDataLabels }) {
  const maybe = (label) => (withDataLabels ? ` data-label="${label}"` : '');
  return `<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Issue 1142 Harness</title>
    <style>${css}</style>
  </head>
  <body>
    <main>
      <article class="card" id="results-list">
        <h2>Result-Liste</h2>
        <p class="meta">Neueste Analyze-Responses als Kurzliste.</p>
        <div id="results-table-shell" class="results-table-shell">
          <table class="results-table" aria-label="Ergebnisliste">
            <thead>
              <tr>
                <th>Zeit</th>
                <th>Input</th>
                <th>Score</th>
                <th>Dist (m)</th>
                <th>Sec</th>
                <th class="actions">Aktionen</th>
              </tr>
            </thead>
            <tbody id="results-body">
              <tr>
                <td${maybe('Zeit')}>04.03.2026, 08:33:00</td>
                <td${maybe('Input')}>Musterstrasse 123, 9000 St. Gallen, Schweiz</td>
                <td${maybe('Score')}>98</td>
                <td${maybe('Dist (m)')}>123</td>
                <td${maybe('Sec')}>88</td>
                <td class="actions"${maybe('Aktionen')}>
                  <div class="results-row-actions">
                    <button type="button" class="copy-btn">Anzeigen</button>
                    <a class="trace-link-btn" href="#trace">Trace</a>
                  </div>
                </td>
              </tr>
              <tr>
                <td${maybe('Zeit')}>04.03.2026, 08:31:00</td>
                <td${maybe('Input')}>Rosenbergstrasse 45, 9000 St. Gallen, Schweiz</td>
                <td${maybe('Score')}>91</td>
                <td${maybe('Dist (m)')}>442</td>
                <td${maybe('Sec')}>79</td>
                <td class="actions"${maybe('Aktionen')}>
                  <div class="results-row-actions">
                    <button type="button" class="copy-btn">Anzeigen</button>
                    <a class="trace-link-btn" href="#trace">Trace</a>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </main>
  </body>
</html>`;
}

function startStaticServer(directory, port) {
  const child = spawn('python3', ['-m', 'http.server', String(port), '--directory', directory], {
    stdio: 'ignore',
  });
  return child;
}

function renderGuiHtmlAtGitRef(repoRoot, gitRef, { quiet = false } = {}) {
  return execFileSync('python3', ['-c', [
    'import importlib.util, subprocess, tempfile, pathlib, sys',
    'ref=sys.argv[1]',
    'src=subprocess.check_output(["git","show",f"{ref}:src/shared/gui_mvp.py"], text=True)',
    'p=pathlib.Path(tempfile.gettempdir())/f"issue_1142_gui_mvp_{ref.replace("/", "_").replace("~", "_")}.py"',
    'p.write_text(src, encoding="utf-8")',
    'spec=importlib.util.spec_from_file_location("gui_mvp_ref", str(p))',
    'mod=importlib.util.module_from_spec(spec)',
    'spec.loader.exec_module(mod)',
    'print(mod.render_gui_mvp_html(app_version="dev"))',
  ].join(';'), gitRef], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
    stdio: quiet ? ['ignore', 'pipe', 'ignore'] : ['ignore', 'pipe', 'pipe'],
  });
}

function normalizeGuiBaseUrl(rawUrl) {
  const trimmed = String(rawUrl || '').trim();
  if (!trimmed) return '';

  let parsed;
  try {
    parsed = new URL(trimmed);
  } catch (error) {
    throw new Error(`Ungültige --base-url: ${trimmed}`);
  }

  if (!/^https?:$/.test(parsed.protocol)) {
    throw new Error(`--base-url muss http/https nutzen: ${trimmed}`);
  }

  const pathname = parsed.pathname || '/';
  if (pathname === '/') {
    parsed.pathname = '/gui';
  } else if (!pathname.startsWith('/gui')) {
    parsed.pathname = pathname.endsWith('/') ? `${pathname}gui` : `${pathname}/gui`;
  }

  return parsed.toString();
}

async function fetchGuiHtmlFromBaseUrl(rawUrl, timeoutMs) {
  const targetUrl = normalizeGuiBaseUrl(rawUrl);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(targetUrl, {
      method: 'GET',
      redirect: 'follow',
      signal: controller.signal,
      headers: {
        accept: 'text/html,application/xhtml+xml',
      },
    });

    if (!response.ok) {
      throw new Error(`Remote GUI HTML fetch fehlgeschlagen: status=${response.status}`);
    }

    const html = await response.text();
    if (!html || !/<style>[\s\S]*?<\/style>/i.test(html)) {
      throw new Error('Remote GUI HTML enthält keinen nutzbaren <style>-Block');
    }

    return {
      html,
      targetUrl,
      finalUrl: response.url || targetUrl,
    };
  } catch (error) {
    if (error && error.name === 'AbortError') {
      throw new Error(`Remote GUI HTML fetch timeout nach ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function main() {
  await fs.mkdir(outDir, { recursive: true });

  const currentHtmlLocal = execFileSync('python3', ['-c', 'from src.shared.gui_mvp import render_gui_mvp_html; print(render_gui_mvp_html(app_version="dev"))'], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  const remoteTimeoutMsRaw = Number(process.env.ISSUE_1142_REMOTE_TIMEOUT_MS);
  const remoteTimeoutMs = Number.isFinite(remoteTimeoutMsRaw) && remoteTimeoutMsRaw > 0
    ? Math.floor(remoteTimeoutMsRaw)
    : DEFAULT_REMOTE_TIMEOUT_MS;

  const targetUrlRequested = String(cli.baseUrl || process.env.ISSUE_1142_BASE_URL || '').trim();
  let targetUrlResolved = '';
  let targetUrlFinal = '';
  let currentHtmlSource = 'local_render';
  let currentHtmlFetchError = null;

  let currentHtml = currentHtmlLocal;
  if (targetUrlRequested) {
    try {
      const remote = await fetchGuiHtmlFromBaseUrl(targetUrlRequested, remoteTimeoutMs);
      currentHtml = remote.html;
      targetUrlResolved = remote.targetUrl;
      targetUrlFinal = remote.finalUrl;
      currentHtmlSource = 'remote_fetch';
    } catch (error) {
      currentHtmlFetchError = error instanceof Error ? error.message : String(error);
      currentHtmlSource = 'local_render_fallback';
    }
  }

  const baselineRefRequested = String(
    cli.baselineRef || process.env.ISSUE_1142_BASELINE_REF || DEFAULT_BASELINE_REF,
  ).trim() || DEFAULT_BASELINE_REF;
  let baselineRefResolved = baselineRefRequested;
  let baselineFallbackUsed = false;
  let baselineHtml;
  try {
    baselineHtml = renderGuiHtmlAtGitRef(repoRoot, baselineRefRequested, { quiet: true });
  } catch (_error) {
    baselineRefResolved = 'HEAD';
    baselineFallbackUsed = true;
    baselineHtml = renderGuiHtmlAtGitRef(repoRoot, baselineRefResolved);
  }

  const baselineCss = extractStyleBlock(baselineHtml);
  const currentCss = extractStyleBlock(currentHtml);

  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), 'issue-1142-'));
  const beforeFile = path.join(tmpDir, 'before.html');
  const afterFile = path.join(tmpDir, 'after.html');
  await fs.writeFile(beforeFile, buildHarnessHtml(baselineCss, { withDataLabels: false }), 'utf8');
  await fs.writeFile(afterFile, buildHarnessHtml(currentCss, { withDataLabels: true }), 'utf8');

  const port = 8994;
  const server = startStaticServer(tmpDir, port);

  const chromium = loadPlaywrightChromium();
  const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'de-CH' });

  const targets = [
    { key: 'before', file: 'before.html', screenshot: path.join(outDir, 'issue-1142-mobile-before.png') },
    { key: 'after', file: 'after.html', screenshot: path.join(outDir, 'issue-1142-mobile-after.png') },
  ];

  const metrics = {};
  try {
    for (const target of targets) {
      const page = await context.newPage();
      await page.goto(`http://127.0.0.1:${port}/${target.file}`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(250);

      metrics[target.key] = await page.evaluate(() => {
        const shell = document.getElementById('results-table-shell');
        const table = document.querySelector('.results-table');
        const doc = document.scrollingElement || document.documentElement;
        const viewportWidth = window.innerWidth;
        const actions = Array.from(document.querySelectorAll('.results-row-actions .copy-btn, .results-row-actions .trace-link-btn')).map((el) => {
          const rect = el.getBoundingClientRect();
          return {
            text: String(el.textContent || '').trim(),
            left: Number(rect.left.toFixed(2)),
            right: Number(rect.right.toFixed(2)),
            visible: rect.left >= 0 && rect.right <= viewportWidth,
          };
        });
        return {
          viewportWidth,
          mq390: window.matchMedia('(max-width: 390px)').matches,
          doc: { scrollWidth: doc.scrollWidth, clientWidth: doc.clientWidth },
          shell: {
            scrollWidth: shell ? shell.scrollWidth : null,
            clientWidth: shell ? shell.clientWidth : null,
          },
          table: {
            scrollWidth: table ? table.scrollWidth : null,
            clientWidth: table ? table.clientWidth : null,
          },
          allActionsVisible: actions.every((entry) => entry.visible),
          actions,
        };
      });

      await page.screenshot({ path: target.screenshot, fullPage: true });
      await page.close();
    }
  } finally {
    await browser.close();
    server.kill('SIGTERM');
  }

  const noHorizontalOverflow = (entry) => {
    if (!entry) return false;
    const scrollWidth = Number(entry.scrollWidth);
    const clientWidth = Number(entry.clientWidth);
    if (!Number.isFinite(scrollWidth) || !Number.isFinite(clientWidth)) {
      return false;
    }
    return scrollWidth <= clientWidth;
  };

  const assertions = {
    afterMq390Matches: Boolean(metrics.after?.mq390),
    afterDocNoOverflow: noHorizontalOverflow(metrics.after?.doc),
    afterShellNoOverflow: noHorizontalOverflow(metrics.after?.shell),
    afterTableNoOverflow: noHorizontalOverflow(metrics.after?.table),
    afterActionsVisible: Boolean(metrics.after?.allActionsVisible),
  };

  const payload = {
    targetUrlRequested,
    targetUrlResolved,
    targetUrlFinal,
    currentHtmlSource,
    currentHtmlFetchError,
    remoteTimeoutMs,
    baselineRefRequested,
    baselineRefResolved,
    baselineFallbackUsed,
    baselineEqualsCurrent: baselineCss === currentCss,
    before: metrics.before ?? null,
    after: metrics.after ?? null,
    assertions,
    ok: Object.values(assertions).every(Boolean),
  };

  const jsonPath = outputJsonPath || path.join(outDir, 'issue-1142-mobile-overflow-evidence.json');
  await fs.writeFile(jsonPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');

  console.log(jsonPath);
  if (!payload.ok) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
