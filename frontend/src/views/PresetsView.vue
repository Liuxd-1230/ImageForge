<template>
  <v-container fluid class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">提示词预设管理</h1>
        <div class="text-caption text-grey">保存常用的正向固定质量前缀与默认 Negative Prompt。</div>
      </div>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
        新建预设
      </v-btn>
    </div>

    <v-row>
      <v-col
        v-for="preset in presetStore.presets"
        :key="preset.id"
        cols="12"
        md="6"
      >
        <v-card variant="outlined" class="pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-2">
            <div class="d-flex align-center">
              <span class="text-subtitle-1 font-weight-bold mr-2">{{ preset.name }}</span>
              <v-chip v-if="preset.is_default" size="x-small" color="primary" variant="flat">默认</v-chip>
            </div>
            <div>
              <v-btn icon="mdi-pencil" size="small" variant="text" color="primary" @click="openEditDialog(preset)" />
              <v-btn icon="mdi-delete" size="small" variant="text" color="error" :disabled="preset.is_default" @click="deletePreset(preset.id)" />
            </div>
          </div>

          <div class="text-caption text-grey mb-1">正向固定前缀 (Positive Prefix):</div>
          <div class="text-caption font-mono border rounded pa-2 mb-2 bg-surface">
            {{ preset.positive_prefix || '无' }}
          </div>

          <div class="text-caption text-grey mb-1">默认 Negative Prompt:</div>
          <div class="text-caption font-mono border rounded pa-2 mb-2 bg-surface">
            {{ preset.default_negative || '无' }}
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Dialog -->
    <v-dialog v-model="dialog" max-width="600px">
      <v-card class="pa-4 rounded-lg bg-surface">
        <v-card-title class="font-weight-bold">{{ isEdit ? '编辑预设' : '新建预设' }}</v-card-title>
        <v-card-text class="pt-2">
          <v-text-field v-model="form.name" label="预设名称" density="compact" variant="outlined" class="mb-2" />
          <v-textarea v-model="form.positive_prefix" label="正向固定前缀" rows="2" density="compact" variant="outlined" class="font-mono text-caption mb-2" />
          <v-textarea v-model="form.default_negative" label="默认 Negative Prompt" rows="3" density="compact" variant="outlined" class="font-mono text-caption mb-2" />
          <v-checkbox v-model="form.is_default" label="设为默认预设" density="compact" hide-details color="primary" />
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!form.name.trim()" @click="savePreset">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePresetStore } from '../stores/presets'
import type { Preset } from '../types'

const presetStore = usePresetStore()
const dialog = ref(false)
const isEdit = ref(false)

const form = ref({
  id: undefined as number | undefined,
  name: '',
  positive_prefix: '',
  default_negative: 'lowres, bad anatomy, bad hands, text',
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
    default_negative: 'lowres, bad anatomy, bad hands, text',
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
  await presetStore.savePreset(form.value)
  dialog.value = false
}

async function deletePreset(id: number) {
  if (confirm('确定删除该预设吗？')) {
    await presetStore.deletePreset(id)
  }
}
</script>
