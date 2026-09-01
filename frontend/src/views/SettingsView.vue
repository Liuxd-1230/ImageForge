<template>
  <v-container fluid class="pa-4">
    <div class="mb-4">
      <h1 class="text-h5 font-weight-bold">系统与服务设置</h1>
      <div class="text-caption text-grey">配置全局默认设置、本地 LM Studio、云端 API 与 ComfyUI 生图服务。</div>
    </div>

    <v-row>
      <!-- Global Preferences -->
      <v-col cols="12">
        <v-card variant="outlined" class="pa-4 rounded-lg mb-4 bg-surface">
          <div class="d-flex align-center mb-3">
            <v-icon color="primary" class="mr-2">mdi-tune</v-icon>
            <span class="text-subtitle-1 font-weight-bold">全局创作偏好</span>
          </div>

          <v-row>
            <v-col cols="12" md="6">
              <v-select
                v-model="form.ACTIVE_PROVIDER"
                :items="[
                  { title: '本地 LM Studio', value: 'lm_studio' },
                  { title: '云端 API (OpenAI 兼容)', value: 'cloud' }
                ]"
                item-title="title"
                item-value="value"
                label="默认 LLM 提供商"
                density="compact"
                variant="outlined"
                hide-details
              />
            </v-col>
            <v-col cols="12" md="6">
              <v-select
                v-model="form.DEFAULT_SAFETY"
                :items="['Safe', 'Sensitive', 'NSFW', 'Explicit']"
                label="创作台启动默认 Safety 档位"
                density="compact"
                variant="outlined"
                hide-details
              />
            </v-col>
          </v-row>
        </v-card>
      </v-col>

      <!-- LM Studio (Local LLM) -->
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-4 rounded-lg mb-4 bg-surface">
          <div class="d-flex justify-space-between align-center mb-3">
            <div class="d-flex align-center">
              <v-icon color="primary" class="mr-2">mdi-robot</v-icon>
              <span class="text-subtitle-1 font-weight-bold">本地 LM Studio 设置</span>
            </div>
            <v-chip :color="settingsStore.lmStudioStatus === 'connected' ? 'success' : 'grey'" size="small">
              {{ settingsStore.lmStudioStatus === 'connected' ? '已连接' : '未连接' }}
            </v-chip>
          </div>

          <v-text-field
            v-model="form.LM_STUDIO_BASE_URL"
            label="LM Studio Base URL"
            density="compact"
            variant="outlined"
            placeholder="http://localhost:1234"
            class="mb-2"
          />

          <v-text-field
            v-model="form.LM_STUDIO_API_KEY"
            label="API Key (可选)"
            density="compact"
            variant="outlined"
            type="password"
            class="mb-2"
          />

          <div class="d-flex gap-2 mb-3">
            <v-select
              v-model="form.LM_STUDIO_MODEL"
              :items="settingsStore.lmStudioModels"
              item-title="id"
              item-value="id"
              label="默认模型"
              density="compact"
              variant="outlined"
              hide-details
              class="flex-grow-1"
            />
            <v-btn
              color="primary"
              variant="tonal"
              prepend-icon="mdi-refresh"
              @click="settingsStore.checkLMStudioHealth({ base_url: form.LM_STUDIO_BASE_URL, api_key: form.LM_STUDIO_API_KEY })"
            >
              刷新模型
            </v-btn>
          </div>

          <div class="d-flex justify-space-between align-center">
            <v-switch
              v-model="form.LM_STUDIO_AUTO_LOAD"
              label="自动加载模型"
              density="compact"
              color="primary"
              hide-details
            />
            <v-switch
              v-model="form.LM_STUDIO_AUTO_UNLOAD"
              label="生成后自动卸载"
              density="compact"
              color="primary"
              hide-details
            />
          </div>
        </v-card>
      </v-col>

      <!-- Cloud API (OpenAI Compatible) -->
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-4 rounded-lg mb-4 bg-surface">
          <div class="d-flex justify-space-between align-center mb-3">
            <div class="d-flex align-center">
              <v-icon color="secondary" class="mr-2">mdi-cloud-outline</v-icon>
              <span class="text-subtitle-1 font-weight-bold">云端 API 设置 (OpenAI 兼容)</span>
            </div>
            <v-chip :color="settingsStore.cloudStatus === 'connected' ? 'success' : 'grey'" size="small">
              {{ settingsStore.cloudStatus === 'connected' ? '已连接' : '未连接' }}
            </v-chip>
          </div>

          <v-text-field
            v-model="form.CLOUD_API_NAME"
            label="Provider 名称 (如: DeepSeek / OpenAI)"
            density="compact"
            variant="outlined"
            class="mb-2"
          />

          <v-text-field
            v-model="form.CLOUD_API_BASE_URL"
            label="Base URL"
            density="compact"
            variant="outlined"
            placeholder="https://api.openai.com/v1"
            class="mb-2"
          />

          <v-text-field
            v-model="form.CLOUD_API_KEY"
            label="API Key"
            density="compact"
            variant="outlined"
            type="password"
            class="mb-2"
          />

          <div class="d-flex gap-2">
            <v-select
              v-model="form.CLOUD_MODEL"
              :items="settingsStore.cloudModels"
              item-title="id"
              item-value="id"
              label="默认模型"
              density="compact"
              variant="outlined"
              hide-details
              class="flex-grow-1"
            />
            <v-btn
              color="secondary"
              variant="tonal"
              prepend-icon="mdi-refresh"
              @click="settingsStore.checkCloudHealth({ base_url: form.CLOUD_API_BASE_URL, api_key: form.CLOUD_API_KEY })"
            >
              刷新模型
            </v-btn>
          </div>
        </v-card>
      </v-col>

      <!-- ComfyUI Settings -->
      <v-col cols="12">
        <v-card variant="outlined" class="pa-4 rounded-lg mb-4 bg-surface">
          <div class="d-flex justify-space-between align-center mb-3">
            <div class="d-flex align-center">
              <v-icon color="success" class="mr-2">mdi-palette</v-icon>
              <span class="text-subtitle-1 font-weight-bold">ComfyUI 生图服务设置</span>
            </div>
            <v-chip :color="settingsStore.comfyStatus === 'connected' ? 'success' : 'grey'" size="small">
              {{ settingsStore.comfyStatus === 'connected' ? '已连接' : '未连接' }}
            </v-chip>
          </div>

          <div class="d-flex gap-2 align-center">
            <v-text-field
              v-model="form.COMFYUI_BASE_URL"
              label="ComfyUI Base URL"
              density="compact"
              variant="outlined"
              placeholder="http://127.0.0.1:8188"
              hide-details
              class="flex-grow-1"
            />
            <v-btn
              color="success"
              variant="tonal"
              prepend-icon="mdi-connection"
              @click="settingsStore.checkComfyHealth(form.COMFYUI_BASE_URL)"
            >
              测试连接
            </v-btn>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <div class="d-flex justify-end mt-2">
      <v-btn
        color="primary"
        size="large"
        prepend-icon="mdi-content-save"
        :loading="settingsStore.isLoading"
        @click="saveAllSettings"
      >
        保存所有设置
      </v-btn>
    </div>

    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="2500">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '../stores/settings'
import type { AppSettings } from '../types'

const settingsStore = useSettingsStore()
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

const form = ref<AppSettings>({
  ACTIVE_PROVIDER: 'lm_studio',
  LM_STUDIO_BASE_URL: 'http://localhost:1234',
  LM_STUDIO_API_KEY: '',
  LM_STUDIO_MODEL: '',
  LM_STUDIO_AUTO_LOAD: true,
  LM_STUDIO_AUTO_UNLOAD: false,

  CLOUD_API_NAME: '自定义云端 API',
  CLOUD_API_BASE_URL: 'https://api.openai.com/v1',
  CLOUD_API_KEY: '',
  CLOUD_MODEL: '',

  COMFYUI_BASE_URL: 'http://127.0.0.1:8188',
  DEFAULT_SAFETY: 'Safe'
})

onMounted(async () => {
  await settingsStore.fetchSettings()
  Object.assign(form.value, settingsStore.settings)
})

async function saveAllSettings() {
  try {
    await settingsStore.saveSettings(form.value)
    snackbarText.value = '设置已成功保存！'
    snackbarColor.value = 'success'
  } catch (err: any) {
    snackbarText.value = `保存设置失败: ${err.message || err}`
    snackbarColor.value = 'error'
  }
  snackbar.value = true
}
</script>

<style scoped>
.gap-2 {
  gap: 8px;
}
</style>
