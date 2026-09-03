<template>
  <v-dialog v-model="modelValueProxy" max-width="420px">
    <v-card class="rounded-xl pa-2 bg-surface overflow-hidden">
      <div class="px-4 pt-4 pb-2">
        <div class="d-flex align-center gap-2 mb-2">
          <v-icon color="error" size="24">mdi-alert-circle-outline</v-icon>
          <span class="font-weight-bold text-subtitle-1 text-on-surface">中断生成任务</span>
        </div>
        <p class="text-body-2 text-on-surface-variant">
          确定要向 ComfyUI 发送中断信号吗？当前执行队列将被清除，正在采样的步骤可能会丢失。
        </p>
      </div>

      <div class="d-flex justify-end gap-2 px-4 py-3 bg-surface border-t">
        <v-btn
          variant="tonal"
          size="small"
          rounded="pill"
          @click="modelValueProxy = false"
        >
          取消
        </v-btn>
        <v-btn
          color="error"
          variant="flat"
          size="small"
          rounded="pill"
          @click="handleConfirm"
        >
          确认中断
        </v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
}>()

const modelValueProxy = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

function handleConfirm() {
  modelValueProxy.value = false
  emit('confirm')
}
</script>
