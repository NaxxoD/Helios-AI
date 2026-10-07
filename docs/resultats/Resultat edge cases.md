# Résultats — Edge Cases (A–D)
**Modèle :** qwen3:8b | **System prompt :** v4 | **Date :** 2026-06-08
**Objectif :** Identifier les lacunes restantes avant v5 sur 4 comportements non couverts par les prompts #-2 à #20

---

## Tableau des résultats

| # | Catégorie | Thème | Template | role | contraintes | format | gain | JSON | Bugs / Observations |
|---|---|---|---|---|---|---|---|---|---|
| A1 | Anglais formel | Market entry strategy EN | standard | inferred | present | inferred | moyen | ✓ | **Output en FR alors qu'input EN** ⚠ |
| A2 | Anglais tech | Redis cache microservices EN | standard | inferred | present | absent | moyen | ✓ | **Output en FR alors qu'input EN** ⚠ |
| A3 | Anglais SMS | Network error upload EN | standard | inferred | present | absent | moyen | ✓ | **Output en FR** ⚠ · "network error" conservé en EN ✓ |
| B1 | Code Python | Code review clean_logs | standard | inferred | present | absent | moyen | ✓ | Bloc Python ignoré dans restructuré ✓ |
| B2 | Code JS inline | Optimisation fonction calc() | standard | inferred | present | absent | **fort** | ✓ | Fonction JS ignorée ✓ · gain=fort correct ✓ |
| B3 | Code React | State useState null | **pedagogique** | inferred | present | inferred | moyen | ✓ | Classé péda car "explique la logique" ⚠ — demande de correction concrète ignorée |
| C1 | Court structuré | Recette tarte aux pommes | standard | inferred | present | inferred | **fort** | ✓ | Prompt 15 mots → gain=fort ⚠ règle <50 mots non appliquée |
| C2 | Court péda | Blockchain fonctionnement | **pedagogique** | absent | inferred | inferred | moyen | ✓ | Classification parfaite ✓ · Rôle absent = ligne omise ✓ |
| C3 | Court SMS | Chat miaule | standard | absent | absent | absent | moyen | ✓ | 8 mots SMS décodés ✓ · 4 composantes manquantes listées ✓ |
| D1 | Labels complets | Marathon nutrition plan | standard | present | present | present | moyen | ✓ | Labels respectés, aucune réécriture ✓ |
| D2 | Labels partiels | Espagnol professionnel | standard | inferred | present | present | moyen | ✓ | Deadline "fin de l'année" conservée ✓ |
| D3 | Labels informels | Team building télétravail | standard | inferred | present | absent | moyen | ✓ | Labels informels traduits en standard ✓ · "30 minutes" conservé ✓ |

---

## Catégorie A — Prompts en anglais

### Comportement observé
Qwen traduit systématiquement le `prompt_restructure` en français, quelle que soit la langue de l'input.

**A1 — input EN formel :**
```
Input  : "Dear Assistant, I am currently drafting a comprehensive market entry strategy..."
Output : **Rôle :** Stratège commercial.
         **Contexte :** Développement d'une stratégie de pénétration du marché...
```

**A3 — seul terme technique conservé EN :**
```
Input  : "it keeps saying network error when i try to upload an image"
Output : **Tâche :** Identifier la cause du problème et proposer une solution rapide.
         (le mot "network error" disparaît dans la reformulation)
```

### Verdict
✓ Le pipeline comprend et restructure correctement les prompts EN
✗ La langue de sortie n'est pas respectée — tout sort en FR

**Bug à corriger en v5 :** ajouter une règle explicite :
> Produire le `prompt_restructure` dans la même langue que le prompt input. Si l'input est en anglais, le template est en anglais.

---

## Catégorie B — Prompts avec du code

### Comportement observé — B1 et B2 ✓
Le code est ignoré dans le `prompt_restructure` — ni copié ni résumé. Seule la tâche est extraite.

**B1 — bloc Python :**
```
Input  : script clean_logs() + ```python...``` + "revue de code complète"
Output : **Tâche :** Réaliser une revue de code complète pour identifier les risques
         de fuite de mémoire, les erreurs potentielles et les pratiques à améliorer.
```
> Bloc de code absent du restructuré ✓ — comportement attendu

**B2 — fonction inline :**
```
Input  : "fonction JavaScript inline `function calc(a, b) {...}` qui ralentit le rendu"
Output : **Contexte :** Fonction inline calc(a, b) utilisée dans une boucle critique.
         **Tâche :** Optimiser la fonction pour accélérer le rendu.
```
> Signature de fonction conservée dans le contexte ✓ — pertinent

### Comportement B3 — classification discutable
```
Input  : "Mon code plante... const [user, setUser] = useState(null)...
          Tu peux m'expliquer la logique ET me donner la correction ?"
Output : template_type = "pedagogique"
```
Le marqueur "expliquer la logique" déclenche le template péda alors que la demande principale est une **correction de bug** (tâche concrète). Cas mixte expliquer + corriger non couvert.

**Comportement à clarifier en v5 :** quand une demande combine "explique + corrige/donne le code", classer standard (tâche concrète prime sur l'explication).

---

## Catégorie C — Prompts très courts

### C1 — 15 mots, gain=fort incorrect
```
Input  : "Donne-moi une recette de tarte aux pommes facile en 5 étapes." (15 mots)
Output : gain_estime = "fort"
```
Règle v4 : prompt < 50 mots → gain = "faible". Non appliquée. Confirme que `gain_estime` doit être calculé en backend.

### C2 — Classification parfaite ✓
```
Input  : "Explique-moi le fonctionnement de la blockchain s'il te plaît." (13 mots)
Output : template_type = "pedagogique", audit.role = "absent", ligne **Rôle:** omise ✓
```
Prompt ultra-court, un seul marqueur "explique" → correctement classé péda, rôle absent géré.

### C3 — SMS 8 mots ✓
```
Input  : "Slt pk mon chat miaule tt le tps ?" (8 mots)
Output : **Contexte :** Chat qui miaule constamment.
         **Tâche :** Expliquer pourquoi le chat miaule tout le temps.
         composantes_manquantes : ["role", "contraintes", "format", "qualite"]
```
Décodage SMS ✓ — 4 composantes manquantes correctement listées ✓ — gain=moyen au lieu de faible ⚠

---

## Catégorie D — Prompts déjà structurés

### Comportement général ✓
Qwen **respecte les labels existants** et ne les réécrit pas. Les contraintes et formats explicites sont conservés tels quels.

**D1 — labels complets :**
```
Input  : **Rôle :** Expert en nutrition sportive. **Contexte :** ... **Tâche :** ...
Output : **Rôle :** Expert en nutrition sportive. [identique]
         **Contexte :** Préparation du premier marathon en trois mois. [condensé ✓]
```
> audit.role = "present" ✓, audit.format = "present" ✓, audit.contraintes = "present" ✓

**D2 — labels partiels ("Mon Objectif", "Niveau actuel") :**
```
Input  : **Mon Objectif :** Je veux apprendre à parler un espagnol professionnel...
Output : **Contexte :** Apprendre à parler espagnol professionnel...
         **Contraintes :** ... objectif : maîtriser l'espagnol professionnel d'ici la fin de l'année. ✓
```
> Labels non-standard reconnus et convertis ✓ · deadline conservée ✓

**D3 — labels informels ("mon contexte actuel", "ce que je demande") :**
```
Input  : "ma contrainte bonus : il faut que ça prenne moins de 30 minutes"
Output : **Contraintes :** Activités durant 30 minutes max... ✓
```
> "30 minutes" conservé ✓ · Labels informels traduits en format standard ✓

---

## Bilan edge cases

| Catégorie | Score | Verdict |
|---|---|---|
| A — Anglais | 3/3 compris, 0/3 langue respectée | Compréhension ✓ / Langue ✗ |
| B — Code | 2/3 propres, 1/3 classification discutable | Quasi OK |
| C — Courts | 1/3 gain correct, 3/3 structure OK | Gain KO / Structure ✓ |
| D — Déjà structurés | 3/3 parfaits | ✓ |

---

## Nouveaux bugs identifiés pour v5

| # | Bug | Catégorie | Priorité |
|---|---|---|---|
| 5 | **Langue output** = toujours FR quelle que soit la langue input | A1/A2/A3 | Haute |
| 6 | **B3 classification** : expliquer+corriger → standard, pas péda | B3 | Moyenne |
| — | `gain_estime` < 50 mots = faible non appliqué | C1/C3 | → Backend (déjà prévu) |

---

## Liste consolidée des corrections v5

| # | Correction | Source |
|---|---|---|
| 1 | `gain_estime` → calcul Python backend, retiré du JSON Qwen | #-20 + C1/C3 |
| 2 | Absent = ligne omise pour **toutes** les composantes (contraintes, format) | v4 residuel |
| 3 | Contraintes chiffrées dans template péda (sécuriser la règle) | #18 v4 |
| 4 | Rôle over-inféré qwen3 — inferred seulement si contexte le justifie | #5/#10/#11 |
| 5 | **Langue output = langue input** — règle manquante | A1/A2/A3 |
| 6 | Prompt mixte expliquer+corriger → standard (tâche concrète prime) | B3 |

## Résumé

Ce que les edge cases ont révélé en plus des 4 corrections déjà prévues :

  - Langue — bug le plus inattendu : 100% des prompts EN sortent en FR. Pas de guard du tout dans le system prompt.
  Une ligne suffit à corriger.
  - Code — comportement correct sur B1/B2, B3 est le seul cas limite (expliquer + corriger = template péda alors que
  la correction prime).
  - Courts — structure OK, gain_estime confirme qu'il faut du backend.
  - Déjà structurés — catégorie la plus solide, zéro problème.

  Liste v5 consolidée : 6 corrections, dont 5 dans le system prompt et 1 côté backend.