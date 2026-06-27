<template>
  <div :class="['avatar-display', `state-${state}`]" aria-label="灵山智慧导游小灵">
    <div class="avatar-ring">
      <svg class="avatar-face" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <circle class="avatar-head" cx="50" cy="48" r="34" />
        <g class="avatar-eyes">
          <ellipse class="eye" cx="36" cy="44" rx="4.5" ry="5.5" />
          <ellipse class="eye" cx="64" cy="44" rx="4.5" ry="5.5" />
          <circle v-if="state === 'thinking'" class="eye-pupil" cx="36" cy="42" r="2" />
          <circle v-if="state === 'thinking'" class="eye-pupil" cx="64" cy="42" r="2" />
        </g>
        <g class="avatar-mouth" :class="{ speaking: state === 'speaking' }">
          <path v-if="state === 'happy'" class="mouth happy" d="M36 62 Q50 78 64 62" />
          <path v-else-if="state === 'apology'" class="mouth apology" d="M36 64 Q50 52 64 64" />
          <path v-else class="mouth neutral" d="M38 62 Q50 68 62 62" />
        </g>
        <circle v-if="state === 'speaking' || state === 'happy'" class="cheek blush left" cx="24" cy="54" r="5" />
        <circle v-if="state === 'speaking' || state === 'happy'" class="cheek blush right" cx="76" cy="54" r="5" />
      </svg>
      <div class="avatar-glow" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  state: {
    type: String,
    default: "idle",
    validator: (v) =>
      ["idle", "listening", "thinking", "speaking", "happy", "apology"].includes(v),
  },
  emotion: {
    type: String,
    default: "neutral",
  },
});
</script>

<style scoped>
.avatar-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  user-select: none;
}

.avatar-ring {
  position: relative;
  width: 112px;
  height: 112px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-face {
  width: 100px;
  height: 100px;
  position: relative;
  z-index: 2;
}

.avatar-head {
  fill: #f0f4f8;
  stroke: #94a3b8;
  stroke-width: 2;
}

.eye {
  fill: #334155;
}

.eye-pupil {
  fill: #fff;
}

.mouth {
  fill: none;
  stroke: #475569;
  stroke-width: 2.5;
  stroke-linecap: round;
}

.mouth.speaking {
  animation: mouthTalk 0.25s ease-in-out infinite alternate;
}

@keyframes mouthTalk {
  0% {
    d: path("M38 62 Q50 68 62 62");
  }
  100% {
    d: path("M34 58 Q50 74 66 58");
  }
}

.cheek.blush {
  fill: #fda4af;
  opacity: 0.35;
}

.avatar-glow {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  z-index: 1;
  opacity: 0;
}

/* 状态动画 */

.state-idle .avatar-glow {
  animation: breathe 3s ease-in-out infinite;
  opacity: 0.6;
  background: radial-gradient(circle, rgba(15, 118, 110, 0.12), transparent 70%);
}

@keyframes breathe {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.06);
  }
}

.state-listening .avatar-glow {
  animation: pulse 0.8s ease-in-out infinite;
  opacity: 1;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.2), transparent 70%);
}

.state-listening .avatar-ring {
  animation: ringPulse 0.8s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

@keyframes ringPulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.3);
  }
  50% {
    box-shadow: 0 0 0 12px rgba(59, 130, 246, 0);
  }
}

.state-thinking .avatar-glow {
  animation: spin 1.5s linear infinite;
  opacity: 0.8;
  background: conic-gradient(from 0deg, rgba(245, 158, 11, 0.15), transparent 60%, rgba(245, 158, 11, 0.15));
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.state-speaking .avatar-glow {
  opacity: 0.7;
  background: radial-gradient(circle, rgba(15, 118, 110, 0.16), transparent 70%);
  animation: speakGlow 0.3s ease-in-out infinite alternate;
}

@keyframes speakGlow {
  0% {
    opacity: 0.5;
  }
  100% {
    opacity: 0.9;
  }
}

.state-happy .avatar-ring {
  animation: bounce 0.5s ease-in-out 2;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-8px);
  }
  60% {
    transform: translateY(-2px);
  }
}

.state-apology .avatar-ring {
  animation: bow 0.6s ease-in-out 1 forwards;
}

@keyframes bow {
  0% {
    transform: rotate(0);
  }
  40% {
    transform: rotate(-8deg);
  }
  80% {
    transform: rotate(2deg);
  }
  100% {
    transform: rotate(0);
  }
}

</style>
