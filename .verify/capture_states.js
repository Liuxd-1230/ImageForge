import { chromium } from 'playwright-core';
import fs from 'fs';
import path from 'path';

const outDir = '/home/rosemary/.gemini/antigravity-cli/brain/9fd1bb14-ccfb-4f20-a1b7-85f47669c993/screenshots';
fs.mkdirSync(outDir, { recursive: true });

async function run() {
  const browser = await chromium.launch({
    executablePath: '/home/rosemary/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1
  });

  const page = await context.newPage();

  console.log('1. Loading Studio Empty State (1440x900)...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(outDir, '01_1440_empty.png') });

  console.log('2. Triggering Parse (Golden case & Facts)...');
  await page.evaluate(() => {
    const store = window.$pinia?._s?.get('studio');
    if (store) {
      store.rawInput = '穗穗穿着浅蓝色系带比基尼泳装，秧秧穿着深蓝色水手海军服，穗穗在阳光沙滩上追逐秧秧。';
      store.isParsing = false;
      store.isSemanticDirty = false;
      store.facts = {
        entities: [
          { id: 'c1', name: '穗穗', source: 'user_defined', canonical_tag: 'suisui' },
          { id: 'c2', name: '秧秧', source: 'model_character', canonical_tag: 'yangyang_(wuthering_waves)' }
        ],
        statements: [
          { kind: 'attribute', subject: 'c1', text: 'wearing light blue string bikini' },
          { kind: 'attribute', subject: 'c2', text: 'wearing dark navy sailor suit' },
          { kind: 'relation', subject: 'c1', target: 'c2', text: 'chasing' },
          { kind: 'scene', subject: null, target: null, text: 'sunny beach, ocean background' }
        ]
      };
      store.positivePrompt = 'masterpiece, best quality, newest, 2girls, suisui, wearing light blue string bikini, yangyang_(wuthering_waves), wearing dark navy sailor suit, suisui chasing yangyang, sunny beach, ocean, sunlight, aesthetic';
      store.negativePrompt = 'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry';
    }
  });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '02_1440_parsed.png') });

  console.log('3. Triggering Active Assets (Artist, LoRA & Character)...');
  await page.evaluate(() => {
    const store = window.$pinia?._s?.get('studio');
    const charStore = window.$pinia?._s?.get('character');
    if (charStore) {
      charStore.characters = [
        { id: 1, name: '穗穗', category: '自设角色 (OC)', extra_description: '浅蓝色系带比基尼泳装, 双马尾' },
        { id: 2, name: '露娜', category: '自设角色 (OC)', extra_description: '白发红瞳, 哥特萝莉长裙' }
      ];
    }
    if (store) {
      store.selectedArtists = [
        { id: 1, name: 'Anmi', tags: '@artist:anmi', category: '画师', is_favorite: true, is_custom: false }
      ];
      store.activeLoras = [
        {
          lora: { id: 101, name: 'swimsuit_enhancer_v2', filename: 'swimsuit_enhancer.safetensors', trigger_words: 'swimsuit', default_strength: 0.8, is_favorite: true, category: '服装', is_valid_file: true },
          isEnabled: true,
          strength: 0.85
        },
        {
          lora: { id: 102, name: 'flat_color_style', filename: 'flat_color.safetensors', trigger_words: 'flat color', default_strength: 0.6, is_favorite: false, category: '风格', is_valid_file: true },
          isEnabled: false,
          strength: 0.6
        }
      ];
    }
  });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '03_1440_assets_active.png') });

  console.log('4. Generating State (Simulating Progress)...');
  await page.evaluate(() => {
    // We can directly mutate the active studio store through Pinia
    const store = window.$pinia?._s?.get('studio');
    if (store) {
      store.isGenerating = true;
      store.generationStage = 'running';
      store.generationProgressValue = 8;
      store.generationProgressMax = 12;
      store.generationMessage = '正在进行第 8/12 步采样…';
    }
  });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '04_1440_generating.png') });

  console.log('5. Generated State (Visual Hero image rendered)...');
  await page.evaluate(() => {
    const store = window.$pinia?._s?.get('studio');
    if (store) {
      store.isGenerating = false;
      store.generationStage = 'done';
      // Use an anime aesthetic sample placeholder image data url or sample
      store.generatedImageUrl = 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=1024&q=80';
    }
  });
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(outDir, '05_1440_generated.png') });

  console.log('6. 1920x1080 Viewport (Empty & Generated)...');
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '06_1920_generated.png') });

  // Reset to empty on 1920
  await page.evaluate(() => {
    const store = window.$pinia?._s?.get('studio');
    if (store) {
      store.generatedImageUrl = null;
      store.rawInput = '';
      store.facts = { entities: [], statements: [] };
    }
  });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '07_1920_empty.png') });

  console.log('7. <1280 Compact Mini Rail...');
  await page.setViewportSize({ width: 1180, height: 800 });
  // Click collapse button on context rail
  const collapseBtn = page.locator('.collapse-toggle-btn');
  if (await collapseBtn.count() > 0) {
    await collapseBtn.click();
  }
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(outDir, '08_1180_minirail.png') });

  await browser.close();
  console.log('All screenshots captured successfully!');
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
