// ImageForge Commit B — bulk selection/delete + canvas overlay + M3 radii QA
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');

const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';
const OUT = '/home/rosemary/workspace/ImageForge/.verify';
const fs = require('fs');

async function shot(page, name) {
  await page.screenshot({ path: `${OUT}/${name}.png` });
  console.log('saved', name);
}

async function overflow(page, label) {
  const r = await page.evaluate(() => {
    const de = document.documentElement;
    return {
      docW: de.scrollWidth, docCw: de.clientWidth,
      docH: de.scrollHeight, docCh: de.clientHeight,
      horiz: de.scrollWidth > de.clientWidth,
      vert: de.scrollHeight > de.clientHeight,
      vw: window.innerWidth, vh: window.innerHeight,
    };
  });
  console.log(label, JSON.stringify(r));
  return r;
}

async function piniaStore(page, id) {
  return await page.evaluate((sid) => {
    const app = document.querySelector('#app') && document.querySelector('#app').__vue_app__;
    const pinia = app && app.config.globalProperties && app.config.globalProperties.$pinia;
    return { hasVue: !!app, hasPinia: !!pinia, hasStore: !!(pinia && pinia._s && pinia._s.get(sid)) };
  }, id);
}

async function setStudio(page, patch) {
  await page.evaluate((p) => {
    const app = document.querySelector('#app').__vue_app__;
    const pinia = app.config.globalProperties.$pinia;
    const s = pinia._s.get('studio');
    Object.assign(s, p);
  }, patch);
}

async function goto(page, href) {
  await page.click(`a[href="${href}"]`);
  await page.waitForTimeout(900);
}

async function clickCheck(page, selector, index = 0) {
  const els = await page.$$(selector);
  if (els[index]) { await els[index].click(); await page.waitForTimeout(350); return true; }
  return false;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(20000);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  const st = await piniaStore(page, 'studio');
  console.log('[pinia]', JSON.stringify(st));

  // ── Studio: canvas overlay with old image + generating (running, real progress) ──
  await setStudio(page, {
    generatedImageUrl: '/qa_placeholder.svg',
    isGenerating: true,
    generationStage: 'running',
    generationProgressValue: 7,
    generationProgressMax: 12,
    generationIsRunning: true,
    generationMessage: '生成中 7 / 12',
  });
  await page.waitForTimeout(600);
  await overflow(page, '[canvas overlay running]');
  const ov = await page.evaluate(() => {
    const el = document.querySelector('.canvas-progress-overlay');
    const img = document.querySelector('.canvas-img');
    if (!el || !img) return { overlay: !!el, img: !!img };
    const er = el.getBoundingClientRect();
    const ir = img.getBoundingClientRect();
    return {
      overlay: true, img: true,
      overlayTop: er.top, overlayBottom: er.bottom, overlayW: er.width,
      imgTop: ir.top, imgBottom: ir.bottom,
      overlayInsideImage: er.top >= ir.top && er.bottom <= ir.bottom,
      notCoveringMain: er.bottom <= ir.bottom - 40,
      fillW: (document.querySelector('.canvas-progress-fill') || {}).style && document.querySelector('.canvas-progress-fill').style.width,
      text: (document.querySelector('.canvas-progress-text') || {}).textContent,
      caption: (document.querySelector('.canvas-empty-caption') || {}).textContent,
    };
  });
  console.log('[canvas overlay geometry]', JSON.stringify(ov));
  await shot(page, 'cb_01_canvas_overlay_running');

  // ── Studio: no old image + generating → central progress empty state ──
  await setStudio(page, {
    generatedImageUrl: '',
    isGenerating: true,
    generationStage: 'queued',
    generationProgressValue: null,
    generationProgressMax: null,
    generationIsRunning: false,
    generationMessage: '',
  });
  await page.waitForTimeout(400);
  const cen = await page.evaluate(() => ({
    empty: !!document.querySelector('.canvas-empty'),
    hasProgress: !!document.querySelector('.canvas-empty .canvas-progress'),
    indeterminate: !!document.querySelector('.canvas-empty .canvas-progress-fill.indeterminate'),
  }));
  console.log('[canvas empty generating]', JSON.stringify(cen));
  await shot(page, 'cb_02_canvas_empty_generating');

  // ── Studio: idle empty state ──
  await setStudio(page, { isGenerating: false, generatedImageUrl: '', generationStage: 'idle', generationError: null });
  await page.waitForTimeout(400);
  await shot(page, 'cb_03_canvas_empty_idle');

  // ── Character Book ──
  await goto(page, '/characters');
  await page.waitForTimeout(900);
  const rowsN = await page.$$('.resolved-row').then(r => r.length);
  console.log('[characterbook resolved rows]', rowsN);
  await shot(page, 'cb_04_characterbook');
  // bulk: select first resolved row
  await clickCheck(page, '.resolved-row .row-check input[type="checkbox"]', 0);
  const cbBulk = await page.evaluate(() => document.body.innerText.includes('已选择'));
  console.log('[characterbook bulk after click]', cbBulk);
  await shot(page, 'cb_05_characterbook_bulk');

  // ── Artist ──
  await goto(page, '/artists');
  await page.waitForTimeout(900);
  await shot(page, 'cb_06_artist');
  await clickCheck(page, '.artist-check input[type="checkbox"]', 0);
  await shot(page, 'cb_07_artist_bulk');

  // ── LoRA ──
  await goto(page, '/loras');
  await page.waitForTimeout(900);
  await shot(page, 'cb_08_lora');
  await clickCheck(page, '.lora-row .head-check input[type="checkbox"]', 1);
  await shot(page, 'cb_09_lora_bulk');

  // ── Rules ──
  await goto(page, '/rules');
  await page.waitForTimeout(900);
  await shot(page, 'cb_10_rules');
  await clickCheck(page, '.rule-card .row-check input[type="checkbox"]', 0);
  await shot(page, 'cb_11_rules_bulk');

  // ── Presets ──
  await goto(page, '/presets');
  await page.waitForTimeout(900);
  await shot(page, 'cb_12_presets');

  // ── History ──
  await goto(page, '/history');
  await page.waitForTimeout(900);
  await shot(page, 'cb_13_history');
  await clickCheck(page, '.history-check input[type="checkbox"]', 0);
  await shot(page, 'cb_14_history_bulk');

  // ── Settings ──
  await goto(page, '/settings');
  await page.waitForTimeout(900);
  await shot(page, 'cb_15_settings');

  // ── Field radius close-up: open artist create dialog (outlined v-text-fields) ──
  await goto(page, '/artists');
  await page.waitForTimeout(700);
  try {
    await page.getByRole('button', { name: '添加画师' }).first().click();
    await page.waitForTimeout(700);
    await shot(page, 'cb_16_field_radius');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
  } catch (e) {
    console.log('artist dialog open failed:', e.message);
  }

  await browser.close();
  console.log('PASS1440');

  // ═══ 1920×1080 ═══
  const b2 = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const p2 = await b2.newPage({ viewport: { width: 1920, height: 1080 } });
  p2.setDefaultTimeout(20000);
  await p2.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await p2.waitForTimeout(1500);
  await overflow(p2, '[1920 studio]');
  await shot(p2, 'cb_17_1920_studio');
  await goto(p2, '/loras');
  await p2.waitForTimeout(800);
  await overflow(p2, '[1920 lora]');
  await shot(p2, 'cb_18_1920_lora');
  await goto(p2, '/characters');
  await p2.waitForTimeout(800);
  await overflow(p2, '[1920 characters]');
  await shot(p2, 'cb_19_1920_characters');
  await goto(p2, '/history');
  await p2.waitForTimeout(800);
  await overflow(p2, '[1920 history]');
  await shot(p2, 'cb_20_1920_history');
  await b2.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
