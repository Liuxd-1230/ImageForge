<template>
  <v-container fluid class="pa-4">
    <!-- Top Bar: Provider, Model, Thinking, Preset, Connection Status -->
    <v-card variant="outlined" class="mb-4 pa-3 rounded-lg bg-surface">
      <v-row align="center" dense>
        <!-- Provider & Model Selection -->
        <v-col cols="12" sm="6" md="3" class="d-flex align-center gap-2">
          <v-btn-toggle
            v-model="studioStore.provider"
            mandatory
            density="compact"
            color="primary"
            variant="outlined"
            @update:model-value="onProviderChange"
          >
            <v-btn value="lm_studio" size="small">LM Studio</v-btn>
            <v-btn value="cloud" size="small">云端 API</v-btn>
          </v-btn-toggle>
        </v-col>

        <v-col cols="12" sm="6" md="3" class="d-flex align-center gap-1">
          <v-select
            v-model="studioStore.model"
            :items="currentModelList"
            item-title="id"
            item-value="id"
            label="LLM 模型"
            density="compact"
            variant="outlined"
            hide-details
            class="flex-grow-1"
          />
          <v-btn
            icon="mdi-refresh"
            size="small"
            variant="text"
            color="primary"
            @click="refreshModels"
          />
        </v-col>

        <!-- Thinking Strength Slider/Select -->
        <v-col cols="12" sm="6" md="3" class="d-flex align-center gap-2">
          <v-select
            v-model="studioStore.reasoningEffort"
            :items="thinkingOptions"
            item-title="title"
            item-value="value"
            label="思考强度"
            density="compact"
            variant="outlined"
            hide-details
            class="flex-grow-1"
          />
        </v-col>

        <!-- Preset & Connection Status -->
        <v-col cols="12" sm="6" md="3" class="d-flex justify-end align-center gap-2">
          <v-select
            v-model="studioStore.selectedPresetId"
            :items="presetStore.presets"
            item-title="name"
            item-value="id"
            label="提示词预设"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width: 180px;"
            @update:model-value="onPresetChange"
          />
          <v-chip
            :color="currentProviderStatus === 'connected' ? 'success' : 'grey'"
            size="small"
            variant="tonal"
          >
            {{ currentProviderStatus === 'connected' ? 'LLM 在线' : 'LLM 离线' }}
          </v-chip>
          <v-chip
            :color="settingsStore.comfyStatus === 'connected' ? 'success' : 'grey'"
            size="small"
            variant="tonal"
          >
            {{ settingsStore.comfyStatus === 'connected' ? 'ComfyUI 在线' : 'ComfyUI 离线' }}
          </v-chip>
        </v-col>
      </v-row>
    </v-card>

    <v-row>
      <!-- LEFT COLUMN: Input, Rules, Semantic Facts -->
      <v-col cols="12" lg="6">
        <!-- Natural Language Input Card -->
        <v-card variant="outlined" class="mb-4 pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-2">
            <span class="text-subtitle-1 font-weight-bold">画面要求 (中文自然语言)</span>
            <!-- Safety 4-level Segmented Control -->
            <v-btn-toggle
              v-model="studioStore.safety"
              mandatory
              density="compact"
              color="primary"
              variant="outlined"
              @update:model-value="studioStore.buildPrompt()"
            >
              <v-btn value="Safe" size="small">Safe</v-btn>
              <v-btn value="Sensitive" size="small">Sensitive</v-btn>
              <v-btn value="NSFW" size="small">NSFW</v-btn>
              <v-btn value="Explicit" size="small">Explicit</v-btn>
            </v-btn-toggle>
          </div>

          <v-textarea
            v-model="studioStore.rawInput"
            placeholder="例如：穗穗穿着泳装，秧秧穿着蓝色海军水手服，穗穗在沙滩上追秧秧。"
            rows="3"
            variant="outlined"
            density="comfortable"
            auto-grow
            hide-details
            class="mb-3"
          />

          <!-- Rule Files Selection Chips -->
          <div v-if="ruleStore.rules.length > 0" class="d-flex align-center gap-2 mb-3 flex-wrap">
            <span class="text-caption text-grey">参考规则:</span>
            <v-chip
              v-for="rule in ruleStore.rules"
              :key="rule.id"
              size="small"
              :variant="studioStore.selectedRuleIds.includes(rule.id) ? 'flat' : 'outlined'"
              :color="studioStore.selectedRuleIds.includes(rule.id) ? 'primary' : 'default'"
              @click="toggleRule(rule.id)"
            >
              <v-icon start size="14">mdi-file-document-outline</v-icon>
              {{ rule.name }}
            </v-chip>
          </div>

          <div class="d-flex justify-end">
            <v-btn
              color="primary"
              variant="flat"
              :loading="studioStore.isParsing"
              prepend-icon="mdi-brain"
              size="large"
              @click="studioStore.parsePrompt()"
            >
              解析提示词
            </v-btn>
          </div>
        </v-card>

        <!-- Semantic Analysis & Fact Preview Card -->
        <v-card variant="outlined" class="mb-4 pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-3">
            <div class="d-flex align-center">
              <v-icon color="primary" class="mr-2">mdi-graph</v-icon>
              <span class="text-subtitle-1 font-weight-bold">系统理解与语义事实</span>
            </div>
            <v-btn
              size="small"
              variant="text"
              color="primary"
              prepend-icon="mdi-refresh"
              :loading="studioStore.isBuilding"
              @click="studioStore.buildPrompt()"
            >
              重新编译 Prompt
            </v-btn>
          </div>

          <div v-if="studioStore.facts.entities.length === 0 && studioStore.facts.statements.length === 0" class="text-center py-6 text-grey">
            <v-icon size="40" class="mb-2">mdi-card-text-outline</v-icon>
            <div>输入画面描述后点击“解析提示词”，系统将提取人物、服装归属与动作关系。</div>
          </div>

          <div v-else>
            <!-- Identified Characters with Trigger & Caption editor -->
            <div class="mb-4">
              <div class="text-caption font-weight-bold text-grey mb-2">识别人物与 Trigger 映射</div>
              <v-row dense>
                <v-col
                  v-for="entity in studioStore.facts.entities"
                  :key="entity.id"
                  cols="12"
                  sm="6"
                >
                  <v-card variant="tonal" class="pa-3 rounded-md">
                    <div class="d-flex justify-space-between align-center mb-2">
                      <span class="font-weight-bold">{{ entity.name }}</span>
                      <v-chip
                        size="x-small"
                        :color="entity.source === 'user_defined' ? 'purple' : 'blue'"
                        variant="flat"
                      >
                        {{ entity.source === 'user_defined' ? '用户角色书' : '模型角色' }}
                      </v-chip>
                    </div>

                    <div v-if="entity.source === 'model_character'">
                      <div class="d-flex gap-1 align-center mb-1">
                        <v-text-field
                          v-model="entity.canonical_tag"
                          label="Canonical Tag"
                          density="compact"
                          variant="outlined"
                          hide-details
                          class="font-mono text-caption"
                        />
                        <v-text-field
                          v-model="entity.caption_name"
                          label="Caption Name"
                          density="compact"
                          variant="outlined"
                          hide-details
                          class="font-mono text-caption"
                        />
                        <v-btn
                          icon="mdi-content-save"
                          size="small"
                          variant="text"
                          color="primary"
                          title="保存映射至缓存"
                          @click="studioStore.saveEntityTrigger(entity)"
                        />
                      </div>
                    </div>
                    <div v-else class="text-caption text-grey">
                      展开设定: {{ entity.custom_description || '无额外属性' }}
                    </div>
                  </v-card>
                </v-col>
              </v-row>
            </div>

            <!-- Identified Statements -->
            <div>
              <div class="text-caption font-weight-bold text-grey mb-2">事实陈述列表</div>
              <v-list density="compact" class="bg-transparent pa-0">
                <v-list-item
                  v-for="(statement, idx) in studioStore.facts.statements"
                  :key="idx"
                  class="mb-2 rounded border pa-2"
                >
                  <div class="d-flex align-center justify-space-between">
                    <div class="d-flex align-center flex-grow-1 mr-2">
                      <v-chip size="x-small" class="mr-2" variant="outlined">
                        {{ statement.kind }}
                      </v-chip>
                      <span class="text-body-2 font-weight-medium">
                        {{ statement.subject ? getEntityName(statement.subject) : '场景' }}
                        <span class="text-grey mx-1">→</span>
                        {{ statement.text }}
                        <template v-if="statement.target">
                          <span class="text-grey mx-1">→</span>
                          {{ getEntityName(statement.target) }}
                        </template>
                      </span>
                    </div>

                    <div class="d-flex align-center">
                      <v-chip
                        v-if="statement.facet"
                        size="x-small"
                        color="secondary"
                        variant="tonal"
                        class="mr-2"
                      >
                        {{ statement.facet }}
                      </v-chip>
                      <v-btn
                        icon="mdi-close"
                        size="x-small"
                        variant="text"
                        color="grey"
                        @click="studioStore.removeStatement(idx)"
                      />
                    </div>
                  </div>
                </v-list-item>
              </v-list>
            </div>
          </div>
        </v-card>

        <!-- IN-STUDIO ARTISTS & LORA CONTROLS -->
        <v-row>
          <!-- Artist In-Studio Selector -->
          <v-col cols="12" md="6">
            <v-card variant="outlined" class="pa-3 rounded-lg bg-surface h-100">
              <div class="d-flex justify-space-between align-center mb-2">
                <span class="text-subtitle-2 font-weight-bold">
                  <v-icon size="18" color="info" class="mr-1">mdi-brush</v-icon>
                  本次画师
                </span>
                <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-plus" @click="artistExplorerDialog = true">
                  浏览添加
                </v-btn>
              </div>

              <div v-if="studioStore.selectedArtists.length === 0" class="text-caption text-grey py-3 text-center">
                未选择画师（Prompt 中将不包含画师 Tag）
              </div>
              <div v-else class="d-flex flex-wrap gap-1">
                <v-chip
                  v-for="art in studioStore.selectedArtists"
                  :key="art.id"
                  closable
                  size="small"
                  color="info"
                  variant="tonal"
                  @click:close="studioStore.toggleArtist(art)"
                >
                  {{ art.name }} ({{ art.tags }})
                </v-chip>
              </div>
            </v-card>
          </v-col>

          <!-- LoRA In-Studio Selector & Strength Sliders -->
          <v-col cols="12" md="6">
            <v-card variant="outlined" class="pa-3 rounded-lg bg-surface h-100">
              <div class="d-flex justify-space-between align-center mb-2">
                <span class="text-subtitle-2 font-weight-bold">
                  <v-icon size="18" color="purple" class="mr-1">mdi-toy-brick</v-icon>
                  本次 LoRA (权重联动)
                </span>
                <span class="text-caption text-grey">已启用: {{ studioStore.activeLoras.filter(l => l.isEnabled).length }}</span>
              </div>

              <div v-if="studioStore.activeLoras.length === 0" class="text-caption text-grey py-3 text-center">
                LoRA 库为空，请先在 LoRA 库中扫描或添加。
              </div>
              <div v-else class="lora-scroll-area">
                <div
                  v-for="item in studioStore.activeLoras"
                  :key="item.lora.id"
                  class="d-flex align-center justify-space-between pa-1 border-b"
                >
                  <v-checkbox
                    v-model="item.isEnabled"
                    :label="item.lora.name"
                    density="compact"
                    hide-details
                    color="purple"
                    class="mr-2"
                    @update:model-value="studioStore.buildPrompt()"
                  />
                  <div class="d-flex align-center" style="width: 140px;">
                    <v-slider
                      v-model="item.strength"
                      min="0.1"
                      max="1.5"
                      step="0.05"
                      density="compact"
                      hide-details
                      thumb-label
                      color="purple"
                      :disabled="!item.isEnabled"
                      @update:model-value="studioStore.buildPrompt()"
                    />
                    <span class="text-caption ml-1 font-mono" style="width: 32px;">{{ item.strength.toFixed(2) }}</span>
                  </div>
                </div>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-col>

      <!-- RIGHT COLUMN: Output & ComfyUI Generation -->
      <v-col cols="12" lg="6">
        <!-- Prompt Preview Card -->
        <v-card variant="outlined" class="mb-4 pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-2">
            <span class="text-subtitle-1 font-weight-bold">最终 Anima Prompt (英文)</span>
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              prepend-icon="mdi-content-copy"
              @click="copyToClipboard(studioStore.positivePrompt)"
            >
              复制 Prompt
            </v-btn>
          </div>
          <v-textarea
            v-model="studioStore.positivePrompt"
            rows="5"
            variant="outlined"
            density="compact"
            auto-grow
            class="font-mono text-body-2 mb-3"
            hide-details
          />

          <!-- Negative Prompt Section -->
          <div class="d-flex justify-space-between align-center mb-2">
            <span class="text-subtitle-2 font-weight-bold text-grey">Negative Prompt</span>
            <v-btn
              size="small"
              variant="text"
              color="grey"
              prepend-icon="mdi-content-copy"
              @click="copyToClipboard(studioStore.negativePrompt)"
            >
              复制 Negative
            </v-btn>
          </div>
          
          <v-textarea
            v-model="studioStore.negativePrompt"
            rows="3"
            variant="outlined"
            density="compact"
            auto-grow
            class="font-mono text-caption mb-3"
            hide-details
          />

          <v-text-field
            v-model="studioStore.extraNegative"
            label="本次额外 Negative (如: extra hands, text)"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="studioStore.buildPrompt()"
          />
        </v-card>

        <!-- ComfyUI Generation & Image Output Card -->
        <v-card variant="outlined" class="pa-4 rounded-lg bg-surface">
          <div class="d-flex justify-space-between align-center mb-3">
            <div class="d-flex align-center">
              <v-icon color="success" class="mr-2">mdi-image-multiple</v-icon>
              <span class="text-subtitle-1 font-weight-bold">ComfyUI 生图控制 (Anima 2.9B)</span>
            </div>
            <v-btn
              color="success"
              variant="flat"
              prepend-icon="mdi-play"
              size="large"
              :loading="studioStore.isGenerating"
              @click="studioStore.generateImage()"
            >
              开始生图
            </v-btn>
          </div>

          <!-- Generation Parameters (Anima-2.9B standards) -->
          <v-row dense class="mb-3">
            <v-col cols="6" sm="3">
              <v-select
                v-model="studioStore.width"
                :items="[812, 1024, 1152, 1280]"
                label="宽度"
                density="compact"
                variant="outlined"
                hide-details
              />
            </v-col>
            <v-col cols="6" sm="3">
              <v-select
                v-model="studioStore.height"
                :items="[1216, 1536, 1792]"
                label="高度"
                density="compact"
                variant="outlined"
                hide-details
              />
            </v-col>
            <v-col cols="6" sm="3">
              <v-text-field
                v-model.number="studioStore.steps"
                label="Steps (28-50)"
                density="compact"
                variant="outlined"
                type="number"
                hide-details
              />
            </v-col>
            <v-col cols="6" sm="3">
              <v-text-field
                v-model.number="studioStore.cfg"
                label="CFG (3.5-5.0)"
                density="compact"
                variant="outlined"
                type="number"
                step="0.5"
                hide-details
              />
            </v-col>
          </v-row>

          <!-- Generation Progress Bar -->
          <div v-if="studioStore.isGenerating" class="mb-4">
            <div class="d-flex justify-space-between text-caption mb-1">
              <span>{{ studioStore.generationMessage }}</span>
              <span>{{ studioStore.generationProgress }}%</span>
            </div>
            <v-progress-linear
              v-model="studioStore.generationProgress"
              color="success"
              height="6"
              rounded
            />
          </div>

          <!-- Rendered Image Result -->
          <div v-if="studioStore.generatedImageUrl" class="text-center mt-3">
            <v-img
              :src="studioStore.generatedImageUrl"
              max-height="460"
              contain
              class="rounded-lg border bg-black cursor-pointer"
            />
          </div>
          <div v-else class="text-center py-8 text-grey border rounded-lg">
            <v-icon size="48" class="mb-2">mdi-image-outline</v-icon>
            <div>准备就绪，点击“开始生图”由 ComfyUI 渲染。</div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- ARTIST EXPLORER MODAL DIALOG (Mini Anima Style Explorer) -->
    <v-dialog v-model="artistExplorerDialog" max-width="800px">
      <v-card class="pa-4 rounded-lg bg-surface">
        <div class="d-flex justify-space-between align-center mb-3">
          <div class="d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-palette-swatch</v-icon>
            <span class="text-h6 font-weight-bold">画师库浏览器</span>
          </div>
          <v-btn icon="mdi-close" variant="text" size="small" @click="artistExplorerDialog = false" />
        </div>

        <v-text-field
          v-model="artistSearchQuery"
          label="搜索画师名称或 Tag"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          class="mb-3"
          clearable
        />

        <div class="artist-grid">
          <v-card
            v-for="art in filteredArtists"
            :key="art.id"
            variant="outlined"
            :class="['pa-3', 'rounded-lg', 'artist-card', isArtistSelected(art) ? 'selected-card' : '']"
            @click="studioStore.toggleArtist(art)"
          >
            <div class="d-flex justify-space-between align-center mb-1">
              <span class="font-weight-bold text-subtitle-2">{{ art.name }}</span>
              <v-icon :color="isArtistSelected(art) ? 'primary' : 'grey'">
                {{ isArtistSelected(art) ? 'mdi-checkbox-marked-circle' : 'mdi-checkbox-blank-circle-outline' }}
              </v-icon>
            </div>
            <div class="text-caption font-mono text-primary mb-1">
              <code>{{ art.tags }}</code>
            </div>
            <div class="text-caption text-grey text-truncate">
              {{ art.description || art.category }}
            </div>
          </v-card>
        </div>

        <v-card-actions class="justify-end mt-3">
          <v-btn color="primary" variant="flat" @click="artistExplorerDialog = false">完成选择</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="2000" color="primary">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useStudioStore } from '../stores/studio'
import { usePresetStore } from '../stores/presets'
import { useSettingsStore } from '../stores/settings'
import { useCharacterStore } from '../stores/character'
import { useArtistStore } from '../stores/artist'
import { useLoraStore } from '../stores/lora'
import { useRuleStore } from '../stores/rules'
import type { Artist } from '../types'

const studioStore = useStudioStore()
const presetStore = usePresetStore()
const settingsStore = useSettingsStore()
const characterStore = useCharacterStore()
const artistStore = useArtistStore()
const loraStore = useLoraStore()
const ruleStore = useRuleStore()

const artistExplorerDialog = ref(false)
const artistSearchQuery = ref('')
const snackbar = ref(false)
const snackbarText = ref('')

const thinkingOptions = [
  { title: 'Instruct (关闭思考)', value: 'instruct' },
  { title: 'Low (轻度思考)', value: 'low' },
  { title: 'Medium (标准思考)', value: 'medium' },
  { title: 'High (深度思考)', value: 'high' },
  { title: 'Xhigh (极高思考)', value: 'xhigh' },
  { title: 'Max (最大思考)', value: 'max' },
]

const currentModelList = computed(() => {
  return studioStore.provider === 'lm_studio' ? settingsStore.lmStudioModels : settingsStore.cloudModels
})

const currentProviderStatus = computed(() => {
  return studioStore.provider === 'lm_studio' ? settingsStore.lmStudioStatus : settingsStore.cloudStatus
})

const filteredArtists = computed(() => {
  let list = artistStore.artists
  if (artistSearchQuery.value) {
    const q = artistSearchQuery.value.toLowerCase()
    list = list.filter(a => a.name.toLowerCase().includes(q) || a.tags.toLowerCase().includes(q))
  }
  return list
})

onMounted(async () => {
  await Promise.all([
    presetStore.fetchPresets(),
    settingsStore.fetchSettings(),
    characterStore.fetchCharacters(),
    artistStore.fetchArtists(),
    loraStore.fetchLoras(),
    ruleStore.fetchRules()
  ])

  // Sync LoRAs into studio state
  studioStore.syncLorasFromLibrary(loraStore.loras)

  // Default preset
  if (!studioStore.selectedPresetId && presetStore.presets.length > 0) {
    const def = presetStore.presets.find(p => p.is_default) || presetStore.presets[0]
    studioStore.selectedPresetId = def.id
    studioStore.safety = def.default_safety
  }

  // Set default model
  if (!studioStore.model) {
    if (studioStore.provider === 'lm_studio' && settingsStore.lmStudioModels.length > 0) {
      studioStore.model = settingsStore.lmStudioModels[0].id
    }
  }
})

function onProviderChange(p: string) {
  studioStore.provider = p as 'lm_studio' | 'cloud'
  if (p === 'lm_studio' && settingsStore.lmStudioModels.length > 0) {
    studioStore.model = settingsStore.lmStudioModels[0].id
  } else if (p === 'cloud' && settingsStore.cloudModels.length > 0) {
    studioStore.model = settingsStore.cloudModels[0].id
  }
}

async function refreshModels() {
  if (studioStore.provider === 'lm_studio') {
    await settingsStore.checkLMStudioHealth()
  } else {
    await settingsStore.checkCloudHealth()
  }
}

function onPresetChange(presetId: number) {
  const p = presetStore.presets.find(item => item.id === presetId)
  if (p) {
    studioStore.safety = p.default_safety
    studioStore.buildPrompt()
  }
}

function toggleRule(ruleId: number) {
  const idx = studioStore.selectedRuleIds.indexOf(ruleId)
  if (idx !== -1) {
    studioStore.selectedRuleIds.splice(idx, 1)
  } else {
    studioStore.selectedRuleIds.push(ruleId)
  }
}

function isArtistSelected(art: Artist): boolean {
  return studioStore.selectedArtists.some(a => a.id === art.id)
}

function getEntityName(entityId: string): string {
  const e = studioStore.facts.entities.find(item => item.id === entityId)
  return e ? e.name : entityId
}

function copyToClipboard(text: string) {
  if (!text) return
  navigator.clipboard.writeText(text)
  snackbarText.value = '已复制到剪贴板'
  snackbar.value = true
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.font-mono { font-family: monospace; }
.lora-scroll-area {
  max-height: 140px;
  overflow-y: auto;
}
.artist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}
.artist-card {
  cursor: pointer;
  transition: all 0.2s ease;
}
.artist-card:hover {
  border-color: #3F51B5;
}
.selected-card {
  border-color: #3F51B5 !important;
  background-color: rgba(63, 81, 181, 0.08) !important;
}
</style>
