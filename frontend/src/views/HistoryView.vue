<template>
  <div class="app-page-container">
    <!-- Top Action Bar -->
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <div class="page-header-title">生图历史 (Generation History)</div>
        <div class="text-caption text-grey">记录每次生图的全部 Prompt、Seed 与 ComfyUI 工作台配置，支持完整恢复至创作台。</div>
      </div>
      <div class="text-caption text-grey font-mono">
        共 {{ historyStore.history.length }} 条生图记录
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="historyStore.history.length === 0" class="text-center py-16 text-grey border rounded-lg bg-surface">
      <v-icon size="48" class="mb-2 opacity-50">mdi-history</v-icon>
      <div class="text-body-2 font-weight-medium">暂无生图历史记录</div>
      <div class="text-caption mt-1">在创作台生成图片后，历史记录将自动保存在此处。</div>
    </div>

    <!-- Image-First History Grid -->
    <v-row v-else dense>
      <v-col
        v-for="item in historyStore.history"
        :key="item.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card variant="outlined" class="h-100 d-flex flex-column rounded-lg bg-surface overflow-hidden history-card">
          <!-- Thumbnail Image (Visual Hero) -->
          <div class="history-image-stage bg-surface-variant d-flex align-center justify-center border-b position-relative">
            <v-img
              v-if="item.image_path"
              :src="item.image_path"
              height="200"
              cover
              class="w-100 cursor-pointer"
              @click="openImagePreview(item.image_path)"
            >
              <template #placeholder>
                <div class="d-flex align-center justify-center fill-height bg-surface">
                  <v-icon size="32" color="grey-lighten-1">mdi-image</v-icon>
                </div>
              </template>
            </v-img>
            <div v-else class="d-flex flex-column align-center justify-center fill-height py-12 text-grey text-caption">
              <v-icon size="36" color="grey-lighten-1" class="mb-1">mdi-image-off-outline</v-icon>
              <div>纯 Prompt 记录 (无图片)</div>
            </div>

            <v-chip
              size="x-small"
              variant="flat"
              class="position-absolute"
              style="top: 8px; left: 8px; background: rgba(0, 0, 0, 0.5) !important; color: white;"
            >
              {{ item.safety }}
            </v-chip>
          </div>

          <!-- Content Metadata -->
          <div class="pa-3 d-flex flex-column flex-grow-1">
            <div class="d-flex justify-space-between align-center mb-1">
              <span class="text-caption text-grey">{{ formatDate(item.created_at) }}</span>
              <span v-if="getSeed(item) !== undefined" class="font-mono text-caption text-grey">
                Seed: {{ getSeed(item) }}
              </span>
            </div>

            <!-- User Natural Language Raw Input -->
            <div class="text-body-2 font-weight-medium text-truncate mb-1">
              {{ item.raw_input || '（直接 Prompt 渲染）' }}
            </div>

            <!-- Compact Tag Row -->
            <div class="d-flex gap-1 mb-2">
              <v-chip v-if="getArtistsCount(item) > 0" size="x-small" color="info" variant="tonal">
                画师 x{{ getArtistsCount(item) }}
              </v-chip>
              <v-chip v-if="getLorasCount(item) > 0" size="x-small" color="purple" variant="tonal">
                LoRA x{{ getLorasCount(item) }}
              </v-chip>
            </div>

            <!-- 1-Line Truncated Prompt Snippet -->
            <div class="text-caption font-mono text-grey border rounded px-2 py-1 mb-3 bg-surface-variant text-truncate" style="font-size: 0.72rem !important;">
              {{ item.prompt }}
            </div>

            <!-- Action Bar -->
            <div class="d-flex justify-space-between align-center mt-auto pt-2 border-t">
              <v-btn
                size="x-small"
                variant="flat"
                color="primary"
                prepend-icon="mdi-restore"
                class="px-2"
                @click="restoreToStudio(item)"
              >
                恢复到创作台
              </v-btn>

              <v-btn
                icon="mdi-delete-outline"
                size="x-small"
                variant="text"
                color="error"
                title="删除记录"
                @click="historyStore.deleteHistory(item.id)"
              />
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Large Image Preview Dialog -->
    <v-dialog v-model="imagePreviewDialog" max-width="1000px">
      <v-card class="bg-surface rounded-lg overflow-hidden">
        <div class="d-flex justify-space-between align-center px-4 py-2 border-b">
          <span class="text-subtitle-2 font-weight-bold">历史画作查看</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="imagePreviewDialog = false" />
        </div>
        <div class="pa-2 bg-black text-center">
          <v-img :src="previewImageUrl" max-height="80vh" contain />
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHistoryStore } from '../stores/history'
import { useStudioStore } from '../stores/studio'
import type { GenerationHistory } from '../types'

const historyStore = useHistoryStore()
const studioStore = useStudioStore()
const router = useRouter()

const imagePreviewDialog = ref(false)
const previewImageUrl = ref('')

onMounted(() => {
  historyStore.fetchHistory()
})

function formatDate(d: string) {
  if (!d) return ''
  const date = new Date(d)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

function getSeed(item: GenerationHistory): number | undefined {
  try {
    if (item.comfy_params_json) {
      const p = JSON.parse(item.comfy_params_json)
      return p.seed
    }
  } catch {}
  return undefined
}

function getArtistsCount(item: GenerationHistory): number {
  try {
    return item.artists_json ? JSON.parse(item.artists_json).length : 0
  } catch {
    return 0
  }
}

function getLorasCount(item: GenerationHistory): number {
  try {
    return item.loras_json ? JSON.parse(item.loras_json).length : 0
  } catch {
    return 0
  }
}

function openImagePreview(url: string) {
  previewImageUrl.value = url
  imagePreviewDialog.value = true
}

function restoreToStudio(item: GenerationHistory) {
  studioStore.restoreSession(item)
  router.push('/')
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.history-card {
  transition: border-color 0.15s ease;
}
.history-card:hover {
  border-color: #4F46E5 !important;
}
</style>
