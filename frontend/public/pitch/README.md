# Handoff — Présentation Helios AI (déjà codée)

`Helios Deck.html` est une **présentation web complète et autonome** : HTML + CSS + JS, sans build.
Elle s'appuie sur un composant web `deck-stage` (scaling auto 16:9, navigation clavier, miniatures,
impression PDF) et `image-slot` (emplacements photo). C'est la **source de vérité du rendu** —
ce que tu vois à l'écran est exactement ce qui sera affiché.

> Objectif de ce handoff : que Claude Code l'**héberge** ou l'**intègre** dans le projet, sans casser
> le rendu. Inutile de tout réécrire — le plus simple est de la servir telle quelle.

## Contenu du dossier
- `Helios Deck.html` — la présentation (8 slides).
- `deck-stage.js` — composant web du diaporama (scaling, nav, miniatures, **impression PDF intégrée**).
- `image-slot.js` — emplacement image que l'utilisateur remplit (capture de l'app, slide démo).
- `README.md` — ce document.

## Option A — La servir telle quelle (le plus rapide)
Les 3 fichiers doivent rester **dans le même dossier** (les `<script src>` sont relatifs).
- En local : ouvrir `Helios Deck.html`, ou `npx serve .` puis ouvrir l'URL.
- En prod : déposer le dossier dans `public/` (Next/Vite) ou sur n'importe quel hébergement statique
  (Netlify, Vercel, GitHub Pages). Aucune dépendance npm.
- Navigation : ←/→, Espace, clic sur les miniatures, `R` pour revenir au début.
- **Export PDF** : déjà géré — `Cmd/Ctrl + P` → Enregistrer en PDF (une page par slide).

## Option B — L'intégrer dans le projet existant
- Place les 3 fichiers (ex. dans `public/deck/`) et lie la page, ou affiche-la dans une route dédiée
  (`/pitch`) via une `<iframe src="/deck/Helios Deck.html">` — c'est l'intégration la plus sûre,
  car `deck-stage` gère lui-même son scaling plein écran.
- Les polices viennent de Google Fonts (CDN, déjà dans le `<head>`). Pour un usage hors-ligne,
  héberge les fonts en local et remplace le `<link>`.

## Option C — Porter dans ta stack (React/Vue) — seulement si nécessaire
Le markup des slides est du HTML statique simple (un `<section><div class="slide">…`).
- Tu peux copier chaque slide dans un composant, **en conservant le `<style>`** (design tokens) à
  l'identique. Garde `deck-stage` comme wrapper (c'est un custom element standard, utilisable en JSX
  via `<deck-stage>`), ou remplace-le par reveal.js **en réutilisant tel quel le CSS des slides**.
- ⚠️ Ne reconstruis pas le design « de tête » : reprends les classes et variables du `<style>`
  (couleurs, polices, espacements) pour garder le rendu exact.

## Design system (déjà dans le `<style>` du fichier)
- Couleurs : fond `#080C0A` · vert `#34D8A0` · orange `#E8843C` · violet `#A88BF2` · texte `#E7EFEA`.
- Polices : **Chakra Petch** (titres) · **Archivo** (corps) · **JetBrains Mono** (labels/chiffres).
- Logo : SVG inline « Aperture » (dégradé vert→orange), défini une fois en haut du `<body>`.
- Slides : design 1920×1080, mises à l'échelle automatiquement par `deck-stage`.

## Les 8 slides
1. Couverture · 2. Le problème (escalier causal) · 3. La solution (pipeline Vous → Helios → IA) ·
4. Démo · 5. Pourquoi Helios (tableau de capacités) · 6. Démarche &amp; limites ·
7. Vision (timeline) · 8. Clôture.

## À personnaliser (zones laissées en placeholder)
- **Slide 4 — Démo** : déposer une capture/GIF de l'app dans l'`<image-slot id="demo-shot">`.
- **Slide 6 — Démarche** : remplacer `[fonctionnalité X]`, ajuster les chips de stack.
- **Slide 1 — Couverture** : noms de l'équipe (ligne du bas).
- **Slide 8 — Clôture** : URL du repo si besoin.

> L'image déposée dans l'`image-slot` persiste via un fichier `.image-slots.state.json` à côté
> du HTML (le composant le gère). En hébergement statique simple sans ce mécanisme, remplace
> l'`<image-slot>` par un simple `<img src="…">` une fois le visuel choisi.
