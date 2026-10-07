"""Tests unitaires pour les helpers de calibration palier dans chat_service.py"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import unittest
from unittest import mock
from fastapi import HTTPException
import services.chat_service as cs
from services.chat_service import (
    _system_from_palier, _max_tokens_from_palier, _temperature_from_palier
)


def _run(coro):
    return asyncio.run(coro)


class _FakeResp:
    """Réponse httpx factice."""
    def __init__(self, status_code=200, payload=None, text="ok"):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self.content = b"{}"

    def json(self):
        return self._payload


class _FakeClient:
    """AsyncClient factice : capture le body envoyé, renvoie une réponse fixée."""
    captured = {}
    _resp = None

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, **kwargs):
        _FakeClient.captured = {"url": url, **kwargs}
        return _FakeClient._resp


def _patch_client(resp):
    _FakeClient._resp = resp
    _FakeClient.captured = {}
    return mock.patch.object(cs.httpx, "AsyncClient", _FakeClient)


class TestPalierHelpers(unittest.TestCase):

    def test_system_contrainte_texte(self):
        self.assertEqual(_system_from_palier('2'), 'Réponds en 115 mots maximum.')
        self.assertEqual(_system_from_palier('C'), 'Code uniquement. Commentaires minimalistes.')
        self.assertEqual(_system_from_palier('★'), 'Réponds en 50 mots maximum.')

    def test_system_none_paliers_libres(self):
        self.assertIsNone(_system_from_palier('5'))
        self.assertIsNone(_system_from_palier('6'))
        self.assertIsNone(_system_from_palier(None))

    def test_max_tokens_sans_thinking(self):
        self.assertEqual(_max_tokens_from_palier('2', 0), 200)
        self.assertEqual(_max_tokens_from_palier('C', 0), 4096)
        self.assertEqual(_max_tokens_from_palier('5', 0), 8192)
        self.assertEqual(_max_tokens_from_palier(None, 0), 8192)
        self.assertEqual(_max_tokens_from_palier('★', 0), 90)

    def test_max_tokens_avec_thinking(self):
        self.assertEqual(_max_tokens_from_palier('2', 8192), 8392)
        self.assertEqual(_max_tokens_from_palier('5', 4096), 12288)

    def test_temperature_par_palier(self):
        self.assertEqual(_temperature_from_palier('C'), 0.1)
        self.assertEqual(_temperature_from_palier('★'), 0.2)
        self.assertEqual(_temperature_from_palier('2'), 0.5)
        self.assertEqual(_temperature_from_palier('4'), 0.7)
        self.assertEqual(_temperature_from_palier('6'), 0.65)
        self.assertEqual(_temperature_from_palier(None), 0.7)

    def test_temperature_thinking_force_1(self):
        self.assertEqual(_temperature_from_palier('C', 8192), 1.0)
        self.assertEqual(_temperature_from_palier('2', 4096), 1.0)


class TestGoogleThinkingBudget(unittest.TestCase):
    """#1 (critique) : maxOutputTokens doit couvrir thinkingBudget, sinon réponse vide → 502."""

    def test_maxout_couvre_le_thinking_budget_palier_bas(self):
        resp = _FakeResp(payload={
            "candidates": [{"content": {"parts": [{"text": "hi"}]}}],
            "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2},
        })
        with _patch_client(resp):
            _run(cs._google("gemini-2-5-flash", "k",
                            [{"role": "user", "content": "x"}], {"google": 16000}, "★"))
        gc = _FakeClient.captured["json"]["generationConfig"]
        self.assertIn("thinkingConfig", gc)
        self.assertGreaterEqual(gc["maxOutputTokens"], gc["thinkingConfig"]["thinkingBudget"])

    def test_sans_thinking_pas_de_thinkingconfig(self):
        resp = _FakeResp(payload={
            "candidates": [{"content": {"parts": [{"text": "hi"}]}}],
            "usageMetadata": {},
        })
        with _patch_client(resp):
            _run(cs._google("gemini-2-5-flash", "k",
                            [{"role": "user", "content": "x"}], {"google": 0}, "★"))
        gc = _FakeClient.captured["json"]["generationConfig"]
        self.assertNotIn("thinkingConfig", gc)


class TestOpenAIReasoningParams(unittest.TestCase):
    """#2 (majeur) : o-series exige max_completion_tokens et refuse temperature≠1."""

    def test_oseries_max_completion_sans_temperature(self):
        resp = _FakeResp(payload={"choices": [{"message": {"content": "ok"}}],
                                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
        with _patch_client(resp):
            _run(cs._openai("o3", "k", [{"role": "user", "content": "x"}], {"openai": "high"}, "2"))
        body = _FakeClient.captured["json"]
        self.assertNotIn("max_tokens", body)
        self.assertIn("max_completion_tokens", body)
        self.assertTrue("temperature" not in body or body["temperature"] == 1)
        self.assertEqual(body.get("reasoning_effort"), "high")

    def test_modele_standard_garde_max_tokens_et_temperature(self):
        resp = _FakeResp(payload={"choices": [{"message": {"content": "ok"}}],
                                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
        with _patch_client(resp):
            _run(cs._openai("gpt-4o", "k", [{"role": "user", "content": "x"}], {}, "2"))
        body = _FakeClient.captured["json"]
        self.assertIn("max_tokens", body)
        self.assertIn("temperature", body)
        self.assertNotIn("max_completion_tokens", body)


class TestEmptyResponsesGuarded(unittest.TestCase):
    """#3 (majeur) : réponse 200-mais-vide ne doit pas crasher en IndexError/502 opaque."""

    def test_openai_choices_vide_erreur_explicite(self):
        resp = _FakeResp(payload={"choices": [], "usage": {}})
        with _patch_client(resp):
            with self.assertRaises(HTTPException) as ctx:
                _run(cs._openai("gpt-4o", "k", [{"role": "user", "content": "x"}], {}, "2"))
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("vide", str(ctx.exception.detail).lower())

    def test_google_prompt_bloque_erreur_avec_raison(self):
        resp = _FakeResp(payload={"candidates": [], "promptFeedback": {"blockReason": "SAFETY"}})
        with _patch_client(resp):
            with self.assertRaises(HTTPException) as ctx:
                _run(cs._google("gemini-2-5-flash", "k", [{"role": "user", "content": "x"}], {}, "2"))
        self.assertIn("SAFETY", str(ctx.exception.detail))

    def test_google_candidat_sans_parts_pas_de_crash(self):
        resp = _FakeResp(payload={"candidates": [{"finishReason": "MAX_TOKENS"}], "usageMetadata": {}})
        with _patch_client(resp):
            out = _run(cs._google("gemini-2-5-flash", "k", [{"role": "user", "content": "x"}], {}, "2"))
        self.assertEqual(out["content"], "")


class TestAnthropicThinkingTokens(unittest.TestCase):
    """#6 (mineur) : thinking_tokens ne doit pas refléter cache_creation_input_tokens."""

    def test_thinking_tokens_zero_pas_cache(self):
        resp = _FakeResp(payload={
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 5, "output_tokens": 3, "cache_creation_input_tokens": 99},
        })
        with _patch_client(resp):
            out = _run(cs._anthropic("claude-haiku-4-5", "k",
                                     [{"role": "user", "content": "x"}], {"anthropic": 0}, "2"))
        self.assertEqual(out["thinking_tokens"], 0)
        self.assertEqual(out["input_tokens"], 5)
        self.assertEqual(out["output_tokens"], 3)


class TestEffortVocab(unittest.TestCase):
    """#8 : 'on' doit être un effort valide ; un effort inconnu doit logger un warning."""

    def test_on_est_un_effort_valide(self):
        self.assertIn("on", cs._EFFORT_MAP)
        self.assertGreater(cs._EFFORT_MAP["on"]["anthropic"], 0)

    def test_effort_inconnu_loggue_warning(self):
        resp = _FakeResp(payload={"content": [{"type": "text", "text": "ok"}],
                                  "usage": {"input_tokens": 1, "output_tokens": 1}})
        with _patch_client(resp), \
             self.assertLogs("services.chat_service", level="WARNING") as cm:
            _run(cs.call_llm("Anthropic", "claude-haiku-4-5", "k",
                             [{"role": "user", "content": "x"}], effort="bogus"))
        self.assertTrue(any("inconnu" in x.lower() for x in cm.output))


class TestAssembleSystem(unittest.TestCase):
    """#2.2 : assemblage du system prompt depuis role/context/palier (objet Helios)."""

    def test_role_context_palier_dans_l_ordre(self):
        s = cs._assemble_system("Tu es expert.", "Projet X.", "2")
        self.assertEqual(s, "Tu es expert.\n\nProjet X.\n\nRéponds en 115 mots maximum.")

    def test_aucun_renvoie_none(self):
        self.assertIsNone(cs._assemble_system(None, None, None))
        self.assertIsNone(cs._assemble_system(None, None, "5"))  # palier libre → pas de system

    def test_palier_seul_identique_au_comportement_anterieur(self):
        self.assertEqual(cs._assemble_system(None, None, "2"), cs._system_from_palier("2"))


class TestRoleContextDansBody(unittest.TestCase):
    """role/context first-class doivent atterrir dans le system prompt du provider."""

    def test_anthropic_system_contient_role_context_et_palier(self):
        resp = _FakeResp(payload={"content": [{"type": "text", "text": "ok"}],
                                  "usage": {"input_tokens": 1, "output_tokens": 1}})
        with _patch_client(resp):
            _run(cs._anthropic("claude-haiku-4-5", "k", [{"role": "user", "content": "x"}],
                               {"anthropic": 0}, "2", role="Tu es expert.", context="Contexte Y."))
        sys_text = _FakeClient.captured["json"]["system"][0]["text"]
        self.assertIn("Tu es expert.", sys_text)
        self.assertIn("Contexte Y.", sys_text)
        self.assertIn("115 mots", sys_text)

    def test_openai_sans_role_context_inchange(self):
        resp = _FakeResp(payload={"choices": [{"message": {"content": "ok"}}],
                                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}})
        with _patch_client(resp):
            _run(cs._openai("gpt-4o", "k", [{"role": "user", "content": "x"}], {}, "2"))
        sys_msgs = [m for m in _FakeClient.captured["json"]["messages"] if m["role"] == "system"]
        self.assertEqual(sys_msgs[0]["content"], "Réponds en 115 mots maximum.")


class TestCallHelios(unittest.TestCase):
    """#2.1/2.2 : call_helios mappe un HeliosCall vers le provider."""

    def test_mappe_vers_provider(self):
        from schemas.helios import HeliosCall, HeliosMessage
        resp = _FakeResp(payload={"content": [{"type": "text", "text": "ok"}],
                                  "usage": {"input_tokens": 2, "output_tokens": 3}})
        call = HeliosCall(provider="Anthropic", model="claude-haiku-4-5",
                          messages=[HeliosMessage(role="user", content="x")],
                          palier="2", role="Tu es expert.")
        with _patch_client(resp):
            out = _run(cs.call_helios(call, "k"))
        self.assertEqual(out["content"], "ok")
        self.assertEqual(out["input_tokens"], 2)
        self.assertIn("Tu es expert.", _FakeClient.captured["json"]["system"][0]["text"])


if __name__ == '__main__':
    unittest.main()
