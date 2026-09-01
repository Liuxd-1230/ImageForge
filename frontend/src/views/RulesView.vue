<template>
  <div class="app-page-container">
    <!-- Top Action Bar -->
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <div class="page-header-title">提示词规则文件 (Rules & Guidelines)</div>
        <div class="text-caption text-grey">维护 Prompt 写作规范与参考说明，支持导入 .md / .txt / .yaml 作为语义抽取上下文。</div>
      </div>
      <div class="d-flex gap-2">
        <v-btn
          color="secondary"
          variant="tonal"
          size="small"
          prepend-icon="mdi-upload"
          class="px-3"
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
        <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" class="px-3" @click="openCreateDialog">
          新建规则
        </v-btn>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="ruleStore.rules.length === 0" class="text-center py-16 text-grey border rounded-lg bg-surface">
      <v-icon size="48" class="mb-2 opacity-50">mdi-file-document-outline</v-icon>
      <div class="text-body-2 font-weight-medium">暂无规则文件</div>
      <div class="text-caption mt-1">点击右上角“导入说明文件”或“新建规则”添加 Prompt 参考规范。</div>
    </div>

    <!-- Rules Grid -->
    <v-row v-else dense>
      <v-col
        v-for="rule in ruleStore.rules"
        :key="rule.id"
        cols="12"
        md="6"
      >
        <v-card variant="outlined" class="h-100 d-flex flex-column pa-3 bg-surface rounded-lg rule-card">
          <!-- Card Header -->
          <div class="d-flex justify-space-between align-center mb-2 pb-2 border-b">
            <div class="d-flex align-center gap-2">
              <v-icon color="primary" size="18">mdi-file-code-outline</v-icon>
              <span class="font-weight-bold text-body-2">{{ rule.name }}</span>
              <v-chip size="x-small" variant="tonal" color="secondary" class="font-mono">
                {{ rule.file_type }}
              </v-chip>
            </div>

            <div class="d-flex align-center gap-1">
              <v-switch
                :model-value="rule.is_enabled"
                color="primary"
                density="compact"
                hide-details
                class="mr-1"
                @update:model-value="val => ruleStore.setEnabled(rule, !!val)"
              />
              <v-btn icon="mdi-pencil-outline" size="x-small" variant="text" color="primary" title="编辑" @click="openEditDialog(rule)" />
              <v-btn icon="mdi-delete-outline" size="x-small" variant="text" color="error" title="删除" @click="deleteRule(rule.id)" />
            </div>
          </div>

          <!-- Content Code Box -->
          <div class="prompt-editor-card flex-grow-1 bg-surface-variant">
            <v-textarea
              :model-value="rule.content"
              rows="6"
              variant="plain"
              density="compact"
              readonly
              hide-details
              class="prompt-textarea px-2 py-1"
            />
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create / Edit Dialog -->
    <v-dialog v-model="dialog" max-width="620px">
      <v-card class="pa-4 bg-surface rounded-lg">
        <div class="d-flex justify-space-between align-center mb-3">
          <span class="text-subtitle-1 font-weight-bold">{{ isEdit ? '编辑规则文件' : '新建规则文件' }}</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="dialog = false" />
        </div>

        <div class="d-flex flex-column gap-2">
          <v-text-field v-model="form.name" label="规则名称 (如: Anima通用服饰写作准则)" density="compact" variant="outlined" />
          <v-textarea
            v-model="form.content"
            label="规则内容 (Markdown / 文本)"
            rows="10"
            density="compact"
            variant="outlined"
            class="font-mono text-caption"
            hide-details
          />
        </div>

        <v-card-actions class="justify-end mt-3 pt-2 border-t">
          <v-btn variant="text" size="small" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" size="small" :disabled="!form.name.trim()" @click="saveRule">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="2000" color="success">
      文件已成功导入
    </v-snackbar>
  </div>
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
  is_enabled: true
})

onMounted(() => {
  ruleStore.fetchRules()
})

function triggerFileInput() {
  fileInput.value?.click()
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)

  try {
    await axios.post('/api/rules/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    await ruleStore.fetchRules()
    snackbar.value = true
  } catch (err) {
    alert('上传文件失败')
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
    is_enabled: true
  }
  dialog.value = true
}

function openEditDialog(rule: RuleFile) {
  isEdit.value = true
  form.value = {
    id: rule.id,
    name: rule.name,
    file_type: rule.file_type,
    content: rule.content,
    is_enabled: rule.is_enabled
  }
  dialog.value = true
}

async function saveRule() {
  if (!form.value.name.trim()) return
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
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.rule-card {
  transition: border-color 0.15s ease;
}
.rule-card:hover {
  border-color: #4F46E5 !important;
}
</style>
