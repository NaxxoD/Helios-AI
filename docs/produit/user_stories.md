# User Stories — Helios AI / EcoIA Tracker

**Projet** : Helios AI — suivi impact environnemental des LLM  
**Équipe** : 2 membres, co-auteur)  
**Méthode** : Scrum — 2 sprints  

---

## Légende

| Priorité | Signification |
|----------|---------------|
| M | Must have — bloquant pour la livraison |
| S | Should have — important mais pas bloquant |
| C | Could have — ajout de valeur si le temps le permet |
| W | Won't have — hors scope ce sprint |

| Statut | |
|--------|-|
| ✅ | Terminé |
| 🔧 | En cours |
| ⬜ | À faire |

---

## Sprint 1 — Fonctionnalités core

| ID | En tant que… | Je veux… | Afin de… | Priorité | Statut |
|----|-------------|----------|----------|----------|--------|
| US-01 | Visiteur | créer un compte avec email + mot de passe | accéder à mes données personnalisées | M | ✅ |
| US-02 | Utilisateur | me connecter et me déconnecter | accéder à mon espace sécurisé | M | ✅ |
| US-03 | Utilisateur | réinitialiser mon mot de passe par email | ne pas perdre l'accès à mon compte | S | ✅ |
| US-04 | Utilisateur | supprimer mon compte | exercer mon droit à l'oubli | C | ✅ |
| US-05 | Visiteur | calculer l'impact d'une conversation sans créer de compte | tester l'outil avant de m'inscrire | M | ✅ |
| US-06 | Utilisateur | importer une conversation (fichier ou texte collé) | mesurer l'impact d'un échange réel | M | ✅ |
| US-07 | Utilisateur | consulter le détail d'une session importée | comprendre précisément mon impact par session | S | ✅ |
| US-08 | Utilisateur | voir la liste de toutes mes sessions | suivre mon historique d'utilisation | M | ✅ |
| US-09 | Utilisateur | consulter mon dashboard avec KPI et graphiques | visualiser mon impact global en un coup d'œil | M | ✅ |
| US-10 | Utilisateur | voir des équivalences concrètes (douches, chauffage) | donner du sens aux chiffres kWh/CO₂ | S | ✅ |

---

## Sprint 2 — Fonctionnalités avancées

| ID | En tant que… | Je veux… | Afin de… | Priorité | Statut |
|----|-------------|----------|----------|----------|--------|
| US-11 | Utilisateur | optimiser un prompt pour réduire son impact | consommer moins d'énergie sans perdre en qualité | S | ✅ |
| US-12 | Utilisateur | faire un quiz comparant différents modèles IA | choisir le modèle le plus adapté à mon usage | C | ✅ |
| US-13 | Administrateur | accéder à un dashboard de supervision | surveiller l'activité globale de la plateforme | S | ✅ |
| US-14 | Administrateur | modifier les facteurs d'impact et supprimer des sessions | maintenir la cohérence des données | S | ✅ |
| US-15 | Utilisateur | naviguer entre les pages de mon historique | consulter mes anciennes sessions sans tout charger d'un coup | S | ✅ |
| US-16 | Utilisateur | exporter mon historique en CSV | analyser mes données dans un tableur | C | ✅ |
| US-17 | Utilisateur | corriger rétroactivement le modèle d'une session | fiabiliser les sessions importées sans modèle détecté | C | ✅ |
| US-18 | Développeur | disposer d'une suite de 24 tests unitaires sur l'optimiseur | garantir la fiabilité des calculs d'impact lors des évolutions | M | ✅ |

---

## Critères d'acceptation détaillés (US restantes)

### US-16 — Export CSV
- Bouton "Exporter en CSV" visible dans HistoriqueView
- Appel `GET /api/export/csv` avec `responseType: blob`
- Fichier téléchargé nommé `helios_historique_AAAA-MM-JJ.csv`
- Colonnes : date, provider, modèle, tokens estimés, kWh, CO₂ standard, CO₂ éthique

### US-17 — Sélecteur modèle rétroactif
- Dans SessionDetailView, afficher un sélecteur de modèle si `session.model === null`
- Appel `PATCH /api/sessions/{id}` avec `{ model: "..." }`
- Recalcul de l'impact affiché sans rechargement complet de la page
- La liste des modèles disponibles vient de `GET /api/upload/providers`

### US-18 — Tests unitaires optimiseur
- Fichier `backend/tests/test_optimiseur.py`
- 24 cas de test couvrant : prompts courts, longs, multilingues, cas limites (vide, caractères spéciaux)
- Exécution via `pytest tests/ -v` sans erreur
- Portage depuis `backend/tests/test_optimiseur.py` sur la branche `proto`

---

## Backlog MoSCoW — synthèse

| Priorité | US | Statut |
|----------|----|--------|
| Must | US-01, US-02, US-05, US-06, US-08, US-09, US-18 | Tous ✅ |
| Should | US-03, US-07, US-10, US-11, US-13, US-14, US-15 | Tous ✅ |
| Could | US-04, US-12, US-16, US-17 | Tous ✅ |

---

  ┌───────┬───────────────────────────────┬──────────────────────────────────────────────┐
  │  ID   │              US               │                    Statut                    │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-01 │ Créer un compte               │ ✅ — flow email complet + mode dev sans SMTP │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-02 │ Se connecter / déconnecter    │ ✅ — check is_verified au login              │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-03 │ Reset mot de passe            │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-04 │ Supprimer son compte          │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-05 │ Calcul anonyme sans compte    │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-06 │ Importer une conversation     │ ✅ — pondération ×5 input/output             │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-07 │ Détail d'une session          │ ✅ — idem via extension                      │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-08 │ Historique sessions           │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-09 │ Dashboard KPI + graphiques    │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-10 │ Équivalences concrètes        │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-11 │ Optimiser un prompt           │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-09 │ Dashboard KPI + graphiques    │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-10 │ Équivalences concrètes        │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-11 │ Optimiser un prompt           │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-12 │ Quiz comparateur modèles      │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-13 │ Dashboard admin               │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-14 │ Gérer sessions + facteurs     │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-15 │ Pagination historique         │ ✅                                           │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-16 │ Export CSV                    │ ✅ — bouton HistoriqueView, Axios blob        │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-17 │ Sélecteur modèle rétroactif   │ ✅ — PATCH /sessions/{id}, recalcul CO2/kWh  │
  ├───────┼───────────────────────────────┼──────────────────────────────────────────────┤
  │ US-18 │ 24 tests unitaires optimiseur │ ✅ — 54/54 tests pytest (44 origine + 10 E2)  │
  └───────┴───────────────────────────────┴──────────────────────────────────────────────┘




*Dernière mise à jour : 2026-06-09 — E2b backend intégré (v6) · US-19 🔧 frontend badges pending*

---

## Phase 2 — Post-soutenance (roadmap features.md)

> Statut global : ⬜ à faire — ordre d'attaque défini dans features.md

### Personas

| Alias | Profil |
|---|---|
| Utilisateur | Tout utilisateur connecté |
| Consultant | Cible non-tech principale (freelance, rédacteur) |
| Dev | Utilisateur technique |
| Admin | Administrateur plateforme |

---

### Bloc 1 — Optimiseur : de nettoyeur à ré-ingénieur

| ID | En tant que… | Je veux… | Afin de… | Priorité | Statut |
|----|-------------|----------|----------|----------|--------|
| US-19 | Utilisateur | que mon prompt soit automatiquement restructuré (tâche → contexte → contraintes → format) avant envoi | obtenir des réponses IA plus précises sans connaître le prompt engineering | M | ✅ |
| US-20 | Utilisateur | voir un score qualité avant/après sur 4 axes (clarté, spécificité, structure, concision) | comprendre concrètement l'amélioration apportée à mon prompt, pas juste "−X tokens" | M | ✅ |
| US-21 | Consultant | être guidé par des chips cliquables pour compléter les informations manquantes de mon prompt (format de sortie, contexte, audience) | écrire des prompts complets sans jamais avoir à apprendre le prompt engineering | S | ✅ |
| US-22bis | Utilisateur récurrent | indiquer explicitement les termes que l'optimiseur ne doit pas supprimer, et gérer ce lexique personnel depuis mes paramètres | que l'optimiseur respecte mon jargon métier sans que je doive le corriger à chaque utilisation (étape 1 — feedback manuel) | S | ⬜ |
| US-22 | Utilisateur récurrent | que l'optimiseur détecte automatiquement mes habitudes de rédaction sans intervention de ma part | que mon lexique personnel s'enrichisse avec l'usage sans effort supplémentaire (étape 2 — auto-learning, dépend de données réelles) | S | ⬜ |

**Critères d'acceptation — US-19 (E2 Restructuration)**
- `_classify_segments()` déjà présent dans l'optimiseur — câbler sa sortie dans le prompt réorganisé
- Ordre canonique : Tâche → Contexte → Contraintes → Format
- Aucun mot inventé — uniquement réordonnancement du contenu existant
- Prompt original conservé en diff visible côté UI

**Critères d'acceptation — US-20 (Note qualité 4 axes)**
- Remplace l'actuel `pertinence_score` dans la réponse de l'optimiseur
- 4 scores entre 0 et 100 : Clarté, Spécificité, Structure, Concision
- Affichage avant → après (ex : Structure 20 → 95)
- Calcul déterministe côté backend (pas d'appel LLM supplémentaire)

**Critères d'acceptation — US-21 (E3 Chips)**
- Détection du type de tâche : technique / analytique / documentaire / simple
- Affichage des slots manquants comme chips cliquables dans l'UI
- Clic sur une chip → slot ajouté au prompt, jamais inventé automatiquement
- Type "simple" → aucune chip proposée

**Critères d'acceptation — US-22 (Lexique personnel)**
- Architecture : `lexique_noise.json` global partagé (existant, inchangé) + table `user_lexique` en base (`user_id`, `terme`, `added_at`)
- Post-optimisation : si un terme a été supprimé, l'user peut cliquer "Toujours garder ce terme" → ajouté à son lexique perso (feedback explicite uniquement, pas d'auto-learning)
- Fusion à l'optimisation : supprime ce qui est dans le global **sauf** si le terme figure dans le lexique perso de l'user
- Paramètres user : page listant les termes du lexique perso, suppression terme par terme + "Vider tout"
- Placement UI : accessible depuis les paramètres du compte, à proximité (mais distinct) de la zone "Supprimer mon compte"
- RGPD : seuls des termes isolés stockés (pas de prompts, pas de contexte) — l'user peut tout consulter et tout supprimer

---

### Bloc 2 — Routing : au-delà du choix de modèle

| ID | En tant que… | Je veux… | Afin de… | Priorité | Statut |
|----|-------------|----------|----------|----------|--------|
| US-23 | Utilisateur | qu'Helios ajuste le niveau de réflexion du modèle (faible / moyen / élevé) selon la complexité de ma tâche | réduire le coût sur les requêtes moyennes sans sacrifier la qualité sur les complexes | S | ✅ |
| US-24 | Dev | consulter le détail du routing (provider, modèle, niveau d'effort, coût estimé) sur chaque échange | comprendre et auditer les décisions d'Helios | C | ✅ |
| US-25 | Utilisateur | qu'Helios route les requêtes ambiguës via un LLM local (Ollama) pour affiner la décision | que le bon modèle soit choisi même pour les tâches difficiles à catégoriser par mots-clés | C | ⚠️ |
| US-25b | Utilisateur | qu'Helios compresse automatiquement le contexte historique quand la session devient trop longue | que mes échanges restent cohérents et moins coûteux sur les sessions longues, sans intervention de ma part | C | ⬜ |

**Critères d'acceptation — US-24 (Détail routing)**
- Données déjà calculées dans le backend — exposition uniquement (même logique que US-28)
- Affichage par échange dans ChatView : provider choisi, modèle exact, niveau d'effort (low/medium/high), coût estimé ($)
- co-auteur a commencé dans `ConversationDetailView` (branche du co-auteur) — merger avant d'implémenter
- Stage 1 (heuristique) : afficher "règle déclenchée : [type détecté]" — simple mais honnête
- Stage 2 (US-25) requis pour afficher une explication routing défendable — US-24 reste partielle sans US-25
- Accessible en mode dev/debug uniquement (masqué pour les profils non-tech)

**Critères d'acceptation — US-25 (Routing stage 2 sémantique)**
- Modèle : `qwen2.5:1.5b` via Ollama (~1 GB VRAM) — pas Nemotron (trop lourd, 43 GB sur Ollama)
- Rôle : classifier les requêtes ambiguës en 4 catégories (technique / analytique / documentaire / simple) que l'heuristique stage 1 ne tranche pas
- Pipeline : heuristique mots-clés → si ambigu → qwen2.5:1.5b → classifie → E2 (qwen3:8b) → LLM final
- Dev (Tour) : `ollama pull qwen2.5:1.5b` — tient en VRAM avec qwen3:8b simultanément (RTX 3050 8 GB, ~6-7 GB utilisés)
- Dev (Debian) : tourne CPU-only, ~300-500ms/appel — acceptable pour les cas ambigus uniquement
- VPS prod : `qwen2.5:1.5b` (~1 GB) + stack existante (Postgres + MinIO + FastAPI) dans 5.4 GB dispo — faisable, à benchmarker
- Ne pas implémenter avant d'avoir identifié de vrais cas ambigus en prod

**Critères d'acceptation — US-25b (Compression de contexte)**
- Déclencheur : contexte historique > seuil (ex. 3000 tokens) — indépendant du routing et des switches de modèle
- Ratio cible : 1:3 (~700 tokens sur 2000) — sweet spot qualité/économie, évite les hallucinations d'un ratio 1:6
- Compression sélective : résumer les échanges conversationnels, préserver les blocs techniques tels quels (chiffres, seuils, noms)
- Modèle de compression : modèle léger (Mistral Small 3.1 en prod hypothétique, ou qwen2.5:1.5b déjà disponible)
- Transparent pour l'user : aucun crédit consommé, aucune mention visible — inclus dans la marge de service
- Pipeline par tour : 1. routing → 2. volume check → si > seuil : compression 1:3 → envoi
- Note technique : ajouter `account_type: personal | enterprise` en base dès cette US pour anticiper le B2B sans refactoring

---

### Bloc 3 — Expérience non-tech

| ID | En tant que… | Je veux… | Afin de… | Priorité | Statut |
|----|-------------|----------|----------|----------|--------|
| US-26 | Consultant | activer un mode "pilote automatique" en un seul toggle | déléguer tous les choix IA à Helios (provider, modèle, effort) sans aucun paramétrage | S | ⬜ |
| US-27 | Nouvel utilisateur | choisir mon profil d'usage (consultant / dev / créatif / étudiant) à l'onboarding et l'affiner dans mes paramètres | que le routing soit pré-configuré pour mon contexte dès le premier échange, sans paramétrage technique | S | ⬜ |

**Critères d'acceptation — US-26 (Pilote auto)**
- Toggle visible dans le header ou les settings
- En mode pilote : tous les sélecteurs provider/modèle/effort masqués ou désactivés
- Helios choisit en fonction du type de tâche détecté + profil user
- Persisté en base par utilisateur

**Critères d'acceptation — US-27 (Presets)**

Couche 1 — Obligatoire à l'onboarding :
- Écran de sélection au premier login — 4 profils persona :

| Profil | Palier défaut | Effort | Type dominant | Chips E3 prioritaires |
|---|---|---|---|---|
| Consultant | 3 | medium | analytique / documentaire | Critères · Format livrable · Audience · Niveau détail |
| Dev | 2 | low | technique | Langage · Format sortie · Gestion erreurs · Objectif |
| Créatif | 4 | low | documentaire / simple | Ton · Audience · Style · Longueur |
| Étudiant | 2 | low-medium | documentaire / simple | Niveau explicatif · Exemples · Structure |

- Stocké en base : `profile: enum(consultant, dev, creatif, etudiant)`
- Modifiable à tout moment depuis les paramètres du compte

Couche 2 — Optionnelle dans les settings (affinage) :
- Override manuel par champ : palier, effort par défaut, type de tâche dominant, chips prioritaires
- Profils supplémentaires disponibles en settings (non proposés à l'onboarding) :

| Profil | Palier défaut | Effort | Type dominant | Chips E3 prioritaires |
|---|---|---|---|---|
| Manager | 1 | low | simple / analytique | Format (synthèse/détail) · Deadline · Décision attendue |
| Chercheur | 3 | high | analytique | Sources · Niveau rigueur · Structure académique · Verdict |

- Pour les cas mixtes (ex : étudiant dev → profil Dev) ou utilisateurs avancés
- La cible non-tech ne voit jamais cette couche

Règle d'implémentation : livrer couche 1 d'abord, couche 2 en itération suivante.

---

### Bloc 4 — Valeur tangible

| ID | En tant que… | Je veux… | Afin de… | Priorité | Statut |
|----|-------------|----------|----------|----------|--------|
| US-28 | Utilisateur | voir sur chaque échange son coût réel, le modèle choisi, les tokens économisés et la note qualité | avoir une traçabilité complète de ma consommation IA échange par échange | S | ✅ |
| US-29 | Consultant | exporter une conversation en PDF ou Markdown avec ses métadonnées (coût, modèle, tokens) | intégrer la trace de mon usage IA dans mes livrables clients | C | ⬜ |

**Critères d'acceptation — US-28 (Historique enrichi)**
- Données déjà calculées dans le backend — exposition uniquement
- Affichage dans ChatView sous chaque réponse : coût ($), modèle, tokens économisés, note qualité
- Également visible dans HistoriqueView par échange

---

### Bloc 5 — Reporté (dépend de données réelles)

| ID | En tant que… | Je veux… | Afin de… | Priorité | Statut |
|----|-------------|----------|----------|----------|--------|
| US-30 | Utilisateur | voir une courbe de mes économies cumulées depuis mon premier échange | mesurer la valeur réelle d'Helios sur le long terme | C | ⬜ |
| US-31 | Utilisateur | recevoir un résumé hebdomadaire de mes économies et de mon impact CO₂ | rester informé même quand je ne suis pas connecté | C | ⬜ |

> Bloqué par : baseline à trancher + volume insuffisant en prod.

**Décision baseline (à valider avec co-auteur) :**

| Option | Avantage | Inconvénient |
|---|---|---|
| Coût brut vs coût optimisé Helios | Honnête, auto-suffisant, pas de source externe | Ne se compare qu'à soi-même |
| GPT-4o prix public | Référence connue, lisible par l'user | Arbitraire si l'user n'utilise pas GPT-4o |
| Moyenne marché (IEA Energy and AI Observatory) | Institutionnel, défendable | Granularité insuffisante (macro, pas par échange) |
| G7 Energy and AI Work Plan (2025) | Officiel, bon pour le pitch | Trop macro (data center / modèle entier) — inutilisable comme baseline par échange |

→ **Option recommandée : coût brut vs coût optimisé Helios** — seule baseline qui ne dépend d'aucune source externe et reste honnête quelle que soit l'évolution des prix marché. Les données G7 et IEA restent utiles pour le positionnement et la landing, pas pour le calcul.

---

### Bloc 6 — Reporté (phase business)

> Ne pas implémenter sans accord co-auteur + structure juridique validée.

| ID | En tant que… | Je veux… | Afin de… | Priorité | Statut |
|----|-------------|----------|----------|----------|--------|
| US-32 | Utilisateur | déposer des crédits Helios et voir mon solde en temps réel | utiliser l'IA sans configurer mes propres clés API | W | ⬜ |
| US-33 | Utilisateur | qu'Helios gère les appels API en backend avec ses propres clés | ne jamais avoir à créer un compte OpenAI ou Anthropic | W | ⬜ |
| US-34 | Utilisateur | recevoir automatiquement 50% de mes économies crédités sur mon wallet chaque semaine | être récompensé financièrement pour mon usage optimisé | W | ⬜ |
| US-35 | Utilisateur | bénéficier d'une période de grâce quand mon solde est épuisé | ne pas être bloqué en plein milieu d'un projet | W | ⬜ |
| US-36 | Consultant | recevoir une facture mensuelle de mon usage Helios | justifier la dépense dans mes notes de frais | W | ⬜ |

> **Alerte réglementaire US-32/33** : revendre des tokens avec marge peut être classifié comme activité de paiement (EU). Vérifier avant le premier euro encaissé.

---

## Récapitulatif Phase 2

| Bloc | US | Priorité | Statut |
|---|---|---|---|
| Optimiseur (E2, note, E3, chips, lexique) | US-19 à US-22 | M / S | US-19 ✅ · US-20 ✅ · US-21 ✅ · US-22bis ⬜ · US-22 ⬜ (long terme) |
| Routing (effort, détail, Ollama, compression) | US-23 à US-25b | S / C | US-23 ✅ · US-24 ✅ (commune) · US-25 ⚠️ (supersédé par routing ML Plan 3) · US-25b ⬜ |
| Expérience non-tech (pilote, presets) | US-26 à US-27 | S | US-26 ⬜ · US-27 ⬜ (4 profils onboarding + Manager/Chercheur en settings, 2 couches) |
| Valeur tangible (historique, export) | US-28 à US-29 | S / C | US-28 ✅ (commune) · US-29 ⬜ |
| Reporté données réelles | US-30 à US-31 | C | ⬜ (baseline = coût brut vs optimisé Helios) |
| Reporté phase business | US-32 à US-36 | W | ⬜ |

*Dernière mise à jour : 2026-06-16 — US-21 ✅ · US-24 ✅ · US-28 ✅ (commune) · US-25 supersédé routing ML · gating ML déprioritisé*

---


## A Débattre IRL 

Voilà une ébauche — à valider avec co-auteur avant toute implémentation :

  ┌────────────┬───────────────┬────────────────┬───────────────────────────┬───────────────────────────────────────────────────────────┐
  │   Profil   │ Palier défaut │ Effort routing │    Type tâche dominant    │                   Chips E3 prioritaires                   │
  ├────────────┼───────────────┼────────────────┼───────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Consultant │ 3             │ medium         │ analytique / documentaire │ Critères · Format livrable · Audience · Niveau détail     │
  ├────────────┼───────────────┼────────────────┼───────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Étudiant   │ 2             │ low-medium     │ documentaire / simple     │ Niveau explicatif · Exemples · Structure                  │
  ├────────────┼───────────────┼────────────────┼───────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Dev        │ 2             │ low            │ technique                 │ Langage · Format sortie · Gestion erreurs · Objectif      │
  ├────────────┼───────────────┼────────────────┼───────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Créatif    │ 4             │ low            │ documentaire / simple     │ Ton · Audience · Longueur · Style                         │
  ├────────────┼───────────────┼────────────────┼───────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Chercheur  │ 3             │ high           │ analytique                │ Sources · Niveau rigueur · Structure académique · Verdict │
  ├────────────┼───────────────┼────────────────┼───────────────────────────┼───────────────────────────────────────────────────────────┤
  │ Manager    │ 1             │ low            │ simple / analytique       │ Format (synthèse/détail) · Deadline · Décision attendue   │
  └────────────┴───────────────┴────────────────┴───────────────────────────┴───────────────────────────────────────────────────────────┘

  Ce que ça révèle :

  - Dev et Étudiant se ressemblent sur l'effort mais divergent sur les chips — potentiellement fusionnables
  - Consultant et Chercheur sont proches — la différence principale c'est l'effort (medium vs high) et le niveau de rigueur
  - Créatif et Manager sont les plus distinctifs — et probablement les plus utilisés hors contexte académique/HETIC

  Question clé avant de fixer la liste : combien de profils à l'onboarding sans perdre l'user ? Au-delà de 4-5 options sur un seul écran, ça devient une décision cognitive, pas un onboarding fluide.

  Ma suggestion : 4 profils max — Consultant, Dev, Créatif, Étudiant — et laisser Chercheur + Manager en "personnalisé" dans les settings.

  Tu veux affiner ou on envoie ça à co-auteur pour avis ?

✻ Sautéed for 20s

> ca me semble correct psk en théorie plus le pannel est large plus c'est spécifique un dev et un etudiant ont peu etre le meme type de profil mais un dev c'est un tech un étudiant pourrait etre dans nimporte
  quelle filliere, consultant et cherhceur pareil les objectif sont pas les memes en principe mais si les profil sont similaire ?

● C'est exactement le bon angle. Le problème c'est qu'on a mélangé deux choses :

  - Persona (qui tu es) → Consultant, Dev, Étudiant, Chercheur
  - Comportement (ce que tu fais) → Technique, Analytique, Créatif, Simple

  Un étudiant dev → comportement technique, même profil qu'un dev.
  Un étudiant en lettres → comportement créatif/documentaire.
  Un consultant et un chercheur → comportement analytique similaire, effort différent.

  Ce qui suggère de basculer sur des profils comportementaux plutôt que des personas :

  ┌────────────┬────────┬────────┬───────────────┬──────────────────────────────────────────┐
  │   Profil   │ Palier │ Effort │ Type dominant │                 Chips E3                 │
  ├────────────┼────────┼────────┼───────────────┼──────────────────────────────────────────┤
  │ Technique  │ 2      │ low    │ technique     │ Langage · Format · Gestion erreurs       │
  ├────────────┼────────┼────────┼───────────────┼──────────────────────────────────────────┤
  │ Analytique │ 3      │ high   │ analytique    │ Critères · Sources · Structure · Verdict │
  ├────────────┼────────┼────────┼───────────────┼──────────────────────────────────────────┤
  │ Créatif    │ 4      │ low    │ documentaire  │ Ton · Audience · Style · Longueur        │
  ├────────────┼────────┼────────┼───────────────┼──────────────────────────────────────────┤
  │ Simple     │ 1      │ low    │ simple        │ (aucune)                                 │
  └────────────┴────────┴────────┴───────────────┴──────────────────────────────────────────┘

  Avantage : ça s'aligne directement avec la classification E3 déjà en place — le routing et les chips utilisent exactement ces 4 catégories. Pas de mapping supplémentaire à maintenir.

  Inconvénient : "Technique / Analytique / Créatif / Simple" c'est moins intuitif à l'onboarding que "Dev / Consultant / Créatif / Étudiant".

  Solution possible : labels persona à l'affichage, comportements en dessous comme description — l'user se reconnaît dans le persona, le système utilise le comportement.

  À trancher avec co-auteur — c'est une décision produit/UX.