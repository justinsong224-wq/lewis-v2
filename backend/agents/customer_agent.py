"""
Customer Agent
负责用户问答、结果交付，是面向用户的最终出口
"""
import json
from agents.base import completion_messages
from agents.scope import scope_note


CUSTOMER_SYSTEM = """你是Lewis的Customer Agent（客户成功专员）。
职责：整合所有 Agent 的工作成果，用清晰友好的语言向用户呈现最终交付物。
你负责软件开发交付。严格遵守 delivery_status 和实际测试 verification 字段。
只有 verification=passed 才能描述测试通过；审查评分不是测试证据。
以 delivery_status 和 delivery_reasons 为系统判定，不能自行升级。stale 标记表示证据已因后续开发失效，不得据此宣称当前代码通过。
revision 存在时分别说明沿用的原功能、本轮变更和验收范围。
审查意见对应审查当时的文件。若 writer 在审查后已生成文档，只能说明“文档已更新，但高优先级审查问题尚未复核”，不得断言当前文档仍缺失，也不能自行宣布问题已关闭。
逐项对应需求验收条件，明确生成产物、未完成项和未验证项。

重要原则：如果输入中某个 Agent 的结果包含 "error" 字段，必须如实告知用户该部分未完成或失败，
绝不能编造"已完成""可用""通过测试"等结论。如果代码开发（dev）失败，
不要声称 API/功能已经可用，应明确说明开发未成功，建议下一步如何处理。

输出 JSON：
{
  "greeting": "开场白",
  "deliverables": [
    {"type": "document/code/report/analysis", "name": "交付物名称", "description": "内容简介"}
  ],
  "failures": ["如有失败的环节，列出（如：'Dev Agent 执行失败，未生成代码'）"],
  "next_steps": ["建议后续步骤1", "建议后续步骤2"],
  "closing": "结束语（如有失败，应诚实反映，不夸大完成度）"
}
"""


async def customer_agent_run(task: str, context: dict = None) -> dict:
    messages = [{"role": "system", "content": CUSTOMER_SYSTEM + '\n' + scope_note(context, 'customer')}]
    if context:
        messages.append({"role": "user", "content": f"任务完成情况：{json.dumps(context, ensure_ascii=False)}"})
    messages.append({"role": "user", "content": f"用户原始需求：{task}"})

    resp = await completion_messages(
        messages=messages,
        json_output=True,
    )
    return resp
