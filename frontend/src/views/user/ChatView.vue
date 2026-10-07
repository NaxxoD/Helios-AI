<template>
  <div class="chat-outer">

  <!-- ── Historique conversations ── -->
  <aside class="chat-history" v-if="isAuthenticated" :class="{ 'tab-hidden': activeTab !== 'history' }">
    <div class="history-header">
      <span class="history-logo">Helios AI</span>
      <button class="history-new" @click="startNewConversation">+ Nouvelle conversation</button>
      <button class="mobile-back" @click="activeTab = 'chat'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </button>
    </div>
    <div class="history-list">
      <template v-if="conversations.length > 0">
        <template v-for="group in conversationGroups" :key="group.label">
          <div class="conv-group-label">{{ group.label }}</div>
          <button
            v-for="conv in group.items" :key="conv.id"
            class="conv-item"
            :class="{ active: conv.id === conversationId }"
            @click="openConversation(conv.id)"
          >
            <div class="conv-title">{{ conv.title }}</div>
            <div class="conv-meta">
              <span class="conv-time">{{ formatConvTime(conv.updated_at) }}</span>
              <span class="conv-badge" :class="`conv-badge--${conv.impact_level}`">{{ conv.impact_level }}</span>
              <span class="conv-tokens">{{ conv.tokens_total.toLocaleString() }} tk</span>
            </div>
          </button>
        </template>
      </template>
      <div v-else class="history-empty">Aucune conversation sauvegardée</div>
    </div>
    <div class="history-footer">
      <RouterLink to="/user/dashboard" class="history-foot-btn">Mon espace</RouterLink>
      <RouterLink to="/historique" class="history-foot-btn">Historique</RouterLink>
      <RouterLink to="/parametres" class="history-foot-btn">Paramètres</RouterLink>
      <button class="history-foot-btn history-logout" @click="handleLogout">Déconnexion</button>
    </div>
  </aside>

  <!-- ── Sidebar live ── -->
  <aside class="chat-sidebar" :class="{ 'tab-hidden': activeTab !== 'stats' }">
    <div class="sidebar-title">
      ⚡ Session en cours
      <button class="mobile-back" @click="activeTab = 'chat'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      </button>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-label">Tokens envoyés</div>
      <div class="sidebar-value">{{ (sessionTotalInputTokens + sessionTotalOutputTokens).toLocaleString() || '—' }}</div>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-label">CO₂ estimé</div>
      <div class="sidebar-value">{{ sessionCO2g > 0 ? formatSessionCO2(sessionCO2g) + ' CO₂' : '—' }}</div>
      <div class="sidebar-sub" v-if="sessionCO2g > 0">
        ≈ {{ co2ToMeters(sessionCO2g) }}
      </div>
    </div>

    <div class="sidebar-block">
      <div class="sidebar-label">Coût session</div>
      <div class="sidebar-value">{{ sessionTotalCost > 0 ? formatCost(sessionTotalCost) : '—' }}</div>
    </div>

    <div class="sidebar-block" :class="{ 'sidebar-block--savings': sessionTokensSaved > 0 }">
      <div class="sidebar-label">Économies optim.</div>
      <div class="sidebar-value sidebar-value--green">
        {{ sessionTokensSaved > 0 ? '−' + sessionTokensSaved + ' tokens' : '—' }}
      </div>
    </div>

    <div class="sidebar-sep"></div>

    <div class="sidebar-block">
      <div class="sidebar-label">Modèle actif</div>
      <div class="sidebar-value sidebar-value--model">{{ model || '—' }}</div>
      <div class="sidebar-sub" v-if="provider">{{ provider }}</div>
      <div class="sidebar-sub" style="color:#a78bfa">
        effort :
        <span v-if="selectedEffort">{{ selectedEffort }}</span>
        <span v-else-if="lastSuggestedEffort && lastSuggestedModelTier">
          auto <span style="opacity:.5">→</span> {{ lastSuggestedEffort }}
          <span style="opacity:.4;font-size:.55rem"> (si routé)</span>
        </span>
        <span v-else-if="lastSuggestedEffort">
          auto <span style="opacity:.5">→</span> {{ lastSuggestedEffort }}
        </span>
        <span v-else>auto</span>
      </div>
    </div>

    <div class="sidebar-block" v-if="sessionMsgCount > 0">
      <div class="sidebar-label">Échanges</div>
      <div class="sidebar-value">{{ sessionMsgCount }}</div>
    </div>

    <!-- Dernière analyse -->
    <template v-if="hasAnalysis">
      <div class="sidebar-sep"></div>
      <div class="sidebar-title">📊 Dernière analyse</div>

      <div class="sidebar-block sidebar-block--flat">
        <div class="sidebar-row">
          <span class="sidebar-label">Compression</span>
          <span class="sidebar-value sidebar-value--accent">−{{ savedPct }}%</span>
        </div>
        <div class="sidebar-row">
          <span class="sidebar-label">Tokens</span>
          <span class="sidebar-value sidebar-value--sm">{{ originalTokens }} → {{ optimizedTokens }}</span>
        </div>
      </div>

      <div class="sidebar-block sidebar-block--flat">
        <div class="sidebar-label">Qualité</div>
        <span class="badge-pertinence badge-pertinence--sm" :class="pertinenceBadge.cls">
          <span class="badge-dot"></span>{{ pertinenceBadge.label }}
        </span>
      </div>

      <div class="sidebar-block sidebar-block--flat" v-if="detectedPalier">
        <div class="sidebar-label">Format détecté</div>
        <div class="sidebar-value sidebar-value--sm" style="display:flex;align-items:center;gap:5px">
          <PalierIcon :palier="detectedPalier.key" :size="13" />{{ detectedPalier.label }}
        </div>
      </div>

      <div class="sidebar-block sidebar-block--flat" v-if="estimatedOutputTokens">
        <div class="sidebar-row">
          <span class="sidebar-label">Réponse estimée</span>
          <span class="sidebar-value sidebar-value--sm">~{{ estimatedOutputTokens }} tokens</span>
        </div>
        <div class="sidebar-row" v-if="exchangeCostUsd != null">
          <span class="sidebar-label">Coût échange</span>
          <span class="sidebar-value sidebar-value--sm">{{ formatCostHuman(exchangeCostUsd) }}</span>
        </div>
        <div class="sidebar-row sidebar-row--savings" v-if="totalSavingsUsd">
          <span class="sidebar-label">Économies</span>
          <span class="sidebar-value sidebar-value--green">−{{ formatCostHuman(totalSavingsUsd) }}</span>
        </div>
      </div>

      <div class="sidebar-block sidebar-block--density" v-if="isGenericPrompt">
        <div class="sidebar-label">⚠ Remplissage détecté</div>
        <div class="density-mini">
          <div class="density-mini-fill" :style="{ width: (1 - junkDensity) * 100 + '%' }"></div>
          <div class="density-mini-junk" :style="{ width: junkDensity * 100 + '%' }"></div>
        </div>
        <div class="sidebar-row">
          <span style="font-size:var(--t-xs);color:#4ade80">Utile {{ Math.round((1-junkDensity)*100) }}%</span>
          <span style="font-size:var(--t-xs);color:#fbbf24">Remplissage {{ Math.round(junkDensity*100) }}%</span>
        </div>
      </div>

      <div class="sidebar-block sidebar-block--reco" v-if="recommendedModel">
        <div class="sidebar-label">💡 Modèle recommandé</div>
        <div class="sidebar-value sidebar-value--model">{{ recommendedModel }}</div>
        <button class="btn-apply-reco-side" @click="applyRecommendation">Appliquer</button>
      </div>
    </template>
  </aside>

  <!-- ── Zone principale chat ── -->
  <div class="chat-layout" :class="{ 'tab-hidden': activeTab !== 'chat' }">

    <transition name="fade">
      <div v-if="toastMsg" class="toast">{{ toastMsg }}</div>
    </transition>

    <!-- Header -->
    <div class="chat-header">
      <div class="header-left">
        <div class="title-tabs-row">
          <h1 class="chat-title">Helios Chat</h1>
          <nav class="mobile-tabs">
            <button class="mobile-tab" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
            </button>
            <button class="mobile-tab" :class="{ active: activeTab === 'chat' }" @click="activeTab = 'chat'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </button>
            <button class="mobile-tab" :class="{ active: activeTab === 'stats' }" @click="activeTab = 'stats'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 14l3-4 3 3 4-7"/></svg>
            </button>
          </nav>
        </div>
        <span v-if="sessionMsgCount === 0" class="chat-sub">Chaque message est analysé et optimisé avant envoi</span>
        <span v-else class="chat-sub session-live">
          {{ sessionMsgCount }} échange{{ sessionMsgCount > 1 ? 's' : '' }}
          · {{ (sessionTotalInputTokens + sessionTotalOutputTokens).toLocaleString() }} tokens
          <template v-if="sessionTotalCost > 0"> · {{ formatCost(sessionTotalCost) }}</template>
          <template v-if="sessionTokensSaved > 0"> · <span class="live-accent">✦ {{ sessionTokensSaved }} sauvés</span></template>
          <template v-if="sessionCO2g > 0"> · {{ formatSessionCO2(sessionCO2g) }} CO₂</template>
        </span>
      </div>
      <div class="header-controls">
        <button class="btn-export" v-if="messages.length > 0" @click="exportConversation" title="Exporter la conversation">
          ↓ Exporter
        </button>
        <button class="btn-config" :class="{ active: apiKey }" @click="showKeyPanel = !showKeyPanel">
          ⚙ Config<span v-if="apiKey" class="config-dot"> ●</span>
        </button>
      </div>
    </div>

    <!-- Panneau config -->
    <transition name="slide">
      <div v-if="showKeyPanel" class="config-panel">
        <div class="config-panel-header">
          <span class="config-title">Configuration LLM</span>
          <button class="btn-close-panel" @click="showKeyPanel = false">×</button>
        </div>

        <!-- Modèle par défaut -->
        <div class="config-row" v-if="providers.length">
          <span class="config-label">Modèle par défaut</span>
          <select v-model="provider" @change="onProviderChange" class="sel">
            <option
              v-for="g in providers"
              :key="g.provider"
              :value="g.provider"
              :disabled="COMING_SOON_PROVIDERS.has(g.provider)"
            >{{ g.provider }}{{ COMING_SOON_PROVIDERS.has(g.provider) ? ' — bientôt' : '' }}</option>
          </select>
          <select v-model="model" class="sel" :disabled="!modelsForProvider.length">
            <option v-for="m in modelsForProvider" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <span v-else class="sel-loading">Chargement des modèles…</span>

        <!-- Effort (thinking) -->
        <div class="config-row" v-if="effortOptions.length">
          <span class="config-label">Effort (thinking)</span>
          <select v-model="selectedEffort" class="sel">
            <option :value="null">Auto</option>
            <option v-for="e in effortOptions" :key="e.id" :value="e.id">{{ e.label }}</option>
          </select>
          <span class="effort-hint" v-if="selectedEffort">
            {{ selectedEffort === 'off' ? '— thinking désactivé' :
               selectedEffort === 'on'  ? '— thinking léger (1k tokens)' :
               selectedEffort === 'low' ? '— 1k tokens thinking' :
               selectedEffort === 'medium' || selectedEffort === 'standard' ? '— 5k tokens thinking' :
               selectedEffort === 'high'   ? '— 16k tokens thinking' :
               selectedEffort === 'xhigh'  ? '— 32k tokens thinking' :
               selectedEffort === 'max'    ? '— 64k tokens thinking' : '' }}
          </span>
        </div>

        <!-- Clés par provider -->
        <div class="config-keys-title">
          Clés API
          <span class="key-note">stockées en session uniquement — jamais envoyées au serveur</span>
        </div>
        <div class="config-provider-row" v-for="p in ALL_PROVIDERS" :key="p">
          <span class="provider-name">{{ p }}</span>
          <span class="provider-status" :class="getProviderKey(p) ? 'has-key' : 'no-key'">
            {{ getProviderKey(p) ? '●' : '○' }}
          </span>
          <template v-if="editingProvider === p">
            <input
              v-model="keyInput"
              :type="keyVisible ? 'text' : 'password'"
              class="key-input"
              :placeholder="keyPlaceholder(p)"
              @keydown.enter="saveKeyFor(p)"
              @keydown.escape="editingProvider = null"
            />
            <button class="btn-eye" @click="keyVisible = !keyVisible">{{ keyVisible ? '🙈' : '👁' }}</button>
            <button class="btn-save-key" @click="saveKeyFor(p)">OK</button>
            <button class="btn-clear-key" @click="editingProvider = null">Annuler</button>
          </template>
          <template v-else>
            <button class="btn-edit-key" @click="startEditKey(p)">
              {{ getProviderKey(p) ? 'Modifier' : 'Ajouter' }}
            </button>
            <button v-if="getProviderKey(p)" class="btn-clear-key" @click="clearKeyFor(p)">Effacer</button>
          </template>
        </div>

        <!-- Routage auto -->
        <label class="config-autoroute">
          <input type="checkbox" v-model="autoRoute" />
          <span>Routage automatique — choisit le modèle optimal par message</span>
        </label>
      </div>
    </transition>

    <!-- Zone messages -->
    <div class="messages-area" ref="messagesEl">

      <transition name="fade">
        <div v-if="modelChangedWarning" class="model-warning">
          ⚠ Modèle changé — l'historique sera envoyé au nouveau modèle
        </div>
      </transition>


      <!-- État vide -->
      <div v-if="messages.length === 0 && !loading" class="empty-chat">
        <div class="empty-icon"><svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div>
        <p class="empty-title">Démarrez une conversation</p>
        <p class="empty-sub">Vos prompts sont optimisés avant l'envoi — l'optimisation retire les tokens superflus sans altérer le sens.</p>
      </div>

      <template v-for="(msg, i) in messages" :key="i">
        <!-- Séparateur de compaction -->
        <div v-if="msg._compacted && msg.role === 'user'" class="compact-sep">
          — historique résumé automatiquement —
        </div>
        <div v-if="!msg._compacted" class="msg-wrap" :class="msg.role">
          <div class="bubble" :class="{ 'is-error': msg.isError }">
            <div
              class="bubble-content"
              v-if="msg.role === 'assistant'"
              v-html="msg.isError ? escapeHtml(msg.content) : formatMarkdown(msg.content)"
            ></div>
            <div class="bubble-content" v-else>{{ msg.content }}</div>
            <div v-if="msg.impact" class="bubble-meta">
              <div>{{ msg.input_tokens }} envoyés · {{ msg.output_tokens }} reçus<span v-if="msg.cost_usd != null"> · {{ formatCost(msg.cost_usd) }}</span></div>
              <div>{{ formatCO2(msg.impact) }}</div>
            </div>
            <div v-if="msg.routed_model" class="bubble-routed">⚡ {{ msg.routed_model }}</div>
            <div v-if="msg.optimized" class="bubble-optimized">
              ✦ Prompt optimisé (−{{ msg.savedPct }}%)<span v-if="msg.pertinenceScore && msg.pertinenceScore < 100"> · pertinence {{ msg.pertinenceScore }}%</span>
            </div>
            <div v-if="msg.optimized && msg.qualityNote" class="bubble-quality">
              <span class="qn-score" :class="msg.qualityNote.global >= 75 ? 'qn-good' : msg.qualityNote.global >= 45 ? 'qn-mid' : 'qn-low'">★ {{ msg.qualityNote.global }}</span>
              <span class="qn-sep">·</span>
              <span class="qn-axes">Clarté {{ msg.qualityNote.clarte }} · Spéc. {{ msg.qualityNote.specificite }} · Struct. {{ msg.qualityNote.structure }} · Conc. {{ msg.qualityNote.concision }}</span>
            </div>
          </div>
        </div>
      </template>

      <div v-if="loading" class="msg-wrap assistant">
        <div class="bubble thinking">
          <span></span><span></span><span></span>
        </div>
        <button v-if="optimizedText" class="btn-optim-peek" @click="showOptimModal = true">
          ✦ Voir l'optimisation
        </button>
      </div>
    </div>

    <!-- Zone de saisie -->
    <div class="input-area">

      <div class="optimize-bar">
        <button class="opt-toggle" :class="{ on: optimizeOn, 'opt-badge': optimizeOn }" @click="toggleOptimize">
          {{ optimizeOn ? '✦ Optimisation activée' : 'Optimisation désactivée' }}
        </button>
        <button v-if="inputText.trim()" class="btn-review" :disabled="analysing" @click="analyse">
          <svg v-if="!analysing" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:4px"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          {{ analysing ? '…' : 'Aperçu' }}
        </button>
      </div>

      <div class="step">
        <div class="step-header" v-if="inputText">
          <span class="token-count">~{{ estimateTokens(inputText) }} tokens</span>
        </div>
        <textarea
          ref="inputEl"
          v-model="inputText"
          class="chat-input"
          :placeholder="optimizeOn ? 'Tapez votre prompt…' : 'Tapez votre message…'"
          @input="e => autoResize(e.target)"
          @keydown.enter.exact.prevent="optimizeOn ? analyseAndSend() : sendDirect()"
          @keydown.enter.shift.exact="inputText += '\n'"
        ></textarea>
        <div class="step-actions">
          <template v-if="optimizeOn">
            <select v-model="selectedPalier" class="sel-palier">
              <option v-for="(info, key) in PALIERS" :key="key" :value="key">
                {{ info.label }}
              </option>
            </select>
            <button class="btn-primary" :disabled="!inputText.trim() || analysing || !canSend" @click="analyseAndSend">
              {{ analysing ? 'Envoi…' : '↑ Envoyer' }}
            </button>
          </template>
          <button v-else class="btn-primary" :disabled="!canSend" @click="sendDirect">Envoyer →</button>
        </div>
      </div>

      <div class="input-footer">
        <p v-if="isAuthenticated && canSendReason" class="cant-send-hint">{{ canSendReason }}</p>
        <div v-else-if="!isAuthenticated && guestLimitReached" class="guest-limit-banner">
          <span>{{ GUEST_LIMIT }} échanges gratuits utilisés —</span>
          <RouterLink to="/inscription" class="guest-limit-link">Créer un compte gratuit</RouterLink>
          <span>pour continuer et sauvegarder votre historique</span>
        </div>
        <p v-else-if="!isAuthenticated" class="guest-hint">
          {{ GUEST_LIMIT - guestExchangeCount }} échange{{ GUEST_LIMIT - guestExchangeCount > 1 ? 's' : '' }} gratuit{{ GUEST_LIMIT - guestExchangeCount > 1 ? 's' : '' }} restant —
          <RouterLink to="/connexion">connectez-vous</RouterLink> pour un accès illimité et le tracking CO₂.
        </p>
        <p v-else class="input-hint">Entrée = Envoyer · Shift+Entrée = saut de ligne</p>
      </div>
    </div>

    <!-- Modal comparaison optimiseur -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showOptimModal" class="modal-overlay" @click.self="closeModal">
          <div class="modal-card">

            <div class="modal-header">
              <div class="modal-header-left">
                <h2 class="modal-title">Résultat de l'optimisation</h2>
                <span v-if="optimizeErrorMsg" class="modal-error-badge">⚠ {{ optimizeErrorMsg }}</span>
              </div>
              <button class="modal-close" @click="closeModal">×</button>
            </div>

            <div class="modal-compare">
              <div class="compare-pane">
                <div class="pane-label">ORIGINAL</div>
                <div class="pane-text" :class="{ 'pane-scanning': analysePhase === 'reading' }">{{ originalPromptText }}</div>
                <div v-if="analysePhase === 'reading'" class="pane-reading-hint">Lecture du bruit conversationnel…</div>
              </div>
              <div class="compare-pane">
                <div class="pane-label optimized-label">
                  OPTIMISÉ
                  <span v-if="qwenAvailable && gainEstime !== 'faible'" class="qwen-badge">★ Qwen</span>
                  <span class="pane-edit-hint" v-if="analysePhase === 'done'">(modifiable)</span>
                  <span class="pane-edit-hint writing-hint" v-else-if="analysePhase === 'writing'">réécriture…</span>
                </div>
                <!-- Phase lecture -->
                <div v-if="analysePhase === 'reading'" class="pane-textarea pane-loading">
                  <span class="loading-dot"></span><span class="loading-dot"></span><span class="loading-dot"></span>
                </div>
                <!-- Phase réécriture : typewriter -->
                <div v-else-if="analysePhase === 'writing'" class="pane-textarea pane-typewriter">{{ displayedOptimText }}<span class="cursor-blink">|</span></div>
                <!-- Phase terminée : éditable -->
                <textarea
                  v-else
                  v-model="optimizedText"
                  class="pane-textarea"
                  :class="{ 'has-error': optimizeErrorMsg }"
                ></textarea>
                <div v-if="palierConstraint && analysePhase === 'done'" class="constraint-chip">
                  <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                  <span class="constraint-text">{{ palierConstraint }}</span>
                  <span class="constraint-label">injecté via system prompt · non déductible</span>
                </div>
              </div>
            </div>

            <!-- E3 — Chips de complétion guidée -->
            <div v-if="chips.length && analysePhase === 'done' && !optimizeErrorMsg" class="modal-chips">
              <p class="chips-hint">Slots manquants — cliquez pour compléter le prompt :</p>
              <div v-for="chip in chips" :key="chip.slot" class="chip-row">
                <span class="chip-label">{{ chip.label }}</span>
                <div class="chip-options">
                  <button
                    v-for="opt in chip.options"
                    :key="opt"
                    class="chip-opt"
                    @click="applyChipInModal(chip.slot, chip.label, opt)"
                  >{{ opt }}</button>
                </div>
              </div>
            </div>

            <div class="modal-stats" v-if="!optimizeErrorMsg">
              <div class="stat-item">
                <span class="badge-pertinence" :class="pertinenceBadge.cls">
                  <span class="badge-dot"></span>{{ pertinenceBadge.label }}
                </span>
                <span class="stat-label">qualité du prompt original</span>
              </div>
              <div class="stat-sep"></div>
              <div class="stat-item">
                <span class="stat-value accent">−{{ savedPct }}%</span>
                <span class="stat-label">économisés</span>
              </div>
              <div class="stat-sep"></div>
              <div class="stat-item">
                <span class="stat-value">{{ originalTokens }} → {{ optimizedTokens }}</span>
                <span class="stat-label">tokens</span>
              </div>
              <div class="stat-sep"></div>
              <div class="stat-item">
                <span class="stat-value">{{ originalTokens - optimizedTokens }}</span>
                <span class="stat-label">tokens en moins</span>
              </div>
              <div class="stat-sep"></div>
              <div class="stat-item">
                <span class="stat-value mono">
                  <PalierIcon :palier="detectedPalier.key" :size="13" style="margin-right:4px" />{{ detectedPalier.label }}
                </span>
                <span class="stat-label">format de réponse attendu</span>
              </div>
            </div>

            <!-- Accordéon Impact & économies -->
            <details class="modal-accordion" v-if="estimatedOutputTokens && !optimizeErrorMsg" open>
              <summary class="accordion-summary">Impact &amp; économies</summary>
              <div class="modal-output-stats">
                <div class="output-cards">
                  <div class="output-card">
                    <div class="output-card-value">~{{ estimatedOutputTokens }} <small>tokens</small></div>
                    <div class="output-card-sub">≈ {{ Math.round(estimatedOutputTokens / 1.35) }} mots · max {{ outputTokensMax }}</div>
                    <div class="output-card-label">Réponse attendue</div>
                  </div>
                  <div class="output-card" v-if="exchangeCostUsd != null">
                    <div class="output-card-value">{{ formatCostHuman(exchangeCostUsd) }}</div>
                    <div class="output-card-sub" v-if="exchangeCostMaxUsd != null">jusqu'à {{ formatCostHuman(exchangeCostMaxUsd) }}</div>
                    <div class="output-card-label">Coût de l'échange</div>
                  </div>
                  <div class="output-card savings-card" v-if="savedPct > 0">
                    <div class="output-card-value savings-pct" v-if="totalSavingsUsd">{{ formatCostHuman(totalSavingsUsd) }}</div>
                    <div class="output-card-value savings-pct" v-else>−{{ savedPct }}<small>%</small></div>
                    <div class="output-card-sub">−{{ originalTokens - optimizedTokens }} tokens · −{{ savedPct }}%</div>
                    <div class="output-card-label">Économies sur ce prompt</div>
                  </div>
                </div>
              </div>
            </details>

            <div v-if="(isUnderspecified || isIncomplete) && !optimizeErrorMsg" class="modal-underspec">
              <div class="underspec-header">
                {{ isUnderspecified ? '✎ Prompt trop bref' : '✎ Phrase incomplète' }}
              </div>
              <p class="underspec-tip">
                <template v-if="underspecType === 'caveman'">Prompt trop court — précisez la tâche, le contexte et le format attendu.</template>
                <template v-else-if="underspecType === 'telegraphic'">Style télégraphique — ajoutez contexte, format attendu, niveau de détail.</template>
                <template v-else>Phrase incomplète — reformulez en précisant ce que vous attendez.</template>
              </p>
            </div>

            <div v-if="isGenericPrompt && !optimizeErrorMsg" class="modal-density">
              <div class="density-header">
                ⚠ Presque la moitié du prompt est du remplissage ({{ Math.round(junkDensity * 100) }}%)
              </div>
              <div class="density-bar">
                <div class="bar-signal" :style="{ width: (1 - junkDensity) * 100 + '%' }">
                  Contenu utile {{ Math.round((1 - junkDensity) * 100) }}%
                </div>
                <div class="bar-junk" :style="{ width: junkDensity * 100 + '%' }">
                  Remplissage {{ Math.round(junkDensity * 100) }}%
                </div>
              </div>
              <p class="density-tip">
                Ces instructions ne changent pas le comportement du modèle — elles consomment des tokens pour rien.
                <span v-if="metaTokensRemoved > 0">{{ metaTokensRemoved }} tokens supprimés par l'optimiseur.</span>
              </p>
            </div>

            <!-- Accordéon Qualité avant/après -->
            <details class="modal-accordion" v-if="qualityNoteOriginal && result?.quality_note && !optimizeErrorMsg">
              <summary class="accordion-summary">Qualité avant / après</summary>
              <div class="quality-compare-table">
                <table>
                  <thead><tr><th>Axe</th><th>Avant</th><th>Après</th></tr></thead>
                  <tbody>
                    <tr v-for="ax in [['clarte','Clarté'],['specificite','Spécificité'],['structure','Structure'],['concision','Concision']]" :key="ax[0]">
                      <td>{{ ax[1] }}</td>
                      <td :class="scoreBandClass(qualityNoteOriginal[ax[0]])">{{ qualityNoteOriginal[ax[0]] }}</td>
                      <td :class="scoreBandClass(result.quality_note?.[ax[0]])">{{ result.quality_note?.[ax[0]] }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </details>

            <!-- Accordéon Qwen — audit + ambiguïtés -->
            <details class="modal-accordion" v-if="qwenAvailable && gainEstime !== 'faible' && !optimizeErrorMsg">
              <summary class="accordion-summary">
                Analyse structurelle
                <span v-if="qwenTemplateType" class="template-badge" :class="qwenTemplateType">{{ qwenTemplateType === 'pedagogique' ? 'Pédagogique' : 'Structuré' }}</span>
              </summary>
              <div class="qwen-detail">
                <div v-if="qwenAmbiguites.length" class="qwen-ambig">
                  <span class="ambig-icon">⚠</span>
                  <span v-for="a in qwenAmbiguites" :key="a" class="ambig-item">{{ a }}</span>
                </div>
                <div v-if="qwenAudit" class="audit-badges">
                  <span v-for="(val, key) in qwenAudit" :key="key" class="audit-badge" :class="'audit-' + val">
                    {{ auditLabel(key) }} <span class="audit-sep">·</span> <em>{{ auditValue(val) }}</em>
                  </span>
                </div>
              </div>
            </details>

            <!-- Accordéon Règles appliquées -->
            <details class="modal-accordion" v-if="rulesApplied.length && !optimizeErrorMsg">
              <summary class="accordion-summary">Règles appliquées ({{ rulesApplied.length }})</summary>
              <div class="modal-rules">
                <span v-for="r in rulesApplied" :key="r.label" class="rule-chip">
                  {{ r.label }}{{ r.count > 1 ? ` ×${r.count}` : '' }}
                </span>
              </div>
            </details>

            <div v-if="recommendedModel && isAuthenticated" class="modal-recommendation">
              💡 <span v-if="suggestedTask" class="reco-task">{{ suggestedTask }} — </span>
              <strong>{{ recommendedModel }}</strong>
              <span v-if="suggestedEffort" class="reco-effort"> / {{ suggestedEffort }}</span>
              serait plus adapté
              <button class="btn-apply-rec" @click="applyRecommendation">Appliquer</button>
            </div>
            <div v-else-if="recommendedModel && !isAuthenticated" class="modal-recommendation guest">
              💡 Ce prompt est adapté pour un modèle <strong>{{ recommendedModel }}</strong>
              <span v-if="suggestedEffort"> / {{ suggestedEffort }}</span>
            </div>
            <div v-else-if="suggestedEffort && suggestedEffort !== selectedEffort" class="modal-recommendation">
              💡 <span v-if="suggestedTask" class="reco-task">{{ suggestedTask }} — </span>
              effort <strong>{{ suggestedEffort }}</strong> recommandé
              <button class="btn-apply-rec" @click="applyEffortOnly">Appliquer</button>
            </div>

            <div class="modal-footer">
              <p v-if="canSendReason" class="modal-cant-send">{{ canSendReason }}</p>
              <div class="modal-actions">
                <button class="btn-cancel" @click="closeModal">Fermer</button>
                <button class="btn-send-original" :disabled="!canSend" @click="sendOriginalFromModal">
                  Envoyer l'original
                </button>
                <button class="btn-primary" :disabled="!canSend || !optimizedText.trim()" @click="sendOptimizedFromModal">
                  Envoyer le prompt optimisé →
                </button>
              </div>
            </div>

          </div>
        </div>
      </Transition>
    </Teleport>

  </div><!-- fin .chat-layout -->
  </div><!-- fin .chat-outer -->

</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api/index.js'
import { useAuth } from '../../composables/useAuth.js'
import PalierIcon from '../../components/PalierIcon.vue'
import { estimateTokens } from '../../lib/tokenEstimator.js'

const { isAuthenticated, deconnexion } = useAuth()
const route  = useRoute()
const router = useRouter()

const activeTab = ref('chat') // 'history' | 'chat' | 'stats'

function handleLogout() {
  deconnexion()
  router.push('/')
}

const PALIERS = {
  'auto': { label: 'Auto-détecté' },
  '★':   { label: 'Ultra-court (~50 mots)' },
  '0':   { label: 'Très court (~60 mots)' },
  '1':   { label: 'Court (~85 mots)' },
  '2':   { label: 'Moyen (~115 mots)' },
  '3':   { label: 'Développé (~140 mots)' },
  '4':   { label: 'Long (~165 mots)' },
  '5':   { label: 'Sans limite (complexe)' },
  'C':   { label: 'Code informatique' },
  '6':   { label: 'Documentation longue' },
}

const MODEL_RECOMMENDATION = {
  OpenAI:    { simple: 'gpt-4o-mini',      medium: 'gpt-4o',            complex: 'gpt-4o'          },
  Anthropic: { simple: 'claude-haiku-4-5', medium: 'claude-sonnet-4-6', complex: 'claude-opus-4-8' },
  Google:    { simple: 'gemini-2-5-flash', medium: 'gemini-2-5-pro',    complex: 'gemini-2-5-pro'  },
}

const SUGGESTIONS = [
  { label: '📝 Résumer un texte', text: 'Résume ce texte en 3 points clés : ' },
  { label: '💻 Expliquer du code', text: 'Explique ce code ligne par ligne : ' },
  { label: '✉️ Rédiger un email', text: 'Rédige un email professionnel pour ' },
]

const ALL_PROVIDERS = ['Anthropic', 'OpenAI', 'Google']
const COMING_SOON_PROVIDERS = new Set(['Meta', 'Mistral'])

// Mapping tier → meilleur modèle par provider
const MODEL_TIER = {
  OpenAI:    { simple: 'gpt-4o-mini',      medium: 'gpt-4o',            complex: 'gpt-4o'          },
  Anthropic: { simple: 'claude-haiku-4-5', medium: 'claude-sonnet-4-6', complex: 'claude-opus-4-8' },
  Google:    { simple: 'gemini-2-5-flash', medium: 'gemini-2-5-pro',    complex: 'gemini-2-5-pro'  },
}
// Providers triés du moins cher au plus cher pour chaque tier
const CHEAPEST_FIRST = {
  simple:  ['Google', 'OpenAI', 'Anthropic'],
  medium:  ['Google', 'Anthropic', 'OpenAI'],
  complex: ['OpenAI', 'Anthropic', 'Google'],
}
const COMPLEXITY_TO_TIER = {
  simple:       'simple',
  technique:    'medium',
  analytique:   'medium',
  documentaire: 'complex',
}

const COMPACT_THRESHOLD = 6000 // tokens estimés avant compaction
const GUEST_LIMIT       = 3    // échanges gratuits sans compte

const providers      = ref([])
const provider       = ref('')
const model          = ref('')
const selectedEffort = ref(null)  // null = API default, sinon off|on|low|medium|high|xhigh|max
const messages       = ref([])
const inputText      = ref('')
const loading        = ref(false)
const analysing      = ref(false)
const optimizeOn     = ref(true)
const autoRoute      = ref(true)
const showKeyPanel   = ref(false)
const keyInput       = ref('')
const keyVisible     = ref(false)
const editingProvider = ref(null)
const messagesEl     = ref(null)
const inputEl        = ref(null)
const toastMsg       = ref('')
const modelChangedWarning = ref(false)

// Optimiseur
const showOptimModal    = ref(false)
const originalPromptText = ref('')
const optimizedText      = ref('')
const palierConstraint   = ref(null)
const analysePhase       = ref('done')  // 'reading' | 'writing' | 'done'
const displayedOptimText = ref('')
const savedPct          = ref(0)
const originalTokens    = ref(0)
const optimizedTokens   = ref(0)
const pertinenceScore   = ref(100)
const pendingQualityNote = ref(null)
const selectedPalier    = ref('auto')
const detectedPalier    = ref({ key: 'auto', label: 'Auto-détecté' })
const rulesApplied            = ref([])
const pendingTokensSaved      = ref(0)
const optimizeErrorMsg        = ref('')
const estimatedOutputTokens   = ref(null)
const outputTokensMax         = ref(null)
const baselineOutputTokens    = ref(null)
const savingsInputUsd         = ref(null)
const savingsOutputUsd        = ref(null)
const exchangeCostUsd         = ref(null)
const exchangeCostMaxUsd      = ref(null)
const recommendedModel        = ref(null)
const suggestedEffort         = ref(null)
const suggestedTask           = ref(null)
const lastSuggestedEffort     = ref(null) // persiste après fermeture du modal
const lastSuggestedModelTier  = ref(null) // tier routing : simple|medium|complex
const junkDensity             = ref(0)
const isGenericPrompt         = ref(false)
const metaTokensRemoved       = ref(0)
const isUnderspecified        = ref(false)
const isIncomplete            = ref(false)
const underspecType           = ref(null)
const detectedComplexity      = ref(null)

// Résultat complet optimiseur (pour quality_note dans le modal)
const result = ref(null)

// E3 — chips de complétion
const chips = ref([])

// Qwen
const qwenAvailable        = ref(false)
const qwenRestructure      = ref(null)
const qwenAudit            = ref(null)
const qwenTemplateType     = ref(null)
const qwenAmbiguites       = ref([])
const gainEstime           = ref(null)
const qualityNoteOriginal  = ref(null)

// État analyse
const hasAnalysis = ref(false)

// Historique conversations
const conversationId  = ref(null)
const conversations   = ref([])

const conversationGroups = computed(() => {
  const now       = new Date()
  const today     = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const yesterday = today - 86400000
  const map = {}
  for (const conv of conversations.value) {
    const d   = new Date(conv.updated_at)
    const day = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
    let label
    if (day === today)     label = 'Aujourd\'hui'
    else if (day === yesterday) label = 'Hier'
    else {
      label = d.toLocaleDateString('fr-FR', { weekday: 'long' })
      label = label.charAt(0).toUpperCase() + label.slice(1)
    }
    if (!map[label]) map[label] = []
    map[label].push(conv)
  }
  return Object.entries(map).map(([label, items]) => ({ label, items }))
})

// Compteur guest
const guestExchangeCount = ref(parseInt(localStorage.getItem('helios_guest_count') || '0', 10))
const guestLimitReached  = computed(() => !isAuthenticated.value && guestExchangeCount.value >= GUEST_LIMIT)

// Cumul session
const sessionTotalCost         = ref(0)
const sessionTokensSaved       = ref(0)
const sessionTotalInputTokens  = ref(0)
const sessionTotalOutputTokens = ref(0)
const sessionCO2g              = ref(0)
const sessionMsgCount          = ref(0)

const apiKey = computed(() => sessionStorage.getItem(`helios_apikey_${provider.value}`) || '')

const modelsForProvider = computed(() =>
  providers.value.find(g => g.provider === provider.value)?.models ?? []
)

// Retourne l'effort compatible avec le modèle effectif (évite medium sur Haiku)
function compatibleEffort(effort, modelName) {
  if (!effort || !modelName) return effort
  const m = modelName.toLowerCase()
  const isHaiku = m.includes('haiku') || m.includes('flash-lite') || m.includes('mini')
  if (isHaiku) return 'off'
  return effort
}

const EFFORT_BY_TIER = {
  haiku:  [
    { id: 'off', label: 'Off — standard (pas de thinking)' },
  ],
  sonnet: [
    { id: 'low',    label: 'Low' },
    { id: 'medium', label: 'Med' },
    { id: 'high',   label: 'High' },
    { id: 'max',    label: 'Max' },
  ],
  opus: [
    { id: 'low',      label: 'Low' },
    { id: 'standard', label: 'Std' },
    { id: 'high',     label: 'High' },
    { id: 'xhigh',    label: 'xHigh' },
    { id: 'max',      label: 'Max' },
  ],
}

const effortOptions = computed(() => {
  const m = (model.value || '').toLowerCase()
  if (m.includes('haiku'))  return EFFORT_BY_TIER.haiku
  if (m.includes('opus'))   return EFFORT_BY_TIER.opus
  if (m.includes('sonnet')) return EFFORT_BY_TIER.sonnet
  // OpenAI o-series
  if (m.startsWith('o1') || m.startsWith('o3') || m.startsWith('o4'))
    return [{ id:'low', label:'Low' }, { id:'medium', label:'Med' }, { id:'high', label:'High' }]
  // Gemini
  if (m.includes('gemini'))
    return [{ id:'low', label:'Low' }, { id:'medium', label:'Med' }, { id:'high', label:'High' }, { id:'max', label:'Max' }]
  return []
})

const hasAnyKey = computed(() =>
  ALL_PROVIDERS.some(p => sessionStorage.getItem(`helios_apikey_${p}`))
)

const canSend = computed(() => {
  if (loading.value) return false
  if (!apiKey.value || !model.value) return false
  if (!isAuthenticated.value && guestLimitReached.value) return false
  return true
})

const totalSavingsUsd = computed(() => {
  const a = savingsInputUsd.value ?? 0
  const b = savingsOutputUsd.value ?? 0
  const total = a + b
  return total > 0 ? total : null
})

const canSendReason = computed(() => {
  if (!isAuthenticated.value) return ''
  if (!apiKey.value) return 'Configurez votre clé API (⚙ Config)'
  if (!model.value) return 'Sélectionnez un modèle'
  return ''
})

// --- Multi-clés ---
function getProviderKey(p) {
  return sessionStorage.getItem(`helios_apikey_${p}`) || ''
}

function keyPlaceholder(p) {
  if (p === 'OpenAI')    return 'sk-...'
  if (p === 'Anthropic') return 'sk-ant-...'
  if (p === 'Google')    return 'AIza...'
  return 'Clé API'
}

function startEditKey(p) {
  editingProvider.value = p
  keyInput.value = ''
  keyVisible.value = false
}

function saveKeyFor(p) {
  const val = keyInput.value.trim()
  if (val) {
    sessionStorage.setItem(`helios_apikey_${p}`, val)
    if (p === provider.value) {
      // force reactivity — apiKey est computed mais on peut toast
    }
    showToast(`Clé ${p} enregistrée`)
  }
  editingProvider.value = null
  keyInput.value = ''
}

function clearKeyFor(p) {
  sessionStorage.removeItem(`helios_apikey_${p}`)
  showToast(`Clé ${p} supprimée`)
}

// --- Routage auto ---
function pickBestModel(complexity) {
  const tier = COMPLEXITY_TO_TIER[complexity] ?? 'medium'
  const configured = ALL_PROVIDERS.filter(p => sessionStorage.getItem(`helios_apikey_${p}`))
  if (!configured.length) return null
  const best = CHEAPEST_FIRST[tier].find(p => configured.includes(p))
  if (!best) return null
  return {
    provider: best,
    model:    MODEL_TIER[best][tier],
    key:      sessionStorage.getItem(`helios_apikey_${best}`),
  }
}

// --- Compaction ---
async function maybeCompact(history) {
  const est = history.reduce((s, m) => s + Math.ceil(m.content.length / 3.5), 0)
  if (est < COMPACT_THRESHOLD) return history

  const toCompact = history.slice(0, -4)
  const toKeep    = history.slice(-4)

  const cheap = pickBestModel('simple') ?? {
    provider: provider.value,
    model:    model.value,
    key:      apiKey.value,
  }

  try {
    const { data } = await api.post('/chat/compact', {
      provider: cheap.provider,
      model:    cheap.model,
      api_key:  cheap.key,
      messages: toCompact,
    })
    showToast('Historique compacté automatiquement')
    return [
      { role: 'user',      content: '[Résumé de la conversation précédente]\n' + data.summary, _compacted: true },
      { role: 'assistant', content: 'Contexte compris.', _compacted: true },
      ...toKeep,
    ]
  } catch {
    return history
  }
}

const pertinenceCardClass = computed(() => {
  const s = pertinenceScore.value
  return s >= 80 ? 'ok' : s >= 50 ? 'warn' : 'bad'
})

const pertinenceLabel = computed(() => {
  const s = pertinenceScore.value
  if (s >= 80) return 'Prompt précis et bien ciblé'
  if (s >= 50) return 'Peut être amélioré'
  return 'Trop vague ou générique'
})

const pertinenceBadge = computed(() => {
  const s = pertinenceScore.value
  if (s >= 93) return { cls: 'badge-emeraude', label: 'Prompt optimal' }
  if (s >= 80) return { cls: 'badge-vert',     label: 'Prompt efficace' }
  if (s >= 65) return { cls: 'badge-jaune',    label: 'Prompt correct' }
  if (s >= 40) return { cls: 'badge-orange',   label: 'Prompt acceptable' }
  return             { cls: 'badge-rouge',     label: 'Prompt peu dense' }
})

async function applySuggestion(text) {
  inputText.value = text
  await nextTick()
  inputEl.value?.focus()
  if (inputEl.value) autoResize(inputEl.value)
}

function scoreBandClass(v) {
  return v >= 75 ? 'score-green' : v >= 45 ? 'score-orange' : 'score-red'
}

const auditLabels = { role: 'Rôle', contexte: 'Contexte', tache: 'Tâche', contraintes: 'Contraintes', format: 'Format', qualite: 'Qualité' }
const auditValues = { present: 'présent', absent: 'absent', inferred: 'inféré' }
function auditLabel(key) { return auditLabels[key] ?? key }
function auditValue(val) { return auditValues[val] ?? val }

function autoResize(el) {
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

function showToast(msg) {
  toastMsg.value = msg
  setTimeout(() => { toastMsg.value = '' }, 2000)
}

function escapeHtml(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function formatCost(usd) {
  if (usd == null || usd === 0) return ''
  if (usd < 0.001) return `${(usd * 1_000_000).toFixed(1)} µ$`
  return `$${usd.toFixed(4)}`
}

function formatCostHuman(usd) {
  if (usd == null || usd === 0) return ''
  if (usd < 0.0001) return `< $0.0001`
  if (usd < 0.01)   return `$${usd.toFixed(4)}`
  if (usd < 1)      return `$${usd.toFixed(3)}`
  return `$${usd.toFixed(2)}`
}

function co2ToMeters(g) {
  // 120 g CO₂/km = 0.12 g CO₂/m → d(m) = g / 0.12
  const m = g / 0.12
  if (m < 1)    return '< 1 m en voiture'
  if (m < 1000) return `≈ ${m.toFixed(0)} m en voiture`
  return `≈ ${(m / 1000).toFixed(2)} km en voiture`
}

function formatSessionCO2(g) {
  if (g < 0.001) return `${(g * 1000).toFixed(1)} µg`
  if (g < 1)     return `${(g * 1000).toFixed(0)} µg`
  return `${g.toFixed(2)} g`
}

function formatCO2(impact) {
  if (!impact) return ''
  const g = impact.co2_standard * 1000
  return g < 0.1 ? `${(g * 1000).toFixed(1)} µg CO₂` : `${g.toFixed(2)} g CO₂`
}

function formatMarkdown(text) {
  // Regex built dynamically to avoid triple-backtick literals confusing Vite's HMR lexer
  const BT = '\x60'
  const codeBlockRe = new RegExp(BT + BT + BT + '(\\w*)\\n?([\\s\\S]*?)' + BT + BT + BT, 'g')
  const blocks = []
  let out = text.replace(codeBlockRe, (_, _lang, code) => {
    const i = blocks.length
    blocks.push(code)
    return '\x00BLOCK' + i + '\x00'
  })
  out = escapeHtml(out)
  out = out
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)(\n<li>[\s\S]*?<\/li>)*/g, s => '<ul>' + s + '</ul>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>')
  out = out.replace(/\x00BLOCK(\d+)\x00/g, (_, i) => {
    const code = blocks[parseInt(i)]
    const safe = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    return `<div class="code-block"><button class="btn-copy">Copier</button><pre><code>${safe}</code></pre></div>`
  })
  return out
}

function persistChat() {
  try {
    localStorage.setItem('helios_chat_messages', JSON.stringify(messages.value))
    localStorage.setItem('helios_chat_meta', JSON.stringify({
      provider:  provider.value,
      model:     model.value,
      palier:    selectedPalier.value,
      autoRoute: autoRoute.value,
    }))
  } catch (_) {}
}

function newConversation() {
  messages.value = []
  inputText.value = ''
  sessionTotalCost.value         = 0
  sessionTokensSaved.value       = 0
  sessionTotalInputTokens.value  = 0
  sessionTotalOutputTokens.value = 0
  sessionCO2g.value              = 0
  sessionMsgCount.value          = 0
  recommendedModel.value         = null
  suggestedEffort.value          = null
  suggestedTask.value            = null
  lastSuggestedEffort.value      = null
  lastSuggestedModelTier.value   = null
  hasAnalysis.value              = false
  localStorage.removeItem('helios_chat_messages')
  localStorage.removeItem('helios_chat_meta')
  closeModal()
}

function startNewConversation() {
  conversationId.value = null
  newConversation()
  router.push('/chat')
}

function formatConvTime(dateStr) {
  return new Date(dateStr).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

async function loadConversations() {
  if (!isAuthenticated.value) return
  try {
    const { data } = await api.get('/conversations')
    conversations.value = data
  } catch (_) {}
}

async function openConversation(uuid) {
  if (uuid === conversationId.value) return
  router.push(`/chat/${uuid}`)
}

async function loadConversation(uuid) {
  try {
    const { data } = await api.get(`/conversations/${uuid}/messages`)
    messages.value      = data.messages ?? []
    if (data.provider)  provider.value = data.provider
    if (data.model)     model.value    = data.model
    conversationId.value = uuid
    sessionTotalInputTokens.value  = 0
    sessionTotalOutputTokens.value = 0
    sessionTotalCost.value         = 0
    sessionCO2g.value              = 0
    sessionMsgCount.value          = 0
    for (const msg of messages.value) {
      if (msg.role === 'assistant' && !msg.isError && !msg._compacted) {
        if (msg.input_tokens)         sessionTotalInputTokens.value  += msg.input_tokens
        if (msg.output_tokens)        sessionTotalOutputTokens.value += msg.output_tokens
        if (msg.cost_usd != null)     sessionTotalCost.value         += msg.cost_usd
        if (msg.impact?.co2_standard) sessionCO2g.value              += msg.impact.co2_standard * 1000
        sessionMsgCount.value++
      }
    }
    await nextTick()
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  } catch (_) {}
}

async function saveConversation() {
  if (!isAuthenticated.value) return
  const userMsgs = messages.value.filter(m => m.role === 'user' && !m._compacted)
  if (userMsgs.length === 0) return
  const title = (userMsgs[0].content || '').slice(0, 50) || 'Nouvelle conversation'
  try {
    const { data } = await api.post('/conversations/save', {
      id:           conversationId.value,
      title,
      provider:     provider.value,
      model:        model.value,
      nb_turns:     sessionMsgCount.value,
      tokens_total: sessionTotalInputTokens.value + sessionTotalOutputTokens.value,
      co2_g:        sessionCO2g.value,
      cost_usd:     sessionTotalCost.value,
      impact_level: 'low',
      messages:     messages.value.filter(m => !m._compacted),
    })
    if (!conversationId.value) {
      conversationId.value = data.id
      router.replace(`/chat/${data.id}`)
      await loadConversations()
    } else {
      const idx = conversations.value.findIndex(c => c.id === data.id)
      if (idx >= 0) {
        conversations.value[idx].tokens_total = sessionTotalInputTokens.value + sessionTotalOutputTokens.value
        conversations.value[idx].nb_turns     = sessionMsgCount.value
        conversations.value[idx].co2_g        = sessionCO2g.value
        conversations.value[idx].updated_at   = new Date().toISOString()
      }
    }
  } catch (_) {}
}

function applyRecommendation() {
  model.value = recommendedModel.value
  if (suggestedEffort.value) selectedEffort.value = suggestedEffort.value
  recommendedModel.value = null
  showToast(`Modèle → ${model.value}${suggestedEffort.value ? ' / effort ' + suggestedEffort.value : ''}`)
}

function applyEffortOnly() {
  selectedEffort.value = suggestedEffort.value
  showToast(`Effort → ${suggestedEffort.value}`)
}

function exportConversation() {
  const lines = messages.value.map(m =>
    `[${m.role === 'user' ? 'Vous' : 'Assistant'}]\n${m.content}`
  ).join('\n\n---\n\n')
  const blob = new Blob([lines], { type: 'text/plain' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `helios-chat-${new Date().toISOString().slice(0, 10)}.txt`
  a.click()
  URL.revokeObjectURL(a.href)
}

function openReview() {
  showOptimModal.value = true
}

function toggleOptimize() {
  optimizeOn.value = !optimizeOn.value
  closeModal()
}

async function analyseAndSend() {
  if (!inputText.value.trim() || analysing.value || !canSend.value) return
  analysing.value        = true
  optimizeErrorMsg.value = ''
  originalPromptText.value = inputText.value.trim()
  try {
    const { data } = await api.post('/optimise/', {
      prompt:   inputText.value.trim(),
      palier:   selectedPalier.value === 'auto' ? null : selectedPalier.value,
      provider: provider.value,
      model:    model.value,
    })
    originalTokens.value   = data.tokens_before  ?? estimateTokens(inputText.value.trim())
    optimizedTokens.value  = data.tokens_after   ?? estimateTokens(data.optimised ?? inputText.value.trim())
    savedPct.value         = data.tokens_before > 0
      ? Math.round(data.tokens_saved / data.tokens_before * 100) : 0
    pertinenceScore.value  = data.pertinence_score ?? 100
    pendingQualityNote.value = data.quality_note ?? null
    optimizedText.value    = data.optimised ?? inputText.value.trim()
    palierConstraint.value = data.palier_constraint ?? null
    const pk = data.palier ?? selectedPalier.value
    detectedPalier.value   = { key: pk, ...PALIERS[pk] }
    rulesApplied.value           = data.rules_applied ?? []
    pendingTokensSaved.value     = data.tokens_saved ?? 0
    estimatedOutputTokens.value  = data.estimated_output_tokens ?? null
    outputTokensMax.value        = data.output_tokens_max ?? null
    baselineOutputTokens.value   = data.baseline_output_tokens ?? null
    savingsInputUsd.value        = data.savings_input_usd ?? null
    savingsOutputUsd.value       = data.savings_output_usd ?? null
    exchangeCostUsd.value        = data.exchange_cost_usd ?? null
    exchangeCostMaxUsd.value     = data.exchange_cost_max_usd ?? null
    junkDensity.value            = data.junk_density ?? 0
    isGenericPrompt.value        = data.is_generic_prompt ?? false
    metaTokensRemoved.value      = data.meta_tokens_removed ?? 0
    isUnderspecified.value       = data.is_underspecified ?? false
    isIncomplete.value           = data.is_incomplete ?? false
    underspecType.value          = data.underspec_type ?? null
    detectedComplexity.value     = data.complexity ?? null
    suggestedEffort.value        = data.suggested_effort ?? null
    suggestedTask.value          = data.suggested_task ?? null
    if (data.suggested_effort)   lastSuggestedEffort.value    = data.suggested_effort
    if (data.suggested_model_tier) lastSuggestedModelTier.value = data.suggested_model_tier
    const group = data.suggested_model_tier ?? COMPLEXITY_TO_TIER[data.complexity] ?? 'simple'
    const routedModel = MODEL_RECOMMENDATION[provider.value]?.[group] ?? null
    recommendedModel.value = isAuthenticated.value
      ? (routedModel !== model.value ? routedModel : null)
      : group
    // Ajuster l'effort affiché au modèle qui sera réellement utilisé
    const effectiveModel = routedModel ?? model.value
    if (suggestedEffort.value)
      suggestedEffort.value = compatibleEffort(suggestedEffort.value, effectiveModel)
    if (lastSuggestedEffort.value)
      lastSuggestedEffort.value = compatibleEffort(lastSuggestedEffort.value, effectiveModel)
    hasAnalysis.value = true
    // Envoi automatique du prompt optimisé
    const text  = optimizedText.value
    const pct   = savedPct.value
    const score = pertinenceScore.value
    const cplx  = detectedComplexity.value
    inputText.value = ''
    await nextTick()
    if (inputEl.value) autoResize(inputEl.value)
    await doSend(text, true, pct, score, cplx)
  } catch (e) {
    console.error('[analyseAndSend]', e.response?.data ?? e.message)
    // Fallback : envoi direct si l'optimiseur échoue
    await sendDirect()
  } finally {
    analysing.value = false
  }
}

function closeModal() {
  showOptimModal.value        = false
  analysePhase.value          = 'done'
  displayedOptimText.value    = ''
  optimizeErrorMsg.value      = ''
  estimatedOutputTokens.value = null
  outputTokensMax.value       = null
  baselineOutputTokens.value  = null
  savingsInputUsd.value       = null
  savingsOutputUsd.value      = null
  exchangeCostUsd.value       = null
  exchangeCostMaxUsd.value    = null
  recommendedModel.value      = null
  result.value                = null
  qwenAvailable.value         = false
  qwenRestructure.value       = null
  qwenAudit.value             = null
  qwenTemplateType.value      = null
  qwenAmbiguites.value        = []
  gainEstime.value            = null
  qualityNoteOriginal.value   = null
  // suggestedEffort et suggestedTask persistent pour la durée de la conversation
  junkDensity.value           = 0
  isGenericPrompt.value       = false
  metaTokensRemoved.value     = 0
  isUnderspecified.value      = false
  isIncomplete.value          = false
  underspecType.value         = null
}

function onProviderChange() {
  keyInput.value = ''
  model.value    = modelsForProvider.value[0] ?? ''
}

async function typewriterReveal(text) {
  analysePhase.value    = 'writing'
  displayedOptimText.value = ''
  for (let i = 0; i < text.length; i++) {
    displayedOptimText.value += text[i]
    await new Promise(r => setTimeout(r, 7))
  }
  await new Promise(r => setTimeout(r, 120))
  analysePhase.value = 'done'
}

async function analyse() {
  if (!inputText.value.trim() || analysing.value) return
  analysing.value          = true
  analysePhase.value       = 'reading'
  optimizeErrorMsg.value   = ''
  originalPromptText.value = inputText.value.trim()
  showOptimModal.value     = true
  try {
    const { data } = await api.post('/optimise/', {
      prompt:           inputText.value.trim(),
      palier:           selectedPalier.value === 'auto' ? null : selectedPalier.value,
      provider:         provider.value,
      model:            model.value,
      save_candidates:  true,
      semantic:         true,
    })
    originalTokens.value    = data.tokens_before  ?? estimateTokens(inputText.value.trim())
    optimizedTokens.value   = data.tokens_after   ?? estimateTokens(data.optimised ?? inputText.value.trim())
    savedPct.value          = data.tokens_before > 0
      ? Math.max(0, Math.round(data.tokens_saved / data.tokens_before * 100))
      : 0
    pertinenceScore.value   = data.pertinence_score ?? 100
    pendingQualityNote.value  = data.quality_note ?? null
    qwenAvailable.value       = data.qwen_available ?? false
    qwenRestructure.value     = data.qwen_restructure ?? null
    qwenAudit.value           = data.qwen_audit ?? null
    qwenTemplateType.value    = data.qwen_template_type ?? null
    qwenAmbiguites.value      = data.qwen_ambiguites ?? []
    gainEstime.value          = data.gain_estime ?? null
    qualityNoteOriginal.value = data.quality_note_original ?? null
    result.value              = data
    const useQwen = data.qwen_available && data.gain_estime !== 'faible' && data.qwen_restructure
    optimizedText.value     = useQwen ? data.qwen_restructure : (data.optimised ?? inputText.value.trim())
    // C2 — aligner savedPct/optimizedTokens sur le texte réellement affiché
    if (useQwen) {
      optimizedTokens.value = estimateTokens(data.qwen_restructure)
      savedPct.value = originalTokens.value > 0
        ? Math.max(0, Math.round((originalTokens.value - optimizedTokens.value) / originalTokens.value * 100))
        : 0
    }
    const pk = data.palier ?? selectedPalier.value
    detectedPalier.value    = { key: pk, ...PALIERS[pk] }
    // Ne pas écraser selectedPalier si l'utilisateur est en mode auto
    rulesApplied.value           = data.rules_applied ?? []
    pendingTokensSaved.value     = data.tokens_saved ?? 0
    estimatedOutputTokens.value  = data.estimated_output_tokens ?? null
    outputTokensMax.value        = data.output_tokens_max ?? null
    baselineOutputTokens.value   = data.baseline_output_tokens ?? null
    savingsInputUsd.value        = data.savings_input_usd ?? null
    savingsOutputUsd.value       = data.savings_output_usd ?? null
    exchangeCostUsd.value        = data.exchange_cost_usd ?? null
    exchangeCostMaxUsd.value     = data.exchange_cost_max_usd ?? null
    junkDensity.value            = data.junk_density ?? 0
    isGenericPrompt.value        = data.is_generic_prompt ?? false
    metaTokensRemoved.value      = data.meta_tokens_removed ?? 0
    isUnderspecified.value       = data.is_underspecified ?? false
    isIncomplete.value           = data.is_incomplete ?? false
    underspecType.value          = data.underspec_type ?? null
    detectedComplexity.value     = data.complexity ?? null
    chips.value                  = data.chips ?? []
    suggestedEffort.value        = data.suggested_effort ?? null
    suggestedTask.value          = data.suggested_task ?? null
    if (data.suggested_effort)   lastSuggestedEffort.value    = data.suggested_effort
    if (data.suggested_model_tier) lastSuggestedModelTier.value = data.suggested_model_tier
    const group = COMPLEXITY_TO_TIER[data.complexity] ?? 'simple'
    recommendedModel.value = isAuthenticated.value
      ? (MODEL_RECOMMENDATION[provider.value]?.[group] !== model.value
          ? MODEL_RECOMMENDATION[provider.value]?.[group] ?? null
          : null)
      : group
    // Lancer le typewriter (modal déjà ouvert en phase 'reading')
    const revealText = useQwen ? data.qwen_restructure : (data.optimised ?? inputText.value.trim())
    typewriterReveal(revealText)
  } catch (e) {
    console.error('[optimiseur]', e.response?.data ?? e.message)
    optimizeErrorMsg.value = 'Optimisation indisponible — prompt envoyé tel quel'
    optimizedText.value    = inputText.value.trim()
    analysePhase.value     = 'done'
  } finally {
    analysing.value = false
  }
}

function applyChipInModal(slot, label, option) {
  const cleanLabel = label.replace('?', '').trim()
  optimizedText.value = optimizedText.value.trimEnd() + `\n${cleanLabel} : ${option}.`
  chips.value = chips.value.filter(c => c.slot !== slot)
}

async function sendOptimizedFromModal() {
  if (!optimizedText.value.trim()) return
  const base  = optimizedText.value.trim()
  const text  = base  // contrainte palier injectée via system parameter API
  const sentTokens = estimateTokens(text)
  const pct   = originalTokens.value > 0
    ? Math.max(0, Math.round((originalTokens.value - sentTokens) / originalTokens.value * 100))
    : 0
  const score = pertinenceScore.value
  const cplx  = detectedComplexity.value
  closeModal()
  await doSend(text, true, pct, score, cplx)
}

async function sendOriginalFromModal() {
  const text = originalPromptText.value
  closeModal()
  await doSend(text, false, 0, null)
}

async function sendDirect() {
  if (!inputText.value.trim()) return
  await doSend(inputText.value.trim(), false, 0, null)
}

async function doSend(text, optimized, pct = 0, pertScore = null, complexity = null) {
  inputText.value = ''
  await nextTick()
  if (inputEl.value) autoResize(inputEl.value)
  const qn = pendingQualityNote.value
  pendingQualityNote.value = null
  messages.value.push({ role: 'user', content: text, optimized, savedPct: pct, pertinenceScore: pertScore, qualityNote: qn })
  await scrollBottom()
  loading.value = true

  try {
    let history = messages.value
      .filter(m => (m.role === 'user' || m.role === 'assistant') && !m.isError)
      .map(m => ({ role: m.role, content: m.content }))

    // Compaction si historique trop lourd
    history = await maybeCompact(history)

    // Routage auto — choisir le meilleur provider/model si activé
    let sendProvider = provider.value
    let sendModel    = model.value
    let sendKey      = apiKey.value

    if (autoRoute.value) {
      if (isAuthenticated.value) {
        // Routing unifié — utilise suggest_routing (tier + effort ensemble)
        // Fallback sur COMPLEXITY_TO_TIER si pas encore de suggestion routing
        const tier = lastSuggestedModelTier.value
          ?? (complexity ? COMPLEXITY_TO_TIER[complexity] ?? 'medium' : null)
        if (tier) {
          const routed = MODEL_RECOMMENDATION[provider.value]?.[tier]
          if (routed && routed !== model.value) {
            sendModel = routed
            showToast(`Routé → ${routed}${lastSuggestedEffort.value ? ' / ' + lastSuggestedEffort.value : ''}`)
          }
        }
      } else {
        const best = pickBestModel(complexity)
        if (best && (best.provider !== provider.value || best.model !== model.value)) {
          sendProvider = best.provider
          sendModel    = best.model
          sendKey      = best.key
          showToast(`Routé → ${best.model} (${best.provider})`)
        }
      }
    }

    model.value    = sendModel
    provider.value = sendProvider
    // Si le modèle a changé via auto-routing, la recommandation modale est périmée
    if (recommendedModel.value === sendModel) recommendedModel.value = null

    const { data } = await api.post('/chat/send', {
      provider:     sendProvider,
      model:        sendModel,
      api_key:      sendKey,
      messages:     history,
      tokens_saved: optimized ? (pendingTokensSaved.value ?? 0) : 0,
      effort:       compatibleEffort(selectedEffort.value ?? lastSuggestedEffort.value, sendModel) ?? undefined,
      palier:       detectedPalier.value?.key ?? null,
    })

    messages.value.push({
      role:          'assistant',
      content:       data.content,
      input_tokens:  data.input_tokens,
      output_tokens: data.output_tokens,
      impact:        data.impact,
      cost_usd:      data.cost_usd ?? null,
      routed_model:  sendModel !== model.value ? `${sendProvider} / ${sendModel}` : null,
    })
    if (data.cost_usd != null)    sessionTotalCost.value          += data.cost_usd
    if (data.input_tokens)        sessionTotalInputTokens.value   += data.input_tokens
    if (data.output_tokens)       sessionTotalOutputTokens.value  += data.output_tokens
    if (data.impact?.co2_standard) sessionCO2g.value              += data.impact.co2_standard * 1000
    if (optimized)                sessionTokensSaved.value        += pendingTokensSaved.value
    sessionMsgCount.value++
    saveConversation()
    if (!isAuthenticated.value) {
      guestExchangeCount.value++
      localStorage.setItem('helios_guest_count', String(guestExchangeCount.value))
    }
    pendingTokensSaved.value = 0
    persistChat()
  } catch (e) {
    const status = e.response?.status
    const detail = e.response?.data?.detail
    let msg
    if (status === 401)      msg = '⚠ Clé API invalide ou expirée. Vérifiez votre clé dans ⚙ Config.'
    else if (status === 429) msg = '⚠ Quota API dépassé. Attendez quelques minutes ou vérifiez votre plan.'
    else if (status === 502) msg = '⚠ Le LLM ne répond pas. Réessayez dans quelques instants.'
    else if (!e.response)    msg = '⚠ Pas de réponse du serveur. Vérifiez votre connexion.'
    else                     msg = `⚠ Erreur : ${detail ?? e.message}`
    messages.value.push({ role: 'assistant', content: msg, isError: true })
    persistChat()
  } finally {
    loading.value = false
    await scrollBottom()
    await nextTick()
    inputEl.value?.focus()
  }
}

async function scrollBottom() {
  await nextTick()
  if (!messagesEl.value) return
  const el = messagesEl.value
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  if (nearBottom) el.scrollTop = el.scrollHeight
}

watch(modelsForProvider, (list) => {
  if (!isAuthenticated.value) return
  if (list.length && !list.includes(model.value)) model.value = list[0]
})

watch([provider, model], ([newP, newM], [oldP, oldM]) => {
  if (messages.value.length > 0 && (newP !== oldP || newM !== oldM)) {
    modelChangedWarning.value = true
    setTimeout(() => { modelChangedWarning.value = false }, 3000)
  }
})

onMounted(async () => {
  let data = []
  try {
    const res = await api.get('/upload/providers')
    data = res.data
    providers.value = data
    if (isAuthenticated.value) {
      provider.value = data[0]?.provider ?? 'OpenAI'
      model.value    = data[0]?.models[0] ?? ''
    }
  } catch (_) {
    showToast('Impossible de charger les modèles — relancez le serveur.')
  }

  // Restauration conversation précédente
  try {
    const savedMsgs = localStorage.getItem('helios_chat_messages')
    const savedMeta = localStorage.getItem('helios_chat_meta')
    if (savedMsgs) {
      messages.value = JSON.parse(savedMsgs)
      for (const msg of messages.value) {
        if (msg.role === 'assistant' && !msg.isError && !msg._compacted) {
          if (msg.input_tokens)         sessionTotalInputTokens.value  += msg.input_tokens
          if (msg.output_tokens)        sessionTotalOutputTokens.value += msg.output_tokens
          if (msg.cost_usd != null)     sessionTotalCost.value         += msg.cost_usd
          if (msg.impact?.co2_standard) sessionCO2g.value              += msg.impact.co2_standard * 1000
          sessionMsgCount.value++
        }
      }
    }
    if (savedMeta) {
      const m = JSON.parse(savedMeta)
      if (m.palier) selectedPalier.value = m.palier
      // ne pas écraser provider/model si déjà chargés depuis providers
      if (isAuthenticated.value && m.provider && providers.value.find(g => g.provider === m.provider)) {
        provider.value = m.provider
        model.value    = m.model || data[0]?.models[0] || ''
      }
      if (m.autoRoute != null) autoRoute.value = m.autoRoute
    }
  } catch (_) {}

  // Charger la liste des conversations + la conversation de l'URL si présente
  await loadConversations()
  if (route.params.uuid) {
    await loadConversation(route.params.uuid)
  }

  // Watcher navigation entre conversations
  watch(() => route.params.uuid, async (uuid) => {
    if (uuid) await loadConversation(uuid)
    else { conversationId.value = null; newConversation() }
  })

  // Escape pour fermer le modal
  function onKeydown(e) { if (e.key === 'Escape' && showOptimModal.value) closeModal() }
  window.addEventListener('keydown', onKeydown)
  onUnmounted(() => window.removeEventListener('keydown', onKeydown))

  // Délégation click pour btn-copy
  messagesEl.value?.addEventListener('click', e => {
    if (e.target.classList.contains('btn-copy')) {
      const code = e.target.nextElementSibling?.querySelector('code')?.textContent ?? ''
      navigator.clipboard.writeText(code).catch(() => {})
      e.target.textContent = 'Copié !'
      setTimeout(() => { e.target.textContent = 'Copier' }, 1500)
    }
  })

  await nextTick()
  if (inputEl.value) autoResize(inputEl.value)
})
</script>

<style scoped>
/* ── Layout 2/3 + 1/3 ── */
.chat-outer {
  display: grid;
  grid-template-columns: 240px 1fr 260px;
  grid-template-areas: "history main sidebar";
  gap: 0;
  height: 100vh;
  width: 100%;
  padding: 0;
  overflow: hidden;
}

/* ── Panel historique ── */
.chat-history {
  grid-area: history;
  display: flex; flex-direction: column;
  height: 100%; overflow: hidden;
  border-right: 1px solid var(--border);
  background: var(--bg-surface-2);
}
.history-header {
  padding: var(--s-4) var(--s-3) var(--s-3);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.history-logo {
  display: block; font-size: var(--t-sm); font-weight: var(--fw-bold);
  color: var(--accent); margin-bottom: var(--s-3); letter-spacing: .04em;
}
.history-new {
  width: 100%; padding: 7px var(--s-3);
  background: var(--accent-soft); border: 1px solid var(--accent);
  border-radius: var(--r-md); color: var(--accent);
  font-size: var(--t-xs); font-weight: var(--fw-semibold); cursor: pointer;
  transition: background .15s;
}
.history-new:hover { background: var(--accent); color: #fff; }
.history-list {
  flex: 1; overflow-y: auto; padding: var(--s-2) 0;
}
.conv-group-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: .1em;
  color: var(--fg-dim); padding: var(--s-3) var(--s-3) var(--s-1);
}
.conv-item {
  display: block; width: 100%; text-align: left;
  padding: var(--s-2) var(--s-3); background: none; border: none;
  cursor: pointer; border-radius: 0;
  transition: background .12s;
}
.conv-item:hover   { background: var(--bg-hover); }
.conv-item.active  { background: var(--accent-soft); border-left: 2px solid var(--accent); }
.conv-title {
  font-size: var(--t-xs); color: var(--fg); white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis; margin-bottom: 3px;
}
.conv-meta {
  display: flex; align-items: center; gap: 5px;
}
.conv-time   { font-size: 10px; color: var(--fg-dim); }
.conv-tokens { font-size: 10px; color: var(--fg-dim); margin-left: auto; }
.conv-badge  {
  font-size: 9px; padding: 1px 5px; border-radius: var(--r-pill);
  font-weight: var(--fw-semibold); text-transform: uppercase;
}
.conv-badge--low    { background: rgba(52,211,153,.15); color: #34d399; }
.conv-badge--medium { background: rgba(249,115,22,.15);  color: #f97316; }
.conv-badge--high   { background: rgba(239,68,68,.15);   color: #ef4444; }
.history-empty {
  font-size: var(--t-xs); color: var(--fg-dim); text-align: center;
  padding: var(--s-6) var(--s-3);
}
.history-footer {
  padding: var(--s-3); border-top: 1px solid var(--border); flex-shrink: 0;
}
.history-foot-btn {
  display: block; font-size: var(--t-xs); color: var(--fg-dim);
  text-decoration: none; padding: var(--s-2) var(--s-2);
  border-radius: var(--r-md); transition: color .15s, background .15s;
}
.history-foot-btn:hover { color: var(--fg); background: var(--bg-hover); }
.history-logout { color: var(--danger); width: 100%; text-align: left; background: none; border: none; cursor: pointer; font-size: inherit; }
.history-logout:hover { color: var(--danger); background: rgba(239,68,68,.08); }

.chat-layout {
  grid-area: main;
  display: flex; flex-direction: column; height: 100%; overflow: hidden;
  padding-right: var(--s-4);
  border-right: 1px solid var(--border);
  min-width: 0;
}

/* ── Sidebar ── */
.chat-sidebar {
  grid-area: sidebar;
  display: flex; flex-direction: column; gap: var(--s-3);
  padding: var(--s-5) var(--s-4);
  height: 100%;
  overflow-y: auto;
  position: sticky;
  top: 0;
}
.sidebar-title {
  font-size: var(--t-xs); text-transform: uppercase; letter-spacing: .08em;
  color: var(--fg-dim); font-weight: var(--fw-semibold); margin-bottom: var(--s-1);
  display: flex; align-items: center; justify-content: space-between;
}
.sidebar-block {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: var(--s-3) var(--s-4);
  transition: border-color .2s;
}
.sidebar-block--savings { border-color: rgba(34,197,94,.3); }
.sidebar-label { font-size: var(--t-xs); color: var(--fg-dim); margin-bottom: 2px; }
.sidebar-value { font-size: var(--t-base); font-weight: var(--fw-semibold); color: var(--fg); }
.sidebar-value--green { color: #4ade80; }
.sidebar-value--model { font-size: var(--t-sm); font-family: var(--font-mono); color: var(--accent); word-break: break-all; }
.sidebar-sub  { font-size: var(--t-xs); color: var(--fg-dim); margin-top: 2px; }
.sidebar-sep  { height: 1px; background: var(--border); margin: var(--s-1) 0; }
.sidebar-row  { display: flex; justify-content: space-between; align-items: center; gap: var(--s-2); margin-top: 3px; }
.sidebar-row--savings .sidebar-value { color: #4ade80; }
.sidebar-value--accent { color: var(--accent); font-size: var(--t-lg); font-weight: var(--fw-bold); }
.sidebar-value--sm     { font-size: var(--t-sm); font-family: var(--font-mono); }
.sidebar-block--flat   { padding: var(--s-2) var(--s-4); }
.sidebar-block--density { padding: var(--s-2) var(--s-4); border-color: rgba(251,191,36,.2); }
.sidebar-block--reco   { padding: var(--s-2) var(--s-4); border-color: rgba(99,102,241,.3); }

.density-mini { display: flex; height: 6px; border-radius: 3px; overflow: hidden; margin: 6px 0 4px; }
.density-mini-fill { background: #166534; transition: width .3s; }
.density-mini-junk { background: #78350f; transition: width .3s; }

.btn-apply-reco-side {
  margin-top: var(--s-2); padding: 3px 10px;
  border: 1px solid var(--accent); color: var(--accent);
  background: none; border-radius: var(--r-pill);
  font-size: var(--t-xs); cursor: pointer;
}
.btn-apply-reco-side:hover { background: var(--accent); color: #fff; }

/* Badge sm dans sidebar */
.badge-pertinence--sm { font-size: var(--t-xs); padding: 3px 8px; margin-top: 4px; }

/* Bouton Revoir prompt */
.btn-review {
  padding: 4px 12px; border-radius: var(--r-pill);
  border: 1px solid var(--accent); color: var(--accent);
  background: none; font-size: var(--t-sm); cursor: pointer;
  transition: background .15s, color .15s;
}
.btn-review:hover { background: var(--accent); color: #fff; }

@media (max-width: 1100px) {
  .chat-outer { grid-template-columns: 200px 1fr; grid-template-areas: "history main"; }
  .chat-sidebar { display: none; }
  .chat-layout { border-right: none; padding-right: 0; }
}
@media (max-width: 700px) {
  .chat-outer {
    display: block;
    position: relative;
    height: 100%;
    overflow: hidden;
  }
  .chat-history,
  .chat-layout,
  .chat-sidebar {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: none;
  }
  .chat-history { display: flex; flex-direction: column; }
  .chat-sidebar { display: flex; flex-direction: column; overflow-y: auto; }
  .chat-history.tab-hidden,
  .chat-layout.tab-hidden,
  .chat-sidebar.tab-hidden { display: none; }
  .mobile-tabs { display: flex; }
}

@media (max-width: 700px) {
  main:has(.chat-outer) {
    height: calc(100dvh - 56px - 56px) !important;
    margin-top: 0 !important;
  }
}

/* ── Mobile tabs ── */
.title-tabs-row { display: flex; align-items: center; gap: var(--s-3); }
.mobile-back {
  display: none; align-items: center; justify-content: center;
  width: 32px; height: 32px; border-radius: var(--r-md);
  background: var(--accent); border: none; cursor: pointer; color: #fff; flex-shrink: 0;
}
.mobile-back svg { width: 16px; height: 16px; }
@media (max-width: 700px) { .mobile-back { display: flex; } }
.mobile-tabs { display: none; align-items: center; gap: 4px; }
.mobile-tab {
  display: flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; border-radius: var(--r-md);
  background: none; border: 1px solid var(--border);
  cursor: pointer; color: var(--fg-muted); transition: color .15s, border-color .15s, background .15s;
}
.mobile-tab svg { width: 18px; height: 18px; }
.mobile-tab.active { color: var(--accent); border-color: var(--accent); background: rgba(var(--accent-rgb, 99,102,241), .08); }

@media (max-width: 700px) {
  .mobile-tabs { display: flex; }
}

@media (max-width: 700px) {
  main:has(.chat-outer) { height: calc(100dvh - 56px) !important; }
}

/* ── Panes hauteur égale ── */

/* Toast */
.toast {
  position: fixed; bottom: var(--s-6); right: var(--s-6);
  background: var(--fg); color: var(--bg-base);
  padding: var(--s-2) var(--s-4); border-radius: var(--r-md);
  font-size: var(--t-sm); z-index: 9999; pointer-events: none;
}

/* Header */
.chat-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--s-4) 0; border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.chat-title { font-size: var(--t-xl); font-weight: var(--fw-bold); color: var(--fg); }
.chat-sub        { font-size: var(--t-xs); color: var(--fg-dim); margin-top: 2px; display: block; }
.session-live    { font-family: var(--font-mono); }
.live-accent     { color: var(--accent); }
.header-controls { display: flex; align-items: center; gap: var(--s-3); }
.btn-export {
  padding: 6px 12px; border: 1px solid var(--border); border-radius: var(--r-md);
  background: none; color: var(--fg-dim); font-size: var(--t-sm); cursor: pointer;
}
.btn-export:hover { border-color: var(--fg-muted); color: var(--fg); }
.btn-new-chat {
  padding: 6px 12px; border: 1px solid var(--border); border-radius: var(--r-md);
  background: none; color: var(--fg-dim); font-size: var(--t-sm); cursor: pointer;
}
.btn-new-chat:hover:not(:disabled) { border-color: var(--fg-muted); color: var(--fg); }
.btn-new-chat:disabled { opacity: 0.35; cursor: not-allowed; }
.btn-config {
  padding: 6px 12px; border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--bg-surface); color: var(--fg-muted); font-size: var(--t-sm); cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.btn-config:hover { border-color: var(--fg-muted); color: var(--fg); }
.btn-config.active { border-color: var(--ok); color: var(--ok); }
.config-dot { color: var(--ok); }

/* Config panel */
.config-panel {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: var(--s-4); margin: var(--s-3) 0; flex-shrink: 0;
}
.config-panel-header {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--s-3);
}
.config-title { font-size: var(--t-sm); font-weight: var(--fw-semibold); color: var(--fg-muted); }
.btn-close-panel {
  background: none; border: none; color: var(--fg-dim); font-size: 1.2rem; cursor: pointer; padding: 0 4px;
}
.btn-close-panel:hover { color: var(--fg); }
.config-row { display: flex; align-items: center; gap: var(--s-2); margin-bottom: var(--s-3); }
.config-label { font-size: var(--t-xs); color: var(--fg-dim); white-space: nowrap; }
.sel {
  padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--bg-surface); color: var(--fg); font-size: var(--t-sm); cursor: pointer;
}
.config-keys-title {
  font-size: var(--t-xs); color: var(--fg-muted); margin: var(--s-3) 0 var(--s-2);
  display: flex; align-items: center; gap: var(--s-2);
}
.config-provider-row {
  display: flex; align-items: center; gap: var(--s-2); padding: var(--s-2) 0;
  border-top: 1px solid var(--border);
}
.provider-name { font-size: var(--t-sm); font-weight: var(--fw-semibold); width: 80px; flex-shrink: 0; }
.provider-status { font-size: 0.7rem; width: 16px; flex-shrink: 0; }
.provider-status.has-key { color: var(--co2-avoided, #22c55e); }
.provider-status.no-key  { color: var(--fg-dim); }
.key-note  { font-size: var(--t-xs); color: var(--fg-dim); }
.key-input {
  flex: 1; padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--r-md);
  background: var(--bg-base); color: var(--fg); font-size: var(--t-sm); font-family: var(--font-mono);
}
.btn-eye {
  padding: 6px 8px; background: none; border: 1px solid var(--border);
  border-radius: var(--r-md); cursor: pointer; font-size: var(--t-sm);
}
.btn-save-key {
  padding: 6px 12px; background: var(--accent); color: #fff;
  border: none; border-radius: var(--r-md); cursor: pointer; font-size: var(--t-sm);
}
.btn-edit-key {
  padding: 4px 10px; border: 1px solid var(--border); color: var(--fg-muted);
  background: none; border-radius: var(--r-md); cursor: pointer; font-size: var(--t-xs);
}
.btn-edit-key:hover { border-color: var(--accent); color: var(--accent); }
.btn-clear-key {
  padding: 4px 10px; border: 1px solid var(--danger); color: var(--danger);
  background: none; border-radius: var(--r-md); cursor: pointer; font-size: var(--t-xs);
}
.config-autoroute {
  display: flex; align-items: center; gap: var(--s-2); margin-top: var(--s-3);
  padding-top: var(--s-3); border-top: 1px solid var(--border);
  font-size: var(--t-sm); color: var(--fg-muted); cursor: pointer;
}
.config-autoroute input { cursor: pointer; accent-color: var(--accent); }

/* Banners */
.model-warning {
  font-size: var(--t-xs); color: var(--fg-muted);
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: var(--s-2) var(--s-3);
}

/* Messages */
.messages-area {
  flex: 1; min-height: 0; overflow-y: auto; padding: var(--s-4) 0;
  display: flex; flex-direction: column; gap: var(--s-3);
}

/* Empty state */
.empty-chat {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--fg-dim); text-align: center; gap: var(--s-3);
}
.empty-icon  { font-size: 2.5rem; color: var(--accent); opacity: 0.5; }
.empty-title { font-size: var(--t-base); color: var(--fg-muted); font-weight: var(--fw-semibold); }
.empty-sub   { font-size: var(--t-sm); color: var(--fg-dim); }
.suggestions { display: flex; flex-wrap: wrap; gap: var(--s-2); justify-content: center; margin-top: var(--s-1); }
.suggestion-chip {
  padding: 6px 14px; border: 1px solid var(--border); border-radius: var(--r-pill);
  background: var(--bg-surface); color: var(--fg-muted); font-size: var(--t-sm);
  cursor: pointer; transition: border-color 0.15s, color 0.15s;
}
.suggestion-chip:hover { border-color: var(--accent); color: var(--accent); }

/* Bubbles */
.msg-wrap { display: flex; }
.msg-wrap.user      { justify-content: flex-end; }
.msg-wrap.assistant { justify-content: flex-start; }
.bubble {
  max-width: 72%; padding: var(--s-4) var(--s-5);
  border-radius: var(--r-xl); font-size: var(--t-sm); line-height: var(--lh-normal);
}
.msg-wrap.user      .bubble { background: var(--accent); color: #fff; border-bottom-right-radius: 4px; }
.msg-wrap.assistant .bubble {
  background: var(--bg-surface); border: 1px solid var(--border);
  color: var(--fg); border-bottom-left-radius: 4px; max-width: 88%;
}
.msg-wrap.assistant .bubble.is-error {
  background: rgba(220, 38, 38, 0.07); border-color: var(--danger);
}
.msg-wrap.assistant .bubble.is-error .bubble-content { color: var(--danger); }
.bubble-meta {
  margin-top: var(--s-2); font-size: var(--t-xs);
  opacity: 0.65; font-family: var(--font-mono);
  display: flex; flex-direction: column; gap: 2px;
}
.bubble-optimized { margin-top: var(--s-1); font-size: var(--t-xs); opacity: 0.75; }
.bubble-quality   { margin-top: 2px; font-size: var(--t-xs); display: flex; align-items: center; gap: var(--s-2); opacity: 0.9; }
.qn-score         { font-weight: var(--fw-semibold); padding: 1px 6px; border-radius: var(--r-pill); }
.qn-score.qn-good { color: #fff; background: rgba(74,222,128,0.30); }
.qn-score.qn-mid  { color: #fff; background: rgba(251,191,36,0.35); }
.qn-score.qn-low  { color: #fff; background: rgba(248,113,113,0.35); }
.qn-sep           { opacity: 0.5; }
.qn-axes          { opacity: 0.85; }
.bubble-routed { margin-top: var(--s-1); font-size: var(--t-xs); color: var(--accent); opacity: 0.8; }
.compact-sep {
  text-align: center; font-size: var(--t-xs); color: var(--fg-dim);
  padding: var(--s-2) 0; margin: var(--s-2) 0;
  border-top: 1px dashed var(--border); border-bottom: 1px dashed var(--border);
}
.bubble-content code {
  background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono);
}
.bubble-content h3 { font-size: var(--t-base); font-weight: var(--fw-bold); margin: var(--s-2) 0 var(--s-1); }
.bubble-content h4 { font-size: var(--t-sm); font-weight: var(--fw-bold); margin: var(--s-2) 0 var(--s-1); }
.code-block {
  position: relative; margin: var(--s-2) 0;
  background: rgba(0,0,0,0.08); border-radius: var(--r-md); overflow: hidden;
}
.code-block pre { padding: var(--s-4); overflow-x: auto; margin: 0; font-family: var(--font-mono); font-size: var(--t-xs); }
.btn-copy {
  position: absolute; top: var(--s-2); right: var(--s-2);
  padding: 2px 8px; font-size: var(--t-xs);
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-md); cursor: pointer; color: var(--fg-muted);
  opacity: 0; transition: opacity 0.15s;
}
.code-block:hover .btn-copy { opacity: 1; }

/* Bouton optim pendant chargement */
.btn-optim-peek {
  margin-top: 6px; align-self: flex-start;
  padding: 4px 12px; border-radius: var(--r-pill);
  border: 1px solid var(--accent); color: var(--accent);
  background: transparent; font-size: 12px; cursor: pointer;
  transition: background .15s, color .15s;
}
.btn-optim-peek:hover { background: var(--accent); color: #fff; }

/* Thinking */
.thinking { display: flex; align-items: center; gap: 5px; padding: var(--s-4); }
.thinking span { width: 8px; height: 8px; border-radius: 50%; background: var(--fg-dim); animation: bounce 1.2s infinite; }
.thinking span:nth-child(2) { animation-delay: 0.2s; }
.thinking span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* Input area */
.input-area {
  border-top: 1px solid var(--border); padding: var(--s-4) 0 var(--s-2); flex-shrink: 0;
  display: flex; flex-direction: column; gap: var(--s-3);
}
.optimize-bar { display: flex; }
.opt-toggle {
  padding: 4px 14px; border-radius: var(--r-pill); border: 1px solid var(--border);
  background: none; color: var(--fg-dim); font-size: var(--t-sm); cursor: pointer; transition: all 0.2s;
}
.opt-toggle.on { border-color: var(--accent); color: var(--accent); }
.opt-toggle.opt-badge {
  background: rgba(var(--accent-rgb, 99,102,241), 0.08);
  border-color: var(--accent); color: var(--accent);
  font-weight: var(--fw-semibold);
  padding-left: 10px;
}
.opt-toggle.opt-badge::before {
  content: '';
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #22c55e;
  margin-right: 7px;
  vertical-align: middle;
  box-shadow: 0 0 0 2px rgba(34,197,94,0.2);
}
.step { display: flex; flex-direction: column; gap: var(--s-2); }
.step-header { display: flex; align-items: center; justify-content: space-between; }
.step-label {
  font-size: var(--t-xs); text-transform: uppercase; letter-spacing: var(--tracking-wide);
  color: var(--fg-dim); font-weight: var(--fw-semibold);
}
.token-count { font-size: var(--t-xs); color: var(--fg-dim); font-family: var(--font-mono); }
.chat-input {
  width: 100%; padding: var(--s-3) var(--s-4); border: 1px solid var(--border);
  border-radius: var(--r-lg); background: var(--bg-surface); color: var(--fg);
  font-size: var(--t-sm); resize: none; line-height: var(--lh-normal); font-family: inherit;
  box-sizing: border-box; min-height: 60px; max-height: 200px; overflow-y: auto;
}
.chat-input:focus { outline: none; border-color: var(--accent); }
.step-actions { display: flex; align-items: center; gap: var(--s-3); justify-content: flex-end; }
.sel-palier {
  padding: 6px 10px; border: 1px solid var(--accent); border-radius: var(--r-md);
  background: var(--bg-surface); color: var(--accent); font-size: var(--t-sm); cursor: pointer;
  flex: 1; max-width: 260px;
}
.btn-primary {
  padding: 8px 20px; background: var(--accent); color: #fff;
  border: none; border-radius: var(--r-lg); cursor: pointer;
  font-weight: var(--fw-semibold); font-size: var(--t-sm);
}
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-cancel {
  padding: 8px 14px; border: 1px solid var(--border); color: var(--fg-muted);
  background: none; border-radius: var(--r-lg); cursor: pointer; font-size: var(--t-sm);
}
.btn-cancel:hover { border-color: var(--fg-muted); color: var(--fg); }

/* Input footer */
.input-footer { min-height: 20px; }
.guest-hint {
  font-size: var(--t-xs); color: var(--fg-muted);
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: var(--s-2) var(--s-3);
}
.guest-hint a { color: var(--accent); text-decoration: none; font-weight: var(--fw-semibold); }

.guest-limit-banner {
  display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap;
  font-size: var(--t-xs); padding: var(--s-2) var(--s-3);
  background: var(--accent-soft); border: 1px solid rgba(52,211,153,.28);
  border-radius: var(--r-md); color: var(--fg-muted);
}
.guest-limit-link {
  color: var(--accent); font-weight: var(--fw-semibold); text-decoration: none;
}
.guest-limit-link:hover { text-decoration: underline; }
.input-hint { font-size: var(--t-xs); color: var(--fg-dim); }
.cant-send-hint {
  font-size: var(--t-xs); color: var(--fg-muted);
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: var(--s-2) var(--s-3);
}

/* ─── MODAL OPTIMISEUR ─── */
.modal-overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0, 0, 0, 0.55);
  display: flex; align-items: center; justify-content: center;
  padding: var(--s-4);
}
.modal-card {
  background: var(--bg-base); border: 1px solid var(--border);
  border-radius: var(--r-xl); width: 100%; max-width: 780px;
  display: flex; flex-direction: column;
  max-height: 90vh; overflow-y: auto;
  box-shadow: 0 24px 80px rgba(0,0,0,0.35);
}
.modal-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  padding: var(--s-5) var(--s-6); border-bottom: 1px solid var(--border); flex-shrink: 0;
}
.modal-header-left { display: flex; flex-direction: column; gap: var(--s-1); }
.modal-title { font-size: var(--t-lg); font-weight: var(--fw-bold); color: var(--fg); }
.modal-error-badge {
  font-size: var(--t-xs); color: var(--danger);
  background: rgba(220,38,38,0.08); border: 1px solid var(--danger);
  border-radius: var(--r-md); padding: 3px 8px; display: inline-block;
}
.modal-close {
  background: none; border: none; color: var(--fg-dim); font-size: 1.5rem;
  cursor: pointer; padding: 0 4px; line-height: 1; flex-shrink: 0; margin-top: 2px;
}
.modal-close:hover { color: var(--fg); }

.modal-compare {
  display: grid; grid-template-columns: 1fr 1fr;
  gap: var(--s-4); padding: var(--s-5) var(--s-6); align-items: stretch;
}
.compare-pane { display: flex; flex-direction: column; gap: var(--s-2); }
.compare-pane:first-child { border-right: 1px solid var(--border); padding-right: var(--s-4); }
.pane-label {
  font-size: var(--t-xs); text-transform: uppercase; letter-spacing: var(--tracking-wide);
  color: var(--fg-dim); font-weight: var(--fw-semibold);
}
.optimized-label { color: var(--accent); }
.pane-edit-hint { text-transform: none; letter-spacing: 0; color: var(--fg-dim); font-weight: var(--fw-normal); font-style: italic; }
.pane-text {
  padding: var(--s-3) var(--s-4);
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); font-size: var(--t-sm); line-height: var(--lh-normal);
  color: var(--fg-dim); min-height: 140px; flex: 1; overflow-y: auto;
  white-space: pre-wrap; word-break: break-word;
}
.pane-textarea {
  width: 100%; padding: var(--s-3) var(--s-4);
  border: 1.5px solid var(--accent); border-radius: var(--r-lg);
  background: var(--bg-surface); color: var(--fg);
  font-size: var(--t-sm); line-height: var(--lh-normal); font-family: inherit;
  min-height: 140px; flex: 1; resize: none; box-sizing: border-box;
  overflow-y: auto;
}
.pane-textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 2px rgba(var(--accent-rgb, 99,102,241), 0.12); }
.pane-textarea.has-error { border-color: var(--danger); }

/* ── Animations deux phases ── */
.pane-scanning {
  position: relative; overflow: hidden;
}
.pane-scanning::after {
  content: '';
  position: absolute; left: 0; right: 0; height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  top: 0; opacity: 0;
  animation: scan-down 1.1s ease-in-out infinite;
}
@keyframes scan-down {
  0%   { top: 0;    opacity: 0; }
  15%  { opacity: 0.7; }
  85%  { opacity: 0.7; }
  100% { top: 100%; opacity: 0; }
}
.pane-reading-hint {
  font-size: var(--t-xs); color: var(--accent); font-family: var(--font-mono);
  letter-spacing: .04em; padding: 4px 0 2px; animation: pulse-text 1s ease-in-out infinite;
}
@keyframes pulse-text { 0%, 100% { opacity: 0.5; } 50% { opacity: 1; } }

.pane-loading {
  display: flex; align-items: center; justify-content: center;
  gap: 6px; min-height: 120px; background: var(--bg-surface-2);
}
.loading-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
  animation: dot-bounce 1s ease-in-out infinite;
}
.loading-dot:nth-child(2) { animation-delay: .15s; }
.loading-dot:nth-child(3) { animation-delay: .30s; }
@keyframes dot-bounce { 0%, 100% { transform: scale(0.6); opacity: 0.3; } 50% { transform: scale(1); opacity: 1; } }

.pane-typewriter {
  font-family: var(--font-mono); font-size: var(--t-sm); line-height: 1.65;
  color: var(--accent); background: var(--bg-surface);
  border: 1px solid var(--border); border-radius: var(--r-lg);
  padding: var(--s-3) var(--s-4); min-height: 120px;
  white-space: pre-wrap; word-break: break-word; overflow-y: auto;
}
.cursor-blink {
  display: inline-block; font-weight: 100; color: var(--accent);
  animation: blink .65s step-end infinite;
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.writing-hint { color: var(--accent); font-style: normal; }
.constraint-chip {
  display: flex; align-items: center; gap: var(--s-2);
  padding: 5px var(--s-3); border-radius: var(--r-md);
  background: rgba(var(--accent-rgb, 52,211,153), 0.06);
  border: 1px solid rgba(var(--accent-rgb, 52,211,153), 0.25);
  font-size: var(--t-xs); color: var(--fg-dim);
}
.constraint-chip svg { color: var(--accent); flex-shrink: 0; }
.constraint-text { font-family: var(--font-mono); color: var(--fg-muted); }
.constraint-label { margin-left: auto; font-size: 10px; color: var(--fg-dim); letter-spacing: .03em; }

.modal-stats {
  display: flex; align-items: center; gap: var(--s-4); flex-wrap: wrap;
  padding: var(--s-4) var(--s-6);
  background: var(--bg-surface); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.stat-item { display: flex; flex-direction: column; gap: 2px; }
.stat-value {
  font-size: 1.35rem; font-weight: var(--fw-bold); color: var(--fg);
  font-family: var(--font-mono); line-height: 1;
}
.stat-value.accent { color: var(--accent); }
.stat-value.ok   { color: var(--ok); }
.stat-value.warn { color: var(--co2-high, #f59e0b); }
.stat-value.mono { font-size: var(--t-sm); font-family: inherit; }
.stat-label { font-size: var(--t-xs); color: var(--fg-dim); white-space: nowrap; }
.stat-sep { width: 1px; height: 32px; background: var(--border); flex-shrink: 0; }

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

.modal-output-stats {
  padding: var(--s-4) var(--s-6);
  border-bottom: 1px solid var(--border);
  background: var(--bg-base);
}
.output-cards {
  display: flex; gap: var(--s-3); flex-wrap: wrap;
}
.output-card {
  flex: 1; min-width: 120px;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: var(--s-3) var(--s-4);
}
.output-card.ok   { border-color: #166534; }
.output-card.warn { border-color: #92400e; }
.output-card.bad  { border-color: #7f1d1d; }
.savings-card { border-color: var(--co2-avoided, #22c55e); }
.output-card-value {
  font-size: 1.2rem; font-weight: var(--fw-bold); color: var(--accent);
  line-height: 1.2; margin-bottom: 2px;
}
.output-card.ok   .output-card-value { color: var(--ok); }
.output-card.warn .output-card-value { color: var(--warn, #f59e0b); }
.output-card.bad  .output-card-value { color: var(--danger); }
.savings-pct { font-size: 1.5rem; color: var(--co2-avoided, #22c55e); }
.output-card-value small { font-size: 0.7em; font-weight: var(--fw-normal); color: var(--fg-dim); }
.output-card-sub   { font-size: var(--t-xs); color: var(--fg-dim); margin-bottom: var(--s-2); }
.output-card-label { font-size: var(--t-xs); color: var(--fg-muted); text-transform: uppercase; letter-spacing: 0.05em; }

.modal-underspec {
  padding: var(--s-4) var(--s-6);
  border-top: 1px solid #92400e;
}
.modal-underspec .underspec-header { font-size: var(--t-sm); font-weight: var(--fw-semibold); color: #fcd34d; margin-bottom: var(--s-1); }
.modal-underspec .underspec-tip    { font-size: var(--t-xs); color: var(--fg-dim); margin: 0; }

.modal-density {
  padding: var(--s-4) var(--s-6);
  border-top: 1px solid #b45309;
  background: #1c120200;
}
.modal-density .density-header { font-size: var(--t-sm); font-weight: var(--fw-semibold); color: #fbbf24; margin-bottom: var(--s-2); }
.modal-density .density-bar { display: flex; border-radius: var(--r-md); overflow: hidden; height: 28px; margin-bottom: var(--s-2); }
.modal-density .bar-signal { background: #166534; color: #86efac; font-size: var(--t-xs); font-weight: var(--fw-semibold); display: flex; align-items: center; justify-content: center; min-width: 50px; transition: width 0.3s; }
.modal-density .bar-junk   { background: #78350f; color: #fcd34d; font-size: var(--t-xs); font-weight: var(--fw-semibold); display: flex; align-items: center; justify-content: center; min-width: 36px; transition: width 0.3s; }
.modal-density .density-tip { font-size: var(--t-xs); color: var(--fg-dim); margin: 0; }

/* ── Accordéons ── */
/* E3 — Chips dans le modal */
.modal-chips {
  padding: var(--s-4) var(--s-6);
  border-top: 1px solid var(--border);
  background: rgba(99,102,241,0.04);
}
.modal-chips .chips-hint {
  font-size: var(--t-xs); color: var(--fg-dim); margin: 0 0 var(--s-3);
}
.modal-chips .chip-row {
  display: flex; align-items: center; flex-wrap: wrap;
  gap: var(--s-3); margin-bottom: var(--s-2);
}
.modal-chips .chip-label {
  font-size: var(--t-xs); color: var(--fg-muted);
  white-space: nowrap; min-width: 120px;
}
.modal-chips .chip-options { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.modal-chips .chip-opt {
  padding: 3px 12px; border-radius: var(--r-pill);
  border: 1px solid var(--border); background: var(--bg-base);
  color: var(--fg-dim); font-size: var(--t-xs); cursor: pointer;
  transition: border-color .15s, color .15s;
}
.modal-chips .chip-opt:hover { border-color: #6366f1; color: #a5b4fc; }

.modal-accordion {
  border-top: 1px solid var(--border);
}
.modal-accordion[open] > .accordion-summary { color: var(--fg); }
.accordion-summary {
  list-style: none; padding: var(--s-3) var(--s-6);
  font-size: var(--t-sm); color: var(--fg-muted);
  cursor: pointer; user-select: none;
  display: flex; align-items: center; gap: var(--s-2);
  transition: color .15s;
}
.accordion-summary:hover { color: var(--fg); }
.accordion-summary::before {
  content: '▶'; font-size: 0.6rem; transition: transform .2s;
}
.modal-accordion[open] .accordion-summary::before { transform: rotate(90deg); }
.accordion-summary::-webkit-details-marker { display: none; }

.modal-rules {
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--s-2);
  padding: var(--s-2) var(--s-6) var(--s-4);
}
.rule-chip {
  font-size: var(--t-xs); padding: 2px 8px;
  border: 1px solid var(--accent); border-radius: var(--r-pill);
  color: var(--accent); opacity: 0.75; font-family: var(--font-mono);
}

/* Badge Qwen dans le label OPTIMISÉ */
.qwen-badge {
  display: inline-block; margin-left: 6px; padding: 1px 7px;
  border-radius: var(--r-pill); font-size: var(--t-xs); font-weight: var(--fw-semibold);
  background: rgba(99,102,241,0.15); border: 1px solid #6366f1; color: #a5b4fc;
}

/* Tableau qualité avant/après */
.quality-compare-table { padding: var(--s-3) var(--s-6); }
.quality-compare-table table { width: 100%; border-collapse: collapse; font-size: var(--t-sm); }
.quality-compare-table th { color: var(--fg-dim); font-weight: var(--fw-semibold); padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--border); }
.quality-compare-table td { padding: 6px 10px; color: var(--fg-2); }
.quality-compare-table td.score-green { color: #4ade80; font-weight: var(--fw-semibold); }
.quality-compare-table td.score-orange { color: #fb923c; font-weight: var(--fw-semibold); }
.quality-compare-table td.score-red { color: #f87171; font-weight: var(--fw-semibold); }

/* Accordéon Qwen — audit + ambiguïtés */
.qwen-detail { padding: var(--s-3) var(--s-6); display: flex; flex-direction: column; gap: var(--s-3); }
.qwen-ambig {
  display: flex; align-items: center; flex-wrap: wrap; gap: var(--s-2);
  background: rgba(180,83,9,0.12); border: 1px solid #92400e; border-radius: var(--r-lg);
  padding: 8px 12px;
}
.ambig-icon { color: #fbbf24; font-size: var(--t-sm); }
.ambig-item { font-size: var(--t-xs); color: #fcd34d; padding: 2px 8px; background: rgba(180,83,9,0.2); border-radius: var(--r-pill); }
.audit-badges { display: flex; flex-wrap: wrap; gap: var(--s-2); }
.audit-badge {
  font-size: var(--t-xs); padding: 3px 10px; border-radius: var(--r-pill);
  border: 1px solid var(--border); color: var(--fg-muted);
}
.audit-sep { color: var(--fg-dim); margin: 0 3px; }
.audit-badge em { font-style: normal; font-weight: var(--fw-semibold); }
.audit-badge.audit-present em  { color: #4ade80; }
.audit-badge.audit-inferred em { color: #fbbf24; }
.audit-badge.audit-absent em   { color: #6b7280; }

/* Badge template type (standard/pedagogique) */
.template-badge { margin-left: 8px; padding: 1px 7px; border-radius: var(--r-pill); font-size: var(--t-xs); font-weight: var(--fw-semibold); }
.template-badge.standard    { background: rgba(6,95,70,0.2); border: 1px solid #065f46; color: #34d399; }
.template-badge.pedagogique { background: rgba(30,58,138,0.2); border: 1px solid #1d4ed8; color: #93c5fd; }

.modal-recommendation {
  display: flex; align-items: center; gap: var(--s-3); flex-wrap: wrap;
  padding: var(--s-3) var(--s-6);
  font-size: var(--t-sm); color: var(--fg-muted);
  background: rgba(99,102,241,0.05); border-bottom: 1px solid var(--border);
}
.btn-apply-rec {
  padding: 4px 12px; border: 1px solid var(--accent); color: var(--accent);
  background: none; border-radius: var(--r-pill); cursor: pointer;
  font-size: var(--t-xs); font-weight: var(--fw-semibold); white-space: nowrap;
}
.btn-apply-rec:hover { background: var(--accent); color: #fff; }
.modal-recommendation.guest { color: var(--fg-dim); font-style: italic; }
.reco-task { color: var(--fg-dim); font-size: var(--t-xs); }
.reco-effort { color: var(--accent); font-weight: var(--fw-semibold); }

.modal-footer {
  padding: var(--s-4) var(--s-6); flex-shrink: 0;
  display: flex; flex-direction: column; gap: var(--s-2);
}
.modal-cant-send {
  font-size: var(--t-xs); color: var(--fg-muted);
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: var(--s-2) var(--s-3);
}
.modal-actions { display: flex; gap: var(--s-3); justify-content: flex-end; align-items: center; }

/* ── Tooltip hover bouton envoyer optimisé ── */
.btn-send-wrap { position: relative; }
.send-tooltip {
  position: absolute; bottom: calc(100% + 10px); right: 0;
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--r-lg); padding: var(--s-3) var(--s-4);
  min-width: 210px; box-shadow: 0 8px 24px rgba(0,0,0,.3);
  opacity: 0; pointer-events: none;
  transition: opacity .15s, transform .15s;
  transform: translateY(4px);
  z-index: 10;
}
.btn-send-wrap:hover .send-tooltip {
  opacity: 1; transform: translateY(0);
}
.tooltip-row {
  display: flex; justify-content: space-between; align-items: center;
  font-size: var(--t-xs); color: var(--fg-muted); padding: 3px 0;
  gap: var(--s-4);
}
.tooltip-row span:last-child { color: var(--fg); font-weight: var(--fw-semibold); font-family: var(--font-mono); }
.tooltip-row--savings span:last-child { color: #4ade80; }
.btn-send-original {
  padding: 8px 16px; border: 1px solid var(--border); color: var(--fg-muted);
  background: none; border-radius: var(--r-lg); cursor: pointer; font-size: var(--t-sm);
}
.btn-send-original:hover:not(:disabled) { border-color: var(--fg-muted); color: var(--fg); }
.btn-send-original:disabled { opacity: 0.4; cursor: not-allowed; }

/* Mobile modal */
@media (max-width: 600px) {
  .modal-compare { grid-template-columns: 1fr; }
  .compare-pane:first-child { border-right: none; padding-right: 0; border-bottom: 1px solid var(--border); padding-bottom: var(--s-4); }
  .modal-card { max-height: 95vh; border-radius: var(--r-lg) var(--r-lg) 0 0; }
  .modal-overlay { align-items: flex-end; padding: 0; }
}

.sel-loading { font-size: var(--t-sm); color: var(--fg-dim); padding: 6px 0; }

/* Modal transition */
.modal-enter-active { transition: opacity 0.2s ease; }
.modal-leave-active { transition: opacity 0.15s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-active .modal-card { transition: transform 0.2s ease; }
.modal-leave-active .modal-card { transition: transform 0.15s ease; }
.modal-enter-from .modal-card { transform: scale(0.97) translateY(8px); }
.modal-leave-to   .modal-card { transform: scale(0.97) translateY(8px); }

/* Shared transitions */
.slide-enter-active, .slide-leave-active { transition: all 0.2s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-8px); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

<!-- Override global main pour la page chat uniquement -->
<style>
main:has(.chat-outer) {
  max-width: 100% !important;
  padding: 0 !important;
  margin: 0 !important;
  height: 100vh !important;
}
</style>
