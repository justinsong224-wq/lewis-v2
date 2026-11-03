<template>
  <div class="overview">
    <section v-if="prd && visible('requirements')">
      <h4>{{ prd.title || '需求与验收条件' }}</h4>
      <p v-if="prd.background">{{ prd.background }}</p>
      <template v-for="group in requirementGroups" :key="group.key">
        <template v-if="Array.isArray(prd[group.key]) && prd[group.key].length">
          <h5>{{ group.label }}</h5>
          <ul><li v-for="(item, index) in prd[group.key]" :key="index">{{ describe(item) }}</li></ul>
        </template>
      </template>
    </section>
    <section v-if="research && visible('research')">
      <h4>技术调研依据</h4>
      <p>{{ research.error || research.summary || '查看原始记录了解调研结果' }}</p>
      <ul v-if="Array.isArray(research.key_points)"><li v-for="(point, index) in research.key_points" :key="index">{{ describe(point) }}</li></ul>
      <ul v-if="Array.isArray(research.sources)">
        <li v-for="(source, index) in research.sources" :key="index">
          <a v-if="sourceUrl(source)" :href="sourceUrl(source)" target="_blank" rel="noopener noreferrer">{{ describe(source) }}</a>
          <span v-else>{{ describe(source) }}</span>
        </li>
      </ul>
    </section>
    <section v-if="visible('plan') && (plan?.technical_plan || tasks.length)">
      <h4>{{ snapshot.execution_type === 'repair' ? '继承方案与本轮修复阶段' : '技术方案与执行计划' }}</h4>
      <p v-if="snapshot.execution_type === 'repair'">需求、调研与技术方案沿用父任务；下表仅展示本轮实际执行的阶段，未重新进行原计划中的全部任务。</p>
      <p v-if="plan?.analysis">{{ plan.analysis }}</p>
      <p v-if="plan?.technical_plan">{{ describe(plan.technical_plan) }}</p>
      <ul v-if="Array.isArray(plan?.research_decisions)">
        <li v-for="(decision, index) in plan.research_decisions" :key="index">
          {{ decision.adopted ? '采纳' : '未采纳' }}：{{ decision.source }} — {{ decision.reason }}
        </li>
      </ul>
      <div v-if="tasks.length" class="table-wrap">
        <table>
          <thead><tr><th>顺序 / 子任务</th><th>职责与任务</th><th>前置任务</th><th>执行结果</th></tr></thead>
          <tbody><tr v-for="(task, index) in tasks" :key="task.id">
            <td>{{ index + 1 }} · {{ task.id }}</td>
            <td><strong>{{ roleLabel(task.agent) }}</strong><p>{{ task.task }}</p></td>
            <td>{{ task.depends_on == null ? '未记录' : task.depends_on.join('、') || '无' }}</td>
            <td>{{ snapshot.subtask_results?.[task.id]?.stale ? '历史结果，需重新验证' : statusLabel(snapshot.subtask_results?.[task.id]?.status) }}<p v-if="snapshot.subtask_results?.[task.id]?.error">{{ snapshot.subtask_results[task.id].error }}</p></td>
          </tr></tbody>
        </table>
      </div>
    </section>
    <section v-if="review && visible('review')">
      <h4>代码审查</h4>
      <p>以下为审查执行时的观察结果，后续修改不会自动消除已记录的问题。</p>
      <p v-if="review.stale">此审查后发生了新的开发，需重新审查当前代码。</p>
      <p>{{ review.error || review.summary || '审查记录已保存' }}</p>
      <p v-if="review.overall_score != null">审查评分：{{ review.overall_score }}（模型评价）</p>
      <ul v-if="Array.isArray(review.issues) && review.issues.length">
        <li v-for="(issue, index) in review.issues" :key="index">
          <strong>{{ severityLabel(issue.severity) }} · {{ issue.file }} {{ issue.line }}</strong>
          <p>{{ issue.issue }}</p><p v-if="issue.suggestion">建议：{{ issue.suggestion }}</p>
        </li>
      </ul>
      <p v-else-if="!review.error">审查未列出问题；实际测试与业务验收结果见下方。</p>
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { AGENTS } from '../stores/taskStore'
import { executionTasks } from '../taskPresentation.js'
const props = defineProps({ snapshot: { type: Object, required: true }, section: { type: String, default: 'all' } })
function visible(section) { return props.section === 'all' || props.section === section }
const prd = computed(() => props.snapshot.agent_results?.pm?.prd)
const research = computed(() => props.snapshot.agent_results?.search)
const review = computed(() => props.snapshot.agent_results?.review)
const plan = computed(() => props.snapshot.plan)
const tasks = computed(() => executionTasks(props.snapshot))
const requirementGroups = [{ key: 'goals', label: '开发目标' }, { key: 'features', label: '功能范围' }, { key: 'acceptance_criteria', label: '验收条件' }]
function describe(value) { return typeof value === 'string' ? value : JSON.stringify(value) }
function roleLabel(id) { return AGENTS.find(agent => agent.id === id)?.label || id }
function statusLabel(status) { return { done: '已执行', error: '失败', skipped: '已跳过' }[status] || '暂无执行结果' }
function severityLabel(severity) { return { high: '高优先级', medium: '中优先级', low: '低优先级' }[severity] || severity }
function sourceUrl(source) {
  const value = typeof source === 'string' ? source : source?.url
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null } catch { return null }
}
</script>

<style scoped>
section { border-bottom: 1px solid var(--border-subtle); padding: 12px 0; }
h4 { margin: 0 0 10px; font-size: 14px; }
h5 { margin: 12px 0 6px; font-size: 13px; }
p, li, td, th { font-size: 13px; line-height: 1.7; overflow-wrap: anywhere; }
p { white-space: pre-wrap; margin: 4px 0; }
ul { margin: 6px 0; padding-left: 22px; }
a { color: var(--color-accent); }
.table-wrap { overflow-x: auto; margin-top: 12px; }
table { border-collapse: collapse; width: 100%; min-width: 500px; text-align: left; }
td, th { padding: 8px; border-bottom: 1px solid var(--border-subtle); vertical-align: top; }
th { color: var(--text-secondary); }
</style>
