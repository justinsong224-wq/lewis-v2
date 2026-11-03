"""
MCP Server 路径注册表
统一管理 server 名称 → 脚本路径的映射，新增 service 只需在此注册
"""
import os

_SERVICE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "service")

MCP_SERVERS: dict[str, str] = {
    "filesystem": os.path.join(_SERVICE_DIR, "filesystem.py"),
    "search":     os.path.join(_SERVICE_DIR, "search.py"),
    "git":        os.path.join(_SERVICE_DIR, "git.py"),
    "database":   os.path.join(_SERVICE_DIR, "database.py"),
    "shell":      os.path.join(_SERVICE_DIR, "shell.py"),
}


def get_server_path(name: str) -> str:
    path = MCP_SERVERS.get(name)
    if not path:
        raise ValueError(f"未注册的 MCP server：{name}。可用：{list(MCP_SERVERS.keys())}")
    return path