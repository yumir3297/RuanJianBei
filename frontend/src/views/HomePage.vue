<template>
  <div class="home-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <div class="home-content">
      <header class="home-top">
        <span class="home-brand">灵山智慧导游</span>
      </header>

      <div class="home-avatar">
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

      <div class="home-cta">
        <p class="guide-text">您好，我将陪您游览灵山</p>
        <button type="button" class="start-button" @click="enterTourist">开始游览</button>
      </div>

      <div class="home-footer-link">
        <a @click="enterAdmin">管理后台</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";

import ThreeAvatar from "../components/ThreeAvatar.vue";

const router = useRouter();
const avatarError = ref(false);
const scenicBgUrl = "var(--lingshan-scenic-bg)";

function enterTourist() {
  router.push("/tourist/select");
}

function enterAdmin() {
  router.push("/admin/dashboard");
}
</script>

<style scoped>
.home-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
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

.home-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  min-height: 100vh;
  width: min(100%, 520px);
  padding: 20px 24px 32px;
}

.home-top {
  padding-top: 12px;
}

.home-brand {
  font-family: "STKaiti", "KaiTi", "STSong", serif;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.16em;
}

.home-avatar {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  width: 100%;
  position: relative;
  padding-bottom: 10px;
}

.avatar-glow {
  position: absolute;
  bottom: 8%;
  left: 50%;
  transform: translateX(-50%);
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(196, 155, 76, 0.18) 0%, transparent 70%);
}

.avatar-wrapper {
  position: relative;
  z-index: 1;
  width: min(280px, 72vw);
  height: min(420px, 58vh);
  min-height: 320px;
}

.avatar-fallback,
.avatar-svg {
  width: 100%;
  height: 100%;
}

.home-cta {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding-bottom: 16px;
}

.guide-text {
  margin: 0;
  font-family: "STKaiti", "KaiTi", "STSong", serif;
  font-size: 17px;
  color: rgba(255, 255, 255, 0.82);
  letter-spacing: 0.08em;
  text-align: center;
}

.start-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 50px;
  padding: 0 48px;
  border: none;
  border-radius: 25px;
  background: var(--lingshan-primary);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  animation: home-cta-breathe 3s ease-in-out infinite;
}

.start-button:hover {
  transform: scale(1.04);
  box-shadow: 0 0 28px rgba(196, 155, 76, 0.3);
}

.start-button:active {
  transform: scale(0.97);
}

@keyframes home-cta-breathe {
  0%,
  100% {
    box-shadow: 0 0 16px rgba(196, 155, 76, 0.2);
  }

  50% {
    box-shadow: 0 0 32px rgba(196, 155, 76, 0.4);
  }
}

.home-footer-link {
  padding-bottom: 8px;
}

.home-footer-link a {
  color: rgba(255, 255, 255, 0.45);
  font-size: 13px;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.16s;
}

.home-footer-link a:hover {
  color: rgba(255, 255, 255, 0.75);
}

@media (max-width: 640px) {
  .home-content {
    padding: 18px 18px 28px;
  }

  .home-brand {
    font-size: 16px;
  }

  .avatar-wrapper {
    width: min(250px, 76vw);
    height: min(380px, 54vh);
    min-height: 280px;
  }

  .guide-text {
    font-size: 16px;
  }

  .start-button {
    width: min(100%, 280px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .start-button {
    animation: none;
  }
}
</style>
