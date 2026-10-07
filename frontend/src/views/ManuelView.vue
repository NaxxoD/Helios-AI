<template>
  <div>
    <h1 class="page-title">Estimation manuelle</h1>
    <p class="page-sub">Pas de fichier ? Estime ton impact en quelques clics.</p>

    <div v-if="!result" class="form-card">
      <p class="error" v-if="error">{{ error }}</p>

      <div class="field">
        <label>LLM utilisé</label>
        <select v-model="selectedProvider" required>
          <option value="" disabled>Sélectionne un LLM</option>
          <option v-for="p in availableProviders" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>

      <div class="field">
        <label>Modèle</label>
        <select v-model="selectedModel" required :disabled="!selectedProvider">
          <option value="" disabled>{{ selectedProvider ? 'Choisir un modèle' : 'Sélectionne un LLM d\'abord' }}</option>
          <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>

      <div class="field">
        <label>Langue de la conversation</label>
        <select v-model="langue">
          <option value="fr">Français</option>
          <option value="en">Anglais</option>
        </select>
      </div>

      <div class="field">
        <label>Intensité de la session</label>
        <div class="slider-labels">
          <span v-for="(level, i) in levels" :key="i" :class="{ active: sliderVal === i + 1 }">
            {{ level.label }}
          </span>
        </div>
        <input type="range" min="1" max="4" step="1" v-model.number="sliderVal" class="slider" />
        <div class="slider-desc">{{ currentLevel.desc }}</div>
      </div>

      <div class="field advanced-toggle">
        <button type="button" class="btn-advanced" @click="advanced = !advanced">
          {{ advanced ? '▲ Masquer' : '▼ Mode avancé' }} — saisie tokens
        </button>
      </div>

      <div v-if="advanced" class="field">
        <div class="unit-toggle">
          <button :class="['toggle-btn', { active: unit === 'tokens' }]" @click="unit = 'tokens'">Tokens</button>
          <button :class="['toggle-btn', { active: unit === 'mots' }]" @click="unit = 'mots'">Mots</button>
        </div>
        <label>
          {{ unit === 'tokens' ? 'Nombre de tokens' : 'Nombre de mots' }}
          <span class="hint">(remplace le curseur)</span>
        </label>
        <input type="number" v-model.number="rawInput" min="1"
               :placeholder="unit === 'tokens' ? 'ex : 5 000' : 'ex : 3 800'" />
        <div v-if="unit === 'mots' && rawInput > 0" class="conversion-hint">
          ≈ {{ Math.round(rawInput * 1.3).toLocaleString() }} tokens (× 1,3)
        </div>
      </div>

      <div class="token-preview">
        Tokens estimés : <strong>{{ finalTokens.toLocaleString() }}</strong>
      </div>

      <button class="btn-primary" :disabled="!selectedProvider || !selectedModel || loading" @click="submit">
        {{ loading ? 'Calcul…' : 'Estimer mon impact' }}
      </button>
    </div>

    <div v-else class="result-card">
      <h2>Résultats estimés</h2>
      <p class="result-meta">{{ result.provider }} · {{ result.total_tokens.toLocaleString() }} tokens · {{ result.turns }} tours</p>
      <div class="result-grid">
        <div class="result-item">
          <p>Énergie consommée</p><span>{{ result.fmt.energie }}</span>
        </div>
        <div class="result-item">
          <p>CO₂ standard</p><span>{{ result.fmt.co2 }}</span>
        </div>
        <div class="result-item">
          <p>CO₂ évité (réseau)</p><span>{{ result.fmt.co2_evite }}</span>
        </div>
        <div class="result-item">
          <p>Chauffage BBC</p><span>{{ result.fmt.logement_bbc }}</span>
        </div>
      </div>
      <p class="saved-msg" v-if="result.saved">✓ Session sauvegardée dans votre espace</p>
      <p class="saved-msg warning" v-else>Connectez-vous pour sauvegarder vos analyses</p>
      <button @click="reset" class="btn-reset">Nouvelle estimation</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../api/index.js'
import { useProviders } from '../composables/useProviders.js'

const { availableProviders, availableModels, selectedProvider, selectedModel } = useProviders()
const langue    = ref('fr')
const sliderVal = ref(2)
const advanced  = ref(false)
const unit      = ref('tokens')
const rawInput  = ref(null)
const result    = ref(null)
const error     = ref('')
const loading   = ref(false)

const levels = [
  { label: 'Léger',   tokens: 500,   desc: 'Quelques échanges courts (~500 tokens)' },
  { label: 'Modéré',  tokens: 2500,  desc: 'Discussion normale (~2 500 tokens)' },
  { label: 'Intense', tokens: 8000,  desc: 'Session de travail approfondie (~8 000 tokens)' },
  { label: 'Massif',  tokens: 20000, desc: 'Travail long et intensif (~20 000 tokens)' },
]

const currentLevel = computed(() => levels[sliderVal.value - 1])

const finalTokens = computed(() => {
  if (advanced.value && rawInput.value > 0) {
    return unit.value === 'mots'
      ? Math.round(rawInput.value * 1.3)
      : rawInput.value
  }
  return currentLevel.value.tokens
})


async function submit() {
  error.value   = ''
  loading.value = true
  try {
    const { data } = await api.post('/upload/manuel', {
      provider: selectedProvider.value,
      model:    selectedModel.value,
      tokens:   finalTokens.value,
      langue:   langue.value,
    })
    result.value = data
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Une erreur est survenue.'
  } finally {
    loading.value = false
  }
}

function reset() {
  result.value   = null
  error.value    = ''
  rawInput.value = null
  advanced.value = false
  unit.value     = 'tokens'
}
</script>

<style scoped>
.page-title { font-size: var(--t-2xl); color: var(--fg); margin-bottom: var(--s-2); }
.page-sub   { color: var(--fg-dim); font-size: var(--t-base); margin-bottom: var(--s-8); }

.form-card, .result-card {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-2xl);
  padding: var(--s-8); max-width: 520px;
}
.field { display: flex; flex-direction: column; gap: var(--s-2); margin-bottom: var(--s-5); }
label  { font-size: var(--t-base); color: var(--fg-muted); }
.hint  { color: var(--fg-dim); font-size: var(--t-xs); }
select, input[type="number"] {
  background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--r-md);
  color: var(--fg-2); padding: 10px 12px; font-size: var(--t-md);
}

.slider-labels { display: flex; justify-content: space-between; margin-bottom: var(--s-1); }
.slider-labels span { font-size: var(--t-xs); color: var(--fg-dim); transition: color var(--t-fast); }
.slider-labels span.active { color: var(--accent); font-weight: var(--fw-bold); }
.slider {
  -webkit-appearance: none; width: 100%; height: 4px;
  background: var(--border); border-radius: 2px; outline: none;
}
.slider::-webkit-slider-thumb {
  -webkit-appearance: none; width: 18px; height: 18px;
  border-radius: 50%; background: var(--accent); cursor: pointer;
}
.slider-desc { font-size: var(--t-sm); color: var(--accent); margin-top: var(--s-1); }

.advanced-toggle { margin-bottom: var(--s-1); }
.btn-advanced {
  background: none; border: none; color: var(--fg-dim); font-size: var(--t-sm);
  cursor: pointer; padding: 0; text-decoration: underline;
}
.btn-advanced:hover { color: var(--fg-muted); }
.unit-toggle { display: flex; gap: 0; margin-bottom: var(--s-2); }
.toggle-btn {
  background: var(--bg-input); border: 1px solid var(--border); color: var(--fg-dim);
  padding: 6px 16px; font-size: var(--t-sm); cursor: pointer;
}
.toggle-btn:first-child { border-radius: var(--r-md) 0 0 var(--r-md); }
.toggle-btn:last-child  { border-radius: 0 var(--r-md) var(--r-md) 0; border-left: none; }
.toggle-btn.active { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: var(--fw-semibold); }
.conversion-hint { font-size: var(--t-xs); color: var(--ok); margin-top: var(--s-1); }

.token-preview {
  background: var(--bg-input); border-radius: var(--r-md); padding: 10px 14px;
  font-size: var(--t-base); color: var(--fg-dim); margin-bottom: var(--s-5);
}
.token-preview strong { color: var(--accent); }

.btn-primary {
  width: 100%; background: var(--accent); color: #fff; border: none;
  border-radius: var(--r-md); padding: 12px; font-weight: var(--fw-bold);
  cursor: pointer; font-size: var(--t-md);
}
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }

.result-meta { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-4); }
.result-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: var(--s-5); }
.result-item { background: var(--bg-base); border-radius: var(--r-lg); padding: 14px 16px; }
.result-item p    { font-size: var(--t-xs); color: var(--fg-dim); margin-bottom: var(--s-1); }
.result-item span { font-size: 1.1rem; font-weight: var(--fw-bold); color: var(--accent); }
.saved-msg { font-size: var(--t-base); color: var(--ok); margin-bottom: var(--s-4); }
.saved-msg.warning { color: var(--warn); }
.btn-reset {
  background: none; border: 1px solid var(--accent); color: var(--accent);
  padding: 10px 20px; border-radius: var(--r-md); cursor: pointer;
}
.error { color: var(--danger); font-size: var(--t-base); margin-bottom: var(--s-3); }
</style>
