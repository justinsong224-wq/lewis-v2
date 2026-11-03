// 修复任务继承原方案作为背景，本轮步骤取实际保存的子任务结果。
export function executionTasks(snapshot) {
  if (!snapshot) return []
  if (snapshot.execution_type === 'repair') {
    return Object.entries(snapshot.subtask_results || {}).map(([id, result]) => ({
      id, agent: result.agent || id.replace(/^repair-/, ''),
      task: result.error || result.summary || '本轮修复阶段，详见执行日志', depends_on: null,
    }))
  }
  const plan = snapshot.plan
  return (plan?.execution_order || []).map(id => plan.subtasks?.find(task => task.id === id)).filter(Boolean)
}
