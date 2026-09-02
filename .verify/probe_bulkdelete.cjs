const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const OUT = '/home/rosemary/workspace/ImageForge/.verify';
(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(10000);
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1200);
  await page.click('a[href="/artists"]');
  await page.waitForTimeout(1200);
  // select first artist row
  await page.evaluate(() => { const el = document.querySelector('.artist-check input[type=checkbox]'); if (el) el.click(); });
  await page.waitForTimeout(400);
  // click 删除所选
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('.v-btn')].find(x => (x.innerText || '').includes('删除所选'));
    if (b) b.click();
  });
  await page.waitForTimeout(500);
  const dlg = await page.evaluate(() => {
    const ov = document.querySelector('.v-overlay--active');
    const text = ov ? (ov.innerText || '').replace(/\s+/g, ' ').trim() : '';
    return {
      open: !!ov,
      hasConfirmBtn: text.includes('删除'),
      hasCancelBtn: text.includes('取消'),
      text: text.slice(0, 120),
    };
  });
  console.log('[bulk delete dialog]', JSON.stringify(dlg));
  await page.screenshot({ path: `${OUT}/cb_21_bulkdelete_dialog.png` });
  console.log('saved cb_21_bulkdelete_dialog');
  // cancel
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('.v-overlay--active .v-btn')].find(x => (x.innerText || '').includes('取消'));
    if (b) b.click();
  });
  await page.waitForTimeout(400);
  const closed = await page.evaluate(() => !document.querySelector('.v-overlay--active'));
  console.log('[dialog closed after cancel]', closed);
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });