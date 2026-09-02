<template>
  <div class="d-flex align-center gap-2 ml-auto">
    <template v-if="selectedCount > 0">
      <span class="text-caption font-mono">已选择 {{ selectedCount }} 项</span>
      <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete" @click="$emit('delete')">
        删除所选
      </v-btn>
    </template>
    <v-btn
      size="small"
      variant="tonal"
      :prepend-icon="isAllSelected ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline'"
      @click="$emit('toggle-all')"
    >
      {{ isAllSelected ? '取消全选' : '全选' }}
    </v-btn>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  selectedCount: number
  isAllSelected: boolean
}>()
defineEmits<{ (e: 'toggle-all'): void; (e: 'delete'): void }>()
</script>
