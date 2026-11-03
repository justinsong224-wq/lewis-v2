"""单独调用真实 Search Agent 补充模型选型调研，不重写旧任务档案。"""
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from agents.search_agent import search_agent_run
from lewis_mcp.audit import event_sink
from research_report import report_markdown, report_html

ROOT = Path(__file__).resolve().parents[1]


async def main():
    destination = ROOT / 'demo/sms-classifier/chinese'
    metrics = json.loads((ROOT / 'backend/workspace/assets/sms/chinese/metrics.json').read_text(encoding='utf-8'))
    events = []
    async def sink(agent, event): events.append(dict(agent=agent, **event))
    token = event_sink.set(sink)
    task = '补充中文短信分类模型选型调研：对比字符 TF-IDF + LogisticRegression baseline 和字符级 Transformer Encoder。优先搜索 scikit-learn.org 官方文本特征、数据泄漏和F1文档，以及 pytorch.org TransformerEncoder 官方文档。调研中文字符适配、相同数据划分、Accuracy/Precision/Recall/F1及开销。不得引用不存在的搜索来源或虚构实验优势。本地实测如下：' + json.dumps({k:v for k,v in metrics.items() if k!='history'}, ensure_ascii=False)
    try:
        result = await search_agent_run(task)
    finally:
        event_sink.reset(token)
    record = dict(id='sms-model-comparison-supplement', user_input=task, created_at=datetime.now(timezone.utc).isoformat(), snapshot=dict(agent_results=dict(search=result)), tool_events=events, scope='本轮补充调研，不属于原始示例生成时的调研')
    destination.mkdir(exist_ok=True)
    (destination/'research.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    markdown = report_markdown(record)
    (destination/'research.md').write_text(markdown,encoding='utf-8')
    (destination/'research.html').write_text(report_html(markdown),encoding='utf-8')
    print('Saved supplementary Search Agent report',flush=True)


if __name__ == '__main__': asyncio.run(main())
