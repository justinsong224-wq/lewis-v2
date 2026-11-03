"""历史产物作为增量开发基线；父任务始终保持原样。"""
import hashlib
import shutil
from artifacts import list_artifacts, artifact_path
from lewis_mcp.workspace import create_workspace


def source_files(task_id):
    files = [item for item in list_artifacts(task_id) if not item['path'].startswith('.lewis/')]
    if not files:
        raise ValueError('父任务没有可复用的文本产物')
    if len(files) > 50 or sum(item['size'] for item in files) > 200_000:
        raise ValueError('当前增量开发支持最多 50 个文件、合计 200 KB 的文本项目')
    return files


def manifest(task_id):
    return {item['path']: hashlib.sha256(artifact_path(task_id, item['path']).read_bytes()).hexdigest()
            for item in list_artifacts(task_id) if not item['path'].startswith('.lewis/')}


def copy_baseline(parent_id, task_id, root=None):
    files = source_files(parent_id)
    root = root if root is not None else create_workspace(task_id)
    for item in files:
        source = artifact_path(parent_id, item['path'])
        target = root / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return files, manifest(task_id)


def changes_since(task_id, baseline):
    current = manifest(task_id)
    return [{'path': path, 'change': 'added' if path not in baseline else 'deleted' if path not in current else 'modified',
             'before_sha256': baseline.get(path), 'after_sha256': current.get(path)}
            for path in sorted(baseline.keys() | current.keys()) if baseline.get(path) != current.get(path)]
