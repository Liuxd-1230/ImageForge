<template>
  <div v-if="historyStore.history.length > 0" class="filmstrip-bar">
    <div class="d-flex align-center justify-space-between mb-1 px-1">
      <div class="d-flex align-center gap-1 text-caption text-grey font-weight-bold">
        <span class="mdi mdi-filmstrip" />
        <span>最近快照 (Filmstrip)</span>
      </div>
      <span class="text-caption text-grey mono">{{ historyStore.history.length }} 条记录</span>
    </div>

    <div class="filmstrip-scroll">
      <div
        v-for="item in historyStore.history.slice(0, 10)"
        :key="item.id"
        class="filmstrip-card"
        :title="`点击恢复该次生图快照 (Seed: ${getSeed(item) ?? '未知'})`"
        @click="restoreItem(item)"
      >
        <img
          v-if="item.image_path"
          :src="item.image_path"
          class="film-thumb"
          alt="history thumbnail"
        />
        <div v-else class="film-thumb-fallback">
          <span class="mdi mdi-image-outline" />
        </div>
        <div class="film-info">
          <span class="film-seed mono">#{{ getSeed(item) ?? '—' }}</span>
          <span class="film-time">{{ formatTime(item.created_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useHistoryStore } from '../../stores/history'
import { useStudioStore } from '../../stores/studio'
import type { GenerationHistory } from '../../types'

const historyStore = useHistoryStore()
const studioStore = useStudioStore()

function getSeed(item: GenerationHistory): number | undefined {
  try {
    if (item.comfy_params_json) {
      const p = JSON.parse(item.comfy_params_json)
      return p.seed
    }
  } catch {}
  return undefined
}

function formatTime(isoStr?: string): string {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  } catch {
    return ''
  }
}

function restoreItem(item: GenerationHistory) {
  studioStore.restoreSession(item)
}
</script>

<style scoped>
.filmstrip-bar {
  height: 86px;
  background: rgb(var(--v-theme-surface-container-low));
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  padding: 6px 14px;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.filmstrip-scroll {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 2px;
}

.filmstrip-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 6px 3px 3px;
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
  cursor: pointer;
  flex-shrink: 0;
  transition: transform 120ms ease, box-shadow 120ms ease;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.filmstrip-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0,0,0,0.1);
}

.film-thumb {
  width: 36px;
  height: 48px;
  object-fit: cover;
  border-radius: 6px;
  background: #0f0d13;
}

.film-thumb-fallback {
  width: 36px;
  height: 48px;
  border-radius: 6px;
  background: rgb(var(--v-theme-surface-container));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: rgb(var(--v-theme-outline));
}

.film-info {
  display: flex;
  flex-direction: column;
}

.film-seed {
  font-size: 10px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.film-time {
  font-size: 9.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
</style>
