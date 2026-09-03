<template>
  <div class="lora-shelf">
    <div class="d-flex align-center justify-space-between mb-2">
      <span class="sec-label">活跃 LoRA 齿轮</span>
      <span class="badge-active mono">{{ enabledCount }} 启用</span>
    </div>

    <!-- Empty state -->
    <div v-if="studioStore.activeLoras.length === 0" class="lora-empty">
      暂无 LoRA，可在「LoRA 库」扫描本地目录添加
    </div>

    <div v-else class="lora-list">
      <div
        v-for="item in studioStore.activeLoras"
        :key="item.lora.id"
        :class="['lora-card', { active: item.isEnabled }]"
      >
        <!-- Top Row -->
        <div class="lora-top">
          <label class="lora-checkbox-label">
            <input
              type="checkbox"
              v-model="item.isEnabled"
              class="lora-checkbox"
              @change="studioStore.buildPrompt()"
            />
            <span class="lora-name text-truncate" :title="item.lora.name">
              {{ item.lora.name }}
            </span>
          </label>
          <span class="lora-val mono">{{ item.strength.toFixed(2) }}</span>
        </div>

        <!-- Slider only shown when enabled (Morph transition) -->
        <div v-if="item.isEnabled" class="lora-slider-wrap">
          <input
            type="range"
            min="0"
            max="1.5"
            step="0.05"
            v-model.number="item.strength"
            class="lora-range"
            @input="studioStore.buildPrompt()"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useStudioStore } from '../../stores/studio'

const studioStore = useStudioStore()

const enabledCount = computed(() => {
  return studioStore.activeLoras.filter(l => l.isEnabled).length
})
</script>

<style scoped>
.lora-shelf {
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

.badge-active {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
  background: rgba(249, 115, 22, 0.15);
  color: #ea580c;
}

.lora-empty {
  font-size: 11px;
  color: rgb(var(--v-theme-on-surface-variant));
  padding: 8px 10px;
  background: rgb(var(--v-theme-surface-container-low));
  border-radius: 8px;
}

.lora-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* Inactive LoRA: compact row (10px radius) */
.lora-card {
  padding: 6px 9px;
  border-radius: 10px;
  background: rgb(var(--v-theme-surface-container-low));
  transition: all 180ms cubic-bezier(0.2, 0, 0, 1);
}

/* Active LoRA: expands to warm-amber tonal container (14px radius) */
.lora-card.active {
  background: rgba(249, 115, 22, 0.08);
  border-radius: 14px;
  padding: 7px 10px 9px;
}

.lora-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.lora-checkbox-label {
  display: flex;
  align-items: center;
  gap: 7px;
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.lora-checkbox {
  accent-color: #ea580c;
  cursor: pointer;
}

.lora-name {
  font-size: 11.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}

.lora-card.active .lora-name {
  color: #c2410c;
  font-weight: 700;
}

.lora-val {
  font-size: 11px;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface-variant));
}
.lora-card.active .lora-val {
  color: #ea580c;
}

.lora-slider-wrap {
  margin-top: 5px;
}

.lora-range {
  width: 100%;
  accent-color: #ea580c;
  height: 4px;
  cursor: pointer;
}
</style>
