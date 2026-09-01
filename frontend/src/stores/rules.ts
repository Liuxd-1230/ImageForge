import { defineStore } from 'pinia'
import axios from 'axios'
import type { RuleFile } from '../types'

export const useRuleStore = defineStore('rules', {
  state: () => ({
    rules: [] as RuleFile[],
    isLoading: false,
  }),

  actions: {
    async fetchRules() {
      this.isLoading = true
      try {
        const resp = await axios.get('/api/rules')
        this.rules = resp.data
      } catch (err) {
        console.error('Fetch rules failed:', err)
      } finally {
        this.isLoading = false
      }
    },

    async saveRule(rule: Partial<RuleFile>) {
      if (rule.id) {
        const resp = await axios.put(`/api/rules/${rule.id}`, rule)
        const idx = this.rules.findIndex(r => r.id === rule.id)
        if (idx !== -1) this.rules[idx] = resp.data
      } else {
        const resp = await axios.post('/api/rules', rule)
        this.rules.push(resp.data)
      }
    },

    async deleteRule(id: number) {
      await axios.delete(`/api/rules/${id}`)
      this.rules = this.rules.filter(r => r.id !== id)
    },

    async toggleEnable(rule: RuleFile) {
      const updated = !rule.is_enabled
      rule.is_enabled = updated
      await axios.put(`/api/rules/${rule.id}`, { is_enabled: updated })
    }
  }
})
