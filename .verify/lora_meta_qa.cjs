// LoRA Metadata V1 — browser QA (card/list dual view + edit dialog + no absolute paths)
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
      horiz: de.scrollWidth > de.clientWidth,
      vw: window.innerWidth, vh: window.innerHeight,
    };
  });
  console.log(label, JSON.stringify(r));
  return r;
}

async function goto(page, href) {
  await page.click(`a[href="${href}"]`);
  await page.waitForTimeout(1000);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(15000);
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);

  // ── LoRA Library: card view (default) ──
  await goto(page, '/loras');
  await page.waitForTimeout(1200);
  const cardInfo = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('.lora-card')];
    const bodyText = document.body.innerText;
    return {
      cardCount: cards.length,
      covers: cards.filter(c => !!c.querySelector('.cover-img')).length,
      coverEmpty: cards.filter(c => !!c.querySelector('.cover-empty')).length,
      hasAbsPath: /D:\\\\|\/mnt\/[a-z]|\/home\/[^ ]*safetensors/i.test(bodyText),
      hasSourcePath: bodyText.includes('source_path'),
      viewToggle: !!document.querySelector('.view-toggle'),
      metaBadges: [...document.querySelectorAll('.meta-badge')].map(b => b.textContent.trim()).slice(0, 6),
    };
  });
  console.log('[card view]', JSON.stringify(cardInfo, null, 1));
  await overflow(page, '[lora card 1440]');
  await shot(page, 'lm_01_lora_card');

  // ── switch to list view ──
  await page.evaluate(() => {
    const btns = [...document.querySelectorAll('.vt-btn')];
    const list = btns.find(b => b.title === '列表视图');
    if (list) list.click();
  });
  await page.waitForTimeout(500);
  const listInfo = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.lora-row')];
    const bodyText = document.body.innerText;
    return {
      rowCount: rows.length,
      hasCoverImg: !!document.querySelector('.lora-row img, .lora-row .cover-img'),
      hasAbsPath: /D:\\\\|\/mnt\/[a-z]|\/home\/[^ ]*safetensors/i.test(bodyText),
      hasFilenameCol: bodyText.includes('文件名'),
      hasMetaCol: !!document.querySelector('.lora-head .col-meta'),
    };
  });
  console.log('[list view]', JSON.stringify(listInfo, null, 1));
  await overflow(page, '[lora list 1440]');
  await shot(page, 'lm_02_lora_list');

  // ── select one row → bulk metadata button visible ──
  const clicked = await page.evaluate(() => {
    const cb = document.querySelector('.lora-row .head-check input');
    if (cb) { cb.click(); return true; }
    return false;
  });
  await page.waitForTimeout(400);
  const bulk = await page.evaluate(() => ({
    hasSelectedText: document.body.innerText.includes('已选择'),
    hasMetaBtn: [...document.querySelectorAll('button')].some(b => (b.innerText || '').includes('补全所选 Metadata')),
    hasDeleteBtn: document.body.innerText.includes('删除所选'),
  }));
  console.log('[list bulk]', JSON.stringify(bulk));
  await shot(page, 'lm_03_lora_list_bulk');

  // ── open edit dialog (three sections) ──
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('.lora-row .op-btn')].find(b => b.title === '编辑');
    if (btn) btn.click();
  });
  await page.waitForTimeout(700);
  const edit = await page.evaluate(() => {
    const dlg = document.querySelector('.v-overlay--active');
    const text = dlg ? (dlg.innerText || '') : '';
    return {
      open: !!dlg,
      hasLocal: text.includes('本地信息'),
      hasRemoteSection: text.includes('远端信息'),
      hasTechToggle: text.includes('技术信息'),
      hasAbsPath: /D:\\\\|\/mnt\/[a-z]|\/home\/[^ ]*safetensors/i.test(text),
      hasFilename: text.includes('ComfyUI filename'),
    };
  });
  console.log('[edit dialog]', JSON.stringify(edit));
  await shot(page, 'lm_04_lora_edit_dialog');
  // expand technical
  await page.evaluate(() => {
    const t = [...document.querySelectorAll('.v-overlay--active .tech-toggle')];
    if (t[0]) t[0].click();
  });
  await page.waitForTimeout(300);
  const tech = await page.evaluate(() => {
    const dlg = document.querySelector('.v-overlay--active');
    const text = dlg ? (dlg.innerText || '') : '';
    return {
      hasSha: text.includes('SHA256'),
      hasModelId: text.includes('Civitai Model ID'),
      hasAbsPath: /D:\\\\|\/mnt\/[a-z]|\/home\/[^ ]*safetensors/i.test(text),
    };
  });
  console.log('[tech section]', JSON.stringify(tech));
  await shot(page, 'lm_05_lora_edit_tech');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);

  // ── source manager still shows paths ──
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('button')].find(b => (b.innerText || '').includes('扫描来源'));
    if (btn) btn.click();
  });
  await page.waitForTimeout(700);
  const src = await page.evaluate(() => {
    const dlg = document.querySelector('.v-overlay--active');
    const text = dlg ? (dlg.innerText || '') : '';
    return {
      open: !!dlg,
      showsPath: /D:\\\\|\/mnt\/[a-z]|\/home\//i.test(text),
      hasAddSource: text.includes('添加来源'),
    };
  });
  console.log('[source manager]', JSON.stringify(src));
  await shot(page, 'lm_06_lora_source_manager');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  await browser.close();
  console.log('PASS1440');

  // ═══ 1920×1080 ═══
  const b2 = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const p2 = await b2.newPage({ viewport: { width: 1920, height: 1080 } });
  p2.setDefaultTimeout(15000);
  await p2.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await p2.waitForTimeout(1500);
  await goto(p2, '/loras');
  await p2.waitForTimeout(1200);
  await overflow(p2, '[lora card 1920]');
  await shot(p2, 'lm_07_1920_lora_card');
  await p2.evaluate(() => {
    const btns = [...document.querySelectorAll('.vt-btn')];
    const list = btns.find(b => b.title === '列表视图');
    if (list) list.click();
  });
  await p2.waitForTimeout(500);
  await overflow(p2, '[lora list 1920]');
  await shot(p2, 'lm_08_1920_lora_list');
  await b2.close();
  console.log('DONE');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
