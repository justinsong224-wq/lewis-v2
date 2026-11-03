import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acceptance import run_acceptance
from lewis_mcp.workspace import create_workspace
from graph.context import planning_context
from unittest.mock import AsyncMock
from agents import dev_agent, test_agent, writer_agent

class SimpleDemoTests(unittest.TestCase):
    def test_new_project_accepts_missing_file_inventory(self):
        self.assertEqual(planning_context({'actual_files': None})['actual_files'], [])
        self.assertEqual(planning_context({})['actual_files'], [])

    def test_planning_drops_source_and_repeated_execution_results(self):
        original = {'user_input': 'requirement', 'actual_files': [{'path': 'app.py', 'content': 'body'}],
                    'subtask_results': {'large': 'body'}, 'test': {'stdout': 'body'},
                    'revision': {'parent_user_input': 'original contract'}}
        compact = planning_context(original)
        self.assertNotIn('subtask_results', compact)
        self.assertNotIn('test', compact)
        self.assertEqual(compact['actual_files'], [{'path': 'app.py'}])
        self.assertEqual(compact['revision'], original['revision'])
        self.assertEqual(original['actual_files'][0]['content'], 'body')


class SimpleRoleScopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_minimal_readme_preserves_markdown_without_file_protocol(self):
        markdown = '# API\n\n```python\nprint(1)\n```\n'
        write = AsyncMock()
        with patch.object(writer_agent, 'llm_text', AsyncMock(return_value=markdown)), patch.object(writer_agent, 'call_tool', write):
            result = await writer_agent.writer_agent_run('readme', {'acceptance_profile': 'sms-classifier', 'files': []})
        self.assertEqual(result['files'], [{'path': 'README.md', 'content': markdown}])
        write.assert_awaited_once_with('filesystem', 'write_file', agent_name='writer', path='README.md', content=markdown)

    async def test_minimal_development_prompt_assigns_only_application(self):
        generate = AsyncMock(side_effect=RuntimeError('stop before writing'))
        with patch.object(dev_agent, 'generate_files', generate):
            with self.assertRaisesRegex(RuntimeError, 'stop before writing'):
                await dev_agent.dev_agent_run('list', {'acceptance_profile': 'sms-classifier'})
        self.assertIn('只写页面/API', generate.await_args.args[0])

    async def test_minimal_test_prompt_limits_scope_and_reads_actual_source(self):
        generate = AsyncMock(side_effect=RuntimeError('stop before writing'))
        read = AsyncMock(return_value='actual application')
        with patch.object(test_agent, 'generate_files', generate), patch.object(test_agent, 'call_tool', read):
            with self.assertRaisesRegex(RuntimeError, 'stop before writing'):
                await test_agent.test_agent_run('test', {'acceptance_profile': 'sms-batch', 'files': ['app.py']})
        self.assertIn('真实模型测试', generate.await_args.args[0])
        self.assertIn('actual application', generate.await_args.args[1])
        read.assert_awaited_once_with('filesystem', 'read_file', agent_name='test', path='app.py')
