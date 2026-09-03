<template>
  <div class="studio-forge">
    <!-- Header -->
    <div class="forge-header">
      <div class="d-flex align-center gap-2">
        <span class="forge-title">工坊流水线 (The Forge)</span>
      </div>
      <div class="d-flex align-center gap-2">
        <!-- Preset selector -->
        <select
          v-model="studioStore.selectedPresetId"
          class="preset-select mono"
          @change="onPresetSelect"
        >
          <option :value="null">默认预设 (None)</option>
          <option v-for="p in presetStore.presets" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </div>
    </div>

    <!-- Scrollable Forge Body -->
    <div class="forge-scroll-body">
      <!-- 1. Natural Language Input (Level 2 Surface with attached Parse Button) -->
      <section class="stage-section">
        <div class="d-flex align-center justify-space-between mb-2">
          <div class="d-flex align-center gap-2">
            <span class="stage-badge mono">01</span>
            <span class="stage-title">画面自然语言描述</span>
          </div>
          <!-- Quick testcase chips -->
          <div class="d-flex gap-1">
            <button
              v-for="gc in goldenCases"
              :key="gc.title"
              type="button"
              class="golden-chip"
              @click="loadGoldenCase(gc.text)"
            >
              <span class="mdi mdi-lightning-bolt-outline text-primary mr-1" />
              {{ gc.title }}
            </button>
          </div>
        </div>

        <div class="input-attached-container">
          <textarea
            v-model="studioStore.rawInput"
            class="nl-textarea"
            rows="3"
            placeholder="描述你想生成的画面角色、动作互动、服装或环境细节…"
            @input="studioStore.isSemanticDirty = true"
          />

          <!-- Attached Action Bar inside container (M3 Expressive tactic) -->
          <div class="input-attached-bar">
            <div class="d-flex align-center gap-2 text-caption text-grey">
              <span v-if="studioStore.isSemanticDirty" class="dirty-hint">
                <span class="dirty-dot" />内容已修改
              </span>
              <span v-else>支持日常自然语言描述</span>
            </div>

            <!-- Prominent Tonal Button inside container -->
            <button
              type="button"
              class="parse-attached-btn"
              :class="{ busy: studioStore.isParsing }"
              :disabled="!studioStore.rawInput.trim() || studioStore.isParsing"
              @click="studioStore.parsePrompt()"
            >
              <span class="mdi mdi-creation-outline mr-1" />
              <span>{{ studioStore.isParsing ? '正在抽取语义…' : '语义抽取 (⌘+Enter)' }}</span>
            </button>
          </div>
        </div>
      </section>

      <!-- 2. Semantic Facts Breakdown (Stage 02) -->
      <section class="stage-section">
        <div class="d-flex align-center gap-2 mb-2">
          <span class="stage-badge mono">02</span>
          <span class="stage-title">语义装配线 (Facts Pipeline)</span>
        </div>
        <SemanticPipelineBoard />
      </section>

      <!-- 3. Final Prompt Editor (Stage 03) -->
      <section class="stage-section flex-1">
        <div class="d-flex align-center gap-2 mb-2">
          <span class="stage-badge mono">03</span>
          <span class="stage-title">Anima 最终 Prompt</span>
        </div>
        <PromptSyntaxEditor />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useStudioStore } from '../../stores/studio'
import { usePresetStore } from '../../stores/presets'
import SemanticPipelineBoard from './SemanticPipelineBoard.vue'
import PromptSyntaxEditor from './PromptSyntaxEditor.vue'

const studioStore = useStudioStore()
const presetStore = usePresetStore()

const goldenCases = [
  {
    title: '穗穗与秧秧海滩',
    text: '穗穗穿着浅蓝色系带比基尼泳装，秧秧穿着深蓝色水手海军服，穗穗在阳光沙滩上追逐秧秧。'
  },
  {
    title: '芙莉莲魔法雪原',
    text: '芙莉莲站在雪山顶峰废墟，手持法杖释放出淡金色环形魔力，极光照耀夜空。'
  }
]

function loadGoldenCase(text: string) {
  studioStore.rawInput = text
  studioStore.isSemanticDirty = true
  studioStore.parsePrompt()
}

function onPresetSelect() {
  studioStore.buildPrompt()
}
</script>

<style scoped>
.studio-forge {
  flex: 1;
  min-width: 500px;
  max-width: 680px;
  height: 100%;
  background: rgb(var(--v-theme-background));
  border-right: 1px solid rgb(var(--v-theme-outline-variant));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 4;
}

.forge-header {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgb(var(--v-theme-outline-variant));
  background: rgb(var(--v-theme-surface));
  flex-shrink: 0;
}

.forge-title {
  font-size: 13px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.preset-select {
  padding: 3px 8px;
  background: rgb(var(--v-theme-surface-container-low));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 6px;
  font-size: 11px;
  color: rgb(var(--v-theme-on-surface));
  outline: none;
}

.forge-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 16px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stage-section {
  display: flex;
  flex-direction: column;
}

.stage-badge {
  font-size: 10.5px;
  font-weight: 700;
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-container));
  padding: 1px 5px;
  border-radius: 4px;
}

.stage-title {
  font-size: 12.5px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.golden-chip {
  border: 0;
  background: rgb(var(--v-theme-surface-container));
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 10.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}
.golden-chip:hover {
  background: rgb(var(--v-theme-surface-container-high));
  color: rgb(var(--v-theme-primary));
}

/* Level 2 Surface with attached Parse CTA inside */
.input-attached-container {
  background: rgb(var(--v-theme-surface-container-low));
  border-radius: 16px;
  padding: 10px 12px 8px;
  display: flex;
  flex-direction: column;
  transition: box-shadow 160ms;
}
.input-attached-container:focus-within {
  box-shadow: 0 0 0 1px rgb(var(--v-theme-primary));
}

.nl-textarea {
  width: 100%;
  border: 0;
  background: transparent;
  outline: none;
  font-size: 13.5px;
  line-height: 1.5;
  color: rgb(var(--v-theme-on-surface));
  resize: vertical;
}

.input-attached-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.dirty-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: rgb(var(--v-theme-warning));
  font-weight: 600;
}
.dirty-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgb(var(--v-theme-warning));
}

/* Prominent Tonal Button inside container */
.parse-attached-btn {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  border-radius: 999px;
  border: 0;
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: background-color 140ms;
}
.parse-attached-btn:hover:not(:disabled) {
  background: rgb(var(--v-theme-primary));
  color: white;
}
.parse-attached-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
