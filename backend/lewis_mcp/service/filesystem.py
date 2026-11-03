"""
Filesystem MCP Service
提供文件读写工具，供 Dev Agent / Writer Agent 共用
"""
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lewis-filesystem")

WORKSPACE = os.environ.get("LEWIS_WORKSPACE", "/tmp/lewis_workspace")
os.makedirs(WORKSPACE, exist_ok=True)


def _safe_path(relative_path: str) -> str:
    abs_path = os.path.realpath(os.path.join(WORKSPACE, relative_path))
    root = os.path.realpath(WORKSPACE)
    if os.path.commonpath([root, abs_path]) != root:
        raise ValueError(f"路径越界：{relative_path}")
    parts = os.path.relpath(abs_path, root).replace("\\", "/").split("/")
    if any(part.casefold() in ('.git', '.lewis', '.env') for part in parts):
        raise ValueError("不允许直接访问 Git 元数据、运行证据或环境凭据文件")
    return abs_path


@mcp.tool()
def read_file(path: str) -> str:
    """读取文件内容。path 为相对于 workspace 的路径。"""
    abs_path = _safe_path(path)
    if not os.path.exists(abs_path):
        return f"ERROR: 文件不存在：{path}"
    with open(abs_path, "r", encoding="utf-8") as f:
        return f.read()


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """写入文件内容（覆盖）。path 为相对于 workspace 的路径。"""
    abs_path = _safe_path(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"OK: 已写入 {path}（{len(content)} 字符）"


@mcp.tool()
def append_file(path: str, content: str) -> str:
    """追加内容到文件末尾。"""
    abs_path = _safe_path(path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "a", encoding="utf-8") as f:
        f.write(content)
    return f"OK: 已追加到 {path}"


@mcp.tool()
def list_files(directory: str = ".") -> str:
    """列出目录下的文件和子目录。"""
    abs_path = _safe_path(directory)
    if not os.path.exists(abs_path):
        return f"ERROR: 目录不存在：{directory}"
    items = []
    for item in sorted(os.listdir(abs_path)):
        full = os.path.join(abs_path, item)
        tag = "[DIR]" if os.path.isdir(full) else "[FILE]"
        items.append(f"{tag} {item}")
    return "\n".join(items) if items else "（空目录）"


@mcp.tool()
def delete_file(path: str) -> str:
    """删除文件。"""
    abs_path = _safe_path(path)
    if not os.path.exists(abs_path):
        return f"ERROR: 文件不存在：{path}"
    os.remove(abs_path)
    return f"OK: 已删除 {path}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
