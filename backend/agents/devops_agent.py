"""
DevOps Agent
负责部署脚本、环境配置
MCP: shell + filesystem
"""
import json
from agents.base import completion_messages
from lewis_mcp.client.client import call_tool


DEVOPS_SYSTEM = """你是Lewis的DevOps Agent（运维工程师）。
职责：编写部署脚本、Docker 配置、CI/CD 流程，执行环境配置命令。
本地命令成功不等于已部署到外部服务。仅依据实际命令输出说明执行情况，未执行或失败明确标注。

输出 JSON：
{
  "plan": "部署方案说明",
  "config_files": [
    {"path": "文件路径", "content": "文件内容"}
  ],
  "commands": ["需要执行的命令1", "命令2"],
  "summary": "部署完成说明"
}
"""


async def devops_agent_run(task: str, context: dict = None) -> dict:
    messages = [{"role": "system", "content": DEVOPS_SYSTEM}]
    if context:
        messages.append({"role": "user", "content": f"背景：{json.dumps(context, ensure_ascii=False)}"})
    messages.append({"role": "user", "content": f"运维任务：{task}"})

    resp = await completion_messages(
        messages=messages,
        json_output=True,
    )
    result = resp

    # 写配置文件
    for f in result.get("config_files", []):
        await call_tool("filesystem", "write_file", agent_name="devops", path=f["path"], content=f["content"])

    # 执行命令
    cmd_results = []
    for cmd in result.get("commands", []):
        out = await call_tool("shell", "run_command", agent_name="devops", command=cmd)
        cmd_results.append({"command": cmd, "output": out})
    result["command_results"] = cmd_results
    result['files'] = [{'path': f['path']} for f in result.get('config_files', [])]
    failed = [item['command'] for item in cmd_results if item['output'].startswith('ERROR:')]
    if failed:
        result['error'] = '运维命令执行失败：' + '、'.join(failed)
    result['verification'] = 'failed' if failed else 'executed' if cmd_results else 'not_run'

    return result
