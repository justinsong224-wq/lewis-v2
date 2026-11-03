"""验证记录绑定实际代码和配置文件版本；Markdown 不属于代码验证范围。"""
import hashlib
from pathlib import Path
from artifacts import list_artifacts, artifact_path


def verification_manifest(task_id):
    return {item['path']: hashlib.sha256(artifact_path(task_id, item['path']).read_bytes()).hexdigest()
            for item in list_artifacts(task_id)
            if not item['path'].startswith('.lewis/') and Path(item['path']).suffix.lower() != '.md'}


def invalidate_changed_evidence(results, subresults, current):
    for role in ('test', 'review'):
        previous = results.get(role)
        if not previous or 'verified_files' not in previous or previous.get('stale'):
            continue
        if previous['verified_files'] != current:
            updated = {**previous, 'stale': True,
                       'evidence_note': '代码、测试或配置文件已变化，此结果仅对应此前文件版本'}
            results[role] = updated
            sid = previous.get('subtask_id')
            if sid in subresults:
                subresults[sid] = updated
