/* =========================================================================
   useLandingEffects — porte TOUS les effets de la maquette Helios Landing.html
   (reveal au scroll qui rejoue, barre de progression, count-up, chat auto-play,
    halo de curseur + parallaxe + tilt 3D de la carte, spotlight des cartes,
    boutons magnétiques, canvas hero « moteur de routing »).

   Tout est guardé : neutralisé sous prefers-reduced-motion et pointeur grossier.
   À appeler dans onMounted (DOM présent). Renvoie une fonction de nettoyage.
   ========================================================================= */
export default function useLandingEffects() {
  const reduce      = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const finePointer = window.matchMedia('(pointer:fine)').matches

  const cleanups = []
  const timers   = []
  const observers = []
  const add = (target, ev, fn, opts) => {
    target.addEventListener(ev, fn, opts)
    cleanups.push(() => target.removeEventListener(ev, fn, opts))
  }
  const later = (fn, ms) => { const t = setTimeout(fn, ms); timers.push(t); return t }

  /* ---- 1. reveal au scroll : REJOUE à chaque passage (descente comme remontée) ---- */
  ;(function () {
    const els = Array.from(document.querySelectorAll('.lp-reveal'))
    if (!els.length) return
    if (reduce) { els.forEach(e => e.classList.remove('lp-reveal--pre')); return }
    els.forEach(el => el.classList.add('lp-reveal--pre'))
    let ticking = false
    const update = () => {
      ticking = false
      const vh = window.innerHeight || document.documentElement.clientHeight
      for (const el of els) {
        const r = el.getBoundingClientRect()
        const inBand = r.top < vh * 0.86 && r.bottom > vh * 0.14
        el.classList.toggle('lp-reveal--pre', !inBand)   // sorti de l'écran → réinitialisé
      }
    }
    const onScroll = () => { if (!ticking) { ticking = true; requestAnimationFrame(update) } }
    add(window, 'scroll', onScroll, { passive: true, capture: true })
    add(window, 'resize', onScroll, { passive: true })
    requestAnimationFrame(update); later(update, 350)
    // filet de sécurité : ne jamais laisser tout caché
    later(() => {
      if (document.querySelectorAll('.lp-reveal.lp-reveal--pre').length === els.length)
        els.forEach(e => e.classList.remove('lp-reveal--pre'))
    }, 2600)
  })()

  /* ---- 2. barre de progression du scroll ---- */
  ;(function () {
    const bar = document.querySelector('.lp-scroll-progress')
    if (!bar || reduce) return
    let ticking = false
    const upd = () => {
      const h = document.documentElement
      const max = h.scrollHeight - h.clientHeight
      bar.style.width = (max > 0 ? (h.scrollTop || document.body.scrollTop) / max * 100 : 0) + '%'
      ticking = false
    }
    add(window, 'scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(upd) } }, { passive: true })
    upd()
  })()

  /* ---- 3. count-up des métriques (anime tout .lp-mval[data-count] > 0) ---- */
  ;(function () {
    const cells = Array.from(document.querySelectorAll('.lp-mval[data-count]'))
    if (!cells.length) return
    const run = (el) => {
      const target = parseFloat(el.getAttribute('data-count')) || 0
      if (target <= 0 || reduce) return
      const dur = 1100, t0 = performance.now()
      const gen = (el.__gen = (el.__gen || 0) + 1)
      const tick = (now) => {
        if (el.__gen !== gen) return                      // un run plus récent a pris la main
        const p = Math.min(1, (now - t0) / dur)
        const e = 1 - Math.pow(1 - p, 3)
        el.firstChild.nodeValue = String(Math.round(target * e))
        if (p < 1) requestAnimationFrame(tick)
      }
      el.firstChild.nodeValue = '0'; requestAnimationFrame(tick)
    }
    const io = new IntersectionObserver((es) => {
      es.forEach(e => {
        const t = parseFloat(e.target.getAttribute('data-count')) || 0
        if (t <= 0) return
        if (e.isIntersecting) run(e.target)
        else { e.target.__gen = (e.target.__gen || 0) + 1; e.target.firstChild.nodeValue = '0' }
      })
    }, { threshold: .5 })
    cells.forEach(c => io.observe(c)); observers.push(io)
  })()

  /* ---- 4. chat mock auto-play (Bascule IA) ---- */
  ;(function () {
    const chat = document.querySelector('.lp-chat')
    if (!chat) return
    const steps = Array.from(chat.querySelectorAll('.lp-chat__row, .lp-switch-note'))
    if (reduce) { steps.forEach(s => s.classList.add('on')); return }
    const show = el => el.classList.add('on')
    const hide = el => el.classList.remove('on')
    steps.forEach(hide)
    const aiBubbles = Array.from(chat.querySelectorAll('.lp-bubble--ai'))
    aiBubbles.forEach(b => { b.dataset.txt = b.innerHTML })
    const TYP = '<span class="lp-typing-dots"><i></i><i></i><i></i></span>'
    let chatTimers = []
    const clearAll = () => { chatTimers.forEach(clearTimeout); chatTimers = [] }
    const at = (ms, fn) => chatTimers.push(setTimeout(fn, ms))
    let playing = false
    function play() {
      clearAll(); playing = true
      steps.forEach(hide)
      aiBubbles.forEach(b => b.innerHTML = b.dataset.txt)
      let t = 400
      steps.forEach(s => {
        const ai = s.querySelector ? s.querySelector('.lp-bubble--ai') : null
        if (ai) {
          at(t, () => { ai.innerHTML = TYP; show(s) })
          at(t + 1000, () => { ai.innerHTML = ai.dataset.txt })
          t += 1650
        } else {
          at(t, () => show(s)); t += 950
        }
      })
      at(t + 2800, play)
    }
    const io = new IntersectionObserver((es) => {
      es.forEach(e => { if (e.isIntersecting) play(); else { clearAll(); playing = false } })
    }, { threshold: .35 })
    io.observe(chat); observers.push(io)
    cleanups.push(clearAll)
    later(() => { if (!playing) steps.forEach(show) }, 4000)
  })()

  /* À partir d'ici : eye-candy au pointeur uniquement (souris fine, pas de reduced-motion) */
  if (reduce || !finePointer) {
    return () => { cleanups.forEach(fn => fn()); timers.forEach(clearTimeout); observers.forEach(o => o.disconnect()) }
  }

  document.querySelector('.lp')?.classList.add('lp--has-pointer')

  /* ---- 5. profondeur au pointeur : halo + parallaxe du fond + tilt 3D de la démo ---- */
  ;(function () {
    let px = innerWidth / 2, py = innerHeight / 2, rafPending = false
    const glow  = document.querySelector('.lp-cursor-glow')
    const demo  = document.querySelector('.lp-demo')
    const blobG = document.querySelector('.lp-bg__blob--g')
    const blobP = document.querySelector('.lp-bg__blob--p')
    const sun   = document.querySelector('.lp-bg__sun')
    let demoHover = false
    function frame() {
      rafPending = false
      const nx = px / innerWidth - 0.5, ny = py / innerHeight - 0.5
      if (glow)  glow.style.transform  = `translate(${px}px,${py}px)`
      if (blobG) blobG.style.transform = `translate(${nx * -46}px,${ny * -30}px)`
      if (blobP) blobP.style.transform = `translate(${nx * 40}px,${ny * 26}px)`
      if (sun)   sun.style.transform   = `translate(${nx * 22}px,${ny * 16}px)`
      if (demo && demoHover) demo.style.transform = `rotateY(${nx * 9}deg) rotateX(${ny * -9}deg) translateZ(22px)`
    }
    add(window, 'pointermove', (e) => {
      px = e.clientX; py = e.clientY
      if (!rafPending) { rafPending = true; requestAnimationFrame(frame) }
    }, { passive: true })
    if (demo) {
      demo.style.transition = 'transform .25s cubic-bezier(.2,.8,.2,1)'
      add(demo, 'pointerenter', () => { demoHover = true; demo.style.transition = 'transform .08s linear' })
      add(demo, 'pointerleave', () => {
        demoHover = false
        demo.style.transition = 'transform .5s cubic-bezier(.2,.8,.2,1)'
        demo.style.transform = 'rotateY(0) rotateX(0) translateZ(0)'
      })
    }
  })()

  /* ---- 6. spotlight curseur dans les cartes ---- */
  document.querySelectorAll('.lp-card').forEach(card => {
    add(card, 'pointermove', (e) => {
      const r = card.getBoundingClientRect()
      card.style.setProperty('--lp-mx', (e.clientX - r.left) + 'px')
      card.style.setProperty('--lp-my', (e.clientY - r.top) + 'px')
    })
  })

  /* ---- 7. boutons magnétiques ---- */
  document.querySelectorAll('.lp-magnetic').forEach(btn => {
    const R = 70
    add(btn, 'pointermove', (e) => {
      const r = btn.getBoundingClientRect()
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2
      const dx = e.clientX - cx, dy = e.clientY - cy, dist = Math.hypot(dx, dy)
      const f = Math.max(0, 1 - dist / (Math.max(r.width, r.height) / 2 + R))
      btn.style.transform = `translate(${dx * f * 0.4}px,${dy * f * 0.4 - 2}px)`
    })
    add(btn, 'pointerleave', () => {
      btn.style.transition = 'transform .4s cubic-bezier(.2,.8,.2,1)'
      btn.style.transform = ''
      later(() => btn.style.transition = '', 400)
    })
    add(btn, 'pointerenter', () => { btn.style.transition = 'transform .08s linear' })
  })

  /* ---- 8. canvas hero : moteur de routing (signature) ---- */
  ;(function () {
    const cv = document.getElementById('lp-hero-canvas')
    if (!cv) return
    const hero = cv.closest('.lp-hero')
    if (!hero) return
    const ctx = cv.getContext('2d')
    let w = 0, h = 0, dpr = Math.min(2, window.devicePixelRatio || 1), raf = 0, last = 0, emitT = 0
    let parts = [], packets = [], nodes = [], core = null, src = null
    const COL = ['52,216,160', '168,139,242', '232,132,60']   // vert · violet · orange

    function layout() {
      const r = hero.getBoundingClientRect(); w = r.width; h = r.height
      cv.width = w * dpr; cv.height = h * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      src  = { x: w * 0.05, y: h * 0.66 }
      core = { x: w * 0.60, y: h * 0.23 }
      nodes = [
        { x: w * 0.93,  y: h * 0.20, c: COL[0], pulse: 0 },
        { x: w * 0.965, y: h * 0.46, c: COL[1], pulse: 0 },
        { x: w * 0.91,  y: h * 0.72, c: COL[2], pulse: 0 }
      ]
      const n = Math.min(38, Math.round(w / 44)); parts = []
      for (let i = 0; i < n; i++) parts.push({
        x: Math.random() * w, y: Math.random() * h,
        vx: (Math.random() - .5) * .16, vy: (Math.random() - .5) * .16,
        r: Math.random() * 1.5 + 0.5, o: Math.random() * .4 + .22
      })
    }
    function emit() {
      const tgt = nodes[(Math.random() * nodes.length) | 0]
      packets.push({
        t: 0, dur: 2400 + Math.random() * 1100, leg: 0, node: tgt, trail: [],
        a: { x: src.x, y: src.y },
        c1: { x: (src.x + core.x) / 2, y: src.y - (src.y - core.y) * 0.65 - 30 },
        b: { x: core.x, y: core.y },
        c2: { x: (core.x + tgt.x) / 2 + 20, y: (core.y + tgt.y) / 2 - (Math.random() * 60 - 10) },
        d: { x: tgt.x, y: tgt.y }
      })
    }
    const bz = (p0, p1, p2, t) => { const u = 1 - t; return { x: u * u * p0.x + 2 * u * t * p1.x + t * t * p2.x, y: u * u * p0.y + 2 * u * t * p1.y + t * t * p2.y } }

    function frame(now) {
      const dt = Math.min(50, now - (last || now)); last = now
      ctx.clearRect(0, 0, w, h)
      for (const p of parts) { p.x += p.vx; p.y += p.vy; if (p.x < 0 || p.x > w) p.vx *= -1; if (p.y < 0 || p.y > h) p.vy *= -1 }
      for (let i = 0; i < parts.length; i++) {
        const a = parts[i]
        for (let j = i + 1; j < parts.length; j++) {
          const b = parts[j], dx = a.x - b.x, dy = a.y - b.y, d = dx * dx + dy * dy
          if (d < 12500) {
            const al = (1 - d / 12500) * 0.12
            ctx.strokeStyle = 'rgba(52,216,160,' + al + ')'; ctx.lineWidth = 1
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke()
          }
        }
      }
      for (const p of parts) { ctx.fillStyle = 'rgba(110,230,180,' + p.o + ')'; ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.283); ctx.fill() }
      const sp = 0.5 + 0.5 * Math.sin(now / 620)
      ctx.strokeStyle = 'rgba(231,239,234,' + (0.10 + 0.12 * sp) + ')'; ctx.lineWidth = 1
      ctx.beginPath(); ctx.arc(src.x, src.y, 8 + sp * 5, 0, 6.283); ctx.stroke()
      ctx.fillStyle = 'rgba(231,239,234,' + (0.45 + 0.3 * sp) + ')'
      ctx.beginPath(); ctx.arc(src.x, src.y, 3, 0, 6.283); ctx.fill()
      const cp = 0.5 + 0.5 * Math.sin(now / 420)
      const cg = ctx.createRadialGradient(core.x, core.y, 0, core.x, core.y, 26 + cp * 8)
      cg.addColorStop(0, 'rgba(52,216,160,' + (0.16 + cp * 0.12) + ')'); cg.addColorStop(1, 'rgba(52,216,160,0)')
      ctx.fillStyle = cg; ctx.beginPath(); ctx.arc(core.x, core.y, 26 + cp * 8, 0, 6.283); ctx.fill()
      ctx.strokeStyle = 'rgba(52,216,160,' + (0.30 + cp * 0.25) + ')'; ctx.lineWidth = 1.4
      ctx.beginPath(); ctx.arc(core.x, core.y, 11 + cp * 3, 0, 6.283); ctx.stroke()
      emitT += dt; if (emitT > 1300) { emitT = 0; emit() }
      for (let i = packets.length - 1; i >= 0; i--) {
        const pk = packets[i]; pk.t += dt / pk.dur
        if (pk.t >= 1) { pk.node.pulse = 1; packets.splice(i, 1); continue }
        const half = pk.t < 0.5, lt = half ? pk.t / 0.5 : (pk.t - 0.5) / 0.5
        const pos = half ? bz(pk.a, pk.c1, pk.b, lt) : bz(pk.b, pk.c2, pk.d, lt)
        const col = half ? '231,239,234' : pk.node.c
        pk.trail.push({ x: pos.x, y: pos.y, c: col }); if (pk.trail.length > 20) pk.trail.shift()
        for (let k = 0; k < pk.trail.length; k++) {
          const tp = pk.trail[k], f = k / pk.trail.length
          ctx.fillStyle = 'rgba(' + tp.c + ',' + (f * 0.5) + ')'
          ctx.beginPath(); ctx.arc(tp.x, tp.y, 1.8 * f + 0.5, 0, 6.283); ctx.fill()
        }
        const g = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, 9)
        g.addColorStop(0, 'rgba(' + col + ',0.85)'); g.addColorStop(1, 'rgba(' + col + ',0)')
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(pos.x, pos.y, 9, 0, 6.283); ctx.fill()
        ctx.fillStyle = 'rgba(' + col + ',1)'; ctx.beginPath(); ctx.arc(pos.x, pos.y, 2.3, 0, 6.283); ctx.fill()
      }
      for (const nd of nodes) {
        nd.pulse *= 0.93; const baseR = 3.6, ring = baseR + 5 + nd.pulse * 9
        const g = ctx.createRadialGradient(nd.x, nd.y, 0, nd.x, nd.y, ring + 8)
        g.addColorStop(0, 'rgba(' + nd.c + ',' + (0.18 + nd.pulse * 0.55) + ')'); g.addColorStop(1, 'rgba(' + nd.c + ',0)')
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(nd.x, nd.y, ring + 8, 0, 6.283); ctx.fill()
        ctx.strokeStyle = 'rgba(' + nd.c + ',' + (0.28 + nd.pulse * 0.5) + ')'; ctx.lineWidth = 1.2
        ctx.beginPath(); ctx.arc(nd.x, nd.y, ring, 0, 6.283); ctx.stroke()
        ctx.fillStyle = 'rgba(' + nd.c + ',0.95)'; ctx.beginPath(); ctx.arc(nd.x, nd.y, baseR, 0, 6.283); ctx.fill()
      }
      raf = requestAnimationFrame(frame)
    }
    function start() { if (!raf) { last = 0; raf = requestAnimationFrame(frame) } }
    function stop()  { cancelAnimationFrame(raf); raf = 0 }
    layout(); emit(); start()
    add(window, 'resize', layout)
    const io = new IntersectionObserver((es) => { es.forEach(e => { e.isIntersecting ? start() : stop() }) }, { threshold: 0 })
    io.observe(hero); observers.push(io)
    cleanups.push(stop)
  })()

  return () => { cleanups.forEach(fn => fn()); timers.forEach(clearTimeout); observers.forEach(o => o.disconnect()) }
}
