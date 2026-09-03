<template>
  <div class="app-page-container">
    <!-- Top Action Header -->
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <div class="page-header-title">提示词预设 (Prompt Presets)</div>
        <div class="text-caption text-grey">配置不同场景的正向固定质量词与默认 Negative Prompt。</div>
      </div>
      <div class="d-flex align-center gap-2">
        <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" class="px-3" @click="openCreateDialog">
          新建预设
        </v-btn>
        <BulkSelectionBar
          :selected-count="bulkSel.selectedCount"
          :is-all-selected="bulkSel.isAllSelected"
          @toggle-all="bulkSel.toggleAll()"
          @delete="openBulkDelete"
        />
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="presetStore.presets.length === 0" class="if-empty text-center py-16 text-grey">
      <v-icon size="48" class="mb-2 opacity-50">mdi-tune-variant</v-icon>
      <div class="text-body-2 font-weight-medium">暂无提示词预设</div>
      <div class="text-caption mt-1">点击右上角“新建预设”添加默认前缀与 Negative Prompt 模板。</div>
    </div>

    <!-- Presets Grid -->
    <v-row v-else dense>
      <v-col
        v-for="(preset, i) in presetStore.presets"
        :key="preset.id"
        cols="12"
        md="6"
        class="if-enter"
        :style="{ '--i': i }"
      >
        <v-card variant="outlined" class="h-100 d-flex flex-column pa-3 bg-surface rounded-lg preset-card">
          <!-- Card Header -->
          <div class="d-flex justify-space-between align-center mb-2 pb-2 border-b">
            <div class="d-flex align-center gap-2">
              <label class="row-check">
                <input
                  type="checkbox"
                  :checked="bulkSel.isSelected(preset.id)"
                  :disabled="preset.is_default"
                  :title="preset.is_default ? '默认预设不可删除' : ''"
                  @change="bulkSel.toggleOne(preset.id)"
                />
              </label>
              <v-icon color="primary" size="18">mdi-tune</v-icon>
              <span class="font-weight-bold text-body-2">{{ preset.name }}</span>
              <v-chip v-if="preset.is_default" size="x-small" color="primary" variant="flat">默认</v-chip>
            </div>

            <div class="d-flex align-center gap-1">
              <v-btn icon="mdi-pencil-outline" size="x-small" variant="text" color="primary" title="编辑" @click="openEditDialog(preset)" />
              <v-btn
                icon="mdi-delete-outline"
                size="x-small"
                variant="text"
                color="error"
                title="删除"
                :disabled="preset.is_default"
                @click="requestDeletePreset(preset)"
              />
            </div>
          </div>

          <!-- Positive Prefix Preview -->
          <div class="mb-2">
            <div class="text-caption text-grey mb-1">正向固定前缀 (Positive Prefix):</div>
            <div class="font-mono text-caption rounded px-2 py-1 bg-surface-container-low text-truncate" style="font-size: 0.72rem !important;">
              {{ preset.positive_prefix || '（无固定前缀）' }}
            </div>
          </div>

          <!-- Negative Prompt Preview -->
          <div class="flex-grow-1">
            <div class="text-caption text-grey mb-1">默认 Negative Prompt:</div>
            <div class="font-mono text-caption rounded px-2 py-1 bg-surface-container-low text-truncate-2" style="font-size: 0.72rem !important;">
              {{ preset.default_negative || '（无默认 Negative）' }}
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create / Edit Dialog -->
    <v-dialog v-model="dialog" max-width="580px">
      <v-card class="pa-4 bg-surface rounded-lg">
        <div class="d-flex justify-space-between align-center mb-3">
          <span class="text-subtitle-1 font-weight-bold">{{ isEdit ? '编辑提示词预设' : '新建提示词预设' }}</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="dialog = false" />
        </div>

        <div class="d-flex flex-column gap-2">
          <v-text-field v-model="form.name" label="预设名称 (如: Anima 2.9B 默认)" density="compact" variant="outlined" />
          <v-textarea
            v-model="form.positive_prefix"
            label="正向固定前缀 (如: master_piece, high_quality)"
            rows="2"
            density="compact"
            variant="outlined"
            class="font-mono text-caption"
          />
          <v-textarea
            v-model="form.default_negative"
            label="默认 Negative Prompt"
            rows="4"
            density="compact"
            variant="outlined"
            class="font-mono text-caption"
          />
          <v-checkbox v-model="form.is_default" label="设为系统全局默认预设" density="compact" hide-details color="primary" />
        </div>

        <v-card-actions class="justify-end mt-3 pt-2 border-t">
          <v-btn variant="text" size="small" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" size="small" :disabled="!form.name.trim()" @click="savePreset">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <BulkDeleteDialog
      :open="confirmOpen"
      :count="confirmCount"
      :title="confirmTitle"
      :semantics="confirmSemantics"
      :loading="confirmLoading"
      @confirm="confirmDelete"
      @cancel="confirmOpen = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePresetStore } from '../stores/presets'
import { useBulkSelection } from '../composables/useBulkSelection'
import BulkSelectionBar from '../components/BulkSelectionBar.vue'
import BulkDeleteDialog from '../components/BulkDeleteDialog.vue'
import type { Preset } from '../types'

const presetStore = usePresetStore()
const dialog = ref(false)
const isEdit = ref(false)

/* ── 多选 / 删除确认（默认预设不可删除：不进多选集合、复选框禁用） ── */
const deletablePresets = computed(() => presetStore.presets.filter(p => !p.is_default))
const bulkSel = useBulkSelection(() => deletablePresets.value)
const confirmOpen = ref(false)
const confirmCount = ref(1)
const confirmTitle = ref('')
const confirmSemantics = ref('')
const confirmLoading = ref(false)
let pendingDelete: (() => Promise<void>) | null = null

const form = ref({
  id: undefined as number | undefined,
  name: '',
  positive_prefix: '',
  default_negative: 'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry',
  is_default: false
})

onMounted(() => {
  presetStore.fetchPresets()
})

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    id: undefined,
    name: '',
    positive_prefix: '',
    default_negative: 'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry',
    is_default: false
  }
  dialog.value = true
}

function openEditDialog(preset: Preset) {
  isEdit.value = true
  form.value = {
    id: preset.id,
    name: preset.name,
    positive_prefix: preset.positive_prefix || '',
    default_negative: preset.default_negative || '',
    is_default: preset.is_default
  }
  dialog.value = true
}

async function savePreset() {
  if (!form.value.name.trim()) return
  await presetStore.savePreset(form.value)
  dialog.value = false
}

function requestDeletePreset(preset: Preset) {
  if (preset.is_default) return
  confirmTitle.value = '删除此预设？'
  confirmCount.value = 1
  confirmSemantics.value = `确定删除「${preset.name}」吗？删除后其正向前缀与默认 Negative Prompt 不再生效。`
  pendingDelete = async () => { await presetStore.deletePreset(preset.id) }
  confirmOpen.value = true
}

function openBulkDelete() {
  if (bulkSel.selected.length === 0) return
  confirmTitle.value = `删除所选 ${bulkSel.selected.length} 个预设？`
  confirmCount.value = bulkSel.selected.length
  confirmSemantics.value = '确定删除所选预设吗？默认预设不可删除；删除后其前缀与默认 Negative 不再生效。'
  pendingDelete = async () => {
    const failed: Array<number | string> = []
    for (const id of bulkSel.selected) {
      try { await presetStore.deletePreset(Number(id)) } catch { failed.push(id) }
    }
    bulkSel.clear()
    if (failed.length) alert(`删除失败 ${failed.length} 项`)
  }
  confirmOpen.value = true
}

async function confirmDelete() {
  if (!pendingDelete) return
  confirmLoading.value = true
  try {
    await pendingDelete()
  } finally {
    confirmLoading.value = false
    pendingDelete = null
    confirmOpen.value = false
  }
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.preset-card {
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.preset-card:hover {
  border-color: rgb(var(--v-theme-primary)) !important;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
}
.text-truncate-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.row-check {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}
.row-check input[type="checkbox"] {
  width: 17px;
  height: 17px;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}
.row-check input[type="checkbox"]:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}
</style>
