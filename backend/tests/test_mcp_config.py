"""搜索子进程继承统一配置，不依赖入口是否 load_dotenv。"""
from contextlib import asynccontextmanager
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lewis_mcp.client import client
from config.settings import Settings


class SearchConfigTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_uses_settings_key_without_modifying_parent_environment(self):
        config = Settings(_env_file=None, serper_api_key='settings-test-key')
        captured = []
        @asynccontextmanager
        async def stdio(params):
            captured.append(params)
            yield (None, None)
        session = AsyncMock()
        session.__aenter__.return_value = session
        with (patch('config.settings.settings', config),
              patch.dict(client.os.environ, {'SERPER_API_KEY': 'old-test-key'}),
              patch.object(client, 'stdio_client', stdio),
              patch.object(client, 'ClientSession', return_value=session)):
            async with client.get_mcp_session('search'):
                pass
            self.assertEqual(captured[0].env['SERPER_API_KEY'], 'settings-test-key')
            self.assertEqual(client.os.environ['SERPER_API_KEY'], 'old-test-key')
