# Corpus de prompts mergé — banc de test de l'optimiseur

**Date** : 2026-06-10
**Projet** : Helios AI (Eco_IA_Tracker)
**But** : fusionner deux datasets Hugging Face en un corpus unifié de prompts réels,
pour tester l'optimiseur (`backend/utils/optimiseur.py`) à grande échelle.

---

## Contexte

L'optimiseur Helios est aujourd'hui testé sur `docs/10 Tests.txt` (10 prompts FR bavards).
On veut un corpus beaucoup plus large et varié pour :
1. Stresser la **classification en paliers** (code / doc / simple / complexe).
2. Valider l'**estimation des tokens de sortie** + contraintes.
3. Vérifier la **robustesse** (aucun crash du pipeline regex sur des prompts réels).
4. **Chiffrer la limite actuelle** des gains input/output sur de l'anglais.

### Datasets sources

| | `data-is-better-together/10k_prompts_ranked` | `fka/prompts.chat` |
|---|---|---|
| Lignes | 10 331 | 1 872 |
| Langue | anglais | anglais |
| Texte | `prompt` | `prompt` |
| Rôle | — | `act` |
| Catégorie | `topic`, `kind` (human/synthetic) | `type`, `for_devs` |
| Qualité | `avg_rating`, `num_responses` | — |

### ⚠️ Limite assumée

L'optimiseur strippe surtout de la politesse/verbosité **française**. Ces datasets sont
en anglais et déjà secs → les gains *input* seront faibles. C'est **voulu** : on cadre ce
corpus comme banc de classification + robustesse, et on chiffre la limite EN. La preuve du
gain CO₂ réel se fera plus tard sur un corpus FR bavard (hors scope).

---

## Schéma unifié

Un fichier, colonnes harmonisées :

| colonne | type | source |
|---|---|---|
| `prompt` | str (requis) | `prompt` des deux datasets |
| `source` | str | `"10k_ranked"` \| `"prompts_chat"` |
| `role` | str \| null | `act` (prompts.chat uniquement) |
| `category` | str \| null | `topic` (10k) / `type` (prompts.chat) |
| `kind` | str \| null | `human`\|`synthetic` (10k) / `dev`\|`general` dérivé de `for_devs` (prompts.chat) |
| `avg_rating` | float \| null | `avg_rating` (10k uniquement) |
| `num_responses` | int \| null | `num_responses` (10k uniquement) |

---

## Traitement au merge

1. **Filtrage** : drop des prompts vides / null, `strip()` des espaces.
2. **Dédup** : sur le texte normalisé (lowercase + espaces collapsés). Le 10k contient
   des doublons, et un recouvrement entre les deux datasets est possible. En cas de
   doublon, on garde la ligne avec le plus de métadonnées (priorité `10k_ranked`).
3. **Logging** : nombre de lignes en entrée, droppées (vides), dédupliquées, et total final.

---

## Livrables

```
analysis/
  build_corpus.py            # télécharge (datasets), harmonise, dédup, écrit parquet+jsonl
  run_optimizer_corpus.py    # charge le parquet, applique optimise(), récap stats
  corpus/
    merged_prompts.parquet   # corpus typé complet
    merged_sample.jsonl      # ~30 lignes lisibles pour inspection à l'œil
    optimizer_report.json    # sortie de run_optimizer_corpus.py
```

### `build_corpus.py`
- Charge les deux datasets via la lib `datasets` (HF).
- Mappe chacun vers le schéma unifié, concatène (pandas), filtre, déduplique.
- Écrit `merged_prompts.parquet` (pyarrow) + échantillon `merged_sample.jsonl`.
- Affiche le récap de nettoyage.

### `run_optimizer_corpus.py`
- Charge `optimise()` en isolé (même technique d'import que `generate_pitch_graphs.py`).
- Applique `optimise()` à chaque prompt, capture les erreurs (robustesse).
- Agrège : distribution des paliers, tokens avant/après, gain moyen/médian input+output,
  gain par `source` et par `category`, nombre de crashes.
- Écrit `optimizer_report.json`.

---

## Hors scope
- Génération d'un corpus FR bavard (test du gain CO₂ réel) — projet séparé.
- Ajout de règles de politesse anglaises à l'optimiseur — décision séparée selon le report.
- Publication du corpus mergé sur le Hub HF.

---

## Critères de succès
- `merged_prompts.parquet` produit, ~12k lignes (moins les doublons), schéma respecté.
- `run_optimizer_corpus.py` tourne sur tout le corpus **sans crash non capturé**.
- `optimizer_report.json` donne une distribution des paliers et les gains chiffrés par source.
