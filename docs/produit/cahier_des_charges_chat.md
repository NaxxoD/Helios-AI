# Cahier des charges — Helios Chat (Sprint 3)

**Date** : 2026-05-21  
**Statut** : En cours de développement  
**Branche** : `integration`

---

## 1. Positionnement produit

### Problème utilisateur

Les développeurs et professionnels qui paient un abonnement ou une API LLM envoient des prompts verbeux sans s'en rendre compte — politesse inutile, contexte répété, formulations redondantes — ce qui gonfle leur facture mensuelle et leur empreinte carbone sans apporter de valeur supplémentaire aux réponses.

**Ce n'est pas un problème de volonté : c'est un problème de visibilité.** Personne ne compte ses tokens en tapant. Personne ne sait que "Bonjour, j'espère que tu vas bien, pourriez-vous m'aider à..." coûte autant que la question elle-même.

### Proposition de valeur

Helios Chat est un **proxy entre l'utilisateur et son LLM** qui :
1. Rend visible le coût réel de chaque prompt (tokens, kWh, CO₂)
2. Optimise automatiquement les prompts verbeux avant envoi — moins de bruit, même qualité de réponse
3. Traduit l'économie en euros : un abonnement à 100€/mois peut descendre à 20€ si les prompts sont optimisés de 40%

### Pourquoi ouvrir Helios plutôt que ChatGPT ?

**Une seule raison valide aujourd'hui : l'optimiseur de prompts.**  
Si l'optimiseur est bon → l'utilisateur économise sur son abonnement LLM sans changer ses habitudes.  
Si l'optimiseur dégrade la réponse → l'utilisateur ne reviendra pas.

L'optimiseur est le composant critique. Tout le reste en dépend.

### Limites connues (à nommer en soutenance)

| Limite | Impact | Décision |
|--------|--------|----------|
| Pas de streaming | Réponse en bloc après 5-8s (vs ChatGPT mot-à-mot) | Acceptable pour MVP juin |
| Clé API perdue au refresh | L'utilisateur la retape à chaque session | Acceptable pour MVP juin — ne pas présenter comme feature de sécurité |
| Optimiseur heuristique | Peut dégrader sur certains types de prompts | Mitigé par seuil de confiance (voir §4) |

---

## 2. User Stories — Sprint 3

### Supprimées

| ID | Raison |
|----|--------|
| ~~US-25~~ | Recommandation modèle par longueur de prompt — signal trop faible. Longueur ≠ complexité. Taux d'erreur estimé ~40%. Retirée. |

### Must Have (MVP juin)

| ID | En tant que… | Je veux… | Afin de… |
|----|-------------|----------|----------|
| US-19 | Utilisateur | saisir ma clé API par provider (OpenAI, Anthropic, Google) | connecter mon LLM sans quitter Helios |
| US-20 | Utilisateur | taper un message dans une interface chat | interagir avec mon LLM directement depuis Helios |
| US-21 | Utilisateur | voir mon prompt optimisé avant envoi avec le % de réduction | choisir d'envoyer l'original ou la version optimisée |
| US-22 | Utilisateur | choisir mon provider et mon modèle | contrôler l'impact énergétique de chaque échange |
| US-23 | Utilisateur | voir la réponse du LLM dans l'interface | avoir un flux de travail complet sans copier-coller |
| US-27 | Utilisateur | que ma clé API ne soit jamais stockée en base de données | garder le contrôle total sur mes credentials |
| US-28 | Utilisateur | que le LLM se souvienne des messages précédents dans la même session | mener une vraie conversation (pas des questions isolées) |

### Should Have

| ID | En tant que… | Je veux… | Afin de… |
|----|-------------|----------|----------|
| US-24 | Utilisateur | voir ma conso (tokens / kWh / CO₂) mise à jour après chaque message | suivre mon impact en temps réel |
| US-26 | Utilisateur | choisir le niveau d'optimisation (doux / modéré / agressif) | adapter la compression à mes besoins |

---

## 3. Architecture technique

### Flux de données

```
[Utilisateur tape] 
    → [ChatView.vue maintient l'historique complet en mémoire]
    → Si optimisation activée :
        → POST /api/optimise/ {prompt} 
        → Si réduction ≥ 10% ET score pertinence ≥ 70 :
            → Modal comparaison original / optimisé
            → Utilisateur choisit
        → Sinon : envoyer directement sans interruption
    → POST /api/chat/send {provider, model, api_key, messages[]}
        → chat_service.call_llm() → API externe (OpenAI / Anthropic / Google)
        → session_repo.create_with_metrics() → PostgreSQL
    → Réponse affichée + métriques CO₂ dans la bulle
```

### Stockage des données

| Donnée | Où | Durée |
|--------|----|-------|
| Clé API | `sessionStorage` navigateur | Jusqu'à fermeture de l'onglet |
| Historique messages | Mémoire Vue (`ref([])`) | Jusqu'à rechargement de la page |
| Métriques session | PostgreSQL (`simulation_sessions` + `impact_metrics`) | Permanent |
| Contenu des messages | **Non stocké** | — |

> **Conséquence** : l'utilisateur ne peut pas relire ses conversations passées (contenu). Il voit seulement les métriques dans l'historique. C'est une limitation documentée, pas un bug.

### Providers supportés

| Provider | API endpoint | Auth | Modèles |
|----------|-------------|------|---------|
| OpenAI | `api.openai.com/v1/chat/completions` | `Bearer sk-...` | gpt-4o, gpt-4o-mini, gpt-4-1, o1, o1-mini |
| Anthropic | `api.anthropic.com/v1/messages` | `x-api-key` | claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5 |
| Google | `generativelanguage.googleapis.com/v1beta/...` | `?key=...` | gemini-2-5-pro, gemini-2-5-flash |

### Multi-turn (US-28)

**Déjà implémenté.** Le frontend maintient `messages[]` en mémoire et envoie l'historique complet à chaque requête. Le LLM reçoit le contexte de toute la conversation.

Cas particulier optimiseur + multi-turn :
- Seul le **dernier message utilisateur** est optimisé avant envoi
- L'historique précédent est envoyé tel quel (ne pas optimiser rétrospectivement)

---

## 4. Règles de l'optimiseur

### Seuil de confiance (nouveau)

L'optimisation est proposée à l'utilisateur **uniquement si** :
- Réduction de tokens ≥ 10% **ET**
- Score de pertinence (pyramide) ≥ 70

Si les deux conditions ne sont pas remplies → envoi direct sans interruption.

**Pourquoi :** une optimisation de moins de 10% ne vaut pas l'interruption du flux. Un score de pertinence < 70 indique que l'optimiseur a supprimé trop de contenu potentiellement utile.

### Niveaux d'optimisation (US-26 — Should Have)

| Niveau | Comportement |
|--------|-------------|
| Doux | Supprime uniquement la couche Bruit (politesse, remplissage) |
| Modéré | Bruit + compression Contexte redondant |
| Agressif | Comportement actuel (toutes les règles) |

### Ce que l'optimiseur ne touche jamais

- Couche **Intention** (ce que l'utilisateur veut obtenir)
- Couche **Contrainte** (règles à respecter — format, langue, limite)
- Messages précédents de la conversation (historique intouché)

---

## 5. Ce qui reste à coder

### Priorité immédiate

- [ ] Appliquer le seuil de confiance (10% / score 70) dans `ChatView.vue`
- [ ] Tester le flux complet avec une vraie clé API

### Should Have (avant soutenance si le temps le permet)

- [ ] US-26 : paramètre `niveau` dans `POST /api/optimise/` + sélecteur dans ChatView
- [ ] Indicateur de progression pendant l'attente de réponse (skeleton ou barre)

### Won't Have (post-soutenance)

- Streaming des réponses
- Stockage de l'historique des messages en DB
- Persistance de la clé API entre sessions
- Recommandation de modèle automatique

---

## 6. Critères d'acceptation — US-21 (optimisation avant envoi)

- [ ] Si réduction < 10% ou score < 70 → envoi direct, aucune interruption
- [ ] Si seuil atteint → modal avec texte original à gauche, optimisé à droite
- [ ] Le % de réduction est affiché dans la modal
- [ ] L'utilisateur peut choisir "Envoyer l'optimisé", "Envoyer l'original", ou "Annuler"
- [ ] Le message envoyé affiche un badge "✦ Prompt optimisé (−X%)" dans la bulle

---

*Cahier des charges rédigé suite à la revue technique co-auteur — 2026-05-21*
