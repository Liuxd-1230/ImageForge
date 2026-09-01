import { defineStore } from 'pinia'
import axios from 'axios'
import type { AppSettings } from '../types'

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    settings: {
      ACTIVE_PROVIDER: 'lm_studio',
      LM_STUDIO_BASE_URL: 'http://localhost:1234',
      LM_STUDIO_API_KEY: '',
      LM_STUDIO_MODEL: '',
      LM_STUDIO_AUTO_LOAD: true,
      LM_STUDIO_AUTO_UNLOAD: false,
      LM_STUDIO_ENABLE_THINKING: false,
      LM_STUDIO_REASONING_EFFORT: 'instruct',

      CLOUD_API_NAME: '自定义云端 API',
      CLOUD_API_BASE_URL: 'https://api.openai.com/v1',
      CLOUD_API_KEY: '',
      CLOUD_MODEL: '',
      CLOUD_REASONING_EFFORT: 'instruct',

      COMFYUI_BASE_URL: 'http://127.0.0.1:8188',
      DEFAULT_SAFETY: 'Safe'
    } as AppSettings,
    lmStudioStatus: 'disconnected' as 'connected' | 'disconnected' | 'error',
    lmStudioModels: [] as any[],
    cloudStatus: 'disconnected' as 'connected' | 'disconnected' | 'error',
    cloudModels: [] as any[],
    comfyStatus: 'disconnected' as 'connected' | 'disconnected' | 'error',
    isLoading: false,
  }),

  actions: {
    async fetchSettings() {
      try {
        const resp = await axios.get('/api/settings')
        Object.assign(this.settings, resp.data)
        await Promise.allSettled([
          this.checkLMStudioHealth(),
          this.checkCloudHealth(),
          this.checkComfyHealth()
        ])
      } catch (err) {
        console.error('Fetch settings failed:', err)
      }
    },

    async saveSettings(updated: Partial<AppSettings>) {
      this.isLoading = true
      try {
        await axios.post('/api/settings', updated)
        Object.assign(this.settings, updated)
        await Promise.allSettled([
          this.checkLMStudioHealth(),
          this.checkCloudHealth(),
          this.checkComfyHealth()
        ])
      } catch (err) {
        console.error('Save settings failed:', err)
        throw err
      } finally {
        this.isLoading = false
      }
    },

    async checkLMStudioHealth(override?: { base_url?: string, api_key?: string }) {
      try {
        const params: Record<string, string> = {}
        if (override?.base_url) params.base_url = override.base_url
        if (override?.api_key !== undefined) params.api_key = override.api_key
        const resp = await axios.get('/api/providers/lm-studio/health', { params })
        this.lmStudioStatus = resp.data.status === 'connected' ? 'connected' : 'disconnected'
        if (this.lmStudioStatus === 'connected') {
          const modelsResp = await axios.get('/api/providers/lm-studio/models', { params })
          this.lmStudioModels = modelsResp.data.models || modelsResp.data.data || []
        }
      } catch {
        this.lmStudioStatus = 'disconnected'
      }
    },

    async checkCloudHealth(override?: { base_url?: string, api_key?: string }) {
      try {
        const params: Record<string, string> = {}
        if (override?.base_url) params.base_url = override.base_url
        if (override?.api_key !== undefined) params.api_key = override.api_key
        const resp = await axios.get('/api/providers/cloud/health', { params })
        this.cloudStatus = resp.data.status === 'connected' ? 'connected' : 'disconnected'
        if (this.cloudStatus === 'connected') {
          const modelsResp = await axios.get('/api/providers/cloud/models', { params })
          this.cloudModels = modelsResp.data.models || modelsResp.data.data || []
        }
      } catch {
        this.cloudStatus = 'disconnected'
      }
    },

    async checkComfyHealth(overrideUrl?: string) {
      try {
        const params: Record<string, string> = {}
        if (overrideUrl) params.base_url = overrideUrl
        const resp = await axios.get('/api/comfyui/health', { params })
        this.comfyStatus = resp.data.status === 'connected' ? 'connected' : 'disconnected'
      } catch {
        this.comfyStatus = 'disconnected'
      }
    }
  }
})
