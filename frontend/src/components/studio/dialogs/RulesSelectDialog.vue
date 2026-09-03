<template>
  <v-dialog v-model="modelValueProxy" max-width="540px">
    <v-card class="rounded-xl overflow-hidden bg-surface">
      <div class="d-flex align-center justify-space-between px-4 py-3 border-b">
        <div class="d-flex align-center gap-2">
          <v-icon color="primary" size="20">mdi-file-code-outline</v-icon>
          <span class="font-weight-bold text-subtitle-2">参考规则文件</span>
        </div>
        <v-btn icon="mdi-close" variant="text" size="small" @click="modelValueProxy = false" />
      </div>

      <div class="px-4 py-3" style="max-height: 420px; overflow-y: auto;">
        <p class="text-caption text-grey mb-3">
          勾选的规则文件将在 Prompt 解析时作为附加指导注入 LLM 上下文。
        </p>

        <div v-if="ruleStore.rules.length === 0" class="text-center py-6 text-grey text-caption">
          暂无规则文件，可前往「规则文件」页面新建。
        </div>

        <div v-else class="d-flex flex-column gap-2">
          <div
            v-for="r in ruleStore.rules"
            :key="r.id"
            :class="['rule-dialog-item', { active: isRuleSelected(r.id) }]"
            @click="toggleRule(r.id)"
          >
            <input
              type="checkbox"
              :checked="isRuleSelected(r.id)"
              class="rule-check"
              @click.stop
              @change="toggleRule(r.id)"
            />
            <div class="rule-dialog-info">
              <div class="rule-dialog-name">{{ r.name }}</div>
              <div class="rule-dialog-desc text-caption text-grey">{{ r.file_type }}</div>
            </div>
            <span v-if="r.is_enabled" class="default-badge">已启用</span>
          </div>
        </div>
      </div>

      <div class="d-flex justify-end px-4 py-3 border-t bg-surface">
        <v-btn color="primary" variant="flat" size="small" rounded="pill" @click="modelValueProxy = false">
          确定
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRuleStore } from '../../../stores/rules'
import { useStudioStore } from '../../../stores/studio'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const modelValueProxy = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const ruleStore = useRuleStore()
const studioStore = useStudioStore()

function isRuleSelected(id: number): boolean {
  return studioStore.selectedRuleIds.includes(id)
}

function toggleRule(id: number) {
  const idx = studioStore.selectedRuleIds.indexOf(id)
  if (idx >= 0) {
    studioStore.selectedRuleIds.splice(idx, 1)
  } else {
    studioStore.selectedRuleIds.push(id)
  }
}
</script>

<style scoped>
.rule-dialog-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  background: rgb(var(--v-theme-surface-container-low));
  cursor: pointer;
  transition: all 140ms;
}
.rule-dialog-item:hover {
  background: rgb(var(--v-theme-surface-container));
}
.rule-dialog-item.active {
  border-color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-surface-container));
}

.rule-check {
  cursor: pointer;
}
.rule-dialog-info {
  flex: 1;
  min-width: 0;
}
.rule-dialog-name {
  font-size: 12.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
}
.rule-dialog-desc {
  font-size: 11px;
  color: rgb(var(--v-theme-on-surface-variant));
}

.default-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
}
</style>
