"""固定业务验收；只运行仓库预设用例，不接受自定义命令。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from lewis_mcp.workspace import workspace_path

ROOT = Path(__file__).resolve().parents[1]


def run_acceptance(task_id, profile="sms-classifier"):
    if profile not in ("sms-classifier", "sms-batch"):
        raise ValueError("未知业务验收配置")
    workspace = workspace_path(task_id)
    report = workspace / ".lewis" / "acceptance.xml"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    command = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
               "--junitxml=" + str(report), str(ROOT / "demo/sms-classifier/test_acceptance.py")]
    expected = 5
    if profile == "sms-batch":
        command.append(str(ROOT / "demo/sms-classifier/test_batch.py"))
        expected = 8
    env = {**os.environ, "LEWIS_DEMO_APP_DIR": str(workspace), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    start = time.monotonic()
    result = {"command": command, "exit_code": None, "stdout": "", "stderr": "",
              "total": 0, "failed": 0, "errors": 0, "skipped": 0}
    try:
        output = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=60,
                                stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        result.update(exit_code=output.returncode, stdout=output.stdout, stderr=output.stderr)
    except (subprocess.TimeoutExpired, OSError) as exc:
        result["stderr"] = f"独立业务验收执行失败：{type(exc).__name__}"
    result["duration_seconds"] = round(time.monotonic() - start, 3)
    if report.exists():
        try:
            for suite in ET.parse(report).getroot().iter("testsuite"):
                for key, attr in [("total", "tests"), ("failed", "failures"), ("errors", "errors"), ("skipped", "skipped")]:
                    result[key] += int(suite.get(attr, 0))
        except (ET.ParseError, ValueError):
            result["errors"] += 1
    result["passed"] = max(0, result["total"] - result["failed"] - result["errors"] - result["skipped"])
    result['profile'] = profile
    result["verification"] = "passed" if (result["exit_code"] == 0 and result["total"] == expected
                                         and result["passed"] == expected and result["errors"] == 0) else "failed"
    (report.parent / "acceptance.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
