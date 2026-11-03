"""
Writer Agent
负责报告撰写、文档生成
MCP: filesystem
"""
import json
from agents.file_output import generate_files
from agents.scope import scope_note
from agents.base import llm_text
from lewis_mcp.client.client import call_tool


WRITER_SYSTEM = """你是Lewis的Writer Agent（技术写作专员）。
职责：根据各 Agent 的输出，撰写完整的报告、文档或交付物。
面向软件交付，必须包含启动方法、接口示例、实际测试结果与已知限制。
区分生成、执行、未验证；不得将失败或未执行描述为通过。
revision 存在时区分原功能和本轮变更。stale 标记的测试或审查不是当前代码的有效证据。
固定验收若尚无结果则明确尚未执行，不预先声明通过。

使用文件块协议，只返回 README.md 或其他 Markdown 说明文件，禁止返回源代码或测试文件。
"""


async def writer_agent_run(task: str, context: dict = None) -> dict:
    prompt = f"写作任务：{task}"
    if context:
        documents = []
        for path in context.get('files', []):
            if path.lower().endswith('.md'):
                documents.append({'path': path, 'content': await call_tool(
                    'filesystem', 'read_file', agent_name='writer', path=path)})
        context = {**context, 'actual_documents': documents}
        prompt += f"\n参考资料：{json.dumps(context, ensure_ascii=False)}"
    if (context or {}).get('acceptance_profile') in ('sms-classifier', 'sms-batch'):
        # 单一说明文件无需多文件封装协议，Markdown 围栏属于文档合法内容。
        system = WRITER_SYSTEM.replace(
            '使用文件块协议，只返回 README.md 或其他 Markdown 说明文件，禁止返回源代码或测试文件。',
            '只返回 README.md 的 Markdown 正文，不使用文件块标记，不在全文外再包一层围栏。')
        content = await llm_text(system + '\n' + scope_note(context, 'writer'), prompt)
        if not content.strip():
            raise ValueError('文档正文为空')
        result = {'files': [{'path': 'README.md', 'content': content}], 'summary': '生成 README.md 说明'}
    else:
        result = await generate_files(WRITER_SYSTEM + '\n' + scope_note(context, 'writer'), prompt, documents_only=True)

    # 保存文档到 workspace
    for item in result["files"]:
        if not item["path"].endswith(".md"):
            raise ValueError("文档角色仅可输出 Markdown 文件")
    for item in result["files"]:
        await call_tool("filesystem", "write_file",
                        agent_name="writer",
                        path=item["path"],
                        content=item["content"])

    return result
