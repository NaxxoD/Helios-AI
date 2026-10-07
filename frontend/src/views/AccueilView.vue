<template>
  <div class="lp">

    <!-- Barre de progression + halo de curseur (réactifs au scroll / pointeur) -->
    <div class="lp-scroll-progress" aria-hidden="true"></div>
    <div class="lp-cursor-glow" aria-hidden="true"></div>

    <!-- ══ NAV ══ -->
    <header class="lp-nav" :class="{ 'lp-nav--scrolled': navScrolled }">
      <div class="lp-nav__inner">
        <RouterLink to="/" class="lp-nav__brand">
          <HeliosLogo :size="22" />
          <span>Helios<span class="lp-nav__ai"> AI</span></span>
        </RouterLink>

        <div class="lp-nav__actions">
          <!-- Dropdown Outils -->
          <div class="lp-dd" ref="ddRef">
            <button class="lp-dd__btn" :aria-expanded="ddOpen" @click="ddOpen = !ddOpen">
              Outils
              <svg class="lp-dd__caret" :class="{ 'lp-dd__caret--open': ddOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
            </button>
            <Transition name="lp-dd-fade">
              <div v-if="ddOpen" class="lp-dd__menu">
                <div class="lp-dd__list">
                  <RouterLink v-for="tool in TOOLS" :key="tool.id" :to="tool.route" class="lp-dd__item"
                    @mouseenter="activeHint = tool.id" @mouseleave="activeHint = null" @click="ddOpen = false">
                    <span>{{ tool.name }}</span><span class="lp-dd__chev">›</span>
                  </RouterLink>
                </div>
                <div class="lp-dd__hint">
                  <template v-if="activeHint">
                    <div class="lp-dd__hint-title">{{ TOOLS.find(t => t.id === activeHint)?.name }}</div>
                    <p>{{ TOOLS.find(t => t.id === activeHint)?.desc }}</p>
                  </template>
                  <em v-else>Survolez un outil pour en savoir plus.</em>
                </div>
              </div>
            </Transition>
          </div>

          <template v-if="!isAuthenticated">
            <RouterLink to="/inscription" class="lp-nav__login">Inscription</RouterLink>
            <RouterLink to="/connexion" class="lp-btn lp-btn--primary lp-btn--sm">Connexion</RouterLink>
          </template>
          <template v-else>
            <RouterLink to="/user/dashboard" class="lp-nav__login">Mon bilan</RouterLink>
            <RouterLink to="/chat" class="lp-btn lp-btn--primary lp-btn--sm">Ouvrir Helios</RouterLink>
            <button class="lp-nav__logout" @click="handleLogout">Déconnexion</button>
          </template>

          <button class="lp-nav__theme" @click="toggle" :title="theme === 'dark' ? 'Mode clair' : 'Mode sombre'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <circle cx="12" cy="12" r="4.2" fill="currentColor" stroke="none"/>
              <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"/>
            </svg>
          </button>
        </div>
      </div>
    </header>

    <!-- ── Fond animé (décoratif, fixed) ── -->
    <div class="lp-bg" aria-hidden="true">
      <div class="lp-bg__blob lp-bg__blob--g"></div>
      <div class="lp-bg__blob lp-bg__blob--p"></div>
      <div class="lp-bg__sun"></div>
      <div class="lp-bg__grid"></div>
    </div>

    <div id="fp">

    <!-- ══ HERO ══ -->
    <section class="lp-hero hero panel" data-fp-label="Accueil">
      <canvas id="lp-hero-canvas" class="lp-hero-canvas" aria-hidden="true"></canvas>
      <div class="lp-wrap lp-hero__grid wrap">

        <!-- Colonne texte -->
        <div class="lp-hero__col">
          <span class="lp-eyebrow">Optimisation · Coût · Impact</span>
          <h1>Le bon modèle.<br>Le bon prompt.<br><span class="lp-hl">Le bon coût.</span></h1>
          <p class="lp-lead">Un système qui optimise vos prompts, détermine l'IA adaptée et mesure chaque réponse — en coût et en CO₂.</p>
          <div class="lp-hero__ctas">
            <RouterLink to="/chat" class="lp-btn lp-btn--primary lp-btn--lg lp-magnetic">Aller au chat →</RouterLink>
            <a href="#fonctionnement" class="lp-btn lp-btn--ghost lp-btn--lg">Voir comment ça marche</a>
          </div>
          <div class="lp-hero__note"><span class="lp-dot"></span> 3 échanges gratuits, sans compte — aucune carte requise.</div>
        </div>

        <!-- Carte démo optimiseur -->
        <div class="lp-demo">
          <div class="lp-demo__head">
            <span class="lp-demo__tag">Helios · optimiseur</span>
            <span class="lp-demo__lights"><i></i><i></i><i></i></span>
          </div>
          <p class="lp-demo__label">Votre message</p>
          <div class="lp-demo__box">
            <span
              v-for="(part, idx) in scenario.parts"
              :key="idx"
              :class="['lp-demo__part', { 'lp-demo__part--junk': part.junk, 'lp-demo__part--cut': part.junk && cutSet.has(idx) }]"
            >{{ part.t }}</span>
          </div>
          <div class="lp-demo__arrow">↓ &nbsp;Helios nettoie &amp; choisit l'IA&nbsp; ↓</div>
          <div class="lp-demo__route">
            <span>IA sélectionnée</span>
            <span class="lp-chip"><span class="lp-chip__pulse"></span>{{ chipName }}</span>
          </div>
          <div class="lp-demo__stats">
            <div class="lp-dstat lp-dstat--green"><div class="lp-dstat__k">Économisé</div><div class="lp-dstat__v">{{ statSave }}</div></div>
            <div class="lp-dstat lp-dstat--orange"><div class="lp-dstat__k">Coût réponse</div><div class="lp-dstat__v">{{ statCost }}</div></div>
            <div class="lp-dstat lp-dstat--purple"><div class="lp-dstat__k">CO₂</div><div class="lp-dstat__v">{{ statCo2 }}</div></div>
          </div>
        </div>

      </div>
      <div class="lp-scroll-hint" aria-hidden="true">
        <span class="lp-scroll-hint__label">Défiler</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
      </div>
    </section>

    <!-- ══ PROBLÈME ══ -->
    <section class="lp-section panel" id="probleme" data-fp-label="Le constat">
      <div class="lp-wrap wrap">
        <div class="lp-sec-head lp-reveal">
          <span class="lp-eyebrow">Le constat</span>
          <h2>Vous utilisez l'IA tous les jours.<br>Mais vous la subissez.</h2>
          <p class="lp-lead">Un seul assistant, un seul fournisseur, zéro visibilité — vous payez sans savoir pour quoi.</p>
        </div>
        <div class="lp-constat-stats">
          <div class="lp-cstat lp-reveal">
            <div class="lp-cn lp-cn--green">40–60<span class="lp-cu">%</span></div>
            <div class="lp-cl">des tokens d'un prompt moyen sont <b>inutiles</b> — vous les payez quand même.</div>
          </div>
          <div class="lp-cstat lp-reveal">
            <div class="lp-cn lp-cn--orange">×70</div>
            <div class="lp-cl">l'écart de prix entre le modèle le moins cher et le plus cher.</div>
          </div>
          <div class="lp-cstat lp-reveal">
            <div class="lp-cn lp-cn--purple">0,42<span class="lp-cu">Wh</span></div>
            <div class="lp-cl">par échange GPT-4o — soit <b>40 % de plus</b> qu'une recherche Google.</div>
          </div>
        </div>
        <p class="lp-constat-src lp-reveal">Sources — Silicon Data 2026 · arXiv 2505.09598 · Epoch AI 2025</p>
      </div>
    </section>

    <!-- ══ COMMENT ÇA MARCHE ══ -->
    <section class="lp-section panel" id="fonctionnement" data-fp-label="Fonctionnement">
      <div class="lp-wrap wrap">
        <div class="lp-sec-head lp-reveal">
          <span class="lp-eyebrow">Comment ça marche</span>
          <h2>Helios se place entre vous et l'IA. Il réfléchit à votre place.</h2>
          <p class="lp-lead">Trois choses qu'aucune interface ne fait — automatiquement, à chaque message.</p>
        </div>
        <div class="lp-cards">
          <div class="lp-card lp-reveal">
            <div class="lp-card__img">
              <img src="/lever2.png" alt="Routage automatique vers la bonne IA" />
            </div>
            <div class="lp-card__ico lp-ico--green">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l3 8 4-16 3 8h4"/></svg>
            </div>
            <div class="lp-card__num">01</div>
            <h3>Il choisit la bonne IA</h3>
            <p>Une question simple n'a pas besoin du modèle le plus cher. Helios envoie chaque demande vers l'assistant le plus adapté — instantanément, sans que vous ayez à choisir.</p>
            <div class="lp-proof"><span class="lp-proof__k">routing local</span> · décision en 0 ms<br>OpenAI · Anthropic · Google</div>
          </div>
          <div class="lp-card lp-reveal">
            <div class="lp-card__img">
              <img src="/lever1.png" alt="Optimisation du prompt avant envoi" />
            </div>
            <div class="lp-card__ico lp-ico--green">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h6M5 8h9M5 16h4"/><path d="M16 9l3 3-3 3"/></svg>
            </div>
            <div class="lp-card__num">02</div>
            <h3>Il allège votre demande</h3>
            <p>Politesses, instructions inutiles, formulations à rallonge… Helios nettoie votre message avant l'envoi. Même réponse — sans le superflu qui vous fait payer plus.</p>
            <div class="lp-proof"><span class="lp-proof__k">pipeline heuristique local</span> · 0 appel API<br>moins envoyé, qualité identique</div>
          </div>
          <div class="lp-card lp-reveal">
            <div class="lp-card__img">
              <img src="/lever3.png" alt="Dashboard tracking CO₂ et coût en temps réel" />
            </div>
            <div class="lp-card__ico lp-ico--green">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 14l3-4 3 3 4-7"/></svg>
            </div>
            <div class="lp-card__num">03</div>
            <h3>Il vous montre tout</h3>
            <p>Pour chaque réponse : le coût en euros, l'énergie, le CO₂. En clair, en temps réel. Ce que vous mesurez, vous pouvez enfin le réduire.</p>
            <div class="lp-proof"><span class="lp-proof__k">temps réel</span> · par message &amp; par session<br>coût € · tokens · gCO₂</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ══ DIFFÉRENCIATEUR ══ -->
    <section class="lp-section panel" id="difference" data-fp-label="Routing auto">
      <div class="lp-wrap lp-diff wrap">
        <div class="lp-reveal">
          <span class="lp-badge">Ce que personne d'autre ne fait</span>
          <h2>Le bon modèle, au bon moment.<br><span class="lp-hl">Automatiquement.</span></h2>
          <p class="lp-lead">Les autres interfaces vous laissent choisir — ou vous imposent un seul modèle. Helios analyse chaque message en 0 ms et envoie vers l'IA la plus adaptée, sans que vous ayez à y penser. Gemini Flash pour une question rapide, Claude Opus pour une analyse complexe — dans la même conversation, sans interruption.</p>
        </div>
        <div class="lp-chat lp-reveal">
          <div class="lp-chat__row">
            <div class="lp-model-tag lp-model-tag--r">
              <span class="lp-model-tag--sw">⚡ Helios → Gemini Flash</span>
              <span style="color:var(--lp-text3);font-size:10px">décision locale · 0 ms</span>
            </div>
            <div class="lp-bubble lp-bubble--user">Résume-moi cet email en 3 points.</div>
          </div>
          <div class="lp-chat__row">
            <div class="lp-bubble lp-bubble--ai">Voici les 3 points clés de votre email…</div>
          </div>
          <div class="lp-switch-note">question suivante, complexité différente</div>
          <div class="lp-chat__row">
            <div class="lp-model-tag lp-model-tag--r">
              <span class="lp-model-tag--sw">⚡ Helios → Claude Sonnet</span>
              <span style="color:var(--lp-text3);font-size:10px">rerouting automatique</span>
            </div>
            <div class="lp-bubble lp-bubble--user">Maintenant, compare nos 3 offres et recommande la meilleure stratégie.</div>
          </div>
          <div class="lp-chat__row">
            <div class="lp-bubble lp-bubble--ai">Analyse comparative des trois offres, avec recommandation argumentée…</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ══ COMPARATIF ══ -->
    <section class="lp-section panel" data-fp-label="Comparatif">
      <div class="lp-wrap wrap">
        <div class="lp-sec-head lp-reveal">
          <span class="lp-eyebrow">Pourquoi pas juste un seul outil ?</span>
          <h2>Ce que Helios fait, et que les autres ne font pas.</h2>
        </div>
        <div class="lp-cmp-wrap lp-reveal">
          <table class="lp-cmp">
            <thead>
              <tr>
                <th>Capacité</th>
                <th>Outils classiques</th>
                <th class="lp-cmp__he-head">Helios</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Choisit l'IA adaptée à chaque demande</td><td><span class="lp-no">✕</span> un seul modèle imposé</td><td class="lp-cmp__he"><span class="lp-yes">✓</span> <b>automatique</b></td></tr>
              <tr><td>Allège votre message avant l'envoi</td><td><span class="lp-no">✕</span></td><td class="lp-cmp__he"><span class="lp-yes">✓</span> <b>à chaque message</b></td></tr>
              <tr><td>Coût en euros affiché en temps réel</td><td><span class="lp-no">✕</span> facture surprise</td><td class="lp-cmp__he"><span class="lp-yes">✓</span></td></tr>
              <tr><td>Impact CO₂ mesuré</td><td><span class="lp-no">✕</span></td><td class="lp-cmp__he"><span class="lp-yes">✓</span></td></tr>
              <tr><td>Routing automatique selon la complexité</td><td><span class="lp-no">✕</span> modèle fixe ou choix manuel</td><td class="lp-cmp__he"><span class="lp-yes">✓</span> <b>0 ms, local</b></td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- ══ MÉTRIQUES ══ -->
    <section class="lp-section panel" id="impact" data-fp-label="Impact">
      <div class="lp-wrap wrap">
        <div class="lp-sec-head lp-reveal">
          <span class="lp-eyebrow">Chiffres &amp; impact</span>
          <h2>Ce que Helios mesure, en vrai.</h2>
          <p class="lp-lead">Pas du marketing : des données agrégées depuis la base de sessions, affichées dans l'interface à chaque échange.</p>
        </div>
        <div class="lp-metrics lp-reveal">
          <div class="lp-mgrid">
            <div class="lp-mcell">
              <div class="lp-mico lp-mico--orange">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M13 2L4.5 13.5H11l-1 8.5L19.5 10H13z"/></svg>
              </div>
              <div class="lp-mval lp-mval--orange">{{ stats.kwh }}</div>
              <div class="lp-mlabel">Énergie tracée</div>
              <div class="lp-msub">mesurée à chaque échange, par IA</div>
            </div>
            <div class="lp-mcell">
              <div class="lp-mico lp-mico--green">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              </div>
              <div class="lp-mval lp-mval--green" data-count="3">3</div>
              <div class="lp-mlabel">Fournisseurs d'IA</div>
              <div class="lp-msub">OpenAI · Anthropic · Google</div>
            </div>
            <div class="lp-mcell">
              <div class="lp-mico lp-mico--purple">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10z"/><path d="M2 21c0-3 1.85-5.36 5.08-6"/></svg>
              </div>
              <div class="lp-mval lp-mval--purple">{{ stats.co2 }}</div>
              <div class="lp-mlabel">CO₂ tracké</div>
              <div class="lp-msub">émissions réelles par session</div>
            </div>
            <div class="lp-mcell">
              <div class="lp-mico lp-mico--gray">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
              </div>
              <div class="lp-mval">{{ stats.sessions }}</div>
              <div class="lp-mlabel">Sessions analysées</div>
              <div class="lp-msub">depuis la mise en production</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ══ CTA FINAL ══ -->
    <section class="lp-final final panel" data-fp-label="Essayer">
      <div class="lp-wrap wrap">
        <span class="lp-eyebrow lp-reveal">Prêt à essayer ?</span>
        <h2 class="lp-reveal">Posez votre première question. Helios fait le reste.</h2>
        <p class="lp-lead lp-reveal">Pas de configuration, pas de jargon. 3 échanges gratuits, sans compte. L'IA qui réfléchit avant de dépenser — à votre place.</p>
        <div class="lp-hero__ctas lp-final__ctas lp-reveal">
          <RouterLink to="/chat" class="lp-btn lp-btn--primary lp-btn--lg lp-magnetic">Aller au chat →</RouterLink>
          <a href="#fonctionnement" class="lp-btn lp-btn--ghost lp-btn--lg">Revoir le fonctionnement</a>
        </div>
      </div>
      <!-- Footer dans le dernier panel (position:absolute bottom:0 par le CSS fullpage) -->
      <footer class="lp-footer">
        <div class="lp-wrap lp-footer__inner">
          <div class="lp-brand">
            <HeliosLogo :size="22" />
            Helios<span class="lp-brand-ai"> AI</span>
          </div>
          <div class="lp-footer__src">Sources : ADEME · Infomaniak D4 · RTE · Epoch AI · IEA 2024</div>
        </div>
      </footer>
    </section>

    </div><!-- /#fp -->

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../api/index.js'
import HeliosLogo from '../components/HeliosLogo.vue'
import { useAuth } from '../composables/useAuth.js'
import { useTheme } from '../composables/useTheme.js'
import useLandingEffects from '../composables/useLandingEffects.js'

const { isAuthenticated, deconnexion } = useAuth()
const { theme, toggle }               = useTheme()

function handleLogout() { deconnexion() }

/* ── Nav ── */
const navScrolled = ref(false)
const ddOpen      = ref(false)
const activeHint  = ref(null)
const ddRef       = ref(null)

const TOOLS = [
  { id: 'optimiseur', name: 'Optimiseur',               route: '/optimiseur',  desc: "Analyse votre prompt et supprime le bruit avant l'envoi — formules de politesse, méta-instructions, répétitions." },
  { id: 'upload',     name: 'Analyser une conversation', route: '/upload',      desc: "Importez un export ChatGPT, Claude ou Gemini et calculez l'énergie consommée, le CO₂ et le coût réel." },
  { id: 'manuel',     name: 'Calcul rapide',             route: '/manuel',      desc: "Estimez en un instant le coût et le CO₂ d'un prompt en saisissant manuellement les tokens." },
  { id: 'extension',  name: 'Extension Chrome',          route: '/extension',   desc: "Intégration directe sur ChatGPT, Claude.ai et Gemini. Comptez vos tokens sans changer d'interface." },
]

function onScroll() { navScrolled.value = window.scrollY > 16 }
function onClickOutside(e) {
  if (ddRef.value && !ddRef.value.contains(e.target)) { ddOpen.value = false; activeHint.value = null }
}

/* ── Stats ── */
const stats = ref({ kwh: '0', co2: '0,0', sessions: '0' })

onMounted(async () => {
  window.addEventListener('scroll', onScroll, { passive: true })
  document.addEventListener('mousedown', onClickOutside)
  onScroll()

  try {
    const { data } = await api.get('/accueil/stats')
    stats.value = {
      kwh:      data.total_kwh      ?? '0',
      co2:      data.total_co2      ?? '0,0 g',
      sessions: data.total_sessions ?? '0',
    }
  } catch { /* stats restent à 0 */ }
})

/* ── Demo optimiseur ── */
const SCENARIOS = [
  {
    parts: [
      { t: "Bonjour, j'espère que tu vas bien. ", junk: true },
      { t: "Tu es une IA très avancée dotée d'une compréhension holistique. ", junk: true },
      { t: "Peux-tu, s'il te plaît, " },
      { t: "si cela ne te dérange pas trop, ", junk: true },
      { t: "résumer cet article en 3 points clés ?" },
    ],
    model: 'Gemini Flash', save: '58 %', cost: '0,001 €', co2: '0,2 g',
  },
  {
    parts: [
      { t: "Salut ! Merci d'avance pour ton aide précieuse. ", junk: true },
      { t: "En tant qu'expert de niveau mondial, ", junk: true },
      { t: "compare ces deux offres commerciales " },
      { t: "(je sais que tu es capable de tout), ", junk: true },
      { t: "et recommande la meilleure stratégie." },
    ],
    model: 'Claude Sonnet', save: '41 %', cost: '0,012 €', co2: '1,4 g',
  },
  {
    parts: [
      { t: "Hello, comment ça va aujourd'hui ? ", junk: true },
      { t: "Traduis ce paragraphe en anglais " },
      { t: "— et n'hésite pas à être créatif si tu veux. ", junk: true },
      { t: "Garde un ton professionnel." },
    ],
    model: "GPT-4o mini", save: '49 %', cost: '0,002 €', co2: '0,4 g',
  },
]

const scenario  = ref(SCENARIOS[0])
const cutSet    = ref(new Set())
const chipName  = ref('analyse…')
const statSave  = ref('0 %')
const statCost  = ref('0,000 €')
const statCo2   = ref('0,0 g')
let   scenarioIdx = 0
let   intervalId  = null
const timeouts    = []

function runScenario(s) {
  timeouts.forEach(clearTimeout)
  timeouts.length = 0
  scenario.value  = s
  cutSet.value    = new Set()
  chipName.value  = 'analyse…'
  statSave.value  = '0 %'
  statCost.value  = '0,000 €'
  statCo2.value   = '0,0 g'

  const junkIndexes = s.parts
    .map((p, i) => (p.junk ? i : -1))
    .filter(i => i >= 0)

  junkIndexes.forEach((idx, k) => {
    const t = setTimeout(() => {
      cutSet.value = new Set([...cutSet.value, idx])
    }, 700 + k * 420)
    timeouts.push(t)
  })

  const after = 700 + junkIndexes.length * 420 + 500
  timeouts.push(setTimeout(() => { chipName.value = s.model }, after))
  timeouts.push(setTimeout(() => {
    statSave.value = s.save
    statCost.value = s.cost
    statCo2.value  = s.co2
  }, after + 300))
}

/* ── Effets de la maquette (reveal, parallaxe, canvas, count-up, chat…) ── */
let stopEffects = null

onMounted(() => {
  runScenario(SCENARIOS[0])
  intervalId = setInterval(() => {
    scenarioIdx = (scenarioIdx + 1) % SCENARIOS.length
    runScenario(SCENARIOS[scenarioIdx])
  }, 6200)

  stopEffects = useLandingEffects()
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  document.removeEventListener('mousedown', onClickOutside)
  clearInterval(intervalId)
  timeouts.forEach(clearTimeout)
  if (stopEffects) stopEffects()
})
</script>

<style scoped>
/* ── Tokens locaux landing page ── */
.lp {
  --lp-bg:       #080C0A;
  --lp-bg2:      #0B1310;
  --lp-surface:  #0E1714;
  --lp-surface2: #121E19;
  --lp-line:     rgba(120,180,150,0.10);
  --lp-line-s:   rgba(120,180,150,0.18);
  --lp-text:     #E7EFEA;
  --lp-text2:    #9AA8A0;
  --lp-text3:    #677169;
  --lp-green:    #34D8A0;
  --lp-green-s:  rgba(52,216,160,0.12);
  --lp-green-l:  rgba(52,216,160,0.30);
  --lp-orange:   #E8843C;
  --lp-purple:   #A88BF2;
  --lp-red:      #c25b5b;
  --lp-maxw:     1180px;
  --lp-fd:       "Chakra Petch", sans-serif;
  --lp-fb:       "Archivo", sans-serif;
  --lp-fm:       "JetBrains Mono", monospace;

  background: var(--lp-bg);
  color: var(--lp-text);
  font-family: var(--lp-fb);
  font-size: 20px;
  line-height: 1.6;
  min-height: 100vh;
  overflow-x: hidden;
}

/* ── Background animé ── */
.lp-bg { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.lp-bg__grid {
  position: absolute; inset: -80px;
  background-image: linear-gradient(var(--lp-line) 1px, transparent 1px),
                    linear-gradient(90deg, var(--lp-line) 1px, transparent 1px);
  background-size: 64px 64px; opacity: .45;
  -webkit-mask-image: radial-gradient(circle at 50% 16%, #000 0%, transparent 70%);
  mask-image: radial-gradient(circle at 50% 16%, #000 0%, transparent 70%);
  animation: lp-gridDrift 26s linear infinite;
}
.lp-bg__sun {
  position: absolute; top: -34%; left: 50%; width: 1040px; height: 1040px; margin-left: -520px;
  background: radial-gradient(circle at center, rgba(232,132,60,.17), rgba(232,132,60,.05) 38%, transparent 62%);
  filter: blur(12px); animation: lp-breathe 11s ease-in-out infinite;
}
.lp-bg__blob {
  position: absolute; border-radius: 50%; filter: blur(90px);
}
.lp-bg__blob--g {
  width: 640px; height: 640px; top: -10%; left: -7%;
  background: radial-gradient(circle, rgba(52,216,160,.16), transparent 65%);
  animation: lp-drift1 21s ease-in-out infinite;
}
.lp-bg__blob--p {
  width: 560px; height: 560px; top: 12%; right: -11%;
  background: radial-gradient(circle, rgba(168,139,242,.12), transparent 65%);
  animation: lp-drift2 27s ease-in-out infinite;
}
@keyframes lp-breathe  { 0%,100%{opacity:.5;transform:scale(1)} 50%{opacity:1;transform:scale(1.07)} }
@keyframes lp-drift1   { 0%,100%{transform:translate(0,0)} 50%{transform:translate(48px,36px)} }
@keyframes lp-drift2   { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-56px,42px)} }
@keyframes lp-gridDrift { from{background-position:0 0} to{background-position:0 64px} }

/* ── Nav ── */
.lp-nav {
  position: sticky; top: 0; z-index: 50;
  backdrop-filter: blur(14px);
  background: rgba(8,12,10,0.72);
  border-bottom: 1px solid var(--lp-line);
  transition: background .2s, box-shadow .2s;
}
.lp-nav--scrolled { background: rgba(8,12,10,.92); box-shadow: 0 10px 34px -20px #000; }
.lp-nav__inner {
  max-width: var(--lp-maxw); margin: 0 auto; padding: 16px 28px;
  display: flex; align-items: center; gap: 28px;
}
.lp-nav__brand {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--lp-fd); font-weight: 600; font-size: 22px;
  color: var(--lp-text); text-decoration: none; white-space: nowrap; flex: 0 0 auto;
}
.lp-nav__ai { color: var(--lp-green); }
/* Logo Aperture : les rayons tournent doucement au survol */
.lp :deep(.ap-rays) { transform-origin: 24px 24px; }
.lp-nav__brand:hover :deep(.ap-rays),
.lp-brand:hover :deep(.ap-rays) { animation: lp-apSpin 9s linear infinite; }
@keyframes lp-apSpin { to { transform: rotate(360deg); } }
.lp-nav__actions { margin-left: auto; display: flex; align-items: center; gap: 14px; }
.lp-nav__login { color: var(--lp-text2); text-decoration: none; font-size: 17px; font-weight: 500; transition: color .2s; white-space: nowrap; }
.lp-nav__login:hover { color: var(--lp-text); }
.lp-btn--sm { font-size: 16px; padding: 10px 18px; border-radius: 8px; }
.lp-nav__logout {
  background: none; border: 1px solid rgba(194,91,91,.4); color: #bd6a64;
  padding: 6px 13px; border-radius: 8px; cursor: pointer; font-size: 13.5px;
  font-family: var(--lp-fb); transition: all .2s;
}
.lp-nav__logout:hover { border-color: #c25b5b; color: #e07070; }
.lp-nav__theme {
  display: grid; place-items: center; width: 38px; height: 38px; border-radius: 9px;
  background: transparent; border: 1px solid var(--lp-line-s); color: var(--lp-orange);
  cursor: pointer; transition: all .2s; flex-shrink: 0;
}
.lp-nav__theme:hover { border-color: var(--lp-green-l); color: var(--lp-green); }
.lp-nav__theme svg { width: 18px; height: 18px; }

/* Dropdown Outils */
.lp-dd { position: relative; }
.lp-dd__btn {
  display: inline-flex; align-items: center; gap: 6px; background: none; border: none;
  cursor: pointer; font-family: var(--lp-fb); font-size: 14.5px; color: var(--lp-text2);
  padding: 6px 2px; transition: color .2s;
}
.lp-dd__btn:hover, .lp-dd__btn[aria-expanded="true"] { color: var(--lp-text); }
.lp-dd__caret { width: 15px; height: 15px; transition: transform .25s; }
.lp-dd__caret--open { transform: rotate(180deg); }
.lp-dd__menu {
  position: absolute; top: calc(100% + 18px); right: 0;
  width: 540px; background: rgba(12,20,16,.97); backdrop-filter: blur(16px);
  border: 1px solid var(--lp-line-s); border-radius: 14px; padding: 10px;
  display: grid; grid-template-columns: 1.15fr .85fr; gap: 6px;
  box-shadow: 0 30px 70px -30px #000; z-index: 60;
}
.lp-dd__list { display: flex; flex-direction: column; gap: 2px; }
.lp-dd__item {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 11px 13px; border-radius: 9px; text-decoration: none;
  color: var(--lp-text); font-size: 14.5px; transition: background .18s, color .18s;
}
.lp-dd__item:hover { background: var(--lp-green-s); color: var(--lp-green); }
.lp-dd__chev { color: var(--lp-text3); font-size: 17px; transition: color .18s, transform .18s; }
.lp-dd__item:hover .lp-dd__chev { color: var(--lp-green); transform: translateX(2px); }
.lp-dd__hint {
  padding: 13px 15px; border-left: 1px solid var(--lp-line);
  color: var(--lp-text2); font-size: 13.5px; line-height: 1.6;
}
.lp-dd__hint em { color: var(--lp-text3); font-style: italic; }
.lp-dd__hint-title { font-size: 13px; font-weight: 600; color: var(--lp-green); margin-bottom: 6px; }
.lp-dd-fade-enter-active, .lp-dd-fade-leave-active { transition: opacity .15s, transform .15s; }
.lp-dd-fade-enter-from, .lp-dd-fade-leave-to { opacity: 0; transform: translateY(-6px); }

/* ── Layout ── */
.lp-wrap { max-width: var(--lp-maxw); margin: 0 auto; padding: 0 28px; position: relative; z-index: 1; }

/* ── Typo ── */
.lp-eyebrow {
  font-family: var(--lp-fm); font-size: 15px; letter-spacing: .22em;
  text-transform: uppercase; color: var(--lp-green); font-weight: 500;
}
.lp h1, .lp h2, .lp h3 {
  font-family: var(--lp-fd); font-weight: 600; line-height: 1.04; letter-spacing: -.01em;
}
.lp h1 { font-size: clamp(32px,6vw,82px); }
.lp h2 { font-size: clamp(26px,5vw,68px); }
.lp h3 { font-size: 26px; letter-spacing: 0; }
.lp-lead { color: var(--lp-text2); font-size: clamp(20px,2vw,26px); max-width: 60ch; }
.lp-hl  { color: var(--lp-green); }

/* ── Reveal au scroll : REJOUE à chaque passage (toggle de .lp-reveal--pre via IntersectionObserver) ── */
.lp-reveal { transition: opacity .58s cubic-bezier(.2,.85,.25,1), transform .58s cubic-bezier(.2,.85,.25,1), filter .58s ease; }
.lp-reveal--pre { opacity: 0; transform: translateY(40px) scale(.99); filter: blur(5px); }
/* léger décalage en cascade dans les grilles */
.lp-constat-stats .lp-cstat.lp-reveal:nth-child(2) { transition-delay: .12s; }
.lp-constat-stats .lp-cstat.lp-reveal:nth-child(3) { transition-delay: .24s; }
.lp-cards .lp-card.lp-reveal:nth-child(2) { transition-delay: .1s; }
.lp-cards .lp-card.lp-reveal:nth-child(3) { transition-delay: .2s; }

/* ── Buttons ── */
.lp-btn {
  font-family: var(--lp-fb); font-weight: 600; font-size: 18px;
  border: none; border-radius: 9px; cursor: pointer; text-decoration: none;
  display: inline-flex; align-items: center; gap: 9px;
  transition: all .2s; white-space: nowrap;
}
.lp-btn--primary { background: var(--lp-green); color: #04140D; padding: 13px 22px; }
.lp-btn--primary:hover { filter: brightness(1.08); transform: translateY(-1px); box-shadow: 0 8px 26px -10px var(--lp-green); }
.lp-btn--ghost { background: transparent; color: var(--lp-text); padding: 13px 21px; border: 1px solid var(--lp-line-s); }
.lp-btn--ghost:hover { border-color: var(--lp-green-l); color: #fff; }
.lp-btn--lg { font-size: 20px; padding: 17px 30px; border-radius: 11px; }
@keyframes lp-ctaPulse { 0%,100%{box-shadow:0 0 0 0 rgba(52,216,160,0)} 50%{box-shadow:0 10px 34px -10px rgba(52,216,160,.5)} }
.lp-btn--primary { animation: lp-ctaPulse 3.4s ease-in-out infinite; }
.lp-btn--primary:hover { animation: none; }

/* ── Hero (plein écran en défilement continu) ── */
.lp-hero { min-height: calc(100svh - 64px); display: flex; align-items: center; padding: 36px 0 64px; position: relative; z-index: 1; }
.lp-hero__grid { display: grid; grid-template-columns: 1.05fr .95fr; gap: 54px; align-items: center; width: 100%; position: relative; z-index: 2; perspective: 1300px; }
/* canvas « moteur de routing » derrière le contenu du hero */
.lp-hero-canvas { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; pointer-events: none; opacity: .95;
  -webkit-mask-image: radial-gradient(135% 125% at 80% 34%, #000 42%, rgba(0,0,0,.18) 100%);
  mask-image: radial-gradient(135% 125% at 80% 34%, #000 42%, rgba(0,0,0,.18) 100%); }
.lp-hero__col > * { animation: lp-heroRise .8s both cubic-bezier(.2,.7,.2,1); }
.lp-hero__col > *:nth-child(1) { animation-delay: .04s; }
.lp-hero__col > *:nth-child(2) { animation-delay: .12s; }
.lp-hero__col > *:nth-child(3) { animation-delay: .20s; }
.lp-hero__col > *:nth-child(4) { animation-delay: .30s; }
.lp-hero__col > *:nth-child(5) { animation-delay: .40s; }
@keyframes lp-heroRise { from{transform:translateY(20px)} to{transform:translateY(0)} }
.lp-hero h1 { margin: 20px 0 22px; }
.lp-hero__ctas { display: flex; gap: 14px; margin: 32px 0 16px; flex-wrap: wrap; }
.lp-hero__note { font-family: var(--lp-fm); font-size: 12.5px; color: var(--lp-text3); display: flex; align-items: center; gap: 9px; }
.lp-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--lp-green); box-shadow: 0 0 10px var(--lp-green); flex-shrink: 0; }

/* ── Demo card ── */
.lp-demo {
  position: relative;
  background: linear-gradient(180deg, var(--lp-surface2), var(--lp-surface));
  border: 1px solid var(--lp-line-s); border-radius: 18px; padding: 20px;
  box-shadow: 0 40px 90px -50px rgba(0,0,0,.9), inset 0 1px 0 rgba(255,255,255,.03);
  /* "backwards" (et non "both") : laisse le transform inline du tilt 3D prendre la main une fois l'entrée jouée */
  animation: lp-demoRise .9s .30s backwards cubic-bezier(.2,.7,.2,1);
  transform-style: preserve-3d; will-change: transform;
}
@keyframes lp-demoRise { from{transform:translateY(26px) scale(.99)} to{transform:none} }
.lp-demo__head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.lp-demo__tag { font-family: var(--lp-fm); font-size: 11px; letter-spacing: .16em; text-transform: uppercase; color: var(--lp-text3); }
.lp-demo__lights { display: flex; gap: 6px; }
.lp-demo__lights i { width: 9px; height: 9px; border-radius: 50%; background: var(--lp-line-s); display: block; }
.lp-demo__label { font-family: var(--lp-fm); font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--lp-text3); margin: 0 0 7px; }
.lp-demo__box {
  background: var(--lp-bg2); border: 1px solid var(--lp-line); border-radius: 11px;
  padding: 14px; font-size: 15px; line-height: 1.65; min-height: 96px; color: var(--lp-text);
}
.lp-demo__part--junk { color: var(--lp-text3); transition: all .5s ease; }
.lp-demo__part--cut { text-decoration: line-through; opacity: .32; color: var(--lp-red); }
.lp-demo__arrow { display: flex; justify-content: center; color: var(--lp-text3); margin: 10px 0; font-family: var(--lp-fm); font-size: 12px; letter-spacing: .1em; }
.lp-demo__route { display: flex; align-items: center; gap: 9px; margin-top: 13px; font-family: var(--lp-fm); font-size: 12.5px; color: var(--lp-text2); }
.lp-chip {
  display: inline-flex; align-items: center; gap: 7px; padding: 5px 11px; border-radius: 7px;
  background: var(--lp-green-s); border: 1px solid var(--lp-green-l); color: var(--lp-green);
  font-family: var(--lp-fm); font-size: 12.5px; font-weight: 500;
}
.lp-chip__pulse {
  width: 6px; height: 6px; border-radius: 50%; background: var(--lp-green);
  animation: lp-pulse 1.6s infinite;
}
@keyframes lp-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
.lp-demo__stats { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; margin-top: 14px; }
.lp-dstat { background: var(--lp-bg2); border: 1px solid var(--lp-line); border-radius: 10px; padding: 11px 12px; }
.lp-dstat__k { font-family: var(--lp-fm); font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; color: var(--lp-text3); }
.lp-dstat__v { font-family: var(--lp-fm); font-weight: 700; font-size: 19px; margin-top: 3px; font-variant-numeric: tabular-nums; }
.lp-dstat--green .lp-dstat__v { color: var(--lp-green); }
.lp-dstat--orange .lp-dstat__v { color: var(--lp-orange); }
.lp-dstat--purple .lp-dstat__v { color: var(--lp-purple); }

/* ── Sections ── */
.lp-section { padding: 78px 0; border-top: 1px solid var(--lp-line); position: relative; z-index: 1; }
.lp-sec-head { max-width: 760px; margin-bottom: 48px; }
.lp-sec-head .lp-eyebrow { display: block; margin-bottom: 16px; }
.lp-sec-head h2 { margin-bottom: 18px; }

/* ── Scroll hint ── */
.lp-scroll-hint {
  position: absolute; bottom: 28px; left: 50%; transform: translateX(-50%);
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  color: var(--lp-text3); animation: lp-scrollBounce 2.2s ease-in-out infinite;
  cursor: default; z-index: 2;
}
.lp-scroll-hint__label { font-family: var(--lp-fm); font-size: 10px; letter-spacing: .18em; text-transform: uppercase; }
.lp-scroll-hint svg { width: 18px; height: 18px; }
@keyframes lp-scrollBounce { 0%,100%{transform:translateX(-50%) translateY(0)} 50%{transform:translateX(-50%) translateY(6px)} }
@media (prefers-reduced-motion:reduce) { .lp-scroll-hint { animation: none; } }

/* ── Le constat : 3 chiffres sourcés ── */
.lp-constat-stats { display: grid; grid-template-columns: repeat(3,1fr); gap: 44px; margin-bottom: 34px; padding-bottom: 38px; border-bottom: 1px solid var(--lp-line); }
.lp-cstat { display: flex; flex-direction: column; gap: 15px; padding-left: 24px; border-left: 2px solid var(--lp-line-s); }
.lp-cn { font-family: var(--lp-fm); font-weight: 700; font-size: clamp(46px,5.6vw,72px); line-height: .95; letter-spacing: -.02em; font-variant-numeric: tabular-nums; }
.lp-cn .lp-cu { font-size: .5em; font-weight: 500; color: var(--lp-text2); margin-left: .12em; }
.lp-cl { color: var(--lp-text2); font-size: 16px; line-height: 1.5; max-width: 30ch; }
.lp-cn--green { color: var(--lp-green); }
.lp-cn--orange { color: var(--lp-orange); }
.lp-cn--purple { color: var(--lp-purple); }
.lp-constat-src { font-family: var(--lp-fm); font-size: 12px; color: var(--lp-text3); letter-spacing: .04em; margin-top: 6px; }
@media (max-width: 560px) { .lp-constat-stats { grid-template-columns: 1fr; gap: 22px; } }

/* ── Cards ── */
.lp-cards { display: grid; grid-template-columns: repeat(3,1fr); gap: 18px; }
.lp-card {
  background: linear-gradient(180deg, var(--lp-surface), var(--lp-bg2));
  border: 1px solid var(--lp-line); border-radius: 16px; padding: 26px;
  display: flex; flex-direction: column; overflow: hidden;
  transition: transform .25s, border-color .25s;
}
.lp-card:hover { transform: translateY(-4px); border-color: var(--lp-green-l); }
.lp-card__img { margin: -26px -26px 20px; height: 220px; flex-shrink: 0; }
#fonctionnement { padding: 10px 0; }
#fonctionnement h2 { font-size: clamp(22px, 2.2vw, 32px); white-space: nowrap; }
#fonctionnement .lp-lead { font-size: clamp(15px, 1.2vw, 18px); white-space: nowrap; }
#fonctionnement .lp-sec-head { margin-bottom: 20px; }
#fonctionnement .lp-sec-head h2 { margin-bottom: 8px; }
.lp-card__img img { width: 100%; height: 100%; object-fit: cover; object-position: center 30%; display: block; }
.lp-card__ico { width: 42px; height: 42px; border-radius: 11px; display: grid; place-items: center; margin-bottom: 20px; border: 1px solid var(--lp-line-s); }
.lp-card__ico svg { width: 21px; height: 21px; }
.lp-ico--green { background: var(--lp-green-s); color: var(--lp-green); }
.lp-card__num { font-family: var(--lp-fm); font-size: 15px; color: var(--lp-text3); margin-bottom: 10px; letter-spacing: .1em; }
.lp-card h3 { margin-bottom: 14px; }
.lp-card p { color: var(--lp-text2); font-size: 18px; flex: 1; }
.lp-proof { margin-top: 20px; padding-top: 15px; border-top: 1px dashed var(--lp-line-s); font-family: var(--lp-fm); font-size: 14px; color: var(--lp-text3); line-height: 1.7; }
.lp-proof__k { color: var(--lp-green); }

/* ── Différenciateur ── */
.lp-diff { display: grid; grid-template-columns: 1fr 1fr; gap: 54px; align-items: center; }
.lp-badge { display: inline-flex; align-items: center; gap: 8px; font-family: var(--lp-fm); font-size: 14px; letter-spacing: .14em; text-transform: uppercase; color: var(--lp-orange); background: rgba(232,132,60,.1); border: 1px solid rgba(232,132,60,.25); padding: 8px 16px; border-radius: 7px; margin-bottom: 20px; }
.lp-diff h2 { margin-bottom: 18px; }
.lp-diff .lp-lead { max-width: 48ch; }
.lp-chat { background: var(--lp-surface); border: 1px solid var(--lp-line-s); border-radius: 18px; padding: 28px; box-shadow: 0 40px 90px -55px #000; }
.lp-chat__row { display: flex; flex-direction: column; gap: 8px; margin-bottom: 22px; }
.lp-bubble { max-width: 92%; padding: 16px 20px; border-radius: 13px; font-size: 19px; line-height: 1.5; }
.lp-bubble--user { align-self: flex-end; background: var(--lp-surface2); border: 1px solid var(--lp-line); border-bottom-right-radius: 4px; }
.lp-bubble--ai { align-self: flex-start; background: var(--lp-green-s); border: 1px solid var(--lp-green-l); border-bottom-left-radius: 4px; color: #dff5ec; }
.lp-model-tag { font-family: var(--lp-fm); font-size: 15px; color: var(--lp-text3); display: flex; align-items: center; gap: 7px; }
.lp-model-tag--r { align-self: flex-end; }
.lp-model-tag--sw { color: var(--lp-orange); }
.lp-switch-note { text-align: center; font-family: var(--lp-fm); font-size: 15px; color: var(--lp-text3); margin: 4px 0 20px; display: flex; align-items: center; justify-content: center; gap: 9px; }
.lp-switch-note::before, .lp-switch-note::after { content: ""; height: 1px; flex: 1; background: var(--lp-line); }

/* ── Comparatif ── */
.lp-cmp-wrap { border: 1px solid var(--lp-line); border-radius: 14px; overflow: hidden; background: var(--lp-surface); overflow-x: auto; }
.lp-cmp { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 15.5px; }
.lp-cmp th, .lp-cmp td { text-align: left; padding: 17px 20px; border-bottom: 1px solid var(--lp-line); }
.lp-cmp thead th { font-family: var(--lp-fm); font-size: 11.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--lp-text3); font-weight: 500; }
.lp-cmp tbody td:first-child { color: var(--lp-text); font-weight: 500; }
.lp-cmp td { color: var(--lp-text2); }
.lp-cmp__he { background: var(--lp-green-s); }
.lp-cmp__he b { color: var(--lp-green); }
.lp-cmp__he-head { background: var(--lp-green-s); color: var(--lp-green) !important; }
.lp-yes { color: var(--lp-green); }
.lp-no  { color: #bd6a64; }

/* ── Métriques ── */
.lp-metrics { background: var(--lp-bg2); border: 1px solid var(--lp-line); border-radius: 20px; padding: 48px 40px; }
.lp-mgrid { display: grid; grid-template-columns: repeat(4,1fr); gap: 0; }
.lp-mcell { padding: 8px 26px; border-left: 1px solid var(--lp-line); }
.lp-mcell:first-child { border-left: none; padding-left: 0; }
.lp-mico { width: 34px; height: 34px; border-radius: 9px; display: grid; place-items: center; margin-bottom: 18px; }
.lp-mico svg { width: 17px; height: 17px; }
.lp-mico--orange { background: rgba(232,132,60,.12); color: var(--lp-orange); }
.lp-mico--green  { background: var(--lp-green-s);        color: var(--lp-green); }
.lp-mico--purple { background: rgba(168,139,242,.12);    color: var(--lp-purple); }
.lp-mico--gray   { background: rgba(120,180,150,.08);    color: var(--lp-text2); }
.lp-mval { font-family: var(--lp-fm); font-weight: 700; font-size: 30px; font-variant-numeric: tabular-nums; letter-spacing: -.01em; }
.lp-mval--orange { color: var(--lp-orange); }
.lp-mval--green  { color: var(--lp-green); }
.lp-mval--purple { color: var(--lp-purple); }
.lp-munit { font-size: 18px; color: var(--lp-text2); margin-left: 4px; }
.lp-mlabel { font-size: 15px; color: var(--lp-text); margin-top: 8px; font-weight: 500; }
.lp-msub { font-family: var(--lp-fm); font-size: 11.5px; color: var(--lp-text3); margin-top: 7px; line-height: 1.65; }

/* ── CTA final ── */
.lp-final { text-align: center; padding: 96px 0; position: relative; z-index: 1; }
.lp-final h2 { margin: 18px auto 20px; max-width: 18ch; }
.lp-final .lp-lead { margin: 0 auto 34px; }
.lp-final__ctas { justify-content: center; }

/* ── Footer ── */
.lp-footer { border-top: 1px solid var(--lp-line); padding: 36px 0; position: relative; z-index: 1; }
.lp-footer__inner { display: flex; align-items: center; justify-content: space-between; gap: 20px; flex-wrap: wrap; }
.lp-brand { display: flex; align-items: center; gap: 10px; font-family: var(--lp-fd); font-weight: 600; font-size: 18px; color: var(--lp-text); }
.lp-brand-ai { color: var(--lp-green); }
.lp-footer__src { font-family: var(--lp-fm); font-size: 11.5px; color: var(--lp-text3); }

/* ── Grands écrans : le contenu s'élargit (hero pleine largeur) ── */
@media (min-width: 1400px) { .lp { --lp-maxw: 1340px; } .lp-hero__grid { gap: 64px; } .lp-hero .lp-lead { font-size: 21px; } }
@media (min-width: 1600px) { .lp { --lp-maxw: 1500px; } .lp-hero__grid { gap: 80px; } }
@media (min-width: 1800px) { .lp { --lp-maxw: 1660px; } .lp h1 { font-size: 86px; } }
@media (min-width: 2100px) { .lp { --lp-maxw: 1820px; } }

/* ── Responsive ── */
@media (max-width: 920px) {
  .lp-hero__grid, .lp-diff { grid-template-columns: 1fr; gap: 36px; }
  .lp-cards { grid-template-columns: 1fr; }
  .lp-mgrid { grid-template-columns: 1fr 1fr; gap: 24px; }
  .lp-mcell { border-left: none; padding: 0; }
  .lp-dd__menu { width: 320px; grid-template-columns: 1fr; }
  .lp-dd__hint { display: none; }
  .lp-card__img { height: 180px; }
  #fonctionnement h2 { white-space: normal; }
  #fonctionnement .lp-lead { white-space: normal; font-size: 16px; }
}
@media (max-width: 680px) {
  .lp-nav__login { display: none; }
  .lp-card__img { height: 140px; }
}
@media (max-width: 560px) {
  .lp-mgrid { grid-template-columns: 1fr; }
  .lp-hero { padding: 54px 0 44px; }
  .lp-demo__stats { grid-template-columns: 1fr 1fr; }
  .lp-metrics { padding: 32px 20px; }
  .lp-lead { font-size: 18px; }
}

/* ════════ EFFETS « LIFE » de la maquette (sweep, hovers, scanner, beams, glow, spotlight, chat…) ════════ */

/* vignette douce sur tout l'écran */
.lp::before { content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background: radial-gradient(130% 90% at 50% -12%, transparent 42%, rgba(3,6,5,.55) 100%); }

/* barre de progression du scroll */
.lp-scroll-progress { position: fixed; top: 0; left: 0; height: 2px; width: 0; z-index: 80;
  background: linear-gradient(90deg, var(--lp-green), var(--lp-orange));
  box-shadow: 0 0 12px var(--lp-green); transition: width .08s linear; will-change: width; }

/* halo de lumière qui suit le pointeur */
.lp-cursor-glow { position: fixed; left: 0; top: 0; width: 460px; height: 460px; margin: -230px 0 0 -230px;
  border-radius: 50%; z-index: 1; pointer-events: none; opacity: 0; transition: opacity .7s ease;
  background: radial-gradient(circle, rgba(52,216,160,.09), rgba(232,132,60,.04) 45%, transparent 62%);
  mix-blend-mode: screen; will-change: transform; }
.lp--has-pointer .lp-cursor-glow { opacity: 1; }

@property --lp-hbeam { syntax: '<angle>'; initial-value: 0deg; inherits: false; }

@media (prefers-reduced-motion: no-preference) {
  /* titre : dégradé vivant qui balaie */
  @keyframes lp-heroSheen { 0% { background-position: 0% 50%; } 100% { background-position: 200% 50%; } }
  .lp-hero h1 .lp-hl {
    background: linear-gradient(100deg, #34D8A0 0%, #8ff2cd 28%, #34D8A0 52%, #8ff2cd 78%, #34D8A0 100%);
    background-size: 220% 100%; -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent; color: transparent; animation: lp-heroSheen 7s linear infinite;
  }

  /* cartes & cellules vivantes au survol */
  .lp-card { position: relative; transition: transform .4s cubic-bezier(.2,.8,.2,1), border-color .4s, box-shadow .4s; }
  .lp-card:hover { transform: translateY(-7px); border-color: var(--lp-green-l); box-shadow: 0 34px 70px -34px rgba(52,216,160,.4); }
  .lp-card__ico { transition: transform .45s cubic-bezier(.2,.8,.2,1); }
  .lp-card:hover .lp-card__ico { transform: scale(1.1) rotate(-5deg); }
  .lp-mcell { transition: transform .35s cubic-bezier(.2,.8,.2,1); }
  .lp-mcell:hover { transform: translateY(-5px); }

  /* gros chiffres du constat qui flottent doucement */
  @keyframes lp-floaty { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
  .lp-cstat .lp-cn { animation: lp-floaty 5s ease-in-out infinite; }
  .lp-cstat:nth-child(2) .lp-cn { animation-delay: .7s; }
  .lp-cstat:nth-child(3) .lp-cn { animation-delay: 1.4s; }

  /* soulignement du titre de section qui se dessine à l'apparition */
  .lp-sec-head h2 { position: relative; }
  .lp-sec-head h2::after { content: ""; position: absolute; left: 0; bottom: -11px; height: 3px; width: 58px; border-radius: 2px;
    background: linear-gradient(90deg, var(--lp-green), transparent); transform: scaleX(0); transform-origin: left;
    transition: transform .75s .18s cubic-bezier(.2,.8,.2,1); }
  .lp-sec-head.lp-reveal:not(.lp-reveal--pre) h2::after { transform: scaleX(1); }

  /* carte optimiseur : bord « scanner » rotatif (traitement en direct) */
  .lp-demo::before { content: ""; position: absolute; inset: 0; border-radius: 18px; pointer-events: none; z-index: 3; padding: 1.4px;
    background: conic-gradient(from var(--lp-hbeam), transparent 0deg, transparent 248deg, rgba(52,216,160,.5) 300deg, #9ff3d4 330deg, rgba(52,216,160,.5) 350deg, transparent 360deg);
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor;
    mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); mask-composite: exclude;
    animation: lp-hbeamSpin 4.6s linear infinite; }
  @keyframes lp-hbeamSpin { to { --lp-hbeam: 360deg; } }

  /* « comment ça marche » : impulsion de données qui traverse les 3 étapes */
  .lp-cards { position: relative; }
  .lp-cards::before { content: ""; position: absolute; top: -1px; left: 7%; right: 7%; height: 1px; opacity: .55;
    background: linear-gradient(90deg, transparent, var(--lp-green-l) 18%, var(--lp-green-l) 82%, transparent); }
  .lp-cards::after { content: ""; position: absolute; top: -3.5px; left: 7%; width: 7px; height: 7px; border-radius: 50%;
    background: var(--lp-green); box-shadow: 0 0 16px 2px var(--lp-green); animation: lp-beamRun 4.4s cubic-bezier(.6,0,.4,1) infinite; }
  @keyframes lp-beamRun { 0% { left: 7%; opacity: 0; } 8% { opacity: 1; } 92% { opacity: 1; } 100% { left: 93%; opacity: 0; } }

  /* comparatif : lignes qui glissent à l'apparition + survol */
  .lp-cmp tbody tr { transition: opacity .5s ease, transform .55s cubic-bezier(.2,.85,.25,1), background .3s; }
  .lp-cmp tbody tr:hover td { background: rgba(52,216,160,.06); }
  .lp-cmp-wrap.lp-reveal--pre tbody tr { opacity: 0; transform: translateX(-14px); }
  .lp-cmp tbody tr:nth-child(2) { transition-delay: .07s; }
  .lp-cmp tbody tr:nth-child(3) { transition-delay: .14s; }
  .lp-cmp tbody tr:nth-child(4) { transition-delay: .21s; }
  .lp-cmp tbody tr:nth-child(5) { transition-delay: .28s; }

  /* comparatif : la colonne Helios rayonne en continu */
  @keyframes lp-heColGlow { 0%,100% { box-shadow: inset 0 0 0 rgba(52,216,160,0); } 50% { box-shadow: inset 0 0 34px -8px rgba(52,216,160,.4); } }
  .lp-cmp__he { animation: lp-heColGlow 3.4s ease-in-out infinite; }
  .lp-cmp tbody tr:hover td.lp-cmp__he { animation: none; }

  /* spotlight curseur dans les cartes */
  .lp-card > * { position: relative; z-index: 1; }
  .lp-card::after { content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none; opacity: 0; transition: opacity .45s;
    background: radial-gradient(380px circle at var(--lp-mx,50%) var(--lp-my,50%), rgba(52,216,160,.16), transparent 58%); }
  .lp-card:hover::after { opacity: 1; }

  /* chat mock auto-play (Bascule IA) */
  .lp-chat .lp-chat__row, .lp-chat .lp-switch-note { opacity: 0; transform: translateY(14px); transition: opacity .5s ease, transform .5s cubic-bezier(.2,.85,.25,1); }
  .lp-chat .lp-chat__row.on, .lp-chat .lp-switch-note.on { opacity: 1; transform: none; }
  .lp-chat .lp-switch-note.on { animation: lp-swPulse 1.6s ease-in-out; }
  @keyframes lp-swPulse { 0%,100% { color: var(--lp-text3); } 50% { color: var(--lp-green); } }
  .lp-typing-dots { display: inline-flex; gap: 5px; align-items: center; height: 1em; }
  .lp-typing-dots i { width: 7px; height: 7px; border-radius: 50%; background: var(--lp-green); opacity: .3; animation: lp-typingBlink 1.1s infinite; }
  .lp-typing-dots i:nth-child(2) { animation-delay: .18s; }
  .lp-typing-dots i:nth-child(3) { animation-delay: .36s; }
  @keyframes lp-typingBlink { 0%,70%,100% { opacity: .25; transform: translateY(0); } 35% { opacity: 1; transform: translateY(-3px); } }
}

/* ── prefers-reduced-motion ── */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .001ms !important; animation-iteration-count: 1 !important; transition-duration: .001ms !important; }
  .lp-reveal, .lp-reveal--pre { opacity: 1 !important; transform: none !important; filter: none !important; }
  .lp-bg__sun, .lp-bg__blob, .lp-bg__grid { animation: none !important; }
  .lp-cursor-glow, .lp-hero-canvas, .lp-scroll-progress { display: none !important; }
}
</style>
