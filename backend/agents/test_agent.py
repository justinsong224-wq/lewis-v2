"""读取实际代码，生成测试文件，再通过 MCP 执行 pytest。"""
import ast
import json
from agents.file_output import generate_files
from agents.scope import scope_note
from lewis_mcp.client.client import call_tool

TEST_SYSTEM = """你是Lewis软件开发公司的测试工程师。
根据实际代码、需求验收条件编写可执行 pytest 用例，覆盖正常、边界与异常输入。
不要修改应用代码。只生成 test_*.py 文件；API 测试使用 fastapi.testclient.TestClient。
使用随后给出的文件输出协议，返回完整测试源文件。
不要输出通过率或声称执行成功，执行结果由系统提供。
若 context.revision 存在，按照原 parent_user_input 和本轮 user_input 同时覆盖原功能回归与新增需求；以本次读取的 actual_files 为实际代码。
"""


async def test_agent_run(task: str, context: dict = None) -> dict:
    paths = (context or {}).get("files", [])
    if not paths:
        raise ValueError("没有实际代码可测试")
    code = []
    for path in paths:
        content = await call_tool("filesystem", "read_file", agent_name="test", path=path)
        code.append({"path": path, "content": content})
    result = await generate_files(TEST_SYSTEM + '\n' + scope_note(context, 'test'), json.dumps({"task": task, "context": context, "actual_files": code}, ensure_ascii=False), tests_only=True)
    files = result.get("files", [])
    if not files:
        raise ValueError("测试工程师未生成可执行测试文件")
    for item in files:
        path = item["path"]
        if "/" in path or "\\" in path or not path.startswith("test_") or not path.endswith(".py"):
            raise ValueError("测试文件必须为任务根目录下的 test_*.py")
        ast.parse(item["content"], filename=path)
    for item in files:
        await call_tool("filesystem", "write_file", agent_name="test", **item)
    execution = json.loads(await call_tool("shell", "run_tests", agent_name="test", paths=[f["path"] for f in files]))
    result.pop("pass_rate", None)
    passed = execution.get("exit_code") == 0 and execution.get("passed", 0) > 0
    result.update({"execution": execution, "verification": "passed" if passed else "failed",
                   "summary": f"实际测试：{execution.get('passed', 0)}/{execution.get('total', 0)} 通过"})
    if not passed:
        result["error"] = "实际测试未通过或未成功收集用例"
    return result
