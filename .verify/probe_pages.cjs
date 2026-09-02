const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';
const pages = [
  ['/characters', '.resolved-row, .character-card'],
  ['/artists', '.artist-item-card'],
  ['/loras', '.lora-row'],
  ['/rules', '.rule-card'],
  ['/presets', '.preset-card'],
  ['/history', '.history-card'],
  ['/settings', 'input, textarea'],
];
(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(15000);
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + String(e).slice(0, 300)));
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1200);
  for (const [href, sel] of pages) {
    await page.click(`a[href="${href}"]`).catch(e => console.log('nav fail', href, e.message));
    await page.waitForTimeout(1100);
    const info = await page.evaluate(({ href, sel }) => {
      const bodyText = document.body.innerText || '';
      return {
        url: location.pathname,
        href,
        count: document.querySelectorAll(sel).length,
        hasEmpty: bodyText.includes('暂无') || bodyText.includes('还没有') || bodyText.includes('未找到'),
        bodyHead: bodyText.replace(/\n+/g, ' | ').slice(0, 150),
        appChildren: document.querySelector('#app') ? document.querySelector('#app').childElementCount : -1,
      };
    }, { href, sel });
    console.log(JSON.stringify(info));
  }
  console.log('JS ERRORS:', JSON.stringify(errors.slice(0, 10)));
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
