<template>
  <button class="detail-trigger mono" @click="open = true" :disabled="!taskStore.logs.length">
    查看完整日志
  </button>

  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="modal-mask" @click.self="open = false">
        <div class="modal">
          <div class="modal__header">
            <span class="modal__title mono">完整执行日志</span>
            <button class="modal__close" @click="open = false">×</button>
          </div>
          <div class="modal__body mono">
            <div v-if="!taskStore.logs.length" class="modal__empty">暂无日志</div>
            <div v-for="(log, idx) in taskStore.logs" :key="idx" class="modal__entry" :class="`status-${log.status}`">
              <div class="modal__entry-head">
                <span class="modal__time">{{ formatTime(log.created_at) }}</span>
                <span class="modal__agent">{{ log.agent }}</span>
                <span class="modal__status">{{ statusText(log.status) }}</span>
              </div>
              <p class="modal__detail">{{ log.detail || log.message }}</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'
import { useTaskStore } from '../stores/taskStore'

const taskStore = useTaskStore()
const open = ref(false)

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString('zh-CN', { hour12: false })
}

function statusText(status) {
  const map = { working: '执行中', done: '完成', completed: '完成', error: '失败', skipped: '跳过' }
  return map[status] || status
}
</script>

<style scoped>
.detail-trigger {
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  font-size: 11px;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.detail-trigger:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.detail-trigger:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 24px;
}

.modal {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  width: 100%;
  max-width: 640px;
  max-height: 78vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.modal__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.modal__close {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  padding: 0 4px;
}

.modal__close:hover {
  color: var(--text-primary);
}

.modal__body {
  flex: 1;
  overflow-y: auto;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.modal__empty {
  color: var(--text-muted);
  font-size: 12.5px;
}

.modal__entry-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.modal__time { color: var(--text-muted); }
.modal__agent { color: var(--color-accent); font-weight: 600; }
.status-error .modal__agent { color: var(--color-error); }
.status-skipped .modal__agent { color: var(--color-skipped); }
.status-done .modal__agent,
.status-completed .modal__agent { color: var(--color-done); }
.modal__status { color: var(--text-muted); }

.modal__detail {
  margin: 4px 0 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-word;
}

.modal-enter-active, .modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-enter-from, .modal-leave-to {
  opacity: 0;
}
</style>