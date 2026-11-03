"""
MCP Client
Agent 通过此模块调用各 MCP Service（stdio 子进程模式）
调用前会校验 Agent 权限（见 registry/permissions.py）
"""
import sys
import os
import asyncio
import time
import logging
from datetime import datetime, timezone
from lewis_mcp.audit import event_sink, subtask_id, summarize
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from lewis_mcp.registry.servers import get_server_path
from lewis_mcp.registry.permissions import check_permission
from lewis_mcp.workspace import task_workspace


@asynccontextmanager
async def get_mcp_session(server_name: str):
    """获取指定 MCP server 的 session"""
    python_exe = sys.executable
    print(f"[MCP DEBUG] 启动子进程，使用解释器：{python_exe}", file=sys.stderr)
    env = {**os.environ}
    if server_name == 'search':
        from config.settings import settings
        env['SERPER_API_KEY'] = settings.serper_api_key
    workspace = task_workspace.get()
    if workspace:
        env["LEWIS_WORKSPACE"] = workspace
    params = StdioServerParameters(
        command=python_exe,
        args=[get_server_path(server_name)],
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def _call_tool(server_name: str, tool_name: str, agent_name: str = None, **kwargs) -> str:
    """
    调用指定 MCP server 的工具，返回结果字符串。
    若传入 agent_name，会先校验该 Agent 是否有权限调用该 server。
    示例：
        result = await call_tool("filesystem", "read_file", agent_name="dev", path="main.py")
    """
    if agent_name and not check_permission(agent_name, server_name):
        raise PermissionError(f"Agent '{agent_name}' 无权限调用 '{server_name}'")
    if server_name in {"filesystem", "git", "shell", "database"} and not task_workspace.get():
        raise RuntimeError("工具调用必须绑定独立任务工作区")

    async with get_mcp_session(server_name) as session:
        result = await session.call_tool(tool_name, arguments=kwargs)
        texts = [c.text for c in result.content if hasattr(c, "text")]
        output = "\n".join(texts)
    # 在 MCP task group 正常关闭后抛错，避免业务异常被包装成 ExceptionGroup。
    if result.isError or output.lstrip().startswith(("ERROR:", "STDERR:", "退出码:")):
        raise RuntimeError(f"{server_name}/{tool_name}: {output}")
    return output


async def call_tool(server_name: str, tool_name: str, agent_name: str = None, **kwargs) -> str:
    started = datetime.now(timezone.utc).isoformat()
    timer = time.monotonic()
    outcome, output, error = "failed", "", None
    try:
        output = await _call_tool(server_name, tool_name, agent_name, **kwargs)
        outcome = "succeeded"
        return output
    except asyncio.CancelledError:
        outcome, error = "cancelled", "调用被取消或角色超时"
        raise
    except Exception as exc:
        error = type(exc).__name__
        raise
    finally:
        sink = event_sink.get()
        if sink is not None:
            # 读文件的全文已作为产物保存，时间线只保存调用结果摘要。
            summary = f"返回 {len(output)} 字符" if outcome == "succeeded" else ""
            payload = {
                "kind": "tool_call", "server": server_name, "tool": tool_name,
                "subtask_id": subtask_id.get(), "arguments": summarize(kwargs),
                "started_at": started, "duration_seconds": round(time.monotonic() - timer, 3),
                "outcome": outcome, "output_summary": summary, "error": error,
            }
            try:
                await sink(agent_name or "SYSTEM", payload)
            except Exception:
                # 审计存储故障不应改变工具结果，也不覆盖原始工具异常。
                logging.getLogger(__name__).exception("工具调用记录保存失败")


async def list_tools(server_name: str) -> list[dict]:
    """列出指定 MCP server 的所有工具"""
    async with get_mcp_session(server_name) as session:
        result = await session.list_tools()
        return [{"name": t.name, "description": t.description} for t in result.tools]
