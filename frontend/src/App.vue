<template>
  <v-app>
    <!-- 全局 Navigation：m3e-nav-rail（compact 72–80px；plain 路由如 /intro 隐藏） -->
    <aside v-if="!isPlainRoute" class="app-nav-rail">
      <router-link to="/" class="rail-brand" title="ImageForge — 创作台">
        <v-icon icon="mdi-creation" color="primary" size="24" />
      </router-link>

      <m3e-nav-rail mode="compact" class="rail-nav">
        <m3e-nav-item
          v-for="item in NAV_ITEMS"
          :key="item.to"
          :selected="isActive(item.to)"
          @click="go(item.to)"
        >
          <span slot="icon" class="mdi" :class="item.icon" />
          {{ item.label }}
        </m3e-nav-item>
      </m3e-nav-rail>

      <div class="rail-footer">
        <router-link to="/intro" class="rail-icon-btn" title="《一句话的旅程》主题体验页">
          <span class="mdi mdi-auto-stories" />
        </router-link>
        <div class="rail-themes" title="主题风格">
          <button
            v-for="f in THEME_FAMILIES"
            :key="f.key"
            type="button"
            :class="['rail-swatch', { on: family === f.key }]"
            :title="f.label"
            @click="setFamily(f.key)"
          >
            <span class="swatch-dot" :style="{ background: f.swatch }" />
          </button>
        </div>
        <button type="button" class="rail-icon-btn" :title="isDark ? '切换浅色模式' : '切换深色模式'" @click="toggleTheme">
          <span class="mdi" :class="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'" />
        </button>
      </div>
    </aside>

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
import { useRoute, useRouter } from 'vue-router'
import { useTheme } from 'vuetify'

const theme = useTheme()
const route = useRoute()
const router = useRouter()
const isPlainRoute = computed(() => !!route.meta.plain)

/* ── 全局导航项（路由结构不变） ── */
const NAV_ITEMS = [
  { to: '/', label: '创作台', icon: 'mdi-brush-variant' },
  { to: '/characters', label: '角色书', icon: 'mdi-account-box-multiple-outline' },
  { to: '/artists', label: '画师库', icon: 'mdi-palette-outline' },
  { to: '/loras', label: 'LoRA 库', icon: 'mdi-toy-brick-outline' },
  { to: '/rules', label: '规则', icon: 'mdi-file-code-outline' },
  { to: '/presets', label: '预设', icon: 'mdi-tune-variant' },
  { to: '/history', label: '历史', icon: 'mdi-history' },
  { to: '/settings', label: '设置', icon: 'mdi-cog-outline' },
]
function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}
function go(to: string) {
  if (!isActive(to)) router.push(to)
}

/* ── 主题族：ImageForge 紫 / Gemini / Antigravity，各自带亮暗两套 ── */
type ThemeFamilyKey = 'imageforge' | 'gemini' | 'antigravity'
const THEME_FAMILIES: Array<{ key: ThemeFamilyKey; label: string; swatch: string; light: string; dark: string }> = [
  { key: 'imageforge', label: 'ImageForge 紫', swatch: '#6750A4', light: 'light', dark: 'dark' },
  { key: 'gemini', label: 'Gemini', swatch: '#0B57D0', light: 'geminiLight', dark: 'geminiDark' },
  { key: 'antigravity', label: 'Antigravity Mono', swatch: '#121317', light: 'antigravityLight', dark: 'antigravityDark' },
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
/* ── m3e-nav-rail 承载列：compact 80px（M3 规范值），品牌 / 导航 / 底部操作三段 ── */
.app-nav-rail {
  width: 80px;
  min-width: 80px;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  background: rgb(var(--v-theme-surface));
  border-right: 1px solid rgb(var(--v-theme-outline-variant));
  flex-shrink: 0;
  z-index: 10;
  /* vertical nav item 默认宽 96–112px，必须收敛进 80px compact rail */
  --m3e-nav-bar-vertical-item-width: 80px;
  /* m3e-nav-rail 自身的 compact 宽度（库默认 96px） */
  --m3e-nav-rail-compact-width: 80px;
}
.rail-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
  flex-shrink: 0;
  text-decoration: none;
}
.rail-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
.rail-nav::-webkit-scrollbar { width: 0; }

.rail-footer {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 0 14px;
  border-top: 1px solid rgb(var(--v-theme-outline-variant));
}
.rail-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 18px;
  cursor: pointer;
  text-decoration: none;
  transition: background-color var(--if-motion-fast-effects), color var(--if-motion-fast-effects);
}
.rail-icon-btn:hover {
  background: rgb(var(--v-theme-surface-container));
  color: rgb(var(--v-theme-primary));
}
.rail-themes {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px 0;
}
.rail-swatch {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: 2px solid transparent;
  border-radius: 50%;
  background: transparent;
  cursor: pointer;
  transition: border-color var(--if-motion-fast-effects);
}
.rail-swatch.on { border-color: rgb(var(--v-theme-primary)); }
.swatch-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
</style>

<style>
.v-application .v-application__wrap {
  flex-direction: row;
}
/* v-main 在 rail 旁必须可收缩（flex-basis auto 会按内容撑满全宽并盖住 rail） */
.v-application .v-main {
  flex: 1 1 auto;
  min-width: 0;
}
</style>
