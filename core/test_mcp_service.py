import asyncio
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

from core.mcp.service import MCPServiceError, cancel_job, enqueue_modeling_tool, get_job, job_result, list_registered_runs
from core.models import RuntimeJob
from core.services.jobs import execute


class MCPModelingServiceTests(TestCase):
    def _queue(self, tool="run_dynamic_selection", key="request-1"):
        source = {"run_id": "source_1", "artifacts": {"source_csv": "01_input/source.csv"}}
        with (
            patch("core.mcp.service.get_run", side_effect=lambda run_id: source if run_id == "source_1" else None),
            patch("core.mcp.service.resolve_artifact", return_value=(Path("/tmp/source.csv"), "source.csv")),
            patch("core.mcp.service.start_local_worker"),
        ):
            return enqueue_modeling_tool(tool, "source_1", idempotency_key=key)

    def test_three_public_tools_map_to_bounded_pipeline_stages(self):
        expected = {
            "run_dynamic_selection": "selection",
            "run_decoupling_identification": "modeling",
            "run_closed_loop_optimization": "optimization",
        }
        for index, (tool, stage) in enumerate(expected.items()):
            result = self._queue(tool, f"key-{index}")
            job = RuntimeJob.objects.get(job_id=result["job_id"])
            self.assertEqual(job.job_type, "mcp_pipeline")
            self.assertEqual(job.payload["stop_after"], stage)
            self.assertFalse(result["actuation_allowed"])
            self.assertEqual(result["control_mode"], "advisory_only")
            self.assertEqual(result["observability_schema_version"], "processpilot-mcp-observability-v1")
            self.assertEqual(result["execution_timeline"][-1]["stage"], stage)
            self.assertTrue(result["current_stage"]["label"])

    def test_idempotency_returns_same_job(self):
        first = self._queue(key="same-key")
        second = self._queue(key="same-key")
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertTrue(second["reused_idempotent_request"])
        self.assertEqual(RuntimeJob.objects.count(), 1)

    def test_invalid_lag_is_rejected_before_queueing(self):
        with (
            patch("core.mcp.service.get_run", return_value={"run_id": "source_1"}),
            patch("core.mcp.service.resolve_artifact", return_value=(Path("/tmp/source.csv"), "source.csv")),
        ):
            with self.assertRaises(MCPServiceError) as invalid:
                enqueue_modeling_tool("run_dynamic_selection", "source_1", max_lag=601)
        self.assertEqual(invalid.exception.code, "INVALID_ARGUMENT")
        self.assertEqual(RuntimeJob.objects.count(), 0)

    def test_caller_isolation_and_queued_cancellation(self):
        result = self._queue()
        with self.assertRaises(MCPServiceError) as denied:
            get_job(result["job_id"], caller_id="another-agent")
        self.assertEqual(denied.exception.code, "ACCESS_DENIED")
        cancelled = cancel_job(result["job_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["error"]["code"], "CANCELLED")

    def test_worker_persists_new_run_reference(self):
        result = self._queue("run_closed_loop_optimization", "worker-key")
        job = RuntimeJob.objects.get(job_id=result["job_id"])
        job.status = "running"
        job.attempts = 1
        job.save(update_fields=("status", "attempts", "updated_at"))
        snapshot = {
            "run_id": "new_run_1",
            "status": "completed",
            "current_stage": "completed",
            "stages": [{"key": "optimization", "status": "completed"}],
            "artifacts": {},
            "results": {
                "optimization": {
                    "synthetic_fallback": False,
                    "validation_target_hash": "hash",
                    "test_used_for_search": False,
                    "test_evaluation_count": 1,
                    "stopping": {"max_rounds": 16, "stop_reason": "完成"},
                }
            },
        }
        with (
            patch("core.services.pipeline.rerun_pipeline", return_value=snapshot) as rerun,
            patch("core.mcp.service.get_run", return_value=snapshot),
        ):
            execute(job)
        rerun.assert_called_once()
        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.result_ref, "new_run_1")
        self.assertEqual(job.progress["percent"], 100)

    def test_status_contract_exposes_ui_ready_timeline_and_stage_evidence(self):
        queued = self._queue("run_decoupling_identification", "observable-job")
        job = RuntimeJob.objects.get(job_id=queued["job_id"])
        job.status = "running"
        job.save(update_fields=("status", "updated_at"))
        snapshot = {
            "run_id": job.result_ref,
            "status": "running",
            "current_stage": "modeling",
            "stages": [
                {"key": "standardization", "status": "completed", "message": "字段标准化完成", "elapsed_ms": 12},
                {"key": "cleaning", "status": "completed", "message": "质量评分 90.1", "elapsed_ms": 34},
                {"key": "selection", "status": "completed", "message": "建模数据 240 行", "elapsed_ms": 56},
                {"key": "modeling", "status": "running", "message": "正在执行时滞、共线性和ARX辨识", "started_at": "2026-09-16T00:00:00+08:00"},
            ],
            "artifacts": {},
            "results": {},
        }
        with patch("core.mcp.service.get_run", return_value=snapshot):
            result = job_result(job)
        self.assertEqual(result["current_stage"]["key"], "modeling")
        self.assertEqual(result["current_stage"]["status"], "running")
        self.assertEqual(result["progress"], {"completed": 3, "total": 4, "percent": 75.0})
        self.assertEqual([row["stage"] for row in result["execution_timeline"]], ["standardization", "cleaning", "selection", "modeling"])
        self.assertEqual(result["execution_timeline"][1]["elapsed_ms"], 34)

    def test_client_publishes_only_changed_mcp_progress_states(self):
        from core.mcp.client import _invoke_and_wait

        def response(payload):
            return {"structuredContent": payload}

        queued = {"job_id": "job_progress", "status": "queued", "current_stage": {"key": "standardization", "status": "queued"}, "progress": {"percent": 0}}
        running = {"job_id": "job_progress", "status": "running", "current_stage": {"key": "cleaning", "status": "running"}, "progress": {"percent": 25}}
        completed = {"job_id": "job_progress", "status": "completed", "current_stage": {"key": "selection", "status": "completed"}, "progress": {"percent": 100}}
        published = []
        with patch("core.mcp.client._rpc", side_effect=[response(queued), response(queued), response(running), response(running), response(completed)]):
            result = _invoke_and_wait("http://mcp.test", "run_dynamic_selection", {"caller_id": "test"}, timeout_seconds=2, on_progress=published.append)
        self.assertEqual(result["status"], "completed")
        self.assertEqual([item["status"] for item in published], ["queued", "running", "completed"])

    def test_official_mcp_client_discovers_public_contract(self):
        from mcp import Client
        from core.mcp.server import mcp

        async def inspect_server():
            async with Client(mcp) as client:
                tools = await client.list_tools()
                resources = await client.list_resources()
                templates = await client.list_resource_templates()
                return (
                    {tool.name for tool in tools.tools},
                    {str(resource.uri) for resource in resources.resources},
                    {str(resource.uri_template) for resource in templates.resource_templates},
                )

        tools, resources, templates = asyncio.run(inspect_server())
        self.assertTrue({
            "run_dynamic_selection",
            "run_decoupling_identification",
            "run_closed_loop_optimization",
            "get_job_status",
            "cancel_job",
            "list_run_artifacts",
            "get_artifact_summary",
        }.issubset(tools))
        self.assertIn("processpilot://server/capabilities", resources)
        self.assertIn("processpilot://runs/{run_id}/evidence", templates)

    def test_zero_strict_segments_is_reported_as_partial(self):
        queued = self._queue(key="partial-selection")
        job = RuntimeJob.objects.get(job_id=queued["job_id"])
        job.status = "completed"
        snapshot = {
            "run_id": job.result_ref,
            "status": "completed",
            "current_stage": "completed",
            "stages": [{"key": "selection", "status": "completed"}],
            "artifacts": {},
            "results": {
                "cleaning": {"split": {"protocol": "chronological"}, "segments_preview": [{}]},
                "selection": {"selected_segment_count": 0, "modeling_row_count": 60},
            },
        }
        with patch("core.mcp.service.get_run", return_value=snapshot):
            result = job_result(job)
        self.assertEqual(result["status"], "partial")
        self.assertIn("严格优质动态段为 0", result["warnings"][0])
        gates = {row["gate"]: row["status"] for row in result["quality_gates"]}
        self.assertEqual(gates["minimum_valid_samples"], "failed")

    @patch("core.mcp.service.list_runs", return_value=[])
    def test_registered_runs_passes_scenario_filter_to_pipeline(self, list_runs_mock):
        result = list_registered_runs(5, "industrial_dryer")
        self.assertEqual(result["count"], 0)
        list_runs_mock.assert_called_once_with(5, scenario_id="industrial_dryer")

    @patch("core.mcp_api.check_server", return_value={"configured": True, "online": True, "tool_count": 9, "missing_tools": []})
    def test_mcp_center_exposes_visible_tools_and_safety_boundary(self, _health):
        response = self.client.get("/api/mcp/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["server"]["online"])
        self.assertEqual(len(payload["tools"]), 9)
        self.assertFalse(payload["server"]["actuation_allowed"])
        self.assertEqual(
            [tool["name"] for tool in payload["tools"][:3]],
            ["run_dynamic_selection", "run_decoupling_identification", "run_closed_loop_optimization"],
        )
