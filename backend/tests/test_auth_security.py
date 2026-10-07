"""Tests de sécurité du router auth.

#4 (faille majeure) : le token de vérification d'email ne doit JAMAIS apparaître
dans les logs (sinon prise de contrôle de compte via accès aux logs).
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest import mock

import routers.auth as auth
from schemas.auth import ForgotPasswordIn


def _run(coro):
    return asyncio.run(coro)


class _FakeUser:
    def __init__(self):
        self.email = "user@example.com"
        self.is_verified = False
        self.verification_token = "SECRET_TOKEN_DO_NOT_LOG_123"


class TestAuthTokenNotLogged(unittest.TestCase):

    def _call_resend(self, fake_user, fake_db):
        # contourne le décorateur slowapi si présent
        fn = getattr(auth.resend_verification, "__wrapped__", auth.resend_verification)
        with mock.patch.object(auth.user_repo, "get_by_email", return_value=fake_user), \
             mock.patch.object(auth, "send_verification_email", new=mock.AsyncMock()), \
             self.assertLogs("routers.auth", level="DEBUG") as cm:
            _run(fn(mock.Mock(), ForgotPasswordIn(email=fake_user.email), fake_db))
        return "\n".join(cm.output)

    def test_resend_verification_ne_logge_pas_le_token(self):
        fake_user = _FakeUser()
        logs = self._call_resend(fake_user, mock.Mock())
        # le secret ne doit apparaître dans AUCUN log
        self.assertNotIn(fake_user.verification_token, logs)
        # l'observabilité « qui » est préservée
        self.assertIn(fake_user.email, logs)


if __name__ == "__main__":
    unittest.main()
