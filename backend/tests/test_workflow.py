"""离线验证协作契约、真实工具和异常收尾，不调用模型或搜索服务。"""
import asyncio
from contextlib import ExitStack
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

os.environ["LLM_API_KEY"] = "offline-test"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph import company_graph as workflow
from graph.contracts import ordered_subtasks, delivery_status
from memory import sqlite_history as history
from lewis_mcp.workspace import task_workspace
from lewis_mcp.client.client import call_tool
from agents import test_agent


def plan():
    return {"subtasks": [
        {"id": "test", "agent": "test", "task": "测试", "depends_on": ["dev"]},
        {"id": "dev", "agent": "dev", "task": "开发"},
        {"id": "review", "agent": "review", "task": "审查", "depends_on": ["dev"]},
    ], "execution_order": ["dev", "test", "review"]}


def state():
    return {"task_id": "offline", "user_input": "开发工单查询接口", "ceo_result": plan(),
            "agent_results": {}, "subtask_results": {}, "current_agent": "pm", "final_output": ""}


class ContractTests(unittest.TestCase):
    def test_order_and_invalid_dependencies(self):
        self.assertEqual([t["id"] for t in ordered_subtasks(plan())], ["dev", "test", "review"])
        bad = plan()
        bad["execution_order"] = ["test", "dev", "review"]
        with self.assertRaises(ValueError):
            ordered_subtasks(bad)
        bad["execution_order"] = ["dev", "dev", "review"]
        with self.assertRaises(ValueError):
            ordered_subtasks(bad)

    def test_completion_requires_execution_evidence(self):
        results = {"dev": {"files": [{"path": "app.py"}]}, "test": {"verification": "passed"}}
        self.assertEqual(delivery_status(results), "partial")
        results["test"]["execution"] = {"exit_code": 0, "passed": 2}
        self.assertEqual(delivery_status(results), "completed")
        results["review"] = {"issues": [{"severity": "high"}]}
        self.assertEqual(delivery_status(results), "partial")


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 节点单元测试隔离持久化和文件扫描；真实 SQLite/MCP 由下方集成测试覆盖。
        for name, replacement in [('update_task', AsyncMock()), ('get_task', AsyncMock(return_value=None)),
                                  ('verification_manifest', lambda task_id: {})]:
            patcher = patch.object(workflow, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_research_timeout_is_recorded_and_plan_can_continue(self):
        async def stalled(*args, **kwargs):
            await asyncio.sleep(1)
        with patch.object(workflow.settings, "agent_timeout_seconds", 0.01), patch.object(workflow, "search_agent_run", stalled), patch.object(workflow, "_emit", AsyncMock()):
            result = await workflow.search_node(state())
        self.assertIn("TimeoutError", result["agent_results"]["search"]["error"])
        self.assertEqual(result["current_agent"], "ceo")

    async def test_startup_recovers_only_unfinished_tasks(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(history, "DB_PATH", str(Path(temp) / "recovery.db")):
                await history.init_db()
                await history.create_task("unfinished", "开发需求")
                await history.create_task("finished", "已完成需求")
                await history.update_task("finished", "completed", "原结果")
                self.assertEqual(await history.recover_interrupted_tasks(), 1)
                self.assertEqual((await history.get_task("unfinished"))["status"], "failed")
                self.assertEqual((await history.get_task("finished"))["result"], "原结果")
                self.assertTrue((await history.get_task_logs("unfinished"))[0]["terminal"])
                self.assertEqual(await history.recover_interrupted_tasks(), 0)

    async def test_dispatch_passes_paths_and_honors_order(self):
        seen = []

        async def dev(task, context):
            seen.append("dev")
            return {"files": [{"path": "app.py", "content": "actual"}]}

        async def test(task, context):
            seen.append("test")
            self.assertEqual(context["files"], ["app.py"])
            return {"verification": "failed", "error": "assertion failed"}

        async def review(task, context):
            seen.append("review")
            self.assertEqual(context["test"]["verification"], "failed")
            return {}

        with patch.dict(workflow.AGENT_RUNNERS, {"dev": dev, "test": test, "review": review}), patch.object(workflow, "_emit", AsyncMock()):
            result = await workflow.dispatch_node(state())
        self.assertEqual(seen, ["dev", "test", "review"])
        self.assertEqual(len(result["subtask_results"]), 3)

    async def test_dev_failure_skips_dependents(self):
        test = AsyncMock()
        with patch.dict(workflow.AGENT_RUNNERS, {"dev": AsyncMock(side_effect=RuntimeError("write failed")), "test": test}), patch.object(workflow, "_emit", AsyncMock()):
            result = await workflow.dispatch_node(state())
        test.assert_not_awaited()
        self.assertEqual(result["agent_results"]["review"]["status"], "skipped")
        self.assertEqual(delivery_status(result["agent_results"]), "failed")

    async def test_full_graph_and_customer_cannot_hide_test_failure(self):
        calls = []

        async def pm(*args, **kwargs):
            calls.append("pm")
            return {"prd": {"acceptance_criteria": ["正确分页"]}}

        async def search(*args, **kwargs):
            calls.append("search")
            return {"sources": ["https://fastapi.tiangolo.com/"]}

        async def ceo(*args, **kwargs):
            calls.append("ceo")
            self.assertIn("search", kwargs["context"])
            return plan()

        with ExitStack() as stack:
            stack.enter_context(patch.object(workflow, "pm_agent_run", pm))
            stack.enter_context(patch.object(workflow, "search_agent_run", search))
            stack.enter_context(patch.object(workflow, "ceo_agent_run", ceo))
            stack.enter_context(patch.dict(workflow.AGENT_RUNNERS, {
                "dev": AsyncMock(return_value={"files": [{"path": "app.py"}]}),
                "test": AsyncMock(return_value={"error": "test failed", "verification": "failed"}),
                "review": AsyncMock(return_value={})}))
            stack.enter_context(patch.object(workflow, "customer_agent_run", AsyncMock(return_value={"closing": "汇总成功"})))
            stack.enter_context(patch.object(workflow, "_emit", AsyncMock()))
            update = stack.enter_context(patch.object(workflow, "update_task", AsyncMock()))
            stack.enter_context(patch.object(workflow, "set_task_state", AsyncMock()))
            result = await workflow.company_graph.ainvoke(state())
        self.assertEqual(calls, ["pm", "search", "ceo"])
        self.assertEqual(update.await_args.args[1], "partial")
        self.assertIn("test failed", result["final_output"])

    async def test_top_level_failure_has_terminal_event(self):
        with patch.object(workflow, "create_workspace", return_value=Path("unused")), patch.object(workflow, "company_graph") as graph, patch.object(workflow, "update_task", AsyncMock()) as update, patch.object(workflow, "set_task_state", AsyncMock()), patch.object(workflow, "_emit", AsyncMock()) as emit:
            graph.ainvoke = AsyncMock(side_effect=ValueError("invalid plan"))
            await workflow._execute("offline", "需求")
        self.assertEqual(update.await_args.args[1], "failed")
        self.assertTrue(emit.await_args.kwargs["terminal"])
        self.assertIsNone(task_workspace.get())

    async def test_legacy_database_migration_and_event_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "history.db"
            with sqlite3.connect(db) as conn:
                conn.execute("CREATE TABLE tasks(id TEXT PRIMARY KEY,user_input TEXT,status TEXT,result TEXT,created_at TEXT,updated_at TEXT)")
                conn.execute("CREATE TABLE task_logs(id INTEGER PRIMARY KEY AUTOINCREMENT,task_id TEXT,agent TEXT,message TEXT,created_at TEXT)")
                conn.execute("INSERT INTO tasks VALUES('old','old input','completed','old result','date','date')")
            conn.close()
            with patch.object(history, "DB_PATH", str(db)):
                await history.init_db()
                await history.init_db()
                self.assertEqual((await history.get_task("old"))["result"], "old result")
                await history.create_task("new", "需求")
                first = await history.add_log("new", "Dev", "writing", status="working", payload={"subtask_id": "t1"})
                await history.add_log("new", "SYSTEM", "failed", status="error", payload={"terminal": True})
                replay = await history.get_task_logs("new", first["id"])
                self.assertEqual(len(replay), 1)
                self.assertTrue(replay[0]["terminal"])


class ToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_mcp_files_and_git_stay_in_task(self):
        with tempfile.TemporaryDirectory() as temp:
            token = task_workspace.set(temp)
            try:
                await call_tool("filesystem", "write_file", agent_name="dev", path="app.py", content="x = 1")
                self.assertEqual(await call_tool("filesystem", "read_file", agent_name="review", path="app.py"), "x = 1")
                with self.assertRaises(RuntimeError):
                    await call_tool("git", "git_add", agent_name="dev", path="app.py")
                await call_tool("git", "git_init", agent_name="dev")
                await call_tool("git", "git_add", agent_name="dev", path="app.py")
                await call_tool("git", "git_commit", agent_name="dev", message="test: isolated artifact 中文提交")
                self.assertIn("isolated artifact", await call_tool("git", "git_log", agent_name="review"))
                with self.assertRaises(RuntimeError):
                    await call_tool("filesystem", "write_file", agent_name="dev", path="../escape.py", content="bad")
                with self.assertRaises(PermissionError):
                    await call_tool("git", "git_status", agent_name="search")
            finally:
                task_workspace.reset(token)

    async def test_test_agent_runs_actual_files(self):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "app.py").write_text("value = 42", encoding="utf-8")
            token = task_workspace.set(temp)
            try:
                for assertion, expected in [("value == 42", "passed"), ("value == 0", "failed")]:
                    result = {"files": [{"path": "test_app.py", "content": f"from app import value\ndef test_value():\n    assert {assertion}\n"}]}
                    with patch.object(test_agent, "generate_files", AsyncMock(return_value=result)):
                        output = await test_agent.test_agent_run("测试", {"files": ["app.py"]})
                    self.assertEqual(output["verification"], expected)
                    self.assertEqual(output["execution"]["total"], 1)
                    self.assertNotIn("pass_rate", output)
            finally:
                task_workspace.reset(token)


if __name__ == "__main__":
    unittest.main()
