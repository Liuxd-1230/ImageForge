const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(10000);
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1000);
  await page.click('a[href="/artists"]');
  await page.waitForTimeout(1200);
  await page.getByRole('button', { name: '添加画师' }).first().click();
  await page.waitForTimeout(700);
  const r = await page.evaluate(() => {
    const ov = document.querySelector('.v-overlay--active');
    const card = ov ? ov.querySelector('.v-card') : null;
    const btns = ov ? [...ov.querySelectorAll('.v-btn:not(.v-btn--icon)')].map(b => ({
      text: (b.innerText || '').trim(), radius: getComputedStyle(b).borderRadius,
    })) : [];
    return {
      overlayCls: ov ? ov.className.toString().slice(0, 60) : null,
      dialogCardRadius: card ? getComputedStyle(card).borderRadius : null,
      btns,
    };
  });
  console.log('[dialog card+btns]', JSON.stringify(r, null, 1));
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });