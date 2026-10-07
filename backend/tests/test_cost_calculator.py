"""#21 : cost_calculator non testé + risque de dérive PRICING vs IDs modèles.

Le test croisé verrouille l'invariant : tout modèle adressable (clés _ANTHROPIC_IDS /
_GOOGLE_IDS de chat_service) DOIT avoir un tarif dans PRICING, sinon cost_usd=None
silencieux dans le payload de facturation.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from utils.cost_calculator import PRICING, calculate_cost, calculate_savings
import services.chat_service as cs


class TestPricingCoherence(unittest.TestCase):

    def test_anthropic_ids_couverts_par_pricing(self):
        for key in cs._ANTHROPIC_IDS:
            self.assertIn(key, PRICING["Anthropic"], f"{key} absent de PRICING['Anthropic']")

    def test_google_ids_couverts_par_pricing(self):
        for key in cs._GOOGLE_IDS:
            self.assertIn(key, PRICING["Google"], f"{key} absent de PRICING['Google']")


class TestCalculateCost(unittest.TestCase):

    def test_cout_connu(self):
        c = calculate_cost("Anthropic", "claude-haiku-4-5", 1_000_000, 1_000_000)
        self.assertAlmostEqual(c["input_cost_usd"], 1.0)
        self.assertAlmostEqual(c["output_cost_usd"], 5.0)
        self.assertAlmostEqual(c["cost_usd"], 6.0)

    def test_modele_inconnu_renvoie_none(self):
        c = calculate_cost("Anthropic", "modele-bidon", 100, 100)
        self.assertIsNone(c["cost_usd"])

    def test_savings(self):
        self.assertAlmostEqual(calculate_savings("Anthropic", "claude-haiku-4-5", 1_000_000), 1.0)
        self.assertIsNone(calculate_savings("Anthropic", "inconnu", 100))
        self.assertIsNone(calculate_savings("Anthropic", "claude-haiku-4-5", 0))


if __name__ == "__main__":
    unittest.main()
