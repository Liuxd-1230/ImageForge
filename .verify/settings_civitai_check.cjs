const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(15000);
  await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1200);
  await page.click('a[href="/settings"]');
  await page.waitForTimeout(1200);
  const r = await page.evaluate(() => {
    const text = document.body.innerText || '';
    return {
      hasCivitaiSection: text.includes('Civitai 元数据'),
      hasHostRed: text.includes('Civitai Red'),
      hasHostCom: text.includes('Civitai.com'),
      hasTokenField: text.includes('Civitai API Token'),
      hostValue: (() => {
        const sel = document.querySelector('.v-select');
        return sel ? (sel.innerText || '').slice(0, 60) : null;
      })(),
    };
  });
  console.log('[settings civitai]', JSON.stringify(r, null, 1));
  await page.screenshot({ path: '/home/rosemary/workspace/ImageForge/.verify/lm_09_settings_civitai.png' });
  console.log('saved lm_09_settings_civitai');
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });