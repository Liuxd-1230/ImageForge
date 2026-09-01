<template>
  <v-container fluid class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">生图历史</h1>
        <div class="text-caption text-grey">查看历史提示词与生图记录，支持一键将全部参数（含实际 Seed、模型与工作台配置）完整恢复到创作台 (Re-prompt)。</div>
      </div>
    </div>

    <v-row v-if="historyStore.history.length === 0">
      <v-col cols="12" class="text-center py-12 text-grey">
        <v-icon size="48" class="mb-2">mdi-history</v-icon>
        <div>暂无生图历史记录</div>
      </v-col>
    </v-row>

    <v-row v-else>
      <v-col
        v-for="item in historyStore.history"
        :key="item.id"
        cols="12"
        md="6"
      >
        <v-card variant="outlined" class="pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-2">
            <span class="text-caption text-grey">{{ formatDate(item.created_at) }}</span>
            <div>
              <v-btn size="small" variant="tonal" color="primary" class="mr-2" prepend-icon="mdi-restore" @click="restoreToStudio(item)">
                恢复到创作台
              </v-btn>
              <v-btn icon="mdi-delete" size="small" variant="text" color="error" @click="historyStore.deleteHistory(item.id)" />
            </div>
          </div>

          <div class="text-body-2 font-weight-bold mb-1">
            输入: {{ item.raw_input }}
          </div>

          <div class="d-flex flex-wrap gap-1 mb-2">
            <v-chip size="x-small" color="primary" variant="outlined">{{ item.safety }}</v-chip>
            <v-chip v-if="getSeed(item) !== undefined" size="x-small" color="teal" variant="outlined">
              Seed: {{ getSeed(item) }}
            </v-chip>
            <v-chip v-if="getArtistsCount(item) > 0" size="x-small" color="secondary" variant="outlined">
              画师 x{{ getArtistsCount(item) }}
            </v-chip>
            <v-chip v-if="getLorasCount(item) > 0" size="x-small" color="purple" variant="outlined">
              LoRA x{{ getLorasCount(item) }}
            </v-chip>
          </div>

          <div class="text-caption font-mono border rounded pa-2 mb-2 bg-surface text-truncate">
            {{ item.prompt }}
          </div>

          <div v-if="item.image_path" class="text-center mt-2">
            <v-img :src="item.image_path" max-height="220" contain class="rounded border" />
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useHistoryStore } from '../stores/history'
import { useStudioStore } from '../stores/studio'
import type { GenerationHistory, SafetyLevel } from '../types'

const historyStore = useHistoryStore()
const studioStore = useStudioStore()
const router = useRouter()

onMounted(() => {
  historyStore.fetchHistory()
})

function formatDate(d: string) {
  if (!d) return ''
  return new Date(d).toLocaleString('zh-CN')
}

function getSeed(item: GenerationHistory): number | undefined {
  try {
    if (item.comfy_params_json) {
      const p = JSON.parse(item.comfy_params_json)
      return p.seed
    }
  } catch {}
  return undefined
}

function getArtistsCount(item: GenerationHistory): number {
  try {
    return item.artists_json ? JSON.parse(item.artists_json).length : 0
  } catch {
    return 0
  }
}

function getLorasCount(item: GenerationHistory): number {
  try {
    return item.loras_json ? JSON.parse(item.loras_json).length : 0
  } catch {
    return 0
  }
}

function restoreToStudio(item: GenerationHistory) {
  studioStore.rawInput = item.raw_input
  studioStore.positivePrompt = item.prompt
  studioStore.negativePrompt = item.negative_prompt
  studioStore.safety = item.safety as SafetyLevel

  try {
    if (item.parsed_facts_json) {
      studioStore.facts = JSON.parse(item.parsed_facts_json)
    }
  } catch {}

  try {
    if (item.artists_json) {
      studioStore.selectedArtists = JSON.parse(item.artists_json)
    }
  } catch {}

  try {
    if (item.loras_json) {
      studioStore.activeLoras = JSON.parse(item.loras_json)
    }
  } catch {}

  try {
    if (item.comfy_params_json) {
      const params = JSON.parse(item.comfy_params_json)
      if (params.unet_name) studioStore.unetName = params.unet_name
      if (params.clip_name) studioStore.clipName = params.clip_name
      if (params.vae_name) studioStore.vaeName = params.vae_name
      if (params.width) studioStore.width = params.width
      if (params.height) studioStore.height = params.height
      if (params.steps) studioStore.steps = params.steps
      if (params.cfg) studioStore.cfg = params.cfg
      if (params.sampler_name) studioStore.samplerName = params.sampler_name
      if (params.scheduler) studioStore.scheduler = params.scheduler
      if (params.seed !== undefined) studioStore.seed = params.seed

      if (params.studio) {
        if (params.studio.selectedPresetId !== undefined) studioStore.selectedPresetId = params.studio.selectedPresetId
        if (params.studio.extraNegative !== undefined) studioStore.extraNegative = params.studio.extraNegative
        if (params.studio.provider) studioStore.provider = params.studio.provider
        if (params.studio.model) studioStore.model = params.studio.model
        if (params.studio.reasoningEffort) studioStore.reasoningEffort = params.studio.reasoningEffort
        if (params.studio.selectedRuleIds) studioStore.selectedRuleIds = params.studio.selectedRuleIds
      }
    }
  } catch {}

  if (item.image_path) {
    studioStore.generatedImageUrl = item.image_path
  }

  router.push('/')
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
</style>
