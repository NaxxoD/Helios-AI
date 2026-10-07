/**
 * inject.js — MAIN world, injecté via chrome.scripting.executeScript.
 */
(function () {
  'use strict';

  const VERSION = 'v21';
  if (window.__heliosInstalled === VERSION) return;
  window.__heliosInstalled = VERSION;

  const PLATFORM = (function () {
    const h = location.hostname;
    if (h.includes('chatgpt.com'))       return 'chatgpt';
    if (h.includes('claude.ai'))         return 'claude';
    if (h.includes('gemini.google.com')) return 'gemini';
    return null;
  })();

  if (!PLATFORM) return;

  const _orig = window.fetch;

  // Debug : inspecte dans la console → window.__heliosPosts / window.__heliosDebug
  window.__heliosPosts  = [];
  window.__heliosDebug  = [];

  window.fetch = async function (...args) {
    const response = await _orig.apply(this, args);
    try {
      const url    = getUrl(args);
      const method = getMethod(args);
      if (method === 'POST') {
        window.__heliosPosts.push({
          url,
          status: response.status,
          ct: response.headers?.get('content-type'),
        });
        const reqBody = getRequestBody(args);
        intercept(url, reqBody, response.clone(), response);
      }
    } catch (_) {}
    return response;
  };

  // ---------------------------------------------------------------------------
  // XHR override — Gemini utilise XHR (pas fetch) pour StreamGenerate
  // ---------------------------------------------------------------------------
  if (PLATFORM === 'gemini') {
    const _xhrOpen = XMLHttpRequest.prototype.open;
    const _xhrSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url) {
      this.__hMethod = (method ?? '').toUpperCase();
      this.__hUrl    = typeof url === 'string' ? url : (url?.toString() ?? '');
      return _xhrOpen.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function (body) {
      const url = this.__hUrl ?? '';
      if (this.__hMethod === 'POST' &&
          (url.includes('StreamGenerate') || url.includes('GenerateContent') || url.includes('generate_content'))) {
        console.warn('[Helios v5] Gemini XHR intercepted | url:', url);
        const reqBody = typeof body === 'string' ? body : null;
        this.addEventListener('load', () => parseGeminiXHR(this.responseText, reqBody));
      }
      return _xhrSend.apply(this, arguments);
    };
  }

  console.warn('[Helios] installed for', PLATFORM);

  function getUrl(args) {
    const a = args?.[0];
    if (!a) return '';
    if (typeof a === 'string') return a;
    return a instanceof URL ? a.href : (a.url ?? '');
  }

  function getMethod(args) {
    const m = args[1]?.method ?? (args[0] instanceof Request ? args[0].method : 'GET');
    return m.toUpperCase();
  }

  function getRequestBody(args) {
    try {
      const body = args[1]?.body ?? (args[0] instanceof Request ? args[0].body : null);
      if (typeof body === 'string') return body;
    } catch (_) {}
    return null;
  }

  // ---------------------------------------------------------------------------
  // Recherche récursive d'un objet usage dans n'importe quelle structure JSON
  // ---------------------------------------------------------------------------
  function findUsage(obj, depth) {
    if (depth > 6 || !obj || typeof obj !== 'object') return null;

    // Patterns connus de token counts
    if (obj.prompt_tokens != null)
      return { in: obj.prompt_tokens, out: obj.completion_tokens ?? 0 };
    if (obj.user_tokens != null)
      return { in: (obj.system_tokens ?? 0) + obj.user_tokens, out: obj.assistant_tokens ?? 0 };
    if (obj.input_tokens != null)
      return { in: obj.input_tokens, out: obj.output_tokens ?? 0 };
    if (obj.promptTokenCount != null)
      return { in: obj.promptTokenCount, out: obj.candidatesTokenCount ?? 0 };

    // Descend dans les clés susceptibles de contenir l'usage
    const priority = ['usage', 'usageMetadata', 'metadata', 'message', 'v', 'data'];
    for (const key of priority) {
      if (obj[key] && typeof obj[key] === 'object') {
        const r = findUsage(obj[key], depth + 1);
        if (r) return r;
      }
    }
    // Balayage général
    for (const key of Object.keys(obj)) {
      if (priority.includes(key)) continue;
      if (obj[key] && typeof obj[key] === 'object') {
        const r = findUsage(obj[key], depth + 1);
        if (r) return r;
      }
    }
    return null;
  }

  function findModel(obj, depth) {
    if (depth > 6 || !obj || typeof obj !== 'object') return null;
    for (const key of ['model', 'model_slug', 'modelSlug', 'modelVersion', 'default_model_slug']) {
      if (typeof obj[key] === 'string' && obj[key].length > 2) return obj[key];
    }
    for (const key of Object.keys(obj)) {
      if (typeof obj[key] === 'object') {
        const r = findModel(obj[key], depth + 1);
        if (r) return r;
      }
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Parser Gemini XHR — réponse multi-chunk texte de StreamGenerate
  // ---------------------------------------------------------------------------
  function parseGeminiXHR(text, reqBody) {
    if (!text) return;

    // Le web gratuit Gemini = gemini-2.0-flash par défaut
    let model = 'gemini-2.0-flash';
    let inTok = 0, outTok = 0;

    // Token counts exacts (présents dans usageMetadata si l'API les expose)
    const promptMatch    = text.match(/promptTokenCount[^0-9]*(\d+)/);
    const candidateMatch = text.match(/candidatesTokenCount[^0-9]*(\d+)/);
    if (promptMatch)    inTok  = parseInt(promptMatch[1],    10);
    if (candidateMatch) outTok = parseInt(candidateMatch[1], 10);

    // Extraction du texte généré — cherche dans TOUTES les lignes [[...]] du stream
    // La chaîne naturelle (avec espaces) = le texte de la réponse ; les IDs n'ont pas d'espaces
    if (outTok === 0) {
      // Prédicat : vrai texte humain (a des espaces, pas un ID/URL/JSON)
      const isNatural = (s) =>
        typeof s === 'string' && s.length > 15 && /\s/.test(s)
        && /[a-zA-Z]{3}/.test(s) && !s.startsWith('http') && !s.startsWith('wrb');

      // Collecte toutes les strings naturelles dans la structure JSON (récursif)
      // On prend ensuite la PLUS LONGUE = la réponse (les labels UI sont courts)
      const collectNatural = (v, acc, d = 0) => {
        if (d > 12 || v == null) return;
        if (typeof v === 'string') {
          if ((v.startsWith('[') || v.startsWith('{')) && v.length > 5) {
            try { collectNatural(JSON.parse(v), acc, d + 1); } catch (_) {}
          } else if (isNatural(v) && v.length < 8000) {
            acc.push(v);
          }
          return;
        }
        if (Array.isArray(v)) { for (const x of v) collectNatural(x, acc, d+1); }
        else if (typeof v === 'object') { for (const x of Object.values(v)) collectNatural(x, acc, d+1); }
      };

      const allNatural = [];
      const allBracketLines = text.replace(/^\)\]\}'\n?/, '').split('\n')
        .filter(l => l.trim().startsWith('[['));
      for (const line of allBracketLines) {
        try { collectNatural(JSON.parse(line), allNatural); } catch (_) {}
      }

      // Priorité : plus longue string ressemblant à une phrase (3+ mots, ponctuation finale)
      const sentences = allNatural.filter(s => s.split(' ').length >= 3 && /[.!?]$/.test(s.trim()));
      const found = sentences.length
        ? sentences.reduce((a, b) => b.length > a.length ? b : a)
        : allNatural.length ? allNatural.reduce((a, b) => b.length > a.length ? b : a) : null;

      window.__heliosGeminiDebug = { found: found?.slice(0, 120), total: allNatural.length, sentences: sentences.length };
      if (found) outTok = Math.max(1, Math.round(found.length / 3.5));
    }
    if (outTok === 0) outTok = 15;

    // Input depuis le f.req de la requête
    if (inTok === 0 && reqBody) {
      try {
        const fRaw  = reqBody.match(/f\.req=([^&]+)/)?.[1];
        const fReq  = fRaw ? decodeURIComponent(fRaw) : '';
        const outer = JSON.parse(fReq);
        // Cherche récursivement la première chaîne lisible non-JSON (le message user)
        const findMsg = (v, d = 0) => {
          if (d > 6 || v == null) return '';
          if (typeof v === 'string' && v.length > 1 && /[a-zA-Z]/.test(v) && !v.startsWith('[')) return v;
          if (Array.isArray(v)) { for (const x of v) { const r = findMsg(x, d + 1); if (r) return r; } }
          return '';
        };
        const userMsg = findMsg(outer);
        inTok = Math.max(1, Math.round(userMsg.length / 3.5));
      } catch (_) { inTok = 5; }
    }

    console.warn('[Helios v5] Gemini parsed — in:', inTok, 'out:', outTok, 'model:', model);
    emit('gemini', model, inTok, outTok);
  }

  // ---------------------------------------------------------------------------
  // Routage
  // ---------------------------------------------------------------------------
  function intercept(url, reqBody, cloned, origResponse) {
    if (PLATFORM === 'chatgpt') {
      const ok = (url.includes('/f/conversation') || url.includes('backend-api/conversation'))
              && !url.includes('conversations?')
              && !url.includes('conversation_id=')
              && !url.includes('/gizmos')
              && !url.includes('/prepare')
              && !url.includes('/title')
              && !url.includes('/gen_title')
              && !url.includes('/init')
              && !url.includes('/feedback');
      const ct = origResponse.headers?.get('content-type') ?? '';
      if (ok && (ct.includes('text/event-stream') || ct.includes('text/plain'))) {
        console.warn('[Helios v5] ChatGPT SSE intercepted | url:', url);
        parseStream(cloned, 'chatgpt', reqBody);
      } else if (ok) {
        console.warn('[Helios v5] ChatGPT POST skipped (not SSE) | ct:', ct, '| url:', url);
      }
    } else if (PLATFORM === 'claude') {
      if (url.includes('completion') || url.includes('append_message'))
        { console.warn('[Helios v5] Claude POST →', url); parseStream(cloned, 'claude', reqBody); }
    } else if (PLATFORM === 'gemini') {
      if (url.includes('GenerateContent') || url.includes('StreamGenerate') || url.includes('generate_content'))
        { console.warn('[Helios v5] Gemini POST →', url); parseStream(cloned, 'gemini', reqBody); }
    }
  }

  // ---------------------------------------------------------------------------
  // Parser générique — lit chaque ligne JSON et cherche usage + model
  // ---------------------------------------------------------------------------
  async function parseStream(response, platform, reqBody) {
    if (!response.body) return;
    const reader = response.body.getReader();
    const dec    = new TextDecoder();
    let buf      = '';
    let inTok = 0, outTok = 0;
    let allLines = [];
    let currentEvent = null;
    let textOut = '';
    let maxSnapshot = '';  // plus longue chaîne naturelle vue dans n'importe quel chunk
    let model    = null;

    // Extraction modèle + estimation input depuis le corps de la requête
    let reqBodyJson = null;
    if (reqBody) {
      try { reqBodyJson = JSON.parse(reqBody); } catch (_) {}
    }
    // "auto" = sélection automatique côté ChatGPT, pas un vrai modèle
    if (reqBodyJson?.model && reqBodyJson.model !== 'auto') model = reqBodyJson.model;

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() ?? '';

        for (const line of lines) {
          // Claude : lignes "event: ..."
          if (line.startsWith('event: ')) { currentEvent = line.slice(7).trim(); continue; }

          const raw = line.startsWith('data: ') ? line.slice(6).trim() : line.trim();
          if (!raw || raw === '[DONE]') continue;

          allLines.push(raw.slice(0, 200));

          try {
            const parsed = JSON.parse(raw);

            // Cherche le modèle — toujours tenté pour écraser "auto" ou null
            const _m = findModel(parsed, 0);
            if (_m && _m !== 'auto') model = _m;

            // ChatGPT : accumule le texte généré pour estimation (multi-format)
            if (platform === 'chatgpt') {
              // 1. Format snapshot : message.content.parts[0] = réponse complète jusqu'ici
              //    On cible précisément ce champ pour éviter de compter les résultats
              //    de recherche web ou le contexte de conversation inclus dans le chunk
              const parts = parsed.message?.content?.parts;
              if (Array.isArray(parts)) {
                for (const part of parts) {
                  if (typeof part === 'string' && part.length > maxSnapshot.length) {
                    maxSnapshot = part;
                  }
                }
              }

              // 2. Delta formats explicites (append/add)
              if (typeof parsed.o === 'string' && typeof parsed.v === 'string') {
                const p = typeof parsed.p === 'string' ? parsed.p : '';
                const isText = !p || p.includes('content') || p.includes('parts') || p.includes('text');
                if (isText && (parsed.o === 'append' || parsed.o === 'add')) {
                  textOut += parsed.v;
                }
              }
              // 3. Format standard OpenAI API
              const delta = parsed.choices?.[0]?.delta?.content;
              if (typeof delta === 'string') textOut += delta;
            }

            // Sur Claude : input exact depuis message_start, output estimé depuis les deltas
            if (platform === 'claude') {
              const evType = parsed.type ?? currentEvent ?? '';
              if (evType === 'message_start') {
                const msg = parsed.message ?? {};
                if (!model && msg.model) model = msg.model;
                const usage = msg.usage ?? parsed.usage ?? {};
                if (usage.input_tokens) inTok = usage.input_tokens;
              } else if (evType === 'message_delta') {
                const usage = parsed.usage ?? {};
                if (usage.output_tokens) outTok = usage.output_tokens;
              } else if (evType === 'content_block_delta') {
                const txt = parsed.delta?.text ?? '';
                if (txt) textOut += txt;
              }
            } else {
              const u = findUsage(parsed, 0);
              if (u && (u.in > 0 || u.out > 0)) { inTok = u.in; outTok = u.out; }
            }
          } catch (_) {}
        }
      }
    } finally {
      try { reader.releaseLock(); } catch (_) {}
    }

    // Debug
    window.__heliosDebug.push({
      platform, total: allLines.length,
      first: allLines.slice(0, 3),
      last:  allLines.slice(-5),
      textOut: textOut.slice(0, 100),
    });

    console.warn('[Helios v5] stream end | lines:', allLines.length, '| textOut:', textOut.length, 'chars');

    // Claude : output estimé depuis le texte si message_delta n'a pas fourni la valeur
    if (platform === 'claude' && outTok === 0 && textOut.length > 0) {
      outTok = Math.max(1, Math.round(textOut.length / 3.5));
    }
    // Claude : input estimé depuis le corps de la requête si message_start n'a rien fourni
    if (platform === 'claude' && inTok === 0 && reqBodyJson) {
      const msgs = reqBodyJson.messages ?? reqBodyJson.prompt ?? reqBodyJson;
      inTok = Math.max(1, Math.round(JSON.stringify(msgs).length / 3.5));
    }

    // Estimation ChatGPT — toujours prioritaire sur findUsage (stream web non fiable)
    // bestOut = meilleur des deux stratégies : delta accumulé vs snapshot le plus long
    if (platform === 'chatgpt') {
      const bestOut = textOut.length > maxSnapshot.length ? textOut : maxSnapshot;
      if (bestOut.length > 0) {
        outTok = Math.max(1, Math.round(bestOut.length / 3.5));
        if (reqBodyJson) {
          try {
            const msgs = reqBodyJson.messages ?? [];
            const plainText = msgs.map(m => {
              const parts = m?.content?.parts;
              if (Array.isArray(parts)) return parts.filter(p => typeof p === 'string').join(' ');
              return typeof m?.content === 'string' ? m.content : '';
            }).join(' ');
            inTok = Math.max(1, Math.round(plainText.length / 3.5));
          } catch (_) {
            inTok = Math.max(1, Math.round(bestOut.length / 3.5));
          }
        } else if (reqBody) {
          inTok = Math.max(1, Math.round(reqBody.length / 10 / 3.5));
        }
        console.warn('[Helios v5] ChatGPT estimation — in:', inTok, 'out:', outTok,
          '| delta:', textOut.length, 'snap:', maxSnapshot.length, 'chars');
      }
    }

    if (inTok > 0 || outTok > 0) {
      console.warn('[Helios v5] emit — in:', inTok, 'out:', outTok, 'model:', model);
      emit(platform, model, inTok, outTok);
    } else {
      console.warn('[Helios v5] no usage found — inspect window.__heliosDebug');
    }
  }

  function emit(platform, model, input, output) {
    window.postMessage({
      __heliosTracker: true,
      platform, model,
      input_tokens: input, output_tokens: output,
      total_tokens: input + output,
    }, '*');
  }

})();
