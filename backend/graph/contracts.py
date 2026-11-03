"""软件开发子任务的顺序、依赖和结果契约。"""


def ordered_subtasks(plan: dict) -> list[dict]:
    tasks = plan.get("subtasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("技术计划必须包含非空 subtasks")
    indexed = {}
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("子任务必须是对象")
        for key in ("id", "agent", "task"):
            if not isinstance(task.get(key), str) or not task[key].strip():
                raise ValueError(f"子任务缺少有效字段：{key}")
        if task["id"] in indexed:
            raise ValueError("子任务 ID 不得重复")
        if task["agent"] in ("pm", "search", "ceo", "customer"):
            raise ValueError("需求、调研、技术规划和交付由图节点负责，不得重复派发")
        indexed[task["id"]] = task
    order = plan.get("execution_order")
    if not isinstance(order, list) or any(not isinstance(i, str) for i in order):
        raise ValueError("execution_order 必须为子任务 ID 列表")
    if len(order) != len(indexed) or set(order) != set(indexed):
        raise ValueError("execution_order 必须包含每个子任务且恰好一次")
    seen = set()
    dev_seen = False
    for task_id in order:
        task = indexed[task_id]
        dependencies = task.get("depends_on", [])
        if not isinstance(dependencies, list) or any(not isinstance(d, str) for d in dependencies):
            raise ValueError("depends_on 必须为子任务 ID 列表")
        if any(d not in seen for d in dependencies):
            raise ValueError(f"{task_id} 的依赖尚未执行或不存在")
        if task["agent"] in ("test", "review") and not dev_seen:
            raise ValueError("测试和审查必须在开发之后")
        dev_seen = dev_seen or task["agent"] == "dev"
        seen.add(task_id)
    if not dev_seen or not any(t["agent"] == "test" for t in tasks):
        raise ValueError("软件交付计划必须包含开发和测试")
    return [indexed[i] for i in order]


def artifact_paths(result: dict) -> list[str]:
    paths = []
    for item in result.get("files", []):
        path = item.get("path") if isinstance(item, dict) else item
        if not isinstance(path, str) or not path.strip():
            raise ValueError("文件产物缺少有效 path")
        if path not in paths:
            paths.append(path)
    return paths


def delivery_assessment(results: dict, subresults=None, acceptance_profile=None, acceptance=None) -> dict:
    reasons = []
    if results.get("dev", {}).get("error") or not results.get("dev", {}).get("files"):
        reasons.append('开发未成功生成可交付文件')
    failed_development = bool(reasons)
    for name, result in results.items():
        if result.get('error'):
            reasons.append(f"{name}: {result['error']}")
    for sid, result in (subresults or {}).items():
        if result.get('error'):
            reasons.append(f"子任务 {sid}: {result['error']}")
    test = results.get('test', {})
    execution = test.get('execution') or {}
    if (test.get('verification') != 'passed' or test.get('stale')
            or execution.get('exit_code') != 0 or execution.get('passed', 0) < 1
            or execution.get('failed', 0) or execution.get('errors', 0)):
        reasons.append('缺少针对当前代码的实际测试通过证据')
    if any(i.get("severity") == "high" for i in results.get("review", {}).get("issues", [])):
        reasons.append('代码审查存在高优先级问题')
    if results.get('review', {}).get('stale'):
        reasons.append('代码已在审查后发生开发变更，需要重新审查')
    if acceptance_profile and (not acceptance or acceptance.get('verification') != 'passed' or acceptance.get('stale')):
        reasons.append('已选择的固定业务验收未通过或未执行')
    elif acceptance and (acceptance.get('verification') != 'passed' or acceptance.get('stale')):
        reasons.append('固定业务验收未通过')
    return {'status': 'failed' if failed_development else 'partial' if reasons else 'completed',
            'reasons': list(dict.fromkeys(reasons))}


def delivery_status(results: dict) -> str:
    return delivery_assessment(results)['status']
