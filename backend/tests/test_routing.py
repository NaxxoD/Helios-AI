"""#19 : suggest_routing (module live, alimente l'endpoint optimiseur) — classification."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from utils.routing import suggest_routing


class TestRouting(unittest.TestCase):

    def test_debug_effort_haut(self):
        r = suggest_routing("j'ai un bug, traceback TypeError dans mon code python")
        self.assertEqual(r["effort"], "high")
        self.assertIn(r["model_tier"], ("medium", "complex"))

    def test_qa_factuelle_simple_off(self):
        r = suggest_routing("c'est quoi la photosynthèse ?")
        self.assertEqual(r["model_tier"], "simple")
        self.assertEqual(r["effort"], "off")

    def test_challenge_complex_xhigh(self):
        r = suggest_routing("challenge mon hypothèse, c'est une décision critique")
        self.assertEqual(r["model_tier"], "complex")
        self.assertEqual(r["effort"], "xhigh")

    def test_aucun_signal_fallback(self):
        r = suggest_routing("xyzzy foobar quux")
        self.assertEqual(r["model_tier"], "medium")
        self.assertIsNone(r["effort"])
        self.assertEqual(r["confidence"], 0)


if __name__ == "__main__":
    unittest.main()
