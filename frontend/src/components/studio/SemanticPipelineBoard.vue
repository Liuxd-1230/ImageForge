<template>
  <div class="pipeline-board">
    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-2">
      <div class="d-flex align-center gap-2">
        <span class="board-title">结构化事实</span>
        <span class="count-pill mono">
          {{ studioStore.facts.entities.length }} 实体 · {{ studioStore.facts.statements.length }} 关系
        </span>
      </div>
      <button
        v-if="studioStore.facts.entities.length > 0 || studioStore.facts.statements.length > 0"
        type="button"
        class="reparse-link"
        @click="studioStore.parsePrompt()"
      >
        <span class="mdi mdi-refresh" />重析
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-if="studioStore.facts.entities.length === 0 && studioStore.facts.statements.length === 0"
      class="board-empty"
    >
      <span class="mdi mdi-vector-polyline mr-1" />
      <span>在上方输入画面描述并点击「语义抽取」，此处将自动展开人物与属性关系。</span>
    </div>

    <div v-else class="facts-content-wrap">
      <!-- 1. Entities Section -->
      <div v-if="studioStore.facts.entities.length > 0" class="entities-deck">
        <div
          v-for="e in studioStore.facts.entities"
          :key="e.id"
          class="entity-item-card"
        >
          <div class="e-main-row">
            <span class="e-name">{{ e.name }}</span>
            <span class="e-source-chip" :class="e.source">{{ sourceLabel(e.source) }}</span>
            <span class="e-tag mono"><code>{{ e.canonical_tag || '待解析 Tag' }}</code></span>
          </div>
        </div>
      </div>

      <!-- 2. Statements Section (Neutral tonal body + subtle leading category badge) -->
      <div v-if="studioStore.facts.statements.length > 0" class="statements-deck">
        <div
          v-for="(st, idx) in studioStore.facts.statements"
          :key="idx"
          class="statement-item-card"
        >
          <!-- Subtle Leading Category Badge (Constraint 3: No full-card rainbow) -->
          <span class="category-badge" :class="getCategoryClass(st.kind)">
            {{ getCategoryLabel(st.kind) }}
          </span>

          <span class="st-subj">{{ getEntityName(st.subject) }}</span>
          <span class="st-arrow">→</span>
          <span class="st-text mono">{{ st.text }}</span>

          <template v-if="st.target">
            <span class="st-arrow">→</span>
            <span class="st-subj">{{ getEntityName(st.target) }}</span>
          </template>

          <button
            type="button"
            class="st-remove-btn"
            title="移除该陈述"
            @click="removeStatement(idx)"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useStudioStore } from '../../stores/studio'

const studioStore = useStudioStore()

function sourceLabel(s?: string | null) {
  if (s === 'user_defined') return '角色书'
  if (s === 'model_character') return '模型内置'
  return '通用'
}

function getCategoryClass(kind: string): string {
  if (kind === 'attribute') return 'cat-attr'
  if (kind === 'relation') return 'cat-rel'
  return 'cat-env'
}

function getCategoryLabel(kind: string): string {
  if (kind === 'attribute') return '属性'
  if (kind === 'relation') return '关系'
  return '环境'
}

function getEntityName(id?: string | null): string {
  if (!id) return ''
  const found = studioStore.facts.entities.find(e => e.id === id)
  return found ? found.name : id
}

function removeStatement(idx: number) {
  studioStore.removeStatement(idx)
}
</script>

<style scoped>
.pipeline-board {
  display: flex;
  flex-direction: column;
}

.board-title {
  font-size: 13px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.count-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container-high));
  color: rgb(var(--v-theme-on-surface-variant));
}

.reparse-link {
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

.board-empty {
  font-size: 11.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  padding: 10px 14px;
  background: rgb(var(--v-theme-surface-container-low));
  border-radius: 12px;
  display: flex;
  align-items: center;
}

.facts-content-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.entities-deck {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.entity-item-card {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgb(var(--v-theme-surface-container-low));
}

.e-main-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
}

.e-name {
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}

.e-source-chip {
  font-size: 9.5px;
  font-weight: 600;
  padding: 1px 5px;
  border-radius: 4px;
  background: rgb(var(--v-theme-surface-container-high));
  color: rgb(var(--v-theme-on-surface-variant));
}
.e-source-chip.model_character {
  background: rgba(103, 80, 164, 0.12);
  color: rgb(var(--v-theme-primary));
}

.e-tag {
  font-size: 10.5px;
  color: rgb(var(--v-theme-primary));
}

.statements-deck {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

/* Neutral tonal body (Constraint 3) */
.statement-item-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 8px;
  background: rgb(var(--v-theme-surface-container-low));
  font-size: 12px;
}

/* Subtle category badge */
.category-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 4px;
}
.category-badge.cat-attr {
  background: rgba(11, 87, 208, 0.12);
  color: #0b57d0;
}
.category-badge.cat-rel {
  background: rgba(125, 82, 96, 0.12);
  color: #7d5260;
}
.category-badge.cat-env {
  background: rgba(56, 106, 32, 0.12);
  color: #386a20;
}

.st-subj {
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
}
.st-arrow {
  color: rgb(var(--v-theme-outline));
  font-size: 11px;
}
.st-text {
  flex: 1;
  color: rgb(var(--v-theme-on-surface));
  font-size: 11.5px;
}

.st-remove-btn {
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 14px;
  cursor: pointer;
  padding: 0 4px;
  opacity: 0.6;
}
.st-remove-btn:hover {
  opacity: 1;
  color: rgb(var(--v-theme-error));
}
</style>
