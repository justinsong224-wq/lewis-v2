<template>
  <section class="lineage" v-if="items.length > 1 || error || incomplete">
    <h4>开发与修复关联记录</h4>
    <p v-if="error">{{ error }}</p>
    <p v-if="incomplete">部分关联记录缺失或链路过长，以下仅展示可核对的记录。</p>
    <ol>
      <li v-for="item in items" :key="item.id">
        <button :disabled="item.id === taskId" @click="store.loadTask(item.id)">{{ { repair: '定向修复', revision: '增量开发' }[item.execution_type] || '完整生成' }} · {{ statusLabel(item.status) }}</button>
        <code>{{ item.id }}</code>
        <p>{{ item.created_at }} · 测试 {{ count(item.test) }} · 固定验收 {{ count(item.acceptance) }}</p>
      </li>
    </ol>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useTaskStore } from '../stores/taskStore'
const props = defineProps({ taskId: String, finished: Boolean })
const store = useTaskStore()
const items = ref([]), error = ref(''), incomplete = ref(false)
watch(() => [props.taskId, props.finished], async ([id], previous, onCleanup) => {
  const controller = new AbortController()
  onCleanup(() => controller.abort())
  items.value = []; error.value = ''; incomplete.value = false
  if (!id) return
  try {
    const response = await fetch('/api/task/' + encodeURIComponent(id) + '/lineage', { signal: controller.signal })
    if (!response.ok) throw new Error('无法读取任务关联记录')
    const data = await response.json()
    if (controller.signal.aborted) return
    items.value = data.items || []; incomplete.value = data.incomplete
  } catch (e) { if (!controller.signal.aborted) error.value = e.message }
}, { immediate: true })
function statusLabel(value) { return { completed: '完成', partial: '部分完成', failed: '失败', running: '执行中', queued: '排队中' }[value] || value }
function count(value) {
  const result = value?.total != null ? (value.passed ?? 0) + '/' + value.total : '无执行证据'
  return value?.stale ? result + '（历史结果，需重新验证）' : result
}
</script>

<style scoped>
.lineage { margin: 16px 0; padding: 12px; border: 1px solid var(--border-subtle); border-radius: 8px; }
h4 { margin: 0 0 10px; }
ol { padding-left: 20px; }
li { margin: 10px 0; }
code { display: block; font-size: 11px; margin-top: 5px; overflow-wrap: anywhere; }
p { font-size: 12px; line-height: 1.6; }
button { color: var(--color-accent); background: transparent; border: 1px solid var(--border-subtle); border-radius: 5px; padding: 6px; cursor: pointer; }
button:disabled { cursor: default; color: var(--text-primary); }
</style>
