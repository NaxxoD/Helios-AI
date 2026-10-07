"""#20 : helpers purs de qwen_optimizer (parsing JSON tolérant + cohérence audit)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from utils.qwen_optimizer import _escape_ctrl_in_strings, _fix_audit_coherence


class TestEscapeCtrl(unittest.TestCase):

    def test_newline_dans_string_devient_parsable(self):
        s = '{"a": "ligne1\nligne2"}'      # retour à la ligne BRUT dans la string → JSON invalide
        out = _escape_ctrl_in_strings(s)
        self.assertEqual(json.loads(out)["a"], "ligne1\nligne2")

    def test_newline_hors_string_inoffensif(self):
        s = '{\n  "a": "x"\n}'             # sauts de ligne hors string = whitespace valide
        out = _escape_ctrl_in_strings(s)
        self.assertEqual(json.loads(out)["a"], "x")


class TestFixAuditCoherence(unittest.TestCase):

    def test_ligne_template_force_audit_inferred(self):
        result = {
            "audit": {"role": "absent", "contexte": "absent", "tache": "absent",
                      "contraintes": "absent", "format": "absent", "qualite": "absent"},
            "composantes_manquantes": ["role", "contexte", "tache",
                                       "contraintes", "format", "qualite"],
            "prompt_restructure": "Tu es expert.\nTu dois coder.",
        }
        fixed = _fix_audit_coherence(result)
        self.assertEqual(fixed["audit"]["role"], "inferred")   # "Tu es " présent
        self.assertEqual(fixed["audit"]["tache"], "inferred")  # "Tu dois " présent
        self.assertNotIn("role", fixed["composantes_manquantes"])
        self.assertNotIn("tache", fixed["composantes_manquantes"])


if __name__ == "__main__":
    unittest.main()
