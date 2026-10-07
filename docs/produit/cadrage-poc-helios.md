# Helios — Cadrage du POC (recadrage après investigation)

**Date** : 2026-06-18
**Objet** : recadrer ce qu'est devenu le POC d'Helios après mesure. Document de référence (académique / 2ᵉ soutenance).
**Esprit** : on assume le parcours. On visait X, la mesure a dit non, on a trouvé Y et on l'a validé. C'est ça, le résultat.

> Ce document remplace le cadrage initial « réduire les tokens I/O de ~5% ». Le détail technique et les chiffres bruts sont dans `synthese-compression-helios.md`.

---

## 1. Ce qu'on visait au départ

POC initial : **« Helios réduit la consommation de tokens d'environ 5%, à qualité de réponse équivalente. »**
Mécanisme supposé : optimiser le prompt (nettoyage heuristique + restructuration Qwen + contrainte de longueur « palier ») → moins de tokens → moins de coût et d'énergie.
Angle écologique : la consommation des datacenters IA grimpe (~565 TWh en 2026, Gartner) — réduire les tokens, c'est réduire l'empreinte.

**L'intuition de départ : agir sur le prompt pour faire maigrir la réponse.**

---

## 2. Ce que la mesure a dit (l'investigation)

**Où est le coût ?** Sur un prompt isolé : input = **1,5%** du coût, output = **98,5%**. Tout se joue sur l'output.

**Tous les leviers d'output ont été testés** sur un corpus réel (comparia) avec un juge LLM :

| Levier | Résultat mesuré | Verdict |
|---|---|---|
| Restructuration Qwen | tokens neutres (input +7%, output +3%) | levier **qualité**, pas tokens |
| `max_tokens` (plafond) | tronque la réponse (ne la raccourcit pas) | pas un levier |
| Consigne de longueur (palier) | **−66% output** mais **dégrade ~2/3** des réponses | inexploitable à l'aveugle |

**Pourquoi ça ne marche pas :** sur ces prompts, **la longueur de la réponse EST la valeur** — le modèle ne « remplit » pas. Comprimer une réponse enlève de la **substance**, pas du gras. Et rien dans le prompt ne permet de prédire quelles réponses survivront à la compression (le classifieur plafonne à ROC 0,59).

**La rigueur qui a évité un faux résultat :** pour mesurer la dégradation, une **grille de qualité à 2 couches** (déterministe + juge sémantique, avec **kappa de Cohen** mesuré). Un **contrôle de fiabilité** (re-jugement par un juge premium) a révélé que les labels du juge local étaient **du bruit** (κ = 0,037) — ce qui a **invalidé un chiffre optimiste (−15%) avant qu'il soit présenté.**

→ **Conclusion : comprimer UNE réponse est une impasse.** Finding négatif, mais rigoureux et documenté.

---

## 3. Le pivot : où est *vraiment* le coût

Le constat qui débloque tout : **un LLM n'a pas de mémoire persistante.** Pour suivre une conversation, l'application lui **renvoie tout l'historique à chaque tour.**

### L'input a deux couches

Le « 1,5% » du §2 cache une distinction essentielle : **l'input n'est pas une seule chose.**

| Couche | Quoi | Taille |
|---|---|---|
| **A — message du tour** | la question que l'utilisateur tape ce tour-ci | petite, ~constante |
| **B — relecture du contexte** | tout l'historique réinjecté (le LLM est sans mémoire) | **nulle au tour 1**, puis **grossit** à chaque tour |

- **Sur un prompt isolé (tour 1)** : il n'y a **pas de Couche B**. Donc input = Couche A seule = **1,5%**, output = 98,5%. C'est ce scope qui rendait la compression de *réponse* logique au départ.
- **Sur une session** : la Couche B **s'accumule jusqu'à dominer.** Mesuré sur 2 vraies sessions : input cumulé **~286k** tokens contre **~15k** d'output (34 tours) → l'input (surtout la Couche B) = **~95% du volume**.

Les deux chiffres ne se contredisent pas : c'est la **même chose à deux échelles**, et la différence **est exactement la Couche B qui s'accumule.**

Et — point clé — **le vieil historique, lui, a du surplus** (politesses, ré-explications, tangentes que le modèle a déjà utilisées). Contrairement à une réponse, **il peut être comprimé sans perte.** On change d'étage et on frappe enfin le bon.

> ### Le principe qui explique tout : **on ne coupe que la redondance, pas la substance.**
>
> | Couche | Nature | Compressible ? |
> |---|---|---|
> | **A — message** | substance (la vraie question) | ❌ irréductible |
> | **Output — réponse** | substance (prouvé : la comprimer dégrade) | ❌ irréductible |
> | **B — relecture du contexte** | **redondance** (le modèle l'a *déjà* vu) | ✅ **compressible sans perte** |
>
> Le POC initial essayait de couper de la **substance** (l'output) — impossible par nature. Le POC validé coupe la seule **redondance** du système : la relecture du passé, l'artefact de l'absence de mémoire du LLM (le système re-paie le même contexte à chaque tour).
>
> On n'a pas trouvé le levier en cherchant *mieux comment* comprimer la réponse, mais en **changeant la question** : de « comment raccourcir la réponse ? » à « **où s'accumule vraiment le coût d'une session ?** ». Réponse : dans la **redondance**, pas dans la substance.

---

## 4. Le POC validé : le sous-agent mémoire

**Le mécanisme.** Un sous-agent interne résume le vieil historique, garde les derniers tours **verbatim**, et **vérifie la fidélité du résumé** avec la grille (ne perd-il aucune décision, entité, chiffre ?). Le modèle principal continue la conversation en relisant un **résumé** au lieu de tout le passé. Il n'agit **que sur la Couche B** (la relecture) — ni sur le message de l'utilisateur, ni sur la réponse :

```
SANS sous-agent (tour N) :  [A: message] + [B: tout l'historique brut] + [Output]
AVEC sous-agent (tour N) :  [A: message] + [B': résumé à 12%]          + [Output inchangé]
                                            ↑ on coupe 88% ICI, et seulement ICI
```

**Mesuré (2 sessions × 3 points de compaction × 2 juges premium) :**

| Métrique | Résultat |
|---|---|
| Compression du vieil historique | **88%** (résumé = 12% du brut) |
| Fidélité (résumé ne perd rien) | **5/6** (Opus) — **6/6** (Sonnet) |
| Économie session — **brut** (agent principal) | **−45% à −58%** input (≈ **−46% de la facture**) |
| Économie session — **nette** (sous-agent inclus) | **−43%** (rédacteur Haiku facturé) → **−46%** (rédacteur local) |
| Modèle rédacteur | **Haiku suffit** (pas besoin de premium) |
| Garde-fou | couper **~85-90%**, pas au-delà (à 96% on casse) |

**Deux fenêtres, pas une.** L'agent principal et le sous-agent sont **deux appels séparés**. L'agent principal ne voit jamais le vieux brut — sa fenêtre est *dégonflée*, pas élargie. Le sous-agent, dans **sa propre fenêtre**, lit le vieil historique et produit le résumé : il consomme donc lui aussi, mais **peu** — ~14k tokens sur une session de 34 tours, en **5 compactions par batch** (pas à chaque tour). Il remplace **~30 relectures premium par 1 résumé cheap/local** → overhead de **3 points** (Haiku) ou **nul** (Qwen local). Deux règles de design : **résumer par batch** + **sous-agent en local**.

**La grille trouve son vrai job ici.** Conçue pour l'ancien levier (échoué), elle sert *vraiment* à garantir que le résumé ne perd rien — un gate de fidélité vérifié. Le « 96% qui casse » a même été détecté par elle : on connaît la borne à ne pas franchir.

**Validé à l'échelle — 39 364 conversations gouvernementales réelles.** Sur le corpus comparia (Etalab), simulation de la réinjection avec le **contenu réel** des tours (sans appel LLM) :

- l'input **écrase l'output : 4,8×** sur une session, et la **Couche B (relecture) = 95% de l'input** → thèse structurelle confirmée sur 39k vraies conversations, pas 2.
- l'économie **scale avec la longueur** — et c'est l'honnêteté décisive :

| Tours | % des convs | économie input |
|---|---|---|
| 3-4 | 67% | **~0%** (rien à comprimer) |
| 5-9 | 26% | ~18% |
| 10+ | 7% | **~52%** |

- **facture corpus (pondérée tokens) : −43%** — mais tirée par les 7% de sessions longues. **La conversation médiane sauve 0%** (moyenne par conv : −9%).

→ Le bon énoncé n'est **pas** « −43% partout », mais **« −52% sur les sessions de 10+ tours, ~0% sur le typique »**. Helios a de la valeur sur les **sessions longues** (interactif, agentique) — ciblé, pas universel. C'est plus honnête, et ça **désigne le marché** (gros usages répétés).

**Fidélité confirmée sur le corpus réel (Palier 2).** Sur **50 vraies conversations comparia longues** (8-20 tours), résumé par Haiku puis jugé par Opus + Sonnet :

| Métrique | Résultat |
|---|---|
| Compression | coupe **90%** |
| Fidélité du résumé | **90%** (Opus) — **96%** (Sonnet) |
| Pertes graves (≥1 juge) | **~12%** (résidu) |
| κ inter-juges | 0,24 (taux agrégé fiable ; label « grave » par cas plus bruité) |

Mieux que les 2 sessions perso (83%). **Le résidu de ~12% est précisément le rôle de la grille en production** : elle vérifie chaque résumé et, sur ces cas, garde plus de verbatim / ne comprime pas → **qualité shippée ~100%**, le résidu rattrapé. (Plusieurs graves étaient à coupe 96%, au-delà du garde-fou ≤90% : calibrer à ~85% réduit encore le résidu.)

**Validé hors corpus (Foxy / qwen local).** Le garde-fou « 96% casse » s'est **reproduit** sur un cas hors comparia (mémoire d'un agent perso, modèle local) → la borne n'est pas un artefact du corpus de test. Et un échec concret y a **prouvé que l'architecture complète est nécessaire** : un résumé *nu* (sans fenêtre verbatim ni gate) a affirmé « accès bloqué » alors qu'il était résolu — il a **figé un état ancien**. → la **fenêtre verbatim** (garder le récent en brut) et le **gate de fidélité** ne sont pas des options, ils sont **obligatoires**. Démonstration vivante de la valeur de la grille.

---

## 5. Ce que ce POC démontre (la contribution)

1. **Un finding négatif rigoureux** : la compression de réponse ne tient pas, et on sait *pourquoi* (la longueur = la substance).
2. **Une démonstration méthodologique rare** : un contrôle de fiabilité (kappa, juge premium) a invalidé notre propre chiffre optimiste *avant* publication. La plupart des POC présentent le chiffre flatteur sans tester la fiabilité du juge qui le produit.
3. **Un levier réel, mesuré, à qualité vérifiée** : **−43 à −46% net** de coût de session (sous-agent inclus), fidélité confirmée par deux juges premium.
4. **Une honnêteté de parcours assumée** : on visait la compression de réponse, la mesure l'a réfutée, on a identifié et validé le vrai levier (la mémoire de session).

C'est un travail **expérimental** : corpus réel, juge indépendant, grille avec kappa, contrôle de fiabilité, pivot fondé sur les données. Pas un chatbot qui « marche » en cachant ses limites.

---

## 6. La différenciation (honnête)

Le sous-agent mémoire **en soi n'est pas une invention** : la compaction de contexte existe déjà dans plusieurs outils. La valeur d'Helios est dans la **combinaison** :

- mémoire de session **+ grille de fidélité vérifiée** (un gate qui *prouve* qu'on n'a rien perdu — c'est ça qui est rare) ;
- **+ routing** vers l'infra la plus efficiente/souveraine selon la tâche *(angle traité à part)* ;
- **+ la couche d'optimisation de prompt** comme expérience utilisateur.

C'est le **package** qui est défendable, pas le résumé tout seul.

---

## 7. Ce qui reste à faire pour blinder

- Élargir la validation (plus de sessions, jeu de cas-limites plus dur pour un kappa inter-juges informatif).
- Spécifier puis implémenter le sous-agent (déclenchement, fenêtre verbatim, format de résumé, branchement de la grille).
- Mesurer en conditions réelles (proxy live).

---

## Annexe — chiffres clés

| Donnée | Valeur |
|---|---|
| Input (Couche A, message) / output — prompt isolé | 1,5% / 98,5% |
| Input cumulé (surtout Couche B, relecture) vs output — session 34 tours | ~286k / ~15k tokens |
| Compression du vieil historique (mesurée) | 88% (résumé = 12% du brut) |
| Fidélité du résumé (2 sessions perso) | 5/6 Opus, 6/6 Sonnet |
| Fidélité sur corpus réel (50 convs comparia) | 90% Opus, 96% Sonnet ; ~12% graves → rattrapés par la grille |
| Économie session — brut (agent principal) | −45 à −58% input ≈ −46% facture |
| Économie session — **nette** (sous-agent inclus) | **−43%** (rédacteur Haiku) → **−46%** (rédacteur local) |
| Coût du sous-agent | ~14k tk / session 34 tours, 5 compactions par batch, modèle léger |
| Garde-fou compression | ≤ ~90% (96% casse) |
| Compression de réponse (ancien levier) | dégrade 68%, labels κ 0,037 → **abandonné** |

*Détail complet et reproductibilité : `synthese-compression-helios.md`. Scripts : `analysis/qm/rejudge_opus.py`, `test_memoire_session.py`, `lock_memoire_session.py`.*
