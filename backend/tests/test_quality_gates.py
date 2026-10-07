"""Tests unitaires de la Couche 1 (quality_gates) — gates déterministes, sans réseau."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from utils.quality_gates import (
    is_empty, is_refusal, is_truncated, repetition_ratio, is_degenerate_repetition,
    bad_format, wrong_language, over_length, needs_escalation, is_unjudgeable, text_of,
)


class TestVide(unittest.TestCase):
    def test_vide(self):
        self.assertTrue(is_empty(""))
        self.assertTrue(is_empty("   \n  "))
        self.assertFalse(is_empty("Une vraie réponse."))


class TestRefus(unittest.TestCase):
    def test_refus_court_en_tete(self):
        self.assertTrue(is_refusal("Je ne peux pas répondre à cette demande."))
        self.assertTrue(is_refusal("I'm unable to help with that."))

    def test_faux_positif_garantir(self):
        # 'je ne peux pas garantir' n'est PAS un refus (lookahead négatif)
        self.assertFalse(is_refusal("Je ne peux pas garantir l'exactitude, mais voici."))

    def test_faux_positif_enfoui_dans_longue_reponse(self):
        long = "Voici une analyse détaillée. " * 20 + "je ne peux pas tout couvrir."
        self.assertFalse(is_refusal(long))   # > 250 car. → pas un refus sec


class TestTroncature(unittest.TestCase):
    def test_flag_explicite(self):
        self.assertTrue(is_truncated({"trunc": True}))
        self.assertTrue(is_truncated({"truncated": True}))

    def test_finish_reason(self):
        self.assertTrue(is_truncated({"finish_reason": "length"}))

    def test_ratio_tokens(self):
        self.assertTrue(is_truncated({"out": 96, "num_predict": 100}))
        self.assertTrue(is_truncated({"output_tokens": 990, "max_tokens": 1000}))
        self.assertFalse(is_truncated({"out": 50, "num_predict": 100}))

    def test_tokens_en_chaine_pas_de_crash(self):
        # #13 : compteurs fournis en str → coercition, pas de TypeError
        self.assertTrue(is_truncated({"output_tokens": "990", "max_tokens": "1000"}))
        self.assertFalse(is_truncated({"output_tokens": "50", "max_tokens": "1000"}))
        self.assertFalse(is_truncated({"output_tokens": "abc", "max_tokens": "1000"}))

    def test_aucune_info(self):
        self.assertFalse(is_truncated({}))
        self.assertFalse(is_truncated("texte brut"))


class TestRepetition(unittest.TestCase):
    def test_ratio(self):
        self.assertAlmostEqual(repetition_ratio("a a a a"), 0.25)
        self.assertAlmostEqual(repetition_ratio("un deux trois"), 1.0)
        self.assertAlmostEqual(repetition_ratio(""), 1.0)

    def test_boucle_degeneree(self):
        self.assertTrue(is_degenerate_repetition(("le " * 60)))           # ratio ~0

    def test_texte_normal(self):
        texte = " ".join(f"mot{i}" for i in range(50))                    # tous uniques
        self.assertFalse(is_degenerate_repetition(texte))

    def test_court_exempte(self):
        self.assertFalse(is_degenerate_repetition("le le le"))            # < 40 mots


class TestFormat(unittest.TestCase):
    def test_json_valide(self):
        self.assertFalse(bad_format('{"a": 1}', "json"))

    def test_json_invalide(self):
        self.assertTrue(bad_format("{a: 1, oops", "json"))
        self.assertTrue(bad_format("aucun json ici", "json"))

    def test_format_non_demande(self):
        self.assertFalse(bad_format("n'importe quoi", None))


class TestLangue(unittest.TestCase):
    def test_mauvaise_langue(self):
        det = lambda t: "en"
        self.assertTrue(wrong_language("a" * 50, "fr", detect_lang=det))

    def test_bonne_langue(self):
        det = lambda t: "fr"
        self.assertFalse(wrong_language("a" * 50, "fr", detect_lang=det))

    def test_desactive_sans_detecteur(self):
        self.assertFalse(wrong_language("a" * 50, "fr", detect_lang=None))

    def test_desactive_texte_court(self):
        self.assertFalse(wrong_language("court", "fr", detect_lang=lambda t: "en"))


class TestLongueur(unittest.TestCase):
    def test_depassement(self):
        self.assertTrue(over_length(" ".join(["mot"] * 140), 100))   # 140 > 1.3*100
    def test_dans_cible(self):
        self.assertFalse(over_length(" ".join(["mot"] * 100), 100))
    def test_pas_de_cible(self):
        self.assertFalse(over_length("x", None))


class TestNeedsEscalation(unittest.TestCase):
    def test_vide(self):
        self.assertEqual(needs_escalation({"content": ""}), (True, "vide"))

    def test_erreur_prioritaire(self):
        self.assertEqual(needs_escalation({"content": "ok", "error": "boom"}), (True, "erreur"))

    def test_troncature(self):
        esc, motif = needs_escalation({"content": "réponse correcte ici", "trunc": True})
        self.assertTrue(esc); self.assertEqual(motif, "troncature")

    def test_refus(self):
        self.assertEqual(needs_escalation({"content": "Je ne peux pas répondre."}),
                         (True, "refus"))

    def test_ok(self):
        bonne = {"content": "Voici une réponse complète, correcte et variée à la demande posée."}
        self.assertEqual(needs_escalation(bonne), (False, "ok"))

    def test_flag_longueur_pas_escalade(self):
        # 200 mots DISTINCTS (sinon le gate répétition saute avant) → seul le
        # drapeau longueur doit ressortir, sans escalade
        resp = {"content": " ".join(f"m{i}" for i in range(200))}
        esc, motif = needs_escalation(resp, max_words=100)
        self.assertFalse(esc); self.assertEqual(motif, "flag:longueur")


class TestIsUnjudgeable(unittest.TestCase):
    def test_tronque_exclu(self):
        self.assertTrue(is_unjudgeable({"content": "x" * 50, "trunc": True}))

    def test_vide_exclu(self):
        self.assertTrue(is_unjudgeable({"content": ""}))

    def test_refus_PAS_exclu(self):
        # un refus est une vraie dégradation → on le garde pour le juge
        self.assertFalse(is_unjudgeable({"content": "Je ne peux pas répondre."}))

    def test_bonne_reponse_gardee(self):
        self.assertFalse(is_unjudgeable({"content": "Une réponse normale et complète."}))


if __name__ == "__main__":
    unittest.main()
