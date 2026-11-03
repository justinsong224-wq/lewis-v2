<template>
  <div class="app">
    <header class="app__header">
      <div class="app__brand">
        <span class="app__logo mono">L</span>
        <span class="app__title">Lewis</span>
        <span class="app__subtitle mono">软件开发团队智能协作</span>
      </div>
      <nav class="app__nav">
        <button @click="view = 'workspace'">开发工作台</button>
        <button @click="view = 'history'">任务历史</button>
      </nav>
    </header>

    <main class="app__main">
      <div v-if="view === 'workspace'" class="app__center">
        <TaskInput />
        <details class="task-details">
          <summary>任务详情：流程、交付与证据 <span>点击展开 / 收起</span></summary>
          <div class="task-details__content">
            <TaskEvidence />
            <details><summary>执行进度、交付说明与日志</summary>
              <TaskFlow />
              <DeliveryResult />
              <ExecutionLog />
            </details>
          </div>
        </details>
        <OfficeScene />
      </div>
      <div v-else class="app__center"><TaskHistory @open="openTask" /></div>
    </main>
  </div>
</template>

<script setup>
import TaskInput from './components/TaskInput.vue'
import OfficeScene from './components/OfficeScene.vue'
import TaskFlow from './components/TaskFlow.vue'
import DeliveryResult from './components/DeliveryResult.vue'
import ExecutionLog from './components/ExecutionLog.vue'
import TaskHistory from './components/TaskHistory.vue'
import TaskEvidence from './components/TaskEvidence.vue'
import { onMounted, onUnmounted, ref } from 'vue'
import { useTaskStore } from './stores/taskStore'

const view = ref('workspace')
const store = useTaskStore()
async function openTask(id) {
  view.value = 'workspace'
  await store.loadTask(id)
}
function restoreHash() {
  const id = new URLSearchParams(window.location.hash.slice(1)).get('task')
  if (id && id !== store.taskId) openTask(id)
}
onMounted(() => {
  restoreHash()
  window.addEventListener('hashchange', restoreHash)
})
onUnmounted(() => {
  window.removeEventListener('hashchange', restoreHash)
  store.resetAgents()
})
</script>

<style scoped>
.task-details { border: 1px solid var(--border-subtle); border-radius: 8px; background: var(--bg-panel); }
.task-details > summary { cursor: pointer; padding: 12px 14px; color: var(--text-primary); font-size: 13px; }
.task-details > summary span { margin-left: 8px; color: var(--text-muted); font-size: 12px; }
.task-details__content { display: flex; flex-direction: column; gap: 12px; padding: 0 12px 12px; min-width: 0; }
.app__nav { display: flex; gap: 10px; padding: 8px 28px; border-bottom: 1px solid var(--border-subtle); }
.app__nav button { background: var(--bg-panel); color: var(--text-primary); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 7px 12px; cursor: pointer; }
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app__header {
  padding: 12px 28px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.app__brand {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.app__logo {
  width: 24px;
  height: 24px;
  background: var(--color-accent);
  color: #0f1115;
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
}

.app__title {
  font-size: 16px;
  font-weight: 700;
}

.app__subtitle {
  font-size: 10.5px;
  color: var(--text-muted);
}

.app__main {
  flex: 1;
  overflow-y: auto;
  padding: 16px 28px 32px;
}

.app__center {
  width: 100%;
  max-width: 860px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>
