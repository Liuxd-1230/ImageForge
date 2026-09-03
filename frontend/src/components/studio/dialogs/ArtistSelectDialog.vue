<template>
  <v-dialog v-model="modelValueProxy" max-width="760px" scrollable>
    <v-card class="rounded-xl overflow-hidden bg-surface">
      <!-- Dialog Header -->
      <div class="d-flex align-center justify-space-between px-4 py-3 border-b">
        <div class="d-flex align-center gap-2">
          <v-icon color="primary" size="20">mdi-palette-outline</v-icon>
          <span class="font-weight-bold text-subtitle-2">选择画师风格</span>
        </div>
        <v-btn icon="mdi-close" variant="text" size="small" @click="modelValueProxy = false" />
      </div>

      <!-- Search & Category Filters -->
      <div class="px-4 pt-3 pb-2 border-b bg-surface-container-low">
        <div class="d-flex gap-2 align-center mb-2">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索画师名称、Tag 或描述…"
            class="dialog-search-input"
          />
        </div>
        <div class="d-flex gap-1 overflow-x-auto pb-1">
          <button
            type="button"
            :class="['cat-chip', { on: selectedCategory === '' }]"
            @click="selectedCategory = ''"
          >
            全部 ({{ artistStore.artists.length }})
          </button>
          <button
            v-for="cat in artistCategories"
            :key="cat"
            :class="['cat-chip', { on: selectedCategory === cat }]"
            @click="selectedCategory = cat"
          >
            {{ cat }}
          </button>
        </div>
      </div>

      <!-- Artist Grid Content -->
      <div class="px-4 py-3 artist-scroll-grid">
        <div
          v-for="art in filteredArtists"
          :key="art.id"
          :class="['artist-modal-card', { selected: isSelected(art) }]"
          @click="toggleArtist(art)"
        >
          <div class="art-img-box">
            <img v-if="art.preview_url" :src="art.preview_url" class="art-img" alt="preview" />
            <div v-else class="art-img-fallback">
              <span class="mdi mdi-palette-outline" />
            </div>
            <span v-if="isSelected(art)" class="art-check-badge">
              <span class="mdi mdi-check" />
            </span>
          </div>
          <div class="art-card-info">
            <div class="art-card-name">{{ art.name }}</div>
            <div class="art-card-tag mono">{{ art.tags }}</div>
            <div v-if="art.description" class="art-card-desc">{{ art.description }}</div>
          </div>
        </div>
      </div>

      <!-- Dialog Footer -->
      <div class="d-flex align-center justify-space-between px-4 py-3 border-t bg-surface">
        <span class="text-caption text-grey">已选用 {{ studioStore.selectedArtists.length }} 位画师</span>
        <v-btn color="primary" variant="flat" size="small" rounded="pill" @click="modelValueProxy = false">
          完成选择
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useArtistStore } from '../../../stores/artist'
import { useStudioStore } from '../../../stores/studio'
import type { Artist } from '../../../types'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const modelValueProxy = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const artistStore = useArtistStore()
const studioStore = useStudioStore()

const searchQuery = ref('')
const selectedCategory = ref('')

const artistCategories = computed(() => {
  const set = new Set<string>()
  artistStore.artists.forEach(a => { if (a.category) set.add(a.category) })
  return Array.from(set)
})

const filteredArtists = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return artistStore.artists.filter(a => {
    const matchCat = !selectedCategory.value || a.category === selectedCategory.value
    const matchQ = !q || a.name.toLowerCase().includes(q) || a.tags.toLowerCase().includes(q) || (a.description || '').toLowerCase().includes(q)
    return matchCat && matchQ
  })
})

function isSelected(art: Artist): boolean {
  return studioStore.selectedArtists.some(a => a.id === art.id)
}

function toggleArtist(art: Artist) {
  studioStore.toggleArtist(art)
}
</script>

<style scoped>
.dialog-search-input {
  width: 100%;
  padding: 6px 12px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 8px;
  font-size: 12.5px;
  outline: none;
  color: rgb(var(--v-theme-on-surface));
}
.dialog-search-input:focus {
  border-color: rgb(var(--v-theme-primary));
}

.cat-chip {
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  background: transparent;
  font-size: 11px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  white-space: nowrap;
}
.cat-chip.on {
  background: rgb(var(--v-theme-primary-container));
  border-color: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary-container));
}

.artist-scroll-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  max-height: 480px;
  overflow-y: auto;
}

.artist-modal-card {
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 10px;
  overflow: hidden;
  background: rgb(var(--v-theme-surface));
  cursor: pointer;
  transition: all 140ms;
  display: flex;
  flex-direction: column;
}
.artist-modal-card:hover {
  border-color: rgb(var(--v-theme-primary));
  transform: translateY(-1px);
}
.artist-modal-card.selected {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 1px rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-surface-container-low));
}

.art-img-box {
  width: 100%;
  height: 110px;
  background: rgb(var(--v-theme-surface-container));
  position: relative;
  overflow: hidden;
}
.art-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.art-img-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: rgb(var(--v-theme-outline));
}
.art-check-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgb(var(--v-theme-primary));
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}

.art-card-info {
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.art-card-name {
  font-size: 12px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}
.art-card-tag {
  font-size: 10.5px;
  color: rgb(var(--v-theme-primary));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.art-card-desc {
  font-size: 10px;
  color: rgb(var(--v-theme-on-surface-variant));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
