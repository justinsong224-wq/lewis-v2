"""临时数据库和工作区验证历史、产物与断线回放接口。"""
import asyncio
import os
from pathlib import Path
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

os.environ["LLM_API_KEY"] = "offline-test"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
import main
from memory import sqlite_history as history
from lewis_mcp.workspace import create_workspace


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(history, "DB_PATH", str(Path(self.temp.name) / "history.db")),
                        patch.dict(os.environ, {"LEWIS_WORKSPACE": self.temp.name}),
                        patch.object(main, "get_redis", AsyncMock(side_effect=RuntimeError("offline")))]
        for p in self.patches:
            p.start()
        self.client = TestClient(main.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def task(self, status="completed"):
        tid = str(uuid4())
        async def save():
            await history.create_task(tid, "开发工单 API")
            await history.update_task(tid, status, "实际结果", snapshot={"plan": {}, "agent_results": {}})
        asyncio.run(save())
        return tid

    def test_submission_saved_before_start_and_validation(self):
        saved = []
        def run(tid, user_input):
            conn = sqlite3.connect(history.DB_PATH)
            conn.row_factory = sqlite3.Row
            try:
                saved.append(dict(conn.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()))
            finally:
                conn.close()
        with patch.object(main, "run_task", run):
            response = self.client.post("/api/task", json={"user_input": "开发接口"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(saved[0]["status"], "queued")
        self.assertEqual(self.client.post("/api/task", json={"user_input": "  "}).status_code, 422)

    def test_research_report_preview_download_and_missing(self):
        tid = self.task()
        self.assertEqual(self.client.get(f'/api/task/{tid}/research-report').status_code, 404)
        snapshot = {'agent_results': {'search': {'query': 'FastAPI SQLite',
            'summary': '<script>alert(1)</script>', 'key_points': ['使用参数化查询'],
            'sources': ['https://fastapi.tiangolo.com/']}},
            'plan': {'research_decisions': [{'source': '官方文档', 'adopted': True, 'reason': '匹配技术栈'}]}}
        asyncio.run(history.update_task(tid, 'completed', snapshot=snapshot))
        response = self.client.get(f'/api/task/{tid}/research-report')
        self.assertEqual(response.status_code, 200)
        self.assertIn('技术调研报告', response.text)
        self.assertIn('&lt;script&gt;', response.text)
        self.assertNotIn('<script>', response.text)
        download = self.client.get(f'/api/task/{tid}/research-report?download=true')
        self.assertIn('attachment', download.headers['content-disposition'])
        self.assertIn('## 技术方案采纳情况', download.text)
        self.assertIn('匹配技术栈', download.text)
        self.assertEqual(self.client.get(f'/api/task/{tid}').json()['snapshot'], snapshot)

    def test_history_filter_and_pagination(self):
        tid = self.task("partial")
        self.task("failed")
        data = self.client.get("/api/tasks?status=partial&page_size=1").json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["id"], tid)
        self.assertFalse(data["items"][0]["has_evidence"])
        asyncio.run(history.update_task(tid, 'partial', snapshot={'agent_results': {'test': {
            'verification': 'passed', 'stale': True}}, 'execution_type': 'revision', 'parent_task_id': 'parent'}))
        item = self.client.get('/api/tasks?status=partial').json()['items'][0]
        self.assertTrue(item['has_evidence'])
        self.assertTrue(item['test_stale'])
        self.assertEqual(item['execution_type'], 'revision')
        self.assertEqual(self.client.get("/api/tasks?page=0").status_code, 422)
        self.assertEqual(self.client.get("/api/tasks?status=madeup").status_code, 422)
        self.assertEqual(self.client.get("/api/task/missing").status_code, 404)

    def test_lineage_preserves_evidence_and_detects_missing_parent_and_cycle(self):
        parent, child = self.task("partial"), self.task()
        async def save():
            await history.update_task(parent, "partial", snapshot={"acceptance": {"passed": 7, "total": 14, "verification": "failed"}})
            await history.update_task(child, "completed", snapshot={"parent_task_id": parent, "execution_type": "repair",
                "agent_results": {"test": {"execution": {"passed": 28, "total": 28, "exit_code": 0}}},
                "acceptance": {"passed": 14, "total": 14, "verification": "passed"}})
        asyncio.run(save())
        data = self.client.get(f"/api/task/{child}/lineage").json()
        self.assertEqual([item["id"] for item in data["items"]], [parent, child])
        self.assertEqual(data["items"][0]["acceptance"]["passed"], 7)
        self.assertEqual(data["items"][1]["test"]["passed"], 28)
        self.assertFalse(data["incomplete"])
        asyncio.run(history.update_task(parent, "partial", snapshot={"parent_task_id": child}))
        self.assertTrue(self.client.get(f"/api/task/{child}/lineage").json()["incomplete"])
        asyncio.run(history.update_task(parent, "partial", snapshot={"parent_task_id": "missing"}))
        self.assertTrue(self.client.get(f"/api/task/{child}/lineage").json()["incomplete"])
        self.assertEqual(self.client.get('/api/task/missing/lineage').status_code, 404)

    def test_explicit_acceptance_profile_is_persisted(self):
        with patch.object(main, "run_task") as run:
            response = self.client.post("/api/task", json={"user_input": "工单查询", "acceptance_profile": "sms-classifier"})
        tid = response.json()["task_id"]
        run.assert_called_once_with(tid, "工单查询", acceptance_profile="sms-classifier")
        self.assertEqual(self.client.get(f"/api/task/{tid}").json()["snapshot"]["acceptance_profile"], "sms-classifier")
        self.assertEqual(self.client.post("/api/task", json={"user_input": "接口", "acceptance_profile": "shell"}).status_code, 422)

    def test_revision_validates_parent_and_persists_link_before_start(self):
        parent = self.task()
        root = create_workspace(parent)
        (root / 'app.py').write_text('value = 42', encoding='utf-8')
        with patch.object(main, 'run_task') as run:
            response = self.client.post('/api/task', json={'user_input': '增加详情', 'parent_task_id': parent, 'acceptance_profile': 'sms-batch'})
        self.assertEqual(response.status_code, 200)
        tid = response.json()['task_id']
        run.assert_called_once_with(tid, '增加详情', acceptance_profile='sms-batch', parent_task_id=parent)
        self.assertEqual(self.client.get(f'/api/task/{tid}').json()['snapshot']['parent_task_id'], parent)
        self.assertEqual(self.client.get(f'/api/task/{parent}').json()['status'], 'completed')
        self.assertEqual(self.client.post('/api/task', json={'user_input': '修改', 'parent_task_id': tid}).status_code, 409)
        self.assertEqual(self.client.post('/api/task', json={'user_input': '修改', 'parent_task_id': 'missing'}).status_code, 404)
        empty = self.task()
        self.assertEqual(self.client.post('/api/task', json={'user_input': '修改', 'parent_task_id': empty}).status_code, 422)

    def test_artifact_list_preview_download_and_traversal(self):
        tid = self.task()
        root = create_workspace(tid)
        (root / "app.py").write_text("value = 42", encoding="utf-8")
        (root / ".git").mkdir()
        (root / ".git" / "config").write_text("private")
        (root / ".env").write_text("private")
        data = self.client.get(f"/api/task/{tid}/artifacts").json()
        self.assertEqual([f["path"] for f in data["files"]], ["app.py"])
        response = self.client.get(f"/api/task/{tid}/artifact", params={"path": "app.py"})
        self.assertEqual(response.json()["content"], "value = 42")
        response = self.client.get(f"/api/task/{tid}/artifact", params={"path": "app.py", "download": True})
        self.assertIn("attachment", response.headers["content-disposition"])
        for path in ("../history.db", ".git/config", ".env"):
            self.assertEqual(self.client.get(f"/api/task/{tid}/artifact", params={"path": path}).status_code, 400)

    def test_websocket_replays_terminal_task_without_redis(self):
        tid = self.task("failed")
        async def events():
            first = await history.add_log(tid, "Dev", "开始", status="working")
            await history.add_log(tid, "SYSTEM", "失败", status="error", payload={"terminal": True, "task_status": "failed"})
            return first["id"]
        first = asyncio.run(events())
        with self.client.websocket_connect(f"/ws/{tid}?after_id={first}") as ws:
            event = ws.receive_json()
            self.assertTrue(event["terminal"])
            self.assertEqual(event["task_status"], "failed")

    def test_websocket_replays_recovery_after_old_terminal(self):
        tid = self.task("completed")
        async def events():
            await history.add_log(tid, "Customer", "额度失败", status="error", payload={"terminal": True, "task_status": "failed"})
            await history.add_log(tid, "SYSTEM", "恢复汇总", status="working")
            await history.add_log(tid, "Customer", "交付完成", status="completed", payload={"terminal": True, "task_status": "completed"})
        asyncio.run(events())
        with self.client.websocket_connect(f"/ws/{tid}") as ws:
            old, recovery, final = [ws.receive_json() for _ in range(3)]
        self.assertFalse(old["terminal"])
        self.assertTrue(old["historical_terminal"])
        self.assertEqual(recovery["message"], "恢复汇总")
        self.assertTrue(final["terminal"])
        self.assertEqual(final["task_status"], "completed")
