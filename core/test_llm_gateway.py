import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from core.services.llm_gateway import LLMGatewayError, generate_grounded_answer, provider_catalog, resolve_llm_config, test_llm_connection
from core.agent_api import _safe_llm_config
from core.services.agent_chat import chat


class _StreamResponse:
    headers = {"content-type": "text/event-stream"}

    def __init__(self, chunks):
        self._lines = [f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n".encode() for chunk in chunks]
        self._lines.append(b"data: [DONE]\n")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __iter__(self):
        return iter(self._lines)


class _JsonResponse:
    headers = {"content-type": "application/json"}

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class LLMGatewayTests(SimpleTestCase):
    @override_settings(DEEPSEEK_API_KEY="server-secret", DEEPSEEK_MODEL="deepseek-flash")
    def test_deepseek_stream_is_grounded_and_never_returns_key(self):
        deltas = []
        with patch("core.services.llm_gateway.urlopen", return_value=_StreamResponse(["**结论**：", "`数据可用`。"] )) as mocked:
            result = generate_grounded_answer(
                message="分析数据", snapshot={"run_id": "run_1", "results": {}},
                response={"answer": "证据回答", "skill_executions": []},
                config={"provider": "deepseek"}, on_delta=deltas.append,
            )
        self.assertEqual(result["answer"], "结论：数据可用。")
        self.assertEqual(deltas, ["**结论**：", "`数据可用`。"])
        self.assertNotIn("server-secret", json.dumps(result))
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(json.loads(request.data)["stream"], True)

    def test_local_provider_only_accepts_loopback(self):
        with self.assertRaisesMessage(LLMGatewayError, "仅允许 localhost"):
            resolve_llm_config({"provider": "local", "base_url": "http://10.0.0.8:11434/v1", "model": "local-model"})
        resolved = resolve_llm_config({"provider": "local", "base_url": "http://127.0.0.1:1234/v1", "model": "local-model"})
        self.assertEqual(resolved.provider, "local")

    @override_settings(DEEPSEEK_API_KEY="")
    def test_catalog_marks_missing_deepseek_key_without_exposing_secrets(self):
        catalog = provider_catalog()
        deepseek = next(item for item in catalog["providers"] if item["id"] == "deepseek")
        self.assertFalse(deepseek["configured"])
        self.assertNotIn("api_key", json.dumps(catalog))

    def test_browser_payload_can_never_persist_an_api_key(self):
        safe = _safe_llm_config({"provider": "local", "model": "model", "base_url": "http://localhost:1234/v1", "api_key": "browser-secret"})
        self.assertNotIn("api_key", safe)

    @override_settings(DEEPSEEK_API_KEY="")
    def test_user_key_is_tested_then_only_an_encrypted_credential_is_queued(self):
        with patch("core.services.llm_gateway.urlopen", return_value=_JsonResponse({"choices": [{"message": {"content": "OK"}}]})):
            result = test_llm_connection({
                "provider": "deepseek", "model": "deepseek-flash",
                "base_url": "https://api.deepseek.com", "api_key": "browser-secret",
            })
        self.assertTrue(result["connected"])
        self.assertNotIn("browser-secret", json.dumps(result))
        safe = _safe_llm_config({
            "provider": "deepseek", "model": "deepseek-flash",
            "base_url": "https://api.deepseek.com", "credential": result["credential"],
        })
        self.assertNotIn("browser-secret", json.dumps(safe))
        self.assertEqual(resolve_llm_config(safe).api_key, "browser-secret")

    @override_settings(DEEPSEEK_API_KEY="")
    def test_llm_test_api_never_echoes_plaintext_key(self):
        with patch("core.services.llm_gateway.urlopen", return_value=_JsonResponse({"choices": [{"message": {"content": "OK"}}]})):
            response = self.client.post('/api/agent/llm/test/', data=json.dumps({
                "provider": "deepseek", "model": "deepseek-flash",
                "base_url": "https://api.deepseek.com", "api_key": "api-test-secret",
            }), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("api-test-secret", response.content.decode("utf-8"))

    def test_agent_keeps_evidence_answer_as_fallback_when_llm_is_used(self):
        snapshot = {
            "run_id": "run_llm", "status": "completed", "artifacts": {}, "stages": [],
            "results": {
                "standardization": {"scenario": {"scenario_name": "工业干燥器", "scenario_id": "industrial_dryer"}, "mapping": {"mappings": [], "required_coverage": 1, "missing_required": []}, "data_decision": {"status": "ready"}},
                "cleaning": {"overall_score": 88, "cleaned_row_count": 100, "modeling_row_count": 80, "selected_segment_count": 2},
                "modeling": {"metrics": {"test": {"r2": .72, "rmse": 1.1, "mae": .8}}, "selected_inputs": []},
                "optimization": {"iterations": [], "best_parameters": {}},
                "review": {"passed": False, "blockers": [], "warnings": [], "conclusion": "待复核"},
            },
        }
        generated = {"answer": "这是大模型基于证据生成的回答。", "provider": "deepseek", "label": "DeepSeek API", "model": "deepseek-flash", "usage": None}
        # This test isolates answer fallback; TaskSpec proposal has its own tests.
        from core.skills.task_understanding import understand_task
        proposal = (understand_task("总结当前任务"), {"fallback": True, "fallback_reason": "unit_test_fixture"})
        with patch("core.services.llm_gateway.propose_task_spec", return_value=proposal), TemporaryDirectory() as directory, patch("core.services.agent_chat.get_run", return_value=snapshot), patch("core.skills.runtime.RUNS_DIR", Path(directory)), patch("core.services.agent_chat.generate_grounded_answer", return_value=generated):
            result = chat("总结当前任务", run_id="run_llm", llm_config={"provider": "deepseek"})
        self.assertEqual(result["answer"], generated["answer"])
        self.assertTrue(result["deterministic_answer"])
        self.assertTrue(result["llm"]["used"])
        self.assertNotIn("answer", result["llm"])
