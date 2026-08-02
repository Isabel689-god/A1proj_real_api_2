<template>
  <router-view />
</template>

<script setup lang="ts">
import { provide, ref } from 'vue'

const THEME_KEY = 'a1proj-theme'
const initialTheme = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark'
const theme = ref<'dark' | 'light'>(initialTheme)

function applyTheme(t: 'dark' | 'light') {
  theme.value = t
  document.documentElement.setAttribute('data-theme', t)
  localStorage.setItem(THEME_KEY, t)
}

function toggleTheme() {
  applyTheme(theme.value === 'dark' ? 'light' : 'dark')
}

provide('theme', theme)
provide('toggleTheme', toggleTheme)
</script>

<style>
body, html {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
}
#app {
  width: 100%;
  height: 100%;
}
</style>
