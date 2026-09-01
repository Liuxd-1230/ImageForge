<template>
  <div class="lib-root">
    <!-- ── Header ── -->
    <div class="lib-head">
      <div>
        <h1 class="lib-title">LoRA 资源库</h1>
        <p class="lib-sub">管理本地权重、来源目录与触发词映射。</p>
      </div>
      <div class="lib-actions">
        <button type="button" class="btn-tonal" @click="openSourceDialog">
          <span class="mdi mdi-folder-search-outline" />扫描来源
        </button>
        <button type="button" class="btn-primary" @click="openCreateDialog">
          <span class="mdi mdi-plus" />添加 LoRA
        </button>
      </div>
    </div>

    <!-- ── M3 Expressive Filter Bar（外层 24 圆角 tonal 面，内嵌 16 圆角搜索） ── -->
    <div class="filter-bar">
      <div class="search-field">
        <span class="mdi mdi-magnify search-icon" />
        <input
          v-model="searchQuery"
          class="search-input"
          placeholder="搜索 LoRA 名称、文件名或触发词"
        />
        <button v-if="searchQuery" type="button" class="search-clear" @click="searchQuery = ''">
          <span class="mdi mdi-close" />
        </button>
      </div>
      <div class="filter-side">
        <button
          type="button"
          :class="['fav-btn', { on: onlyFavorites }]"
          @click="onlyFavorites = !onlyFavorites"
        >
          <span class="mdi" :class="onlyFavorites ? 'mdi-star' : 'mdi-star-outline'" />
          仅看收藏
        </button>
        <span class="count-mono mono">{{ filteredLoras.length }} 个模型</span>
      </div>
    </div>

    <!-- ── Empty ── -->
    <div v-if="filteredLoras.length === 0" class="lib-empty">
      <div class="lib-empty-icon"><span class="mdi mdi-toy-brick-outline" /></div>
      <p>暂无 LoRA 记录</p>
      <p class="lib-empty-hint">点击「扫描来源」添加本地目录并选择导入，或手动添加。</p>
    </div>

    <!-- ── List ── -->
    <div v-else class="lora-list">
      <div class="lora-head">
        <span class="cell col-fav">收藏</span>
        <span class="cell col-name">名称 / 分类</span>
        <span class="cell col-file">文件名</span>
        <span class="cell col-trigger">触发词</span>
        <span class="cell col-weight">权重</span>
        <span class="cell col-status">状态</span>
        <span class="cell col-ops">操作</span>
      </div>
      <div v-for="lora in filteredLoras" :key="lora.id" class="lora-row">
        <div class="cell col-fav">
          <button
            type="button"
            :class="['fav-star', { on: lora.is_favorite }]"
            :title="lora.is_favorite ? '取消收藏' : '收藏'"
            @click="loraStore.toggleFavorite(lora)"
          >
            <span class="mdi" :class="lora.is_favorite ? 'mdi-star' : 'mdi-star-outline'" />
          </button>
        </div>
        <div class="cell col-name">
          <div class="name-line">
            <span class="lora-name" :title="lora.name">{{ lora.name }}</span>
            <span class="cat-pill">{{ lora.category || '通用' }}</span>
          </div>
        </div>
        <div class="cell col-file">
          <span class="mono ellipsis file-name" :title="lora.filename">{{ lora.filename }}</span>
          <span v-if="lora.source_path" class="mono src-path ellipsis" :title="lora.source_path">{{ lora.source_path }}</span>
        </div>
        <div class="cell col-trigger">
          <span v-if="lora.trigger_words" class="mono ellipsis trigger" :title="lora.trigger_words">{{ lora.trigger_words }}</span>
          <span v-else class="none-hint">无触发词</span>
        </div>
        <div class="cell col-weight">
          <span class="mono weight">{{ lora.default_strength.toFixed(2) }}</span>
        </div>
        <div class="cell col-status">
          <span :class="['status-badge', lora.is_valid_file ? 'ok' : 'bad']">
            <span class="dot" />
            {{ lora.is_valid_file ? '就绪' : '未识别' }}
          </span>
        </div>
        <div class="cell col-ops">
          <button type="button" class="op-btn" title="编辑" @click="openEditDialog(lora)">
            <span class="mdi mdi-pencil-outline" />
          </button>
          <button type="button" class="op-btn danger" title="删除" @click="askDeleteLora(lora)">
            <span class="mdi mdi-delete-outline" />
          </button>
        </div>
      </div>
    </div>

    <!-- ══════════ 来源管理 Dialog ══════════ -->
    <v-dialog v-model="sourceDialog" max-width="640px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">LoRA 来源管理</span>
          <button type="button" class="dialog-close" @click="sourceDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <p class="dialog-hint">扫描不会直接修改 LoRA 库；勾选预览后再「导入所选」。</p>

        <!-- 添加来源 -->
        <div class="add-source">
          <input
            v-model="newSourcePath"
            class="path-input mono"
            placeholder="目录路径，如 D:\ComfyUI\models\loras\Anima"
            @input="resolvePreview"
            @keyup.enter="addSource"
          />
          <label class="rec-check">
            <input v-model="newSourceRecursive" type="checkbox" />
            <span class="rec-box"><span v-if="newSourceRecursive" class="mdi mdi-check" /></span>
            递归子目录
          </label>
          <button type="button" class="btn-primary sm" :disabled="!newSourcePath.trim() || addingSource" @click="addSource">
            {{ addingSource ? '添加中…' : '添加来源' }}
          </button>
        </div>
        <p v-if="sourceError" class="form-error">{{ sourceError }}</p>
        <p v-if="newSourceResolved" class="path-preview">
          <span class="pv-label">实际解析路径</span>
          <span class="mono pv-path">{{ newSourceResolved }}</span>
        </p>

        <!-- 来源列表 -->
        <div class="source-list">
          <div v-for="s in loraStore.sources" :key="s.id" class="source-row">
            <span :class="['dot', s.exists && s.readable ? 'ok' : 'bad']" />
            <div class="source-main">
              <span class="mono src-display ellipsis" :title="s.display_path">{{ s.display_path }}</span>
              <span v-if="s.resolved_path !== s.display_path" class="mono src-resolved ellipsis" :title="s.resolved_path">{{ s.resolved_path }}</span>
              <span v-else-if="!s.exists" class="src-invalid">{{ s.error || '路径不可访问' }}</span>
            </div>
            <div class="source-ops">
              <button
                type="button"
                :class="['mini-switch', { on: s.enabled }]"
                :title="s.enabled ? '停用' : '启用'"
                @click="loraStore.updateSource(s.id, { enabled: !s.enabled })"
              >
                <span class="knob" />
              </button>
              <button
                type="button"
                :class="['mini-chip', { on: s.recursive }]"
                title="递归子目录"
                @click="loraStore.updateSource(s.id, { recursive: !s.recursive })"
              >
                递归
              </button>
              <button type="button" class="op-btn" title="扫描" :disabled="!s.enabled" @click="runScan(s)">
                <span class="mdi mdi-scan-helper" />
              </button>
              <button type="button" class="op-btn danger" title="删除来源（不影响已导入 LoRA）" @click="askDeleteSource(s)">
                <span class="mdi mdi-delete-outline" />
              </button>
            </div>
          </div>
          <div v-if="loraStore.sources.length === 0" class="src-empty">还没有来源目录</div>
        </div>

        <div class="dialog-foot">
          <button type="button" class="btn-tonal" @click="sourceDialog = false">关闭</button>
        </div>
      </div>
    </v-dialog>

    <!-- ══════════ 扫描预览 Dialog ══════════ -->
    <v-dialog v-model="scanDialog" max-width="860px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">扫描预览 · 选择导入</span>
          <button type="button" class="dialog-close" @click="scanDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <div v-if="scanResult" class="scan-body">
          <div class="scan-summary">
            <span class="sum-item"><b>{{ scanResult.summary.total }}</b>发现</span>
            <span class="sum-item primary"><b>{{ scanResult.summary.new }}</b>新增</span>
            <span class="sum-item muted"><b>{{ scanResult.summary.already_imported }}</b>已存在</span>
            <span :class="['sum-item', scanResult.summary.comfy_unrecognized > 0 ? 'warn' : 'muted']">
              <b>{{ scanResult.summary.comfy_unrecognized }}</b>ComfyUI 未识别
            </span>
            <span :class="['sum-item', scanResult.summary.basename_conflicts > 0 ? 'err' : 'muted']">
              <b>{{ scanResult.summary.basename_conflicts }}</b>重名冲突
            </span>
            <span v-if="!scanResult.summary.comfy_available" class="sum-item warn">ComfyUI 离线</span>
          </div>

          <div class="scan-toolbar">
            <button type="button" class="btn-tonal sm" @click="selectAllNew">全选新增</button>
            <button type="button" class="btn-ghost sm" @click="clearSelection">取消全选</button>
            <span class="scan-path mono ellipsis">{{ scanResult.source.display_path }}</span>
          </div>

          <div class="cand-list">
            <div class="cand-head">
              <span class="cell c-check" />
              <span class="cell c-name">文件</span>
              <span class="cell c-flag">状态</span>
            </div>
            <div
              v-for="c in scanResult.candidates"
              :key="c.full_path"
              :class="['cand-row', { disabled: c.exists_in_db }]"
            >
              <span class="cell c-check">
                <button
                  type="button"
                  :class="['row-check', { on: isSelected(c) }]"
                  :disabled="c.exists_in_db"
                  @click="toggleCandidate(c)"
                >
                  <span v-if="isSelected(c)" class="mdi mdi-check" />
                </button>
              </span>
              <span class="cell c-name">
                <span class="cand-name ellipsis">{{ c.name_hint }}</span>
                <span class="mono cand-path ellipsis" :title="c.relative_path">{{ c.relative_path }}</span>
              </span>
              <span class="cell c-flag">
                <span v-if="c.exists_in_db" class="flag done">已导入</span>
                <template v-else>
                  <span v-if="c.basename_conflict" class="flag err" title="多来源存在同名文件，导入后仍以完整相对路径区分">重名</span>
                  <span v-if="!c.comfy_recognized" class="flag warn" title="文件存在 · ComfyUI 未识别">文件存在 · ComfyUI 未识别</span>
                  <span v-if="c.comfy_recognized && !c.basename_conflict" class="flag ok">可导入</span>
                </template>
              </span>
            </div>
            <div v-if="scanResult.candidates.length === 0" class="src-empty">该目录下未发现 LoRA 权重文件</div>
          </div>
        </div>

        <div class="dialog-foot">
          <span class="foot-hint">已选 {{ selectedCandidates.length }} 项</span>
          <button type="button" class="btn-tonal" @click="scanDialog = false">取消</button>
          <button
            type="button"
            class="btn-primary"
            :disabled="selectedCandidates.length === 0 || importing"
            @click="doImport"
          >
            {{ importing ? '导入中…' : `导入所选（${selectedCandidates.length}）` }}
          </button>
        </div>
      </div>
    </v-dialog>

    <!-- ══════════ LoRA 创建/编辑 Dialog ══════════ -->
    <v-dialog v-model="loraDialog" max-width="520px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">{{ isEdit ? '编辑 LoRA 设定' : '添加 LoRA' }}</span>
          <button type="button" class="dialog-close" @click="loraDialog = false">
            <span class="mdi mdi-close" />
          </button>
        </div>
        <div class="form-body">
          <label class="field">
            <span class="field-label">显示名称</span>
            <input v-model="form.name" class="field-input" placeholder="如: Water Dress" />
          </label>
          <label class="field">
            <span class="field-label">文件名（ComfyUI LoRA 文件）</span>
            <input v-model="form.filename" class="field-input mono" :readonly="isEdit" placeholder="如: water_dress.safetensors" />
          </label>
          <label class="field">
            <span class="field-label">触发词 Trigger Words（英文逗号分隔）</span>
            <textarea v-model="form.trigger_words" class="field-input" rows="2" placeholder="如: water_dress, flowing_water" />
          </label>
          <label class="field">
            <span class="field-label">分类</span>
            <input v-model="form.category" class="field-input" />
          </label>
          <div class="strength-field">
            <span class="field-label">默认权重 <b class="mono">{{ form.default_strength.toFixed(2) }}</b></span>
            <div class="mini-slider" @pointerdown="onStrengthDown">
              <div class="ms-track">
                <div class="ms-fill" :style="{ width: strengthPct + '%' }" />
                <div class="ms-thumb" :style="{ left: strengthPct + '%' }" />
              </div>
            </div>
          </div>
        </div>
        <div class="dialog-foot">
          <button type="button" class="btn-tonal" @click="loraDialog = false">取消</button>
          <button type="button" class="btn-primary" :disabled="!form.name || !form.filename" @click="saveLora">
            保存
          </button>
        </div>
      </div>
    </v-dialog>

    <!-- ══════════ 删除确认 Dialog ══════════ -->
    <v-dialog v-model="confirmDialog" max-width="420px">
      <div class="m3-dialog">
        <div class="dialog-head">
          <span class="dialog-title">{{ confirmTitle }}</span>
        </div>
        <p class="confirm-text">{{ confirmText }}</p>
        <div class="dialog-foot">
          <button type="button" class="btn-tonal" @click="confirmDialog = false">取消</button>
          <button type="button" class="btn-danger" @click="confirmAction">删除</button>
        </div>
      </div>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="2600" :color="snackbarColor">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useLoraStore } from '../stores/lora'
import { useStudioStore } from '../stores/studio'
import type { Lora, LoraSource, ScanCandidate } from '../types'

const loraStore = useLoraStore()
const studioStore = useStudioStore()

const searchQuery = ref('')
const onlyFavorites = ref(false)

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

/* ── 来源管理 ── */
const sourceDialog = ref(false)
const newSourcePath = ref('')
const newSourceRecursive = ref(true)
const addingSource = ref(false)
const sourceError = ref('')
const newSourceResolved = ref('')

/* ── 扫描预览 ── */
const scanDialog = ref(false)
const scanResult = ref<null | { source: LoraSource; candidates: ScanCandidate[]; summary: any }>(null)
const selectedPaths = ref<Set<string>>(new Set())
const importing = ref(false)

/* ── LoRA 编辑 ── */
const loraDialog = ref(false)
const isEdit = ref(false)
const form = ref({
  id: undefined as number | undefined,
  name: '',
  filename: '',
  trigger_words: '',
  default_strength: 0.8,
  is_favorite: false,
  category: '通用',
  is_custom: true,
  is_valid_file: true,
})

/* ── 删除确认 ── */
const confirmDialog = ref(false)
const confirmTitle = ref('')
const confirmText = ref('')
let confirmAction: () => void = () => {}

const filteredLoras = computed(() => {
  return loraStore.loras.filter(l => {
    const matchFav = !onlyFavorites.value || l.is_favorite
    const q = searchQuery.value.toLowerCase()
    const matchQuery = !q ||
      l.name.toLowerCase().includes(q) ||
      l.filename.toLowerCase().includes(q) ||
      (l.trigger_words && l.trigger_words.toLowerCase().includes(q))
    return matchFav && matchQuery
  })
})

const strengthPct = computed(() => ((form.value.default_strength - 0.1) / 1.4) * 100)

const selectedCandidates = computed(() =>
  scanResult.value ? scanResult.value.candidates.filter(c => selectedPaths.value.has(c.full_path)) : [],
)

onMounted(() => {
  loraStore.fetchLoras()
  loraStore.fetchSources()
})

function notify(text: string, color = 'success') {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

/* ── 来源管理 ── */
async function openSourceDialog() {
  sourceError.value = ''
  await loraStore.fetchSources()
  sourceDialog.value = true
}

function resolvePreview() {
  if (!newSourcePath.value.trim()) { newSourceResolved.value = ''; return }
  // 前端只做展示性转译；权威解析在后端（WSL 检测以后端环境为准）
  const p = newSourcePath.value.trim().replace(/\\/g, '/')
  const m = p.match(/^([A-Za-z]):\/(.*)$/)
  newSourceResolved.value = m ? `/mnt/${m[1].toLowerCase()}/${m[2]}` : p
}

async function addSource() {
  sourceError.value = ''
  const p = newSourcePath.value.trim()
  if (!p) return
  addingSource.value = true
  try {
    await loraStore.addSource(p, newSourceRecursive.value)
    newSourcePath.value = ''
    newSourceResolved.value = ''
    notify('来源已添加')
  } catch (err: any) {
    sourceError.value = err.response?.data?.detail || err.message || '添加来源失败'
  } finally {
    addingSource.value = false
  }
}

async function runScan(s: LoraSource) {
  try {
    const result = await loraStore.scanSource(s.id)
    if (result) {
      scanResult.value = result
      selectedPaths.value = new Set(
        result.candidates.filter(c => !c.exists_in_db).map(c => c.full_path),
      )
      scanDialog.value = true
    }
  } catch (err: any) {
    notify(err.response?.data?.detail || err.message || '扫描失败', 'error')
  }
}

function askDeleteSource(s: LoraSource) {
  confirmTitle.value = '删除来源'
  confirmText.value = `删除来源「${s.display_path}」不会删除已导入的 LoRA 库记录。确定删除该来源吗？`
  confirmAction = async () => {
    await loraStore.deleteSource(s.id)
    notify('来源已删除，LoRA 库记录保留')
    confirmDialog.value = false
  }
  confirmDialog.value = true
}

/* ── 扫描预览选择 ── */
function isSelected(c: ScanCandidate) {
  return selectedPaths.value.has(c.full_path)
}
function toggleCandidate(c: ScanCandidate) {
  if (c.exists_in_db) return
  const s = new Set(selectedPaths.value)
  if (s.has(c.full_path)) s.delete(c.full_path)
  else s.add(c.full_path)
  selectedPaths.value = s
}
function selectAllNew() {
  if (!scanResult.value) return
  selectedPaths.value = new Set(
    scanResult.value.candidates.filter(c => !c.exists_in_db).map(c => c.full_path),
  )
}
function clearSelection() {
  selectedPaths.value = new Set()
}
async function doImport() {
  if (selectedCandidates.value.length === 0) return
  importing.value = true
  try {
    const res = await loraStore.importCandidates(selectedCandidates.value)
    studioStore.syncLorasFromLibrary(loraStore.loras)
    notify(`已导入 ${res.imported.length} 项，跳过 ${res.skipped.length} 项`)
    scanDialog.value = false
  } catch (err: any) {
    notify(err.response?.data?.detail || err.message || '导入失败', 'error')
  } finally {
    importing.value = false
  }
}

/* ── LoRA 编辑 ── */
function openCreateDialog() {
  isEdit.value = false
  form.value = {
    id: undefined, name: '', filename: '', trigger_words: '',
    default_strength: 0.8, is_favorite: false, category: '通用', is_custom: true, is_valid_file: true,
  }
  loraDialog.value = true
}
function openEditDialog(lora: Lora) {
  isEdit.value = true
  form.value = { is_custom: true, ...lora }
  loraDialog.value = true
}
async function saveLora() {
  await loraStore.saveLora(form.value)
  studioStore.syncLorasFromLibrary(loraStore.loras)
  await studioStore.buildPrompt()
  loraDialog.value = false
  notify('LoRA 配置已保存并同步至创作台')
}
function askDeleteLora(lora: Lora) {
  confirmTitle.value = '删除 LoRA 记录'
  confirmText.value = `确定删除「${lora.name}」吗？该操作只删除库记录，不影响磁盘文件。`
  confirmAction = async () => {
    await loraStore.deleteLora(lora.id)
    studioStore.syncLorasFromLibrary(loraStore.loras)
    confirmDialog.value = false
    notify('已删除')
  }
  confirmDialog.value = true
}

/* ── 默认权重 slider ── */
function onStrengthDown(e: PointerEvent) {
  if (e.button !== 0) return
  const track = e.currentTarget as HTMLElement
  const apply = (clientX: number) => {
    const rect = track.getBoundingClientRect()
    const p = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
    form.value.default_strength = Math.round((0.1 + p * 1.4) / 0.05) * 0.05
  }
  apply(e.clientX)
  const move = (ev: PointerEvent) => apply(ev.clientX)
  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}
</script>

<style scoped>
.lib-root {
  padding: 24px 28px 40px;
  color: rgb(var(--v-theme-on-surface));
}
.lib-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.lib-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.lib-sub {
  margin: 6px 0 0;
  font-size: 13.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.lib-actions {
  display: flex;
  gap: 10px;
}

/* ── 按钮 ── */
.btn-primary, .btn-tonal, .btn-ghost, .btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 0;
  border-radius: 999px;
  padding: 11px 20px;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized),
    opacity var(--motion-fast) var(--motion-emphasized);
}
.btn-primary {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}
.btn-primary:hover { background: rgb(var(--v-theme-primary-darken-1)); }
.btn-primary:disabled { opacity: 0.45; cursor: default; }
.btn-tonal {
  background: rgb(var(--v-theme-primary-container));
  color: rgb(var(--v-theme-on-primary-container));
}
.btn-tonal:hover { background: rgb(var(--v-theme-secondary-container)); }
.btn-ghost {
  background: transparent;
  color: rgb(var(--v-theme-primary));
}
.btn-danger {
  background: rgb(var(--v-theme-error-container));
  color: rgb(var(--v-theme-error));
}
.btn-primary.sm, .btn-tonal.sm, .btn-ghost.sm {
  padding: 8px 14px;
  font-size: 13px;
}

/* ── Filter Bar ── */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px;
  border-radius: 24px;
  background: rgb(var(--v-theme-surface-container));
  margin-bottom: 18px;
}
.search-field {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  border-radius: 16px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgb(var(--v-theme-outline-variant));
  transition: border-color var(--motion-fast) var(--motion-emphasized),
    box-shadow var(--motion-fast) var(--motion-emphasized);
}
.search-field:focus-within {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.12);
}
.search-icon {
  position: absolute;
  left: 14px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 18px;
  pointer-events: none;
}
.search-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  padding: 12px 38px 12px 42px;
  font-family: var(--font-sans);
  font-size: 14.5px;
  color: rgb(var(--v-theme-on-surface));
}
.search-clear {
  position: absolute;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
}
.filter-side {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.fav-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 16px;
  border: 0;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: var(--font-sans);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized),
    color var(--motion-fast) var(--motion-emphasized);
}
.fav-btn.on {
  background: rgb(var(--v-theme-secondary-container));
  color: rgb(var(--v-theme-on-secondary-container));
}
.count-mono {
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
  white-space: nowrap;
}

/* ── Empty ── */
.lib-empty {
  text-align: center;
  padding: 70px 0;
  color: rgb(var(--v-theme-on-surface-variant));
}
.lib-empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  margin: 0 auto 14px;
  border-radius: 20px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 30px;
}
.lib-empty p { margin: 0 0 4px; font-size: 14.5px; font-weight: 600; }
.lib-empty-hint { font-weight: 400 !important; font-size: 13px !important; }

/* ── List（CSS grid，minmax(0,…) 保证 ellipsis、不撑宽） ── */
.lora-list {
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 20px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
}
.lora-head, .lora-row {
  display: grid;
  grid-template-columns: 44px minmax(0, 1.25fr) minmax(0, 1.55fr) minmax(0, 1.3fr) 72px 96px 96px;
  align-items: center;
  min-width: 0;
}
.lora-head {
  padding: 12px 16px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgb(var(--v-theme-on-surface-variant));
}
.lora-row {
  padding: 12px 16px;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  min-width: 0;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.lora-row:hover { background: rgb(var(--v-theme-surface-container-low)); }
.cell { min-width: 0; }
.col-fav { text-align: center; }
.col-ops { text-align: right; display: flex; justify-content: flex-end; gap: 2px; }

.fav-star {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgb(var(--v-theme-outline));
  cursor: pointer;
  font-size: 16px;
}
.fav-star.on { color: rgb(var(--v-theme-warning)); }
.name-line { display: flex; align-items: center; gap: 8px; min-width: 0; }
.lora-name {
  font-size: 14px;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cat-pill {
  flex-shrink: 0;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 11.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
}
.file-name { display: block; font-size: 12.5px; color: rgb(var(--v-theme-on-surface-variant)); }
.src-path { display: block; font-size: 11.5px; color: rgb(var(--v-theme-text-muted)); margin-top: 2px; }
.trigger { font-size: 12.5px; color: rgb(var(--v-theme-primary)); }
.none-hint { font-size: 12.5px; color: rgb(var(--v-theme-text-muted)); font-style: italic; }
.weight { font-size: 13px; font-weight: 700; color: rgb(var(--v-theme-on-surface)); }
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.status-badge.ok { background: rgb(var(--v-theme-surface-container)); color: rgb(var(--v-theme-success)); }
.status-badge.bad { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }
.status-badge .dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.op-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  font-size: 15px;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.op-btn:hover { background: rgb(var(--v-theme-surface-container)); }
.op-btn.danger:hover { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }
.op-btn:disabled { opacity: 0.4; cursor: default; }

/* ── Dialog 公共 ── */
.m3-dialog {
  background: rgb(var(--v-theme-surface));
  border-radius: 24px;
  overflow: hidden;
}
.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 10px;
}
.dialog-title { font-size: 18px; font-weight: 700; letter-spacing: -0.01em; }
.dialog-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 18px;
  cursor: pointer;
}
.dialog-close:hover { background: rgb(var(--v-theme-surface-container)); }
.dialog-hint {
  margin: 0;
  padding: 0 24px 12px;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.dialog-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 24px 20px;
}
.foot-hint { margin-right: auto; font-size: 13px; color: rgb(var(--v-theme-on-surface-variant)); }

/* ── 来源管理 ── */
.add-source {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 24px;
}
.path-input {
  flex: 1;
  min-width: 0;
  padding: 12px 14px;
  border: 1px solid rgb(var(--v-theme-outline));
  border-radius: 14px;
  background: rgb(var(--v-theme-surface-container-low));
  font-size: 13.5px;
  color: rgb(var(--v-theme-on-surface));
}
.path-input:focus { outline: none; border-color: rgb(var(--v-theme-primary)); }
.rec-check {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  flex-shrink: 0;
}
.rec-check input { display: none; }
.rec-box {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  border: 2px solid rgb(var(--v-theme-outline));
  color: #fff;
  font-size: 12px;
}
.rec-check input:checked + .rec-box { background: rgb(var(--v-theme-primary)); border-color: rgb(var(--v-theme-primary)); }
.form-error {
  margin: 8px 24px 0;
  font-size: 12.5px;
  color: rgb(var(--v-theme-error));
}
.path-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 24px 0;
  font-size: 12.5px;
}
.pv-label { color: rgb(var(--v-theme-on-surface-variant)); flex-shrink: 0; }
.pv-path { color: rgb(var(--v-theme-primary)); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-list {
  max-height: 44vh;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 16px;
}
.source-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 14px;
  background: rgb(var(--v-theme-surface-container-low));
  min-width: 0;
}
.source-row .dot { flex-shrink: 0; width: 8px; height: 8px; border-radius: 50%; }
.dot.ok { background: rgb(var(--v-theme-success)); }
.dot.bad { background: rgb(var(--v-theme-error)); }
.source-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.src-display { font-size: 13px; color: rgb(var(--v-theme-on-surface)); }
.src-resolved { font-size: 12px; color: rgb(var(--v-theme-on-surface-variant)); }
.src-invalid { font-size: 12px; color: rgb(var(--v-theme-error)); }
.source-ops { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.mini-switch {
  position: relative;
  width: 36px;
  height: 22px;
  border: 0;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container-highest));
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--motion-emphasized);
}
.mini-switch.on { background: rgb(var(--v-theme-primary)); }
.mini-switch .knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform var(--motion-fast) var(--motion-spring);
}
.mini-switch.on .knob { transform: translateX(14px); }
.mini-chip {
  padding: 5px 10px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 999px;
  background: transparent;
  font-size: 11.5px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
}
.mini-chip.on { background: rgb(var(--v-theme-secondary-container)); border-color: transparent; color: rgb(var(--v-theme-on-secondary-container)); }
.src-empty {
  padding: 26px 0;
  text-align: center;
  font-size: 13px;
  color: rgb(var(--v-theme-on-surface-variant));
}

/* ── 扫描预览 ── */
.scan-body { padding: 0 24px; }
.scan-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.sum-item {
  padding: 7px 14px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 12.5px;
  color: rgb(var(--v-theme-on-surface-variant));
}
.sum-item b { margin-right: 6px; font-size: 14px; }
.sum-item.primary { background: rgb(var(--v-theme-primary-container)); color: rgb(var(--v-theme-on-primary-container)); }
.sum-item.warn { background: rgb(var(--v-theme-warning)); color: #fff; }
.sum-item.err { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }
.sum-item.muted { opacity: 0.75; }
.scan-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.scan-path { flex: 1; min-width: 0; font-size: 12px; color: rgb(var(--v-theme-on-surface-variant)); text-align: right; }
.cand-list {
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 16px;
  overflow: hidden;
  max-height: 46vh;
  overflow-y: auto;
}
.cand-head, .cand-row {
  display: grid;
  grid-template-columns: 44px minmax(0, 1.4fr) minmax(0, 1fr);
  align-items: center;
  min-width: 0;
}
.cand-head {
  padding: 10px 14px;
  background: rgb(var(--v-theme-surface-container));
  font-size: 11.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgb(var(--v-theme-on-surface-variant));
}
.cand-row {
  padding: 10px 14px;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
  min-width: 0;
}
.cand-row.disabled { opacity: 0.55; }
.row-check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  border: 2px solid rgb(var(--v-theme-outline));
  background: transparent;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.row-check.on { background: rgb(var(--v-theme-primary)); border-color: rgb(var(--v-theme-primary)); }
.row-check:disabled { cursor: default; }
.c-name { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.cand-name { font-size: 13.5px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cand-path { font-size: 11.5px; color: rgb(var(--v-theme-on-surface-variant)); }
.c-flag { display: flex; flex-wrap: wrap; gap: 4px; }
.flag {
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}
.flag.ok { background: rgb(var(--v-theme-primary-container)); color: rgb(var(--v-theme-on-primary-container)); }
.flag.done { background: rgb(var(--v-theme-surface-container)); color: rgb(var(--v-theme-on-surface-variant)); }
.flag.warn { background: rgb(var(--v-theme-warning)); color: #fff; }
.flag.err { background: rgb(var(--v-theme-error-container)); color: rgb(var(--v-theme-error)); }

/* ── LoRA 编辑表单 ── */
.form-body { padding: 4px 24px 0; display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: 12.5px; font-weight: 600; color: rgb(var(--v-theme-on-surface-variant)); }
.field-input {
  width: 100%;
  box-sizing: border-box;
  padding: 11px 13px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 12px;
  background: rgb(var(--v-theme-surface-container-low));
  font-family: var(--font-sans);
  font-size: 14px;
  color: rgb(var(--v-theme-on-surface));
}
.field-input:focus { outline: none; border-color: rgb(var(--v-theme-primary)); box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.12); }
.strength-field { padding-top: 4px; }
.mini-slider { margin-top: 10px; height: 20px; display: flex; align-items: center; cursor: pointer; }
.ms-track {
  position: relative;
  width: 100%;
  height: 5px;
  border-radius: 999px;
  background: rgb(var(--v-theme-surface-container-highest));
}
.ms-fill {
  position: absolute;
  left: 0; top: 0; height: 100%;
  border-radius: 999px;
  background: rgb(var(--v-theme-primary));
}
.ms-thumb {
  position: absolute;
  top: 50%;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  background: rgb(var(--v-theme-surface));
  border: 2.5px solid rgb(var(--v-theme-primary));
  pointer-events: none;
}

.confirm-text {
  margin: 0;
  padding: 0 24px;
  font-size: 14px;
  line-height: 1.6;
  color: rgb(var(--v-theme-on-surface-variant));
}
</style>
