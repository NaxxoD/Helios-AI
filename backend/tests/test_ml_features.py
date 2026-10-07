import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import unittest
from ml import features


class TestStructuralFeatures(unittest.TestCase):
    def test_structural_vector_length_and_values(self):
        # n'appelle PAS Ollama : teste seulement la partie structurelle
        feats = features.structural_features("Explique-moi la récursivité en 50 mots ?")
        # 8 features structurels attendus, ordre stable
        self.assertEqual(len(feats), features.N_STRUCTURAL)
        self.assertEqual(features.N_STRUCTURAL, 8)
        # word_count > 0, question_marks == 1, has_constraint == 1 ("50 mots")
        names = features.STRUCTURAL_NAMES
        d = dict(zip(names, feats))
        self.assertGreater(d["word_count"], 0)
        self.assertEqual(d["question_marks"], 1.0)
        self.assertEqual(d["has_constraint"], 1.0)

    def test_palier_feature_uses_backend_logic(self):
        feats = dict(zip(features.STRUCTURAL_NAMES,
                         features.structural_features("Écris une fonction Python qui trie une liste")))
        # detect_palier renvoie 'C' (code) -> encodé en index numérique stable
        self.assertGreaterEqual(feats["palier_idx"], 0)


if __name__ == "__main__":
    unittest.main()
