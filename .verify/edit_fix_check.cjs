const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const OUT = '/home/rosemary/workspace/ImageForge/.verify';
(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(15000);
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1200);
  await page.click('a[href="/loras"]');
  await page.waitForTimeout(1200);
  // open edit dialog on first row/card
  const opened = await page.evaluate(() => {
    const btn = [...document.querySelectorAll('.op-btn')].find(b => b.title === '编辑');
    if (btn) { btn.click(); return true; }
    return false;
  });
  await page.waitForTimeout(800);
  const edit = await page.evaluate(() => {
    const dlg = document.querySelector('.v-overlay--active');
    const text = dlg ? (dlg.innerText || '') : '';
    return {
      open: !!dlg,
      hasLocal: text.includes('本地信息'),
      hasRemote: text.includes('远端信息'),
      hasTech: text.includes('技术信息'),
      hasFavorite: text.includes('收藏'),
      hasCoverHidden: text.includes('隐藏封面'),
      hasAbsPath: /D:\\\\|\/mnt\/[a-z]|\/home\/[^ ]*safetensors/i.test(text),
      sectionsScrollable: (() => {
        const s = document.querySelector('.edit-sections');
        return s ? getComputedStyle(s).overflowY : null;
      })(),
    };
  });
  console.log('[edit dialog after fix]', JSON.stringify(edit, null, 1));
  await page.screenshot({ path: `${OUT}/lm_04_lora_edit_dialog.png` });
  console.log('saved lm_04_lora_edit_dialog');
  // expand tech
  await page.evaluate(() => {
    const t = [...document.querySelectorAll('.v-overlay--active .tech-toggle')];
    if (t[0]) t[0].click();
  });
  await page.waitForTimeout(300);
  const tech = await page.evaluate(() => {
    const dlg = document.querySelector('.v-overlay--active');
    const text = dlg ? (dlg.innerText || '') : '';
    return { hasSha: text.includes('SHA256'), hasModelId: text.includes('Civitai Model ID'), hasAbsPath: /D:\\\\|\/mnt\/[a-z]|\/home\/[^ ]*safetensors/i.test(text) };
  });
  console.log('[tech after fix]', JSON.stringify(tech));
  await page.screenshot({ path: `${OUT}/lm_05_lora_edit_tech.png` });
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });