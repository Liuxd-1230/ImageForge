<template>
  <v-dialog :model-value="open" max-width="440px" @update:model-value="v => !v && $emit('cancel')">
    <v-card class="pa-4 bg-surface rounded-2xl">
      <div class="d-flex align-center gap-2 mb-2">
        <v-icon color="error">mdi-delete-alert-outline</v-icon>
        <span class="text-subtitle-1 font-weight-bold">{{ title || ('删除所选 ' + count + ' 项？') }}</span>
      </div>
      <p class="text-caption text-grey mb-0">{{ semantics }}</p>
      <v-card-actions class="justify-end mt-3 pt-2 border-t">
        <v-btn variant="text" size="small" @click="$emit('cancel')">取消</v-btn>
        <v-btn color="error" variant="flat" size="small" :loading="loading" @click="$emit('confirm')">删除</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
defineProps<{
  open: boolean
  count: number
  semantics: string
  loading?: boolean
  title?: string
}>()
defineEmits<{ (e: 'confirm'): void; (e: 'cancel'): void }>()
</script>
