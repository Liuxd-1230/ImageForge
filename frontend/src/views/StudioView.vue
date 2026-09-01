<template>
  <div class="app-page-container">
    <!-- Top Compact Desktop Toolbar -->
    <v-card variant="outlined" class="mb-3 px-3 py-2 bg-surface rounded-lg">
      <div class="d-flex align-center justify-space-between flex-wrap gap-2">
        <!-- Provider & Model Controls -->
        <div class="d-flex align-center gap-2 flex-grow-1 flex-sm-grow-0">
          <v-btn-toggle
            v-model="studioStore.provider"
            mandatory
            density="compact"
            color="primary"
            variant="outlined"
            rounded="md"
            class="toolbar-toggle"
            @update:model-value="onProviderChange"
          >
            <v-btn value="lm_studio" size="small" class="px-3">LM Studio</v-btn>
            <v-btn value="cloud" size="small" class="px-3">云端 API</v-btn>
          </v-btn-toggle>

          <div class="d-flex align-center gap-1" style="min-width: 200px; max-width: 280px;">
            <v-select
              v-model="studioStore.model"
              :items="currentModelList"
              item-title="id"
              item-value="id"
              label="LLM 模型"
              density="compact"
              variant="outlined"
              hide-details
              class="flex-grow-1 text-caption"
            />
            <v-btn
              icon="mdi-refresh"
              size="x-small"
              variant="text"
              color="secondary"
              title="刷新模型列表"
              @click="refreshModels"
            />
          </div>

          <v-select
            v-model="studioStore.reasoningEffort"
            :items="activeThinkingOptions"
            item-title="title"
            item-value="value"
            label="思考强度"
            density="compact"
            variant="outlined"
            hide-details
            style="min-width: 140px; max-width: 170px;"
            class="text-caption"
          />
        </div>

        <!-- Preset & Engine Health Statuses -->
        <div class="d-flex align-center justify-end gap-2 flex-grow-1 flex-sm-grow-0">
          <v-select
            v-model="studioStore.selectedPresetId"
            :items="presetStore.presets"
            item-title="name"
            item-value="id"
            label="提示词预设"
            density="compact"
            variant="outlined"
            hide-details
            style="min-width: 140px; max-width: 180px;"
            @update:model-value="onPresetChange"
          />

          <!-- Live Status Indicators -->
          <div class="d-flex align-center gap-2 px-2 py-1 rounded bg-surface-variant text-caption">
            <div class="d-flex align-center gap-1" :title="`LLM 状态: ${currentProviderStatus}`">
              <span :class="['status-indicator', currentProviderStatus === 'connected' ? 'online' : 'offline']" />
              <span class="text-caption font-weight-medium">LLM</span>
            </div>
            <v-divider vertical class="my-1" />
            <div class="d-flex align-center gap-1" :title="`ComfyUI 状态: ${settingsStore.comfyStatus}`">
              <span :class="['status-indicator', settingsStore.comfyStatus === 'connected' ? 'online' : 'offline']" />
              <span class="text-caption font-weight-medium">ComfyUI</span>
            </div>
          </div>
        </div>
      </div>
    </v-card>

    <!-- Main 2-Column Workstation Grid -->
    <v-row dense>
      <!-- LEFT COLUMN (~46%): Input, Rules, Semantic Facts & Ownership -->
      <v-col cols="12" lg="6">
        <!-- Natural Language Input Section -->
        <v-card variant="outlined" class="mb-3 pa-3 bg-surface rounded-lg">
          <div class="d-flex justify-space-between align-center mb-2">
            <span class="section-label text-primary">画面要求 (自然语言)</span>
            
            <!-- Safety 4-level Segmented Control -->
            <v-btn-toggle
              v-model="studioStore.safety"
              mandatory
              density="compact"
              color="primary"
              variant="outlined"
              rounded="md"
              @update:model-value="studioStore.buildPrompt()"
            >
              <v-btn value="Safe" size="x-small" class="px-2">Safe</v-btn>
              <v-btn value="Sensitive" size="x-small" class="px-2">Sensitive</v-btn>
              <v-btn value="NSFW" size="x-small" class="px-2">NSFW</v-btn>
              <v-btn value="Explicit" size="x-small" class="px-2">Explicit</v-btn>
            </v-btn-toggle>
          </div>

          <v-textarea
            v-model="studioStore.rawInput"
            placeholder="例如：穗穗穿着泳装，秧秧穿着蓝色海军水手服，穗穗在沙滩上追秧秧。"
            rows="3"
            variant="outlined"
            density="compact"
            auto-grow
            hide-details
            class="mb-2 text-body-2"
            @input="studioStore.isSemanticDirty = true"
          />

          <!-- Rule Selection Chips -->
          <div v-if="activeRules.length > 0" class="d-flex align-center gap-1 mb-3 flex-wrap">
            <span class="text-caption text-grey mr-1">参考规则:</span>
            <v-chip
              v-for="rule in activeRules"
              :key="rule.id"
              size="x-small"
              :variant="studioStore.selectedRuleIds.includes(rule.id) ? 'flat' : 'outlined'"
              :color="studioStore.selectedRuleIds.includes(rule.id) ? 'primary' : 'default'"
              @click="toggleRule(rule.id)"
            >
              <v-icon start size="12">mdi-file-document-outline</v-icon>
              {{ rule.name }}
            </v-chip>
          </div>

          <div class="d-flex justify-space-between align-center pt-1 border-t">
            <div class="d-flex align-center gap-1">
              <v-chip v-if="studioStore.isSemanticDirty" size="x-small" color="warning" variant="tonal">
                画面描述有修改，待重新解析
              </v-chip>
            </div>
            <v-btn
              color="primary"
              variant="flat"
              :loading="studioStore.isParsing"
              prepend-icon="mdi-creation"
              size="small"
              class="font-weight-medium px-4"
              @click="studioStore.parsePrompt()"
            >
              解析语义事实
            </v-btn>
          </div>
        </v-card>

        <!-- Semantic Understanding & Facts Area -->
        <v-card variant="outlined" class="mb-3 pa-3 bg-surface rounded-lg">
          <div class="d-flex justify-space-between align-center mb-2 pb-1 border-b">
            <div class="d-flex align-center gap-1">
              <span class="section-label">系统理解与事实解析</span>
            </div>
            <v-btn
              size="x-small"
              variant="text"
              color="primary"
              prepend-icon="mdi-sync"
              :loading="studioStore.isBuilding"
              @click="studioStore.buildPrompt(true)"
            >
              重新编译 Prompt
            </v-btn>
          </div>

          <!-- Empty State -->
          <div v-if="studioStore.facts.entities.length === 0 && studioStore.facts.statements.length === 0" class="text-center py-5 text-grey">
            <v-icon size="32" class="mb-1 opacity-60">mdi-text-box-search-outline</v-icon>
            <div class="text-caption">输入描述并解析后，此处将呈现结构化人物、服装与动作关系。</div>
          </div>

          <div v-else>
            <!-- Character Entities List -->
            <div class="mb-3">
              <div class="text-caption font-weight-bold text-grey mb-1">人物实体与 Trigger 绑定:</div>
              <div class="d-flex flex-column gap-1">
                <div
                  v-for="entity in studioStore.facts.entities"
                  :key="entity.id"
                  :class="[
                    'pa-2 rounded border',
                    entity.source === 'model_character' && !entity.canonical_tag
                      ? 'border-error bg-red-lighten-5'
                      : 'bg-surface-variant'
                  ]"
                >
                  <div class="d-flex justify-space-between align-center">
                    <div class="d-flex align-center gap-2">
                      <span class="font-weight-bold text-body-2">{{ entity.name }}</span>
                      <v-chip
                        size="x-small"
                        :color="entity.source === 'user_defined' ? 'purple' : (entity.source === 'model_character' ? 'primary' : 'teal')"
                        variant="tonal"
                      >
                        {{ entity.source === 'user_defined' ? '用户角色书' : (entity.source === 'model_character' ? '模型角色' : '通用人物') }}
                      </v-chip>
                    </div>

                    <div v-if="entity.source === 'user_defined'" class="text-caption text-grey text-truncate">
                      {{ entity.custom_description || '展开角色设定' }}
                    </div>
                    <div v-else-if="!entity.source" class="text-caption font-mono text-grey">
                      {{ entity.caption_name || 'the character' }}
                    </div>
                  </div>

                  <!-- Unresolved Trigger Editor -->
                  <div v-if="entity.source === 'model_character' && (!entity.canonical_tag || !entity.caption_name)" class="mt-2 pt-2 border-t">
                    <div class="text-caption text-error mb-1">
                      未能自动识别该角色 Trigger，请手动填写保存：
                    </div>
                    <div class="d-flex gap-1 align-center">
                      <v-text-field
                        v-model="entity.canonical_tag"
                        label="Canonical Tag (如: suisui)"
                        density="compact"
                        variant="outlined"
                        hide-details
                        class="font-mono text-caption"
                      />
                      <v-text-field
                        v-model="entity.caption_name"
                        label="Caption Name (如: Suisui)"
                        density="compact"
                        variant="outlined"
                        hide-details
                        class="font-mono text-caption"
                      />
                      <v-btn
                        size="small"
                        color="primary"
                        variant="flat"
                        :disabled="!entity.canonical_tag || !entity.caption_name"
                        @click="saveEntityTrigger(entity)"
                      >
                        保存
                      </v-btn>
                    </div>
                  </div>
                  <div v-else-if="entity.source === 'model_character'" class="d-flex gap-2 text-caption font-mono text-grey mt-1">
                    <span>Tag: <strong class="text-primary">{{ entity.canonical_tag }}</strong></span>
                    <span>Caption: <strong class="text-primary">{{ entity.caption_name }}</strong></span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Statements List -->
            <div>
              <div class="text-caption font-weight-bold text-grey mb-1">事实陈述列表:</div>
              <div class="d-flex flex-column gap-1">
                <div
                  v-for="(statement, idx) in studioStore.facts.statements"
                  :key="idx"
                  class="d-flex align-center justify-space-between px-2 py-1 rounded border bg-surface text-caption"
                >
                  <div class="d-flex align-center gap-1 text-truncate">
                    <v-chip size="x-small" variant="outlined" class="text-uppercase" style="font-size: 0.65rem;">
                      {{ statement.kind }}
                    </v-chip>
                    <span class="font-weight-medium">
                      {{ statement.subject ? getEntityName(statement.subject) : '场景' }}
                    </span>
                    <span class="text-grey">→</span>
                    <span class="font-mono text-high-emphasis">{{ statement.text }}</span>
                    <template v-if="statement.target">
                      <span class="text-grey">→</span>
                      <span class="font-weight-medium">{{ getEntityName(statement.target) }}</span>
                    </template>
                  </div>

                  <div class="d-flex align-center gap-1 flex-shrink-0">
                    <v-chip v-if="statement.facet" size="x-small" color="secondary" variant="tonal">
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
              </div>
            </div>
          </div>
        </v-card>

        <!-- Active Artists & LoRAs Control Bar -->
        <v-row dense>
          <!-- Active Artists -->
          <v-col cols="12" sm="6">
            <v-card variant="outlined" class="pa-2 bg-surface rounded-lg h-100">
              <div class="d-flex justify-space-between align-center mb-1">
                <span class="section-label text-info">画师选择 (Artist)</span>
                <v-btn size="x-small" variant="tonal" color="info" prepend-icon="mdi-plus" @click="artistExplorerDialog = true">
                  添加画师
                </v-btn>
              </div>
              <div v-if="studioStore.selectedArtists.length === 0" class="text-caption text-grey py-2 text-center">
                未选择画师
              </div>
              <div v-else class="d-flex flex-wrap gap-1">
                <v-chip
                  v-for="art in studioStore.selectedArtists"
                  :key="art.id"
                  closable
                  size="x-small"
                  color="info"
                  variant="tonal"
                  @click:close="studioStore.toggleArtist(art)"
                >
                  {{ art.name }}
                </v-chip>
              </div>
            </v-card>
          </v-col>

          <!-- Active LoRAs -->
          <v-col cols="12" sm="6">
            <v-card variant="outlined" class="pa-2 bg-surface rounded-lg h-100">
              <div class="d-flex justify-space-between align-center mb-1">
                <span class="section-label text-purple">本次 LoRA 挂载</span>
                <span class="text-caption text-grey font-mono">{{ studioStore.activeLoras.filter(l => l.isEnabled).length }} 项启用</span>
              </div>
              <div v-if="studioStore.activeLoras.length === 0" class="text-caption text-grey py-2 text-center">
                LoRA 库为空
              </div>
              <div v-else class="lora-scroll-area">
                <div
                  v-for="item in studioStore.activeLoras"
                  :key="item.lora.id"
                  class="d-flex align-center justify-space-between py-1 border-b text-caption"
                >
                  <v-checkbox
                    v-model="item.isEnabled"
                    :label="item.lora.name"
                    density="compact"
                    hide-details
                    color="purple"
                    class="mr-1 text-truncate"
                    @update:model-value="studioStore.buildPrompt()"
                  />
                  <div class="d-flex align-center" style="width: 120px;">
                    <v-slider
                      v-model="item.strength"
                      min="0.1"
                      max="1.5"
                      step="0.05"
                      density="compact"
                      hide-details
                      color="purple"
                      :disabled="!item.isEnabled"
                      @update:model-value="studioStore.buildPrompt()"
                    />
                    <span class="text-caption ml-1 font-mono text-grey" style="width: 28px;">{{ item.strength.toFixed(2) }}</span>
                  </div>
                </div>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-col>

      <!-- RIGHT COLUMN (~54%): Code Editor Prompt, Generation Params & Large Image Canvas -->
      <v-col cols="12" lg="6">
        <!-- Prompt Editor Box -->
        <v-card variant="outlined" class="mb-3 pa-3 bg-surface rounded-lg">
          <!-- Positive Prompt -->
          <div class="d-flex justify-space-between align-center mb-1">
            <div class="d-flex align-center gap-1">
              <span class="section-label text-success">Positive Prompt (Anima-2.9B)</span>
              <v-chip v-if="studioStore.isPositivePromptDirty" size="x-small" color="warning" variant="flat">
                已手动编辑
              </v-chip>
            </div>
            <v-btn
              size="x-small"
              variant="text"
              color="primary"
              prepend-icon="mdi-content-copy"
              @click="copyToClipboard(studioStore.positivePrompt)"
            >
              复制
            </v-btn>
          </div>

          <div class="prompt-editor-card mb-2">
            <v-textarea
              v-model="studioStore.positivePrompt"
              rows="4"
              variant="plain"
              density="compact"
              auto-grow
              hide-details
              class="prompt-textarea px-2 py-1"
              @input="studioStore.isPositivePromptDirty = true"
            />
          </div>

          <!-- Negative Prompt -->
          <div class="d-flex justify-space-between align-center mb-1">
            <div class="d-flex align-center gap-1">
              <span class="section-label text-secondary">Negative Prompt</span>
              <v-chip v-if="studioStore.isNegativePromptDirty" size="x-small" color="warning" variant="flat">
                已手动编辑
              </v-chip>
            </div>
            <v-btn
              size="x-small"
              variant="text"
              color="grey"
              prepend-icon="mdi-content-copy"
              @click="copyToClipboard(studioStore.negativePrompt)"
            >
              复制
            </v-btn>
          </div>

          <div class="prompt-editor-card mb-2">
            <v-textarea
              v-model="studioStore.negativePrompt"
              rows="2"
              variant="plain"
              density="compact"
              auto-grow
              hide-details
              class="prompt-textarea px-2 py-1"
              @input="studioStore.isNegativePromptDirty = true"
            />
          </div>

          <v-text-field
            v-model="studioStore.extraNegative"
            label="本次追加 Negative (如: text, lowres)"
            density="compact"
            variant="outlined"
            hide-details
            class="text-caption"
            @update:model-value="studioStore.buildPrompt()"
          />
        </v-card>

        <!-- Generation Controls & Parameters Bar -->
        <v-card variant="outlined" class="pa-3 bg-surface rounded-lg">
          <!-- Generation Action Top Bar -->
          <div class="d-flex justify-space-between align-center mb-3">
            <div class="d-flex align-center gap-2">
              <span class="section-label text-primary">ComfyUI 渲染工作区</span>
              <!-- Workflow Mode Toggle -->
              <v-btn-toggle
                v-model="studioStore.workflowMode"
                mandatory
                density="compact"
                color="primary"
                variant="outlined"
                rounded="md"
              >
                <v-btn value="builtin" size="x-small" class="px-2">内置 2.9B</v-btn>
                <v-btn value="custom" size="x-small" class="px-2">自定义 API</v-btn>
              </v-btn-toggle>
            </div>

            <v-btn
              color="primary"
              variant="flat"
              prepend-icon="mdi-play"
              size="default"
              class="font-weight-bold px-5"
              :loading="studioStore.isGenerating"
              @click="studioStore.generateImage()"
            >
              开始生图
            </v-btn>
          </div>

          <!-- Custom Workflow File Input Row -->
          <div v-if="studioStore.workflowMode === 'custom'" class="mb-3 pa-2 rounded border bg-surface-variant">
            <div class="d-flex justify-space-between align-center flex-wrap gap-1 text-caption">
              <div class="d-flex align-center gap-1">
                <v-icon size="16" color="primary">mdi-file-code-outline</v-icon>
                <span>{{ studioStore.customWorkflowName ? studioStore.customWorkflowName : '未选择 API Workflow JSON' }}</span>
              </div>
              <div class="d-flex align-center gap-1">
                <input
                  ref="workflowFileInput"
                  type="file"
                  accept=".json"
                  style="display: none"
                  @change="handleWorkflowUpload"
                />
                <v-btn size="x-small" variant="tonal" color="primary" @click="triggerWorkflowUpload">
                  导入 JSON
                </v-btn>
                <v-btn
                  v-if="studioStore.customWorkflowTemplate"
                  size="x-small"
                  variant="text"
                  color="error"
                  @click="studioStore.resetToBuiltinWorkflow()"
                >
                  重置
                </v-btn>
              </div>
            </div>
          </div>

          <!-- Generation Parameters (Dense Row) -->
          <v-row dense class="mb-3">
            <v-col cols="6" sm="3">
              <v-select
                v-model="studioStore.width"
                :items="[812, 1024, 1152, 1280]"
                label="宽 (Width)"
                density="compact"
                variant="outlined"
                hide-details
                class="text-caption"
              />
            </v-col>
            <v-col cols="6" sm="3">
              <v-select
                v-model="studioStore.height"
                :items="[1216, 1536, 1792]"
                label="高 (Height)"
                density="compact"
                variant="outlined"
                hide-details
                class="text-caption"
              />
            </v-col>
            <v-col cols="6" sm="3">
              <v-text-field
                v-model.number="studioStore.steps"
                label="步数 (Steps)"
                density="compact"
                variant="outlined"
                type="number"
                hide-details
                class="text-caption"
              />
            </v-col>
            <v-col cols="6" sm="3">
              <v-text-field
                v-model.number="studioStore.cfg"
                label="CFG (Guidance)"
                density="compact"
                variant="outlined"
                type="number"
                step="0.5"
                hide-details
                class="text-caption"
              />
            </v-col>
          </v-row>

          <!-- Generation Progress & Messages -->
          <div v-if="studioStore.isGenerating" class="mb-3 pa-2 rounded border bg-surface-variant">
            <div class="d-flex justify-space-between text-caption mb-1">
              <span class="font-weight-medium">{{ studioStore.generationMessage }}</span>
              <span class="font-mono font-weight-bold">{{ studioStore.generationProgress }}%</span>
            </div>
            <v-progress-linear
              v-model="studioStore.generationProgress"
              color="primary"
              height="6"
              rounded
            />
          </div>

          <!-- Error Alert Banner -->
          <v-alert
            v-if="!studioStore.isGenerating && studioStore.generationMessage && (studioStore.generationMessage.includes('失败') || studioStore.generationMessage.includes('超时') || studioStore.generationMessage.includes('错误'))"
            type="error"
            density="compact"
            variant="tonal"
            class="mb-3 text-caption"
          >
            {{ studioStore.generationMessage }}
          </v-alert>

          <!-- Image Render Stage (Visual Hero) -->
          <div class="image-stage-box rounded-lg border bg-surface-variant d-flex align-center justify-center position-relative overflow-hidden">
            <div v-if="studioStore.generatedImageUrl" class="w-100 text-center position-relative">
              <v-img
                :src="studioStore.generatedImageUrl"
                max-height="520"
                contain
                class="bg-black cursor-pointer rounded"
                @click="openImagePreview(studioStore.generatedImageUrl)"
              />
              <!-- Image Quick Action Overlay Toolbar -->
              <div class="image-overlay-actions d-flex align-center justify-space-between px-3 py-1 bg-surface border-t">
                <span class="text-caption font-mono text-grey">
                  {{ studioStore.width }}×{{ studioStore.height }} | Steps: {{ studioStore.steps }} | CFG: {{ studioStore.cfg }}
                </span>
                <div class="d-flex align-center gap-1">
                  <v-btn
                    size="x-small"
                    variant="text"
                    prepend-icon="mdi-magnify-plus-outline"
                    @click="openImagePreview(studioStore.generatedImageUrl)"
                  >
                    查看大图
                  </v-btn>
                  <v-btn
                    size="x-small"
                    variant="text"
                    prepend-icon="mdi-download"
                    @click="downloadImage(studioStore.generatedImageUrl)"
                  >
                    保存
                  </v-btn>
                </div>
              </div>
            </div>

            <!-- Empty Ready State -->
            <div v-else-if="!studioStore.isGenerating" class="text-center py-12 text-grey">
              <v-icon size="48" class="mb-2 opacity-50">mdi-image-outline</v-icon>
              <div class="text-body-2 font-weight-medium">生图渲染画板</div>
              <div class="text-caption mt-1">设置参数并点击“开始生图”，ComfyUI 将在此渲染高精画作。</div>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Mini Artist Explorer Dialog -->
    <v-dialog v-model="artistExplorerDialog" max-width="820px">
      <v-card class="pa-4 rounded-lg bg-surface">
        <div class="d-flex justify-space-between align-center mb-3">
          <div class="d-flex align-center gap-1">
            <v-icon color="info" size="20">mdi-palette-swatch-outline</v-icon>
            <span class="font-weight-bold text-subtitle-1">画师库快速选择</span>
          </div>
          <v-btn icon="mdi-close" variant="text" size="small" @click="artistExplorerDialog = false" />
        </div>

        <v-text-field
          v-model="artistSearchQuery"
          label="搜索画师名称、风格或 Tag"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          class="mb-3 text-caption"
          clearable
        />

        <div class="artist-grid">
          <div
            v-for="art in filteredArtists"
            :key="art.id"
            :class="['artist-card', 'pa-2', 'rounded-lg', 'border', isArtistSelected(art) ? 'selected-card' : '']"
            @click="studioStore.toggleArtist(art)"
          >
            <div class="d-flex justify-space-between align-center mb-1">
              <span class="font-weight-bold text-caption">{{ art.name }}</span>
              <v-icon size="16" :color="isArtistSelected(art) ? 'primary' : 'grey'">
                {{ isArtistSelected(art) ? 'mdi-check-circle' : 'mdi-circle-outline' }}
              </v-icon>
            </div>
            <div class="text-caption font-mono text-primary text-truncate mb-1">
              <code>{{ art.tags }}</code>
            </div>
            <div class="text-caption text-grey text-truncate">
              {{ art.description || art.category }}
            </div>
          </div>
        </div>

        <v-card-actions class="justify-end mt-3 pt-2 border-t">
          <v-btn color="primary" variant="flat" size="small" @click="artistExplorerDialog = false">完成选择</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Large Image Preview Dialog -->
    <v-dialog v-model="imagePreviewDialog" max-width="1100px">
      <v-card class="bg-surface rounded-lg overflow-hidden">
        <div class="d-flex justify-space-between align-center px-4 py-2 border-b">
          <span class="text-subtitle-2 font-weight-bold">渲染画作原图预览</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="imagePreviewDialog = false" />
        </div>
        <div class="pa-2 bg-black text-center">
          <v-img :src="previewImageUrl" max-height="82vh" contain />
        </div>
      </v-card>
    </v-dialog>

    <!-- System Notification Snackbar -->
    <v-snackbar v-model="snackbar" :timeout="2500" :color="snackbarColor">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useStudioStore } from '../stores/studio'
import { usePresetStore } from '../stores/presets'
import { useSettingsStore } from '../stores/settings'
import { useArtistStore } from '../stores/artist'
import { useLoraStore } from '../stores/lora'
import { useRuleStore } from '../stores/rules'
import type { Artist } from '../types'

const studioStore = useStudioStore()
const presetStore = usePresetStore()
const settingsStore = useSettingsStore()
const artistStore = useArtistStore()
const loraStore = useLoraStore()
const ruleStore = useRuleStore()

const artistExplorerDialog = ref(false)
const artistSearchQuery = ref('')
const imagePreviewDialog = ref(false)
const previewImageUrl = ref('')

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('primary')
const workflowFileInput = ref<HTMLInputElement | null>(null)

const lmStudioThinkingOptions = [
  { title: 'Instruct (关闭思考 / off)', value: 'instruct' },
  { title: 'Low (轻度思考)', value: 'low' },
  { title: 'Medium (标准思考)', value: 'medium' },
  { title: 'High (深度思考)', value: 'high' },
  { title: 'On (开启思考)', value: 'on' },
]

const cloudThinkingOptions = [
  { title: 'Instruct (关闭思考)', value: 'instruct' },
  { title: 'Low (轻度思考)', value: 'low' },
  { title: 'Medium (标准思考)', value: 'medium' },
  { title: 'High (深度思考)', value: 'high' },
  { title: 'Xhigh (极高思考)', value: 'xhigh' },
  { title: 'Max (最大思考)', value: 'max' },
]

const activeThinkingOptions = computed(() => {
  return studioStore.provider === 'lm_studio' ? lmStudioThinkingOptions : cloudThinkingOptions
})

const currentModelList = computed(() => {
  return studioStore.provider === 'lm_studio' ? settingsStore.lmStudioModels : settingsStore.cloudModels
})

const currentProviderStatus = computed(() => {
  return studioStore.provider === 'lm_studio' ? settingsStore.lmStudioStatus : settingsStore.cloudStatus
})

const activeRules = computed(() => {
  return ruleStore.rules.filter(r => r.is_enabled)
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
    artistStore.fetchArtists(),
    loraStore.fetchLoras(),
    ruleStore.fetchRules()
  ])

  studioStore.initStudioSettings(settingsStore.settings)
  studioStore.syncLorasFromLibrary(loraStore.loras)

  if (!studioStore.selectedPresetId && presetStore.presets.length > 0) {
    const def = presetStore.presets.find(p => p.is_default) || presetStore.presets[0]
    studioStore.selectedPresetId = def.id
  }

  if (!studioStore.model) {
    if (studioStore.provider === 'lm_studio' && settingsStore.lmStudioModels.length > 0) {
      const defModel = settingsStore.settings.LM_STUDIO_MODEL
      studioStore.model = (defModel && settingsStore.lmStudioModels.some(m => m.id === defModel)) ? defModel : settingsStore.lmStudioModels[0].id
    } else if (studioStore.provider === 'cloud' && settingsStore.cloudModels.length > 0) {
      const defCloud = settingsStore.settings.CLOUD_MODEL
      studioStore.model = (defCloud && settingsStore.cloudModels.some(m => m.id === defCloud)) ? defCloud : settingsStore.cloudModels[0].id
    }
  }
})

function onProviderChange(p: string) {
  studioStore.provider = p as 'lm_studio' | 'cloud'
  if (p === 'lm_studio') {
    const defModel = settingsStore.settings.LM_STUDIO_MODEL
    if (defModel && settingsStore.lmStudioModels.some(m => m.id === defModel)) {
      studioStore.model = defModel
    } else if (settingsStore.lmStudioModels.length > 0) {
      studioStore.model = settingsStore.lmStudioModels[0].id
    }
    studioStore.reasoningEffort = 'instruct'
  } else if (p === 'cloud') {
    const defCloud = settingsStore.settings.CLOUD_MODEL
    if (defCloud && settingsStore.cloudModels.some(m => m.id === defCloud)) {
      studioStore.model = defCloud
    } else if (settingsStore.cloudModels.length > 0) {
      studioStore.model = settingsStore.cloudModels[0].id
    }
    studioStore.reasoningEffort = 'instruct'
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
  studioStore.selectedPresetId = presetId
  studioStore.buildPrompt()
}

function toggleRule(ruleId: number) {
  const idx = studioStore.selectedRuleIds.indexOf(ruleId)
  if (idx !== -1) {
    studioStore.selectedRuleIds.splice(idx, 1)
  } else {
    studioStore.selectedRuleIds.push(ruleId)
  }
  studioStore.isSemanticDirty = true
}

function isArtistSelected(art: Artist): boolean {
  return studioStore.selectedArtists.some(a => a.id === art.id)
}

function getEntityName(entityId: string): string {
  const e = studioStore.facts.entities.find(item => item.id === entityId)
  return e ? e.name : entityId
}

function triggerWorkflowUpload() {
  workflowFileInput.value?.click()
}

function handleWorkflowUpload(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = e.target?.result as string
      const json = JSON.parse(content)
      if (typeof json !== 'object' || json === null) {
        throw new Error('JSON 根节点必须是一个对象')
      }
      
      const keys = Object.keys(json)
      if (keys.length === 0) {
        throw new Error('工作流 JSON 为空')
      }
      const firstNode = json[keys[0]]
      if (!firstNode || typeof firstNode !== 'object' || !firstNode.class_type) {
        throw new Error('未检测到有效的 ComfyUI API Format 节点结构 (class_type 缺失)')
      }

      studioStore.setWorkflowTemplate(file.name, json)
      snackbarText.value = `已导入工作流: ${file.name}`
      snackbarColor.value = 'success'
      snackbar.value = true
    } catch (err: any) {
      alert(`导入工作流失败: ${err.message || err}`)
    }
  }
  reader.readAsText(file)
  target.value = ''
}

function copyToClipboard(text: string) {
  if (!text) return
  navigator.clipboard.writeText(text)
  snackbarText.value = '已复制到剪贴板'
  snackbarColor.value = 'success'
  snackbar.value = true
}

function openImagePreview(url: string) {
  previewImageUrl.value = url
  imagePreviewDialog.value = true
}

function downloadImage(url: string) {
  const link = document.createElement('a')
  link.href = url
  link.download = `ImageForge_Anima_${Date.now()}.png`
  link.click()
}

async function saveEntityTrigger(entity: any) {
  try {
    await studioStore.saveEntityTrigger(entity)
    const remainingUnresolved = studioStore.facts.entities.filter(
      e => e.source === 'model_character' && !e.canonical_tag
    )
    if (remainingUnresolved.length > 0) {
      snackbarText.value = `已保存角色【${entity.name}】映射，仍有 ${remainingUnresolved.length} 个角色未补全`
      snackbarColor.value = 'warning'
    } else {
      snackbarText.value = `已保存角色【${entity.name}】的 Trigger 映射`
      snackbarColor.value = 'success'
    }
    snackbar.value = true
  } catch (err: any) {
    snackbarText.value = `保存 Trigger 失败: ${err.response?.data?.detail || err.message || '网络请求异常'}`
    snackbarColor.value = 'error'
    snackbar.value = true
  }
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.font-mono { font-family: monospace; }
.lora-scroll-area {
  max-height: 120px;
  overflow-y: auto;
}
.image-stage-box {
  min-height: 320px;
}
.artist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
}
.artist-card {
  cursor: pointer;
  transition: all 0.15s ease;
  background-color: var(--v-theme-surface);
}
.artist-card:hover {
  border-color: #4F46E5 !important;
}
.selected-card {
  border-color: #4F46E5 !important;
  background-color: rgba(79, 70, 229, 0.08) !important;
}
</style>
