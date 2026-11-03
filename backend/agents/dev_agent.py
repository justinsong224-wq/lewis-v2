"""
Dev Agent
职责：根据开发任务编写代码，写入文件系统，提交 Git
工具权限：filesystem, git
"""
import json
from agents.file_output import generate_files
from agents.scope import scope_note
from lewis_mcp.client.client import call_tool

DEV_SYSTEM = """你是Lewis的Dev Agent（软件工程师）。
职责：根据任务编写代码，可输出多个文件。
遵循项目经理的验收条件和技术总监方案。文件路径相对任务根目录，不添加 workspace/ 前缀。
context.user_input 是客户原始契约，优先于方案中的缩写或转述。样例字符串、空格、字段名必须逐字保持，不得自行规范化。
Python API 入口固定为 app.py 并导出 app，使用 FastAPI；按需求提供依赖文件和必要数据。
本角色只生成代码，不声称代码已运行或测试通过。
若 context.revision 存在，这是现有项目增量开发：先依据 actual_files 和 parent_user_input 理解原项目，保留原功能，仅输出新增或修改文件的完整内容，不重新创建整套系统。
使用随后给出的文件输出协议，返回完整源文件。
"""


async def dev_agent_run(task: str, context: dict = None) -> dict:
    """
    1. LLM 生成代码（可多文件）
    2. 写入 filesystem
    3. git add + commit
    """
    user_prompt = f"开发任务：{task}"
    if context:
        user_prompt = f"背景：{json.dumps(context, ensure_ascii=False)}\n\n{user_prompt}"

    result = await generate_files(DEV_SYSTEM + '\n' + scope_note(context, 'dev'), user_prompt)
    files = result.get("files", [])
    if not files:
        raise ValueError("开发结果没有文件")

    write_results = []
    for f in files:
        r = await call_tool("filesystem", "write_file", agent_name="dev", path=f["path"], content=f["content"])
        write_results.append(r)

    commit_status = "未提交（无文件变更）"
    if files:
        await call_tool("git", "git_init", agent_name="dev")
        for f in files:
            await call_tool("git", "git_add", agent_name="dev", path=f["path"])
        commit_status = await call_tool(
            "git", "git_commit", agent_name="dev",
            message=result.get("git_message", f"feat: {task[:50]}")
        )

    return {**result, "write_results": write_results, "commit_status": commit_status}
