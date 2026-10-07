# La pipeline Helios, expliquée simplement

**But du document** : comprendre, sans jargon, ce qui se passe entre le moment où tu tapes un prompt et le moment où tu reçois une réponse — et où le Machine Learning vient se greffer.

---

## En une phrase

> Helios prend ton prompt, le **nettoie et le calibre** avant de l'envoyer à l'IA, pour que la réponse coûte **moins cher** et pollue **moins**, sans être moins bonne.

Pense à Helios comme à un **assistant qui relit ta demande avant de l'envoyer** : il enlève le superflu, va droit au but, et décide quelle longueur de réponse est raisonnable.

---

## Le voyage d'un prompt, étape par étape

Imaginons que tu écris :

> *« Bonjour ! J'espère que tu vas bien 😊 Est-ce que tu pourrais m'expliquer, s'il te plaît, comment fonctionne la récursivité en programmation ? Merci d'avance ! »*

Voici ce qu'Helios en fait.

### Étape 1 — Le nettoyage (E1) 🧹
On enlève tout ce qui ne sert pas à l'IA pour répondre : politesses, salutations, émojis, formules de remerciement, répétitions.

➡️ Devient : *« Explique comment fonctionne la récursivité en programmation. »*

**Comment** : ~200 règles de détection (des « filtres » qui reconnaissent les tournures inutiles). C'est mécanique, pas d'IA ici.

### Étape 2 — La mise en ordre (E2) 📐
On met **la demande en premier**. Si quelqu'un noie sa question au milieu d'un paragraphe, on la remonte en tête, parce que l'IA répond mieux quand l'instruction est claire et au début.

➡️ La phrase est déjà bien ordonnée ici, donc peu de changement.

**Comment** : une règle simple de réorganisation. Pas d'IA non plus.

### Étape 3 — La vérification (E3) 🔍
On repère si le prompt est **trop vague** ou incomplet (style télégramme, sans contexte) et on peut suggérer de le préciser.

### Étape 4 — Le palier de longueur 📏 ⭐
C'est **l'étape la plus importante pour le coût.** Helios devine quelle **longueur de réponse** convient à la question, et ajoute une consigne du type *« Réponds en 115 mots maximum »*.

Pourquoi ça compte : **une réponse 2× plus courte coûte ~2× moins cher** (et la sortie de l'IA coûte 5× plus cher que l'entrée). C'est là que vient l'essentiel de l'économie.

**Comment aujourd'hui** : par mots-clés (si ça ressemble à du code → tel palier, si c'est une question courte → tel autre…). C'est une **devinette à base de règles**.

### Étape 5 — Le routage 🚦
Helios suggère **quel niveau de modèle** et **quel effort** utiliser : une question simple n'a pas besoin du plus gros modèle (cher), une analyse complexe oui.

**Comment aujourd'hui** : encore par mots-clés.

### Étape 6 — L'estimation coût + CO₂ 🌱
Avant même d'envoyer, Helios estime combien de tokens, quel coût en $, et quelle empreinte carbone (avec une équivalence parlante : « = X minutes de chauffage », « = X douches »).

### Étape 7 — L'envoi et la mesure 📤
Le prompt optimisé part vers l'IA (Claude, etc.). On récupère la vraie réponse, les vrais tokens, le vrai coût — et on les affiche.

---

## Le schéma global

```
   Ton prompt
       │
       ▼
   🧹 E1  Nettoyage      (enlève le superflu)
       │
       ▼
   📐 E2  Mise en ordre  (la demande d'abord)
       │
       ▼
   🔍 E3  Vérification   (prompt trop vague ?)
       │
       ▼
   📏 Palier de longueur (quelle taille de réponse ?)   ← le levier d'économie
       │
       ▼
   🚦 Routage            (quel modèle / quel effort ?)
       │
       ▼
   🌱 Estimation coût + CO₂
       │
       ▼
   📤 Envoi à l'IA  →  réponse + vraie facture mesurée
```

---

## Le problème qu'on a découvert

Le palier (étape 4) fait économiser **~32 %**. Super. **Mais** : en l'appliquant **partout**, on force parfois une réponse trop courte sur une question qui méritait du détail → la réponse devient moins bonne **1 fois sur 2**.

Analogie : c'est comme dire à quelqu'un *« réponds en 2 phrases »* à **toutes** les questions. Pour « quelle heure est-il ? », parfait. Pour « explique-moi la fiscalité des entreprises », catastrophe.

---

## Là où le Machine Learning arrive 🤖

On ajoute une **brique intelligente** juste après l'optimiseur : la **Policy Engine**. Sa première mission, le **gating** (« portillon ») :

> Avant d'appliquer le raccourcissement, un modèle entraîné regarde le prompt et décide : **« raccourcir ici, est-ce risqué ? »**
> - **Non risqué** → on applique le palier, on économise les 32 %.
> - **Risqué** → on laisse l'IA répondre librement, on protège la qualité.

```
   ... optimiseur (E1·E2·E3 + palier) ...
            │
            ▼
   🤖 POLICY ENGINE
      « raccourcir ce prompt, c'est sûr ? »
            │
       ┌────┴─────┐
   OUI │          │ NON
       ▼          ▼
  on garde    on laisse
  le palier   la réponse
  (−32 %)     libre
            │
            ▼
        envoi à l'IA
```

**Pourquoi un modèle plutôt que des règles ?** Parce que « est-ce risqué de raccourcir ? » dépend de subtilités du sens qu'aucune liste de mots-clés ne capture bien. Un modèle qui **apprend** sur des exemples (où on sait si raccourcir a dégradé ou non) fait ça mieux.

**Le garde-fou** : si le modèle n'est pas sûr de lui, ou s'il n'est pas encore entraîné, Helios **revient au comportement actuel**. Donc ça ne casse jamais rien — au pire, c'est comme avant.

---

## Ce qui change, en résumé

| | Avant | Avec le ML |
|---|---|---|
| Décider de raccourcir | règles par mots-clés, **appliqué partout** | modèle qui décide **au cas par cas** |
| Économie | ~32 % mais qualité abîmée 1×/2 | ~32 % **sur le sous-ensemble sûr** |
| Qualité | dégradée trop souvent | protégée (dégradation visée < 10 %) |
| Si le modèle doute | — | retour automatique au comportement actuel |

**L'idée à retenir** : on ne demande plus à une IA de « mieux écrire » le prompt (ça ne marchait pas). On utilise un modèle pour **prendre la bonne décision coût/qualité, prompt par prompt.**
