<template>
  <v-app>
    <!-- Desktop Navigation Sidebar -->
    <v-navigation-drawer
      v-model="drawer"
      :rail="rail"
      permanent
      border="e"
      width="230"
      class="app-sidebar"
    >
      <div class="d-flex align-center justify-space-between px-3 py-3 app-brand-header">
        <div v-if="!rail" class="d-flex align-center gap-2">
          <v-icon icon="mdi-creation" color="primary" size="22" />
          <div class="d-flex flex-column">
            <span class="font-weight-bold text-body-2 tracking-tight">ImageForge</span>
            <span class="text-caption text-grey text-truncate" style="font-size: 0.68rem !important; line-height: 1;">Anima 工作台</span>
          </div>
        </div>
        <v-icon v-else icon="mdi-creation" color="primary" class="mx-auto" />
        
        <v-btn
          variant="text"
          density="compact"
          :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          size="small"
          @click.stop="rail = !rail"
        />
      </div>

      <v-divider class="my-1 opacity-20" />

      <v-list density="compact" nav class="px-2 py-1">
        <v-list-item
          prepend-icon="mdi-brush-variant"
          title="创作台"
          to="/"
          value="studio"
          rounded="md"
          class="mb-1"
        />
        <v-list-item
          prepend-icon="mdi-account-box-multiple-outline"
          title="角色书"
          to="/characters"
          value="characters"
          rounded="md"
          class="mb-1"
        />
        <v-list-item
          prepend-icon="mdi-palette-outline"
          title="画师库"
          to="/artists"
          value="artists"
          rounded="md"
          class="mb-1"
        />
        <v-list-item
          prepend-icon="mdi-toy-brick-outline"
          title="LoRA 库"
          to="/loras"
          value="loras"
          rounded="md"
          class="mb-1"
        />
        <v-list-item
          prepend-icon="mdi-file-code-outline"
          title="规则文件"
          to="/rules"
          value="rules"
          rounded="md"
          class="mb-1"
        />
        <v-list-item
          prepend-icon="mdi-tune-variant"
          title="提示词预设"
          to="/presets"
          value="presets"
          rounded="md"
          class="mb-1"
        />
        <v-list-item
          prepend-icon="mdi-history"
          title="生图历史"
          to="/history"
          value="history"
          rounded="md"
          class="mb-1"
        />
        <v-list-item
          prepend-icon="mdi-cog-outline"
          title="系统设置"
          to="/settings"
          value="settings"
          rounded="md"
          class="mb-1"
        />
      </v-list>

      <template #append>
        <div class="pa-2 border-t">
          <!-- 主题风格切换（三族：ImageForge 紫 / Gemini / Antigravity） -->
          <div v-if="!rail" class="theme-family-row">
            <button
              v-for="f in THEME_FAMILIES"
              :key="f.key"
              type="button"
              :class="['theme-swatch', { on: family === f.key }]"
              :title="f.label"
              @click="setFamily(f.key)"
            >
              <span class="swatch-dot" :style="{ background: f.swatch }" />
              <span class="swatch-label">{{ f.label }}</span>
            </button>
          </div>
          <div class="text-center">
            <v-btn
              variant="text"
              block
              density="compact"
              size="small"
              class="text-caption text-grey"
              @click="toggleTheme"
            >
              <v-icon size="16" class="mr-1">
                {{ isDark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}
              </v-icon>
              <span v-if="!rail">{{ isDark ? '浅色模式' : '深色模式' }}</span>
            </v-btn>
          </div>
        </div>
      </template>
    </v-navigation-drawer>

    <!-- Main Content Canvas -->
    <v-main class="bg-background">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTheme } from 'vuetify'

const drawer = ref(true)
const rail = ref(false)
const theme = useTheme()

/* ── 主题族：ImageForge 紫 / Gemini / Antigravity，各自带亮暗两套 ── */
type ThemeFamilyKey = 'imageforge' | 'gemini' | 'antigravity'
const THEME_FAMILIES: Array<{ key: ThemeFamilyKey; label: string; swatch: string; light: string; dark: string }> = [
  { key: 'imageforge', label: '紫', swatch: '#6750A4', light: 'light', dark: 'dark' },
  { key: 'gemini', label: 'Gemini', swatch: '#0B57D0', light: 'geminiLight', dark: 'geminiDark' },
  { key: 'antigravity', label: 'Mono', swatch: '#121317', light: 'antigravityLight', dark: 'antigravityDark' },
]
const FAMILY_KEY = 'if-theme-family'
const MODE_KEY = 'if-theme-mode'

const family = ref<ThemeFamilyKey>('imageforge')
const darkMode = ref(false)
const isDark = computed(() => darkMode.value)

function currentFamily() {
  return THEME_FAMILIES.find(f => f.key === family.value) ?? THEME_FAMILIES[0]
}
function applyTheme() {
  const f = currentFamily()
  theme.global.name.value = darkMode.value ? f.dark : f.light
}
function setFamily(key: ThemeFamilyKey) {
  family.value = key
  try { localStorage.setItem(FAMILY_KEY, key) } catch { /* ignore */ }
  applyTheme()
}
function toggleTheme() {
  darkMode.value = !darkMode.value
  try { localStorage.setItem(MODE_KEY, darkMode.value ? 'dark' : 'light') } catch { /* ignore */ }
  applyTheme()
}

onMounted(() => {
  try {
    const savedFamily = localStorage.getItem(FAMILY_KEY)
    if (savedFamily === 'gemini' || savedFamily === 'antigravity' || savedFamily === 'imageforge') {
      family.value = savedFamily
    }
    darkMode.value = localStorage.getItem(MODE_KEY) === 'dark'
  } catch { /* ignore */ }
  applyTheme()
})
</script>

<style scoped>
.app-brand-header {
  height: 48px;
}
.tracking-tight {
  letter-spacing: -0.02em;
}
.gap-2 {
  gap: 8px;
}

/* ── 主题族切换 swatch 行 ── */
.theme-family-row {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
}
.theme-swatch {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 6px 4px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  font-size: 11px;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface-variant));
  cursor: pointer;
  transition: background-color 160ms cubic-bezier(0.2, 0, 0, 1),
    border-color 160ms cubic-bezier(0.2, 0, 0, 1);
}
.theme-swatch:hover {
  background: rgb(var(--v-theme-surface-container));
}
.theme-swatch.on {
  border-color: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-primary));
}
.swatch-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.swatch-label {
  line-height: 1;
}
</style>
