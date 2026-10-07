"""#12 : get_optional_user ne doit avaler que les ValueError (token invalide),
tracer toute autre erreur, et ne jamais crasher l'endpoint optionnel."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest import mock

import dependencies as deps


class _Req:
    def __init__(self, token=None):
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.cookies = {}


class TestGetOptionalUser(unittest.TestCase):

    def test_pas_de_token_retourne_none(self):
        self.assertIsNone(deps.get_optional_user(_Req(), mock.Mock()))

    def test_token_invalide_retourne_none(self):
        import services.auth_service as a
        with mock.patch.object(a, "decode_token", side_effect=ValueError("bad")):
            self.assertIsNone(deps.get_optional_user(_Req("x"), mock.Mock()))

    def test_erreur_inattendue_loggee_et_none(self):
        import services.auth_service as a
        db = mock.Mock()
        db.get.side_effect = RuntimeError("db down")
        with mock.patch.object(a, "decode_token", return_value=1), \
             self.assertLogs("dependencies", level="WARNING") as cm:
            self.assertIsNone(deps.get_optional_user(_Req("x"), db))
        self.assertTrue(any("inattendue" in x.lower() for x in cm.output))


if __name__ == "__main__":
    unittest.main()
