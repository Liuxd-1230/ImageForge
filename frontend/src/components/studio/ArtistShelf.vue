<template>
  <div class="artist-shelf">
    <div class="d-flex align-center justify-space-between mb-2">
      <span class="sec-label">画师风格 (@artist)</span>
      <button type="button" class="browse-btn" @click="emit('open-dialog')">
        <span class="mdi mdi-plus" />浏览选择
      </button>
    </div>

    <!-- Empty state -->
    <div v-if="studioStore.selectedArtists.length === 0" class="artist-empty" @click="emit('open-dialog')">
      <span class="mdi mdi-palette-outline mr-1" />
      <span>未选择画师风格 (点击添加)</span>
    </div>

    <!-- Selected artist pill list -->
    <div v-else class="artist-chips-wrap">
      <span
        v-for="art in studioStore.selectedArtists"
        :key="art.id"
        class="artist-tonal-pill"
      >
        <span class="artist-tag mono">{{ art.tags }}</span>
        <button
          type="button"
          class="pill-remove-btn"
          title="移除"
          @click.stop="studioStore.toggleArtist(art)"
        >
          ×
        </button>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useStudioStore } from '../../stores/studio'

const emit = defineEmits<{
  (e: 'open-dialog'): void
}>()

const studioStore = useStudioStore()
</script>

<style scoped>
.artist-shelf {
  display: flex;
  flex-direction: column;
}

.sec-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgb(var(--v-theme-on-surface-variant));
  text-transform: uppercase;
}

.browse-btn {
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-primary));
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.artist-empty {
  font-size: 11px;
  color: rgb(var(--v-theme-on-surface-variant));
  padding: 8px 10px;
  background: rgb(var(--v-theme-surface-container-low));
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
}
.artist-empty:hover {
  background: rgb(var(--v-theme-surface-container));
}

.artist-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

/* Tertiary-tinted M3 Expressive Pill */
.artist-tonal-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.28);
  color: #047857;
  font-size: 11px;
  font-weight: 600;
}

.artist-tag {
  line-height: 1;
}

.pill-remove-btn {
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  line-height: 1;
  padding: 0 1px;
  opacity: 0.7;
}
.pill-remove-btn:hover {
  opacity: 1;
}
</style>
