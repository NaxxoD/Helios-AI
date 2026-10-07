<template>
  <!-- Floating trigger button -->
  <div class="jessy-root">

    <!-- Bubble avatar trigger -->
    <Transition name="bounce">
      <button
        v-if="!open"
        class="jessy-trigger"
        @click="openJessy()"
        :class="{ pulse: hasPendingMessage }"
        aria-label="Ouvrir Jessy votre guide"
      >
        <JessyAvatar size="52" />
        <div class="trigger-badge" v-if="hasPendingMessage">1</div>
        <div class="trigger-label">Jessy</div>
      </button>
    </Transition>

    <!-- Chat window -->
    <Transition name="slide-up">
      <div v-if="open" class="jessy-window" role="dialog" aria-label="Chat avec Jessy">

        <!-- Header -->
        <div class="jessy-header">
          <div class="jessy-header-left">
            <JessyAvatar size="38" />
            <div class="header-info">
              <div class="header-name">Jessy</div>
              <div class="header-status">
                <span class="status-dot" />
                Guide Helios AI
              </div>
            </div>
          </div>
          <div class="header-actions">
            <button class="hbtn" @click="resetChat" title="Recommencer">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.5"/></svg>
            </button>
            <button class="hbtn" @click="open = false" title="Fermer">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </div>

        <!-- Messages -->
        <div class="jessy-messages" ref="messagesEl">
          <div
            v-for="(msg, i) in messages"
            :key="i"
            :class="['msg-row', msg.from === 'jessy' ? 'msg-jessy' : 'msg-user']"
          >
            <JessyAvatar v-if="msg.from === 'jessy'" size="28" class="msg-avatar" />
            <div class="msg-bubble" v-html="msg.html || msg.text" />
          </div>

          <!-- Typing indicator -->
          <div v-if="typing" class="msg-row msg-jessy">
            <JessyAvatar size="28" class="msg-avatar" />
            <div class="msg-bubble typing-bubble">
              <span class="dot" /><span class="dot" /><span class="dot" />
            </div>
          </div>
        </div>

        <!-- Quick replies -->
        <div v-if="quickReplies.length" class="quick-replies">
          <button
            v-for="qr in quickReplies"
            :key="qr"
            class="qr-btn"
            @click="sendUserMessage(qr)"
          >{{ qr }}</button>
        </div>

        <!-- Input -->
        <div class="jessy-input-row">
          <input
            v-model="userInput"
            class="jessy-input"
            placeholder="Écris ta question…"
            @keydown.enter="sendFromInput"
            maxlength="300"
            ref="inputEl"
          />
          <button class="send-btn" @click="sendFromInput" :disabled="!userInput.trim()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
          </button>
        </div>

      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import JessyAvatar from './JessyAvatar.vue'

const open             = ref(false)
const userInput        = ref('')
const messages         = ref([])
const quickReplies     = ref([])
const typing           = ref(false)
const hasPendingMessage = ref(true)
const messagesEl       = ref(null)
const inputEl          = ref(null)

/* ── Knowledge base ── */
const KB = {
  chat:       `<b>💬 Helios Chat — la feature principale</b><br>Va dans <b>Chat</b>. Tu chattes directement avec OpenAI, Anthropic ou Google via tes clés API.<br><br>Ce qui est unique : <b>chaque message est optimisé avant l'envoi</b> — moins de tokens, même qualité. Tu vois en temps réel l'énergie consommée, le coût et les économies réalisées dans la barre latérale droite 🌿`,
  optimiseur: `<b>⚡ Optimiseur de prompts</b><br>L'optimiseur tourne automatiquement dans le Chat, ou de façon standalone dans <b>Outils → Optimiseur</b>.<br><br>Il fait 3 choses :<br>• <b>Supprime le remplissage</b> — méta-instructions, tournures verbales creuses, politesses inutiles<br>• <b>Attribue un palier</b> — longueur de réponse calibrée selon ta tâche<br>• <b>Calcule les économies</b> — tokens sauvés, dollars économisés, CO₂ évité<br><br>Clique sur <b>↔ Revoir avant envoi</b> pour voir l'original vs l'optimisé avant d'envoyer.`,
  paliers:    `<b>📏 Les paliers de réponse</b><br>Helios contraint la longueur de réponse du LLM selon la tâche :<br><br>• <b>Ultra-court</b> — ~50 mots (salutation, oui/non)<br>• <b>Moyen</b> — ~115 mots (question factuelle)<br>• <b>Code informatique</b> — sans limite de longueur, optimisé pour le code<br>• <b>Documentation</b> — réponse longue et structurée<br><br>En mode <b>Auto</b>, Helios détecte le bon palier tout seul selon ton prompt 🤖`,
  autoroute:  `<b>⚡ Routage automatique</b><br>Active le <b>Routage automatique</b> dans Config. Helios choisit alors le modèle le moins cher adapté à chaque message :<br><br>• Question simple → Gemini Flash (le moins cher)<br>• Analyse comparative → Sonnet ou GPT-4o<br>• Documentation complexe → Opus ou GPT-5<br><br>Tu gardes la qualité, tu réduis la facture automatiquement 💰`,
  upload:     `<b>📤 Importer une conversation</b><br>Va dans <b>Outils → Calculer</b>. Tu exportes ton fichier .txt depuis ChatGPT, Claude ou Gemini, tu choisis ton modèle, et Helios calcule automatiquement l'énergie consommée, le CO₂ et la chaleur récupérable 🌿`,
  manuel:     `<b>✍️ Estimation manuelle</b><br>Va dans <b>Outils → Estimation</b>. Tu choisis ton LLM, le modèle et une intensité (léger à massif). Parfait si tu n'as pas le fichier — l'estimation reste très fiable !`,
  dashboard:  `<b>📊 Ton tableau de bord</b><br>Dans <b>Mon espace</b> tu vois tes stats complètes : énergie totale, CO₂ avec équivalences concrètes (mètres en voiture !), graphiques d'évolution, barre de progression hebdomadaire, et toutes tes sessions. Clique sur une session pour le détail.`,
  co2:        `<b>🌍 CO₂ standard vs éthique</b><br><b>Standard</b> : basé sur le mix énergétique moyen (≈400g CO₂/kWh).<br><b>Éthique</b> : basé sur Infomaniak D4 à Genève — 100% renouvelable, chaleur réutilisée pour chauffer des logements. La différence peut atteindre <b>-96%</b> 🌿`,
  infomaniak: `<b>🏢 Infomaniak D4 (Genève)</b><br>Ce data center récupère 90% de la chaleur de ses serveurs pour chauffer des milliers de logements via le réseau urbain genevois. C'est le modèle de référence d'Helios pour l'impact éthique.`,
  extension:  `<b>🔌 Extension Chrome</b><br>Va dans <b>Outils → Extension</b>. Tu charges le dossier <code>chrome-extension/</code> en mode développeur, et l'overlay apparaît automatiquement sur ChatGPT, Claude.ai et Gemini pour compter tes tokens en temps réel !`,
  modeles:    `<b>🤖 Différences entre modèles</b><br>L'écart peut être <b>×60</b> entre le modèle le plus sobre (Gemini Flash Lite) et le plus gourmand (GPT-5.5-Pro) !<br><br>Helios peut choisir automatiquement le bon modèle via le <b>routage automatique</b> — ou tu peux configurer ta clé API pour chaque provider dans ⚙ Config.`,
  seuil:      `<b>📈 Seuil d'alerte CO₂</b><br>Dans <b>Paramètres</b>, tu définis un seuil CO₂ hebdomadaire. Si tu le dépasses, une barre de progression rouge s'affiche sur ton dashboard. Tu peux aussi le configurer lors du premier login.`,
  compte:     `<b>👤 Ton compte</b><br>Dans <b>Paramètres</b> : modifier ton seuil CO₂, changer ton mot de passe, ou supprimer ton compte. Tes données restent privées.`,
}

/* ── Guided tour steps ── */
const tourSteps = [
  {
    html: `Heyy ! 👋🏾 Je m'appelle <b>Jessy</b>, votre guide Helios AI !<br><br>Je suis là pour t'aider à découvrir la plateforme et répondre à toutes tes questions. C'est parti ? 🌿✨`,
    qr: ['Oui, guide-moi !', "J'ai une question"],
  },
  {
    html: `Super ! 🎉 Helios AI c'est un <b>client LLM qui optimise avant d'envoyer</b>.<br><br>Concrètement, il fait 3 choses qu'aucune autre interface ne fait :<br>⚡ <b>Choisit le bon modèle</b> selon ta question<br>✂️ <b>Nettoie ton prompt</b> avant l'envoi (moins de tokens = moins de CO₂)<br>📊 <b>Mesure l'impact</b> en temps réel — en dollars et en grammes de CO₂<br><br>Par où tu veux commencer ?`,
    qr: ['Le Chat', "L'Optimiseur", 'Importer une conversation', 'Les modèles IA'],
  },
]

let tourIndex = 0

/* ── Init — ouverture manuelle uniquement ── */
let tourStarted = false

function openJessy() {
  open.value = true
  if (!tourStarted) {
    tourStarted = true
    playTourStep(0)
  }
}

watch(open, (v) => {
  if (v) nextTick(() => inputEl.value?.focus())
})

/* ── Core functions ── */
async function playTourStep(idx) {
  if (idx >= tourSteps.length) return
  const step = tourSteps[idx]
  typing.value = true
  await delay(900 + Math.random() * 400)
  typing.value = false
  pushJessy(step.html || step.text, step.qr || [])
  tourIndex = idx + 1
}

function pushJessy(html, qr = []) {
  messages.value.push({ from: 'jessy', html })
  quickReplies.value = qr
  hasPendingMessage.value = false
  scrollBottom()
}

function sendUserMessage(text) {
  if (!text.trim()) return
  messages.value.push({ from: 'user', text })
  quickReplies.value = []
  userInput.value = ''
  scrollBottom()
  handleUserMessage(text)
}

function sendFromInput() {
  if (userInput.value.trim()) sendUserMessage(userInput.value.trim())
}

async function handleUserMessage(text) {
  const t = text.toLowerCase()
  typing.value = true
  await delay(700 + Math.random() * 500)
  typing.value = false

  // Tour continuation
  if (t.includes('oui') || t.includes('guide') || t.includes('parti') || t.includes('découvrir')) {
    if (tourIndex < tourSteps.length) { playTourStep(tourIndex); return }
  }

  // KB matching
  if (t.includes('chat') || t.includes('envoyer') || t.includes('message') || t.includes('convers') || t.includes('clé api') || t.includes('cle api')) {
    pushJessy(KB.chat, ["L'Optimiseur", 'Routage automatique', 'Autre question'])
  } else if (t.includes('palier') || t.includes('longueur') || t.includes('réponse courte') || t.includes('ultra-court') || t.includes('format')) {
    pushJessy(KB.paliers, ["L'Optimiseur", 'Routage automatique', 'Autre question'])
  } else if (t.includes('auto') || t.includes('rout') || t.includes('choisit') || t.includes('automatique') || t.includes('meilleur modèle')) {
    pushJessy(KB.autoroute, ['Les modèles IA', "L'Optimiseur", 'Autre question'])
  } else if (t.includes('optim') || t.includes('prompt') || t.includes('token') || t.includes('remplissage') || t.includes('revoir')) {
    pushJessy(KB.optimiseur, ['Les paliers', 'Routage automatique', 'Autre question'])
  } else if (t.includes('import') || t.includes('upload') || t.includes('fichier') || t.includes('calculer')) {
    pushJessy(KB.upload, ['Estimation manuelle', 'Voir mon dashboard', 'Autre question'])
  } else if (t.includes('manuel') || t.includes('estimation') || t.includes('sans fichier')) {
    pushJessy(KB.manuel, ['Importer une conversation', 'Voir mon dashboard', 'Autre question'])
  } else if (t.includes('dashboard') || t.includes('tableau') || t.includes('stats') || t.includes('espace')) {
    pushJessy(KB.dashboard, ["L'Optimiseur", 'Les modèles IA', 'Autre question'])
  } else if (t.includes('co2') || t.includes('carbone') || t.includes('éthique') || t.includes('standard')) {
    pushJessy(KB.co2, ['Infomaniak D4', 'Les modèles IA', 'Autre question'])
  } else if (t.includes('infomaniak') || t.includes('data center') || t.includes('chaleur') || t.includes('logement')) {
    pushJessy(KB.infomaniak, ['CO₂ standard vs éthique', 'Extension Chrome', 'Autre question'])
  } else if (t.includes('extension') || t.includes('chrome') || t.includes('overlay')) {
    pushJessy(KB.extension, ['Le Chat', 'Les modèles IA', 'Autre question'])
  } else if (t.includes('modèle') || t.includes('model') || t.includes('gpt') || t.includes('claude') || t.includes('gemini') || t.includes('différence')) {
    pushJessy(KB.modeles, ['Routage automatique', "L'Optimiseur", 'Autre question'])
  } else if (t.includes('seuil') || t.includes('alerte') || t.includes('paramètre') || t.includes('notification')) {
    pushJessy(KB.seuil, ['Mon compte', 'Autre question'])
  } else if (t.includes('compte') || t.includes('mot de passe') || t.includes('profil') || t.includes('param')) {
    pushJessy(KB.compte, ['Voir mon dashboard', 'Autre question'])
  } else if (t.includes('autre') || t.includes('question') || t.includes('aide') || t.includes('quoi')) {
    pushJessy(
      `Bonne question ! 🤔 Je peux t'expliquer :<br><br>💬 <b>Le Chat</b> — chatter directement avec les LLMs<br>⚡ <b>L'Optimiseur</b> — réduire tes prompts avant envoi<br>📏 <b>Les paliers</b> — calibrer la longueur des réponses<br>🔀 <b>Le routage automatique</b> — choisir le meilleur modèle<br>📤 Importer une conversation<br>✍️ L'estimation manuelle<br>📊 Ton dashboard<br>🌍 CO₂ standard vs éthique<br>🔌 L'extension Chrome<br><br>Qu'est-ce qui t'intéresse ?`,
      ['Le Chat', "L'Optimiseur", 'Les paliers', 'Routage automatique']
    )
  } else if (t.includes('merci') || t.includes('super') || t.includes('nickel') || t.includes('top')) {
    pushJessy(
      `Avec plaisir ! 💚 N'hésite pas à revenir si tu as d'autres questions. Bonne exploration sur Helios AI ! 🌿✨`,
      ['Autre question']
    )
  } else {
    pushJessy(
      `Hmm, je ne suis pas sûre de comprendre ta question 😅<br>Voici ce sur quoi je peux t'aider :`,
      ['Importer une conversation', 'Les modèles IA', 'CO₂ standard vs éthique', 'Optimiseur']
    )
  }
}

function resetChat() {
  messages.value = []
  quickReplies.value = []
  tourIndex = 0
  hasPendingMessage.value = true
  playTourStep(0)
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)) }

function scrollBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.jessy-root {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 999;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--s-3);
}

/* ── Trigger ── */
.jessy-trigger {
  position: relative;
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  filter: drop-shadow(0 4px 20px rgba(52,211,153,0.4));
  transition: transform 0.2s var(--ease-spring);
}
.jessy-trigger:hover { transform: scale(1.06) translateY(-2px); }

.trigger-badge {
  position: absolute;
  top: -2px; right: -4px;
  width: 18px; height: 18px;
  background: var(--green);
  color: #022c22;
  border-radius: 50%;
  font-size: 10px;
  font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  animation: ping 1.6s ease-in-out infinite;
}
@keyframes ping {
  0%, 100% { box-shadow: 0 0 0 0 var(--green-glow); }
  50%       { box-shadow: 0 0 0 8px transparent; }
}

.trigger-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--green);
  letter-spacing: 0.08em;
  text-shadow: 0 0 10px var(--green-glow);
}

.pulse { animation: floatPulse 2.5s ease-in-out infinite; }
@keyframes floatPulse {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-5px); }
}

/* ── Window ── */
.jessy-window {
  width: 360px;
  max-height: 560px;
  background: var(--bg-card);
  border: 1px solid var(--border-green);
  border-radius: var(--r-2xl);
  box-shadow: 0 8px 60px rgba(0,0,0,0.5), var(--glow-green);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Header */
.jessy-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: linear-gradient(135deg, rgba(52,211,153,0.08), rgba(139,92,246,0.06));
  border-bottom: 1px solid var(--border);
}
.jessy-header-left { display: flex; align-items: center; gap: 10px; }
.header-name   { font-size: 14px; font-weight: 700; color: var(--fg); }
.header-status {
  font-size: 11px; color: var(--green);
  display: flex; align-items: center; gap: 5px;
}
.status-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--green);
  box-shadow: 0 0 6px var(--green);
  animation: blink 2s ease-in-out infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.4} }

.header-actions { display: flex; gap: 4px; }
.hbtn {
  background: none; border: 1px solid var(--border-strong);
  border-radius: var(--r-md); color: var(--fg-muted);
  padding: 5px 7px; cursor: pointer;
  transition: all 0.15s;
}
.hbtn:hover { border-color: var(--green); color: var(--green); background: var(--green-soft); }

/* Messages */
.jessy-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-behavior: smooth;
}
.jessy-messages::-webkit-scrollbar { width: 3px; }
.jessy-messages::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 2px; }

.msg-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
.msg-jessy { justify-content: flex-start; }
.msg-user  { justify-content: flex-end; flex-direction: row-reverse; }

.msg-avatar { flex-shrink: 0; }

.msg-bubble {
  max-width: 82%;
  padding: 10px 13px;
  border-radius: 16px;
  font-size: 13px;
  line-height: 1.55;
}

.msg-jessy .msg-bubble {
  background: var(--jessy-bubble-bg);
  border: 1px solid var(--jessy-bubble-border);
  border-bottom-left-radius: 4px;
  color: var(--fg-2);
}
.msg-jessy .msg-bubble :deep(b) { color: var(--green); }
.msg-jessy .msg-bubble :deep(code) {
  font-family: var(--font-mono);
  background: var(--bg-surface-2);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--violet-hover);
}

.msg-user .msg-bubble {
  background: var(--jessy-user-bg);
  border: 1px solid var(--jessy-user-border);
  border-bottom-right-radius: 4px;
  color: var(--fg);
}

/* Typing */
.typing-bubble {
  display: flex; align-items: center; gap: 4px;
  padding: 12px 14px;
  min-width: 54px;
}
.dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--green);
  animation: typingDot 1.2s ease-in-out infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes typingDot {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* Quick replies */
.quick-replies {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 14px;
  border-top: 1px solid var(--border);
}
.qr-btn {
  background: var(--green-soft);
  border: 1px solid var(--border-green);
  color: var(--green);
  padding: 6px 12px;
  border-radius: var(--r-pill);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.qr-btn:hover {
  background: var(--green);
  color: #022c22;
  border-color: var(--green);
  box-shadow: 0 0 10px var(--green-glow);
}

/* Input */
.jessy-input-row {
  display: flex;
  gap: 8px;
  padding: 12px 14px;
  border-top: 1px solid var(--border);
  background: var(--bg-surface);
}
.jessy-input {
  flex: 1;
  background: var(--bg-input);
  border: 1px solid var(--border-strong);
  border-radius: var(--r-pill);
  color: var(--fg-2);
  padding: 9px 14px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}
.jessy-input:focus { border-color: var(--green); box-shadow: 0 0 0 2px var(--green-soft); }
.jessy-input::placeholder { color: var(--fg-dim); }

.send-btn {
  width: 36px; height: 36px;
  background: var(--green);
  border: none;
  border-radius: 50%;
  color: #022c22;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: opacity 0.15s, box-shadow 0.15s;
  box-shadow: 0 0 12px var(--green-glow);
}
.send-btn:hover:not(:disabled) { opacity: 0.88; box-shadow: 0 0 20px var(--green-glow); }
.send-btn:disabled { opacity: 0.35; cursor: not-allowed; box-shadow: none; }

/* Transitions */
.slide-up-enter-active {
  transition: opacity 0.3s var(--ease-out), transform 0.3s var(--ease-out);
}
.slide-up-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.slide-up-enter-from { opacity: 0; transform: translateY(20px) scale(0.96); }
.slide-up-leave-to   { opacity: 0; transform: translateY(12px) scale(0.97); }

.bounce-enter-active { transition: all 0.35s var(--ease-spring); }
.bounce-leave-active { transition: all 0.2s ease; }
.bounce-enter-from   { opacity: 0; transform: scale(0.6); }
.bounce-leave-to     { opacity: 0; transform: scale(0.8); }
</style>
