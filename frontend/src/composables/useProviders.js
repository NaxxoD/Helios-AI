import { ref, computed, watch, onMounted } from 'vue'
import api from '../api/index.js'

export function useProviders() {
  const providerGroups  = ref([])
  const selectedProvider = ref('')
  const selectedModel    = ref('')

  const availableProviders = computed(() =>
    providerGroups.value.map(g => g.provider)
  )

  const availableModels = computed(() =>
    providerGroups.value.find(g => g.provider === selectedProvider.value)?.models ?? []
  )

  watch(selectedProvider, () => { selectedModel.value = '' })

  onMounted(async () => {
    const { data } = await api.get('/upload/providers')
    providerGroups.value = data
  })

  return { availableProviders, availableModels, selectedProvider, selectedModel }
}
