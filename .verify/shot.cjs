// ImageForge Studio UI — verification via Playwright
// Launch uses the cached Chrome for Testing binary via executablePath.
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');

const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';
const OUT = '/home/rosemary/workspace/ImageForge/.verify';

const fs = require('fs');

async function shot(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log('saved', name);
}

async function overflowReport(page, label) {
  const r = await page.evaluate(() => {
    const de = document.documentElement;
    const docW = de.scrollWidth;
    const docCw = de.clientWidth;
    const docH = de.scrollHeight;
    const docCh = de.clientHeight;
    const insp = document.querySelector('.inspector');
    const inspScroll = document.querySelector('.inspector-scroll');
    const inspW = insp ? insp.getBoundingClientRect().width : -1;
    const inspSW = inspScroll ? inspScroll.scrollWidth : -1;
    const inspCW = inspScroll ? inspScroll.clientWidth : -1;
    const canvas = document.querySelector('.canvas-box');
    const gen = document.querySelector('.generate-btn');
    const canvasR = canvas ? canvas.getBoundingClientRect() : null;
    const genR = gen ? gen.getBoundingClientRect() : null;
    const vh = window.innerHeight;
    const vw = window.innerWidth;
    return {
      docW, docCw, docH, docCh,
      horizPageOverflow: docW > docCw,
      vertPageOverflow: docH > docCh,
      inspW, inspSW, inspCW,
      horizInspOverflow: inspSW > inspCW,
      canvasVisible: !!canvasR && canvasR.top >= 0 && canvasR.bottom <= vh + 1 && canvasR.width > 0,
      genVisible: !!genR && genR.bottom <= vh + 1 && genR.width > 0,
      vh, vw,
    };
  });
  console.log(label, JSON.stringify(r, null, 2));
  return r;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(20000);

  console.log('goto', BASE);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // ---- default state at 1440x900 ----
  await overflowReport(page, '[1440 default]');
  await shot(page, '01_1440_default');

  // ---- open 解析详情 ----
  const accHeads = await page.$$('.acc-head');
  console.log('acc-head count:', accHeads.length);
  if (accHeads[0]) {
    await accHeads[0].click();
    await page.waitForTimeout(500);
    await shot(page, '02_1440_parse_details_open');
  }

  // ---- open 高级设置 ----
  if (accHeads[1]) {
    await accHeads[1].click();
    await page.waitForTimeout(500);
    await shot(page, '03_1440_advanced_open');
  }

  // ---- switch provider to Cloud ----
  const cloudBtn = await page.evaluateHandle(() => {
    const btns = [...document.querySelectorAll('.adv-provider-btn')];
    return btns.find(b => b.textContent.trim() === 'Cloud');
  });
  if (cloudBtn) {
    await cloudBtn.asElement().click();
    await page.waitForTimeout(500);
    await shot(page, '04_1440_cloud_reasoning');
  }

  // ---- set reasoning to MAX ----
  const maxLabel = await page.evaluateHandle(() => {
    const labels = [...document.querySelectorAll('.rs-label')];
    return labels.find(l => l.textContent.includes('MAX'));
  });
  if (maxLabel) {
    await maxLabel.asElement().click();
    await page.waitForTimeout(700);
    await shot(page, '05_1440_cloud_max_neon');
    // check MAX neon classes present
    const maxState = await page.evaluate(() => ({
      isMax: document.querySelector('.rs-thumb.max') !== null,
      hasGradientTrack: document.querySelector('.rs-fill.if-max-track') !== null,
      hasGradientText: document.querySelector('.rs-label .if-max-gradient') !== null,
      reasonCurrent: (document.querySelector('.reason-current') || {}).textContent,
    }));
    console.log('[MAX state]', JSON.stringify(maxState));
  }

  // ---- switch back to LM Studio ----
  const lmBtn = await page.evaluateHandle(() => {
    const btns = [...document.querySelectorAll('.adv-provider-btn')];
    return btns.find(b => b.textContent.trim() === 'LM Studio');
  });
  if (lmBtn) {
    await lmBtn.asElement().click();
    await page.waitForTimeout(400);
    const lmLabels = await page.$$eval('.rs-label', els => els.map(e => e.textContent.trim()));
    console.log('[LM Studio reasoning labels]', JSON.stringify(lmLabels));
    await shot(page, '06_1440_lm_reasoning');
  }

  // ---- toggle a LoRA on ----
  const loraChecks = await page.$$('.lora-check');
  console.log('lora rows:', loraChecks.length);
  if (loraChecks.length >= 2) {
    await loraChecks[0].click();
    await page.waitForTimeout(400);
    await shot(page, '07_1440_lora_enabled');
  }

  // ---- open artist dialog ----
  await page.click('.artist-add');
  await page.waitForTimeout(500);
  await shot(page, '08_1440_artist_dialog');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);

  // ---- open rules dialog ----
  await page.click('.rules-picker');
  await page.waitForTimeout(400);
  await shot(page, '09_1440_rules_dialog');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);

  // ---- type into scene input ----
  await page.click('.scene-input');
  await page.type('.scene-input', '穗穗穿着泳装，秧秧穿着蓝色海军水手服，穗穗在沙滩上追秧秧。');
  await page.waitForTimeout(400);
  await shot(page, '10_1440_scene_input_dirty');

  await browser.close();

  // ---- second browser pass at 1920x1080 ----
  const browser2 = await chromium.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const page2 = await browser2.newPage({ viewport: { width: 1920, height: 1080 } });
  page2.setDefaultTimeout(20000);
  await page2.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page2.waitForTimeout(1500);
  await overflowReport(page2, '[1920 default]');
  await shot(page2, '11_1920_default');

  // open advanced + cloud + MAX at 1920
  const accs = await page2.$$('.acc-head');
  if (accs[1]) { await accs[1].click(); await page2.waitForTimeout(400); }
  const cBtn = await page2.evaluateHandle(() => {
    const btns = [...document.querySelectorAll('.adv-provider-btn')];
    return btns.find(b => b.textContent.trim() === 'Cloud');
  });
  if (cBtn) { await cBtn.asElement().click(); await page2.waitForTimeout(400); }
  const mLabel = await page2.evaluateHandle(() => {
    const labels = [...document.querySelectorAll('.rs-label')];
    return labels.find(l => l.textContent.includes('MAX'));
  });
  if (mLabel) { await mLabel.asElement().click(); await page2.waitForTimeout(500); }
  await overflowReport(page2, '[1920 advanced+max]');
  await shot(page2, '12_1920_cloud_max');

  // LoRA enabled + long-name visible
  const checks2 = await page2.$$('.lora-check');
  if (checks2.length >= 2) { await checks2[1].click(); await page2.waitForTimeout(400); }
  await shot(page2, '13_1920_lora');

  await browser2.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
