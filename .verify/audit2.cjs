// ImageForge Studio — corrected objective audit
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  const audit = await page.evaluate(() => {
    const cs = (el, p) => el ? getComputedStyle(el)[p] : null;
    const q = s => document.querySelector(s);
    const qa = s => [...document.querySelectorAll(s)];
    const genBtn = q('.generate-btn');
    const sceneWrap = q('.scene-input-wrap');
    const promptTa = q('.prompt-textarea');
    const longName = [...qa('.lora-name')].sort((a, b) => b.scrollWidth - a.scrollWidth)[0];
    return {
      fontFamily: cs(document.body, 'fontFamily'),
      sectionTitleSize: cs(q('.section-title'), 'fontSize'),
      sceneRadius: cs(sceneWrap, 'borderRadius'),
      sceneFontSize: cs(q('.scene-input'), 'fontSize'),
      sceneBorder: cs(sceneWrap, 'borderTopWidth') + ' ' + cs(sceneWrap, 'borderColor'),
      promptFont: cs(promptTa, 'fontFamily'),
      promptFontSize: cs(promptTa, 'fontSize'),
      promptLineHeight: cs(promptTa, 'lineHeight'),
      promptMinHeight: cs(promptTa, 'minHeight'),
      promptRadius: cs(q('.prompt-editor'), 'borderRadius'),
      genHeight: cs(genBtn, 'height'),
      genRadius: cs(genBtn, 'borderRadius'),
      genBg: cs(genBtn, 'backgroundColor'),
      genFontSize: cs(genBtn, 'fontSize'),
      genColor: cs(genBtn, 'color'),
      canvasRadius: cs(q('.canvas-box'), 'borderRadius'),
      canvasBg: cs(q('.canvas-box'), 'backgroundColor'),
      canvasEmptyText: q('.canvas-empty-caption') ? q('.canvas-empty-caption').textContent : null,
      inspWidth: q('.inspector').getBoundingClientRect().width,
      safetyHeight: q('.safety-seg').getBoundingClientRect().height,
      longNameEllipsis: {
        text: longName ? longName.textContent.slice(0, 30) : null,
        textOverflow: longName ? cs(longName, 'textOverflow') : null,
        whiteSpace: longName ? cs(longName, 'whiteSpace') : null,
        overflowX: longName ? cs(longName, 'overflowX') : null,
        minWidth: longName ? cs(longName, 'minWidth') : null,
        clientW: longName ? longName.clientWidth : null,
      },
      noTinyFonts: qa('.studio-root *').map(e => parseFloat(cs(e, 'fontSize')) || 0).filter(v => v > 0 && v <= 10.9).length,
    };
  });
  console.log('AUDIT ' + JSON.stringify(audit, null, 2));

  // Open advanced
  await page.evaluate(() => document.querySelectorAll('.acc-head')[1].click());
  await page.waitForTimeout(300);
  // Switch to Cloud
  await page.evaluate(() => {
    [...document.querySelectorAll('.adv-provider-btn')].find(b => b.textContent.trim() === 'Cloud').click();
  });
  await page.waitForTimeout(300);
  const cloudLabels = await page.$$eval('.rs-label', els => els.map(e => e.textContent.trim()));
  console.log('CLOUD_LABELS ' + JSON.stringify(cloudLabels));
  // MAX
  await page.evaluate(() => {
    [...document.querySelectorAll('.rs-label')].find(x => x.textContent.includes('MAX')).click();
  });
  await page.waitForTimeout(400);
  const maxGeo = await page.evaluate(() => ({
    fillCls: document.querySelector('.rs-fill').className,
    fillW: getComputedStyle(document.querySelector('.rs-fill')).width,
    thumbCls: document.querySelector('.rs-thumb').className,
    thumbLeft: getComputedStyle(document.querySelector('.rs-thumb')).left,
    maxText: (document.querySelector('.reason-current') || {}).textContent,
    maxLabelHasGradient: !!document.querySelector('.rs-label .if-max-gradient'),
    stops: [...document.querySelectorAll('.rs-stop')].map(s => getComputedStyle(s).left),
  }));
  console.log('MAX_GEO ' + JSON.stringify(maxGeo));

  // LM Studio
  await page.evaluate(() => {
    [...document.querySelectorAll('.adv-provider-btn')].find(b => b.textContent.trim() === 'LM Studio').click();
  });
  await page.waitForTimeout(300);
  const lmLabels = await page.$$eval('.rs-label', els => els.map(e => e.textContent.trim()));
  console.log('LM_LABELS ' + JSON.stringify(lmLabels));

  // MAX effect disappears in LM mode (no neon in normal state)
  const lmNeon = await page.evaluate(() => ({
    thumbMax: document.querySelector('.rs-thumb.max') !== null,
    trackMax: document.querySelector('.rs-fill.if-max-track') !== null,
  }));
  console.log('LM_NO_NEON ' + JSON.stringify(lmNeon));

  console.log('ERRORS ' + JSON.stringify(errors.slice(0, 10)));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
