<template>
  <div class="app-page-container">
    <!-- Top Header -->
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <div class="page-header-title">画师风格库 (Artist Gallery)</div>
        <div class="text-caption text-grey">精选 Anima 适配画师（标准 @artist 规范），支持视觉画风预览与分类管理。</div>
      </div>
      <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" class="px-3" @click="openCreateDialog">
        添加画师
      </v-btn>
    </div>

    <!-- Filter Bar -->
    <v-card variant="flat" class="if-panel pa-2 mb-3 library-toolbar">
      <div class="d-flex align-center gap-2 flex-wrap">
        <v-text-field
          v-model="searchQuery"
          label="搜索画师名称或 Tag"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          class="text-caption"
          style="min-width: 220px; max-width: 320px;"
          clearable
        />

        <div class="d-flex align-center gap-1 overflow-x-auto py-1">
          <v-chip
            :color="selectedCategory === '' ? 'primary' : undefined"
            :variant="selectedCategory === '' ? 'flat' : 'tonal'"
            size="x-small"
            @click="selectedCategory = ''"
          >
            全部 ({{ artistStore.artists.length }})
          </v-chip>
          <v-chip
            v-for="cat in categories"
            :key="cat"
            :color="selectedCategory === cat ? 'primary' : undefined"
            :variant="selectedCategory === cat ? 'flat' : 'tonal'"
            size="x-small"
            @click="selectedCategory = cat"
          >
            {{ cat }}
          </v-chip>
          <v-chip
            :color="onlyFavorites ? 'amber' : undefined"
            :variant="onlyFavorites ? 'flat' : 'tonal'"
            size="x-small"
            prepend-icon="mdi-star"
            @click="onlyFavorites = !onlyFavorites"
          >
            仅看收藏
          </v-chip>
        </div>
        <BulkSelectionBar
          :selected-count="bulkSel.selectedCount"
          :is-all-selected="bulkSel.isAllSelected"
          @toggle-all="bulkSel.toggleAll()"
          @delete="openBulkDelete"
        />
      </div>
    </v-card>

    <!-- Empty State -->
    <div v-if="filteredArtists.length === 0" class="if-empty text-center py-12 text-grey">
      <v-icon size="40" class="mb-2 opacity-50">mdi-palette-outline</v-icon>
      <div class="text-body-2 font-weight-medium">未找到符合条件的画师</div>
      <div class="text-caption mt-1">请尝试调整搜索词或分类筛选。</div>
    </div>

    <!-- Image-First Grid -->
    <v-row v-else dense>
      <v-col
        v-for="art in filteredArtists"
        :key="art.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card variant="outlined" class="h-100 d-flex flex-column rounded-lg bg-surface overflow-hidden artist-item-card">
          <!-- Image Preview Area (Hero) -->
          <div class="artist-preview-box bg-surface-container-low d-flex align-center justify-center border-b position-relative">
            <label class="row-check artist-check">
              <input type="checkbox" :checked="bulkSel.isSelected(art.id)" @change="bulkSel.toggleOne(art.id)" />
            </label>
            <v-img
              v-if="art.preview_url"
              :src="art.preview_url"
              height="180"
              cover
              class="w-100"
            >
              <template #placeholder>
                <div class="d-flex align-center justify-center fill-height bg-surface">
                  <v-icon size="32" color="grey-lighten-1">mdi-palette</v-icon>
                </div>
              </template>
              <template #error>
                <div class="d-flex flex-column align-center justify-center fill-height bg-surface text-grey text-caption">
                  <v-icon size="28" color="grey">mdi-image-broken</v-icon>
                  <div style="font-size: 0.7rem;">预览加载失败</div>
                </div>
              </template>
            </v-img>
            <div v-else class="d-flex flex-column align-center justify-center fill-height py-10 text-grey text-caption">
              <v-icon size="36" color="grey-lighten-1" class="mb-1">mdi-palette-outline</v-icon>
              <div style="font-size: 0.75rem;">无样式预览图</div>
            </div>

            <v-btn
              :icon="art.is_favorite ? 'mdi-star' : 'mdi-star-outline'"
              :color="art.is_favorite ? 'amber' : 'white'"
              size="x-small"
              variant="flat"
              class="position-absolute favorite-badge"
              style="top: 8px; right: 8px; background: rgba(0, 0, 0, 0.45) !important;"
              @click.stop="artistStore.toggleFavorite(art)"
            />
          </div>

          <!-- Metadata & Actions -->
          <div class="pa-3 d-flex flex-column flex-grow-1">
            <div class="d-flex justify-space-between align-center mb-1">
              <span class="font-weight-bold text-body-2 text-truncate">{{ art.name }}</span>
              <v-chip size="x-small" variant="tonal" color="secondary" class="ml-1 flex-shrink-0">
                {{ art.category }}
              </v-chip>
            </div>

            <div class="text-caption font-mono text-primary mb-1 text-truncate">
              <code>{{ art.tags }}</code>
            </div>

            <div class="text-caption text-grey flex-grow-1 mb-2 text-truncate-2" style="font-size: 0.75rem !important;">
              {{ art.description || '暂无画风描述' }}
            </div>

            <div class="d-flex justify-space-between align-center mt-auto pt-2 border-t">
              <v-btn
                size="x-small"
                :variant="isArtistSelectedInStudio(art) ? 'flat' : 'tonal'"
                :color="isArtistSelectedInStudio(art) ? 'success' : 'primary'"
                :prepend-icon="isArtistSelectedInStudio(art) ? 'mdi-check' : 'mdi-plus'"
                class="px-2"
                @click="toggleStudioArtist(art)"
              >
                {{ isArtistSelectedInStudio(art) ? '已在创作台' : '加入创作台' }}
              </v-btn>

              <div class="d-flex gap-1">
                <v-btn
                  icon="mdi-pencil-outline"
                  size="x-small"
                  variant="text"
                  color="primary"
                  title="编辑"
                  @click="openEditDialog(art)"
                />
                <v-btn
                  icon="mdi-delete-outline"
                  size="x-small"
                  variant="text"
                  color="error"
                  title="删除"
                  @click="openDeleteArt(art)"
                />
              </div>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Create / Edit Dialog -->
    <v-dialog v-model="dialog" max-width="500px">
      <v-card class="pa-4 bg-surface rounded-lg">
        <div class="d-flex justify-space-between align-center mb-3">
          <span class="text-subtitle-1 font-weight-bold">{{ isEdit ? '编辑画师' : '添加画师' }}</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="dialog = false" />
        </div>

        <div class="d-flex flex-column gap-2">
          <v-text-field v-model="form.name" label="画师名称 (如: Mika Pikazo)" density="compact" variant="outlined" />
          <v-text-field v-model="form.tags" label="画师 Tag (规范格式: @mika_pikazo)" density="compact" variant="outlined" />
          <v-text-field v-model="form.category" label="风格分类 (如: 高饱和/活力、厚涂/光影)" density="compact" variant="outlined" />
          <v-text-field v-model="form.preview_url" label="样例预览图 URL (网络或本地静态地址)" density="compact" variant="outlined" />
          <v-textarea v-model="form.description" label="画风特点与描述" density="compact" variant="outlined" rows="2" hide-details />
        </div>

        <v-card-actions class="justify-end mt-3 pt-2 border-t">
          <v-btn variant="text" size="small" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" size="small" :disabled="!form.name || !form.tags" @click="saveArtist">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <BulkDeleteDialog
      :open="confirmOpen"
      :count="confirmCount"
      :title="confirmTitle"
      :semantics="confirmSemantics"
      :loading="bulkLoading"
      @confirm="confirmDelete"
      @cancel="confirmOpen = false"
    />

    <v-snackbar v-model="snackbar" :timeout="1500" color="success">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useArtistStore } from '../stores/artist'
import { useStudioStore } from '../stores/studio'
import { useBulkSelection } from '../composables/useBulkSelection'
import BulkSelectionBar from '../components/BulkSelectionBar.vue'
import BulkDeleteDialog from '../components/BulkDeleteDialog.vue'
import type { Artist } from '../types'

const artistStore = useArtistStore()
const studioStore = useStudioStore()

const dialog = ref(false)
const isEdit = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')
const selectedCategory = ref('')
const searchQuery = ref('')
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
  artistStore.artists.forEach(a => {
    if (a.category) set.add(a.category)
  })
  return Array.from(set)
})

const filteredArtists = computed(() => {
  return artistStore.artists.filter(a => {
    const matchCat = !selectedCategory.value || a.category === selectedCategory.value
    const matchFav = !onlyFavorites.value || a.is_favorite
    const matchQuery = !searchQuery.value ||
      a.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      a.tags.toLowerCase().includes(searchQuery.value.toLowerCase())
    return matchCat && matchFav && matchQuery
  })
})

const bulkSel = useBulkSelection(() => filteredArtists.value)
const confirmOpen = ref(false)
const confirmCount = ref(1)
const confirmTitle = ref('')
const confirmSemantics = ref('')
const bulkLoading = ref(false)
let pendingDelete: (() => Promise<void>) | null = null

onMounted(() => {
  artistStore.fetchArtists()
})

function isArtistSelectedInStudio(art: Artist): boolean {
  return studioStore.selectedArtists.some(a => a.id === art.id)
}

function toggleStudioArtist(art: Artist) {
  studioStore.toggleArtist(art)
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
    is_custom: art.is_custom ?? true
  }
  dialog.value = true
}

async function saveArtist() {
  if (!form.value.name || !form.value.tags) return
  await artistStore.saveArtist(form.value)
  studioStore.syncArtistsFromLibrary(artistStore.artists)
  dialog.value = false
  snackbarText.value = '画师信息已保存并同步至创作台'
  snackbar.value = true
}

function openDeleteArt(art: Artist) {
  confirmTitle.value = '删除此画师记录？'
  confirmCount.value = 1
  confirmSemantics.value = `确定删除「${art.name}」吗？只删除画师记录，不影响任何本地文件。`
  pendingDelete = async () => {
    await artistStore.deleteArtist(art.id)
    studioStore.syncArtistsFromLibrary(artistStore.artists)
  }
  confirmOpen.value = true
}

function openBulkDelete() {
  if (bulkSel.selected.length === 0) return
  confirmTitle.value = `删除所选 ${bulkSel.selected.length} 个画师记录？`
  confirmCount.value = bulkSel.selected.length
  confirmSemantics.value = '只删除画师记录（不删除任何本地图片/文件）。'
  pendingDelete = async () => {
    const failed: Array<number | string> = []
    for (const id of bulkSel.selected) {
      try { await artistStore.deleteArtist(Number(id)) } catch { failed.push(id) }
    }
    studioStore.syncArtistsFromLibrary(artistStore.artists)
    bulkSel.clear()
    if (failed.length) alert(`删除失败 ${failed.length} 项`)
  }
  confirmOpen.value = true
}

async function confirmDelete() {
  if (!pendingDelete) return
  bulkLoading.value = true
  try {
    await pendingDelete()
  } finally {
    bulkLoading.value = false
    pendingDelete = null
    confirmOpen.value = false
  }
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.artist-item-card {
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.artist-item-card:hover {
  border-color: rgb(var(--v-theme-primary)) !important;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
}
.text-truncate-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.row-check {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}
.row-check input[type="checkbox"] {
  width: 17px;
  height: 17px;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}
.artist-check {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 5;
  padding: 4px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
}
</style>
