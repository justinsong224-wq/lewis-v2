"""
Git MCP Service
提供 Git 操作工具，供 Dev / DevOps Agent 共用
"""
import os
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lewis-git")

WORKSPACE = os.environ.get("LEWIS_WORKSPACE", "/tmp/lewis_workspace")


def _safe_target(path: str) -> str:
    root = os.path.realpath(WORKSPACE)
    target = os.path.realpath(os.path.join(root, path))
    if os.path.commonpath([root, target]) != root:
        raise ValueError("Git 路径越界")
    if ".git" in os.path.relpath(target, root).replace("\\", "/").split("/"):
        raise ValueError("不允许直接操作 Git 元数据")
    return target


def _run_git(args: list[str], cwd: str = None) -> str:
    cwd = cwd or WORKSPACE
    cwd = _safe_target(os.path.relpath(cwd, WORKSPACE))
    if args[0] != "init" and not os.path.isdir(os.path.join(WORKSPACE, ".git")):
        return "ERROR: 任务目录未初始化 Git，拒绝使用父仓库"
    try:
        result = subprocess.run(
            ["git", "-c", "user.name=Lewis", "-c", "user.email=lewis@localhost",
             "-c", "core.hooksPath=", "-c", "commit.gpgsign=false"] + args,
            cwd=cwd,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
        )
        output = (result.stdout or "").strip()
        if result.returncode != 0:
            return f"ERROR: {(result.stderr or result.stdout or 'git command failed').strip()}"
        return output or "OK"
    except subprocess.TimeoutExpired:
        return "ERROR: git 命令超时"
    except FileNotFoundError:
        return "ERROR: git 未安装"


@mcp.tool()
def git_init(path: str = ".") -> str:
    """在指定目录初始化 Git 仓库。"""
    target = _safe_target(path)
    if target != os.path.realpath(WORKSPACE):
        return "ERROR: 只能在任务根目录初始化仓库"
    os.makedirs(target, exist_ok=True)
    return _run_git(["init", "--template="], cwd=target)


@mcp.tool()
def git_status(path: str = ".") -> str:
    """查看工作区状态。"""
    return _run_git(["status", "--short"], cwd=_safe_target(path))


@mcp.tool()
def git_add(path: str = ".") -> str:
    """暂存文件（git add）。path 支持 '.' 或具体文件路径。"""
    _safe_target(path)
    return _run_git(["add", "--", path])


@mcp.tool()
def git_commit(message: str) -> str:
    """提交暂存区内容。message 为提交信息。"""
    return _run_git(["commit", "-m", message])


@mcp.tool()
def git_log(max_count: int = 10) -> str:
    """查看提交历史。"""
    return _run_git(["log", f"--max-count={max_count}", "--oneline"])


@mcp.tool()
def git_diff(path: str = ".") -> str:
    """查看未暂存的变更内容。"""
    _safe_target(path)
    return _run_git(["diff", "--", path])


@mcp.tool()
def git_create_branch(branch_name: str) -> str:
    """创建并切换到新分支。"""
    return _run_git(["checkout", "-b", branch_name])


@mcp.tool()
def git_checkout(branch_name: str) -> str:
    """切换分支。"""
    return _run_git(["checkout", branch_name])


if __name__ == "__main__":
    mcp.run(transport="stdio")
