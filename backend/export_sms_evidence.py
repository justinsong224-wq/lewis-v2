"""只读导出短信案例事件，便于答辩核对生成来源。"""
import json
from pathlib import Path
import sqlite3
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]


def main():
    case = json.loads((ROOT / "demo/sms-classifier/case.json").read_text(encoding="utf-8"))
    database = ROOT / "backend/workspace/validation/sms-history.db"
    destination = database.parent / "sms-evidence"
    destination.mkdir(exist_ok=True)
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        pending = [value for value in case.values() if value]
        seen = set()
        while pending:
            task_id = pending.pop()
            if task_id in seen:
                continue
            seen.add(task_id)
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise ValueError("案例任务不存在：" + task_id)
            task = dict(row)
            task["snapshot"] = json.loads(task["snapshot"] or "{}")
            parent = task["snapshot"].get("parent_task_id")
            if parent:
                pending.append(parent)
            logs = []
            for event in db.execute("SELECT * FROM task_logs WHERE task_id=? ORDER BY id", (task_id,)):
                item = dict(event)
                for field in ("payload", "detail"):
                    if item.get(field):
                        try:
                            item[field] = json.loads(item[field])
                        except (ValueError, TypeError):
                            pass
                logs.append(item)
            target = destination / (task_id + ".json")
            target.write_text(json.dumps({"task": task, "logs": logs}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(str(target))


if __name__ == "__main__":
    main()
