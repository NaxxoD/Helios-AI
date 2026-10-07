"""Jalon 3 — cœur déterministe du sous-agent mémoire : plan de compaction, gate de
couverture (Couche 1), gate de cohérence d'état (retour du co-auteur), évaluation combinée."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from services import memory_service as mem


def _big_turns(n):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": "mot " * 3000}
            for i in range(n)]


class TestPlanCompaction(unittest.TestCase):

    def test_sous_keep_pas_de_compaction(self):
        p = mem.plan_compaction(_big_turns(3), keep=4)
        self.assertFalse(p["should_compact"])
        self.assertEqual(p["fold"], [])
        self.assertEqual(len(p["recent"]), 3)

    def test_seuil_non_atteint(self):
        msgs = [{"role": "user", "content": "court"} for _ in range(10)]
        p = mem.plan_compaction(msgs, keep=4, seuil=8000)
        self.assertFalse(p["should_compact"])
        self.assertEqual(len(p["recent"]), 4)
        self.assertEqual(len(p["fold"]), 6)

    def test_seuil_atteint(self):
        p = mem.plan_compaction(_big_turns(8), keep=4, seuil=8000)
        self.assertTrue(p["should_compact"])
        self.assertEqual(len(p["recent"]), 4)
        self.assertEqual(len(p["fold"]), 4)


class TestCoverageGate(unittest.TestCase):
    FOLD = [{"role": "user",
             "content": "Budget 5000, version 3, 42 utilisateurs, deadline 12 mars 2026."}]

    def test_vide_rejete(self):
        ok, _ = mem.coverage_gate("", self.FOLD)
        self.assertFalse(ok)

    def test_degenere_rejete(self):
        ok, reason = mem.coverage_gate("oui oui oui " * 30, self.FOLD)
        self.assertFalse(ok)

    def test_resume_fidele_sans_tous_les_chiffres_passe(self):
        # #4.1c : un résumé abandonne par nature les chiffres incidents du brut → la Couche 1
        # ne doit PAS le rejeter (la couverture sémantique est le job de la Couche 2 juge).
        ok, _ = mem.coverage_gate("Un résumé en prose qui ne reprend aucun chiffre du brut.", self.FOLD)
        self.assertTrue(ok)

    def test_resume_normal_passe(self):
        ok, _ = mem.coverage_gate(
            "Projet : budget 5000, version 3, 42 utilisateurs, deadline 12 mars 2026.", self.FOLD)
        self.assertTrue(ok)


class TestStateGate(unittest.TestCase):
    FOLD = [{"role": "user", "content": "accès bloqué"},
            {"role": "assistant", "content": "après relance → accès résolu"}]

    def test_contradiction_detectee(self):
        judge = lambda s, u: {"contradiction": True, "detail": "dit bloqué, brut finit résolu"}
        ok, detail = mem.state_consistency_ok("L'accès est bloqué.", self.FOLD, judge)
        self.assertFalse(ok)
        self.assertIn("résolu", detail)

    def test_pas_de_contradiction(self):
        judge = lambda s, u: {"contradiction": False}
        ok, _ = mem.state_consistency_ok("L'accès est résolu.", self.FOLD, judge)
        self.assertTrue(ok)


class TestEvaluateSummary(unittest.TestCase):
    FOLD = [{"role": "user", "content": "Budget 5000, version 3, 42 users, deadline 12 mars 2026."}]
    GOOD = "Budget 5000, version 3, 42 users, deadline 12 mars 2026."

    def test_couverture_ko_court_circuite(self):
        ok, reason = mem.evaluate_summary("", self.FOLD, state_judge=lambda s, u: {"contradiction": False})
        self.assertFalse(ok)
        self.assertIn("vide", reason)

    def test_etat_ko_rejette(self):
        judge = lambda s, u: {"contradiction": True, "detail": "X"}
        ok, reason = mem.evaluate_summary(self.GOOD, self.FOLD, judge)
        self.assertFalse(ok)
        self.assertIn("état", reason)

    def test_tout_ok(self):
        judge = lambda s, u: {"contradiction": False}
        ok, _ = mem.evaluate_summary(self.GOOD, self.FOLD, judge)
        self.assertTrue(ok)

    def test_sans_state_judge_couverture_seule(self):
        ok, _ = mem.evaluate_summary(self.GOOD, self.FOLD)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
