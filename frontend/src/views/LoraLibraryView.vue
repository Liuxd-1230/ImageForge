<template>
  <div class="app-page-container">
    <!-- Top Action Header -->
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <div class="page-header-title">LoRA 资源库 (LoRA Manager)</div>
        <div class="text-caption text-grey">管理本地 ComfyUI LoRA 权重与触发词 (Trigger Words) 映射。</div>
      </div>
      <div class="d-flex gap-2">
        <v-btn
          color="secondary"
          variant="tonal"
          size="small"
          prepend-icon="mdi-sync"
          :loading="loraStore.isLoading"
          class="px-3"
          @click="syncLoras"
        >
          扫描本地 LoRA
        </v-btn>
        <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" class="px-3" @click="openCreateDialog">
          添加 LoRA
        </v-btn>
      </div>
    </div>

    <!-- Filter Bar -->
    <v-card variant="outlined" class="pa-2 mb-3 bg-surface rounded-lg">
      <div class="d-flex align-center justify-space-between flex-wrap gap-2">
        <v-text-field
          v-model="searchQuery"
          label="搜索 LoRA 名称、文件名或触发词"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          class="text-caption"
          style="min-width: 240px; max-width: 360px;"
          clearable
        />

        <div class="d-flex align-center gap-2">
          <v-chip
            :color="onlyFavorites ? 'amber' : undefined"
            :variant="onlyFavorites ? 'flat' : 'outlined'"
            size="x-small"
            prepend-icon="mdi-star"
            @click="onlyFavorites = !onlyFavorites"
          >
            仅看收藏
          </v-chip>
          <span class="text-caption text-grey font-mono">共 {{ filteredLoras.length }} 个模型</span>
        </div>
      </div>
    </v-card>

    <!-- Empty State -->
    <div v-if="filteredLoras.length === 0" class="text-center py-12 text-grey border rounded-lg bg-surface">
      <v-icon size="40" class="mb-2 opacity-50">mdi-toy-brick-outline</v-icon>
      <div class="text-body-2 font-weight-medium">暂无 LoRA 记录</div>
      <div class="text-caption mt-1">请点击右上角“扫描本地 LoRA”从 ComfyUI 目录自动识别。</div>
    </div>

    <!-- Table / List Hybrid -->
    <v-card v-else variant="outlined" class="bg-surface rounded-lg overflow-hidden">
      <v-table density="compact" class="lora-table">
        <thead>
          <tr class="bg-surface-variant text-caption font-weight-bold">
            <th style="width: 44px;" class="text-center">收藏</th>
            <th>显示名称 / 分类</th>
            <th>文件名 (ComfyUI File)</th>
            <th>触发词 (Trigger Words)</th>
            <th style="width: 100px;">默认权重</th>
            <th style="width: 90px;" class="text-center">状态</th>
            <th style="width: 90px;" class="text-right pr-4">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="lora in filteredLoras" :key="lora.id" class="lora-row">
            <!-- Favorite -->
            <td class="text-center">
              <v-btn
                :icon="lora.is_favorite ? 'mdi-star' : 'mdi-star-outline'"
                :color="lora.is_favorite ? 'amber' : 'grey'"
                size="x-small"
                variant="text"
                @click="loraStore.toggleFavorite(lora)"
              />
            </td>

            <!-- Name & Category -->
            <td>
              <div class="d-flex align-center gap-1">
                <span class="font-weight-medium text-body-2">{{ lora.name }}</span>
                <v-chip size="x-small" variant="tonal" color="secondary" class="ml-1">
                  {{ lora.category || '通用' }}
                </v-chip>
              </div>
            </td>

            <!-- Filename -->
            <td>
              <span class="font-mono text-caption text-grey-darken-1">{{ lora.filename }}</span>
            </td>

            <!-- Trigger Words -->
            <td>
              <div v-if="lora.trigger_words" class="font-mono text-caption text-purple font-weight-medium">
                <v-chip size="x-small" color="purple" variant="tonal" class="font-mono">
                  {{ lora.trigger_words }}
                </v-chip>
              </div>
              <span v-else class="text-caption text-grey italic">无触发词</span>
            </td>

            <!-- Default Strength -->
            <td>
              <span class="font-mono text-caption font-weight-bold">{{ lora.default_strength.toFixed(2) }}</span>
            </td>

            <!-- Validity Dot -->
            <td class="text-center">
              <div class="d-flex align-center justify-center gap-1 text-caption" :class="lora.is_valid_file ? 'text-success' : 'text-error'">
                <span :class="['status-indicator', lora.is_valid_file ? 'online' : 'error']" style="width: 6px; height: 6px;" />
                <span style="font-size: 0.72rem;">{{ lora.is_valid_file ? '就绪' : '缺失' }}</span>
              </div>
            </td>

            <!-- Actions -->
            <td class="text-right pr-3">
              <div class="d-flex align-center justify-end gap-1">
                <v-btn
                  icon="mdi-pencil-outline"
                  size="x-small"
                  variant="text"
                  color="primary"
                  title="编辑触发词与配置"
                  @click="openEditDialog(lora)"
                />
                <v-btn
                  icon="mdi-delete-outline"
                  size="x-small"
                  variant="text"
                  color="error"
                  title="删除"
                  @click="deleteLora(lora.id)"
                />
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- Create / Edit Dialog -->
    <v-dialog v-model="dialog" max-width="500px">
      <v-card class="pa-4 bg-surface rounded-lg">
        <div class="d-flex justify-space-between align-center mb-3">
          <span class="text-subtitle-1 font-weight-bold">{{ isEdit ? '编辑 LoRA 设定' : '添加 LoRA' }}</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="dialog = false" />
        </div>

        <div class="d-flex flex-column gap-2">
          <v-text-field v-model="form.name" label="显示名称 (如: Water Dress)" density="compact" variant="outlined" />
          <v-text-field
            v-model="form.filename"
            label="文件名 (对应 ComfyUI LoRA 文件)"
            density="compact"
            variant="outlined"
            :readonly="isEdit"
          />
          <v-textarea
            v-model="form.trigger_words"
            label="触发词 Trigger Words (英文逗号分隔)"
            placeholder="如: water_dress, flowing_water"
            rows="2"
            density="compact"
            variant="outlined"
          />
          
          <div class="pa-2 rounded border bg-surface-variant">
            <div class="d-flex justify-space-between text-caption mb-1">
              <span class="font-weight-medium">默认权重 (Default Strength)</span>
              <span class="font-mono font-weight-bold">{{ form.default_strength.toFixed(2) }}</span>
            </div>
            <v-slider
              v-model="form.default_strength"
              min="0.1"
              max="1.5"
              step="0.05"
              density="compact"
              hide-details
              color="primary"
            />
          </div>

          <v-text-field v-model="form.category" label="分类" density="compact" variant="outlined" hide-details />
        </div>

        <v-card-actions class="justify-end mt-3 pt-2 border-t">
          <v-btn variant="text" size="small" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" size="small" :disabled="!form.name || !form.filename" @click="saveLora">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="2000" color="success">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useLoraStore } from '../stores/lora'
import { useStudioStore } from '../stores/studio'
import type { Lora } from '../types'

const loraStore = useLoraStore()
const studioStore = useStudioStore()

const dialog = ref(false)
const isEdit = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')
const searchQuery = ref('')
const onlyFavorites = ref(false)

const form = ref({
  id: undefined as number | undefined,
  name: '',
  filename: '',
  trigger_words: '',
  default_strength: 0.8,
  is_favorite: false,
  category: '通用',
  is_custom: true,
  is_valid_file: true
})

const filteredLoras = computed(() => {
  return loraStore.loras.filter(l => {
    const matchFav = !onlyFavorites.value || l.is_favorite
    const q = searchQuery.value.toLowerCase()
    const matchQuery = !q ||
      l.name.toLowerCase().includes(q) ||
      l.filename.toLowerCase().includes(q) ||
      (l.trigger_words && l.trigger_words.toLowerCase().includes(q))
    return matchFav && matchQuery
  })
})

onMounted(() => {
  loraStore.fetchLoras()
})

async function syncLoras() {
  await loraStore.syncComfyUILoras()
  studioStore.syncLorasFromLibrary(loraStore.loras)
  snackbarText.value = 'LoRA 列表已同步'
  snackbar.value = true
}

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    id: undefined,
    name: '',
    filename: '',
    trigger_words: '',
    default_strength: 0.8,
    is_favorite: false,
    category: '通用',
    is_custom: true,
    is_valid_file: true
  }
  dialog.value = true
}

function openEditDialog(lora: Lora) {
  isEdit.value = true
  form.value = { is_custom: true, ...lora }
  dialog.value = true
}

async function saveLora() {
  await loraStore.saveLora(form.value)
  studioStore.syncLorasFromLibrary(loraStore.loras)
  await studioStore.buildPrompt()
  dialog.value = false
  snackbarText.value = 'LoRA 配置已保存并同步至创作台'
  snackbar.value = true
}

async function deleteLora(id: number) {
  if (confirm('确定删除该 LoRA 记录吗？')) {
    await loraStore.deleteLora(id)
    studioStore.syncLorasFromLibrary(loraStore.loras)
  }
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.lora-table th {
  font-size: 0.72rem !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--v-medium-emphasis-opacity);
}
.lora-row {
  transition: background-color 0.1s ease;
}
.lora-row:hover {
  background-color: var(--v-theme-surface-variant);
}
</style>
