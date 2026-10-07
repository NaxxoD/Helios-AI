"""Sécurité du router optimiseur.

#11 (faille) : l'écriture du dataset noise_candidates (save_candidates=True) ne doit
PAS être possible pour un appelant anonyme (pollution du dataset sans authentification).
"""
import sys, os, asyncio, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest import mock

import routers.optimiseur as opt
from routers.optimiseur import OptimiseRequest


def _run(coro):
    return asyncio.run(coro)


_FAKE_RESULT = {
    "noise_candidates": [{"text": "bla bla", "score": 0.85}],
    "optimised_flat": "",
    "palier": "2",
}


class TestOptimiseSaveCandidatesAuth(unittest.TestCase):

    def _call(self, user):
        fn = inspect.unwrap(opt.optimise_prompt)   # déballe les 2 décorateurs slowapi
        upsert = mock.Mock()
        with mock.patch.object(opt, "optimise", return_value=dict(_FAKE_RESULT)), \
             mock.patch.object(opt, "suggest_routing",
                               return_value={"effort": None, "model_tier": "medium",
                                             "task": None, "confidence": 0}), \
             mock.patch.object(opt.noise_candidate_repo, "upsert", upsert):
            body = OptimiseRequest(prompt="un prompt de test", save_candidates=True, semantic=False)
            _run(fn(mock.Mock(), body, db=mock.Mock(), user=user))
        return upsert

    def test_anonyme_ne_peut_pas_ecrire_le_dataset(self):
        upsert = self._call(user=None)
        upsert.assert_not_called()

    def test_authentifie_peut_ecrire_le_dataset(self):
        upsert = self._call(user=mock.Mock())   # utilisateur authentifié
        upsert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
