// R2.1 Character Library QA — resolved/custom × 1440/1920
import { chromium } from 'playwright-core';
import fs from 'fs';
const outDir = '/home/rosemary/workspace/ImageForge/.verify/r2.1';
fs.mkdirSync(outDir, { recursive: true });
const EXE = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const browser = await chromium.launch({ executablePath: EXE, args: ['--no-sandbox', '--disable-gpu'] });

for (const [w, h, tag] of [[1440, 900, '1440'], [1920, 1080, '1920']]) {
  const page = await (await browser.newContext({ viewport: { width: w, height: h } })).newPage();
  page.on('pageerror', e => console.log('[pageerror]', String(e).slice(0, 200)));
  await page.goto('http://localhost:5173/characters', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${outDir}/${tag}_resolved.png` });
  const ov1 = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  await page.locator('m3e-tab').nth(1).click();
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${outDir}/${tag}_custom.png` });
  const ov2 = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  console.log(`${tag}: resolved overflow=${ov1} custom overflow=${ov2}`);
  await page.close();
}
await browser.close();
console.log('DONE');
