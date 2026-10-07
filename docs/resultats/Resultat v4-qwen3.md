# Résultats v4 — qwen3:8b vs qwen2.5:7b-instruct
**Modèle :** qwen3:8b (Q4_K_M, 5.2GB) | **System prompt :** v4 | **Date :** 2026-06-08
**RAM Tour :** 16GB / 7.5GB libres — modèle chargé sans swap ✓

---

## Tableau des résultats — qwen3:8b

| # | Thème | Template | role | contexte | tache | contraintes | format | qualite | gain | JSON | Bugs notables |
|---|---|---|---|---|---|---|---|---|---|---|---|
| -2 | Micheline — boulangerie | standard | inferred | present | present | present | absent | absent | moyen | ✓ | Ambiguïté "IA = Matrix" non signalée ✓ · Contraintes inférées pertinentes ✓ |
| -1 | Kevin — SMS biz IA | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | Décodage argot + contexte financier bien capturé ✓ |
| 0 | Agent IA mémoriel *(humain)* | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | "LLM" avec majuscules (vs "llm" attendu) ⚠ · Propre sinon ✓ |
| 1 | Coach burnout | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | Propre ✓ |
| 2 | Marque éco + roadmap | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | Ambiguïtés 3 projets non signalées · Propre ✓ |
| 3 | SEO bougies | standard | inferred | present | present | present | absent | absent | moyen | ✓ | Contraintes deadline "fin d'année" bien conservée ✓ |
| 4 | Développement perso vague | pedagogique | inferred | present | present | present | inferred | absent | moyen | ✓ | Propre ✓ |
| 5 | Communication interne | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | **Rôle inféré** alors qu'absent du prompt ⚠ · Contraintes inférées pertinentes |
| 6 | Scraping voitures | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | Python/Node ambiguïté signalée dans Contraintes ✓ · Non résolue ✓ |
| 7 | YouTube/TikTok/podcast | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | Classification standard ✓ (v4-7b classait péda) · Ambiguïtés bien détectées ✓ |
| 8 | Commerce / salon de thé | standard | inferred | present | present | present | present | absent | moyen | ✓ | Ambiguïté boutique/salon non signalée mais contexte préservé ✓ |
| 9 | App micro-journaling | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | React/Flutter/Firebase dans Contraintes sans choisir ✓ |
| 10 | Post LinkedIn coaching | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | **Rôle inféré** alors qu'absent du prompt ⚠ |
| 11 | Recette poulet/riz | standard | inferred | present | present | absent | inferred | absent | moyen | ✓ | **Rôle inféré** alors qu'absent ⚠ · contraintes=absent correct ✓ |
| 12 | Blog productivité télétravail | standard | inferred | present | present | present | present | absent | moyen | ✓ | Propre ✓ |
| 13 | Doc API Swagger | pedagogique | inferred | present | present | present | inferred | absent | moyen | ✓ | Classification péda correcte ✓ · JSON propre ✓ |
| 14 | Sécuriser SSH | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | Classification standard correcte ✓ (v4-7b classait péda) · Contraintes techniques précises ✓ |
| 15 | Analyse Meta Ads ROAS | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | Format "Tableau + liste" inféré ✓ · Propre ✓ |
| 16 | Titres blog tarte tatin | standard | present | present | present | present | present | absent | **fort** | ✓ | 5/6 champs present/inferred ✓ · gain fort correct ✓ |
| 17 | Prospection photographe | standard | inferred | present | present | present | present | absent | moyen | ✓ | Coach business bien inféré ✓ |
| 18 | Comptabilité bilan/résultat | pedagogique | absent | present | present | present | present | absent | **fort** | ✓ | **"max 250 mots" conservé ✓** · Rôle absent = pas de ligne ✓ |
| 19 | Dire non / communication | standard | inferred | present | present | present | inferred | absent | moyen | ✓ | "3 exemples" conservé dans Contraintes ✓ |
| 20 | Planning télétravail | standard | inferred | present | present | present | present | absent | moyen | ✓ | Propre ✓ |

---

## Comparatif direct qwen2.5:7b-instruct vs qwen3:8b

| Critère | 7b-instruct | **qwen3:8b** | Δ |
|---|---|---|---|
| JSON valide 23/23 | 21/23 (91%) | **23/23 (100%)** | +2 |
| Audit schéma strict | 91% | **100%** | +9pts |
| `gain_estime` varié | 13 fort / 23 (57%) | **2 fort / 23 (9%)** | -48pts ← régression |
| Ambiguïté "IA = peur" (#-2) | signalée ⚠ | **non signalée ✓** | +1 |
| "max 250 mots" conservé (#18) | perdu ⚠ | **conservé ✓** | +1 |
| Classification SSH standard (#14) | péda ⚠ | **standard ✓** | +1 |
| `\n` littéraux | 1 cas | **0 cas** | +1 |
| Contenu inventé dans Contraintes | ~6/23 | **~3/23** | +3 |
| Rôle inféré quand audit=absent | 5/5 omis ✓ | 3/5 injectés ⚠ | -2 |
| Cohérence audit ↔ composantes_manquantes | ~88% | **~96%** | +8pts |

---

## Exemple emblématique — #18 Comptabilité "max 250 mots"

**qwen2.5:7b-instruct (v4) :**
```
Explique les grands principes du bilan et du compte de résultat en 5 sections :
1) Définition simple ...
[contrainte "max 250 mots" absente]
```

**qwen3:8b (v4) :**
```
Explique bilan et compte de résultat en 5 sections :
1) Définition simple
...
Contraintes :
* langage accessible, exemples concrets, pas de jargon non expliqué
* maximum 250 mots                          ← conservé ✓
* format : titres + listes, résumé en 5 lignes, 5 questions de révision en fin
```

---

## Points forts qwen3:8b

| Point | Détail |
|---|---|
| **Zéro erreur JSON** | 23/23 sans parse error, aucun `\n` littéral |
| **Audit 100% schéma** | Tous les champs = `present`/`absent`/`inferred` sans exception |
| **Contraintes riches** | Infère des contraintes pertinentes même quand absentes (ex : #6 "Python ou Node.js à préciser") |
| **Classification modèles** | Standard/péda presque toujours correct (#7 standard ✓, #14 standard ✓) |
| **Contraintes chiffrées** | "max 250 mots", "3 exemples", "5-6 pistes" tous conservés |
| **Ambiguïtés propres** | Zéro faux positif — "IA = Matrix" non signalé ✓ |

---

## Point faible principal — `gain_estime` bloqué sur "moyen"

**Seuls 2/23 = "fort"** (#16 et #18) — qwen3:8b refuse d'évaluer "fort" même sur des réductions >50%.

Exemples clairs où "fort" était attendu mais "moyen" retourné :
- #11 : 35 mots → ~20 mots (-43%) → devrait être "fort"
- #12 : 142 mots → ~30 mots (-79%) → devrait être "fort"
- #19 : 89 mots → ~40 mots (-55%) → devrait être "fort"

**Cause probable :** qwen3 n'effectue pas le comptage réel des mots — il applique "moyen" comme valeur par défaut sécurisée. La règle 7 du system prompt v4 n'est pas suffisamment contraignante pour ce modèle.

---

## Régression mineure — rôle inféré quand audit.role = absent

Sur #5, #10, #11 : `audit.role = inferred` alors que le rôle n'était pas dans le prompt, et la ligne `**Rôle :**` est présente dans le restructuré. En v4 avec 7b-instruct, ces cas avaient le rôle absent et la ligne omise. qwen3 infère "trop" facilement.

---

## Ressources

| Métrique | Valeur |
|---|---|
| RAM utilisée pendant le batch | ~14.5GB (pic) |
| RAM libre restante | ~1.5GB (serré mais stable) |
| Temps moyen par prompt | ~8-12 secondes |
| Crashes / OOM | 0 |

**Conclusion :** qwen3:8b tient sur 16GB mais sans marge. Fermer Chrome/autres apps avant de lancer un batch complet.

---

## Verdict final — quel modèle pour v5 ?

| Critère | Recommandation |
|---|---|
| Qualité JSON et schéma | **qwen3:8b** ← sans discussion |
| Contraintes et contenu | **qwen3:8b** ← plus précis, moins d'inventions |
| `gain_estime` | **7b-instruct** ← qwen3 bloqué sur moyen |
| RAM / stabilité | **7b-instruct** ← plus confortable sur 16GB |

**Recommandation :** passer à qwen3:8b pour la v5 avec un correctif fort sur `gain_estime` — forcer un exemple de comptage explicite dans le system prompt. Si le bug persiste sur qwen3, envisager un calcul côté backend qui override le champ.
