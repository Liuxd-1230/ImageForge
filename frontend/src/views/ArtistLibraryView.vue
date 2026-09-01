<template>
  <v-container fluid class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">画师风格库</h1>
        <div class="text-caption text-grey">精选 Anima-2.9B 适配画师（推荐使用 @artist 格式），支持风格分类筛选与一键置入创作台。</div>
      </div>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
        添加画师
      </v-btn>
    </div>

    <!-- Search & Filter Bar -->
    <v-row class="mb-2">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="artistStore.searchQuery"
          label="搜索画师名称或 Tag"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          clearable
        />
      </v-col>
      <v-col cols="12" md="8" class="d-flex align-center gap-2 overflow-x-auto">
        <v-chip
          :color="selectedCategory === '' ? 'primary' : undefined"
          :variant="selectedCategory === '' ? 'flat' : 'outlined'"
          size="small"
          @click="selectedCategory = ''"
        >
          全部画师 ({{ artistStore.artists.length }})
        </v-chip>
        <v-chip
          v-for="cat in categories"
          :key="cat"
          :color="selectedCategory === cat ? 'primary' : undefined"
          :variant="selectedCategory === cat ? 'flat' : 'outlined'"
          size="small"
          @click="selectedCategory = cat"
        >
          {{ cat }}
        </v-chip>
        <v-chip
          :color="onlyFavorites ? 'amber' : undefined"
          :variant="onlyFavorites ? 'flat' : 'outlined'"
          size="small"
          prepend-icon="mdi-star"
          @click="onlyFavorites = !onlyFavorites"
        >
          仅看收藏
        </v-chip>
      </v-col>
    </v-row>

    <!-- Artists Grid -->
    <v-row>
      <v-col
        v-for="art in filteredArtists"
        :key="art.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card variant="outlined" class="h-100 d-flex flex-column pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-1">
            <span class="text-subtitle-1 font-weight-bold">{{ art.name }}</span>
            <v-btn
              :icon="art.is_favorite ? 'mdi-star' : 'mdi-star-outline'"
              :color="art.is_favorite ? 'amber' : 'grey'"
              size="small"
              variant="text"
              @click="artistStore.toggleFavorite(art)"
            />
          </div>

          <div class="text-caption font-mono text-primary mb-2">
            <code>{{ art.tags }}</code>
          </div>

          <div class="text-caption text-grey flex-grow-1 mb-3">
            {{ art.description || art.category }}
          </div>

          <div class="d-flex justify-space-between align-center mt-auto pt-2 border-t">
            <v-btn
              size="small"
              :variant="isArtistSelectedInStudio(art) ? 'flat' : 'tonal'"
              :color="isArtistSelectedInStudio(art) ? 'success' : 'primary'"
              :prepend-icon="isArtistSelectedInStudio(art) ? 'mdi-check' : 'mdi-plus'"
              @click="toggleStudioArtist(art)"
            >
              {{ isArtistSelectedInStudio(art) ? '已加入创作台' : '加入创作台' }}
            </v-btn>
            <div class="d-flex gap-1">
              <v-btn
                icon="mdi-pencil"
                size="small"
                variant="text"
                color="primary"
                title="编辑画师"
                @click="openEditDialog(art)"
              />
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                title="删除画师"
                @click="deleteArt(art.id)"
              />
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add/Edit Artist Dialog -->
    <v-dialog v-model="dialog" max-width="500px">
      <v-card class="pa-4 rounded-lg bg-surface">
        <v-card-title class="font-weight-bold">{{ isEdit ? '编辑画师' : '添加画师' }}</v-card-title>
        <v-card-text class="pt-2">
          <v-text-field v-model="form.name" label="画师名称 (如: Mika Pikazo)" density="compact" variant="outlined" class="mb-2" />
          <v-text-field v-model="form.tags" label="画师 Tag (推荐格式: @mika_pikazo)" density="compact" variant="outlined" class="mb-2" />
          <v-text-field v-model="form.category" label="风格分类 (如: 高饱和/活力、厚涂/光影)" density="compact" variant="outlined" class="mb-2" />
          <v-text-field v-model="form.preview_url" label="样例预览图 URL (可选)" density="compact" variant="outlined" class="mb-2" />
          <v-textarea v-model="form.description" label="画风特点与描述" density="compact" variant="outlined" rows="2" />
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!form.name || !form.tags" @click="saveArtist">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="1500" color="success">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useArtistStore } from '../stores/artist'
import { useStudioStore } from '../stores/studio'
import type { Artist } from '../types'

const artistStore = useArtistStore()
const studioStore = useStudioStore()

const dialog = ref(false)
const isEdit = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')
const selectedCategory = ref('')
const onlyFavorites = ref(false)

const form = ref({
  id: undefined as number | undefined,
  name: '',
  tags: '',
  category: '综合',
  description: '',
  preview_url: '',
  is_favorite: false,
  is_custom: true
})

const categories = computed(() => {
  const set = new Set<string>()
  artistStore.artists.forEach((a: Artist) => {
    if (a.category && a.category.trim()) set.add(a.category.trim())
  })
  return Array.from(set)
})

const filteredArtists = computed(() => {
  return artistStore.artists.filter((a: Artist) => {
    if (onlyFavorites.value && !a.is_favorite) return false
    if (selectedCategory.value && a.category !== selectedCategory.value) return false
    if (artistStore.searchQuery) {
      const q = artistStore.searchQuery.toLowerCase()
      return a.name.toLowerCase().includes(q) || a.tags.toLowerCase().includes(q) || (a.description || '').toLowerCase().includes(q)
    }
    return true
  })
})

onMounted(() => {
  artistStore.fetchArtists()
})

function isArtistSelectedInStudio(art: Artist): boolean {
  return studioStore.selectedArtists.some(a => a.id === art.id)
}

function toggleStudioArtist(art: Artist) {
  studioStore.toggleArtist(art)
  snackbarText.value = isArtistSelectedInStudio(art) ? `已添加画师 ${art.name}` : `已移除画师 ${art.name}`
  snackbar.value = true
}

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    id: undefined,
    name: '',
    tags: '',
    category: '综合',
    description: '',
    preview_url: '',
    is_favorite: false,
    is_custom: true
  }
  dialog.value = true
}

function openEditDialog(art: Artist) {
  isEdit.value = true
  form.value = {
    id: art.id,
    name: art.name,
    tags: art.tags,
    category: art.category || '综合',
    description: art.description || '',
    preview_url: art.preview_url || '',
    is_favorite: art.is_favorite,
    is_custom: art.is_custom
  }
  dialog.value = true
}

async function saveArtist() {
  await artistStore.saveArtist(form.value)
  snackbarText.value = isEdit.value ? '画师信息已更新' : '画师已创建'
  dialog.value = false
  snackbar.value = true
}

async function deleteArt(id: number) {
  if (confirm('确定删除该画师记录吗？')) {
    await artistStore.deleteArtist(id)
    snackbarText.value = '画师已删除'
    snackbar.value = true
  }
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.overflow-x-auto {
  overflow-x: auto;
  white-space: nowrap;
}
</style>
