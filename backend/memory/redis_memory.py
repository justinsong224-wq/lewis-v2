"""Redis 仅作缓存与事件唤醒；故障时使用 SQLite，不阻断开发流程。"""
import asyncio
import json
import logging
import time
import redis.asyncio as aioredis
from redis.backoff import NoBackoff
from redis.asyncio.retry import Retry
from config.settings import settings

_redis: aioredis.Redis | None = None
_retry_after = 0.0
_probe_lock = asyncio.Lock()
logger = logging.getLogger(__name__)


class RedisUnavailable(RuntimeError):
    pass


def mark_redis_unavailable(exc):
    global _retry_after
    if time.monotonic() >= _retry_after:
        logger.warning('Redis 暂不可用（%s），使用 SQLite 事件回放，%.0f 秒后允许重连',
                       type(exc).__name__, settings.redis_retry_seconds)
    _retry_after = time.monotonic() + settings.redis_retry_seconds


async def close_redis():
    global _redis, _retry_after
    client, _redis = _redis, None
    _retry_after = 0.0
    if client is not None:
        try:
            await client.aclose()
        except Exception as exc:
            logger.debug('Redis 关闭失败：%s', type(exc).__name__)


async def get_redis() -> aioredis.Redis:
    global _redis, _retry_after
    if not settings.redis_url.strip() or time.monotonic() < _retry_after:
        raise RedisUnavailable('Redis 已禁用或处于故障冷却期')
    async with _probe_lock:
        if time.monotonic() < _retry_after:
            raise RedisUnavailable('Redis 处于故障冷却期')
        if _redis is None:
            _redis = aioredis.from_url(settings.redis_url, decode_responses=True,
                socket_connect_timeout=1, socket_timeout=1, retry=Retry(NoBackoff(), 0))
        if _retry_after:
            try:
                await _redis.ping()
            except Exception as exc:
                mark_redis_unavailable(exc)
                raise RedisUnavailable('Redis 重连失败') from exc
            _retry_after = 0.0
            logger.info('Redis 连接已恢复')
        return _redis


async def _optional_command(name, *args, **kwargs):
    try:
        client = await get_redis()
        return await getattr(client, name)(*args, **kwargs)
    except RedisUnavailable:
        return None
    except Exception as exc:
        mark_redis_unavailable(exc)
        return None


async def set_task_state(task_id: str, state: dict, ttl: int = 3600):
    await _optional_command('set', f"task:{task_id}", json.dumps(state, ensure_ascii=False), ex=ttl)

async def get_task_state(task_id: str) -> dict | None:
    val = await _optional_command('get', f"task:{task_id}")
    return json.loads(val) if val else None

async def publish_event(task_id: str, event: dict):
    """向前端推送实时事件（WebSocket中转）"""
    await _optional_command('publish', f"events:{task_id}", json.dumps(event, ensure_ascii=False))
