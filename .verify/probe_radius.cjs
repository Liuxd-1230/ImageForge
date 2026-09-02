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

  const cards = await page.evaluate(() =>
    [...document.querySelectorAll('.v-card')].map((c, i) => ({
      i, cls: c.className.toString().replace(/\s+/g, ' ').slice(0, 80),
      radius: getComputedStyle(c).borderRadius,
      w: Math.round(c.getBoundingClientRect().width),
    })));
  console.log('[artist cards]', JSON.stringify(cards));

  await page.getByRole('button', { name: '添加画师' }).first().click();
  await page.waitForTimeout(800);
  const dlg = await page.evaluate(() => {
    const overlays = [...document.querySelectorAll('.v-overlay')].map(o => ({ active: o.className.toString().includes('--active'), visible: !!(o.offsetWidth) }));
    const dialogs = [...document.querySelectorAll('.v-dialog')].map(d => ({ cls: d.className.toString().slice(0, 60), visible: !!(d.offsetWidth), text: (d.innerText || '').replace(/\s+/g, ' ').slice(0, 120) }));
    const fields = [...document.querySelectorAll('.v-field--outlined')].map(f => ({
      cls: f.className.toString().replace(/\s+/g, ' ').slice(0, 60),
      radius: getComputedStyle(f).borderRadius,
      outline: f.querySelector('.v-field__outline') ? getComputedStyle(f.querySelector('.v-field__outline')).borderRadius : null,
      start: f.querySelector('.v-field__outline__start') ? getComputedStyle(f.querySelector('.v-field__outline__start')).borderRadius : null,
      end: f.querySelector('.v-field__outline__end') ? getComputedStyle(f.querySelector('.v-field__outline__end')).borderRadius : null,
    }));
    return { overlays, dialogs, fields };
  });
  console.log('[artist dialog]', JSON.stringify(dlg, null, 1));
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });