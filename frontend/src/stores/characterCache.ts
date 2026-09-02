import { defineStore } from 'pinia'
import axios from 'axios'

export interface ResolvedCharacter {
  id: number
  name: string
  canonical_tag: string
  series_tag: string
  caption_name: string
  aliases: string
  source: string
  resolved_at: string | null
  updated_at: string | null
}

export const useCharacterCacheStore = defineStore('characterCache', {
  state: () => ({
    items: [] as ResolvedCharacter[],
    isLoading: false,
    searchQuery: '',
  }),

  getters: {
    filtered(state): ResolvedCharacter[] {
      const q = state.searchQuery.trim().toLowerCase()
      if (!q) return state.items
      return state.items.filter(it =>
        it.name.toLowerCase().includes(q) ||
        it.canonical_tag.toLowerCase().includes(q) ||
        it.series_tag.toLowerCase().includes(q) ||
        it.caption_name.toLowerCase().includes(q)
      )
    },
  },

  actions: {
    async fetchCache() {
      this.isLoading = true
      try {
        const resp = await axios.get('/api/characters/cache')
        this.items = resp.data
      } catch (err) {
        console.error('Fetch resolved characters failed:', err)
      } finally {
        this.isLoading = false
      }
    },

    async updateItem(id: number, patch: Partial<ResolvedCharacter>) {
      const resp = await axios.put(`/api/characters/cache/${id}`, patch)
      const idx = this.items.findIndex(it => it.id === id)
      if (idx !== -1) {
        this.items[idx] = { ...this.items[idx], ...patch, source: 'manual' }
      }
      return resp.data
    },

    async deleteItem(id: number) {
      await axios.delete(`/api/characters/cache/${id}`)
      this.items = this.items.filter(it => it.id !== id)
    },

    /** 批量删除（只删 Trigger Cache 记录）。返回失败列表。 */
    async bulkDelete(ids: number[]): Promise<number[]> {
      const failed: number[] = []
      for (const id of ids) {
        try {
          await this.deleteItem(id)
        } catch (e) {
          failed.push(id)
        }
      }
      return failed
    },

    /** 联网重新解析。force=false 不覆盖 manual 非空；force=true=“重新解析并替换”。 */
    async reResolve(name: string, force = false): Promise<any> {
      const resp = await axios.post('/api/characters/resolve-online', { name, force })
      return resp.data
    },

    /** 多候选确认（写缓存；force 可选）。 */
    async confirmCandidate(name: string, index: number, force = false): Promise<any> {
      const resp = await axios.post('/api/characters/resolve-online', { name, candidate_index: index, force })
      return resp.data
    },
  },
})
