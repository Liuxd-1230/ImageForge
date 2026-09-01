import { defineStore } from 'pinia'
import axios from 'axios'
import type { Preset } from '../types'

export const usePresetStore = defineStore('presets', {
  state: () => ({
    presets: [] as Preset[],
    isLoading: false,
  }),

  actions: {
    async fetchPresets() {
      this.isLoading = true
      try {
        const resp = await axios.get('/api/presets')
        this.presets = resp.data
      } catch (err) {
        console.error('Fetch presets failed:', err)
      } finally {
        this.isLoading = false
      }
    },

    async savePreset(preset: Partial<Preset>) {
      if (preset.id) {
        const resp = await axios.put(`/api/presets/${preset.id}`, preset)
        const idx = this.presets.findIndex(p => p.id === preset.id)
        if (idx !== -1) this.presets[idx] = resp.data
      } else {
        const resp = await axios.post('/api/presets', preset)
        this.presets.push(resp.data)
      }
    },

    async deletePreset(id: number) {
      await axios.delete(`/api/presets/${id}`)
      this.presets = this.presets.filter(p => p.id !== id)
    }
  }
})
