<template>
  <div v-if="session">
    <div class="page-header">
      <button class="back-btn" @click="$router.push('/user/dashboard')">← Retour</button>
      <h1>Session S-{{ String(session.id).padStart(3, '0') }}</h1>
      <p class="sub">{{ session.date?.slice(0, 10) ?? '—' }} · {{ session.provider }}</p>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <p>Tokens</p>
        <span>{{ session.tokens_estimated?.toLocaleString() }}</span>
      </div>
      <div class="kpi-card">
        <p>Énergie</p>
        <span>{{ session.kwh_estimated ? (session.kwh_estimated * 1000).toFixed(4) + ' Wh' : '—' }}</span>
      </div>
      <div class="kpi-card">
        <p>CO₂ standard</p>
        <span>{{ session.co2_standard ? (session.co2_standard * 1000).toFixed(4) + ' g' : (session.co2_equiv ? (session.co2_equiv * 1000).toFixed(4) + ' g' : '—') }}</span>
      </div>
      <div class="kpi-card ethical">
        <p>CO₂ éthique</p>
        <span>{{ session.co2_ethical ? (session.co2_ethical * 1000).toFixed(4) + ' g' : '—' }}</span>
      </div>
      <div class="kpi-card saved">
        <p>CO₂ évité</p>
        <span>{{ session.co2_saved ? (session.co2_saved * 1000).toFixed(4) + ' g' : '—' }}</span>
      </div>
      <div class="kpi-card">
        <p>Logements BBC</p>
        <span>{{ session.homes_heated_min ? session.homes_heated_min.toFixed(1) + ' min' : '—' }}</span>
      </div>
      <div class="kpi-card">
        <p>Statut</p>
        <span :class="['status', session.energy_status]">{{ session.energy_status ?? '—' }}</span>
      </div>
    </div>

    <div class="section" v-if="factors">
      <h2>Pourquoi ce chiffre ?</h2>
      <div class="breakdown">
        <div class="breakdown-row">
          <span class="br-label">Énergie</span>
          <code>{{ session.tokens_estimated.toLocaleString() }} tokens</code>
          <span class="br-op">×</span>
          <code>{{ factors.kwh_per_token }} kWh/token</code>
          <span class="br-op">=</span>
          <code class="br-result">{{ session.kwh_estimated?.toFixed(6) }} kWh</code>
        </div>
        <div class="breakdown-row">
          <span class="br-label">CO₂ standard</span>
          <code>{{ session.kwh_estimated?.toFixed(6) }} kWh</code>
          <span class="br-op">×</span>
          <code>{{ factors.co2_per_kwh }} kg/kWh × 1 000</code>
          <span class="br-op">=</span>
          <code class="br-result" style="color: var(--sources)">{{ session.co2_standard ? (session.co2_standard * 1000).toFixed(4) : '—' }} g</code>
        </div>
        <div class="breakdown-row">
          <span class="br-label">CO₂ éthique</span>
          <code>{{ session.kwh_estimated?.toFixed(6) }} kWh</code>
          <span class="br-op">×</span>
          <code>{{ factors.co2_per_kwh_ethical }} kg/kWh × 1 000</code>
          <span class="br-op">=</span>
          <code class="br-result" style="color: var(--ok)">{{ session.co2_ethical ? (session.co2_ethical * 1000).toFixed(4) : '—' }} g</code>
        </div>
        <p class="br-note">Coefficients {{ session.provider }} / {{ session.model }} — estimations issues de la littérature académique (Epoch AI, IEA).</p>
      </div>
    </div>

    <div class="section" v-if="suggestions !== null">
      <h2>Tu pourrais économiser</h2>
      <div class="sugg-card" v-if="suggestions.length > 0">
        <p class="sugg-intro">En utilisant un modèle moins énergivore pour cette même session :</p>
        <div class="sugg-row" v-for="s in suggestions" :key="s.provider + s.model">
          <span class="sugg-model">{{ s.provider }} / <strong>{{ s.model }}</strong></span>
          <span class="sugg-save">−{{ s.savePct }}% CO₂ (−{{ s.saveGrams }} g)</span>
        </div>
      </div>
      <div class="sugg-optimal" v-else>
        Tu utilises déjà l'un des modèles les plus sobres disponibles.
      </div>
    </div>

    <div class="section">
      <h2>Corriger le modèle</h2>
      <div class="model-selector">
        <select v-model="editProvider" @change="editModel = ''" class="sel">
          <option value="" disabled>Provider</option>
          <option v-for="g in providers" :key="g.provider" :value="g.provider">{{ g.provider }}</option>
        </select>
        <select v-model="editModel" :disabled="!editProvider" class="sel">
          <option value="" disabled>Modèle</option>
          <option v-for="m in modelsForProvider" :key="m" :value="m">{{ m }}</option>
        </select>
        <button class="btn-save" :disabled="!editProvider || !editModel || saving" @click="saveModel">
          {{ saving ? '…' : 'Mettre à jour' }}
        </button>
        <span v-if="saveMsg" :class="['save-msg', saveError ? 'err' : 'ok']">{{ saveMsg }}</span>
      </div>
    </div>

    <div class="section">
      <h2>Contenu de la conversation</h2>
      <pre v-if="content" class="conversation">{{ content }}</pre>
      <p v-else class="empty">Fichier non disponible.</p>
    </div>
  </div>

  <p v-else-if="error" class="error">{{ error }}</p>
  <p v-else class="loading">Chargement...</p>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/index.js'

const KWH_TABLE = [
  // ── OpenAI anciens (workflows, n8n, intégrations) ──
  { provider: 'OpenAI', model: 'gpt-4.1-nano',  kwh: 0.0000001 },
  { provider: 'OpenAI', model: 'gpt-4o-mini',   kwh: 0.0000002 },
  { provider: 'OpenAI', model: 'gpt-4-1',       kwh: 0.0000009 },
  { provider: 'OpenAI', model: 'gpt-4.1',       kwh: 0.0000015 },
  { provider: 'OpenAI', model: 'gpt-4o',        kwh: 0.0000009 },
  { provider: 'OpenAI', model: 'o1-mini',       kwh: 0.0000008 },
  { provider: 'OpenAI', model: 'o3-mini',       kwh: 0.0000010 },
  { provider: 'OpenAI', model: 'o1',            kwh: 0.0000020 },
  { provider: 'OpenAI', model: 'o3',            kwh: 0.0000030 },
  // ── OpenAI GPT-5.x ──
  { provider: 'OpenAI', model: 'gpt-5-nano',    kwh: 0.0000002 },
  { provider: 'OpenAI', model: 'gpt-5.4-nano',  kwh: 0.0000003 },
  { provider: 'OpenAI', model: 'gpt-5-mini',    kwh: 0.0000005 },
  { provider: 'OpenAI', model: 'gpt-5.4-mini',  kwh: 0.0000008 },
  { provider: 'OpenAI', model: 'gpt-5',         kwh: 0.0000035 },
  { provider: 'OpenAI', model: 'gpt-5.4',       kwh: 0.0000030 },
  { provider: 'OpenAI', model: 'gpt-5.4-pro',   kwh: 0.0000035 },
  { provider: 'OpenAI', model: 'gpt-5.5',       kwh: 0.0000050 },
  { provider: 'OpenAI', model: 'gpt-5.5-pro',   kwh: 0.0000060 },
  // ── Anthropic ──
  { provider: 'Anthropic', model: 'claude-haiku-4-5',  kwh: 0.0000002 },
  { provider: 'Anthropic', model: 'claude-sonnet-4-6', kwh: 0.0000009 },
  { provider: 'Anthropic', model: 'claude-opus-4-7',   kwh: 0.0000022 },
  // ── Google Gemini 2.x ──
  { provider: 'Google', model: 'gemini-2-0-flash',      kwh: 0.0000002 },
  { provider: 'Google', model: 'gemini-2-5-flash-lite', kwh: 0.0000002 },
  { provider: 'Google', model: 'gemini-2-5-flash',      kwh: 0.0000003 },
  { provider: 'Google', model: 'gemini-2-5-pro',        kwh: 0.0000012 },
  // ── Google Gemini 3.x ──
  { provider: 'Google', model: 'gemini-3-1-flash-lite', kwh: 0.0000003 },
  { provider: 'Google', model: 'gemini-3-flash',        kwh: 0.0000006 },
  { provider: 'Google', model: 'gemini-3-1-pro',        kwh: 0.0000018 },
]
const CO2_STD_G_PER_KWH = 400

const route   = useRoute()
const session = ref(null)
const content = ref(null)
const factors = ref(null)
const error   = ref(null)

const providers        = ref([])
const editProvider     = ref('')
const editModel        = ref('')
const saving           = ref(false)
const saveMsg          = ref('')
const saveError        = ref(false)

const modelsForProvider = computed(() =>
  providers.value.find(g => g.provider === editProvider.value)?.models ?? []
)

const suggestions = computed(() => {
  if (!session.value || !factors.value) return null
  const currentKwh = factors.value.kwh_per_token
  if (!currentKwh) return []
  const tokens = session.value.tokens_estimated || 0
  const currentCo2g = currentKwh * tokens * CO2_STD_G_PER_KWH * 1000

  return KWH_TABLE
    .filter(m =>
      m.kwh < currentKwh &&
      !(m.provider === session.value.provider && m.model === session.value.model)
    )
    .map(m => {
      const altCo2g = m.kwh * tokens * CO2_STD_G_PER_KWH * 1000
      const savePct = Math.round((1 - m.kwh / currentKwh) * 100)
      const saveGrams = ((currentCo2g - altCo2g) / 1000).toFixed(4)
      return { provider: m.provider, model: m.model, savePct, saveGrams }
    })
    .sort((a, b) => b.savePct - a.savePct)
    .slice(0, 3)
})

async function saveModel() {
  saving.value  = true
  saveMsg.value = ''
  try {
    const { data } = await api.patch(`/sessions/${route.params.id}`, {
      provider: editProvider.value,
      model:    editModel.value,
    })
    session.value   = data.session
    factors.value   = data.factors
    saveMsg.value   = 'Modèle mis à jour.'
    saveError.value = false
  } catch (e) {
    saveMsg.value   = e.response?.data?.detail ?? 'Erreur lors de la mise à jour.'
    saveError.value = true
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const [detail, prov] = await Promise.all([
      api.get(`/sessions/${route.params.id}`),
      api.get('/upload/providers'),
    ])
    session.value   = detail.data.session
    content.value   = detail.data.content
    factors.value   = detail.data.factors
    providers.value = prov.data
    editProvider.value = session.value?.provider ?? ''
    editModel.value    = session.value?.model    ?? ''
  } catch (e) {
    error.value = e.response?.status === 404
      ? 'Session introuvable.'
      : 'Erreur lors du chargement.'
  }
})
</script>

<style scoped>
.page-header { margin-bottom: var(--s-8); }
.back-btn {
  background: none; border: 1px solid var(--border); color: var(--fg-muted);
  padding: 6px 14px; border-radius: var(--r-md); cursor: pointer; margin-bottom: var(--s-4); font-size: var(--t-base);
}
.back-btn:hover { background: var(--bg-surface); color: var(--fg); }
.page-header h1 { font-size: var(--t-2xl); color: var(--fg); }
.sub { color: var(--fg-dim); font-size: var(--t-base); margin-top: var(--s-1); }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--s-4); margin-bottom: var(--s-10); }
.kpi-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl); padding: var(--s-5) var(--s-6); }
.kpi-card p    { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-2); }
.kpi-card span { font-size: 1.3rem; font-weight: var(--fw-bold); color: var(--accent); }
.kpi-card.ethical span { color: var(--ok); }
.kpi-card.saved span   { color: var(--co2-avoided); }

.status { padding: 3px 8px; border-radius: var(--r-pill); font-size: var(--t-sm); font-weight: var(--fw-semibold); }
.status.low     { background: var(--ok-soft);      color: var(--ok); }
.status.medium  { background: var(--warn-soft);    color: var(--warn); }
.status.high    { background: var(--sources-soft); color: var(--sources); }
.status.massive { background: var(--danger-soft);  color: var(--danger); }

.section h2 { font-size: var(--t-lg); color: var(--fg-muted); margin-bottom: var(--s-4); }

.breakdown {
  background: var(--bg-base); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: var(--s-5); display: flex; flex-direction: column; gap: var(--s-4);
}
.breakdown-row {
  display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap;
}
.br-label {
  font-size: var(--t-xs); color: var(--fg-dim); width: 90px;
  flex-shrink: 0; text-transform: uppercase; letter-spacing: var(--tracking-wide);
}
code {
  font-family: var(--font-mono); font-size: var(--t-sm);
  background: var(--bg-surface); padding: 3px 8px; border-radius: var(--r-sm);
  color: var(--fg-2);
}
.br-op     { color: var(--fg-dim); font-size: var(--t-sm); }
.br-result { font-weight: var(--fw-semibold); color: var(--accent); }
.br-note   { font-size: var(--t-xs); color: var(--fg-dim); margin-top: var(--s-2); padding-top: var(--s-3); border-top: 1px solid var(--border); }
.conversation {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl);
  padding: var(--s-5); font-size: var(--t-sm); color: var(--fg-2);
  white-space: pre-wrap; word-break: break-word;
  max-height: 600px; overflow-y: auto; line-height: var(--lh-normal);
}
.empty, .loading { color: var(--fg-dim); font-size: var(--t-base); }
.error { color: var(--danger); font-size: var(--t-base); }

.sugg-card {
  background: var(--bg-base); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: var(--s-5);
  display: flex; flex-direction: column; gap: var(--s-3);
}
.sugg-intro { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-2); }
.sugg-row {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--s-2);
  padding: var(--s-3) var(--s-4);
  background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--r-md);
}
.sugg-model { font-size: var(--t-sm); color: var(--fg-2); }
.sugg-model strong { color: var(--fg); }
.sugg-save { font-size: var(--t-sm); font-weight: var(--fw-semibold); color: var(--ok); }
.model-selector {
  display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap;
}
.sel {
  padding: 8px 12px; border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--bg-surface); color: var(--fg); font-size: var(--t-sm); cursor: pointer;
}
.sel:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-save {
  padding: 8px 16px; background: var(--accent); color: #fff;
  border: none; border-radius: var(--r-md); font-size: var(--t-sm);
  cursor: pointer; font-weight: var(--fw-semibold);
}
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.save-msg { font-size: var(--t-sm); font-weight: var(--fw-semibold); }
.save-msg.ok  { color: var(--ok); }
.save-msg.err { color: var(--danger); }

.sugg-optimal {
  background: var(--ok-soft); border: 1px solid var(--ok);
  border-radius: var(--r-lg); padding: var(--s-4) var(--s-5);
  font-size: var(--t-sm); color: var(--ok); font-weight: var(--fw-semibold);
}
</style>
