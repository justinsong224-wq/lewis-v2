"""工具审计和固定验收的离线回归；不请求模型。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

os.environ["LLM_API_KEY"] = "offline-test"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import acceptance
from graph import company_graph as workflow
from lewis_mcp.audit import event_sink, subtask_id
from lewis_mcp.client.client import call_tool


class AuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_redacts_body_and_preserves_subtask(self):
        sink = AsyncMock()
        token, sid = event_sink.set(sink), subtask_id.set("dev-1")
        try:
            with patch("lewis_mcp.client.client._call_tool", AsyncMock(return_value="private body")):
                self.assertEqual(await call_tool("filesystem", "write_file", "dev", content="private body", token="credential"), "private body")
            payload = sink.await_args.args[1]
            self.assertEqual(payload["subtask_id"], "dev-1")
            self.assertEqual(payload["outcome"], "succeeded")
            self.assertNotIn("private body", str(payload))
            self.assertNotIn("credential", str(payload))
        finally:
            event_sink.reset(token)
            subtask_id.reset(sid)

    async def test_audit_failure_does_not_mask_permission_error(self):
        token = event_sink.set(AsyncMock(side_effect=RuntimeError("audit unavailable")))
        try:
            with self.assertLogs("lewis_mcp.client.client", level="ERROR"):
                with self.assertRaises(PermissionError):
                    await call_tool("git", "git_status", "search")
        finally:
            event_sink.reset(token)

    async def test_cancelled_call_is_recorded(self):
        import asyncio
        sink = AsyncMock()
        token = event_sink.set(sink)
        try:
            with patch("lewis_mcp.client.client._call_tool", AsyncMock(side_effect=asyncio.CancelledError)):
                with self.assertRaises(asyncio.CancelledError):
                    await call_tool("filesystem", "read_file", "dev", path="app.py")
            self.assertEqual(sink.await_args.args[1]["outcome"], "cancelled")
        finally:
            event_sink.reset(token)


class AcceptanceTests(unittest.TestCase):
    def test_subprocess_report_and_stale_report_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / ".lewis" / "acceptance.xml"
            report.parent.mkdir()
            report.write_text('<testsuites><testsuite tests="5"/></testsuites>')

            def execute(command, **kwargs):
                self.assertFalse(report.exists())
                self.assertEqual(kwargs["env"]["LEWIS_DEMO_APP_DIR"], temp)
                report.write_text('<testsuites><testsuite tests="5" failures="0" errors="0" skipped="0"/></testsuites>')
                return subprocess.CompletedProcess(command, 0, "5 passed", "")

            with patch.object(acceptance, "workspace_path", return_value=root), patch.object(acceptance.subprocess, "run", execute):
                result = acceptance.run_acceptance("unused")
            self.assertEqual(result["verification"], "passed")
            with patch.object(acceptance, "workspace_path", return_value=root), patch.object(acceptance.subprocess, "run", side_effect=subprocess.TimeoutExpired("pytest", 60)):
                result = acceptance.run_acceptance("unused")
            self.assertEqual(result["verification"], "failed")
            self.assertEqual(result["passed"], 0)
        with self.assertRaises(ValueError):
            acceptance.run_acceptance("unused", "arbitrary-command")


class AcceptanceWorkflowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch.object(workflow, 'verification_manifest', return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_acceptance_failure_downgrades_delivery(self):
        state = {"task_id": "offline", "user_input": "需求", "ceo_result": {}, "subtask_results": {},
                 "acceptance_profile": "sms-classifier", "agent_results": {
                     "dev": {"files": [{"path": "app.py"}]},
                     "test": {"verification": "passed", "execution": {"exit_code": 0, "passed": 2}}}}
        with patch.object(workflow, "run_acceptance", return_value={"verification": "failed"}) as check, patch.object(workflow, "_emit", AsyncMock()), patch.object(workflow, "customer_agent_run", AsyncMock(return_value={"closing": "完成"})), patch.object(workflow, "update_task", AsyncMock()) as update, patch.object(workflow, "set_task_state", AsyncMock()):
            state = await workflow.acceptance_node(state)
            await workflow.customer_node(state)
        check.assert_called_once_with("offline", "sms-classifier")
        self.assertEqual(update.await_args.args[1], "partial")
        self.assertEqual(update.await_args.kwargs["snapshot"]["acceptance"]["verification"], "failed")

    async def test_default_task_does_not_run_fixed_acceptance(self):
        with patch.object(workflow, "run_acceptance") as check:
            self.assertEqual(await workflow.acceptance_node({"task_id": "offline"}), {"task_id": "offline"})
        check.assert_not_called()
