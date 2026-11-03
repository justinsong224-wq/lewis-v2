<template>
  <section v-if="store.taskId" class="evidence">
    <header class="evidence-header"><div><h3>Agent 工作与生成证据</h3>
    <code>{{ store.taskId }}</code></div><span class="record-label">任务交付档案</span></header>
    <AgentWorkSummary v-if="store.snapshot" :snapshot="store.snapshot" :task-id="store.taskId" />
    <details class="technical-details"><summary>查看需求、方案和审查详情</summary>
    <div class="research-entry">
      <div><strong>技术调研报告</strong><p>{{ research ? research.error ? '调研未成功，查看报告了解原因' : '搜索结论、实现建议、参考来源与方案采纳情况' : '调研完成后，可在这里查看报告' }}</p></div>
      <div v-if="research" class="report-actions"><a :href="reportUrl" target="_blank" rel="noopener">查看调研报告 ↗</a><a :href="reportUrl + '?download=true'">下载报告 .md</a></div>
    </div>
    <nav class="section-nav" aria-label="交付内容导航"><button v-for="item in overviewSections" :key="item.key" :aria-pressed="activeSection === item.key" @click="activeSection = item.key">{{ item.label }}</button></nav>
    <div v-if="store.snapshot" class="overview-panel"><TaskOverview :snapshot="store.snapshot" :section="activeSection" /><p v-if="!hasActiveContent" class="empty-hint">当前阶段尚无{{ overviewSections.find(item => item.key === activeSection)?.label }}记录。</p></div>
    </details>
    <details><summary>增量与修复关联证据</summary><TaskLineage :task-id="store.taskId" :finished="store.finished" /></details>
    <details><summary>客户开发需求</summary><p>{{ store.userInput }}</p></details>
    <details v-if="toolCalls.length" class="technical-details">
      <summary>MCP 工具调用 · {{ toolCalls.length }} 次</summary>
      <article v-for="call in toolCalls" :key="call.id" class="tool-call">
        <strong>{{ roleLabel(call.agent) }} · {{ call.server }}/{{ call.tool }}</strong>
        <p>{{ outcomeLabel(call.outcome) }} · {{ call.duration_seconds }} 秒 · {{ call.subtask_id || '流程节点' }}</p>
        <details><summary>参数与结果</summary><pre>{{ JSON.stringify(call.arguments, null, 2) }}
{{ call.error || call.output_summary }}</pre></details>
      </article>
    </details>
    <p v-if="!store.snapshot && store.finished">该任务没有完整结构化交付记录。请根据执行日志判断实际完成情况。</p>
    <template v-if="store.snapshot">
      <details v-if="store.snapshot.delivery_assessment"><summary>系统交付判定</summary>
        <h4>系统交付判定</h4>
        <p>{{ { completed: '完成', partial: '部分完成', failed: '失败' }[store.snapshot.delivery_assessment.status] || store.snapshot.delivery_assessment.status }}</p>
        <ul v-if="store.snapshot.delivery_assessment.reasons?.length"><li v-for="reason in store.snapshot.delivery_assessment.reasons" :key="reason">{{ reason }}</li></ul>
        <p v-else>当前记录满足系统交付条件，具体覆盖范围以实际测试和所选验收为准。</p>
      </details>
      <section v-if="store.snapshot.execution_type === 'revision'">
        <h4>相对父任务的文件变更</h4>
        <p v-if="store.snapshot.changes_error">变更摘要读取失败：{{ store.snapshot.changes_error }}</p>
        <p v-else-if="!store.snapshot.changes">任务完成后生成变更摘要。</p>
        <p v-else-if="!store.snapshot.changes.length">没有检测到文件内容变化。</p>
        <details v-for="file in store.snapshot.changes" :key="file.path">
          <summary>{{ { added: '新增', modified: '修改', deleted: '删除' }[file.change] }} · {{ file.path }}</summary>
          <pre>原 SHA256：{{ file.before_sha256 || '无' }}
现 SHA256：{{ file.after_sha256 || '无' }}</pre>
        </details>
      </section>
      <details>
        <summary>结构化原始记录</summary>
        <details v-for="section in sections" :key="section.name">
          <summary>{{ section.name }}</summary>
          <pre>{{ JSON.stringify(section.data, null, 2) }}</pre>
        </details>
      </details>
      <div v-if="execution" class="test-result">
        <p v-if="store.snapshot.agent_results?.test?.stale">此测试后发生了新的开发，以下是历史结果，不能证明当前代码通过。</p>
        <strong>实际测试：{{ execution.passed }} / {{ execution.total }} 通过</strong>
        <p>退出码：{{ execution.exit_code ?? '未正常退出' }} · 耗时：{{ execution.duration_seconds }} 秒</p>
        <details><summary>测试命令和原始输出</summary><pre>{{ execution.command?.join(' ') }}
{{ execution.stdout }}
{{ execution.stderr }}</pre></details>
      </div>
      <div v-if="store.snapshot.acceptance" class="test-result">
        <strong>独立业务验收：{{ store.snapshot.acceptance.stale ? '需重新验收' : store.snapshot.acceptance.verification === 'passed' ? '通过' : '未通过' }}</strong>
        <p>{{ store.snapshot.acceptance.passed ?? 0 }} / {{ store.snapshot.acceptance.total ?? '未统计' }} 项通过 · 与测试工程师生成的测试分开执行</p>
        <details><summary>验收命令与原始结果</summary><pre>{{ JSON.stringify(store.snapshot.acceptance, null, 2) }}</pre></details>
      </div>
      <p v-else-if="store.snapshot.acceptance_profile">{{ store.finished ? '此任务未完成固定业务验收，请查看流程失败记录。' : '已选择固定业务验收，等待执行结果。' }}</p>
      <p v-else>此任务未选择固定业务验收；测试结果以测试工程师的实际执行记录为准。</p>
    </template>
    <h4>实际文件产物</h4>
    <p v-if="!store.artifacts.length">尚无可访问的文件产物</p>
    <div v-for="file in store.artifacts" :key="file.path" class="file">
      <span>{{ file.path }} · {{ file.size }} 字节</span>
      <button @click="preview(file.path)">查看</button>
      <a :href="artifactUrl(file.path) + '&download=true'">下载</a>
    </div>
    <p v-if="error">{{ error }}</p>
    <details v-if="selected" open><summary>{{ selected }}</summary><pre>{{ content }}</pre></details>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useTaskStore, AGENTS } from '../stores/taskStore'
import TaskOverview from './TaskOverview.vue'
import TaskLineage from './TaskLineage.vue'
import AgentWorkSummary from './AgentWorkSummary.vue'
const store = useTaskStore()
const activeSection = ref('research')
const overviewSections = [{ key: 'requirements', label: '需求与验收条件' }, { key: 'research', label: '技术调研' }, { key: 'plan', label: '方案与执行计划' }, { key: 'review', label: '代码审查' }]
const research = computed(() => store.snapshot?.agent_results?.search)
const reportUrl = computed(() => `/api/task/${encodeURIComponent(store.taskId)}/research-report`)
const hasActiveContent = computed(() => {
  const snapshot = store.snapshot || {}
  return { requirements: snapshot.agent_results?.pm?.prd, research: research.value, plan: snapshot.plan?.technical_plan || snapshot.plan?.subtasks?.length, review: snapshot.agent_results?.review }[activeSection.value]
})
const toolCalls = computed(() => store.logs.filter(log => log.kind === 'tool_call'))
function roleLabel(agent) { return AGENTS.find(a => a.id === agent.toLowerCase())?.label || agent }
function outcomeLabel(outcome) { return { succeeded: '成功', failed: '失败', cancelled: '取消或超时' }[outcome] || outcome }
const selected = ref(''), content = ref(''), error = ref('')
watch(() => store.taskId, () => { selected.value = ''; content.value = ''; error.value = ''; activeSection.value = 'research' })
const sections = computed(() => {
  const snapshot = store.snapshot
  if (!snapshot) return []
  return [
    { name: '需求与验收条件', data: snapshot.agent_results?.pm },
    { name: '技术调研来源', data: snapshot.agent_results?.search },
    { name: '技术方案与依赖计划', data: snapshot.plan },
    { name: '代码审查意见', data: snapshot.agent_results?.review },
    { name: '角色执行结果', data: snapshot.subtask_results },
  ].filter(s => s.data)
})
const execution = computed(() => store.snapshot?.agent_results?.test?.execution)
function artifactUrl(path) { return `/api/task/${store.taskId}/artifact?${new URLSearchParams({ path })}` }
async function preview(path) {
  const taskId = store.taskId
  selected.value = path
  content.value = '读取中…'
  error.value = ''
  try {
    const response = await fetch(artifactUrl(path))
    if (!response.ok) throw new Error('无法读取该文件')
    const data = await response.json()
    if (store.taskId === taskId && selected.value === path) content.value = data.content
  } catch (e) { if (store.taskId === taskId) error.value = e.message }
}
</script>

<style scoped>
.evidence { background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 16px; }
.evidence-header { display: flex; justify-content: space-between; align-items: start; gap: 10px; margin-bottom: 18px; }
.record-label { color: var(--text-secondary); font-size: 11px; white-space: nowrap; }
.research-entry { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; padding: 18px; background: var(--bg-main); border: 1px solid var(--color-accent); border-radius: 10px; margin-bottom: 18px; }
.research-entry strong { color: var(--color-accent); font-size: 17px; }
.research-entry p { color: var(--text-secondary); margin: 6px 0 0; }
.report-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.report-actions a { border-color: var(--color-accent); font-size: 13px; }
.section-nav { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.section-nav button { font-size: 13px; padding: 9px 12px; }
.section-nav button[aria-pressed='true'] { border-color: var(--color-accent); color: var(--color-accent); background: var(--bg-main); }
.overview-panel { border: 1px solid var(--border-subtle); border-radius: 10px; padding: 4px 16px; margin-bottom: 18px; max-height: 520px; overflow: auto; }
.empty-hint { padding: 12px 0; color: var(--text-secondary); }
.technical-details { background: var(--bg-main); padding: 12px; border: 1px solid var(--border-subtle); border-radius: 8px; }
.test-result { padding: 15px; border: 1px solid var(--border-subtle); border-left: 3px solid var(--color-accent); border-radius: 8px; margin: 12px 0; }
h4 { margin-top: 22px; padding-top: 16px; border-top: 1px solid var(--border-subtle); font-size: 15px; }
code { overflow-wrap: anywhere; }
.tool-call { border-left: 2px solid var(--border-subtle); padding: 8px 12px; margin: 8px 0; }
h3 { margin: 0 0 10px; font-size: 15px; }
code { color: var(--text-muted); font-size: 11px; }
details { margin: 10px 0; }
summary { cursor: pointer; color: var(--text-primary); }
pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 400px; overflow: auto; padding: 10px; background: var(--bg-main); font-size: 12px; }
p { white-space: pre-wrap; font-size: 13px; line-height: 1.6; }
.file { display: flex; align-items: center; gap: 12px; margin: 8px 0; font-size: 13px; }
.file span { flex: 1; overflow-wrap: anywhere; }
button, a { color: var(--text-primary); background: transparent; border: 1px solid var(--border-subtle); border-radius: 5px; padding: 5px 8px; cursor: pointer; text-decoration: none; }
</style>
