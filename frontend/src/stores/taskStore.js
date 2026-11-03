import { defineStore } from 'pinia'
import { executionTasks } from '../taskPresentation.js'

const API_BASE = ''
const terminalStatuses = ['completed', 'partial', 'failed']

// 内部角色 ID 与后端保持一致，界面使用软件开发职责名称。
export const AGENTS = [
    { id: 'pm', label: '项目经理', dept: '需求管理' },
    { id: 'search', label: '技术调研员', dept: '技术支持' },
    { id: 'ceo', label: '技术总监', dept: '技术规划' },
    { id: 'dev', label: '开发工程师', dept: '开发团队' },
    { id: 'test', label: '测试工程师', dept: '开发团队' },
    { id: 'devops', label: '运维工程师', dept: '开发团队' },
    { id: 'review', label: '代码审查员', dept: '开发团队' },
    { id: 'analyst', label: '数据分析员', dept: '技术支持' },
    { id: 'writer', label: '文档工程师', dept: '交付团队' },
    { id: 'customer', label: '交付专员', dept: '交付团队' },
]

export const useTaskStore = defineStore('task', {
    state: () => ({
        taskId: null,
        userInput: '',
        submitting: false,
        loading: false,
        selectionVersion: 0,
        finished: false,
        finalOutput: '',
        taskStatus: null,
        executionOrder: [],
        subtaskStates: {},
        acceptanceState: null,
        error: '',
        snapshot: null,
        artifacts: [],
        // agentId -> { status: 'idle'|'working'|'done'|'error'|'skipped', message: string }
        agentStates: Object.fromEntries(AGENTS.map(a => [a.id, { status: 'idle', message: '' }])),
        logs: [], // { agent, status, message, created_at }
        ws: null,
    }),

    actions: {
        resetAgents() {
            this.selectionVersion++
            this.loading = false
            if (this.ws) {
                this.ws.close()
                this.ws = null
            }
            this.taskId = null
            this.userInput = ''
            this.taskStatus = null
            this.executionOrder = []
            this.subtaskStates = {}
            this.acceptanceState = null
            this.error = ''
            this.snapshot = null
            this.artifacts = []
            for (const a of AGENTS) {
                this.agentStates[a.id] = { status: 'idle', message: '' }
            }
            this.logs = []
            this.finished = false
            this.finalOutput = ''
        },

        async submitTask(userInput, acceptanceProfile = null, parentTaskId = null) {
            if (this.submitting) return
            this.resetAgents()
            const version = this.selectionVersion
            this.userInput = userInput
            this.submitting = true
            try {
                const resp = await fetch(`${API_BASE}/api/task`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_input: userInput, acceptance_profile: acceptanceProfile, parent_task_id: parentTaskId }),
                })
                const data = await resp.json()
                if (!resp.ok || !data.task_id) {
                    throw new Error(typeof data.detail === 'string' ? data.detail : '提交失败，请检查开发需求或服务状态')
                }
                if (version !== this.selectionVersion) return data.task_id
                this.taskId = data.task_id
                window.location.hash = `task=${data.task_id}`
                this.taskStatus = 'queued'
                this.snapshot = { acceptance_profile: acceptanceProfile,
                    ...(parentTaskId ? { parent_task_id: parentTaskId, execution_type: 'revision' } : {}) }
                if (acceptanceProfile) this.acceptanceState = { status: 'idle' }
                this.connectWebSocket(data.task_id)
                return data.task_id
            } catch (e) {
                if (version === this.selectionVersion) this.error = e.message
                throw e
            } finally {
                this.submitting = false
            }
        },

        connectWebSocket(taskId) {
            if (this.taskId !== taskId || this.finished) return
            if (this.ws) {
                this.ws.close()
            }
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
            const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/${taskId}`)

            ws.onmessage = (event) => {
                if (this.taskId !== taskId || this.ws !== ws) return
                try {
                    this.handleEvent(JSON.parse(event.data))
                } catch {
                    this.error = '收到无法解析的进度消息，可重新连接恢复任务记录'
                }
            }
            ws.onerror = () => {
                if (this.taskId !== taskId || this.ws !== ws) return
                this.logs.push({
                    agent: 'SYSTEM',
                    status: 'error',
                    message: 'WebSocket 连接出错，请确认后端服务正在运行',
                    created_at: new Date().toISOString(),
                })
            }
            ws.onclose = () => {
                if (this.ws !== ws) return
                this.ws = null
                if (this.taskId === taskId && this.finished) {
                    this.loadEvidence(taskId).catch(e => { if (this.taskId === taskId) this.error = e.message })
                }
                if (this.taskId === taskId && !this.finished) {
                    this.recoverTask(taskId).catch(() => {
                        if (this.taskId === taskId) this.error = '连接中断，暂时无法获取任务状态'
                    })
                }
            }
            this.ws = ws
        },

        async loadTask(taskId) {
            if (this.submitting) return
            this.resetAgents()
            const version = this.selectionVersion
            this.loading = true
            this.taskId = taskId
            window.location.hash = `task=${taskId}`
            try {
                await this.recoverTask(taskId)
                if (version === this.selectionVersion && !this.finished) this.connectWebSocket(taskId)
            } catch (e) {
                if (version === this.selectionVersion) this.error = e.message
            } finally {
                if (version === this.selectionVersion) this.loading = false
            }
        },

        async loadEvidence(taskId) {
            const version = this.selectionVersion
            const [taskResp, filesResp] = await Promise.all([
                fetch(`${API_BASE}/api/task/${taskId}`),
                fetch(`${API_BASE}/api/task/${taskId}/artifacts`),
            ])
            if (!taskResp.ok || !filesResp.ok) throw new Error('获取交付证据失败')
            const task = await taskResp.json()
            const files = await filesResp.json()
            if (this.taskId !== taskId || version !== this.selectionVersion) return
            this.snapshot = task.snapshot
            this.artifacts = files.files || []
            this.userInput = task.user_input
            this.applyTaskStatus(task)
            this.executionOrder = executionTasks(task.snapshot)
            for (const [id, result] of Object.entries(task.snapshot?.subtask_results || {})) {
                this.subtaskStates[id] = { status: result.status, stale: result.stale, message: result.error || result.summary || '' }
            }
            for (const [role, result] of Object.entries(task.snapshot?.agent_results || {})) {
                if (this.agentStates[role] && !this.agentStates[role].message) {
                    this.agentStates[role] = { status: result.error ? 'error' : result.status || 'done',
                        message: result.error || result.summary || '阶段结果已保存' }
                }
            }
            if (this.finished) {
                for (const state of [...Object.values(this.agentStates), ...Object.values(this.subtaskStates)]) {
                    if (state.status === 'working') state.status = 'interrupted'
                }
            }
            if (task.snapshot?.acceptance) {
                this.acceptanceState = { status: task.snapshot.acceptance.stale ? 'stale' : task.snapshot.acceptance.verification === 'passed' ? 'done' : 'error' }
            } else if (task.snapshot?.acceptance_profile && !this.acceptanceState) {
                this.acceptanceState = { status: 'idle' }
            }
            if (this.finished && this.acceptanceState?.status === 'working') this.acceptanceState.status = 'interrupted'
            for (const role of ['test', 'review']) {
                if (task.snapshot?.agent_results?.[role]?.stale) this.agentStates[role].status = 'stale'
            }
        },

        handleEvent(data) {
            if (data.task_id && data.task_id !== this.taskId) return
            if (data.id && this.logs.some(log => log.id === data.id)) return
            const { agent, status, message, detail } = data
            this.logs.push({ ...data, detail: detail || message, created_at: data.created_at || new Date().toISOString() })
            // 工具调用是过程证据，不覆盖角色执行状态或任务终态。
            if (data.kind === 'tool_call' || data.historical_terminal) return
            if (this.finished && !data.terminal) return
            if (data.plan) this.executionOrder = executionTasks({ plan: data.plan })

            if (data.subtask_id) this.subtaskStates[data.subtask_id] = { status, message }
            if ((agent || '').toLowerCase() === 'acceptance') this.acceptanceState = { status, message }

            const agentId = (agent || '').toLowerCase()
            if (this.agentStates[agentId]) {
                this.agentStates[agentId] = { status: status || 'working', message: message || '' }
            }

            if (data.terminal || (agentId === 'customer' && (status === 'completed' || status === 'error'))) {
                this.finished = true
                this.finalOutput = message
                this.taskStatus = data.task_status || (status === 'completed' ? 'completed' : 'failed')
            } else {
                this.taskStatus = 'running'
            }
        },

        async recoverTask(taskId) {
            const version = this.selectionVersion
            const resp = await fetch(`${API_BASE}/api/task/${taskId}`)
            if (!resp.ok) throw new Error('获取任务状态失败')
            const task = await resp.json()
            const logs = await this.fetchLogs(taskId)
            if (this.taskId !== taskId || version !== this.selectionVersion) return
            for (const log of logs) this.handleEvent(log)
            this.applyTaskStatus(task)
            await this.loadEvidence(taskId)
            if (this.taskId !== taskId || version !== this.selectionVersion) return
            if (!this.finished) {
                this.error = this.ws ? '' : '可重新连接查看任务进度'
            }
        },

        applyTaskStatus(task) {
            // 较早发出的详情请求不能把已收到的终态覆盖回执行中。
            if (this.finished && !terminalStatuses.includes(task.status)) return
            this.taskStatus = task.status
            this.finished = terminalStatuses.includes(task.status)
            if (this.finished) this.finalOutput = task.result || this.finalOutput
        },

        async fetchLogs(taskId) {
            const resp = await fetch(`${API_BASE}/api/task/${taskId}/logs`)
            if (!resp.ok) throw new Error('获取任务日志失败')
            const data = await resp.json()
            return data.logs || []
        },
    },
})
