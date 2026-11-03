<template>
  <section class="history">
    <h2>开发任务历史</h2>
    <div class="controls">
      <select v-model="status" @change="page = 1; refresh()">
        <option value="">全部状态</option>
        <option v-for="(label, value) in labels" :key="value" :value="value">{{ label }}</option>
      </select>
      <button @click="refresh">刷新</button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">正在读取任务…</p>
    <p v-else-if="!items.length">暂无符合条件的任务</p>
    <article v-for="task in items" :key="task.id" class="task">
      <div><strong>{{ labels[task.status] || task.status }}</strong> · {{ { revision: '增量开发', repair: '定向修复' }[task.execution_type] || '需求开发' }} · {{ new Date(task.created_at).toLocaleString('zh-CN') }}</div>
      <p>{{ task.user_input }}</p>
      <small v-if="!task.has_evidence">暂无结构化过程或验证记录；历史完成状态不代表测试通过</small>
      <small v-else>角色测试：{{ verification(task.test_verification, task.test_stale) }} · 固定验收：{{ verification(task.acceptance_verification, task.acceptance_stale) }}</small>
      <small v-if="task.parent_task_id">父任务：{{ task.parent_task_id }}</small>
      <div><code>{{ task.id }}</code> <button @click="emit('open', task.id)">查看过程与交付</button></div>
    </article>
    <div class="controls">
      <button :disabled="page === 1 || loading" @click="page--; refresh()">上一页</button>
      <span>第 {{ page }} 页 · 共 {{ total }} 条</span>
      <button :disabled="page * 10 >= total || loading" @click="page++; refresh()">下一页</button>
    </div>
  </section>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
const emit = defineEmits(['open'])
const labels = { queued: '待执行', running: '执行中', completed: '已交付', partial: '部分完成', failed: '失败' }
const items = ref([]), status = ref(''), page = ref(1), total = ref(0), loading = ref(false), error = ref('')
let request = 0
function verification(value, stale) { return stale ? '需重新验证' : { passed: '通过', failed: '未通过', not_run: '未执行' }[value] || '暂无结果' }
async function refresh() {
  const current = ++request
  loading.value = true
  error.value = ''
  try {
    const params = new URLSearchParams({ page: page.value, page_size: 10 })
    if (status.value) params.set('status', status.value)
    const response = await fetch(`/api/tasks?${params}`)
    if (!response.ok) throw new Error('无法读取任务历史')
    const data = await response.json()
    if (current !== request) return
    items.value = data.items
    total.value = data.total
  } catch (e) { if (current === request) error.value = e.message }
  finally { if (current === request) loading.value = false }
}
onMounted(refresh)
onUnmounted(() => { request++ })
</script>

<style scoped>
h2 { font-size: 18px; }
.task { padding: 14px; margin: 12px 0; border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg-panel); }
.task p { white-space: pre-wrap; max-height: 100px; overflow: auto; }
.task small { display: block; color: var(--text-muted); margin-bottom: 8px; }
.controls { display: flex; align-items: center; gap: 12px; }
button, select { padding: 7px 10px; background: var(--bg-panel); color: var(--text-primary); border: 1px solid var(--border-subtle); border-radius: 5px; cursor: pointer; }
button:disabled { opacity: .4; cursor: not-allowed; }
.error { color: var(--color-error); }
code { font-size: 11px; overflow-wrap: anywhere; }
</style>
