<template>
  <div class="app-page-container">
    <!-- Top Action Bar -->
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <div class="page-header-title">用户角色书 (Character Database)</div>
        <div class="text-caption text-grey">在此定义自定义角色外观，生图时角色书将作为覆盖层展开，名字不会作为 Anima tag 发送。</div>
      </div>
      <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" class="px-3" @click="openCreateDialog">
        新建角色
      </v-btn>
    </div>

    <!-- Search & Filter Bar -->
    <v-card variant="outlined" class="pa-2 mb-3 bg-surface rounded-lg">
      <div class="d-flex align-center gap-2">
        <v-text-field
          v-model="characterStore.searchQuery"
          label="搜索角色名称、别名或特征"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          class="text-caption"
          style="max-width: 360px;"
          clearable
        />
        <div class="text-caption text-grey ml-auto font-mono">
          共 {{ filteredCharacters.length }} 个角色设定
        </div>
      </div>
    </v-card>

    <!-- Character Cards Grid -->
    <div v-if="filteredCharacters.length === 0" class="text-center py-12 text-grey border rounded-lg bg-surface">
      <v-icon size="40" class="mb-2 opacity-50">mdi-account-search-outline</v-icon>
      <div class="text-body-2 font-weight-medium">未找到角色设定</div>
      <div class="text-caption mt-1">点击右上角“新建角色”开始录入人物外貌与服装设定。</div>
    </div>

    <v-row v-else dense>
      <v-col
        v-for="char in filteredCharacters"
        :key="char.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card variant="outlined" class="h-100 d-flex flex-column pa-3 bg-surface rounded-lg character-card">
          <!-- Card Header: Avatar Initial, Name, Actions -->
          <div class="d-flex justify-space-between align-center mb-2 pb-2 border-b">
            <div class="d-flex align-center gap-2">
              <v-avatar size="32" color="primary" variant="tonal" class="font-weight-bold text-caption">
                {{ char.name.charAt(0) }}
              </v-avatar>
              <div class="d-flex flex-column">
                <span class="font-weight-bold text-body-2">{{ char.name }}</span>
                <span class="text-caption text-grey" style="font-size: 0.7rem !important;">
                  {{ char.aliases ? `别名: ${char.aliases}` : '无别名' }}
                </span>
              </div>
            </div>

            <div class="d-flex align-center">
              <v-btn
                :icon="char.is_favorite ? 'mdi-star' : 'mdi-star-outline'"
                :color="char.is_favorite ? 'amber' : 'grey'"
                size="x-small"
                variant="text"
                title="收藏"
                @click="characterStore.toggleFavorite(char)"
              />
              <v-btn
                icon="mdi-pencil-outline"
                size="x-small"
                variant="text"
                color="primary"
                title="编辑"
                @click="openEditDialog(char)"
              />
              <v-btn
                icon="mdi-delete-outline"
                size="x-small"
                variant="text"
                color="error"
                title="删除"
                @click="deleteChar(char.id!)"
              />
            </div>
          </div>

          <!-- Character Identity Attributes -->
          <div class="d-flex gap-1 mb-2">
            <v-chip v-if="char.gender" size="x-small" variant="tonal" color="purple">
              {{ char.gender }}
            </v-chip>
            <v-chip v-if="char.age_group" size="x-small" variant="tonal" color="secondary">
              {{ char.age_group }}
            </v-chip>
            <v-chip v-if="char.body" size="x-small" variant="tonal">
              {{ char.body }}
            </v-chip>
          </div>

          <!-- Appearance & Features -->
          <div class="d-flex flex-column gap-1 mb-2 flex-grow-1 text-caption">
            <div v-if="char.hair_color || char.hair_style" class="d-flex align-start gap-1">
              <span class="text-grey flex-shrink-0">发型:</span>
              <span class="font-mono text-high-emphasis">{{ [char.hair_length, char.hair_style, char.hair_color].filter(Boolean).join(' ') }}</span>
            </div>
            <div v-if="char.eye_color" class="d-flex align-start gap-1">
              <span class="text-grey flex-shrink-0">瞳色:</span>
              <span class="font-mono text-high-emphasis">{{ char.eye_color }}</span>
            </div>
            <div v-if="char.top || char.bottom" class="d-flex align-start gap-1">
              <span class="text-grey flex-shrink-0">服装:</span>
              <span class="font-mono text-high-emphasis">{{ [char.top, char.bottom].filter(Boolean).join(', ') }}</span>
            </div>
            <div v-if="char.headwear" class="d-flex align-start gap-1">
              <span class="text-grey flex-shrink-0">头饰:</span>
              <span class="font-mono text-high-emphasis">{{ char.headwear }}</span>
            </div>
          </div>

          <!-- Description Footer -->
          <div class="pt-2 border-t text-caption text-grey text-truncate">
            {{ char.extra_description || '暂无补充描述' }}
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Character Create / Edit Dialog -->
    <v-dialog v-model="dialog" max-width="680px">
      <v-card class="pa-4 bg-surface rounded-lg">
        <div class="d-flex justify-space-between align-center mb-3">
          <span class="text-subtitle-1 font-weight-bold">{{ isEdit ? '编辑角色设定' : '新建角色设定' }}</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="dialog = false" />
        </div>

        <div class="d-flex flex-column gap-3">
          <!-- Section 1: 基础身份 -->
          <div class="pa-3 rounded border bg-surface-variant">
            <div class="section-label mb-2 text-primary">1. 基础身份与识别</div>
            <v-row dense>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.name" label="角色名称 (必填，如: 穗穗)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-text-field v-model="form.aliases" label="别名 / 简称 (逗号分隔)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="4">
                <v-text-field v-model="form.gender" label="性别 (woman/girl/man)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="4">
                <v-text-field v-model="form.age_group" label="年龄段 (young adult/teen)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="4">
                <v-text-field v-model="form.body" label="体态身材 (petite/slender)" density="compact" variant="outlined" />
              </v-col>
            </v-row>
          </div>

          <!-- Section 2: 头部发型与面容 -->
          <div class="pa-3 rounded border bg-surface-variant">
            <div class="section-label mb-2 text-info">2. 头部发型与面部特征</div>
            <v-row dense>
              <v-col cols="4">
                <v-text-field v-model="form.hair_color" label="发色 (如: blonde)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="4">
                <v-text-field v-model="form.hair_style" label="发型 (如: twintails)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="4">
                <v-text-field v-model="form.hair_length" label="发长 (如: long hair)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="form.eye_color" label="瞳色 (如: blue eyes)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="form.headwear" label="头饰/配饰 (如: ribbon)" density="compact" variant="outlined" />
              </v-col>
            </v-row>
          </div>

          <!-- Section 3: 默认服装 -->
          <div class="pa-3 rounded border bg-surface-variant">
            <div class="section-label mb-2 text-purple">3. 默认服装设定 (可被场景要求覆盖)</div>
            <v-row dense>
              <v-col cols="6">
                <v-text-field v-model="form.top" label="上衣 (如: white shirt)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="form.bottom" label="下装 (如: pleated skirt)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="form.socks" label="袜子 (如: thighhighs)" density="compact" variant="outlined" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model="form.shoes" label="鞋履 (如: loafers)" density="compact" variant="outlined" />
              </v-col>
            </v-row>
          </div>

          <!-- Section 4: 补充描述 -->
          <v-textarea
            v-model="form.extra_description"
            label="补充外貌/特征 Tag (英文描述)"
            density="compact"
            variant="outlined"
            rows="2"
            hide-details
          />
        </div>

        <v-card-actions class="justify-end mt-3 pt-2 border-t">
          <v-btn variant="text" size="small" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" size="small" :disabled="!form.name.trim()" @click="saveChar">保存设定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCharacterStore } from '../stores/character'
import type { Character } from '../types'

const characterStore = useCharacterStore()
const dialog = ref(false)
const isEdit = ref(false)

const form = ref<Character>({
  name: '',
  aliases: '',
  gender: 'woman',
  age_group: 'young adult',
  body: 'petite',
  hair_color: '',
  hair_style: '',
  hair_length: '',
  eye_color: '',
  headwear: '',
  top: '',
  bottom: '',
  socks: '',
  shoes: '',
  extra_description: '',
  is_favorite: false
})

const filteredCharacters = computed(() => {
  let list = characterStore.characters
  if (characterStore.searchQuery) {
    const q = characterStore.searchQuery.toLowerCase()
    list = list.filter(c =>
      c.name.toLowerCase().includes(q) ||
      (c.aliases && c.aliases.toLowerCase().includes(q)) ||
      (c.extra_description && c.extra_description.toLowerCase().includes(q))
    )
  }
  return list
})

onMounted(() => {
  characterStore.fetchCharacters()
})

function openCreateDialog() {
  isEdit.value = false
  form.value = {
    name: '',
    aliases: '',
    gender: 'woman',
    age_group: 'young adult',
    body: 'petite',
    hair_color: '',
    hair_style: '',
    hair_length: '',
    eye_color: '',
    headwear: '',
    top: '',
    bottom: '',
    socks: '',
    shoes: '',
    extra_description: '',
    is_favorite: false
  }
  dialog.value = true
}

function openEditDialog(char: Character) {
  isEdit.value = true
  form.value = { ...char }
  dialog.value = true
}

async function saveChar() {
  if (!form.value.name.trim()) return
  await characterStore.saveCharacter(form.value)
  dialog.value = false
}

async function deleteChar(id: number) {
  if (confirm('确定删除该角色设定吗？')) {
    await characterStore.deleteCharacter(id)
  }
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.character-card {
  transition: border-color 0.15s ease;
}
.character-card:hover {
  border-color: #4F46E5 !important;
}
</style>
