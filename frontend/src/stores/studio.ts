import { defineStore } from 'pinia'
import axios from 'axios'
import type { SemanticFacts, Entity, Statement, SafetyLevel, Artist, Lora, ReasoningEffort, AppSettings, GenerationHistory } from '../types'

export interface ActiveLoraItem {
  lora: Lora;
  strength: number;
  isEnabled: boolean;
}

/** 一次生成提交时的参数快照（A9）：任务提交后改 Studio 参数不污染已完成图片的 metadata。 */
export interface GenerationSnapshot {
  prompt: string;
  negativePrompt: string;
  seed: number;
  width: number;
  height: number;
  steps: number;
  cfg: number;
  sampler: string;
  scheduler: string;
  safety: SafetyLevel;
  artists: Artist[];
  loras: ActiveLoraItem[];
  submittedAt: number;
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
    
    unetName: 'anima29BInt8Convrot_v10.safetensors',
    clipName: 'qwen_3_06b_base.safetensors',
    vaeName: 'qwen_image_vae.safetensors',
    samplerName: 'euler',
    scheduler: 'beta57',
    width: 1024,
    height: 1536,
    steps: 12,
    cfg: 1,
    seed: -1,
    lastGeneratedSeed: null as number | null,
    generatedImageUrl: '' as string,
    generationComfyUrl: '' as string,
    generationPersisted: false,
    generationProgress: 0,
    generationStage: 'idle' as 'idle' | 'preparing' | 'queued' | 'running' | 'saving' | 'done' | 'timeout' | 'error' | 'cancelled',
    generationMessage: '',
    generationQueuePosition: null as number | null,
    generationProgressValue: null as number | null,
    generationProgressMax: null as number | null,
    generationIsRunning: false,
    generationError: null as { kind?: string; summary: string; detail: string } | null,
    activePromptId: '' as string,
    activeGenerationSnapshot: null as GenerationSnapshot | null,
    lastGenerationSnapshot: null as GenerationSnapshot | null,
    _generationAbort: false,
    
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

          // A4：恢复该次生成真正使用的 seed（有具体值才是"固定"，-1 表示随机策略）
          if (typeof params.seed === 'number' && params.seed >= 0) {
            this.lastGeneratedSeed = params.seed
          }

          // A4：依据恢复的参数重建"上一张"快照，Canvas metadata 显示历史真实值
          this.lastGenerationSnapshot = {
            prompt: this.positivePrompt,
            negativePrompt: this.negativePrompt,
            seed: typeof params.seed === 'number' && params.seed >= 0 ? params.seed : -1,
            width: params.width ?? this.width,
            height: params.height ?? this.height,
            steps: params.steps ?? this.steps,
            cfg: params.cfg ?? this.cfg,
            sampler: params.sampler_name ?? this.samplerName,
            scheduler: params.scheduler ?? this.scheduler,
            safety: (item.safety as SafetyLevel) || 'Safe',
            artists: (() => { try { return JSON.parse(item.artists_json || '[]') } catch { return [] } })(),
            loras: (() => { try { return JSON.parse(item.loras_json || '[]') } catch { return [] } })(),
            submittedAt: Date.now(),
          }

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

        // 空 facts 保护：恢复的 Prompt 若没有对应 facts（如旧版草稿/未解析），
        // 非 force 的 build 不得用空 facts 重编译覆盖用户已看到的场景 Prompt；
        // 此时应保持 isSemanticDirty=true，引导用户重新解析。
        const hasFacts = this.facts.entities.length > 0 || this.facts.statements.length > 0
        if ((!this.isPositivePromptDirty && (hasFacts || !this.positivePrompt.trim())) || force) {
          this.positivePrompt = resp.data.prompt
          this.isPositivePromptDirty = false
        }
        if ((!this.isNegativePromptDirty && (hasFacts || !this.negativePrompt.trim())) || force) {
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
      if (this.isGenerating) return  // 并发保护：防止双击重复提交 ComfyUI 任务
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

      // 尺寸硬校验：不静默修改输入，越界则明确阻止并解释
      const wNum = Number(this.width)
      const hNum = Number(this.height)
      if (!Number.isInteger(wNum) || !Number.isInteger(hNum) || wNum < 64 || hNum < 64 || wNum > 8192 || hNum > 8192) {
        this.generationProgress = 0
        this.generationStage = 'error'
        this.generationMessage = `尺寸超出可生成范围（64–8192）：当前 ${this.width}×${this.height}。未修改你的输入，请调整后再生成。`
        return
      }
      const sizeRatio = wNum / hNum
      if (sizeRatio < 0.25 || sizeRatio > 4) {
        this.generationProgress = 0
        this.generationStage = 'error'
        this.generationMessage = `尺寸宽高比超出可生成范围（0.25:1 – 4:1）：当前 ${this.width}×${this.height}。未修改你的输入，请调整后再生成。`
        return
      }

      // ── 生成快照（A9）：提交前定格本次真实参数，之后改 Studio 参数不污染已完成图片 ──
      const actualSeed = this.seed === -1 ? Math.floor(Math.random() * 1000000000) : this.seed
      const snapshot: GenerationSnapshot = {
        prompt: this.positivePrompt,
        negativePrompt: this.negativePrompt,
        seed: actualSeed,
        width: this.width,
        height: this.height,
        steps: this.steps,
        cfg: this.cfg,
        sampler: this.samplerName,
        scheduler: this.scheduler,
        safety: this.safety,
        artists: this.selectedArtists.map(a => ({ ...a })),
        loras: this.activeLoras.filter(i => i.isEnabled).map(i => ({ lora: { ...i.lora }, strength: i.strength, isEnabled: true })),
        submittedAt: Date.now(),
      }
      this.activeGenerationSnapshot = snapshot
      this.generationError = null
      this.generationQueuePosition = null
      this.generationProgressValue = null
      this.generationProgressMax = null
      this.generationIsRunning = false
      this.generationPersisted = false
      this._generationAbort = false
      this.isGenerating = true
      this.generationProgress = 10
      this.generationStage = 'preparing'
      this.generationMessage = '正在组装工作流并提交 ComfyUI…'

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
        this.activePromptId = promptId
        this.generationStage = 'queued'
        this.generationMessage = '已提交，等待队列…'

        // 可配置超时（默认 300s），前端停止等待≠任务已取消
        const timeoutMs = (this.generateTimeoutSeconds || 300) * 1000
        const startedAt = Date.now()
        let terminal = false
        while (!terminal && !this._generationAbort && Date.now() - startedAt < timeoutMs) {
          await new Promise(r => setTimeout(r, 1000))
          if (this._generationAbort) break
          let st: any = null
          try {
            st = (await axios.get(`/api/comfyui/status/${promptId}`)).data
          } catch {
            continue
          }

          if (st.stage === 'queued') {
            this.generationStage = 'queued'
            this.generationIsRunning = false
            this.generationQueuePosition = st.queue_position
            this.generationMessage = st.queue_position != null && st.queue_position > 0
              ? `队列中 · 前方 ${st.queue_position} 个任务`
              : '队列中…'
          } else if (st.stage === 'running') {
            this.generationStage = 'running'
            this.generationIsRunning = !!st.is_running
            this.generationProgressValue = st.progress_value
            this.generationProgressMax = st.progress_max
            this.generationMessage = st.progress_max
              ? `生成中 ${st.progress_value ?? 0} / ${st.progress_max}`
              : '生成中…'
          } else if (st.stage === 'done') {
            this.generationStage = 'saving'
            this.generationIsRunning = false
            this.generationMessage = '生成完成，正在保存到本地…'
            if (await this.finishGeneration(promptId, actualSeed, snapshot)) {
              terminal = true
              break
            }
            // history 尚未就绪（done 消息先于 history 落库）——继续轮询
            this.generationStage = 'running'
          } else if (st.stage === 'error') {
            this.generationStage = 'error'
            this.generationIsRunning = false
            this.generationMessage = st.error_summary || '生成失败'
            this.generationError = {
              kind: st.error_type,
              summary: st.error_summary || '生成失败',
              detail: st.error_detail || '',
            }
            terminal = true
          } else if (st.stage === 'cancelled') {
            this.generationStage = 'cancelled'
            this.generationMessage = '已中断'
            terminal = true
          }
        }

        if (!terminal) {
          this.generationProgress = 0
          this.generationStage = 'timeout'
          if (this._generationAbort) {
            this.generationMessage = '已停止等待。ComfyUI 任务可能仍在后台运行（停止等待 ≠ 取消任务），请到 ComfyUI 队列确认后再决定是否重试。'
          } else {
            const waited = Math.round(timeoutMs / 1000)
            this.generationMessage = `已等待 ${waited} 秒未收到结果。前端已停止等待，但这不代表 ComfyUI 任务已取消——任务可能仍在后台生成。请先到 ComfyUI 队列确认，再决定是否重试，避免重复提交。`
          }
        }
      } catch (err: any) {
        console.error('Image generation error:', err)
        this.generationProgress = 0
        this.generationStage = 'error'
        const det = err.response?.data?.detail
        if (det && typeof det === 'object') {
          this.generationMessage = det.summary || '生图失败'
          this.generationError = {
            kind: det.kind,
            summary: det.summary || '生图失败',
            detail: det.detail || JSON.stringify(det),
          }
        } else {
          this.generationMessage = `生图失败: ${det || err.message || '请检查 ComfyUI 连接与模型设置'}`
        }
      } finally {
        this.isGenerating = false
        this.activePromptId = ''
      }
    },

    /** 从 ComfyUI history 取图 → 本地持久化 → 记录 history → 定格快照。返回是否真正完成。 */
    async finishGeneration(promptId: string, actualSeed: number, snapshot: GenerationSnapshot): Promise<boolean> {
      let histData: any = null
      try {
        histData = (await axios.get(`/api/comfyui/history/${promptId}`)).data[promptId]
      } catch {
        return false
      }
      if (!histData || !histData.outputs) return false
      let img: any = null
      for (const nodeId in histData.outputs) {
        const nodeOut = histData.outputs[nodeId]
        if (nodeOut.images && nodeOut.images.length > 0) {
          img = nodeOut.images[0]
          break
        }
      }
      if (!img) return false

      this.generationStage = 'saving'
      this.generationMessage = '生成完成，正在保存到本地…'
      try {
        const persist = await axios.post('/api/comfyui/persist-image', {
          filename: img.filename,
          subfolder: img.subfolder,
          type: img.type,
        })
        this.generatedImageUrl = persist.data.image_path
        this.generationComfyUrl = persist.data.comfy_view_url
        this.generationPersisted = true
        this.generationMessage = '生成完成！'
      } catch {
        this.generatedImageUrl = `/api/comfyui/view?filename=${img.filename}&subfolder=${img.subfolder}&type=${img.type}`
        this.generationComfyUrl = this.generatedImageUrl
        this.generationPersisted = false
        this.generationMessage = '图片已生成，但本地历史归档失败——历史记录当前依赖 ComfyUI output（清理 ComfyUI output 后历史图片可能失效）。'
      }
      this.generationProgress = 100
      this.generationStage = 'done'
      this.lastGeneratedSeed = actualSeed
      this.lastGenerationSnapshot = snapshot
      await this.saveHistory(promptId, snapshot)
      return true
    },

    /** 停止等待：只停止前端轮询，不取消 ComfyUI 任务（准确语义）。 */
    stopWaiting() {
      this._generationAbort = true
    },

    /** 中断当前任务。ComfyUI 0.34.2 无 task-scoped cancel（DELETE /queue/{id}=405），
     *  只能全局 POST /interrupt——因此前端仅当本任务确实是 ComfyUI 当前运行任务时
     *  才允许调用（is_running 门控），并向用户明示这是对当前执行任务的全局中断。 */
    async interruptGeneration() {
      try {
        await axios.post('/api/comfyui/interrupt')
        this.generationMessage = '已请求中断（全局 interrupt），等待确认…'
      } catch (err: any) {
        this.generationMessage = `中断失败: ${err.response?.data?.detail?.summary || err.message || '未知错误'}`
      }
    },

    async saveHistory(promptId: string, snapshot: GenerationSnapshot) {
      try {
        await axios.post('/api/history', {
          raw_input: this.rawInput,
          parsed_facts_json: JSON.stringify(this.facts),
          prompt: snapshot.prompt,
          negative_prompt: snapshot.negativePrompt,
          safety: snapshot.safety,
          artists_json: JSON.stringify(snapshot.artists),
          loras_json: JSON.stringify(snapshot.loras),
          comfy_params_json: JSON.stringify({
            unet_name: this.unetName,
            clip_name: this.clipName,
            vae_name: this.vaeName,
            width: snapshot.width,
            height: snapshot.height,
            steps: snapshot.steps,
            cfg: snapshot.cfg,
            sampler_name: snapshot.sampler,
            scheduler: snapshot.scheduler,
            seed: snapshot.seed,
            comfy_prompt_id: promptId,
            comfy_image_url: this.generationComfyUrl || undefined,
            persisted: this.generationPersisted,
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
          v: 2,
          rawInput: this.rawInput,
          lastParsedInput: this.lastParsedInput,
          safety: this.safety,
          selectedPresetId: this.selectedPresetId,
          selectedRuleIds: this.selectedRuleIds,
          selectedArtistIds: this.selectedArtists.map(a => a.id),
          activeLoras: this.activeLoras.map(i => ({ id: i.lora.id, strength: i.strength, isEnabled: i.isEnabled })),
          positivePrompt: this.positivePrompt,
          negativePrompt: this.negativePrompt,
          extraNegative: this.extraNegative,
          facts: this.facts,
          isSemanticDirty: this.isSemanticDirty,
          isPositivePromptDirty: this.isPositivePromptDirty,
          isNegativePromptDirty: this.isNegativePromptDirty,
          width: this.width,
          height: this.height,
          steps: this.steps,
          cfg: this.cfg,
          seed: this.seed,
          lastGeneratedSeed: this.lastGeneratedSeed,
          lastGenerationSnapshot: this.lastGenerationSnapshot,
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
        if (!d || typeof d.rawInput !== 'string') return false
        if (d.v !== 1 && d.v !== 2) return false

        // 逐字段安全恢复：类型不符的字段安全忽略，绝不因旧/脏草稿导致 Studio 启动失败
        if (typeof d.rawInput === 'string') this.rawInput = d.rawInput
        if (typeof d.lastParsedInput === 'string') this.lastParsedInput = d.lastParsedInput
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
        if (typeof d.lastGeneratedSeed === 'number' && d.lastGeneratedSeed >= 0) this.lastGeneratedSeed = d.lastGeneratedSeed
        if (d.lastGenerationSnapshot && typeof d.lastGenerationSnapshot === 'object') {
          this.lastGenerationSnapshot = d.lastGenerationSnapshot
        }
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

        // ── 语义状态：facts / dirty ──
        // v2 草稿：完整恢复 facts 与 dirty 标记。
        // 无可信 facts（旧版 v1 或字段异常）：保留恢复出的 Prompt，但标记需要重新解析，
        // 绝不用空 facts 自动 build 覆盖恢复的 Prompt（buildPrompt 已加空 facts 保护）。
        const hasFacts = d.facts
          && Array.isArray(d.facts.entities)
          && Array.isArray(d.facts.statements)
        if (hasFacts) {
          this.facts = { entities: d.facts.entities, statements: d.facts.statements }
          if (typeof d.isSemanticDirty === 'boolean') this.isSemanticDirty = d.isSemanticDirty
          if (typeof d.isPositivePromptDirty === 'boolean') this.isPositivePromptDirty = d.isPositivePromptDirty
          if (typeof d.isNegativePromptDirty === 'boolean') this.isNegativePromptDirty = d.isNegativePromptDirty
        } else {
          this.facts = { entities: [], statements: [] }
          this.isSemanticDirty = true
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
      this.lastParsedInput = ''
      this.isSemanticDirty = false
      this.safety = 'Safe'
      this.selectedPresetId = null
      this.selectedRuleIds = []
      this.selectedArtists = []
      this.activeLoras = this.activeLoras.map(i => ({ ...i, isEnabled: false }))
      this.positivePrompt = ''
      this.negativePrompt = ''
      this.extraNegative = ''
      this.isPositivePromptDirty = false
      this.isNegativePromptDirty = false
      // 语义状态彻底清空，防止旧场景残留
      this.facts = { entities: [], statements: [] }
      // 生成 stale 状态清空
      this.seed = -1
      this.lastGeneratedSeed = null
      this.activeGenerationSnapshot = null
      this.lastGenerationSnapshot = null
      this.generatedImageUrl = ''
      this.generationComfyUrl = ''
      this.generationPersisted = false
      this.generationProgress = 0
      this.generationStage = 'idle'
      this.generationMessage = ''
      this.generationError = null
      this.generationQueuePosition = null
      this.generationProgressValue = null
      this.generationProgressMax = null
      this.draftRestored = false
    },
  }
})
