"""
Tests unitaires pour utils/optimiseur.py
Lancer : depuis backend/ -> pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from utils.optimiseur import optimise as _optimise
from utils.calculator import DEFAULT_KWH_PER_TOKEN


class TestPolitesse(unittest.TestCase):

    def test_sil_te_plait(self):
        r = _optimise("s'il te plait explique-moi la recursivite")
        assert "s'il te plait" not in r['optimised'].lower()
        assert r['tokens_saved'] >= 0

    def test_pourrais_tu(self):
        r = _optimise("pourrais-tu me faire un resume de ce texte ?")
        assert "pourrais-tu" not in r['optimised'].lower()

    def test_merci_davance(self):
        r = _optimise("liste les 5 meilleurs frameworks Python, merci d'avance")
        assert "merci d'avance" not in r['optimised'].lower()

    def test_sil_vous_plait(self):
        r = _optimise("pourriez-vous s'il vous plait corriger ce code")
        assert "s'il vous plait" not in r['optimised'].lower()

    def test_prompt_sans_politesse(self):
        prompt = "Explique la recursivite avec un exemple Python."
        r = _optimise(prompt)
        assert r['optimised'] == prompt
        assert r['tokens_saved'] == 0


class TestTournuresVerbeuses(unittest.TestCase):

    def test_est_ce_que_tu_peux(self):
        r = _optimise("est-ce que tu peux generer un fichier CSV ?")
        assert "est-ce que tu peux" not in r['optimised'].lower()

    def test_jaimerais_que_tu(self):
        r = _optimise("j'aimerais que tu ecrives une fonction de tri en Python")
        assert "j'aimerais que tu" not in r['optimised'].lower()

    def test_noublie_pas_de(self):
        # "n'oublie pas de" est une contrainte — protégée, non supprimée
        r = _optimise("n'oublie pas de mettre des commentaires dans le code")
        assert "n'oublie pas de" in r['optimised'].lower()
        assert r['pyramid']['contrainte']

    def test_je_voudrais(self):
        r = _optimise("je voudrais une liste de frameworks JS populaires")
        assert "je voudrais" not in r['optimised'].lower()


class TestRedondances(unittest.TestCase):

    def test_comme_je_te_lai_dit(self):
        r = _optimise("comme je te l'ai dit avant, le bug vient du parser")
        assert "comme je te l'ai dit" not in r['optimised'].lower()

    def test_je_pense_que(self):
        r = _optimise("je pense que le probleme vient de la boucle for")
        assert "je pense que" not in r['optimised'].lower()

    def test_en_fait(self):
        r = _optimise("en fait le code plante a la ligne 42")
        assert "en fait" not in r['optimised'].lower()

    def test_evidemment(self):
        r = _optimise("evidemment il faut tester les cas limites")
        assert "evidemment" not in r['optimised'].lower()


class TestRulesApplied(unittest.TestCase):

    def test_rules_listed(self):
        r = _optimise("s'il te plait est-ce que tu peux ecrire un tri rapide")
        labels = [rule['label'] for rule in r['rules_applied']]
        assert 'formule de politesse' in labels
        assert any(l in labels for l in ('tournure verbale condensee', 'tournure verbale condensée', 'tournure interrogative condensee'))

    def test_no_rules_on_clean_prompt(self):
        r = _optimise("Ecris une fonction Python qui inverse une chaine.")
        assert r['rules_applied'] == []
        assert r['suggestions'] == []


class TestSuggestions(unittest.TestCase):

    def test_liste_en_prose(self):
        prompt = (
            "Genere un rapport avec une introduction, puis un resume, "
            "et une conclusion et des recommandations et une bibliographie."
        )
        r = _optimise(prompt)
        types = [s['type'] for s in r['suggestions']]
        assert 'format_liste' in types

    def test_repetition_mots(self):
        prompt = (
            "Ecris un algorithme. L'algorithme doit etre rapide. "
            "Optimise l'algorithme pour les grandes listes. "
            "L'algorithme doit aussi gerer les doublons."
        )
        r = _optimise(prompt)
        types = [s['type'] for s in r['suggestions']]
        assert 'repetition' in types

    def test_prompt_long(self):
        prompt = "Explique " + "tres " * 200 + "bien ce concept."  # > 800 chars
        r = _optimise(prompt)
        types = [s['type'] for s in r['suggestions']]
        assert 'longueur' in types


class TestTokens(unittest.TestCase):

    def test_tokens_saved_nonnegative(self):
        r = _optimise("s'il te plait pourrais-tu m'expliquer la recursivite, merci d'avance")
        assert r['tokens_saved'] >= 0
        assert r['tokens_after'] <= r['tokens_before']

    def test_tokens_before_nonzero(self):
        r = _optimise("Explique la programmation orientee objet.")
        assert r['tokens_before'] > 0

    def test_kwh_saved_coherent(self):
        r = _optimise("s'il te plait genere un resume, merci beaucoup")
        expected = round(r['tokens_saved'] * DEFAULT_KWH_PER_TOKEN, 9)
        assert r['kwh_saved'] == expected

    def test_empty_prompt(self):
        r = _optimise("   ")
        assert r['tokens_before'] == 0 or r['tokens_after'] == 0 or r['optimised'] == ''


class TestOutputStructure(unittest.TestCase):

    def test_keys_present(self):
        r = _optimise("Resume ce texte s'il te plait.")
        for key in ('original', 'optimised', 'rules_applied', 'suggestions',
                    'tokens_before', 'tokens_after', 'tokens_saved', 'kwh_saved'):
            assert key in r, f"Cle manquante : {key}"

    def test_original_preserved(self):
        prompt = "  Explique la recursivite.  "
        r = _optimise(prompt)
        assert r['original'] == prompt.strip()


class TestPyramide(unittest.TestCase):

    def test_contrainte_preserved(self):
        r = _optimise("n'oublie pas de repondre en JSON. Explique la recursivite.")
        assert "n'oublie pas de" in r['optimised'].lower()
        assert r['pyramid']['contrainte']

    def test_politesse_in_bruit(self):
        r = _optimise("s'il te plait")
        assert r['pyramid']['bruit']

    def test_score_100_on_clean(self):
        r = _optimise("Ecris une fonction Python qui trie une liste.")
        assert r['pertinence_score'] == 100

    def test_score_decreases_with_noise(self):
        r = _optimise("s'il te plait, merci d'avance, explique la recursivite.")
        assert r['pertinence_score'] < 100

    def test_pyramid_keys_present(self):
        r = _optimise("Explique la recursivite s'il te plait.")
        for key in ('intention', 'contrainte', 'contexte', 'bruit'):
            assert key in r['pyramid'], f"Cle manquante dans pyramid : {key}"


class TestNonRegression(unittest.TestCase):

    # Préservation des impératifs courts
    def test_preserve_imperatif_court_corrige(self):
        r = _optimise("Corrige-le.")
        self.assertIn("corrige-le", r['optimised'].lower())
        self.assertTrue(r['tokens_saved'] >= 0)

    def test_preserve_imperatif_court_sois_bref(self):
        r = _optimise("Sois bref.")
        self.assertIn("sois bref", r['optimised'].lower())
        self.assertTrue(r['tokens_saved'] >= 0)

    def test_preserve_imperatif_court_reponds(self):
        r = _optimise("Réponds.")
        self.assertIn("réponds", r['optimised'].lower())
        self.assertTrue(r['tokens_saved'] >= 0)

    def test_preserve_imperatif_court_verifie(self):
        r = _optimise("Vérifie.")
        self.assertIn("vérifie", r['optimised'].lower())
        self.assertTrue(r['tokens_saved'] >= 0)

    def test_preserve_imperatif_court_teste_ca(self):
        r = _optimise("Teste ça.")
        self.assertIn("teste ça", r['optimised'].lower())
        self.assertTrue(r['tokens_saved'] >= 0)

    # Préservation des assignations de rôle
    def test_preserve_role_expert_python(self):
        r = _optimise("Tu es un expert en Python. Fais une boucle sur cette liste.")
        self.assertIn("tu es un expert en python", r['optimised'].lower())

    def test_preserve_role_specialiste_cybersecurite(self):
        r = _optimise("Tu es un spécialiste en cybersécurité. Analyse ce log d'erreur.")
        self.assertIn("tu es un spécialiste en cybersécurité", r['optimised'].lower())

    def test_preserve_role_developpeur_senior(self):
        r = _optimise("Tu es un développeur senior. Relis mon code et optimise-le.")
        self.assertIn("tu es un développeur senior", r['optimised'].lower())

    def test_preserve_role_consultant_marketing(self):
        r = _optimise("Tu es un consultant marketing. Trouve un slogan accrocheur.")
        self.assertIn("tu es un consultant marketing", r['optimised'].lower())

    # Non-suppression abusive de "tu peux" et "pense à"
    def test_preserve_tu_peux_contexte_technique(self):
        r = _optimise("Tu peux aussi considérer X dans ton architecture si besoin.")
        self.assertIn("tu peux aussi considérer x", r['optimised'].lower())

    def test_preserve_pense_a_validation(self):
        r = _optimise("Pense à bien valider Y avant d'exécuter la fonction principale.")
        self.assertIn("pense à bien valider y", r['optimised'].lower())

    def test_preserve_tu_peux_alternative(self):
        r = _optimise("Tu peux utiliser une API REST ou GraphQL pour ce projet.")
        self.assertIn("tu peux utiliser une api rest ou graphql", r['optimised'].lower())

    # Cas mixtes
    def test_cas_mixte_politesse_et_role(self):
        r = _optimise("Salut ! J'espère que tu vas bien aujourd'hui. Tu es un développeur senior. Écris cette classe.")
        self.assertIn("tu es un développeur senior", r['optimised'].lower())
        self.assertNotIn("j'espère que tu vas bien", r['optimised'].lower())
        self.assertTrue(r['tokens_saved'] >= 0)

    def test_cas_mixte_meteo_et_imperatif_court(self):
        r = _optimise("En plus il fait super beau aujourd'hui ça donne de l'énergie. Corrige-le.")
        self.assertIn("corrige-le", r['optimised'].lower())
        self.assertTrue(r['tokens_saved'] >= 0)

    def test_cas_mixte_verbeux_et_pense_a(self):
        r = _optimise("En gros j'aimerais un truc technique. Pense à bien valider le formulaire de contact.")
        self.assertIn("pense à bien valider le formulaire", r['optimised'].lower())
        self.assertTrue(r['tokens_saved'] >= 0)


class TestScaffold(unittest.TestCase):
    """Socle déterministe E2 — 'lead with the ask'."""

    def test_lead_remonte_la_demande(self):
        r = _optimise("Je vends des bougies artisanales depuis deux ans. Donne-moi une stratégie SEO.")
        self.assertTrue(r['restructured'])
        opt = r['optimised'].lower()
        self.assertLess(opt.index('donne'), opt.index('vends'))

    def test_phrase_unique_pas_de_reorder(self):
        r = _optimise("Explique la récursivité.")
        self.assertFalse(r['restructured'])

    def test_garde_anti_coreference(self):
        r = _optimise("Mon serveur renvoie une erreur 502. Cela, explique-le en détail.")
        self.assertFalse(r['restructured'])

    def test_verbatim_aucun_mot_perdu(self):
        r = _optimise("Je lance une marque écoresponsable cette année. Rédige-moi un plan marketing complet.")
        if r['restructured']:
            for w in ('écoresponsable', 'marketing', 'rédige'):
                self.assertIn(w, r['optimised'].lower())

    def test_idempotence(self):
        r1 = _optimise("Je vends des bougies artisanales depuis deux ans. Donne-moi une stratégie SEO.")
        r2 = _optimise(r1['optimised'])
        self.assertFalse(r2['restructured'])

    def test_optimised_flat_present(self):
        r = _optimise("Je vends des bougies. Donne-moi une stratégie SEO.")
        self.assertIn('optimised_flat', r)
        self.assertTrue(isinstance(r['optimised_flat'], str))


class TestQualityNote(unittest.TestCase):

    def test_cles_et_bornes(self):
        q = _optimise("Explique la récursivité en 3 points.")['quality_note']
        self.assertEqual(set(q.keys()),
                         {'clarte', 'specificite', 'structure', 'concision', 'global'})
        for k, v in q.items():
            self.assertTrue(0 <= v <= 100, f"{k}={v} hors bornes")

    def test_additif_pertinence_conservee(self):
        r = _optimise("s'il te plait explique-moi la récursivité")
        self.assertIn('pertinence_score', r)
        self.assertIn('quality_note', r)


class TestContratStable(unittest.TestCase):

    def test_cles_contrat(self):
        r = _optimise("Explique la récursivité s'il te plait.")
        for k in ('optimised', 'optimised_flat', 'restructured', 'pertinence_score',
                  'complexity', 'quality_note', 'tokens_before', 'tokens_after'):
            self.assertIn(k, r)


class TestDegenere(unittest.TestCase):

    def test_entrees_degenerees_sans_crash(self):
        for deg in ('', '   ', '😀😀', 'https://example.com', '123 456'):
            r = _optimise(deg)
            self.assertIn('optimised_flat', r)
            self.assertIn(r['restructured'], (True, False))


class TestE3Chips(unittest.TestCase):

    def test_chips_technique_retourne_slots_manquants(self):
        r = _optimise("Écris une fonction qui parse du JSON")
        self.assertEqual(r['complexity'], 'technique')
        slots = [c['slot'] for c in r['chips']]
        self.assertIn('langage', slots)
        self.assertIn('format_sortie', slots)

    def test_chips_technique_masque_slot_deja_present(self):
        r = _optimise("Écris une fonction Python qui parse du JSON")
        slots = [c['slot'] for c in r['chips']]
        self.assertNotIn('langage', slots)       # Python détecté → slot masqué
        self.assertIn('format_sortie', slots)    # toujours manquant

    def test_chips_simple_vide(self):
        r = _optimise("Bonjour")
        self.assertEqual(r['complexity'], 'simple')
        self.assertEqual(r['chips'], [])

    def test_chips_analytique_retourne_slots(self):
        r = _optimise("Compare React et Vue pour un projet e-commerce")
        self.assertEqual(r['complexity'], 'analytique')
        slots = [c['slot'] for c in r['chips']]
        self.assertIn('criteres', slots)

    def test_chips_analytique_masque_format_present(self):
        r = _optimise("Compare React et Vue, retourne un tableau avec pros et cons")
        slots = [c['slot'] for c in r['chips']]
        self.assertNotIn('format', slots)        # tableau + pros/cons détectés

    def test_chips_documentaire_retourne_slots(self):
        r = _optimise("Rédige un guide complet sur Docker")
        self.assertEqual(r['complexity'], 'documentaire')
        slots = [c['slot'] for c in r['chips']]
        self.assertIn('audience', slots)
        self.assertIn('niveau', slots)

    def test_chips_champ_present_dans_reponse(self):
        r = _optimise("Explique la récursivité")
        self.assertIn('chips', r)
        self.assertIsInstance(r['chips'], list)


from unittest import mock


class TestPolicyIntegration(unittest.TestCase):
    def test_unsafe_gating_overrides_palier_to_free(self):
        from ml.policy import PolicyDecision
        with mock.patch("utils.optimiseur.decide_policy",
                        return_value=PolicyDecision(False, 0.1, "model")):
            r = _optimise("Compare en profondeur les avantages et inconvénients du nucléaire")
            self.assertEqual(r["palier"], "5")
            self.assertEqual(r["gating_source"], "model")
            self.assertFalse(r["gating_compress"])

    def test_safe_gating_keeps_heuristic_palier(self):
        from ml.policy import PolicyDecision
        with mock.patch("utils.optimiseur.decide_policy",
                        return_value=PolicyDecision(True, 0.9, "model")):
            r = _optimise("Explique-moi la récursivité ?")
            self.assertNotEqual(r["palier"], "5")
            self.assertTrue(r["gating_compress"])

    def test_fallback_preserves_current_behavior(self):
        from ml.policy import PolicyDecision
        with mock.patch("utils.optimiseur.decide_policy",
                        return_value=PolicyDecision(True, 0.0, "fallback")):
            r = _optimise("Explique-moi la récursivité ?")
            self.assertEqual(r["gating_source"], "fallback")
