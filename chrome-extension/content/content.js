/**
 * content.js — ISOLATED world, document_start.
 * inject.js est injecté dans MAIN world par le service_worker via
 * chrome.scripting.executeScript (seule méthode qui bypass le CSP des pages).
 */
'use strict';

// Bridge: MAIN world postMessage → service_worker
window.addEventListener('message', (event) => {
  if (event.source !== window) return;
  if (!event.data?.__heliosTracker) return;
  const { __heliosTracker, ...payload } = event.data;
  chrome.runtime.sendMessage({ type: 'TOKEN_USAGE', payload }).catch(() => {});
});

// Bridge: service_worker → overlay.js (même ISOLATED world)
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'UPDATE_OVERLAY') {
    window.__heliosUpdateOverlay?.(message.data);
    sendResponse({ ok: true });
  }
  if (message.type === 'PING') {
    sendResponse({ alive: true });
  }
});
