<template>
  <div class="page">
    <div class="page-header">
      <button class="back-btn" @click="$router.push('/historique')">← Retour</button>
      <div class="header-row">
        <div>
          <h1>{{ conv?.title || 'Conversation' }}</h1>
          <p class="sub">{{ conv?.provider }}<template v-if="conv?.model"> · {{ conv.model }}</template></p>
        </div>
        <button v-if="exchanges.length" class="btn-export" @click="exportMarkdown">⬇ Exporter (Markdown)</button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">Chargement…</div>
    <p v-else-if="!exchanges.length" class="table-empty">Conversation vide ou contenu non disponible.</p>

    <template v-else>
      <!-- Récap -->
      <div class="kpi-grid">
        <div class="kpi-card">
          <span class="kpi-card__label">Échanges</span>
          <div class="kpi-card__value">{{ nbUser }}</div>
        </div>
        <div class="kpi-card">
          <span class="kpi-card__label">Tokens</span>
          <div class="kpi-card__value">{{ totalTokens.toLocaleString() }}</div>
        </div>
        <div class="kpi-card">
          <span class="kpi-card__label">Coût</span>
          <div class="kpi-card__value">{{ formatCost(totalCost) }}</div>
        </div>
        <div class="kpi-card">
          <span class="kpi-card__label">CO₂</span>
          <div class="kpi-card__value">{{ totalCo2.toFixed(2) }} g</div>
        </div>
      </div>

      <!-- Échanges -->
      <div class="thread">
        <div
          v-for="(m, i) in exchanges"
          :key="i"
          :class="['msg', m.role === 'user' ? 'msg--user' : 'msg--assistant']"
        >
          <div class="msg-role">{{ m.role === 'user' ? 'Vous' : 'Assistant' }}</div>
          <div class="msg-content">{{ m.content }}</div>
          <div class="msg-meta">
            <template v-if="m.role === 'user'">
              <span v-if="m.optimized" class="meta-pill meta-pill--ok">✦ optimisé −{{ m.savedPct }}%</span>
              <span v-if="m.pertinenceScore != null" class="meta-item">pertinence {{ m.pertinenceScore }}/100</span>
            </template>
            <template v-else>
              <span class="meta-item">{{ m.routed_model || conv?.model || '—' }}</span>
              <span v-if="m.input_tokens != null" class="meta-item">{{ m.input_tokens }}→{{ m.output_tokens }} tok</span>
              <span v-if="m.cost_usd != null" class="meta-item">{{ formatCost(m.cost_usd) }}</span>
              <span v-if="co2Of(m) != null" class="meta-item">{{ co2Of(m).toFixed(3) }} g CO₂</span>
            </template>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/index.js'

const route = useRoute()
const conv     = ref(null)
const messages = ref([])
const loading  = ref(true)

function co2Of(m) {
  const kg = m.impact?.co2_standard
  return kg != null ? kg * 1000 : null
}

function formatCost(usd) {
  if (usd == null || usd === 0) return '—'
  if (usd < 0.01) return (usd * 1000).toFixed(2) + ' m$'
  return '$' + usd.toFixed(4)
}

// Échanges affichables : on ignore les messages d'erreur, on garde le reste (dont _compacted)
const exchanges = computed(() => messages.value.filter(m => !m.isError))
const nbUser = computed(() => exchanges.value.filter(m => m.role === 'user').length)
const totalTokens = computed(() =>
  exchanges.value.reduce((a, m) => a + (m.input_tokens || 0) + (m.output_tokens || 0), 0)
)
const totalCost = computed(() =>
  exchanges.value.reduce((a, m) => a + (m.cost_usd || 0), 0)
)
const totalCo2 = computed(() =>
  exchanges.value.reduce((a, m) => a + (co2Of(m) || 0), 0)
)

function slug(s) {
  return (s || 'conversation').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'conversation'
}

function exportMarkdown() {
  const title = conv.value?.title || 'Conversation'
  const date = new Date().toISOString().slice(0, 10)
  const lines = [
    `# ${title}`,
    '',
    `> Exporté le ${date} · Helios AI`,
    `> Modèle : ${conv.value?.provider || '—'}${conv.value?.model ? ' / ' + conv.value.model : ''}`,
    `> ${nbUser.value} échanges · ${totalTokens.value.toLocaleString()} tokens · ${formatCost(totalCost.value)} · ${totalCo2.value.toFixed(2)} g CO₂`,
    '',
    '---',
    '',
  ]
  for (const m of exchanges.value) {
    lines.push(m.role === 'user' ? '**Vous**' : '**Assistant**', '', m.content || '', '')
    if (m.role === 'user' && m.optimized) {
      lines.push(`*✦ Prompt optimisé −${m.savedPct}%${m.pertinenceScore != null ? ' · pertinence ' + m.pertinenceScore + '/100' : ''}*`, '')
    } else if (m.role === 'assistant') {
      const meta = [m.routed_model || conv.value?.model]
      if (m.input_tokens != null) meta.push(`${m.input_tokens}→${m.output_tokens} tokens`)
      if (m.cost_usd != null) meta.push(formatCost(m.cost_usd))
      if (co2Of(m) != null) meta.push(`${co2Of(m).toFixed(3)} g CO₂`)
      lines.push(`*🤖 ${meta.filter(Boolean).join(' · ')}*`, '')
    }
    lines.push('---', '')
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `helios_${slug(title)}_${date}.md`
  a.click()
  URL.revokeObjectURL(a.href)
}

onMounted(async () => {
  try {
    const { data } = await api.get(`/conversations/${route.params.uuid}/messages`)
    conv.value = data
    messages.value = data.messages || []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.page { max-width: 860px; margin: 0 auto; padding: var(--s-10) var(--s-6); min-height: 100%; }

.page-header { margin-bottom: var(--s-6); }
.back-btn {
  background: none; border: none; color: var(--fg-muted); cursor: pointer;
  font-size: var(--t-sm); padding: 0 0 var(--s-3);
}
.back-btn:hover { color: var(--fg); }
.header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--s-4); }
.page-header h1 { font-size: var(--t-xl); font-weight: var(--fw-semibold); color: var(--fg); margin: 0; }
.sub { font-size: var(--t-sm); color: var(--fg-muted); margin-top: var(--s-1); }

.btn-export {
  flex-shrink: 0; font-size: var(--t-sm); font-weight: var(--fw-medium); color: var(--fg-muted);
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-lg);
  padding: var(--s-2) var(--s-4); cursor: pointer;
}
.btn-export:hover { color: var(--fg); border-color: var(--border-strong); background: var(--bg-hover); }

.loading-state { font-size: var(--t-sm); color: var(--fg-muted); padding: var(--s-8) 0; }
.table-empty { text-align: center; font-size: var(--t-sm); color: var(--fg-muted); padding: var(--s-10) 0; }

.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--s-3); margin-bottom: var(--s-6); }
@media (max-width: 640px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
.kpi-card {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl);
  padding: var(--s-4) var(--s-5); display: flex; flex-direction: column; gap: var(--s-1);
}
.kpi-card__label { font-size: var(--t-xs); font-weight: var(--fw-medium); color: var(--fg-muted); text-transform: uppercase; letter-spacing: var(--tracking-caps); }
.kpi-card__value { font-family: var(--font-mono); font-size: var(--t-xl); font-weight: var(--fw-semibold); color: var(--fg); }

.thread { display: flex; flex-direction: column; gap: var(--s-3); }
.msg {
  background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-xl);
  padding: var(--s-4) var(--s-5);
}
.msg--user { border-left: 2px solid var(--border-strong); }
.msg--assistant { border-left: 2px solid var(--accent); }
.msg-role { font-size: var(--t-xs); font-weight: var(--fw-semibold); color: var(--fg-muted); text-transform: uppercase; letter-spacing: var(--tracking-caps); margin-bottom: var(--s-2); }
.msg-content { font-size: var(--t-sm); color: var(--fg-2); white-space: pre-wrap; line-height: var(--lh-normal); }
.msg-meta { display: flex; flex-wrap: wrap; gap: var(--s-2); margin-top: var(--s-3); }
.meta-item { font-family: var(--font-mono); font-size: var(--t-xs); color: var(--fg-dim); }
.meta-pill { font-size: var(--t-xs); font-weight: var(--fw-semibold); padding: 2px 8px; border-radius: var(--r-pill); }
.meta-pill--ok { background: var(--accent-soft); color: var(--accent); }
</style>
