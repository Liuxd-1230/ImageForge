<template>
  <div class="app-page-container">
    <!-- Top Action Header -->
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <div class="page-header-title">系统与服务设置 (Preferences)</div>
        <div class="text-caption text-grey">配置 LLM 语义推理引擎、云端 API 与 ComfyUI 生图服务地址。</div>
      </div>
      <v-btn
        color="primary"
        variant="flat"
        size="small"
        prepend-icon="mdi-content-save"
        :loading="settingsStore.isLoading"
        class="px-3"
        @click="saveAllSettings"
      >
        保存设置
      </v-btn>
    </div>

    <v-row dense>
      <!-- Section 1: 全局偏好 -->
      <v-col cols="12">
        <v-card variant="outlined" class="pa-3 bg-surface rounded-lg mb-3">
          <div class="section-label mb-2 text-primary">1. 全局创作偏好</div>
          <v-row dense>
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
                class="text-caption"
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
                class="text-caption"
              />
            </v-col>
          </v-row>
        </v-card>
      </v-col>

      <!-- Section 2: 本地 LM Studio -->
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3 bg-surface rounded-lg mb-3 h-100 d-flex flex-column">
          <div class="d-flex justify-space-between align-center mb-2 pb-1 border-b">
            <div class="section-label text-primary">2. 本地 LM Studio 设置</div>
            <div class="d-flex align-center gap-1 text-caption">
              <span :class="['status-indicator', settingsStore.lmStudioStatus === 'connected' ? 'online' : 'offline']" />
              <span class="font-weight-medium">{{ settingsStore.lmStudioStatus === 'connected' ? '已连接' : '未连接' }}</span>
            </div>
          </div>

          <div class="d-flex flex-column gap-2 flex-grow-1">
            <v-text-field
              v-model="form.LM_STUDIO_BASE_URL"
              label="LM Studio Base URL"
              density="compact"
              variant="outlined"
              placeholder="http://localhost:1234"
              class="text-caption"
            />

            <v-text-field
              v-model="form.LM_STUDIO_API_KEY"
              label="API Key (可选)"
              density="compact"
              variant="outlined"
              type="password"
              class="text-caption"
            />

            <div class="d-flex gap-1 align-center">
              <v-select
                v-model="form.LM_STUDIO_MODEL"
                :items="settingsStore.lmStudioModels"
                item-title="id"
                item-value="id"
                label="默认模型"
                density="compact"
                variant="outlined"
                hide-details
                class="flex-grow-1 text-caption"
              />
              <v-btn
                color="primary"
                variant="tonal"
                size="small"
                prepend-icon="mdi-refresh"
                @click="settingsStore.checkLMStudioHealth({ base_url: form.LM_STUDIO_BASE_URL, api_key: form.LM_STUDIO_API_KEY })"
              >
                测试并拉取
              </v-btn>
            </div>

            <div class="d-flex justify-space-between align-center pt-2 border-t mt-auto">
              <v-switch
                v-model="form.LM_STUDIO_AUTO_LOAD"
                label="自动加载模型"
                density="compact"
                color="primary"
                hide-details
              />
              <v-switch
                v-model="form.LM_STUDIO_AUTO_UNLOAD"
                label="生图时卸载以释放显存"
                density="compact"
                color="primary"
                hide-details
              />
            </div>
          </div>
        </v-card>
      </v-col>

      <!-- Section 3: 云端 API -->
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3 bg-surface rounded-lg mb-3 h-100 d-flex flex-column">
          <div class="d-flex justify-space-between align-center mb-2 pb-1 border-b">
            <div class="section-label text-secondary">3. 云端 API 设置 (OpenAI 兼容)</div>
            <div class="d-flex align-center gap-1 text-caption">
              <span :class="['status-indicator', settingsStore.cloudStatus === 'connected' ? 'online' : 'offline']" />
              <span class="font-weight-medium">{{ settingsStore.cloudStatus === 'connected' ? '已连接' : '未连接' }}</span>
            </div>
          </div>

          <div class="d-flex flex-column gap-2 flex-grow-1">
            <v-text-field
              v-model="form.CLOUD_API_NAME"
              label="Provider 名称 (如: DeepSeek / OpenAI)"
              density="compact"
              variant="outlined"
              class="text-caption"
            />

            <v-text-field
              v-model="form.CLOUD_API_BASE_URL"
              label="Base URL"
              density="compact"
              variant="outlined"
              placeholder="https://api.openai.com/v1"
              class="text-caption"
            />

            <v-text-field
              v-model="form.CLOUD_API_KEY"
              label="API Key"
              density="compact"
              variant="outlined"
              type="password"
              class="text-caption"
            />

            <div class="d-flex gap-1 align-center mt-auto">
              <v-select
                v-model="form.CLOUD_MODEL"
                :items="settingsStore.cloudModels"
                item-title="id"
                item-value="id"
                label="默认模型"
                density="compact"
                variant="outlined"
                hide-details
                class="flex-grow-1 text-caption"
              />
              <v-btn
                color="secondary"
                variant="tonal"
                size="small"
                prepend-icon="mdi-refresh"
                @click="settingsStore.checkCloudHealth({ base_url: form.CLOUD_API_BASE_URL, api_key: form.CLOUD_API_KEY })"
              >
                测试并拉取
              </v-btn>
            </div>
          </div>
        </v-card>
      </v-col>

      <!-- Section 4: ComfyUI -->
      <v-col cols="12">
        <v-card variant="outlined" class="pa-3 bg-surface rounded-lg mb-3">
          <div class="d-flex justify-space-between align-center mb-2 pb-1 border-b">
            <div class="section-label text-success">4. ComfyUI 生图服务设置</div>
            <div class="d-flex align-center gap-1 text-caption">
              <span :class="['status-indicator', settingsStore.comfyStatus === 'connected' ? 'online' : 'offline']" />
              <span class="font-weight-medium">{{ settingsStore.comfyStatus === 'connected' ? '已连接' : '未连接' }}</span>
            </div>
          </div>

          <div class="d-flex gap-2 align-center">
            <v-text-field
              v-model="form.COMFYUI_BASE_URL"
              label="ComfyUI Base URL"
              density="compact"
              variant="outlined"
              placeholder="http://127.0.0.1:8188"
              hide-details
              class="flex-grow-1 text-caption"
            />
            <v-btn
              color="success"
              variant="tonal"
              size="small"
              prepend-icon="mdi-connection"
              @click="settingsStore.checkComfyHealth(form.COMFYUI_BASE_URL)"
            >
              测试连接
            </v-btn>
          </div>

          <div class="d-flex align-center gap-2 mt-3">
            <v-text-field
              v-model.number="form.GENERATE_TIMEOUT_SECONDS"
              label="生图等待超时（秒）"
              type="number"
              min="60"
              max="3600"
              density="compact"
              variant="outlined"
              hide-details
              class="flex-grow-1 text-caption"
            />
            <span class="text-caption text-grey">超时只停止前端等待，不会取消 ComfyUI 任务</span>
          </div>
        </v-card>
      </v-col>

      <!-- Section 5: 角色联网解析（Online Resolver V1） -->
      <v-col cols="12">
        <v-card variant="outlined" class="pa-3 bg-surface rounded-lg mb-3">
          <div class="section-label mb-2">5. 角色联网解析</div>
          <div class="d-flex align-center justify-space-between py-1">
            <div class="text-caption">未知角色自动联网查询（Tag 数据源 + 本地 LLM 转写；失败时回退既有 LLM 解析，不中断）</div>
            <v-switch v-model="form.ONLINE_RESOLVE_ENABLED" color="primary" density="compact" hide-details class="ma-0" />
          </div>
          <div class="d-flex align-center justify-space-between py-1 border-t mt-1">
            <div class="text-caption">查询结果写入本地缓存（之后离线直接复用；manual 手工值永不被覆盖）</div>
            <v-switch
              v-model="form.ONLINE_RESOLVE_CACHE_WRITE"
              color="primary"
              density="compact"
              hide-details
              class="ma-0"
              :disabled="!form.ONLINE_RESOLVE_ENABLED"
            />
          </div>
          <div class="d-flex align-center justify-space-between py-1 border-t mt-1">
            <div class="text-caption">多个候选时：询问我（不静默选中第一个）</div>
            <v-select
              v-model="form.ONLINE_RESOLVE_AMBIGUOUS"
              :items="[{ value: 'ask', title: '询问我' }]"
              density="compact"
              variant="outlined"
              hide-details
              class="flex-grow-0 text-caption"
              style="width: 180px"
              disabled
            />
          </div>
          <div class="text-caption text-grey mt-2">数据源：Safebooru（gelbooru 系 SFW booru），输出 canonical_tag + series_tag + caption + aliases。</div>
        </v-card>
      </v-col>

      <!-- Section 6: Civitai Metadata（LoRA Metadata V1） -->
      <v-col cols="12">
        <v-card variant="outlined" class="pa-3 bg-surface rounded-lg mb-3">
          <div class="section-label mb-2 text-tertiary">6. Civitai 元数据（LoRA Metadata V1）</div>
          <div class="d-flex gap-2 align-center py-1">
            <v-select
              v-model="form.CIVITAI_API_HOST"
              :items="[
                { title: 'Civitai Red（https://civitai.red）', value: 'red' },
                { title: 'Civitai.com（https://civitai.com）', value: 'com' }
              ]"
              item-title="title"
              item-value="value"
              label="API Host"
              density="compact"
              variant="outlined"
              hide-details
              class="text-caption"
              style="max-width: 360px"
            />
            <span class="text-caption text-grey">默认 Red；查询时优先使用该条 LoRA 此前成功匹配的 host。</span>
          </div>
          <div class="d-flex gap-2 align-center py-1 mt-1">
            <v-text-field
              v-model="form.CIVITAI_API_TOKEN"
              label="Civitai API Token（可选）"
              :placeholder="form.CIVITAI_API_TOKEN_SET ? '已设置（输入新值覆盖，留空保持不变）' : '不填也能查询公开元数据'"
              density="compact"
              variant="outlined"
              type="password"
              autocomplete="new-password"
              hide-details
              class="text-caption"
              style="max-width: 420px"
            />
            <span class="text-caption text-grey">Token 仅后端使用（Authorization: Bearer），只发送给 Red / Com 官方域名。</span>
          </div>
          <div class="text-caption text-grey mt-2">封面与元数据缓存于本地（backend/data/cache/lora_metadata）；刷新永不覆盖本地名称 / 描述 / Trigger / 权重。</div>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="2500">
      {{ snackbarText }}
    </v-snackbar>
  </div>
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
  DEFAULT_SAFETY: 'Safe',
  GENERATE_TIMEOUT_SECONDS: 300,

  ONLINE_RESOLVE_ENABLED: false,
  ONLINE_RESOLVE_CACHE_WRITE: true,
  ONLINE_RESOLVE_AMBIGUOUS: 'ask',

  CIVITAI_API_HOST: 'red',
  CIVITAI_API_TOKEN: '',
  CIVITAI_API_TOKEN_SET: false
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
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
</style>
