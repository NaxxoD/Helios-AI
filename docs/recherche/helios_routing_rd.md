# Helios — R&D Routing Model × Effort
> Réflexion personnelle post-soutenance — non concertée avec l'équipe  
> À valider avec co-auteur avant toute décision d'implémentation  
> Date : 2026-06-03

---

## Contexte

Le MVP Helios intègre un système de routing automatique vers le modèle selon la requête, sans appel API pour la détection. L'objectif de cette R&D est d'étendre ce routing pour calibrer non seulement le **modèle** mais aussi l'**effort** associé, de façon transparente pour l'utilisateur non-tech.

---

## 1. Modèles et granularité d'effort réelle

La grille d'effort n'est pas uniforme entre les modèles — chaque provider expose une granularité différente.

### Anthropic

| Modèle | Niveaux d'effort | Particularité |
|---|---|---|
| Haiku | `off` / `on` | Pas de granularité — thinking activé ou non |
| Sonnet | `low` · `medium` · `high` · `max` | Paramètre `effort` API |
| Opus | `low` · `standard` · `high` · `xhigh` · `max` | `xhigh` entre high et max (depuis Opus 4.7) |

### OpenAI

| Modèle | Paramètre | Niveaux |
|---|---|---|
| o-series (o3, o4-mini) | `reasoning_effort` | `low` · `medium` · `high` |
| GPT-4o standard | — | Pas de paramètre d'effort exposé |

### Google Gemini

| Modèle | Paramètre | Niveaux |
|---|---|---|
| Gemini Pro/Flash | `thinking_config` + `thinking_budget` | Budget en tokens (0 → N) — pas sémantique |

Le routing ne peut donc pas être uniforme entre providers — une **couche d'abstraction** est nécessaire pour mapper un niveau d'effort sémantique vers le paramètre natif de chaque provider.

```python
def build_effort_params(provider, model, effort_level):
    if provider == "anthropic":
        return {"effort": effort_level}
    elif provider == "openai" and is_reasoning_model(model):
        return {"reasoning_effort": effort_level}  # low/medium/high seulement
    elif provider == "google":
        budget = {"low": 1024, "medium": 8192, "high": 32768}.get(effort_level, 8192)
        return {"thinking_config": {"thinking_budget": budget}}
    else:
        return {}  # provider sans support effort — ignoré silencieusement
```

---

## 2. Grille de décision model × effort par tâche

Règle générale (indépendante du provider) :

| Profil tâche | Modèle | Effort | Exemple |
|---|---|---|---|
| Trivial / reformulation | Haiku | off | Rediriger un mail |
| Rédaction simple | Haiku | on | Résumer un texte court |
| Rédaction standard / code | Sonnet | medium | Rédiger un mail professionnel |
| Document dense / analyse | Sonnet | high | Bilan de société, rapport |
| Architecture / algo | Sonnet | high | Conception système |
| Stratégie / décision critique | Sonnet ou Opus | high / xhigh | Arbitrage business, hypothèses |
| Déblocage profond | Opus | xhigh | Blocage architectural confirmé |

> **Règle écologique** : plus le routing est statique (heuristique pure), moins il consomme. Objectif : activer la sémantique uniquement sur les cas ambigus (~15-20% des requêtes).

---

## 3. Architecture de routing à deux étages

### Vue d'ensemble

```
Requête user
    ↓
┌─────────────────────────────────────┐
│  Étage 1 — Heuristique (statique)   │  ~0 CO₂
│  Score par keywords                 │
│  Cas clair → route direct (80%)     │
│  Cas ambigu → étage 2              │
└─────────────────────────────────────┘
    ↓ (conflits uniquement)
┌─────────────────────────────────────┐
│  Étage 2 — Sémantique local         │  CO₂ marginal
│  Modèle Ollama spécialisé           │
│  Score sémantique affine            │
│  model + effort                     │
└─────────────────────────────────────┘
    ↓
Routing final → Provider API
(Anthropic / OpenAI / Google)
```

### Étage 1 — Heuristique keyword

Deux sous-scores indépendants :

**Score modèle** — keywords par niveau :
```python
MODEL_KEYWORDS = {
    "haiku":  ["traduis", "reformule", "résume", "redirige", "convertis", "formate", "extrait"],
    "sonnet": ["rédige", "écris", "explique", "analyse", "compare", "prépare", "génère", "document"],
    "opus":   ["stratégie", "architecture", "arbitrage", "critique", "évalue", "hypothèse", "bilan complexe"],
}
```

**Score effort** — keywords orthogonaux au modèle :
```python
EFFORT_SIGNALS = {
    "off":    ["reformule", "traduis", "copie", "redirige", "formate"],
    "on":     ["résume", "structure", "extrait les points"],
    "low":    ["vite", "rapide", "simple", "court", "liste"],
    "medium": ["rédige", "prépare", "explique", "propose"],
    "high":   ["document", "rapport", "complet", "détaillé", "professionnel", "bilan", "analyse"],
    "max":    ["exhaustif", "approfondi", "critique", "décision finale"],
}
```

**Garde-fous cross-étages** :
```python
# Haiku ne supporte pas high/max → degrade proprement
if model == "haiku" and effort in ("high", "max"):
    effort = "on"

# Opus/low = gaspillage inverse
if model == "opus" and effort == "low":
    effort = "standard"
```

**Limite structurelle** : les cas mixtes type *"rédige une stratégie"* génèrent un conflit systémique — `rédige` → sonnet/medium vs `stratégie` → opus/high. L'heuristique ne peut pas trancher sans comprendre la relation entre les mots. C'est le déclencheur de l'étage 2.

### Étage 2 — Sémantique local (Ollama sur VPS)

En cas de conflit détecté à l'étage 1, un modèle Ollama spécialisé selon le domaine probable affine le routing.

**Modèles spécialisés par domaine** — source : https://ollama.com/library

| Domaine détecté | Modèle Ollama | Taille | Route finale |
|---|---|---|---|
| SQL / données | `sqlcoder` | ~4GB | Sonnet/Medium |
| Code général | `qwen2.5-coder:3b` | ~2GB | Sonnet/High |
| Rédaction simple | `qwen2.5:1.5b` | ~1GB | Haiku/On |
| Document formel / stratégie | `qwen2.5:3b` | ~2GB | Sonnet/High |
| Ambiguïté totale (fallback) | `qwen2.5:3b` | ~2GB | Sonnet/Medium |

> Référence complète des modèles disponibles : **https://ollama.com/library**

**Score final combiné** :
```python
score_final = (
    poids_heuristique * score_heuristique +
    poids_semantique  * score_semantique
)
# poids_heuristique = 0.9 si cas clair / 0.4 si conflit
# poids_semantique  = 0.1 si cas clair / 0.6 si conflit
```

Plus le cas est ambigu, plus le sémantique prend le dessus.
Plus c'est clair, plus l'heuristique reste souveraine — le VPS reste silencieux.

---

## 4. Exemples concrets

### Gertrude (profil non-tech, secrétaire)

| Requête | Étage 1 | Étage 2 | Résultat |
|---|---|---|---|
| "redirige ce mail à Paul" | haiku / off — clair | — | Haiku/Off |
| "rédige un mail professionnel pour..." | haiku↔sonnet conflit | qwen2.5:1.5b → rédaction | Sonnet/Medium |
| "fais le bilan de la société" | sonnet/high — clair | — | Sonnet/High |

### Jean-Michel (profil tech)

| Requête | Étage 1 | Étage 2 | Résultat |
|---|---|---|---|
| "optimise ce prompt SQL pour réduire la latence" | conflit optimise↔SQL | sqlcoder → SQL technique | Sonnet/Medium |
| "explique cette architecture microservices" | sonnet/high — clair | — | Sonnet/High |

---

## 5. Lien avec le cercle vertueux Helios

Le routing intelligent devient un argument de valeur produit :

- **Optimiseur tokens** (existant) + **routing effort** (v2) = deux leviers combinés de réduction du coût réel
- Les économies générées alimentent le wallet user → l'utilisateur non-tech bénéficie du bon calibrage sans comprendre le mécanisme
- Plus le lexique s'enrichit (effet d'apprentissage), plus les marges montent — le routing effort amplifie cet effet

---

## 6. Roadmap d'implémentation suggérée

| Phase | Contenu | Statut |
|---|---|---|
| MVP actuel | Routing modèle heuristique seul | ✅ En prod |
| v2.0 | Routing model + effort heuristique (étage 1 complet) | 🔴 À construire |
| v2.1 | Couche abstraction effort multi-provider | 🔴 À construire |
| v2.2 | Étage 2 sémantique local Ollama (feature flag) | 🔴 Après données réelles v2.0 |
| v3.0 | Calibrage poids heuristique/sémantique sur données usage | 🔴 Après volume suffisant |

> **Note** : l'étage 2 ne doit être implémenté qu'après que le volume de requêtes réelles ait révélé les patterns de conflits fréquents. Éviter de sur-ingénierer sur des cas hypothétiques.

---

## 7. Questions ouvertes

- Seuil de score heuristique à partir duquel on déclenche l'étage 2 ?
- Politique de cache sémantique : mémoriser les résolutions de conflits fréquents pour éviter les appels Ollama répétés sur les mêmes patterns ?
- Dimensionnement VPS Coolify : RAM suffisante pour faire tourner qwen2.5:3b + sqlcoder en parallèle ?
- Accord co-auteur sur l'orientation v2 avant tout développement
- Modèle de pricing : l'effort plus élevé = coût plus élevé pour l'user, ou Helios absorbe la différence via la marge ?
