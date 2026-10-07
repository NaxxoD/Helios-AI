# Résultat Comparia — Corpus v6 (100 prompts humains FR réels)

**Source** : ministere-culture/comparia-conversations (Etalab 2.0)
**Filtre** : premier tour humain, FR, 30–200 mots, non-tech
**Pipeline** : heuristique E1 + Qwen v6 (qwen3:8b local)

---

## Métriques globales

| Métrique | Valeur |
|---|---|
| Prompts traités | 100 |
| Qwen disponible | 94/100 (94%) |
| Réduction scaffold moy. | -2.7% |
| Réduction Qwen moy. | --27.8% |
| gain_estime faible | 78 (83%) |
| gain_estime moyen | 11 (12%) |
| gain_estime fort | 5 (5%) |

---

## Corpus v6 (36 prompts IA) — comparaison

| Dataset | Qwen dispo | Réd. scaffold | Réd. Qwen | gain fort |
|---|---|---|---|---|
| Corpus v6 (IA/synth) | 36/36 (100%) | -10.2% | -40.6% | 1 (3%) |
| Comparia (humain réel) | 94/100 | -2.7% | --27.8% | 5 (5%) |

---

## Cas notables — gain fort

**c068** (1077 chars) — -61.0% Qwen
> Ci-dessous la logique d'une route qui gère la création d'un objet 'Thing' puis à titre informatif la déclaration du modè...

**c006** (487 chars) — -55.4% Qwen
> peux tu compléter cette liste de marques de chaussures de trail par d'autres que j'aurai oubliés, dans tes propositions,...

**c098** (712 chars) — -53.9% Qwen
> d0@Uzairs-MacBook-Pro Web-app % npm update npm ERR! code ERESOLVE npm ERR! ERESOLVE unable to resolve dependency tree np...

**c008** (467 chars) — -52.6% Qwen
> peux tu compléter cette liste de marques de chaussures de trail par d'autres que j'aurai oubliés, mon instruction est de...

**c047** (948 chars) — -41.9% Qwen
> Le contexte est le suivant: mon boss me demande en accord avec le PDG de prendre un périmètre de responsabilité accrue e...

## Cas edge — suroptimisation (Qwen plus verbeux)

**c000** — -20.6% (négatif)
> Le partage de données (open data, cloud collaboratif) favorise l’innovation et la transparence, mais...

**c001** — -14.4% (négatif)
> Serveur(s)	Société	Liens SRV-ABYLA-PROD	Stonal	 SRV-ABYLA-PROD	Stonal	 SRV-ABYLA-RECT	Stonal	 SRV-AP...

**c002** — -68.8% (négatif)
> [Contexte] : Vous êtes un expert en pédagogie en mathématiques, et vous allez aider un enseignant de...
