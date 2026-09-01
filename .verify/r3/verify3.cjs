// Round-3 audit UI tests (draft semantics, clear, lock+swap, double-click generate, scan default, resolve preview)
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';
const FIXTURE = '/home/rosemary/workspace/ImageForge/.verify/testsrc';

let failures = [];
function check(name, cond, detail = '') {
  console.log((cond ? 'PASS' : 'FAIL'), name, detail);
  if (!cond) failures.push(name);
}

async function api(method, path, body) {
  const res = await fetch('http://127.0.0.1:8000' + path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let j = null; try { j = JSON.parse(text); } catch { j = null; }
  if (!res.ok) throw new Error(`${res.status} ${text.slice(0, 150)}`);
  return j;
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(20000);

  // ensure fixture dir exists (backend_test cleans it up)
  const fs = require('fs');
  const path = require('path');
  fs.mkdirSync(FIXTURE, { recursive: true });
  for (const rel of ['Anima/foo_style_v1.safetensors', 'bar_boost.safetensors', 'dup_name.safetensors']) {
    const p = path.join(FIXTURE, ...rel.split('/'));
    fs.mkdirSync(path.dirname(p), { recursive: true });
    if (!fs.existsSync(p)) fs.writeFileSync(p, Buffer.from([0, 0, 0, 1]));
  }
  // ensure fixture source exists
  const srcs = await api('GET', '/api/loras/sources');
  if (!srcs.some(s => s.display_path === FIXTURE)) {
    await api('POST', '/api/loras/sources', { display_path: FIXTURE, recursive: true });
  }

  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  // clean start: remove draft + reload
  await page.evaluate(() => localStorage.removeItem('imageforge_studio_draft_v1'));
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);

  // ═══ 1. 草稿恢复（v2 facts/空）+ 改 Safety 不覆盖恢复的 Prompt（审计 P1）═══
  await page.click('.scene-input');
  await page.type('.scene-input', '草稿测试：穗穗在沙滩');
  await page.click('.prompt-textarea');
  await page.type('.prompt-textarea', 'restored-prompt-content');
  await page.waitForTimeout(900); // debounce autosave

  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const banner = await page.isVisible('.draft-banner').catch(() => false);
  check('draft banner after reload', banner);
  const restored = await page.$eval('.scene-input', el => el.value);
  const restoredPrompt = await page.$eval('.prompt-textarea', el => el.value);
  check('scene restored', restored.includes('草稿测试：穗穗在沙滩'));
  check('prompt restored', restoredPrompt.includes('restored-prompt-content'), restoredPrompt);

  // 修改 Safety → 触发 buildPrompt（空 facts，非 force）→ 不得覆盖恢复的 Prompt
  await page.evaluate(() => {
    [...document.querySelectorAll('.safety-seg-btn')].find(b => b.textContent.trim() === 'NSFW').click();
  });
  await page.waitForTimeout(700);
  const afterSafety = await page.$eval('.prompt-textarea', el => el.value);
  check('改 Safety 后恢复的 Prompt 未被空 facts 覆盖', afterSafety.includes('restored-prompt-content'), afterSafety.slice(0, 60));

  // ═══ 2. 清空创作台后语义状态清空（审计 P1）═══
  if (await page.isVisible('.draft-banner').catch(() => false)) {
    await page.click('.draft-clear');
    await page.waitForTimeout(500);
  }
  await page.evaluate(() => document.querySelectorAll('.acc-head')[0].click()); // 解析详情
  await page.waitForTimeout(400);
  const pdEmpty = await page.textContent('.pd-empty').catch(() => '');
  check('clear 后解析详情为空（facts 已清）', pdEmpty.includes('输入描述并解析后'), pdEmpty.trim());

  // ═══ 3. 锁定比例后交换宽高（审计 P1：ratio 需反转）═══
  await page.evaluate(() => document.querySelectorAll('.acc-head')[1].click()); // 高级设置
  await page.waitForTimeout(300);

  // 先确保解锁，再设置 1000×2000 并锁定（ratio = 0.5）
  const lockBtnSel = async () => {
    const on = await page.evaluate(() => !!document.querySelector('.size-icon-btn.on'));
    if (on) { await page.click('.size-icon-btn:has(.mdi-link-variant)'); await page.waitForTimeout(150); }
  };
  await lockBtnSel();
  let si = await page.$$('.size-input');
  await si[0].fill('1000'); await si[1].fill('2000'); await si[1].evaluate(el => el.blur());
  await page.waitForTimeout(200);
  await page.click('.size-icon-btn:has(.mdi-link-variant-off)'); // 锁定 ratio=0.5
  await page.waitForTimeout(200);
  await page.click('.size-icon-btn:has(.mdi-swap-horizontal)');  // swap → 2000×1000，ratio 应翻转为 2
  await page.waitForTimeout(200);
  si = await page.$$('.size-input');
  await si[0].fill('500'); await si[0].evaluate(el => el.blur()); // 宽 500，swap 后 ratio=2 → 高=500/2=250
  await page.waitForTimeout(250);
  const hVals = await page.$$eval('.size-input', els => els.map(e => e.value));
  check('lock+swap 后 ratio 已反转(500→250)', hVals[1] === '250', hVals.join('×'));

  // ═══ 4. 双击 Generate 只提交一次（审计 P1：route 拦截 + 同步双 click）═══
  await page.evaluate(() => localStorage.removeItem('imageforge_studio_draft_v1'));
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.click('.prompt-textarea');
  await page.type('.prompt-textarea', 'double click test prompt');
  await page.waitForTimeout(200);
  let genCount = 0;
  let genDisabledObserved = false;
  await page.route('**/api/comfyui/generate', async route => {
    genCount++;
    // 确认生成期间按钮处于 disabled 状态（并发保护 + UI 禁用双保险）
    genDisabledObserved = genDisabledObserved || (await page.$eval('.generate-btn', el => el.disabled));
    await new Promise(r => setTimeout(r, 1200)); // 慢响应，保持 isGenerating=true
    await route.fulfill({ status: 502, contentType: 'application/json', body: JSON.stringify({ detail: 'mock down' }) });
  });
  // 同步双 click：第一次同步进入 generateImage 并置 isGenerating=true，第二次应被守卫拦截
  await page.evaluate(() => {
    const b = document.querySelector('.generate-btn');
    b.click();
    b.click();
  });
  await page.waitForTimeout(2500);
  check('双击 Generate 仅 1 次提交', genCount === 1, `count=${genCount}`);
  check('生成期间按钮 disabled', genDisabledObserved);

  // ═══ 5. 扫描预览默认 0 选中（审计 P1）═══
  await page.goto(BASE + 'loras', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1500);
  await page.click('button:has-text("扫描来源")');
  await page.waitForTimeout(500);
  await page.click('.source-row .op-btn[title="扫描"]');
  await page.waitForTimeout(900);
  const foot = await page.textContent('.foot-hint');
  const anySelected = await page.$$eval('.cand-row .row-check.on', els => els.length);
  check('扫描预览默认 0 选中', foot.includes('0') && anySelected === 0, `${foot.trim()} selected=${anySelected}`);

  // ═══ 6. 路径预览必须走后端 resolve-path API（审计 P0/P1：前端不自己猜 /mnt）═══
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  let resolveApiCalls = 0;
  let apiResolved = null;
  await page.route('**/api/loras/resolve-path', async route => {
    resolveApiCalls++;
    const body = route.request().postDataJSON();
    const res = await fetch('http://127.0.0.1:8000/api/loras/resolve-path', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const j = await res.json();
    apiResolved = j.resolved_path;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(j) });
  });
  await page.fill('.path-input', 'D:\\Models\\LoRA');
  await page.waitForTimeout(700); // debounce + API
  const resolved = await page.textContent('.pv-path').catch(() => '');
  check('路径预览调用了后端 resolve-path', resolveApiCalls >= 1, `calls=${resolveApiCalls}`);
  check('显示值来自后端(本机为 WSL 故 /mnt/d 正确)', apiResolved !== null && resolved.includes(apiResolved), `api=${apiResolved} ui=${resolved}`);

  await browser.close();

  // cleanup fixture source
  const srcs2 = await api('GET', '/api/loras/sources');
  for (const s of srcs2) {
    if (s.display_path === FIXTURE) await api('DELETE', `/api/loras/sources/${s.id}`);
  }
  const loras = await api('GET', '/api/loras');
  for (const l of loras) {
    if ((l.source_path || '').startsWith(FIXTURE)) await api('DELETE', `/api/loras/${l.id}`);
  }

  console.log(`\n=== ${failures.length === 0 ? 'ALL' : failures.length + ' FAILED'} ===`);
  if (failures.length) { console.log('FAILURES:', failures); process.exit(1); }
  console.log('DONE-ALL-PASS');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
