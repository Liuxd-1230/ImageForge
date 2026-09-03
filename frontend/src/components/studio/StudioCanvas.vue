<template>
  <main class="studio-canvas-pane">
    <!-- Top Telemetry Status Line -->
    <div class="canvas-telemetry-header">
      <div class="d-flex align-center gap-2">
        <span :class="['status-indicator', comfyStatusClass]" />
        <span class="font-weight-bold text-caption text-on-surface">ComfyUI {{ comfyStatusText }}</span>
        <span class="telemetry-chip mono text-truncate" :title="studioStore.unetName">
          {{ studioStore.unetName }}
        </span>
      </div>

      <div class="d-flex align-center gap-2">
        <span v-if="canvasMeta" class="meta-snippet mono">
          {{ canvasMeta }}
        </span>
      </div>
    </div>

    <!-- Viewport Stage: Visual Hero (Level 1a) -->
    <div class="viewport-stage-wrap">
      <!-- 2:3 Hero Container -->
      <div class="canvas-stage-box">
        <!-- Floating Tonal HUD Toolbar (Constraint 2: Material tonal floating, no glassmorphism) -->
        <div v-if="studioStore.generatedImageUrl" class="floating-tonal-hud">
          <button type="button" class="hud-item-btn" title="查看高清大图" @click="emit('open-preview', studioStore.generatedImageUrl)">
            <span class="mdi mdi-fullscreen" />
          </button>
          <button type="button" class="hud-item-btn" title="导出下载" @click="downloadImage(studioStore.generatedImageUrl)">
            <span class="mdi mdi-tray-arrow-down" />
          </button>
          <button
            v-if="lastSnapshotSeed != null"
            type="button"
            class="hud-item-btn"
            title="固定使用当前图片的 seed"
            @click="useLastSeed"
          >
            <span class="mdi mdi-pin-outline" />
          </button>
        </div>

        <!-- Rendered Image -->
        <div v-if="studioStore.generatedImageUrl" class="artwork-display-wrap">
          <img
            :src="studioStore.generatedImageUrl"
            class="artwork-img"
            alt="Generated Result"
            @click="emit('open-preview', studioStore.generatedImageUrl)"
          />
        </div>

        <!-- Generating Active Progress Overlay：wavy circular = 主进度（真实 step），
             unknown 阶段用 m3e-loading-indicator，绝不伪造百分比 -->
        <div v-if="studioStore.isGenerating" class="generating-progress-overlay">
          <div class="gen-tonal-card">
            <div class="progress-hero">
              <m3e-circular-progress-indicator
                v-if="realProgress"
                variant="wavy"
                :value="studioStore.generationProgressValue"
                :max="studioStore.generationProgressMax"
                class="gen-circular"
                aria-label="生成进度"
              />
              <m3e-loading-indicator v-else class="gen-loading" aria-label="等待中" />
              <div v-if="realProgress" class="progress-center mono">{{ progressPct }}%</div>
            </div>
            <div class="text-center">
              <div class="font-weight-bold text-body-2 text-on-surface">{{ stageLabel }}</div>
              <div class="text-caption text-on-surface-variant mono mt-1">
                {{ progressStepText }}
              </div>
            </div>

            <div class="d-flex justify-center gap-2 mt-3">
              <button type="button" class="gen-ghost-action" @click="studioStore.stopWaiting()">
                停止等待
              </button>
              <button
                v-if="studioStore.generationIsRunning"
                type="button"
                class="gen-ghost-action danger"
                @click="emit('open-interrupt')"
              >
                中断生成
              </button>
            </div>
          </div>
        </div>

        <!-- Empty Canvas State (Clean, quiet M3 containment) -->
        <div v-else-if="!studioStore.generatedImageUrl" class="canvas-empty-state">
          <div class="empty-icon-ring">
            <span class="mdi mdi-image-outline text-h4 text-outline" />
          </div>
          <div class="font-weight-bold text-subtitle-2 text-on-surface mt-2">画布已就绪</div>
          <div class="text-caption text-on-surface-variant mt-1 text-center">
            在左侧输入画面，点击「生成图片」开始创作
          </div>
          <div v-if="studioStore.generationError" class="error-msg-box mt-3">
            <span class="mdi mdi-alert-circle text-error mr-1" />
            <span>{{ studioStore.generationError.summary }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom Generation Controls (Level 1b Oversized CTA) -->
    <GenerationControls @open-advanced="emit('open-advanced')" />

    <!-- Bottom Filmstrip -->
    <StudioFilmstrip />
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useStudioStore } from '../../stores/studio'
import { useSettingsStore } from '../../stores/settings'
import GenerationControls from './GenerationControls.vue'
import StudioFilmstrip from './StudioFilmstrip.vue'

const emit = defineEmits<{
  (e: 'open-preview', url: string): void
  (e: 'open-interrupt'): void
  (e: 'open-advanced'): void
}>()

const studioStore = useStudioStore()
const settingsStore = useSettingsStore()

const comfyStatusText = computed(() => {
  if (studioStore.isGenerating) return '生成中'
  if (settingsStore.comfyStatus === 'connected') return '已连接'
  if (settingsStore.comfyStatus === 'error') return '连接异常'
  return '未连接'
})

const comfyStatusClass = computed(() => {
  if (studioStore.isGenerating) return 'busy'
  if (settingsStore.comfyStatus === 'connected') return 'online'
  if (settingsStore.comfyStatus === 'error') return 'error'
  return 'offline'
})

const canvasMeta = computed(() => {
  const snap = studioStore.activeGenerationSnapshot || studioStore.lastGenerationSnapshot
  if (!snap) return ''
  return `${snap.width}×${snap.height} · ${snap.steps}步 · CFG ${snap.cfg} · Seed ${snap.seed}`
})

const realProgress = computed(() => {
  return studioStore.generationProgressValue != null &&
         studioStore.generationProgressMax != null &&
         studioStore.generationProgressMax > 0
})

const progressPct = computed(() => {
  if (!realProgress.value) return 0
  return Math.min(100, Math.round((studioStore.generationProgressValue! / studioStore.generationProgressMax!) * 100))
})

const progressStepText = computed(() => {
  if (realProgress.value) {
    return `${studioStore.generationProgressValue} / ${studioStore.generationProgressMax} steps (${progressPct.value}%)`
  }
  return studioStore.generationMessage || '正在等待 ComfyUI 调度…'
})

const stageLabel = computed(() => {
  const map: Record<string, string> = {
    idle: '就绪',
    preparing: '准备任务…',
    queued: '排队中…',
    running: '采样计算中…',
    saving: '保存图片…',
    done: '生成完成',
    timeout: '等待超时',
    error: '生成失败',
    cancelled: '已取消',
  }
  return map[studioStore.generationStage] || '渲染中…'
})

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

function downloadImage(url: string) {
  const a = document.createElement('a')
  a.href = url
  a.download = `imageforge_${Date.now()}.png`
  a.click()
}
</script>

<style scoped>
.studio-canvas-pane {
  flex: 1.2;
  min-width: 440px;
  height: 100%;
  background: rgb(var(--v-theme-surface));
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.canvas-telemetry-header {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgb(var(--v-theme-outline-variant));
  flex-shrink: 0;
}

.telemetry-chip {
  font-size: 10.5px;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface-variant));
  max-width: 180px;
}

.meta-snippet {
  font-size: 11px;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* Viewport Stage: Visual Hero (Level 1a) */
.viewport-stage-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(var(--v-theme-surface-container-lowest));
  position: relative;
  overflow: hidden;
}

/* 2:3 Hero Container */
.canvas-stage-box {
  position: relative;
  height: 100%;
  aspect-ratio: 2 / 3;
  max-width: 100%;
  border-radius: 18px;
  overflow: hidden;
  background: #0f0d13;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.16);
  display: flex;
  align-items: center;
  justify-content: center;
}

.artwork-display-wrap {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.artwork-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  cursor: pointer;
}

/* Floating Tonal HUD Toolbar (Constraint 2: Material tonal floating container, no glassmorphism) */
.floating-tonal-hud {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container-high));
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
  z-index: 10;
}

.hud-item-btn {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 15px;
  transition: background-color 140ms ease;
}
.hud-item-btn:hover {
  background: rgb(var(--v-theme-surface-container-highest));
  color: rgb(var(--v-theme-primary));
}

/* Generating Active Progress Overlay */
.generating-progress-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.62);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}

.gen-tonal-card {
  width: 290px;
  padding: 20px;
  border-radius: 20px;
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
}

/* wavy circular 主进度（真实 step）；loading indicator 兜底 unknown 阶段 */
.progress-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 96px;
  margin-bottom: 10px;
}
.gen-circular {
  --m3e-circular-wavy-progress-indicator-diameter: 88px;
}
.gen-loading {
  --m3e-loading-indicator-active-indicator-size: 56px;
}
.progress-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
  pointer-events: none;
}

.gen-ghost-action {
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  cursor: pointer;
}
.gen-ghost-action.danger {
  color: rgb(var(--v-theme-error));
}

/* Empty State */
.canvas-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.empty-icon-ring {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgb(var(--v-theme-surface-container));
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-msg-box {
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(186, 26, 26, 0.12);
  color: #ba1a1a;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
}
</style>
