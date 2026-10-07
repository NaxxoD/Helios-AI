/**
 * service_worker.js — background script (Manifest V3 service worker).
 *
 * Responsibilities:
 *  - Accumulate per-tab token data in tabSessions Map
 *  - Push overlay updates to the active tab's content script
 *  - Save sessions to the Helios backend (POST /api/sessions/from-extension)
 *  - Check auth status (GET /api/auth/me)
 */
'use strict';

const BACKEND = 'http://localhost:8000';

const SUPPORTED_HOSTS = ['chatgpt.com', 'claude.ai', 'gemini.google.com'];

// ---------------------------------------------------------------------------
// Inject fetch interceptor into MAIN world via scripting API (bypasses CSP)
// ---------------------------------------------------------------------------
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status !== 'loading') return;
  const url = tab.url ?? '';
  if (!SUPPORTED_HOSTS.some(h => url.includes(h))) return;

  chrome.scripting.executeScript({
    target: { tabId },
    files: ['content/inject.js'],
    world: 'MAIN',
  }).then(() => {
    console.log('[Helios SW] inject.js injected in tab', tabId, url);
  }).catch(err => {
    console.warn('[Helios SW] inject failed:', err.message);
  });
});

// In-memory per-tab session state (lives as long as the service worker is alive)
// { tabId: { platform, model, totalInput, totalOutput, turns, startedAt } }
const tabSessions = new Map();

const PROVIDER_MAP = {
  chatgpt: 'OpenAI',
  claude:  'Anthropic',
  gemini:  'Google',
};

// ---------------------------------------------------------------------------
// Message handler
// ---------------------------------------------------------------------------
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const tabId = sender.tab?.id ?? null;

  switch (message.type) {

    case 'TOKEN_USAGE':
      handleTokenUsage(tabId, message.payload).then(() => sendResponse({ ok: true }));
      return true; // async

    case 'SAVE_SESSION':
      saveSession(tabId, message.data ?? {}).then(sendResponse);
      return true; // async

    case 'GET_SESSION':
      getSession(tabId).then(sendResponse);
      return true; // async

    case 'RESET_SESSION':
      resetSession(tabId).then(() => sendResponse({ ok: true }));
      return true; // async

    case 'CHECK_AUTH':
      checkAuth().then(sendResponse);
      return true; // async
  }
});

// ---------------------------------------------------------------------------
// Storage helpers — persist sessions across service worker restarts (MV3)
// ---------------------------------------------------------------------------
function storageKey(tabId) { return `session_${tabId}`; }

async function loadSession(tabId) {
  const cached = tabSessions.get(tabId);
  if (cached) return cached;
  const result = await chrome.storage.session.get(storageKey(tabId));
  const session = result[storageKey(tabId)] ?? null;
  if (session) tabSessions.set(tabId, session);
  return session;
}

async function persistSession(tabId, session) {
  tabSessions.set(tabId, session);
  await chrome.storage.session.set({ [storageKey(tabId)]: session });
}

async function getSession(tabId) {
  if (tabId) return loadSession(tabId);
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab ? loadSession(tab.id) : null;
}

async function resetSession(tabId) {
  if (!tabId) return;
  tabSessions.delete(tabId);
  await chrome.storage.session.remove(storageKey(tabId));
  chrome.action.setBadgeText({ text: '', tabId }).catch(() => {});
}

// ---------------------------------------------------------------------------
// Token accumulation
// ---------------------------------------------------------------------------
async function handleTokenUsage(tabId, payload) {
  if (!tabId) return;

  let session = await loadSession(tabId);

  if (!session) {
    session = {
      platform:    payload.platform,
      model:       payload.model ?? null,
      totalInput:  0,
      totalOutput: 0,
      turns:       0,
      startedAt:   Date.now(),
    };
  }

  session.totalInput  += payload.input_tokens  ?? 0;
  session.totalOutput += payload.output_tokens ?? 0;
  session.turns       += 1;
  if (!session.model && payload.model) session.model = payload.model;

  await persistSession(tabId, session);

  // Update badge
  const total = session.totalInput + session.totalOutput;
  const label = total >= 1000 ? Math.round(total / 1000) + 'k' : String(total);
  chrome.action.setBadgeText({ text: label, tabId }).catch(() => {});
  chrome.action.setBadgeBackgroundColor({ color: '#ff6600', tabId }).catch(() => {});

  // Push to overlay
  chrome.tabs.sendMessage(tabId, {
    type: 'UPDATE_OVERLAY',
    data: { ...session },
  }).catch(() => {});

  // Notify popup if open
  chrome.runtime.sendMessage({
    type: 'SESSION_UPDATE',
    data: { tabId, session: { ...session } },
  }).catch(() => {});
}

// ---------------------------------------------------------------------------
// Auth check
// ---------------------------------------------------------------------------
async function checkAuth() {
  try {
    const res = await fetch(`${BACKEND}/api/auth/me`, {
      credentials: 'include',
    });
    if (!res.ok) return { authenticated: false, user: null };
    const data = await res.json();
    return { authenticated: !!data.user, user: data.user ?? null };
  } catch {
    return { authenticated: false, user: null };
  }
}

// ---------------------------------------------------------------------------
// Save session to Helios
// ---------------------------------------------------------------------------
async function saveSession(tabId, overrides) {
  // Resolve tabId from active tab when called from popup
  let resolvedTabId = tabId;
  if (!resolvedTabId) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    resolvedTabId = tab?.id ?? null;
  }

  if (!resolvedTabId) return { error: 'Aucun onglet actif trouvé.' };

  const session = await loadSession(resolvedTabId);
  if (!session) return { error: 'Aucune session en cours pour cet onglet.' };

  const totalTokens = session.totalInput + session.totalOutput;
  if (totalTokens === 0) return { error: 'Aucun token enregistré dans cette session.' };

  const now = new Date().toLocaleDateString('fr-FR', {
    day: '2-digit', month: '2-digit', year: 'numeric',
  });
  const platformLabel = session.platform.charAt(0).toUpperCase() + session.platform.slice(1);

  const body = {
    name:                overrides.name || `${platformLabel} — ${now}`,
    provider:            PROVIDER_MAP[session.platform] ?? session.platform,
    model:               session.model ?? overrides.model ?? '',
    exact_input_tokens:  session.totalInput,
    exact_output_tokens: session.totalOutput,
    exact_total_tokens:  totalTokens,
    nb_turns:            session.turns,
  };

  try {
    const res = await fetch(`${BACKEND}/api/sessions/from-extension`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (res.status === 401) return { error: 'not_authenticated' };

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { error: err.error ?? `Erreur HTTP ${res.status}` };
    }

    const saved = await res.json();

    // Clear local session + badge after successful save
    await resetSession(resolvedTabId);

    return { ok: true, session: saved };
  } catch (e) {
    return { error: e.message };
  }
}

// ---------------------------------------------------------------------------
// Clear session when tab is closed
// ---------------------------------------------------------------------------
chrome.tabs.onRemoved.addListener((tabId) => {
  tabSessions.delete(tabId);
  chrome.storage.session.remove(storageKey(tabId)).catch(() => {});
});
