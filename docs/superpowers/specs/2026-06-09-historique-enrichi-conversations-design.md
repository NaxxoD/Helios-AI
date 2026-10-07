# Design — Historique enrichi des conversations (Bloc 4)

**Date** : 2026-06-09
**Chantier** : Bloc 4 « Valeur tangible » — US-28 (historique enrichi)
**Statut** : design validé, prêt pour le plan d'implémentation

---

## Contexte

US-28 veut « voir sur chaque échange son coût réel, le modèle, les tokens économisés et la note qualité » — une **traçabilité par échange** de la consommation IA.

Le brainstorming a révélé un **trou d'architecture** : l'app a deux « historiques » disjoints —
- `/historique` (`HistoriqueView.vue`) = **sessions importées** (`SimulationSession`, flux upload).
- Les **conversations chat modernes** (`Conversation` + messages en MinIO) ne sont accessibles **que depuis la sidebar du chat** — **aucune page dans l'espace utilisateur**.

Décision validée : **unifier sous `/historique` avec deux onglets**, et ajouter une **vue détail par conversation** dans l'espace utilisateur. Cela comble le trou et donne la traçabilité par échange **sans toucher la zone de l'auteur** (ChatView / chat_service / routing).

## Objectifs

- Onglet **Conversations** dans `/historique` : liste des conversations chat avec métriques agrégées.
- **Vue détail conversation** : chaque échange affiché avec ses métriques (coût, modèle, tokens, CO₂, optimisation, pertinence).
- **Zéro collision** avec le travail de l'auteur : uniquement de nouvelles vues + des endpoints existants.

## Non-objectifs (hors v1)

- **Note qualité 4 axes par échange** : la `quality_note` n'est pas stockée par message aujourd'hui → **phase 2** (nécessite que ChatView persiste `quality_note` dans le message — petit changement en zone l'auteur, à coordonner). En v1 on affiche `pertinenceScore` (déjà stocké).
- Pas de modification de ChatView, chat_service, routing.
- Export PDF (l'export Markdown réutilise le plan déjà validé).

## Architecture

`/historique` devient une page à **2 onglets** :

| Onglet | Contenu | Source |
|---|---|---|
| **Conversations** (nouveau) | liste des conversations chat (titre, modèle, tokens, coût, CO₂, date) | `GET /api/conversations` (existe) |
| **Sessions importées** (existant) | contenu actuel de HistoriqueView, **inchangé** | inchangé |

**Nouvelle route** : `/user/conversations/:uuid` → `ConversationDetailView.vue` (en miroir de `/user/sessions/:id` → `SessionDetailView`).

## Composants

1. **`HistoriqueView.vue`** — refactor léger : barre d'onglets ; le contenu actuel (sessions + KPI + export CSV) passe dans l'onglet « Sessions importées ». L'onglet « Conversations » rend la nouvelle liste.
2. **Liste Conversations** (dans HistoriqueView ou sous-composant `ConversationsList.vue`) — `GET /api/conversations` ; chaque ligne cliquable → route détail. **Ne réutilise pas** la sidebar de ChatView (= zone l'auteur) ; liste autonome.
3. **`ConversationDetailView.vue`** (nouveau) — route `/user/conversations/:uuid`. `GET /api/conversations/{id}/messages`. Affiche l'en-tête (titre, modèle, totaux) puis **chaque échange** :
   - message **user** : contenu + badge « optimisé » si `optimized`, `savedPct`, `pertinenceScore`.
   - message **assistant** : contenu + ligne métriques `input→output tokens · coût · CO₂ · modèle/routed_model`.
   - Bouton **« Exporter (Markdown) »** réutilisant le plan export validé (client-side, à partir des messages chargés).

## Flux de données (tout existe déjà)

- Liste : `GET /api/conversations` → `[{id, title, provider, model, nb_turns, tokens_total, co2_g, cost_usd, impact_level, created_at}]` (`routers/conversations.py:39`).
- Détail : `GET /api/conversations/{id}/messages` → `{id, title, provider, model, messages[]}` (`routers/conversations.py:107`), ownership vérifiée via `conversation_repo.get(db, id, user.id)`.
- Structure message (MinIO) : user `{role, content, optimized, savedPct, pertinenceScore}` · assistant `{role, content, input_tokens, output_tokens, impact:{co2_standard}, cost_usd, routed_model}` · variantes `_compacted` (résumé, à afficher) et `isError` (à ignorer).

## Fichiers touchés

| Fichier | Nature |
|---|---|
| `frontend/src/views/user/HistoriqueView.vue` | refactor onglets (additif) |
| `frontend/src/views/user/ConversationDetailView.vue` | **nouveau** |
| `frontend/src/router/index.js` | **nouvelle route** `/user/conversations/:uuid` |
| `frontend/src/components/NavBar.vue` | éventuel libellé onglet (sinon inchangé) |

Aucun fichier backend modifié (endpoints existants). Aucun fichier de la zone l'auteur (ChatView, chat_service, routing).

## Vérification

1. Build front : `node.exe node_modules/vite/bin/vite.js build` (OK dans cet env).
2. Manuel : `/historique` affiche 2 onglets ; « Sessions importées » identique à avant ; « Conversations » liste les conversations ; clic → `/user/conversations/:uuid` affiche chaque échange avec métriques ; `isError` masqués, `_compacted` lisibles ; bouton export produit le Markdown attendu.

## Phase 2 (documenté, hors v1)

- Persister `quality_note` par message (capture côté ChatView au moment de l'optimisation) → afficher le **radar 4 axes** par échange. Coordination l'auteur.
- Option : endpoint backend `GET /api/conversations/{id}/export` (export par id sans ouvrir) — réutiliserait `conversation_repo.get` + `minio_client.load_messages` + `StreamingResponse`.
