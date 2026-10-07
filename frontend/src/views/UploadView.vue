<template>
  <div>
    <h1 class="page-title">Calculer mon impact</h1>

    <div v-if="!result" class="upload-layout">
    <div class="upload-card">
      <p class="error" v-if="error">{{ error }}</p>
      <form @submit.prevent="submit">
        <label>Fichier de conversation (.txt)</label>
        <input type="file" accept=".txt" @change="onFile" required />
        <label>
          LLM
          <span v-if="detectConfidence === 'full'"          class="detected-badge ok">détecté automatiquement</span>
          <span v-else-if="detectConfidence === 'provider_only'" class="detected-badge warn">provider détecté — choisis le modèle</span>
        </label>
        <select v-model="selectedProvider" required>
          <option value="" disabled>Choisir un LLM</option>
          <option v-for="p in availableProviders" :key="p" :value="p">{{ p }}</option>
        </select>
        <label>Modèle</label>
        <select v-model="selectedModel" required :disabled="!selectedProvider">
          <option value="" disabled>{{ selectedProvider ? 'Choisir un modèle' : 'Sélectionne un LLM d\'abord' }}</option>
          <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
        </select>
        <label>Langue du texte</label>
        <select v-model="langue">
          <option value="fr">Français</option>
          <option value="en">Anglais</option>
        </select>
        <button type="submit" :disabled="loading || !selectedProvider || !selectedModel">
          {{ loading ? 'Calcul en cours...' : 'Analyser' }}
        </button>
      </form>
    </div>
    <div class="export-guide">
      <button class="guide-toggle" @click="guideOpen = !guideOpen">
        <span>Comment exporter ma conversation ?</span>
        <span class="guide-chevron">{{ guideOpen ? '▲' : '▼' }}</span>
      </button>
      <div v-if="guideOpen" class="guide-body">
        <div v-for="llm in exportGuide" :key="llm.name" class="guide-item">
          <button class="guide-llm" @click="llm.open = !llm.open">
            <span class="guide-llm-name">{{ llm.name }}</span>
            <span>{{ llm.open ? '−' : '+' }}</span>
          </button>
          <div v-if="llm.open" class="guide-steps">
            <ol>
              <li v-for="step in llm.steps" :key="step">{{ step }}</li>
            </ol>
            <p v-if="llm.tip" class="guide-tip">💡 {{ llm.tip }}</p>
          </div>
        </div>
        <p class="guide-note">Le fichier doit être au format <strong>.txt</strong> — un simple copier-coller du texte suffit.</p>
      </div>
    </div>

    </div> <!-- /upload-layout -->

    <div v-else class="result-card">
      <h2>Résultats</h2>
      <p class="result-meta">{{ result.provider }} · {{ result.model }}</p>
      <div class="result-grid">
        <div class="result-item">
          <p>Caractères</p><span>{{ result.char_count.toLocaleString() }}</span>
        </div>
        <div class="result-item">
          <p>Tokens estimés</p><span>{{ result.total_tokens.toLocaleString() }}</span>
        </div>
        <div class="result-item">
          <p>Turns estimés</p><span>{{ result.turns }}</span>
        </div>
        <div class="result-item">
          <p>Énergie consommée</p><span>{{ result.fmt.energie }}</span>
        </div>
        <div class="result-item">
          <p>CO₂ émis</p><span>{{ result.fmt.co2 }}</span>
        </div>
        <div class="result-item">
          <p>CO₂ évité (réseau)</p><span>{{ result.fmt.co2_evite }}</span>
        </div>
        <div class="result-item">
          <p>Chauffage BBC</p><span>{{ result.fmt.logement_bbc }}</span>
        </div>
        <div class="result-item">
          <p>Appartement moyen</p><span>{{ result.fmt.appart_moyen }}</span>
        </div>
      </div>
      <p class="saved-msg" v-if="result.saved">✓ Session sauvegardée dans votre espace</p>
      <p class="saved-msg warning" v-else>Connectez-vous pour sauvegarder vos analyses</p>
      <button @click="result = null" class="btn-reset">Nouvelle analyse</button>
    </div>

    <div v-if="result" class="sources-card">
      <h2>Méthodologie & Sources</h2>
      <div class="sources-grid">
        <div class="source-item">
          <div class="source-label">TOKEN</div>
          <div class="source-body">Unité de traitement IA. ~3,5 caractères/token en français, ~4 en anglais.</div>
        </div>
        <div class="source-item">
          <div class="source-label">BBC</div>
          <div class="source-body">Bâtiment Basse Consommation — label Effinergie. Seuil : &lt; 50 kWh/m²/an. Précurseur de la RE2020.</div>
        </div>
        <div class="source-item">
          <div class="source-label">ADEME</div>
          <div class="source-body">Agence de la Transition Écologique. Source : Base Carbone — référence officielle FR pour les facteurs d'émission CO₂.</div>
        </div>
        <div class="source-item">
          <div class="source-label">SNCU</div>
          <div class="source-body">Syndicat National du Chauffage Urbain. Contenu carbone moyen réseau chaleur : 113 g CO₂/kWh (rapport 2023).</div>
        </div>
        <div class="source-item">
          <div class="source-label">kWh/TOKEN</div>
          <div class="source-body">Énergie consommée par token selon le LLM. Estimations issues de la littérature académique (Epoch AI, IEA 2023).</div>
        </div>
        <div class="source-item">
          <div class="source-label">INSEE</div>
          <div class="source-body">Surface moyenne appartement France : 63–70 m². Source : enquête Logement INSEE 2013.</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api/index.js'
import { useProviders } from '../composables/useProviders.js'

const { availableProviders, availableModels, selectedProvider, selectedModel } = useProviders()
const langue    = ref('fr')
const guideOpen = ref(false)

const exportGuide = ref([
  {
    name: 'ChatGPT',
    open: false,
    steps: [
      'Ouvre la conversation dans ChatGPT.',
      'Sélectionne tout le texte de la page (Ctrl+A ou Cmd+A).',
      'Copie (Ctrl+C) et colle dans un éditeur de texte (Notepad, TextEdit…).',
      'Sauvegarde en .txt.',
    ],
    tip: 'ChatGPT propose aussi un export complet via Paramètres → Contrôle des données → Exporter les données (format JSON — prends alors la conversation souhaitée dans le ZIP).',
  },
  {
    name: 'Claude',
    open: false,
    steps: [
      'Ouvre la conversation dans claude.ai.',
      'Clique sur les trois points "…" en haut à droite de la conversation.',
      'Sélectionne "Exporter la conversation" si disponible, ou sélectionne tout le texte (Ctrl+A).',
      'Colle dans un éditeur de texte et sauvegarde en .txt.',
    ],
    tip: 'Les artefacts (code, documents) sont inclus dans la sélection — tu peux les supprimer manuellement si tu veux uniquement le dialogue.',
  },
  {
    name: 'Gemini',
    open: false,
    steps: [
      'Ouvre la conversation dans gemini.google.com.',
      'Sélectionne tout le texte de la page (Ctrl+A).',
      'Copie et colle dans un éditeur de texte.',
      'Sauvegarde en .txt.',
    ],
    tip: 'Gemini n\'a pas d\'export natif — le copier-coller manuel est la seule option.',
  },
  {
    name: 'Mistral / Le Chat',
    open: false,
    steps: [
      'Ouvre la conversation sur chat.mistral.ai.',
      'Sélectionne tout le texte (Ctrl+A) et copie.',
      'Colle dans un éditeur de texte, sauvegarde en .txt.',
    ],
    tip: null,
  },
  {
    name: 'Autre LLM',
    open: false,
    steps: [
      'Ouvre ta conversation dans l\'interface web du LLM.',
      'Sélectionne tout le texte (Ctrl+A), copie (Ctrl+C).',
      'Ouvre Notepad (Windows) ou TextEdit (Mac) en mode texte brut.',
      'Colle le texte et sauvegarde en .txt.',
    ],
    tip: 'La méthode copier-coller fonctionne avec n\'importe quel LLM — la précision du calcul dépend uniquement du nombre de caractères dans le fichier.',
  },
])
const file    = ref(null)
const result  = ref(null)
const error   = ref('')
const loading = ref(false)

const detectConfidence = ref('none')
const detectRaw        = ref('')

async function onFile(e) {
  file.value         = e.target.files[0]
  detectConfidence.value = 'none'
  detectRaw.value    = ''
  if (!file.value) return
  try {
    const form = new FormData()
    form.append('conversation', file.value)
    const { data } = await api.post('/upload/detect', form)
    detectConfidence.value = data.confidence
    if (data.confidence === 'full') {
      selectedProvider.value = data.provider
      selectedModel.value    = data.model
    } else if (data.confidence === 'provider_only') {
      selectedProvider.value = data.provider
      selectedModel.value    = ''
      detectRaw.value        = data.raw || ''
    }
  } catch { /* silencieux */ }
}

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const form = new FormData()
    form.append('conversation', file.value)
    form.append('provider', selectedProvider.value)
    form.append('model', selectedModel.value)
    form.append('langue', langue.value)
    const { data } = await api.post('/upload/file', form)
    result.value = data
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Une erreur est survenue.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.page-title { font-size: var(--t-2xl); color: var(--fg); margin-bottom: var(--s-5); }

.upload-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--s-6);
  align-items: start;
  margin-bottom: var(--s-6);
}
@media (max-width: 768px) { .upload-layout { grid-template-columns: 1fr; } }

.export-guide {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-2xl);
  overflow: hidden;
}
.guide-toggle {
  width: 100%; display: flex; justify-content: space-between; align-items: center;
  padding: var(--s-4) var(--s-6); background: none; border: none; cursor: pointer;
  color: var(--fg-muted); font-size: var(--t-base); font-weight: var(--fw-medium);
  text-align: left;
}
.guide-toggle:hover { color: var(--fg); }
.guide-chevron { font-size: var(--t-xs); color: var(--fg-dim); }
.guide-body { padding: 0 var(--s-6) var(--s-5); border-top: 1px solid var(--border); }
.guide-item { margin-top: var(--s-4); }
.guide-llm {
  width: 100%; display: flex; justify-content: space-between; align-items: center;
  background: var(--bg-base); border: 1px solid var(--border); border-radius: var(--r-md);
  padding: var(--s-2) var(--s-4); cursor: pointer; color: var(--fg-2); font-size: var(--t-sm);
  text-align: left;
}
.guide-llm:hover { border-color: var(--accent); color: var(--accent); }
.guide-llm-name { font-weight: var(--fw-semibold); }
.guide-steps { padding: var(--s-3) var(--s-4) 0; }
.guide-steps ol { padding-left: var(--s-5); margin: 0; }
.guide-steps li { font-size: var(--t-sm); color: var(--fg-muted); line-height: 1.8; }
.guide-tip {
  margin-top: var(--s-3); font-size: var(--t-xs); color: var(--fg-dim);
  background: var(--accent-soft); border-radius: var(--r-md); padding: var(--s-2) var(--s-3);
}
.guide-note {
  margin-top: var(--s-5); font-size: var(--t-xs); color: var(--fg-dim);
  border-top: 1px solid var(--border); padding-top: var(--s-4);
}
.upload-card, .result-card {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-2xl); padding: var(--s-8);
}
form { display: flex; flex-direction: column; gap: 14px; }
label { font-size: var(--t-base); color: var(--fg-muted); }
.detected-badge {
  margin-left: var(--s-2); font-size: var(--t-xs); padding: 2px 8px;
  border-radius: var(--r-pill); font-weight: var(--fw-medium);
}
.detected-badge.ok   { color: var(--ok);     background: var(--ok-soft); }
.detected-badge.warn { color: var(--warn);   background: var(--warn-soft); }
input[type="file"], select {
  background: var(--bg-input); border: 1px solid var(--border); border-radius: var(--r-md);
  color: var(--fg-2); padding: 10px 12px; font-size: var(--t-md); width: 100%;
}
button[type="submit"] {
  background: var(--accent); color: #fff; border: none; border-radius: var(--r-md);
  padding: 12px; font-weight: var(--fw-bold); cursor: pointer; font-size: var(--t-md);
}
button[type="submit"]:disabled { opacity: .5; cursor: not-allowed; }
.error { color: var(--danger); font-size: var(--t-base); margin-bottom: var(--s-2); }
.result-meta { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-4); }
.result-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-4); margin: var(--s-5) 0; }
.result-item { background: var(--bg-base); border-radius: var(--r-lg); padding: 14px 16px; }
.result-item p    { font-size: var(--t-xs); color: var(--fg-dim); margin-bottom: var(--s-1); }
.result-item span { font-size: 1.1rem; font-weight: var(--fw-bold); color: var(--accent); }
.saved-msg { font-size: var(--t-base); color: var(--ok); margin-bottom: var(--s-4); }
.saved-msg.warning { color: var(--warn); }
.btn-reset {
  background: none; border: 1px solid var(--accent); color: var(--accent);
  padding: 10px 20px; border-radius: var(--r-md); cursor: pointer;
}
.sources-card {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-2xl);
  padding: var(--s-8); max-width: 560px; margin-top: var(--s-6);
}
.sources-card h2 { font-size: var(--t-base); color: var(--fg-muted); margin-bottom: var(--s-5); }
.sources-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--s-4); }
.source-label { font-size: var(--t-xs); color: var(--sources); font-weight: var(--fw-bold); margin-bottom: var(--s-1); letter-spacing: var(--tracking-caps); }
.source-body  { font-size: var(--t-xs); color: var(--fg-dim); line-height: var(--lh-normal); }
</style>
