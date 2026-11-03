<template>
  <div class="desk" :class="`status-${state.status}`" :title="`${agent.label} · ${statusLabel}`">
    <svg viewBox="0 0 80 84" class="desk__svg">
      <ellipse cx="40" cy="78" rx="26" ry="4.5" class="desk__shadow" />

      <rect x="10" y="56" width="60" height="6" class="desk__desk-side" />
      <rect x="10" y="44" width="60" height="14" rx="2" class="desk__desk-top" />
      <rect x="14" y="58" width="6" height="14" class="desk__leg" />
      <rect x="60" y="58" width="6" height="14" class="desk__leg" />

      <rect x="28" y="20" width="24" height="17" rx="2" class="desk__monitor" />
      <rect x="30" y="22.5" width="20" height="12" rx="1" class="desk__screen" />
      <rect x="37" y="37" width="6" height="4" class="desk__monitor-stand" />
      <rect x="33" y="41" width="14" height="2.5" rx="1" class="desk__keyboard" />

      <path d="M22 56 Q22 46 32 44 L48 44 Q58 46 58 56 Z" class="desk__torso" />
      <ellipse cx="40" cy="48" rx="6" ry="3" class="desk__torso-top" />

      <circle cx="40" cy="34" r="8.5" class="desk__head" />
      <path d="M32 30 Q32 22 40 22 Q48 22 48 30 L48 32 Q40 28 32 32 Z" class="desk__hair" />

      <circle cx="40" cy="13" r="3" class="desk__status-dot" />
    </svg>

    <div class="desk__label">
      <span class="desk__name mono">{{ agent.label }}</span>
      <span class="desk__status-text mono">{{ statusLabel }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  agent: { type: Object, required: true },
  state: { type: Object, required: true },
})

const statusLabel = computed(() => {
  const map = {
    idle: '空闲',
    working: '工作中',
    done: '完成',
    completed: '完成',
    error: '出错',
    skipped: '跳过',
    interrupted: '已中断',
    stale: '需重新验证',
  }
  return map[props.state.status] || props.state.status
})
</script>

<style scoped>
.desk {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: var(--radius-md);
  transition: background 0.2s ease;
}

.desk:hover {
  background: rgba(255, 255, 255, 0.03);
}

.desk__svg {
  width: 92px;
  aspect-ratio: 80 / 84;
  overflow: visible;
}

.desk__shadow { fill: rgba(0, 0, 0, 0.28); }

.desk__desk-top { fill: #2c3140; stroke: #3a4051; stroke-width: 0.5; }
.desk__desk-side { fill: #1c2029; }
.desk__leg { fill: #20242f; }

.desk__monitor { fill: #11141b; stroke: #3a4051; stroke-width: 0.5; }
.desk__monitor-stand { fill: #3a4051; }
.desk__keyboard { fill: #3a4051; }
.desk__screen { fill: var(--color-idle); transition: fill 0.3s ease; }

.desk__torso { fill: #4a5268; }
.desk__torso-top { fill: #565f78; }
.desk__head { fill: #d4a374; }
.desk__hair { fill: #2c2419; }

.desk__status-dot {
  fill: var(--color-idle);
  transition: fill 0.3s ease;
}

.status-working .desk__screen,
.status-working .desk__status-dot {
  fill: var(--color-working);
}
.status-working .desk__status-dot {
  animation: blink 1.3s ease-in-out infinite;
}

.status-done .desk__screen,
.status-completed .desk__screen,
.status-done .desk__status-dot,
.status-completed .desk__status-dot {
  fill: var(--color-done);
}

.status-error .desk__screen,
.status-error .desk__status-dot {
  fill: var(--color-error);
}

.status-skipped .desk__screen,
.status-skipped .desk__status-dot {
  fill: var(--color-skipped);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.desk__label {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.3;
}

.desk__name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.desk__status-text {
  font-size: 10.5px;
  color: var(--text-muted);
}

.status-working .desk__status-text { color: var(--color-working); }
.status-done .desk__status-text,
.status-completed .desk__status-text { color: var(--color-done); }
.status-error .desk__status-text { color: var(--color-error); }
.status-skipped .desk__status-text { color: var(--color-skipped); }
</style>
