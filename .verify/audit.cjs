// ImageForge Studio — objective style/geometry audit (no vision needed)
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push('console.error: ' + m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  const audit = await page.evaluate(() => {
    const cs = (el, p) => el ? getComputedStyle(el)[p] : null;
    const q = s => document.querySelector(s);
    const qa = s => [...document.querySelectorAll(s)];
    const body = document.body;
    const sceneWrap = q('.scene-input-wrap');
    const sceneInput = q('.scene-input');
    const safetySeg = q('.safety-seg');
    const promptTa = q('.prompt-textarea');
    const genBtn = q('.generate-btn');
    const canvasBox = q('.canvas-box');
    const inspScroll = q('.inspector-scroll');
    const loraNames = qa('.lora-name');
    const sectionTitle = q('.section-title');

    // LoRA name ellipsis check — any name wider than its box?
    const loraEllipsis = loraNames.map(n => ({
      text: n.textContent.slice(0, 24),
      scrollW: n.scrollWidth,
      clientW: n.clientWidth,
      ellipsisOk: n.scrollWidth <= n.clientWidth + 1,
    }));

    // broad overflow: any element in inspector whose right edge exceeds inspector content width
    const insp = q('.inspector');
    const inspRect = insp.getBoundingClientRect();
    let overflowers = [];
    qa('.inspector *').forEach(el => {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && (r.right > inspRect.right + 1 || r.left < inspRect.left - 1)) {
        overflowers.push(`${el.tagName}.${(el.className || '').toString().slice(0, 40)} right=${Math.round(r.right)} inspRight=${Math.round(inspRect.right)}`);
      }
    });

    return {
      fontFamily: cs(body, 'fontFamily'),
      sectionTitleSize: cs(sectionTitle, 'fontSize'),
      sceneRadius: cs(sceneWrap, 'borderRadius'),
      sceneFontSize: cs(sceneInput, 'fontSize'),
      sceneBg: cs(sceneWrap, 'backgroundColor'),
      promptFont: cs(promptTa, 'fontFamily'),
      promptFontSize: cs(promptTa, 'fontSize'),
      promptLineHeight: cs(promptTa, 'lineHeight'),
      promptRadius: cs(q('.prompt-editor'), 'borderRadius'),
      promptMinHeight: cs(promptTa, 'minHeight'),
      genHeight: cs(genBtn, 'height'),
      genRadius: cs(genBtn, 'borderRadius'),
      genBg: cs(genBtn, 'backgroundColor'),
      genFontSize: cs(genBtn, 'fontSize'),
      genColor: cs(genBtn, 'color'),
      canvasRadius: cs(canvasBox, 'borderRadius'),
      canvasBg: cs(canvasBox, 'backgroundColor'),
      safetyRadius: cs(safetySeg, 'borderRadius'),
      safetyIndicatorTransform: cs(q('.safety-indicator'), 'transform'),
      safetyBtnCount: qa('.safety-seg-btn').length,
      safetyActiveText: cs(q('.safety-seg-btn.active'), 'color'),
      safetyActiveWeight: cs(q('.safety-seg-btn.active'), 'fontWeight'),
      inspectorWidth: inspRect.width,
      genBarVisible: (() => { const r = q('.generate-bar').getBoundingClientRect(); return r.bottom <= window.innerHeight + 1; })(),
      canvasTop: (() => { const r = canvasBox.getBoundingClientRect(); return r.top; })(),
      loraCount: loraNames.length,
      loraEllipsis,
      inspectorOverflowers: overflowers.slice(0, 12),
      horizInspOverflow: inspScroll.scrollWidth > inspScroll.clientWidth,
      primaryVar: getComputedStyle(document.documentElement).getPropertyValue('--v-theme-primary').trim(),
      backgroundVar: getComputedStyle(document.documentElement).getPropertyValue('--v-theme-background').trim(),
      surfaceVar: getComputedStyle(document.documentElement).getPropertyValue('--v-theme-surface').trim(),
      fontSizeSet: qa('.studio-root *').map(e => parseFloat(cs(e, 'fontSize')) || 0).filter(v => v > 0 && v <= 10.9).length,
    };
  });
  console.log('AUDIT ' + JSON.stringify(audit, null, 2));

  // safety indicator movement across values
  const safetyLabels = ['Safe', 'Sensitive', 'NSFW', 'Explicit'];
  const transforms = [];
  for (const lab of safetyLabels) {
    await page.evaluate((l) => {
      const b = [...document.querySelectorAll('.safety-seg-btn')].find(x => x.textContent.trim() === l);
      if (b) b.click();
    }, lab);
    await page.waitForTimeout(250);
    transforms.push(await page.evaluate(() => getComputedStyle(document.querySelector('.safety-indicator')).transform));
  }
  console.log('SAFETY_TRANSFORMS ' + JSON.stringify(transforms));

  // reasoning slider labels for both providers
  await page.click('.acc-head >> nth=1');
  await page.waitForTimeout(300);
  const cloudLabels = await page.$$eval('.rs-label', els => els.map(e => e.textContent.trim()));
  console.log('CLOUD_LABELS ' + JSON.stringify(cloudLabels));
  // click MAX and read fill width + thumb left
  await page.evaluate(() => {
    const l = [...document.querySelectorAll('.rs-label')].find(x => x.textContent.includes('MAX'));
    if (l) l.click();
  });
  await page.waitForTimeout(300);
  const maxGeo = await page.evaluate(() => ({
    fillW: getComputedStyle(document.querySelector('.rs-fill')).width,
    thumbLeft: getComputedStyle(document.querySelector('.rs-thumb')).left,
    trackCls: document.querySelector('.rs-fill').className,
    thumbCls: document.querySelector('.rs-thumb').className,
  }));
  console.log('MAX_GEO ' + JSON.stringify(maxGeo));

  // LM Studio labels
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('.adv-provider-btn')].find(x => x.textContent.trim() === 'LM Studio');
    if (b) b.click();
  });
  await page.waitForTimeout(300);
  const lmLabels = await page.$$eval('.rs-label', els => els.map(e => e.textContent.trim()));
  console.log('LM_LABELS ' + JSON.stringify(lmLabels));

  console.log('ERRORS ' + JSON.stringify(errors));
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
