/**
 * Automated screenshot capture for TrueSignal README.
 * Usage: node scripts/take-screenshots.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs   = require('fs');

const BASE    = 'https://truesignalapp.com';
const OUT_DIR = path.join(__dirname, '..', 'docs', 'screenshots');

fs.mkdirSync(OUT_DIR, { recursive: true });

async function shot(page, name) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  console.log(`  ✓  ${name}.png`);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx     = await browser.newContext({
    viewport: { width: 1400, height: 820 },
    deviceScaleFactor: 2,           // retina-quality
  });
  const page = await ctx.newPage();

  // ── 1. Landing page ─────────────────────────────────────────────────────────
  console.log('→ Landing page');
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await shot(page, 'landing');

  // ── 2. Click "Try the Demo" ─────────────────────────────────────────────────
  console.log('→ Logging in as demo (may take ~30s for Render cold start)…');
  await page.locator('button:has-text("Try the Demo")').first().click();
  await page.waitForURL('**/dashboard/**', { timeout: 90000 });
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1500);

  // ── 3. Overview dashboard ────────────────────────────────────────────────────
  console.log('→ Overview');
  await shot(page, 'overview');

  // ── 4. Asset Health ──────────────────────────────────────────────────────────
  console.log('→ Asset Health');
  await page.goto(`${BASE}/dashboard/assets`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await shot(page, 'asset-health');

  // ── 5. PM Planner ───────────────────────────────────────────────────────────
  console.log('→ PM Planner');
  await page.goto(`${BASE}/dashboard/pm-planner`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await shot(page, 'pm-planner');

  // ── 6. Settings (connected state) ───────────────────────────────────────────
  console.log('→ Settings');
  await page.goto(`${BASE}/dashboard/settings`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await shot(page, 'settings');

  await browser.close();
  console.log(`\nDone — screenshots saved to docs/screenshots/`);
})();
