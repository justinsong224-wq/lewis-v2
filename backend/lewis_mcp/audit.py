"""绑定当前任务的工具调用记录；不记录文件正文和凭据。"""
from contextvars import ContextVar

event_sink = ContextVar("tool_event_sink", default=None)
subtask_id = ContextVar("tool_subtask_id", default=None)


def summarize(arguments):
    result = {}
    for key, value in arguments.items():
        lowered = key.lower()
        if any(word in lowered for word in ("key", "token", "password", "secret", "authorization")):
            result[key] = "[已隐藏]"
        elif key == "content":
            result[key] = {"characters": len(str(value))}
        else:
            result[key] = str(value)[:300]
    return result
