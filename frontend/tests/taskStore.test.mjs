import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import { useTaskStore } from '../src/stores/taskStore.js'
import { executionTasks } from '../src/taskPresentation.js'

const repaired = { execution_type: 'repair', plan: { execution_order: ['old'], subtasks: [{ id: 'old', agent: 'dev' }] },
  subtask_results: { 'repair-test': { status: 'done', summary: '28/28' }, 'repair-review': { status: 'done' } } }
assert.deepEqual(executionTasks(repaired).map(task => task.id), ['repair-test', 'repair-review'])
assert.equal(executionTasks(repaired)[0].agent, 'test')
assert.deepEqual(executionTasks(null), [])

globalThis.window = { location: { hash: '', protocol: 'http:', host: 'localhost' } }
setActivePinia(createPinia())
const store = useTaskStore()
store.taskId = 'task-a'
store.handleEvent({ id: 1, task_id: 'task-a', agent: 'Dev', status: 'working', message: '生成代码', created_at: '2026-10-14T12:00:00' })
store.handleEvent({ id: 1, task_id: 'task-a', agent: 'Dev', status: 'working', message: '重复事件' })
store.handleEvent({ id: 2, task_id: 'task-b', agent: 'Dev', status: 'error', message: '另一任务' })
assert.equal(store.logs.length, 1)
assert.equal(store.logs[0].created_at, '2026-10-14T12:00:00')
store.handleEvent({ id: 10, task_id: 'task-a', agent: 'Dev', status: 'info', kind: 'tool_call', outcome: 'succeeded' })
assert.equal(store.agentStates.dev.status, 'working')
store.handleEvent({ id: 3, task_id: 'task-a', agent: 'SYSTEM', status: 'error', terminal: true, task_status: 'failed', message: '规划失败' })
assert.equal(store.finished, true)
assert.equal(store.taskStatus, 'failed')
store.handleEvent({ id: 11, task_id: 'task-a', agent: 'Dev', status: 'info', kind: 'tool_call' })
assert.equal(store.taskStatus, 'failed')

store.resetAgents()
store.taskId = 'multi-step'
store.handleEvent({ id: 20, agent: 'Dev', subtask_id: 'dev-1', status: 'done', message: '接口已完成' })
store.handleEvent({ id: 21, agent: 'Dev', subtask_id: 'dev-2', status: 'working', message: '补充说明' })
store.handleEvent({ id: 22, agent: 'Dev', subtask_id: 'dev-2', status: 'info', kind: 'tool_call' })
assert.equal(store.subtaskStates['dev-1'].status, 'done')
assert.equal(store.subtaskStates['dev-2'].status, 'working')
store.handleEvent({ id: 23, agent: 'Acceptance', status: 'working', message: '开始验收' })
assert.equal(store.acceptanceState.status, 'working')
assert.equal(store.finished, false)
store.handleEvent({ id: 24, agent: 'Acceptance', status: 'error', message: '验收失败' })
assert.equal(store.acceptanceState.status, 'error')
assert.equal(store.finished, false)

globalThis.fetch = async url => ({ ok: true, json: async () => {
  if (url.endsWith('/logs')) return { logs: [{ id: 5, agent: 'Customer', status: 'error', terminal: true, task_status: 'partial', message: '部分完成' }] }
  if (url.endsWith('/artifacts')) return { files: [{ path: 'app.py', size: 42 }] }
  return { status: 'partial', result: '部分完成', user_input: '短信需求', snapshot: {
    plan: { execution_order: ['d'], subtasks: [{ id: 'd', agent: 'dev' }] },
    subtask_results: { d: { status: 'done', summary: '已实现接口' } },
    acceptance_profile: 'ticket-query', acceptance: { verification: 'failed' },
  } }
} })
await store.loadTask('history-task')
assert.equal(store.taskStatus, 'partial')
assert.equal(store.userInput, '短信需求')
assert.equal(store.executionOrder[0].agent, 'dev')
assert.equal(store.artifacts[0].path, 'app.py')
assert.equal(window.location.hash, 'task=history-task')
assert.equal(store.subtaskStates.d.status, 'done')
assert.equal(store.acceptanceState.status, 'error')
assert.equal(store.subtaskStates['dev-1'], undefined)
console.log('taskStore: event deduplication, terminal failure and history recovery passed')

let submitted
globalThis.fetch = async (url, options) => {
  submitted = JSON.parse(options.body)
  return { ok: true, json: async () => ({ task_id: 'revision-child' }) }
}
store.connectWebSocket = () => {}
await store.submitTask('增加批量预测', 'sms-batch', 'parent-task')
assert.deepEqual(submitted, { user_input: '增加批量预测', acceptance_profile: 'sms-batch', parent_task_id: 'parent-task' })
assert.equal(store.taskId, 'revision-child')
assert.equal(store.acceptanceState.status, 'idle')
store.handleEvent({ id: 89, task_id: 'revision-child', agent: 'Customer', status: 'error', historical_terminal: true, terminal: false, message: '旧汇总失败' })
assert.equal(store.finished, false)
console.log('taskStore: revision submission preserves parent and acceptance profile passed')

store.handleEvent({ id: 90, task_id: 'revision-child', agent: 'SYSTEM', terminal: true, task_status: 'failed', status: 'error', message: '中断' })
store.handleEvent({ id: 91, task_id: 'revision-child', agent: 'Dev', status: 'working', message: '迟到进度' })
store.applyTaskStatus({ status: 'running' })
assert.equal(store.taskStatus, 'failed')
assert.equal(store.finished, true)

// 旧任务请求晚于新任务返回，不能改变新任务页面。
let releaseOld
globalThis.fetch = async url => {
  if (url === '/api/task/old-task') await new Promise(resolve => { releaseOld = resolve })
  return { ok: true, json: async () => url.endsWith('/logs') ? { logs: [] } : url.endsWith('/artifacts') ? { files: [] } :
    { status: 'completed', user_input: url.includes('old-task') ? 'old' : 'new', result: 'done', snapshot: {} } }
}
const oldLoad = store.loadTask('old-task')
await store.loadTask('new-task')
releaseOld()
await oldLoad
assert.equal(store.taskId, 'new-task')
assert.equal(store.userInput, 'new')
assert.equal(store.loading, false)
console.log('taskStore: terminal protection and out-of-order history requests passed')
