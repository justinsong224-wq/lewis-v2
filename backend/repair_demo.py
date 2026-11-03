"""从失败验证任务创建关联修复任务，复用真实需求/调研/规划，不改写父任务。"""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
from uuid import UUID

from agents.dev_agent import dev_agent_run
from agents.test_agent import test_agent_run
from agents.review_agent import review_agent_run
from agents.writer_agent import writer_agent_run
from artifacts import list_artifacts, artifact_path
from config.settings import settings
from graph import company_graph as workflow
from lewis_mcp.audit import event_sink, subtask_id
from lewis_mcp.client.client import call_tool
from lewis_mcp.workspace import create_workspace, task_workspace
from memory import sqlite_history as history


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent_task")
    parser.add_argument("--tests-only", action="store_true", help="复用父任务应用，仅重做失败测试、审查和说明")
    parser.add_argument('--case', choices=('sms',), default='sms')
    args = parser.parse_args()
    UUID(args.parent_task)
    directory = Path(__file__).resolve().parent / "workspace" / "validation"
    history.DB_PATH = str(directory / "demo-history.db")
    if args.case == 'sms':
        import os
        history.DB_PATH = str(directory / 'sms-history.db')
        os.environ.setdefault('SMS_ASSET_DIR', str(Path(__file__).resolve().parent / 'workspace/assets/sms'))
    await history.init_db()
    parent = await history.get_task(args.parent_task)
    if not parent or parent["status"] not in ("failed", "partial"):
        raise ValueError("只修复已结束的失败或部分完成任务")
    snapshot = parent.get("snapshot") or {}
    profile = snapshot.get('acceptance_profile') or 'sms-classifier'
    if not snapshot.get("plan") or not snapshot.get("acceptance"):
        raise ValueError("父任务缺少规划或固定验收证据")
    tid = workflow.create_task_id()
    root = create_workspace(tid)
    copied = []
    for item in list_artifacts(parent["id"]):
        if item["path"].startswith(".lewis/"):
            continue
        source = artifact_path(parent["id"], item["path"])
        target = root / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append({"path": item["path"]})
    await history.create_task(tid, parent["user_input"], acceptance_profile=profile)
    await history.update_task(tid, "running", snapshot={"parent_task_id": parent["id"], "acceptance_profile": profile})
    print(json.dumps({"task_id": tid, "parent_task_id": parent["id"]}), flush=True)

    async def emit(agent, status, message, **kwargs):
        print(json.dumps({"agent": agent, "status": status, "message": str(message)[:160]}, ensure_ascii=False), flush=True)
        return await workflow._emit(tid, agent, status, message, **kwargs)

    async def tool_event(agent, payload):
        await emit(agent.upper(), "info", payload["server"] + "/" + payload["tool"] + ":" + payload["outcome"], **payload)

    workspace_token, audit_token = task_workspace.set(str(root)), event_sink.set(tool_event)
    results = {k: v for k, v in snapshot["agent_results"].items() if k in ("pm", "search")}
    if args.tests_only:
        results["dev"] = {"files": copied, "summary": "沿用父任务已生成的应用", "status": "done"}
    subtasks = {}
    acceptance = None
    try:
        await emit("SYSTEM", "working", "从父任务复制产物，基于实际失败证据定向修复；沿用父任务需求、调研与规划", parent_task_id=parent["id"])
        await call_tool("git", "git_init", "dev")
        for item in copied:
            await call_tool("git", "git_add", "dev", path=item["path"])
        await call_tool("git", "git_commit", "dev", message="chore: preserve parent artifacts before repair")
        actual = [{"path": f["path"], "content": await call_tool("filesystem", "read_file", "dev", path=f["path"])} for f in copied]
        context = {**results, "user_input": parent["user_input"], "plan": snapshot["plan"],
                   "actual_files": actual, "acceptance_failure": snapshot["acceptance"], "parent_task_id": parent["id"], 'acceptance_profile': profile, "files": [f["path"] for f in copied]}
        repairs = [
            ('repair-dev', 'dev', dev_agent_run, '依据实际失败证据修复短信应用，保留原契约与真实模型，只修改必要文件。'),
            ('repair-test', 'test', test_agent_run, '读取实际应用与失败报告，生成并执行真实模型测试。'),
            ('repair-writer', 'writer', writer_agent_run, '编写简短 README，说明真实资产、接口、启动和本轮验证。'),
            ('repair-review', 'review', review_agent_run, '审查最终应用、测试和文档，如实指出问题。'),
        ]
        if args.tests_only:
            repairs = repairs[1:]
            context["previous_test_failure"] = snapshot["agent_results"].get("test")
            context["previous_review"] = snapshot["agent_results"].get("review")
            if profile in ('sms-classifier', 'sms-batch'):
                repairs = [
                    ('repair-test', 'test', test_agent_run, '根据实际源文件和 previous_test_failure 修正测试，真实调用 Predictor，不伪造分类结果。保留应用不修改。trim 后 5000 字合法，5001 才是 422。若为 CSV：用 csv.writer 构造含逗号/双引号/换行的合法字段，不直接拼接；Node subprocess 显式 encoding="utf-8" 保留 BOM；公式保护校验用 csv.reader 解析后逐字段对比，不把缺少概率字段的字符串与完整 CSV 行比较。保留相关覆盖，不删除失败用例来凑通过。若静态断言 BOM：JS 的反斜杠 uFEFF 转义与实际 BOM 字符均合法，以真实 Blob 下载行为为准；run_batch_inference 接收的是路由已 trim 的 validated 列表，不要求内部重复 trim，端点 trim 行为仍需测试；DOM 统计标签有中文冒号，比较时 strip 尾部冒号，不改页面去迎合测试。只返回严格 test_app.py 文件块，无额外文字。'),
                    ('repair-writer', 'writer', writer_agent_run, '生成简短 README，说明 SMS_ASSET_DIR、运行命令、复用资产、本轮真实测试与未验收事项。不引用继承的旧哈希作为本轮证明，哈希范围仅按真实记录描述。'),
                    ('repair-review', 'review', review_agent_run, '审查实际应用、修正后的测试与最终文档，以本轮结果为准。'),
                ]
        for sid, agent, runner, description in repairs:
            await emit(agent.upper(), "working", description, subtask_id=sid)
            token = subtask_id.set(sid)
            try:
                result = await asyncio.wait_for(runner(description, context=context), settings.agent_timeout_seconds)
                if agent == "dev":
                    files = {f["path"]: f for f in copied}
                    files.update({f["path"]: f for f in result["files"]})
                    result["files"] = list(files.values())
                result["status"] = "error" if result.get("error") else "done"
            except Exception as exc:
                result = {"error": f"{type(exc).__name__}: {exc}", "status": "error"}
            finally:
                subtask_id.reset(token)
            results[agent] = subtasks[sid] = result
            await emit(agent.upper(), result["status"], result.get("error") or result.get("summary") or "执行完成", subtask_id=sid)
            if agent == "dev" and result.get("error"):
                break
            context.update(results)
            context["files"] = workflow.artifact_paths(results.get("dev", {}))
        state = {"task_id": tid, "user_input": parent["user_input"], "ceo_result": snapshot["plan"],
                 "agent_results": results, "subtask_results": subtasks, "acceptance_profile": profile}
        state = await workflow.acceptance_node(state)
        acceptance = state["acceptance"]
        await workflow.customer_node(state)
    except Exception as exc:
        await history.update_task(tid, "failed", f"修复流程失败：{type(exc).__name__}: {exc}")
        await emit("SYSTEM", "error", "修复流程失败", terminal=True, task_status="failed")
    finally:
        event_sink.reset(audit_token)
        task_workspace.reset(workspace_token)
        task = await history.get_task(tid)
        saved = task["snapshot"] or {}
        saved.update(parent_task_id=parent["id"], execution_type="repair", inherited_plan=True)
        await history.update_task(tid, task["status"], snapshot=saved)
        task = await history.get_task(tid)
        (directory / (tid + ".json")).write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"task_id": tid, "status": task["status"], "acceptance": acceptance}, ensure_ascii=False), flush=True)
    return 0 if task["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

