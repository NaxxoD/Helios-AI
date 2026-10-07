# Résultats v3 — Prompts #0-20
**Modèle :** Qwen 2.5:7b | **System prompt :** v3 | **Date :** 2026-06-08 | **Prompts testés :** 21 (#0 = prompt humain natif)

---

## Tableau des résultats

| # | Thème | Template | role | contexte | tache | contraintes | format | qualite | gain | JSON | Bugs notables |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | Agent IA mémoriel local *(humain)* | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | `llm` et `mvp` conservés ✓ — propre |
| 1 | Coach burnout | standard | inferred | present | present | absent | inferred | absent | moyen | ✓ | Contraintes injectées dans restructure malgré audit=absent ⚠ |
| 2 | Marque éco + roadmap | standard | inferred | present | present | present | absent | absent | moyen | ✓ | Clé `ambiguités` avec accent (non-schéma mineur) |
| 3 | SEO bougies | standard | absent | present | present | present | inferred | absent | moyen | ✓ | Rôle absent en audit mais injecté quand même dans restructure ⚠ |
| 4 | Développement perso vague | pedagogique | absent | present | present | present | inferred | — | moyen | ✓ | Champ `qualite` absent de l'audit (incomplet) |
| 5 | Communication interne | standard | inferred | present | present | absent | absent | absent | moyen | ✓ | Contraintes inventées dans restructure ("pratiques et rapides") ⚠ |
| 6 | Scraping voitures | standard | inferred | present | present | absent | present | absent | **fort** | ✓ | "Pas de restrictions spécifiques" inventé dans Contraintes ⚠ — Python/Node non résolu ✓ |
| 7 | YouTube/TikTok/podcast | pedagogique | absent | present | present | absent | inferred | absent | moyen | ✓ | Classification péda toujours douteuse (demande = choisir + idées, pas expliquer) |
| 8 | Commerce / salon de thé | standard | absent | present | present | present | absent | absent | moyen | ✓ | Rôle absent en audit mais injecté dans restructure ⚠ |
| 9 | App micro-journaling | standard | inferred | present | present | absent | absent | absent | moyen | ✓ | Ambiguïté "technologies" trop vague — React/Flutter/Firebase non listés explicitement |
| 10 | Post LinkedIn coaching | standard | inferred | present | present | absent | inferred | absent | moyen | ✓ | "150-200 mots" inventé dans restructure — contrainte absente du prompt ⚠ |
| 11 | Recette poulet/riz | standard | absent | present | present | present | absent | absent | moyen | ✓ | "Aide culinaire" = rôle inféré discutable |
| 12 | Blog productivité télétravail | standard | present | present | present | present | inferred | absent | moyen | ✓ | Propre ✓ |
| 13 | Doc API Swagger | pedagogique | present | present | present | absent | inferred | absent | **fort** | ✗ parse | `\n` littéral dans string JSON — classification péda discutable |
| 14 | Sécuriser SSH | standard | inferred | present | present | absent | inferred | absent | **fort** | ✓ | Propre ✓ — rôle "spécialiste en cybersécurité" bien inféré |
| 15 | Analyse Meta Ads ROAS | standard | present | present | present | absent | inferred | absent | moyen | ✓ | CTR/CPC introduits au lieu de conserver termes originaux |
| 16 | Titres blog tarte tatin | standard | present | present | present | absent | present | absent | **fort** | ✓ | `qualité` avec accent dans composantes_manquantes (mineur) — propre ✓ |
| 17 | Prospection photographe freelance | standard | inferred | present | present | present | present | absent | moyen | ✓ | Propre ✓ |
| 18 | Comptabilité bilan/résultat | pedagogique | present | present | present | present | present | absent | **fort** | ✓ | "max 250 mots" conservé ✓ — classification péda correcte ✓ |
| 19 | Dire non / communication bienveillante | standard | absent | present | present | present | inferred | absent | moyen | ✓ | Propre ✓ |
| 20 | Planning télétravail heure/heure | standard | absent | present | present | absent | inferred | absent | moyen | ✓ | Propre ✓ |

---

## Prompts restructurés — avant / après (sélection)

### #0 — Agent IA mémoriel *(prompt humain natif)* ✓
**Original :** 108 mots — bruit ~25%
**Restructuré :**
```
**Rôle :** Ingénieur IA.
**Contexte :** Construction d'un agent IA mémoriel utilisant des fichiers locaux et conversations llm.
Objectif : performance optimisée sur machine personnelle, indépendance vis-à-vis des outils big tech.
**Tâche :** Construire une roadmap de build et coder de bout en bout l'architecture, les dépendances
et les outils adaptés à l'objectif cible.
**Contraintes :** Performance optimisée sur machine personnelle, indépendance maximale, MVP dans la soirée.
**Format :** Plan détaillé.
```
> `llm` et `mvp` conservés tels quels ✓ — règle 3 v3 appliquée

---

### #14 — Sécuriser SSH ✓
**Original :** 105 mots — bruit ~30%
**Restructuré :**
```
**Rôle :** Spécialiste en cybersécurité.
**Contexte :** Sécuration d'un serveur SSH pour éviter les attaques par force brute,
configuration du port et des clés RSA.
**Tâche :** Mettre en place 3 meilleures pratiques de base rapides à mettre en place.
**Format :** Liste sous forme de points.
```
> `gain=fort` ✓ — classification standard correcte (v2 classait péda) ✓

---

### #16 — Titres blog ✓
**Original :** 73 mots — rôle explicite "copywriter professionnel"
**Restructuré :**
```
**Rôle :** Copywriter professionnel.
**Contexte :** Blog de cuisine, article sur une recette de tarte tatin aux pommes.
**Tâche :** Rédige 5 titres accrocheurs mais honnêtes pour l'article.
**Format :** Liste sous forme de puces.
```
> `audit.role = "present"` ✓ — bug valeur libre v2 corrigé

---

### #18 — Comptabilité bilan/résultat ✓
**Original :** 85 mots — contrainte "max 250 mots" explicite
**Restructuré :**
```
Explique [SUJET] en 5 sections :
1) Définition simple
2) Comment ça marche
3) Exemples concrets
4) Limites / risques
5) Points clés à retenir

Contraintes :
* Langage accessible, sans jargon
* Explication globale de maximum 250 mots

Format :
* Titres + listes
```
> Contrainte chiffrée "max 250 mots" conservée ✓ — bug v2 corrigé

---

## Bilan synthèse

| Métrique | V1 | V2 | V3 |
|---|---|---|---|
| JSON valide | 14/15 (93%) | 15/15 (100%) | **20/21 (95%)** |
| Audit schéma respecté | 13/15 (87%) | 9/15 (60%) | **19/21 (90%)** |
| gain != moyen | 0/15 | 1/15 | **6/21 (29%)** |
| Ambiguïtés pertinentes | 12/15 (80%) | 14/15 (93%) | **19/21 (90%)** |
| Contraintes chiffrées conservées | — | 0/1 | **1/1 (100%)** |
| Acronymes conservés (llm, mvp) | ✗ | ✗ | **✓** |
| Classification péda correcte | — | 1/4 (25%) | **3/4 (75%)** |
| Contenu inventé dans restructure | ~3/15 | ~4/15 | ~5/21 |

---

## Bugs persistants v3

| Bug | Occurrences | Prompts |
|---|---|---|
| `\n` littéral dans JSON string | 1/21 | #13 |
| Contenu inventé dans `Contraintes` du restructure | 5/21 | #1, #5, #6, #10, #11 |
| Rôle absent en audit mais injecté dans restructure | 2/21 | #3, #8 |
| Classification péda encore douteuse | 1/21 | #7 |
| Clés avec accent (`qualité`, `ambiguités`) | 2/21 | #2, #16 |

---

## Gains confirmés v3 vs v2

- **Bug valeur libre audit résolu** : 90% des champs = `present`/`absent`/`inferred` (vs 60% en v2)
- **`gain_estime` débloqué** : 6 "fort" sur 21 (vs 1 sur 15 en v2)
- **Contraintes chiffrées** : "max 250 mots" (#18) conservé — règle 4 appliquée
- **Acronymes** : `llm`, `mvp` conservés sur #0 — règle 3 appliquée
- **Classification péda resserrée** : #14 (SSH) correctement reclassé en standard (était péda en v2)
- **`\n` littéraux** : 1 seul cas restant vs 2 en v2

---

## Priorités v4

1. **Contenu inventé dans restructure** — Qwen injecte des précisions absentes du prompt dans `Contraintes` (~5/21). Ajouter un exemple négatif explicite dans le system prompt.
2. **Rôle absent = pas de label `**Rôle :**`** — si `audit.role = "absent"`, omettre complètement la ligne du template.
3. **`\n` littéraux** — 1 occurrence restante sur #13, probablement un prompt long. Renforcer la règle 6.
4. **Classification #7** — YouTube/TikTok/podcast : demande de conseil pratique, pas pédagogique. Affiner les marqueurs d'exclusion.

Résumé de la progression v1 → v2 → v3 :

  - Audit schéma : 87% → 60% → 90% (v2 avait régressé, v3 corrige)
  - gain_estime varié : 0 → 1 → 6/21
  - Contraintes chiffrées : 0 → 0 → 100%
  - Acronymes conservés : ✗ → ✗ → ✓
  - Classification péda : — → 25% → 75%

  Bug principal restant pour v4 : Qwen invente encore du contenu dans **Contraintes :** quand elles sont absentes (~5/21), au lieu d'omettre la ligne. C'est le dernier gros chantier.