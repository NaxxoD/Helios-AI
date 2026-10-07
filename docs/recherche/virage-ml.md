# Le virage ML — décision et résultats

**Date** : 12 juin 2026
**Auteurs** : les deux auteurs
**Statut** : décision actée, design validé

---

## TL;DR

On a mesuré rigoureusement la valeur de l'optimiseur Helios. Résultat :

- ✅ **Le contrôle de longueur (palier) fait économiser ~32 %** de coût. C'est réel.
- ❌ Mais il **dégrade la qualité de la réponse ~1 fois sur 2** quand on l'applique aveuglément.
- ❌ **La réécriture du prompt par un LLM (Qwen) n'apporte rien** : +1,9 % de coût (du bruit) et elle dégrade aussi.

**Décision** : on arrête la réécriture LLM. On garde le levier de longueur, mais on lui ajoute **un modèle de Machine Learning qui décide *quand* l'appliquer sans dégrader** — au lieu de l'appliquer partout. C'est le « virage ML ».

---

## 1. Ce qu'on cherchait à prouver

Helios promet de réduire le coût et l'empreinte des requêtes IA en optimisant le prompt. Deux affirmations à vérifier :

1. **Économie** : est-ce qu'on consomme vraiment moins de tokens (= moins cher, moins de CO₂) ?
2. **Non-dégradation** : est-ce que la réponse reste au moins aussi bonne ?

Une économie qui casse la réponse n'a aucune valeur. Il fallait mesurer **les deux ensemble**.

## 2. Le protocole (benchmark « QM »)

Pour chaque prompt, on a comparé **3 versions**, toutes envoyées au même modèle cible (Mistral, en local) :

| Version | Ce que c'est |
|---|---|
| **A — sans Helios** | le prompt brut, aucune consigne |
| **B — palier seul** | le prompt brut + la consigne de longueur (« Réponds en X mots max ») |
| **C — Helios complet** | le prompt réécrit par Qwen + la consigne de longueur |

Puis on a mesuré :
- **Le coût réel** : vrais comptes de tokens (entrée + sortie), tarif Haiku ($0.80 / $4.00 par million ; la sortie coûte **5× l'entrée**).
- **La qualité** : un **juge LLM neutre** compare deux réponses et dit laquelle satisfait le mieux la demande, **en ignorant la longueur**. Pour fiabiliser, on a utilisé **deux juges de familles différentes** (llama3.1:8b et qwen2.5:14b) et randomisé l'ordre (anti-biais).

> Échantillon : 45 prompts (smoke test), dont 40 exploitables pour les tokens.

## 3. Les résultats

### 3.1 L'hypothèse de départ : « qwen raccourcit la réponse » — **réfutée**

Le plan initial reposait sur cette chaîne :

```
prompt brut
   │
   ▼
[qwen3:8b]  ← optimiseur sémantique
   ├── prompt_raw  (non optimisé)
   └── prompt_qwen (restructuré)
         │
         ▼
   [mistral]  ← LLM cible, mesure les tokens de sortie
         ├── output_tokens_raw
         └── output_tokens_qwen
               │
               ▼
   delta = (raw − qwen) / raw × 100
```

L'idée : si qwen restructure mieux, la réponse devrait être **plus courte** → `delta` **positif**.

On l'a mesuré (39 prompts exploitables, **sans palier**, sortie uniquement) :

| Mesure | Delta |
|---|---|
| delta moyen (moyenne des ratios par prompt) | **−38,4 %** |
| delta pondéré tokens ((Σraw − Σqwen)/Σraw) | **−14,8 %** |
| prompts où qwen **allonge** la sortie | **20/39 (51 %)** |

**Le delta est négatif → qwen ALLONGE la réponse, il ne la raccourcit pas.**
Output brut total **21 281** tokens → avec qwen **24 434** tokens : qwen a **ajouté ~3 150 tokens** de sortie. Le −38,4 % (non pondéré) est gonflé par les petits prompts où qwen explose la longueur ; le chiffre honnête à l'échelle est le **pondéré : −14,8 % de surcoût**.

Cause : qwen invente un rôle (« Tu es expert… »), décompose la tâche, ajoute des consignes de format → le modèle cible répond **plus long**. L'hypothèse fondatrice est donc fausse, mesures à l'appui. (Et ce n'est que la sortie — qwen allonge **aussi** l'entrée.)

### 3.2 Coût — le palier marche, Qwen non

| | Tokens | Coût | vs A |
|---|---|---|---|
| **A** sans Helios | 30 597 | $0.0958 | référence |
| **B** palier seul | 23 260 | $0.0650 | **−32,1 %** |
| **C** Helios complet | 20 914 | $0.0638 | **−33,4 %** |

- **L'économie vient du palier**, pas de Qwen.
- **Apport propre de Qwen (B→C) : −1,9 %** = indiscernable du bruit sur 45 prompts. Cohérent avec §3.1 : une fois le palier qui impose la longueur, l'expansion de qwen est masquée, mais il n'apporte aucune économie.
- Formule du prof (Gain = 1 − Y/X sur l'échange complet, pondéré tokens) : **−31,6 %**.
- Projection /1M prompts : A $2 396 → B $1 626 → C $1 595.

### 3.3 Qualité — le levier se paie cher

Comparaison **Helios complet (C) vs sans Helios (A)**, deux juges :

| Juge | Helios mieux | équiv. | **Helios pire** | non-dégradation |
|---|---|---|---|---|
| llama3.1:8b | 20 | 1 | 24 | 47 % |
| qwen2.5:14b | 20 | 0 | 24 | **45 %** |

- **Les deux juges convergent** : appliqué aveuglément, Helios **dégrade plus souvent qu'il n'aide**.
- **17 prompts / 45 (38 %) sont dégradés selon les DEUX juges** — c'est le socle dur, pas un caprice d'un petit juge.
- Ces dégradations se concentrent sur le **palier 2** (compression agressive, « 115 mots max »).
- Exemple typique : une question qui méritait des exemples chiffrés reçoit **un tableau vide** parce qu'on a forcé une réponse trop courte.

### 3.4 La nuance honnête

L'accord **exact** entre les deux juges n'est que de **29/45 (64 %)** : les jugements par-prompt sont **bruités**. Le *sens* (Helios dégrade trop souvent) est solide ; les étiquettes prompt-par-prompt, moins. Et 45 prompts = un smoke, pas une preuve définitive : les **magnitudes défendables** exigeront le run complet sur les 458 prompts disponibles.

## 4. La lecture — pourquoi un virage ML

Trois conclusions :

1. **La réécriture LLM générique (Qwen) est un cul-de-sac.** Coûteuse, sans gain mesurable, elle ajoute un mode de dégradation (elle impose un format que le modèle remplit creux). → **On l'abandonne.**

2. **Le vrai levier, c'est la longueur de réponse** (le palier). Mais l'appliquer **partout** casse la réponse une fois sur deux. Le problème n'est donc pas *« comment mieux réécrire »*, c'est :

   > **« Sur QUELS prompts peut-on raccourcir la réponse sans la dégrader ? »**

3. **Ça, c'est un problème de Machine Learning bien posé** : supervisé (on a un signal — le juge dit si ça dégrade) et mesurable de bout en bout (tokens économisés à qualité préservée). C'est l'inverse de Qwen, qui était une intuition non mesurable.

## 5. La décision

On construit une **couche ML « Policy Engine »** par-dessus l'optimiseur existant. Sa première brique :

- **Le gating de compression** : un modèle qui prédit, pour chaque prompt, si appliquer le palier est **sûr**. Si oui → on économise les ~32 %. Si non → on laisse la réponse libre.
- **Effet attendu** : garder l'économie sur le sous-ensemble sûr, et faire **chuter la dégradation de ~45 % à <10 %** sur ce qu'on comprime.

Extensions prévues (mêmes principes) : prédire la **bonne longueur** par prompt, **router** vers le bon modèle (cheap/cher), et un **dashboard** montrant la frontière coût/qualité avant/après.

> **Pourquoi c'est défendable** (là où Qwen ne l'était pas) : chaque décision du modèle est entraînée sur un **signal mesuré** (le juge) et évaluée sur une **métrique chiffrée** (coût à iso-qualité). Pas d'intuition, des nombres.

## 6. Alignement Kirha

Kirha (context graph) décide **quel contexte** injecter dans une requête IA. Helios devient la **couche qui décide combien dépenser** pour y répondre, sans dégrader la qualité. Même nature de problème — du ML qui pilote une décision coût/qualité mesurable au-dessus d'un graphe de contexte.

## 7. Annexes — fichiers

- Données brutes du benchmark : `analysis/qm/smoke45_abc.json`
- Verdicts des juges : `analysis/qm/qm_abc_verdicts.json` (8B), `qm_abc_verdicts_qwen14b.json` (14B)
- Scripts : `analysis/qm/qm_run_abc.py` (génération), `qm_evaluate_abc.py` (juge)
- Spec du design ML : `docs/superpowers/specs/2026-06-12-helios-ml-policy-engine-design.md`
- Plan d'implémentation : `docs/superpowers/plans/2026-06-12-helios-gating-policy.md`
