// ImageForge Studio — dark theme + reduced-motion checks
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';
const OUT = '/home/rosemary/workspace/ImageForge/.verify';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // Toggle dark mode via sidebar button (App.vue toggle)
  await page.evaluate(() => {
    const btns = [...document.querySelectorAll('button')];
    const b = btns.find(x => x.textContent.includes('深色模式') || x.textContent.includes('浅色模式'));
    if (b) b.click();
  });
  await page.waitForTimeout(600);
  const dark = await page.evaluate(() => ({
    themeName: document.documentElement.getAttribute('class'),
    bg: getComputedStyle(document.querySelector('.studio-root')).backgroundColor,
    surface: getComputedStyle(document.querySelector('.inspector')).backgroundColor,
    text: getComputedStyle(document.querySelector('.studio-root')).color,
    genBg: getComputedStyle(document.querySelector('.generate-btn')).backgroundColor,
    canvasBg: getComputedStyle(document.querySelector('.canvas-box')).backgroundColor,
  }));
  console.log('DARK ' + JSON.stringify(dark));
  await page.screenshot({ path: `${OUT}/14_1440_dark.png` });

  // open advanced + cloud + MAX in dark to confirm neon works
  await page.evaluate(() => document.querySelectorAll('.acc-head')[1].click());
  await page.waitForTimeout(200);
  await page.evaluate(() => [...document.querySelectorAll('.adv-provider-btn')].find(b => b.textContent.trim() === 'Cloud').click());
  await page.waitForTimeout(200);
  await page.evaluate(() => [...document.querySelectorAll('.rs-label')].find(x => x.textContent.includes('MAX')).click());
  await page.waitForTimeout(400);
  const darkMax = await page.evaluate(() => ({
    thumbMax: document.querySelector('.rs-thumb.max') !== null,
    trackMax: document.querySelector('.rs-fill.if-max-track') !== null,
  }));
  console.log('DARK_MAX ' + JSON.stringify(darkMax));
  await page.screenshot({ path: `${OUT}/15_1440_dark_max.png` });
  await browser.close();

  // Reduced motion
  const browser2 = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const ctx = await browser2.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
  const page2 = await ctx.newPage();
  await page2.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page2.waitForTimeout(1200);
  await page2.evaluate(() => document.querySelectorAll('.acc-head')[1].click());
  await page2.waitForTimeout(200);
  await page2.evaluate(() => [...document.querySelectorAll('.adv-provider-btn')].find(b => b.textContent.trim() === 'Cloud').click());
  await page2.waitForTimeout(200);
  await page2.evaluate(() => [...document.querySelectorAll('.rs-label')].find(x => x.textContent.includes('MAX')).click());
  await page2.waitForTimeout(400);
  const rm = await page2.evaluate(() => {
    const thumb = document.querySelector('.rs-thumb.max');
    const fill = document.querySelector('.rs-fill.if-max-track');
    return {
      thumbAnimDur: getComputedStyle(thumb).animationDuration,
      fillAnimDur: getComputedStyle(fill).animationDuration,
      fillAnimIter: getComputedStyle(fill).animationIterationCount,
    };
  });
  console.log('REDUCED_MOTION ' + JSON.stringify(rm));
  await browser2.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
