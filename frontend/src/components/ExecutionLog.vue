<template>
  <div class="log-widget">
    <button class="log-widget__toggle mono" @click="open = !open">
      <span class="log-widget__dot" :class="{ active: hasNew }"></span>
      执行日志
      <span class="log-widget__count">{{ taskStore.logs.length }}</span>
      <span class="log-widget__chevron">{{ open ? '▲' : '▼' }}</span>
    </button>

    <Transition name="expand">
      <div v-if="open" class="log-widget__panel">
        <div class="log-widget__panel-head">
          <DetailLogModal />
        </div>
        <div class="log-widget__body mono" ref="logBody">
          <div v-if="!taskStore.logs.length" class="log-widget__empty">等待任务输入...</div>
          <div
            v-for="(log, idx) in taskStore.logs"
            :key="idx"
            class="log-widget__line"
            :class="`status-${log.status}`"
          >
            <span class="log-widget__time">{{ formatTime(log.created_at) }}</span>
            <span class="log-widget__agent">{{ log.agent }}</span>
            <span class="log-widget__msg">{{ log.message }}</span>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import DetailLogModal from './DetailLogModal.vue'

const taskStore = useTaskStore()
const open = ref(false)
const hasNew = ref(false)
const logBody = ref(null)

watch(() => taskStore.logs.length, async (val, oldVal) => {
  if (val > oldVal && !open.value) hasNew.value = true
  await nextTick()
  if (logBody.value) logBody.value.scrollTop = logBody.value.scrollHeight
})

watch(open, (val) => {
  if (val) hasNew.value = false
})

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.log-widget {
  width: 100%;
}

.log-widget__toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 9px 14px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.log-widget__toggle:hover {
  border-color: var(--color-accent);
}

.log-widget__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border-subtle);
  flex-shrink: 0;
}
.log-widget__dot.active {
  background: var(--color-working);
  animation: blink 1.2s ease-in-out infinite;
}

.log-widget__count {
  background: var(--bg-card);
  border-radius: 10px;
  padding: 1px 7px;
  font-size: 10.5px;
  color: var(--text-muted);
}

.log-widget__chevron {
  margin-left: auto;
  font-size: 9px;
  color: var(--text-muted);
}

.log-widget__panel {
  margin-top: 8px;
}

.log-widget__panel-head {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}

.log-widget__body {
  max-height: 220px;
  overflow-y: auto;
  background: #0b0d11;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 11.5px;
  line-height: 1.7;
}

.log-widget__empty { color: var(--text-muted); }

.log-widget__line {
  display: flex;
  gap: 8px;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-widget__time { color: var(--text-muted); flex-shrink: 0; }
.log-widget__agent { color: var(--color-accent); flex-shrink: 0; min-width: 60px; }
.status-error .log-widget__agent { color: var(--color-error); }
.status-skipped .log-widget__agent { color: var(--color-skipped); }
.status-done .log-widget__agent,
.status-completed .log-widget__agent { color: var(--color-done); }
.log-widget__msg { color: var(--text-secondary); }

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.expand-enter-active, .expand-leave-active {
  transition: opacity 0.15s ease;
}
.expand-enter-from, .expand-leave-to {
  opacity: 0;
}
</style>