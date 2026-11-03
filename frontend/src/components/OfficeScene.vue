<template>
  <div ref="office" class="office">
    <div class="office__demo-controls">
      <button :disabled="realTaskBusy" @click="playing ? stopDemo() : startDemo()">{{ playing ? '停止演示' : '演示协作全流程' }}</button>
      <span>约 32 秒 · 仅前端动画，不调用模型</span>
    </div>
    <div v-if="demoVisible" class="office__demo-banner" role="status">
      <strong>演示模式 · {{ playing ? `${stageIndex + 1}/8 ${currentStage.title}` : '演示结束' }}</strong>
      <span>{{ playing ? currentStage.message : '协作流程展示完毕，可查看已有 CSV 成果。' }}</span>
      <progress :value="elapsed" :max="collaborationDemoSeconds" aria-label="协作演示进度"></progress>
      <small>预设流程动画，不代表正在开发或已生成新文件。</small>
      <button v-if="!playing" @click="stopDemo">退出演示</button>
    </div>
    <svg v-if="demoVisible" class="office__connections" :viewBox="`0 0 ${canvas.width} ${canvas.height}`" aria-hidden="true">
      <path v-for="(line, index) in connections" :key="index" :d="line" :class="{ active: index === stageIndex - 1, passed: index < stageIndex - 1 || !playing }" />
    </svg>
    <h3>软件开发团队职责</h3>
    <p class="office__note">展示角色分工与当前状态；具体执行顺序和依赖见上方任务流程。</p>
    <!-- 需求管理 -->
    <div class="office__tier office__tier--solo">
      <DigitalEmployee
        v-for="agent in requirementTeam"
        :key="agent.id"
        :agent="agent"
        :data-agent="agent.id"
        :state="displayStates[agent.id]"
      />
    </div>

    <!-- 技术规划 -->
    <div class="office__tier office__tier--solo">
      <DigitalEmployee
        v-for="agent in planningTeam"
        :key="agent.id"
        :agent="agent"
        :data-agent="agent.id"
        :state="displayStates[agent.id]"
      />
    </div>

    <!-- 技术部 + 数据部 并排 -->
    <div class="office__tier office__tier--split">
      <div class="office__dept">
        <span class="office__dept-label mono">开发与质量</span>
        <div class="office__row">
          <DigitalEmployee
            v-for="agent in tierTech"
            :key="agent.id"
            :agent="agent"
            :data-agent="agent.id"
            :state="displayStates[agent.id]"
          />
        </div>
      </div>
      <div class="office__dept">
        <span class="office__dept-label mono">技术支持</span>
        <div class="office__row">
          <DigitalEmployee
            v-for="agent in tierData"
            :key="agent.id"
            :agent="agent"
            :data-agent="agent.id"
            :state="displayStates[agent.id]"
          />
        </div>
      </div>
    </div>

    <!-- 运营部：承接交付 -->
    <div class="office__tier office__tier--solo">
      <div class="office__dept">
        <span class="office__dept-label mono">软件交付</span>
        <div class="office__row">
          <DigitalEmployee
            v-for="agent in tierOps"
            :key="agent.id"
            :agent="agent"
            :data-agent="agent.id"
            :state="displayStates[agent.id]"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { collaborationDemo, collaborationDemoSeconds } from '../collaborationDemo'
import DigitalEmployee from './DigitalEmployee.vue'
import { useTaskStore, AGENTS } from '../stores/taskStore'

const taskStore = useTaskStore()
const office = ref(null)
const playing = ref(false)
const demoVisible = ref(false)
const elapsed = ref(0)
const connections = ref([])
const canvas = ref({ width: 1, height: 1 })
let timer, observer, startedAt
const realTaskBusy = computed(() => taskStore.submitting || taskStore.loading || ['queued', 'running'].includes(taskStore.taskStatus))
const stageIndex = computed(() => {
  let end = 0
  for (let i = 0; i < collaborationDemo.length; i++) {
    end += collaborationDemo[i].seconds
    if (elapsed.value < end) return i
  }
  return collaborationDemo.length - 1
})
const currentStage = computed(() => collaborationDemo[stageIndex.value])
const displayStates = computed(() => {
  if (!demoVisible.value) return taskStore.agentStates
  return Object.fromEntries(AGENTS.map(agent => {
    const index = collaborationDemo.findIndex(stage => stage.role === agent.id)
    return [agent.id, { status: index < 0 ? 'idle' : !playing.value || index < stageIndex.value ? 'done' : index === stageIndex.value ? 'working' : 'idle', message: '前端演示' }]
  }))
})
function measureConnections() {
  if (!office.value || !demoVisible.value) return
  const bounds = office.value.getBoundingClientRect()
  canvas.value = { width: bounds.width, height: bounds.height }
  const points = collaborationDemo.map(stage => {
    const node = office.value.querySelector(`[data-agent="${stage.role}"]`)
    const rect = node.getBoundingClientRect()
    return { x: rect.left - bounds.left + rect.width / 2, y: rect.top - bounds.top + 48 }
  })
  connections.value = points.slice(1).map((point, i) => {
    const from = points[i]
    return `M ${from.x} ${from.y} Q ${(from.x + point.x) / 2 + 35} ${(from.y + point.y) / 2} ${point.x} ${point.y}`
  })
}
async function startDemo() {
  if (realTaskBusy.value) return
  clearInterval(timer)
  elapsed.value = 0
  demoVisible.value = playing.value = true
  startedAt = performance.now()
  timer = setInterval(() => {
    elapsed.value = Math.min(collaborationDemoSeconds, (performance.now() - startedAt) / 1000)
    if (elapsed.value >= collaborationDemoSeconds) { playing.value = false; clearInterval(timer) }
  }, 100)
  await nextTick()
  measureConnections()
}
function stopDemo() { clearInterval(timer); playing.value = demoVisible.value = false }
watch(() => taskStore.taskId, stopDemo)
watch(realTaskBusy, busy => { if (busy) stopDemo() })
onMounted(() => { observer = new ResizeObserver(measureConnections); observer.observe(office.value) })
onUnmounted(() => { clearInterval(timer); observer?.disconnect() })

const byId = (...ids) => AGENTS.filter(a => ids.includes(a.id))

const requirementTeam = computed(() => byId('pm'))
const planningTeam = computed(() => byId('ceo'))
const tierTech = computed(() => byId('dev', 'test', 'devops', 'review'))
const tierData = computed(() => byId('search', 'analyst'))
const tierOps = computed(() => byId('writer', 'customer'))

</script>

<style scoped>
h3 { margin: 12px 0 4px; font-size: 14px; }
.office__note { margin: 0 0 8px; color: var(--text-secondary); font-size: 12px; text-align: center; }
.office {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 100%;
}
.office__demo-controls { display: flex; align-items: center; justify-content: center; gap: 10px; flex-wrap: wrap; margin-top: 8px; }
.office__demo-controls span { color: var(--text-secondary); font-size: 12px; }
.office button { cursor: pointer; background: var(--bg-panel); border: 1px solid var(--color-accent); color: var(--text-primary); border-radius: 6px; padding: 8px 12px; }
.office button:disabled { opacity: .45; cursor: not-allowed; }
.office__demo-banner { width: 100%; display: flex; flex-direction: column; gap: 5px; border: 1px solid var(--color-accent); border-radius: 8px; padding: 12px; font-size: 13px; background: var(--bg-panel); }
.office__demo-banner small { color: var(--text-secondary); }
.office__demo-banner progress { width: 100%; height: 6px; accent-color: var(--color-accent); }
.office__connections { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
.office__connections path { fill: none; stroke: var(--color-accent); stroke-width: 2; opacity: .12; }
.office__connections path.passed { opacity: .35; }
.office__connections path.active { opacity: 1; stroke-dasharray: 7 7; animation: demo-flow .65s linear infinite; }
.office__tier, .office__demo-controls, .office__demo-banner { position: relative; z-index: 1; }
@keyframes demo-flow { to { stroke-dashoffset: -28; } }

.office__tier {
  display: flex;
  justify-content: center;
}

.office__tier--solo {
  gap: 10px;
}

.office__tier--split {
  flex-wrap: wrap;
  gap: 36px;
}

.office__dept {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 8px 16px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.015);
}

.office__dept-label {
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.06em;
}

.office__row {
  flex-wrap: wrap;
  justify-content: center;
  display: flex;
  gap: 6px;
}
</style>
