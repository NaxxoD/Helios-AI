<template>
  <div class="page">
    <!-- En-tête -->
    <div class="page-header">
      <div class="page-header__titles">
        <h1>Historique</h1>
        <p class="page-header__sub">Vos conversations et sessions IA</p>
      </div>
    </div>

    <!-- Onglets -->
    <div class="tabs">
      <button :class="['tab', activeTab === 'conversations' && 'tab--active']" @click="activeTab = 'conversations'">Conversations</button>
      <button :class="['tab', activeTab === 'sessions' && 'tab--active']" @click="activeTab = 'sessions'">Sessions importées</button>
    </div>

    <!-- Onglet Conversations -->
    <div v-if="activeTab === 'conversations'">
      <div v-if="convLoading" class="loading-state">Chargement...</div>
      <div v-else class="table-wrap">
        <table v-if="convs.length" class="data-table">
          <thead>
            <tr class="data-table__head-row">
              <th class="data-table__th">Conversation</th>
              <th class="data-table__th">Modèle</th>
              <th class="data-table__th">Tokens</th>
              <th class="data-table__th">Coût</th>
              <th class="data-table__th">CO₂</th>
              <th class="data-table__th">Date</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in convs"
              :key="c.id"
              class="data-table__row"
              @click="$router.push(`/user/conversations/${c.id}`)"
            >
              <td class="data-table__td">
                <div class="session-cell">
                  <span class="provider-dot" :style="{ backgroundColor: providerColor(c.provider) }"></span>
                  <span class="session-cell__name">{{ c.title || 'Conversation' }}</span>
                </div>
              </td>
              <td class="data-table__td data-table__td--muted">{{ c.model || '—' }}</td>
              <td class="data-table__td data-table__td--mono">{{ c.tokens_total ? c.tokens_total.toLocaleString() : '—' }}</td>
              <td class="data-table__td data-table__td--mono">{{ formatCost(c.cost_usd) }}</td>
              <td class="data-table__td data-table__td--mono">{{ c.co2_g != null ? c.co2_g.toFixed(2) + ' g' : '—' }}</td>
              <td class="data-table__td data-table__td--muted">{{ formatDate(c.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="table-empty">Aucune conversation enregistrée.</p>
      </div>
    </div>

    <!-- Onglet Sessions importées -->
    <div v-else class="sessions-tab">
      <div class="sessions-toolbar">
        <button class="btn-export" @click="exportCsv">⬇ Exporter CSV</button>
      </div>

    <div v-if="loading" class="loading-state">Chargement...</div>

    <template v-else>
      <!-- KPI cards -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <span class="kpi-card__label">Total sessions</span>
          <div class="kpi-card__value">{{ filteredSessions.length }}</div>
        </div>
        <div class="kpi-card">
          <span class="kpi-card__label">Énergie (filtrée)</span>
          <div class="kpi-card__value">{{ totalWh }} Wh</div>
        </div>
        <div class="kpi-card">
          <span class="kpi-card__label">CO₂ (filtré)</span>
          <div class="kpi-card__value">{{ totalCo2 }} g</div>
        </div>
      </div>

      <!-- Barre de filtres -->
      <div class="filters-bar">
        <input
          v-model="searchQuery"
          class="filter-input"
          type="search"
          placeholder="Rechercher une session…"
        />
        <select v-model="filterProvider" class="filter-select">
          <option value="">Tous les providers</option>
          <option v-for="p in uniqueProviders" :key="p" :value="p">{{ p }}</option>
        </select>
        <span class="filter-count">{{ filteredSessions.length }} / {{ sessions.length }}</span>
      </div>

      <!-- Table -->
      <div class="table-wrap">
        <table v-if="filteredSessions.length" class="data-table">
          <thead>
            <tr class="data-table__head-row">
              <th class="data-table__th">Session</th>
              <th class="data-table__th">Modèle</th>
              <th class="data-table__th">Énergie</th>
              <th class="data-table__th">CO₂</th>
              <th class="data-table__th">Date</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="s in filteredSessions"
              :key="s.id"
              class="data-table__row"
              @click="$router.push(`/user/sessions/${s.id}`)"
            >
              <td class="data-table__td">
                <div class="session-cell">
                  <span
                    class="provider-dot"
                    :style="{ backgroundColor: providerColor(s.provider) }"
                  ></span>
                  <span class="session-cell__name">{{ s.provider }} · {{ s.name || 'Session importée' }}</span>
                </div>
              </td>
              <td class="data-table__td data-table__td--muted">{{ s.model || '—' }}</td>
              <td class="data-table__td data-table__td--mono">
                {{ s.total_kwh ? (s.total_kwh * 1000).toFixed(2) + ' Wh' : '—' }}
              </td>
              <td class="data-table__td data-table__td--mono">
                {{ s.co2_standard ? (s.co2_standard * 1000).toFixed(3) + ' g' : '—' }}
              </td>
              <td class="data-table__td data-table__td--muted">{{ formatDate(s.created_at) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="table-empty">Aucune session enregistrée.</p>
      </div>
    </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/index.js'

const PER_PAGE = 15

const sessions = ref([])
const loading  = ref(true)
const page     = ref(1)
const meta     = ref({ total: 0, pages: 1, has_next: false, has_prev: false })

const searchQuery    = ref('')
const filterProvider = ref('')

const activeTab   = ref('conversations')
const convs       = ref([])
const convLoading = ref(true)

function formatCost(usd) {
  if (usd == null || usd === 0) return '—'
  if (usd < 0.01) return (usd * 1000).toFixed(2) + ' m$'
  return '$' + usd.toFixed(4)
}

const COLORS = {
  OpenAI:    '#3b82f6',
  Anthropic: '#a78bfa',
  Google:    '#f97316',
  Meta:      '#ef4444',
  Mistral:   '#8b5cf6',
  default:   '#64748b',
}

function providerColor(p) { return COLORS[p] || COLORS.default }

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

const uniqueProviders = computed(() => {
  const set = new Set(sessions.value.map(s => s.provider).filter(Boolean))
  return [...set].sort()
})

const filteredSessions = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return sessions.value.filter(s => {
    const matchSearch = !q
      || (s.name  && s.name.toLowerCase().includes(q))
      || (s.model && s.model.toLowerCase().includes(q))
    const matchProvider = !filterProvider.value || s.provider === filterProvider.value
    return matchSearch && matchProvider
  })
})

const totalWh = computed(() =>
  filteredSessions.value.reduce((acc, s) => acc + (s.total_kwh || 0), 0).toFixed(2)
)
const totalCo2 = computed(() =>
  filteredSessions.value.reduce((acc, s) => acc + (s.co2_standard || 0), 0).toFixed(3)
)

async function fetchSessions() {
  loading.value = true
  try {
    const { data } = await api.get('/sessions', { params: { page: page.value, per_page: PER_PAGE } })
    sessions.value = data.items || data
    meta.value = {
      total:    data.total    ?? sessions.value.length,
      pages:    data.pages    ?? 1,
      has_next: data.has_next ?? false,
      has_prev: data.has_prev ?? false,
    }
  } finally {
    loading.value = false
  }
}

async function exportCsv() {
  const { data } = await api.get('/export/csv', { responseType: 'blob' })
  const url = URL.createObjectURL(new Blob([data], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = 'helios_sessions.csv'
  a.click()
  URL.revokeObjectURL(url)
}

async function fetchConversations() {
  convLoading.value = true
  try {
    const { data } = await api.get('/conversations')
    convs.value = data || []
  } finally {
    convLoading.value = false
  }
}

onMounted(() => { fetchSessions(); fetchConversations() })
</script>

<style scoped>
/* ── Layout ─────────────────────────────────────────────────────── */
.page {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--s-10) var(--s-6);
  background: var(--bg-base);
  min-height: 100%;
}

/* ── Header ─────────────────────────────────────────────────────── */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--s-4);
  margin-bottom: var(--s-6);
}

.page-header__titles h1 {
  font-size: var(--t-xl);
  font-weight: var(--fw-semibold);
  color: var(--fg);
  margin: 0;
  line-height: var(--lh-snug);
}

.page-header__sub {
  font-size: var(--t-sm);
  color: var(--fg-muted);
  margin-top: var(--s-1);
}

.btn-export {
  flex-shrink: 0;
  font-size: var(--t-sm);
  font-weight: var(--fw-medium);
  color: var(--fg-muted);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: var(--s-2) var(--s-4);
  cursor: pointer;
  transition: color var(--t-fast) var(--ease-out),
              border-color var(--t-fast) var(--ease-out),
              background var(--t-fast) var(--ease-out);
}

.btn-export:hover {
  color: var(--fg);
  border-color: var(--border-strong);
  background: var(--bg-hover);
}

/* ── Onglets ─────────────────────────────────────────────────────── */
.tabs {
  display: flex;
  gap: var(--s-1);
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--s-5);
}

.tab {
  font-size: var(--t-sm);
  font-weight: var(--fw-medium);
  color: var(--fg-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: var(--s-3) var(--s-4);
  margin-bottom: -1px;
  cursor: pointer;
  transition: color var(--t-fast) var(--ease-out),
              border-color var(--t-fast) var(--ease-out);
}

.tab:hover { color: var(--fg); }

.tab--active {
  color: var(--fg);
  border-bottom-color: var(--accent);
}

.sessions-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--s-4);
}

/* ── Loading ─────────────────────────────────────────────────────── */
.loading-state {
  font-size: var(--t-sm);
  color: var(--fg-muted);
  padding: var(--s-8) 0;
}

/* ── KPI grid ────────────────────────────────────────────────────── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--s-3);
  margin-bottom: var(--s-5);
}

.kpi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  padding: var(--s-5) var(--s-5) var(--s-4);
  box-shadow: var(--shadow-2);
  display: flex;
  flex-direction: column;
  gap: var(--s-1);
}

.kpi-card__label {
  font-size: var(--t-xs);
  font-weight: var(--fw-medium);
  color: var(--fg-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
}

.kpi-card__value {
  font-family: var(--font-mono);
  font-size: var(--t-2xl);
  font-weight: var(--fw-semibold);
  color: var(--fg);
  line-height: var(--lh-tight);
  letter-spacing: var(--tracking-tight);
}

/* ── Filters bar ─────────────────────────────────────────────────── */
.filters-bar {
  display: flex;
  align-items: center;
  gap: var(--s-3);
  margin-bottom: var(--s-4);
}

.filter-input,
.filter-select {
  font-family: var(--font-sans);
  font-size: var(--t-sm);
  color: var(--fg-2);
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: var(--r-lg);
  padding: var(--s-2) var(--s-3);
  transition: border-color var(--t-fast) var(--ease-out),
              box-shadow var(--t-fast) var(--ease-out);
  outline: none;
}

.filter-input {
  flex: 1;
  min-width: 0;
}

.filter-select {
  flex-shrink: 0;
  cursor: pointer;
  background-color: var(--bg-input);
}

.filter-input::placeholder {
  color: var(--fg-dim);
}

.filter-input:focus,
.filter-select:focus {
  border-color: var(--border-strong);
  box-shadow: var(--shadow-focus);
}

.filter-count {
  flex-shrink: 0;
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: var(--t-sm);
  color: var(--fg-muted);
  white-space: nowrap;
}

/* ── Table wrapper ───────────────────────────────────────────────── */
.table-wrap {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--r-xl);
  overflow: hidden;
}

/* ── Table ───────────────────────────────────────────────────────── */
.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table__head-row {
  background: var(--bg-surface-2);
  border-bottom: 1px solid var(--border);
}

.data-table__th {
  text-align: left;
  font-size: var(--t-xs);
  font-weight: var(--fw-medium);
  color: var(--fg-muted);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  padding: var(--s-3) var(--s-5);
  white-space: nowrap;
}

.data-table__row {
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background var(--t-fast) var(--ease-out);
}

.data-table__row:last-child {
  border-bottom: none;
}

.data-table__row:hover {
  background: var(--bg-hover);
}

.data-table__td {
  padding: var(--s-4) var(--s-5);
  font-size: var(--t-sm);
  color: var(--fg);
  vertical-align: middle;
}

.data-table__td--muted {
  color: var(--fg-muted);
}

.data-table__td--mono {
  font-family: var(--font-mono);
  font-weight: var(--fw-medium);
}

/* ── Session cell ────────────────────────────────────────────────── */
.session-cell {
  display: flex;
  align-items: center;
  gap: var(--s-2);
}

.provider-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.session-cell__name {
  font-size: var(--t-sm);
  font-weight: var(--fw-medium);
  color: var(--fg);
}

/* ── Empty state ─────────────────────────────────────────────────── */
.table-empty {
  text-align: center;
  font-size: var(--t-sm);
  color: var(--fg-muted);
  padding: var(--s-10) var(--s-6);
  margin: 0;
}
</style>
