<template>
  <div>
    <div class="page-header">
      <h1>Optimiseur de prompts</h1>
      <p class="sub">Réduis les tokens de tes prompts sans perdre en précision.</p>
    </div>

    <div class="provider-row">
      <label>LLM utilisé</label>
      <select v-model="selectedProvider" class="provider-select">
        <option value="">LLM (optionnel)</option>
        <option v-for="p in availableProviders" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-if="selectedProvider" v-model="selectedModel" class="provider-select">
        <option value="">Modèle</option>
        <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
      </select>
    </div>

    <div class="editor-grid">
      <div class="panel">
        <label>Prompt original</label>
        <textarea v-model="prompt" placeholder="Pourrais-tu s'il te plaît m'expliquer…" rows="10" />
        <div class="char-count">{{ prompt.length }} caractères · ~{{ estimateTokens(prompt) }} tokens</div>
        <button class="btn-primary" :disabled="!prompt.trim() || loading" @click="run">
          {{ loading ? 'Analyse…' : 'Optimiser' }}
        </button>
      </div>

      <div class="panel" v-if="result">
        <label>
          Prompt optimisé
          <span v-if="qwenActive" class="restruct-badge qwen-badge">★ Qwen</span>
          <span v-else-if="result.restructured" class="restruct-badge">✦ Restructuré</span>
          <span v-if="result.qwen_template_type" class="template-type-badge" :class="result.qwen_template_type">
            {{ result.qwen_template_type === 'pedagogique' ? 'Pédagogique' : 'Structuré' }}
          </span>
        </label>
        <textarea :value="displayedOutput" readonly rows="10" class="output" />
        <div class="char-count">
          {{ displayedOutput.length }} caractères · {{ viewTokens }} tokens
        </div>
        <div class="view-toggle" v-if="qwenActive || result.restructured">
          <button :class="['toggle-btn', viewMode === 'qwen' ? 'active' : '']"
                  v-if="qwenActive" @click="viewMode = 'qwen'">★ Qwen</button>
          <button :class="['toggle-btn', viewMode === 'heuristic' ? 'active' : '']"
                  @click="viewMode = 'heuristic'">Heuristique</button>
          <button :class="['toggle-btn', viewMode === 'original' ? 'active' : '']"
                  @click="viewMode = 'original'">Original</button>
        </div>
        <button class="btn-copy" @click="copy(displayedOutput)">{{ copied ? '✓ Copié' : 'Copier' }}</button>
      </div>
    </div>

    <!-- E3 — Chips de complétion guidée -->
    <div v-if="result?.chips?.length" class="chips-section">
      <p class="chips-hint">Slots manquants — cliquez pour compléter votre prompt :</p>
      <div v-for="chip in result.chips" :key="chip.slot" class="chip-row">
        <span class="chip-label">{{ chip.label }}</span>
        <div class="chip-options">
          <button
            v-for="opt in chip.options"
            :key="opt"
            class="chip-opt"
            @click="applyChip(chip.slot, chip.label, opt)"
          >{{ opt }}</button>
        </div>
      </div>
    </div>

    <div v-if="result" class="results">
      <div v-if="!selectedProvider" class="cost-hint">
        Sélectionnez un modèle pour voir les économies en dollars.
      </div>

      <div class="kpi-grid">
        <div class="kpi-card">
          <p>Tokens économisés</p>
          <span :class="result.tokens_saved > 0 ? 'green' : ''">{{ result.tokens_saved }}</span>
        </div>
        <div class="kpi-card">
          <p>Réduction</p>
          <span class="green">{{ reductionPct }}%</span>
        </div>
        <div class="kpi-card">
          <p>Énergie économisée</p>
          <span class="green">{{ (result.kwh_saved * 1_000_000).toFixed(3) }} mWh</span>
        </div>
        <div class="kpi-card kpi-card--badge">
          <p>Qualité du prompt</p>
          <span class="badge-pertinence" :class="pertinenceBadge.cls">
            <span class="badge-dot"></span>{{ pertinenceBadge.label }}
          </span>
          <small class="kpi-score-sub">{{ result.pertinence_score }}/100</small>
        </div>
        <div v-if="result.savings_input_usd != null" class="kpi-card">
          <p>Économie input</p>
          <span class="green">−{{ formatCost(result.savings_input_usd) }}</span>
        </div>
        <div v-if="result.savings_output_usd != null" class="kpi-card">
          <p>Économie output</p>
          <span class="green">−{{ formatCost(result.savings_output_usd) }}</span>
        </div>
        <div v-if="result.exchange_cost_usd != null" class="kpi-card">
          <p>Coût échange estimé</p>
          <span>{{ formatCost(result.exchange_cost_usd) }}<small v-if="result.exchange_cost_max_usd != null"> — {{ formatCost(result.exchange_cost_max_usd) }}</small></span>
        </div>
      </div>

      <!-- Note qualité 4 axes -->
      <div v-if="result.quality_note" class="section quality-section">
        <h2>Note qualité <small class="quality-global">global {{ result.quality_note.global }}/100</small></h2>
        <div class="quality-grid">
          <div v-for="axis in qualityAxes" :key="axis.key" class="quality-axis">
            <div class="quality-head">
              <span>{{ axis.label }}</span>
              <span class="quality-val">{{ result.quality_note[axis.key] }}</span>
            </div>
            <div class="quality-track">
              <div class="quality-fill" :class="scoreBand(result.quality_note[axis.key])"
                   :style="{ width: result.quality_note[axis.key] + '%' }"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tableau qualité avant / après -->
      <div v-if="result.quality_note_original && result.quality_note" class="section quality-compare-section">
        <h2>Qualité <small class="quality-global">avant → après</small></h2>
        <table class="quality-compare-table">
          <thead><tr><th>Axe</th><th>Avant</th><th>Après</th><th></th></tr></thead>
          <tbody>
            <tr v-for="ax in qualityAxes" :key="ax.key">
              <td>{{ ax.label }}</td>
              <td :class="scoreBand(result.quality_note_original[ax.key])">{{ result.quality_note_original[ax.key] }}</td>
              <td :class="scoreBand(result.quality_note[ax.key])">{{ result.quality_note[ax.key] }}</td>
              <td class="delta" :class="result.quality_note[ax.key] - result.quality_note_original[ax.key] > 0 ? 'delta-pos' : result.quality_note[ax.key] - result.quality_note_original[ax.key] < 0 ? 'delta-neg' : ''">
                {{ result.quality_note[ax.key] - result.quality_note_original[ax.key] > 0 ? '+' : '' }}{{ result.quality_note[ax.key] - result.quality_note_original[ax.key] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Ambiguïtés Qwen -->
      <div v-if="result.qwen_ambiguites?.length" class="section qwen-ambig-section">
        <div class="ambig-header">⚠ Ambiguïtés détectées</div>
        <div class="ambig-list">
          <span v-for="a in result.qwen_ambiguites" :key="a" class="ambig-chip">{{ a }}</span>
        </div>
      </div>

      <!-- Audit Qwen -->
      <div v-if="result.qwen_audit && qwenActive" class="section">
        <h2>Audit structurel</h2>
        <div class="audit-badges">
          <span v-for="(val, key) in result.qwen_audit" :key="key" class="audit-badge" :class="'audit-' + val">
            {{ auditLabels[key] ?? key }} <span class="audit-sep">·</span> <em>{{ auditValues[val] ?? val }}</em>
          </span>
        </div>
      </div>

      <!-- Prompt sous-spécifié -->
      <div v-if="result.is_underspecified || result.is_incomplete" class="underspec-alert section">
        <div class="underspec-header">
          {{ result.is_underspecified ? '✎ Prompt trop bref' : '✎ Phrase incomplète' }}
        </div>
        <p class="underspec-tip">
          <template v-if="result.underspec_type === 'caveman'">
            Prompt trop court — le LLM n'a pas assez de contexte pour répondre avec précision.
          </template>
          <template v-else-if="result.underspec_type === 'telegraphic'">
            Style télégraphique détecté. Ajoutez : la tâche précise, le format attendu, le niveau de détail.
          </template>
          <template v-else>
            Votre phrase semble incomplète. Reformulez en précisant ce que vous attendez.
          </template>
        </p>
      </div>

      <!-- Densité méta — prompt générique -->
      <div v-if="result.is_generic_prompt" class="density-alert section">
        <div class="density-header">
          ⚠ Presque la moitié du prompt est du remplissage ({{ Math.round(result.junk_density * 100) }}%)
        </div>
        <div class="density-bar">
          <div class="bar-signal" :style="{ width: (1 - result.junk_density) * 100 + '%' }">
            Contenu utile {{ Math.round((1 - result.junk_density) * 100) }}%
          </div>
          <div class="bar-junk" :style="{ width: result.junk_density * 100 + '%' }">
            Remplissage {{ Math.round(result.junk_density * 100) }}%
          </div>
        </div>
        <p class="density-tip">
          Ces instructions ne changent pas le comportement du modèle — elles consomment des tokens pour rien.
          <span v-if="result.meta_tokens_removed > 0">{{ result.meta_tokens_removed }} tokens supprimés par l'optimiseur.</span>
        </p>
      </div>

      <!-- Pyramide Pertinence / Détail -->
      <div v-if="result.pyramid" class="section">
        <button class="pyramid-toggle" @click="pyramidOpen = !pyramidOpen">
          {{ pyramidOpen ? '▲' : '▼' }} Analyse du prompt — Pyramide Pertinence/Détail
        </button>
        <div v-if="pyramidOpen" class="pyramid">
          <div v-for="layer in pyramidLayers" :key="layer.key" class="pyramid-layer">
            <span class="layer-label" :class="layer.key">{{ layer.icon }} {{ layer.label }}</span>
            <div class="layer-pills">
              <span v-if="result.pyramid[layer.key].length === 0" class="pill empty">aucun</span>
              <span v-for="seg in result.pyramid[layer.key]" :key="seg" class="pill" :class="layer.key">
                {{ seg }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="result.rules_applied.length" class="section">
        <h2>Règles appliquées</h2>
        <div class="tags">
          <span v-for="r in result.rules_applied" :key="r.label" class="tag">
            {{ r.label }} <em>({{ r.count }}x)</em>
          </span>
        </div>
      </div>

      <div v-if="result.suggestions.length" class="section">
        <h2>Suggestions</h2>
        <div v-for="s in result.suggestions" :key="s.type" class="suggestion">
          <p>{{ s.message }}</p>
          <pre v-if="s.example" class="example">{{ s.example }}</pre>
        </div>
      </div>

      <p v-if="!result.rules_applied.length && !result.suggestions.length" class="clean">
        ✓ Prompt déjà optimisé — aucune amélioration détectée.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../api/index.js'
import { useProviders } from '../../composables/useProviders.js'
import { estimateTokens } from '../../lib/tokenEstimator.js'

const { availableProviders, availableModels, selectedProvider, selectedModel } = useProviders()
const prompt      = ref('')
const result      = ref(null)
const loading     = ref(false)
const copied      = ref(false)
const pyramidOpen = ref(false)
const viewMode    = ref('qwen') // 'qwen' | 'heuristic' | 'original'

const auditLabels = { role: 'Rôle', contexte: 'Contexte', tache: 'Tâche', contraintes: 'Contraintes', format: 'Format', qualite: 'Qualité' }
const auditValues = { present: 'présent', absent: 'absent', inferred: 'inféré' }

const qwenActive = computed(() =>
  result.value?.qwen_available && result.value?.gain_estime !== 'faible' && result.value?.qwen_restructure
)

const qualityAxes = [
  { key: 'clarte',      label: 'Clarté'      },
  { key: 'specificite', label: 'Spécificité' },
  { key: 'structure',   label: 'Structure'   },
  { key: 'concision',   label: 'Concision'   },
]

const displayedOutput = computed(() => {
  if (!result.value) return ''
  if (viewMode.value === 'original') return result.value.original ?? ''
  if (viewMode.value === 'heuristic') return result.value.optimised ?? ''
  if (viewMode.value === 'qwen' && qwenActive.value) return result.value.qwen_restructure ?? result.value.optimised ?? ''
  return result.value.optimised ?? ''
})

const viewTokens = computed(() => {
  if (!result.value) return 0
  return estimateTokens(displayedOutput.value)
})

function scoreBand(v) {
  return v >= 75 ? 'q-green' : v >= 45 ? 'q-orange' : 'q-red'
}

const pyramidLayers = [
  { key: 'intention',  icon: '🎯', label: 'Intention'  },
  { key: 'contrainte', icon: '🔒', label: 'Contrainte' },
  { key: 'contexte',   icon: '💡', label: 'Contexte'   },
  { key: 'bruit',      icon: '🗑️', label: 'Bruit'      },
  { key: 'meta',       icon: '⚙️', label: 'Méta'       },
]

const scoreClass = computed(() => {
  if (!result.value) return ''
  const s = result.value.pertinence_score
  return s >= 80 ? 'green' : s >= 50 ? 'orange' : 'red'
})

const pertinenceBadge = computed(() => {
  const s = result.value?.pertinence_score ?? 100
  if (s >= 93) return { cls: 'badge-emeraude', label: 'Prompt optimal' }
  if (s >= 80) return { cls: 'badge-vert',     label: 'Prompt efficace' }
  if (s >= 65) return { cls: 'badge-jaune',    label: 'Prompt correct' }
  if (s >= 40) return { cls: 'badge-orange',   label: 'Prompt acceptable' }
  return             { cls: 'badge-rouge',     label: 'Prompt peu dense' }
})



const reductionPct = computed(() => {
  if (!result.value || result.value.tokens_before === 0) return 0
  return Math.round((result.value.tokens_saved / result.value.tokens_before) * 100)
})

async function run() {
  loading.value = true
  result.value  = null
  try {
    const { data } = await api.post('/optimise/', {
      prompt:   prompt.value,
      provider: selectedProvider.value || null,
      model:    selectedModel.value || null,
      semantic: true,
    })
    result.value = data
    pyramidOpen.value = false
    viewMode.value = (data.qwen_available && data.gain_estime !== 'faible' && data.qwen_restructure) ? 'qwen' : 'heuristic'
  } finally {
    loading.value = false
  }
}

function applyChip(slot, label, option) {
  const cleanLabel = label.replace('?', '').trim()
  prompt.value = prompt.value.trimEnd() + `\n${cleanLabel} : ${option}.`
  result.value = { ...result.value, chips: result.value.chips.filter(c => c.slot !== slot) }
}

async function copy(text) {
  await navigator.clipboard.writeText(text)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

function formatCost(usd) {
  if (usd == null || usd === 0) return ''
  if (usd < 0.001) return `${(usd * 1_000_000).toFixed(1)} µ$`
  if (usd < 0.01)  return `${(usd * 1_000).toFixed(3)} m$`
  return `$${usd.toFixed(4)}`
}
</script>

<style scoped>
.page-header { margin-bottom: var(--s-8); }
.page-header h1 { font-size: var(--t-2xl); color: var(--fg); }
.sub { color: var(--fg-dim); font-size: var(--t-base); margin-top: var(--s-1); }

.provider-row { display: flex; align-items: center; gap: var(--s-3); margin-bottom: var(--s-6); }
.provider-row label { font-size: var(--t-base); color: var(--fg-dim); white-space: nowrap; }
.provider-select {
  background: var(--bg-surface); border: 1px solid var(--border); color: var(--fg-2);
  padding: 8px 14px; border-radius: var(--r-lg); font-size: var(--t-base); min-width: 180px;
}
.editor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-5); margin-bottom: var(--s-8); }
@media (max-width: 768px) { .editor-grid { grid-template-columns: 1fr; } }

.panel label { display: block; font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-2); }
textarea {
  width: 100%; background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-lg);
  color: var(--fg-2); padding: 14px; font-size: var(--t-base); resize: vertical; line-height: var(--lh-normal);
  font-family: inherit; box-sizing: border-box;
}
textarea.output { color: #a3e635; border-color: #365314; }
textarea:focus { outline: none; border-color: var(--accent); }
.char-count { font-size: var(--t-xs); color: var(--fg-dim); margin: 6px 0 12px; }

.btn-primary {
  background: var(--accent); color: #fff; border: none; padding: 10px 24px;
  border-radius: var(--r-lg); cursor: pointer; font-size: var(--t-md); font-weight: var(--fw-semibold);
}
.btn-primary:hover:not(:disabled) { background: var(--accent-press); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-copy {
  background: var(--bg-surface); border: 1px solid var(--border); color: var(--fg-muted);
  padding: 8px 18px; border-radius: var(--r-md); cursor: pointer; font-size: var(--t-sm);
}
.btn-copy:hover { border-color: var(--accent); color: var(--accent); }

.cost-hint { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-4); font-style: italic; }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--s-4); margin-bottom: var(--s-8); }
.kpi-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl); padding: var(--s-5) var(--s-6); }
.kpi-card p    { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-2); }
.kpi-card span { font-size: 1.4rem; font-weight: var(--fw-bold); color: var(--accent); }
.kpi-card--badge { justify-content: flex-start; gap: var(--s-2); }
.kpi-score-sub { font-size: var(--t-xs); color: var(--fg-dim); margin-top: 2px; display: block; }

/* Badge pertinence coloré */
.badge-pertinence {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: var(--r-pill);
  font-size: var(--t-sm); font-weight: var(--fw-semibold);
  border: 1px solid; line-height: 1.2; white-space: nowrap;
}
.badge-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.badge-rouge    { background: rgba(127,29,29,0.3);  border-color: #7f1d1d; color: #f87171; }
.badge-rouge    .badge-dot { background: #ef4444; }
.badge-orange   { background: rgba(124,45,18,0.3);  border-color: #7c2d12; color: #fb923c; }
.badge-orange   .badge-dot { background: #f97316; }
.badge-jaune    { background: rgba(113,63,18,0.3);  border-color: #713f12; color: #fbbf24; }
.badge-jaune    .badge-dot { background: #f59e0b; }
.badge-vert     { background: rgba(20,83,45,0.3);   border-color: #14532d; color: #4ade80; }
.badge-vert     .badge-dot { background: #22c55e; }
.badge-emeraude { background: rgba(6,95,70,0.3);    border-color: #065f46; color: #34d399; }
.badge-emeraude .badge-dot { background: #10b981; }
.kpi-card span.green { color: var(--ok); }

.section { margin-bottom: var(--s-6); }
.section h2 { font-size: var(--t-base); color: var(--fg-muted); margin-bottom: var(--s-3); }
.tags { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.tag {
  background: var(--bg-surface); border: 1px solid var(--border); color: var(--fg-muted);
  padding: 4px 12px; border-radius: var(--r-pill); font-size: var(--t-xs);
}
.tag em { color: var(--accent); font-style: normal; }

.suggestion {
  background: var(--bg-surface); border-left: 3px solid #ca8a04; border-radius: var(--r-lg);
  padding: 14px 16px; margin-bottom: 10px;
}
.suggestion p { color: #fbbf24; font-size: var(--t-base); margin: 0 0 8px; }
.example {
  background: var(--bg-base); border-radius: var(--r-md); padding: 10px 14px;
  font-size: var(--t-sm); color: var(--fg-muted); white-space: pre-wrap; margin: 0;
}
.clean { color: var(--ok); font-size: var(--t-base); }

.kpi-card span.orange { color: #f59e0b; }
.kpi-card span.red    { color: #ef4444; }
.kpi-card span small  { font-size: 0.75rem; font-weight: normal; color: var(--fg-dim); margin-left: 2px; }

.pyramid-toggle {
  background: none; border: 1px solid var(--border); color: var(--fg-dim);
  padding: 8px 16px; border-radius: var(--r-lg); cursor: pointer; font-size: var(--t-sm);
  margin-bottom: var(--s-4); width: 100%; text-align: left;
}
.pyramid-toggle:hover { border-color: var(--accent); color: var(--fg); }

.pyramid { display: flex; flex-direction: column; gap: var(--s-3); }
.pyramid-layer { display: flex; align-items: flex-start; gap: var(--s-3); }
.layer-label {
  font-size: var(--t-xs); font-weight: var(--fw-semibold); white-space: nowrap;
  padding: 4px 10px; border-radius: var(--r-pill); min-width: 110px; text-align: center;
}
.underspec-alert { background: var(--bg-surface); border: 1px solid #92400e; border-radius: var(--r-xl); padding: var(--s-5) var(--s-6); }
.underspec-header { font-size: var(--t-base); font-weight: var(--fw-semibold); color: #fcd34d; margin-bottom: var(--s-2); }
.underspec-tip { font-size: var(--t-sm); color: var(--fg-dim); margin: 0; }

.density-alert { background: var(--bg-surface); border: 1px solid #b45309; border-radius: var(--r-xl); padding: var(--s-5) var(--s-6); }
.density-header { font-size: var(--t-base); font-weight: var(--fw-semibold); color: #fbbf24; margin-bottom: var(--s-3); }
.density-bar { display: flex; border-radius: var(--r-md); overflow: hidden; height: 32px; margin-bottom: var(--s-3); }
.bar-signal { background: #166534; color: #86efac; font-size: var(--t-xs); font-weight: var(--fw-semibold); display: flex; align-items: center; justify-content: center; min-width: 60px; transition: width 0.3s; }
.bar-junk   { background: #78350f; color: #fcd34d; font-size: var(--t-xs); font-weight: var(--fw-semibold); display: flex; align-items: center; justify-content: center; min-width: 40px; transition: width 0.3s; }
.density-tip { font-size: var(--t-sm); color: var(--fg-dim); margin: 0; }

.layer-label.meta { background: #1c1917; color: #a8a29e; }
.pill.meta        { background: #1c1917; border-color: #44403c; color: #a8a29e; font-style: italic; }

.layer-label.intention  { background: #14532d; color: #86efac; }
.layer-label.contrainte { background: #1e3a5f; color: #93c5fd; }
.layer-label.contexte   { background: #422006; color: #fcd34d; }
.layer-label.bruit      { background: #1f2937; color: #6b7280; }

.layer-pills { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.pill {
  font-size: var(--t-xs); padding: 4px 10px; border-radius: var(--r-pill);
  border: 1px solid transparent; max-width: 320px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pill.intention  { background: #052e16; border-color: #166534; color: #86efac; }
.pill.contrainte { background: #0c1a2e; border-color: #1d4ed8; color: #93c5fd; }
.pill.contexte   { background: #1c0a00; border-color: #92400e; color: #fcd34d; }
.pill.bruit      { background: #111827; border-color: #374151; color: #6b7280; text-decoration: line-through; }
.pill.empty      { color: var(--fg-dim); border: none; font-style: italic; text-decoration: none; background: none; }

/* Toggle 3 modes Qwen/Heuristique/Original */
.view-toggle { display: flex; gap: var(--s-2); margin: 8px 0 12px; }
.toggle-btn {
  padding: 4px 12px; border-radius: var(--r-pill); font-size: var(--t-xs); cursor: pointer;
  background: var(--bg-base); border: 1px solid var(--border); color: var(--fg-dim);
}
.toggle-btn:hover { border-color: var(--accent); color: var(--fg); }
.toggle-btn.active { background: rgba(99,102,241,0.15); border-color: #6366f1; color: #a5b4fc; font-weight: var(--fw-semibold); }

/* Badge Qwen */
.qwen-badge { background: rgba(99,102,241,0.15) !important; border-color: #6366f1 !important; color: #a5b4fc !important; }

/* Badge template type */
.template-type-badge { margin-left: 6px; padding: 1px 7px; border-radius: var(--r-pill); font-size: var(--t-xs); font-weight: var(--fw-semibold); }
.template-type-badge.standard    { background: rgba(6,95,70,0.2); border: 1px solid #065f46; color: #34d399; }
.template-type-badge.pedagogique { background: rgba(30,58,138,0.2); border: 1px solid #1d4ed8; color: #93c5fd; }

/* Tableau qualité avant/après */
.quality-compare-section h2 { display: flex; align-items: baseline; gap: var(--s-2); }
.quality-compare-table { width: 100%; border-collapse: collapse; font-size: var(--t-sm); }
.quality-compare-table th { color: var(--fg-dim); font-weight: var(--fw-semibold); padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--border); }
.quality-compare-table td { padding: 6px 10px; color: var(--fg-2); }
.quality-compare-table td.q-green  { color: #4ade80; font-weight: var(--fw-semibold); }
.quality-compare-table td.q-orange { color: #fb923c; font-weight: var(--fw-semibold); }
.quality-compare-table td.q-red    { color: #f87171; font-weight: var(--fw-semibold); }
.delta     { font-weight: var(--fw-semibold); }
.delta-pos { color: #4ade80; }
.delta-neg { color: #f87171; }

/* Ambiguïtés */
.qwen-ambig-section .ambig-header { font-size: var(--t-sm); font-weight: var(--fw-semibold); color: #fbbf24; margin-bottom: var(--s-2); }
.ambig-list { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.ambig-chip { font-size: var(--t-xs); padding: 3px 10px; border-radius: var(--r-pill); background: rgba(180,83,9,0.15); border: 1px solid #92400e; color: #fcd34d; }

/* Audit badges */
.audit-badges { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.audit-badge { font-size: var(--t-xs); padding: 3px 10px; border-radius: var(--r-pill); border: 1px solid var(--border); color: var(--fg-muted); }
.audit-sep { color: var(--fg-dim); margin: 0 3px; }
.audit-badge em { font-style: normal; font-weight: var(--fw-semibold); }
.audit-badge.audit-present em  { color: #4ade80; }
.audit-badge.audit-inferred em { color: #fbbf24; }
.audit-badge.audit-absent em   { color: #6b7280; }

/* Badge restructuré + toggle flat/restructuré */
.restruct-badge {
  display: inline-block; margin-left: 8px; padding: 2px 8px; border-radius: var(--r-pill);
  background: rgba(6,95,70,0.3); border: 1px solid #065f46; color: #34d399;
  font-size: var(--t-xs); font-weight: var(--fw-semibold);
}
.link-toggle {
  background: none; border: none; color: var(--accent); cursor: pointer;
  font-size: var(--t-xs); margin-left: 8px; padding: 0; text-decoration: underline;
}
.link-toggle:hover { color: var(--accent-press); }

/* E3 — Chips */
.chips-section {
  margin-bottom: var(--s-6);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  padding: var(--s-4) var(--s-5);
}
.chips-hint {
  font-size: var(--t-xs);
  color: var(--fg-dim);
  margin: 0 0 var(--s-3);
}
.chip-row {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  margin-bottom: var(--s-2);
  flex-wrap: wrap;
}
.chip-label {
  font-size: var(--t-xs);
  color: var(--fg-muted);
  white-space: nowrap;
  min-width: 130px;
}
.chip-options { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.chip-opt {
  padding: 3px 12px;
  border-radius: var(--r-pill);
  border: 1px solid var(--border);
  background: var(--bg-base);
  color: var(--fg-dim);
  font-size: var(--t-xs);
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.chip-opt:hover { border-color: var(--accent); color: var(--accent); }

/* Note qualité 4 axes */
.quality-section h2 { display: flex; align-items: baseline; gap: var(--s-2); }
.quality-global { font-size: var(--t-xs); color: var(--fg-dim); font-weight: var(--fw-semibold); }
.quality-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--s-4); }
.quality-axis { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-lg); padding: var(--s-3) var(--s-4); }
.quality-head { display: flex; justify-content: space-between; font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: 6px; }
.quality-val { font-weight: var(--fw-bold); color: var(--fg-2); }
.quality-track { height: 8px; background: var(--bg-base); border-radius: var(--r-pill); overflow: hidden; }
.quality-fill { height: 100%; border-radius: var(--r-pill); transition: width 0.3s; }
.quality-fill.q-green  { background: #22c55e; }
.quality-fill.q-orange { background: #f59e0b; }
.quality-fill.q-red    { background: #ef4444; }
</style>
