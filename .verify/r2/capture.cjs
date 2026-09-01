// Capture source-manager + scan-preview dialogs for review
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';
const OUT = '/home/rosemary/workspace/ImageForge/.verify/r2';
const FIXTURE = '/home/rosemary/workspace/ImageForge/.verify/testsrc';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BASE + 'loras', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // add a source if not present
  const srcs = await page.evaluate(async () => {
    const r = await fetch('/api/loras/sources');
    return r.json();
  });
  if (!srcs.some(s => s.display_path === FIXTURE)) {
    await page.evaluate(async (p) => {
      await fetch('/api/loras/sources', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ display_path: p, recursive: true }) });
    }, FIXTURE);
    await page.waitForTimeout(400);
  }

  await page.click('button:has-text("扫描来源")');
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/06_source_dialog.png` });

  // run scan and capture preview
  await page.click('.source-row .op-btn[title="扫描"]');
  await page.waitForTimeout(900);
  await page.screenshot({ path: `${OUT}/07_scan_preview.png` });

  // select first two new + show
  await page.click('button:has-text("取消全选")');
  const checks = await page.$$('.cand-row:not(.disabled) .row-check');
  if (checks.length >= 2) { await checks[0].click(); await checks[1].click(); }
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/08_scan_selected.png` });
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);

  // search filter demo
  await page.fill('.search-input', 'bar_boost');
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/09_library_search.png` });
  await page.fill('.search-input', '');
  await page.waitForTimeout(300);
  await page.close();
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
