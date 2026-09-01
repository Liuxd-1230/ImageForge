import { defineStore } from 'pinia'
import axios from 'axios'
import type { SemanticFacts, Entity, Statement, SafetyLevel, Artist, Lora, ReasoningEffort } from '../types'

export interface ActiveLoraItem {
  lora: Lora;
  strength: number;
  isEnabled: boolean;
}

export const useStudioStore = defineStore('studio', {
  state: () => ({
    rawInput: '',
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
    
    // Generated Prompt Outputs
    positivePrompt: '',
    negativePrompt: '',
    
    // LLM Provider & Model Control in Workbench
    provider: 'lm_studio' as 'lm_studio' | 'cloud',
    model: '',
    reasoningEffort: 'instruct' as ReasoningEffort,
    
    // ComfyUI Parameters & State (Anima-2.9B tuned defaults)
    comfyStatus: 'disconnected' as 'connected' | 'disconnected' | 'generating' | 'error',
    checkpoint: 'anima-preview.safetensors',
    samplerName: 'euler',
    scheduler: 'sgm_uniform',
    width: 1024,
    height: 1536,
    steps: 28,
    cfg: 4.5,
    seed: -1,
    generatedImageUrl: '' as string,
    generationProgress: 0,
    generationMessage: '',
    
    // Loading Flags
    isParsing: false,
    isBuilding: false,
    isGenerating: false,
  }),

  actions: {
    syncLorasFromLibrary(allLoras: Lora[]) {
      const existingMap = new Map(this.activeLoras.map(item => [item.lora.id, item]))
      this.activeLoras = allLoras.map(lora => {
        const exist = existingMap.get(lora.id)
        return {
          lora,
          strength: exist ? exist.strength : lora.default_strength,
          isEnabled: exist ? exist.isEnabled : false
        }
      })
    },

    toggleLora(loraId: number) {
      const item = this.activeLoras.find(i => i.lora.id === loraId)
      if (item) {
        item.isEnabled = !item.isEnabled
        this.buildPrompt()
      }
    },

    updateLoraStrength(loraId: number, strength: number) {
      const item = this.activeLoras.find(i => i.lora.id === loraId)
      if (item) {
        item.strength = strength
        if (item.isEnabled) {
          this.buildPrompt()
        }
      }
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

    async parsePrompt() {
      if (!this.rawInput.trim()) return
      this.isParsing = true
      try {
        const resp = await axios.post('/api/prompt/parse', {
          text: this.rawInput,
          preset_id: this.selectedPresetId,
          rule_ids: this.selectedRuleIds.length > 0 ? this.selectedRuleIds : undefined,
          provider: this.provider,
          model: this.model || undefined,
          reasoning_effort: this.reasoningEffort
        })
        this.facts = resp.data
        await this.buildPrompt()
      } catch (err: any) {
        console.error('Parse failed:', err)
        throw err
      } finally {
        this.isParsing = false
      }
    },

    async buildPrompt() {
      this.isBuilding = true
      try {
        const artistTags = this.selectedArtists.map(a => a.tags)
        const loraItems = this.activeLoras
          .filter(item => item.isEnabled)
          .map(item => ({
            filename: item.lora.filename,
            trigger_words: item.lora.trigger_words,
            strength: item.strength,
            is_enabled: true
          }))

        const resp = await axios.post('/api/prompt/build', {
          facts: this.facts,
          safety: this.safety,
          preset_id: this.selectedPresetId,
          artist_tags: artistTags,
          lora_items: loraItems,
          extra_negative: this.extraNegative
        })
        this.positivePrompt = resp.data.prompt
        this.negativePrompt = resp.data.negative_prompt
        this.facts = resp.data.facts
      } catch (err: any) {
        console.error('Build prompt failed:', err)
        throw err
      } finally {
        this.isBuilding = false
      }
    },

    async saveEntityTrigger(entity: Entity) {
      if (!entity.name || !entity.canonical_tag || !entity.caption_name) return
      try {
        await axios.post('/api/prompt/resolve-trigger', {
          name: entity.name,
          canonical_tag: entity.canonical_tag,
          caption_name: entity.caption_name,
          save_to_cache: true
        })
        await this.buildPrompt()
      } catch (err) {
        console.error('Save trigger mapping failed:', err)
      }
    },

    async generateImage() {
      if (!this.positivePrompt.trim()) {
        await this.buildPrompt()
      }
      this.isGenerating = true
      this.generationProgress = 10
      this.generationMessage = '正在组装 Anima-2.9B 工作流并提交 ComfyUI...'
      try {
        const loraItems = this.activeLoras
          .filter(item => item.isEnabled)
          .map(item => ({
            filename: item.lora.filename,
            trigger_words: item.lora.trigger_words,
            strength: item.strength,
            is_enabled: true
          }))

        const resp = await axios.post('/api/comfyui/generate', {
          positive_prompt: this.positivePrompt,
          negative_prompt: this.negativePrompt,
          checkpoint: this.checkpoint,
          loras: loraItems,
          width: this.width,
          height: this.height,
          steps: this.steps,
          cfg: this.cfg,
          sampler_name: this.samplerName,
          scheduler: this.scheduler,
          seed: this.seed === -1 ? Math.floor(Math.random() * 1000000000) : this.seed
        })

        const promptId = resp.data.prompt_id
        this.generationProgress = 30
        this.generationMessage = 'ComfyUI 正在生成图像...'
        
        let done = false
        let attempts = 0
        while (!done && attempts < 120) {
          await new Promise(r => setTimeout(r, 1500))
          attempts++
          this.generationProgress = Math.min(95, 30 + attempts * 2)
          try {
            const histResp = await axios.get(`/api/comfyui/history/${promptId}`)
            const histData = histResp.data[promptId]
            if (histData && histData.outputs) {
              for (const nodeId in histData.outputs) {
                const nodeOut = histData.outputs[nodeId]
                if (nodeOut.images && nodeOut.images.length > 0) {
                  const img = nodeOut.images[0]
                  this.generatedImageUrl = `/api/comfyui/view?filename=${img.filename}&subfolder=${img.subfolder}&type=${img.type}`
                  done = true
                  this.generationProgress = 100
                  this.generationMessage = '生成完成！'
                  
                  await axios.post('/api/history', {
                    raw_input: this.rawInput,
                    parsed_facts_json: JSON.stringify(this.facts),
                    prompt: this.positivePrompt,
                    negative_prompt: this.negativePrompt,
                    safety: this.safety,
                    artists_json: JSON.stringify(this.selectedArtists),
                    loras_json: JSON.stringify(this.activeLoras.filter(i => i.isEnabled)),
                    comfy_params_json: JSON.stringify({
                      checkpoint: this.checkpoint,
                      width: this.width,
                      height: this.height,
                      steps: this.steps,
                      cfg: this.cfg,
                      sampler: this.samplerName,
                      scheduler: this.scheduler
                    }),
                    image_path: this.generatedImageUrl
                  })
                  break
                }
              }
            }
          } catch (e) {
            // Processing
          }
        }
      } catch (err: any) {
        this.generationMessage = `生图失败: ${err.response?.data?.detail || err.message}`
        throw err
      } finally {
        this.isGenerating = false
      }
    },

    removeEntity(index: number) {
      const e = this.facts.entities[index]
      if (e) {
        this.facts.statements = this.facts.statements.filter(s => s.subject !== e.id && s.target !== e.id)
        this.facts.entities.splice(index, 1)
        this.buildPrompt()
      }
    },

    removeStatement(index: number) {
      this.facts.statements.splice(index, 1)
      this.buildPrompt()
    },

    addStatement(statement: Statement) {
      this.facts.statements.push(statement)
      this.buildPrompt()
    }
  }
})
