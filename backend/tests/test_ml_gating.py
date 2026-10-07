import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
import numpy as np
from ml import gating


class TestGatingLoader(unittest.TestCase):
    def test_missing_artifact_returns_none(self):
        g = gating.GatingModel(path="/chemin/inexistant.joblib")
        self.assertFalse(g.available)
        self.assertIsNone(g.predict_safe(np.zeros(8, dtype="float32")))

    def test_loaded_model_predicts_probability(self):
        g = gating.GatingModel()  # charge l'artifact par défaut
        if not g.available:
            self.skipTest("artifact absent — lancer train_gating.py d'abord")
        # vecteur structurel de bonne taille
        from ml.features import structural_features
        p = g.predict_safe(structural_features("Explique la récursivité en 50 mots"))
        self.assertIsInstance(p, float)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)


if __name__ == "__main__":
    unittest.main()
