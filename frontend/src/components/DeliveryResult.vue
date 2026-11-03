<template>
  <Transition name="reveal">
    <div v-if="taskStore.finished" class="delivery" :class="{ 'delivery--error': isError }">
      <div class="delivery__header">
        <span class="delivery__icon">{{ isError ? '!' : '✓' }}</span>
        <span class="delivery__title">{{ title }}</span>
      </div>
      <p class="delivery__content">{{ taskStore.finalOutput }}</p>
      <p v-if="!taskStore.snapshot?.delivery_assessment" class="delivery__content">此记录没有新版系统判定明细，请结合下方实际测试与验收证据核对。</p>
    </div>
  </Transition>
</template>

<script setup>
import { computed } from 'vue'
import { useTaskStore } from '../stores/taskStore'

const taskStore = useTaskStore()

const isError = computed(() => taskStore.taskStatus !== 'completed')
const title = computed(() => ({ completed: '开发任务已交付', partial: '部分完成，仍有未完成或未验证项', failed: '开发交付失败' }[taskStore.taskStatus] || '任务已结束'))
</script>

<style scoped>
.delivery {
  background: linear-gradient(135deg, rgba(74, 222, 128, 0.08), rgba(74, 222, 128, 0.02));
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
}

.delivery--error {
  background: linear-gradient(135deg, rgba(248, 113, 113, 0.08), rgba(248, 113, 113, 0.02));
  border-color: rgba(248, 113, 113, 0.3);
}

.delivery__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.delivery__icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-done);
  color: #0f1115;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.delivery--error .delivery__icon {
  background: var(--color-error);
}

.delivery__title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.delivery__content {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.reveal-enter-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.reveal-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
