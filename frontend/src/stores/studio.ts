import { defineStore } from 'pinia'
import axios from 'axios'
import type { SemanticFacts, Entity, Statement, SafetyLevel, Artist, Lora, ReasoningEffort, AppSettings, GenerationHistory } from '../types'

export interface ActiveLoraItem {
  lora: Lora;
  strength: number;
  isEnabled: boolean;
}

export const useStudioStore = defineStore('studio', {
  state: () => ({
    isInitialized: false,
    rawInput: '',
    lastParsedInput: '',
    isSemanticDirty: false,
    safety: 'Safe' as SafetyLevel,
    selectedPresetId: null as number | null,
    extraNegative: '',
    
    // Extracted Semantic Facts
    facts: {
      entities: [] as Entity[],
      statements: [] as Statement[]
    } as SemanticFacts,
    
    // Selected options in workbench
    selectedArtists: [] as Artist[],
    activeLoras: [] as ActiveLoraItem[],
    selectedRuleIds: [] as number[],
    
    // Generated Prompt Outputs & Manual Edit Dirty Tracking
    positivePrompt: '',
    negativePrompt: '',
    isPositivePromptDirty: false,
    isNegativePromptDirty: false,
    
    // LLM Provider & Model Control in Workbench
    provider: 'lm_studio' as 'lm_studio' | 'cloud',
    model: '',
    reasoningEffort: 'off' as ReasoningEffort,
    providerMemory: {
      lm_studio: { model: '', reasoning: 'off' as ReasoningEffort },
      cloud: { model: '', reasoning: 'off' as ReasoningEffort },
    },
    generateTimeoutSeconds: 300,
    
    // ComfyUI Parameters & State (Anima-2.9B tuned defaults)
    workflowMode: 'builtin' as 'builtin' | 'custom',
    customWorkflowName: '',
    customWorkflowTemplate: null as Record<string, any> | null,
    overrideWorkflowModels: false,
    
    unetName: 'anima29B_v10.safetensors',
    clipName: 'qwen_3_06b_base.safetensors',
    vaeName: 'qwen_image_vae.safetensors',
    samplerName: 'euler',
    scheduler: 'sgm_uniform',
    width: 1024,
    height: 1536,
    steps: 28,
    cfg: 4.5,
    seed: -1,
    generatedImageUrl: '' as string,
    generationComfyUrl: '' as string,
    generationProgress: 0,
    generationStage: 'idle' as 'idle' | 'preparing' | 'submitted' | 'done' | 'timeout' | 'error',
    generationMessage: '',
    
    // Loading Flags
    isParsing: false,
    isBuilding: false,
    isGenerating: false,

    // Draft autosave
    draftRestored: false,
    _draftTimer: null as ReturnType<typeof setTimeout> | null,
    _skipNextDraftSave: false,
    _draftArtistIds: [] as number[],
    _draftLoraStates: [] as any[],
  }),

  actions: {
    initStudioSettings(settings: AppSettings) {
      if (!this.isInitialized) {
        if (settings.DEFAULT_SAFETY) {
          this.safety = settings.DEFAULT_SAFETY
        }
        if (settings.ACTIVE_PROVIDER) {
          this.provider = settings.ACTIVE_PROVIDER
        }
        this.model = this.provider === 'lm_studio' ? (settings.LM_STUDIO_MODEL || '') : (settings.CLOUD_MODEL || '')
        this.generateTimeoutSeconds = settings.GENERATE_TIMEOUT_SECONDS || 300
        this.isInitialized = true
      }
    },

    restoreSession(item: GenerationHistory) {
      this.rawInput = item.raw_input || ''
      this.lastParsedInput = item.raw_input || ''
      this.isSemanticDirty = false
      this.positivePrompt = item.prompt || ''
      this.negativePrompt = item.negative_prompt || ''
      this.safety = (item.safety as SafetyLevel) || 'Safe'
      this.isPositivePromptDirty = false
      this.isNegativePromptDirty = false

      try {
        if (item.parsed_facts_json) {
          this.facts = JSON.parse(item.parsed_facts_json)
        }
      } catch {}

      try {
        if (item.artists_json) {
          this.selectedArtists = JSON.parse(item.artists_json)
        }
      } catch {}

      try {
        if (item.loras_json) {
          this.activeLoras = JSON.parse(item.loras_json)
        }
      } catch {}

      try {
        if (item.comfy_params_json) {
          const params = JSON.parse(item.comfy_params_json)
          if (params.unet_name) this.unetName = params.unet_name
          if (params.clip_name) this.clipName = params.clip_name
          if (params.vae_name) this.vaeName = params.vae_name
          if (params.width) this.width = params.width
          if (params.height) this.height = params.height
          if (params.steps) this.steps = params.steps
          if (params.cfg) this.cfg = params.cfg
          if (params.sampler_name) this.samplerName = params.sampler_name
          if (params.scheduler) this.scheduler = params.scheduler
          if (params.seed !== undefined) this.seed = params.seed

          if (params.studio) {
            if (params.studio.selectedPresetId !== undefined) this.selectedPresetId = params.studio.selectedPresetId
            if (params.studio.extraNegative !== undefined) this.extraNegative = params.studio.extraNegative
            if (params.studio.provider) this.provider = params.studio.provider
            if (params.studio.model) this.model = params.studio.model
            if (params.studio.reasoningEffort) {
              this.reasoningEffort = (params.studio.reasoningEffort === 'instruct' ? 'off' : params.studio.reasoningEffort) as ReasoningEffort
            }
            if (params.studio.selectedRuleIds) this.selectedRuleIds = params.studio.selectedRuleIds
            if (params.studio.workflowMode) this.workflowMode = params.studio.workflowMode
            if (params.studio.customWorkflowName !== undefined) this.customWorkflowName = params.studio.customWorkflowName
            if (params.studio.customWorkflowTemplate !== undefined) this.customWorkflowTemplate = params.studio.customWorkflowTemplate
            if (params.studio.overrideWorkflowModels !== undefined) this.overrideWorkflowModels = params.studio.overrideWorkflowModels
          }
        }
      } catch {}

      if (item.image_path) {
        this.generatedImageUrl = item.image_path
      }
      this.isInitialized = true
    },

    setWorkflowTemplate(filename: string, templateJson: Record<string, any>) {
      this.workflowMode = 'custom'
      this.customWorkflowName = filename
      this.customWorkflowTemplate = templateJson
    },

    resetToBuiltinWorkflow() {
      this.workflowMode = 'builtin'
      this.customWorkflowName = ''
      this.customWorkflowTemplate = null
      this.overrideWorkflowModels = false
    },

    syncLorasFromLibrary(allLoras: Lora[]) {
      const existingMap = new Map(this.activeLoras.map(item => [item.lora.id, item]))
      this.activeLoras = allLoras.map(lora => {
        const existing = existingMap.get(lora.id)
        return {
          lora,
          strength: existing ? existing.strength : lora.default_strength,
          isEnabled: existing ? existing.isEnabled : false
        }
      })
    },

    syncArtistsFromLibrary(allArtists: Artist[]) {
      const libraryMap = new Map(allArtists.map(a => [a.id, a]))
      this.selectedArtists = this.selectedArtists
        .filter(a => libraryMap.has(a.id))
        .map(a => libraryMap.get(a.id)!)
      this.buildPrompt()
    },

    toggleArtist(artist: Artist) {
      const idx = this.selectedArtists.findIndex(a => a.id === artist.id)
      if (idx !== -1) {
        this.selectedArtists.splice(idx, 1)
      } else {
        this.selectedArtists.push(artist)
      }
      this.buildPrompt()
    },

    toggleLora(loraId: number) {
      const item = this.activeLoras.find(i => i.lora.id === loraId)
      if (item) {
        item.isEnabled = !item.isEnabled
        this.buildPrompt()
      }
    },

    setLoraStrength(loraId: number, strength: number) {
      const item = this.activeLoras.find(i => i.lora.id === loraId)
      if (item) {
        item.strength = strength
        this.buildPrompt()
      }
    },

    removeStatement(index: number) {
      this.facts.statements.splice(index, 1)
      this.buildPrompt()
    },

    async saveEntityTrigger(entity: Entity) {
      if (entity.source === 'model_character' && entity.canonical_tag && entity.caption_name) {
        // 1. Save to cache
        await axios.post('/api/prompt/resolve-trigger', {
          name: entity.name,
          canonical_tag: entity.canonical_tag,
          caption_name: entity.caption_name,
          save_to_cache: true
        })
        // 2. Try to build prompt (swallow compile error so save is not marked as failed)
        try {
          await this.buildPrompt()
        } catch (compileErr) {
          console.warn('Trigger saved, but some characters still unresolved:', compileErr)
        }
      } else {
        throw new Error('Canonical Tag 与 Caption Name 均不能为空')
      }
    },

    async parsePrompt() {
      if (!this.rawInput.trim()) return
      this.isParsing = true
      this.generationMessage = ''
      try {
        const resp = await axios.post('/api/prompt/parse', {
          text: this.rawInput,
          rule_ids: this.selectedRuleIds,
          provider: this.provider,
          model: this.model,
          reasoning_effort: this.reasoningEffort
        })
        this.facts = resp.data
        this.lastParsedInput = this.rawInput
        this.isSemanticDirty = false
        await this.buildPrompt(true)
      } catch (err: any) {
        console.error('Prompt parsing failed:', err)
        const msg = err.response?.data?.detail || err.message || '解析提示词失败'
        this.generationMessage = `解析失败: ${msg}`
      } finally {
        this.isParsing = false
      }
    },

    async buildPrompt(force: boolean = false) {
      this.isBuilding = true
      try {
        const loraBuildItems = this.activeLoras.map(item => ({
          filename: item.lora.filename,
          trigger_words: item.lora.trigger_words,
          strength: item.strength,
          is_enabled: item.isEnabled
        }))

        const resp = await axios.post('/api/prompt/build', {
          facts: this.facts,
          safety: this.safety,
          preset_id: this.selectedPresetId,
          extra_negative: this.extraNegative,
          artist_tags: this.selectedArtists.map(a => a.tags),
          lora_items: loraBuildItems
        })

        if (!this.isPositivePromptDirty || force) {
          this.positivePrompt = resp.data.prompt
          this.isPositivePromptDirty = false
        }
        if (!this.isNegativePromptDirty || force) {
          this.negativePrompt = resp.data.negative_prompt
          this.isNegativePromptDirty = false
        }
        this.facts = resp.data.facts
      } catch (err: any) {
        console.error('Prompt compilation failed:', err)
        const msg = err.response?.data?.detail || err.message || 'Prompt 构建未成功'
        this.generationMessage = `编译提示词异常: ${msg}`
      } finally {
        this.isBuilding = false
      }
    },

    async generateImage() {
      if (this.workflowMode === 'custom' && !this.customWorkflowTemplate) {
        this.generationProgress = 0
        this.generationStage = 'error'
        this.generationMessage = '生图失败：当前为自定义工作流模式，但尚未导入任何 API Workflow JSON 文件。请先导入工作流文件或切换回内置工作流。'
        return
      }

      if (this.isSemanticDirty && !this.isPositivePromptDirty) {
        this.generationProgress = 0
        this.generationStage = 'error'
        this.generationMessage = '画面要求已修改，请重新点击“解析提示词”。'
        return
      }

      if (!this.positivePrompt.trim()) {
        await this.buildPrompt(true)
        if (!this.positivePrompt.trim()) {
          this.generationProgress = 0
          this.generationStage = 'error'
          this.generationMessage = '生图失败：Prompt 构建未成功，请检查人物 Trigger 或输入要求。'
          return
        }
      }

      this.isGenerating = true
      this.generationProgress = 10
      this.generationStage = 'preparing'
      this.generationMessage = '正在组装工作流并提交 ComfyUI…'

      const actualSeed = this.seed === -1 ? Math.floor(Math.random() * 1000000000) : this.seed

      try {
        const loraItems = this.activeLoras
          .filter(item => item.isEnabled)
          .map(item => ({
            filename: item.lora.filename,
            trigger_words: item.lora.trigger_words,
            strength: item.strength,
            is_enabled: true
          }))

        const reqPayload: Record<string, any> = {
          positive_prompt: this.positivePrompt,
          negative_prompt: this.negativePrompt,
          unet_name: this.unetName,
          clip_name: this.clipName,
          vae_name: this.vaeName,
          loras: loraItems,
          width: this.width,
          height: this.height,
          steps: this.steps,
          cfg: this.cfg,
          sampler_name: this.samplerName,
          scheduler: this.scheduler,
          seed: actualSeed
        }

        if (this.workflowMode === 'custom' && this.customWorkflowTemplate) {
          reqPayload.custom_template = this.customWorkflowTemplate
          reqPayload.override_models = this.overrideWorkflowModels
        }

        const resp = await axios.post('/api/comfyui/generate', {
          ...reqPayload
        })

        const promptId = resp.data.prompt_id
        this.generationProgress = 30
        this.generationStage = 'submitted'
        this.generationMessage = '已提交，ComfyUI 正在生成…'

        // 可配置超时（默认 300s），前端停止等待≠任务已取消
        const timeoutMs = (this.generateTimeoutSeconds || 300) * 1000
        const startedAt = Date.now()
        let done = false
        while (!done && Date.now() - startedAt < timeoutMs) {
          await new Promise(r => setTimeout(r, 1500))
          if (Date.now() - startedAt >= timeoutMs) break
          try {
            const histResp = await axios.get(`/api/comfyui/history/${promptId}`)
            const histData = histResp.data[promptId]
            if (histData && histData.outputs) {
              for (const nodeId in histData.outputs) {
                const nodeOut = histData.outputs[nodeId]
                if (nodeOut.images && nodeOut.images.length > 0) {
                  const img = nodeOut.images[0]
                  done = true
                  this.generationStage = 'done'
                  // 保存到 ImageForge 自己的 data/generated，历史不再依赖 ComfyUI output
                  try {
                    this.generationMessage = '生成完成，正在保存到本地…'
                    const persist = await axios.post('/api/comfyui/persist-image', {
                      filename: img.filename,
                      subfolder: img.subfolder,
                      type: img.type,
                    })
                    this.generatedImageUrl = persist.data.image_path
                    this.generationComfyUrl = persist.data.comfy_view_url
                  } catch {
                    this.generatedImageUrl = `/api/comfyui/view?filename=${img.filename}&subfolder=${img.subfolder}&type=${img.type}`
                    this.generationComfyUrl = this.generatedImageUrl
                  }
                  this.generationProgress = 100
                  this.generationMessage = '生成完成！'
                  await this.saveHistory(promptId, actualSeed)
                  break
                }
              }
            }
          } catch (e) {
            console.warn('Waiting for ComfyUI task...', e)
          }
        }

        if (!done) {
          this.generationProgress = 0
          this.generationStage = 'timeout'
          const waited = Math.round(timeoutMs / 1000)
          this.generationMessage = `已等待 ${waited} 秒未收到结果。前端已停止等待，但这不代表 ComfyUI 任务已取消——任务可能仍在后台生成。请先到 ComfyUI 队列确认，再决定是否重试，避免重复提交。`
        }
      } catch (err: any) {
        console.error('Image generation error:', err)
        const msg = err.response?.data?.detail || err.message || '生图失败，请检查 ComfyUI 连接与模型设置。'
        this.generationProgress = 0
        this.generationStage = 'error'
        this.generationMessage = `生图失败: ${msg}`
      } finally {
        this.isGenerating = false
      }
    },

    async saveHistory(promptId: string, actualSeed: number) {
      try {
        await axios.post('/api/history', {
          raw_input: this.rawInput,
          parsed_facts_json: JSON.stringify(this.facts),
          prompt: this.positivePrompt,
          negative_prompt: this.negativePrompt,
          safety: this.safety,
          artists_json: JSON.stringify(this.selectedArtists),
          loras_json: JSON.stringify(this.activeLoras.filter(i => i.isEnabled)),
          comfy_params_json: JSON.stringify({
            unet_name: this.unetName,
            clip_name: this.clipName,
            vae_name: this.vaeName,
            width: this.width,
            height: this.height,
            steps: this.steps,
            cfg: this.cfg,
            sampler_name: this.samplerName,
            scheduler: this.scheduler,
            seed: actualSeed,
            comfy_prompt_id: promptId,
            comfy_image_url: this.generationComfyUrl || undefined,
            studio: {
              selectedPresetId: this.selectedPresetId,
              extraNegative: this.extraNegative,
              provider: this.provider,
              model: this.model,
              reasoningEffort: this.reasoningEffort,
              selectedRuleIds: this.selectedRuleIds,
              workflowMode: this.workflowMode,
              customWorkflowName: this.customWorkflowName,
              customWorkflowTemplate: this.customWorkflowTemplate,
              overrideWorkflowModels: this.overrideWorkflowModels
            }
          }),
          image_path: this.generatedImageUrl
        })
      } catch (e) {
        console.warn('Failed to save history:', e)
      }
    },

    /* ───────────────── 草稿 autosave（localStorage，schema version 容错） ───────────────── */
    persistDraft() {
      try {
        const draft = {
          v: 1,
          rawInput: this.rawInput,
          safety: this.safety,
          selectedPresetId: this.selectedPresetId,
          selectedRuleIds: this.selectedRuleIds,
          selectedArtistIds: this.selectedArtists.map(a => a.id),
          activeLoras: this.activeLoras.map(i => ({ id: i.lora.id, strength: i.strength, isEnabled: i.isEnabled })),
          positivePrompt: this.positivePrompt,
          negativePrompt: this.negativePrompt,
          extraNegative: this.extraNegative,
          width: this.width,
          height: this.height,
          steps: this.steps,
          cfg: this.cfg,
          seed: this.seed,
          provider: this.provider,
          model: this.model,
          reasoningEffort: this.reasoningEffort,
          providerMemory: this.providerMemory,
        }
        localStorage.setItem('imageforge_studio_draft_v1', JSON.stringify(draft))
      } catch (e) {
        console.warn('Draft save failed:', e)
      }
    },

    scheduleDraftSave() {
      if (this._draftTimer) clearTimeout(this._draftTimer)
      this._draftTimer = setTimeout(() => {
        if (this._skipNextDraftSave) {
          this._skipNextDraftSave = false
          return
        }
        this.persistDraft()
      }, 500)
    },

    loadDraft(): boolean {
      try {
        const raw = localStorage.getItem('imageforge_studio_draft_v1')
        if (!raw) return false
        const d = JSON.parse(raw)
        if (!d || d.v !== 1 || typeof d.rawInput !== 'string') return false

        // 逐字段安全恢复：类型不符的字段安全忽略，绝不因旧/脏草稿导致 Studio 启动失败
        if (typeof d.rawInput === 'string') this.rawInput = d.rawInput
        if (d.safety && ['Safe', 'Sensitive', 'NSFW', 'Explicit'].includes(d.safety)) this.safety = d.safety
        if (typeof d.selectedPresetId === 'number' || d.selectedPresetId === null) this.selectedPresetId = d.selectedPresetId
        if (Array.isArray(d.selectedRuleIds)) this.selectedRuleIds = d.selectedRuleIds.filter((x: any) => typeof x === 'number')
        if (Array.isArray(d.selectedArtistIds)) this._draftArtistIds = d.selectedArtistIds.filter((x: any) => typeof x === 'number')
        if (Array.isArray(d.activeLoras)) this._draftLoraStates = d.activeLoras.filter((x: any) => x && typeof x.id === 'number')
        if (typeof d.positivePrompt === 'string') this.positivePrompt = d.positivePrompt
        if (typeof d.negativePrompt === 'string') this.negativePrompt = d.negativePrompt
        if (typeof d.extraNegative === 'string') this.extraNegative = d.extraNegative
        if (typeof d.width === 'number') this.width = d.width
        if (typeof d.height === 'number') this.height = d.height
        if (typeof d.steps === 'number') this.steps = d.steps
        if (typeof d.cfg === 'number') this.cfg = d.cfg
        if (typeof d.seed === 'number') this.seed = d.seed
        if (d.provider === 'lm_studio' || d.provider === 'cloud') this.provider = d.provider
        if (typeof d.model === 'string') this.model = d.model
        if (d.reasoningEffort) {
          const r = d.reasoningEffort === 'instruct' ? 'off' : d.reasoningEffort
          if (['off', 'on', 'low', 'medium', 'high', 'xhigh', 'max'].includes(r)) this.reasoningEffort = r as ReasoningEffort
        }
        if (d.providerMemory && typeof d.providerMemory === 'object') {
          const m = d.providerMemory
          if (m.lm_studio && typeof m.lm_studio.model === 'string') this.providerMemory.lm_studio.model = m.lm_studio.model
          if (m.cloud && typeof m.cloud.model === 'string') this.providerMemory.cloud.model = m.cloud.model
          if (m.lm_studio && typeof m.lm_studio.reasoning === 'string') this.providerMemory.lm_studio.reasoning = m.lm_studio.reasoning as ReasoningEffort
          if (m.cloud && typeof m.cloud.reasoning === 'string') this.providerMemory.cloud.reasoning = m.cloud.reasoning as ReasoningEffort
        }
        this.draftRestored = true
        return true
      } catch (e) {
        console.warn('Draft restore failed (ignored):', e)
        return false
      }
    },

    /** 在 LoRA 库数据就绪后应用草稿中的 LoRA 勾选/权重。 */
    applyDraftLoraStates() {
      if (!this._draftLoraStates || this._draftLoraStates.length === 0) return
      for (const item of this.activeLoras) {
        const st = this._draftLoraStates.find((x: any) => x.id === item.lora.id)
        if (st) {
          item.isEnabled = !!st.isEnabled
          if (typeof st.strength === 'number') item.strength = st.strength
        }
      }
      this._draftLoraStates = []
    },

    /** 在画师库数据就绪后应用草稿中的画师选择。 */
    applyDraftArtistIds(library: any[]) {
      if (!this._draftArtistIds || this._draftArtistIds.length === 0) return
      this.selectedArtists = library.filter((a: any) => this._draftArtistIds.includes(a.id))
      this._draftArtistIds = []
    },

    clearDraft() {
      try {
        localStorage.removeItem('imageforge_studio_draft_v1')
      } catch { /* ignore */ }
      this._skipNextDraftSave = true
      if (this._draftTimer) clearTimeout(this._draftTimer)
      this.rawInput = ''
      this.isSemanticDirty = false
      this.safety = 'Safe'
      this.selectedPresetId = null
      this.selectedRuleIds = []
      this.selectedArtists = []
      this.activeLoras = this.activeLoras.map(i => ({ ...i, isEnabled: false }))
      this.positivePrompt = ''
      this.negativePrompt = ''
      this.extraNegative = ''
      this.generatedImageUrl = ''
      this.draftRestored = false
    },
  }
})
