<template>
  <nav class="navbar">
    <RouterLink to="/" class="brand">
      <HeliosLogo :size="24" />
      <span>Helios<span class="brand-ai"> AI</span></span>
    </RouterLink>

    <button class="burger" @click="showMenu = !showMenu" :aria-label="showMenu ? 'Fermer le menu' : 'Ouvrir le menu'">
      <span></span><span></span><span></span>
    </button>

    <div class="nav-links" :class="{ 'nav-open': showMenu }">
      <!-- Outils — popup click, visible pour tous -->
      <div class="nav-outils" ref="outilsRef">
        <button class="nav-outils-trigger" @click="showOutils = !showOutils">
          Outils <span class="caret">{{ showOutils ? '▲' : '▾' }}</span>
        </button>
        <Transition name="outils-fade">
          <div v-show="showOutils" class="outils-panel">
            <div class="outils-left">
              <div
                v-for="tool in TOOLS"
                :key="tool.id"
                class="outils-item"
                @mouseenter="hoveredTool = tool.id"
                @mouseleave="hoveredTool = null"
                @click="navigateTool(tool)"
              >
                <span class="outils-name">{{ tool.name }}</span>
                <span v-if="!isAuthenticated" class="outils-lock">·</span>
              </div>
            </div>
            <div class="outils-right">
              <Transition name="desc-fade" mode="out-in">
                <div v-if="hoveredTool" :key="hoveredTool" class="outils-desc">
                  <div class="desc-title">{{ TOOLS.find(t => t.id === hoveredTool)?.name }}</div>
                  <p class="desc-text">{{ TOOLS.find(t => t.id === hoveredTool)?.desc }}</p>
                  <span v-if="!isAuthenticated" class="desc-auth">Connexion requise</span>
                </div>
                <div v-else class="outils-desc outils-desc--empty">
                  <p>Survolez un outil pour en savoir plus.</p>
                </div>
              </Transition>
            </div>
          </div>
        </Transition>
      </div>

      <template v-if="isAuthenticated">
        <span class="nav-sep"></span>
        <RouterLink to="/user/dashboard">Mon bilan</RouterLink>
        <RouterLink to="/historique">Historique</RouterLink>
        <RouterLink to="/parametres" class="nav-secondary">Paramètres</RouterLink>
        <RouterLink v-if="isAdmin" to="/admin/dashboard" class="btn-admin">Admin</RouterLink>
        <button class="btn-logout" @click="handleDeconnexion">Déconnexion</button>
      </template>
      <template v-else>
        <RouterLink to="/inscription">Inscription</RouterLink>
        <RouterLink to="/connexion" class="btn-login">Connexion</RouterLink>
      </template>

      <button class="btn-theme" @click="toggle" :title="theme === 'dark' ? 'Mode clair' : 'Mode sombre'">
        {{ theme === 'dark' ? '☀' : '◑' }}
      </button>
    </div>
  </nav>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useAuth } from '../composables/useAuth.js'
import HeliosLogo from './HeliosLogo.vue'
import { useTheme } from '../composables/useTheme.js'
import { useRouter } from 'vue-router'

const { isAuthenticated, isAdmin, deconnexion } = useAuth()
const { theme, toggle } = useTheme()
const router = useRouter()

const showOutils  = ref(false)
const showMenu    = ref(false)
const hoveredTool = ref(null)
const outilsRef   = ref(null)

const TOOLS = [
  {
    id: 'optimiseur', name: 'Optimiseur',
    route: '/optimiseur',
    desc: 'Analyse votre prompt et supprime le bruit avant l\'envoi — formules de politesse, méta-instructions, répétitions. Résultat instantané, aucun appel API supplémentaire.',
  },
  {
    id: 'upload', name: 'Analyser une conversation',
    route: '/upload',
    desc: 'Importez un export ChatGPT, Claude ou Gemini et calculez l\'énergie consommée, le CO₂ et le coût réel de votre session.',
  },
  {
    id: 'manuel', name: 'Calcul rapide',
    route: '/manuel',
    desc: 'Estimez l\'impact d\'un échange en saisissant manuellement le nombre de tokens et le modèle utilisé. Résultat immédiat.',
  },
  {
    id: 'extension', name: 'Extension Chrome',
    route: '/extension',
    desc: 'Intégration directe sur ChatGPT, Claude.ai et Gemini. Comptez vos tokens et suivez votre impact sans changer d\'interface.',
  },
]

function navigateTool(tool) {
  showOutils.value = false
  hoveredTool.value = null
  if (!isAuthenticated.value) {
    router.push('/connexion')
  } else {
    router.push(tool.route)
  }
}

function handleDeconnexion() {
  deconnexion()
  router.push('/')
}

function onClickOutside(e) {
  if (outilsRef.value && !outilsRef.value.contains(e.target)) {
    showOutils.value = false
    hoveredTool.value = null
  }
}

onMounted(() => document.addEventListener('mousedown', onClickOutside))
onUnmounted(() => document.removeEventListener('mousedown', onClickOutside))
</script>

<style scoped>
.navbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--s-4) var(--s-8); background: var(--bg-surface); border-bottom: 1px solid var(--border);
  position: relative;
}
.brand {
  display: flex; align-items: center; gap: 8px;
  font-size: 1.2rem; font-weight: var(--fw-bold); color: var(--fg);
  text-decoration: none; letter-spacing: .005em;
  font-family: "Chakra Petch", var(--font-sans), sans-serif;
}
.brand-ai { color: #34D8A0; }
.nav-links { display: flex; align-items: center; gap: 20px; }
.nav-links a { color: var(--fg-muted); text-decoration: none; font-size: var(--t-base); transition: color var(--t-fast); }
.nav-links a:hover, .nav-links a.router-link-active { color: var(--fg); }

.btn-login {
  background: var(--accent); color: #fff !important; padding: 6px 14px;
  border-radius: var(--r-md); font-weight: var(--fw-semibold);
}
.btn-chat {
  background: var(--accent); color: #fff !important; padding: 6px 14px;
  border-radius: var(--r-md); font-weight: var(--fw-semibold); font-size: var(--t-base);
}
.btn-admin {
  background: var(--co2-avoided); color: #fff !important; padding: 6px 14px;
  border-radius: var(--r-md); font-weight: var(--fw-semibold); font-size: var(--t-base);
}
.btn-logout {
  background: none; border: 1px solid var(--danger); color: var(--danger);
  padding: 6px 14px; border-radius: var(--r-md); cursor: pointer; font-size: var(--t-base);
}
.nav-sep { width: 1px; height: 20px; background: var(--border); flex-shrink: 0; }
.nav-secondary { font-size: var(--t-sm) !important; color: var(--fg-dim) !important; }
.nav-secondary:hover, .nav-secondary.router-link-active { color: var(--fg-muted) !important; }
.btn-theme {
  background: none; border: 1px solid var(--border); color: var(--fg-muted);
  padding: 5px 10px; border-radius: var(--r-md); cursor: pointer; font-size: 1rem;
  transition: border-color var(--t-fast), color var(--t-fast);
}
.btn-theme:hover { border-color: var(--accent); color: var(--fg); }

/* ── Outils popup ─────────────────────────────── */
.nav-outils { position: relative; }

.nav-outils-trigger {
  background: none; border: none; cursor: pointer;
  font-size: var(--t-base); color: var(--fg-muted); padding: 0;
  display: flex; align-items: center; gap: 4px;
  transition: color var(--t-fast);
}
.nav-outils-trigger:hover { color: var(--fg); }
.caret { font-size: 0.6rem; opacity: 0.6; }

.outils-panel {
  position: absolute; top: calc(100% + 12px); left: 50%;
  transform: translateX(-50%);
  display: grid; grid-template-columns: 200px 220px;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); box-shadow: 0 12px 32px rgba(0,0,0,0.4);
  z-index: 200; overflow: hidden;
}

.outils-left {
  padding: var(--s-3) 0; border-right: 1px solid var(--border);
}
.outils-item {
  display: flex; align-items: center; gap: var(--s-3);
  padding: 10px var(--s-4); cursor: pointer;
  transition: background var(--t-fast);
  font-size: var(--t-sm); color: var(--fg-muted);
}
.outils-item:hover { background: var(--bg-base); color: var(--fg); }
.outils-icon { font-size: 1rem; flex-shrink: 0; }
.outils-name { flex: 1; }
.outils-lock { font-size: var(--t-xs); color: var(--fg-dim); }

.outils-right {
  padding: var(--s-4);
  display: flex; align-items: flex-start;
}
.outils-desc {
  width: 100%;
}
.outils-desc--empty p {
  color: var(--fg-dim); font-size: var(--t-sm); font-style: italic;
  margin: 0; padding-top: var(--s-2);
}
.desc-title {
  font-size: var(--t-sm); font-weight: var(--fw-semibold);
  color: var(--accent); margin-bottom: var(--s-2);
}
.desc-text {
  font-size: var(--t-sm); color: var(--fg-muted);
  line-height: 1.5; margin: 0 0 var(--s-3);
}
.desc-auth {
  font-size: var(--t-xs); color: var(--fg-dim);
  border: 1px solid var(--border); border-radius: var(--r-sm);
  padding: 2px 6px;
}

/* Transitions */
.outils-fade-enter-active, .outils-fade-leave-active { transition: opacity .15s, transform .15s; }
.outils-fade-enter-from, .outils-fade-leave-to { opacity: 0; transform: translateX(-50%) translateY(-6px); }

.desc-fade-enter-active, .desc-fade-leave-active { transition: opacity .1s; }
.desc-fade-enter-from, .desc-fade-leave-to { opacity: 0; }

/* ── Burger mobile ────────────────────────────── */
.burger {
  display: none; flex-direction: column; justify-content: center; gap: 5px;
  background: none; border: none; cursor: pointer; padding: 4px; width: 32px;
}
.burger span {
  display: block; height: 2px; width: 100%;
  background: var(--fg-muted); border-radius: 2px; transition: background var(--t-fast);
}
.burger:hover span { background: var(--fg); }

@media (max-width: 768px) {
  .navbar { padding: var(--s-3) var(--s-4); }
  .burger { display: flex; }
  .nav-links {
    display: none; position: absolute; top: 100%; left: 0; right: 0;
    flex-direction: column; align-items: flex-start; gap: 0;
    background: var(--bg-surface); border-bottom: 1px solid var(--border);
    padding: var(--s-3) var(--s-4); z-index: 100;
    max-height: calc(100vh - 56px); overflow-y: auto;
  }
  .nav-links.nav-open { display: flex; }
  .nav-links a, .nav-links button { width: 100%; padding: 10px 0; font-size: var(--t-base); }
  .nav-sep { display: none; }
  .nav-outils { width: 100%; }
  .outils-panel {
    position: static; transform: none; grid-template-columns: 1fr;
    box-shadow: none; border: 1px solid var(--border); margin-top: var(--s-2);
  }
  .outils-right { display: none; }
}
</style>
