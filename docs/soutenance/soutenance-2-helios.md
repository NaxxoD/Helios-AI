# Helios — Support 2ᵉ soutenance

**Date cible** : 2ᵉ soutenance HETIC
**Statut projet** : POC v2 validé bout-en-bout (post-soutenance 1, 17/20)
**Esprit de la défense** : on assume le parcours. On visait X, la mesure a dit non, on a trouvé Y et on l'a validé sur données réelles. **Le pivot fondé sur les données EST le résultat.**

> Doc de référence (détail + repro) : `cadrage-poc-helios.md` et `synthese-compression-helios.md`. Ce fichier-ci = le **storyboard oral** + l'anticipation jury.

---

## 0. Le virage du pitch (la phrase d'ouverture)

**AVANT (soutenance 1)** :
> « Helios réduit la consommation de tokens I/O d'environ **5%**, à qualité équivalente. »

**APRÈS (soutenance 2)** :
> « Helios réduit le coût d'une **session** de conversation **selon sa longueur** — de ~0% sur les échanges courts jusqu'à **~52% sur les sessions longues** — à **fidélité vérifiée**. »

Pourquoi le virage est défendable, pas un repli :
- Le « 5% I/O » visait l'**output** (raccourcir la réponse). La mesure l'a réfuté : **la longueur d'une réponse EST sa substance**, incompressible.
- Le vrai coût n'est pas dans la réponse, il est dans la **relecture de l'historique** que le système re-paie à chaque tour (le LLM n'a pas de mémoire). **Ça**, c'est de la redondance, donc compressible sans perte.
- On ne « triche » pas sur les tokens : **on supprime un artefact** (le LLM stateless qui re-paie le passé). C'est conceptuellement propre.

**La règle à dire au jury** : *« On ne coupe que la redondance, pas la substance. »*

---

## 1. Storyboard (slide par slide)

### Slide 1 — Contexte / problème
- Consommation énergétique des datacenters IA en forte hausse (~565 TWh estimés 2026).
- Réduire les tokens = réduire le coût **et** l'empreinte. C'est l'angle éco.
- **Bonus de crédibilité** : le corpus comparia (Etalab) embarque l'**énergie réelle mesurée** par conversation (kWh) → on ne dépend pas d'une extrapolation.

### Slide 2 — L'objectif initial
- POC v1 : « réduire les tokens I/O de ~5% » en optimisant le prompt (nettoyage + restructuration Qwen + contrainte de longueur « palier »).
- Intuition : agir sur le prompt pour faire **maigrir la réponse**.

### Slide 3 — Ce que la mesure a dit (le finding négatif)
Sur un prompt isolé : **input = 1,5% du coût, output = 98,5%**. Tout se joue sur l'output. Or tous les leviers d'output échouent :

| Levier | Résultat mesuré | Verdict |
|---|---|---|
| Restructuration Qwen | tokens neutres (input +7%, output +3%) | levier **qualité**, pas tokens |
| `max_tokens` (plafond) | **tronque** la réponse | pas un levier |
| Consigne de longueur (palier) | −66% output mais **dégrade ~2/3** des réponses | inexploitable à l'aveugle |

→ **Comprimer UNE réponse est une impasse** : la longueur = la substance.

### Slide 4 — La rigueur qui a évité un faux résultat (contribution méthodo)
- Grille de qualité à 2 couches (déterministe + juge LLM) avec **kappa de Cohen** mesuré.
- **Contrôle de fiabilité** : on a re-jugé les labels du juge local avec un juge premium (Opus) → **κ = 0,037 (du bruit)**.
- Conséquence : un chiffre optimiste (−15%) reposait sur du bruit → recalculé, le net réel était **+4%** (ça coûtait plus cher). **On a invalidé notre propre chiffre flatteur AVANT de le présenter.**
- *La plupart des POC montrent le beau chiffre sans tester le juge qui le produit. Nous, si.*

### Slide 5 — Le pivot : où est *vraiment* le coût
**Un LLM n'a pas de mémoire.** Pour suivre une conversation, l'app lui renvoie **tout l'historique à chaque tour**. L'input a donc **deux couches** :

| Couche | Quoi | Compressible ? |
|---|---|---|
| **A — message du tour** | la question tapée ce tour-ci | ❌ substance |
| **Output — réponse** | la réponse du modèle | ❌ substance (prouvé) |
| **B — relecture du contexte** | tout l'historique réinjecté | ✅ **redondance** (le modèle l'a déjà vu) |

- Tour 1 : pas de Couche B → input = 1,5%.
- Session : la Couche B **s'accumule jusqu'à dominer** → l'input passe à **~95% du volume**.
- Les deux chiffres ne se contredisent pas : la différence **EST** la Couche B. On change d'étage, on frappe le bon.

### Slide 6 — Le POC validé : le sous-agent mémoire
```
SANS sous-agent (tour N) :  [A: message] + [B: tout l'historique brut] + [Output]
AVEC sous-agent (tour N) :  [A: message] + [B': résumé à ~12%]         + [Output inchangé]
                                            ↑ on coupe ~88% ICI, et seulement ICI
```
- Un sous-agent **interne et contraint** résume le vieil historique, **garde les derniers tours verbatim**, et un **gate de fidélité (la grille)** vérifie que le résumé ne perd aucune décision/entité/chiffre.
- **Deux fenêtres séparées** : l'agent principal ne voit jamais le vieux brut (sa fenêtre est *dégonflée*) ; le sous-agent lit le brut dans **sa** fenêtre, mais peu (par **batch**, modèle **léger/local**).

### Slide 6 bis — L'escalier complet (2 leviers, et leur poids honnête)
Helios a **deux** leviers selon la longueur de session :

| Longueur | Levier | Gain tokens **mesuré** |
|---|---|---|
| 3-4 tours (67%) | **heuristique** : nettoyage + restructuration de la Couche A | **~marginal** (voir ci-dessous) |
| 5-9 tours (26%) | + sous-agent dégonfle la Couche B | ~18% |
| 10+ tours (7%) | + sous-agent dégonfle la Couche B | ~52% |

**Le rung court, mesuré honnêtement (Palier A, 4000 convs comparia, 14 278 messages user) :**
- gain nettoyage Couche A = **2,8% pondéré**, **médiane 0%**, 26% des messages seulement ont du bruit ;
- la Couche B est à **69% des sorties assistant** (substance, intouchable) → nettoyer les tours user ne gagne que **0,9% de B**.

→ **Le nettoyage du prompt n'est PAS un levier de coût.** On le garde comme levier **UX / qualité** (prompt propre, restructuré, contexte implicite explicité), pas comme une économie. *Le présenter comme un gain tokens serait répéter l'erreur du −15%.* Le vrai levier reste le sous-agent, qui résume B **sorties assistant comprises** (d'où −52% là où l'heuristique plafonne à ~1%).

*Caveat : comparia = prompts publics peu bavards ; 2,8% est un plancher sur corpus propre. Sur un corpus oral/conversationnel le bruit serait plus élevé — non mesuré, donc non revendiqué.*

### Slide 7 — La preuve, en 3 échelles complémentaires
**Chacune prouve une chose différente** (à dire explicitement — c'est la force) :

**(a) Structure — 39 364 conversations gouvernementales réelles (comparia)**
L'input écrase l'output (**4,8×**), la Couche B = **95% de l'input**. L'économie **scale avec la longueur** :

| Tours | % des convs | économie input |
|---|---|---|
| 3-4 | 67% | **~0%** (rien à comprimer) |
| 5-9 | 26% | ~18% |
| 10+ | 7% | **~52%** |

→ Facture corpus pondérée : **−43%**, mais **tirée par les 7% de sessions longues**. La conversation **médiane sauve 0%**.
→ Énoncé honnête : **« −52% sur les sessions 10+ tours, ~0% sur le typique »**. Ça **désigne le marché** : usages longs / interactif / agentique.

**(b) Fidélité — 50 vraies conversations comparia longues (8-20 tours)**
Résumé par Haiku, jugé par Opus + Sonnet :

| Métrique | Résultat |
|---|---|
| Compression | coupe **90%** |
| Fidélité du résumé | **90%** (Opus) — **96%** (Sonnet) |
| Pertes graves (≥1 juge) | **~12%** (résidu) |
| κ inter-juges | 0,24 (taux fiable ; label « grave » par cas plus bruité) |

→ Le résidu ~12% **EST le rôle de la grille** : sur ces cas, garder plus de verbatim → qualité shippée proche de 100%.

**(c) Stress-test hors corpus — Foxy (qwen local, n=1, non prévu)**
*Ce n'est PAS une 3ᵉ confirmation du 90%* (à dire tel quel — sinon le jury le démonte). C'est un stress-test qui a **trouvé le mode d'échec** :
- le garde-fou **« 96% casse » s'est reproduit** sur un autre corpus/modèle → la borne n'est **pas** un artefact de comparia ;
- un résumé *nu* (sans verbatim ni gate) a affirmé « accès bloqué » alors que c'était **résolu** → il a **figé un état ancien**. → **la fenêtre verbatim + le gate ne sont pas optionnels, ils sont prouvés nécessaires PAR L'ÉCHEC.**

### Slide 8 — Bilan chiffré (à projeter)
| Donnée | Valeur |
|---|---|
| Compression du vieil historique | **~88-90%** |
| Garde-fou (ne pas dépasser) | ~85-90% (à 96% on casse) |
| Fidélité (corpus réel, 50 convs) | **90% Opus / 96% Sonnet** |
| Économie session — brut | −45 à −58% input (≈ −46% facture) |
| Économie session — **nette** (sous-agent inclus) | **−43%** (rédacteur Haiku) → **−46%** (local) |
| Coût du sous-agent | ~14k tk / session 34 tours, 5 compactions par batch |
| Compression de réponse (ancien levier) | abandonné (dégrade 68%, labels κ 0,037) |

### Slide 9 — La contribution
1. **Finding négatif rigoureux** : la compression de réponse ne tient pas, et on sait *pourquoi*.
2. **Démonstration méthodologique rare** : un contrôle de fiabilité (kappa) a **invalidé notre propre chiffre** avant publication.
3. **Levier réel, mesuré, fidélité vérifiée** : −43 à −46% net de coût de session.
4. **Honnêteté de parcours** : pivot fondé sur les données, limites assumées.

### Slide 10 — Limites assumées (on les met sur la table)
*(Voir §2 ci-dessous — slide à montrer, pas à cacher.)*

### Slide 11 — Ce qui reste (le vrai travail restant)
La fidélité d'état (péremption, échec Foxy) a été **investiguée jusqu'au bout** :
- L'idée d'co-auteur — un **gate de cohérence d'état** par juge — a été **mesurée** (Palier État, n=120, labels contrôlés) : **peu fiable** (Haiku 0% / Sonnet 25% de rappel, FP 4%). **L'inconnue n°1 est levée, par la négative.**
- Conséquence actée : **la fenêtre verbatim est la protection primaire** de l'état (prévention en amont) ; on ne câble pas un juge d'état en prod (coût pour ~0 bénéfice). Piste ouverte : gate déterministe (« état final » structuré vérifié mécaniquement).
- **Mesuré en live** (smoke réel + Palier Continuation n=40) : le sous-agent tourne bout-en-bout, le **fail-safe (gate → rollback) protège la qualité** ; mode d'échec quantifié = le résumeur *continue* ~18% (hit-rate compaction ~82%) → **durcir le résumeur** = travail restant ciblé.
- Reste ouvert : fiabilité de la grille de **couverture** en conditions réelles (4.1c) ; run sur trafic.

---

## 2. Limites assumées (la diapo honnêteté)

**Structurelles — par design (c'est la portée, pas un défaut)**
- Gain **bimodal** : médiane par conv = **0%**. Helios n'aide pas le one-shot ni les sessions courtes (3-4 tours = 67% du corpus). Valeur sur **sessions longues** uniquement.
- Pas de free lunch local : le rédacteur local plafonne à **~70%** de fidélité → soit le gate porte plus de charge, soit on paie Haiku et on retombe à **−43%**.

**Maturité — pour l'instant**
- Le POC est une **simulation** (sorties recombinées + comptabilité papier), **pas un run live**. Orchestrateur non branché dans le proxy.
- Échantillon fidélité réduit : Palier 2 **n=50, IC ±8 pts** ; Foxy n=1.
- Seuil / KEEP / taux ~85% = choix de design, **non calibrés en réel**.

**Inconnues — assumées explicitement**
- Le gate **ne sera jamais à 100%** : juge LLM bruité (κ 0,24 par-cas). Il réduit le résidu ~12%, ne le supprime pas.
- **Angle mort du gate local** : qwen n'a pas vu sa propre erreur d'état → un gate qwen la verrait-il ? Si le gate doit être **premium** pour être fiable, l'économie locale s'érode. **Non mesuré = inconnue n°1.**
- On n'a **pas cartographié tous les modes d'échec** : la contradiction d'état est une classe découverte **par hasard** (Foxy). La découverte par stress-test est partielle par nature.

**Phrase de clôture honnête** :
> « Le levier est prouvé sur la structure (39k) et la fidélité (n=50), la portée est bornée (sessions longues), et le maillon critique — un gate qui attrape les contradictions d'état avec un juge abordable — reste à blinder et à mesurer en réel. On le présente comme du travail identifié, pas comme un trou caché. »

---

## 3. Anticipation des questions du jury

| Question probable | Réponse courte |
|---|---|
| « Vous annoncez −43% mais c'est tiré par 7% des sessions, non ? » | Oui, c'est pondéré-tokens. La médiane est 0%. Le bon énoncé est **−52% sur 10+ tours, ~0% sur le typique** — d'où le ciblage sessions longues. |
| « La compaction de contexte existe déjà (Claude, etc.). Quelle est votre valeur ? » | La compaction seule n'est pas l'invention. La valeur est le **package** : mémoire + **gate de fidélité vérifié (kappa)** + verbatim + routing. Le gate qui *prouve* qu'on n'a rien perdu est ce qui est rare. |
| « Comment garantissez-vous que le résumé ne perd rien ? » | Grille 2 couches + 2 juges premium → 90/96% fidèle, résidu ~12% rattrapé par rollback/verbatim. Et on **connaît la borne** (96% casse). |
| « Votre POC tourne-t-il en vrai ? » | Non : c'est une **simulation mesurée** sur corpus réel. Le run live (orchestrateur dans le proxy) est le travail restant prioritaire, identifié. |
| « Pourquoi avoir changé d'objectif ? N'est-ce pas un échec ? » | Un POC qui **pivote sur des données** est meilleure science qu'un POC qui « marche » en cachant ses limites. La mesure a réfuté l'output, on a trouvé et validé l'input. |
| « Le sous-agent ne coûte-t-il pas lui-même ? » | Si, dans **sa propre fenêtre**. Net = −43% (Haiku facturé) / −46% (local). Il remplace **~30 relectures premium par 1 résumé cheap**, par batch. |
| « Et si le résumé fige un état périmé ? » | La **fenêtre verbatim** (garder les tours récents bruts) le prévient **en amont** = protection primaire. On a aussi **mesuré** un gate-juge de cohérence d'état (Palier État, n=120) : peu fiable (Haiku 0%, Sonnet 25%) → on ne s'appuie pas dessus. On a testé l'idée d'co-auteur et **tranché par la donnée**, pas par opinion. |
| « Et l'optimisation du prompt, ça rapporte quoi ? » | **Mesuré : marginal en tokens** (2,8% sur la Couche A, 0,9% sur la Couche B). On l'assume comme levier **UX/qualité** (prompt propre + contexte explicité), pas comme une économie. La transparence sur ce point fait partie de la rigueur. |
| « Le sous-agent tourne-t-il vraiment en live ? » | Oui (run réel bout-en-bout). Et on a **mesuré un mode d'échec** : le résumeur *continue* parfois la conversation au lieu de résumer (~18%) — mais le **gate l'attrape → rollback → qualité préservée** (hit-rate compaction ~82%). Le −52% s'applique aux compactions **réussies**. Mesuré, pas supposé. |

---

## 4. Checklist matériel à produire avant la soutenance

- [ ] Slides à partir de ce storyboard (§1)
- [ ] Le tableau « tours / % convs / économie » en visuel propre (graphe en barres)
- [ ] La diapo « limites assumées » (§2)
- [ ] 1-2 captures des scripts/résultats (`palier1_*`, `palier2_verdicts.json`) comme preuve d'exécution
- [ ] (optionnel) chiffre kWh réel du parquet pour la diapo éco
- [ ] Démo ou schéma « deux fenêtres » animé (slide 6)
- [ ] Répétition orale du virage de pitch (§0) — la 1ʳᵉ phrase doit être nette
