<template>
  <NavBar v-if="!isChat && !isLanding && !isPitch" />
  <main :class="{ 'main--full': isLanding || isChat || isPitch }">
    <RouterView />
  </main>
  <JessyChatbot v-if="!isChat && !isPitch" />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar        from './components/NavBar.vue'
import JessyChatbot  from './components/JessyChatbot.vue'
import { useAuth }   from './composables/useAuth.js'

const { isAuthenticated } = useAuth()
const route     = useRoute()
const isChat    = computed(() => route.path.startsWith('/chat'))
const isLanding = computed(() => route.path === '/')
const isPitch   = computed(() => route.path === '/pitch')
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: var(--font-sans); background: var(--bg-base); color: var(--fg-2); }
main { padding: var(--s-10) var(--s-5); max-width: 1100px; margin: 0 auto; }
main.main--full { padding: 0; max-width: none; margin: 0; background: transparent; }
</style>
