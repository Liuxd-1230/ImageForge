<template>
  <aside :class="['context-rail', { collapsed: isCollapsed }]">
    <!-- Rail Header -->
    <div class="rail-header">
      <div v-if="!isCollapsed" class="header-content">
        <span class="header-title">上下文与资产</span>
      </div>
      <button
        type="button"
        class="collapse-toggle-btn"
        :title="isCollapsed ? '展开面板' : '收起至极细轨 (56px)'"
        @click="isCollapsed = !isCollapsed"
      >
        <span class="mdi" :class="isCollapsed ? 'mdi-chevron-double-right' : 'mdi-chevron-double-left'" />
      </button>
    </div>

    <!-- Collapsed 56px Mini-Rail View -->
    <div v-if="isCollapsed" class="mini-rail-icons">
      <button class="mini-icon-btn" title="Safety 分级" @click="isCollapsed = false">
        <span class="mdi mdi-shield-check-outline" />
      </button>
      <button class="mini-icon-btn" title="登场角色" @click="isCollapsed = false">
        <span class="mdi mdi-account-box-multiple-outline" />
      </button>
      <button class="mini-icon-btn" title="画师风格" @click="emit('open-artist-dialog')">
        <span class="mdi mdi-palette-outline" />
      </button>
      <button class="mini-icon-btn" title="LoRA 齿轮" @click="isCollapsed = false">
        <span class="mdi mdi-toy-brick-outline" />
      </button>
      <button class="mini-icon-btn" title="规则文件" @click="emit('open-rules-dialog')">
        <span class="mdi mdi-file-code-outline" />
      </button>
    </div>

    <!-- Expanded 260px Full Panel -->
    <div v-else class="rail-scroll-body">
      <!-- 1. Safety Segmented Control (Zero layout reflow) -->
      <section class="rail-section">
        <div class="d-flex align-center justify-space-between mb-1">
          <span class="sec-label">SAFETY 分级</span>
          <span class="safety-state-tag" :class="studioStore.safety.toLowerCase()">
            {{ studioStore.safety }}
          </span>
        </div>
        <div class="safety-grid">
          <button
            v-for="opt in (['Safe', 'Sensitive', 'NSFW', 'Explicit'] as const)"
            :key="opt"
            type="button"
            :class="['safety-tab', { active: studioStore.safety === opt }]"
            @click="setSafety(opt)"
          >
            {{ opt }}
          </button>
        </div>
      </section>

      <!-- 2. Rules -->
      <section class="rail-section">
        <div class="d-flex align-center justify-space-between mb-1">
          <span class="sec-label">参考规则集</span>
          <button type="button" class="mini-link-btn" @click="emit('open-rules-dialog')">
            {{ studioStore.selectedRuleIds.length > 0 ? `已选 ${studioStore.selectedRuleIds.length}` : '未选择' }}
            <span class="mdi mdi-chevron-right" />
          </button>
        </div>
        <div class="rules-summary" @click="emit('open-rules-dialog')">
          <span class="mdi mdi-file-check-outline text-primary mr-1" />
          <span class="rules-text text-truncate">
            {{ activeRulesSummary }}
          </span>
        </div>
      </section>

      <!-- 3. Artist Shelf -->
      <section class="rail-section">
        <ArtistShelf @open-dialog="emit('open-artist-dialog')" />
      </section>

      <!-- 4. LoRA Shelf -->
      <section class="rail-section">
        <LoraShelf />
      </section>

      <!-- 5. Character Cast Shelf (Auto-lighting) -->
      <section class="rail-section">
        <CharacterCastShelf />
      </section>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useStudioStore } from '../../stores/studio'
import { useRuleStore } from '../../stores/rules'
import type { SafetyLevel } from '../../types'
import ArtistShelf from './ArtistShelf.vue'
import LoraShelf from './LoraShelf.vue'
import CharacterCastShelf from './CharacterCastShelf.vue'

const emit = defineEmits<{
  (e: 'open-artist-dialog'): void
  (e: 'open-rules-dialog'): void
}>()

const isCollapsed = ref(false)
const studioStore = useStudioStore()
const ruleStore = useRuleStore()

function setSafety(lvl: SafetyLevel) {
  if (studioStore.safety === lvl) return
  studioStore.safety = lvl
  studioStore.buildPrompt()
}

const activeRulesSummary = computed(() => {
  if (studioStore.selectedRuleIds.length === 0) return '默认官方生图规范（点击添加）'
  const names = ruleStore.rules
    .filter(r => studioStore.selectedRuleIds.includes(r.id))
    .map(r => r.name)
  return names.join('、')
})
</script>

<style scoped>
.context-rail {
  width: 260px;
  min-width: 260px;
  max-width: 260px;
  height: 100%;
  background: rgb(var(--v-theme-surface));
  border-right: 1px solid rgb(var(--v-theme-outline-variant));
  display: flex;
  flex-direction: column;
  transition: width 200ms cubic-bezier(0.2, 0, 0, 1), min-width 200ms cubic-bezier(0.2, 0, 0, 1);
  flex-shrink: 0;
  z-index: 5;
}

.context-rail.collapsed {
  width: 56px;
  min-width: 56px;
  max-width: 56px;
}

.rail-header {
  height: 48px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgb(var(--v-theme-outline-variant));
  flex-shrink: 0;
}

.header-title {
  font-size: 13px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
  letter-spacing: -0.01em;
}

.collapse-toggle-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.collapse-toggle-btn:hover {
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface));
}

.mini-rail-icons {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 14px;
  gap: 12px;
}

.mini-icon-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  cursor: pointer;
}
.mini-icon-btn:hover {
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-primary));
}

.rail-scroll-body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 12px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rail-section {
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

.safety-state-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 999px;
}
.safety-state-tag.safe { background: rgba(56, 106, 32, 0.15); color: #2e7d32; }
.safety-state-tag.sensitive { background: rgba(234, 179, 8, 0.15); color: #b45309; }
.safety-state-tag.nsfw { background: rgba(239, 68, 68, 0.15); color: #dc2626; }
.safety-state-tag.explicit { background: rgba(185, 28, 28, 0.2); color: #991b1b; }

/* Safety Segmented Control (Constraint 1: 4 fixed equal columns, zero layout reflow!) */
.safety-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  background: rgb(var(--v-theme-surface-container));
  padding: 3px;
  border-radius: 10px;
  gap: 2px;
}

.safety-tab {
  border: 0;
  background: transparent;
  padding: 5px 0;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  text-align: center;
  transition: background-color 140ms ease, color 140ms ease;
}

.safety-tab.active {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-primary));
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}

.mini-link-btn {
  border: 0;
  background: transparent;
  color: rgb(var(--v-theme-primary));
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.rules-summary {
  display: flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 8px;
  background: rgb(var(--v-theme-surface-container-low));
  font-size: 11.5px;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
}
.rules-summary:hover {
  background: rgb(var(--v-theme-surface-container));
}
.rules-text {
  flex: 1;
}
</style>
