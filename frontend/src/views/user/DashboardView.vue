<template>
  <OnboardingModal
    v-if="showOnboarding"
    @done="onOnboardingDone"
    @skip="showOnboarding = false"
  />

  <div v-if="data">
    <div v-if="showAlert" class="alert-threshold">
      Vous avez consommé <strong>{{ data.weekly_co2 }} g CO₂</strong> cette semaine —
      seuil fixé à <strong>{{ data.user.threshold }} g</strong>.
      <RouterLink to="/parametres">Modifier le seuil →</RouterLink>
    </div>

    <div class="page-header">
      <div>
        <h1>Mon espace</h1>
        <p class="email">{{ data.user.email }}</p>
      </div>
      <div class="tab-switcher">
        <button :class="['tab-btn', activeTab === 'financier' && 'active']" @click="activeTab = 'financier'">
          $ Financier
        </button>
        <button :class="['tab-btn', activeTab === 'eco' && 'active']" @click="activeTab = 'eco'">
          🌱 Éco
        </button>
      </div>
    </div>

    <!-- ── ONGLET FINANCIER ── -->
    <template v-if="activeTab === 'financier'">
      <div class="kpi-grid">
        <div class="kpi-card">
          <p>Coût total estimé</p>
          <span>{{ data.financial.cost_usd > 0 ? formatCost(data.financial.cost_usd) : '—' }}</span>
          <small class="kpi-equiv">{{ data.kpi.sessions }} session{{ data.kpi.sessions > 1 ? 's' : '' }}</small>
        </div>
        <div class="kpi-card kpi-card--savings">
          <p>Économies réalisées</p>
          <span class="green">{{ data.financial.savings_usd > 0 ? '−' + formatCost(data.financial.savings_usd) : '—' }}</span>
          <small class="kpi-equiv">{{ data.financial.tokens_saved?.toLocaleString() ?? 0 }} tokens supprimés</small>
        </div>
        <div class="kpi-card">
          <p>Coût moyen / session</p>
          <span>{{ data.financial.avg_cost_usd > 0 ? formatCost(data.financial.avg_cost_usd) : '—' }}</span>
          <small class="kpi-equiv">{{ data.kpi.tokens?.toLocaleString() ?? '—' }} tokens au total</small>
        </div>
        <div class="kpi-card">
          <p>Sessions analysées</p>
          <span>{{ data.kpi.sessions }}</span>
          <small class="kpi-equiv">depuis le début</small>
        </div>
      </div>

      <div class="section">
        <h2>Historique des sessions</h2>
        <table v-if="data.sessions.length">
          <thead>
            <tr>
              <th>Date</th><th>Type</th><th>Modèle</th>
              <th>Tokens</th><th>Économisés</th><th>Coût estimé</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in data.sessions" :key="s.id" class="clickable" @click="$router.push(`/user/sessions/${s.id}`)">
              <td>{{ s.date?.slice(0, 10) ?? '—' }}</td>
              <td><span :class="['type-badge', s.session_type]">{{ { chat: '💬 Chat', import: '📤 Import', estimation: '📝 Estimation' }[s.session_type] ?? '—' }}</span></td>
              <td class="mono">{{ s.model ?? s.provider ?? '—' }}</td>
              <td>{{ s.tokens_estimated?.toLocaleString() ?? '—' }}</td>
              <td class="green">{{ s.tokens_saved > 0 ? '−' + s.tokens_saved.toLocaleString() : '—' }}</td>
              <td class="mono">{{ s.cost_usd != null ? formatCost(s.cost_usd) : '—' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">
          <div class="empty-icon">⚡</div>
          <h3>Votre tableau de bord est vide</h3>
          <p>Démarrez une conversation pour voir vos économies, votre coût par échange et votre impact en temps réel.</p>
          <div class="empty-actions">
            <RouterLink to="/chat" class="cta-btn primary">Démarrer une session Chat →</RouterLink>
            <RouterLink to="/upload" class="cta-btn">Analyser une conversation</RouterLink>
            <RouterLink to="/manuel" class="cta-btn">Calcul rapide</RouterLink>
          </div>
        </div>
      </div>
    </template>

    <!-- ── ONGLET ÉCO ── -->
    <template v-if="activeTab === 'eco'">
      <div class="kpi-grid">
        <div class="kpi-card">
          <p>Énergie consommée</p>
          <span>{{ data.kpi.kwh }} Wh</span>
          <small class="kpi-equiv">≈ {{ (data.kpi.kwh * 0.4).toFixed(1) }} g CO₂</small>
        </div>
        <div class="kpi-card">
          <p>CO₂ émis</p>
          <span>{{ (data.kpi.co2 * 1000).toFixed(1) }} g</span>
          <small class="kpi-equiv">{{ co2CarEquiv }}</small>
        </div>
        <div class="kpi-card">
          <p>Sessions</p>
          <span>{{ data.kpi.sessions }}</span>
          <small class="kpi-equiv">{{ data.kpi.tokens?.toLocaleString() ?? '—' }} tokens</small>
        </div>
        <div class="kpi-card">
          <p>Moy. par session</p>
          <span>{{ data.kpi.avg_kwh }} Wh</span>
          <small class="kpi-equiv">≈ {{ (data.kpi.avg_kwh * 0.4).toFixed(1) }} g CO₂</small>
        </div>
      </div>

      <!-- Progression CO₂ hebdomadaire -->
      <div class="weekly-progress" v-if="data.user.threshold != null">
        <div class="progress-header">
          <span>CO₂ cette semaine</span>
          <span :class="weeklyPct >= 90 ? 'red' : weeklyPct >= 70 ? 'orange' : 'green'">
            {{ (data.weekly_co2 * 1000).toFixed(3) }} g / {{ data.user.threshold }} g
          </span>
        </div>
        <div class="progress-track">
          <div class="progress-fill"
            :class="weeklyPct >= 90 ? 'red' : weeklyPct >= 70 ? 'orange' : 'green'"
            :style="{ width: Math.min(weeklyPct, 100) + '%' }">
          </div>
        </div>
        <small class="progress-note" v-if="weeklyPct >= 90">Seuil CO₂ presque atteint — optimisez vos prompts pour continuer à travailler au même rythme.</small>
      </div>
      <div v-else class="weekly-cta">
        <RouterLink to="/parametres">Définir un objectif hebdomadaire →</RouterLink>
      </div>

      <div class="triptych" v-if="data.sessions.length">
        <div class="chart-card">
          <h3>Consommation par session</h3>
          <Bar :data="barData" :options="barOpts" />
        </div>
        <div class="chart-card">
          <h3>Évolution dans le temps</h3>
          <Line :data="lineData" :options="lineOpts" />
        </div>
        <div class="chart-card">
          <h3>Répartition providers</h3>
          <PolarArea :data="polarData" :options="polarOpts" />
        </div>
      </div>

      <div class="section">
        <h2>Historique des sessions</h2>
        <table v-if="data.sessions.length">
          <thead>
            <tr>
              <th>ID</th><th>Date</th><th>Type</th><th>Provider</th>
              <th>Tokens</th><th>Énergie</th><th>Efficacité</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in data.sessions" :key="s.id" class="clickable" @click="$router.push(`/user/sessions/${s.id}`)">
              <td>S-{{ String(s.id).padStart(3, '0') }}</td>
              <td>{{ s.date?.slice(0, 10) ?? '—' }}</td>
              <td><span :class="['type-badge', s.session_type]">{{ { chat: '💬 Chat', import: '📤 Import', estimation: '📝 Estimation' }[s.session_type] ?? '—' }}</span></td>
              <td>{{ s.provider }}</td>
              <td>{{ s.tokens_estimated?.toLocaleString() }}</td>
              <td>{{ s.kwh_estimated?.toFixed(4) ?? '—' }} kWh</td>
              <td><span :class="['status', s.energy_status]">{{ { low: 'Faible', medium: 'Moyen', high: 'Élevé' }[s.energy_status] ?? '—' }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">
          <div class="empty-icon">⚡</div>
          <h3>Votre tableau de bord est vide</h3>
          <p>Démarrez une conversation pour voir vos économies, votre coût par échange et votre impact en temps réel.</p>
          <div class="empty-actions">
            <RouterLink to="/chat" class="cta-btn primary">Démarrer une session Chat →</RouterLink>
            <RouterLink to="/upload" class="cta-btn">Analyser une conversation</RouterLink>
            <RouterLink to="/manuel" class="cta-btn">Calcul rapide</RouterLink>
          </div>
        </div>
      </div>
    </template>

  </div>
  <p v-else class="loading">Chargement...</p>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import OnboardingModal from '../../components/OnboardingModal.vue'
import { Bar, Line, PolarArea } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  LineElement, PointElement, ArcElement, RadialLinearScale,
  Tooltip, Legend, Filler,
} from 'chart.js'
import api from '../../api/index.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, RadialLinearScale, Tooltip, Legend, Filler)

const data           = ref(null)
const showOnboarding = ref(false)
const activeTab      = ref('financier')

const showAlert = computed(() =>
  data.value?.user?.threshold != null &&
  data.value?.weekly_co2 > data.value?.user?.threshold
)

const weeklyPct = computed(() => {
  if (!data.value?.user?.threshold) return 0
  return Math.round((data.value.weekly_co2 * 1000) / data.value.user.threshold * 100)
})

const co2CarEquiv = computed(() => {
  if (!data.value) return ''
  const g = data.value.kpi.co2 * 1000
  const m = g / 0.12
  if (m < 1)    return `< 1 m en voiture`
  if (m < 1000) return `≈ ${m.toFixed(0)} m en voiture`
  return `≈ ${(m / 1000).toFixed(2)} km en voiture`
})

function formatCost(usd) {
  if (usd == null || usd === 0) return '—'
  if (usd < 0.0001) return '< $0.0001'
  if (usd < 0.01)   return `$${usd.toFixed(4)}`
  if (usd < 1)      return `$${usd.toFixed(3)}`
  return `$${usd.toFixed(2)}`
}

function onOnboardingDone(seuil) {
  showOnboarding.value = false
  if (data.value?.user) data.value.user.threshold = seuil
}

const GRID  = 'rgba(0,0,0,0.05)'
const TICK  = '#9ca3af'
const baseOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
}

const barData = computed(() => ({
  labels: data.value?.chart.labels ?? [],
  datasets: [
    { label: 'Wh',    data: (data.value?.chart.kwh ?? []).map(v => +(v * 1000).toFixed(4)), backgroundColor: '#3B6D11', borderRadius: 3 },
    { label: 'g CO₂', data: (data.value?.chart.co2 ?? []).map(v => +(v * 1000).toFixed(4)), backgroundColor: '#C0DD97', borderRadius: 3 },
  ],
}))
const barOpts = { ...baseOpts, scales: {
  x: { ticks: { color: TICK, font: { size: 10 } }, grid: { color: GRID } },
  y: { ticks: { color: TICK, font: { size: 10 } }, grid: { color: GRID } },
}}

const lineData = computed(() => ({
  labels: data.value?.chart.labels ?? [],
  datasets: [
    { label: 'Wh',    data: (data.value?.chart.kwh ?? []).map(v => +(v * 1000).toFixed(4)), borderColor: '#3B6D11', backgroundColor: 'rgba(59,109,17,0.08)', fill: true, tension: 0.4, pointRadius: 3 },
    { label: 'g CO₂', data: (data.value?.chart.co2 ?? []).map(v => +(v * 1000).toFixed(4)), borderColor: '#E24B4A', backgroundColor: 'rgba(226,75,74,0.08)', fill: true, tension: 0.4, pointRadius: 3 },
  ],
}))
const lineOpts = { ...baseOpts, scales: {
  x: { ticks: { color: TICK, font: { size: 10 } }, grid: { color: GRID } },
  y: { ticks: { color: TICK, font: { size: 10 } }, grid: { color: GRID } },
}}

const POLAR_COLORS = ['#3B6D11', '#378ADD', '#EF9F27', '#E24B4A', '#8B5CF6', '#EC4899']
const polarData = computed(() => ({
  labels: data.value?.donut.labels ?? [],
  datasets: [{ data: data.value?.donut.values ?? [], backgroundColor: POLAR_COLORS, borderWidth: 0 }],
}))
const polarOpts = { ...baseOpts,
  plugins: { legend: { display: true, position: 'bottom', labels: { color: TICK, font: { size: 10 }, boxWidth: 10 } } },
  scales: { r: { ticks: { display: false }, grid: { color: GRID } } },
}

onMounted(async () => {
  const { data: d } = await api.get('/user/dashboard')
  data.value = d
  if (d.user?.threshold === null || d.user?.threshold === undefined) {
    showOnboarding.value = true
  }
})
</script>

<style scoped>
.alert-threshold {
  background: var(--sources-soft); border: 1px solid var(--sources);
  border-radius: var(--r-lg); padding: var(--s-3) var(--s-5);
  font-size: var(--t-sm); color: var(--sources); margin-bottom: var(--s-6);
  display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap;
}
.alert-threshold strong { font-weight: var(--fw-bold); }
.alert-threshold a { color: var(--sources); font-weight: var(--fw-semibold); margin-left: auto; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: var(--s-8); flex-wrap: wrap; gap: var(--s-4);
}
.page-header h1 { font-size: var(--t-2xl); color: var(--fg); }
.email { color: var(--fg-dim); font-size: var(--t-base); margin-top: var(--s-1); }

/* ── Tabs ── */
.tab-switcher {
  display: flex; background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: 3px; gap: 2px;
}
.tab-btn {
  padding: 7px 18px; border-radius: var(--r-md); border: none;
  background: none; color: var(--fg-muted); font-size: var(--t-sm);
  font-weight: var(--fw-semibold); cursor: pointer;
  transition: background var(--t-fast), color var(--t-fast);
}
.tab-btn:hover { color: var(--fg); }
.tab-btn.active { background: var(--bg-base); color: var(--fg); box-shadow: 0 1px 3px rgba(0,0,0,0.2); }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: var(--s-4); margin-bottom: var(--s-10); }
.kpi-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl); padding: var(--s-5) var(--s-6); }
.kpi-card--savings { border-color: rgba(34,197,94,.3); }
.kpi-card p    { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-2); }
.kpi-card span { font-size: 1.4rem; font-weight: var(--fw-bold); color: var(--accent); display: block; }
.kpi-card span.green { color: #4ade80; }
.kpi-equiv     { font-size: var(--t-xs); color: var(--fg-dim); margin-top: var(--s-1); display: block; }

.triptych { display: grid; grid-template-columns: 1fr 2fr 1fr; gap: var(--s-4); margin-bottom: var(--s-10); }
@media (max-width: 900px) { .triptych { grid-template-columns: 1fr; } }
.chart-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl); padding: var(--s-5); }
.chart-card h3 { font-size: var(--t-xs); color: var(--fg-dim); text-transform: uppercase; letter-spacing: var(--tracking-caps); margin-bottom: var(--s-3); }
.chart-card canvas { height: 220px !important; }

.section h2 { font-size: var(--t-lg); color: var(--fg-muted); margin-bottom: var(--s-4); }
table { width: 100%; border-collapse: collapse; font-size: var(--t-base); }
th { padding: 10px 14px; background: var(--bg-surface); color: var(--fg-dim); text-align: left; border-bottom: 1px solid var(--border); }
td { padding: 10px 14px; border-bottom: 1px solid var(--border-subtle); }
td.green { color: #4ade80; font-weight: var(--fw-semibold); }
td.mono  { font-family: var(--font-mono); font-size: var(--t-sm); }
tr.clickable { cursor: pointer; }
tr.clickable:hover td { background: var(--bg-hover); }

.type-badge { padding: 3px 8px; border-radius: var(--r-pill); font-size: var(--t-xs); font-weight: var(--fw-semibold); white-space: nowrap; }
.type-badge.chat       { background: var(--accent-soft, rgba(99,102,241,0.1)); color: var(--accent); }
.type-badge.import     { background: var(--ok-soft);   color: var(--ok); }
.type-badge.estimation { background: var(--bg-surface); color: var(--fg-muted); border: 1px solid var(--border); }
.status { padding: 3px 8px; border-radius: var(--r-pill); font-size: var(--t-xs); font-weight: var(--fw-semibold); }
.status.low     { background: var(--ok-soft);      color: var(--ok); }
.status.medium  { background: var(--warn-soft);    color: var(--warn); }
.status.high    { background: var(--sources-soft); color: var(--sources); }
.status.massive { background: var(--danger-soft);  color: var(--danger); }

.weekly-progress {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl);
  padding: var(--s-4) var(--s-6); margin-bottom: var(--s-8);
}
.progress-header {
  display: flex; justify-content: space-between; align-items: center;
  font-size: var(--t-sm); color: var(--fg-muted); margin-bottom: var(--s-3);
}
.progress-header .green { color: var(--ok); font-weight: var(--fw-semibold); }
.progress-header .orange { color: #f59e0b; font-weight: var(--fw-semibold); }
.progress-header .red   { color: var(--danger); font-weight: var(--fw-semibold); }
.progress-track { background: var(--border); border-radius: var(--r-pill); height: 8px; overflow: hidden; }
.progress-fill  { height: 100%; border-radius: var(--r-pill); transition: width 0.4s ease; }
.progress-fill.green  { background: var(--ok); }
.progress-fill.orange { background: #f59e0b; }
.progress-fill.red    { background: var(--danger); }
.progress-note { font-size: var(--t-xs); color: var(--fg-dim); margin-top: var(--s-2); display: block; }
.weekly-cta { margin-bottom: var(--s-8); font-size: var(--t-sm); }
.weekly-cta a { color: var(--accent); text-decoration: none; }
.weekly-cta a:hover { text-decoration: underline; }

.empty, .loading { color: var(--fg-dim); font-size: var(--t-base); }
.empty-state {
  display: flex; flex-direction: column; align-items: center; text-align: center;
  padding: var(--s-12) var(--s-6);
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-2xl);
}
.empty-icon { font-size: 2.5rem; margin-bottom: var(--s-4); }
.empty-state h3 { font-size: var(--t-xl); color: var(--fg); margin-bottom: var(--s-3); }
.empty-state p { font-size: var(--t-base); color: var(--fg-dim); max-width: 440px; line-height: 1.6; margin-bottom: var(--s-8); }
.empty-actions { display: flex; gap: var(--s-3); flex-wrap: wrap; justify-content: center; }
.cta-btn {
  padding: 10px 20px; border-radius: var(--r-md); border: 1px solid var(--border);
  font-size: var(--t-base); font-weight: var(--fw-semibold);
  color: var(--fg-muted); text-decoration: none; background: var(--bg-base);
  transition: border-color var(--t-fast), color var(--t-fast);
}
.cta-btn:hover { border-color: var(--accent); color: var(--accent); }
.cta-btn.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.cta-btn.primary:hover { opacity: 0.9; }
</style>
