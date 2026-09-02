// Focused debug: reproduce test-3 generation, print per-iteration UI state
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(30000);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // ensure prompt set directly (skip parse for speed)
  await page.click('.prompt-textarea');
  await page.type('.prompt-textarea', 'debug prompt test');
  await page.waitForTimeout(300);

  await page.evaluate(() => document.querySelectorAll('.acc-head')[1].click());
  await page.waitForTimeout(300);
  const si = await page.$$('.size-input');
  await si[0].fill('384');
  await si[1].fill('384');
  await si[1].evaluate(el => el.blur());
  await page.waitForTimeout(200);

  await page.click('.generate-btn');
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(1000);
    const state = await page.evaluate(() => {
      const gs = document.querySelector('.gen-status')?.textContent?.trim() || '';
      const cap = document.querySelector('.canvas-empty-caption')?.textContent?.trim() || '';
      const msg = document.querySelector('.canvas-gen-msg')?.textContent?.trim() || '';
      const progText = document.querySelector('.canvas-progress-text')?.textContent?.trim() || '';
      const hasImg = !!document.querySelector('.canvas-img');
      const imgVisible = !!document.querySelector('.canvas-img') && document.querySelector('.canvas-img').offsetWidth > 0;
      const err = document.querySelector('.canvas-error')?.textContent?.trim() || '';
      const btn = document.querySelector('.generate-btn')?.textContent?.trim() || '';
      const meta = document.querySelector('.toolbar-meta')?.textContent?.trim() || '';
      return { gs, cap, msg, progText, hasImg, imgVisible, err, btn, meta };
    });
    console.log(`[${i}]`, JSON.stringify(state));
    if (state.hasImg && state.imgVisible) { console.log('IMAGE FOUND'); break; }
    if (state.err.includes('失败') || state.err.includes('异常')) { console.log('ERR SHOWN'); break; }
    if (!state.btn.includes('生成中')) { console.log('GEN ENDED'); break; }
  }
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
