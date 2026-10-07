# Helios AI — Document de positionnement produit

---

## Le problème

Les interfaces LLM grand public (ChatGPT, Claude.ai, Gemini) ont un défaut structurel : elles vous enferment.

Un seul provider. Un seul modèle. Zéro visibilité sur le coût réel. Zéro contrôle sur ce que vous envoyez.

Résultat :
- Vous payez un modèle large pour des questions simples qui n'en ont pas besoin.
- Vous envoyez des prompts gonflés de politesses et de méta-instructions que le LLM ignore de toute façon.
- Vous n'avez aucune idée de combien ça coûte ni de ce que ça consomme.
- Quand vous voulez changer de modèle en cours de conversation, vous recommencez à zéro.

---

## La réponse

**Helios AI est le client LLM qui pense à votre place avant d'envoyer.**

Il ne remplace pas les LLMs. Il se place entre vous et eux pour faire trois choses qu'aucune interface ne fait aujourd'hui :

1. **Choisir le bon modèle** — selon ce que vous demandez, pas selon ce que vous avez configuré hier.
2. **Nettoyer le prompt** — supprimer ce qui est inutile avant que le token soit consommé.
3. **Mesurer ce qui part et ce qui revient** — en temps réel, en dollars, en grammes de CO₂.

---

## Pour qui

**Utilisateurs cibles primaires — les utilisateurs intensifs des APIs LLM :**

- Développeurs qui paient leurs tokens à la fin du mois et veulent réduire la facture
- Étudiants et chercheurs avec un budget API limité
- Power users fatigués d'être captifs d'un seul provider

**Ce qu'ils ont en commun :** ils ont des clés API OpenAI, Anthropic ou Google. Ils savent que les modèles n'ont pas la même valeur selon la tâche. Ils n'ont pas d'outil qui tient compte de ça.

---

## La proposition de valeur centrale

> **Chaque message coûte ce qu'il doit coûter — pas plus.**

Trois leviers :

**Levier 1 — Routage par complexité**
Une question simple va sur Gemini Flash (0,10 $/M tokens input). Une analyse comparative va sur Sonnet ou GPT-4o. Une documentation complète va sur Opus. Le modèle suit la tâche, pas l'inverse. La décision est prise en local, en zéro milliseconde.

**Levier 2 — Optimisation du prompt**
Avant d'envoyer, Helios passe le prompt dans un pipeline heuristique local (zéro appel API) :
- Suppression des formules de politesse et tournures verbales creuses
- Suppression des méta-instructions comportementales ("tu es une IA avancée disposant d'une compréhension holistique…") — que le LLM ignore de toute façon
- Détection et signalement des prompts trop vagues ou incomplets
- Ajout d'une contrainte d'output calibrée selon la nature de la tâche

Résultat : moins de tokens envoyés, même qualité de réponse.

**Levier 3 — Visibilité totale**
Par message : tokens input/output, coût USD, CO₂. Par session : cumul, tokens économisés, équivalences concrètes. Ce que vous ne mesurez pas, vous ne pouvez pas le réduire.

---

## Le différenciateur clé

**Le changement de modèle en cours de conversation.**

Claude.ai vous bloque sur un modèle. ChatGPT aussi. Si vous commencez une session sur GPT-4o-mini et que votre question suivante nécessite de la puissance, vous êtes coincé ou vous recommencez.

Helios reroute chaque message indépendamment, en conservant l'historique. Vous commencez sur Haiku, vous finissez sur Opus — dans la même conversation, de manière transparente. Aucun concurrent ne propose ça aujourd'hui dans une interface chat grand public.

---

## Contre quoi on se positionne

| Interface | Problème |
|---|---|
| **ChatGPT** | Un seul provider, modèle fixe par conversation, zéro visibilité coût |
| **Claude.ai** | Idem — captif Anthropic, pas de routing, pas de tracking |
| **LM Studio / Ollama** | Local uniquement, pas d'accès aux modèles frontier |
| **OpenRouter** | Routing multi-provider mais pas d'optimisation prompt, pas de tracking environnemental, pas d'interface chat |
| **Spreadsheet + copier-coller** | Ce que font les gens sérieux sur leur budget — Helios l'automatise |

**Ce que Helios fait qu'aucun de ces outils ne fait :**
routing + optimisation + tracking dans une interface chat unifiée.

---

## Ce que Helios ne prétend pas être

- Un modèle LLM. Helios n'entraîne rien, ne stocke pas vos conversations.
- Un outil "green" au sens marketing. Le CO₂ mesuré reste du CO₂ consommé — la valeur est dans la prise de conscience et la réduction active.
- Une solution enterprise. C'est un outil pour les utilisateurs avec leurs propres clés API, pas une plateforme avec gestion des droits et SSO.

---

## Les métriques qui prouvent le positionnement

Ce qu'on mesure pour valider l'utilité réelle :

- **% de tokens économisés par l'optimiseur** sur un prompt donné
- **Économie USD par session** grâce au routing (modèle sélectionné vs modèle le plus cher)
- **Score de pertinence** du prompt avant/après optimisation
- **Junk density** — ratio tokens méta vs tokens signal dans les prompts génériques

Ces métriques sont affichées en temps réel dans l'interface. L'utilisateur voit la valeur à chaque message, pas dans un rapport mensuel.

---

## Tagline candidates

> *Le bon modèle. Le bon prompt. Le bon coût.*

> *Votre LLM ne vous appartient pas. Helios change ça.*

> *ChatGPT vous vend un abonnement. Helios vous vend de l'efficacité.*

---

*Document interne — projet intégrateur 2025/2026*
