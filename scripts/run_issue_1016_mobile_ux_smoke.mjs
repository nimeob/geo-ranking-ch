#!/usr/bin/env node
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const issueNumber = 1016;
const baseUrl = process.env.BASE_URL || 'http://127.0.0.1:8877/gui';
const repoRoot = process.cwd();
const outDir = path.join(repoRoot, 'reports', 'evidence');
const stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');

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
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    userAgent:
      'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    isMobile: true,
    hasTouch: true,
    locale: 'de-CH',
  });

  const page = await context.newPage();
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded' });

  const burger = await runBurgerSmoke(page);
  const pinch = await runPinchSmoke(page);

  await fs.mkdir(outDir, { recursive: true });
  const screenshotPath = path.join(outDir, `issue-${issueNumber}-mobile-ux-${stamp}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  await context.close();
  await browser.close();

  const payload = {
    issue: issueNumber,
    targetUrl: baseUrl,
    checks: {
      burgerMenuUx: burger,
      pinchZoomSmoothness: pinch,
    },
    artifacts: {
      screenshot: path.relative(repoRoot, screenshotPath),
    },
    ok: burger.passed && pinch.passed,
  };

  const outJson = path.join(outDir, `issue-${issueNumber}-mobile-ux-smoke-${stamp}.json`);
  await fs.writeFile(outJson, JSON.stringify(payload, null, 2) + '\n', 'utf8');

  console.log(path.relative(repoRoot, outJson));
  if (!payload.ok) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
