# Spec — Helios v2 : la couche *Policy* apprise (Policy Engine)

- **Date** : 2026-06-12
- **Statut** : design validé, prêt pour plan d'implémentation
- **Auteur** : co-auteur (+ Claude)

## 1. Contexte & problème

Helios optimise aujourd'hui le prompt (E1 nettoyage regex, E2 scaffold déterministe, E3 complétude)
puis prend des **décisions heuristiques isolées** :

- **Palier de longueur** : `detect_palier()` (`backend/utils/optimiseur.py:160`) — choix par mots-clés/regex.
- **Routing** : `suggest_routing()` (`backend/utils/routing.py:41`) — `model_tier`/`effort` par scoring de mots-clés sur 31 tâches.
- **Estimation tokens output** : `_estimate_output_tokens()` (`optimiseur.py:60`) — multiplicateurs heuristiques.
- **Pertinence / quality note** : formules (`optimiseur.py:724`, `:1185`).

**Aucun modèle appris en production** (vérifié : pas de sklearn/torch/embeddings dans le backend).

Mesures (benchmark QM, juin 2026, 2 juges indépendants llama3.1:8b + qwen2.5:14b sur 45 prompts) :

- Le **palier** (contrainte de longueur) est **le seul levier coût réel** : **−32 %** sur l'échange complet (output facturé 5× l'input).
- Mais il **dégrade la qualité ~45 % du temps** (forcer "115 mots max" sur une question qui en demande 400) — 17/45 dégradations confirmées par les **deux** juges, concentrées sur le palier 2.
- La **réécriture LLM type Qwen** (variante expérimentale de l'auteur) : apport coût ~ +1,9 % (bruit) + dégradation propre (format creux). **Abandonnée.**

**Conclusion** : le levier marche mais est appliqué aveuglément. Le bon problème n'est pas « mieux réécrire »,
c'est **décider quand/comment comprimer sans dégrader** — un problème supervisé et mesurable.

## 2. Objectif & non-objectifs

**Objectif** : remplacer les décisions heuristiques isolées par **une couche ML unique, la Policy Engine**,
qui répond à : *pour ce prompt, quelle est l'exécution coût-optimale qui ne dégrade pas la réponse ?*
= **comprimer ou non** × **quel modèle** × **quelle longueur attendue**.

**Non-objectifs** :

- Pas de réécriture LLM générative du prompt (Qwen) — abandonné, mesuré sans valeur.
- Pas d'apprentissage de la pertinence/quality-note : **aucune vérité terrain** → piège, exclu.
- Pas de refonte de E1/E2/E3 : la Policy se branche **après** l'optimiseur existant.

## 3. Design — la nouvelle pipeline

### Chemin en ligne (requête)

```
prompt ─► OPTIMISEUR (existant : E1·E2·E3)
       ─► FEATURE EXTRACTOR (embedding nomic-embed + features structurels)
       ─► POLICY ENGINE :
            ① Gating model     → P(compression sûre)
            ② Routing model    → tier modèle (cheap/cher)
            ③ Output regressor → tokens de sortie prédits
            ④ Combiner         → minimise coût prédit SOUS contrainte
                                  non-dégradation ≥ seuil ; FALLBACK heuristique si confiance basse
       ─► PLAN {compress, palier, modèle}
       ─► chat_service.call_llm() ─► réponse
       ─► OUTCOME LOG (tokens réels, coût) ─► ré-entraînement
```

### Chemin hors-ligne (production des labels)

```
corpus prompts ─► run baseline + variantes (modèle cible local)
              ─► JUGE LLM (Nemotron / qwen2.5:14b) ─► dataset labellisé
              ─► entraîne ①②③ ─► sérialise (.joblib) ─► chargé au démarrage
```

### Composants (unités isolées, un rôle chacune)

| Unité | Rôle | Entrée → Sortie | Dépend de |
|---|---|---|---|
| **Feature Extractor** | vectoriser un prompt | prompt → vecteur (embed + structurels) | nomic-embed (Ollama) |
| **Gating model** ① | comprimer sans risque ? | features → P(sûr) ∈ [0,1] | label juge A-vs-B |
| **Routing model** ② | quel tier modèle | features → tier | label juge cheap-vs-cher |
| **Output regressor** ③ | longueur de réponse | features+palier → tokens | label `eval_count` (mesuré, propre) |
| **Policy Combiner** ④ | décider le plan | sorties ①②③ → plan + fallback | seuil de non-dégradation |
| **Labeling pipeline** | produire les labels | corpus → dataset | juge LLM (réutilise `analysis/qm/qm_*`) |
| **Outcome log** | tracer pour ré-entraîner | exécution → ligne dataset | DB existante |

**Principe directeur** : la Policy **surclasse** les heuristiques quand elle est confiante et **retombe dessus
sinon** (cold-start, hors-distribution). Le système marche dès J0 (dégradé), et l'heuristique reste le
**baseline à battre** = le before/after de la démo.

## 4. Priorisation par valeur (incréments)

1. **Labeling pipeline + Output regressor** — label propre (`eval_count`), zéro dépendance au juge bruité. Fondation.
2. **Gating model + Combiner + intégration** (fallback heuristique) — la valeur prouvée (−32 % sur sous-ensemble sûr, dégradation 45 %→<10 %). Cœur démontrable.
3. **Routing model** — extension forte (RouteLLM-like), demande l'infra 2-tiers.
4. **Dashboard frontière coût/qualité** (heuristique vs ML) — livrable visuel.

## 5. Labels & données

- **Output regressor** : label = `eval_count` mesuré. Propre, abondant.
- **Gating** : label = verdict juge A (libre) vs B (palier). **Bruité** (accord inter-juges 64 %).
  Mitigation : entraîner sur labels haute-confiance (2 juges d'accord), labelliser final au juge fort (Nemotron).
- **Routing** : label = la réponse du tier cheap vaut-elle celle du cher (juge). Demande inférence 2-tiers.
- **Corpus** : partir des 458 prompts QM (`analysis/qm/input_delta_QM.json`), étendre vers la distribution d'usage réel.

## 6. Risques & mitigations (baked-in)

| Risque | Mitigation |
|---|---|
| Labels bruités (juge 64 % accord) | labels haute-confiance + seuil Combiner conservateur (biais anti-dégradation) + juge Nemotron |
| Cold-start (modèle non entraîné) | fallback heuristique obligatoire, jamais de trou |
| Le juge est l'oracle (borne la qualité) | labeling = composant first-class, juge le plus fort dispo |
| Dérive de distribution | outcome log + ré-entraînement ; corpus représentatif de l'usage |
| Sur-ingénierie | incréments stricts : ③ puis ①④ puis ② ; chaque incrément livre une valeur isolée |

## 7. Vérification / critères de succès

- **Output regressor** : MAE tokens prédits vs réels < heuristique actuelle (`_estimate_output_tokens`).
- **Gating** : sur un hold-out, le sous-ensemble "compresser" garde le gain coût (≈ −30 %) **et** non-dégradation > 90 % (vs ~55 % en compression aveugle).
- **Routing** : coût ↓ à non-dégradation iso vs router heuristique.
- **Bout-en-bout** : frontière coût/qualité de la Policy domine celle de l'heuristique (dashboard before/after).

## 8. Passerelle Kirha

Kirha (context graph) décide *quel contexte* injecter ; Helios devient la **couche de policy** qui décide
*combien dépenser* pour répondre dessus, sans dégrader. Même nature : du ML pilotant une décision mesurable
au-dessus d'un graphe de contexte.

## 9. Questions ouvertes

- Juge de référence pour la labellisation finale : Nemotron (clé build.nvidia.com à obtenir) vs qwen2.5:14b local.
- Modèle "cher" de référence pour le routing (incrément 3) : API distante vs gros modèle local.
- Format de sérialisation/chargement des modèles dans le backend FastAPI (joblib au démarrage).
