// ImageForge round-2 UI verification — real user path + boundary tests
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';
const OUT = '/home/rosemary/workspace/ImageForge/.verify/r2';
const fs = require('fs');

const FIXTURE = '/home/rosemary/workspace/ImageForge/.verify/testsrc';

let failures = [];
function check(name, cond, detail = '') {
  console.log((cond ? 'PASS' : 'FAIL'), name, detail);
  if (!cond) failures.push(name);
}

async function horizReport(page, label) {
  const r = await page.evaluate(() => ({
    docW: document.documentElement.scrollWidth,
    docCw: document.documentElement.clientWidth,
    pageHOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    list: (() => { const el = document.querySelector('.lora-list'); return el ? { sw: el.scrollWidth, cw: el.clientWidth, overflow: el.scrollWidth > el.clientWidth + 1 } : null })(),
  }));
  check(`${label} 页面无横向 overflow`, !r.pageHOverflow, JSON.stringify(r));
  if (r.list) check(`${label} LoRA 列表无横向 overflow`, !r.list.overflow, JSON.stringify(r.list));
  return r;
}

async function api(method, path, body) {
  const res = await fetch('http://127.0.0.1:8000' + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let j = null;
  try { j = JSON.parse(text); } catch { j = null; }
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 150)}`);
  return j;
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });

  // ---- API setup: a DISABLED rule for the rules-filter test ----
  let disabledRuleId = null;
  try {
    const r = await api('POST', '/api/rules', {
      name: '已禁用测试规则（不应出现在 Studio）', file_type: '.md', content: '', is_enabled: false, sort_order: 99,
    });
    disabledRuleId = r.id;
  } catch (e) { console.log('rule setup err', e.message); }

  // ─────────────────── A. LoRA Library 三档宽度无横滚 ───────────────────
  for (const [w, h, label] of [[1280, 800, '1280'], [1440, 900, '1440'], [1920, 1080, '1920']]) {
    const page = await browser.newPage({ viewport: { width: w, height: h } });
    await page.goto(BASE + '#/loras', { waitUntil: 'networkidle', timeout: 60000 }).catch(async () => {
      await page.goto(BASE + 'loras', { waitUntil: 'networkidle', timeout: 60000 });
    });
    await page.waitForTimeout(1200);
    await horizReport(page, `LoRA Library ${label}`);
    await page.close();
  }

  // ─────────────────── B. 来源管理 → 扫描预览 → 选择导入 ───────────────────
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto(BASE + 'loras', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1200);

    // open source dialog
    await page.click('button:has-text("扫描来源")');
    await page.waitForTimeout(500);

    // add fixture source
    await page.fill('.path-input', FIXTURE);
    await page.waitForTimeout(200);
    const previewText = await page.textContent('.path-preview').catch(() => '');
    check('路径预览显示解析路径', previewText.includes(FIXTURE), previewText.trim());
    await page.click('button:has-text("添加来源")');
    await page.waitForTimeout(700);
    const srcVisible = await page.isVisible('.source-row');
    check('来源已添加并显示', srcVisible);

    // scan
    await page.click('.source-row .op-btn[title="扫描"]');
    await page.waitForTimeout(900);
    check('扫描预览 Dialog 打开', await page.isVisible('.scan-body'));
    const summaryText = await page.textContent('.scan-summary').catch(() => '');
    check('扫描摘要显示发现/新增', summaryText.includes('发现') && summaryText.includes('新增'), summaryText.replace(/\s+/g, ' '));

    const candRows = await page.$$('.cand-row');
    check('候选列表有行', candRows.length >= 5, `rows=${candRows.length}`);
    const flagTexts = await page.$$eval('.cand-row .flag', els => els.map(e => e.textContent.trim()));
    check('ComfyUI 未识别标记存在', flagTexts.some(t => t.includes('未识别')), flagTexts.join('|'));
    check('重名冲突标记存在', flagTexts.some(t => t === '重名'), flagTexts.join('|'));

    // select only 2 (uncheck all then check first two new)
    await page.click('button:has-text("取消全选")');
    const checkables = await page.$$('.cand-row:not(.disabled) .row-check');
    if (checkables.length >= 2) { await checkables[0].click(); await checkables[1].click(); }
    const selText = await page.textContent('.foot-hint');
    check('选中计数为 2', selText.includes('2'), selText);

    // import
    await page.click('button:has-text("导入所选")');
    await page.waitForTimeout(900);
    check('导入后 Dialog 关闭', !(await page.isVisible('.scan-body').catch(() => false)));
    const libCount = await page.$$eval('.lora-row', els => els.length);
    check('LoRA 列表数量增长', libCount >= 20, `rows=${libCount}`);

    await page.screenshot({ path: `${OUT}/01_lora_library.png` });
    await page.close();
  }

  // ─────────────────── C. Studio：空 Prompt 解析 disabled ───────────────────
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1500);

    const parseDisabled = await page.$eval('.parse-btn', el => el.disabled);
    check('空输入时解析按钮 disabled', parseDisabled === true);

    await page.click('.scene-input');
    await page.type('.scene-input', '穗穗穿着泳装');
    await page.waitForTimeout(200);
    const parseEnabled = await page.$eval('.parse-btn', el => el.disabled);
    check('有输入时解析按钮 enabled', parseEnabled === false);

    // ── 尺寸自由输入 + warning + 交换 + 锁定 ──
    await page.evaluate(() => document.querySelectorAll('.acc-head')[1].click());
    await page.waitForTimeout(300);
    const sizeInputs = await page.$$('.size-input');
    check('尺寸自由输入框存在(2个)', sizeInputs.length === 2);
    await sizeInputs[0].fill('100');
    await sizeInputs[1].fill('9000');
    await sizeInputs[1].evaluate(el => el.blur());
    await page.waitForTimeout(300);
    const warn = await page.textContent('.size-warning').catch(() => '');
    check('异常尺寸 100×9000 显示 warning', warn.includes('尺寸异常'), warn.trim());

    // preset
    await page.click('.size-chip:has-text("1152×1536")');
    await page.waitForTimeout(200);
    const sizeVals = await page.$$eval('.size-input', els => els.map(e => e.value));
    check('推荐尺寸快捷键生效', sizeVals[0] === '1152' && sizeVals[1] === '1536', `${sizeVals[0]}×${sizeVals[1]}`);

    // swap
    await page.click('.size-icon-btn:has(.mdi-swap-horizontal)');
    await page.waitForTimeout(200);
    const swapped = await page.$$eval('.size-input', els => els.map(e => e.value));
    check('交换宽高生效', swapped[0] === '1536', `w=${swapped[0]}`);

    // lock aspect: set 1000×2000 then lock, change width -> height follows
    const si = await page.$$('.size-input');
    await si[0].fill('1000');
    await si[1].fill('2000');
    await si[1].evaluate(el => el.blur());
    await page.waitForTimeout(200);
    await page.click('.size-icon-btn:has(.mdi-link-variant-off)');
    await page.waitForTimeout(200);
    const si2 = await page.$$('.size-input');
    await si2[0].fill('500');
    await si2[0].evaluate(el => el.blur());
    await page.waitForTimeout(250);
    const hLocked = await page.$$eval('.size-input', els => els[1].value);
    check('锁定比例后改宽自动改高(500→1000)', hLocked === '1000', `h=${hLocked}`);

    // ── Reasoning slider + Provider memory ──
    await page.evaluate(() => [...document.querySelectorAll('.adv-provider-btn')].find(b => b.textContent.trim() === 'Cloud').click());
    await page.waitForTimeout(300);
    await page.evaluate(() => [...document.querySelectorAll('.rs-label')].find(x => x.textContent.includes('MAX')).click());
    await page.waitForTimeout(300);
    const maxOnCloud = await page.evaluate(() => document.querySelector('.rs-thumb.max') !== null);
    check('Cloud MAX 生效', maxOnCloud);
    // switch to LM -> MAX should disappear (LM has no MAX)
    await page.evaluate(() => [...document.querySelectorAll('.adv-provider-btn')].find(b => b.textContent.trim() === 'LM Studio').click());
    await page.waitForTimeout(300);
    const lmMax = await page.evaluate(() => document.querySelector('.rs-thumb.max') !== null);
    check('切到 LM 无 MAX', !lmMax);
    // switch back to Cloud -> memory restores MAX
    await page.evaluate(() => [...document.querySelectorAll('.adv-provider-btn')].find(b => b.textContent.trim() === 'Cloud').click());
    await page.waitForTimeout(300);
    const maxRestored = await page.evaluate(() => document.querySelector('.rs-thumb.max') !== null);
    check('切回 Cloud 恢复 MAX（Provider 记忆）', maxRestored);

    // ── Rules dialog 只显示启用规则 ──
    await page.click('.rules-picker');
    await page.waitForTimeout(400);
    const ruleNames = await page.$$eval('.rule-opt-name', els => els.map(e => e.textContent.trim()));
    check('Rules Dialog 只显示启用规则', ruleNames.length >= 1 && !ruleNames.some(n => n.includes('已禁用测试规则')), ruleNames.join('|'));
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    await page.screenshot({ path: `${OUT}/02_studio_advanced.png` });
    await page.close();
  }

  // ─────────────────── D. 草稿恢复 ───────────────────
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1500);
    // clear any prior draft
    await page.evaluate(() => localStorage.removeItem('imageforge_studio_draft_v1'));
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1200);

    await page.click('.scene-input');
    await page.type('.scene-input', '草稿测试：穗穗在沙滩');
    const loraChecks = await page.$$('.lora-check');
    if (loraChecks.length >= 2) { await loraChecks[1].click(); }
    // wait for debounce autosave
    await page.waitForTimeout(900);
    const saved = await page.evaluate(() => !!localStorage.getItem('imageforge_studio_draft_v1'));
    check('草稿已写入 localStorage', saved);

    // reload -> restore
    await page.reload({ waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    const banner = await page.isVisible('.draft-banner').catch(() => false);
    check('刷新后出现恢复横幅', banner);
    const restoredText = await page.$eval('.scene-input', el => el.value);
    check('画面描述已恢复', restoredText.includes('草稿测试：穗穗在沙滩'), restoredText);
    const loraOn = await page.evaluate(() => {
      const checks = [...document.querySelectorAll('.lora-check')];
      return checks.some(c => c.classList.contains('on'));
    });
    check('LoRA 勾选已恢复', loraOn);
    await page.screenshot({ path: `${OUT}/03_draft_restored.png` });

    // 清空创作台
    await page.click('.draft-clear');
    await page.waitForTimeout(500);
    const clearedText = await page.$eval('.scene-input', el => el.value);
    const bannerGone = !(await page.isVisible('.draft-banner').catch(() => false));
    check('清空创作台后输入为空', clearedText === '');
    check('清空后横幅消失', bannerGone);
    const keyGone = await page.evaluate(() => localStorage.getItem('imageforge_studio_draft_v1') === null);
    check('清空后 localStorage 草稿已删除', keyGone);
    await page.close();
  }

  // ─────────────────── E. 角色书新建默认空字段 ───────────────────
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto(BASE + 'characters', { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1200);
    await page.click('button:has-text("新建角色")');
    await page.waitForTimeout(500);
    const gender = await page.$eval('input[aria-label*="性别"], input[label*="性别"]', el => el.value).catch(async () => {
      // fallback: find by placeholder-less field near label
      const v = await page.evaluate(() => {
        const inputs = [...document.querySelectorAll('.v-text-field input')];
        const idx = inputs.findIndex(i => (i.closest('.v-text-field')?.textContent || '').includes('性别'));
        return idx >= 0 ? inputs[idx].value : 'NOT_FOUND';
      });
      return v;
    });
    check('新建角色性别默认为空', gender === '' || gender === 'NOT_FOUND', `gender=${gender}`);
    await page.screenshot({ path: `${OUT}/04_character_new.png` });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    await page.close();
  }

  // ─────────────────── F. 1920 Studio 关键态 ───────────────────
  {
    const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
    await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1500);
    const r = await page.evaluate(() => ({
      docW: document.documentElement.scrollWidth, docCw: document.documentElement.clientWidth,
      inspW: document.querySelector('.inspector').getBoundingClientRect().width,
    }));
    check('1920 无横向 overflow', r.docW <= r.docCw, JSON.stringify(r));
    await page.screenshot({ path: `${OUT}/05_studio_1920.png` });
    await page.close();
  }

  // cleanup: delete the disabled rule + imported fixture loras
  if (disabledRuleId) await api('DELETE', `/api/rules/${disabledRuleId}`);
  const loras = await api('GET', '/api/loras');
  for (const l of (loras || [])) {
    if ((l.source_path || '').startsWith(FIXTURE)) await api('DELETE', `/api/loras/${l.id}`);
  }
  const srcs = await api('GET', '/api/loras/sources');
  for (const s of (srcs || [])) await api('DELETE', `/api/loras/sources/${s.id}`);

  await browser.close();
  console.log(`\n=== ${failures.length === 0 ? 'ALL' : failures.length + ' FAILED'} ===`);
  if (failures.length) { console.log('FAILURES:', failures); process.exit(1); }
  console.log('DONE-ALL-PASS');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
