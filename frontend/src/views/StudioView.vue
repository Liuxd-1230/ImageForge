<template>
  <div class="studio-shell-root">
    <!-- Top Product Header -->
    <header class="studio-top-header">
      <div class="header-left">
        <span class="product-title font-weight-bold">创作台</span>
        <span class="product-sub text-caption text-grey">Anima Studio · M3 Expressive</span>
      </div>

      <!-- Draft Restored Pill Banner -->
      <div v-if="studioStore.draftRestored" class="draft-pill-banner">
        <span class="mdi mdi-history mr-1" />
        <span>已恢复上次未完成的创作</span>
        <button type="button" class="draft-dismiss-btn" title="关闭提示" @click="studioStore.draftRestored = false">
          ×
        </button>
      </div>

      <div class="header-right">
        <!-- Switch to Legacy backup view -->
        <router-link to="/legacy-studio" class="legacy-link-btn" title="查看旧版 3600 行页面供回归比对">
          <span class="mdi mdi-history mr-1" />
          <span>旧版对比</span>
        </router-link>
      </div>
    </header>

    <!-- Main Fluid Tri-Panel Workspace -->
    <div class="tri-panel-workspace">
      <!-- 1. Left: Context & Assets Rail (240~280px / 56px) -->
      <StudioContextRail
        @open-artist-dialog="artistDialog = true"
        @open-rules-dialog="rulesDialog = true"
      />

      <!-- 2. Center: The Forge (520~680px) -->
      <StudioForge />

      <!-- 3. Right: Canvas & Viewport Stage (Remaining width) -->
      <StudioCanvas
        @open-preview="openImagePreview"
        @open-interrupt="interruptDialog = true"
        @open-advanced="advancedDialog = true"
      />
    </div>

    <!-- Modals & Dialogs (Extracted into clean subcomponents) -->
    <ArtistSelectDialog v-model="artistDialog" />
    <RulesSelectDialog v-model="rulesDialog" />
    <ImageDetailDialog v-model="previewDialog" :image-url="previewImageUrl" />
    <InterruptConfirmDialog v-model="interruptDialog" @confirm="studioStore.interruptGeneration()" />
    <AdvancedSettingsDialog v-model="advancedDialog" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useStudioStore } from '../stores/studio'
import { useSettingsStore } from '../stores/settings'
import { useArtistStore } from '../stores/artist'
import { useLoraStore } from '../stores/lora'
import { useRuleStore } from '../stores/rules'
import { useHistoryStore } from '../stores/history'

import StudioContextRail from '../components/studio/StudioContextRail.vue'
import StudioForge from '../components/studio/StudioForge.vue'
import StudioCanvas from '../components/studio/StudioCanvas.vue'

import ArtistSelectDialog from '../components/studio/dialogs/ArtistSelectDialog.vue'
import RulesSelectDialog from '../components/studio/dialogs/RulesSelectDialog.vue'
import ImageDetailDialog from '../components/studio/dialogs/ImageDetailDialog.vue'
import InterruptConfirmDialog from '../components/studio/dialogs/InterruptConfirmDialog.vue'
import AdvancedSettingsDialog from '../components/studio/dialogs/AdvancedSettingsDialog.vue'

const studioStore = useStudioStore()
const settingsStore = useSettingsStore()
const artistStore = useArtistStore()
const loraStore = useLoraStore()
const ruleStore = useRuleStore()
const historyStore = useHistoryStore()

/* Dialog States */
const artistDialog = ref(false)
const rulesDialog = ref(false)
const previewDialog = ref(false)
const previewImageUrl = ref('')
const interruptDialog = ref(false)
const advancedDialog = ref(false)

function openImagePreview(url: string) {
  previewImageUrl.value = url
  previewDialog.value = true
}

/* Global Shortcut: Ctrl + Enter to Generate */
function handleKeyDown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    if (!studioStore.isGenerating) {
      e.preventDefault()
      studioStore.generateImage()
    }
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handleKeyDown)
  await settingsStore.fetchSettings()
  await Promise.all([
    artistStore.fetchArtists(),
    loraStore.fetchLoras(),
    ruleStore.fetchRules(),
    historyStore.fetchHistory(),
  ])
  studioStore.initStudioSettings(settingsStore.settings)
  // 与旧版一致：库数据就绪后同步 LoRA 到创作台 shelf（缺失会导致 shelf 永远为空）
  studioStore.syncLorasFromLibrary(loraStore.loras)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.studio-shell-root {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: rgb(var(--v-theme-background));
  color: rgb(var(--v-theme-on-surface));
  overflow: hidden;
}

.studio-top-header {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgb(var(--v-theme-outline-variant));
  background: rgb(var(--v-theme-surface));
  flex-shrink: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.product-title {
  font-size: 16px;
  letter-spacing: -0.01em;
  color: rgb(var(--v-theme-on-surface));
}

.product-sub {
  font-size: 11px;
}

.draft-pill-banner {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
  font-size: 11.5px;
  font-weight: 600;
  gap: 6px;
}

.draft-dismiss-btn {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 14px;
}

.legacy-link-btn {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 11.5px;
  font-weight: 600;
  text-decoration: none;
  transition: all 140ms ease;
}
.legacy-link-btn:hover {
  background: rgb(var(--v-theme-surface-container-high));
  color: rgb(var(--v-theme-primary));
}

/* Fluid Tri-Panel Workspace with Responsive Breakpoints */
.tri-panel-workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: row;
  overflow: hidden;
  position: relative;
}

/* Responsive Media Queries */
@media (max-width: 1280px) {
  .tri-panel-workspace {
    /* Ensures panels smoothly allocate space on laptops */
  }
}
</style>
