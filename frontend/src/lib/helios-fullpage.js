/* =========================================================================
   helios-fullpage.js — navigation "fullpage" (une section = un écran)
   Sans dépendance. Compatible React / Vue / Svelte / vanilla.

   UTILISATION
   1) Enveloppe tes sections dans un conteneur :  <div id="fp"> ...sections... </div>
   2) Donne la classe "panel" à CHAQUE section directe :  <section class="panel"> ...
   3) Importe le CSS  helios-fullpage.css
   4) Appelle initHeliosFullpage() une fois le DOM monté.
      - Vanilla :  initHeliosFullpage();
      - React    :  useEffect(() => initHeliosFullpage(), []);   // le retour nettoie
      - Vue      :  onMounted(() => { const stop = initHeliosFullpage(); onUnmounted(stop); });

   Libellé des points de repère : ajoute  data-fp-label="Le constat"  sur chaque .panel
   (sinon on utilise l'id de la section, sinon rien).

   Renvoie une fonction de NETTOYAGE (retire les écouteurs + la classe fp-on).
   ========================================================================= */
function initHeliosFullpage(options) {
  options = options || {};
  const fp = document.querySelector(options.container || '#fp');
  if (!fp) { console.warn('[helios-fullpage] conteneur "#fp" introuvable — rien à faire.'); return function(){}; }

  const panels = Array.prototype.slice.call(fp.querySelectorAll(options.panel || '.panel'));
  if (panels.length < 2) { console.warn('[helios-fullpage] moins de 2 .panel trouvés.'); return function(){}; }

  const nav = document.querySelector(options.nav || 'header.nav, nav.nav, [data-nav]');
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // --- Fallback accessibilité : pas d'effet, scroll normal, tout visible ---
  if (reduce) {
    panels.forEach(function (p) { p.classList.add('active'); });
    return function(){};
  }

  let index = 0, animating = false, timer = null;

  // --- Points de repère (créés s'ils n'existent pas déjà) ---
  let dotsWrap = document.querySelector('.fp-dots');
  if (!dotsWrap) {
    dotsWrap = document.createElement('div');
    dotsWrap.className = 'fp-dots';
    document.body.appendChild(dotsWrap);
  }
  dotsWrap.innerHTML = '';
  const dots = panels.map(function (p, i) {
    const label = p.getAttribute('data-fp-label') || p.id || '';
    const b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('aria-label', label || ('Section ' + (i + 1)));
    b.innerHTML = '<span class="lbl"></span><span class="d"></span>';
    b.querySelector('.lbl').textContent = label;
    b.addEventListener('click', function () { go(i); });
    dotsWrap.appendChild(b);
    return b;
  });

  function measureTall() {
    panels.forEach(function (p) { p.classList.toggle('tall', p.scrollHeight > p.clientHeight + 4); });
  }
  function setActive() {
    panels.forEach(function (p, i) { p.classList.toggle('active', i === index); });
    dots.forEach(function (d, i) { d.classList.toggle('on', i === index); });
    if (nav) nav.classList.toggle('scrolled', index > 0);
  }
  function go(i) {
    i = Math.max(0, Math.min(panels.length - 1, i));
    if (i === index || animating) return;
    animating = true;
    index = i;
    fp.style.transform = 'translateY(' + (-i * 100) + 'vh)';
    panels[i].scrollTop = 0;
    setActive();
    clearTimeout(timer);
    timer = setTimeout(function () { animating = false; }, 940);
  }

  // --- Active le mode plein écran ---
  document.documentElement.classList.add('fp-on');
  document.body.classList.add('fp-on');
  requestAnimationFrame(function () { measureTall(); setActive(); });

  // --- Molette : laisse défiler une section trop haute, puis bascule ---
  let wheelLock = false;
  function onWheel(e) {
    const panel = panels[index];
    const dir = e.deltaY > 0 ? 1 : -1;
    const atTop = panel.scrollTop <= 0;
    const atBottom = panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 1;
    const canInternal = (dir > 0 && !atBottom) || (dir < 0 && !atTop);
    if (panel.classList.contains('tall') && canInternal) return; // scroll interne
    e.preventDefault();
    if (animating || Math.abs(e.deltaY) < 8 || wheelLock) return;
    wheelLock = true; setTimeout(function () { wheelLock = false; }, 140);
    go(index + dir);
  }

  // --- Clavier ---
  function onKey(e) {
    if (e.target && e.target.matches && e.target.matches('input, textarea, [contenteditable]')) return;
    if (['ArrowDown', 'PageDown', ' '].indexOf(e.key) > -1) { e.preventDefault(); go(index + 1); }
    else if (['ArrowUp', 'PageUp'].indexOf(e.key) > -1) { e.preventDefault(); go(index - 1); }
    else if (e.key === 'Home') { e.preventDefault(); go(0); }
    else if (e.key === 'End') { e.preventDefault(); go(panels.length - 1); }
  }

  // --- Tactile ---
  let ty = null;
  function onTouchStart(e) { ty = e.touches[0].clientY; }
  function onTouchMove(e) {
    if (ty === null) return;
    const panel = panels[index];
    const dy = ty - e.touches[0].clientY, dir = dy > 0 ? 1 : -1;
    const atTop = panel.scrollTop <= 0, atBottom = panel.scrollTop + panel.clientHeight >= panel.scrollHeight - 1;
    const canInternal = (dir > 0 && !atBottom) || (dir < 0 && !atTop);
    if (panel.classList.contains('tall') && canInternal) return;
    if (Math.abs(dy) > 46) { e.preventDefault(); if (!animating) go(index + dir); ty = null; }
  }
  function onTouchEnd() { ty = null; }

  // --- Liens d'ancre internes (#id) → saut vers le panel correspondant ---
  const idMap = {};
  panels.forEach(function (p, i) { if (p.id) idMap['#' + p.id] = i; });
  function onAnchorClick(e) {
    const a = e.target.closest && e.target.closest('a[href^="#"]');
    if (!a) return;
    const t = a.getAttribute('href');
    if (idMap[t] != null) { e.preventDefault(); go(idMap[t]); }
  }

  function onResize() { measureTall(); fp.style.transform = 'translateY(' + (-index * 100) + 'vh)'; }

  window.addEventListener('wheel', onWheel, { passive: false });
  window.addEventListener('keydown', onKey);
  window.addEventListener('touchstart', onTouchStart, { passive: true });
  window.addEventListener('touchmove', onTouchMove, { passive: false });
  window.addEventListener('touchend', onTouchEnd);
  document.addEventListener('click', onAnchorClick);
  window.addEventListener('resize', onResize);

  // --- Fonction de nettoyage (à appeler au démontage du composant) ---
  return function destroy() {
    window.removeEventListener('wheel', onWheel);
    window.removeEventListener('keydown', onKey);
    window.removeEventListener('touchstart', onTouchStart);
    window.removeEventListener('touchmove', onTouchMove);
    window.removeEventListener('touchend', onTouchEnd);
    document.removeEventListener('click', onAnchorClick);
    window.removeEventListener('resize', onResize);
    clearTimeout(timer);
    document.documentElement.classList.remove('fp-on');
    document.body.classList.remove('fp-on');
    fp.style.transform = '';
    if (dotsWrap && dotsWrap.parentNode) dotsWrap.parentNode.removeChild(dotsWrap);
  };
}

// Auto-init si l'attribut data-helios-fullpage-auto est présent sur #fp
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', function () {
    if (document.querySelector('#fp[data-helios-fullpage-auto]')) initHeliosFullpage();
  });
}

// Export ES module optionnel
if (typeof module !== 'undefined' && module.exports) module.exports = initHeliosFullpage;
export default initHeliosFullpage;
