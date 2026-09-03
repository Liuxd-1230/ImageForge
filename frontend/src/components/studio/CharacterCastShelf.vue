<template>
  <div class="cast-shelf">
    <div class="d-flex align-center justify-space-between mb-2">
      <span class="cast-label">登场角色 (Cast Roster)</span>
      <span v-if="detectedCount > 0" class="detected-badge mono">
        {{ detectedCount }} 自动检出
      </span>
    </div>

    <!-- Empty state -->
    <div v-if="characterStore.characters.length === 0" class="cast-empty">
      暂无角色，可在「角色书」创建自设角色 (OC)
    </div>

    <!-- Character Capsules List -->
    <div v-else class="cast-list">
      <div
        v-for="char in characterStore.characters"
        :key="char.id"
        :class="['char-capsule', { detected: isDetected(char.name, char.aliases) }]"
        :title="isDetected(char.name, char.aliases) ? '已自动从画面描述识别并载入' : '点击将角色名插入画面描述'"
        @click="handleCharClick(char.name, isDetected(char.name, char.aliases))"
      >
        <div class="char-avatar" :style="{ background: getAvatarColor(char.name) }">
          {{ char.name.slice(0, 1) }}
        </div>

        <div class="char-meta">
          <div class="d-flex align-center gap-1">
            <span class="char-name">{{ char.name }}</span>
            <span v-if="isDetected(char.name, char.aliases)" class="status-dot-pulse" />
          </div>
          <span class="char-sub mono">{{ char.category || '自设角色' }}</span>
        </div>

        <!-- Hover info preview tooltip -->
        <div class="char-tooltip">
          <div class="tooltip-title">{{ char.name }} <span class="tooltip-series">{{ char.category }}</span></div>
          <div v-if="char.extra_description" class="tooltip-attr"><code>{{ char.extra_description }}</code></div>
          <div class="tooltip-hint">{{ isDetected(char.name, char.aliases) ? '✓ 已在本轮装配线生效' : '点击插入画面描述' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCharacterStore } from '../../stores/character'
import { useStudioStore } from '../../stores/studio'

const characterStore = useCharacterStore()
const studioStore = useStudioStore()

function isDetected(name: string, aliases?: string): boolean {
  const entities = studioStore.facts.entities
  if (!entities || entities.length === 0) return false
  const names = [name.toLowerCase()]
  if (aliases) {
    aliases.split(/[,，|]/).forEach(a => {
      const trimmed = a.trim().toLowerCase()
      if (trimmed) names.push(trimmed)
    })
  }
  return entities.some(e => names.includes(e.name.toLowerCase()) || names.some(n => e.name.toLowerCase().includes(n)))
}

const detectedCount = computed(() => {
  return characterStore.characters.filter(c => isDetected(c.name, c.aliases)).length
})

function handleCharClick(name: string, detected: boolean) {
  if (detected) return
  const current = studioStore.rawInput.trim()
  studioStore.rawInput = current ? `${current}，${name}` : name
  studioStore.isSemanticDirty = true
}

function getAvatarColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const colors = ['#6750A4', '#0B57D0', '#7D5260', '#386A20', '#B3261E', '#00639B', '#4F378B']
  return colors[Math.abs(hash) % colors.length]
}
</script>

<style scoped>
.cast-shelf {
  display: flex;
  flex-direction: column;
}

.cast-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgb(var(--v-theme-on-surface-variant));
  text-transform: uppercase;
}

.detected-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
}

.cast-empty {
  font-size: 11px;
  color: rgb(var(--v-theme-on-surface-variant));
  padding: 8px 10px;
  background: rgb(var(--v-theme-surface-container-low));
  border-radius: 8px;
}

.cast-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

/* Character Capsule: shape morph from 8px to 14px when detected */
.char-capsule {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 10px;
  background: rgb(var(--v-theme-surface-container-low));
  cursor: pointer;
  transition: background-color 160ms ease, border-radius 200ms cubic-bezier(0.2, 0.85, 0.25, 1.08), transform 160ms ease;
}

.char-capsule:hover {
  background: rgb(var(--v-theme-surface-container));
}

/* Morph to secondary container when detected */
.char-capsule.detected {
  background: rgb(var(--v-theme-secondary-container));
  border-radius: 14px;
}

.char-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.char-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.char-name {
  font-size: 11.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  line-height: 1.2;
}

.char-capsule.detected .char-name {
  color: rgb(var(--v-theme-on-secondary-container));
  font-weight: 700;
}

.char-sub {
  font-size: 9.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-dot-pulse {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(var(--v-theme-success));
}

/* Hover popover tooltip */
.char-tooltip {
  display: none;
  position: absolute;
  left: 100%;
  top: 0;
  margin-left: 8px;
  width: 190px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 10px;
  padding: 8px 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  z-index: 30;
  pointer-events: none;
}
.char-capsule:hover .char-tooltip {
  display: block;
}
.tooltip-title {
  font-size: 11.5px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}
.tooltip-series {
  font-size: 10px;
  font-weight: 400;
  color: rgb(var(--v-theme-on-surface-variant));
}
.tooltip-attr {
  font-size: 10px;
  color: rgb(var(--v-theme-primary));
  margin: 3px 0;
  max-height: 40px;
  overflow: hidden;
}
.tooltip-hint {
  font-size: 9.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
</style>
