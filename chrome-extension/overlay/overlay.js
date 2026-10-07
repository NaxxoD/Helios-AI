/**
 * overlay.js — Helios floating widget.
 *
 * Loaded as an ES module by content.js.
 * Mounts a shadow DOM widget on document.body — fully isolated from the host page's CSS.
 * Exposes window.__heliosUpdateOverlay() for content.js to call.
 */
'use strict';

// ---------------------------------------------------------------------------
// kWh lookup table (mirrors backend/utils/calculator.py seed values)
// Used for the live estimate; authoritative calculation happens server-side at save.
// ---------------------------------------------------------------------------
const KWH_TABLE = [
  ['gpt-4o-mini',          0.00000020],
  ['gpt-4o',               0.00000090],
  ['gpt-4-turbo',          0.00000170],
  ['gpt-4',                0.00000170],
  ['gpt-3.5',              0.00000030],
  ['o1-mini',              0.00000040],
  ['o1',                   0.00000200],
  ['claude-haiku',         0.00000020],
  ['claude-3-5-haiku',     0.00000020],
  ['claude-sonnet',        0.00000090],
  ['claude-3-5-sonnet',    0.00000090],
  ['claude-opus',          0.00000200],
  ['gemini-2.0-flash',     0.00000020],
  ['gemini-1.5-flash',     0.00000030],
  ['gemini-1.5-pro',       0.00000100],
  ['gemini-pro',           0.00000060],
];
const DEFAULT_KWH     = 0.000001;   // fallback
const CO2_STD_G_KWH   = 400;        // g CO₂ / kWh (standard grid mix)

function kwhPerToken(model) {
  if (!model) return DEFAULT_KWH;
  const lower = model.toLowerCase();
  for (const [key, val] of KWH_TABLE) {
    if (lower.includes(key)) return val;
  }
  return DEFAULT_KWH;
}

function fmtTokens(n) {
  return n.toLocaleString('fr-FR');
}

function fmtKwh(kwh) {
  if (kwh === 0) return '0 Wh';
  if (kwh >= 1)          return kwh.toFixed(3) + ' kWh';
  if (kwh >= 0.001)      return (kwh * 1000).toFixed(2) + ' Wh';
  if (kwh >= 0.000001)   return (kwh * 1_000_000).toFixed(1) + ' mWh';
  return (kwh * 1_000_000_000).toFixed(0) + ' µWh';
}

function fmtCo2(g) {
  if (g < 0.001) return (g * 1000).toFixed(2) + ' µg';
  if (g < 1)     return (g * 1000).toFixed(1) + ' mg';
  return g.toFixed(3) + ' g';
}

// ---------------------------------------------------------------------------
// Shadow DOM widget
// ---------------------------------------------------------------------------
const CSS = `
:host { all: initial; font-family: 'Inter', system-ui, sans-serif; }

* { box-sizing: border-box; margin: 0; padding: 0; }

.widget {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 230px;
  background: #1a1a2e;
  color: #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.45);
  border: 1px solid rgba(255,255,255,0.07);
  z-index: 2147483647;
  overflow: hidden;
  transition: box-shadow 0.2s;
  user-select: none;
}

.header {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 12px 9px;
  background: #003366;
  cursor: move;
}

.logo {
  width: 22px; height: 22px;
  background: #ff6600;
  border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 12px; color: #fff;
  flex-shrink: 0;
  letter-spacing: -0.5px;
}

.title {
  font-weight: 700;
  font-size: 12px;
  flex: 1;
  color: #e2e8f0;
}

.platform-badge {
  font-size: 9px;
  font-weight: 600;
  background: rgba(255,255,255,0.12);
  border-radius: 4px;
  padding: 1px 5px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.toggle-btn {
  background: none; border: none;
  color: #94a3b8; cursor: pointer;
  font-size: 17px; line-height: 1;
  padding: 0; width: 18px;
  display: flex; align-items: center; justify-content: center;
}
.toggle-btn:hover { color: #e2e8f0; }

.body { padding: 10px 12px 12px; }

.metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 12px;
}
.metric:last-of-type { border-bottom: none; }

.metric .lbl { color: #94a3b8; }
.metric .val { font-weight: 600; font-variant-numeric: tabular-nums; }

.metric.hi .val { color: #ff6600; font-weight: 700; font-size: 13px; }
.metric.green .val { color: #4ade80; }
.metric.blue  .val { color: #60a5fa; }

.model-row {
  margin-top: 7px;
  font-size: 10px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.save-btn {
  margin-top: 10px;
  width: 100%;
  padding: 8px 0;
  background: #ff6600;
  border: none;
  border-radius: 9px;
  color: #fff;
  font-weight: 700;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s, opacity 0.15s;
  letter-spacing: 0.2px;
}
.save-btn:hover:not(:disabled) { background: #ff8533; }
.save-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.reset-btn {
  margin-top: 5px;
  width: 100%;
  padding: 5px 0;
  background: none;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 7px;
  color: #64748b;
  font-size: 10px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.reset-btn:hover { border-color: rgba(255,255,255,0.25); color: #94a3b8; }

.status {
  margin-top: 7px;
  font-size: 10px;
  text-align: center;
  min-height: 14px;
  color: #64748b;
}
.status.ok  { color: #4ade80; }
.status.err { color: #f87171; }

.idle-msg {
  padding: 20px 0 10px;
  text-align: center;
  font-size: 11px;
  color: #475569;
  line-height: 1.5;
}
`;

const HTML = `
<div class="header" id="h-header">
  <div class="logo">H</div>
  <span class="title">Helios Tracker</span>
  <span class="platform-badge" id="h-platform">—</span>
  <button class="toggle-btn" id="h-toggle" title="Réduire">−</button>
</div>
<div class="body" id="h-body">
  <div class="idle-msg" id="h-idle">
    En attente d'une<br>conversation IA…
  </div>
  <div id="h-metrics" style="display:none">
    <div class="metric">
      <span class="lbl">Tokens input</span>
      <span class="val" id="h-input">—</span>
    </div>
    <div class="metric">
      <span class="lbl">Tokens output</span>
      <span class="val" id="h-output">—</span>
    </div>
    <div class="metric hi">
      <span class="lbl">Total tokens</span>
      <span class="val" id="h-total">—</span>
    </div>
    <div class="metric">
      <span class="lbl">Tours</span>
      <span class="val" id="h-turns">0</span>
    </div>
    <div class="metric blue">
      <span class="lbl">kWh estimé</span>
      <span class="val" id="h-kwh">—</span>
    </div>
    <div class="metric green">
      <span class="lbl">CO₂ estimé</span>
      <span class="val" id="h-co2">—</span>
    </div>
    <div class="model-row" id="h-model">Modèle : —</div>
  </div>
  <button class="save-btn" id="h-save" disabled>Sauvegarder dans Helios</button>
  <button class="reset-btn" id="h-reset">Réinitialiser</button>
  <div class="status" id="h-status"></div>
</div>
`;

let el = {};
let collapsed = false;

function initOverlay() {
  if (document.getElementById('__helios-root')) return;

  const host = document.createElement('div');
  host.id = '__helios-root';
  const shadow = host.attachShadow({ mode: 'closed' });

  const style = document.createElement('style');
  style.textContent = CSS;
  shadow.appendChild(style);

  const widget = document.createElement('div');
  widget.className = 'widget';
  widget.innerHTML = HTML;
  shadow.appendChild(widget);

  document.body.appendChild(host);

  // Cache elements
  el = {
    platform: widget.querySelector('#h-platform'),
    toggle:   widget.querySelector('#h-toggle'),
    body:     widget.querySelector('#h-body'),
    idle:     widget.querySelector('#h-idle'),
    metrics:  widget.querySelector('#h-metrics'),
    input:    widget.querySelector('#h-input'),
    output:   widget.querySelector('#h-output'),
    total:    widget.querySelector('#h-total'),
    turns:    widget.querySelector('#h-turns'),
    kwh:      widget.querySelector('#h-kwh'),
    co2:      widget.querySelector('#h-co2'),
    model:    widget.querySelector('#h-model'),
    save:     widget.querySelector('#h-save'),
    reset:    widget.querySelector('#h-reset'),
    status:   widget.querySelector('#h-status'),
    header:   widget.querySelector('#h-header'),
  };

  // Collapse / expand
  el.toggle.addEventListener('click', () => {
    collapsed = !collapsed;
    el.body.style.display = collapsed ? 'none' : '';
    el.toggle.textContent = collapsed ? '+' : '−';
  });

  // Save button
  el.save.addEventListener('click', handleSave);

  // Reset button
  el.reset.addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'RESET_SESSION' }).catch(() => {});
    resetDisplay();
    showStatus('Session réinitialisée.', 'ok');
  });

  // Draggable header
  makeDraggable(widget, el.header);

  // Expose update function to content.js (same ISOLATED world)
  window.__heliosUpdateOverlay = updateOverlay;
  console.log('[Helios] Overlay mounted');
}

// ---------------------------------------------------------------------------
// Update overlay with session data
// ---------------------------------------------------------------------------
function updateOverlay(data) {
  if (!el.input) return;

  const total = (data.totalInput ?? 0) + (data.totalOutput ?? 0);

  if (total === 0) {
    el.idle.style.display = '';
    el.metrics.style.display = 'none';
    el.save.disabled = true;
    return;
  }

  el.idle.style.display = 'none';
  el.metrics.style.display = '';
  el.save.disabled = false;

  const kwh = total * kwhPerToken(data.model);
  const co2g = kwh * CO2_STD_G_KWH;

  el.platform.textContent = data.platform ?? '—';
  el.input.textContent    = fmtTokens(data.totalInput ?? 0);
  el.output.textContent   = fmtTokens(data.totalOutput ?? 0);
  el.total.textContent    = fmtTokens(total);
  el.turns.textContent    = String(data.turns ?? 0);
  el.kwh.textContent      = fmtKwh(kwh);
  el.co2.textContent      = fmtCo2(co2g);
  el.model.textContent    = 'Modèle : ' + (data.model ?? '—');
}

function resetDisplay() {
  if (!el.input) return;
  el.idle.style.display = '';
  el.metrics.style.display = 'none';
  el.save.disabled = true;
  el.platform.textContent = '—';
  el.model.textContent = 'Modèle : —';
}

// ---------------------------------------------------------------------------
// Save handler
// ---------------------------------------------------------------------------
async function handleSave() {
  el.save.disabled = true;
  showStatus('Sauvegarde en cours…', '');

  let result;
  try {
    result = await chrome.runtime.sendMessage({ type: 'SAVE_SESSION', data: {} });
  } catch {
    showStatus('Erreur : extension non disponible.', 'err');
    el.save.disabled = false;
    return;
  }

  if (result.ok) {
    showStatus('Session sauvegardée !', 'ok');
    resetDisplay();
  } else if (result.error === 'not_authenticated') {
    showStatus('Connectez-vous sur Helios d\'abord.', 'err');
    el.save.disabled = false;
  } else {
    showStatus('Erreur : ' + result.error, 'err');
    el.save.disabled = false;
  }

  setTimeout(() => showStatus('', ''), 5000);
}

function showStatus(text, cls) {
  if (!el.status) return;
  el.status.textContent = text;
  el.status.className = 'status' + (cls ? ' ' + cls : '');
}

// ---------------------------------------------------------------------------
// Draggable (mouse-based, no pointer capture needed)
// ---------------------------------------------------------------------------
function makeDraggable(widget, handle) {
  let startX, startY, startRight, startBottom;
  let dragging = false;

  handle.addEventListener('mousedown', (e) => {
    if (e.target.classList.contains('toggle-btn')) return;
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    const rect = widget.getBoundingClientRect();
    startRight  = window.innerWidth  - rect.right;
    startBottom = window.innerHeight - rect.bottom;
    e.preventDefault();
  });

  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const dx = startX - e.clientX;
    const dy = startY - e.clientY;
    widget.style.right  = Math.max(0, startRight  + dx) + 'px';
    widget.style.bottom = Math.max(0, startBottom + dy) + 'px';
  });

  document.addEventListener('mouseup', () => { dragging = false; });
}

// Auto-init when loaded as a content script
initOverlay();
