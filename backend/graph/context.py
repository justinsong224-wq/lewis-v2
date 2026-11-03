"""统一角色输入：保留需求和证据摘要，正文由角色读取当前文件。"""


def result_context(result):
    if not isinstance(result, dict):
        return result
    projected = {}
    for key, value in result.items():
        if key in ('raw_search_results', 'write_results', 'commit_status', 'stdout', 'stderr', 'verified_files', 'command_results'):
            continue
        if key == 'config_files':
            projected[key] = [{'path': item['path']} for item in value]
            continue
        if key == 'files':
            projected[key] = [{'path': item['path']} if isinstance(item, dict) else {'path': item}
                              for item in value]
        elif key == 'execution' and isinstance(value, dict):
            projected[key] = {k: v for k, v in value.items() if k not in ('stdout', 'stderr')}
        else:
            projected[key] = value
    return projected


def role_context(state, results=None, subresults=None):
    results = state.get('agent_results', {}) if results is None else results
    revision = state.get('revision') or {}
    return {
        **{role: result_context(result) for role, result in results.items()},
        'user_input': state['user_input'],
        'revision': {key: value for key, value in revision.items() if key != 'baseline'} or None,
        'plan': state.get('ceo_result', {}),
        'subtask_results': {sid: result_context(result) for sid, result in
                            (state.get('subtask_results', {}) if subresults is None else subresults).items()},
        'acceptance_profile': state.get('acceptance_profile'),
        'acceptance': result_context(state.get('acceptance')),
    }


def planning_context(context):
    """需求、调研、规划只接收契约和文件清单，保留原状态不变。"""
    context = context or {}
    return {key: value for key, value in {
        'user_input': context.get('user_input'),
        'revision': context.get('revision'),
        'pm': context.get('pm'),
        'search': context.get('search'),
        'acceptance_profile': context.get('acceptance_profile'),
        'actual_files': [{'path': item['path']} for item in (context.get('actual_files') or [])],
    }.items() if value is not None}
