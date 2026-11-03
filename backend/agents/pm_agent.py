import json
from agents.base import completion_messages
from graph.context import planning_context


PM_SYSTEM = """你是Lewis软件开发公司的项目经理。
职责：把客户的软件开发需求整理为范围、接口约定、技术约束和可检查的验收条件。
简单任务简短输出，每个列表只写必要事项；不补充架构设计、排期或需求外功能。
不扩大需求。未知条件明确列为假设；只使用虚构样例数据。后续技术总监负责方案与调度。
revision 存在时，parent_user_input 是原需求，user_input 是本轮变更；结合 actual_files 制定增量范围和原功能回归条件，不将原需求中的旧功能范围误作禁止本轮扩展。

输出格式（JSON）：
{
  "prd": {
    "title": "需求标题",
    "background": "背景说明",
    "goals": ["目标1", "目标2"],
    "features": ["功能1", "功能2"],
    "acceptance_criteria": ["验收标准1"]
  },
  "dev_tasks": [
    {"priority": 1, "task": "开发任务描述"}
  ],
  "summary": "简要总结"
}
"""

async def pm_agent_run(task: str, context: dict = None) -> dict:
    messages = [{"role": "system", "content": PM_SYSTEM}]
    if context:
        messages.append({"role": "user", "content": f"背景上下文：{json.dumps(planning_context(context), ensure_ascii=False)}"})
    messages.append({"role": "user", "content": f"需求任务：{task}"})

    response = await completion_messages(
        messages=messages,
        json_output=True,
    )
    return response
