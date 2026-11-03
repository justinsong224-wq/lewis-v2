<template>
  <div class="connector" :class="state">
    <svg class="connector__svg" :viewBox="`0 0 ${branch === 2 ? 200 : 40} 28`" preserveAspectRatio="none">
      <template v-if="branch === 2">
        <path d="M100 0 L100 10 L30 10 L30 28" class="connector__line" />
        <path d="M100 0 L100 10 L170 10 L170 28" class="connector__line" />
        <circle v-if="state === 'flowing'" cx="30" cy="10" r="2" class="connector__dot">
          <animateMotion dur="1.4s" repeatCount="indefinite" path="M100 0 L100 10 L30 10 L30 28" />
        </circle>
        <circle v-if="state === 'flowing'" cx="170" cy="10" r="2" class="connector__dot">
          <animateMotion dur="1.4s" repeatCount="indefinite" path="M100 0 L100 10 L170 10 L170 28" />
        </circle>
      </template>
      <template v-else>
        <path d="M20 0 L20 28" class="connector__line" />
        <circle v-if="state === 'flowing'" cx="20" cy="0" r="2" class="connector__dot">
          <animateMotion dur="1s" repeatCount="indefinite" path="M20 0 L20 28" />
        </circle>
      </template>
    </svg>
  </div>
</template>

<script setup>
defineProps({
  // 'idle' | 'flowing'（数据正在传递，播放动画）| 'settled'（已完成，静态高亮）
  state: { type: String, default: 'idle' },
  branch: { type: Number, default: 1 },
})
</script>

<style scoped>
.connector {
  width: 100%;
  max-width: 240px;
  height: 28px;
}

.connector__svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.connector__line {
  fill: none;
  stroke: var(--border-subtle);
  stroke-width: 1.5;
  transition: stroke 0.3s ease;
}

.connector.flowing .connector__line,
.connector.settled .connector__line {
  stroke: var(--color-accent);
}

.connector__dot {
  fill: var(--color-working);
}
</style>