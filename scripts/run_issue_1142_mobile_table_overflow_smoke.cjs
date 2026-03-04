#!/usr/bin/env node

const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const { execFileSync, spawn } = require('node:child_process');

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

async function main() {
  const repoRoot = process.cwd();
  const outDir = path.join(repoRoot, 'reports', 'evidence');
  await fs.mkdir(outDir, { recursive: true });

  const currentHtml = execFileSync('python3', ['-c', 'from src.shared.gui_mvp import render_gui_mvp_html; print(render_gui_mvp_html(app_version="dev"))'], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

  const baselineHtml = execFileSync('python3', ['-c', [
    'import importlib.util, re, subprocess, tempfile, pathlib',
    'src=subprocess.check_output(["git","show","HEAD:src/shared/gui_mvp.py"], text=True)',
    'p=pathlib.Path(tempfile.gettempdir())/"issue_1142_gui_mvp_before.py"',
    'p.write_text(src, encoding="utf-8")',
    'spec=importlib.util.spec_from_file_location("gui_mvp_before", str(p))',
    'mod=importlib.util.module_from_spec(spec)',
    'spec.loader.exec_module(mod)',
    'print(mod.render_gui_mvp_html(app_version="dev"))',
  ].join(';')], {
    cwd: repoRoot,
    encoding: 'utf8',
    maxBuffer: 20 * 1024 * 1024,
  });

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

  await browser.close();
  server.kill('SIGTERM');

  const jsonPath = path.join(outDir, 'issue-1142-mobile-overflow-evidence.json');
  await fs.writeFile(jsonPath, `${JSON.stringify(metrics, null, 2)}\n`, 'utf8');

  console.log(jsonPath);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
