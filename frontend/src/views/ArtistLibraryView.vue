<template>
  <v-container fluid class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">画师库</h1>
        <div class="text-caption text-grey">浏览并管理 Anima 画师风格（推荐使用 @artist 格式），支持一键加入创作台。</div>
      </div>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
        添加画师
      </v-btn>
    </div>

    <!-- Filter & Search Bar -->
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
          <div class="d-flex justify-space-between align-center mb-2">
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

          <div class="d-flex justify-space-between align-center">
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              prepend-icon="mdi-plus"
              @click="addToStudio(art)"
            >
              加入创作台
            </v-btn>
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="deleteArt(art.id)"
            />
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add Artist Dialog -->
    <v-dialog v-model="dialog" max-width="500px">
      <v-card class="pa-4 rounded-lg bg-surface">
        <v-card-title class="font-weight-bold">添加画师</v-card-title>
        <v-card-text class="pt-2">
          <v-text-field v-model="form.name" label="画师名称 (如: Mika Pikazo)" density="compact" variant="outlined" class="mb-2" />
          <v-text-field v-model="form.tags" label="画师 Tag (推荐格式: @mika_pikazo)" density="compact" variant="outlined" class="mb-2" />
          <v-text-field v-model="form.category" label="分类" density="compact" variant="outlined" class="mb-2" />
          <v-textarea v-model="form.description" label="风格说明" density="compact" variant="outlined" rows="2" />
        </v-card-text>
        <v-card-actions class="justify-end">
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!form.name || !form.tags" @click="saveArtist">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="1500" color="success">
      已加入创作台
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
const snackbar = ref(false)

const form = ref({
  name: '',
  tags: '',
  category: '常用',
  description: '',
  is_favorite: false,
  is_custom: true
})

onMounted(() => {
  artistStore.fetchArtists()
})

const filteredArtists = computed(() => {
  let list = artistStore.artists
  if (artistStore.searchQuery) {
    const q = artistStore.searchQuery.toLowerCase()
    list = list.filter(a => a.name.toLowerCase().includes(q) || a.tags.toLowerCase().includes(q))
  }
  return list
})

function openCreateDialog() {
  form.value = {
    name: '',
    tags: '@',
    category: '常用',
    description: '',
    is_favorite: false,
    is_custom: true
  }
  dialog.value = true
}

async function saveArtist() {
  let tag = form.value.tags.trim()
  if (!tag.startsWith('@')) {
    tag = '@' + tag.replace(/^artist:/, '')
  }
  form.value.tags = tag
  await artistStore.saveArtist(form.value)
  dialog.value = false
}

async function deleteArt(id: number) {
  if (confirm('确定删除该画师吗？')) {
    await artistStore.deleteArtist(id)
  }
}

function addToStudio(art: Artist) {
  if (!studioStore.selectedArtists.some(a => a.id === art.id)) {
    studioStore.selectedArtists.push(art)
    studioStore.buildPrompt()
    snackbar.value = true
  }
}
</script>
