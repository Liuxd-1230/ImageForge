<template>
  <div class="gen-controls-bar">
    <!-- Left: Seed & Dimensions summary -->
    <div class="left-controls">
      <!-- Seed Strip -->
      <div class="seed-control-group">
        <span class="ctrl-label">SEED</span>
        <div class="seed-seg">
          <button
            type="button"
            :class="['seed-tab', { active: isRandomSeed }]"
            title="每次生成换新随机 Seed"
            @click="setRandomSeed"
          >
            随机
          </button>
          <button
            type="button"
            :class="['seed-tab', { active: !isRandomSeed }]"
            title="锁定当前数值复现比较"
            @click="setFixedSeed"
          >
            固定
          </button>
        </div>

        <input
          v-model="seedDisplay"
          type="number"
          :disabled="isRandomSeed"
          :placeholder="isRandomSeed ? '每次随机' : '输入 Seed'"
          class="seed-num-input mono"
          @change="commitSeedInput"
        />

        <button
          type="button"
          class="seed-reuse-btn"
          :disabled="lastSnapshotSeed == null"
          title="使用上一张图片实际使用的 seed"
          @click="useLastSeed"
        >
          <span class="mdi mdi-history mr-1" />
          <span>{{ lastSnapshotSeed != null ? `复用上次 #${lastSnapshotSeed}` : '复用上次' }}</span>
        </button>
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
  display: flex;
  background: rgb(var(--v-theme-surface-container));
  border-radius: 6px;
  padding: 2px;
  gap: 2px;
}

.seed-tab {
  border: 0;
  background: transparent;
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
}
.seed-tab.active {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-primary));
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
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
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-primary));
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}
.seed-reuse-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
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
  transition: all 160ms cubic-bezier(0.2, 0, 0, 1);
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
