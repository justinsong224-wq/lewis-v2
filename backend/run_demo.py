"""真实短信流程验证：独立验证数据库，不修改原历史库。"""
import asyncio
import json
from pathlib import Path
import argparse
import sys
import time
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
from graph.company_graph import _execute, create_task_id
from memory import sqlite_history as history
from acceptance import run_acceptance
from memory.redis_memory import close_redis


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance-only", metavar="TASK_ID", help="只验收已有任务，避免重复调用模型")
    parser.add_argument('--parent-task', help='基于已结束的验证任务增量开发')
    parser.add_argument('--case', choices=('sms',), default='sms')
    parser.add_argument('--requirement-file', type=Path, help='使用明确指定的需求文件（验收方案保持对应案例）')
    parser.add_argument('--sms-base', action='store_true', help='短信界面修复仍使用基础版验收')
    args = parser.parse_args()
    evidence = ROOT / "backend" / "workspace" / "validation"
    evidence.mkdir(parents=True, exist_ok=True)
    history.DB_PATH = str(evidence / "demo-history.db")
    if args.case == 'sms':
        import os
        os.environ.setdefault('SMS_ASSET_DIR', str(ROOT / 'backend/workspace/assets/sms'))
        history.DB_PATH = str(evidence / 'sms-history.db')
    await history.init_db()
    if args.acceptance_only:
        task = await history.get_task(args.acceptance_only)
        if not task:
            raise ValueError("验证数据库中不存在该任务")
        result = await asyncio.to_thread(run_acceptance, args.acceptance_only,
                                         (task['snapshot'] or {}).get('acceptance_profile') or 'sms-classifier')
        snapshot = task["snapshot"] or {}
        snapshot["acceptance"] = result
        status = "partial" if task["status"] == "completed" and result["verification"] != "passed" else task["status"]
        await history.update_task(task["id"], status, snapshot=snapshot)
        print(json.dumps(result, ensure_ascii=True), flush=True)
        return 0 if result["verification"] == "passed" else 1
    if args.parent_task:
        from revisions import source_files
        parent = await history.get_task(args.parent_task)
        if not parent or parent["status"] not in ("completed", "partial", "failed"):
            raise ValueError("父任务不存在或尚未结束")
        source_files(args.parent_task)
    tid = create_task_id()
    if args.case == 'sms':
        if args.parent_task and (parent['snapshot'] or {}).get('acceptance_profile') not in ('sms-classifier', 'sms-batch'):
            raise ValueError('短信增量必须基于短信任务')
        requirement = (ROOT / 'demo/sms-classifier' / ('batch-requirement.md' if args.parent_task else 'requirement.md')).read_text(encoding='utf-8')
        profile = 'sms-batch' if args.parent_task else 'sms-classifier'
    if args.requirement_file:
        requirement = args.requirement_file.read_text(encoding='utf-8')
    if args.sms_base:
        if args.case != 'sms':
            raise ValueError('--sms-base 仅用于短信案例')
        profile = 'sms-classifier'
    await history.create_task(tid, requirement, acceptance_profile=profile)
    if args.parent_task:
        await history.update_task(tid, 'queued', snapshot={'parent_task_id': args.parent_task,
            'execution_type': 'revision', 'acceptance_profile': profile})
    print(json.dumps({"task_id": tid, "database": history.DB_PATH}), flush=True)
    start = time.monotonic()
    execution = asyncio.create_task(_execute(tid, requirement, acceptance_profile=profile, parent_task_id=args.parent_task))
    cursor = 0
    while not execution.done():
        for event in await history.get_task_logs(tid, cursor):
            cursor = event["id"]
            print(json.dumps({"agent": event["agent"], "status": event["status"],
                              "message": event["message"][:180]}, ensure_ascii=True), flush=True)
        await asyncio.sleep(1)
    await execution
    task = await history.get_task(tid)
    (evidence / f"{tid}.json").write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"task_id": tid, "status": task["status"], 'duration_seconds': round(time.monotonic() - start, 1), "result": task["result"]}, ensure_ascii=True), flush=True)
    return 0 if task["status"] == "completed" else 1


async def entrypoint():
    try:
        return await main()
    finally:
        await close_redis()


if __name__ == "__main__":
    sys.exit(asyncio.run(entrypoint()))
