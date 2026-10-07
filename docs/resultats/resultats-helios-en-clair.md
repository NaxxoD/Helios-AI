# Helios — Tous les résultats, en clair

> **But de ce doc** : tout ce qu'on a mesuré, et ce que ça veut dire, sans jargon.
> Mis à jour le 2026-06-16 (co-auteur).

---

## En une phrase

**La valeur d'Helios vient d'envoyer chaque question au bon modèle (routing), PAS de comprimer les prompts.** Comprimer dégrade plus que ça ne fait économiser.

---

## Les 4 leviers qu'on a testés

### 1. Comprimer la SORTIE — le "palier" ("réponds en X mots max")

- **Économie** : ~−32 % de coût.
- **Mais ça dégrade la réponse ~6 fois sur 10.** Sur 458 prompts, quand nos 2 juges sont d'accord, **seulement 37 % des compressions passent sans dégât** (donc 63 % abîment la réponse).
- **Ce que ça veut dire** : appliquer le palier à *tout le monde* en aveugle, c'est se tirer une balle dans le pied. L'économie ne vaut pas la perte de qualité.

### 2. Comprimer l'ENTRÉE — réécrire le prompt avec Qwen

- **Résultat** : **+1,9 % de coût** (ça n'aide pas), et ça **rallonge** même 75 % des prompts courts.
- **Ce que ça veut dire** : **mort.** Le pitch « Helios compresse vos prompts pour vous faire économiser » ne tient pas. est arrivé exactement à la même conclusion de son côté.)

### 3. Router vers le BON MODÈLE (le gros modèle seulement si nécessaire)

- **Résultat** : jusqu'à **+45 % d'économie** si chaque prompt part vers le modèle le moins cher qui suffit.
- **Ce que ça veut dire** : **c'est LE levier.** L'économie vient du *choix du modèle*, pas d'une triche sur les tokens.

### 4. Le "gating" — un modèle qui décide QUAND comprimer sans risque

L'idée maligne : ne comprimer que les prompts où ça ne casse rien. On a entraîné un modèle pour ça.

*(Comment lire le score "ROC-AUC" : 0,50 = pile ou face / inutile ; 1,00 = devin parfait.)*

| Sur quoi le modèle se base | Score | Verdict |
|---|---|---|
| La **forme** du prompt (longueur, ponctuation, type…) | **0,50** | Pile ou face → inutile |
| Le **sens** du prompt (embedding) | **0,59** | Petit signal réel, mais faible |

- **Ce que ça veut dire** : savoir si comprimer va casser la réponse dépend du **sens** de la question, pas de sa forme. C'est encourageant (le signal existe), mais 0,59 c'est trop faible pour décider tout seul en prod.

---

## Pourquoi on plafonne à 0,59 ? (le point important)

Nos 2 juges IA ne sont **d'accord que 2 fois sur 3** sur la question « est-ce que la version courte est aussi bonne ? ». 

👉 Si les profs ne sont pas d'accord entre eux, l'élève (le modèle) ne *peut pas* apprendre mieux. Le plafond ne vient pas de notre code, il vient de la **qualité floue des étiquettes**. Pour monter, il faudrait un **juge plus fiable** (GPT/Claude plutôt que des modèles locaux) — pas encore fait (question de budget).

---

## Un fait utile en plus

La **sortie** coûte ~**5× plus cher** que l'entrée. → C'est la **longueur de la réponse** qui pèse sur la facture, pas la taille du prompt. (Ça renforce le point n°1 : c'est bien la sortie qu'il faudrait maîtriser… mais sans dégrader.)

---

## Ce qu'on garde / ce qu'on jette

| Levier | Décision |
|---|---|
| Comprimer l'entrée (Qwen) | ❌ **Jeté** — ne marche pas |
| Comprimer la sortie en aveugle | ❌ **Jeté** — dégrade 6 fois sur 10 |
| Comprimer la sortie *pilotée* (gating ML) | ⚠️ **Faible** — optionnel, à garder en heuristique prudente |
| **Router le bon modèle** | ✅ **Gardé — priorité n°1** (+45 %) |
| Suivi coût / CO₂ en direct | ✅ **Gardé** (déjà codé) |

---

## La recommandation

**Concentrer l'effort sur le routing** (+45 % prouvé, c'est le vrai produit). Le gating ML, au mieux à 0,59, ne mérite pas un gros investissement maintenant — on le garde sous forme de **règle simple et prudente** : *ne pas comprimer les questions analytiques/complexes*, ne comprimer que sur demande explicite de l'utilisateur.

---

## D'où viennent ces chiffres (transparence)

- **Mesuré sur 458 prompts** (double-juge, 15 juin 2026) : les 63 % de dégradation du palier, le désaccord juges (1/3), et les scores de gating 0,50 / 0,59. → Solide.
- **Mesuré sur échantillons plus petits** (45–90 prompts, runs antérieurs) : le −32 % du palier, le +1,9 % de Qwen, le +45 % du routing, le 5× sortie/entrée. → Indicatifs, à reconfirmer à l'échelle.
- **Limite générale** : tout tourne sur un modèle local (mistral) comme banc d'essai. Les **économies en euros réels** demandent un test sur les vrais modèles (GPT / Claude / Gemini) — pas encore fait.
