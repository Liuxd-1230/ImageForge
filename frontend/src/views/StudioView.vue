<template>
  <div class="studio-root">
    <!-- ── Slim product header: title + tiny status dots ───────────────── -->
    <header class="studio-header">
      <div class="studio-title">
        <span class="studio-title-main">创作台</span>
        <span class="studio-title-sub">Anima Prompt Studio</span>
      </div>
      <div class="studio-status">
        <span class="status-pill" :title="`${providerLabel} 状态: ${currentProviderStatus}`">
          <span :class="['status-indicator', providerStatusClass]" />
          {{ providerLabel }}
        </span>
        <span class="status-pill" title="ComfyUI 状态">
          <span :class="['status-indicator', comfyStatusClass]" />
          ComfyUI
        </span>
      </div>
    </header>

    <!-- 草稿恢复横幅 -->
    <div v-if="studioStore.draftRestored" class="draft-banner">
      <span class="mdi mdi-history" />
      <span class="draft-banner-text">已恢复上次未完成的创作</span>
      <button type="button" class="draft-clear" @click="clearDraftWorkbench">
        <span class="mdi mdi-broom" />清空创作台
      </button>
      <button type="button" class="draft-dismiss" title="知道了" @click="studioStore.draftRestored = false">
        <span class="mdi mdi-close" />
      </button>
    </div>

    <div class="studio-body">
      <!-- ═════════════════ LEFT: Composer / Inspector ═════════════════ -->
      <aside class="inspector">
        <div class="inspector-scroll">
          <!-- 1 · 画面描述 -->
          <section class="studio-section">
            <h2 class="section-title">画面描述</h2>
            <div class="scene-input-wrap">
              <textarea
                v-model="studioStore.rawInput"
                class="scene-input"
                rows="4"
                placeholder="描述你想生成的画面…"
                @input="studioStore.isSemanticDirty = true"
              />
            </div>
            <div v-if="studioStore.isSemanticDirty" class="dirty-hint">
              <span class="dirty-dot" />内容已修改
            </div>

            <!-- 参考规则 — 紧凑选择行（解析上下文，紧邻输入与解析） -->
            <div class="rules-row">
              <span class="rules-label">解析规则</span>
              <button type="button" class="rules-picker" @click="rulesDialog = true">
                <template v-if="selectedRules.length === 0">
                  <span class="rules-empty">未选择规则</span>
                </template>
                <template v-else>
                  <span v-for="r in selectedRulesPreview" :key="r.id" class="rule-chip">{{ r.name }}</span>
                  <span v-if="selectedRules.length > 2" class="rules-more">+{{ selectedRules.length - 2 }}</span>
                </template>
                <span class="mdi mdi-chevron-down rules-caret" />
              </button>
            </div>

            <button
              type="button"
              class="parse-btn"
              :class="{ 'is-busy': studioStore.isParsing }"
              :disabled="!studioStore.rawInput.trim()"
              @click="studioStore.parsePrompt()"
            >
              <span class="mdi mdi-creation-outline" />
              {{ studioStore.isParsing ? '解析中…' : '解析' }}
            </button>
          </section>

          <!-- 2 · Safety -->
          <section class="studio-section">
            <h2 class="section-title">Safety</h2>
            <div class="safety-seg" :style="safetyIndicatorStyle">
              <div class="safety-indicator" />
              <button
                v-for="opt in safetyOptions"
                :key="opt.value"
                type="button"
                :class="['safety-seg-btn', { active: studioStore.safety === opt.value }]"
                @click="setSafety(opt.value)"
              >
                {{ opt.label }}
              </button>
            </div>
          </section>

          <!-- 3 · Prompt Preset -->
          <section class="studio-section">
            <h2 class="section-title">Prompt Preset</h2>
            <div class="preset-wrap">
              <select
                v-model="studioStore.selectedPresetId"
                class="preset-select"
                @change="onPresetChange(Number(studioStore.selectedPresetId))"
              >
                <option v-for="p in presetStore.presets" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
              <span class="mdi mdi-chevron-down preset-caret" />
            </div>
          </section>

          <!-- 4 · Artist / LoRA -->
          <section class="studio-section">
            <h2 class="section-title">Artist / LoRA</h2>

            <!-- Artist: compact settings row -->
            <div class="artist-row">
              <span class="row-label">画师</span>
              <div class="artist-pills">
                <span v-for="art in studioStore.selectedArtists" :key="art.id" class="artist-pill">
                  <span class="artist-pill-name">{{ art.name }}</span>
                  <button type="button" class="artist-pill-x" title="移除" @click="studioStore.toggleArtist(art)">×</button>
                </span>
                <button type="button" class="artist-add" title="添加画师" @click="artistDialog = true">
                  <span class="mdi mdi-plus" />
                </button>
              </div>
            </div>

            <!-- LoRA: two-line rows, no horizontal scroll ever -->
            <div class="lora-list">
              <div v-for="item in studioStore.activeLoras" :key="item.lora.id" class="lora-row">
                <div class="lora-line1">
                  <button
                    type="button"
                    :class="['lora-check', { on: item.isEnabled }]"
                    :aria-label="item.isEnabled ? '停用 ' + item.lora.name : '启用 ' + item.lora.name"
                    @click="toggleLoraItem(item)"
                  >
                    <span v-if="item.isEnabled" class="mdi mdi-check-bold" />
                  </button>
                  <span :class="['lora-name', { dim: !item.isEnabled }]" :title="item.lora.name">{{ item.lora.name }}</span>
                  <span class="lora-value mono">{{ item.strength.toFixed(2) }}</span>
                </div>
                <div class="lora-line2">
                  <div class="lora-slider" @pointerdown="onLoraPointerDown($event, item)">
                    <div class="slider-track">
                      <div class="slider-fill" :style="{ width: loraPct(item.strength) + '%' }" />
                      <div class="slider-thumb" :style="{ left: loraPct(item.strength) + '%' }" />
                    </div>
                  </div>
                </div>
              </div>
              <div v-if="studioStore.activeLoras.length === 0" class="lora-empty">LoRA 库为空</div>
            </div>
          </section>

          <!-- 5 · Final Prompt -->
          <section class="studio-section">
            <div class="prompt-head">
              <h2 class="section-title">Final Prompt</h2>
              <button
                type="button"
                class="head-text-btn"
                :class="{ 'is-busy': studioStore.isBuilding }"
                title="从当前事实重新编译 Prompt"
                @click="studioStore.buildPrompt(true)"
              >
                <span class="mdi mdi-sync" />
                {{ studioStore.isBuilding ? '编译中…' : '重新编译' }}
              </button>
            </div>

            <div class="prompt-editor">
              <div class="prompt-editor-head">
                <span class="prompt-label">Positive Prompt</span>
                <span v-if="studioStore.isPositivePromptDirty" class="dirty-hint-inline"><span class="dirty-dot" />Modified</span>
                <button type="button" class="copy-btn" @click="copyToClipboard(studioStore.positivePrompt)">复制</button>
              </div>
              <textarea
                v-model="studioStore.positivePrompt"
                class="prompt-textarea"
                rows="6"
                spellcheck="false"
                @input="studioStore.isPositivePromptDirty = true"
              />
            </div>

            <!-- Negative: compact, collapsed by default -->
            <div class="neg-block" :class="{ open: negOpen }">
              <button type="button" class="neg-head" @click="negOpen = !negOpen">
                <span class="mdi neg-caret" :class="negOpen ? 'mdi-chevron-down' : 'mdi-chevron-right'" />
                <span class="neg-title">Negative Prompt</span>
                <span v-if="studioStore.isNegativePromptDirty" class="dirty-hint-inline"><span class="dirty-dot" />Modified</span>
                <span class="neg-copy" @click.stop="copyToClipboard(studioStore.negativePrompt)">复制</span>
              </button>
              <div v-show="negOpen" class="neg-body">
                <textarea
                  v-model="studioStore.negativePrompt"
                  class="prompt-textarea neg"
                  rows="3"
                  spellcheck="false"
                  @input="studioStore.isNegativePromptDirty = true"
                />
                <input
                  v-model="studioStore.extraNegative"
                  class="extra-neg-input"
                  placeholder="本次追加 Negative（如: text, lowres）"
                  @input="studioStore.buildPrompt()"
                />
              </div>
            </div>
          </section>

          <!-- 6 · 解析详情（默认折叠） -->
          <section class="studio-section accordion" :class="{ open: parseOpen }">
            <button type="button" class="acc-head" @click="parseOpen = !parseOpen">
              <span class="mdi acc-caret" :class="parseOpen ? 'mdi-chevron-down' : 'mdi-chevron-right'" />
              <span class="acc-title">解析详情</span>
              <span v-if="hasUnresolvedTrigger" class="acc-warn-dot" title="存在未解析的 Trigger" />
            </button>
            <div v-show="parseOpen" class="acc-body">
              <template v-if="studioStore.facts.entities.length === 0 && studioStore.facts.statements.length === 0">
                <p class="pd-empty">输入描述并解析后，此处将呈现结构化的人物与动作关系。</p>
              </template>
              <template v-else>
                <div v-if="studioStore.facts.entities.length > 0" class="pd-group">
                  <span class="pd-group-label">Entities</span>
                  <div
                    v-for="entity in studioStore.facts.entities"
                    :key="entity.id"
                    :class="['pd-entity', { unresolved: isEntityUnresolved(entity) }]"
                  >
                    <div class="pd-entity-top">
                      <span class="pd-entity-name">{{ entity.name }}</span>
                      <span class="pd-source-badge">{{ sourceLabel(entity) }}</span>
                    </div>

                    <!-- 只突出有问题的人物，给出手动填写入口 -->
                    <div v-if="isEntityUnresolved(entity)" class="pd-trigger-fix">
                      <p class="pd-trigger-hint">未能自动识别该角色的 Trigger，请手动填写：</p>
                      <div class="pd-trigger-fields">
                        <input v-model="entity.canonical_tag" class="pd-trigger-input mono" placeholder="Canonical Tag（如: suisui）" />
                        <input v-model="entity.caption_name" class="pd-trigger-input mono" placeholder="Caption Name（如: Suisui）" />
                        <button
                          type="button"
                          class="pd-trigger-save"
                          :disabled="!entity.canonical_tag || !entity.caption_name"
                          @click="saveEntityTrigger(entity)"
                        >
                          保存
                        </button>
                      </div>
                    </div>
                    <div v-else-if="entity.source === 'model_character'" class="pd-entity-tags">
                      <span class="pd-tag mono">Tag: <b>{{ entity.canonical_tag }}</b></span>
                      <span class="pd-tag mono">Caption: <b>{{ entity.caption_name }}</b></span>
                    </div>
                  </div>
                </div>

                <div v-if="studioStore.facts.statements.length > 0" class="pd-group">
                  <span class="pd-group-label">Statements</span>
                  <div v-for="(s, idx) in studioStore.facts.statements" :key="idx" class="pd-statement">
                    <span class="pd-kind">{{ s.kind }}</span>
                    <span class="pd-st-subj">{{ getEntityName(s.subject) }}</span>
                    <span class="pd-arrow">→</span>
                    <span class="pd-st-text mono">{{ s.text }}</span>
                    <template v-if="s.target">
                      <span class="pd-arrow">→</span>
                      <span class="pd-st-subj">{{ getEntityName(s.target) }}</span>
                    </template>
                    <span v-if="s.facet" class="pd-facet">{{ s.facet }}</span>
                    <span v-if="s.effect" class="pd-facet">{{ s.effect }}</span>
                    <button type="button" class="pd-remove" title="移除该陈述" @click="studioStore.removeStatement(idx)">×</button>
                  </div>
                </div>
              </template>
            </div>
          </section>

          <!-- 7 · 高级设置（默认折叠） -->
          <section class="studio-section accordion" :class="{ open: advOpen }">
            <button type="button" class="acc-head" @click="advOpen = !advOpen">
              <span class="mdi acc-caret" :class="advOpen ? 'mdi-chevron-down' : 'mdi-chevron-right'" />
              <span class="acc-title">高级设置</span>
            </button>
            <div v-show="advOpen" class="acc-body">
              <!-- Provider -->
              <div class="adv-field">
                <span class="param-label">Provider</span>
                <div class="adv-provider">
                  <button
                    type="button"
                    :class="['adv-provider-btn', { active: studioStore.provider === 'lm_studio' }]"
                    @click="onProviderChange('lm_studio')"
                  >
                    LM Studio
                  </button>
                  <button
                    type="button"
                    :class="['adv-provider-btn', { active: studioStore.provider === 'cloud' }]"
                    @click="onProviderChange('cloud')"
                  >
                    Cloud
                  </button>
                </div>
              </div>

              <!-- Model -->
              <div class="adv-field">
                <span class="param-label">Model</span>
                <div class="model-row">
                  <select v-model="studioStore.model" class="param-select model-select">
                    <option v-for="m in currentModelList" :key="m.id" :value="m.id">{{ m.id }}</option>
                  </select>
                  <button type="button" class="icon-btn" title="刷新模型列表" @click="refreshModels">
                    <span class="mdi mdi-refresh" />
                  </button>
                </div>
              </div>

              <!-- 思考强度 Slider（禁止 Select） -->
              <div class="adv-field">
                <div class="reason-label-row">
                  <span class="param-label">思考强度</span>
                  <span class="reason-current" :class="{ max: isMaxReasoning }">
                    <span v-if="isMaxReasoning" class="if-max-gradient rs-max-text">MAX</span>
                    <span v-else>{{ currentRsLabel }}</span>
                  </span>
                </div>
                <div class="reason-slider">
                  <div ref="rsRailRef" class="rs-rail" @pointerdown="onRsPointerDown">
                    <div class="rs-track-line" />
                    <div
                      class="rs-fill"
                      :class="{ 'if-max-track': isMaxReasoning }"
                      :style="{ width: rsPct + '%' }"
                    />
                    <span
                      v-for="i in rsOptions.length"
                      :key="i"
                      class="rs-stop"
                      :class="{ active: i - 1 <= rsIndex, max: isMaxReasoning }"
                      :style="{ left: rsStopLeft(i - 1) }"
                    />
                    <div
                      class="rs-thumb"
                      :class="{ max: isMaxReasoning }"
                      :style="{ left: rsPct + '%' }"
                    >
                      <span v-if="isMaxReasoning" class="rs-thumb-halo if-max-thumb" />
                    </div>
                  </div>
                  <div class="rs-labels">
                    <button
                      v-for="(o, i) in rsOptions"
                      :key="i"
                      type="button"
                      :class="['rs-label', { active: i === rsIndex }]"
                      @click="rsIndex = i"
                    >
                      <template v-if="o.star"><span class="rs-star">✦</span>{{ o.label }}</template>
                      <template v-else-if="o.max"><span class="if-max-gradient rs-max-text">{{ o.label }}</span></template>
                      <template v-else>{{ o.label }}</template>
                    </button>
                  </div>
                </div>
              </div>

              <!-- 尺寸：自由输入 + 推荐快捷键（非白名单） -->
              <div class="adv-field">
                <div class="size-head">
                  <span class="param-label">尺寸</span>
                  <div class="size-presets">
                    <button
                      v-for="p in sizePresets"
                      :key="p.label"
                      type="button"
                      class="size-chip"
                      @click="applySizePreset(p)"
                    >
                      {{ p.label }}
                    </button>
                  </div>
                </div>
                <div class="size-row">
                  <input
                    v-model.number="widthInput"
                    type="number"
                    class="size-input"
                    min="64"
                    max="8192"
                    placeholder="宽"
                    @change="commitWidth"
                  />
                  <span class="size-x">×</span>
                  <input
                    v-model.number="heightInput"
                    type="number"
                    class="size-input"
                    min="64"
                    max="8192"
                    placeholder="高"
                    @change="commitHeight"
                  />
                  <button type="button" class="size-icon-btn" title="交换宽高" @click="swapSize">
                    <span class="mdi mdi-swap-horizontal" />
                  </button>
                  <button
                    type="button"
                    :class="['size-icon-btn', { on: lockAspect }]"
                    :title="lockAspect ? '解锁宽高比' : '锁定宽高比'"
                    @click="toggleLockAspect"
                  >
                    <span class="mdi" :class="lockAspect ? 'mdi-link-variant' : 'mdi-link-variant-off'" />
                  </button>
                </div>
                <p v-if="sizeWarning" class="size-warning">{{ sizeWarning }}</p>
              </div>

              <!-- 步数 / CFG -->
              <div class="param-grid">
                <div class="param-field">
                  <span class="param-label">步数 Steps</span>
                  <input v-model.number="studioStore.steps" type="number" class="param-input" />
                </div>
                <div class="param-field">
                  <span class="param-label">CFG</span>
                  <input v-model.number="studioStore.cfg" type="number" step="0.5" class="param-input" />
                </div>
              </div>

              <!-- Workflow -->
              <div class="adv-field">
                <span class="param-label">Workflow</span>
                <div class="adv-provider wf">
                  <button
                    type="button"
                    :class="['adv-provider-btn', { active: studioStore.workflowMode === 'builtin' }]"
                    @click="studioStore.workflowMode = 'builtin'"
                  >
                    内置 2.9B
                  </button>
                  <button
                    type="button"
                    :class="['adv-provider-btn', { active: studioStore.workflowMode === 'custom' }]"
                    @click="studioStore.workflowMode = 'custom'"
                  >
                    自定义 API
                  </button>
                </div>
                <div v-if="studioStore.workflowMode === 'custom'" class="wf-import">
                  <span class="wf-name mono">{{ studioStore.customWorkflowName || '未选择 API Workflow JSON' }}</span>
                  <div class="wf-actions">
                    <button type="button" class="mini-btn" @click="triggerWorkflowUpload">导入 JSON</button>
                    <button
                      v-if="studioStore.customWorkflowTemplate"
                      type="button"
                      class="mini-btn danger"
                      @click="studioStore.resetToBuiltinWorkflow()"
                    >
                      重置
                    </button>
                  </div>
                  <input
                    ref="workflowFileInput"
                    type="file"
                    accept=".json"
                    style="display: none"
                    @change="handleWorkflowUpload"
                  />
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- Generate — 固定在左栏底部，页面第一 CTA -->
        <div class="generate-bar">
          <button
            type="button"
            class="generate-btn"
            :class="{ generating: studioStore.isGenerating }"
            @click="studioStore.generateImage()"
          >
            <span class="gen-fill" :class="{ indeterminate: studioStore.isGenerating }" />
            <span class="gen-content">
              <span v-if="!studioStore.isGenerating" class="mdi mdi-creation" />
              {{ studioStore.isGenerating ? '生成中…' : '生成图片' }}
            </span>
          </button>
          <div v-if="studioStore.isGenerating" class="gen-status">
            {{ stageLabel }}
          </div>
        </div>
      </aside>

      <!-- ═════════════════ RIGHT: Canvas ═════════════════ -->
      <main class="canvas-pane">
        <div class="canvas-box">
          <template v-if="studioStore.generatedImageUrl">
            <div class="canvas-img-wrap">
              <img
                :src="studioStore.generatedImageUrl"
                class="canvas-img"
                alt="生成结果"
                @click="openImagePreview(studioStore.generatedImageUrl)"
              />
            </div>
            <div class="canvas-toolbar">
              <span class="toolbar-meta mono">
                {{ studioStore.width }} × {{ studioStore.height }} · Seed {{ displaySeed }} · {{ studioStore.steps }} Steps
              </span>
              <span class="toolbar-divider" />
              <button type="button" class="toolbar-btn" @click="openImagePreview(studioStore.generatedImageUrl)">
                <span class="mdi mdi-magnify-plus-outline" />放大
              </button>
              <button type="button" class="toolbar-btn" @click="downloadImage(studioStore.generatedImageUrl)">
                <span class="mdi mdi-tray-arrow-down" />保存
              </button>
              <button type="button" class="toolbar-btn strong" @click="studioStore.generateImage()">
                <span class="mdi mdi-refresh" />再生成
              </button>
            </div>
            <p v-if="errorMessage" class="canvas-error mono">{{ errorMessage }}</p>
          </template>

          <div v-else-if="studioStore.isGenerating" class="canvas-empty">
            <div class="canvas-progress">
              <div class="canvas-progress-track">
                <div class="canvas-progress-fill indeterminate" />
              </div>
            </div>
            <p class="canvas-empty-caption">{{ stageLabel }}</p>
          </div>

          <div v-else class="canvas-empty">
            <div class="canvas-empty-icon">
              <span class="mdi mdi-image-outline" />
            </div>
            <p class="canvas-empty-caption">尚未生成</p>
            <p v-if="errorMessage" class="canvas-error mono">{{ errorMessage }}</p>
          </div>
        </div>
      </main>
    </div>

    <!-- ── 规则多选 Dialog ── -->
    <v-dialog v-model="rulesDialog" max-width="520px">
      <div class="rules-dialog">
        <div class="dialog-head">
          <span class="dialog-title">解析规则</span>
          <button type="button" class="preview-close" @click="rulesDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <p class="rules-dialog-hint">规则将作为解析时的参考上下文。</p>
        <div class="rules-list">
          <button
            v-for="r in enabledRules"
            :key="r.id"
            type="button"
            :class="['rule-opt', { on: studioStore.selectedRuleIds.includes(r.id) }]"
            @click="toggleRule(r.id)"
          >
            <span class="rule-opt-check">
              <span v-if="studioStore.selectedRuleIds.includes(r.id)" class="mdi mdi-check" />
            </span>
            <span class="rule-opt-name">{{ r.name }}</span>
            <span class="rule-opt-type mono">{{ r.file_type }}</span>
          </button>
          <div v-if="enabledRules.length === 0" class="rules-list-empty">暂无启用的规则文件</div>
        </div>
        <div class="dialog-foot">
          <button type="button" class="dialog-done" @click="rulesDialog = false">完成</button>
        </div>
      </div>
    </v-dialog>

    <!-- ── 画师选择 Dialog ── -->
    <v-dialog v-model="artistDialog" max-width="760px" scrollable>
      <div class="artist-dialog">
        <div class="dialog-head">
          <span class="dialog-title">选择画师</span>
          <button type="button" class="preview-close" @click="artistDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <div class="dialog-search">
          <span class="mdi mdi-magnify dialog-search-icon" />
          <input v-model="artistSearchQuery" class="dialog-search-input" placeholder="搜索画师名称、风格或 Tag" />
        </div>
        <div class="artist-grid">
          <button
            v-for="art in filteredArtists"
            :key="art.id"
            type="button"
            :class="['artist-card', { selected: isArtistSelected(art) }]"
            @click="studioStore.toggleArtist(art)"
          >
            <div class="artist-thumb">
              <img v-if="art.preview_url" :src="art.preview_url" class="artist-thumb-img" alt="" />
              <span v-else class="artist-thumb-ph">{{ art.name.charAt(0) }}</span>
              <span v-if="isArtistSelected(art)" class="artist-check"><span class="mdi mdi-check" /></span>
            </div>
            <span class="artist-card-name">{{ art.name }}</span>
            <span class="artist-card-tag mono">{{ art.tags }}</span>
          </button>
          <div v-if="filteredArtists.length === 0" class="artist-empty">没有匹配的画师</div>
        </div>
        <div class="dialog-foot">
          <span class="dialog-foot-hint">{{ studioStore.selectedArtists.length }} 位已选</span>
          <button type="button" class="dialog-done" @click="artistDialog = false">完成</button>
        </div>
      </div>
    </v-dialog>

    <!-- ── 大图预览 Dialog ── -->
    <v-dialog v-model="imagePreviewDialog" max-width="1100px">
      <div class="preview-dialog">
        <div class="dialog-head">
          <span class="dialog-title">渲染画作预览</span>
          <button type="button" class="preview-close" @click="imagePreviewDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <div class="preview-body">
          <img :src="previewImageUrl" class="preview-img" alt="预览" />
        </div>
      </div>
    </v-dialog>

    <!-- ── Snackbar ── -->
    <v-snackbar v-model="snackbar" :timeout="2500" :color="snackbarColor">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useStudioStore, type ActiveLoraItem } from '../stores/studio'
import { usePresetStore } from '../stores/presets'
import { useSettingsStore } from '../stores/settings'
import { useArtistStore } from '../stores/artist'
import { useLoraStore } from '../stores/lora'
import { useRuleStore } from '../stores/rules'
import type { Artist, Entity, SafetyLevel, ReasoningEffort } from '../types'

const studioStore = useStudioStore()
const presetStore = usePresetStore()
const settingsStore = useSettingsStore()
const artistStore = useArtistStore()
const loraStore = useLoraStore()
const ruleStore = useRuleStore()

/* ── UI state ── */
const rulesDialog = ref(false)
const artistDialog = ref(false)
const artistSearchQuery = ref('')
const imagePreviewDialog = ref(false)
const previewImageUrl = ref('')
const parseOpen = ref(false)
const advOpen = ref(false)
const negOpen = ref(false)

/* ── 尺寸自由输入（推荐尺寸只是快捷键，非白名单） ── */
const widthInput = ref<number>(studioStore.width)
const heightInput = ref<number>(studioStore.height)
const lockAspect = ref(false)
let lockedRatio: number | null = null
const sizePresets = [
  { label: '812×1216', w: 812, h: 1216 },
  { label: '1152×1536', w: 1152, h: 1536 },
  { label: '1536×1536', w: 1536, h: 1536 },
]

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('primary')
const workflowFileInput = ref<HTMLInputElement | null>(null)

/* ── Safety segmented control ── */
const safetyOptions: { label: string; value: SafetyLevel }[] = [
  { label: 'Safe', value: 'Safe' },
  { label: 'Sensitive', value: 'Sensitive' },
  { label: 'NSFW', value: 'NSFW' },
  { label: 'Explicit', value: 'Explicit' },
]
const safetyIdx = computed(() => Math.max(0, safetyOptions.findIndex(o => o.value === studioStore.safety)))
const safetyIndicatorStyle = computed(() => ({ '--safety-idx': safetyIdx.value }))

function setSafety(v: SafetyLevel) {
  if (studioStore.safety === v) return
  studioStore.safety = v
  studioStore.buildPrompt()
}

/* ── Reasoning slider（LM Studio / Cloud 两套离散档位） ── */
const rsOptions = computed<{ value: ReasoningEffort; label: string; star?: boolean; max?: boolean }[]>(() =>
  studioStore.provider === 'lm_studio'
    ? [
        { value: 'off', label: '关闭' },
        { value: 'on', label: '自动', star: true },
        { value: 'low', label: '低' },
        { value: 'medium', label: '中' },
        { value: 'high', label: '高' },
      ]
    : [
        { value: 'off', label: '关闭' },
        { value: 'low', label: '低' },
        { value: 'medium', label: '中' },
        { value: 'high', label: '高' },
        { value: 'xhigh', label: '极高' },
        { value: 'max', label: 'MAX', max: true },
      ],
)
const rsIndex = computed({
  get() {
    const i = rsOptions.value.findIndex(o => o.value === studioStore.reasoningEffort)
    return i === -1 ? 0 : i
  },
  set(i: number) {
    const opt = rsOptions.value[Math.min(Math.max(0, i), rsOptions.value.length - 1)]
    studioStore.reasoningEffort = opt.value
  },
})
const rsPct = computed(() =>
  rsOptions.value.length <= 1 ? 0 : (rsIndex.value / (rsOptions.value.length - 1)) * 100,
)
function rsStopLeft(i: number) {
  return `${(i / (rsOptions.value.length - 1)) * 100}%`
}
const currentRsLabel = computed(() => rsOptions.value[rsIndex.value]?.label ?? '关闭')
const isMaxReasoning = computed(
  () => studioStore.provider === 'cloud' && studioStore.reasoningEffort === 'max',
)

const rsRailRef = ref<HTMLElement | null>(null)
function rsIndexFromX(clientX: number) {
  const el = rsRailRef.value
  if (!el) return rsIndex.value
  const rect = el.getBoundingClientRect()
  const n = rsOptions.value.length
  const p = (clientX - rect.left) / rect.width
  return Math.min(n - 1, Math.max(0, Math.round(p * (n - 1))))
}
function onRsPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  e.preventDefault()
  rsIndex.value = rsIndexFromX(e.clientX)
  bindPointerDrag(e, x => { rsIndex.value = rsIndexFromX(x) })
}

/* ── generic pointer drag helper ── */
function bindPointerDrag(e: PointerEvent, onMove: (clientX: number) => void, onUp?: () => void) {
  const move = (ev: PointerEvent) => onMove(ev.clientX)
  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    onUp?.()
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
  onMove(e.clientX)
}

/* ── LoRA（两行式，禁止横向滚动） ── */
function loraPct(strength: number) {
  return ((strength - 0.1) / (1.5 - 0.1)) * 100
}
function loraStrengthFromX(e: PointerEvent, track: HTMLElement) {
  const rect = track.getBoundingClientRect()
  const p = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width))
  return Math.round((0.1 + p * 1.4) / 0.05) * 0.05
}
function onLoraPointerDown(e: PointerEvent, item: ActiveLoraItem) {
  if (e.button !== 0) return
  const track = e.currentTarget as HTMLElement
  e.preventDefault()
  item.strength = Number(loraStrengthFromX(e, track).toFixed(2))
  bindPointerDrag(
    e,
    x => {
      item.strength = Number(loraStrengthFromX({ clientX: x } as PointerEvent, track).toFixed(2))
    },
    () => studioStore.buildPrompt(),
  )
}
function toggleLoraItem(item: ActiveLoraItem) {
  item.isEnabled = !item.isEnabled
  studioStore.buildPrompt()
}

/* ── Rules ── */
const enabledRules = computed(() => ruleStore.rules.filter(r => r.is_enabled))
const selectedRules = computed(() =>
  enabledRules.value.filter(r => studioStore.selectedRuleIds.includes(r.id)),
)
const selectedRulesPreview = computed(() => selectedRules.value.slice(0, 2))
function toggleRule(ruleId: number) {
  const idx = studioStore.selectedRuleIds.indexOf(ruleId)
  if (idx !== -1) {
    studioStore.selectedRuleIds.splice(idx, 1)
  } else {
    studioStore.selectedRuleIds.push(ruleId)
  }
  studioStore.isSemanticDirty = true
}

/* ── Provider / model ── */
const currentModelList = computed(() =>
  studioStore.provider === 'lm_studio' ? settingsStore.lmStudioModels : settingsStore.cloudModels,
)
const currentProviderStatus = computed(() =>
  studioStore.provider === 'lm_studio' ? settingsStore.lmStudioStatus : settingsStore.cloudStatus,
)
const providerLabel = computed(() => (studioStore.provider === 'lm_studio' ? 'LM Studio' : 'Cloud'))
const providerStatusClass = computed(() => {
  const s = currentProviderStatus.value
  return s === 'connected' ? 'online' : s === 'error' ? 'error' : 'offline'
})
const comfyStatusClass = computed(() => {
  const s = settingsStore.comfyStatus
  return s === 'connected' ? 'online' : s === 'error' ? 'error' : 'offline'
})

function onProviderChange(p: 'lm_studio' | 'cloud') {
  const prev = studioStore.provider
  if (prev !== p) {
    // 记住旧 Provider 本次使用的 model + reasoning
    studioStore.providerMemory[prev] = {
      model: studioStore.model,
      reasoning: studioStore.reasoningEffort === 'instruct' ? 'off' : studioStore.reasoningEffort,
    }
  }
  studioStore.provider = p

  const mem = studioStore.providerMemory[p]
  const models = p === 'lm_studio' ? settingsStore.lmStudioModels : settingsStore.cloudModels
  const defModel = p === 'lm_studio'
    ? settingsStore.settings.LM_STUDIO_MODEL
    : settingsStore.settings.CLOUD_MODEL

  if (mem.model && models.some(m => m.id === mem.model)) {
    studioStore.model = mem.model
  } else if (defModel && models.some(m => m.id === defModel)) {
    studioStore.model = defModel
  } else if (models.length > 0) {
    studioStore.model = models[0].id
  } else {
    studioStore.model = ''
  }
  const r = mem.reasoning === 'instruct' ? 'off' : mem.reasoning
  studioStore.reasoningEffort = (['off', 'on', 'low', 'medium', 'high', 'xhigh', 'max'].includes(r) ? r : 'off') as ReasoningEffort
}

async function refreshModels() {
  if (studioStore.provider === 'lm_studio') {
    await settingsStore.checkLMStudioHealth()
  } else {
    await settingsStore.checkCloudHealth()
  }
}

function onPresetChange(presetId: number) {
  studioStore.selectedPresetId = presetId
  studioStore.buildPrompt()
}

/* ── Parse details / unresolved trigger ── */
const hasUnresolvedTrigger = computed(() =>
  studioStore.facts.entities.some(
    e => e.source === 'model_character' && (!e.canonical_tag || !e.caption_name),
  ),
)
watch(hasUnresolvedTrigger, v => {
  if (v) parseOpen.value = true
}, { immediate: true })

function sourceLabel(e: Entity) {
  return e.source === 'user_defined'
    ? '用户角色书'
    : e.source === 'model_character'
      ? '模型角色'
      : '通用人物'
}
function isEntityUnresolved(e: Entity) {
  return e.source === 'model_character' && (!e.canonical_tag || !e.caption_name)
}
function getEntityName(entityId: string | null | undefined): string {
  if (!entityId) return '场景'
  const e = studioStore.facts.entities.find(item => item.id === entityId)
  return e ? e.name : entityId
}

/* ── Canvas helpers ── */
const displaySeed = computed(() =>
  studioStore.seed === -1 || !studioStore.seed ? '随机' : String(studioStore.seed),
)
const stageLabel = computed(() => {
  const s = studioStore.generationStage
  if (s === 'preparing') return '准备工作流…'
  if (s === 'submitted') return '已提交 · ComfyUI 生成中…'
  if (s === 'done') return '生成完成'
  if (s === 'timeout') return '等待超时'
  if (s === 'error') return '生成失败'
  return studioStore.generationMessage || '生成中…'
})
const errorMessage = computed(() => {
  const m = studioStore.generationMessage
  if (!m || studioStore.isGenerating) return ''
  if (m.includes('失败') || m.includes('超时') || m.includes('错误')) return m
  return ''
})

/* ── 尺寸逻辑 ── */
watch(() => studioStore.width, v => { if (widthInput.value !== v) widthInput.value = v })
watch(() => studioStore.height, v => { if (heightInput.value !== v) heightInput.value = v })

const sizeWarning = computed(() => {
  const w = Number(widthInput.value)
  const h = Number(heightInput.value)
  if (!w || !h || w <= 0 || h <= 0) return ''
  if (w < 64 || h < 64 || w > 8192 || h > 8192) return '尺寸超出常见范围（64–8192）'
  const ratio = w / h
  if (ratio < 0.4 || ratio > 2.5) return `尺寸异常：${w}×${h}（比例 ${ratio.toFixed(2)}:1），生成可能失败`
  return ''
})

function commitWidth() {
  const w = Math.round(Number(widthInput.value) || 0)
  const clamped = Math.min(8192, Math.max(64, w))
  studioStore.width = clamped
  widthInput.value = clamped
  if (lockAspect.value && lockedRatio && clamped > 0) {
    const h = Math.round(clamped / lockedRatio)
    const ch = Math.min(8192, Math.max(64, h))
    studioStore.height = ch
    heightInput.value = ch
  }
}
function commitHeight() {
  const h = Math.round(Number(heightInput.value) || 0)
  const clamped = Math.min(8192, Math.max(64, h))
  studioStore.height = clamped
  heightInput.value = clamped
  if (lockAspect.value && lockedRatio && clamped > 0) {
    const w = Math.round(clamped * lockedRatio)
    const cw = Math.min(8192, Math.max(64, w))
    studioStore.width = cw
    widthInput.value = cw
  }
}
function swapSize() {
  const w = studioStore.width
  const h = studioStore.height
  studioStore.width = h
  studioStore.height = w
  widthInput.value = h
  heightInput.value = w
}
function toggleLockAspect() {
  lockAspect.value = !lockAspect.value
  lockedRatio = lockAspect.value ? (studioStore.width / studioStore.height || 1) : null
}
function applySizePreset(p: { w: number; h: number }) {
  studioStore.width = p.w
  studioStore.height = p.h
  widthInput.value = p.w
  heightInput.value = p.h
  if (lockAspect.value) lockedRatio = p.w / p.h
}
function syncSizeFromStore() {
  widthInput.value = studioStore.width
  heightInput.value = studioStore.height
}

/* ── Artists ── */
const filteredArtists = computed(() => {
  let list = artistStore.artists
  if (artistSearchQuery.value) {
    const q = artistSearchQuery.value.toLowerCase()
    list = list.filter(
      a => a.name.toLowerCase().includes(q) || a.tags.toLowerCase().includes(q),
    )
  }
  return list
})
function isArtistSelected(art: Artist): boolean {
  return studioStore.selectedArtists.some(a => a.id === art.id)
}

/* ── Workflow upload ── */
function triggerWorkflowUpload() {
  workflowFileInput.value?.click()
}
function handleWorkflowUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = e.target?.result as string
      const json = JSON.parse(content)
      if (typeof json !== 'object' || json === null) {
        throw new Error('JSON 根节点必须是一个对象')
      }
      const keys = Object.keys(json)
      if (keys.length === 0) {
        throw new Error('工作流 JSON 为空')
      }
      const firstNode = json[keys[0]]
      if (!firstNode || typeof firstNode !== 'object' || !firstNode.class_type) {
        throw new Error('未检测到有效的 ComfyUI API Format 节点结构 (class_type 缺失)')
      }
      studioStore.setWorkflowTemplate(file.name, json)
      snackbarText.value = `已导入工作流: ${file.name}`
      snackbarColor.value = 'success'
      snackbar.value = true
    } catch (err: any) {
      snackbarText.value = `导入工作流失败: ${err.message || err}`
      snackbarColor.value = 'error'
      snackbar.value = true
    }
  }
  reader.readAsText(file)
  target.value = ''
}

/* ── Clipboard / preview / download ── */
function copyToClipboard(text: string) {
  if (!text) return
  const done = () => {
    snackbarText.value = '已复制到剪贴板'
    snackbarColor.value = 'success'
    snackbar.value = true
  }
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(() => fallbackCopy(text, done))
  } else {
    fallbackCopy(text, done)
  }
}
function fallbackCopy(text: string, done: () => void) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  try { document.execCommand('copy') } catch { /* ignore */ }
  document.body.removeChild(ta)
  done()
}
function openImagePreview(url: string) {
  previewImageUrl.value = url
  imagePreviewDialog.value = true
}
function downloadImage(url: string) {
  const link = document.createElement('a')
  link.href = url
  link.download = `ImageForge_Anima_${Date.now()}.png`
  link.click()
}

async function saveEntityTrigger(entity: Entity) {
  try {
    await studioStore.saveEntityTrigger(entity)
    const remainingUnresolved = studioStore.facts.entities.filter(
      e => e.source === 'model_character' && !e.canonical_tag,
    )
    if (remainingUnresolved.length > 0) {
      snackbarText.value = `已保存角色【${entity.name}】映射，仍有 ${remainingUnresolved.length} 个角色未补全`
      snackbarColor.value = 'warning'
    } else {
      snackbarText.value = `已保存角色【${entity.name}】的 Trigger 映射`
      snackbarColor.value = 'success'
    }
    snackbar.value = true
  } catch (err: any) {
    snackbarText.value = `保存 Trigger 失败: ${err.response?.data?.detail || err.message || '网络请求异常'}`
    snackbarColor.value = 'error'
    snackbar.value = true
  }
}

/* ── Mount ── */
onMounted(async () => {
  await Promise.all([
    presetStore.fetchPresets(),
    settingsStore.fetchSettings(),
    artistStore.fetchArtists(),
    loraStore.fetchLoras(),
    ruleStore.fetchRules(),
  ])

  studioStore.initStudioSettings(settingsStore.settings)

  // 草稿恢复（安全容错；需要画师/LoRA 库数据就绪后再应用引用型字段）
  const restored = studioStore.loadDraft()
  studioStore.syncLorasFromLibrary(loraStore.loras)
  studioStore.applyDraftLoraStates()
  studioStore.applyDraftArtistIds(artistStore.artists)

  // 只保留已启用规则的选中项
  const enabledRuleIds = ruleStore.rules.filter(r => r.is_enabled).map(r => r.id)
  studioStore.selectedRuleIds = studioStore.selectedRuleIds.filter(id => enabledRuleIds.includes(id))

  if (!studioStore.selectedPresetId && presetStore.presets.length > 0) {
    const def = presetStore.presets.find(p => p.is_default) || presetStore.presets[0]
    studioStore.selectedPresetId = def.id
  }

  if (!studioStore.model) {
    if (studioStore.provider === 'lm_studio' && settingsStore.lmStudioModels.length > 0) {
      const defModel = settingsStore.settings.LM_STUDIO_MODEL
      studioStore.model = defModel && settingsStore.lmStudioModels.some(m => m.id === defModel)
        ? defModel
        : settingsStore.lmStudioModels[0].id
    } else if (studioStore.provider === 'cloud' && settingsStore.cloudModels.length > 0) {
      const defCloud = settingsStore.settings.CLOUD_MODEL
      studioStore.model = defCloud && settingsStore.cloudModels.some(m => m.id === defCloud)
        ? defCloud
        : settingsStore.cloudModels[0].id
    }
  }

  syncSizeFromStore()

  if (restored) {
    snackbarText.value = '已恢复上次未完成的创作'
    snackbarColor.value = 'primary'
    snackbar.value = true
  }
})

// 草稿 autosave：关键状态变化 debounce 500ms 写入 localStorage
watch(
  () => [
    studioStore.rawInput, studioStore.safety, studioStore.selectedPresetId,
    studioStore.selectedRuleIds, studioStore.selectedArtists, studioStore.activeLoras,
    studioStore.positivePrompt, studioStore.negativePrompt, studioStore.extraNegative,
    studioStore.width, studioStore.height, studioStore.steps, studioStore.cfg, studioStore.seed,
    studioStore.provider, studioStore.model, studioStore.reasoningEffort, studioStore.providerMemory,
  ],
  () => studioStore.scheduleDraftSave(),
  { deep: true },
)

function clearDraftWorkbench() {
  studioStore.clearDraft()
  syncSizeFromStore()
  snackbarText.value = '创作台已清空'
  snackbarColor.value = 'primary'
  snackbar.value = true
}
</script>

<style scoped>
/* 等宽辅助类 */
.mono {
  font-family: var(--font-mono) !important;
}

/* ════════════════════════════════════════════════════════════════════
   Studio 布局骨架 — Canvas-first，页面自身禁止纵向滚动
   ════════════════════════════════════════════════════════════════════ */
.studio-root {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: rgb(var(--v-theme-background));
  color: rgb(var(--v-theme-on-surface));
}

.studio-header {
  flex-shrink: 0;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 28px;
}
.studio-title {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.studio-title-main {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: rgb(var(--v-theme-on-surface));
}
.studio-title-sub {
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  letter-spacing: 0.02em;
}
.studio-status {
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 12.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
}

.studio-body {
  flex: 1;
  min-height: 0;
  display: flex;
}

/* ── 草稿恢复横幅 ── */
.draft-banner {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 28px 14px;
  padding: 10px 14px;
  border-radius: 14px;
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
  font-size: 13px;
  font-weight: 600;
}
.draft-banner-text { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.draft-clear {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 0;
  border-radius: 999px;
  padding: 6px 13px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  font-size: 12.5px;
  font-weight: 650;
  cursor: pointer;
  flex-shrink: 0;
}
.draft-dismiss {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 16px;
  flex-shrink: 0;
}
.draft-dismiss:hover { background: rgba(0, 0, 0, 0.06); }

/* ── 左栏 Inspector：420–460px 稳定宽度、独立滚动、禁止横向滚动 ── */
.inspector {
  width: 444px;
  min-width: 444px;
  max-width: 444px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: rgb(var(--v-theme-surface));
  border-right: 1px solid rgb(var(--v-theme-outline-variant));
}
.inspector-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 22px 26px 28px;
}

.studio-section {
  margin-bottom: 30px;
  min-width: 0;
}
.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: rgb(var(--v-theme-on-surface));
}

/* ── 画面描述 ── */
.scene-input-wrap {
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 16px;
  background: rgb(var(--v-theme-surface-container-low));
  transition: border-color var(--motion-base) var(--motion-emphasized),
    box-shadow var(--motion-base) var(--motion-emphasized);
}
.scene-input-wrap:focus-within {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.14);
}
.scene-input {
  display: block;
  width: 100%;
  min-height: 108px;
  padding: 14px 16px;
  border: 0;
  outline: none;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.6;
  color: rgb(var(--v-theme-on-surface));
  resize: vertical;
}
.scene-input::placeholder {
  color: rgb(var(--v-theme-on-surface-variant));
  opacity: 0.75;
}

.dirty-hint {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 9px;
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.dirty-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  opacity: 0.85;
  flex-shrink: 0;
}
.dirty-hint-inline {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* 参考规则紧凑行 */
.rules-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}
.rules-label {
  flex-shrink: 0;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.rules-picker {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px 7px 12px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 12px;
  background: rgb(var(--v-theme-surface-container-low));
  cursor: pointer;
  font-family: var(--font-sans);
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    background-color var(--motion-fast) var(--motion-emphasized);
}
.rules-picker:hover {
  border-color: rgb(var(--v-theme-outline));
  background: rgb(var(--v-theme-surface-container));
}
.rules-empty {
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.rule-chip {
  max-width: 130px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
  font-size: 12.5px;
  font-weight: 600;
}
.rules-more {
  flex-shrink: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
}
.rules-caret {
  margin-left: auto;
  flex-shrink: 0;
  font-size: 16px;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* 解析按钮 */
.parse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 14px;
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 16px;
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
  font-family: var(--font-sans);
  font-size: 15px;
  font-weight: 650;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized),
    box-shadow var(--motion-fast) var(--motion-emphasized);
}
.parse-btn:hover {
  background: rgb(var(--v-theme-secondary-container));
  box-shadow: 0 2px 10px rgba(var(--v-theme-primary), 0.16);
}
.parse-btn.is-busy {
  opacity: 0.7;
  pointer-events: none;
}
.parse-btn:disabled {
  opacity: 0.45;
  cursor: default;
  box-shadow: none;
}

/* ── Safety segmented control ── */
.safety-seg {
  position: relative;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  padding: 4px;
  border-radius: 14px;
  background: rgb(var(--v-theme-surface-container));
}
.safety-indicator {
  position: absolute;
  top: 4px;
  left: 4px;
  width: calc((100% - 8px - 12px) / 4);
  height: calc(100% - 8px);
  border-radius: 11px;
  background: rgb(var(--v-theme-secondary-container));
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  transform: translateX(calc(var(--safety-idx) * (100% + 4px)));
  transition: transform var(--motion-base) var(--motion-spring);
  pointer-events: none;
}
.safety-seg-btn {
  position: relative;
  z-index: 1;
  padding: 11px 0;
  border: 0;
  border-radius: 11px;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 550;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  transition: color var(--motion-fast) var(--motion-emphasized);
}
.safety-seg-btn.active {
  color: rgb(var(--v-theme-on-secondary-container));
  font-weight: 750;
}

/* ── Prompt Preset ── */
.preset-wrap {
  position: relative;
}
.preset-select {
  width: 100%;
  padding: 12px 38px 12px 14px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 14px;
  background: rgb(var(--v-theme-surface-container-low));
  font-family: var(--font-sans);
  font-size: 14.5px;
  color: rgb(var(--v-theme-on-surface));
  appearance: none;
  cursor: pointer;
  transition: border-color var(--motion-fast) var(--motion-emphasized);
}
.preset-select:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.12);
}
.preset-caret {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* ── Artist ── */
.artist-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}
.row-label {
  flex-shrink: 0;
  padding-top: 9px;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.artist-pills {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.artist-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  padding: 6px 8px 6px 12px;
  border-radius: 999px;
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
  font-size: 13px;
  font-weight: 600;
}
.artist-pill-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.artist-pill-x {
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 15px;
  line-height: 1;
  padding: 0 2px;
  cursor: pointer;
  opacity: 0.75;
}
.artist-pill-x:hover {
  opacity: 1;
}
.artist-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1.5px dashed rgb(var(--v-theme-outline));
  background: transparent;
  color: rgb(var(--v-theme-primary));
  font-size: 16px;
  cursor: pointer;
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    background-color var(--motion-fast) var(--motion-emphasized);
}
.artist-add:hover {
  border-color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-container));
}

/* ── LoRA：两行式，名称 ellipsis，slider 全宽，禁止横向滚动 ── */
.lora-list {
  margin-top: 6px;
  min-width: 0;
}
.lora-row {
  min-width: 0;
  padding: 9px 8px 12px;
  border-radius: 12px;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.lora-row:hover {
  background: rgb(var(--v-theme-surface-container-low));
}
.lora-line1 {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.lora-check {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  border: 2px solid rgb(var(--v-theme-outline));
  background: transparent;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized),
    border-color var(--motion-fast) var(--motion-emphasized);
}
.lora-check.on {
  background: rgb(var(--v-theme-primary));
  border-color: rgb(var(--v-theme-primary));
}
.lora-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 550;
  color: rgb(var(--v-theme-on-surface));
}
.lora-name.dim {
  color: rgb(var(--v-theme-on-surface-variant));
  font-weight: 500;
}
.lora-value {
  flex-shrink: 0;
  min-width: 36px;
  text-align: right;
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.lora-line2 {
  margin-top: 9px;
  padding-left: 32px;
}
.lora-slider {
  width: 100%;
  min-width: 0;
  height: 22px;
  display: flex;
  align-items: center;
  cursor: pointer;
  touch-action: none;
}
.slider-track {
  position: relative;
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container-highest));
}
.slider-fill {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 999px;
  background: rgb(var(--v-theme-primary));
}
.slider-thumb {
  position: absolute;
  top: 50%;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgb(var(--v-theme-surface));
  border: 2px solid rgb(var(--v-theme-primary));
  transform: translate(-50%, -50%);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.16);
  pointer-events: none;
}
.lora-empty {
  padding: 16px 0 6px;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* ── Final Prompt ── */
.prompt-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.head-text-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-primary));
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 10px;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.head-text-btn:hover {
  background: rgb(var(--v-theme-primary-container));
}
.head-text-btn.is-busy {
  opacity: 0.65;
}

.prompt-editor {
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 16px;
  background: rgb(var(--v-theme-surface-container-low));
  overflow: hidden;
  transition: border-color var(--motion-base) var(--motion-emphasized),
    box-shadow var(--motion-base) var(--motion-emphasized);
}
.prompt-editor:focus-within {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.14);
}
.prompt-editor-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 2px 16px;
}
.prompt-label {
  font-size: 12.5px;
  font-weight: 650;
  letter-spacing: 0.02em;
  color: rgb(var(--v-theme-on-surface-variant));
}
.copy-btn {
  margin-left: auto;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-primary));
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 650;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.copy-btn:hover {
  background: rgb(var(--v-theme-primary-container));
}
.prompt-textarea {
  display: block;
  width: 100%;
  min-height: 158px;
  padding: 8px 16px 14px;
  border: 0;
  outline: none;
  background: transparent;
  resize: vertical;
  font-family: var(--font-mono);
  font-size: 14px;
  line-height: 1.6;
  color: rgb(var(--v-theme-on-surface));
}

/* Negative 折叠 */
.neg-block {
  margin-top: 10px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 14px;
  overflow: hidden;
  transition: border-color var(--motion-fast) var(--motion-emphasized);
}
.neg-block:focus-within {
  border-color: rgb(var(--v-theme-outline));
}
.neg-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 11px 14px;
  border: 0;
  background: transparent;
  cursor: pointer;
  font-family: var(--font-sans);
}
.neg-caret {
  font-size: 16px;
  color: rgb(var(--v-theme-on-surface-variant));
  transition: transform var(--motion-base) var(--motion-spring);
}
.neg-title {
  font-size: 13.5px;
  font-weight: 650;
  color: rgb(var(--v-theme-on-surface-variant));
}
.neg-copy {
  margin-left: auto;
  font-size: 12.5px;
  font-weight: 650;
  color: rgb(var(--v-theme-primary));
  padding: 4px 8px;
  border-radius: 8px;
}
.neg-copy:hover {
  background: rgb(var(--v-theme-primary-container));
}
.neg-body {
  padding: 2px 14px 14px;
}
.prompt-textarea.neg {
  min-height: 84px;
  padding: 10px 12px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 10px;
  background: rgb(var(--v-theme-surface-container));
}
.extra-neg-input {
  margin-top: 8px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 10px;
  background: rgb(var(--v-theme-surface-container));
  font-family: var(--font-sans);
  font-size: 13.5px;
  color: rgb(var(--v-theme-on-surface));
  box-sizing: border-box;
}
.extra-neg-input:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
}

/* ── 折叠面板（解析详情 / 高级设置） ── */
.accordion {
  border-radius: 16px;
  background: rgb(var(--v-theme-surface-container-low));
  overflow: hidden;
  transition: background-color var(--motion-base) var(--motion-emphasized);
}
.acc-head {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 14px 16px;
  border: 0;
  background: transparent;
  cursor: pointer;
  font-family: var(--font-sans);
}
.acc-caret {
  font-size: 17px;
  color: rgb(var(--v-theme-on-surface-variant));
  transition: transform var(--motion-base) var(--motion-spring);
}
.acc-title {
  font-size: 14.5px;
  font-weight: 650;
  color: rgb(var(--v-theme-on-surface));
}
.acc-warn-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgb(var(--v-theme-error));
  flex-shrink: 0;
}
.acc-body {
  padding: 2px 16px 18px;
}

/* 解析详情内容 */
.pd-empty {
  margin: 6px 0 10px;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.pd-group {
  margin-bottom: 14px;
}
.pd-group-label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgb(var(--v-theme-on-surface-variant));
}
.pd-entity {
  padding: 11px 12px;
  margin-bottom: 8px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 12px;
  background: rgb(var(--v-theme-surface));
}
.pd-entity.unresolved {
  border-color: rgb(var(--v-theme-error));
  background: rgb(var(--v-theme-error-container));
}
.pd-entity-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.pd-entity-name {
  font-size: 14px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}
.pd-source-badge {
  flex-shrink: 0;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 11.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
}
.pd-entity-tags {
  display: flex;
  gap: 12px;
  margin-top: 7px;
  font-size: 12px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.pd-entity-tags b {
  color: rgb(var(--v-theme-primary));
  font-weight: 650;
}
.pd-trigger-fix {
  margin-top: 9px;
  padding-top: 9px;
  border-top: 1px solid rgba(var(--v-theme-error), 0.35);
}
.pd-trigger-hint {
  margin: 0 0 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}
.pd-trigger-fields {
  display: flex;
  gap: 6px;
}
.pd-trigger-input {
  flex: 1;
  min-width: 0;
  padding: 9px 10px;
  border: 1px solid rgba(var(--v-theme-error), 0.45);
  border-radius: 9px;
  background: rgb(var(--v-theme-surface));
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface));
}
.pd-trigger-input:focus {
  outline: none;
  border-color: rgb(var(--v-theme-error));
}
.pd-trigger-save {
  flex-shrink: 0;
  padding: 9px 14px;
  border: 0;
  border-radius: 9px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
}
.pd-trigger-save:disabled {
  opacity: 0.45;
  cursor: default;
}
.pd-statement {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 10px;
  margin-bottom: 6px;
  border-radius: 10px;
  background: rgb(var(--v-theme-surface));
  font-size: 12.5px;
}
.pd-kind {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgb(var(--v-theme-on-surface-variant));
}
.pd-st-subj {
  font-weight: 650;
  color: rgb(var(--v-theme-on-surface));
}
.pd-arrow {
  color: rgb(var(--v-theme-outline));
}
.pd-st-text {
  color: rgb(var(--v-theme-on-surface));
}
.pd-facet {
  flex-shrink: 0;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgb(var(--v-theme-secondary-container));
  font-size: 11px;
  font-weight: 650;
  color: rgb(var(--v-theme-on-secondary-container));
}
.pd-remove {
  margin-left: auto;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 15px;
  cursor: pointer;
  padding: 0 4px;
  flex-shrink: 0;
}

/* ── 高级设置内容 ── */
.adv-field {
  margin-bottom: 16px;
}
.param-label {
  display: block;
  margin-bottom: 7px;
  font-size: 12.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
}
.adv-provider {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border-radius: 12px;
  background: rgb(var(--v-theme-surface-container));
}
.adv-provider.wf {
  grid-template-columns: 1.2fr 1fr;
}
.adv-provider-btn {
  padding: 9px 0;
  border: 0;
  border-radius: 9px;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 13.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized),
    color var(--motion-fast) var(--motion-emphasized),
    box-shadow var(--motion-fast) var(--motion-emphasized);
}
.adv-provider-btn.active {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.model-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.model-select {
  flex: 1;
  min-width: 0;
}
.icon-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 10px;
  background: rgb(var(--v-theme-surface-container-low));
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  transition: color var(--motion-fast) var(--motion-emphasized);
}
.icon-btn:hover {
  color: rgb(var(--v-theme-primary));
}

/* 思考强度 Slider */
.reason-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.reason-current {
  font-size: 13px;
  font-weight: 650;
  color: rgb(var(--v-theme-on-surface));
}
.reason-slider {
  padding: 6px 2px 0;
}
.rs-rail {
  position: relative;
  height: 26px;
  margin: 0 11px;
  cursor: pointer;
  touch-action: none;
}
.rs-track-line {
  position: absolute;
  left: 0;
  right: 0;
  top: 50%;
  height: 6px;
  transform: translateY(-50%);
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container-highest));
}
/* 离散档位 step stops */
.rs-stop {
  position: absolute;
  top: 50%;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: rgb(var(--v-theme-surface));
  border: 2px solid rgb(var(--v-theme-surface-container-highest));
  pointer-events: none;
  transition: border-color var(--motion-fast) var(--motion-emphasized);
}
.rs-stop.active {
  border-color: rgb(var(--v-theme-primary));
}
.rs-stop.max {
  border-color: #7c4dff;
}
.rs-fill {
  position: absolute;
  left: 0;
  top: 50%;
  height: 6px;
  transform: translateY(-50%);
  border-radius: 999px;
  background: rgb(var(--v-theme-primary));
}
.rs-thumb {
  position: absolute;
  top: 50%;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: rgb(var(--v-theme-surface));
  border: 2.5px solid rgb(var(--v-theme-primary));
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    box-shadow var(--motion-fast) var(--motion-emphasized);
  pointer-events: none;
}
/* MAX 专属：紫蓝 / cyan halo · 柔和 neon glow · 极轻微 breathing（呼吸放在光晕层，避免破坏 thumb 定位） */
.rs-thumb.max {
  border-color: #7c4dff;
  box-shadow: 0 0 0 6px rgba(124, 77, 255, 0.16), 0 0 18px 4px rgba(53, 207, 255, 0.38);
}
.rs-thumb-halo {
  position: absolute;
  inset: -9px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(53, 207, 255, 0.3) 0%, rgba(255, 79, 186, 0.14) 45%, transparent 70%);
  pointer-events: none;
}
.rs-labels {
  display: flex;
  margin: 4px 11px 0;
}
.rs-label {
  flex: 1;
  text-align: center;
  border: 0;
  background: transparent;
  padding: 5px 2px;
  border-radius: 8px;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 550;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  transition: color var(--motion-fast) var(--motion-emphasized);
}
.rs-label.active {
  color: rgb(var(--v-theme-on-surface));
  font-weight: 750;
}
.rs-star {
  color: rgb(var(--v-theme-tertiary));
  margin-right: 1px;
}
.rs-max-text {
  font-weight: 800;
  letter-spacing: 0.02em;
}

/* 参数网格 */
.param-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 16px;
}
.param-field {
  min-width: 0;
}
.param-select,
.param-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 10px;
  background: rgb(var(--v-theme-surface-container));
  font-family: var(--font-sans);
  font-size: 14px;
  color: rgb(var(--v-theme-on-surface));
  appearance: none;
}
.param-select:focus,
.param-input:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.12);
}

/* ── 尺寸自由输入 ── */
.size-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 7px;
}
.size-head .param-label { margin-bottom: 0; }
.size-presets { display: flex; gap: 6px; }
.size-chip {
  padding: 5px 10px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  font-family: var(--font-sans);
  font-size: 11.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    color var(--motion-fast) var(--motion-emphasized);
}
.size-chip:hover {
  border-color: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-primary));
}
.size-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.size-input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 10px;
  background: rgb(var(--v-theme-surface-container));
  font-family: var(--font-sans);
  font-size: 14px;
  color: rgb(var(--v-theme-on-surface));
}
.size-input:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.12);
}
.size-x { color: rgb(var(--v-theme-on-surface-variant)); }
.size-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 10px;
  background: rgb(var(--v-theme-surface-container-low));
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  font-size: 16px;
  flex-shrink: 0;
}
.size-icon-btn.on {
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
  border-color: transparent;
}
.size-warning {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--v-theme-warning));
}
.wf-import {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px dashed rgb(var(--v-theme-outline));
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.wf-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.wf-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.mini-btn {
  padding: 7px 12px;
  border: 0;
  border-radius: 9px;
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 650;
  cursor: pointer;
}
.mini-btn.danger {
  background: rgb(var(--v-theme-error-container));
  color: rgb(var(--v-theme-error));
}

/* ── Generate 固定栏 ── */
.generate-bar {
  flex-shrink: 0;
  padding: 14px 26px 18px;
  background: rgb(var(--v-theme-surface));
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
}
.generate-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 56px;
  border: none;
  border-radius: 24px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  font-family: var(--font-sans);
  font-size: 16px;
  font-weight: 750;
  letter-spacing: 0.01em;
  cursor: pointer;
  overflow: hidden;
  box-shadow: 0 6px 18px rgba(var(--v-theme-primary), 0.3);
  transition: background-color var(--motion-base) var(--motion-emphasized),
    border-radius var(--motion-base) var(--motion-emphasized),
    box-shadow var(--motion-base) var(--motion-emphasized);
}
.generate-btn:hover {
  background: rgb(var(--v-theme-primary-darken-1));
}
.generate-btn.generating {
  border-radius: 22px;
  box-shadow: 0 4px 14px rgba(var(--v-theme-primary), 0.22);
}
.gen-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0;
}
/* indeterminate：柔和的扫光，绝不展示假百分比 */
.gen-fill.indeterminate {
  width: 100%;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0) 0%, rgba(255, 255, 255, 0.32) 50%, rgba(255, 255, 255, 0) 100%);
  background-size: 200% 100%;
  animation: if-gen-sweep 1.4s linear infinite;
}
@keyframes if-gen-sweep {
  from { background-position: 200% 0; }
  to { background-position: -200% 0; }
}
.gen-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 9px;
}
.gen-status {
  margin-top: 9px;
  text-align: center;
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* ════════════════════════════════════════════════════════════════════
   右侧 Canvas — 页面最强视觉焦点
   ════════════════════════════════════════════════════════════════════ */
.canvas-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 20px 24px 24px;
}
.canvas-box {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px;
  border-radius: 28px;
  background: rgb(var(--v-theme-surface-container-low));
  overflow: hidden;
  position: relative;
}
.canvas-empty {
  text-align: center;
  max-width: 100%;
}
.canvas-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 74px;
  height: 74px;
  margin: 0 auto 18px;
  border-radius: 24px;
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 34px;
}
.canvas-empty-caption {
  margin: 0;
  font-size: 14px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.canvas-error {
  margin: 14px auto 0;
  max-width: 520px;
  font-size: 12.5px;
  line-height: 1.5;
  color: rgb(var(--v-theme-error));
}
.canvas-progress {
  width: min(360px, 80%);
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.canvas-progress-track {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container-highest));
  overflow: hidden;
}
.canvas-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: rgb(var(--v-theme-primary));
  transition: width 400ms ease;
}
.canvas-progress-fill.indeterminate {
  width: 40%;
  background: linear-gradient(90deg, transparent, rgb(var(--v-theme-primary)), transparent);
  background-size: 200% 100%;
  animation: if-progress-sweep 1.3s ease-in-out infinite;
}
@keyframes if-progress-sweep {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(320%); }
}
.canvas-progress-text {
  font-size: 12.5px;
  font-weight: 700;
  color: rgb(var(--v-theme-primary));
}

.canvas-img-wrap {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.canvas-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 16px;
  cursor: zoom-in;
  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.16);
}
.canvas-toolbar {
  flex-shrink: 0;
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px 6px 18px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 999px;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  max-width: 100%;
}
.toolbar-meta {
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  white-space: nowrap;
}
.toolbar-divider {
  width: 1px;
  height: 18px;
  margin: 0 8px;
  background: rgb(var(--v-theme-outline-variant));
  flex-shrink: 0;
}
.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: transparent;
  border-radius: 999px;
  padding: 8px 12px;
  font-family: var(--font-sans);
  font-size: 13.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
  white-space: nowrap;
}
.toolbar-btn:hover {
  background: rgb(var(--v-theme-surface-container));
}
.toolbar-btn.strong {
  color: rgb(var(--v-theme-primary));
}

/* ═══════════════════ Dialog 公共 ═══════════════════ */
.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 12px;
}
.dialog-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: rgb(var(--v-theme-on-surface));
}
.preview-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 18px;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.preview-close:hover {
  background: rgb(var(--v-theme-surface-container));
}
.dialog-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px 24px 20px;
}
.dialog-foot-hint {
  margin-right: auto;
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.dialog-done {
  padding: 11px 24px;
  border: 0;
  border-radius: 999px;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.dialog-done:hover {
  background: rgb(var(--v-theme-primary-darken-1));
}

/* 规则 Dialog */
.rules-dialog,
.artist-dialog,
.preview-dialog {
  background: rgb(var(--v-theme-surface));
  border-radius: 24px;
  overflow: hidden;
}
.rules-dialog-hint {
  margin: 0;
  padding: 0 24px 12px;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.rules-list {
  max-height: 52vh;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 16px;
}
.rule-opt {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 12px;
  margin-bottom: 6px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 12px;
  background: rgb(var(--v-theme-surface-container-low));
  cursor: pointer;
  font-family: var(--font-sans);
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    background-color var(--motion-fast) var(--motion-emphasized);
}
.rule-opt.on {
  border-color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-container));
}
.rule-opt-check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  border: 2px solid rgb(var(--v-theme-outline));
  color: #fff;
  font-size: 13px;
  flex-shrink: 0;
}
.rule-opt.on .rule-opt-check {
  background: rgb(var(--v-theme-primary));
  border-color: rgb(var(--v-theme-primary));
}
.rule-opt-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  text-align: left;
}
.rule-opt-type {
  flex-shrink: 0;
  font-size: 12px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.rules-list-empty {
  padding: 20px 0;
  text-align: center;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* 画师 Dialog */
.dialog-search {
  position: relative;
  margin: 0 24px 14px;
}
.dialog-search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 18px;
}
.dialog-search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 12px 14px 12px 42px;
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 14px;
  background: rgb(var(--v-theme-surface-container-low));
  font-family: var(--font-sans);
  font-size: 14.5px;
  color: rgb(var(--v-theme-on-surface));
}
.dialog-search-input:focus {
  outline: none;
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.14);
}
.artist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  max-height: 46vh;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 2px 24px 4px;
}
.artist-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 16px;
  background: rgb(var(--v-theme-surface-container-low));
  cursor: pointer;
  font-family: var(--font-sans);
  text-align: left;
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    background-color var(--motion-fast) var(--motion-emphasized);
}
.artist-card:hover {
  border-color: rgb(var(--v-theme-outline));
}
.artist-card.selected {
  border-color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-container));
}
.artist-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 12px;
  overflow: hidden;
  background: rgb(var(--v-theme-surface-container));
  display: flex;
  align-items: center;
  justify-content: center;
}
.artist-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.artist-thumb-ph {
  font-size: 34px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface-variant));
}
.artist-check {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  color: #fff;
  font-size: 14px;
}
.artist-card-name {
  font-size: 14px;
  font-weight: 650;
  color: rgb(var(--v-theme-on-surface));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}
.artist-card-tag {
  font-size: 12px;
  color: rgb(var(--v-theme-primary));
}
.artist-empty {
  grid-column: 1 / -1;
  padding: 30px 0;
  text-align: center;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* 大图预览 Dialog */
.preview-body {
  padding: 16px;
  background: #0e0d12;
  text-align: center;
  max-height: 82vh;
  overflow: hidden;
}
.preview-img {
  max-width: 100%;
  max-height: 76vh;
  object-fit: contain;
  border-radius: 12px;
}
</style>
