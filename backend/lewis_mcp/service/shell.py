"""任务工作区中的命令与测试执行，返回可核对的实际证据。"""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("lewis-shell")
WORKSPACE = os.environ.get("LEWIS_WORKSPACE", "/tmp/lewis_workspace")
ALLOWED_COMMANDS = {"python", "npm", "node", "yarn"}


@mcp.tool()
def run_command(command: str, timeout: int = 30) -> str:
    """执行单条命令，不接受 Shell 运算符，工作目录固定为任务目录。"""
    try:
        if any(c in command for c in (";", "&", "|", ">", "<", "\n", "\r", "\x60")):
            return "ERROR: 不允许 Shell 运算符"
        args = shlex.split(command)
        if not args or args[0] not in ALLOWED_COMMANDS:
            return "ERROR: 命令不在允许列表中"
        if args[0] == "python":
            args[0] = sys.executable
        result = subprocess.run(args, shell=False, cwd=WORKSPACE, capture_output=True, stdin=subprocess.DEVNULL,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                text=True, encoding="utf-8", errors="replace", timeout=max(1, min(timeout, 60)))
        if result.returncode:
            return f"ERROR: 退出码 {result.returncode}\n{result.stdout}\n{result.stderr}"
        return result.stdout.strip() or "OK（无输出）"
    except Exception as exc:
        return f"ERROR: {exc}"


@mcp.tool()
def run_tests(paths: list[str], timeout: int = 60) -> str:
    """仅执行根目录 test_*.py，保存 JUnit 报告并返回退出码、输出、耗时与实际统计。"""
    if not paths or any(not p.startswith("test_") or not p.endswith(".py") or "/" in p or "\\" in p for p in paths):
        raise ValueError("测试路径必须为根目录 test_*.py")
    report = Path(WORKSPACE) / ".lewis" / "test-results.xml"
    report.parent.mkdir(exist_ok=True)
    report.unlink(missing_ok=True)
    command = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
               "--override-ini=addopts=", "--junitxml=" + str(report), *paths]
    start = time.monotonic()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    try:
        result = subprocess.run(command, cwd=WORKSPACE, env=env, capture_output=True, stdin=subprocess.DEVNULL,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                                text=True, encoding="utf-8", errors="replace", timeout=max(1, min(timeout, 60)))
        evidence = {"command": command, "exit_code": result.returncode,
                    "stdout": result.stdout, "stderr": result.stderr, "timed_out": False}
    except subprocess.TimeoutExpired as exc:
        def text(value):
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value or ""
        evidence = {"command": command, "exit_code": None, "stdout": text(exc.stdout),
                    "stderr": text(exc.stderr), "timed_out": True}
    evidence.update({"duration_seconds": round(time.monotonic() - start, 3),
                     "total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0})
    if report.exists():
        suites = list(ET.parse(report).getroot().iter("testsuite"))
        for suite in suites:
            evidence["total"] += int(suite.get("tests", 0))
            evidence["failed"] += int(suite.get("failures", 0))
            evidence["errors"] += int(suite.get("errors", 0))
            evidence["skipped"] += int(suite.get("skipped", 0))
        evidence["passed"] = max(0, evidence["total"] - evidence["failed"] - evidence["errors"] - evidence["skipped"])
    return json.dumps(evidence, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
