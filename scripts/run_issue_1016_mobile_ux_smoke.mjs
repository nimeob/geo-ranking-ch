#!/usr/bin/env node
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const issueNumber = 1016;
const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const guiStabilityWaitMs = Number.parseInt(process.env.GUI_STABILITY_WAIT_MS || '1200', 10);
const baseUrlProbeTimeoutMs = Number.parseInt(process.env.BASE_URL_PROBE_TIMEOUT_MS || '5000', 10);
const repoRoot = process.cwd();
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

class BaseUrlReachabilityError extends Error {
  constructor(message, { targetUrl, reasonCode, hint, cause } = {}) {
    super(message, cause ? { cause } : undefined);
    this.name = 'BaseUrlReachabilityError';
    this.targetUrl = targetUrl || '';
    this.reasonCode = reasonCode || 'unreachable';
    this.hint = hint || '';
  }
}

function compactMessage(message, maxLength = 320) {
  const normalized = String(message || '').replace(/\s+/g, ' ').trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength)}…`;
}

function normalizeError(error) {
  const hint = typeof error?.hint === 'string' ? error.hint : '';
  const reasonCode = typeof error?.reasonCode === 'string' ? error.reasonCode : '';
  const targetUrl = typeof error?.targetUrl === 'string' ? error.targetUrl : '';

  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack || '',
      ...(hint ? { hint } : {}),
      ...(reasonCode ? { reasonCode } : {}),
      ...(targetUrl ? { targetUrl } : {}),
    };
  }

  return {
    name: 'Error',
    message: String(error || 'unknown error'),
    stack: '',
    ...(hint ? { hint } : {}),
    ...(reasonCode ? { reasonCode } : {}),
    ...(targetUrl ? { targetUrl } : {}),
  };
}

function isLocalHost(hostname) {
  const host = String(hostname || '').trim().toLowerCase();
  return host === '127.0.0.1' || host === 'localhost' || host === '::1';
}

function classifyConnectivityReason(error) {
  const message = String(error?.message || '');
  const causeCode = String(error?.cause?.code || '');
  const causeName = String(error?.cause?.name || '');
  const raw = `${message} ${causeCode} ${causeName}`.toLowerCase();

  if (raw.includes('econnrefused') || raw.includes('err_connection_refused')) return 'connection_refused';
  if (raw.includes('enotfound') || raw.includes('name_not_resolved') || raw.includes('err_name_not_resolved')) {
    return 'dns_not_found';
  }
  if (raw.includes('etimedout') || raw.includes('aborted') || raw.includes('timeout')) return 'timeout';
  if (raw.includes('econnreset') || raw.includes('err_connection_reset')) return 'connection_reset';
  return 'unreachable';
}

function buildBaseUrlReachabilityHint(targetUrl, reasonCode) {
  let parsed;
  try {
    parsed = new URL(targetUrl);
  } catch {
    return 'BASE_URL ist ungültig. Bitte vollständige URL inkl. Schema prüfen (z. B. http://127.0.0.1:8877/gui oder https://www.dev.georanking.ch/gui).';
  }

  if (isLocalHost(parsed.hostname)) {
    return [
      `Lokalen GUI-Server starten (Default): HOST=127.0.0.1 PORT=${parsed.port || '8877'} APP_VERSION=dev python3 -m src.web_service`,
      `Danach Smoke erneut ausführen: BASE_URL=\"${targetUrl}\" node scripts/run_issue_1016_mobile_ux_smoke.mjs`,
      `reason=${reasonCode}`,
    ].join(' | ');
  }

  return [
    `Ziel-URL nicht erreichbar: ${targetUrl}`,
    'Prüfe DNS/TLS/Ingress und ob /gui ohne Auth-Block erreichbar ist.',
    `reason=${reasonCode}`,
  ].join(' | ');
}

async function assertBaseUrlReachable(targetUrl, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), Math.max(200, timeoutMs));

  try {
    const response = await fetch(targetUrl, {
      method: 'GET',
      redirect: 'manual',
      signal: controller.signal,
      headers: { Accept: 'text/html,*/*;q=0.8' },
    });

    return {
      ok: true,
      status: response.status,
      finalUrl: String(response.url || targetUrl),
    };
  } catch (error) {
    const reasonCode = classifyConnectivityReason(error);
    const hint = buildBaseUrlReachabilityHint(targetUrl, reasonCode);
    throw new BaseUrlReachabilityError(
      `BASE_URL nicht erreichbar (${reasonCode}): ${targetUrl}. reason=${compactMessage(error?.message || error, 240)}. hint=${hint}`,
      { targetUrl, reasonCode, hint, cause: error }
    );
  } finally {
    clearTimeout(timer);
  }
}

function isAuthRedirectUrl(url) {
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase();
    const pathname = parsed.pathname.toLowerCase();
    const hasOauthLoginQuery = parsed.searchParams.has('response_type') && parsed.searchParams.has('client_id');
    if (hostname.startsWith('auth.')) return true;
    if (pathname === '/login' && hasOauthLoginQuery) return true;
    return false;
  } catch {
    return false;
  }
}

async function waitForGuiOrAuthRedirect(page, { stageLabel, selector, timeoutMs }) {
  const currentUrl = page.url();
  if (isAuthRedirectUrl(currentUrl)) {
    throw new Error(
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${currentUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  const guiWait = page
    .locator(selector)
    .waitFor({ state: 'visible', timeout: timeoutMs })
    .then(() => ({ kind: 'gui-ready' }))
    .catch((error) => ({ kind: 'gui-timeout', error }));

  const authWait = page
    .waitForURL((url) => isAuthRedirectUrl(String(url)), { timeout: timeoutMs })
    .then(() => ({ kind: 'auth-redirect' }))
    .catch(() => ({ kind: 'auth-timeout' }));

  const winner = await Promise.race([guiWait, authWait]);

  if (winner.kind === 'auth-redirect') {
    const authUrl = page.url();
    throw new Error(
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${authUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  if (winner.kind === 'gui-ready') {
    return;
  }

  const finalUrl = page.url();
  if (isAuthRedirectUrl(finalUrl)) {
    throw new Error(
      `[${stageLabel}] Unerwarteter Redirect auf Auth-Login erkannt: ${finalUrl} (target=${baseUrl}, waitMs=${guiStabilityWaitMs}).`
    );
  }

  if (winner.kind === 'gui-timeout') {
    const reason = winner.error instanceof Error ? winner.error.message : String(winner.error || 'timeout');
    throw new Error(
      `[${stageLabel}] GUI-Shell nicht bereit: ${selector} nach ${timeoutMs}ms nicht sichtbar (url=${finalUrl}). reason=${reason}`
    );
  }

  throw new Error(`[${stageLabel}] GUI-Shell nicht bereit: ${selector} nach ${timeoutMs}ms nicht sichtbar (url=${finalUrl}).`);
}

async function openStableGuiPage(context) {
  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(Math.max(0, guiStabilityWaitMs));

  await waitForGuiOrAuthRedirect(page, {
    stageLabel: 'mobile-ux',
    selector: '#analyze-form',
    timeoutMs: 20_000,
  });

  return page;
}

async function readMetaZoom(page) {
  const text = (await page.locator('#map-view-meta').textContent()) || '';
  const match = /Zoom\s+(\d+)/i.exec(text);
  return {
    text: text.trim(),
    zoom: match ? Number(match[1]) : null,
  };
}

async function runBurgerSmoke(page) {
  const burgerBtn = page.locator('#burger-btn');
  const burgerMenu = page.locator('#burger-menu');
  const burgerBackdrop = page.locator('#burger-backdrop');

  await burgerBtn.click();
  await page.waitForTimeout(120);

  const openState = await page.evaluate(() => ({
    expanded: document.getElementById('burger-btn')?.getAttribute('aria-expanded') || null,
    menuHidden: document.getElementById('burger-menu')?.hasAttribute('hidden') ?? true,
    menuAriaHidden: document.getElementById('burger-menu')?.getAttribute('aria-hidden') || null,
    backdropHidden: document.getElementById('burger-backdrop')?.hasAttribute('hidden') ?? true,
    bodyBurgerOpen: document.body.classList.contains('burger-open'),
  }));

  await burgerBackdrop.click({ position: { x: 2, y: 2 } });
  await page.waitForTimeout(120);

  const closeState = await page.evaluate(() => ({
    expanded: document.getElementById('burger-btn')?.getAttribute('aria-expanded') || null,
    menuHidden: document.getElementById('burger-menu')?.hasAttribute('hidden') ?? false,
    menuAriaHidden: document.getElementById('burger-menu')?.getAttribute('aria-hidden') || null,
    backdropHidden: document.getElementById('burger-backdrop')?.hasAttribute('hidden') ?? false,
    bodyBurgerOpen: document.body.classList.contains('burger-open'),
    activeElementId: document.activeElement?.id || '',
  }));

  const passed =
    openState.expanded === 'true' &&
    openState.menuHidden === false &&
    openState.menuAriaHidden === 'false' &&
    openState.backdropHidden === false &&
    openState.bodyBurgerOpen === true &&
    closeState.expanded === 'false' &&
    closeState.menuHidden === true &&
    closeState.menuAriaHidden === 'true' &&
    closeState.backdropHidden === true &&
    closeState.bodyBurgerOpen === false;

  return {
    openState,
    closeState,
    passed,
  };
}

async function runPinchSmoke(page) {
  const before = await readMetaZoom(page);

  const pinchResult = await page.evaluate(async () => {
    const surface = document.getElementById('map-click-surface');
    if (!surface) throw new Error('map-click-surface not found');

    const longTasks = [];
    let observer = null;
    if (typeof PerformanceObserver !== 'undefined') {
      observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          longTasks.push(Number(entry.duration || 0));
        }
      });
      try {
        observer.observe({ entryTypes: ['longtask'] });
      } catch {
        observer = null;
      }
    }

    const rect = surface.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;

    const fire = (type, id, x, y) => {
      const ev = new PointerEvent(type, {
        pointerId: id,
        pointerType: 'touch',
        isPrimary: id === 1,
        clientX: x,
        clientY: y,
        bubbles: true,
        cancelable: true,
      });
      surface.dispatchEvent(ev);
    };

    const rafDeltas = [];
    let previous = performance.now();
    for (let i = 0; i < 10; i += 1) {
      await new Promise((resolve) => requestAnimationFrame(resolve));
      const now = performance.now();
      rafDeltas.push(now - previous);
      previous = now;
    }

    fire('pointerdown', 1, cx - 28, cy);
    fire('pointerdown', 2, cx + 28, cy);

    for (let step = 0; step < 9; step += 1) {
      const offset = 28 + step * 9;
      fire('pointermove', 1, cx - offset, cy - 4);
      fire('pointermove', 2, cx + offset, cy + 4);
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }

    fire('pointerup', 1, cx - 118, cy - 6);
    fire('pointerup', 2, cx + 118, cy + 6);

    await new Promise((resolve) => setTimeout(resolve, 220));

    observer?.disconnect();

    const maxRafDelta = rafDeltas.length ? Math.max(...rafDeltas) : null;
    const maxLongTaskMs = longTasks.length ? Math.max(...longTasks) : 0;

    return {
      maxRafDelta,
      longTaskCount: longTasks.length,
      maxLongTaskMs,
    };
  });

  const after = await readMetaZoom(page);
  const passed =
    Number.isFinite(before.zoom) &&
    Number.isFinite(after.zoom) &&
    after.zoom > before.zoom &&
    Number.isFinite(pinchResult.maxLongTaskMs) &&
    pinchResult.maxLongTaskMs <= 50;

  return {
    before,
    after,
    perf: pinchResult,
    passed,
  };
}

async function main() {
  const startedAtUtc = new Date().toISOString();
  let browser = null;
  let context = null;
  let screenshotPath = '';
  let burger = null;
  let pinch = null;
  let runError = null;

  try {
    await assertBaseUrlReachable(baseUrl, baseUrlProbeTimeoutMs);

    browser = await chromium.launch({ headless: true });
    context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      userAgent:
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
      isMobile: true,
      hasTouch: true,
      locale: 'de-CH',
    });

    const page = await openStableGuiPage(context);

    burger = await runBurgerSmoke(page);
    pinch = await runPinchSmoke(page);

    await fs.mkdir(outDir, { recursive: true });
    screenshotPath = path.join(outDir, `issue-${issueNumber}-mobile-ux-${stamp}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
  } catch (error) {
    runError = normalizeError(error);
  } finally {
    if (context) {
      await context.close();
    }
    if (browser) {
      await browser.close();
    }
  }

  const checks =
    runError === null
      ? {
          burgerMenuUx: burger,
          pinchZoomSmoothness: pinch,
        }
      : {
          bootstrap: {
            stage: 'openStableGuiPage',
            error: runError.message,
            passed: false,
          },
        };

  const ok = runError === null && burger?.passed === true && pinch?.passed === true;
  const finishedAtUtc = new Date().toISOString();

  const payload = {
    issue: issueNumber,
    startedAtUtc,
    finishedAtUtc,
    targetUrl: baseUrl,
    baseUrlProbeTimeoutMs,
    checks,
    artifacts: screenshotPath
      ? {
          screenshot: path.relative(repoRoot, screenshotPath),
        }
      : {},
    runError,
    ok,
  };

  const outJson = path.join(outDir, `issue-${issueNumber}-mobile-ux-smoke-${stamp}.json`);
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!ok) process.exit(1);
}

main().catch(async (error) => {
  const finishedAtUtc = new Date().toISOString();
  const payload = {
    issue: issueNumber,
    startedAtUtc: finishedAtUtc,
    finishedAtUtc,
    targetUrl: baseUrl,
    baseUrlProbeTimeoutMs,
    checks: {},
    artifacts: {},
    runError: normalizeError(error),
    ok: false,
  };

  await fs.mkdir(outDir, { recursive: true });
  const outJson = path.join(outDir, `issue-${issueNumber}-mobile-ux-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');
  console.log(path.relative(repoRoot, outJson));
  process.exit(1);
});
