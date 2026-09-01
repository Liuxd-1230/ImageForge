<template>
  <v-app>
    <!-- Navigation Drawer / Rail -->
    <v-navigation-drawer
      v-model="drawer"
      :rail="rail"
      permanent
      @click="rail = false"
    >
      <v-list-item
        prepend-icon="mdi-creation"
        title="ImageForge"
        subtitle="Anima 提示词工作台"
        class="py-3"
      >
        <template #append>
          <v-btn
            variant="text"
            icon="mdi-chevron-left"
            @click.stop="rail = !rail"
          />
        </template>
      </v-list-item>

      <v-divider />

      <v-list density="compact" nav class="mt-2">
        <v-list-item prepend-icon="mdi-brush" title="创作台" to="/" value="studio" />
        <v-list-item prepend-icon="mdi-account-group" title="角色书" to="/characters" value="characters" />
        <v-list-item prepend-icon="mdi-palette" title="画师库" to="/artists" value="artists" />
        <v-list-item prepend-icon="mdi-toy-brick" title="LoRA" to="/loras" value="loras" />
        <v-list-item prepend-icon="mdi-file-document" title="规则文件" to="/rules" value="rules" />
        <v-list-item prepend-icon="mdi-tune" title="预设管理" to="/presets" value="presets" />
        <v-list-item prepend-icon="mdi-history" title="生图历史" to="/history" value="history" />
        <v-list-item prepend-icon="mdi-cog" title="设置" to="/settings" value="settings" />
      </v-list>
    </v-navigation-drawer>

    <!-- Top App Bar -->
    <v-app-bar density="compact" elevation="0" border="b">
      <v-app-bar-nav-icon @click="drawer = !drawer" />
      <v-app-bar-title class="text-subtitle-1 font-weight-bold">
        ImageForge — Anima 二次元生图提示词工作台
      </v-app-bar-title>

      <v-spacer />

      <!-- Dark / Light Theme Toggle -->
      <v-btn
        icon
        variant="text"
        size="small"
        @click="toggleTheme"
      >
        <v-icon>{{ theme.global.current.value.dark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}</v-icon>
      </v-btn>
    </v-app-bar>

    <!-- Main Content View -->
    <v-main>
      <router-view />
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

<style>
/* Global smooth scrollbar & typography adjustments */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(128, 128, 128, 0.3);
  border-radius: 3px;
}
</style>
