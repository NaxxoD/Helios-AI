# Résultats v2.5 — Prompts #16-20
**Modèle :** Qwen 2.5:7b | **System prompt :** v2 | **Date :** 2026-06-08

---

## Tableau des résultats

| # | Thème | Template | role | contexte | tache | contraintes | format | qualite | gain | JSON | Bugs notables |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 16 | Titres blog tarte tatin | standard | `⚠ valeur libre` | present | present | present | absent | — | moyen | ✗ parse | `audit.role` = "copywriter professionnel" (non-schéma) + `\n` dans string |
| 17 | Prospection photographe freelance | standard | `⚠ valeur libre` | present | present | absent | `⚠ valeur libre` | — | moyen | ✗ parse | `audit.role` = "coach business", `audit.format` = "tableau" (non-schéma) + `\n` dans string |
| 18 | Comptabilité bilan/résultat | pedagogique | present | present | present | present | absent | — | moyen | ✓ | `composantes_manquantes` = ["format"] mais `audit.format` = "absent" ✓ — cohérent. Pas de labels **Rôle/Tâche** dans restructure (template péda différent) ✓ |
| 19 | Dire non / communication bienveillante | standard | `⚠ valeur libre` | `⚠ "présent"` | `⚠ "présent"` | `⚠ valeur libre` | `⚠ "présent"` | — | moyen | ✓ | Tous les champs audit = valeurs libres. Restructure correct et concis ✓ |
| 20 | Planning télétravail heure/heure | standard | `⚠ "inferred (coach)"` | `⚠ string longue` | `⚠ string longue` | `⚠ valeur libre` | `⚠ "present (heure...)"` | — | **faible** | ✓ | Audit = descriptions au lieu de present/absent/inferred. `gain=faible` correct : prompt déjà bien formé ✓ |

> `⚠ valeur libre` = le champ contient une valeur textuelle au lieu de `"present"` / `"absent"` / `"inferred"`

---

## Prompt restructuré — avant / après

### #16 — Titres blog (JSON non parsé, données depuis raw)
**Original (73 mots) :**
> Blog de cuisine, recette de tarte tatin aux pommes rédigée. Besoin de titres accrocheurs mais pas mensongers. Copywriter professionnel. Liste de 5 propositions sous forme de puces.

**Restructuré (Qwen) :**
```
Rôle : copywriter professionnel
Contexte : Rédiger une liste de titres accrocheurs pour un article de cuisine sur la tarte tatin aux pommes.
Tâche : Proposer exactement 5 propositions différentes sous forme de puces.
Contraintes :
* Accrocheur mais pas mensonger
* Liste sous forme de puces
```
**Réduction estimée :** ~35% | **Labels présents :** ✓

---

### #17 — Prospection photographe (JSON non parsé, données depuis raw)
**Original (84 mots) :**
> Lancement activité photographe mariage freelance. Besoin méthode prospection locale le mois prochain. Coach business. Tableau action / canal.

**Restructuré (Qwen) :**
```
Rôle : coach business
Contexte : lancement d'activité de photographe de mariage en freelance, besoin de prospecter des clients locaux le mois prochain sans passer toutes les nuits dessus.
Tâche : organiser une méthode claire pour la prospection locale sous forme d'un tableau avec actions à faire et canaux utilisés.
Format : tableau
```
**Réduction estimée :** ~40% | **Labels présents :** ✓

---

### #18 — Comptabilité bilan/résultat ✓
**Original (85 mots) :**
> Réunion partenaires étrangers dans 2 semaines. Part de zéro en comptabilité. Professeur pédagogue. Bilan + compte de résultat, sans jargon, max 250 mots.

**Restructuré (Qwen) :**
```
Explique les grands principes du bilan et du compte de résultat simplement, sans jargon.
Définitons d'abord le bilan puis comment il est construit avec des exemples concrets.
Ensuite, expliquons le compte de résultat en détail, avec aussi des exemples pratiques.
Évoquons les limites possibles et les points clés à retenir pour bien comprendre ces concepts fondamentaux.
```
**Réduction estimée :** ~50% | **Contrainte 250 mots perdue** ⚠

---

### #19 — Dire non / communication bienveillante ✓
**Original (89 mots) :**
> Tendance à accepter tous les projets, débordé et fatigué. Apprendre à dire non sans vexer. Communication bienveillante. 3 phrases types prêtes à l'emploi.

**Restructuré (Qwen) :**
```
Donne-moi des conseils de communication bienveillante pour apprendre à dire non.
Rédige-moi 3 exemples de phrases types prêtes à l'emploi que je pourrai utiliser dès demain.
```
**Réduction estimée :** ~75% | **Très propre, essentiel conservé ✓**

---

### #20 — Planning télétravail ✓
**Original (94 mots) :**
> Travail à distance, distractions (téléphone, réseaux sociaux, rangement). Perte de concentration sur tâches prioritaires. Planning journée type, travailleur indépendant, heure par heure.

**Restructuré (Qwen) :**
```
Rôle : coach
Contexte : travail à distance, distractions, gestion du temps
Tâche : Concevoir un planning de journée type idéal pour un travailleur indépendant
Contraintes : langage accessible, exemples concrets, pas de jargon non expliqué
Format : heure par heure, du matin au soir
```
**Réduction estimée :** ~55% | **`gain=faible` attribué alors que ~55% supprimés — bug calcul persistant**

---

## Bilan #16-20

| Métrique | Résultat |
|---|---|
| JSON parseable | 3/5 (#18, #19, #20) — `\n` dans string = parse error sur #16 et #17 |
| Audit schéma respecté | 0/5 — tous les champs ont des valeurs libres |
| gain_estime varié | 1/5 (#20 = faible) — 4/5 encore sur "moyen" |
| Ambiguïtés pertinentes | 5/5 — aucune ambiguïté, aucune inventée ✓ |
| Template pédagogique correct | 1/1 (#18 ✓) |
| Contraintes perdues dans restructure | 1/5 (#18 — contrainte 250 mots non transmise) |
| Labels **Rôle/Tâche/Format** présents | 4/5 — absents seulement sur #18 (template péda) ✓ |

---

## Observations clés

**Régression confirmée :** le bug `audit.valeurs libres` est **systématique** sur les prompts bien formés avec rôle explicite. Dès que l'utilisateur écrit "tu es un copywriter" ou "agis comme un coach", Qwen copie la valeur dans le champ audit au lieu de mettre `"present"`.

**Bug nouveau :** les `\n` littéraux dans `prompt_restructure` causent des erreurs de parsing JSON sur #16 et #17. À corriger avec un rappel dans le system prompt : pas de retours à la ligne littéraux dans les strings JSON.

**Point positif :** sur les prompts déjà structurés (#16-20), le nettoyage du bruit est efficace et les labels **Rôle/Contexte/Tâche** sont bien remplis avec le bon contenu.

**Priorités v3 :**
1. Forcer `audit.*` = `"present"` / `"absent"` / `"inferred"` — exemples contre-exemples dans le system prompt
2. Interdire les `\n` littéraux dans `prompt_restructure`
3. Ne pas perdre les contraintes chiffrées (ex : "max 250 mots")
