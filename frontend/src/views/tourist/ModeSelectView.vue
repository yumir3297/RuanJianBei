<template>
  <div class="mode-select-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <div class="mode-content">
      <header class="mode-top">
        <button type="button" class="back-btn" @click="goHome">← 返回</button>
        <span class="mode-brand">灵山智慧导游</span>
      </header>

      <div class="mode-avatar">
        <div class="avatar-glow"></div>
        <div class="avatar-wrapper">
          <ThreeAvatar
            v-if="!avatarError"
            preset="hanfu"
            emotion="happy"
            :is-speaking="false"
            @error="avatarError = true"
          />
          <div v-else class="avatar-fallback">
            <svg viewBox="0 0 280 400" class="avatar-svg">
              <defs>
                <linearGradient id="modeGuideGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#2D5A4B" stop-opacity="0.95" />
                  <stop offset="100%" stop-color="#1f4638" stop-opacity="0.85" />
                </linearGradient>
              </defs>
              <ellipse cx="140" cy="55" rx="32" ry="28" fill="url(#modeGuideGrad)" opacity="0.9" />
              <ellipse cx="140" cy="80" rx="26" ry="30" fill="url(#modeGuideGrad)" />
              <rect x="132" y="108" width="16" height="12" rx="3" fill="url(#modeGuideGrad)" opacity="0.8" />
              <path d="M90 125 Q100 118 140 122 Q180 118 190 125 L210 180 Q195 185 185 200 L175 280 Q170 310 160 340 L140 345 L120 340 Q110 310 105 280 L95 200 Q85 185 70 180 Z" fill="url(#modeGuideGrad)" />
              <path d="M70 180 Q50 200 35 260 Q25 310 20 360 Q18 385 30 395 L60 390 Q55 360 65 320 Q75 270 90 220 Z" fill="url(#modeGuideGrad)" opacity="0.6" />
              <path d="M210 180 Q230 200 245 260 Q255 310 260 360 Q262 385 250 395 L220 390 Q225 360 215 320 Q205 270 190 220 Z" fill="url(#modeGuideGrad)" opacity="0.6" />
              <path d="M90 220 Q100 230 120 260 Q140 290 140 310 Q140 290 160 260 Q180 230 190 220 L185 350 Q180 380 170 395 L140 398 L110 395 Q100 380 95 350 Z" fill="url(#modeGuideGrad)" opacity="0.5" />
              <path d="M90 130 Q70 145 62 175 Q58 195 65 210 Q68 200 72 185 Q78 165 88 148 Z" fill="url(#modeGuideGrad)" opacity="0.75" />
              <path d="M190 130 Q210 145 218 175 Q222 195 215 210 Q212 200 208 185 Q202 165 192 148 Z" fill="url(#modeGuideGrad)" opacity="0.75" />
            </svg>
          </div>
        </div>
      </div>

      <p class="mode-guide">请选择您偏好的游览方式</p>

      <div class="mode-cards">
        <button
          v-for="mode in modes"
          :key="mode.key"
          type="button"
          :class="['mode-card', { selected: selectedMode === mode.key }]"
          :aria-pressed="selectedMode === mode.key"
          @click="selectMode(mode.key)"
        >
          <span v-if="mode.recommended" class="mode-badge">推荐</span>
          <strong class="mode-name">{{ mode.label }}</strong>
          <p class="mode-desc">{{ mode.desc }}</p>
        </button>
      </div>

      <button
        type="button"
        :class="['confirm-btn', { active: selectedMode }]"
        :disabled="!selectedMode"
        @click="confirmMode"
      >
        确认选择
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

import ThreeAvatar from "../../components/ThreeAvatar.vue";
import { useChatStore } from "../../stores/chat";
import { useInteractionStore } from "../../stores/interaction";

const GUIDE_STYLE_STORAGE_KEY = "a5-pending-guide-style-v1";

const router = useRouter();
const interactionStore = useInteractionStore();
const chatStore = useChatStore();
const avatarError = ref(false);
const selectedMode = ref(null);
const scenicBgUrl = "var(--lingshan-scenic-bg)";

const modes = [
  { key: "child", label: "亲子游", desc: "适合家庭轻松出行", recommended: true, chatStyle: "child" },
  { key: "leisure", label: "休闲游", desc: "轻松体验，随走随听", recommended: false, chatStyle: "adult" },
  { key: "expert", label: "文化深度游", desc: "深入解读历史与文化", recommended: false, chatStyle: "expert" },
  { key: "free", label: "自由游览", desc: "按需陪伴，不过度打扰", recommended: false, chatStyle: "none" },
];

function selectMode(key) {
  selectedMode.value = selectedMode.value === key ? null : key;
}

function confirmMode() {
  if (!selectedMode.value) {
    return;
  }

  const mode = modes.find((item) => item.key === selectedMode.value);
  if (!mode) {
    return;
  }

  interactionStore.setMode("free_chat");
  chatStore.resetSession();

  try {
    window.sessionStorage.setItem(GUIDE_STYLE_STORAGE_KEY, mode.chatStyle);
  } catch {}

  router.push("/tourist");
}

function goHome() {
  router.push("/tourist/welcome");
}
</script>

<style scoped>
.mode-select-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--lingshan-paper);
}

.scenic-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.scenic-bg-img {
  position: absolute;
  inset: 0;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  filter: blur(6px) saturate(0.5) brightness(0.45);
  transform: scale(1.04);
}

.scenic-bg-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse 65% 50% at 50% 55%,
    transparent 0%,
    rgba(27, 46, 37, 0.45) 70%,
    rgba(15, 25, 18, 0.6) 100%
  );
}

.mode-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100vh;
  width: min(100%, 520px);
  margin: 0 auto;
  padding: 16px 20px 28px;
}

.mode-top {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-btn {
  min-width: 44px;
  min-height: 44px;
  padding: 0 8px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.72);
  font-size: 14px;
  cursor: pointer;
}

.mode-brand {
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.12em;
}

.mode-avatar {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  width: 100%;
  position: relative;
  margin-bottom: 10px;
}

.avatar-glow {
  position: absolute;
  bottom: 12%;
  left: 50%;
  transform: translateX(-50%);
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(196, 155, 76, 0.16) 0%, transparent 72%);
}

.avatar-wrapper {
  position: relative;
  z-index: 1;
  width: min(260px, 70vw);
  height: min(400px, 54vh);
  min-height: 300px;
}

.avatar-fallback,
.avatar-svg {
  width: 100%;
  height: 100%;
}

.mode-guide {
  margin: 0 0 16px;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.88);
  letter-spacing: 0.08em;
  text-align: center;
}

.mode-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  width: 100%;
  max-width: 420px;
  margin-bottom: 20px;
}

.mode-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 116px;
  padding: 18px 12px;
  border: 1px solid var(--lingshan-line);
  border-radius: 14px;
  background: rgba(250, 248, 244, 0.78);
  backdrop-filter: blur(8px);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
  text-align: center;
  color: inherit;
  font: inherit;
}

.mode-card:hover {
  border-color: var(--lingshan-accent);
  transform: translateY(-2px);
}

.mode-card:focus-visible,
.confirm-btn:focus-visible,
.back-btn:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--lingshan-accent) 78%, white);
  outline-offset: 3px;
}

.mode-card.selected {
  background: rgba(45, 90, 75, 0.94);
  color: #fff;
  border-color: var(--lingshan-accent);
  box-shadow: 0 14px 30px rgba(17, 33, 26, 0.22);
}

.mode-card.selected .mode-name,
.mode-card.selected .mode-desc {
  color: #fff;
}

.mode-name {
  margin-bottom: 4px;
  font-size: 17px;
  font-weight: 600;
  color: var(--lingshan-ink);
}

.mode-desc {
  margin: 0;
  font-size: 12px;
  color: var(--lingshan-stone);
  line-height: 1.5;
}

.mode-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  padding: 2px 8px;
  border-radius: 8px;
  background: var(--lingshan-accent);
  color: #3d2e14;
  font-size: 11px;
  font-weight: 600;
}

.confirm-btn {
  width: 100%;
  max-width: 420px;
  height: 46px;
  border: none;
  border-radius: 23px;
  background: var(--lingshan-primary);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  opacity: 0.45;
  cursor: default;
  transition: opacity 0.2s ease, transform 0.2s ease, filter 0.2s ease;
}

.confirm-btn.active {
  opacity: 1;
  cursor: pointer;
}

.confirm-btn.active:hover {
  transform: translateY(-1px);
  filter: brightness(1.08);
}

@media (max-width: 640px) {
  .mode-content {
    padding: 16px 16px 24px;
  }

  .mode-brand {
    font-size: 15px;
  }

  .avatar-wrapper {
    width: min(236px, 74vw);
    height: min(360px, 48vh);
    min-height: 260px;
  }

  .mode-cards {
    gap: 10px;
  }

  .mode-card {
    min-height: 108px;
    padding: 16px 10px;
  }
}
</style>
