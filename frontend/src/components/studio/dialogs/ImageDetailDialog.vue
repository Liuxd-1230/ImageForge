<template>
  <v-dialog v-model="modelValueProxy" max-width="1100px">
    <v-card class="rounded-xl overflow-hidden bg-surface">
      <div class="d-flex align-center justify-space-between px-4 py-3 border-b">
        <div class="d-flex align-center gap-2">
          <v-icon color="primary" size="20">mdi-image-outline</v-icon>
          <span class="font-weight-bold text-subtitle-2">原画高清视口</span>
        </div>
        <div class="d-flex align-center gap-2">
          <v-btn
            icon="mdi-tray-arrow-down"
            variant="text"
            size="small"
            title="下载原图"
            @click="downloadImage"
          />
          <v-btn icon="mdi-close" variant="text" size="small" @click="modelValueProxy = false" />
        </div>
      </div>

      <div class="d-flex align-center justify-center bg-black pa-4" style="max-height: 82vh; overflow: auto;">
        <img :src="imageUrl" class="detail-preview-img" alt="Artwork Detail" />
      </div>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: boolean
  imageUrl: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const modelValueProxy = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

function downloadImage() {
  if (!props.imageUrl) return
  const a = document.createElement('a')
  a.href = props.imageUrl
  a.download = `anima_${Date.now()}.png`
  a.click()
}
</script>

<style scoped>
.detail-preview-img {
  max-width: 100%;
  max-height: 76vh;
  object-fit: contain;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}
</style>
