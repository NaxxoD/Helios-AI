 Tableau résultats — Qwen 2.5:7b / Optimiseur sémantique Helios

  ┌─────┬───────────────────────────────┬──────────┬──────────┬──────────┬─────────────┬──────────┬──────────┬───────┬─────────────┬─────────────────────────────────────────────────────────────────────────┐
  │  #  │             Thème             │   role   │ contexte │  tache   │ contraintes │  format  │ qualité  │ gain  │ JSON valide │                              Bugs notables                              │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 1   │ Coach burnout                 │ inferred │ present  │ present  │ present     │ present  │ absent   │ moyen │ ✓           │ composantes_manquantes ≠ audit (format listé absent mais audit=present) │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 2   │ Marque éco + roadmap          │ inferred │ present  │ present  │ absent      │ inferred │ absent   │ moyen │ ✗           │ prompt_restructure = objet JSON au lieu de string                       │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 3   │ SEO bougies                   │ absent   │ present  │ present  │ absent      │ inferred │ absent   │ moyen │ ✓           │ Ambiguïtés anecdotiques (date, cousine)                                 │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 4   │ Développement perso vague     │ absent   │ present  │ present  │ absent      │ inferred │ absent   │ moyen │ ✓           │ Prompt ultra-vague, gain "moyen" trop généreux                          │
  │ 2   │ Marque éco + roadmap          │ inferred │ present  │ present  │ absent      │ inferred │ absent   │ moyen │ ✗           │ prompt_restructure = objet JSON au lieu de string                       │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 3   │ SEO bougies                   │ absent   │ present  │ present  │ absent      │ inferred │ absent   │ moyen │ ✓           │ Ambiguïtés anecdotiques (date, cousine)                                 │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 4   │ Développement perso vague     │ absent   │ present  │ present  │ absent      │ inferred │ absent   │ moyen │ ✓           │ Prompt ultra-vague, gain "moyen" trop généreux                          │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 5   │ Communication interne         │ absent   │ present  │ present  │ inferred    │ absent   │ absent   │ moyen │ ✓           │ Ambiguïté "3 ou 4" signalée → anecdotique                               │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 6   │ Scraping voitures             │ absent   │ present  │ present  │ absent      │ absent   │ absent   │ moyen │ ✓           │ A choisi Python+BeautifulSoup → viole règle no-choix-arbitraire         │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 7   │ YouTube/TikTok/podcast        │ absent   │ present  │ inferred │ inferred    │ inferred │ absent   │ moyen │ ✓           │ prompt_restructure trop court, perd le contexte                         │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 8   │ Commerce / salon de thé       │ absent   │ present  │ present  │ absent      │ absent   │ inferred │ moyen │ ✓           │ Ambiguïté boutique/salon bien détectée ✓                                │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 9   │ App micro-journaling          │ absent   │ present  │ present  │ inferred    │ absent   │ inferred │ moyen │ ✓           │ React/Flutter non tranché dans prompt_restructure                       │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 10  │ Post LinkedIn coaching        │ inferred │ absent   │ present  │ present     │ absent   │ absent   │ moyen │ ✓           │ Contexte offre coaching manquant, bien signalé ✓                        │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 11  │ Recette poulet/riz            │ absent   │ inferred │ present  │ inferred    │ inferred │ absent   │ moyen │ ✓           │ Ambiguïté hallucinée ("accent local") — invention pure                  │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 12  │ Blog productivité télétravail │ absent   │ present  │ present  │ absent      │ inferred │ absent   │ moyen │ ✓           │ Correct, propre                                                         │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 13  │ Doc API Swagger               │ absent   │ present  │ present  │ inferred    │ inferred │ absent   │ moyen │ ✓           │ composantes_manquantes inclut "tache" alors qu'audit=present            │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 14  │ Sécuriser SSH                 │ present  │ absent   │ present  │ absent      │ inferred │ absent   │ moyen │ ✓           │ Le role était explicite dans le prompt → bien détecté ✓                 │
  ├─────┼───────────────────────────────┼──────────┼──────────┼──────────┼─────────────┼──────────┼──────────┼───────┼─────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ 15  │ Analyse Meta Ads ROAS         │ present  │ present  │ present  │ absent      │ absent   │ inferred │ moyen │ ✓           │ Le role était explicite → bien détecté ✓                                │
  └─────┴───────────────────────────────┴──────────┴──────────┴──────────┴─────────────┴──────────┴──────────┴───────┴─────────────┴─────────────────────────────────────────────────────────────────────────┘

  ---
  Bilan synthèse :

  ┌─────────────────────────────────────────────┬───────────────────────────────────────────┐
  │                  Métrique                   │                 Résultat                  │
  ├─────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ JSON valide                                 │ 14/15 (93%)                               │
  ├─────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ gain_estime = "moyen" systématique          │ 15/15 — bloqué, jamais "faible" ni "fort" │
  ├─────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ role absent/non détecté quand explicite     │ 0 — détecté correctement sur #14 et #15 ✓ │
  ├─────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Ambiguïtés hallucinées (non pertinentes)    │ ~5/15 (#1, #3, #5, #11, #15)              │
  ├─────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Violation règle no-choix-arbitraire         │ 1 (#6 Python choisi)                      │
  ├─────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ prompt_restructure = mauvais type           │ 1 (#2 objet au lieu de string)            │
  ├─────────────────────────────────────────────┼───────────────────────────────────────────┤
  │ Incohérence audit vs composantes_manquantes │ 2 (#1, #13)                               │
  └─────────────────────────────────────────────┴───────────────────────────────────────────┘

  Réduction volumétrique : -61.9% en moyenne (1808 mots → 689 mots sur 14 prompts valides)

  ┌────────────────────────────┬──────────┐
  │          Métrique          │  Valeur  │
  ├────────────────────────────┼──────────┤
  │ Réduction mots moyenne     │ -61.9%   │
  ├────────────────────────────┼──────────┤
  │ Taux de bruit orig moyen   │ 9.4%     │
  ├────────────────────────────┼──────────┤
  │ Taux de bruit struct moyen │ 0.2%     │
  ├────────────────────────────┼──────────┤
  │ Gain signal net            │ +9.2 pts │
  ├────────────────────────────┼──────────┤
  │ Prompts valides            │ 14/15    │
  └────────────────────────────┴──────────┘

  Cas extrêmes :
  - #4 : -81.5% — prompt ultra-vague/verbeux, condensé à l'os (200 → 37 mots)
  - #11 : -78.5% — recette poulet/riz noyée dans 3 paragraphes d'intro émotionnelle
  - #1 : -23.6% négatif — Qwen a ajouté du contenu sur un prompt déjà court, il a paraphrasé plutôt que condensé

  Observation importante : le bruit conversationnel est éliminé quasi-parfaitement (9.4% → 0.2%), mais sur les prompts courts (#1), Qwen tend à reformuler en ajoutant de la masse plutôt qu'à optimiser. Le seuil à partir duquel le gain
  est réel semble être autour de 80-100 mots dans l'original.