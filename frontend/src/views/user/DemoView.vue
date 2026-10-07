<template>
  <div class="demo-outer">

    <!-- ── Header ── -->
    <header class="demo-head">
      <div class="demo-head-left">
        <div class="demo-title-row">
          <div class="demo-title">Helios <span>AI</span> — démo</div>
          <div class="demo-acts">
            <button v-for="a in ACTS" :key="a.key" class="act-tab" :class="{ on: act === a.key }"
                    @click="loadAct(a.key)">{{ a.label }}</button>
          </div>
        </div>
        <div class="demo-focus" v-if="currentAct">{{ currentAct.focus }}</div>
        <div class="demo-subject" v-if="meta">
          <span class="demo-subject-label">conv réelle (comparia FR) ·</span>
          « {{ truncate(meta.first_message, 70) }} »
        </div>
      </div>
      <div class="demo-controls">
        <button class="demo-btn" :class="{ playing }" @click="toggle" :disabled="!data">
          {{ !started ? '▶ Lancer' : playing ? '⏸ Pause' : done ? '↺ Rejouer' : '▶ Reprendre' }}
        </button>
        <label class="demo-speed">
          vitesse
          <input type="range" min="0.4" max="3" step="0.2" v-model.number="speed" />
          <span>×{{ speed.toFixed(1) }}</span>
        </label>
        <div class="demo-progress" v-if="meta">
          <span class="prog-cur">T{{ Math.min(idx, meta.n_turns) }}</span><span class="prog-tot">/ {{ meta.n_turns }}</span>
        </div>
      </div>
    </header>

    <!-- ── Corps 75 / 25 ── -->
    <div class="demo-body">

      <!-- Chat (gauche, 75%) -->
      <section class="demo-chat" ref="msgsEl">
        <div v-if="!started" class="demo-hint">
          Replay accéléré d'une vraie session de <b>{{ meta ? meta.n_turns : '…' }} tours</b>.<br>
          Sans sous-agent, le contexte relu gonfle à chaque tour ; avec, il reste dégonflé
          (résumé + {{ meta ? meta.KEEP : 4 }} tours verbatim).
        </div>
        <div v-for="(m, i) in msgs" :key="i" class="msg-wrap" :class="m.role">
          <div class="bubble">
            <div class="bubble-meta">
              {{ m.role === 'user' ? 'Utilisateur' : 'Assistant' }} · T{{ m.t }}
              <span v-if="m.role === 'assistant' && m.route" class="route-chip"
                    :style="{ color: modelColor(m.route.model), borderColor: modelColor(m.route.model) }">
                ⟐ routé → {{ m.route.model }}<span v-if="m.route.effort"> · {{ m.route.effort }}</span>
              </span>
            </div>
            <div class="bubble-content">{{ m.content }}</div>
          </div>
        </div>
        <div v-if="thinking" class="msg-wrap assistant">
          <div class="bubble thinking">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            <span v-if="compactingNow" class="compact-note">↯ compaction mémoire…</span>
          </div>
        </div>
      </section>

      <!-- Monitoring (droite, 25%) -->
      <aside class="demo-side">
        <div class="side-route" v-if="started">
          <span class="sr-lbl">modèle routé →</span>
          <span class="sr-model" :style="{ color: modelColor(curModel) }">{{ curModel || '—' }}</span>
          <span class="sr-effort" v-if="curEffort">· effort {{ curEffort }}</span>
        </div>
        <div class="side-counters">
          <div class="sc-card sans">
            <div class="sc-label">sans agent</div>
            <div class="sc-val">{{ fmtTk(curSans) }}</div>
          </div>
          <div class="sc-card avec" :class="{ pulse: compactionPulse }">
            <div class="sc-label">avec agent</div>
            <div class="sc-val">{{ fmtTk(curAvec) }}</div>
          </div>
        </div>
        <div class="side-saving" v-if="started && cumSans > 0">
          coût input : <b>−{{ savingPct }}%</b> · {{ fmtCost(cumAvec * PRICE_IN) }} <span class="ss-vs">vs {{ fmtCost(cumSans * PRICE_IN) }}</span>
        </div>

        <!-- Graphe différentiel (se trace tour par tour) -->
        <div class="side-chart">
          <svg :viewBox="`0 0 ${CW} ${CH}`" preserveAspectRatio="none" class="chart-svg">
            <line v-for="g in 3" :key="g" :x1="0" :x2="CW" :y1="CH*g/4" :y2="CH*g/4" class="grid" />
            <polygon :points="areaSans" class="area-sans" />
            <polygon :points="areaAvec" class="area-avec" />
            <polyline :points="lineSans" class="line-sans" />
            <polyline :points="lineAvec" class="line-avec" />
            <circle v-if="head" :cx="head.xs" :cy="head.ys" r="6" class="dot-sans" />
            <circle v-if="head" :cx="head.xa" :cy="head.ya" r="6" class="dot-avec" />
          </svg>
          <div class="chart-legend"><i class="sw sans"></i>sans &nbsp;<i class="sw avec"></i>avec · couche B sur {{ meta ? meta.n_turns : '' }} tours</div>
        </div>

        <!-- Journal tour-par-tour (défile en auto) -->
        <div class="side-log-head">monitoring · tour par tour</div>
        <div class="side-log" ref="logEl">
          <div v-for="row in logRows" :key="row.t" class="log-row" :class="{ cmp: row.cmp }">
            <span class="lr-t">T{{ String(row.t).padStart(2,'0') }}</span>
            <span class="lr-sans">{{ fmtTk(row.sans) }}</span>
            <span class="lr-arrow">→</span>
            <span class="lr-avec">{{ fmtTk(row.avec) }}</span>
            <span class="lr-eco">−{{ row.eco }}%</span>
            <span v-if="row.cmp" class="lr-tag">↯</span>
          </div>
        </div>

      </aside>
    </div>

    <!-- ── Popup résultat (gros, lisible rétroprojecteur) ── -->
    <transition name="fade">
      <div class="final-modal" v-if="done && totals && !modalClosed" @click="modalClosed = true">
        <div class="fm-card" @click.stop>
          <div class="fm-title">Helios · {{ meta.n_turns }} tours · sous-agent mémoire</div>
          <div class="fm-row">
            <span class="fm-lbl">coût input <small>(contexte relu = Couche B)</small></span>
            <span class="fm-vals">{{ fmtCost(totals.cost_input_no) }} <i>→</i> {{ fmtCost(totals.cost_input_with) }}</span>
            <span class="fm-pct">−{{ totals.saving_input_pct.toFixed(0) }}%</span>
          </div>
          <div class="fm-row net">
            <span class="fm-lbl">coût net <small>(tout compris)</small></span>
            <span class="fm-vals">{{ fmtCost(totals.cost_no_agent) }} <i>→</i> {{ fmtCost(totals.cost_net) }}</span>
            <span class="fm-pct">−{{ totals.saving_net_pct.toFixed(0) }}%</span>
          </div>
          <div class="fm-breakdown">
            net avec = input réduit <b>{{ fmtCost(totals.cost_input_with) }}</b>
            <i>+</i> sortie <b>{{ fmtCost(totals.cost_output) }}</b> <small>(inchangée)</small>
            <i>+</i> sous-agent <b>{{ fmtCost(totals.cost_subagent) }}</b>
          </div>
          <div class="fm-note">
            Le sous-agent ne compresse que <b>l'input</b> (la relecture du contexte) → <b>−{{ totals.saving_input_pct.toFixed(0) }}%</b>.
            Le <b>net</b> baisse moins (<b>−{{ totals.saving_net_pct.toFixed(0) }}%</b>) car la <b>sortie</b>
            (réponses identiques avec/sans) ne se compresse pas, et le <b>sous-agent</b> a son propre coût.
          </div>
          <div class="fm-caveat">
            Coûts simulés sur une vraie conversation (compression {{ Math.round(meta.COMPRESS*100) }}%).
            À l'échelle du corpus : <b>−52% sur les sessions longues</b>.
          </div>
          <div class="fm-actions">
            <button class="fm-btn ghost" @click="modalClosed = true">✕ Fermer</button>
            <button class="fm-btn" @click="replay">↺ Rejouer</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

const PRICE_IN = 3.0 / 1_000_000
const CW = 1000, CH = 320, PAD = 12

const data = ref(null)
const msgs = ref([])
const idx = ref(0)
const playing = ref(false)
const started = ref(false)
const done = ref(false)
const thinking = ref(false)
const compactingNow = ref(false)
const compactionPulse = ref(false)
const speed = ref(1.4)
const cumSans = ref(0)
const cumAvec = ref(0)
const curSans = ref(0)
const curAvec = ref(0)
const curModel = ref(null)
const curEffort = ref(null)
const modalClosed = ref(false)
const msgsEl = ref(null)
const logEl = ref(null)

const MODEL_COLOR = { Haiku: '#60a5fa', Sonnet: '#34d399', Opus: '#c084fc' }
function modelColor(m) { return MODEL_COLOR[m] || 'var(--fg-muted)' }

// Démo à deux temps : Acte 1 routing (14t, alternance) · Acte 2 mémoire (41t, dégonflage fort)
const ACTS = [
  { key: 'routing', label: '① Routing', file: '/demo/demo_routing.json',
    focus: "Acte 1 — le routing choisit le modèle selon l'échange : Sonnet par défaut, Opus sur une question pointue, Haiku sur une simple." },
  { key: 'memoire', label: '② Mémoire', file: '/demo/demo_memoire.json',
    focus: "Acte 2 — sur une longue session (41 tours), le sous-agent dégonfle le contexte : la Couche B reste plate au lieu d'exploser." },
]
const act = ref('routing')
const currentAct = computed(() => ACTS.find(a => a.key === act.value))

let cancelled = false

const meta = computed(() => data.value?.meta)
const totals = computed(() => data.value?.totals)
const NA = computed(() => data.value?.turns_no_agent || [])
const WA = computed(() => data.value?.turns_with_agent || [])
const CONTENT = computed(() => data.value?.turns_content || [])
const maxInput = computed(() => Math.max(1, ...NA.value.map(t => t.input)))
const nTurns = computed(() => meta.value?.n_turns || NA.value.length || 1)
const savingPct = computed(() => cumSans.value ? Math.max(0, (1 - cumAvec.value / cumSans.value) * 100).toFixed(0) : 0)
// Coûts : INPUT (ce que le sous-agent réduit) vs NET total (output inclus, inchangé)
const inputSans = computed(() => (totals.value?.input_no_agent || 0) * PRICE_IN)
const inputAvec = computed(() => (totals.value?.input_with_agent || 0) * PRICE_IN)

function isCompaction(i) {
  return i > 0 && WA.value[i] && WA.value[i - 1] && WA.value[i].summary_tokens > WA.value[i - 1].summary_tokens
}

// Journal des tours déjà joués
const logRows = computed(() => {
  const out = []
  for (let i = 0; i < Math.min(idx.value, NA.value.length); i++) {
    const na = NA.value[i], wa = WA.value[i]
    out.push({ t: na.t, sans: na.input, avec: wa.input,
      eco: Math.max(0, (1 - wa.input / na.input) * 100).toFixed(0), cmp: isCompaction(i) })
  }
  return out
})

// Graphe
function xFor(t) { return PAD + (t - 1) / Math.max(1, nTurns.value - 1) * (CW - 2 * PAD) }
function yFor(v) { return CH - PAD - (v / maxInput.value) * (CH - 2 * PAD) }
function pts(arr) {
  const out = []; const upto = Math.min(idx.value, arr.length)
  for (let i = 0; i < upto; i++) out.push([xFor(arr[i].t), yFor(arr[i].input)])
  return out
}
const lineSans = computed(() => pts(NA.value).map(p => p.join(',')).join(' '))
const lineAvec = computed(() => pts(WA.value).map(p => p.join(',')).join(' '))
function area(arr) { const p = pts(arr); if (!p.length) return ''; return `${p[0][0]},${CH - PAD} ` + p.map(x => x.join(',')).join(' ') + ` ${p[p.length - 1][0]},${CH - PAD}` }
const areaSans = computed(() => area(NA.value))
const areaAvec = computed(() => area(WA.value))
const head = computed(() => {
  const i = Math.min(idx.value, NA.value.length) - 1
  if (i < 0) return null
  return { xs: xFor(NA.value[i].t), ys: yFor(NA.value[i].input), xa: xFor(WA.value[i].t), ya: yFor(WA.value[i].input) }
})

function fmtTk(n) { if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M'; if (n >= 1e3) return (n / 1e3).toFixed(1) + 'k'; return Math.round(n).toString() }
function fmtCost(c) { return '$' + c.toFixed(c < 0.01 ? 4 : 2) }
function truncate(s, n) { return s && s.length > n ? s.slice(0, n) + '…' : s }
const sleep = (ms) => new Promise(r => setTimeout(r, ms))

async function scrollDown() {
  await nextTick()
  if (msgsEl.value) msgsEl.value.scrollTop = msgsEl.value.scrollHeight
  if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
}
async function waited(ms) { await sleep(ms / speed.value); return cancelled || !playing.value }
function pulse() { compactionPulse.value = true; setTimeout(() => { compactionPulse.value = false }, 700) }

async function run() {
  while (playing.value && idx.value < NA.value.length) {
    const i = idx.value
    const na = NA.value[i], wa = WA.value[i], ct = CONTENT.value[i] || { user: '', assistant: '' }
    const cmp = isCompaction(i)

    msgs.value.push({ role: 'user', content: ct.user, t: na.t })
    await scrollDown()
    if (await waited(200)) return

    thinking.value = true; compactingNow.value = cmp
    if (await waited(cmp ? 520 : 300)) return
    thinking.value = false; compactingNow.value = false

    msgs.value.push({ role: 'assistant', content: ct.assistant, t: na.t, route: ct.route })
    cumSans.value += na.input; cumAvec.value += wa.input
    curSans.value = na.input; curAvec.value = wa.input
    curModel.value = ct.route?.model || null; curEffort.value = ct.route?.effort || null
    if (cmp) pulse()
    idx.value++
    await scrollDown()
    if (await waited(cmp ? 460 : 230)) return
  }
  if (idx.value >= NA.value.length) { playing.value = false; done.value = true }
}

function reset() {
  msgs.value = []; idx.value = 0; cumSans.value = 0; cumAvec.value = 0
  curSans.value = 0; curAvec.value = 0; curModel.value = null; curEffort.value = null
  thinking.value = false; done.value = false; modalClosed.value = false
}
function toggle() {
  if (!data.value) return
  if (playing.value) { playing.value = false; return }
  if (done.value) reset()
  started.value = true; playing.value = true; run()
}
function replay() { reset(); started.value = true; playing.value = true; run() }

async function loadAct(key) {
  playing.value = false
  cancelled = true
  act.value = key
  reset()
  started.value = false
  try { data.value = await (await fetch(currentAct.value.file)).json() }
  catch (e) { console.error('[demo] chargement échoué', e) }
  cancelled = false
}
onMounted(() => loadAct('routing'))
onUnmounted(() => { cancelled = true; playing.value = false })
</script>

<style scoped>
.demo-outer { display: flex; flex-direction: column; height: calc(100dvh - 56px);
  background: var(--bg-base); color: var(--fg); font-family: var(--font-mono); }

/* Header */
.demo-head { display: flex; align-items: center; justify-content: space-between; gap: 1.5rem;
  padding: .9rem 1.8rem; border-bottom: 1px solid var(--bg-surface); flex-wrap: wrap; flex-shrink: 0; }
.demo-title-row { display: flex; align-items: center; gap: 1.3rem; flex-wrap: wrap; }
.demo-title { font-size: 1.35rem; font-weight: 800; letter-spacing: .03em; }
.demo-title span { color: var(--accent); }
.demo-acts { display: flex; gap: .4rem; }
.act-tab { font-family: var(--font-mono); font-size: .82rem; background: var(--bg-surface); color: var(--fg-muted);
  border: 1px solid var(--bg-surface); padding: .35rem .95rem; border-radius: 7px; cursor: pointer; transition: all .15s; }
.act-tab:hover { color: var(--fg); }
.act-tab.on { background: var(--accent); color: #04130c; font-weight: 800; border-color: var(--accent); }
.demo-focus { font-size: .82rem; color: var(--accent); margin-top: .45rem; line-height: 1.5; max-width: 70ch; }
.demo-subject { font-size: .78rem; color: var(--fg-muted); margin-top: .25rem; font-style: italic; }
.demo-subject-label { color: var(--fg-dim); font-style: normal; }
.demo-controls { display: flex; align-items: center; gap: 1.3rem; }
.demo-btn { font-family: var(--font-mono); font-size: .9rem; letter-spacing: .06em; background: var(--accent);
  color: #04130c; border: none; padding: .6rem 1.6rem; border-radius: 8px; cursor: pointer; font-weight: 800; }
.demo-btn:hover { filter: brightness(1.1); } .demo-btn.playing { background: #f59e0b; }
.demo-btn:disabled { background: var(--fg-dim); opacity: .5; cursor: not-allowed; }
.demo-speed { font-size: .72rem; color: var(--fg-muted); display: flex; align-items: center; gap: .5rem; }
.demo-speed input { accent-color: var(--accent); }
.prog-cur { font-size: 1.6rem; font-weight: 800; color: var(--accent); }
.prog-tot { font-size: .85rem; color: var(--fg-dim); margin-left: .15rem; }

/* Corps 75 / 25 */
.demo-body { flex: 1; display: grid; grid-template-columns: 3fr 1fr; min-height: 0; }
.demo-chat { overflow-y: auto; padding: 1.4rem 2rem; display: flex; flex-direction: column; gap: .8rem;
  scroll-behavior: smooth; border-right: 1px solid var(--bg-surface); }
.demo-hint { color: var(--fg-dim); font-size: .95rem; line-height: 1.7; text-align: center; margin: auto; max-width: 560px; }
.demo-hint b { color: var(--accent); }
.msg-wrap { display: flex; } .msg-wrap.user { justify-content: flex-end; } .msg-wrap.assistant { justify-content: flex-start; }
.bubble { max-width: 76%; padding: .75rem 1.05rem; border-radius: 13px; font-size: .9rem; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
.msg-wrap.user .bubble { background: var(--accent); color: #04130c; border-bottom-right-radius: 4px; }
.msg-wrap.assistant .bubble { background: var(--bg-surface); color: var(--fg); border-bottom-left-radius: 4px; }
.bubble-meta { font-size: .58rem; opacity: .6; margin-bottom: .25rem; letter-spacing: .1em; text-transform: uppercase; }
.bubble.thinking { display: flex; align-items: center; gap: .35rem; }
.bubble.thinking .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--fg-muted); animation: bounce 1.2s infinite; }
.bubble.thinking .dot:nth-child(2) { animation-delay: .2s; } .bubble.thinking .dot:nth-child(3) { animation-delay: .4s; }
.compact-note { font-size: .72rem; color: var(--accent); margin-left: .5rem; }
@keyframes bounce { 0%,60%,100% { transform: translateY(0); opacity: .4; } 30% { transform: translateY(-5px); opacity: 1; } }

/* Monitoring (sidebar 25%) */
.demo-side { display: flex; flex-direction: column; min-height: 0; padding: 1rem 1rem 0; gap: .8rem; background: var(--bg-base); }
.side-counters { display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; }
.sc-card { background: var(--bg-surface); border-radius: 10px; padding: .7rem .8rem; border-top: 2px solid; transition: box-shadow .3s; }
.sc-card.sans { border-color: #f59e0b; } .sc-card.avec { border-color: var(--accent); }
.sc-card.pulse { box-shadow: 0 0 26px rgba(52,211,153,.55); }
.sc-label { font-size: .56rem; letter-spacing: .12em; text-transform: uppercase; color: var(--fg-dim); }
.sc-val { font-size: 1.7rem; font-weight: 800; line-height: 1.1; margin-top: .15rem; }
.sc-card.sans .sc-val { color: #fbbf24; } .sc-card.avec .sc-val { color: var(--accent); }
.side-saving { font-size: .74rem; color: var(--fg-muted); text-align: center; }
.side-saving b { color: var(--accent); font-size: 1.05rem; }

.side-chart { flex-shrink: 0; }
.chart-svg { width: 100%; height: 130px; display: block; }
.grid { stroke: var(--bg-surface); stroke-width: 1; }
.area-sans { fill: rgba(245,158,11,.14); } .area-avec { fill: rgba(52,211,153,.18); }
.line-sans { fill: none; stroke: #f59e0b; stroke-width: 2; vector-effect: non-scaling-stroke; }
.line-avec { fill: none; stroke: var(--accent); stroke-width: 2; vector-effect: non-scaling-stroke; }
.dot-sans { fill: #fbbf24; } .dot-avec { fill: var(--accent); }
.chart-legend { font-size: .6rem; color: var(--fg-dim); text-align: center; margin-top: .2rem; }
.sw { display: inline-block; width: 9px; height: 9px; border-radius: 2px; vertical-align: middle; margin-right: .2rem; }
.sw.sans { background: #f59e0b; } .sw.avec { background: var(--accent); }

.side-log-head { font-size: .58rem; letter-spacing: .12em; text-transform: uppercase; color: var(--fg-dim); }
.side-log { flex: 1; min-height: 60px; overflow-y: auto; scroll-behavior: smooth; display: flex; flex-direction: column; gap: 2px; }
.log-row { display: grid; grid-template-columns: 2.2rem 1fr .8rem 1fr 2.4rem .8rem; align-items: center; gap: .25rem;
  font-size: .68rem; padding: .25rem .35rem; border-radius: 5px; }
.log-row.cmp { background: rgba(52,211,153,.1); }
.lr-t { color: var(--fg-dim); } .lr-sans { color: #fbbf24; text-align: right; } .lr-arrow { color: var(--fg-dim); text-align: center; }
.lr-avec { color: var(--accent); text-align: right; } .lr-eco { color: var(--fg-muted); text-align: right; } .lr-tag { color: var(--accent); }

.route-chip { display: inline-block; margin-left: .5rem; padding: .05rem .45rem; border: 1px solid;
  border-radius: 999px; font-size: .62rem; font-weight: 700; letter-spacing: .03em; vertical-align: middle; }
.ss-vs { color: #fbbf24; }

/* indicateur modèle routé (monitoring) */
.side-route { background: var(--bg-surface); border-radius: 10px; padding: .6rem .8rem; display: flex;
  align-items: baseline; gap: .4rem; flex-wrap: wrap; }
.sr-lbl { font-size: .58rem; letter-spacing: .12em; text-transform: uppercase; color: var(--fg-dim); }
.sr-model { font-size: 1.3rem; font-weight: 800; transition: color .25s; }
.sr-effort { font-size: .66rem; color: var(--fg-muted); }

.fm-actions { display: flex; gap: 1rem; justify-content: center; margin-top: 1.7rem; }
.fm-btn.ghost { background: transparent; color: var(--fg-muted); border: 1px solid var(--fg-dim); }
.fm-btn.ghost:hover { color: var(--fg); border-color: var(--fg-muted); filter: none; }

/* Popup résultat (gros, rétroprojecteur) */
.final-modal { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,.78); backdrop-filter: blur(4px); }
.fm-card { background: var(--bg-surface); border: 1px solid var(--accent); border-radius: 18px; padding: 2.6rem 3rem;
  max-width: 920px; width: 92%; box-shadow: 0 0 90px rgba(52,211,153,.25); text-align: center; }
.fm-title { font-size: 1rem; color: var(--fg-muted); letter-spacing: .1em; text-transform: uppercase; margin-bottom: 2rem; font-family: var(--font-sans); font-weight: 500; }
.fm-row { display: flex; align-items: center; justify-content: center; gap: 2rem; margin: 1.1rem 0; flex-wrap: wrap; }
.fm-lbl { font-size: 1.1rem; color: var(--fg-muted); width: 17rem; text-align: right; }
.fm-lbl small { color: var(--fg-dim); font-size: .8rem; }
.fm-vals { font-size: 2.1rem; font-weight: 600; color: var(--fg); font-family: var(--font-sans); letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.fm-vals i { color: var(--fg-dim); font-style: normal; margin: 0 .5rem; }
.fm-pct { font-size: 1.9rem; font-weight: 700; color: var(--accent); width: 8rem; text-align: left; font-family: var(--font-sans); letter-spacing: -.02em; text-shadow: 0 0 18px rgba(52,211,153,.3); }
.fm-row.net .fm-pct { color: #fbbf24; text-shadow: none; }
.fm-breakdown { font-size: 1.05rem; color: var(--fg-muted); margin: 1.4rem auto 0; }
.fm-breakdown b { color: var(--fg); } .fm-breakdown i { color: var(--fg-dim); font-style: normal; margin: 0 .35rem; }
.fm-breakdown small { color: var(--fg-dim); font-size: .8rem; }
.fm-note { font-size: .9rem; color: var(--fg-dim); line-height: 1.65; margin: 1rem auto 0; max-width: 680px; }
.fm-note b { color: var(--fg-muted); }
.fm-caveat { font-size: .78rem; color: var(--fg-dim); line-height: 1.6; margin: 1rem auto 0; max-width: 700px;
  border-top: 1px solid var(--bg-base); padding-top: .9rem; }
.fm-caveat b { color: var(--fg-muted); }
.fm-btn { background: var(--accent); color: #04130c; border: none; padding: .75rem 2.4rem;
  border-radius: 8px; font-family: var(--font-mono); font-weight: 800; font-size: 1.05rem; cursor: pointer; }
.fm-btn:hover { filter: brightness(1.1); }

@media (max-width: 820px) { .demo-body { grid-template-columns: 1fr; } .demo-side { display: none; } }
</style>

<!-- Override global main pour /demo (pleine largeur, comme /chat) -->
<style>
main:has(.demo-outer) {
  max-width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  height: 100vh !important;
}
</style>
