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
        const payload: Record<string, string> = {}
        if (override?.base_url !== undefined) payload.base_url = override.base_url
        if (override?.api_key !== undefined) payload.api_key = override.api_key
        
        const resp = await axios.post('/api/providers/lm-studio/test', payload)
        this.lmStudioStatus = resp.data.status === 'connected' ? 'connected' : 'disconnected'
        if (this.lmStudioStatus === 'connected') {
          this.lmStudioModels = resp.data.models || []
        } else {
          this.lmStudioModels = []
        }
      } catch {
        this.lmStudioStatus = 'disconnected'
        this.lmStudioModels = []
      }
    },

    async checkCloudHealth(override?: { base_url?: string, api_key?: string }) {
      try {
        const payload: Record<string, string> = {}
        if (override?.base_url !== undefined) payload.base_url = override.base_url
        if (override?.api_key !== undefined) payload.api_key = override.api_key

        const resp = await axios.post('/api/providers/cloud/test', payload)
        this.cloudStatus = resp.data.status === 'connected' ? 'connected' : 'disconnected'
        if (this.cloudStatus === 'connected') {
          this.cloudModels = resp.data.models || []
        } else {
          this.cloudModels = []
        }
      } catch {
        this.cloudStatus = 'disconnected'
        this.cloudModels = []
      }
    },

    async checkComfyHealth(overrideUrl?: string) {
      try {
        const payload: Record<string, string> = {}
        if (overrideUrl !== undefined) payload.base_url = overrideUrl
        const resp = await axios.post('/api/comfyui/test', payload)
        this.comfyStatus = resp.data.status === 'connected' ? 'connected' : 'disconnected'
      } catch {
        this.comfyStatus = 'disconnected'
      }
    }
  }
})
