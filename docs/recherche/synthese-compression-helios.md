# Helios — Synthèse du POC « optimisation I/O par compression »

**Date** : 2026-06-18
**Objet** : compte-rendu honnête du travail quantitatif sur la réduction de tokens par compression de réponse.
**Statut** : finding négatif rigoureux + contribution méthodologique.

> Ce document est écrit pour servir de méthodologie de mesure et de trame de soutenance. Il assume ses résultats — y compris quand ils invalident une hypothèse de départ. C'est précisément ce qui en fait un travail défendable.

---

## 1. La question de départ

Helios est un proxy LLM d'optimisation de prompt. Le POC visé : pouvoir affirmer
**« Helios réduit la consommation de tokens I/O d'environ 5 %, à qualité de réponse équivalente. »**

Deux sous-questions ont structuré l'enquête :
1. **Où est réellement le coût** d'un échange LLM ? (pour savoir sur quoi agir)
2. **Existe-t-il un levier qui réduise ce coût sans dégrader la qualité ?**

La réponse honnête, en une phrase : **le levier existe (compression de réponse, −66 % de tokens), mais il dégrade la qualité 2 fois sur 3 de façon imprévisible, et aucun mécanisme bon marché ne permet de capturer le gain sans casser la réponse.**

---

## 2. Où est le coût : l'output écrase tout

Mesure sur le corpus (comparia, modèle cible Qwen3:8b, tarif Sonnet 3 $/15 $ par M tokens) :

| Poste | Tokens | Part du coût |
|---|---|---|
| **Input** (le prompt) | 3 351 | **1,5 %** |
| **Output** (la réponse) | 45 229 | **98,5 %** |

Ratio sortie/entrée ≈ **9:1**. **Conséquence directe et non négociable : tout se joue sur l'output.** Optimiser l'input, c'est optimiser 1,5 % de la facture.

Cela disqualifie d'emblée toute une famille d'idées (voir §3).

---

## 3. Cartographie des leviers : ce que chacun fait *vraiment*

Trois leviers orthogonaux, qu'on ne peut pas cumuler sans arbitrage :

| Levier | Agit sur | Effet mesuré | Verdict |
|---|---|---|---|
| **Regex / heuristique** | nettoyage du bruit input | −3 à −5 % input, déterministe | utile, marginal (input = 1,5 %) |
| **Qwen (restructuration du prompt)** | qualité + forme | input **+7 à +15 %**, output **+3 %** (token-neutre) | **levier QUALITÉ, pas tokens** |
| **Consigne de longueur (palier)** | longueur de l'output | output **−66 %** | **le seul levier tokens réel — mais dégrade ~la moitié à l'aveugle** |

### Pièges écartés (chiffrés)

- **`max_tokens` comme levier de longueur** : *faux*. `max_tokens` est un plafond dur qui **tronque**, il ne raccourcit jamais proprement. Sur les réponses sous le plafond → effet nul ; sur celles au-dessus → amputation. Posé à la valeur « pyramide » (379 tk pour le palier dominant), il tronquerait **78 %** des réponses déjà contraintes. Preuve empirique : le cas c017 a été tronqué à 16 000 tk = exactement son `max_tokens`. → `max_tokens` = filet de sécurité large, jamais un levier.
- **GIST (extraction d'intention avant Qwen)** : viserait à réduire l'input. Or **l'input = 1,5 % du coût** → mort-né comme levier tokens. (Reste éventuellement un levier qualité/UX, jamais coût.)
- **Restructuration en pseudo-code / format** : la forme du prompt ne change pas l'output. Vérifié : 12 prompts sur 20 demandaient déjà un tableau → output toujours **+3 %** (neutre). L'output suit la *demande* + une *contrainte de longueur explicite*, pas la syntaxe du prompt.

**Principe consolidé :** toute optimisation côté prompt (regex, Qwen, GIST, pseudo-code) est un levier **input + qualité, jamais output**. L'output se gouverne en aval, par le contrat de longueur — qui est le seul à mordre, et qui dégrade.

---

## 4. Méthodologie : la grille de qualité 2 couches

Pour mesurer « la compression dégrade-t-elle ? » sans naïveté, une grille à **non-régression différentielle** : on ne note pas une réponse dans l'absolu, on tranche *« la version compressée vaut-elle au moins la baseline ? »*. Verdict ternaire (équivalent / dégradé tolérable / dégradé inacceptable → escalade).

| Couche | Nature | Fiabilité |
|---|---|---|
| **Couche 1 — gates mécaniques** | déterministe, 0 LLM (vide/erreur/refus/troncature/répétition/langue) | **κ = 1 par construction** |
| **Couche 2 — juge sémantique** | LLM, dimension par dimension (exactitude véto / complétude / pertinence) | κ **mesuré** |

Deux profils de jugement (correctif clé) :
- **Profil A** — non-régression vs la *réponse* baseline → pour la **compression** (toute omission = dégradation).
- **Profil B** — conformité à un *barème* de tâche → pour la **restructuration** (les ajouts utiles comptent).

**Point méthodologique central :** une grille ne vaut que par sa **reproductibilité**, qu'on mesure par le **kappa de Cohen** (accord inter-juges). On sait donc *quand* notre mesure est fiable — et quand elle ne l'est pas. Ce critère s'est révélé décisif (§7).

---

## 5. Le POC envisagé : « comprimer → vérifier → rollback »

Le levier (consigne, −66 %) dégrade à l'aveugle. L'idée de POC : **ne pas prédire** depuis le prompt (on a montré que c'est impossible, ROC 0,59), mais **vérifier** sur la réponse produite, via la grille :

```
Prompt → réponse compressée (consigne)
       → Couche 1 (gratuit) : échec dur ? → escalade
       → Couche 2 (juge) : la version courte tient ?
            ✅ oui → on garde (tokens économisés)
            ❌ non → rollback vers la réponse complète
```

La grille devient le **gate de sélectivité** que le classifieur-prompt ne pouvait pas être : elle juge depuis l'**output** (fiable) au lieu du **prompt** (0,59).

---

## 6. Résultats : le net I/O des politiques

Mesure sur 443 prompts, gate en local (coût électricité, seul l'appel final facturé) :

| Politique | net coût | qualité | shippable |
|---|---|---|---|
| **BLIND** (comprimer tout) | **−66 %** | **68 % dégradent** | ❌ injouable |
| **ORACLE** (routing parfait, irréel) | −18 % | ~0 % dégrade | 🚫 inatteignable |
| **VÉRIFIE-ROLLBACK** (réaliste) | **+4 %** | ~0 % dégrade | ⚠️ coûte plus cher |

**Lecture :** comprimer tout économise 66 % mais casse 2 réponses sur 3 (impitchable). Router parfaitement donnerait −18 % à qualité préservée, mais c'est irréel (la prédiction côté prompt plafonne à 0,59). La version *réaliste* (vérifie-rollback) **coûte +4 %** : avec 68 % de rollbacks, le gaspillage (réponse compressée jetée + escalade) écrase l'économie sur les 32 % qui passent.

→ **Sur ce corpus, il n'existe aucune compression net-positive qui préserve la qualité.**

---

## 7. Le contrôle de fiabilité : le moment décisif

Les chiffres du §6 dépendent de la qualité des **labels** (« cette compression a-t-elle dégradé ? »). Première passe avec un juge local (qwen2.5:7b) → safe 48 %, vérifie-rollback **−15 %** (chiffre flatteur).

**Avant de publier ce −15 %, contrôle de fiabilité** : re-jugement des 443 paires avec un juge premium (Claude Opus 4.8, 4 min 37, **7,66 $**), puis kappa de Cohen entre les deux juges.

```
Accord qwen-7b ↔ Opus 4.8 (349 prompts communs)
  accord brut    = 52 %   (≈ pile ou face)
  κ de Cohen     = 0.037  ← ~ZÉRO accord au-delà du hasard
  taux safe : qwen 48 %  →  Opus 32 %
  qwen « SAFE » mais Opus « DÉGRADÉ » : 109 cas (juge local trop optimiste)
```

**Le juge local était statistiquement indiscernable du hasard.** Le « −15 % » reposait sur des labels-bruit. Recalculé avec les labels fiables d'Opus, il devient **+4 %** (cf. §6).

> C'est la contribution méthodologique la plus forte du projet : **un contrôle de fiabilité a invalidé un chiffre optimiste avant qu'il soit présenté — pour 7,66 $.** La plupart des POC publient le chiffre flatteur sans tester la fiabilité du juge qui le produit.

---

## 8. Structure de la dégradation : pas de sous-ensemble safe

Dernière vérification : la dégradation se concentre-t-elle quelque part (longueur, palier…) ? Si oui, on pourrait comprimer sélectivement le reste. Avec les labels fiables d'Opus :

| Découpe | safe |
|---|---|
| longueur du prompt (<80 → >200 tk) | 31 % · 35 % · 30 % · 31 % → **plat** |
| longueur de réponse (<500 → >2000) | 30 % · 41 % · 34 % · **25 %** (les longues dégradent *plus*) |
| palier 2 (dominant) / palier C (code) | 33 % / **18 %** (le code casse le plus) |
| gain_estime faible/moyen/fort | 31 % · 35 % · 38 % → **plat** |

**Aucun sous-ensemble au-dessus de ~41 %.** La dégradation est **intrinsèque, non structurée, uniforme** sur toutes les dimensions mesurables. Le seul gradient (longues réponses → moins safe) va à *l'envers* d'un POC d'économie. → **Pas de POC sélectif possible.**

---

## 9. Conclusion honnête

1. **La compression est un vrai levier tokens** (−66 % d'output) — c'est le plus gros chiffre du projet.
2. **Mais elle dégrade ~2 réponses sur 3, de façon imprévisible.** Rien dans le prompt ne sépare le safe du cassé : ni la longueur, ni le palier, ni la complexité estimée (tout à ~32 %).
3. **Aucun mécanisme ne la transforme en produit net-positif quality-safe** sur ce corpus : prédiction prompt (0,59), vérifie-rollback (+4 %), compression sélective (pas de sous-ensemble) — tous échouent.
4. **Le « mur des labels » est confirmé** : le plafond du gating (ROC 0,59) ne venait pas que des features — les **labels eux-mêmes** étaient du bruit (κ 0,037 local vs premium). *« Si les juges ne sont pas d'accord entre eux, le modèle ne peut pas apprendre. »*

L'argument écologique (datacenters ~565 TWh en 2026, Gartner) cadre **l'enjeu** — pourquoi le sujet mérite d'être mesuré — mais la mesure honnête dit que les 5 % ne sont pas au rendez-vous sur la compression de prompt isolé.

---

## 10. Contribution & pistes

**Ce que ce travail démontre** (niveau attendu d'un projet rigoureux) :
- Un **corpus de test réel** mesuré (tokens, coûts) avec **juge LLM indépendant**.
- Une **grille de qualité 2 couches** avec kappa mesuré — on sait quand notre mesure est fiable.
- Un **finding contre-intuitif** documenté et un **contrôle de fiabilité** qui a invalidé un chiffre avant publication.
- Une **identification claire** des cas où ça marche et où ça échoue.

**Ce qu'il faudrait pour franchir le mur** (hors périmètre actuel) :
- **Features sémantiques** (embeddings) — co-auteur mesure 0,59 avec, le plafond reste bas.
- **Juges premium** comme source de vérité (coûteux mais fiable — démontré ici).
- **Une définition de « bon/mauvais » qui ne dépende pas d'un juge LLM** : feedback utilisateur (👍/👎), taux de ré-édition, temps de relecture. *« Si les profs ne sont pas d'accord, fais voter les élèves. »*

---

## Annexe — chiffres clés & artefacts

| Donnée | Valeur |
|---|---|
| Part input / output dans le coût | 1,5 % / 98,5 % |
| Consigne palier (A→B), gain output | −66 % |
| Qwen restructuration, effet tokens | input +7-15 %, output +3 % (neutre) |
| Non-dégradation BLIND (juge Opus) | **32 %** (68 % dégradent) |
| κ inter-juges qwen-7b ↔ Opus 4.8 | **0,037** |
| Net coût vérifie-rollback (réaliste) | **+4 %** |
| Plafond gating (ROC-AUC) | 0,50 structurel / 0,59 embedding |
| Coût du re-jugement Opus (443 paires) | 7,66 $ / 4 min 37 |

**Artefacts** :
- `analysis/qm/qwen_458_abc.json` — run ABC 458 prompts (3 conditions).
- `analysis/qm/qwen_458_verdicts_qwen25_7b.json` — labels juge local (bruités, κ 0,037).
- `analysis/qm/qwen_458_verdicts_opus48.json` — labels juge premium Opus 4.8 (fiables).
- `analysis/qm/rejudge_opus.py` — script de re-jugement parallèle + mesure coût.
- `docs/grille-qualite-helios.md` — spécification de la grille 2 couches.
- `backend/utils/quality_gates.py` / `backend/services/judge_service.py` — implémentation Couche 1 / Couche 2.
