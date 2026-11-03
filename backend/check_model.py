"""最小真实模型连通性检查；不运行开发任务，不打印 Key 或原始错误响应。"""
import asyncio
import json
from urllib.parse import urlsplit
from agents.base import llm_json
from config.settings import settings


async def main():
    url = urlsplit(settings.llm_base_url)
    print(json.dumps({"endpoint": url.scheme + "://" + url.netloc + url.path,
                      "model": settings.llm_model, "json_mode": settings.llm_json_mode,
                      "key_configured": bool(settings.llm_api_key)}, ensure_ascii=False), flush=True)
    try:
        result = await llm_json('You are a connection checker. Return JSON.', 'Return {"ok": true}.')
        valid = result.get("ok") is True
        print(json.dumps({"connection": "ok", "json_ok": valid}), flush=True)
        return 0 if valid else 1
    except Exception as exc:
        print(json.dumps({"connection": "failed", "error_type": type(exc).__name__,
                          "status_code": getattr(exc, "status_code", None)}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
