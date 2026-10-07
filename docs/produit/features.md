# Helios AI — Features envisagées

> Consolidation post-soutenance HETIC (17/20) — 2026-06-04  
> Sources : R&D_AD.md, business_model_wallet.md, helios_routing_rd.md + retours instance co-auteur

---
## Structure en 6 blocs :

  1. Optimiseur — E2 (restructuration, immédiat), Note qualité, E3 chips, Lexique par user
  2. Routing — Calibrage effort, Ollama stage 2
  3. Expérience non-tech — Pilote auto, Presets
  4. Valeur tangible — Historique enrichi, Export
  5. Reporté — dépend de données réelles (dashboard, cache, explication routing)
  6. Reporté — phase business (wallet, CGU, clés serveur)

reframer l'optimiseur en 3 étages empilés :

  ┌───────┬────────────────────────────────┬──────────────────────────────────────────┐
  │ Étage │              Nom               │                  État                    │
  ├───────┼────────────────────────────────┼──────────────────────────────────────────┤
  │ E1    │ Soustraction (nettoyage bruit) │ ✅ en prod                               │
  ├───────┼────────────────────────────────┼──────────────────────────────────────────┤
  │ E2a   │ Scaffold déterministe          │ ✅ mergé main 2026-06-08                 │
  ├───────┼────────────────────────────────┼──────────────────────────────────────────┤
  │ E2b   │ Couche sémantique Qwen         │ ✅ system prompt v6 intégré · audit co-auteur traité (2026-06-09) │
  ├───────┼────────────────────────────────┼──────────────────────────────────────────┤
  │ E3    │ Complétion guidée par chips    │ ⏳ le cœur ambitieux — prochain sprint   │
  └───────┴────────────────────────────────┴──────────────────────────────────────────┘

  E2 : _classify_segments() classe déjà chaque morceau en intention/contrainte/contexte/meta. Aujourd'hui c'est calculé
  puis jeté. Il suffit de câbler ça dans la sortie → prompt réordonné en tâche → contexte → contraintes → format. Zéro
  mot inventé, déterministe, gros ratio gain/effort.

  E3 : Détecter les slots vides selon le type de tâche (technique/analytique/documentaire) et les proposer comme chips
  cliquables. L'user valide, Helios ne devine pas.

  Note qualité 4 axes à la place du pertinence_score actuel : Clarté / Spécificité / Structure / Concision —
  avant→après.

  Ordre de bataille suggéré par co-auteur :
  1. E2 restructuration (déjà ~80% du code)
  2. Note 4 axes (rend E2 visible)
  3. E3 chips (identité produit)
  4. Calibrage effort par provider
  5. Mode pilote automatique
  6. Presets consultant/étudiant/dev
  7. Historique enrichi
  8. (plus tard) Ollama stage 2
  9. (phase business) Wallet/CGU/clés serveur

  ---
  Point clé du méta-retour : les 3 docs sont dans le bon ordre conceptuel mais pas encore dans le bon ordre
  d'implémentation. Effort → Wallet → SaaS. Et avant tout ça : E2 + note qualité, parce que c'est du code présent à
  câbler, pas des features nouvelles.


## Ordre d'attaque

```
✅ E2 scaffold → ✅ Note qualité → ✅ Calibrage effort
→ ✅ E2b Qwen intégré (v6) · 🔧 frontend E2b badges audit
→ ⏳ E3 chips → Pilote auto → Presets
→ Historique enrichi → (Ollama stage 2) → (Wallet / CGU)
```

---

## Bloc 1 — Optimiseur : de nettoyeur à ré-ingénieur

### E2 · Restructuration pyramidale ✅
**Statut : livré 2026-06-08**

Deux couches implémentées et mergées dans main :

**E2a — Scaffold déterministe (co-auteur, mergé)**
- `_restructure_scaffold()` — remonte la demande en tête ("lead with the ask")
- `_FORMAT_RE` — détection des contraintes de format (0/10 → 2/10 sur corpus réel)
- `_compute_quality_note()` — note 4 axes additive à `pertinence_score`
- 54/54 tests verts

**E2b — Couche sémantique Qwen (system prompt v6 intégré — 2026-06-09)**
- qwen3:8b via Ollama (Tour, RTX 3050 via Tailscale)
- Amorces naturelles : "Tu es / Je travaille sur / Tu dois" (labels Markdown supprimés)
- Ancres sémantiques par composante · Contraintes dure vs molle · Inférence signal fort
- Fix cohérence audit : `_fix_audit_coherence()` Python + ÉTAPE 4 system prompt
- Corrections audit co-auteur : opt-in `semantic`, timeout granulaire, métriques propres
- Frontend E2b en cours : audit badges (6 axes) + warning ambiguïtés → pending

---

### Note qualité 4 axes ✅
**Statut : livré 2026-06-08 (mergé avec E2a)**

Remplacer "combien tu as économisé" par une grille lisible :

| Axe | Avant | Après |
|---|---|---|
| Clarté | 72 | 94 |
| Spécificité | 41 | 88 |
| Structure | 20 | 95 |
| Concision | 100 | 100 |

Ce qui fait dire "mon prompt est passé de moyen à excellent" — pas "−18 tokens".

---

### E3 · Complétion guidée par chips
**Priorité : court terme — identité produit**

Détecter les slots vides selon le type de tâche, proposer des chips cliquables. L'user valide, Helios ne devine jamais.

| Type tâche | Slots attendus |
|---|---|
| technique | langage · objectif · format sortie · gestion erreurs |
| analytique | sujets comparés · critères · format · verdict attendu |
| documentaire | sujet · audience · niveau · structure |
| simple | (aucun — on le laisse court) |

UI : `Manque : Format de sortie ? → [ Code seul ] [ Code + explications ]`

Version heuristique d'abord (chips fixes). Version sémantique via Ollama plus tard.

---

### Apprentissage lexique par user
**Priorité : court terme**

`lexique_noise.json` qui s'enrichit par profil utilisateur. L'optimiseur devient meilleur avec l'usage pour chaque user. Augmente la marge ET les économies redistribuées (futur).

---

## Bloc 2 — Routing : aller plus loin que "quel modèle"

### Calibrage effort par provider ✅
**Statut : livré — mergé main session précédente (2026-06-05→08)**

La couche naturelle après "quel modèle" : "combien il réfléchit".

| Provider | Paramètre | Valeurs |
|---|---|---|
| OpenAI o-series | `reasoning_effort` | `low` / `medium` / `high` |
| Gemini | `thinking_budget` | tokens alloués |
| Claude Opus | `budget_tokens` | tokens alloués |

Sur les tâches moyennes, c'est là que les vraies économies supplémentaires se cachent. À absorber en marge, ne pas répercuter à l'user.

---

### Ollama stage 2 — routing sémantique
**Priorité : moyen terme — bloqué par dimensionnement VPS**

Routing sémantique sur les ~20% de cas ambigus que l'heuristique ne gère pas bien.

- VPS Coolify : 7.8GB RAM, 5.4GB dispo — qwen2.5:3b (~2GB) possible mais tendu avec Postgres + MinIO + FastAPI
- Débloque aussi : E3 sémantique, explication routing défendable
- **Ne pas implémenter avant d'avoir de vrais conflits en prod à analyser**

---

## Bloc 3 — Expérience non-tech (la cible)

### Mode pilote automatique
**Priorité : court terme**

Toggle unique. L'user tape son message, Helios choisit tout (provider, modèle, effort). Zéro paramétrage. C'est le produit pour la cible non-tech (consultant, rédacteur, étudiant).

---

### Profils d'usage presets
**Priorité : court terme**

`consultant` / `étudiant` / `dev` — configurent le routing par défaut + les squelettes E3. Onboarding en 20 secondes pour un non-tech.

---

## Bloc 4 — Valeur tangible (sans rien à prouver)

### Historique enrichi par conversation
**Priorité : court terme — données déjà calculées, juste à exposer**

Afficher sur chaque échange : coût réel, modèle utilisé, CO₂, tokens économisés, note qualité. La donnée existe déjà dans le backend.

---

### Export conversation
**Priorité : moyen terme**

PDF ou Markdown avec métadonnées (coût, modèle, tokens économisés). Utile pour les consultants qui tracent leur usage IA dans leurs livrables.

---

## Bloc 5 — Reporté : dépend de données réelles

| Feature | Bloquant par |
|---|---|
| Dashboard coûts cumulés vs baseline | Baseline arbitraire à trancher + données réelles |
| Cache sémantique patterns fréquents | Volume faible en prod pour l'instant |
| Explication routing visible | Stage 2 Ollama requis (sinon heuristique trop fragile à montrer) |
| Rapport d'économies hebdo | Cumul fiable requis |

---

## Bloc 6 — Reporté : phase business (produit à ~90%)

> Ne pas implémenter sans accord co-auteur + structure juridique.

| Feature | Bloquant par |
|---|---|
| Wallet prépayé (Stripe / LemonSqueezy) | Accord équipe + risque réglementaire EU (classification paiement) |
| Clés API côté serveur | Wallet requis pour avoir du sens |
| Redistribution automatique économies | Données réelles d'usage requis d'abord |
| Grace period crédit épuisé | Wallet requis |
| Factures automatiques | Wallet requis |
| CGU + politique RGPD | Structure juridique (auto-entreprise / SAS) à définir d'abord |
| Multi-workspace équipes | Maturité produit |
| API Helios publique | Maturité produit |

**Point réglementaire wallet** : acheter des tokens en gros et les revendre à l'unité avec marge peut être classifié comme activité de paiement selon certaines juridictions EU. À vérifier avant le premier euro encaissé.

---

## Ce qui a été tranché (ne pas rouvrir)

- **Comparateur "sans Helios" par message** → bruit, fatigant. Version cumulée seulement (bloc 5).
- **Score de confiance routing** → redondant avec le stage 2, supprimé.
- **Double condition CO₂ + économies pour la redistribution** → trop complexe. Condition économies uniquement.
- **Minimum redistribution** : 0,10€ (en dessous = pas de valeur perçue).
