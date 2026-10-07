# Résultats v4 — Prompts #-2 à #20 (23 prompts)
**Modèle :** Qwen 2.5:7b-instruct | **System prompt :** v4 | **Date :** 2026-06-08

---

## Tableau des résultats

| # | Thème | Template | role | contexte | tache | contraintes | format | qualite | gain | JSON | Bugs notables |
|---|---|---|---|---|---|---|---|---|---|---|---|
| -2 | Micheline — boulangerie | standard | inferred | present | present | absent | absent | absent | **fort** | ✓ | Ambiguïté "IA = Matrix" encore signalée ⚠ · "Aucune contrainte spécifiée" inventé |
| -1 | Kevin — SMS biz IA | standard | inferred | present | present | absent | absent | absent | moyen | ✓ | "Pas de contraintes mentionnées" inventé ⚠ · décodage argot ✓ |
| 0 | Agent IA mémoriel *(humain)* | standard | inferred | present | present | present | absent | absent | moyen | ✓ | "LLm" au lieu de "llm" (casse partielle) ⚠ · `format`=absent mais ligne **Format:** présente |
| 1 | Coach burnout | standard | inferred | present | present | absent | inferred | absent | moyen | ✓ | Propre ✓ |
| 2 | Marque éco + roadmap | standard | inferred | present | present | absent | inferred | absent | **fort** | ✓ | Propre ✓ |
| 3 | SEO bougies | standard | inferred | present | present | absent | inferred | absent | moyen | ⚠ wrap | Backticks json autour du JSON — parse fragile |
| 4 | Développement perso vague | pedagogique | inferred | present | present | absent | absent | absent | **fort** | ✓ | Rôle inféré injecté dans template péda ⚠ |
| 5 | Communication interne | standard | **absent** | present | present | absent | inferred | absent | moyen | ✓ | **Rôle absent = ligne omise ✓** |
| 6 | Scraping voitures | standard | inferred | present | present | absent | absent | absent | **fort** | ✓ | Python/Node ambiguïté non signalée mais non résolue ✓ |
| 7 | YouTube/TikTok/podcast | pedagogique | **absent** | present | present | absent | inferred | absent | **fort** | ✓ | Template hybride péda+standard ⚠ · Classification péda discutable |
| 8 | Commerce / salon de thé | standard | inferred | present | present | absent | inferred | absent | **fort** | ✓ | Propre ✓ |
| 9 | App micro-journaling | standard | inferred | present | present | absent | inferred | absent | **fort** | ✓ | Propre ✓ |
| 10 | Post LinkedIn coaching | standard | **absent** | present | present | present | absent | absent | moyen | ✓ | **Rôle absent = ligne omise ✓** · "max 250 mots" injecté (absent du prompt) ⚠ |
| 11 | Recette poulet/riz | standard | **absent** | present | present | inferred | absent | — | **fort** | ✓ | **Rôle absent = ligne omise ✓** · clé "ambiguïtés" accent |
| 12 | Blog productivité télétravail | standard | inferred | present | present | present | absent | absent | **fort** | ✓ | Propre ✓ |
| 13 | Doc API Swagger | pedagogique | **absent** | present | present | absent | absent | — | **fort** | ✓ | composantes_manquantes inclut contexte+tache (audit=present) ⚠ |
| 14 | Sécuriser SSH | pedagogique | inferred | present | present | absent | present | — | moyen | ✗ parse | `\n` littéral · Classification péda incorrecte (était standard en v3) ⚠ |
| 15 | Analyse Meta Ads ROAS | standard | present | present | present | absent | absent | absent | moyen | ✓ | "Aucunes contraintes non mentionnées" inventé ⚠ |
| 16 | Titres blog tarte tatin | standard | present | present | present | absent | present | absent | **fort** | ✓ | Propre ✓ |
| 17 | Prospection photographe | standard | inferred | present | present | absent | present | absent | moyen | ✓ | Rôle "Entrepreneur" au lieu de "Coach business" (moins précis) |
| 18 | Comptabilité bilan/résultat | pedagogique | inferred | present | present | absent | absent | — | **fort** | ✓ | **"max 250 mots" PERDU** ⚠ — régression vs v3 |
| 19 | Dire non / communication | standard | inferred | present | present | absent | absent | absent | **fort** | ✓ | Propre ✓ |
| 20 | Planning télétravail | standard | **absent** | present | present | present | absent | absent | moyen | ✓ | **Rôle absent = ligne omise ✓** |

---

## Bilan comparatif v1 → v4

| Critère | V1 | V2 | V3 | **V4** |
|---|---|---|---|---|
| JSON valide | 14/15 | 15/15 | 20/21 | **21/23** |
| Audit schéma (`present`/`absent`/`inferred`) | 87% | 60% | 90% | **91%** |
| `gain_estime` varié (≠ moyen) | 0/15 | 1/15 | 6/21 | **13/23 (57%)** |
| Ambiguïtés pertinentes | 80% | 93% | 90% | **87%** |
| Rôle absent = ligne omise | ✗ | ✗ | ✗ | **✓ 5/5 cas** |
| Contraintes chiffrées conservées | 0/1 | 0/1 | 1/1 | **0/1 ← régression** |
| Contenu inventé dans restructure | ~3/15 | ~4/15 | ~5/21 | **~6/23** |
| Classification péda correcte | — | 25% | 75% | **60% ← régression #14** |

---

## Correctif majeur confirmé ✓

**Rôle absent = ligne **Rôle:** omise du template** — appliqué sur les 5 cas concernés :

| # | audit.role | Résultat v3 | Résultat v4 |
|---|---|---|---|
| 5 | absent | `**Rôle :** Responsable équipe` injecté ❌ | Ligne absente ✓ |
| 10 | absent | `**Rôle :** Réseaux sociaux/Marketing` injecté ❌ | Ligne absente ✓ |
| 11 | absent | `**Rôle :** Aide culinaire` injecté ❌ | Ligne absente ✓ |
| 13 | absent | `**Rôle :** injecté` ❌ | Ligne absente ✓ |
| 20 | absent | `**Rôle :** Travailleur indépendant` injecté ❌ | Ligne absente ✓ |

---

## `gain_estime` débloqué

En v4, **13/23 prompts = "fort"** vs 6/21 en v3 — la règle de comptage des mots est mieux appliquée.

Prompts avec `gain = fort` : #-2, #2, #4, #6, #7, #8, #9, #11, #12, #13, #16, #18, #19

---

## Bugs persistants et nouvelles régressions

### Persistants
| Bug | Occurrences |
|---|---|
| "Aucune contrainte spécifiée" inventé quand contraintes=absent | #-2, #-1, #15 |
| Ambiguïté "IA = peur user" encore signalée (#-2) | 1/23 |
| `\n` littéral dans JSON string | #14 |
| Classification péda discutable | #7, #13, #14 |

### Nouvelles régressions v4
| Bug | Prompt | Détail |
|---|---|---|
| "max 250 mots" perdu | #18 | Contrainte chiffrée présente en v3, absente en v4 |
| #14 reclassé péda | #14 | Était standard en v3, péda en v4 — régression |
| Template hybride péda+standard | #7 | Mix des deux formats dans le même restructuré |

---

## Priorités v5

1. **"Absent = ligne omise" pour TOUTES les composantes** — le correctif s'applique au rôle mais pas encore aux contraintes. Quand `audit.contraintes = "absent"`, ne pas écrire `**Contraintes :** Aucune contrainte spécifiée`. Omettre la ligne complètement.
2. **Contrainte chiffrée #18 perdue** — "max 250 mots" doit survivre dans le template péda aussi.
3. **Classification péda #14 SSH** — sécuriser un serveur = guide pratique → standard. Renforcer les exemples d'exclusion.
4. **`gain_estime` "fort" sur #0** — format absent mais ligne **Format:** présente dans le restructuré.

---

## Ressources qwen3:8b

RAM Tour : 16GB / 7.5GB libre | qwen3:8b : ~6-6.5GB nécessaires → **faisable mais serré**.
Recommandation : fermer les autres processus lourds avant de lancer, tester sur 5 prompts d'abord.
