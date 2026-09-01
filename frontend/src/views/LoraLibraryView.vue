<template>
  <v-container fluid class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">LoRA 库</h1>
        <div class="text-caption text-grey">管理本地 ComfyUI LoRA 模型，配置触发词 (Trigger Words) 与默认权重，支持实时编辑。</div>
      </div>
      <div class="d-flex gap-2">
        <v-btn
          color="secondary"
          variant="tonal"
          prepend-icon="mdi-sync"
          :loading="loraStore.isLoading"
          @click="syncLoras"
        >
          扫描 ComfyUI LoRA
        </v-btn>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
          添加 LoRA
        </v-btn>
      </div>
    </div>

    <!-- LoRA Cards Grid -->
    <v-row>
      <v-col
        v-for="lora in loraStore.loras"
        :key="lora.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card variant="outlined" class="h-100 d-flex flex-column pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-1">
            <span class="text-subtitle-1 font-weight-bold">{{ lora.name }}</span>
            <v-btn
              :icon="lora.is_favorite ? 'mdi-star' : 'mdi-star-outline'"
              :color="lora.is_favorite ? 'amber' : 'grey'"
              size="small"
              variant="text"
              @click="loraStore.toggleFavorite(lora)"
            />
          </div>

          <div class="text-caption font-mono text-grey mb-2">
            文件: {{ lora.filename }}
          </div>

          <!-- Highlighted Trigger Words -->
          <div class="pa-2 rounded bg-surface-variant mb-3">
            <div class="text-caption font-weight-bold text-grey mb-1">Trigger Words:</div>
            <div v-if="lora.trigger_words" class="text-caption font-mono text-purple font-weight-medium">
              <code>{{ lora.trigger_words }}</code>
            </div>
            <div v-else class="text-caption text-grey italic">
              （未设置触发词，点击编辑添加）
            </div>
          </div>

          <div class="d-flex align-center justify-space-between mb-3">
            <span class="text-caption">默认权重: {{ lora.default_strength }}</span>
            <v-chip size="x-small" :color="lora.is_valid_file ? 'success' : 'error'" variant="tonal">
              {{ lora.is_valid_file ? '文件正常' : '文件缺失' }}
            </v-chip>
          </div>

          <!-- Actions: 启用至创作台 | 编辑 | 删除 -->
          <div class="d-flex align-center justify-space-between mt-auto pt-2 border-t">
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              prepend-icon="mdi-plus"
              @click="addToStudio(lora)"
            >
              启用
            </v-btn>
            <div class="d-flex gap-1">
              <v-btn
                icon="mdi-pencil"
                size="small"
                variant="text"
                color="primary"
                title="编辑 LoRA 与触发词"
                @click="openEditDialog(lora)"
              />
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                title="删除 LoRA"
                @click="deleteLora(lora.id)"
              />
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add/Edit LoRA Dialog -->
    <v-dialog v-model="dialog" max-width="500px">
      <v-card class="pa-4 rounded-lg bg-surface">
        <v-card-title class="font-weight-bold">{{ isEdit ? '编辑 LoRA' : '添加 LoRA' }}</v-card-title>
        <v-card-text class="pt-2">
          <v-text-field v-model="form.name" label="显示名称" density="compact" variant="outlined" class="mb-2" />
          <v-text-field
            v-model="form.filename"
            label="文件名 (对应 ComfyUI LoRA 文件)"
            density="compact"
            variant="outlined"
            :readonly="isEdit"
            class="mb-2"
          />
          <v-textarea
            v-model="form.trigger_words"
            label="触发词 Trigger Words (逗号分隔)"
            placeholder="如: water_dress, flowing_water"
            rows="2"
            density="compact"
            variant="outlined"
            class="mb-2"
          />
          <v-slider
            v-model="form.default_strength"
            min="0.1"
            max="1.5"
            step="0.05"
            label="默认权重"
            thumb-label
            class="mb-2"
          />
          <v-text-field v-model="form.category" label="分类" density="compact" variant="outlined" />
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!form.name || !form.filename" @click="saveLora">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="1500" color="success">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useLoraStore } from '../stores/lora'
import { useStudioStore } from '../stores/studio'
import type { Lora } from '../types'

const loraStore = useLoraStore()
const studioStore = useStudioStore()

const dialog = ref(false)
const isEdit = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')

const form = ref({
  id: undefined as number | undefined,
  name: '',
  filename: '',
  trigger_words: '',
  default_strength: 0.8,
  is_enabled: false,
  is_favorite: false,
  category: '通用',
  is_custom: true,
  is_valid_file: true
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
    is_enabled: false,
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
    await studioStore.buildPrompt()
  }
}

function addToStudio(lora: Lora) {
  const item = studioStore.activeLoras.find(i => i.lora.id === lora.id)
  if (item) {
    item.isEnabled = true
  } else {
    studioStore.activeLoras.push({
      lora,
      strength: lora.default_strength,
      isEnabled: true
    })
  }
  studioStore.buildPrompt()
  snackbarText.value = `已启用 ${lora.name} 至创作台`
  snackbar.value = true
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.bg-surface-variant {
  background-color: rgba(255, 255, 255, 0.04);
}
</style>
