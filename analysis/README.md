# Analysis — graphes de pitch Helios

Génère des figures qui vulgarisent la valeur d'Helios, **à partir de données réelles** du repo (aucun chiffre inventé).

## Lancer
```bash
cd backend
./.venv/Scripts/python.exe -m pip install -r ../analysis/requirements.txt
./.venv/Scripts/python.exe ../analysis/generate_pitch_graphs.py
# → figures dans analysis/figures/
```

Principe : **ne montrer que les données rendues possibles PAR Helios** (pas de
prix/CO₂ publics génériques que n'importe qui peut tracer). Thème : charte Helios sombre.

## Sources de données
| Figure | Donnée | Source | Statut |
|---|---|---|---|
| fig1 problème | % du prompt retiré (bruit) | `optimise()` sur `docs/10 Tests.txt` | réel (n=10) |
| fig2 tokens | avant/après par prompt | idem | réel (n=10) |
| fig3 radar qualité | 4 axes avant→après | `quality_note` | réel (n=10) |

## En attente (données d'usage réelles
- **fig5** économies cumulées sans/avec Helios (€/mois) — nécessite un scénario/volume d'usage réel.
- `results_v5.json` (n=35, Qwen) + `Prompt Tests.md` → fig2/fig3 plus solides que n=10.

## Retiré volontairement
- Prix $/M par modèle et CO₂ par modèle : données **publiques génériques**, pas la valeur propre d'Helios.

## Honnêteté (règles)
- Toujours légender **quel optimiseur** (−27% déterministe vs −52% Qwen) et **n**.
- Toute extrapolation = « hypothèse : … » visible sur la figure.
- CO₂ montré **par requête / à l'échelle**, jamais survendu par prompt.
