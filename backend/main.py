import asyncio
import json
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from fastapi.responses import FileResponse, HTMLResponse, Response
from research_report import report_markdown, report_html
from memory.sqlite_history import init_db, create_task, get_task_logs, get_task, list_tasks, recover_interrupted_tasks
from artifacts import list_artifacts, artifact_path
from memory.redis_memory import get_redis, close_redis, mark_redis_unavailable, RedisUnavailable
from graph.company_graph import run_task, create_task_id, stop_background_tasks
from revisions import source_files


@asynccontextmanager
async def lifespan(app):
    await init_db()
    await recover_interrupted_tasks()
    try:
        yield
    finally:
        await stop_background_tasks()
        await close_redis()


app = FastAPI(title="Lewis 软件开发协作 API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


async def close_subscription(pubsub):
    if pubsub is not None:
        try:
            await pubsub.aclose()
        except Exception:
            pass  # 清理失败不阻断 SQLite 回放或覆盖原异常


class TaskRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=5000)
    acceptance_profile: Literal['sms-classifier', 'sms-batch'] | None = None
    parent_task_id: str | None = Field(default=None, max_length=36)

    @field_validator("user_input")
    @classmethod
    def non_blank(cls, value):
        if not value.strip():
            raise ValueError("请填写软件开发需求")
        return value.strip()


@app.post("/api/task")
async def submit_task(req: TaskRequest):
    if req.parent_task_id:
        parent = await task_detail(req.parent_task_id)
        if parent['status'] not in ('completed', 'partial', 'failed'):
            raise HTTPException(409, '父任务尚未结束')
        try:
            await asyncio.to_thread(source_files, req.parent_task_id)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(422, str(exc))
    task_id = create_task_id()
    await create_task(task_id, req.user_input, acceptance_profile=req.acceptance_profile)
    if req.parent_task_id:
        from memory.sqlite_history import update_task
        await update_task(task_id, 'queued', snapshot={"parent_task_id": req.parent_task_id, "execution_type": "revision",
                          "acceptance_profile": req.acceptance_profile})
        run_task(task_id, req.user_input, acceptance_profile=req.acceptance_profile, parent_task_id=req.parent_task_id)
    elif req.acceptance_profile:
        run_task(task_id, req.user_input, acceptance_profile=req.acceptance_profile)
    else:
        run_task(task_id, req.user_input)
    return {"task_id": task_id}


@app.get("/api/task/{task_id}")
async def task_detail(task_id: str):
    task = await get_task(task_id)
    if task is None:
        raise HTTPException(404, "任务不存在")
    return task


@app.get("/api/tasks")
async def task_list(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), status: str | None = None):
    if status is not None and status not in ("queued", "running", "completed", "partial", "failed"):
        raise HTTPException(422, "任务状态无效")
    return await list_tasks(page, page_size, status)


@app.get('/api/demo/sms/model-research')
async def sms_model_research():
    from pathlib import Path
    report = Path(__file__).resolve().parents[1] / 'demo/sms-classifier/chinese/research.html'
    if not report.is_file():
        raise HTTPException(404, '模型对比补充调研尚未生成')
    return HTMLResponse(report.read_text(encoding='utf-8'))


@app.get('/api/task/{task_id}/research-report')
async def research_report(task_id: str, download: bool = False):
    task = await task_detail(task_id)
    markdown = report_markdown(task)
    if markdown is None:
        raise HTTPException(404, '该任务尚无调研记录')
    if download:
        return Response(markdown, media_type='text/markdown; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename=research-report.md'})
    return HTMLResponse(report_html(markdown), headers={
        'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'self'"})


@app.get("/api/task/{task_id}/lineage")
async def task_lineage(task_id: str):
    task = await task_detail(task_id)
    chain, seen = [], set()
    while task and task["id"] not in seen and len(chain) < 20:
        seen.add(task["id"])
        snapshot = task.get("snapshot") or {}
        test = snapshot.get("agent_results", {}).get("test", {}).get("execution") or {}
        acceptance = snapshot.get("acceptance") or {}
        chain.append({"id": task["id"], "status": task["status"],
                      "created_at": task["created_at"], "updated_at": task["updated_at"],
                      "execution_type": snapshot.get("execution_type", "generation"),
                      "test": {**{k: test.get(k) for k in ("passed", "total", "exit_code")},
                               "stale": bool(snapshot.get('agent_results', {}).get('test', {}).get('stale'))},
                      "acceptance": {k: acceptance.get(k) for k in ("verification", "passed", "total", "stale")}})
        parent = snapshot.get("parent_task_id")
        if not parent:
            return {"items": list(reversed(chain)), "incomplete": False}
        task = await get_task(parent)
    return {"items": list(reversed(chain)), "incomplete": True}


@app.get("/api/task/{task_id}/artifacts")
async def task_artifacts(task_id: str):
    await task_detail(task_id)
    try:
        return {"files": await asyncio.to_thread(list_artifacts, task_id)}
    except ValueError:
        return {"files": []}  # 旧任务没有独立 UUID 产物目录


@app.get("/api/task/{task_id}/artifact")
async def read_artifact(task_id: str, path: str, download: bool = False):
    await task_detail(task_id)
    try:
        file = artifact_path(task_id, path)
        if download:
            return FileResponse(file, filename=file.name, media_type="application/octet-stream")
        return {"path": path, "content": await asyncio.to_thread(file.read_text, encoding="utf-8")}
    except FileNotFoundError:
        raise HTTPException(404, "产物不存在")
    except (ValueError, UnicodeError):
        raise HTTPException(400, "产物路径或文本格式无效")


@app.get("/api/task/{task_id}/logs")
async def get_logs(task_id: str, after_id: int = Query(default=0, ge=0)):
    if await get_task(task_id) is None:
        raise HTTPException(404, "任务不存在")
    return {"logs": await get_task_logs(task_id, after_id)}


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str, after_id: int = 0):
    if after_id < 0 or await get_task(task_id) is None:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    pubsub = None
    try:
        try:
            r = await get_redis()
            pubsub = r.pubsub()
            await pubsub.subscribe(f"events:{task_id}")
        except Exception as exc:
            if not isinstance(exc, RedisUnavailable):
                mark_redis_unavailable(exc)
            await close_subscription(pubsub)
            pubsub = None
        # Redis 用于唤醒；SQLite 事件 ID 用于排序、去重及补偿迟订阅事件。
        cursor = after_id
        while True:
            events = await get_task_logs(task_id, cursor)
            for index, event in enumerate(events):
                # 交付恢复会在旧终态之后追加事件；回放必须继续到最新终态。
                if event.get("terminal") and index < len(events) - 1:
                    event = {**event, "terminal": False, "historical_terminal": True}
                await websocket.send_json(event)
                cursor = event["id"]
                if event.get("terminal"):
                    return
            task = await get_task(task_id)
            if task["status"] in ("completed", "partial", "failed"):
                # 终态更新和终态事件之间也可能有间隔，补取后再发送快照。
                events = await get_task_logs(task_id, cursor)
                for event in events:
                    await websocket.send_json(event)
                if not any(e.get("terminal") for e in events):
                    await websocket.send_json({"agent": "SYSTEM", "status": "done", "terminal": True,
                                               "task_status": task["status"], "message": task["result"] or "任务已结束"})
                return
            if pubsub is None:
                await asyncio.sleep(0.5)
            else:
                try:
                    await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                except Exception as exc:
                    mark_redis_unavailable(exc)
                    await close_subscription(pubsub)
                    pubsub = None
    except WebSocketDisconnect:
        pass
    finally:
        await close_subscription(pubsub)
        try:
            await websocket.close()
        except RuntimeError:
            pass
