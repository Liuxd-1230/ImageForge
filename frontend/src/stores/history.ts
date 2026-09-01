import { defineStore } from 'pinia'
import axios from 'axios'
import type { GenerationHistory } from '../types'

export const useHistoryStore = defineStore('history', {
  state: () => ({
    history: [] as GenerationHistory[],
    isLoading: false,
  }),

  actions: {
    async fetchHistory() {
      this.isLoading = true
      try {
        const resp = await axios.get('/api/history')
        this.history = resp.data
      } catch (err) {
        console.error('Fetch history failed:', err)
      } finally {
        this.isLoading = false
      }
    },

    async deleteHistory(id: number) {
      await axios.delete(`/api/history/${id}`)
      this.history = this.history.filter(h => h.id !== id)
    }
  }
})
