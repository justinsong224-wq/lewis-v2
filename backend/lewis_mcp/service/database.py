"""
Database MCP Service
提供 SQLite 查询工具，供 Analyst Agent 专用
"""
import os
import sqlite3
import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lewis-database")

WORKSPACE = os.environ.get("LEWIS_WORKSPACE", "/tmp/lewis_workspace")


def _db_path(db_name: str) -> str:
    path = os.path.realpath(os.path.join(WORKSPACE, db_name))
    if os.path.commonpath([path, os.path.realpath(WORKSPACE)]) != os.path.realpath(WORKSPACE):
        raise ValueError("路径越界")
    return path


@mcp.tool()
def query(db_name: str, sql: str) -> str:
    """执行 SELECT 查询，返回 JSON 格式结果。db_name: 数据库文件名（相对 workspace），sql: SELECT 语句"""
    if not sql.strip().upper().startswith("SELECT"):
        return "ERROR: 只允许 SELECT 查询"
    try:
        conn = sqlite3.connect(_db_path(db_name))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(sql)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return json.dumps(rows, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def list_tables(db_name: str) -> str:
    """列出数据库中所有表名。"""
    try:
        conn = sqlite3.connect(_db_path(db_name))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        return "\n".join(tables) if tables else "（无表）"
    except Exception as e:
        return f"ERROR: {e}"


@mcp.tool()
def describe_table(db_name: str, table_name: str) -> str:
    """查看表结构。"""
    try:
        conn = sqlite3.connect(_db_path(db_name))
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        cols = [f"{r[1]} ({r[2]})" for r in cursor.fetchall()]
        conn.close()
        return "\n".join(cols) if cols else "（表不存在或无列）"
    except Exception as e:
        return f"ERROR: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
