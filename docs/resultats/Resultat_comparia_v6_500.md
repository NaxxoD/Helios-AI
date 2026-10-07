# Résultat Comparia — Corpus v6 (500 prompts humains FR réels)

**Source** : ministere-culture/comparia-conversations (Etalab 2.0)
**Filtre** : premier tour humain, FR, 30–200 mots, non-tech
**Pipeline** : heuristique E1 + Qwen v6 (qwen3:8b local)

---

## Métriques globales

| Métrique | Valeur |
|---|---|
| Prompts traités | 500 |
| Qwen disponible | 458/500 (92%) |
| Réduction scaffold moy. | -2.0% |
| Réduction Qwen moy. | -23.0% |
| gain_estime faible | 372 (81%) |
| gain_estime moyen | 63 (14%) |
| gain_estime fort | 23 (5%) |

---

## Comparaison v5 vs v6 — même dataset (compar:IA, 500 prompts humains FR)

| Métrique | v5 / 500 | **v6 / 500** | Delta |
|---|---|---|---|
| Qwen disponible | 88% | **92%** | +4 pp |
| Réduction scaffold moy. | n/d | **-2.0%** | — |
| Réduction Qwen moy. | -19.2% | **-23.0%** | -3.8 pp |
| gain fort | n/d | **23 (5%)** | — |
| gain moyen | n/d | **63 (14%)** | — |
| gain faible | n/d | **372 (81%)** | — |

> v5 : run 2026-06-10, system prompt avec labels Markdown `**Rôle:**`.
> v6 : run 2026-06-11, amorces naturelles "Tu es / Je travaille sur / Tu dois".

---

## Cas notables — gain fort

**c084** (1439 chars) — -89.7% Qwen
> réecris ca sous forme de vecteur en R :    [1] "Brazil"                 "Paraguay"               "Mexico"               ...

**c392** (972 chars) — -88.5% Qwen
> cree une histoire d'un lion qui devient le roi de la jungle et qui est multicolor ummm et qui s'appel musafacree une his...

**c085** (1453 chars) — -81.5% Qwen
> réecris ca sous forme de vecteur : Show in New Window    [1] "Brazil"                 "Paraguay"               "Mexico" ...

**c098** (1389 chars) — -78.1% Qwen
> Peux-tu transformer cette partie de code :                     <!-- Repeat and Shuffle Buttons --> <ToggleButton x:Name=...

**c417** (715 chars) — -77.5% Qwen
> Commentaire littéraire du poème Hélène de Paul Valéry: "Azur ! C’est moi… Je viens des grottes de la mort Entendre l’ond...

## Cas edge — suroptimisation (Qwen plus verbeux)

**c000** — -72.9% (négatif)
> Le partage de données (open data, cloud collaboratif) favorise l’innovation et la transparence, mais...

**c001** — -10.8% (négatif)
> Serveur(s)	Société	Liens SRV-ABYLA-PROD	Stonal	 SRV-ABYLA-PROD	Stonal	 SRV-ABYLA-RECT	Stonal	 SRV-AP...

**c002** — -127.3% (négatif)
> [Contexte] : Vous êtes un expert en pédagogie en mathématiques, et vous allez aider un enseignant de...
