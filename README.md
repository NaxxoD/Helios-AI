# Helios AI

> L'intelligence avant l'IA

Helios est un **client LLM multi-provider** qui se place entre vous et les assistants IA pour faire trois choses qu'aucune interface ne fait aujourd'hui : choisir le bon modèle, alléger le prompt avant l'envoi, et mesurer ce que chaque réponse coûte — en euros et en grammes de CO₂.

---

## Le problème qu'on résout

Les interfaces grand public (ChatGPT, Claude.ai, Gemini) vous enferment sur un seul provider, un seul modèle, avec zéro visibilité sur ce que vous dépensez. Résultat : vous payez un modèle frontier pour des questions qui n'en ont pas besoin, vous envoyez des prompts gonflés de politesses que le LLM ignore de toute façon, et vous ne savez pas ce que ça consomme.

Helios corrige ça.

---

## Ce que Helios fait

### Routing par complexité
Chaque message est analysé localement en 0 ms. Une question simple part sur Gemini Flash (0,10 $/M tokens). Une analyse comparative part sur Claude Sonnet ou GPT-4o. Pas de configuration — la décision est automatique, à chaque message, dans la même conversation.

### Optimisation du prompt
Avant l'envoi, un pipeline heuristique local passe le message au crible : formules de politesse, méta-instructions comportementales, répétitions, formulations à rallonge. Tout ça part à la corbeille. Même réponse — moins de tokens consommés.

### Tracking CO₂ et coût en temps réel
Par message : tokens input/output, coût en euros, CO₂ en grammes. Par session : cumul, tokens économisés, équivalences concrètes (douches, chauffage BBC). Dashboard complet avec graphiques par provider et évolution dans le temps.

### Changement de modèle en cours de conversation
Vous commencez sur Haiku pour une question rapide, vous continuez sur Opus pour une analyse complexe — dans la même conversation, historique conservé. Aucun concurrent ne propose ça dans une interface chat grand public.

---

## Pour qui

Développeurs qui paient leurs tokens à la fin du mois, étudiants avec un budget API limité, power users fatigués d'être captifs d'un seul provider. En un mot : ceux qui ont des clés API OpenAI, Anthropic ou Google et qui veulent en tirer le maximum.

---

## Demo

Pas de démo hébergée : lancez le projet en local (voir ci-dessous) ou parcourez le deck de présentation dans `frontend/public/pitch/`.

---

## Stack

| Couche | Technologie |
|---|---|
| Backend | FastAPI + SQLAlchemy ORM + psycopg v3 |
| Base de données | PostgreSQL 16 |
| Stockage messages | MinIO (S3-compatible) |
| Frontend | Vue 3 + Vite |
| Auth | JWT (HS256) + cookie httponly |
| Déploiement | Docker Compose + Coolify v4 |

Les messages de conversation sont stockés dans MinIO (`conversations/{user_id}/{conv_id}.json`). Les métadonnées (tokens, coût, CO₂, provider) sont en PostgreSQL. Les clés API LLM ne transitent jamais en base — elles restent côté client.

---

## Architecture

```
frontend (Nginx)
  └── /api/* → proxy → backend (FastAPI :8000)
                          ├── PostgreSQL  (users, sessions, conversations, facteurs)
                          ├── MinIO       (messages JSON)
                          └── LLM APIs    (OpenAI / Anthropic / Google)
```

La logique de calcul (`tokens → kWh → CO₂`) est dans `backend/utils/calculator.py`. Les coefficients par modèle sont en base (`conversion_factors`), seedés au démarrage et éditables via l'admin.

```
tokens × kwh_per_token
  → CO₂ standard  = kWh × 0,4 kg/kWh   (mix réseau mondial)
  → CO₂ éthique   = kWh × 0,015 kg/kWh  (Infomaniak D4, chaleur fatale)
```

---

## Installation locale

**Prérequis** : Python 3.12+, Node 20+, Docker

```bash
git clone https://github.com/NaxxoD/Helios-AI.git
cd Helios-AI

# Infrastructure (PostgreSQL + MinIO)
docker-compose up -d

# Backend
cd backend
cp .env.example .env   # éditer SECRET_KEY au minimum
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd ../frontend
npm install
npm run dev
```

| Service | URL |
|---|---|
| App | http://localhost:5173 |
| API Swagger | http://localhost:8000/docs |
| Console MinIO | http://localhost:9001 |

Au premier démarrage, uvicorn crée les tables et seed les facteurs CO₂ pour 30+ modèles (OpenAI, Anthropic, Google, Meta, Mistral).

---

## Créer un compte admin

```bash
cd backend
python set_admin.py votre@email.com
```

---

## Variables d'environnement

Copier `backend/.env.example` → `backend/.env`.

| Variable | Description |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL — format psycopg v3 obligatoire |
| `SECRET_KEY` | Clé JWT — **changer en production** |
| `FRONTEND_URL` | Origin CORS autorisée |
| `MINIO_ENDPOINT` | Host MinIO (sans `http://` — ex: `localhost:9000`) |
| `MINIO_USER` / `MINIO_PASSWORD` | Credentials MinIO |
| `MAIL_USERNAME` | SMTP — laisser vide pour désactiver les emails |
| `LOG_LEVEL` | Niveau de log uvicorn (défaut: `INFO`) |

---

## Routes API principales

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/auth/inscription` | Créer un compte |
| `POST` | `/api/auth/connexion` | Login → JWT |
| `POST` | `/api/chat/send` | Envoyer un message (routing + optimisation) |
| `GET` | `/api/sessions` | Historique des sessions |
| `POST` | `/api/sessions/import` | Importer une conversation |
| `POST` | `/api/optimise` | Analyser un prompt standalone |
| `GET` | `/api/stats` | KPI + données graphiques |
| `GET` | `/api/export/csv` | Export CSV |
| `GET` | `/api/admin/dashboard` | Dashboard admin |

Documentation complète : `http://localhost:8000/docs`

---

## Extension Chrome

`chrome-extension/` — capture automatique des conversations depuis chatgpt.com, claude.ai et gemini.google.com. Injecte un overlay CO₂ directement dans l'interface native.

---

## Déploiement

Le projet tourne en production via **Coolify v4** sur VPS (Docker Compose build pack). Voir `docker-compose.yml` à la racine. Les 4 services : `postgres`, `minio`, `backend`, `frontend` (Nginx).

---

## Auteurs

Projet académique réalisé en équipe, 2025/2026. Conception et développement : [NaxxoD](https://github.com/NaxxoD) et Elyas (co-auteur).

---

*Projet académique — 2025/2026*
