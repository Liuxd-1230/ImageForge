<template>
  <div class="app-page-container">
    <!-- Top Action Bar -->
    <div class="d-flex justify-space-between align-center mb-3">
      <div>
        <div class="page-header-title">角色库 (Character Library)</div>
        <div class="text-caption text-grey">统一管理已解析角色缓存与自定义角色设定。</div>
      </div>
      <v-btn v-if="tab === 'custom'" color="primary" variant="flat" size="small" prepend-icon="mdi-plus" class="px-3" @click="openCreateDialog">
        新建角色
      </v-btn>
    </div>

    <!-- Segmented: 已解析角色 / 自定义角色 -->
    <div class="library-segmented mb-3">
      <button
        type="button"
        :class="['library-seg-btn', { active: tab === 'resolved' }]"
        @click="tab = 'resolved'"
      >已解析角色</button>
      <button
        type="button"
        :class="['library-seg-btn', { active: tab === 'custom' }]"
        @click="tab = 'custom'"
      >自定义角色</button>
    </div>

    <!-- ════════ 已解析角色（Trigger Cache） ════════ -->
    <template v-if="tab === 'resolved'">
      <!-- 搜索 + 全选/批量删除 toolbar -->
      <v-card variant="flat" class="if-panel pa-2 mb-3 library-toolbar">
        <div class="d-flex align-center gap-2 flex-wrap">
          <v-text-field
            v-model="cacheStore.searchQuery"
            label="搜索角色名 / Tag / 作品"
            prepend-inner-icon="mdi-magnify"
            density="compact"
            variant="outlined"
            hide-details
            class="text-caption library-search"
            clearable
          />
          <div class="d-flex align-center gap-2 ml-auto">
            <template v-if="cacheSel.selectedCount > 0">
              <span class="text-caption font-mono">已选择 {{ cacheSel.selectedCount }} 项</span>
              <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete" @click="openBulkDelete('resolved')">
                删除所选
              </v-btn>
            </template>
            <v-btn size="small" variant="tonal" :prepend-icon="cacheSel.isAllSelected ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline'" @click="cacheSel.toggleAll()">
              {{ cacheSel.isAllSelected ? '取消全选' : '全选' }}
            </v-btn>
          </div>
        </div>
      </v-card>

      <div v-if="cacheStore.filtered.length === 0" class="if-empty text-center py-12 text-grey">
        <v-icon size="40" class="mb-2 opacity-50">mdi-database-search-outline</v-icon>
        <div class="text-body-2 font-weight-medium">{{ cacheStore.items.length === 0 ? '还没有已解析角色' : '无匹配结果' }}</div>
        <div class="text-caption mt-1">首次解析（含 &lt;角色名&gt; 显式标记）成功后会自动写入这里的本地缓存，下次直接复用。</div>
      </div>

      <div v-else class="d-flex flex-column gap-2">
        <div
          v-for="row in cacheStore.filtered"
          :key="row.id"
          :class="['resolved-row', { selected: cacheSel.isSelected(row.id) }]"
        >
          <label class="row-check">
            <input type="checkbox" :checked="cacheSel.isSelected(row.id)" @change="cacheSel.toggleOne(row.id)" />
          </label>
          <div class="resolved-main">
            <div class="resolved-title">
              <span class="resolved-name">{{ row.name }}</span>
              <span :class="['source-badge', row.source]">{{ sourceLabel(row.source) }}</span>
            </div>
            <div class="resolved-fields">
              <span class="resolved-field">角色 Tag <b class="mono">{{ row.canonical_tag }}</b></span>
              <span v-if="row.series_tag" class="resolved-field">作品 <b class="mono">{{ row.series_tag }}</b></span>
              <span v-if="row.caption_name" class="resolved-field">Caption <b class="mono">{{ row.caption_name }}</b></span>
            </div>
            <div class="resolved-meta text-caption text-grey">
              <span v-if="row.aliases" class="mono">别名: {{ row.aliases }}</span>
              <span v-if="row.resolved_at">最近解析 {{ formatTime(row.resolved_at) }}</span>
            </div>
          </div>
          <div class="resolved-actions">
            <v-btn size="x-small" variant="text" color="primary" prepend-icon="mdi-pencil-outline" @click="openCacheEdit(row)">编辑</v-btn>
            <v-btn size="x-small" variant="text" color="info" prepend-icon="mdi-refresh" @click="reResolve(row)">联网刷新</v-btn>
            <v-btn size="x-small" variant="text" color="error" prepend-icon="mdi-delete-outline" @click="openBulkDelete('resolved', [row.id])">删除</v-btn>
          </div>
        </div>
      </div>
    </template>

    <!-- ════════ 自定义角色（Character Book） ════════ -->
    <template v-else>

    <!-- Search & Filter Bar + 全选/批量删除 -->
    <v-card variant="flat" class="if-panel pa-2 mb-3 library-toolbar">
      <div class="d-flex align-center gap-2 flex-wrap">
        <v-text-field
          v-model="characterStore.searchQuery"
          label="搜索角色名称、别名或特征"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          class="text-caption library-search"
          clearable
        />
        <div class="d-flex align-center gap-2 ml-auto">
          <template v-if="customSel.selectedCount > 0">
            <span class="text-caption font-mono">已选择 {{ customSel.selectedCount }} 项</span>
            <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete" @click="openBulkDelete('custom')">
              删除所选
            </v-btn>
          </template>
          <v-btn size="small" variant="tonal" :prepend-icon="customSel.isAllSelected ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline'" @click="customSel.toggleAll()">
            {{ customSel.isAllSelected ? '取消全选' : '全选' }}
          </v-btn>
          <span class="text-caption text-grey font-mono">共 {{ filteredCharacters.length }} 个角色设定</span>
        </div>
      </div>
    </v-card>

    <!-- Character Cards Grid -->
    <div v-if="filteredCharacters.length === 0" class="if-empty text-center py-12 text-grey">
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
              <label class="row-check card-check">
                <input type="checkbox" :checked="customSel.isSelected(char.id)" @change="customSel.toggleOne(char.id)" />
              </label>
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
                @click="openBulkDelete('custom', [char.id!])"
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
    </template>

    <!-- ════════ 已解析角色：编辑 metadata ════════ -->
    <v-dialog v-model="cacheDialog" max-width="520px">
      <v-card class="pa-4 bg-surface rounded-2xl">
        <div class="d-flex justify-space-between align-center mb-3">
          <span class="text-subtitle-1 font-weight-bold">编辑角色元数据 — {{ cacheForm.name }}</span>
          <v-btn icon="mdi-close" variant="text" size="small" @click="cacheDialog = false" />
        </div>
        <div class="d-flex flex-column gap-3">
          <v-text-field v-model="cacheForm.canonical_tag" label="角色 Tag（canonical）" density="compact" variant="outlined" />
          <v-text-field v-model="cacheForm.series_tag" label="作品 Tag（series）" density="compact" variant="outlined" />
          <v-text-field v-model="cacheForm.caption_name" label="Caption Name" density="compact" variant="outlined" />
          <v-textarea v-model="cacheForm.aliases" label="别名（逗号分隔）" density="compact" variant="outlined" rows="2" hide-details />
          <div class="text-caption text-grey">保存后来源记为 manual：自动联网只补空字段，不会覆盖这里的值。</div>
        </div>
        <v-card-actions class="justify-end mt-3 pt-2 border-t">
          <v-btn variant="text" size="small" @click="cacheDialog = false">取消</v-btn>
          <v-btn color="info" variant="tonal" size="small" prepend-icon="mdi-refresh" :disabled="cacheResolving" @click="reResolveForce()">
            {{ cacheResolving ? '解析中…' : '重新解析并替换' }}
          </v-btn>
          <v-btn color="primary" variant="flat" size="small" @click="saveCacheEdit">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ════════ 多候选选择 ════════ -->
    <v-dialog v-model="ambDialog" max-width="520px">
      <v-card class="pa-4 bg-surface rounded-2xl">
        <div class="text-subtitle-1 font-weight-bold mb-2">找到多个候选 — {{ ambName }}</div>
        <div class="d-flex flex-column gap-2">
          <div
            v-for="(c, i) in ambCands"
            :key="i"
            class="amb-row"
            @click="pickAmbCandidate(i)"
          >
            <span class="mono">{{ c.canonical_tag }}</span>
            <span v-if="c.series_tag" class="mono text-grey"> / {{ c.series_tag }}</span>
            <span v-if="c.caption_name" class="mono amb-cap">{{ c.caption_name }}</span>
          </div>
        </div>
        <v-card-actions class="justify-end mt-2 pt-2 border-t">
          <v-btn variant="text" size="small" @click="ambDialog = false">取消</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ════════ 删除确认（M3 Dialog，非 browser confirm） ════════ -->
    <v-dialog v-model="delDialog" max-width="440px">
      <v-card class="pa-4 bg-surface rounded-2xl">
        <div class="d-flex align-center gap-2 mb-2">
          <v-icon color="error">mdi-delete-alert-outline</v-icon>
          <span class="text-subtitle-1 font-weight-bold">{{ delIds.length === 1 ? '删除此角色？' : `删除所选 ${delIds.length} 项？` }}</span>
        </div>
        <p class="text-caption text-grey mb-0">
          {{ delSemantics }}
        </p>
        <v-card-actions class="justify-end mt-3 pt-2 border-t">
          <v-btn variant="text" size="small" @click="delDialog = false">取消</v-btn>
          <v-btn color="error" variant="flat" size="small" :loading="delLoading" @click="confirmBulkDelete">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useCharacterStore } from '../stores/character'
import { useCharacterCacheStore, type ResolvedCharacter } from '../stores/characterCache'
import { useBulkSelection } from '../composables/useBulkSelection'
import type { Character } from '../types'

const characterStore = useCharacterStore()
const cacheStore = useCharacterCacheStore()

const tab = ref<'resolved' | 'custom'>('resolved')
const dialog = ref(false)
const isEdit = ref(false)

const form = ref<Character>({
  name: '',
  aliases: '',
  gender: '',
  age_group: '',
  body: '',
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
    gender: '',
    age_group: '',
    body: '',
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

/* ════ 已解析角色（Trigger Cache）tab ════ */
const cacheSel = useBulkSelection(() => cacheStore.filtered as ResolvedCharacter[])
const customSel = useBulkSelection(() => filteredCharacters.value as Character[])

const cacheDialog = ref(false)
const cacheForm = reactive<{ id: number | null; name: string; canonical_tag: string; series_tag: string; caption_name: string; aliases: string }>({
  id: null, name: '', canonical_tag: '', series_tag: '', caption_name: '', aliases: '',
})
const cacheResolving = ref(false)

const ambDialog = ref(false)
const ambName = ref('')
const ambCands = ref<any[]>([])
let ambTargetId: number | null = null
let ambForce = false

const delDialog = ref(false)
const delIds = ref<Array<number | string>>([])
const delKind = ref<'resolved' | 'custom'>('resolved')
const delSemantics = ref('')
const delLoading = ref(false)

onMounted(() => {
  characterStore.fetchCharacters()
  cacheStore.fetchCache()
})

function sourceLabel(src: string): string {
  if (src === 'manual') return 'manual（手工）'
  if (src === 'online') return 'online'
  if (src === 'llm') return 'llm'
  return '本地'
}

function formatTime(iso: string | null): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

function openCacheEdit(row: ResolvedCharacter) {
  cacheForm.id = row.id
  cacheForm.name = row.name
  cacheForm.canonical_tag = row.canonical_tag
  cacheForm.series_tag = row.series_tag
  cacheForm.caption_name = row.caption_name
  cacheForm.aliases = row.aliases || ''
  cacheDialog.value = true
}

async function saveCacheEdit() {
  if (cacheForm.id == null) return
  await cacheStore.updateItem(cacheForm.id, {
    canonical_tag: cacheForm.canonical_tag,
    series_tag: cacheForm.series_tag,
    caption_name: cacheForm.caption_name,
    aliases: cacheForm.aliases,
  })
  cacheDialog.value = false
}

/** 重新解析（默认不覆盖 manual 非空值）。唯一结果直接更新；多候选弹选择。 */
async function reResolve(row: ResolvedCharacter, force = false) {
  ambForce = force
  try {
    const d = await cacheStore.reResolve(row.name, force)
    if (d.status === 'resolved') {
      await cacheStore.fetchCache()
    } else if (d.status === 'ambiguous') {
      ambName.value = row.name
      ambCands.value = d.candidates || []
      ambTargetId = row.id
      ambDialog.value = true
    } else {
      alert(`未找到可靠结果（${d.status}）`)
    }
  } catch (e: any) {
    console.error('re-resolve failed', e)
  }
}

async function reResolveForce() {
  if (cacheForm.id == null) return
  cacheResolving.value = true
  try {
    await reResolve({ name: cacheForm.name } as ResolvedCharacter, true)
  } finally {
    cacheResolving.value = false
    cacheDialog.value = false
  }
}

async function pickAmbCandidate(i: number) {
  if (!ambTargetId) return
  try {
    await cacheStore.confirmCandidate(ambName.value, i, ambForce)
    await cacheStore.fetchCache()
  } catch (e) {
    console.error('confirm failed', e)
  }
  ambDialog.value = false
  ambTargetId = null
}

function openBulkDelete(kind: 'resolved' | 'custom', ids?: Array<number | string>) {
  if (ids) {
    delIds.value = ids
  } else if (kind === 'resolved') {
    delIds.value = [...cacheSel.selected]
  } else {
    delIds.value = [...customSel.selected]
  }
  if (delIds.value.length === 0) return
  delKind.value = kind
  delSemantics.value = kind === 'resolved'
    ? '只删除本地已解析角色缓存记录（Trigger Cache），不影响模型、图片或自定义角色。'
    : '只删除自定义角色设定（Character Book）记录，不影响已解析缓存或其他资源。'
  delDialog.value = true
}

async function confirmBulkDelete() {
  if (delIds.value.length === 0) return
  delLoading.value = true
  try {
    if (delKind.value === 'resolved') {
      const ids = delIds.value.map(Number)
      const failed = await cacheStore.bulkDelete(ids)
      cacheSel.clear()
      if (failed.length) alert(`删除失败 ${failed.length} 项`)
    } else {
      const failed: Array<number | string> = []
      for (const id of delIds.value) {
        try { await characterStore.deleteCharacter(Number(id)) } catch { failed.push(id) }
      }
      customSel.clear()
      if (failed.length) alert(`删除失败 ${failed.length} 项`)
    }
  } finally {
    delLoading.value = false
    delDialog.value = false
  }
}
</script>

<style scoped>
.gap-1 { gap: 4px; }
.gap-2 { gap: 8px; }
.gap-3 { gap: 12px; }
.character-card {
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.character-card:hover {
  border-color: rgb(var(--v-theme-primary)) !important;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
}

/* ════ 角色库 segmented ════ */
.library-segmented {
  display: inline-flex;
  padding: 4px;
  border-radius: var(--if-radius-container, 24px);
  background: rgb(var(--v-theme-surface-container));
  gap: 4px;
}
.library-seg-btn {
  border: 0;
  padding: 7px 18px;
  border-radius: 999px;
  background: transparent;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 650;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  transition: background var(--motion-fast, 160ms) var(--motion-emphasized, ease);
}
.library-seg-btn.active {
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
}
.library-search { max-width: 380px; }
.library-toolbar { border-radius: var(--if-radius-container, 24px) !important; }

/* ════ resolved rows ════ */
.resolved-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: var(--if-radius-card, 20px);
  background: rgb(var(--v-theme-surface));
  transition: border-color 0.15s ease;
}
.resolved-row.selected { border-color: rgb(var(--v-theme-primary)); }
.row-check {
  display: inline-flex;
  align-items: center;
  margin-top: 2px;
  cursor: pointer;
}
.row-check input[type="checkbox"] {
  width: 17px;
  height: 17px;
  accent-color: rgb(var(--v-theme-primary));
  cursor: pointer;
}
.card-check { margin-left: 0; }
.resolved-main { flex: 1; min-width: 0; }
.resolved-title { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.resolved-name { font-size: 14.5px; font-weight: 750; }
.resolved-fields { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 6px; font-size: 12.5px; color: rgb(var(--v-theme-on-surface-variant)); }
.resolved-field b { color: rgb(var(--v-theme-primary)); font-weight: 650; }
.resolved-meta { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 4px; }
.resolved-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.source-badge {
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 650;
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-on-surface-variant));
}
.source-badge.manual { background: rgba(var(--v-theme-warning), 0.16); color: rgb(var(--v-theme-on-surface)); }
.source-badge.online { background: rgba(var(--v-theme-primary), 0.14); color: rgb(var(--v-theme-primary)); }
.amb-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid rgba(var(--v-theme-primary), 0.35);
  border-radius: var(--if-radius-field, 16px);
  background: rgba(var(--v-theme-primary), 0.06);
  font-size: 13px;
  cursor: pointer;
}
.amb-row:hover { background: rgba(var(--v-theme-primary), 0.12); }
.amb-cap { margin-left: auto; color: rgb(var(--v-theme-on-surface-variant)); }
</style>
