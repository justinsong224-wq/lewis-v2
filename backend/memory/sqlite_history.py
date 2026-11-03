"""SQLite 为任务终态和事件回放提供持久化依据，兼容已有表。"""
import aiosqlite
import json
from datetime import datetime

DB_PATH = "./Lewis.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY, user_input TEXT, status TEXT DEFAULT 'running',
            result TEXT, created_at TEXT, updated_at TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS task_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, agent TEXT,
            message TEXT, created_at TEXT)""")
        additions = {"tasks": {"snapshot": "TEXT"}, "task_logs": {
            "status": "TEXT", "detail": "TEXT", "payload": "TEXT"}}
        for table, columns in additions.items():
            existing = {row[1] for row in await (await db.execute(f"PRAGMA table_info({table})")).fetchall()}
            for name, kind in columns.items():
                if name not in existing:
                    await db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")
        await db.execute("CREATE INDEX IF NOT EXISTS task_logs_task_id ON task_logs(task_id, id)")
        await db.commit()


async def create_task(task_id, user_input, acceptance_profile=None):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO tasks (id,user_input,status,created_at,updated_at,snapshot) VALUES (?,?,?,?,?,?)",
                         (task_id, user_input, "queued", now, now,
                          json.dumps({"acceptance_profile": acceptance_profile}) if acceptance_profile else None))
        await db.commit()


async def update_task(task_id, status, result=None, snapshot=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET status=?,result=COALESCE(?,result),updated_at=?,snapshot=COALESCE(?,snapshot) WHERE id=?",
                         (status, result, datetime.now().isoformat(),
                          json.dumps(snapshot, ensure_ascii=False) if snapshot is not None else None, task_id))
        await db.commit()


async def get_task(task_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))).fetchone()
        if row is None:
            return None
        task = dict(row)
        task["snapshot"] = json.loads(task["snapshot"]) if task["snapshot"] else None
        return task


async def list_tasks(page=1, page_size=20, status=None):
    where = " WHERE status=?" if status else ""
    params = (status,) if status else ()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        total = (await (await db.execute("SELECT COUNT(*) FROM tasks" + where, params)).fetchone())[0]
        rows = await (await db.execute(
            "SELECT id,user_input,status,created_at,updated_at,snapshot FROM tasks"
            + where + " ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",
            (*params, page_size, (page - 1) * page_size))).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        snapshot = json.loads(item.pop('snapshot') or '{}')
        results = snapshot.get('agent_results') or {}
        item.update(
            has_evidence=bool(results or snapshot.get('subtask_results') or snapshot.get('acceptance')),
            execution_type=snapshot.get('execution_type', 'generation'),
            parent_task_id=snapshot.get('parent_task_id'),
            test_verification=results.get('test', {}).get('verification'),
            test_stale=bool(results.get('test', {}).get('stale')),
            acceptance_verification=(snapshot.get('acceptance') or {}).get('verification'),
            acceptance_stale=bool((snapshot.get('acceptance') or {}).get('stale')))
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def recover_interrupted_tasks():
    """单进程启动时将遗留执行记录收尾，保留此前事件和文件。"""
    async with aiosqlite.connect(DB_PATH) as db:
        rows = await (await db.execute("SELECT id,snapshot FROM tasks WHERE status IN ('queued','running')")).fetchall()
        for tid, raw_snapshot in rows:
            message = "执行进程已中断，任务未完成；已保存的过程和产物保留，请重新提交需求。"
            now = datetime.now().isoformat()
            snapshot = json.loads(raw_snapshot or '{}')
            snapshot.update(execution_error=message, delivery_assessment={'status': 'failed', 'reasons': [message]})
            await db.execute("UPDATE tasks SET status='failed',result=?,updated_at=?,snapshot=? WHERE id=?",
                             (message, now, json.dumps(snapshot, ensure_ascii=False), tid))
            await db.execute("INSERT INTO task_logs(task_id,agent,message,created_at,status,detail,payload) VALUES (?,?,?,?,?,?,?)",
                             (tid, "SYSTEM", message, now, "error", message, json.dumps({"terminal": True, "task_status": "failed"})))
        await db.commit()
    return len(rows)


async def add_log(task_id, agent, message, status=None, detail=None, payload=None):
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO task_logs (task_id,agent,message,created_at,status,detail,payload) VALUES (?,?,?,?,?,?,?)",
                                  (task_id, agent, message, now, status, detail or message,
                                   json.dumps(payload or {}, ensure_ascii=False)))
        await db.commit()
        event_id = cursor.lastrowid
    return {**(payload or {}), "id": event_id, "task_id": task_id, "agent": agent,
            "message": message, "detail": detail or message, "status": status, "created_at": now}


async def get_task_logs(task_id, after_id=0):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id,agent,message,created_at,status,detail,payload FROM task_logs WHERE task_id=? AND id>? ORDER BY id",
                              (task_id, after_id)) as cursor:
            rows = await cursor.fetchall()
    return [{**json.loads(r[6] or "{}"), "id": r[0], "task_id": task_id, "agent": r[1], "message": r[2],
             "created_at": r[3], "status": r[4], "detail": r[5] or r[2]} for r in rows]
