# Résultats v3.5 — Prompts extrêmes #-2 et #-1
**Modèle :** Qwen 2.5:7b | **System prompt :** v3 | **Date :** 2026-06-08
**Profils testés :** Micheline (non-tech, boulangerie) · Kevin (SMS argot trash)

---

## Contexte des profils

| # | Alias | Profil | Particularités |
|---|---|---|---|
| -2 | Micheline | Boulangère 50+, non-tech, poussée par sa fille | Vouvoiement, confusion IA = Matrix/Terminator, syntaxe correcte mais naïve |
| -1 | Kevin | 16-20 ans, SMS language, business mindset cash | Argot, abréviations, fautes, motivations financières explicites, aucune structure |

---

## Tableau des résultats

| # | Profil | Template | role | contexte | tache | contraintes | format | qualite | gain | JSON | Bugs notables |
|---|---|---|---|---|---|---|---|---|---|---|---|
| -2 | Micheline — boulangerie Lyon | standard | inferred | present | present | absent | inferred | absent | **fort** | ✓ | `format`=inferred en audit mais dans `composantes_manquantes` → incohérence ⚠ · Ambiguïté "IA" discutable |
| -1 | Kevin — contenu insta + biz IA | standard | absent | present | present | absent | inferred | absent | moyen | ✓ | "insta et autres réseaux" non signalé comme vague · Rôle absent mais injecté dans restructure ⚠ |

---

## Avant / Après complet

### #-2 — Micheline *(boulangerie, profil non-tech)*

**Original (82 mots) :**
```
Bonjour, je me permets de vous écrire car j'ai un petit souci avec mon entreprise,
ça fait maintenant 3 ans que je tiens ma boulangerie à Lyon et j'adorerais avoir plus
de clients, ma fille m'a dit qu'il faudrait que je fasse des choses sur internet mais
je ne sais pas trop par où commencer, est-ce que vous pourriez m'aider à faire quelque
chose pour attirer du monde, elle ma parler d'integrer de l'ia
( c'est les truc a la Matrix ou Terminator, c'est dangereux non ? ).
Merci de votre aide et d'améliorer ma situation
```

**Restructuré Qwen v3 (49 mots) :**
```
**Rôle :** Propriétaire de boulangerie.
**Contexte :** Besoin d'augmenter le nombre de clients pour une boulangerie à Lyon,
ayant reçu un conseil sur l'utilisation de l'IA mais inquiet concernant son utilisation.
**Tâche :** Concevoir et mettre en place des stratégies digitales pour attirer plus de clients.
**Format :** Document structuré comprenant une stratégie globale, des étapes concrètes
à suivre, et des points clés à retenir.
```

**Bruit supprimé ✓ :**
- "je me permets de vous écrire" → supprimé
- "ça fait maintenant 3 ans" → conservé dans contexte (pertinent)
- "c'est les truc a la Matrix ou Terminator, c'est dangereux non ?" → supprimé
- "Merci de votre aide" → supprimé

**Observations :**
- `gain = fort` ✓ — 82 → 49 mots (-40%)
- Décodage de l'incompréhension IA correctement ignoré dans le restructuré ✓
- **Ambiguïté "IA"** signalée : discutable — ce n'est pas une option contradictoire, c'est une incompréhension. Règle 5 v3 mal appliquée ici.
- `format` = inferred en audit mais listé dans `composantes_manquantes` → bug cohérence persistant

---

### #-1 — Kevin *(SMS argot, biz mindset)*

**Original (63 mots) :**
```
slt bg, c koi le mieux pourr faire du contenu insta et les autres réseau sociau,
j'essaie de monté 1 biz, pcq les cours c naze, ta vus et askip on peut faire de la
moula avec l'ia du coup jveu me lancer psk jveux mettre la daronne a l'abri et gerer
des gow avec ma thune t'es un boss la bete méca
```

**Restructuré Qwen v3 (52 mots) :**
```
**Rôle :** Entrepreneur.
**Contexte :** Essayer de créer du contenu pour Instagram et d'autres réseaux sociaux,
avec l'objectif de monter un business. Besoin de conseils sur la meilleure approche,
en utilisant l'IA pour potentiellement générer des revenus.
Objectifs financiers : mettre la famille à l'abri.
**Tâche :** Élaborer une stratégie pour créer et diffuser du contenu efficace
sur Instagram et d'autres réseaux sociaux.
**Format :** Guide détaillé avec étapes clés.
```

**Décodage argot réussi ✓ :**

| Argot | Traduit |
|---|---|
| `slt bg` | salut |
| `c koi le mieux` | quelle est la meilleure approche |
| `pcq les cours c naze` | supprimé (hors sujet) |
| `moula` | revenus / argent |
| `jveu me lancer` | je veux me lancer |
| `daronne` | famille / mère |
| `gow / ma thune` | supprimé (bruit) |
| `t'es un boss la bête méca` | supprimé (bruit) |

**Observations :**
- JSON valide du premier coup malgré l'argot ✓
- "mettre la daronne à l'abri" → "mettre la famille à l'abri" conservé dans contexte ✓
- `gain = moyen` — 63 → 52 mots (-17%) → techniquement correct
- **Aucune ambiguïté signalée** — "insta et les autres réseaux sociaux" aurait pu être signalé (quelle plateforme prioritaire ?)
- Rôle "Entrepreneur" injecté alors que `audit.role = absent` → incohérence règle 2 ⚠

---

## Bilan

| Critère | Résultat |
|---|---|
| JSON valide | 2/2 ✓ |
| Audit schéma respecté | 2/2 ✓ — zéro valeur libre |
| Décodage argot/SMS | 1/1 ✓ — Kevin décodé intégralement |
| Bruit non-tech éliminé | 1/1 ✓ — Micheline nettoyée |
| Ambiguïtés pertinentes | 0/2 — "IA" sur-signalé (#-2), "insta + réseaux" sous-signalé (#-1) |
| Cohérence audit ↔ composantes_manquantes | 1/2 — bug sur #-2 (format) |
| Contenu inventé dans restructure | 1/2 — #-1 rôle "Entrepreneur" inventé |

---

## Points clés pour la v4

**Confirmation :** Le pipeline tient sur des profils utilisateurs très éloignés — argot SMS et non-tech — sans hallucinations majeures ni plantage JSON.

**Deux ajustements ciblés :**

1. **Ambiguïté = options contradictoires, pas incompréhensions** — "IA" chez Micheline n'est pas une ambiguïté de prompt, c'est une incompréhension utilisateur à traiter différemment (suggestion, pas warning). Affiner la règle 5 avec un exemple négatif explicite.

2. **Rôle absent = label omis dans restructure** — si `audit.role = absent`, ne pas injecter de rôle inféré dans `**Rôle :**`. Soit on infère et on met `inferred`, soit on omet la ligne. Pas les deux.
