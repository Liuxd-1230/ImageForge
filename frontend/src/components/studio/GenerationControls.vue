<template>
  <div class="gen-controls-bar">
    <!-- Left: Seed & Dimensions summary -->
    <div class="left-controls">
      <!-- Seed Strip：m3e segmented（随机/固定）+ tonal action（复用上次） -->
      <div class="seed-control-group">
        <span class="ctrl-label">SEED</span>
        <m3e-segmented-button class="seed-seg" @change="onSeedModeChange">
          <m3e-button-segment value="random" :checked="isRandomSeed" title="每次生成换新随机 Seed">随机</m3e-button-segment>
          <m3e-button-segment value="fixed" :checked="!isRandomSeed" title="锁定当前数值复现比较">固定</m3e-button-segment>
        </m3e-segmented-button>

        <input
          v-model="seedDisplay"
          type="number"
          :disabled="isRandomSeed"
          :placeholder="isRandomSeed ? '每次随机' : '输入 Seed'"
          class="seed-num-input mono"
          @change="commitSeedInput"
        />

        <m3e-button
          variant="tonal"
          class="seed-reuse-btn"
          :disabled="lastSnapshotSeed == null"
          title="使用上一张图片实际使用的 seed"
          @click="useLastSeed"
        >
          <span slot="icon" class="mdi mdi-history" />
          {{ lastSnapshotSeed != null ? `复用 #${lastSnapshotSeed}` : '复用上次' }}
        </m3e-button>
      </div>

      <!-- Quick Resolution and Advanced Settings button -->
      <div class="d-flex align-center gap-2">
        <span class="params-pill mono" @click="emit('open-advanced')">
          <span class="mdi mdi-aspect-ratio mr-1" />
          {{ studioStore.width }}×{{ studioStore.height }} · {{ studioStore.steps }}步 · CFG {{ studioStore.cfg }}
        </span>
        <button
          type="button"
          class="adv-settings-btn"
          title="打开高级模型与尺寸设置"
          @click="emit('open-advanced')"
        >
          <span class="mdi mdi-tune-variant" />
        </button>
      </div>
    </div>

    <!-- Right: Level 1b Oversized Generate CTA (M3 Expressive prominent action) -->
    <div class="right-action">
      <button
        type="button"
        class="oversized-generate-cta"
        :class="{ generating: studioStore.isGenerating }"
        :disabled="studioStore.isGenerating"
        @click="studioStore.generateImage()"
      >
        <span v-if="!studioStore.isGenerating" class="mdi mdi-creation mr-1 text-h6" />
        <span v-else class="mdi mdi-loading spin-anim mr-1 text-h6" />
        <span class="cta-label">
          {{ studioStore.isGenerating ? '渲染采集中…' : '生成图片' }}
        </span>
        <span class="shortcut-tag mono">Ctrl + Enter</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useStudioStore } from '../../stores/studio'

const emit = defineEmits<{
  (e: 'open-advanced'): void
}>()

const studioStore = useStudioStore()

const isRandomSeed = computed(() => studioStore.seed === -1)
const seedDisplay = ref<number | ''>(studioStore.seed === -1 ? '' : studioStore.seed)

watch(() => studioStore.seed, v => {
  seedDisplay.value = v === -1 ? '' : v
})

function setRandomSeed() {
  studioStore.seed = -1
}

function setFixedSeed() {
  if (studioStore.seed === -1) {
    const rolled = studioStore.lastGeneratedSeed != null ? studioStore.lastGeneratedSeed : Math.floor(Math.random() * 1000000000)
    studioStore.seed = rolled
  }
}

/** m3e segmented-button change：随机 = seed -1；固定 = 沿用上次 seed 或新 roll */
function onSeedModeChange(e: Event) {
  const v = (e.target as unknown as { value?: string | readonly string[] | null }).value
  const mode = Array.isArray(v) ? v[0] : v
  if (mode === 'random') setRandomSeed()
  else if (mode === 'fixed') setFixedSeed()
}

function commitSeedInput() {
  const v = Math.round(Number(seedDisplay.value) || 0)
  studioStore.seed = Math.max(0, Math.min(2147483647, v))
}

const lastSnapshotSeed = computed(() => {
  const s = studioStore.lastGenerationSnapshot
  if (s && typeof s.seed === 'number' && s.seed >= 0) return s.seed
  if (studioStore.lastGeneratedSeed != null && studioStore.lastGeneratedSeed >= 0) return studioStore.lastGeneratedSeed
  return null
})

function useLastSeed() {
  if (lastSnapshotSeed.value != null) {
    studioStore.seed = lastSnapshotSeed.value
  }
}
</script>

<style scoped>
.gen-controls-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: rgb(var(--v-theme-surface));
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  flex-shrink: 0;
  gap: 12px;
}

.left-controls {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.seed-control-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.ctrl-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgb(var(--v-theme-on-surface-variant));
}

.seed-seg {
  --m3e-segmented-button-height: 30px;
  --m3e-segmented-button-font-size: 11px;
}

.seed-num-input {
  width: 105px;
  padding: 4px 8px;
  background: rgb(var(--v-theme-surface-container-low));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 6px;
  font-size: 11.5px;
  color: rgb(var(--v-theme-on-surface));
  outline: none;
}
.seed-num-input:focus {
  border-color: rgb(var(--v-theme-primary));
}

.seed-reuse-btn {
  white-space: nowrap;
  flex-shrink: 0;
}

.params-pill {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}
.params-pill:hover {
  background: rgb(var(--v-theme-surface-container-high));
  color: rgb(var(--v-theme-primary));
}

.adv-settings-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 0;
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface-variant));
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.adv-settings-btn:hover {
  background: rgb(var(--v-theme-surface-container-high));
  color: rgb(var(--v-theme-primary));
}

.right-action {
  flex-shrink: 0;
}

/* Level 1b Oversized Generate CTA (M3 Expressive Prominent Pill) */
.oversized-generate-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 48px;
  padding: 0 24px;
  border-radius: 999px;
  border: 0;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: transform var(--if-motion-fast-spatial), box-shadow var(--if-motion-fast-effects), opacity var(--if-motion-fast-effects);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.oversized-generate-cta:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18);
}

.oversized-generate-cta:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.shortcut-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.spin-anim {
  animation: spin 1s linear infinite;
}
@keyframes spin { 100% { transform: rotate(360deg); } }
</style>
