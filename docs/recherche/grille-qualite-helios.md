# Grille de qualité de réponse — Helios

**Objet** : définir, de façon opérationnelle et défendable, comment Helios mesure qu'une réponse optimisée (courte / cheap / restructurée) **n'a pas dégradé** la qualité par rapport à une réponse de référence.
**Double usage** : (1) méthodologie de mesure pour le pitch / la soutenance ; (2) spécification d'implémentation (`escalation.py` + service juge).
**Date** : 2026-06-16

---

## 0. Principe directeur

Helios ne note pas une réponse « dans l'absolu » (sur 20). Il tranche une **non-régression différentielle** :

> *La réponse candidate (optimisée) vaut-elle au moins la réponse de référence (baseline) ?*

Conséquence : une réponse médiocre qui **reste** médiocre après optimisation = **succès** (on n'a rien perdu). On ne juge pas « est-ce excellent », on juge « a-t-on perdu quelque chose ».

La grille a **2 couches** et un **verdict ternaire**. Certaines dimensions sont **éliminatoires** (veto), les autres sont des points. **Jamais** de simple moyenne : une réponse fausse mais élégante doit échouer.

---

## 1. Le verdict (la sortie de la grille)

| Verdict | Sens | Action |
|---|---|---|
| ✅ **ÉQUIVALENT** | Aucune perte mesurable vs référence | Garder la réponse cheap |
| ⚠️ **DÉGRADÉ TOLÉRABLE** | Perte mineure (ex : un point secondaire omis) | Garder + flag (suivi qualité) |
| ❌ **DÉGRADÉ INACCEPTABLE** | Perte de sens, erreur, ou échec mécanique | **Escalade** vers le modèle premium |

L'échelle est ternaire **parce que l'action est ternaire**. Inutile d'une note sur 10 quand la décision est garder / garder-en-surveillant / escalader.

---

## 2. Deux modes d'usage (distinction critique)

La grille tourne dans deux contextes qui n'ont **pas** les mêmes moyens :

| | **Mode ÉVALUATION (offline)** | **Mode PRODUCTION (live)** |
|---|---|---|
| Référence disponible ? | OUI (on a calculé baseline + optimisée) | NON (on n'a appelé que le cheap) |
| Couche 1 mécanique | ✅ | ✅ (temps réel, 0 coût) |
| Couche 2 juge **comparatif** | ✅ (fiable) | ❌ impossible (pas de référence) |
| Couche 2 juge **sans référence** | inutile | optionnel (plus bruité, coûte un appel) |
| Sert à… | mesurer le % de non-dégradation, **produire les labels**, calibrer | décider l'escalade en direct |

**Le pont entre les deux** : le mode évaluation produit des **labels propres** (« sur ce type de prompt, le cheap suffit / ne suffit pas »). Le **gating** apprend à prédire ce verdict *à partir du prompt seul*, pour qu'en production on décide **sans** avoir besoin de la référence. → C'est précisément pourquoi la **qualité des labels** (donc de cette grille) est le verrou de tout le projet.

---

## 3. Couche 1 — Gates mécaniques (déterministe, 0 juge, 0 bruit)

Chaque gate est un **pass/fail calculable sans LLM**. Un seul échec « dur » → ❌ escalade immédiate, sans déranger un juge. Fiabilité = parfaite (κ = 1 par construction).

| Gate | Mesure | Seuil d'échec | Type |
|---|---|---|---|
| **Vide** | `len(contenu.strip())` | < 10 caractères | dur |
| **Erreur** | exception / timeout / HTTP non-2xx | présence | dur |
| **Refus** | regex de refus **dans les 120 premiers car.** ET réponse totale < 250 car. ET tâche bénigne | match | dur |
| **Troncature** | `finish_reason == "length"` **ou** `output_tokens ≥ 0,95 × max_tokens` | vrai | dur |
| **Répétition dégénérée** | `unigrammes_uniques / total` (réponses ≥ 40 mots) ; robuste : `distinct-2` | ratio < 0,55 (ou distinct-2 < 0,30) | dur |
| **Langue** | détection (langdetect/fasttext), confiance > 0,8 | langue ≠ langue attendue | dur |
| **Format** | parsing du format demandé (JSON, etc.) | parsing échoue | dur (si format requis) |
| **Longueur / palier** | nb mots vs cible du palier | > 1,3 × cible | ⚠️ flag (pas escalade) |

**Notes anti-faux-positifs :**
- *Refus* : ne déclencher que sur un refus **réel et court** en tête de réponse. « je ne peux pas **garantir** que… » n'est PAS un refus. Patterns FR : `je ne peux pas`, `je ne suis pas en mesure`, `en tant qu'IA`, `je n'ai pas accès`. EN : `I can't help`, `I'm unable to`, `as an AI`.
- *Répétition* : ratio instable sur les réponses très courtes → ne l'appliquer qu'au-delà de ~40 mots.
- *Longueur/palier* : dépasser la cible = consigne non respectée → information, pas forcément dégradation de fond. Reste un flag.

> À elle seule, la Couche 1 capture la majorité des **vrais** échecs (vide, plantage, boucle, troncature, hors-sujet de langue) à **coût et bruit nuls**. C'est le cœur du cheap-first mécanique.

---

## 4. Couche 2 — Jugement sémantique comparatif (juge ancré)

Ne tourne **que** si la Couche 1 passe, et **uniquement en mode évaluation** (référence disponible). Le juge compare **candidate vs référence**, **dimension par dimension** (pas de « note globale » fourre-tout, qui est la principale source de bruit).

### 4.0 Deux profils de jugement (correctif)

« Référence » est ambigu, et appliquer la grille à un vrai cas (restructuration de prompt) l'a révélé : comparer la candidate à la **réponse** baseline ne pénalise que les **omissions** et ne crédite **jamais** les ajouts. C'est juste pour la **compression**, mais faux pour la **restructuration** (où la réponse change de forme et peut s'améliorer). D'où deux profils, choisis selon ce qu'on optimise :

| Profil | « Référence » = | Quand l'utiliser | Logique |
|---|---|---|---|
| **A — Non-régression** | la **réponse** baseline | palier / compression (la réponse optimisée est une version *raccourcie* de la même) | toute omission de fond = dégradation |
| **B — Conformité à la tâche** | un **barème** (checklist du « ce qu'une bonne réponse doit contenir ») | restructuration / changement de modèle (la réponse change de forme) | on note chaque réponse **contre le barème** ; les ajouts utiles comptent, la candidate peut **dépasser** la baseline |

**Règle :** la complétude se juge contre **ce que la tâche exige**, pas contre ce que la baseline contenait *par hasard*. Laisser tomber du remplissage présent dans la baseline = bonne compression (non pénalisé). Ajouter un élément exigé que la baseline avait raté = crédité.

En **profil B**, la réponse baseline reste un simple **plancher de substance** (a-t-on perdu en exactitude / en sens ?), **pas** un gabarit de couverture.

### Dimensions jugées

| Dimension | Question posée au juge | Échelle |
|---|---|---|
| **Exactitude** | La candidate introduit-elle une **erreur factuelle absente** de la référence ? | bool (veto) |
| **Complétude** | Omet-elle un élément **important** présent dans la référence ? | complète / partielle / insuffisante |
| **Pertinence** | Répond-elle bien à la **question posée** ? | bool |
| **Concision** *(bonus)* | Est-elle **plus concise sans perte** ? (valorise l'optimisation) | bool |

### Template de prompt-juge (à figer)

```
Tu es un évaluateur STRICT de non-régression. On te donne une QUESTION, une
réponse RÉFÉRENCE (la bonne) et une réponse CANDIDATE (à évaluer). Ta seule
tâche : dire si la CANDIDATE perd en qualité par rapport à la RÉFÉRENCE.

Règles :
- Juge dimension par dimension, pas d'impression globale.
- Sois conservateur : en cas de doute, penche vers « dégradé ».
- Ignore le style si le fond est préservé. Une formulation plus courte qui
  garde l'information n'est PAS une dégradation — c'est l'objectif.
- Une erreur factuelle ou un contresens = inacceptable, quel que soit le reste.

QUESTION :
{prompt}

RÉFÉRENCE :
{reponse_reference}

CANDIDATE :
{reponse_candidate}

Réponds UNIQUEMENT en JSON strict :
{
  "exactitude_regression": <true|false>,
  "completude": "complete" | "partielle" | "insuffisante",
  "pertinence": <true|false>,
  "concision_gain": <true|false>,
  "verdict": "equivalent" | "tolerable" | "inacceptable",
  "justification": "<1 à 2 phrases>"
}
```

**Leviers anti-bruit intégrés au prompt** : rubrique explicite + réponse de référence + jugement par dimension + consigne conservatrice + justification demandée (le fait de justifier améliore la fiabilité du juge).

---

## 5. Agrégation → verdict final (arbre de décision)

```
SI un gate Couche 1 échoue (dur)        → ❌ INACCEPTABLE   (escalade)
SINON SI exactitude_regression == true  → ❌ INACCEPTABLE   (escalade)
SINON SI pertinence == false            → ❌ INACCEPTABLE   (escalade)
SINON SI completude == "insuffisante"   → ❌ INACCEPTABLE   (escalade)
SINON SI completude == "partielle"      → ⚠️ TOLÉRABLE      (garder + flag)
SINON                                   → ✅ ÉQUIVALENT     (garder)
```

Le flag « longueur/palier » est orthogonal : il s'ajoute en métadonnée, il ne change pas le verdict de fond.

---

## 6. Calibration par type de tâche

Les critères qui comptent **changent selon la tâche** (même logique que les presets de paramètres). La grille est **conditionnelle** :

| Tâche | Gates en + | Veto exactitude | Dimension dominante |
|---|---|---|---|
| **Extraction** | format (JSON valide) | OUI (strict) | exactitude + format |
| **Factuel / Q&R** | — | OUI | exactitude + complétude |
| **Code** | format (bloc), idéalement « ça compile/teste » | OUI (fonctionnelle) | exactitude fonctionnelle |
| **Rédaction** | longueur / palier | assoupli | complétude + cohérence |
| **Créatif** | — | **sans objet** | cohérence + ton |

---

## 7. Fiabilité de la grille elle-même (le point qui a tué le gating)

Une grille ne vaut **que** par sa reproductibilité. Le gating Helios a plafonné (ROC-AUC 0,59) parce que les juges locaux étaient en désaccord ~1 fois sur 3 → labels bruités → plafond d'apprentissage.

**Protocole de validation avant de s'en servir comme vérité :**
1. **Double juge** sur un échantillon (n ≥ 100). Mesurer le **kappa de Cohen** :
   - κ < 0,40 : faible → grille mal définie ou tâche ambiguë, **ne pas entraîner dessus**
   - 0,40–0,60 : modéré
   - 0,60–0,80 : substantiel (cible minimale)
   - > 0,80 : excellent
2. Ne garder comme **labels d'entraînement** que les items où les juges **sont d'accord** (ou ajouter un 3ᵉ juge arbitre).
3. La **Couche 1** a κ = 1 (déterministe) → toujours fiable.

**Pour franchir le plafond** (quand le juge LLM ne suffit pas) :
- soit un **juge fondamentalement meilleur** (GPT/Claude premium en juge) ;
- soit un **signal qui ne dépend pas d'un juge LLM** : 👍/👎 utilisateur, taux de ré-édition du prompt, temps de relecture, clic. → *« si les profs sont en désaccord, fais voter les élèves. »*

---

## 8. Exemple travaillé

**Question** : « Explique en quelques lignes la différence entre le RGPD et la directive ePrivacy. »

**Référence (baseline, ~140 mots)** : définit les deux, précise que le RGPD est un règlement général sur les données personnelles, ePrivacy une directive sectorielle (communications électroniques, cookies), et que ePrivacy est *lex specialis* par rapport au RGPD.

**Candidate (cheap, palier court, ~45 mots)** : définit correctement les deux et le périmètre, **mais** omet la nuance *lex specialis*.

**Passage dans la grille :**
- Couche 1 : vide ❌→ok, erreur ❌→ok, refus ❌→ok, troncature ❌→ok, répétition ok, langue FR ok, longueur dans la cible ✅ → **passe**.
- Couche 2 : `exactitude_regression=false`, `pertinence=true`, `completude="partielle"` (la nuance manque mais l'essentiel est là), `concision_gain=true`.
- Arbre → **⚠️ DÉGRADÉ TOLÉRABLE** → on garde la réponse cheap et on la flague.

Interprétation : pour ce prompt, le cheap suffit → label « palier sûr ». C'est ce type de label, agrégé sur le corpus, qui alimente le gating et le chiffre de non-dégradation du pitch.

---

## 9. Mapping implémentation

| Couche | Où | Forme |
|---|---|---|
| Couche 1 (gates) | `backend/utils/escalation.py` → `needs_escalation(result) -> (bool, reason)` | fonctions pures déterministes, une par gate |
| Couche 2 (juge) | `backend/services/judge_service.py` (nouveau) → appelle un LLM juge avec le template §4 | mode évaluation surtout ; optionnel en prod |
| Agrégation | router `/send` (live → Couche 1) ; script d'éval (offline → Couches 1+2) | arbre §5 |
| Labels → gating | `analysis/ml/gating_dataset.csv` | verdict offline = label |

**Formulation pitch défendable :**
> « Notre non-dégradation n'est pas une impression : elle est mesurée par une grille à deux couches. La première est **déterministe** (fiabilité parfaite) et capture les échecs durs. La seconde est un **juge ancré et comparatif**, dont nous **mesurons l'accord inter-juges** (kappa) — donc nous savons quand notre propre mesure est fiable, et quand elle ne l'est pas. C'est cette honnêteté méthodologique qui rend le chiffre crédible. »

---

> **Correctif 2026-06-16** : ajout des deux profils de jugement (§4.0) après application de la grille à une paire restructurée (Test4a/4b). Le profil unique « non-régression vs réponse baseline » sous-créditait les réponses restructurées améliorées (elles ressortaient « tolérable » alors qu'elles étaient supérieures). Le profil B (conformité à un barème de tâche) corrige ce biais.

*Rédigé pour servir de méthodologie de mesure et de spec d'implémentation. À versionner avec les autres docs de référence Helios.*
