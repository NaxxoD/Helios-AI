<template>
  <div v-if="data">

    <!-- ── TABS ── -->
    <div class="admin-tabs">
      <button v-for="tab in tabs" :key="tab.id"
        :class="['tab-btn', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id">
        {{ tab.label }}
      </button>
    </div>

    <!-- ══ TAB : DASHBOARD ══ -->
    <template v-if="activeTab === 'dashboard'">

    <!-- ── KPIs ── -->
    <div class="kpi-grid">
      <div class="kpi-card"><p>Énergie totale</p><span>{{ data.kpi.kwh }} Wh</span></div>
      <div class="kpi-card"><p>CO₂ évité</p><span>{{ data.kpi.co2 }} g</span></div>
      <div class="kpi-card"><p>Sessions</p><span>{{ data.kpi.sessions }}</span></div>
      <div class="kpi-card"><p>Utilisateurs</p><span>{{ data.kpi.users }}</span></div>
      <div class="kpi-card"><p>User le + actif</p><span class="top">{{ data.kpi.top_user }}</span></div>
    </div>

    <!-- ── SANTÉ PLATEFORME ── -->
    <div class="section-title">Santé plateforme</div>
    <div class="charts-row">
      <div class="chart-card wide">
        <h3>Consommation globale (Wh + g CO₂)</h3>
        <Line :data="lineData" :options="lineOpts" />
      </div>
      <div class="chart-card">
        <h3>CO₂ par provider (g)</h3>
        <Bar :data="providerBarData" :options="providerBarOpts" />
      </div>
    </div>

    <!-- ── QUI CONSOMME ── -->
    <div class="section-title">Qui consomme</div>
    <div class="charts-row">
      <div class="chart-card">
        <h3>Top utilisateurs — Énergie (Wh)</h3>
        <Bar :data="topUsersKwhData" :options="topUsersOpts" />
      </div>
      <div class="chart-card">
        <h3>Top utilisateurs — Sessions</h3>
        <Bar :data="topUsersSessionsData" :options="topUsersOpts" />
      </div>
    </div>

    </template>

    <!-- ══ TAB : SESSIONS ══ -->
    <template v-if="activeTab === 'sessions'">
    <div class="section">
      <div class="section-header">
        <h2>Sessions <span class="count">({{ filteredSessions.length }})</span></h2>
        <div class="filters">
          <input v-model="filterEmail"    class="filter-input" placeholder="Filtrer par email…" />
          <select v-model="filterProvider" class="filter-select">
            <option value="">Tous les providers</option>
            <option v-for="p in providers" :key="p" :value="p">{{ p }}</option>
          </select>
          <select v-model="filterStatus" class="filter-select">
            <option value="">Tous les statuts</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
            <option value="massive">massive</option>
          </select>
          <button v-if="filterEmail || filterProvider || filterStatus" class="btn-reset" @click="resetFilters">✕ Reset</button>
        </div>
      </div>
      <table>
        <thead><tr><th>ID</th><th>User</th><th>Provider</th><th>kWh</th><th>Statut</th><th></th></tr></thead>
        <tbody>
          <tr v-for="s in filteredSessions" :key="s.id">
            <td>S-{{ String(s.id).padStart(3, '0') }}</td>
            <td>{{ s.email }}</td>
            <td>{{ s.provider }}</td>
            <td>{{ s.kwh_estimated?.toFixed(6) ?? '—' }}</td>
            <td><span :class="['status', s.energy_status]">{{ s.energy_status ?? '—' }}</span></td>
            <td><button class="btn-delete" @click="deleteSession(s.id)">✕</button></td>
          </tr>
          <tr v-if="filteredSessions.length === 0">
            <td colspan="6" class="empty">Aucune session ne correspond aux filtres.</td>
          </tr>
        </tbody>
      </table>
    </div>

    </template>

    <!-- ══ TAB : UTILISATEURS ══ -->
    <template v-if="activeTab === 'utilisateurs'">
    <div class="section">
      <h2>Utilisateurs</h2>
      <table>
        <thead><tr><th>Email</th><th>Rôle</th><th>Inscription</th></tr></thead>
        <tbody>
          <tr v-for="u in data.users" :key="u.id">
            <td>{{ u.email }}</td>
            <td><span :class="['role', u.role]">{{ u.role }}</span></td>
            <td>{{ u.created_at?.slice(0, 10) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    </template>

    <!-- ══ TAB : PROVIDERS ══ -->
    <template v-if="activeTab === 'providers'">
    <div class="section">
      <h2>Coefficients de conversion</h2>
      <table>
        <thead><tr><th>Provider</th><th>Modèle</th><th>kWh/token</th><th>CO₂ std</th><th>CO₂ eth</th><th>Action</th></tr></thead>
        <tbody>
          <tr v-for="f in data.factors" :key="`${f.provider}-${f.model}`">
            <template v-if="editingFactor?.provider === f.provider && editingFactor?.model === f.model">
              <td>{{ f.provider }}</td>
              <td>{{ f.model }}</td>
              <td><input v-model.number="editForm.kwh" class="edit-input" step="any" type="number" /></td>
              <td><input v-model.number="editForm.co2" class="edit-input" step="any" type="number" /></td>
              <td><input v-model.number="editForm.eth" class="edit-input" step="any" type="number" /></td>
              <td class="edit-actions">
                <button class="btn-small btn-ok" @click="saveEdit">✓</button>
                <button class="btn-small btn-cancel" @click="editingFactor = null">✕</button>
              </td>
            </template>
            <template v-else>
              <td>{{ f.provider }}</td>
              <td>{{ f.model }}</td>
              <td>{{ f.kwh_per_token }}</td>
              <td>{{ f.co2_per_kwh }}</td>
              <td>{{ f.co2_per_kwh_ethical }}</td>
              <td><button class="btn-small" @click="openEdit(f)">Modifier</button></td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    </template>

  </div>
  <p v-else class="loading">Chargement...</p>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Bar, Line } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement,
  LineElement, PointElement, Tooltip, Legend, Filler,
} from 'chart.js'
import api from '../../api/index.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Tooltip, Legend, Filler)

const data           = ref(null)
const activeTab      = ref('dashboard')
const filterEmail    = ref('')
const filterProvider = ref('')
const filterStatus   = ref('')
const editingFactor  = ref(null)
const editForm       = ref({ kwh: 0, co2: 0, eth: 0 })

const tabs = [
  { id: 'dashboard',    label: 'Dashboard' },
  { id: 'sessions',     label: 'Sessions' },
  { id: 'utilisateurs', label: 'Utilisateurs' },
  { id: 'providers',    label: 'Providers' },
]

const GRID = '#1e2a3a'
const TICK = '#64748b'
const baseOpts = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }

// Santé plateforme
const lineData = computed(() => ({
  labels: data.value?.chart.labels ?? [],
  datasets: [
    { label: 'Wh',    data: (data.value?.chart.kwh ?? []).map(v => +(v * 1000).toFixed(4)), borderColor: '#ff6b35', backgroundColor: 'rgba(255,107,53,0.10)', fill: true, tension: 0.4, pointRadius: 2 },
    { label: 'g CO₂', data: (data.value?.chart.co2 ?? []).map(v => +(v * 1000).toFixed(4)), borderColor: '#00d4aa', backgroundColor: 'rgba(0,212,170,0.08)', fill: true, tension: 0.4, pointRadius: 2 },
  ],
}))
const lineOpts = { ...baseOpts,
  plugins: { legend: { display: true, position: 'top', labels: { color: TICK, font: { size: 10 }, boxWidth: 10 } } },
  scales: {
    x: { ticks: { color: TICK, font: { size: 9 } }, grid: { color: GRID } },
    y: { ticks: { color: TICK, font: { size: 9 } }, grid: { color: GRID } },
  },
}

const providerBarData = computed(() => ({
  labels: data.value?.by_provider.labels ?? [],
  datasets: [{ data: data.value?.by_provider.co2 ?? [], backgroundColor: '#3b82f6', borderRadius: 4 }],
}))
const providerBarOpts = { ...baseOpts, indexAxis: 'y', scales: {
  x: { ticks: { color: TICK, font: { size: 10 } }, grid: { color: GRID } },
  y: { ticks: { color: TICK, font: { size: 10 } }, grid: { display: false } },
}}

// Qui consomme
const topUsersKwhData = computed(() => ({
  labels: (data.value?.top_users ?? []).map(u => u.email.split('@')[0]),
  datasets: [{ data: (data.value?.top_users ?? []).map(u => u.kwh), backgroundColor: '#a78bfa', borderRadius: 4 }],
}))
const topUsersSessionsData = computed(() => ({
  labels: (data.value?.top_users ?? []).map(u => u.email.split('@')[0]),
  datasets: [{ data: (data.value?.top_users ?? []).map(u => u.sessions), backgroundColor: '#22c55e', borderRadius: 4 }],
}))
const topUsersOpts = { ...baseOpts, scales: {
  x: { ticks: { color: TICK, font: { size: 10 } }, grid: { color: GRID } },
  y: { ticks: { color: TICK, font: { size: 10 } }, grid: { display: false } },
}}

// Filtres
const providers = computed(() => {
  if (!data.value) return []
  return [...new Set(data.value.sessions.map(s => s.provider))].sort()
})
const filteredSessions = computed(() => {
  if (!data.value) return []
  return data.value.sessions.filter(s => {
    if (filterEmail.value    && !s.email.toLowerCase().includes(filterEmail.value.toLowerCase())) return false
    if (filterProvider.value && s.provider !== filterProvider.value) return false
    if (filterStatus.value   && s.energy_status !== filterStatus.value) return false
    return true
  })
})
function resetFilters() { filterEmail.value = ''; filterProvider.value = ''; filterStatus.value = '' }

async function load() {
  const { data: d } = await api.get('/admin/dashboard')
  data.value = d
}
async function deleteSession(id) {
  if (!confirm(`Supprimer la session S-${String(id).padStart(3, '0')} ?`)) return
  await api.delete(`/admin/sessions/${id}`)
  await load()
}
function openEdit(factor) {
  editingFactor.value = factor
  editForm.value = { kwh: factor.kwh_per_token, co2: factor.co2_per_kwh, eth: factor.co2_per_kwh_ethical }
}
async function saveEdit() {
  const f = editingFactor.value
  await api.put(`/admin/factors/${f.provider}/${f.model}`, {
    kwh_per_token: editForm.value.kwh,
    co2_per_kwh: editForm.value.co2,
    co2_per_kwh_ethical: editForm.value.eth,
  })
  editingFactor.value = null
  await load()
}
onMounted(load)
</script>

<style scoped>
.admin-tabs {
  display: flex; gap: 4px; margin-bottom: var(--s-8);
  border-bottom: 1px solid var(--border); padding-bottom: 0;
}
.tab-btn {
  background: none; border: none; cursor: pointer;
  padding: 10px 20px; font-size: var(--t-base); font-weight: var(--fw-medium);
  color: var(--fg-dim); border-bottom: 2px solid transparent;
  margin-bottom: -1px; transition: color var(--t-fast), border-color var(--t-fast);
}
.tab-btn:hover  { color: var(--fg-muted); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: var(--fw-semibold); }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: var(--s-4); margin-bottom: var(--s-10); }
.kpi-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl); padding: var(--s-5) var(--s-6); }
.kpi-card p    { font-size: var(--t-sm); color: var(--fg-dim); margin-bottom: var(--s-2); }
.kpi-card span { font-size: 1.4rem; font-weight: var(--fw-bold); color: var(--accent); }
.kpi-card span.top { font-size: var(--t-md); color: var(--warn); }

.section-title { font-size: var(--t-xs); color: var(--fg-dim); text-transform: uppercase; letter-spacing: var(--tracking-caps); margin-bottom: var(--s-4); padding-bottom: var(--s-2); border-bottom: 1px solid var(--border); }
.charts-row { display: grid; grid-template-columns: 2fr 1fr; gap: var(--s-4); margin-bottom: var(--s-10); }
.charts-row + .charts-row { grid-template-columns: 1fr 1fr; }
@media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }
.chart-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl); padding: var(--s-5); }
.chart-card h3 { font-size: var(--t-xs); color: var(--fg-dim); text-transform: uppercase; letter-spacing: var(--tracking-caps); margin-bottom: var(--s-3); }
.chart-card canvas { height: 200px !important; }

.section { margin-bottom: var(--s-10); }
.section-header { display: flex; align-items: center; flex-wrap: wrap; gap: var(--s-3); margin-bottom: var(--s-4); }
.section-header h2, .section > h2 { font-size: var(--t-lg); color: var(--fg-muted); margin-bottom: var(--s-4); }
.count { font-size: var(--t-base); color: var(--fg-dim); font-weight: var(--fw-regular); }
.filters { display: flex; gap: var(--s-2); flex-wrap: wrap; margin-left: auto; }
.filter-input, .filter-select { background: var(--bg-surface); border: 1px solid var(--border); color: var(--fg-2); padding: 5px 10px; border-radius: var(--r-md); font-size: var(--t-sm); }
.filter-input { width: 180px; }
.filter-input::placeholder { color: var(--fg-dim); }
.btn-reset { background: none; border: 1px solid var(--fg-dim); color: var(--fg-muted); padding: 5px 10px; border-radius: var(--r-md); cursor: pointer; font-size: var(--t-xs); }
.btn-reset:hover { border-color: var(--danger); color: var(--danger); }

table { width: 100%; border-collapse: collapse; font-size: var(--t-base); }
th { padding: 10px 14px; background: var(--bg-surface); color: var(--fg-dim); text-align: left; border-bottom: 1px solid var(--border); }
td { padding: 10px 14px; border-bottom: 1px solid var(--border-subtle); }
.empty { color: var(--fg-dim); font-size: var(--t-base); text-align: center; padding: 20px 0; }

.status { padding: 3px 8px; border-radius: var(--r-pill); font-size: var(--t-xs); font-weight: var(--fw-semibold); }
.status.low     { background: var(--ok-soft);      color: var(--ok); }
.status.medium  { background: var(--warn-soft);    color: var(--warn); }
.status.high    { background: var(--sources-soft); color: var(--sources); }
.status.massive { background: var(--danger-soft);  color: var(--danger); }

.role { padding: 3px 8px; border-radius: var(--r-pill); font-size: var(--t-xs); font-weight: var(--fw-semibold); }
.role.admin { background: var(--co2-avoided-soft); color: var(--co2-avoided); }
.role.user  { background: var(--accent-soft);      color: var(--accent); }

.btn-small  { background: var(--bg-surface); border: 1px solid var(--accent); color: var(--accent); padding: 4px 10px; border-radius: var(--r-sm); cursor: pointer; font-size: var(--t-xs); }
.btn-ok     { border-color: var(--ok); color: var(--ok); }
.btn-cancel { border-color: var(--danger); color: var(--danger); }
.btn-delete { background: none; border: none; color: var(--danger); cursor: pointer; font-size: 1rem; }
.edit-input { background: var(--bg-input); border: 1px solid var(--accent); color: var(--fg); padding: 3px 6px; border-radius: var(--r-sm); font-size: var(--t-xs); width: 90px; }
.edit-actions { display: flex; gap: 4px; }
.loading { color: var(--fg-dim); }
</style>
