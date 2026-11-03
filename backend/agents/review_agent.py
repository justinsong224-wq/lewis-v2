"""
Review Agent
负责 Code Review、规范检查
MCP: filesystem
"""
import json
from agents.base import completion_messages
from agents.scope import scope_note
from lewis_mcp.client.client import call_tool


REVIEW_SYSTEM = """你是Lewis的Review Agent（代码审查工程师）。
职责：审查代码质量、规范性、安全性，给出改进建议。
以本次读取的实际文件为准，结合原需求、本轮增量需求及实际测试结果判断；stale 标记的旧测试不能证明当前代码通过。
记录本次审查时观察到的问题，不预测后续文档角色已经修复；审查评分不是测试结论。

输出 JSON：
{
  "overall_score": 85,
  "issues": [
    {"severity": "high/medium/low", "file": "文件名", "line": "行号或范围", "issue": "问题描述", "suggestion": "改进建议"}
  ],
  "strengths": ["优点1", "优点2"],
  "summary": "总体评价"
}
"""


async def review_agent_run(task: str, context: dict = None) -> dict:
    code_context = ""
    paths = list((context or {}).get('files', []))
    for role in ('test', 'writer'):
        for item in (context or {}).get(role, {}).get('files', []):
            path = item['path'] if isinstance(item, dict) else item
            if path not in paths:
                paths.append(path)
    if paths:
        for f in paths:
            content = await call_tool("filesystem", "read_file", agent_name="review", path=f)
            code_context += f"\n--- {f} ---\n{content}\n"
    if not code_context:
        raise ValueError("没有实际代码可审查")

    messages = [{"role": "system", "content": REVIEW_SYSTEM + '\n' + scope_note(context, 'review')}]
    if code_context:
        messages.append({"role": "user", "content": f"待审查代码：{code_context}"})
    if context:
        messages.append({"role": "user", "content": f"背景：{json.dumps(context, ensure_ascii=False)}"})
    messages.append({"role": "user", "content": f"Review 任务：{task}"})

    resp = await completion_messages(
        messages=messages,
        json_output=True,
    )
    return resp
