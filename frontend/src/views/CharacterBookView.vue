<template>
  <v-container fluid class="pa-4">
    <div class="d-flex justify-space-between align-center mb-4">
      <div>
        <h1 class="text-h5 font-weight-bold">用户角色书</h1>
        <div class="text-caption text-grey">在此定义自定义角色外观，生图时角色书将作为覆盖层展开，名字不会作为 Anima tag 发送。</div>
      </div>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
        新建角色
      </v-btn>
    </div>

    <!-- Search & Filters -->
    <v-row class="mb-2">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="characterStore.searchQuery"
          label="搜索角色"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          clearable
        />
      </v-col>
    </v-row>

    <!-- Character Cards Grid -->
    <v-row>
      <v-col
        v-for="char in filteredCharacters"
        :key="char.id"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card variant="outlined" class="h-100 d-flex flex-column pa-4 rounded-lg">
          <div class="d-flex justify-space-between align-center mb-2">
            <span class="text-subtitle-1 font-weight-bold">{{ char.name }}</span>
            <div>
              <v-btn
                :icon="char.is_favorite ? 'mdi-star' : 'mdi-star-outline'"
                :color="char.is_favorite ? 'amber' : 'grey'"
                size="small"
                variant="text"
                @click="characterStore.toggleFavorite(char)"
              />
              <v-btn
                icon="mdi-pencil"
                size="small"
                variant="text"
                color="primary"
                @click="openEditDialog(char)"
              />
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                @click="deleteChar(char.id!)"
              />
            </div>
          </div>

          <div class="text-caption text-grey mb-2">
            别名: {{ char.aliases || '无' }}
          </div>

          <!-- Feature tags summary -->
          <div class="d-flex flex-wrap gap-1 mb-3 flex-grow-1">
            <v-chip v-if="char.hair_color || char.hair_style" size="x-small" variant="tonal">
              发型: {{ [char.hair_length, char.hair_style, char.hair_color].filter(Boolean).join(' ') }}
            </v-chip>
            <v-chip v-if="char.eye_color" size="x-small" variant="tonal">
              眼睛: {{ char.eye_color }}
            </v-chip>
            <v-chip v-if="char.top || char.bottom" size="x-small" variant="tonal">
              默认服装: {{ [char.top, char.bottom].filter(Boolean).join(', ') }}
            </v-chip>
          </div>

          <div class="text-caption text-grey-darken-1 text-truncate">
            {{ char.extra_description || '暂无补充描述' }}
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Character Edit Dialog -->
    <v-dialog v-model="dialog" max-width="700px">
      <v-card class="pa-4 rounded-lg">
        <v-card-title class="font-weight-bold">
          {{ isEdit ? '编辑角色' : '新建角色' }}
        </v-card-title>
        <v-card-text class="pt-2">
          <!-- Basic Info -->
          <v-row dense class="mb-2">
            <v-col cols="12" sm="6">
              <v-text-field v-model="form.name" label="角色名称 (必填)" density="compact" variant="outlined" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="form.aliases" label="别名 (逗号分隔)" density="compact" variant="outlined" />
            </v-col>
            <v-col cols="4">
              <v-text-field v-model="form.gender" label="性别 (woman/girl/man)" density="compact" variant="outlined" />
            </v-col>
            <v-col cols="4">
              <v-text-field v-model="form.age_group" label="年龄段 (young adult/teen)" density="compact" variant="outlined" />
            </v-col>
            <v-col cols="4">
              <v-text-field v-model="form.body" label="身材 (petite/slender)" density="compact" variant="outlined" />
            </v-col>
          </v-row>

          <v-expansion-panels variant="accordion" class="mb-3">
            <!-- Head / Hair / Eyes -->
            <v-expansion-panel title="头部与面部 (Hair & Eyes)">
              <v-expansion-panel-text>
                <v-row dense>
                  <v-col cols="4">
                    <v-text-field v-model="form.hair_color" label="发色 (black/blonde)" density="compact" variant="outlined" />
                  </v-col>
                  <v-col cols="4">
                    <v-text-field v-model="form.hair_style" label="发型 (straight/twintails)" density="compact" variant="outlined" />
                  </v-col>
                  <v-col cols="4">
                    <v-text-field v-model="form.hair_length" label="发长 (long/short)" density="compact" variant="outlined" />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field v-model="form.eye_color" label="瞳色 (green/blue)" density="compact" variant="outlined" />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field v-model="form.headwear" label="头饰 (hairband/ribbon)" density="compact" variant="outlined" />
                  </v-col>
                </v-row>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Default Outfit -->
            <v-expansion-panel title="默认服装 (Default Outfit)">
              <v-expansion-panel-text>
                <v-row dense>
                  <v-col cols="6">
                    <v-text-field v-model="form.top" label="上衣 (white blouse)" density="compact" variant="outlined" />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field v-model="form.bottom" label="下装 (black pleated skirt)" density="compact" variant="outlined" />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field v-model="form.socks" label="袜子 (black thighhighs)" density="compact" variant="outlined" />
                  </v-col>
                  <v-col cols="6">
                    <v-text-field v-model="form.shoes" label="鞋子 (brown loafers)" density="compact" variant="outlined" />
                  </v-col>
                </v-row>
              </v-expansion-panel-text>
            </v-expansion-panel>

            <!-- Other -->
            <v-expansion-panel title="补充描述 (Extra Description)">
              <v-expansion-panel-text>
                <v-textarea
                  v-model="form.extra_description"
                  label="补充外观/特征描述"
                  density="compact"
                  variant="outlined"
                  rows="2"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>

        <v-card-actions class="justify-end">
          <v-btn variant="text" @click="dialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!form.name.trim()" @click="saveChar">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
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
  facial_features: '',
  headwear: '',
  top: '',
  outer: '',
  bottom: '',
  socks: '',
  shoes: '',
  accessories: '',
  default_expression: '',
  default_pose: '',
  negative_traits: '',
  extra_description: '',
  category: '默认',
  is_favorite: false
})

onMounted(() => {
  characterStore.fetchCharacters()
})

const filteredCharacters = computed(() => {
  let list = characterStore.characters
  if (characterStore.searchQuery) {
    const q = characterStore.searchQuery.toLowerCase()
    list = list.filter(c => c.name.toLowerCase().includes(q) || (c.aliases && c.aliases.toLowerCase().includes(q)))
  }
  return list
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
    facial_features: '',
    headwear: '',
    top: '',
    outer: '',
    bottom: '',
    socks: '',
    shoes: '',
    accessories: '',
    default_expression: '',
    default_pose: '',
    negative_traits: '',
    extra_description: '',
    category: '默认',
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
  if (confirm('确定删除该角色吗？')) {
    await characterStore.deleteCharacter(id)
  }
}
</script>

<style scoped>
.gap-1 {
  gap: 4px;
}
</style>
