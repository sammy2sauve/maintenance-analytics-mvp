/**
 * Automated screenshot capture for TrueSignal README.
 * Walks the full demo flow: landing → connect gate → settings connect → dashboard.
 * Usage: node scripts/take-screenshots.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs   = require('fs');

const BASE = 'https://truesignalapp.com';
const API  = 'https://maintenance-analytics-mvp.onrender.com';
const OUT_DIR  = path.join(__dirname, '..', 'docs', 'screenshots');
const MOCK_URL = `${API}/mock-fw`;
const MOCK_KEY = 'demo-key';

fs.mkdirSync(OUT_DIR, { recursive: true });

async function shot(page, name) {
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  console.log(`  ✓  ${name}.png`);
}

// Injects the JWT into localStorage so page reloads don't lose auth
async function injectToken(page, token) {
  await page.evaluate(t => localStorage.setItem('ts_token', t), token);
}

// Navigate and wait for the nav bar to confirm auth succeeded
async function gotoProtected(page, url, token) {
  await injectToken(page, token);
  await page.goto(url, { waitUntil: 'load' });
  await injectToken(page, token); // re-inject after load in case storage was reset
  // Wait for the nav to appear — confirms ProtectedRoute passed
  await page.locator('nav').waitFor({ timeout: 15000 });
  await page.waitForTimeout(1500);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx     = await browser.newContext({
    viewport: { width: 1400, height: 820 },
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();

  // ── 1. Landing ───────────────────────────────────────────────────────────────
  console.log('→ Landing page');
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await shot(page, 'landing');

  // ── 2. Get demo token via Node fetch (bypasses Render cold-start timing issues)
  console.log('→ Getting demo token (may take ~30s for Render cold start)…');
  let tokenData;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const r = await fetch(`${API}/auth/demo`, { method: 'POST' });
      tokenData = await r.json();
      break;
    } catch (e) {
      if (attempt === 2) throw e;
      console.log(`  … retry ${attempt + 1}`);
      await new Promise(r => setTimeout(r, 10000));
    }
  }
  const token = tokenData.token;
  console.log(`  ✓  Token: ${token.slice(0, 20)}…`);

  // Inject token and navigate to dashboard
  await page.evaluate(t => localStorage.setItem('ts_token', t), token);
  await page.goto(`${BASE}/dashboard/`, { waitUntil: 'load' });
  await page.evaluate(t => localStorage.setItem('ts_token', t), token);
  await page.locator('nav').waitFor({ timeout: 15000 });
  await page.waitForTimeout(1200);

  // ── 3. Connect gate (overview, FaciliWorks not yet connected) ────────────────
  console.log('→ Connect gate');
  await shot(page, 'connect-gate');

  // ── 4. Settings — FaciliWorks connect form ───────────────────────────────────
  console.log('→ Settings — connect form');
  await gotoProtected(page, `${BASE}/dashboard/settings`, token);
  await shot(page, 'connect');

  // ── 5. Fill credentials ───────────────────────────────────────────────────────
  console.log('→ Filling mock credentials…');
  await page.locator('input[placeholder*="faciliworks"]').fill(MOCK_URL);
  await page.locator('input[type="password"]').fill(MOCK_KEY);
  await shot(page, 'connect-filled');

  // ── 6. Connect + sync ─────────────────────────────────────────────────────────
  console.log('→ Connecting (sync may take ~60s)…');
  await page.locator('button:has-text("Connect FaciliWorks")').last().click();

  try {
    await page.waitForSelector('text=Syncing data', { timeout: 10000 });
    console.log('  … syncing');
    await shot(page, 'sync');
  } catch { }

  try {
    await page.waitForSelector('text=Connected', { timeout: 120000 });
    console.log('  ✓  Connected');
  } catch {
    console.warn('  ⚠  Timed out — continuing anyway');
  }
  await page.waitForTimeout(1500);

  // Re-read token after sync (it shouldn't have changed but just in case)
  token = await page.evaluate(() => localStorage.getItem('ts_token')) || token;

  // ── 7. Overview ───────────────────────────────────────────────────────────────
  console.log('→ Overview');
  await gotoProtected(page, `${BASE}/dashboard/`, token);
  await shot(page, 'overview');

  // ── 8. Asset Health ───────────────────────────────────────────────────────────
  console.log('→ Asset Health');
  await page.locator('nav a, nav button').filter({ hasText: /Asset Health/i }).first().click();
  await page.waitForTimeout(2000);
  await shot(page, 'asset-health');

  // ── 9. PM Planner ─────────────────────────────────────────────────────────────
  console.log('→ PM Planner');
  await page.waitForTimeout(3000); // let Render settle after asset-health requests
  await page.locator('nav a, nav button').filter({ hasText: /PM Planner/i }).first().click();
  await page.waitForTimeout(3000);
  // If network error appears, click Retry and wait
  const retry = page.locator('button:has-text("Retry")');
  if (await retry.count() > 0) {
    console.log('  … network error, retrying');
    await retry.click();
    await page.waitForTimeout(5000);
  }
  await shot(page, 'pm-planner');

  await browser.close();
  console.log(`\nDone — screenshots saved to docs/screenshots/`);
})();
