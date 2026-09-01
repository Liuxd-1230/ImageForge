import { defineStore } from 'pinia'
import axios from 'axios'
import type { Artist } from '../types'

export const useArtistStore = defineStore('artist', {
  state: () => ({
    artists: [] as Artist[],
    isLoading: false,
  }),

  actions: {
    async fetchArtists() {
      this.isLoading = true
      try {
        const resp = await axios.get('/api/artists')
        this.artists = resp.data
      } catch (err) {
        console.error('Fetch artists failed:', err)
      } finally {
        this.isLoading = false
      }
    },

    async saveArtist(artist: Partial<Artist>) {
      if (artist.id) {
        const resp = await axios.put(`/api/artists/${artist.id}`, artist)
        const idx = this.artists.findIndex(a => a.id === artist.id)
        if (idx !== -1) this.artists[idx] = resp.data
      } else {
        const resp = await axios.post('/api/artists', artist)
        this.artists.push(resp.data)
      }
    },

    async deleteArtist(id: number) {
      await axios.delete(`/api/artists/${id}`)
      this.artists = this.artists.filter(a => a.id !== id)
    },

    async toggleFavorite(artist: Artist) {
      const updated = !artist.is_favorite
      artist.is_favorite = updated
      await axios.put(`/api/artists/${artist.id}`, { is_favorite: updated })
    }
  }
})
