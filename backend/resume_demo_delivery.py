"""仅重试汇总失败的短信交付，核对既有证据，不重跑开发。"""
import argparse
import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
from memory import sqlite_history as history
from graph.company_graph import customer_node, _emit
from graph.evidence import verification_manifest
from memory.redis_memory import close_redis


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    args = parser.parse_args()
    directory = ROOT / "backend/workspace/validation"
    history.DB_PATH = str(directory / "sms-history.db")
    os.environ.setdefault("SMS_ASSET_DIR", str(ROOT / "backend/workspace/assets/sms"))
    task = await history.get_task(args.task_id)
    if not task or task["status"] != "failed":
        raise ValueError("只恢复汇总失败的已有任务")
    snapshot = task["snapshot"]
    if snapshot.get("delivery_assessment", {}).get("reasons") != ["交付汇总生成失败"]:
        raise ValueError("存在其他未完成事项，不能仅恢复汇总")
    current = verification_manifest(args.task_id)
    # 修复入口的角色记录没有单独 manifest；最终验收保存了全部代码及测试哈希。
    for record in (snapshot["acceptance"],):
        if record.get("stale") or record.get("verified_files") != current:
            raise ValueError("文件版本与保存证据不一致")
    backup = directory / (args.task_id + ".before-delivery-retry.json")
    if not backup.exists():
        backup.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    await _emit(args.task_id, "SYSTEM", "working", "模型配置更换后仅重试交付汇总，开发、测试与审查沿用已核对的证据")
    state = {"task_id": task["id"], "user_input": task["user_input"], "ceo_result": snapshot["plan"],
             "agent_results": snapshot["agent_results"], "subtask_results": snapshot["subtask_results"],
             "acceptance_profile": snapshot["acceptance_profile"], "acceptance": snapshot["acceptance"]}
    try:
        await customer_node(state)
        result = await history.get_task(task["id"])
        saved = result["snapshot"]
        for key in ("parent_task_id", "execution_type", "inherited_plan"):
            if key in snapshot:
                saved[key] = snapshot[key]
        saved["delivery_retry"] = {"previous_status": "failed", "reason": "交付汇总额度耗尽后更换配置重试"}
        await history.update_task(task["id"], result["status"], snapshot=saved)
        result = await history.get_task(task["id"])
        (directory / (task["id"] + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"task_id": task["id"], "status": result["status"]}, ensure_ascii=True))
    finally:
        await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
