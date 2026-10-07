"""
Inférence tâche → modèle tier + effort
Portage de la matrice la matrice de routage vers le backend.

Retourne : { model_tier, effort, task, confidence }
  model_tier : 'simple' | 'medium' | 'complex'
  effort     : off|on|low|standard|medium|high|xhigh|max|None
"""

_TASKS = [
    # (id, label, model_tier, effort, signals, cat)
    ('qa',            'Q&A factuelle',              'simple',  'off',    ['définition', "c'est quoi", "qu'est-ce que", 'explique-moi', 'kesako'],          None),
    ('translation',   'Traduction',                 'simple',  'off',    ['traduis', 'traduction', 'translate', 'en anglais', 'en français', 'en espagnol'], None),
    ('resume',        'Résumé / synthèse',           'medium',  'low',    ['résume', 'synthèse', 'résumé', 'récapitule', 'tldr', 'condense', 'points clés'], None),
    ('reformulation', 'Reformulation / amélioration','medium',  'low',    ['reformule', 'améliore', 'réécris', 'clarifie', 'simplifie', 'tourne autrement', 'peaufine'], None),
    ('email',         'Email / communication pro',   'medium',  'low',    ['email', 'mail', 'relance', 'proposition', 'devis', 'client', 'objet', 'réponse'], None),
    ('boilerplate',   'Génération boilerplate',      'medium',  'low',    ['génère', 'boilerplate', 'scaffold', 'template', 'squelette', 'code de base'],   'dev'),
    ('brainstorm',    'Brainstorm / idéation',       'medium',  'medium', ['brainstorm', 'idée', 'suggestion', 'piste', 'créatif', 'angle', 'concept'],     None),
    ('copywriting',   'Rédaction / copywriting',     'medium',  'medium', ['rédige', 'écris', 'copywriting', 'article', 'newsletter', 'post', 'slogan', 'accroche'], None),
    ('presentation',  'Présentation / structuration','medium',  'medium', ['présentation', 'slides', 'pitch', 'plan', 'structure', 'organise', 'rapport'],  None),
    ('research',      'Recherche / veille',          'medium',  'medium', ['recherche', 'veille', 'compare', 'benchmark', 'concurrence', 'marché', 'alternatives'], None),
    ('refacto',       'Refacto / review code',       'medium',  'medium', ['refacto', 'review', 'clean', 'réécrire', 'améliorer le code', 'nettoyer'],      'dev'),
    ('strategy',      'Stratégie produit',           'medium',  'medium', ['stratégie', 'produit', 'mvp', 'saas', 'roadmap', 'vision', 'pivot', 'feature'], 'strategy'),
    ('data',          'Analyse de données',          'medium',  'high',   ['analyse', 'données', 'tableau', 'excel', 'csv', 'sql', 'statistique', 'kpi', 'taux', 'roas', 'cpa', 'conversion', 'campagne', 'performance', 'chiffres'], 'analysis'),
    ('debug',         'Debug code',                  'medium',  'high',   ['debug', 'erreur', 'bug', 'traceback', 'typeerror', 'exception', 'plantage', 'crash', 'ne fonctionne pas'], 'dev'),
    ('archi',         'Architecture système',        'medium',  'high',   ['architecture', 'design pattern', 'microservice', 'conception', 'diagramme'],    'dev'),
    ('pricing',       'Modèle économique / pricing', 'medium',  'high',   ['pricing', 'marge', 'rentabilité', 'abonnement', 'monétisation', 'freemium', 'revenue', 'modèle économique'], 'strategy'),
    ('sec_def',       'Sécu défensive',              'medium',  'high',   ['sécurité', 'hardening', 'patch', 'vulnérabilité', 'audit', 'owasp', 'protection', 'durcir'], 'sec'),
    ('sec_off',       'Analyse offensive',           'medium',  'high',   ['offensif', 'exploit', 'xss', 'sqli', 'injection', 'pentest', 'ctf', 'payload'], 'sec'),
    ('challenge',     'Challenge hypothèses',        'complex', 'xhigh',  ['challenger', 'hypothèse', 'décision critique', 'risque', 'arbitrage', 'trade-off', 'choisir entre', 'pour ou contre'], None),
]

_CAT_BOOSTS = {
    'dev':      ['code', 'bug', 'python', 'javascript', 'typescript', 'api', 'fonction', 'script'],
    'strategy': ['stratégie', 'business', 'marché', 'startup', 'saas'],
    'analysis': ['analyse', 'données', 'résultats', 'performance', 'metrics', 'meta ads', 'google ads'],
    'sec':      ['sécu', 'cyber', 'pentest', 'sécurité', 'attaque'],
}


def suggest_routing(text: str) -> dict:
    """Infère la tâche, le tier modèle et l'effort optimal depuis le texte du prompt."""
    lower = text.lower()
    scored = []

    for task_id, label, tier, effort, signals, cat in _TASKS:
        score = sum(2 for s in signals if s in lower)
        if cat and any(w in lower for w in _CAT_BOOSTS.get(cat, [])):
            score += 3
        if score > 0:
            scored.append({
                'task_id':    task_id,
                'task':       label,
                'model_tier': tier,
                'effort':     effort,
                'score':      score,
            })

    if not scored:
        return {'model_tier': 'medium', 'effort': None, 'task': None, 'confidence': 0}

    scored.sort(key=lambda x: x['score'], reverse=True)
    best = scored[0]
    return {
        'model_tier': best['model_tier'],
        'effort':     best['effort'],
        'task':       best['task'],
        'confidence': best['score'],
    }
