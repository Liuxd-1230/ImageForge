// ImageForge Commit B — DOM / computed-style QA (objective evidence, no vision needed)
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';

async function cs(page, selector, props) {
  return await page.evaluate(({ sel, props }) => {
    const el = document.querySelector(sel);
    if (!el) return { sel, missing: true };
    const s = getComputedStyle(el);
    const out = { sel };
    props.forEach(p => { out[p] = s.getPropertyValue(p); });
    return out;
  }, { sel: selector, props });
}

async function goto(page, href) {
  await page.click(`a[href="${href}"]`);
  await page.waitForTimeout(900);
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(20000);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // 1) Studio canvas overlay CSS
  await page.evaluate((p) => {
    const app = document.querySelector('#app').__vue_app__;
    const s = app.config.globalProperties.$pinia._s.get('studio');
    Object.assign(s, p);
  }, {
    generatedImageUrl: '/qa_placeholder.svg', isGenerating: true, generationStage: 'running',
    generationProgressValue: 7, generationProgressMax: 12, generationIsRunning: true, generationMessage: '生成中 7 / 12',
  });
  await page.waitForTimeout(500);
  const overlayCss = await cs(page, '.canvas-progress-overlay', ['position', 'bottom', 'z-index', 'background-color', 'backdrop-filter', 'border-radius', 'width', 'max-width', 'box-shadow', 'padding']);
  const canvasCss = await cs(page, '.canvas-box', ['position', 'overflow']);
  const fillCss = await cs(page, '.canvas-progress-fill', ['height', 'border-radius', 'background-color', 'width']);
  console.log('[overlay css]', JSON.stringify(overlayCss));
  console.log('[canvas css]', JSON.stringify(canvasCss));
  console.log('[fill css]', JSON.stringify(fillCss));

  // 2) M3 radius tokens on :root
  const tokens = await page.evaluate(() => {
    const r = getComputedStyle(document.documentElement);
    return {
      field: r.getPropertyValue('--if-radius-field').trim(),
      container: r.getPropertyValue('--if-radius-container').trim(),
      card: r.getPropertyValue('--if-radius-card').trim(),
      dialog: r.getPropertyValue('--if-radius-dialog').trim(),
      button: r.getPropertyValue('--if-radius-button').trim(),
      pill: r.getPropertyValue('--if-radius-pill').trim(),
    };
  });
  console.log('[radius tokens]', JSON.stringify(tokens));

  // 3) real v-field outline radius (open a dialog with outlined fields)
  await goto(page, '/artists');
  await page.waitForTimeout(600);
  await page.click('text=添加画师').catch(() => console.log('add button click failed'));
  await page.waitForTimeout(600);
  const outline = await page.evaluate(() => {
    const o = document.querySelector('.v-field--outlined .v-field__outline');
    const oStart = document.querySelector('.v-field--outlined .v-field__outline__start');
    const oEnd = document.querySelector('.v-field--outlined .v-field__outline__end');
    const field = document.querySelector('.v-field--outlined');
    const input = document.querySelector('.v-field--outlined input, .v-field--outlined textarea');
    const btn = document.querySelector('.v-btn');
    const s = (el) => el ? getComputedStyle(el).borderRadius : null;
    return {
      fieldRadius: s(field),
      outlineRadius: o ? getComputedStyle(o).borderRadius : null,
      outlineStartRadius: oStart ? getComputedStyle(oStart).borderRadius : null,
      outlineEndRadius: oEnd ? getComputedStyle(oEnd).borderRadius : null,
      inputRadius: input ? getComputedStyle(input).borderRadius : null,
      btnRadius: btn ? getComputedStyle(btn).borderRadius : null,
    };
  });
  console.log('[field radius computed]', JSON.stringify(outline));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // 4) v-card / v-btn / v-dialog radius on a real page
  const cardRadius = await page.evaluate(() => {
    const c = document.querySelector('.v-card');
    const b = document.querySelector('.v-btn');
    return { card: c ? getComputedStyle(c).borderRadius : null, btn: b ? getComputedStyle(b).borderRadius : null };
  });
  console.log('[card/btn radius]', JSON.stringify(cardRadius));

  // 5) Presets: default row checkbox disabled
  await goto(page, '/presets');
  await page.waitForTimeout(800);
  const presets = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('.preset-card')];
    return cards.map(c => {
      const chip = c.querySelector('.v-chip') && c.querySelector('.v-chip').textContent.trim();
      const cb = c.querySelector('.row-check input[type=checkbox]');
      return { chip, checkboxDisabled: cb ? cb.disabled : null };
    });
  });
  console.log('[presets rows]', JSON.stringify(presets));

  // 6) BulkSelectionBar visible on each resource page when items selected
  const bulkPage = async (href) => {
    await goto(page, href);
    await page.waitForTimeout(800);
    // click first row checkbox
    const clicked = await page.evaluate(() => {
      const el = document.querySelector('.row-check input[type=checkbox], .artist-check input[type=checkbox], .lora-row .head-check input[type=checkbox], .history-check input[type=checkbox]');
      if (!el) return false;
      el.click();
      return true;
    });
    await page.waitForTimeout(400);
    const hasBulkText = await page.evaluate(() => document.body.innerText.includes('已选择'));
    const hasDeleteBtn = await page.evaluate(() => document.body.innerText.includes('删除所选'));
    console.log(`[bulk ${href}] clicked=${clicked} hasSelectedText=${hasBulkText} hasDeleteBtn=${hasDeleteBtn}`);
  };
  await bulkPage('/artists');
  await bulkPage('/loras');
  await bulkPage('/rules');
  await bulkPage('/history');

  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
