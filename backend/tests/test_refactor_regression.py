"""收尾改动专项回归：版本证据、需求上下文与 Redis 冷却。"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph.evidence import verification_manifest, invalidate_changed_evidence
from graph.contracts import delivery_assessment
from graph.context import role_context
from agents.file_output import parse_file_blocks
from lewis_mcp.workspace import create_workspace
from memory import redis_memory as cache
from memory import sqlite_history as history
from graph import company_graph as workflow


class EvidenceRegressionTests(unittest.TestCase):
    def test_code_changes_invalidate_but_markdown_does_not(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'LEWIS_WORKSPACE': temp}):
            tid = str(uuid4())
            root = create_workspace(tid)
            (root / 'app.py').write_text('value=1')
            baseline = verification_manifest(tid)
            result = {'verified_files': baseline, 'subtask_id': 't', 'verification': 'passed',
                      'execution': {'exit_code': 0, 'passed': 1}}
            results = {'dev': {'files': [{'path': 'app.py'}]}, 'test': result}
            subs = {'t': result}
            (root / 'README.md').write_text('new docs')
            invalidate_changed_evidence(results, subs, verification_manifest(tid))
            self.assertEqual(delivery_assessment(results)['status'], 'completed')
            (root / 'app.py').write_text('value=2')
            invalidate_changed_evidence(results, subs, verification_manifest(tid))
            self.assertTrue(subs['t']['stale'])
            self.assertEqual(delivery_assessment(results)['status'], 'partial')
            self.assertEqual(delivery_assessment({'dev': results['dev'], 'test': result},
                acceptance_profile='sms-classifier')['status'], 'partial')

    def test_context_projection_preserves_original_evidence(self):
        result = {'files': [{'path': 'app.py', 'content': 'source'}],
                  'execution': {'exit_code': 0, 'stdout': 'long output'}}
        context = role_context({'user_input': 'change', 'agent_results': {'dev': result},
            'revision': {'parent_user_input': 'original', 'baseline': {'app.py': 'hash'}}})
        self.assertNotIn('content', context['dev']['files'][0])
        self.assertNotIn('stdout', context['dev']['execution'])
        self.assertNotIn('baseline', context['revision'])
        self.assertEqual(result['files'][0]['content'], 'source')

    def test_protected_and_windows_duplicate_paths_are_rejected(self):
        for path in ('.lewis/acceptance.json', '.git/config', '.env', './app.py'):
            with self.assertRaises(ValueError):
                parse_file_blocks(f'<<<LEWIS_FILE:{path}>>>\nx\n<<<LEWIS_END_FILE>>>')
        with self.assertRaises(ValueError):
            parse_file_blocks('<<<LEWIS_FILE:app.py>>>\nx\n<<<LEWIS_END_FILE>>>\n<<<LEWIS_FILE:APP.py>>>\ny\n<<<LEWIS_END_FILE>>>')


class RedisRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_final_review_reads_new_writer_documents(self):
        from agents import review_agent
        context = {'files': ['app.py', 'README.md'],
                   'test': {'files': [{'path': 'test_app.py'}]},
                   'writer': {'files': [{'path': 'README.md'}, {'path': 'docs/usage.md'}]}}
        read = AsyncMock(side_effect=lambda *args, **kwargs: 'actual:' + kwargs['path'])
        model = AsyncMock(return_value={'issues': []})
        with patch.object(review_agent, 'call_tool', read), patch.object(review_agent, 'completion_messages', model):
            await review_agent.review_agent_run('final review', context)
        self.assertEqual([call.kwargs['path'] for call in read.await_args_list],
                         ['app.py', 'README.md', 'test_app.py', 'docs/usage.md'])
        messages = model.call_args.kwargs['messages']
        self.assertIn('actual:docs/usage.md', messages[1]['content'])

    async def test_checkpoint_and_failure_preserve_real_snapshot(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(history, 'DB_PATH', str(Path(temp) / 'history.db')):
            await history.init_db()
            tid = str(uuid4())
            await history.create_task(tid, 'requirement')
            state = {'task_id': tid, 'user_input': 'requirement',
                     'agent_results': {'pm': {'prd': {'acceptance_criteria': ['contract']}}}}
            await workflow.save_checkpoint(state)
            with patch.object(workflow, '_emit', AsyncMock()):
                await workflow.save_execution_failure(tid, 'interrupted')
            task = await history.get_task(tid)
            self.assertEqual(task['status'], 'failed')
            self.assertEqual(task['snapshot']['agent_results']['pm']['prd']['acceptance_criteria'], ['contract'])
            self.assertEqual(task['snapshot']['delivery_assessment']['status'], 'failed')
            await history.update_task(tid, 'completed', 'done')
            with patch.object(workflow, '_emit', AsyncMock()):
                await workflow.save_execution_failure(tid, 'late cleanup error')
            self.assertEqual((await history.get_task(tid))['status'], 'completed')

    async def test_failure_cools_down_and_reconnects(self):
        client = AsyncMock()
        client.publish.side_effect = [TimeoutError(), 1]
        with (patch.object(cache, '_redis', client), patch.object(cache, '_retry_after', 0.0),
              patch.object(cache.time, 'monotonic', return_value=100) as clock):
            await cache.publish_event('task', {'id': 1})
            await cache.publish_event('task', {'id': 2})
            self.assertEqual(client.publish.await_count, 1)
            clock.return_value = 131
            await cache.publish_event('task', {'id': 3})
            client.ping.assert_awaited_once()
            self.assertEqual(client.publish.await_count, 2)
            self.assertEqual(cache._retry_after, 0)
