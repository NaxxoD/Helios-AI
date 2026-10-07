import { ref, watch } from 'vue'

const theme = ref(localStorage.getItem('theme') || 'dark')

function apply(t) {
  document.documentElement.setAttribute('data-theme', t)
  localStorage.setItem('theme', t)
}

apply(theme.value)

watch(theme, apply)

export function useTheme() {
  function toggle() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }
  return { theme, toggle }
}
