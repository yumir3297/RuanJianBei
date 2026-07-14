<template>
  <div class="welcome">
    <div class="bg-img" aria-hidden="true" :style="{ backgroundImage: scenicBgUrl }"></div>
    <div class="bg-veil" aria-hidden="true"></div>

    <div class="avatar-layer" aria-hidden="true">
      <div class="avatar-aura"></div>
      <div class="avatar-frame">
        <ThreeAvatar
          v-if="!avatarError"
          :preset="activePreset"
          emotion="neutral"
          :is-speaking="false"
          @error="avatarError = true"
        />
        <div v-else class="avatar-fallback" aria-label="数字人导游形象">
          <svg viewBox="0 0 280 400" class="avatar-svg">
            <defs>
              <linearGradient id="guideGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#2D5A4B" stop-opacity="0.95" />
                <stop offset="100%" stop-color="#1f4638" stop-opacity="0.85" />
              </linearGradient>
            </defs>
            <ellipse cx="140" cy="55" rx="32" ry="28" fill="url(#guideGrad)" opacity="0.9" />
            <ellipse cx="140" cy="80" rx="26" ry="30" fill="url(#guideGrad)" />
            <rect x="132" y="108" width="16" height="12" rx="3" fill="url(#guideGrad)" opacity="0.8" />
            <path d="M90 125 Q100 118 140 122 Q180 118 190 125 L210 180 Q195 185 185 200 L175 280 Q170 310 160 340 L140 345 L120 340 Q110 310 105 280 L95 200 Q85 185 70 180 Z" fill="url(#guideGrad)" />
            <path d="M70 180 Q50 200 35 260 Q25 310 20 360 Q18 385 30 395 L60 390 Q55 360 65 320 Q75 270 90 220 Z" fill="url(#guideGrad)" opacity="0.6" />
            <path d="M210 180 Q230 200 245 260 Q255 310 260 360 Q262 385 250 395 L220 390 Q225 360 215 320 Q205 270 190 220 Z" fill="url(#guideGrad)" opacity="0.6" />
            <path d="M90 220 Q100 230 120 260 Q140 290 140 310 Q140 290 160 260 Q180 230 190 220 L185 350 Q180 380 170 395 L140 398 L110 395 Q100 380 95 350 Z" fill="url(#guideGrad)" opacity="0.5" />
            <path d="M90 130 Q70 145 62 175 Q58 195 65 210 Q68 200 72 185 Q78 165 88 148 Z" fill="url(#guideGrad)" opacity="0.75" />
            <path d="M190 130 Q210 145 218 175 Q222 195 215 210 Q212 200 208 185 Q202 165 192 148 Z" fill="url(#guideGrad)" opacity="0.75" />
          </svg>
        </div>
      </div>
    </div>

    <div class="content">
      <button type="button" class="back-btn" aria-label="返回首页" @click="goHome">
        <span class="back-arrow" aria-hidden="true">&larr;</span> 返回
      </button>

      <div class="hero-text" aria-hidden="true">
        <h1 class="hero-title">灵山智慧导览</h1>
        <p class="hero-sub">清岚 &middot; AI 数字人导览员</p>
      </div>

      <div class="cta-zone">
        <p class="welcome-text">{{ welcomeText }}</p>
        <button type="button" class="glass-btn" @click="enterTourist">
          开启导览
          <span class="btn-arrow" aria-hidden="true">&rarr;</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import ThreeAvatar from "../components/ThreeAvatar.vue";
import { useScenicBackground } from "../composables/useScenicBackground";
import { fetchAvatarConfig } from "../api/admin";
import { normalizeAvatarPresetFromModelPath, DEFAULT_AVATAR_PRESET } from "../utils/avatarConfig";

const router = useRouter();
const avatarError = ref(false);
const { scenicBgUrl, welcomeText, refresh } = useScenicBackground();

const activePreset = ref(DEFAULT_AVATAR_PRESET);

async function loadAvatarPreset() {
  try {
    const config = await fetchAvatarConfig();
    activePreset.value = normalizeAvatarPresetFromModelPath(config?.model_path, DEFAULT_AVATAR_PRESET);
  } catch {
    // use default
  }
}

function goHome() {
  router.push("/");
}

function enterTourist() {
  router.push("/tourist/select");
}

onMounted(() => {
  loadAvatarPreset();
  refresh();
});
</script>

<style scoped>
.welcome {
  position: relative;
  width: 100%;
  height: 100vh;
  height: 100dvh;
  color: #f0ece5;
  background: #1a1612;
  overflow: hidden;
}

.bg-img {
  position: absolute;
  inset: 0;
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
  filter: blur(8px) saturate(0.4) brightness(0.55);
  transform: scale(1.05);
}

.bg-veil {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 50% 40% at 50% 40%, transparent 0%, rgba(20, 16, 10, 0.55) 80%),
    radial-gradient(ellipse 70% 60% at 50% 100%, rgba(20, 16, 8, 0.5) 0%, transparent 70%);
}

.avatar-layer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 16vh;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.avatar-aura {
  position: absolute;
  inset: -10% -20%;
  border-radius: 50%;
  background: radial-gradient(ellipse 45% 35% at 50% 55%, rgba(217, 164, 65, 0.06) 0%, transparent 70%);
  pointer-events: none;
}

.avatar-frame {
  position: relative;
  width: min(60vh, 72vw);
  aspect-ratio: 3 / 4;
  max-height: min(70vh, calc(100vh - 20vh));
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-fallback,
.avatar-svg {
  width: 100%;
  height: 100%;
}

.content {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  padding-bottom: 6vh;
  pointer-events: none;
}

.content > * {
  pointer-events: auto;
}

.back-btn {
  position: absolute;
  top: 28px;
  left: 28px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  border: 1px solid rgba(255, 250, 242, 0.11);
  border-radius: 999px;
  background: rgba(255, 250, 242, 0.07);
  backdrop-filter: blur(16px);
  color: rgba(232, 228, 219, 0.6);
  font-family: inherit;
  font-size: 14px;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
}

.back-btn:hover {
  border-color: rgba(255, 250, 242, 0.19);
  background: rgba(255, 255, 255, 0.09);
  color: rgba(232, 228, 219, 0.85);
}

.back-arrow {
  display: inline-block;
  transition: transform 0.3s ease;
}

.back-btn:hover .back-arrow {
  transform: translateX(-3px);
}

.hero-text {
  position: absolute;
  top: 8vh;
  left: 0;
  right: 0;
  text-align: center;
  pointer-events: none;
}

.hero-title {
  font-size: clamp(28px, 3.5vw, 42px);
  font-weight: 400;
  letter-spacing: 0.16em;
  color: rgba(232, 228, 219, 0.82);
  text-shadow: 0 0 60px rgba(217, 164, 65, 0.15);
  margin: 0;
}

.hero-sub {
  margin: 8px 0 0;
  font-size: clamp(13px, 1.2vw, 16px);
  letter-spacing: 0.12em;
  color: rgba(217, 164, 65, 0.55);
}

.cta-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  z-index: 1;
}

.welcome-text {
  margin: 0;
  font-size: 15px;
  color: rgba(232, 228, 219, 0.55);
  letter-spacing: 0.06em;
  text-align: center;
  max-width: 480px;
  line-height: 1.65;
}

.glass-btn {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 16px 44px;
  border: 1px solid rgba(217, 164, 65, 0.18);
  border-radius: 999px;
  background: rgba(255, 250, 242, 0.09);
  backdrop-filter: blur(20px);
  color: rgba(232, 228, 219, 0.85);
  font-family: inherit;
  font-size: 17px;
  font-weight: 400;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: border-color 0.35s cubic-bezier(0.22, 1, 0.36, 1), background 0.35s cubic-bezier(0.22, 1, 0.36, 1), color 0.35s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.35s cubic-bezier(0.22, 1, 0.36, 1);
  box-shadow: 0 0 30px rgba(217, 164, 65, 0.06);
}

.glass-btn:hover {
  border-color: rgba(217, 164, 65, 0.3);
  background: rgba(255, 250, 242, 0.13);
  color: rgba(232, 228, 219, 0.95);
  box-shadow: 0 0 50px rgba(217, 164, 65, 0.12), 0 0 80px rgba(217, 164, 65, 0.05), inset 0 1px 0 rgba(255, 250, 242, 0.07);
}

.glass-btn:active {
  transform: scale(0.97);
  background: rgba(255, 250, 242, 0.05);
}

.glass-btn:focus-visible {
  outline: 2px solid #d9a441;
  outline-offset: 3px;
}

.btn-arrow {
  display: inline-block;
  transition: transform 0.35s ease;
}

.glass-btn:hover .btn-arrow {
  transform: translateX(3px);
}

@media (prefers-reduced-motion: reduce) {
  .glass-btn {
    transition: none;
  }

  .glass-btn:hover .btn-arrow {
    transform: none;
  }
}

@media (max-width: 860px) {
  .avatar-layer {
    bottom: 20vh;
  }

  .avatar-frame {
    width: min(45vh, 75vw);
    max-height: 55vh;
  }

  .hero-text {
    top: 5vh;
  }

  .content {
    padding-bottom: 5vh;
  }

  .glass-btn {
    padding: 14px 34px;
    font-size: 15px;
  }
}
</style>
