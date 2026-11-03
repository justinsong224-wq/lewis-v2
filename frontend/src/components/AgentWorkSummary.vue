<template>
  <section class="agent-work">
    <h3>本次 Agent 做了什么</h3>
    <p class="note">职责说明对应下列角色；具体完成情况以本任务保存的记录为准。</p>
    <article v-for="role in roles" :key="role.id">
      <strong>{{ role.name }}</strong><span>{{ role.work }}</span>
      <small>{{ recorded(role.id) ? snapshot.execution_type === 'repair' && ['ceo', 'pm', 'search'].includes(role.id) ? '沿用父任务记录' : '已有记录' : '本任务暂无记录' }}</small>
      <a v-if="role.id === 'search' && recorded('search')" :href="`/api/task/${taskId}/research-report`" target="_blank" rel="noopener">查看调研报告 ↗</a>
    </article>
    <p v-if="snapshot.acceptance_profile?.startsWith('sms')"><a href="/api/demo/sms/model-research" target="_blank" rel="noopener">Search 模型对比补充调研 ↗</a> · 本轮新增，对比 baseline 与 Transformer，独立于原始生成记录。</p>
    <p v-if="execution">测试工程师实际执行：{{ execution.passed }}/{{ execution.total }}；固定验收：{{ snapshot.acceptance?.passed ?? '—' }}/{{ snapshot.acceptance?.total ?? '—' }}。</p>
    <p v-if="snapshot.agent_results?.test?.stale || snapshot.acceptance?.stale">文件已变化，以上历史验证需重新执行。</p>
  </section>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ snapshot: { type: Object, required: true }, taskId: { type: String, required: true } })
const roles = [
  { id: 'ceo', name: 'CEO · 技术总监', work: '制定技术方案，拆分子任务并安排依赖与分工。' },
  { id: 'pm', name: 'PM · 项目经理', work: '整理需求、功能范围和验收条件。' },
  { id: 'search', name: 'Search · 技术调研', work: '搜索技术资料，形成带来源的调研报告。' },
  { id: 'dev', name: 'Dev · 开发工程师', work: '读取基础代码，修改接口与页面，通过 MCP 写入文件。' },
  { id: 'test', name: 'Test · 测试工程师', work: '编写并实际运行测试，保存输出和通过数量。' },
  { id: 'writer', name: 'Writer · 文档工程师', work: '编写 README，说明启动、功能与限制。' },
  { id: 'review', name: 'Review · 代码审查', work: '检查实际代码和需求，记录问题及建议。' },
  { id: 'customer', name: 'Customer · 交付专员', work: '汇总实际产物和验证结果，说明交付范围。' },
]
function recorded(id) { return id === 'ceo' ? Boolean(props.snapshot.plan) : id === 'customer' ? Boolean(props.snapshot.delivery) : Boolean(props.snapshot.agent_results?.[id]) }
const execution = computed(() => props.snapshot.agent_results?.test?.execution)
</script>
<style scoped>
.agent-work article { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 14px; padding: 12px 0; border-bottom: 1px solid var(--border-subtle); font-size: 13px; }
strong { min-width: 145px; }
span { flex: 1; min-width: 180px; line-height: 1.6; }
small, .note { color: var(--text-secondary); font-size: 12px; }
a { color: var(--color-accent); white-space: nowrap; }
p { font-size: 13px; line-height: 1.6; }
h3 { font-size: 15px; }
</style>
