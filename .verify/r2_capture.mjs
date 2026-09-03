// R2 Character Library QA — 真实 DB 数据（Dense List 定稿）
import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';

const outDir = '/home/rosemary/workspace/ImageForge/.verify/r2';
fs.mkdirSync(outDir, { recursive: true });

const EXE = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';

async function newPage(browser, w, h) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on('console', m => { if (m.type() === 'error') console.log('  [console.error]', m.text().slice(0, 200)); });
  page.on('pageerror', e => console.log('  [pageerror]', String(e).slice(0, 300)));
  return page;
}

async function run() {
  const browser = await chromium.launch({ executablePath: EXE, args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'] });

  // ───── 1440×900 ─────
  let page = await newPage(browser, 1440, 900);

  console.log('1. 已解析角色默认 (1440)');
  await page.goto('http://localhost:5173/characters', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(outDir, '01_1440_list_default.png') });

  console.log('2. 搜索结果');
  await page.fill('.cl-search input', '秧秧');
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(outDir, '02_1440_search.png') });
  await page.fill('.cl-search input', '');
  await page.waitForTimeout(400);

  console.log('3. 多选状态 (前 3 行)');
  const boxes = page.locator('.cl-list .cl-row m3e-checkbox');
  const n = await boxes.count();
  for (let i = 0; i < Math.min(3, n); i++) await boxes.nth(i).click();
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(outDir, '03_1440_multiselect.png') });
  // 取消选择，复原
  for (let i = 0; i < Math.min(3, n); i++) await boxes.nth(i).click();
  await page.waitForTimeout(300);

  console.log('4. 联网刷新 loading（点击后立即截）');
  await page.locator('.cl-list .cl-row').first().locator('m3e-icon-button').nth(1).click();
  await page.waitForTimeout(350);
  await page.screenshot({ path: path.join(outDir, '04_1440_refresh_loading.png') });
  await page.waitForTimeout(4000);

  console.log('5. Edit dialog');
  await page.locator('.cl-list .cl-row').first().locator('m3e-icon-button').first().click();
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(outDir, '05_1440_edit_dialog.png') });
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);

  console.log('6. 自定义角色 tab');
  await page.locator('m3e-tab').nth(1).click();
  await page.waitForTimeout(700);
  await page.screenshot({ path: path.join(outDir, '06_1440_custom_tab.png') });

  // ───── 1920×1080 ─────
  page = await newPage(browser, 1920, 1080);

  console.log('7. 默认列表 (1920)');
  await page.goto('http://localhost:5173/characters', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(outDir, '07_1920_list_default.png') });

  console.log('8. Studio 对照 (1920)');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(outDir, '08_1920_studio_ref.png') });

  await browser.close();
  console.log('DONE →', outDir);
}

run().catch(e => { console.error(e); process.exit(1); });
