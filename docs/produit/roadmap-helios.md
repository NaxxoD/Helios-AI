# Helios — Roadmap (post-audit adversarial)

**Date** : 2026-06-18
**Méthode** : audit multi-agent adversarial du backend (6 dimensions × review + réfutation par relecture du code réel). **28 findings confirmés / 29 examinés (1 réfuté)**. Déduplication → ~21 problèmes réels.
**Discipline** (exigée) : pour chaque correction → test rouge (repro) AVANT le fix → fix → test vert → suite complète verte → re-vérification ciblée. Critique/faille = double passe adversariale.

> Référence de l'audit : `analysis/qm/` (workflow). Le `nb_turns=1` de `/chat/send` a été examiné et **réfuté comme bug** : c'est by-design (SimulationSession = métrique par appel ; la vraie unité conversationnelle est `Conversation` via `/conversations/save`).

---

## 0. Tableau de bord des findings confirmés

| # | Sévérité | Cat. | Problème | Fichier |
|---|---|---|---|---|
| 1 | 🔴 **critique** | bug | Google : `thinkingBudget` peut dépasser `maxOutputTokens` (palier bas) → réponse vide → **502** | `services/chat_service.py` `_google` |
| 2 | 🟠 majeur | bug | OpenAI o-series : `max_tokens`+`temperature≠1` envoyés → **400 systématique** | `chat_service.py` `_openai` |
| 3 | 🟠 majeur | bug | Accès index non gardés (OpenAI/Google) → **502** sur réponse vide/filtrée/tronquée | `chat_service.py` `_openai`/`_google` |
| 4 | 🟠 majeur | **faille** | Token de vérification email **loggé en clair** (WARNING, actif en prod) → prise de contrôle compte via accès logs | `routers/auth.py` |
| 5 | 🟠 majeur | dette | `call_llm` + 3 branches provider **sans aucun test** (cœur du chat, sémantique tokens) | `chat_service.py` + `tests/` |
| 6 | 🟡 mineur | bug | `thinking_tokens` Anthropic = `cache_creation_input_tokens` (faux label, ≈0) | `chat_service.py` `_anthropic` |
| 7 | 🟡 mineur | incoh. | 2 tables palier divergentes → le « coût max » affiché **sous-estime** (~−20%) | `optimiseur.py` + `chat_service.py` |
| 8 | 🟡 mineur | incoh. | Vocab effort : `on` documenté mais absent de `_EFFORT_MAP` (thinking désactivé en silence) ; `standard` jamais produit | `routing.py`+`chat_service.py`+`chat.py` |
| 9 | 🟡 mineur | écart | `/chat/compact` réécrit tout en **502**, masque 401/429 | `routers/chat.py` |
| 10 | 🟡 mineur | dette | Extraction bloc ` ```json ` fragile (cassant sur sortie tronquée) | `qwen_optimizer.py` |
| 11 | 🟡 mineur | **faille** | `/api/optimise` **sans auth** (Qwen + écriture `noise_candidates` anonyme) | `routers/optimiseur.py` |
| 12 | 🟡 mineur | err. code | `get_optional_user` : `except (ValueError, Exception)` avale tout en silence | `dependencies.py` |
| 13 | 🟡 mineur | bug | `is_truncated()` crashe si tokens en `str` (chemin `needs_escalation`, pas encore live) | `quality_gates.py` |
| 14 | 🟡 mineur | bug | `score_bareme()` / `judge_profil_b` : `KeyError` sur barème sans `id` | `judge_service.py` |
| 15 | 🟡 mineur | incoh. | 2× `calculate_impact` homonymes ; celui de `parsers` est **mort** + schéma incompatible | `parsers.py` vs `calculator.py` |
| 16 | 🟡 mineur | incoh. | Économies affichées sur tokens **heuristiques**, jamais réconciliées au réel facturé | `routers/optimiseur.py` |
| 17 | 🟡 mineur | incoh. | `tokens_estimated` = proxy énergie pondéré (`output×5`) stocké comme un compteur de tokens | `chat.py`+`session_service.py` |
| 18 | 🟡 mineur | dette | `numpy` importé top-level mais absent de `requirements.txt` (transitif via sklearn) | `requirements.txt` |
| 19-21 | 🟡 mineur | dette | `routing`, `qwen_optimizer`, services auth/session/admin/stats + `cost_calculator` **non testés** | `tests/` |
| 22 | ⚪ info | incoh. | effort `max` = `xhigh` côté Google (limite Gemini), non documenté | `chat_service.py` |
| 23 | ⚪ info | incoh. | GPT-5.x absents de `_OPENAI_REASONING_MODELS` → effort ignoré (modèles prospectifs) | `chat_service.py` |
| 24 | ⚪ info | dette | `predict_safe` fallback index 1 aveugle si classe absente | `ml/gating.py` |
| 25 | ⚪ info | dette | `_post_with_retry` : `raise last_exc` final inatteignable (code mort) | `judge_service.py` |

---

## Jalon 0 — Stabilisation : tuer les bugs & failles (BLOQUANT)

**But** : zéro crash dur, zéro faille de sécurité, sur le chemin de requête. Couvrir chaque fix par un test.

| Étape | Fix | Test / vérification | Done |
|---|---|---|---|
| 0.1 | **#1 Google 502** : `_google` → `max_out_tokens = _max_tokens_from_palier(palier, thinking_budget)` (symétrie avec `_anthropic`) ; garantir `maxOutputTokens ≥ thinkingBudget + ceiling` | Test : palier `★` + effort `high` → body Google a `maxOutputTokens > thinkingBudget` (httpx mocké) | réponse non vide sur palier bas + thinking |
| 0.2 | **#4 Faille logs auth** : supprimer / conditionner `logger.warning(verify_url)` à un mode dev explicite (ex. `if not settings.MAIL_USERNAME`) | Test : en mode prod (MAIL configuré), le token n'apparaît dans aucun log | aucun secret d'auth en clair dans les logs |
| 0.3 | **#3 Accès non gardés** : `_openai`/`_google` → garder `choices`/`candidates` vides, concaténer les `parts`, gérer `finishReason` SAFETY/MAX_TOKENS avec message explicite (≠ 502 opaque) | Test : réponse 200 sans contenu / filtrée → erreur claire, pas un 502 | 200-vide distinct d'une panne API |
| 0.4 | **#2 OpenAI o-series** : si `model in _OPENAI_REASONING_MODELS` → `max_completion_tokens` au lieu de `max_tokens`, omettre/forcer `temperature=1` | Test : body o3 n'a pas `max_tokens` ni `temperature≠1` | o-series ne renvoie plus 400 |
| 0.5 | **#11 Faille `/api/optimise`** : exiger `get_optional_user`, réserver `semantic=True` et `save_candidates=True` aux authentifiés | Test : appel anonyme avec `save_candidates` → 401/refus | pas d'écriture DB ni Qwen anonyme |
| 0.6 | **#5 Tests `call_llm`** : suite httpx mockée (respx/monkeypatch) couvrant body par provider, mapping IDs, effort, extraction tokens | Suite verte couvrant les 3 branches | cœur du chat sous filet de test |

**Vérif de sortie Jalon 0** : suite complète verte + re-passe adversariale sur `chat_service.py` (les fixes #1/#2/#3 touchent le même fichier — vérifier qu'ils ne se contredisent pas).

---

## Jalon 1 — Cohérence & dette (FIABILITÉ)

| Étape | Fix | Test / vérification |
|---|---|---|
| 1.1 | **#6 `thinking_tokens`** : retourner `0` pour Anthropic (non exposé par l'API) ou exposer `cache_creation/read` sous leur vrai nom | test sémantique du champ |
| 1.2 | **#7 Tables palier** : source unique (`utils/paliers.py`) OU calculer le « coût max » affiché à partir de `_PALIER_MAX_TOKENS` (vrai plafond) / renommer en « coût estimé » | test croisé des 2 ex-tables |
| 1.3 | **#8 Vocab effort** : aligner les 3 sources, valider l'effort entrant, `log.warning` si inconnu (ne plus désactiver thinking en silence) | test : effort `on`/inconnu → warning + comportement défini |
| 1.4 | **#9 `/compact` statuts** : `except HTTPException: raise` avant `except Exception` | test : 401 upstream → 401 client (pas 502) |
| 1.5 | **#12 `get_optional_user`** : `except ValueError` seul + log sur le reste | test : erreur DB ne dégrade plus silencieusement en invité |
| 1.6 | **#15 `calculate_impact` mort** : supprimer/renommer la version `parsers` | suite verte, aucun import cassé |
| 1.7 | **#13 `is_truncated`** + **#14 `score_bareme`** : cast `float`/`try` + `e.get('id')` (et f-string l.312) | tests de repro (str tokens, barème sans id) |
| 1.8 | **#10 strip ` ```json `** : regex non-greedy + repli `{`…`}` | test sur sorties tronquées/malformées |
| 1.9 | **#18 numpy** + **#24/#25 dette ML/retry** : déclarer `numpy` ; `predict_safe`→`None` si classe absente ; retirer le `raise` mort | suite ML verte hors-venv minimal |
| 1.10 | **#19/#20/#21 tests manquants** : `routing`, `qwen_optimizer`, `cost_calculator` (+ test paramétré croisant `_ANTHROPIC_IDS`/`_GOOGLE_IDS` ↔ `PRICING` pour détecter la dérive) | couverture des modules live + facturation |

---

## Jalon 2 — Orchestrateur backend + objet Helios unifié (ÉCART ARCHI)

*Comble l'écart vs le tableau blanc : le flux `optimise → route → adapt` est aujourd'hui en pièces (2 endpoints + le front).*

| Étape | Objectif | Fichiers | Test / vérif | Done |
|---|---|---|---|---|
| 2.1 | **Objet Helios** `{message, effort, role, context}` comme structure unique (Pydantic) — `role`/`context` first-class | nouveau `schemas/helios.py` | tests de (dé)sérialisation | un seul format générique en interne |
| 2.2 | **Mapping centralisé** Helios → provider (réutilise `_EFFORT_MAP`, IDs) ; corrige #16/#17 au passage (réconcilier estimation vs réel, séparer `tokens_bruts` / `weighted_energy`) | `chat_service.py`, `session.py` | test mapping par provider | mapping unique testé |
| 2.3 | **Orchestrateur** `/chat/send` qui chaîne optionnellement optimise → suggest_routing → adapt (la boucle « return select model + Helios variable ») | `routers/chat.py`, `services/` | test e2e mocké du flux complet | flux gauche→droite câblé backend |

---

## Jalon 3 — Couche mémoire de session (P1/Pn) = LE sous-agent mémoire (POC v2 → live)

*La pièce manquante du tableau (« context management, variable & non-variable set », blocs P1 init / Pn itérations) = le sous-agent mémoire validé en simulation. C'est le cœur produit.*

| Étape | Objectif | Test / vérif | Done |
|---|---|---|---|
| 3.1 | **État de session** `{summary, recent[], history[]}` + déclenchement par seuil tokens, par batch (spec `sous-agent-memoire-helios.md`) | tests unitaires de l'orchestrateur (seuil, KEEP, batch) | l'état tient sur N tours |
| 3.2 | **P1/Pn** : poser l'invariable (rôle, contexte) une fois (P1) ; ne ré-injecter que la variable (message) + résumé (Pn) | test : Couche B dégonflée tour après tour | −X% input réel mesuré live |
| 3.3 | **Gate de fidélité** (grille) branché comme garde sur chaque résumé → rollback/verbatim sur `perte_grave` | test : résidu ~12% rattrapé | qualité shippée ~100% |
| 3.4 | **Gate cohérence d'état** (retour du co-auteur) → ✅ **MESURÉ (Palier État, n=120)** : gate-juge peu fiable (Haiku 0% / Sonnet 25%, FP 4%) → inconnue n°1 levée par la négative. **NON câblé live.** | `analysis/qm/palierE_state_gate.py` | **acté** : fenêtre verbatim = protection primaire d'état ; gate-juge écarté |
| 3.5 | **Garde-fou** : plafond ~85-90% de coupe (96% casse), fenêtre verbatim sur le récent | test de non-régression sur garde-fou | borne respectée |

---

## Jalon 4 — Live, mesure de fiabilité & compléments

| Étape | Objectif | Dépend de |
|---|---|---|
| 4.1a | ✅ harness e2e (sans crédits) — câblage memory→orchestrate prouvé | — |
| 4.1b | ✅ **run live réel** + **Palier Continuation (n=40)** : fail-safe OK, mais résumeur *continue* ~18% (hit-rate compaction ~82%) → durcir le résumeur = travail restant ciblé | fait |
| 4.1c | ✅ smoke : a révélé que la Couche 1 (règle des chiffres) rejetait ~100% des résumés fidèles → **bug corrigé** (FP 100%→0%). Rappel non concluant (n=5) ; thème convergent : juges LLM cheap = détecteurs faibles | fait (fix `8a94059`) |
| 4.2 | **Phase 1b restructuration** (sur **Tour**, Ollama/qwen local) : décomposer le `+7%` via l'audit `present`/`inferred` (contexte implicite explicité vs surcoût template) | Tour |
| 4.3 | **Élargir Palier 2 à n=200** (~$24) si IC à resserrer pour la soutenance | optionnel |

---

## Jalon 5 — Soutenance

- Finaliser `soutenance-2-helios.md` (storyboard + escalier honnête + limites assumées + Q&A jury).
- Intégrer : verdict Palier A (heuristique = UX/qualité), gate cohérence d'état comme « travail restant identifié », chiffres Palier 1/2.
- Fichier **Infercom** séparé (angle pro, hors cadrage académique).

---

## Discipline de vérification (transverse — exigée)

1. **Repro d'abord** : pour chaque bug, un test qui échoue AVANT le fix (prouve qu'on corrige le bon problème).
2. **Fix minimal** : la plus petite correction qui rend le test vert.
3. **Suite complète** : `pytest backend/tests/` vert après chaque fix (pas de régression).
4. **Re-vérif ciblée** : relire le fichier touché — les fixes #1/#2/#3 partagent `chat_service.py`, vérifier la cohérence d'ensemble.
5. **Double passe adversariale** sur critique/faille (#1, #4, #11) avant de déclarer « done ».
6. **Commits atomiques** par étape (sans `Co-Authored-By`, push sur demande).

## Ordre recommandé

**Jalon 0 (bloquant) → Jalon 1 → Jalon 2 → Jalon 3 (cœur produit) → Jalon 4 → Jalon 5.**
Jalon 0 d'abord : un 502 dur (Google) et une faille de compte (logs auth) ne doivent pas survivre à la prochaine démo.
