import { ref, computed, watch, reactive } from 'vue'

/**
 * 资源列表通用多选/全选/批量删除状态。
 * - 「全选」= 当前可见（过滤后）集合
 * - 过滤变化后自动剪枝到可见集合，避免 ghost selection
 * - 不持久化
 */
export interface BulkSel {
  id?: number | string
}

export function useBulkSelection<T extends BulkSel>(getVisible: () => T[]) {
  const selected = ref<Array<number | string>>([])
  const visibleIds = computed(() =>
    getVisible().map(x => x.id).filter(v => v !== undefined && v !== null) as Array<number | string>
  )

  const isAllSelected = computed(() =>
    visibleIds.value.length > 0 && visibleIds.value.every(id => selected.value.includes(id))
  )
  const selectedCount = computed(() => selected.value.length)

  function toggleAll() {
    selected.value = isAllSelected.value ? [] : [...visibleIds.value]
  }
  function toggleOne(id: number | string | undefined | null) {
    if (id === undefined || id === null) return
    const idx = selected.value.indexOf(id)
    if (idx >= 0) selected.value.splice(idx, 1)
    else selected.value.push(id)
  }
  function isSelected(id: number | string | undefined | null): boolean {
    return id !== undefined && id !== null && selected.value.includes(id)
  }
  function clear() {
    selected.value = []
  }

  // 过滤/可见集合变化 → 剪枝，避免 ghost selection
  watch(visibleIds, (ids) => {
    const keep = new Set(ids)
    selected.value = selected.value.filter(id => keep.has(id))
  })

  return reactive({
    selected, isAllSelected, selectedCount,
    toggleAll, toggleOne, isSelected, clear,
  })
}
