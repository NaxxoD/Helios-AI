import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from ml import policy


class TestPolicy(unittest.TestCase):
    def test_fallback_when_model_unavailable(self):
        # force un modèle indisponible
        d = policy.decide_policy("Explique la récursivité", model=policy._UnavailableModel())
        self.assertTrue(d.compress)               # fallback = comportement actuel (on comprime)
        self.assertEqual(d.source, "fallback")

    def test_compress_decision_respects_threshold(self):
        class FakeModel:
            available = True
            def predict_safe(self, vec):
                return 0.9
        d = policy.decide_policy("Explique", model=FakeModel(),
                                 struct_only=True, threshold=0.5)
        self.assertTrue(d.compress)
        self.assertEqual(d.source, "model")

        class FakeLow(FakeModel):
            def predict_safe(self, vec):
                return 0.2
        d2 = policy.decide_policy("Explique", model=FakeLow(),
                                  struct_only=True, threshold=0.5)
        self.assertFalse(d2.compress)


if __name__ == "__main__":
    unittest.main()
