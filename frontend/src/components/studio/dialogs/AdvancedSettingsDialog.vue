<template>
  <v-dialog v-model="modelValueProxy" max-width="640px" scrollable>
    <v-card class="rounded-2xl overflow-hidden bg-surface">
      <!-- Header -->
      <div class="d-flex align-center justify-space-between px-5 py-3 border-b">
        <div class="d-flex align-center gap-2">
          <v-icon color="primary" size="22">mdi-tune-variant</v-icon>
          <span class="font-weight-bold text-subtitle-1">高级生图与模型设置</span>
        </div>
        <v-btn icon="mdi-close" variant="text" size="small" @click="modelValueProxy = false" />
      </div>

      <!-- Scrollable Body -->
      <div class="pa-5 d-flex flex-column gap-5" style="max-height: 72vh; overflow-y: auto;">
        <!-- 1. LLM Provider -->
        <div class="adv-section">
          <div class="adv-sec-title">LLM 推理提供商</div>
          <div class="m3-segmented mt-1">
            <button
              type="button"
              :class="['m3-seg-item', { active: studioStore.provider === 'lm_studio' }]"
              @click="switchProvider('lm_studio')"
            >
              LM Studio (本地)
            </button>
            <button
              type="button"
              :class="['m3-seg-item', { active: studioStore.provider === 'cloud' }]"
              @click="switchProvider('cloud')"
            >
              Cloud (OpenAI-compatible)
            </button>
          </div>
        </div>

        <!-- 2. Model Selection -->
        <div class="adv-section">
          <div class="d-flex align-center justify-space-between mb-1">
            <span class="adv-sec-title">推理模型</span>
            <button type="button" class="text-caption text-primary d-inline-flex align-center gap-1 cursor-pointer bg-transparent border-0" @click="refreshModels">
              <span class="mdi mdi-refresh" />刷新列表
            </button>
          </div>
          <div class="d-flex align-center gap-2">
            <select v-model="studioStore.model" class="m3-input-field mono flex-1">
              <option v-for="m in modelList" :key="m.id" :value="m.id">{{ m.id }}</option>
            </select>
          </div>
        </div>

        <!-- 3. Reasoning Effort：m3e-slider（离散档位；MAX 仅 slider 局部 neon treatment） -->
        <div class="adv-section">
          <div class="d-flex align-center justify-space-between mb-1">
            <span class="adv-sec-title">思考强度</span>
            <span class="text-caption font-weight-bold" :class="isMaxReasoning ? 'if-max-gradient' : 'text-primary'">
              {{ currentRsLabel }}
            </span>
          </div>
          <m3e-slider
            labelled
            min="0"
            :max="reasoningOptions.length - 1"
            step="1"
            class="reasoning-slider"
            :class="{ 'max-active': isMaxReasoning }"
            aria-label="思考强度"
            @input="onReasoningSlide"
          >
            <m3e-slider-thumb :value="reasoningIndex" />
          </m3e-slider>
          <div class="reasoning-ticks mono" aria-hidden="true">
            <span
              v-for="(opt, i) in reasoningOptions"
              :key="opt.value"
              :class="['rs-tick', { on: i === reasoningIndex, max: opt.max }]"
            >{{ opt.max ? 'MAX' : opt.label }}</span>
          </div>
        </div>

        <!-- 4. Generation Dimensions -->
        <div class="adv-section">
          <div class="d-flex align-center justify-space-between mb-2">
            <span class="adv-sec-title">画面尺寸 (Width × Height)</span>
            <div class="d-flex gap-1">
              <button
                v-for="p in sizePresets"
                :key="p.label"
                type="button"
                class="size-preset-chip"
                @click="applySizePreset(p)"
              >
                {{ p.label }}
              </button>
            </div>
          </div>
          <div class="d-flex align-center gap-2">
            <input
              v-model.number="studioStore.width"
              type="number"
              min="64"
              max="8192"
              step="64"
              class="m3-input-field mono"
              style="width: 120px;"
            />
            <span class="text-grey font-weight-bold">×</span>
            <input
              v-model.number="studioStore.height"
              type="number"
              min="64"
              max="8192"
              step="64"
              class="m3-input-field mono"
              style="width: 120px;"
            />
            <button type="button" class="m3-icon-btn" title="交换宽高" @click="swapSize">
              <span class="mdi mdi-swap-horizontal" />
            </button>
          </div>
        </div>

        <!-- 5. Steps & CFG -->
        <div class="adv-section">
          <div class="row-2cols">
            <div>
              <span class="adv-sec-title mb-1 d-block">采样步数</span>
              <input
                v-model.number="studioStore.steps"
                type="number"
                min="1"
                max="100"
                class="m3-input-field mono w-100"
              />
            </div>
            <div>
              <span class="adv-sec-title mb-1 d-block">CFG Scale</span>
              <input
                v-model.number="studioStore.cfg"
                type="number"
                min="0.5"
                max="20"
                step="0.5"
                class="m3-input-field mono w-100"
              />
            </div>
          </div>
        </div>

        <!-- 6. Custom ComfyUI Workflow -->
        <div class="adv-section">
          <span class="adv-sec-title mb-1 d-block">ComfyUI Workflow 模式</span>
          <div class="m3-segmented mb-2">
            <button
              type="button"
              :class="['m3-seg-item', { active: studioStore.workflowMode === 'builtin' }]"
              @click="studioStore.workflowMode = 'builtin'"
            >
              内置 Anima 2.9B 优化工作流
            </button>
            <button
              type="button"
              :class="['m3-seg-item', { active: studioStore.workflowMode === 'custom' }]"
              @click="studioStore.workflowMode = 'custom'"
            >
              自定义 API Workflow (JSON)
            </button>
          </div>

          <div v-if="studioStore.workflowMode === 'custom'" class="pa-3 rounded-lg bg-surface-container-low border">
            <div class="text-caption mono text-truncate mb-2 text-primary">
              {{ studioStore.customWorkflowName || '尚未导入 API 格式的 Workflow JSON' }}
            </div>
            <div class="d-flex gap-2">
              <button type="button" class="m3-action-btn tonal" @click="triggerUpload">
                <span class="mdi mdi-upload" />导入 JSON
              </button>
              <button
                v-if="studioStore.customWorkflowTemplate"
                type="button"
                class="m3-action-btn error"
                @click="studioStore.resetToBuiltinWorkflow()"
              >
                重置为内置
              </button>
            </div>
            <input
              ref="fileInput"
              type="file"
              accept=".json"
              style="display: none"
              @change="handleWorkflowUpload"
            />
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="d-flex justify-end px-5 py-3 border-t bg-surface">
        <v-btn color="primary" variant="flat" size="small" rounded="pill" @click="modelValueProxy = false">
          保存并关闭
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStudioStore } from '../../../stores/studio'
import { useSettingsStore } from '../../../stores/settings'
import type { ReasoningEffort } from '../../../types'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const modelValueProxy = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const studioStore = useStudioStore()
const settingsStore = useSettingsStore()
const fileInput = ref<HTMLInputElement | null>(null)

const sizePresets = [
  { label: '人像 1024×1536', w: 1024, h: 1536 },
  { label: '横版 1536×1024', w: 1536, h: 1024 },
  { label: '方形 1152×1152', w: 1152, h: 1152 },
]

function applySizePreset(p: { w: number; h: number }) {
  studioStore.width = p.w
  studioStore.height = p.h
}

function swapSize() {
  const temp = studioStore.width
  studioStore.width = studioStore.height
  studioStore.height = temp
}

const modelList = computed(() => {
  return studioStore.provider === 'lm_studio'
    ? settingsStore.lmStudioModels
    : settingsStore.cloudModels
})

async function refreshModels() {
  if (studioStore.provider === 'lm_studio') {
    await settingsStore.checkLMStudioHealth()
  } else {
    await settingsStore.checkCloudHealth()
  }
}

function switchProvider(p: 'lm_studio' | 'cloud') {
  studioStore.provider = p
  studioStore.model = p === 'lm_studio'
    ? (settingsStore.settings.LM_STUDIO_MODEL || '')
    : (settingsStore.settings.CLOUD_MODEL || '')
  // LM Studio 绝不发送 xhigh/max：切回本地时强制收束到 high
  if (p === 'lm_studio' && (studioStore.reasoningEffort === 'xhigh' || studioStore.reasoningEffort === 'max')) {
    studioStore.reasoningEffort = 'high'
  }
}

const reasoningOptions = computed<{ value: ReasoningEffort; label: string; max?: boolean }[]>(() => {
  if (studioStore.provider === 'lm_studio') {
    return [
      { value: 'off', label: '关闭' },
      { value: 'on', label: '自动' },
      { value: 'low', label: '低' },
      { value: 'medium', label: '中' },
      { value: 'high', label: '高' },
    ]
  } else {
    return [
      { value: 'off', label: '关闭' },
      { value: 'low', label: '低' },
      { value: 'medium', label: '中' },
      { value: 'high', label: '高' },
      { value: 'xhigh', label: '极高' },
      { value: 'max', label: 'MAX', max: true },
    ]
  }
})

const isMaxReasoning = computed(() => studioStore.reasoningEffort === 'max')
const currentRsLabel = computed(() => {
  const opt = reasoningOptions.value.find(o => o.value === studioStore.reasoningEffort)
  return opt ? opt.label : studioStore.reasoningEffort
})

/** 档位索引 ↔ ReasoningEffort（slider 只搬数字，语义映射在这里） */
const reasoningIndex = computed(() => {
  const i = reasoningOptions.value.findIndex(o => o.value === studioStore.reasoningEffort)
  return i >= 0 ? i : 0
})

function onReasoningSlide(e: Event) {
  const i = Math.round(Number((e.target as unknown as { value?: number | null }).value))
  const opt = reasoningOptions.value[i]
  if (opt) studioStore.reasoningEffort = opt.value
}

function triggerUpload() {
  fileInput.value?.click()
}

function handleWorkflowUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    try {
      const json = JSON.parse(reader.result as string)
      studioStore.setWorkflowTemplate(file.name, json)
    } catch {}
  }
  reader.readAsText(file)
}
</script>

<style scoped>
.adv-section {
  display: flex;
  flex-direction: column;
}
.adv-sec-title {
  font-size: 12px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface-variant));
  letter-spacing: 0.02em;
}

.m3-segmented {
  display: flex;
  background: rgb(var(--v-theme-surface-container));
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
}
.m3-seg-item {
  flex: 1;
  padding: 6px 12px;
  border-radius: 6px;
  border: 0;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  transition: all 140ms;
}
.m3-seg-item.active {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-primary));
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.m3-input-field {
  padding: 7px 12px;
  background: rgb(var(--v-theme-surface-container-low));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 8px;
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface));
  outline: none;
}
.m3-input-field:focus {
  border-color: rgb(var(--v-theme-primary));
}

/* Reasoning m3e-slider + 档位列（MAX 霓虹只许出现在 slider 相关元素内） */
.reasoning-slider {
  width: 100%;
  margin-top: 4px;
}
.reasoning-slider.max-active {
  --m3e-slider-active-track-color: transparent;
}
.reasoning-slider.max-active::part(track-active) {
  background: var(--max-gradient);
  background-size: var(--max-gradient-size);
  animation: if-max-flow 7s linear infinite;
}
.reasoning-ticks {
  display: flex;
  justify-content: space-between;
  margin-top: 2px;
  padding: 0 2px;
}
.rs-tick {
  font-size: 10px;
  color: rgb(var(--v-theme-on-surface-variant));
  opacity: 0.75;
}
.rs-tick.on {
  color: rgb(var(--v-theme-primary));
  font-weight: 700;
  opacity: 1;
}
.rs-tick.max.on {
  background: var(--max-gradient);
  background-size: var(--max-gradient-size);
  animation: if-max-flow 7s linear infinite;
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.size-preset-chip {
  padding: 2px 7px;
  border-radius: 4px;
  border: 0;
  background: rgb(var(--v-theme-surface-container));
  font-size: 10.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
}
.size-preset-chip:hover {
  background: rgb(var(--v-theme-surface-container-high));
  color: rgb(var(--v-theme-primary));
}

.m3-icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.row-2cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.m3-action-btn {
  padding: 5px 12px;
  border-radius: 6px;
  border: 0;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.m3-action-btn.tonal {
  background: rgb(var(--v-theme-surface-container-high));
  color: rgb(var(--v-theme-on-surface));
}
.m3-action-btn.error {
  background: rgba(239, 68, 68, 0.15);
  color: #dc2626;
}
</style>
