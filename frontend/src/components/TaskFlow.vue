<template>
  <div v-if="steps.length" class="progress">
    <div class="progress__track">
      <div
        v-for="step in steps"
        :key="step.id"
        :title="step.agent + ' · ' + statusText(step.status)"
        class="progress__seg"
        :class="`status-${step.status}`"
      ></div>
    </div>
    <div class="progress__current mono">
      <span class="progress__agent">{{ currentStep?.agent }}</span>
      <span class="progress__sep">·</span>
      <span class="progress__status">{{ statusText(currentStep?.status) }}</span>
    </div>
    <ol class="progress__steps">
      <li v-for="step in steps" :key="step.id">{{ step.agent }} · {{ statusText(step.status) }}</li>
    </ol>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTaskStore, AGENTS } from '../stores/taskStore'

const taskStore = useTaskStore()

const steps = computed(() => {
  if (!taskStore.taskId) return []
  const roleStep = id => ({ id, agent: AGENTS.find(a => a.id === id)?.label || id, status: taskStore.agentStates[id]?.status || 'idle' })
  const planned = taskStore.executionOrder.map(task => ({
    id: 'subtask-' + task.id,
    agent: (AGENTS.find(a => a.id === task.agent)?.label || task.agent) + ' / ' + task.id,
    status: taskStore.subtaskStates[task.id]?.stale ? 'stale' : taskStore.subtaskStates[task.id]?.status || 'idle',
  }))
  return [...(taskStore.snapshot?.execution_type === 'repair' ? [] : [roleStep('pm'), roleStep('search'), roleStep('ceo')]), ...planned,
    ...(taskStore.acceptanceState ? [{ id: 'acceptance', agent: '固定业务验收', status: taskStore.acceptanceState.status }] : []),
    roleStep('customer')]
})

const currentStep = computed(() => {
  const working = steps.value.find(s => s.status === 'working')
  return working || [...steps.value].reverse().find(s => s.status !== 'idle') || steps.value[0]
})

function statusText(status) {
  const map = { idle: taskStore.finished ? '未执行' : '待执行', working: '执行中', done: '完成', completed: '完成', error: '失败', skipped: '跳过', interrupted: '已中断', stale: '需重新验证' }
  return map[status] || ''
}
</script>

<style scoped>
.progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}

.progress__track {
  display: flex;
  gap: 3px;
  height: 4px;
}

.progress__seg {
  flex: 1;
  border-radius: 2px;
  background: var(--color-idle);
  transition: background 0.3s ease;
}

.progress__seg.status-working { background: var(--color-working); }
.progress__seg.status-done,
.progress__seg.status-completed { background: var(--color-done); }
.progress__seg.status-error { background: var(--color-error); }
.progress__seg.status-skipped { background: var(--color-skipped); }
.progress__seg.status-interrupted, .progress__seg.status-stale { background: var(--color-error); }
.progress__steps { display: flex; flex-wrap: wrap; gap: 6px 20px; padding-left: 20px; margin: 6px 0; color: var(--text-secondary); font-size: 12px; }

.progress__current {
  font-size: 11px;
  color: var(--text-secondary);
  display: flex;
  gap: 6px;
}

.progress__agent { color: var(--text-primary); font-weight: 600; }
.progress__sep { color: var(--text-muted); }
</style>
