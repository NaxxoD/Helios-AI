# Spec — Sous-agent mémoire (Helios)

**Date** : 2026-06-18
**Statut** : architecture figée, validée (cf `cadrage-poc-helios.md` + `synthese-compression-helios.md`). À implémenter.
**Type** : **sous-agent** (worker contraint), pas un agent autonome — voir §8.

---

## 1. Objet

Sur une conversation multi-tours, le LLM (sans mémoire) **relit tout l'historique à chaque tour** — cette relecture redondante (« Couche B ») devient **~95% du coût** d'une session longue. Le sous-agent mémoire **résume ce vieil historique** et le ré-injecte à la place du brut, pour que l'agent principal continue **sans rien perdre**.

Il n'agit **que sur la Couche B** (la relecture) — ni sur le message de l'utilisateur (Couche A), ni sur la réponse (Output).

---

## 2. Architecture & flux

Trois rôles, **deux fenêtres distinctes** :

```
Utilisateur
    │  (message du tour)
    ▼
┌─────────────── PROXY HELIOS (orchestrateur) ────────────────┐
│  tient l'état : { summary, recent[], history[] }            │
│                                                             │
│   si déclenchement → appelle le SOUS-AGENT MÉMOIRE          │
│        (modèle léger, SA PROPRE fenêtre)                    │
│        in  = résumé précédent + tours à plier               │
│        out = nouveau résumé                                 │
│        → passe par la GRILLE (gate de fidélité)             │
│                                                             │
│   construit le contexte de l'AGENT PRINCIPAL :              │
│        [système] + [résumé] + [recent verbatim] + [message] │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
                   AGENT PRINCIPAL (LLM premium)
                   ne voit JAMAIS le vieux brut → sa fenêtre est dégonflée
                          │
                          ▼
                       Réponse
```

Le sous-agent **dégonfle** la fenêtre de l'agent principal, il ne l'élargit pas. Il tourne dans **sa propre fenêtre** (appel séparé), sur un **modèle pas cher / local**.

---

## 3. Le system prompt du sous-agent

```
# SOUS-AGENT MÉMOIRE — Helios

## Tâche
Tu es le sous-agent MÉMOIRE. On te fournit le DÉBUT d'une conversation (tours anciens).
Produis un RÉSUMÉ STRUCTURÉ qui REMPLACERA ce passé brut dans le contexte de l'agent
principal — un LLM qui n'a JAMAIS vu le brut. But : qu'il continue sans rien perdre.

## Entrée
Ton seul matériau = l'historique brut fourni. Aucun fichier, aucun outil, aucun web.

## Format de sortie (sections ; omets celles qui sont vides ; puces courtes, un fait par ligne)
- Objectif / fil courant       — où on en est, ce qu'on cherche
- Parcours / chronologie        — la SÉQUENCE des événements et les blocages RÉSOLUS
                                  (ex : « X bloquait → corrigé par Y → débloqué »)
- Décisions & faits actés       — ce sur quoi l'utilisateur construit
- Entités / chiffres / fichiers — tout ce qui sera rappelé plus tard
- Questions ouvertes            — ce qui n'est pas résolu

## Scope (compresser SANS perte — la fidélité prime sur le taux)
Jette : politesses, ré-explications, tangentes mortes, verbosité, style.
Ne jette JAMAIS : une décision, un chiffre, une entité, une question ouverte,
un blocage et sa résolution, l'ordre des événements.
Doute sur l'importance d'un élément → GARDE-le.
Plafond ~85% de réduction : si tu l'atteins, c'est que tu as gardé l'essentiel —
n'aspire PAS à compresser plus. Sur un historique dense, comprime MOINS.

## Fidélité (tu transmets, tu ne crées pas)
Chaque élément doit être présent dans le brut. N'invente rien, ne déduis rien qui n'y
est pas, ne reformule pas un fait au point de le changer.

## Sortie
UNIQUEMENT le résumé structuré. Pas de préambule, pas de méta. Auto-suffisant : tout
terme doit être clair pour qui n'a pas vu le brut.
```

---

## 4. Déclenchement (trigger)

- **Principal** : quand l'historique réinjecté (Couche B) dépasse un **seuil de tokens** (≈ **8 000 tk**) **ET** qu'il y a plus de `KEEP` tours à plier.
- **Secondaire (UX)** : à l'approche du **mur de quota** de l'abonnement — compacter *avant* de taper la limite (avec alerte possible : « 80% de ta fenêtre utile »).
- **Par BATCH, jamais à chaque tour.** Compacter par lot garde le coût du sous-agent minimal (~14k tk / session, ~5 compactions — cf §7).

---

## 5. Fenêtre verbatim & ré-injection

- **`KEEP`** = derniers **4 à 6 tours gardés VERBATIM** (2-3 échanges récents, pleine fidélité). Paramètre à affiner.
- Au-delà de `KEEP` → plié dans le résumé.
- **Pourquoi verbatim ≠ que du coût (fidélité d'état)** : si un *changement d'état récent* (ex : un blocage qu'on vient de résoudre) tombe dans le résumé, le rédacteur peut **figer l'ancien état** → affirmation FAUSSE. Observé en vrai sur Foxy : le résumé disait « accès bloqué » alors qu'il était résolu après la relance. Garder le récent verbatim **préserve l'état courant** — la fenêtre verbatim est un levier de **fidélité**, pas seulement de coût.
- **Ré-injection** (contexte de l'agent principal, chaque tour) :
  ```
  [système] + [résumé structuré] + [KEEP derniers tours verbatim] + [message courant]
  ```
- **Résumé incrémental** : le sous-agent lit `[résumé précédent + tours à plier]` (pas tout le brut à chaque fois) → coût borné.

### Pseudo-code de l'orchestrateur

```
état = { summary: "", recent: [], }
à chaque tour utilisateur:
    recent.append(message_user)
    si tokens(historique_replié) > SEUIL et len(recent) > KEEP:
        à_plier   = recent[:-KEEP]
        candidat  = sous_agent_mémoire(summary + à_plier)     # appel modèle léger
        si grille_ok(candidat, summary + à_plier):            # gate de fidélité (§6)
            summary = candidat
            recent  = recent[-KEEP:]
        sinon:
            # rollback : on NE compacte pas ce tour (garde verbatim),
            # ou on re-résume avec moins de compression
            pass
    contexte = [système] + [summary] + recent + [message_user]
    réponse  = agent_principal(contexte)
```

---

## 6. Le gate de fidélité (la grille)

Le sous-agent peut perdre une info → la **grille vérifie son résumé** avant de l'accepter. C'est le bloc *Evidence* externalisé.

- **Couche 1 (déterministe, gratuit)** : le résumé n'est pas vide, couvre tous les tours, garde les entités/chiffres détectés, pas tronqué.
- **Couche 2 (juge)** : non-régression *« résumé vs historique brut »* (Profil B / barème) — le résumé perd-il une décision / un fait / une entité / une question ouverte ?
- **Verdict `perte_grave` → rollback** : ne pas accepter le résumé ; garder plus de verbatim, ou re-résumer moins agressivement.

→ La **qualité shippée reste ~100%** (le résidu est rattrapé), même si le sous-agent rate ~1 résumé sur 8.

### Gate de cohérence d'état — MESURÉ (Palier État, 2026-06-18)

Le gate « cohérence d'état » (proposé par co-auteur, msg15 : *« une affirmation du résumé contredit-elle l'état FINAL du brut ? »*) a été **mesuré hors-ligne** sur 120 vraies convs comparia (16 contradictions d'état injectées en labels contrôlés, `analysis/qm/palierE_state_gate.py`) :

| Juge du gate | Rappel (contradictions attrapées) | Faux positifs |
|---|---|---|
| Haiku (abordable) | **0%** (0/16) | 4% |
| Sonnet (premium, mêmes cas) | **25%** (4/16) | 4% |

**Conclusion : un gate d'état basé sur un JUGE LLM est peu fiable** — un juge abordable n'attrape rien, un premium 1 cas sur 4. → réponse **négative** à l'inconnue n°1 d'co-auteur, et on **ne câble PAS** un juge d'état sur le chemin de requête (coût/latence pour ~0 bénéfice). *(Caveat : corruption synthétique = proxy ; le prompt du juge pourrait être affiné — non retenu pour l'instant.)*

→ **La fenêtre verbatim (`KEEP`) est donc la protection PRIMAIRE de la fidélité d'état**, pas le gate-juge : garder le récent brut empêche un changement d'état récent d'être figé, sans dépendre d'un juge. Le gate de fidélité (Couche 1 déterministe + Couche 2 couverture) reste utile pour la **perte d'info** ; la **contradiction d'état**, elle, se prévient en amont (verbatim) plutôt que se rattrape en aval (juge). Une approche déterministe (le résumeur sort un « état final » structuré, vérifié mécaniquement) reste une piste ouverte.

---

## 7. Paramètres mesurés (les chiffres du jour)

| Paramètre | Valeur mesurée | Source |
|---|---|---|
| Compression du vieil historique | **~88%** (résumé ≈ 12% du brut) | b2 + Palier 2 |
| **Garde-fou** | couper **≤ ~85-90%**, **pas au-delà** (96% casse) | b2 + Palier 2 |
| Fidélité du résumé (corpus réel) | **90% (Opus) / 96% (Sonnet)** | Palier 2 (50 convs) |
| Résidu à rattraper par la grille | **~12%** pertes graves (≥1 juge) | Palier 2 |
| Modèle rédacteur | **Haiku** (cloud) ou **qwen2.5:7b-instruct** (local, gratuit) | b2 + test Foxy |
| Coût du sous-agent | ~14k tk / session 34 tours, **5 compactions** | net I/O |
| **Économie nette** (sous-agent inclus) | **−43% (Haiku) à −46% (local)** | net I/O |
| Validité par longueur | **~52% sur sessions 10+ tours**, ~0% sur le typique | Palier 1 (39k convs) |

**Portée honnête** : valeur sur les **sessions longues / interactives** (10+ tours), négligeable en one-shot. Ça cible le marché (usages répétés), ça ne sur-promet pas l'universel.

**Validation hors corpus (inter-instance, Foxy/Tour).** Le garde-fou « 96% casse » s'est **reproduit** sur `first_memory.md` (qwen local, hors comparia) → la borne tient au-delà du corpus de test. Rédacteur local retenu : **qwen2.5:7b-instruct** (le 3b *hallucine l'absence d'info* ; qwen3:8b = surcoût *thinking* inutile pour de l'extraction). ⚠️ Surtout : le résumé NU (prompt seul, sans fenêtre verbatim ni gate) a produit une **affirmation fausse** (état figé sur « bloqué » alors que résolu) → preuve par l'échec que le **package complet (résumé + verbatim + gate) est nécessaire**, pas le prompt seul.

---

## 8. Ce que ce sous-agent N'EST PAS (la distinction archi)

C'est un **sous-agent** (worker contraint), **pas un agent autonome**. Conséquence sur les blocs du template d'agent :

| Bloc | Agent autonome | Sous-agent mémoire |
|---|---|---|
| Task / Entrée / Schéma / Scope / Fidélité | ✅ | ✅ (le contrat) |
| **Delegate** | ✅ | ❌ une feuille ne délègue pas |
| **Checkpoint** | ✅ pause pour l'humain | ❌ tourne une fois, rend |
| **Memory (tient des notes)** | ✅ | ❌ il **est** la mémoire (son output = la note) |
| **Effort ouvert / Act autonome** | ✅ | ⚠️ borné, sortie directe |

On veut ici **fidélité + prévisibilité**, *pas* d'autonomie. Un agent autonome qui résume pourrait « explorer » → risque sur la fidélité. Le contraindre **est** la sécurité. (C'est ton « Mémorien », mais en sous-agent feuille orchestré par le proxy, pas un agent pair.)

---

## 9. Reste à implémenter / mesurer

### État d'implémentation & validation live (2026-06-18)

Implémenté : orchestrateur (`services/orchestrator_service.apply_memory`), état P1/Pn via `HeliosCall.context`, grille Couche 1 branchée comme gate, rollback. Flag `/chat/send memory=false` par défaut.

**Validé en live (smoke réel + Palier Continuation n=40, `analysis/qm/{run_live_smoke,palier_continuation}.py`) :**
- ✅ **Le fail-safe fonctionne en réel** : un résumé invalide → gate Couche 1 → rollback → historique intact (qualité préservée).
- ⚠️ **Mode d'échec mesuré : le résumeur CONTINUE la conversation ~18%** du temps au lieu de résumer (67% quand le fold finit sur un tour user — rare ; 14% sur assistant). → **hit-rate de compaction ~82%** ; le −52% (sessions longues) s'applique aux compactions **réussies**.
- Le fix de bord (« le fold ne finit pas sur un tour user ») est **marginal** (−3 pts) → non retenu seul.
- **Travail restant ciblé** : durcir le résumeur (cadrage + détecteur déterministe de continuation dans le gate pour un rollback fiable, pas par coïncidence). `summarizer_input()` (consigne « résume, ne continue pas ») est nécessaire mais insuffisant seul.
- Gate de **cohérence d'état** : mesuré faible (Palier État, voir §6) → fenêtre verbatim = protection primaire.

### Reste

- Implémenter l'orchestrateur (§5) dans le proxy (état session, déclenchement, ré-injection).
- Brancher la grille existante (`quality_gates.py` + `judge_service.py`) comme gate (§6).
- **Run live de bout en bout** (le POC actuel est de la simulation sur sorties loguées).
- Mesurer la **fiabilité live de la grille** (sa précision/rappel à rattraper le résidu).
- Affiner `KEEP`, `SEUIL`, le taux de compression cible (~85%).
- Élargir Palier 2 si chiffre plus serré voulu (n=200 ≈ 24$ → IC ±4 pts).

*Référence chiffres : `cadrage-poc-helios.md`, `synthese-compression-helios.md`. Scripts : `analysis/qm/{test_memoire_session,lock_memoire_session,palier1_session_corpus,palier2_fidelite_corpus}.py`.*
