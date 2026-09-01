import { defineStore } from 'pinia'
import axios from 'axios'
import type { Lora } from '../types'

export const useLoraStore = defineStore('lora', {
  state: () => ({
    loras: [] as Lora[],
    isLoading: false,
  }),

  actions: {
    async fetchLoras() {
      this.isLoading = true
      try {
        const resp = await axios.get('/api/loras')
        this.loras = resp.data
      } catch (err) {
        console.error('Fetch loras failed:', err)
      } finally {
        this.isLoading = false
      }
    },

    async syncComfyUILoras() {
      this.isLoading = true
      try {
        await axios.post('/api/loras/sync-comfyui')
        await this.fetchLoras()
      } catch (err) {
        console.error('Sync LoRAs failed:', err)
      } finally {
        this.isLoading = false
      }
    },

    async saveLora(lora: Partial<Lora>) {
      if (lora.id) {
        const resp = await axios.put(`/api/loras/${lora.id}`, lora)
        const idx = this.loras.findIndex(l => l.id === lora.id)
        if (idx !== -1) this.loras[idx] = resp.data
      } else {
        const resp = await axios.post('/api/loras', lora)
        this.loras.push(resp.data)
      }
    },

    async deleteLora(id: number) {
      await axios.delete(`/api/loras/${id}`)
      this.loras = this.loras.filter(l => l.id !== id)
    },

    async toggleFavorite(lora: Lora) {
      const updated = !lora.is_favorite
      lora.is_favorite = updated
      await axios.put(`/api/loras/${lora.id}`, { is_favorite: updated })
    }
  }
})
