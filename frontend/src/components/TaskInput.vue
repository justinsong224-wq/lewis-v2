<template>
  <div>
  <div class="task-input">
    <span class="task-input__prompt mono">&gt;</span>
    <textarea
      v-model="text"
      class="task-input__field mono"
      rows="3"
      maxlength="5000"
      placeholder="描述开发需求、技术约束和验收条件..."
      :disabled="busy"
      @keydown.ctrl.enter.prevent="submit"
    ></textarea>
    <button class="task-input__btn" :disabled="busy || !text.trim()" @click="submit">
      {{ busy ? '开发任务进行中...' : '提交开发需求' }}
    </button>
  </div>
  <p class="acceptance-option">{{ text.length }} / 5000 字 · Ctrl+Enter 提交</p>
  <button class="demo-button" :disabled="busy" @click="parentTaskId = null; useBatchAcceptance = false; text = smsDemo">填入短信分类演示需求</button>
  <template v-if="taskStore.taskId && taskStore.finished">
    <button v-if="smsParent" class="demo-button" :disabled="busy || !taskStore.artifacts.some(file => file.path === 'app.py')" @click="useCurrentProject">基于当前任务增加 CSV 批量预测</button>
  </template>
  <p v-if="parentTaskId" class="acceptance-option">基于任务 {{ parentTaskId }} 增量开发，保留原产物。<button class="demo-button" :disabled="busy" @click="parentTaskId = null; useBatchAcceptance = false">取消关联</button></p>
  <label v-if="parentTaskId" class="acceptance-option"><input v-model="useBatchAcceptance" type="checkbox" :disabled="busy" />执行短信基础与 CSV 验收（共 8 项）</label>
  <label v-else class="acceptance-option"><input v-model="useSmsAcceptance" type="checkbox" :disabled="busy" />执行短信分类验收（5 项，需本地模型资产）</label>
  <p v-if="taskStore.error" class="input-error">{{ taskStore.error }}</p>
  <button v-if="taskStore.taskId && !taskStore.finished && !taskStore.ws" class="demo-button" @click="taskStore.connectWebSocket(taskStore.taskId)">重新连接任务</button>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { smsDemo, smsBatchDemo } from '../smsDemo'

const taskStore = useTaskStore()
const text = ref('')
const parentTaskId = ref(null)
const useBatchAcceptance = ref(false)
const smsParent = computed(() => ['sms-classifier', 'sms-batch'].includes(taskStore.snapshot?.acceptance_profile))
watch(() => taskStore.taskId, () => { parentTaskId.value = null; useBatchAcceptance.value = false })
function useCurrentProject() {
  parentTaskId.value = taskStore.taskId
  text.value = smsBatchDemo
  useBatchAcceptance.value = true
}
const useSmsAcceptance = ref(false)
watch(text, value => { useSmsAcceptance.value = value.trim() === smsDemo.trim() })
const submitting = ref(false)
const busy = computed(() => submitting.value || taskStore.submitting || taskStore.loading || ['queued', 'running'].includes(taskStore.taskStatus))

async function submit() {
  if (!text.value.trim() || busy.value) return
  submitting.value = true
  try {
    await taskStore.submitTask(text.value.trim(), parentTaskId.value ? (useBatchAcceptance.value ? 'sms-batch' : null) : useSmsAcceptance.value ? 'sms-classifier' : null, parentTaskId.value)
    text.value = ''
    parentTaskId.value = null
    useBatchAcceptance.value = false
  } catch (e) {
    console.error('提交任务失败', e)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.demo-button { margin-top: 8px; background: transparent; color: var(--text-secondary); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 6px 10px; cursor: pointer; }
.demo-button:disabled { opacity: .4; cursor: not-allowed; }
.acceptance-option { display: block; margin-top: 10px; font-size: 13px; color: var(--text-secondary); }
.input-error { color: var(--color-error); font-size: 13px; }
.task-input {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 10px 14px;
}

.task-input__prompt {
  color: var(--color-accent);
  font-size: 14px;
}

.task-input__field {
  resize: vertical;
  min-height: 70px;
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 14px;
}

.task-input__field::placeholder {
  color: var(--text-muted);
}

.task-input__btn {
  background: var(--color-accent);
  color: #0f1115;
  border: none;
  border-radius: var(--radius-sm);
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.task-input__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.task-input__btn:not(:disabled):hover {
  opacity: 0.85;
}
</style>
