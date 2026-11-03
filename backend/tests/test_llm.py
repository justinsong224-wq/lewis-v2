"""模拟兼容接口验证配置、请求及错误回退，无外部网络调用。"""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import httpx
from openai import AsyncOpenAI, AuthenticationError, BadRequestError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents import base
from config.settings import Settings
from agents.file_output import normalize_files, parse_file_blocks


class SettingsTests(unittest.TestCase):
    def test_file_blocks_preserve_code_and_reject_partial_or_unsafe_output(self):
        code = 'value = "quoted"' + chr(10) + 'def f():' + chr(10) + '    return value' + chr(10)
        block = '<<<LEWIS_FILE:app.py>>>' + chr(10) + code + '<<<LEWIS_END_FILE>>>'
        self.assertEqual(parse_file_blocks(block)["files"], [{"path": "app.py", "content": code}])
        for invalid in (block.replace('app.py', '../app.py'), block + chr(10) + block, block.replace('<<<LEWIS_END_FILE>>>', ''), 'explanation' + chr(10) + block):
            with self.assertRaises(ValueError):
                parse_file_blocks(invalid)

    def test_file_lines_preserve_quotes_indentation_and_legacy_content(self):
        lines = ['def label():', '    return "演示工单 01"', '']
        value = normalize_files({"files": [{"path": "app.py", "lines": lines}]})
        self.assertEqual(value["files"][0]["content"], chr(10).join(lines))
        self.assertNotIn("lines", value["files"][0])
        legacy = {"files": [{"path": "app.py", "content": "value = 1"}]}
        self.assertEqual(normalize_files(legacy), legacy)
        for item in ({"path": "app.py", "lines": [1]}, {"path": "app.py", "lines": ['a' + chr(10) + 'b']}, {"path": "app.py", "lines": ["a"], "content": "b"}):
            with self.assertRaises(ValueError):
                normalize_files({"files": [item]})

    def test_json_control_characters_and_invalid_structure(self):
        raw = '{"technical_plan":"first' + chr(10) + 'second"}'
        self.assertEqual(base.parse_json_object(raw), {"technical_plan": "first" + chr(10) + "second"})
        with self.assertRaises(ValueError):
            base.parse_json_object('{"technical_plan":')

    def test_generic_config_and_no_provider_defaults(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "generic"}, clear=True):
            config = Settings(_env_file=None)
            self.assertEqual(config.llm_api_key, "generic")
            self.assertNotIn("generic", repr(config))
        with patch.dict(os.environ, {}, clear=True):
            config = Settings(_env_file=None)
            self.assertEqual(config.llm_api_key, "")
            self.assertEqual(config.llm_base_url, "")
            self.assertEqual(config.llm_model, "")

    def test_url_alias_normalization_and_validation(self):
        with patch.dict(os.environ, {"LLM_BASE_URL": "https://provider.example/api/v1/chat/completions/"}, clear=True):
            self.assertEqual(Settings(_env_file=None).llm_base_url, "https://provider.example/api/v1")
        with patch.dict(os.environ, {}, clear=True):
            for url in ("ftp://example.com", "https://user:secret@example.com/v1", "https://example.com/v1?key=secret"):
                with self.assertRaises(ValueError):
                    Settings(_env_file=None, llm_base_url=url)


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_total_deadline_cancels_slow_request_without_retry(self):
        import asyncio
        from unittest.mock import AsyncMock
        config = Settings(_env_file=None, llm_api_key='test', llm_base_url='https://provider.example/v1',
                          llm_model='test-model', llm_timeout_seconds=0.03)
        cancelled = asyncio.Event()
        async def slow(**kwargs):
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.set()
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.chat.completions.create.side_effect = slow
        with patch.object(base, 'settings', config), patch.object(base, 'AsyncOpenAI', return_value=client) as factory:
            with self.assertRaisesRegex(TimeoutError, '未自动重试'):
                await base.llm_json('system', 'task')
        self.assertTrue(cancelled.is_set())
        self.assertEqual(client.chat.completions.create.await_count, 1)
        self.assertEqual(factory.call_args.kwargs['max_retries'], 0)

    async def test_planning_keeps_requirements_without_copying_source_bodies(self):
        from agents import ceo_agent
        from unittest.mock import AsyncMock
        context = {'actual_files': [{'path': 'app.py', 'content': 'large source body'}],
                   'revision': {'parent_user_input': 'keep original contract'},
                   'pm': {'prd': {'acceptance_criteria': ['404 and 422']}}}
        model = AsyncMock(return_value={'subtasks': []})
        with patch.object(ceo_agent, 'completion_messages', model):
            await ceo_agent.ceo_agent_run('POST /predict-batch', 'test', context)
        prompt = model.call_args.kwargs['messages'][1]['content']
        self.assertNotIn('large source body', prompt)
        self.assertIn('app.py', prompt)
        self.assertIn('keep original contract', prompt)
        self.assertIn('404 and 422', prompt)
        self.assertIn('POST /predict-batch', prompt)
        self.assertEqual(context['actual_files'][0]['content'], 'large source body')

    async def test_invalid_json_gets_only_one_model_correction(self):
        from unittest.mock import AsyncMock
        config = Settings(_env_file=None, llm_api_key="test", llm_base_url="https://provider.example/v1", llm_model="model")
        from types import SimpleNamespace
        def response(text):
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=text))])
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.chat.completions.create.side_effect = [response('{"bad":'), response('{"ok":true}')]
        with patch.object(base, "settings", config), patch.object(base, "AsyncOpenAI", return_value=client):
            self.assertEqual(await base.llm_json("system", "task"), {"ok": True})
        self.assertEqual(client.chat.completions.create.await_count, 2)
        repair_messages = client.chat.completions.create.call_args.kwargs['messages']
        self.assertNotIn('system', [message['content'] for message in repair_messages])
        repair_input = json.loads(repair_messages[1]['content'])
        self.assertEqual(repair_input['invalid_json'], '{"bad":')
        self.assertEqual(repair_input['parse_error']['line'], 1)
        self.assertIn('column', repair_input['parse_error'])
        client.chat.completions.create.reset_mock()
        client.chat.completions.create.side_effect = [response('{"bad":'), response('{"still_bad":')]
        with patch.object(base, "settings", config), patch.object(base, "AsyncOpenAI", return_value=client):
            with self.assertRaises(ValueError):
                await base.llm_json("system", "task")
        self.assertEqual(client.chat.completions.create.await_count, 2)

    async def test_missing_configuration_fails_before_request(self):
        for missing in ("llm_api_key", "llm_base_url", "llm_model"):
            values = {"llm_api_key": "test", "llm_base_url": "https://provider.example/v1", "llm_model": "model"}
            values[missing] = ""
            config = Settings(_env_file=None, **values)
            with patch.object(base, "settings", config), patch.object(base, "AsyncOpenAI") as client:
                with self.assertRaises(ValueError):
                    await base.llm_json("system", "task")
            client.assert_not_called()

    async def invoke(self, handler, mode="auto"):
        config = Settings(_env_file=None, llm_api_key="test-key", llm_base_url="https://provider.example/custom/v1", llm_model="provider-model", llm_json_mode=mode)
        client = AsyncOpenAI(api_key=config.llm_api_key, base_url=config.llm_base_url, max_retries=0,
                             http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
        with patch.object(base, "settings", config), patch.object(base, "AsyncOpenAI", return_value=client):
            return await base.llm_json("test system", "test task")

    def response(self, request, content='{"ok": true}', finish="stop"):
        return httpx.Response(200, request=request, json={"id": "test", "object": "chat.completion", "created": 0,
            "model": "provider-model", "choices": [{"index": 0, "finish_reason": finish,
            "message": {"role": "assistant", "content": content}}]})

    async def test_custom_url_key_and_model_are_used(self):
        def handler(request):
            self.assertEqual(str(request.url), "https://provider.example/custom/v1/chat/completions")
            self.assertEqual(request.headers["authorization"], "Bearer test-key")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "provider-model")
            self.assertEqual(body["response_format"], {"type": "json_object"})
            return self.response(request)
        self.assertEqual(await self.invoke(handler), {"ok": True})

    async def test_auto_fallback_only_for_explicit_unsupported_format(self):
        calls = []
        def handler(request):
            body = json.loads(request.content)
            calls.append(body)
            if len(calls) == 1:
                return httpx.Response(400, request=request, json={"error": {"message": "response_format is not supported"}})
            self.assertNotIn("response_format", body)
            self.assertIn("JSON", body["messages"][-1]["content"])
            return self.response(request, chr(96)*3 + 'json' + chr(10) + '{"ok":true}' + chr(10) + chr(96)*3)
        self.assertEqual(await self.invoke(handler), {"ok": True})
        self.assertEqual(len(calls), 2)

    async def test_auth_and_unrelated_bad_request_are_not_retried(self):
        for status, exception in ((401, AuthenticationError), (400, BadRequestError)):
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(status, request=request, json={"error": {"message": "invalid model or credentials"}})
            with self.assertRaises(exception):
                await self.invoke(handler)
            self.assertEqual(len(calls), 1)

    async def test_prompt_mode_and_invalid_output(self):
        def handler(request):
            self.assertNotIn("response_format", json.loads(request.content))
            return self.response(request)
        self.assertEqual(await self.invoke(handler, "prompt"), {"ok": True})
        for content, finish in (("[]", "stop"), (None, "stop"), ('{"partial":', "length")):
            with self.assertRaises(ValueError):
                await self.invoke(lambda request: self.response(request, content, finish))

    async def test_strict_mode_does_not_fallback(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(400, request=request, json={"error": {"message": "unsupported response_format"}})
        with self.assertRaises(BadRequestError):
            await self.invoke(handler, "json_object")
        self.assertEqual(len(calls), 1)
