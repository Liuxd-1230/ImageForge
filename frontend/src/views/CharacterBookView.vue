<template>
  <div class="app-page-container charlib">
    <!-- ════════ Header ════════ -->
    <header class="cl-header">
      <div>
        <div class="page-header-title">角色库</div>
        <div class="page-header-subtitle">已解析的模型角色缓存与自定义角色设定，统一在这里管理。</div>
      </div>
      <m3e-button v-if="tab === 'custom'" variant="filled" @click="openCreateDialog">
        <span slot="icon" class="mdi mdi-plus" />
        新建角色
      </m3e-button>
    </header>

    <!-- ════════ Tabs：已解析角色 / 自定义角色（m3e-tabs，下划线指示器） ════════ -->
    <m3e-tabs class="cl-tabs" @change="onTabsChange">
      <m3e-tab :selected="tab === 'resolved'" @click="tab = 'resolved'">已解析角色</m3e-tab>
      <m3e-tab :selected="tab === 'custom'" @click="tab = 'custom'">自定义角色</m3e-tab>
    </m3e-tabs>

    <!-- ════════ 已解析角色（Trigger Cache） ════════ -->
    <template v-if="tab === 'resolved'">
      <!-- 搜索 + 全选/批量操作 toolbar -->
      <div class="cl-toolbar">
        <m3e-search-bar class="cl-search" clearable clear-label="清空搜索" @clear="cacheStore.searchQuery = ''">
          <span slot="leading" class="mdi mdi-magnify" />
          <input slot="input" v-model="cacheStore.searchQuery" placeholder="搜索角色名 / Tag / 作品 / 别名" />
        </m3e-search-bar>
        <div class="cl-toolbar-right">
          <template v-if="cacheSel.selectedCount > 0">
            <span class="cl-sel-count">已选 {{ cacheSel.selectedCount }} 项</span>
            <m3e-button variant="tonal" class="cl-btn-danger" @click="openBulkDelete('resolved')">
              <span slot="icon" class="mdi mdi-delete-outline" />
              删除所选
            </m3e-button>
          </template>
          <div class="cl-select-all">
            <m3e-checkbox
              :checked="cacheSel.isAllSelected"
              :indeterminate="cacheSel.selectedCount > 0 && !cacheSel.isAllSelected"
              aria-label="全选当前筛选结果"
              @change="cacheSel.toggleAll()"
            />
            <span class="cl-select-all-label" @click="cacheSel.toggleAll()">全选</span>
          </div>
        </div>
      </div>

      <div v-if="cacheStore.filtered.length === 0" class="if-empty text-center py-12 text-grey">
        <v-icon size="40" class="mb-2 opacity-50">mdi-database-search-outline</v-icon>
        <div class="text-body-2 font-weight-medium">{{ cacheStore.items.length === 0 ? '还没有已解析角色' : '无匹配结果' }}</div>
        <div class="text-caption mt-1">首次解析（含 &lt;角色名&gt; 显式标记）成功后会自动写入这里的本地缓存，下次直接复用。</div>
      </div>

      <!-- ── M3E Dense List（R2 原型对比后选定：扫描效率高、无死白区） ── -->
      <div v-else class="cl-list">
        <div
          v-for="(row, i) in cacheStore.filtered"
          :key="row.id"
          :class="['cl-row', 'if-enter', { selected: cacheSel.isSelected(row.id) }]"
          :style="{ '--i': i }"
        >
          <div class="cl-row-leading">
            <m3e-checkbox
              :checked="cacheSel.isSelected(row.id)"
              :aria-label="`选择 ${row.name}`"
              @change="cacheSel.toggleOne(row.id)"
            />
            <span class="cl-avatar">{{ row.name.charAt(0) }}</span>
          </div>

          <div class="cl-row-main">
            <div class="cl-row-title">
              <span class="cl-name">{{ row.name }}</span>
              <m3e-chip :class="['cl-src-chip', srcClass(row.source)]">{{ sourceLabel(row.source) }}</m3e-chip>
            </div>
            <div class="cl-row-line2 mono">
              {{ row.canonical_tag }}<template v-if="row.series_tag"> · {{ row.series_tag }}</template>
            </div>
            <div v-if="row.caption_name || row.aliases" class="cl-row-line3">
              <span v-if="row.caption_name">Caption {{ row.caption_name }}</span>
              <span v-if="row.aliases">别名 {{ row.aliases }}</span>
            </div>
          </div>

          <div class="cl-row-trailing">
            <span v-if="row.resolved_at" class="cl-time" :title="`最近解析 ${formatTime(row.resolved_at)}`">
              {{ formatTimeShort(row.resolved_at) }}
            </span>
            <div class="cl-actions">
              <m3e-icon-button :id="`cl-edit-${row.id}`" size="small" @click="openCacheEdit(row)">
                <span class="mdi mdi-pencil-outline" />
              </m3e-icon-button>
              <m3e-tooltip :for="`cl-edit-${row.id}`" position="above">编辑元数据</m3e-tooltip>

              <m3e-icon-button
                :id="`cl-refresh-${row.id}`"
                size="small"
                :disabled="resolvingIds.has(row.id)"
                @click="reResolve(row)"
              >
                <m3e-loading-indicator v-if="resolvingIds.has(row.id)" class="cl-row-loading" />
                <span v-else class="mdi mdi-refresh" />
              </m3e-icon-button>
              <m3e-tooltip :for="`cl-refresh-${row.id}`" position="above">联网刷新</m3e-tooltip>

              <m3e-icon-button :id="`cl-more-${row.id}`" size="small">
                <m3e-menu-trigger :for="`cl-menu-${row.id}`">
                  <span class="mdi mdi-dots-vertical" />
                </m3e-menu-trigger>
              </m3e-icon-button>
              <m3e-tooltip :for="`cl-more-${row.id}`" position="above">更多操作</m3e-tooltip>
              <m3e-menu :id="`cl-menu-${row.id}`">
                <m3e-menu-item class="cl-menu-danger" @click="openBulkDelete('resolved', [row.id])">
                  <span slot="icon" class="mdi mdi-delete-outline" />
                  删除
                </m3e-menu-item>
              </m3e-menu>
            </div>
          </div>
        </div>
      </div>

    </template>

    <!-- ════════ 自定义角色（Character Book） ════════ -->
    <template v-else>
      <div class="cl-toolbar">
        <m3e-search-bar class="cl-search" clearable clear-label="清空搜索" @clear="characterStore.searchQuery = ''">
          <span slot="leading" class="mdi mdi-magnify" />
          <input slot="input" v-model="characterStore.searchQuery" placeholder="搜索角色名称、别名或特征" />
        </m3e-search-bar>
        <div class="cl-toolbar-right">
          <template v-if="customSel.selectedCount > 0">
            <span class="cl-sel-count">已选 {{ customSel.selectedCount }} 项</span>
            <m3e-button variant="tonal" class="cl-btn-danger" @click="openBulkDelete('custom')">
              <span slot="icon" class="mdi mdi-delete-outline" />
              删除所选
            </m3e-button>
          </template>
          <div class="cl-select-all">
            <m3e-checkbox
              :checked="customSel.isAllSelected"
              :indeterminate="customSel.selectedCount > 0 && !customSel.isAllSelected"
              aria-label="全选当前筛选结果"
              @change="customSel.toggleAll()"
            />
            <span class="cl-select-all-label" @click="customSel.toggleAll()">全选</span>
          </div>
          <span class="cl-total">共 {{ filteredCharacters.length }} 个角色设定</span>
        </div>
      </div>

      <div v-if="filteredCharacters.length === 0" class="if-empty text-center py-12 text-grey">
        <v-icon size="40" class="mb-2 opacity-50">mdi-account-search-outline</v-icon>
        <div class="text-body-2 font-weight-medium">未找到角色设定</div>
        <div class="text-caption mt-1">点击右上角“新建角色”开始录入人物外貌与服装设定。</div>
      </div>

      <v-row v-else dense>
        <v-col
          v-for="(char, i) in filteredCharacters"
          :key="char.id"
          cols="12"
          sm="6"
          md="4"
          lg="3"
          class="if-enter"
          :style="{ '--i': i }"
        >
          <v-card variant="outlined" class="h-100 d-flex flex-column pa-3 bg-surface rounded-lg character-card">
            <div class="d-flex justify-space-between align-center mb-2 pb-2 border-b">
              <div class="d-flex align-center gap-2">
                <m3e-checkbox
                  :checked="customSel.isSelected(char.id)"
                  :aria-label="`选择 ${char.name}`"
                  @change="customSel.toggleOne(char.id)"
                />
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
                <m3e-icon-button
                  :id="`clu-fav-${char.id}`"
                  size="small"
                  :class="{ 'cl-fav-on': char.is_favorite }"
                  @click="characterStore.toggleFavorite(char)"
                >
                  <span class="mdi" :class="char.is_favorite ? 'mdi-star' : 'mdi-star-outline'" />
                </m3e-icon-button>
                <m3e-tooltip :for="`clu-fav-${char.id}`" position="above">收藏</m3e-tooltip>

                <m3e-icon-button :id="`clu-edit-${char.id}`" size="small" @click="openEditDialog(char)">
                  <span class="mdi mdi-pencil-outline" />
                </m3e-icon-button>
                <m3e-tooltip :for="`clu-edit-${char.id}`" position="above">编辑</m3e-tooltip>

                <m3e-icon-button :id="`clu-more-${char.id}`" size="small">
                  <m3e-menu-trigger :for="`clu-menu-${char.id}`">
                    <span class="mdi mdi-dots-vertical" />
                  </m3e-menu-trigger>
                </m3e-icon-button>
                <m3e-tooltip :for="`clu-more-${char.id}`" position="above">更多操作</m3e-tooltip>
                <m3e-menu :id="`clu-menu-${char.id}`">
                  <m3e-menu-item class="cl-menu-danger" @click="openBulkDelete('custom', [char.id!])">
                    <span slot="icon" class="mdi mdi-delete-outline" />
                    删除
                  </m3e-menu-item>
                </m3e-menu>
              </div>
            </div>

            <div class="d-flex gap-1 mb-2">
              <m3e-chip v-if="char.gender">{{ char.gender }}</m3e-chip>
              <m3e-chip v-if="char.age_group">{{ char.age_group }}</m3e-chip>
              <m3e-chip v-if="char.body">{{ char.body }}</m3e-chip>
            </div>

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

            <div class="pt-2 border-t text-caption text-grey text-truncate">
              {{ char.extra_description || '暂无补充描述' }}
            </div>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <!-- ════════ 自定义角色：新建 / 编辑（m3e-dialog 承载复杂表单） ════════ -->
    <m3e-dialog :open="dialog" class="cl-dialog cl-dialog-lg" @closed="dialog = false">
      <span slot="header">{{ isEdit ? '编辑角色设定' : '新建角色设定' }}</span>
      <!-- v-if 延迟挂载：Vuetify field 在隐藏容器里测量不到 label 宽度，notch 会破 -->
      <div v-if="dialog" class="cl-dialog-body">
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
      </div>
      <div slot="actions" class="cl-dialog-actions">
        <m3e-button variant="text" @click="dialog = false">取消</m3e-button>
        <m3e-button variant="filled" :disabled="!form.name.trim()" @click="saveChar">保存设定</m3e-button>
      </div>
    </m3e-dialog>

    <!-- ════════ 已解析角色：编辑 metadata ════════ -->
    <m3e-dialog :open="cacheDialog" class="cl-dialog" @closed="cacheDialog = false">
      <span slot="header">编辑角色元数据 — {{ cacheForm.name }}</span>
      <div v-if="cacheDialog" class="cl-dialog-body">
        <div class="d-flex flex-column gap-3">
          <v-text-field v-model="cacheForm.canonical_tag" label="角色 Tag（canonical）" density="compact" variant="outlined" />
          <v-text-field v-model="cacheForm.series_tag" label="作品 Tag（series）" density="compact" variant="outlined" />
          <v-text-field v-model="cacheForm.caption_name" label="Caption Name" density="compact" variant="outlined" />
          <v-textarea v-model="cacheForm.aliases" label="别名（逗号分隔）" density="compact" variant="outlined" rows="2" hide-details />
          <div class="text-caption text-grey">保存后来源记为「手动」：自动联网只补空字段，不会覆盖这里的值。</div>
        </div>
      </div>
      <div slot="actions" class="cl-dialog-actions">
        <m3e-button variant="text" @click="cacheDialog = false">取消</m3e-button>
        <m3e-button variant="tonal" :disabled="cacheResolving" @click="reResolveForce()">
          <m3e-loading-indicator v-if="cacheResolving" slot="icon" class="cl-row-loading" />
          <span v-else slot="icon" class="mdi mdi-refresh" />
          {{ cacheResolving ? '解析中…' : '重新解析并替换' }}
        </m3e-button>
        <m3e-button variant="filled" @click="saveCacheEdit">保存</m3e-button>
      </div>
    </m3e-dialog>

    <!-- ════════ 多候选选择 ════════ -->
    <m3e-dialog :open="ambDialog" class="cl-dialog" @closed="ambDialog = false">
      <span slot="header">找到多个候选 — {{ ambName }}</span>
      <div class="cl-dialog-body">
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
      </div>
      <div slot="actions" class="cl-dialog-actions">
        <m3e-button variant="text" @click="ambDialog = false">取消</m3e-button>
      </div>
    </m3e-dialog>

    <!-- ════════ 删除确认 ════════ -->
    <m3e-dialog :open="delDialog" alert class="cl-dialog cl-dialog-sm" @closed="delDialog = false">
      <span slot="header">{{ delIds.length === 1 ? '删除此角色？' : `删除所选 ${delIds.length} 项？` }}</span>
      <div class="cl-dialog-body">
        <p class="text-body-2 text-grey mb-0" style="margin-top: 0">{{ delSemantics }}</p>
      </div>
      <div slot="actions" class="cl-dialog-actions">
        <m3e-button variant="text" @click="delDialog = false">取消</m3e-button>
        <m3e-button variant="filled" class="cl-btn-danger-filled" :disabled="delLoading" @click="confirmBulkDelete">
          {{ delLoading ? '删除中…' : '删除' }}
        </m3e-button>
      </div>
    </m3e-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { M3eSnackbar } from '@m3e/web/snackbar'
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
  cacheStore.fetchCache()
})

/** m3e-tabs change：selectedIndex 为权威来源；click 兜底保证无 panel 时也能切换 */
function onTabsChange(e: Event) {
  const idx = (e.target as unknown as { selectedIndex?: number }).selectedIndex
  if (idx === 0 || idx === 1) tab.value = idx === 0 ? 'resolved' : 'custom'
}

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
  M3eSnackbar.open(isEdit.value ? '角色设定已更新' : '角色设定已创建')
}

/* ════ 已解析角色（Trigger Cache）tab ════ */
const cacheSel = useBulkSelection(() => cacheStore.filtered as ResolvedCharacter[])
const customSel = useBulkSelection(() => filteredCharacters.value as Character[])

const cacheDialog = ref(false)
const cacheForm = reactive<{ id: number | null; name: string; canonical_tag: string; series_tag: string; caption_name: string; aliases: string }>({
  id: null, name: '', canonical_tag: '', series_tag: '', caption_name: '', aliases: '',
})
const cacheResolving = ref(false)
/* 逐行联网解析状态：行内 refresh 按钮切换为 m3e-loading-indicator */
const resolvingIds = ref<Set<number>>(new Set())

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

function sourceLabel(src: string): string {
  if (src === 'manual') return '手动'
  if (src === 'online') return '在线'
  if (src === 'llm') return 'LLM'
  return '本地'
}

/** source chip 语义色：online = secondary tonal（角色页身份色），其余 neutral */
function srcClass(src: string): string {
  return src === 'online' ? 'online' : 'neutral'
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

/** 行尾时间：紧凑「月/日 时:分」，完整时间在 tooltip */
function formatTimeShort(iso: string | null): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })
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
  M3eSnackbar.open('角色元数据已更新')
}

/** 重新解析（默认不覆盖 manual 非空值）。唯一结果直接更新；多候选弹选择。 */
async function reResolve(row: ResolvedCharacter, force = false) {
  ambForce = force
  if (row.id != null) {
    resolvingIds.value.add(row.id)
  }
  try {
    const d = await cacheStore.reResolve(row.name, force)
    if (d.status === 'resolved') {
      await cacheStore.fetchCache()
      M3eSnackbar.open(`「${row.name}」元数据已刷新`)
    } else if (d.status === 'ambiguous') {
      ambName.value = row.name
      ambCands.value = d.candidates || []
      ambTargetId = row.id
      ambDialog.value = true
    } else {
      M3eSnackbar.open(`未找到可靠结果（${d.status}）`)
    }
  } catch (e: any) {
    console.error('re-resolve failed', e)
    M3eSnackbar.open('联网解析失败，请检查网络或数据源设置')
  } finally {
    if (row.id != null) {
      resolvingIds.value.delete(row.id)
    }
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
    M3eSnackbar.open(`「${ambName.value}」元数据已刷新`)
  } catch (e) {
    console.error('confirm failed', e)
    M3eSnackbar.open('候选确认失败')
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
      if (failed.length) {
        M3eSnackbar.open(`删除失败 ${failed.length} 项`)
      } else {
        M3eSnackbar.open(`已删除 ${delIds.value.length} 项`)
      }
    } else {
      const failed: Array<number | string> = []
      for (const id of delIds.value) {
        try { await characterStore.deleteCharacter(Number(id)) } catch { failed.push(id) }
      }
      customSel.clear()
      if (failed.length) {
        M3eSnackbar.open(`删除失败 ${failed.length} 项`)
      } else {
        M3eSnackbar.open(`已删除 ${delIds.value.length} 项`)
      }
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

/* ════ Header ════ */
.cl-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

/* ════ Tabs ════ */
.cl-tabs {
  margin-bottom: 16px;
  --m3e-tabs-divider-color: rgb(var(--v-theme-outline-variant));
}

/* ════ Toolbar（tonal panel，无描边） ════ */
.cl-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 12px;
  margin-bottom: 16px;
  background: rgb(var(--v-theme-surface-container));
  border-radius: var(--if-radius-container, 24px);
}
.cl-search {
  flex: 0 1 420px;
  min-width: 240px;
  --m3e-search-bar-container-height: 44px;
  --m3e-search-bar-container-color: rgb(var(--v-theme-surface));
}
.cl-toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}
.cl-sel-count {
  font-size: 0.8125rem;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
}
.cl-select-all {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.cl-select-all-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  user-select: none;
}
.cl-total {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-on-surface-variant));
}
.cl-btn-danger {
  --m3e-tonal-button-container-color: rgba(var(--v-theme-error), 0.14);
  --m3e-tonal-button-label-text-color: rgb(var(--v-theme-error));
}
.cl-btn-danger-filled {
  --m3e-filled-button-container-color: rgb(var(--v-theme-error));
  --m3e-filled-button-label-text-color: rgb(var(--v-theme-on-error));
}

/* ════ 方案 A：M3E Dense List ════
   单一 tonal 容器承载全部行；行高 ≥68px；selected = secondary-container（不是描边）。 */
.cl-list {
  max-width: 960px;
  background: rgb(var(--v-theme-surface-container-low));
  border-radius: var(--if-radius-card, 20px);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cl-row {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 68px;
  padding: 8px 10px 8px 12px;
  border-radius: 14px;
  transition: background-color var(--if-motion-fast-effects), border-radius var(--if-motion-fast-spatial);
}
.cl-row:hover {
  background: rgb(var(--v-theme-surface-container));
}
.cl-row.selected {
  background: rgb(var(--v-theme-secondary-container));
  border-radius: 16px;
}
.cl-row-leading {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.cl-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
  font-size: 0.875rem;
  font-weight: 650;
  flex-shrink: 0;
}
.cl-row.selected .cl-avatar {
  background: rgb(var(--v-theme-surface));
}
.cl-row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cl-row-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.cl-name {
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: 0.005em;
  color: rgb(var(--v-theme-on-surface));
}
.cl-row-line2 {
  font-size: 0.75rem;
  color: rgb(var(--v-theme-on-surface-variant));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cl-row-line3 {
  display: flex;
  gap: 12px;
  font-size: 0.6875rem;
  color: rgb(var(--v-theme-outline));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cl-row-trailing {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.cl-time {
  font-size: 0.6875rem;
  color: rgb(var(--v-theme-outline));
  white-space: nowrap;
}
.cl-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}
.cl-actions .mdi {
  font-size: 20px;
}
.cl-row-loading {
  --m3e-loading-indicator-container-size: 22px;
  --m3e-loading-indicator-active-indicator-size: 18px;
}

/* source chip：轻量语义色，不污染整行 */
.cl-src-chip {
  --m3e-chip-container-height: 22px;
  --m3e-chip-label-text-font-size: 0.6875rem;
  --m3e-chip-label-text-font-weight: 600;
}
.cl-src-chip.neutral {
  --m3e-chip-container-color: rgb(var(--v-theme-surface-container-highest));
  --m3e-chip-label-text-color: rgb(var(--v-theme-on-surface-variant));
}
.cl-src-chip.online {
  --m3e-chip-container-color: rgb(var(--v-theme-secondary-container));
  --m3e-chip-label-text-color: rgb(var(--v-theme-on-secondary-container));
}
.cl-row.selected .cl-src-chip.online {
  --m3e-chip-container-color: rgb(var(--v-theme-surface));
}

/* overflow menu 的 danger 项 */
.cl-menu-danger {
  --m3e-menu-item-color: rgb(var(--v-theme-error));
  --m3e-menu-item-icon-color: rgb(var(--v-theme-error));
}

/* ════ 自定义角色卡（沿用 grid，已换 M3E primitives） ════ */
.character-card {
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.character-card:hover {
  border-color: rgb(var(--v-theme-primary)) !important;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
}
.cl-fav-on .mdi {
  color: rgb(var(--v-theme-warning, 245 158 11));
}

/* ════ Dialogs ════ */
.cl-dialog {
  --m3e-dialog-min-width: 420px;
  --m3e-dialog-max-width: 560px;
}
.cl-dialog-lg {
  --m3e-dialog-max-width: 720px;
}
.cl-dialog-sm {
  --m3e-dialog-min-width: 360px;
  --m3e-dialog-max-width: 440px;
}
.cl-dialog-body {
  max-height: 68vh;
  overflow-y: auto;
  padding-top: 4px;
}
.cl-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* 多候选行 */
.amb-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: var(--if-radius-field, 16px);
  background: rgb(var(--v-theme-surface-container));
  font-size: 13px;
  cursor: pointer;
  transition: background-color var(--if-motion-fast-effects);
}
.amb-row:hover { background: rgb(var(--v-theme-surface-container-high)); }
.amb-cap { margin-left: auto; color: rgb(var(--v-theme-on-surface-variant)); }
</style>
