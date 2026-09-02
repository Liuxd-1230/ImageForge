const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(10000);
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1200);

  // 1) Settings page: real outlined fields
  await page.click('a[href="/settings"]');
  await page.waitForTimeout(1200);
  const settings = await page.evaluate(() => {
    const fields = [...document.querySelectorAll('.v-field--outlined')].slice(0, 4).map(f => {
      const o = f.querySelector('.v-field__outline');
      const s = f.querySelector('.v-field__outline__start');
      const n = f.querySelector('.v-field__outline__notch');
      const e = f.querySelector('.v-field__outline__end');
      const inp = f.querySelector('input, textarea');
      const br = (el) => el ? getComputedStyle(el).borderRadius : null;
      return {
        fieldRadius: br(f),
        outlineRadius: br(o),
        startRadius: br(s),
        notchRadius: br(n),
        endRadius: br(e),
        inputRadius: br(inp),
        label: (f.querySelector('label') || {}).textContent || '',
      };
    });
    return { outlinedCount: document.querySelectorAll('.v-field--outlined').length, fields: fields };
  });
  console.log('[settings field radius]', JSON.stringify(settings, null, 1));

  // 2) Artist dialog fields via getByRole
  await page.click('a[href="/artists"]');
  await page.waitForTimeout(1000);
  await page.getByRole('button', { name: '添加画师' }).first().click();
  await page.waitForTimeout(700);
  const dialog = await page.evaluate(() => {
    const dlg = document.querySelector('.v-dialog--active');
    const fields = dlg ? [...dlg.querySelectorAll('.v-field--outlined')].map(f => {
      const o = f.querySelector('.v-field__outline');
      const s = f.querySelector('.v-field__outline__start');
      const e = f.querySelector('.v-field__outline__end');
      const br = (el) => el ? getComputedStyle(el).borderRadius : null;
      return {
        fieldRadius: br(f), outlineRadius: br(o), startRadius: br(s), endRadius: br(e),
        label: (f.querySelector('label') || {}).textContent || '',
      };
    }) : [];
    const btn = dlg ? [...dlg.querySelectorAll('.v-btn')].find(b => b.textContent.includes('保存')) : null;
    return { dialogOpen: !!dlg, fields, saveBtnRadius: btn ? getComputedStyle(btn).borderRadius : null };
  });
  console.log('[artist dialog radius]', JSON.stringify(dialog, null, 1));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // 3) Btn radius on page
  const pageBtns = await page.evaluate(() => {
    const b = [...document.querySelectorAll('.v-btn:not(.v-btn--icon)')].slice(0, 3).map(x => getComputedStyle(x).borderRadius);
    const card = document.querySelector('.artist-item-card, .v-card');
    return { btnRadii: b, cardRadius: card ? getComputedStyle(card).borderRadius : null };
  });
  console.log('[page btn/card radius]', JSON.stringify(pageBtns));

  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });