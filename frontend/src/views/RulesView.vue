<template>
  <v-container fluid class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">提示词规则与说明文件</h1>
        <div class="text-caption text-grey">在此维护提示词写作规范与说明，支持导入 .md / .txt / .yaml 文件作为 Prompt 抽取上下文。</div>
      </div>
      <div class="d-flex gap-2">
        <v-btn
          color="secondary"
          variant="tonal"
          prepend-icon="mdi-upload"
          @click="triggerFileInput"
        >
          导入说明文件
        </v-btn>
        <input
          ref="fileInput"
          type="file"
          accept=".md,.txt,.yaml,.yml"
          style="display: none"
          @change="handleFileUpload"
        />
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
          新建规则
        </v-btn>
      </div>
    </div>

    <v-row>
      <v-col
        v-for="rule in ruleStore.rules"
        :key="rule.id"
        cols="12"
        md="6"
      >
        <v-card variant="outlined" class="pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-2">
            <div class="d-flex align-center">
              <span class="text-subtitle-1 font-weight-bold mr-2">{{ rule.name }}</span>
              <v-chip size="x-small" variant="tonal" color="primary">{{ rule.file_type }}</v-chip>
            </div>
            <div class="d-flex align-center">
              <v-switch
                v-model="rule.is_enabled"
                color="primary"
                density="compact"
                hide-details
                class="mr-2"
                @update:model-value="ruleStore.toggleEnable(rule)"
              />
              <v-btn icon="mdi-pencil" size="small" variant="text" color="primary" @click="openEditDialog(rule)" />
              <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="deleteRule(rule.id)" />
            </div>
          </div>

          <v-textarea
            :model-value="rule.content"
            rows="6"
            variant="outlined"
            density="compact"
            readonly
            class="font-mono text-caption"
            hide-details
          />
        </v-card>
      </v-col>
    </v-row>

    <!-- Dialog -->
    <v-dialog v-model="dialog" max-width="600px">
      <v-card class="pa-4 rounded-lg bg-surface">
        <v-card-title class="font-weight-bold">{{ isEdit ? '编辑规则' : '新建规则' }}</v-card-title>
        <v-card-text class="pt-2">
          <v-text-field v-model="form.name" label="规则名称" density="compact" variant="outlined" class="mb-2" />
          <v-textarea v-model="form.content" label="规则内容" rows="8" density="compact" variant="outlined" class="font-mono text-caption" />
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!form.name.trim()" @click="saveRule">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="2000" color="success">
      文件已成功导入
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useRuleStore } from '../stores/rules'
import type { RuleFile } from '../types'

const ruleStore = useRuleStore()
const dialog = ref(false)
const isEdit = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const snackbar = ref(false)

const form = ref({
  id: undefined as number | undefined,
  name: '',
  file_type: '.md',
  content: '',
  is_enabled: true,
  sort_order: 0
})

onMounted(() => {
  ruleStore.fetchRules()
})

function triggerFileInput() {
  fileInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  const file = target.files[0]
  const formData = new FormData()
  formData.append('file', file)

  try {
    await axios.post('/api/rules/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    await ruleStore.fetchRules()
    snackbar.value = true
  } catch (err) {
    console.error('File upload failed:', err)
  } finally {
    target.value = ''
  }
}

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    id: undefined,
    name: '',
    file_type: '.md',
    content: '',
    is_enabled: true,
    sort_order: 0
  }
  dialog.value = true
}

function openEditDialog(rule: RuleFile) {
  isEdit.value = true
  form.value = { ...rule }
  dialog.value = true
}

async function saveRule() {
  await ruleStore.saveRule(form.value)
  dialog.value = false
}

async function deleteRule(id: number) {
  if (confirm('确定删除该规则文件吗？')) {
    await ruleStore.deleteRule(id)
  }
}
</script>

<style scoped>
.gap-2 { gap: 8px; }
.font-mono { font-family: monospace; }
</style>
