"""每个开发任务拥有自己的产物目录；ContextVar 避免并发任务串目录。"""
import os
from contextvars import ContextVar
from pathlib import Path
from uuid import UUID

task_workspace: ContextVar[str | None] = ContextVar("task_workspace", default=None)


def workspace_path(task_id: str) -> Path:
    UUID(task_id)
    base = Path(os.environ.get("LEWIS_WORKSPACE", Path(__file__).resolve().parents[1] / "workspace"))
    if not base.is_absolute():
        base = Path(__file__).resolve().parents[1] / base
    path = (base / "tasks" / task_id).resolve()
    return path


def create_workspace(task_id: str) -> Path:
    path = workspace_path(task_id)
    path.mkdir(parents=True, exist_ok=False)
    return path
