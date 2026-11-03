"""只访问任务目录中的文本产物，排除 Git、缓存和符号链接。"""
from pathlib import Path
from lewis_mcp.workspace import workspace_path

HIDDEN = {".git", "__pycache__", ".pytest_cache", "node_modules", ".venv", "venv"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".xml", ".yaml", ".yml", ".js", ".ts", ".html", ".css", ".vue", ".toml", ".ini", ".csv"}


def artifact_path(task_id, relative):
    root = workspace_path(task_id)
    path = Path(relative)
    if path.is_absolute() or not relative or any(p in HIDDEN or p in ("..", ".env") for p in path.parts):
        raise ValueError("产物路径无效")
    candidate = root / path
    if any(p.is_symlink() for p in [candidate, *candidate.parents] if p != root.parent):
        raise ValueError("不允许访问符号链接产物")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise FileNotFoundError(relative)
    if resolved.suffix.lower() not in TEXT_SUFFIXES or resolved.stat().st_size > 1024 * 1024:
        raise ValueError("仅支持不超过 1 MB 的文本产物")
    return resolved


def list_artifacts(task_id):
    root = workspace_path(task_id)
    if not root.is_dir():
        return []
    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        try:
            safe = artifact_path(task_id, relative)
        except (ValueError, FileNotFoundError):
            continue
        files.append({"path": relative, "size": safe.stat().st_size})
    return sorted(files, key=lambda f: f["path"])
