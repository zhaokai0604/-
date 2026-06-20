<script setup>
import { onMounted, onUnmounted } from 'vue'

import AuthDrawer from './components/AuthDrawer.vue'
import SettingsDrawer from './components/SettingsDrawer.vue'
import { usePlatform } from './stores/platform'

const platform = usePlatform()

onMounted(() => {
  platform.initPlatform()
})

onUnmounted(() => {
  platform.destroyPlatform()
})
</script>

<template>
  <router-view />
  <AuthDrawer />
  <SettingsDrawer />
</template>
