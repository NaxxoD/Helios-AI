'use strict';

const KWH_TABLE = [
  ['gpt-4o-mini', 0.00000020], ['gpt-4o', 0.00000090], ['gpt-4', 0.00000170],
  ['gpt-3.5', 0.00000030], ['o1-mini', 0.00000040], ['o1', 0.00000200],
  ['claude-haiku', 0.00000020], ['claude-3-5-haiku', 0.00000020],
  ['claude-sonnet', 0.00000090], ['claude-3-5-sonnet', 0.00000090],
  ['claude-opus', 0.00000200],
  ['gemini-2.0-flash', 0.00000020], ['gemini-1.5-flash', 0.00000030],
  ['gemini-1.5-pro', 0.00000100], ['gemini-pro', 0.00000060],
];
const DEFAULT_KWH   = 0.000001;
const CO2_STD_G_KWH = 400;

function kwhPerToken(model) {
  if (!model) return DEFAULT_KWH;
  const lower = model.toLowerCase();
  for (const [key, val] of KWH_TABLE) {
    if (lower.includes(key)) return val;
  }
  return DEFAULT_KWH;
}

function fmtKwh(kwh) {
  if (kwh === 0) return '0 Wh';
  if (kwh >= 1)        return kwh.toFixed(3) + ' kWh';
  if (kwh >= 0.001)    return (kwh * 1000).toFixed(2) + ' Wh';
  if (kwh >= 0.000001) return (kwh * 1_000_000).toFixed(1) + ' mWh';
  return (kwh * 1_000_000_000).toFixed(0) + ' µWh';
}

function fmtCo2(g) {
  if (g < 0.001) return (g * 1000).toFixed(2) + ' µg';
  if (g < 1)     return (g * 1000).toFixed(1) + ' mg';
  return g.toFixed(3) + ' g';
}

function fmtN(n) { return n.toLocaleString('fr-FR'); }

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const $ = id => document.getElementById(id);

const authLabel  = $('auth-label');
const authDot    = $('auth-dot');
const idleMsg    = $('idle-msg');
const sessionDiv = $('session-data');
const pInput     = $('p-input');
const pOutput    = $('p-output');
const pTotal     = $('p-total');
const pTurns     = $('p-turns');
const pKwh       = $('p-kwh');
const pCo2       = $('p-co2');
const pModel     = $('p-model');
const btnSave    = $('btn-save');
const btnReset   = $('btn-reset');
const saveStatus = $('save-status');

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
async function init() {
  // 1. Auth check
  const auth = await chrome.runtime.sendMessage({ type: 'CHECK_AUTH' });
  if (auth.authenticated) {
    authLabel.textContent = auth.user.email;
    authDot.className = 'dot ok';
  } else {
    authLabel.textContent = 'Non connecté';
    authDot.className = 'dot err';
  }

  // 2. Current session
  const session = await chrome.runtime.sendMessage({ type: 'GET_SESSION' });
  renderSession(session);

  // 3. Live updates from service_worker
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'SESSION_UPDATE') renderSession(msg.data.session);
  });
}

function renderSession(session) {
  if (!session || (session.totalInput + session.totalOutput) === 0) {
    idleMsg.style.display = '';
    sessionDiv.style.display = 'none';
    btnSave.disabled = true;
    return;
  }

  idleMsg.style.display = 'none';
  sessionDiv.style.display = '';
  btnSave.disabled = false;

  const total = session.totalInput + session.totalOutput;
  const kwh   = total * kwhPerToken(session.model);
  const co2g  = kwh * CO2_STD_G_KWH;

  pInput.textContent  = fmtN(session.totalInput);
  pOutput.textContent = fmtN(session.totalOutput);
  pTotal.textContent  = fmtN(total);
  pTurns.textContent  = String(session.turns);
  pKwh.textContent    = fmtKwh(kwh);
  pCo2.textContent    = fmtCo2(co2g);
  pModel.textContent  = 'Modèle : ' + (session.model ?? '—');
}

// ---------------------------------------------------------------------------
// Buttons
// ---------------------------------------------------------------------------
btnSave.addEventListener('click', async () => {
  btnSave.disabled = true;
  setStatus('Sauvegarde en cours…', '');

  const result = await chrome.runtime.sendMessage({ type: 'SAVE_SESSION', data: {} });

  if (result.ok) {
    setStatus('Session sauvegardée !', 'ok');
    renderSession(null);
  } else if (result.error === 'not_authenticated') {
    setStatus('Connectez-vous sur Helios d\'abord.', 'err');
    btnSave.disabled = false;
  } else {
    setStatus('Erreur : ' + result.error, 'err');
    btnSave.disabled = false;
  }

  setTimeout(() => setStatus('', ''), 5000);
});

btnReset.addEventListener('click', async () => {
  await chrome.runtime.sendMessage({ type: 'RESET_SESSION' });
  renderSession(null);
  setStatus('Session réinitialisée.', 'ok');
  setTimeout(() => setStatus('', ''), 3000);
});

function setStatus(text, cls) {
  saveStatus.textContent = text;
  saveStatus.className = 'status' + (cls ? ' ' + cls : '');
}

init();
