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
      // Keep only artists that still exist in library, and update to latest object
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
        try {
          await axios.post('/api/prompt/resolve-trigger', {
            name: entity.name,
            canonical_tag: entity.canonical_tag,
            caption_name: entity.caption_name,
            save_to_cache: true
          })
          await this.buildPrompt()
        } catch (err) {
          console.error('Failed to save trigger to cache:', err)
        }
      }
    },

    async parsePrompt() {
      if (!this.rawInput.trim()) return
      this.isParsing = true
      try {
        const resp = await axios.post('/api/prompt/parse', {
          text: this.rawInput,
          rule_ids: this.selectedRuleIds,
          provider: this.provider,
          model: this.model,
          reasoning_effort: this.reasoningEffort
        })
        this.facts = resp.data
        await this.buildPrompt()
      } catch (err) {
        console.error('Prompt parsing failed:', err)
      } finally {
        this.isParsing = false
      }
    },

    async buildPrompt() {
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

        this.positivePrompt = resp.data.prompt
        this.negativePrompt = resp.data.negative_prompt
        this.facts = resp.data.facts
      } catch (err) {
        console.error('Prompt compilation failed:', err)
      } finally {
        this.isBuilding = false
      }
    },

    async generateImage() {
      if (!this.positivePrompt) {
        await this.buildPrompt()
      }
      this.isGenerating = true
      this.generationProgress = 10
      this.generationMessage = '正在组装 Anima-2.9B 工作流并提交 ComfyUI...'
      
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

        const resp = await axios.post('/api/comfyui/generate', {
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
                      studio: {
                        selectedPresetId: this.selectedPresetId,
                        extraNegative: this.extraNegative,
                        provider: this.provider,
                        model: this.model,
                        reasoningEffort: this.reasoningEffort,
                        selectedRuleIds: this.selectedRuleIds
                      }
                    }),
                    image_path: this.generatedImageUrl
                  })
                  break
                }
              }
            }
          } catch (e) {
            console.warn('Waiting for ComfyUI task...', e)
          }
        }
      } catch (err) {
        console.error('Image generation error:', err)
        this.generationMessage = '生图失败，请检查 ComfyUI 连接与模型设置。'
      } finally {
        this.isGenerating = false
      }
    }
  }
})
