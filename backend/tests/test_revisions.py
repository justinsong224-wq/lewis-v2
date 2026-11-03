"""增量任务复用真实文件，验证父目录不变及新增功能验收。"""
import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from revisions import copy_baseline, changes_since, manifest
from lewis_mcp.workspace import create_workspace, workspace_path
from graph import company_graph as workflow
from memory import sqlite_history as history
from acceptance import run_acceptance


class RevisionTests(unittest.TestCase):
    def test_baseline_excludes_old_reports_and_detects_real_changes(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'LEWIS_WORKSPACE': temp}):
            parent, child = str(uuid4()), str(uuid4())
            root = create_workspace(parent)
            (root / 'app.py').write_text('old', encoding='utf-8')
            (root / '.lewis').mkdir()
            (root / '.lewis/acceptance.json').write_text('{}')
            before = manifest(parent)
            files, baseline = copy_baseline(parent, child)
            self.assertEqual([f['path'] for f in files], ['app.py'])
            target = workspace_path(child)
            self.assertFalse((target / '.lewis/acceptance.json').exists())
            (target / 'app.py').write_text('new', encoding='utf-8')
            (target / 'README.md').write_text('docs', encoding='utf-8')
            self.assertEqual({f['path']: f['change'] for f in changes_since(child, baseline)}, {'README.md': 'added', 'app.py': 'modified'})
            self.assertEqual(manifest(parent), before)

    def test_execution_passes_actual_files_and_original_contract_to_graph(self):
        async def check():
            with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'LEWIS_WORKSPACE': temp}), patch.object(history, 'DB_PATH', str(Path(temp) / 'history.db')):
                await history.init_db()
                parent, child = str(uuid4()), str(uuid4())
                root = create_workspace(parent)
                (root / 'app.py').write_text('original = 42', encoding='utf-8')
                await history.create_task(parent, 'original contract')
                await history.update_task(parent, 'completed')
                await history.create_task(child, 'add detail')
                async def tool(server, name, agent, **kwargs):
                    return 'original = 42' if name == 'read_file' else 'ok'
                graph = AsyncMock()
                with patch.object(workflow, 'call_tool', side_effect=tool) as calls, patch.object(workflow, 'company_graph', graph), patch.object(workflow, 'set_task_state', AsyncMock()), patch.object(workflow, '_emit', AsyncMock()):
                    await workflow._execute(child, 'add detail', parent_task_id=parent)
                state = graph.ainvoke.call_args.args[0]
                self.assertEqual(state['actual_files'][0]['content'], 'original = 42')
                self.assertEqual(state['revision']['parent_user_input'], 'original contract')
                self.assertEqual(state['revision']['parent_task_id'], parent)
                self.assertEqual((workspace_path(child) / 'app.py').read_text(), 'original = 42')
                self.assertTrue(any(c.args[1] == 'read_file' for c in calls.call_args_list))
        asyncio.run(check())

