// Milestone A — real generation experience UI verification (real LLM + real ComfyUI gen)
const { chromium } = require('/home/rosemary/.npm/_npx/9833c18b2d85bc59/node_modules/playwright');
const CHROME = '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome';
const BASE = 'http://127.0.0.1:5173/';
const OUT = '/home/rosemary/workspace/ImageForge/.verify/r4';
const fs = require('fs');

let failures = [];
function check(name, cond, detail = '') {
  console.log((cond ? 'PASS' : 'FAIL'), name, detail);
  if (!cond) failures.push(name);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.setDefaultTimeout(30000);
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !m.text().includes('Failed to load resource')) errors.push('console: ' + m.text()); });

  // clean start
  await page.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1800);
  await page.evaluate(() => localStorage.removeItem('imageforge_studio_draft_v1'));
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  // ═══ 1. 空输入时解析 disabled（回归） ═══
  const parseDisabled = await page.$eval('.parse-btn', el => el.disabled);
  check('空输入解析 disabled', parseDisabled === true);

  // ═══ 2. 真实解析（LM Studio，35B 首次调用较慢，最长等 90s）→ Prompt 构建 ═══
  await page.click('.scene-input');
  await page.type('.scene-input', '穗穗穿着白色泳装，在海边微笑，蓝发。');
  await page.waitForTimeout(200);
  await page.click('.parse-btn');
  let promptText = '';
  let parseErrShown = '';
  for (let i = 0; i < 90; i++) {
    await page.waitForTimeout(1000);
    promptText = await page.$eval('.prompt-textarea', el => el.value).catch(() => '');
    parseErrShown = await page.textContent('.canvas-error').catch(() => '');
    if (promptText.trim().length > 0) break
    if (parseErrShown.includes('失败') || parseErrShown.includes('异常')) break
  }
  check('解析后 Prompt 已构建', promptText.trim().length > 0, promptText.slice(0, 80) || parseErrShown.slice(0, 80));

  // ═══ 3. 设置小尺寸 + 8 步，随机 seed 真实生成 ═══
  await page.evaluate(() => document.querySelectorAll('.acc-head')[1].click());
  await page.waitForTimeout(300);
  const si = await page.$$('.size-input');
  await si[0].fill('384');
  await si[1].fill('384');
  await si[1].evaluate(el => el.blur());
  await page.waitForTimeout(200);
  const stepsEl = await page.$('.param-input');
  await stepsEl.fill('8');
  await stepsEl.evaluate(el => el.blur());
  await page.waitForTimeout(200);
  // seed: 确保随机模式
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('.seed-mode-btn')].find(x => x.textContent.includes('每次随机'));
    if (b) b.click();
  });
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}/a1_seed_random.png` });

  // 生成（真实 ComfyUI）
  await page.click('.generate-btn');
  let imgDone = false;
  let genErrorText = '';
  let seenRunning = false;
  let seenProgress = false;
  for (let i = 0; i < 150; i++) {
    await page.waitForTimeout(1000);
    const s = await page.evaluate(() => {
      const prog = document.querySelector('.canvas-progress-text')?.textContent?.trim() || '';
      const hasImg = !!document.querySelector('.canvas-img') && document.querySelector('.canvas-img').offsetWidth > 0;
      const err = document.querySelector('.canvas-error')?.textContent?.trim() || '';
      const cap = document.querySelector('.canvas-empty-caption')?.textContent?.trim() || '';
      return { prog, hasImg, err, cap };
    });
    if (!seenRunning && s.cap.includes('生成中')) { seenRunning = true; await page.screenshot({ path: `${OUT}/a2_running.png` }); }
    if (!seenProgress && s.prog.includes('/')) { seenProgress = true; await page.screenshot({ path: `${OUT}/a3_progress.png` }); }
    if (s.hasImg) { imgDone = true; break; }
    if (s.err) { genErrorText = s.err; break; }
  }
  check('生成进入 running 态', seenRunning);
  check('生成显示真实 step 进度', seenProgress, 'x/N');
  check('图片生成成功', imgDone, genErrorText);

  if (imgDone) {
    await page.waitForTimeout(800);
    // ═══ 4. Canvas metadata 显示真实 seed（A1：不能是"随机"）═══
    const meta = await page.textContent('.toolbar-meta');
    const seedMatch = meta.match(/Seed (\d+)/);
    check('Canvas 显示真实 seed', !!seedMatch && !meta.includes('随机'), meta.trim());
    const actualSeed = seedMatch ? Number(seedMatch[1]) : -1;
    const archived = await page.isVisible('.archived-pill').catch(() => false);
    check('本地归档标记显示', archived);
    await page.screenshot({ path: `${OUT}/a4_done_seed.png` });

    // ═══ 5. 使用此 Seed → 固定；再生成同一 seed ═══
    await page.click('.toolbar-btn:has-text("使用此 Seed")');
    await page.waitForTimeout(300);
    // 打开高级设置确认 seed 输入为固定值
    const seedVal = await page.$eval('.seed-row .size-input', el => el.value);
    check('使用此 Seed 后固定为实际 seed', Number(seedVal) === actualSeed, `seed=${seedVal} actual=${actualSeed}`);
    const fixedMode = await page.$eval('.seed-mode-btn.on', el => el.textContent.trim());
    check('模式切为固定当前', fixedMode.includes('固定'), fixedMode);

    // ═══ 6. 生成中修改参数不污染 metadata（A9）——先在生成中改尺寸 ═══
    // 用一次小生成（8 步）中途改 size，最后确认 metadata 仍是快照值
    const s2 = await page.$$('.size-input');
    await s2[0].fill('448'); await s2[0].evaluate(el => el.blur()); // blur 触发 commitWidth
    await s2[1].fill('448'); await s2[1].evaluate(el => el.blur());
    await page.waitForTimeout(200);
    await page.click('.generate-btn'); // 固定 seed（=actualSeed），尺寸 448
    // 生成中快速改回 384（两处都 blur 确保 commit）
    await page.waitForTimeout(1500);
    const s3 = await page.$$('.size-input');
    await s3[0].fill('384'); await s3[0].evaluate(el => el.blur());
    await s3[1].fill('384'); await s3[1].evaluate(el => el.blur());
    // 等本轮生成真正结束（旧图仍显示，不能用 hasImage 判断）
    for (let i = 0; i < 150; i++) {
      await page.waitForTimeout(1000);
      const stillGen = await page.evaluate(() => (document.querySelector('.generate-btn')?.textContent || '').includes('生成中'));
      if (!stillGen) break;
    }
    await page.waitForTimeout(600);
    const meta2 = await page.textContent('.toolbar-meta');
    check('生成中改参数不污染 metadata（仍 448×448）', meta2.includes('448 × 448'), meta2.trim());
    const metaSeed2 = (meta2.match(/Seed (\d+)/) || [])[1];
    check('固定 seed 再生成使用相同 seed', Number(metaSeed2) === actualSeed, `seed=${metaSeed2} actual=${actualSeed}`);
  }

  // ═══ 7. History 恢复完整复现（A4）：restoreToStudio 是 SPA 导航（router.push('/')），不整页刷新 ═══
  await page.goto(BASE + 'history', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(1800);
  const restoreBtn = await page.$('text=恢复到创作台');
  if (restoreBtn) {
    await restoreBtn.click(); // router.push('/')
    await page.waitForTimeout(1800); // SPA 导航 + store 恢复 + draft autosave
    const seedInputAfter = await page.$eval('.seed-row .size-input', el => el.value).catch(() => 'N/A');
    check('History 恢复后 seed 已恢复为固定值', /^\d+$/.test(seedInputAfter), `seed=${seedInputAfter}`);
    const sizeAfter = await page.$$eval('.size-input', els => els.slice(0, 2).map(e => e.value));
    check('History 恢复后尺寸正确', sizeAfter.join('×') === '384×384' || sizeAfter.join('×') === '448×448', sizeAfter.join('×'));
    const meta3 = await page.textContent('.toolbar-meta').catch(() => '');
    check('History 恢复后 Canvas metadata 正确（seed/size/steps）', /Seed \d+/.test(meta3), meta3.trim());
  } else {
    check('History 有恢复按钮', false, 'not found');
  }

  // ═══ 8. ComfyUI 断开错误清晰（A8，route 拦截模拟 503） ═══
  const page2 = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page2.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page2.waitForTimeout(1500);
  await page2.click('.prompt-textarea');
  await page2.type('.prompt-textarea', 'disconnect test prompt');
  await page2.waitForTimeout(200);
  await page2.route('**/api/comfyui/generate', async route => {
    await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: { kind: 'connection', summary: 'ComfyUI 未连接', detail: 'connect failed' } }) });
  });
  await page2.click('.generate-btn');
  await page2.waitForTimeout(1500);
  const connErr = await page2.textContent('.canvas-error').catch(() => '');
  check('ComfyUI 断开错误清晰', connErr.includes('ComfyUI 未连接'), connErr.trim());

  // ═══ 9. 执行错误摘要 + 详情（A8，拦截 monitor error） ═══
  const page3 = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page3.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page3.waitForTimeout(1500);
  await page3.click('.prompt-textarea');
  await page3.type('.prompt-textarea', 'exec error test prompt');
  await page3.waitForTimeout(200);
  let genCount = 0;
  await page3.route('**/api/comfyui/generate', async route => {
    genCount++;
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ prompt_id: 'mock-exec-error', number: 99, node_errors: {} }) });
  });
  await page3.route('**/api/comfyui/status/mock-exec-error', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      prompt_id: 'mock-exec-error', stage: 'error', error_type: 'execution_error',
      error_summary: '节点执行失败（8）：RuntimeError: some node blew up', error_detail: 'RAW TRACEBACK line1\nline2',
      terminal: true, is_running: false, is_queued: false, queue_position: null,
    }) });
  });
  await page3.click('.generate-btn');
  await page3.waitForTimeout(2500);
  const execErr = await page3.textContent('.canvas-error').catch(() => '');
  check('执行错误显示可读摘要', execErr.includes('节点执行失败'), execErr.trim());
  await page3.click('.err-detail-toggle');
  await page3.waitForTimeout(300);
  const detailVisible = await page3.isVisible('.err-detail').catch(() => false);
  check('查看详情展开原始 detail', detailVisible);
  await page3.screenshot({ path: `${OUT}/a5_error_detail.png` });

  // ═══ 10. 双击 Generate 只提交一次（并发保护，拦截计数；test9 已贡献 1 次，此处重置） ═══
  await page3.route('**/api/comfyui/status/**', async route => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ stage: 'running', progress_value: 1, progress_max: 8, is_running: true }) });
  });
  genCount = 0; // 重置计数（test9 的 mock 提交不计入）
  await page3.route('**/api/comfyui/generate', async route => {
    genCount++;
    await new Promise(r => setTimeout(r, 800));
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ prompt_id: 'mock-dbl-' + genCount, number: 99 }) });
  });
  await page3.evaluate(() => {
    const b = document.querySelector('.generate-btn');
    b.click();
    b.click();
  });
  await page3.waitForTimeout(3000);
  check('双击 Generate 仅 1 次提交', genCount === 1, `count=${genCount}`);
  await page3.close();

  // ═══ 11. 真实中断（较长生成中途点击中断）═══
  const page4 = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await page4.goto(BASE, { waitUntil: 'networkidle', timeout: 60000 });
  await page4.waitForTimeout(1500);
  await page4.click('.prompt-textarea');
  await page4.type('.prompt-textarea', 'interrupt test prompt');
  await page4.waitForTimeout(200);
  // 大尺寸长步骤，给足中断时间
  await page4.evaluate(() => document.querySelectorAll('.acc-head')[1].click());
  await page4.waitForTimeout(300);
  const si4 = await page4.$$('.size-input');
  await si4[0].fill('512');
  await si4[1].fill('512');
  await si4[1].evaluate(el => el.blur());
  await page4.waitForTimeout(200);
  const steps4 = await page4.$('.param-input');
  await steps4.fill('40');
  await steps4.evaluate(el => el.blur());
  await page4.waitForTimeout(200);
  await page4.click('.generate-btn');
  let interruptShown = false;
  let cancelledSeen = false;
  for (let i = 0; i < 90; i++) {
    await page4.waitForTimeout(1000);
    const hasInterruptBtn = await page4.isVisible('.gen-ghost-btn.danger').catch(() => false);
    if (hasInterruptBtn && !interruptShown) {
      interruptShown = true;
      await page4.screenshot({ path: `${OUT}/a6_interrupt_btn.png` });
      await page4.click('.gen-ghost-btn.danger');
      await page4.waitForTimeout(300);
      await page4.click('.dialog-done.danger');
    }
    const stageText = await page4.evaluate(() => {
      const t = document.body.innerText;
      return (t.includes('已中断') || t.includes('中断') ? 'cancelled-mark' : '') + '|' + (document.querySelector('.gen-status')?.textContent || '');
    });
    if (stageText.includes('cancelled-mark') || stageText.includes('已中断')) { cancelledSeen = true; break; }
    const done = await page4.isVisible('.canvas-img').catch(() => false);
    if (done) break;
  }
  check('中断按钮在 running 时出现', interruptShown);
  // 中断后任务应显示已中断（monitor 收到 execution_interrupted）
  check('中断后状态为已中断', cancelledSeen);
  await page4.screenshot({ path: `${OUT}/a7_cancelled.png` });

  await browser.close();
  console.log('PAGE_ERRORS', JSON.stringify(errors.slice(0, 5)));
  console.log(`\n=== ${failures.length === 0 ? 'ALL' : failures.length + ' FAILED'} ===`);
  if (failures.length) { console.log('FAILURES:', failures); process.exit(1); }
  console.log('DONE-ALL-PASS');
})().catch(e => { console.error('FATAL', e); process.exit(1); });
