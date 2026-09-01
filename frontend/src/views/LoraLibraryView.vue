<template>
  <v-container fluid class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">LoRA 库</h1>
        <div class="text-caption text-grey">管理本地 ComfyUI LoRA 模型，配置触发词 (Trigger Words) 与默认权重。</div>
      </div>
      <div class="d-flex gap-2">
        <v-btn
          color="secondary"
          variant="tonal"
          prepend-icon="mdi-sync"
          :loading="loraStore.isLoading"
          @click="loraStore.syncComfyUILoras()"
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

          <div class="text-caption text-grey mb-3">
            Trigger Words: <code>{{ lora.trigger_words || '无' }}</code>
          </div>

          <div class="d-flex align-center justify-space-between mb-3">
            <span class="text-caption">默认权重: {{ lora.default_strength }}</span>
            <v-chip size="x-small" :color="lora.is_valid_file ? 'success' : 'error'" variant="tonal">
              {{ lora.is_valid_file ? '文件正常' : '文件缺失' }}
            </v-chip>
          </div>

          <div class="d-flex justify-space-between align-center mt-auto">
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              prepend-icon="mdi-plus"
              @click="addToStudio(lora)"
            >
              启用至创作台
            </v-btn>
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="deleteLora(lora.id)"
            />
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add/Edit LoRA Dialog -->
    <v-dialog v-model="dialog" max-width="500px">
      <v-card class="pa-4 rounded-lg bg-surface">
        <v-card-title class="font-weight-bold">添加 / 编辑 LoRA</v-card-title>
        <v-card-text class="pt-2">
          <v-text-field v-model="form.name" label="LoRA 名称" density="compact" variant="outlined" class="mb-2" />
          <v-text-field v-model="form.filename" label="文件名 (如: water_dress.safetensors)" density="compact" variant="outlined" class="mb-2" />
          <v-text-field v-model="form.trigger_words" label="触发词 (逗号分隔)" density="compact" variant="outlined" class="mb-2" />
          <v-slider v-model="form.default_strength" min="0.1" max="1.5" step="0.05" label="默认权重" thumb-label />
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!form.name || !form.filename" @click="saveLora">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="1500" color="success">
      已启用至创作台
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
const snackbar = ref(false)

const form = ref({
  name: '',
  filename: '',
  trigger_words: '',
  default_strength: 0.8,
  is_enabled: false,
  is_favorite: false,
  category: '通用',
  is_valid_file: true
})

onMounted(() => {
  loraStore.fetchLoras()
})

function openCreateDialog() {
  form.value = {
    name: '',
    filename: '',
    trigger_words: '',
    default_strength: 0.8,
    is_enabled: false,
    is_favorite: false,
    category: '通用',
    is_valid_file: true
  }
  dialog.value = true
}

async function saveLora() {
  await loraStore.saveLora(form.value)
  dialog.value = false
}

async function deleteLora(id: number) {
  if (confirm('确定删除该 LoRA 记录吗？')) {
    await loraStore.deleteLora(id)
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
  snackbar.value = true
}
</script>

<style scoped>
.gap-2 { gap: 8px; }
</style>
