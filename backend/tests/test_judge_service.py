"""Tests unitaires des fonctions PURES de judge_service (Couche 2 de la grille).

On ne teste PAS les appels LLM (IO) — seulement la logique déterministe :
kappa de Cohen, remap anti-biais Profil A, scoring/verdict Profil B.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from services.judge_service import (
    cohen_kappa, remap_profil_a, score_bareme, verdict_profil_b, compare_profil_b,
)


class TestCohenKappa(unittest.TestCase):

    def test_accord_parfait(self):
        self.assertAlmostEqual(cohen_kappa([1, 1, 2, 2, 3], [1, 1, 2, 2, 3]), 1.0)

    def test_niveau_hasard(self):
        # 50% d'accord brut mais entièrement explicable par le hasard → κ = 0
        self.assertAlmostEqual(cohen_kappa(["y", "y", "n", "n"],
                                           ["y", "n", "y", "n"]), 0.0)

    def test_pire_que_hasard(self):
        self.assertAlmostEqual(cohen_kappa(["y", "y", "n", "n"],
                                           ["n", "n", "y", "y"]), -1.0)

    def test_accord_modere_valeur_connue(self):
        # 75% d'accord brut, marginales (3/4,1/4) vs (2/4,2/4) → p_e=0.5 → κ=0.5
        self.assertAlmostEqual(cohen_kappa(["y", "y", "y", "n"],
                                           ["y", "y", "n", "n"]), 0.5)

    def test_categorie_unique_accord_trivial(self):
        self.assertAlmostEqual(cohen_kappa(["y", "y", "y"], ["y", "y", "y"]), 1.0)

    def test_erreurs(self):
        with self.assertRaises(ValueError):
            cohen_kappa([1, 2], [1])
        with self.assertRaises(ValueError):
            cohen_kappa([], [])


class TestRemapProfilA(unittest.TestCase):
    # Sans swap : la candidate est affichée en "Réponse 2".
    def test_sans_swap_candidate_meilleure(self):
        v = remap_profil_a({"meilleure": "2", "ecart": "aucun",
                            "exactitude_ko": "aucune"}, swap=False)
        self.assertEqual(v["candidate_vs_ref"], "meilleure")
        self.assertEqual(v["verdict"], "equivalent")

    def test_sans_swap_candidate_moins_bonne_mineur(self):
        v = remap_profil_a({"meilleure": "1", "ecart": "mineur",
                            "exactitude_ko": "aucune"}, swap=False)
        self.assertEqual(v["candidate_vs_ref"], "moins_bonne")
        self.assertEqual(v["verdict"], "tolerable")

    def test_sans_swap_ecart_majeur_inacceptable(self):
        v = remap_profil_a({"meilleure": "1", "ecart": "majeur",
                            "exactitude_ko": "aucune"}, swap=False)
        self.assertEqual(v["verdict"], "inacceptable")

    def test_exactitude_candidate_veto(self):
        # candidate (="2" sans swap) a une erreur factuelle → veto, même si "meilleure"
        v = remap_profil_a({"meilleure": "2", "ecart": "aucun",
                            "exactitude_ko": "2"}, swap=False)
        self.assertTrue(v["exactitude_candidate_ko"])
        self.assertEqual(v["verdict"], "inacceptable")

    def test_avec_swap_candidate_meilleure(self):
        # swap=True → candidate affichée en "Réponse 1"
        v = remap_profil_a({"meilleure": "1", "ecart": "aucun",
                            "exactitude_ko": "aucune"}, swap=True)
        self.assertEqual(v["candidate_vs_ref"], "meilleure")
        self.assertEqual(v["verdict"], "equivalent")

    def test_avec_swap_erreur_sur_reference_pas_penalisee(self):
        # exactitude_ko="2" = la référence (swap) a l'erreur, pas la candidate
        v = remap_profil_a({"meilleure": "1", "ecart": "aucun",
                            "exactitude_ko": "2"}, swap=True)
        self.assertFalse(v["exactitude_candidate_ko"])
        self.assertEqual(v["verdict"], "equivalent")

    def test_egal_equivalent(self):
        v = remap_profil_a({"meilleure": "egal"}, swap=False)
        self.assertEqual(v["verdict"], "equivalent")


class TestScoreBareme(unittest.TestCase):
    BAREME = [
        {"id": 1, "element": "a", "essentiel": True},
        {"id": 2, "element": "b", "essentiel": True},
        {"id": 3, "element": "c", "essentiel": False},
    ]

    def test_couverture_mixte(self):
        couv = [{"id": 1, "statut": "couvert"}, {"id": 2, "statut": "partiel"},
                {"id": 3, "statut": "absent"}]
        s = score_bareme(self.BAREME, couv)
        self.assertAlmostEqual(s["score_essentiel"], 0.75)   # (1.0+0.5)/2
        self.assertAlmostEqual(s["score_global"], 0.5)       # (1.0+0.5+0.0)/3
        self.assertEqual(s["essentiel_absents"], 0)
        self.assertEqual(s["n_essentiel"], 2)

    def test_essentiel_absent_compte(self):
        couv = [{"id": 1, "statut": "absent"}, {"id": 2, "statut": "couvert"},
                {"id": 3, "statut": "couvert"}]
        s = score_bareme(self.BAREME, couv)
        self.assertEqual(s["essentiel_absents"], 1)
        self.assertAlmostEqual(s["score_essentiel"], 0.5)

    def test_id_manquant_traite_absent(self):
        # couverture ne mentionne pas l'id 2 → compté absent
        s = score_bareme(self.BAREME, [{"id": 1, "statut": "couvert"}])
        self.assertEqual(s["essentiel_absents"], 1)

    def test_bareme_sans_cle_id_ne_crash_pas(self):
        # #14 : barème hand-crafted sans clé 'id' → pas de KeyError (e.get('id'))
        s = score_bareme([{"element": "a", "essentiel": True}], [])
        self.assertIn("score_essentiel", s)
        self.assertEqual(s["essentiel_absents"], 1)


class TestVerdictProfilB(unittest.TestCase):

    def test_exactitude_ko_inacceptable(self):
        s = {"score_essentiel": 1.0, "essentiel_absents": 0}
        self.assertEqual(verdict_profil_b(s, exactitude_ok=False), "inacceptable")

    def test_essentiel_absent_inacceptable(self):
        s = {"score_essentiel": 0.8, "essentiel_absents": 1}
        self.assertEqual(verdict_profil_b(s, exactitude_ok=True), "inacceptable")

    def test_tout_essentiel_couvert_equivalent(self):
        s = {"score_essentiel": 1.0, "essentiel_absents": 0}
        self.assertEqual(verdict_profil_b(s, exactitude_ok=True), "equivalent")

    def test_essentiel_partiel_tolerable(self):
        s = {"score_essentiel": 0.75, "essentiel_absents": 0}
        self.assertEqual(verdict_profil_b(s, exactitude_ok=True), "tolerable")


class TestCompareProfilB(unittest.TestCase):

    def test_candidate_meilleure(self):
        self.assertEqual(compare_profil_b({"score_essentiel": 0.5},
                                          {"score_essentiel": 0.9}), "candidate_meilleure")

    def test_candidate_moins_bonne(self):
        self.assertEqual(compare_profil_b({"score_essentiel": 0.9},
                                          {"score_essentiel": 0.5}), "candidate_moins_bonne")

    def test_equivalent_sous_seuil(self):
        self.assertEqual(compare_profil_b({"score_essentiel": 0.80},
                                          {"score_essentiel": 0.85}), "equivalent")


class TestRetry(unittest.TestCase):
    """Retry-on-timeout (retour du co-auteur). time.sleep monkeypatché → test rapide."""

    def _patch(self, fake_post):
        import services.judge_service as js
        self._orig = (js.httpx.post, js.time.sleep)
        js.httpx.post, js.time.sleep = fake_post, (lambda *_: None)
        return js

    def tearDown(self):
        if hasattr(self, "_orig"):
            import services.judge_service as js
            js.httpx.post, js.time.sleep = self._orig

    def test_recupere_apres_un_timeout(self):
        calls = {"n": 0}
        class FakeResp: status_code = 200
        def fake_post(*a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                import services.judge_service as js
                raise js.httpx.TimeoutException("boom")
            return FakeResp()
        js = self._patch(fake_post)
        r = js._post_with_retry("u", {}, {}, retries=3)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(calls["n"], 2)        # 1 échec + 1 succès

    def test_retries_epuises_releve(self):
        import services.judge_service as js
        def always_timeout(*a, **k):
            raise js.httpx.TimeoutException("boom")
        self._patch(always_timeout)
        with self.assertRaises(js.httpx.TimeoutException):
            js._post_with_retry("u", {}, {}, retries=2)


if __name__ == "__main__":
    unittest.main()
