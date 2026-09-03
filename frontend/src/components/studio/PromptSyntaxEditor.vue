<template>
  <div class="prompt-syntax-editor">
    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-2">
      <div class="d-flex align-center gap-2">
        <span class="editor-title">最终 Prompt (Final Prompt)</span>
        <span v-if="studioStore.isPositivePromptDirty" class="dirty-badge">
          <span class="dirty-dot" />已手动修改
        </span>
      </div>

      <div class="d-flex align-center gap-2">
        <!-- View Toggle (Text vs Read-only Structure) -->
        <div class="view-seg-control">
          <button
            type="button"
            :class="['seg-btn', { on: viewMode === 'text' }]"
            @click="viewMode = 'text'"
          >
            编辑文本
          </button>
          <button
            type="button"
            :class="['seg-btn', { on: viewMode === 'structure' }]"
            @click="viewMode = 'structure'"
          >
            结构概览
          </button>
        </div>

        <button type="button" class="tool-btn" title="重新从事实编译" @click="recompile">
          <span class="mdi mdi-sync" :class="{ 'spin-anim': studioStore.isBuilding }" />
        </button>
        <button type="button" class="tool-btn" title="复制到剪贴板" @click="copyPrompt">
          <span class="mdi mdi-content-copy" />
        </button>
      </div>
    </div>

    <!-- 1. Text Mode (Primary, Level 2 Surface) -->
    <div v-if="viewMode === 'text'" class="editor-surface">
      <textarea
        v-model="studioStore.positivePrompt"
        class="prompt-textarea mono"
        rows="5"
        spellcheck="false"
        placeholder="编译生成的 Positive Prompt 将显示在此处，亦可自由手动微调…"
        @input="studioStore.isPositivePromptDirty = true"
      />
    </div>

    <!-- 2. Read-only Structural Tokens Preview (No bi-directional AST complexity) -->
    <div v-else class="structure-surface">
      <div class="tokens-legend mb-2">
        <span class="leg"><span class="dot quality" />质量词</span>
        <span class="leg"><span class="dot char" />角色词</span>
        <span class="leg"><span class="dot artist" />画师 (@artist)</span>
        <span class="leg"><span class="dot lora" />LoRA</span>
        <span class="leg"><span class="dot nl" />自然语言从句</span>
      </div>
      <div class="tokens-cloud">
        <span
          v-for="(t, i) in parsedTokens"
          :key="i"
          :class="['token-chip mono', t.category]"
        >
          {{ t.text }}
        </span>
      </div>
    </div>

    <!-- 3. Negative Prompt Collapsible Strip -->
    <div class="neg-collapse-block">
      <button
        type="button"
        class="neg-header-btn"
        @click="negOpen = !negOpen"
      >
        <span class="mdi" :class="negOpen ? 'mdi-chevron-down' : 'mdi-chevron-right'" />
        <span class="font-weight-bold">Negative Prompt</span>
        <span v-if="studioStore.isNegativePromptDirty" class="dirty-badge-sub">Modified</span>
        <span class="copy-neg-link" @click.stop="copyNeg">复制</span>
      </button>

      <div v-if="negOpen" class="neg-body-wrap">
        <textarea
          v-model="studioStore.negativePrompt"
          class="neg-textarea mono"
          rows="2"
          spellcheck="false"
          @input="studioStore.isNegativePromptDirty = true"
        />
        <input
          v-model="studioStore.extraNegative"
          type="text"
          class="extra-neg-input mono"
          placeholder="本次临时追加的负面词（如: text, lowres, watermark）"
          @input="studioStore.buildPrompt()"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStudioStore } from '../../stores/studio'

const studioStore = useStudioStore()
const viewMode = ref<'text' | 'structure'>('text')
const negOpen = ref(false)

function recompile() {
  studioStore.buildPrompt(true)
}

function copyPrompt() {
  if (studioStore.positivePrompt) {
    navigator.clipboard.writeText(studioStore.positivePrompt)
  }
}

function copyNeg() {
  if (studioStore.negativePrompt) {
    navigator.clipboard.writeText(studioStore.negativePrompt)
  }
}

interface TokenItem {
  text: string
  category: 'quality' | 'char' | 'artist' | 'lora' | 'nl'
}

const parsedTokens = computed<TokenItem[]>(() => {
  const p = studioStore.positivePrompt || ''
  if (!p.trim()) return []

  // Split comma-separated tokens
  const rawParts = p.split(',').map(s => s.trim()).filter(Boolean)
  return rawParts.map(item => {
    if (item.startsWith('@artist:')) {
      return { text: item, category: 'artist' }
    }
    if (item.startsWith('<lora:')) {
      return { text: item, category: 'lora' }
    }
    if (/masterpiece|best quality|newest|aesthetic|very aesthetic/i.test(item)) {
      return { text: item, category: 'quality' }
    }
    if (item.includes(' ') && item.length > 28) {
      return { text: item, category: 'nl' }
    }
    // Check if matches known entity triggers
    const isChar = studioStore.facts.entities.some(e =>
      (e.canonical_tag && item.includes(e.canonical_tag)) || item.includes(e.name)
    )
    if (isChar) {
      return { text: item, category: 'char' }
    }
    return { text: item, category: 'quality' }
  })
})
</script>

<style scoped>
.prompt-syntax-editor {
  display: flex;
  flex-direction: column;
}

.editor-title {
  font-size: 13px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.dirty-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-warning));
  background: rgba(234, 179, 8, 0.12);
  padding: 1px 6px;
  border-radius: 999px;
}
.dirty-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgb(var(--v-theme-warning));
}

.view-seg-control {
  display: flex;
  background: rgb(var(--v-theme-surface-container));
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
}
.seg-btn {
  border: 0;
  background: transparent;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
}
.seg-btn.on {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-primary));
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.tool-btn {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tool-btn:hover {
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface));
}

.spin-anim {
  animation: spin 1s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }

/* Level 2 Surface: round 16px, surface-container-low */
.editor-surface {
  background: rgb(var(--v-theme-surface-container-low));
  border-radius: 14px;
  padding: 8px 10px;
}

.prompt-textarea {
  width: 100%;
  border: 0;
  background: transparent;
  outline: none;
  font-size: 12.5px;
  line-height: 1.55;
  color: rgb(var(--v-theme-on-surface));
  resize: vertical;
}

.structure-surface {
  background: rgb(var(--v-theme-surface-container-low));
  border-radius: 14px;
  padding: 10px 12px;
  min-height: 100px;
}

.tokens-legend {
  display: flex;
  gap: 10px;
  font-size: 10px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.leg {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.dot.quality { background: #94a3b8; }
.dot.char { background: #a855f7; }
.dot.artist { background: #10b981; }
.dot.lora { background: #ea580c; }
.dot.nl { background: #0b57d0; }

.tokens-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.token-chip {
  display: inline-flex;
  padding: 3px 7px;
  border-radius: 6px;
  font-size: 11px;
}
.token-chip.quality { background: rgba(148, 163, 184, 0.15); color: rgb(var(--v-theme-on-surface)); }
.token-chip.char { background: rgba(168, 85, 247, 0.15); color: #9333ea; font-weight: 600; }
.token-chip.artist { background: rgba(16, 185, 129, 0.15); color: #059669; font-weight: 600; }
.token-chip.lora { background: rgba(234, 88, 12, 0.15); color: #ea580c; font-weight: 600; }
.token-chip.nl { background: rgba(11, 87, 208, 0.12); color: #0b57d0; line-height: 1.4; }

/* Negative Prompt section */
.neg-collapse-block {
  margin-top: 8px;
}

.neg-header-btn {
  border: 0;
  background: transparent;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  padding: 3px 0;
}
.dirty-badge-sub {
  font-size: 9.5px;
  color: rgb(var(--v-theme-warning));
  margin-left: 2px;
}
.copy-neg-link {
  font-size: 10.5px;
  color: rgb(var(--v-theme-primary));
  margin-left: 8px;
}

.neg-body-wrap {
  margin-top: 5px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.neg-textarea {
  width: 100%;
  padding: 6px 10px;
  border-radius: 8px;
  border: 0;
  background: rgb(var(--v-theme-surface-container-low));
  font-size: 11.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  outline: none;
  resize: vertical;
}

.extra-neg-input {
  width: 100%;
  padding: 5px 10px;
  border-radius: 6px;
  border: 0;
  background: rgb(var(--v-theme-surface-container-low));
  font-size: 11px;
  color: rgb(var(--v-theme-on-surface));
  outline: none;
}
</style>
