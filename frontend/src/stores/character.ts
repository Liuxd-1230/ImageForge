import { defineStore } from 'pinia'
import axios from 'axios'
import type { Character } from '../types'

export const useCharacterStore = defineStore('character', {
  state: () => ({
    characters: [] as Character[],
    isLoading: false,
    selectedCategory: '全部',
    searchQuery: '',
  }),

  actions: {
    async fetchCharacters() {
      this.isLoading = true
      try {
        const resp = await axios.get('/api/characters')
        this.characters = resp.data
      } catch (err) {
        console.error('Fetch characters failed:', err)
      } finally {
        this.isLoading = false
      }
    },

    async saveCharacter(char: Character) {
      if (char.id) {
        const resp = await axios.put(`/api/characters/${char.id}`, char)
        const idx = this.characters.findIndex(c => c.id === char.id)
        if (idx !== -1) this.characters[idx] = resp.data
      } else {
        const resp = await axios.post('/api/characters', char)
        this.characters.push(resp.data)
      }
    },

    async deleteCharacter(id: number) {
      await axios.delete(`/api/characters/${id}`)
      this.characters = this.characters.filter(c => c.id !== id)
    },

    async toggleFavorite(char: Character) {
      if (!char.id) return
      const updated = !char.is_favorite
      char.is_favorite = updated
      await axios.put(`/api/characters/${char.id}`, { is_favorite: updated })
    }
  }
})
