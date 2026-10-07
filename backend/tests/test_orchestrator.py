"""#2.3 : orchestrateur opt-in — nettoie le dernier message, route, complète effort/palier,
puis appelle le LLM via call_helios. optimise/suggest_routing/call_helios sont mockés."""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest import mock

import services.orchestrator_service as orch


def _run(coro):
    return asyncio.run(coro)


class TestOrchestrate(unittest.TestCase):

    def test_nettoie_route_complete_et_appelle(self):
        fake_opt = {"optimised": "prompt nettoyé", "tokens_saved": 12, "palier": "2"}
        fake_routing = {"effort": "high", "model_tier": "medium", "task": "debug", "confidence": 6}

        async def fake_call_helios(call, api_key):
            fake_call_helios.captured = call
            return {"content": "ok", "input_tokens": 1, "output_tokens": 1}

        with mock.patch.object(orch, "optimise", return_value=fake_opt), \
             mock.patch.object(orch, "suggest_routing", return_value=fake_routing), \
             mock.patch.object(orch.chat_service, "call_helios", new=fake_call_helios):
            out = _run(orch.orchestrate("Anthropic", "claude-haiku-4-5", "k",
                                        [{"role": "user", "content": "prompt brut bla bla"}]))

        # résultat LLM + bloc d'orchestration
        self.assertEqual(out["content"], "ok")
        self.assertTrue(out["orchestration"]["optimised"])
        self.assertEqual(out["orchestration"]["tokens_saved"], 12)
        self.assertEqual(out["orchestration"]["suggested_effort"], "high")

        # le HeliosCall envoyé : message nettoyé, effort/palier complétés
        call = fake_call_helios.captured
        self.assertEqual(call.messages[-1].content, "prompt nettoyé")
        self.assertEqual(call.effort, "high")   # complété depuis le routing (effort initial None)
        self.assertEqual(call.palier, "2")      # complété depuis optimise (palier initial None)

    def test_effort_explicite_non_ecrase_par_routing(self):
        fake_opt = {"optimised": "x", "tokens_saved": 0, "palier": "3"}
        fake_routing = {"effort": "high", "model_tier": "medium", "task": None, "confidence": 1}

        async def fake_call_helios(call, api_key):
            fake_call_helios.captured = call
            return {"content": "ok", "input_tokens": 1, "output_tokens": 1}

        with mock.patch.object(orch, "optimise", return_value=fake_opt), \
             mock.patch.object(orch, "suggest_routing", return_value=fake_routing), \
             mock.patch.object(orch.chat_service, "call_helios", new=fake_call_helios):
            _run(orch.orchestrate("Anthropic", "claude-haiku-4-5", "k",
                                  [{"role": "user", "content": "y"}], effort="low", palier="1"))

        call = fake_call_helios.captured
        self.assertEqual(call.effort, "low")    # l'effort fourni prime sur le routing
        self.assertEqual(call.palier, "1")      # le palier fourni prime sur optimise


class TestApplyMemory(unittest.TestCase):
    """Jalon 3 — apply_memory : compaction si seuil franchi, gates, rollback."""

    def _big(self):
        return [{"role": "user" if i % 2 == 0 else "assistant", "content": "mot " * 3000}
                for i in range(8)]

    def test_compacte_et_injecte_le_resume(self):
        async def fake_summarize(fold_render):
            return "RÉSUMÉ structuré fidèle."

        async def run():
            return await orch.apply_memory(self._big(), "k", summarize=fake_summarize,
                                           state_judge=lambda s, u: {"contradiction": False})
        out = _run(run())
        self.assertTrue(out["compacted"])
        self.assertEqual(out["context"], "RÉSUMÉ structuré fidèle.")
        self.assertEqual(len(out["messages"]), 4)   # KEEP derniers tours verbatim

    def test_rollback_sur_contradiction_etat(self):
        async def fake_summarize(fold_render):
            return "résumé qui fige un état périmé"

        async def run():
            return await orch.apply_memory(self._big(), "k", summarize=fake_summarize,
                                           state_judge=lambda s, u: {"contradiction": True, "detail": "figé"})
        out = _run(run())
        self.assertFalse(out["compacted"])
        self.assertIsNone(out["context"])
        self.assertEqual(len(out["messages"]), 8)    # historique inchangé (aucune perte)
        self.assertIn("rollback", out["reason"])

    def test_seuil_non_atteint_aucune_compaction(self):
        small = [{"role": "user", "content": "court"} for _ in range(3)]

        async def run():
            return await orch.apply_memory(small, "k", summarize=None)
        out = _run(run())
        self.assertFalse(out["compacted"])
        self.assertEqual(len(out["messages"]), 3)


if __name__ == "__main__":
    unittest.main()
