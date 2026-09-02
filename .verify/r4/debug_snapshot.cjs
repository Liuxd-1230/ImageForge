// Debug: does blur+fill actually commit 448 before generate? Print store values via a window hook.
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(30000);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // expose pinia store for debugging
  await page.evaluate(async () => {
    const { useStudioStore } = await import('/src/stores/studio.ts');
    window.__st = useStudioStore();
  });

  await page.click('.prompt-textarea');
  await page.type('.prompt-textarea', 'debug snapshot test');
  await page.waitForTimeout(200);

  await page.evaluate(() => document.querySelectorAll('.acc-head')[1].click());
  await page.waitForTimeout(300);

  const readStore = () => page.evaluate(() => ({ w: window.__st.width, h: window.__st.height, seed: window.__st.seed }));

  console.log('initial', JSON.stringify(await readStore()));
  const s = await page.$$('.size-input');
  console.log('num size-inputs:', s.length);
  await s[0].fill('448');
  await s[0].evaluate(el => el.blur());
  await s[1].fill('448');
  await s[1].evaluate(el => el.blur());
  await page.waitForTimeout(300);
  console.log('after 448 fill+blur', JSON.stringify(await readStore()));
  await page.click('.generate-btn');
  await page.waitForTimeout(1200);
  console.log('1.2s after generate', JSON.stringify(await readStore()), 'isGenerating=', await page.evaluate(() => window.__st.isGenerating));
  await page.waitForTimeout(1500);
  const s3 = await page.$$('.size-input');
  await s3[0].fill('384');
  await s3[0].evaluate(el => el.blur());
  await s3[1].fill('384');
  await s3[1].evaluate(el => el.blur());
  console.log('after mid-gen 384', JSON.stringify(await readStore()));
  // wait for done
  for (let i = 0; i < 60; i++) {
    await page.waitForTimeout(1000);
    const hasImg = await page.evaluate(() => !!document.querySelector('.canvas-img') && document.querySelector('.canvas-img').offsetWidth > 0);
    if (hasImg) break;
  }
  const meta = await page.textContent('.toolbar-meta').catch(() => '');
  const snap = await page.evaluate(() => JSON.stringify(window.__st.lastGenerationSnapshot && { w: window.__st.lastGenerationSnapshot.width, h: window.__st.lastGenerationSnapshot.height, seed: window.__st.lastGenerationSnapshot.seed, steps: window.__st.lastGenerationSnapshot.steps }));
  console.log('final meta:', meta);
  console.log('lastGenerationSnapshot:', snap);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
