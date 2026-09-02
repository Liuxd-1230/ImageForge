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
  const btns = await page.evaluate(() => [...document.querySelectorAll('button')].map((b, i) => ({
    i,
    text: (b.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 30),
    cls: (b.className || '').toString().slice(0, 40),
    visible: !!(b.offsetWidth || b.offsetHeight),
  })));
  console.log(JSON.stringify(btns, null, 1));
  // try getByRole
  const roleBtn = page.getByRole('button', { name: '添加画师' });
  const n = await roleBtn.count().catch(() => -1);
  console.log('getByRole add count:', n);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });