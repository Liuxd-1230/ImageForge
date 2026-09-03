// LoRA Metadata V1 Final Closure — browser QA
// Usage Tips / Trigger fallback / descriptions / strength display / no overflow
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
    return { docW: de.scrollWidth, docCw: de.clientWidth, horiz: de.scrollWidth > de.clientWidth };
  });
  console.log(label, JSON.stringify(r));
  return r;
}

async function qaAt(page, tag) {
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1200);
  await page.click('a[href="/loras"]');
  await page.waitForTimeout(1500);

  // ── CARD view ──
  const card = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('.lora-card')];
    const ashipin = cards.find(c => c.textContent.includes('Ashipin'));
    const bodyText = document.body.innerText;
    if (!ashipin) return { found: false };
    return {
      found: true,
      hasCover: !!ashipin.querySelector('.cover-img'),
      triggerText: ashipin.querySelector('.card-trigger')?.innerText?.slice(0, 120),
      showsCivitaiChip: !!ashipin.querySelector('.card-trigger .tw-src'),
      showsNoTriggerFalse: ashipin.querySelector('.card-trigger')?.textContent.includes('无触发词') ?? null,
      metaRow: ashipin.querySelector('.card-meta-row')?.innerText?.replace(/\n/g, ' | '),
      hasCivitaiRec: !!ashipin.querySelector('.rec-weight'),
      hasAbsPath: /D:\\\\|\/mnt\/[a-z]|\/home\/[^ ]*safetensors/i.test(bodyText),
    };
  });
  console.log(`[${tag} card]`, JSON.stringify(card, null, 1));
  await overflow(page, `[${tag} card overflow]`);
  await shot(page, `fc_${tag}_01_card`);

  // ── LIST view ──
  await page.evaluate(() => {
    const btns = [...document.querySelectorAll('.vt-btn')];
    btns[1]?.click();
  });
  await page.waitForTimeout(800);
  const list = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.lora-row')];
    const ashipin = rows.find(r => r.textContent.includes('Ashipin'));
    if (!ashipin) return { found: false };
    const trig = ashipin.querySelector('.col-trigger');
    const weight = ashipin.querySelector('.col-weight');
    return {
      found: true,
      noCover: !ashipin.querySelector('img'),
      triggerText: trig?.innerText?.slice(0, 100),
      triggerSingleLine: trig ? trig.scrollHeight <= 40 : null,
      triggerScrollW: trig ? { sw: trig.scrollWidth, cw: trig.clientWidth, ok: trig.scrollWidth <= trig.clientWidth + 2 } : null,
      weightText: weight?.innerText?.replace(/\n/g, ' | '),
      hasRecMini: !!ashipin.querySelector('.rec-mini'),
    };
  });
  console.log(`[${tag} list]`, JSON.stringify(list, null, 1));
  await overflow(page, `[${tag} list overflow]`);
  await shot(page, `fc_${tag}_02_list`);

  // ── EDIT dialog (id=7 Ashipin) ──
  await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.lora-row')];
    const ashipin = rows.find(r => r.textContent.includes('Ashipin'));
    ashipin?.querySelector('.op-btn')?.click();
  });
  await page.waitForTimeout(1000);
  const edit = await page.evaluate(() => {
    const dlg = document.querySelector('.m3-dialog');
    if (!dlg) return { found: false };
    const text = dlg.innerText;
    const usageBlock = [...dlg.querySelectorAll('.remote-block')].find(b => b.textContent.includes('Usage Tips'));
    const usageRows = usageBlock ? [...usageBlock.querySelectorAll('.rg-item')].map(i => i.innerText.replace(/\n/g, ': ')) : [];
    const chips = [...dlg.querySelectorAll('.tw-chip')].map(c => c.textContent);
    const descs = [...dlg.querySelectorAll('.remote-desc')].map(d => ({
      label: d.querySelector('.rg-label')?.textContent,
      len: d.querySelector('.remote-desc-text')?.textContent.length || 0,
    }));
    return {
      found: true,
      hasUsageTips: text.includes('Usage Tips'),
      usageRows,
      hidesClipSkip: !text.includes('Clip Skip'),
      hasAdoptStrength: [...dlg.querySelectorAll('button')].some(b => b.textContent.includes('采用推荐权重')),
      twChipCount: chips.length,
      hasAdoptTrigger: [...dlg.querySelectorAll('button')].some(b => b.textContent.includes('采用全部为本地 Trigger')),
      descs,
      hasAbsPath: /D:\\\\|\/mnt\/[a-z]|\/home\/[^ ]*safetensors/i.test(text),
    };
  });
  console.log(`[${tag} edit]`, JSON.stringify(edit, null, 1));
  await shot(page, `fc_${tag}_03_edit_remote`);

  // scroll edit sections to show descriptions
  await page.evaluate(() => {
    const sec = document.querySelector('.edit-sections');
    if (sec) sec.scrollTop = sec.scrollHeight;
  });
  await page.waitForTimeout(400);
  await shot(page, `fc_${tag}_04_edit_bottom`);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });

  const p1 = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  p1.setDefaultTimeout(15000);
  await qaAt(p1, '1440');
  await p1.close();

  const p2 = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  p2.setDefaultTimeout(15000);
  await qaAt(p2, '1920');
  await p2.close();

  await browser.close();
  console.log('QA DONE');
})().catch(e => { console.error('QA FAILED', e); process.exit(1); });
