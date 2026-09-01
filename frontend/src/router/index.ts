import { createRouter, createWebHistory } from 'vue-router'
import StudioView from '../views/StudioView.vue'
import CharacterBookView from '../views/CharacterBookView.vue'
import ArtistLibraryView from '../views/ArtistLibraryView.vue'
import LoraLibraryView from '../views/LoraLibraryView.vue'
import RulesView from '../views/RulesView.vue'
import PresetsView from '../views/PresetsView.vue'
import HistoryView from '../views/HistoryView.vue'
import SettingsView from '../views/SettingsView.vue'

const routes = [
  { path: '/', name: 'Studio', component: StudioView },
  { path: '/characters', name: 'Characters', component: CharacterBookView },
  { path: '/artists', name: 'Artists', component: ArtistLibraryView },
  { path: '/loras', name: 'Loras', component: LoraLibraryView },
  { path: '/rules', name: 'Rules', component: RulesView },
  { path: '/presets', name: 'Presets', component: PresetsView },
  { path: '/history', name: 'History', component: HistoryView },
  { path: '/settings', name: 'Settings', component: SettingsView },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
