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
        <div class="pa-2 border-t text-center">
          <v-btn
            variant="text"
            block
            density="compact"
            size="small"
            class="text-caption text-grey"
            @click="toggleTheme"
          >
            <v-icon size="16" class="mr-1">
              {{ theme.global.current.value.dark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}
            </v-icon>
            <span v-if="!rail">{{ theme.global.current.value.dark ? '浅色模式' : '深色模式' }}</span>
          </v-btn>
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
import { ref } from 'vue'
import { useTheme } from 'vuetify'

const drawer = ref(true)
const rail = ref(false)
const theme = useTheme()

function toggleTheme() {
  theme.global.name.value = theme.global.current.value.dark ? 'light' : 'dark'
}
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
</style>
