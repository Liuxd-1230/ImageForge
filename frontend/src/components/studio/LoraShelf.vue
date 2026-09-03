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
        <!-- Top Row：m3e-switch（M3E binary control，替代原生 checkbox） -->
        <div class="lora-top">
          <m3e-switch
            class="lora-switch"
            :checked="item.isEnabled"
            :aria-label="`启用 ${item.lora.name}`"
            @change="onToggle(item, $event)"
          />
          <span class="lora-name text-truncate" :title="item.lora.name">
            {{ item.lora.name }}
          </span>
          <span class="lora-val mono">{{ item.strength.toFixed(2) }}</span>
        </div>

        <!-- m3e-slider（0~1.5 / step 0.05），仅启用时展开 -->
        <div v-if="item.isEnabled" class="lora-slider-wrap">
          <m3e-slider
            min="0"
            max="1.5"
            step="0.05"
            class="lora-slider"
            :aria-label="`${item.lora.name} 权重`"
            @input="onStrength(item, $event)"
          >
            <m3e-slider-thumb :value="item.strength" />
          </m3e-slider>
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

/** m3e-switch change：target.checked 为新状态；buildPrompt 语义不变 */
function onToggle(item: { isEnabled: boolean }, e: Event) {
  item.isEnabled = !!(e.target as unknown as { checked?: boolean }).checked
  studioStore.buildPrompt()
}

/** m3e-slider input：thumb.value 为当前数值（0~1.5 / step 0.05） */
function onStrength(item: { strength: number }, e: Event) {
  const v = Number((e.target as unknown as { value?: number | null }).value)
  if (Number.isFinite(v)) {
    item.strength = Math.min(1.5, Math.max(0, v))
    studioStore.buildPrompt()
  }
}
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
  transition: background-color var(--if-motion-fast-effects), border-radius var(--if-motion-fast-spatial), padding var(--if-motion-fast-spatial);
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
  gap: 8px;
}

.lora-switch {
  flex-shrink: 0;
  --m3e-switch-track-height: 26px;
  --m3e-switch-track-width: 42px;
}

.lora-name {
  flex: 1;
  min-width: 0;
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
  margin-top: 6px;
  padding: 0 2px;
}

.lora-slider {
  width: 100%;
}
</style>
