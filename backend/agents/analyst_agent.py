"""
Analyst Agent
负责数据分析、图表建议
MCP: database
"""
import json
from agents.base import completion_messages
from lewis_mcp.client.client import call_tool


ANALYST_SYSTEM = """你是Lewis的Analyst Agent（数据分析师）。
职责：查询数据库、分析数据规律、生成分析报告和图表建议。

输出 JSON：
{
  "queries_executed": ["执行的SQL1"],
  "findings": ["发现1", "发现2"],
  "chart_suggestions": [
    {"type": "bar/line/pie", "title": "图表标题", "x": "x轴字段", "y": "y轴字段"}
  ],
  "report": "数据分析报告正文"
}
"""


async def analyst_agent_run(task: str, context: dict = None) -> dict:
    # 如果指定了数据库，先获取表结构
    db_context = ""
    if context and context.get("db_name"):
        db_name = context["db_name"]
        tables = await call_tool("database", "list_tables", agent_name="analyst", db_name=db_name)
        db_context = f"数据库：{db_name}\n表列表：\n{tables}"

    messages = [{"role": "system", "content": ANALYST_SYSTEM}]
    if db_context:
        messages.append({"role": "user", "content": db_context})
    if context:
        messages.append({"role": "user", "content": f"背景：{json.dumps(context, ensure_ascii=False)}"})
    messages.append({"role": "user", "content": f"分析任务：{task}"})

    resp = await completion_messages(
        messages=messages,
        json_output=True,
    )
    result = resp

    # 执行 LLM 建议的查询
    if context and context.get("db_name") and result.get("queries_executed"):
        query_results = []
        for sql in result["queries_executed"]:
            out = await call_tool("database", "query", agent_name="analyst", db_name=context["db_name"], sql=sql)
            query_results.append({"sql": sql, "result": out})
        result["query_results"] = query_results

    return result