import { defineStore } from 'pinia'
import axios from 'axios'
import type { Lora, LoraSource, ScanResult, ScanCandidate } from '../types'

export const useLoraStore = defineStore('lora', {
  state: () => ({
    loras: [] as Lora[],
    sources: [] as LoraSource[],
    isLoading: false,
    scanningSourceId: null as number | null,
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

    /** 校验既有库记录与 ComfyUI 的一致性（只更新 is_valid_file，不再自动导入）。 */
    async validateAgainstComfyUI() {
      this.isLoading = true
      try {
        const resp = await axios.post('/api/loras/sync-comfyui')
        await this.fetchLoras()
        return resp.data
      } catch (err) {
        console.error('Validate LoRAs failed:', err)
        return null
      } finally {
        this.isLoading = false
      }
    },

    // ── 来源管理 ──
    async fetchSources() {
      const resp = await axios.get('/api/loras/sources')
      this.sources = resp.data
      return resp.data
    },

    async addSource(display_path: string, recursive: boolean) {
      const resp = await axios.post('/api/loras/sources', { display_path, recursive })
      this.sources.push(resp.data)
      return resp.data
    },

    async updateSource(id: number, patch: { enabled?: boolean; recursive?: boolean }) {
      const resp = await axios.put(`/api/loras/sources/${id}`, patch)
      const idx = this.sources.findIndex(s => s.id === id)
      if (idx !== -1) this.sources[idx] = resp.data
      return resp.data
    },

    async deleteSource(id: number) {
      await axios.delete(`/api/loras/sources/${id}`)
      this.sources = this.sources.filter(s => s.id !== id)
    },

    async scanSource(id: number): Promise<ScanResult | null> {
      this.scanningSourceId = id
      try {
        const resp = await axios.post(`/api/loras/sources/${id}/scan`)
        return resp.data
      } catch (err: any) {
        console.error('Scan source failed:', err)
        throw err
      } finally {
        this.scanningSourceId = null
      }
    },

    async importCandidates(items: ScanCandidate[]) {
      const payload = items.map(c => ({
        relative_path: c.relative_path,
        full_path: c.full_path,
        comfy_name: c.comfy_name,
        comfy_recognized: c.comfy_recognized,
        name_hint: c.name_hint,
      }))
      const resp = await axios.post('/api/loras/import', { items: payload })
      await this.fetchLoras()
      return resp.data
    },

    // ── 基础 CRUD ──
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
