"""Jalon 4.1a — harness e2e (SANS crédits) du flux composé memory → orchestrate → provider.

On n'exerce QUE du vrai code (memory_service.plan/gates, apply_memory, orchestrate, call_helios,
_assemble_system, parsing réponse) ; seule la frontière HTTP (httpx.AsyncClient) est mockée.
But : prouver que le câblage bout-en-bout tient — le résumé s'injecte en `context`, l'agent
principal ne voit que les KEEP derniers tours (fenêtre dégonflée), la réponse est assemblée.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest import mock

import services.chat_service as cs
import services.orchestrator_service as orch


def _run(coro):
    return asyncio.run(coro)


def _anthropic_payload(content):
    return {"content": [{"type": "text", "text": content}],
            "usage": {"input_tokens": 10, "output_tokens": 5}}


class _RecordingClient:
    """AsyncClient factice qui ENREGISTRE tous les bodies POST (pour inspecter le flux)."""
    calls = []
    resp_content = "Résumé structuré : objectif, décisions, entités, questions ouvertes."

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kw):
        _RecordingClient.calls.append(kw.get("json"))

        class R:
            status_code = 200
            content = b"{}"
            def json(self_inner):
                return _anthropic_payload(_RecordingClient.resp_content)
        return R()


def _patch():
    _RecordingClient.calls = []
    return mock.patch.object(cs.httpx, "AsyncClient", _RecordingClient)


class TestE2EMemoryOrchestrate(unittest.TestCase):

    def _long_history(self):
        # 9 tours longs (≈3000 tk/tour) finissant sur un message user → fold dépasse le seuil
        return [{"role": "user" if i % 2 == 0 else "assistant", "content": "mot " * 3000}
                for i in range(9)]

    def test_flux_complet_memory_puis_orchestrate(self):
        async def flow():
            msgs = self._long_history()
            # 1) sous-agent mémoire (vrai apply_memory ; résumeur via call_llm → _anthropic → httpx mock)
            mem = await orch.apply_memory(msgs, "k")
            self.assertTrue(mem["compacted"])
            self.assertEqual(len(mem["messages"]), 4)        # KEEP derniers tours verbatim
            # 2) orchestrateur sur l'historique dégonflé + résumé injecté en context
            res = await orch.orchestrate("Anthropic", "claude-haiku-4-5", "k",
                                         mem["messages"], context=mem["context"])
            return res

        with _patch():
            res = _run(flow())

        bodies = _RecordingClient.calls
        self.assertGreaterEqual(len(bodies), 2)   # résumeur + agent principal
        # 1er appel = résumeur : system = prompt du sous-agent mémoire, et le message user
        # porte la consigne « résume, ne continue pas » (fix anti-continuation, smoke live)
        self.assertIn("SOUS-AGENT MÉMOIRE", bodies[0]["system"][0]["text"])
        self.assertIn("À RÉSUMER", bodies[0]["messages"][0]["content"])
        # dernier appel = agent principal : le résumé est bien injecté dans le system (context)
        main = bodies[-1]
        self.assertIn(_RecordingClient.resp_content, main["system"][0]["text"])
        # fenêtre dégonflée : l'agent principal ne reçoit que les KEEP tours récents (≠ 9)
        self.assertEqual(len(main["messages"]), 4)
        # réponse assemblée + traçabilité d'orchestration
        self.assertEqual(res["content"], _RecordingClient.resp_content)
        self.assertIn("orchestration", res)

    def test_rollback_resume_vide_ne_compacte_pas(self):
        async def flow():
            msgs = self._long_history()
            _RecordingClient.resp_content = ""   # résumeur renvoie vide → coverage_gate KO
            try:
                return await orch.apply_memory(msgs, "k")
            finally:
                _RecordingClient.resp_content = "Résumé structuré : objectif, décisions."

        with _patch():
            mem = _run(flow())
        self.assertFalse(mem["compacted"])
        self.assertIsNone(mem["context"])
        self.assertEqual(len(mem["messages"]), 9)   # historique intact (aucune perte)
        self.assertIn("rollback", mem["reason"])


if __name__ == "__main__":
    unittest.main()
