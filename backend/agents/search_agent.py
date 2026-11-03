"""
Search Agent
使用 MCP search server 执行网络搜索，汇总信息返回给 CEO/其他 Agent
"""
from datetime import datetime
from agents.base import completion_messages
from graph.context import planning_context
from lewis_mcp.client.client import call_tool


SEARCH_SYSTEM = """你是Lewis软件开发公司的技术调研员。
职责：查询影响开发实现或验收的技术问题，优先官方文档，输出来源和可供技术总监采用的建议。
只引用实际搜索结果中的来源，未查证的信息明确标注。
当任务涉及机器学习模型、分类或实验展示时，调研必须覆盖传统 baseline 与目标模型的比较：
数据语言和分词适配、相同训练/验证/测试划分、Accuracy/Precision/Recall/F1、资源开销与适用限制。
没有本地实验时不得编造指标或宣称 Transformer 优于 baseline；外部文献结果和本地实测必须区分。

输出格式（JSON）：
{
  "query": "实际搜索的关键词",
  "summary": "综合搜索结果的摘要（200字以内）",
  "key_points": ["要点1", "要点2", "要点3"],
  "sources": ["链接1", "链接2"]
}
"""


async def search_agent_run(task: str, context: dict = None) -> dict:
    """
    1. LLM 决定搜索关键词
    2. 调用 MCP search 工具执行搜索
    3. LLM 整理结果输出结构化报告
    """
    import json

    today_str = datetime.now().strftime("%Y年%m月%d日")

    # Step 1: 让 LLM 生成搜索关键词（注入当前日期，避免"今天/昨天/最近"等相对时间被误解）
    kw_resp = await completion_messages(
        messages=[
            {"role": "system", "content": (
                f"今天是 {today_str}。你是搜索关键词生成助手，根据任务提炼1-3个最佳搜索关键词。"
                "如果任务中包含相对时间表述（如'今天''昨天''最近''上个月'），请基于上面给出的当前日期换算成具体日期或年份后再生成关键词。"
                "直接输出关键词，用逗号分隔，不要其他内容。"
                "涉及模型分类或实验展示时，必须包含 baseline 与目标模型比较、数据语言适配和公平评估的关键词。"
            )},
            {"role": "user", "content": f"任务：{task}"},
        ],
    )
    keywords = kw_resp

    # Step 2: 调用 MCP 工具搜索
    search_results = await call_tool("search", "web_search", agent_name="search", query=keywords, num_results=5)

    # Step 3: LLM 整理结果
    messages = [{"role": "system", "content": SEARCH_SYSTEM}]
    if context:
        messages.append({"role": "user", "content": f"背景：{json.dumps(planning_context(context), ensure_ascii=False)}"})
    messages.append({"role": "user", "content": f"任务：{task}\n\n搜索结果：\n{search_results}"})

    final_resp = await completion_messages(
        messages=messages,
        json_output=True,
    )
    result = final_resp
    return {**result, "query": keywords, "raw_search_results": search_results}
