"""#2.1 : objet Helios (format pivot) — (dé)sérialisation + valeurs par défaut."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from schemas.helios import HeliosCall, HeliosMessage


class TestHeliosCall(unittest.TestCase):

    def test_defaults(self):
        c = HeliosCall(provider="Anthropic", model="claude-haiku-4-5",
                       messages=[HeliosMessage(role="user", content="x")])
        self.assertIsNone(c.effort)
        self.assertIsNone(c.palier)
        self.assertIsNone(c.role)
        self.assertIsNone(c.context)

    def test_roundtrip(self):
        c = HeliosCall(provider="OpenAI", model="gpt-4o",
                       messages=[HeliosMessage(role="user", content="x")],
                       effort="high", palier="2", role="R", context="C")
        d = c.model_dump()
        self.assertEqual(d["effort"], "high")
        self.assertEqual(d["role"], "R")
        c2 = HeliosCall(**d)
        self.assertEqual(c2.messages[0].content, "x")
        self.assertEqual(c2.context, "C")


if __name__ == "__main__":
    unittest.main()
