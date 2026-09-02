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
  await page.waitForTimeout(800);
  const fields = await page.evaluate(() => {
    const all = [...document.querySelectorAll('.v-field')].map(f => ({
      cls: f.className.toString().replace(/\s+/g, ' '),
      radius: getComputedStyle(f).borderRadius,
      outlineEl: !!f.querySelector('.v-field__outline'),
      outlineRadius: f.querySelector('.v-field__outline') ? getComputedStyle(f.querySelector('.v-field__outline')).borderRadius : null,
      startR: f.querySelector('.v-field__outline__start') ? getComputedStyle(f.querySelector('.v-field__outline__start')).borderRadius : null,
      endR: f.querySelector('.v-field__outline__end') ? getComputedStyle(f.querySelector('.v-field__outline__end')).borderRadius : null,
    }));
    // also find ANY element whose class contains 'outlined'
    const outlinedCls = [...document.querySelectorAll('[class*="outlined"]')].map(e => e.className.toString().slice(0, 70));
    return { fields: all, outlinedCls: [...new Set(outlinedCls)].slice(0, 20) };
  });
  console.log('[dialog fields]', JSON.stringify(fields, null, 1));
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });