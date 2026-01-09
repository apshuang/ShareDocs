<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import { computed } from 'vue'
import Navbar from './components/Navbar.vue'

const route = useRoute()
const showNavbar = computed(() => {
  return route.name !== 'login' && route.name !== 'register'
})
</script>

<template>
  <div id="app">
    <Navbar v-if="showNavbar" />
    <main :class="{ 'full-screen': !showNavbar }">
      <RouterView />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
}

#app {
  min-height: 100vh;
  width: 100%;
  background: #f5f5f5;
}

main {
  width: 100%;
  margin: 0;
  padding: 0;
  min-height: 100vh;
}

main.full-screen {
  min-height: 100vh;
  margin: 0;
  padding: 0;
}
</style>
