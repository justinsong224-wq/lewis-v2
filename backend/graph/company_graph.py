"""软件开发公司：需求 → 技术调研 → 技术规划 → 顺序派发 → 交付。"""
import asyncio
import json
import logging
import uuid
from typing import TypedDict
from langgraph.graph import StateGraph, END

from agents.ceo_agent import ceo_agent_run
from agents.pm_agent import pm_agent_run
from agents.search_agent import search_agent_run
from agents.dev_agent import dev_agent_run
from agents.test_agent import test_agent_run
from agents.devops_agent import devops_agent_run
from agents.review_agent import review_agent_run
from agents.analyst_agent import analyst_agent_run
from agents.writer_agent import writer_agent_run
from agents.customer_agent import customer_agent_run
from graph.contracts import ordered_subtasks, artifact_paths, delivery_assessment
from graph.context import role_context
from graph.evidence import verification_manifest, invalidate_changed_evidence
from lewis_mcp.workspace import create_workspace, task_workspace
from memory.redis_memory import set_task_state, publish_event
from memory.sqlite_history import add_log, update_task
from config.settings import settings
from lewis_mcp.audit import event_sink, subtask_id
from acceptance import run_acceptance
from revisions import copy_baseline, changes_since
from memory.sqlite_history import get_task
from lewis_mcp.client.client import call_tool

logger = logging.getLogger(__name__)


class CompanyState(TypedDict):
    revision: dict
    actual_files: list
    acceptance_profile: str | None
    acceptance: dict | None
    task_id: str
    user_input: str
    ceo_result: dict
    agent_results: dict
    subtask_results: dict
    current_agent: str
    final_output: str


async def _emit(task_id, agent, status, message, detail=None, **extra):
    event = await add_log(task_id, agent, message, status=status, detail=detail or message, payload=extra)
    try:
        await publish_event(task_id, event)
    except Exception as exc:
        logger.warning('实时推送异常（%s），事件已保存 task=%s', type(exc).__name__, task_id)
    return event


def task_snapshot(state):
    snapshot = {"plan": state.get('ceo_result', {}),
                "agent_results": state.get('agent_results', {}),
                "subtask_results": state.get('subtask_results', {}),
                "acceptance_profile": state.get('acceptance_profile'),
                "acceptance": state.get('acceptance'),
                "current_agent": state.get('current_agent')}
    snapshot.update(state.get('revision') or {})
    return snapshot


async def save_checkpoint(state):
    await update_task(state['task_id'], 'running', snapshot=task_snapshot(state))


async def save_execution_failure(task_id, message):
    saved = await get_task(task_id)
    if saved and saved['status'] in ('completed', 'partial', 'failed'):
        logger.warning('执行收尾异常，保留已保存终态 task=%s', task_id)
        return
    snapshot = dict((saved or {}).get('snapshot') or {})
    snapshot['execution_error'] = message
    snapshot['delivery_assessment'] = {'status': 'failed', 'reasons': [message]}
    if snapshot.get('baseline') is not None:
        try:
            snapshot['changes'] = await asyncio.to_thread(changes_since, task_id, snapshot['baseline'])
        except Exception as exc:
            snapshot['changes_error'] = type(exc).__name__
    await update_task(task_id, 'failed', message, snapshot=snapshot)
    await _emit(task_id, 'SYSTEM', 'error', message, terminal=True, task_status='failed')


AGENT_RUNNERS = {
    "dev": dev_agent_run, "test": test_agent_run, "devops": devops_agent_run,
    "review": review_agent_run, "analyst": analyst_agent_run, "writer": writer_agent_run,
}


async def pm_node(state):
    tid = state["task_id"]
    await _emit(tid, "PM", "working", "项目经理正在整理需求与验收条件")
    context = {**role_context(state), 'actual_files': state.get('actual_files', [])}
    result = await asyncio.wait_for(pm_agent_run(state["user_input"], context=context), timeout=settings.agent_timeout_seconds)
    if not result.get("prd", {}).get("acceptance_criteria"):
        raise ValueError("需求分析缺少验收条件")
    await _emit(tid, "PM", "done", result.get("summary", "需求分析完成"),
                detail=json.dumps(result, ensure_ascii=False))
    next_state = {**state, "agent_results": {**state['agent_results'], "pm": result}, "current_agent": "search"}
    await save_checkpoint(next_state)
    return next_state


async def search_node(state):
    tid = state["task_id"]
    await _emit(tid, "Search", "working", "技术调研员正在查询实现依据")
    results = dict(state["agent_results"])
    task = "调研本开发需求中影响实现和验收的技术问题，优先使用官方文档，给出来源与建议：" + state["user_input"]
    try:
        result = await asyncio.wait_for(search_agent_run(task, context=role_context(state, results)), timeout=settings.agent_timeout_seconds)
        results["search"] = result
        await _emit(tid, "Search", "done", result.get("summary", "调研完成"),
                    detail=json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        results["search"] = {"error": f"{type(exc).__name__}: {exc}"}
        await _emit(tid, "Search", "error", f"调研失败：{exc}")
    next_state = {**state, "agent_results": results, "current_agent": "ceo"}
    await save_checkpoint(next_state)
    return next_state


async def ceo_node(state):
    tid = state["task_id"]
    await _emit(tid, "CEO", "working", "技术总监正在制定方案与执行计划")
    context = {**role_context(state), 'actual_files': state.get('actual_files', [])}
    result = await asyncio.wait_for(ceo_agent_run(state["user_input"], tid, context=context), timeout=settings.agent_timeout_seconds)
    tasks = ordered_subtasks(result)
    if state.get('revision') and not any(task['agent'] == 'dev' for task in tasks):
        raise ValueError('增量开发计划必须包含开发任务')
    await _emit(tid, "CEO", "done", f"计划完成，共 {len(tasks)} 个开发子任务",
                detail=json.dumps(result, ensure_ascii=False), plan=result)
    next_state = {**state, "ceo_result": result, "current_agent": tasks[0]["agent"]}
    await save_checkpoint(next_state)
    return next_state


async def dispatch_node(state):
    tid = state["task_id"]
    results = dict(state["agent_results"])
    subresults = dict(state.get("subtask_results", {}))
    for subtask in ordered_subtasks(state["ceo_result"]):
        sid, agent, desc = subtask["id"], subtask["agent"], subtask["task"]
        blocked = any(subresults[d].get("error") for d in subtask.get("depends_on", []))
        if agent in ("test", "review"):
            blocked = blocked or bool(results.get("dev", {}).get("error")) or not results.get("dev", {}).get("files")
        runner = AGENT_RUNNERS.get(agent)
        if blocked or not runner:
            result = {"error": "依赖未成功，已跳过" if blocked else f"未知角色：{agent}",
                      "status": "skipped", "subtask_id": sid}
            results[agent] = subresults[sid] = result
            await _emit(tid, agent.upper(), "skipped", result["error"], subtask_id=sid)
            await save_checkpoint({**state, 'agent_results': results, 'subtask_results': subresults, 'current_agent': agent})
            continue
        await _emit(tid, agent.upper(), "working", desc, subtask_id=sid)
        if agent == 'dev':
            for role in ('test', 'review'):
                if role in results:
                    results[role] = {**results[role], 'stale': True,
                                     'evidence_note': '后续开发已开始，此结果不能证明当前代码通过验证'}
                    previous_sid = results[role].get('subtask_id')
                    if previous_sid in subresults:
                        subresults[previous_sid] = results[role]
            await save_checkpoint({**state, 'agent_results': results, 'subtask_results': subresults, 'current_agent': agent})
        context = {**role_context(state, results, subresults),
                   'files': artifact_paths(results.get('dev', {}))}
        try:
            subtask_token = subtask_id.set(sid)
            if agent == 'dev' and context['files']:
                context['actual_files'] = [{"path": path, "content": await call_tool(
                    'filesystem', 'read_file', 'dev', path=path)} for path in context['files']]
            result = await asyncio.wait_for(runner(desc, context=context), timeout=settings.agent_timeout_seconds)
            if not isinstance(result, dict):
                raise ValueError("角色结果必须是对象")
            if agent == "dev" and not artifact_paths(result):
                raise ValueError("开发未生成文件")
            result = {**result, "subtask_id": sid}
            if agent in ('test', 'review'):
                result['verified_files'] = await asyncio.to_thread(verification_manifest, tid)
            if agent == "dev":
                files_by_path = {f["path"]: f for f in results.get("dev", {}).get("files", [])}
                files_by_path.update({f["path"]: f for f in result.get("files", [])})
                result["files"] = list(files_by_path.values())
            status = "error" if result.get("error") else "done"
            result["status"] = status
            summary = result.get("error") or result.get("summary") or result.get("test_report") or "执行完成"
            results[agent] = subresults[sid] = result
            await _emit(tid, agent.upper(), status, str(summary),
                        detail=json.dumps(result, ensure_ascii=False), subtask_id=sid)
        except Exception as exc:
            result = {"error": f"{type(exc).__name__}: {exc}", "status": "error", "subtask_id": sid}
            results[agent] = subresults[sid] = result
            await _emit(tid, agent.upper(), "error", result["error"], subtask_id=sid)
        finally:
            subtask_id.reset(subtask_token)
        current = await asyncio.to_thread(verification_manifest, tid)
        invalidate_changed_evidence(results, subresults, current)
        await save_checkpoint({**state, 'agent_results': results, 'subtask_results': subresults, 'current_agent': agent})
    return {**state, "agent_results": results, "subtask_results": subresults, "current_agent": "customer"}


async def customer_node(state):
    tid = state["task_id"]
    await _emit(tid, "Customer", "working", "正在汇总实际产物与验证结果")
    current = await asyncio.to_thread(verification_manifest, tid)
    invalidate_changed_evidence(state['agent_results'], state['subtask_results'], current)
    acceptance = state.get("acceptance")
    if acceptance and 'verified_files' in acceptance and acceptance['verified_files'] != current:
        acceptance = {**acceptance, 'stale': True, 'evidence_note': '固定验收后的代码或配置已变化'}
        state = {**state, 'acceptance': acceptance}
    assessment = delivery_assessment(state['agent_results'], state['subtask_results'],
                                     state.get('acceptance_profile'), acceptance)
    status = assessment['status']
    try:
        result = await asyncio.wait_for(customer_agent_run(state["user_input"], context={
            **role_context(state), 'delivery_status': status,
            'delivery_reasons': assessment['reasons']}), timeout=settings.agent_timeout_seconds)
        final = result.get("closing", "交付汇总已生成")
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}
        final = f"交付汇总失败：{exc}"
        status = "failed"
        assessment['reasons'].append('交付汇总生成失败')
    assessment['status'] = status
    if status != "completed":
        failures = assessment['reasons']
        final = f"{'开发交付失败' if status == 'failed' else '部分完成'}\n" + "\n".join(failures) + "\n" + final
    snapshot = {**task_snapshot(state), 'delivery': result, 'delivery_assessment': assessment}
    if state.get('revision'):
        snapshot.update(state['revision'])
        try:
            snapshot['changes'] = changes_since(tid, state['revision']['baseline'])
        except Exception as exc:
            snapshot['changes_error'] = f'{type(exc).__name__}: {exc}'
    await update_task(tid, status, final, snapshot=snapshot)
    try:
        await set_task_state(tid, {"status": status, "final_output": final})
    except Exception as exc:
        logger.warning('缓存终态写入异常（%s），SQLite 终态已保存 task=%s', type(exc).__name__, tid)
    await _emit(tid, "Customer", "completed" if status == "completed" else "error", final,
                terminal=True, task_status=status)
    return {**state, "final_output": final}


async def acceptance_node(state):
    profile = state.get("acceptance_profile")
    if not profile:
        return state
    tid = state["task_id"]
    await _emit(tid, "Acceptance", "working", "正在执行固定业务验收（独立于角色生成测试）")
    try:
        result = await asyncio.to_thread(run_acceptance, tid, profile)
        result['verified_files'] = await asyncio.to_thread(verification_manifest, tid)
    except Exception as exc:
        result = {"verification": "failed", "error": f"{type(exc).__name__}: {exc}"}
    await _emit(tid, "Acceptance", "done" if result.get("verification") == "passed" else "error",
                "固定业务验收：" + result["verification"], detail=json.dumps(result, ensure_ascii=False))
    next_state = {**state, "acceptance": result}
    await save_checkpoint(next_state)
    return next_state


def build_graph():
    graph = StateGraph(CompanyState)
    for name, node in [("pm", pm_node), ("search", search_node), ("ceo", ceo_node),
                       ("dispatch", dispatch_node), ("verify_delivery", acceptance_node), ("customer", customer_node)]:
        graph.add_node(name, node)
    graph.set_entry_point("pm")
    for before, after in [("pm", "search"), ("search", "ceo"), ("ceo", "dispatch"),
                          ("dispatch", "verify_delivery"), ("verify_delivery", "customer"), ("customer", END)]:
        graph.add_edge(before, after)
    return graph.compile()


company_graph = build_graph()


def create_task_id():
    return str(uuid.uuid4())


async def _execute(task_id, user_input, acceptance_profile=None, parent_task_id=None):
    token = None
    async def tool_event(agent, payload):
        message = f"{payload['server']}/{payload['tool']}：{payload['outcome']}"
        await _emit(task_id, agent.upper(), "info", message,
                    detail=json.dumps(payload, ensure_ascii=False), **payload)
    audit_token = event_sink.set(tool_event)
    try:
        workspace = create_workspace(task_id)
        token = task_workspace.set(str(workspace))
        await update_task(task_id, "running")
        try:
            await set_task_state(task_id, {"status": "running", "user_input": user_input})
        except Exception as exc:
            logger.warning('缓存写入异常（%s），使用持久化事件 task=%s', type(exc).__name__, task_id)
        initial = {"task_id": task_id, "user_input": user_input, "ceo_result": {},
                   "acceptance_profile": acceptance_profile, "acceptance": None,
                   "agent_results": {}, "subtask_results": {}, "current_agent": "pm", "final_output": ""}
        if parent_task_id:
            parent = await get_task(parent_task_id)
            if not parent or parent['status'] not in ('completed', 'partial', 'failed'):
                raise ValueError('父任务不可用于增量开发')
            files, baseline = await asyncio.to_thread(copy_baseline, parent_task_id, task_id, workspace)
            initial['revision'] = {"parent_task_id": parent_task_id, "execution_type": "revision",
                                   "parent_user_input": ((parent.get('snapshot') or {}).get('parent_user_input', '') + '\n' + parent['user_input']).strip(), "baseline": baseline}
            initial['agent_results'] = {"dev": {"files": files, "status": "idle", "summary": '父任务产物基线，尚未执行本轮开发'}}
            await save_checkpoint(initial)
            await call_tool('git', 'git_init', 'dev')
            for item in files:
                await call_tool('git', 'git_add', 'dev', path=item['path'])
            await call_tool('git', 'git_commit', 'dev', message='chore: preserve parent project baseline')
            actual = [{"path": f['path'], "content": await call_tool('filesystem', 'read_file', 'dev', path=f['path'])} for f in files]
            initial['actual_files'] = actual
            await _emit(task_id, 'SYSTEM', 'working', '已复制父任务产物并通过 MCP 读取实际文件，开始增量开发', parent_task_id=parent_task_id)
        await company_graph.ainvoke(initial)
    except asyncio.CancelledError:
        saved = await get_task(task_id)
        if saved and saved['status'] in ('queued', 'running'):
            final = '执行进程正在关闭，任务已中断；已保存的阶段记录和产物保留。'
            await save_execution_failure(task_id, final)
        raise
    except Exception as exc:
        final = f"开发流程失败：{type(exc).__name__}: {exc}"
        await save_execution_failure(task_id, final)
    finally:
        event_sink.reset(audit_token)
        if token is not None:
            task_workspace.reset(token)


_background_tasks = set()


async def stop_background_tasks():
    tasks = list(_background_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def _background_finished(task):
    _background_tasks.discard(task)
    if not task.cancelled() and task.exception() is not None:
        logger.error('后台任务收尾失败：%s', type(task.exception()).__name__)


def run_task(task_id: str, user_input: str, acceptance_profile=None, parent_task_id=None):
    """只在任务记录创建完成后启动。"""
    task = asyncio.create_task(_execute(task_id, user_input, acceptance_profile, parent_task_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_finished)
    return task_id
