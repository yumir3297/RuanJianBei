<template>
  <div class="home-page">
    <!-- 背景层 -->
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <div class="home-content">
      <!-- 顶栏 -->
      <header class="home-top">
        <div class="top-left">
          <span class="home-brand">灵山胜境</span>
          <span class="top-divider"></span>
          <span class="home-tagline">AI 数字人智慧导览</span>
        </div>
        <button type="button" class="admin-entry" @click="enterAdmin">
          管理后台
        </button>
      </header>

      <!-- 主区域：左右分栏 -->
      <div class="home-hero">
        <!-- 左侧：欢迎语 + 功能亮点 -->
        <div class="hero-text">
          <h1 class="hero-title">
            <span class="title-line">智慧导览</span>
            <span class="title-line title-accent">数字相伴</span>
          </h1>
          <p class="hero-welcome">{{ welcomeText }}</p>

          <div class="feature-grid">
            <div v-for="f in features" :key="f.label" class="feature-item">
              <span class="feature-dot" :style="{ background: f.color }"></span>
              <span class="feature-label">{{ f.label }}</span>
              <span class="feature-desc">{{ f.desc }}</span>
            </div>
          </div>

          <button type="button" class="start-btn" @click="enterTourist">
            开始游览
          </button>
        </div>

        <!-- 右侧：数字人 -->
        <div class="hero-avatar">
          <div class="avatar-pedestal"></div>
          <div class="avatar-wrapper">
            <ThreeAvatar
              v-if="!avatarError"
              preset="hanfu"
              emotion="neutral"
              :is-speaking="false"
              camera-preset="fullbody"
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
          <p class="avatar-label">清岚 · 数字人导览员</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import ThreeAvatar from "../components/ThreeAvatar.vue";
import { fetchDisplayAssets } from "../api/admin";

const router = useRouter();
const avatarError = ref(false);
const scenicBgUrl = "var(--lingshan-scenic-bg)";

const DEFAULT_WELCOME = "欢迎来到灵山胜境，愿您在此感受千年佛韵，尽享山水之美。";
const welcomeText = ref(DEFAULT_WELCOME);

const features = [
  { label: "RAG 100%", desc: "三级重排序精准回答", color: "#0065fd" },
  { label: "盲区闭环", desc: "未知问题自动收集并解决", color: "#10b981" },
  { label: "拍照识景", desc: "Qwen VL 多模态视觉识别", color: "#f59e0b" },
  { label: "拼音口型", desc: "音素级中文唇形同步", color: "#8b5cf6" },
  { label: "分级讲解", desc: "FAQ 三级漏斗精确匹配", color: "#ec4899" },
  { label: "全链路降级", desc: "语义→模糊→兜底容错", color: "#06b6d4" },
];

async function loadWelcomeText() {
  try {
    const assets = await fetchDisplayAssets();
    if (assets?.welcome_text) {
      welcomeText.value = assets.welcome_text;
    }
  } catch {
    // 使用默认值
  }
}

function enterTourist() {
  router.push("/tourist/select");
}

function enterAdmin() {
  router.push("/admin/dashboard");
}

onMounted(loadWelcomeText);
</script>

<style scoped>
.home-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--lingshan-paper);
}

/* ── 背景 ── */
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
  min-height: 100vh;
  padding: 0;
}

/* ── 顶栏 ── */
.home-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.home-brand {
  font-family: "STKaiti", "KaiTi", "STSong", serif;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.88);
  font-weight: 600;
  letter-spacing: 0.12em;
}

.top-divider {
  width: 1px;
  height: 14px;
  background: rgba(255, 255, 255, 0.2);
}

.home-tagline {
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  letter-spacing: 0.04em;
}

.admin-entry {
  padding: 6px 16px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.55);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.admin-entry:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
}

/* ── 主区域 ── */
.home-hero {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  padding: 0 48px 48px;
  gap: 32px;
}

/* ── 左侧文案 ── */
.hero-text {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-title {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-line {
  display: block;
  font-family: "STKaiti", "KaiTi", "STSong", serif;
  font-size: 42px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.92);
  letter-spacing: 0.08em;
  line-height: 1.2;
}

.title-accent {
  background: linear-gradient(90deg, #c49b4c, #e8c87a, #c49b4c);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: shimmer 4s ease-in-out infinite;
}

@keyframes shimmer {
  0%, 100% { background-position: 0% center; }
  50% { background-position: 100% center; }
}

.hero-welcome {
  margin: 0;
  font-family: "STKaiti", "KaiTi", "STSong", serif;
  font-size: 16px;
  color: rgba(255, 255, 255, 0.68);
  line-height: 1.7;
  letter-spacing: 0.04em;
}

/* ── 功能网格 ── */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px 24px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.feature-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.feature-label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.85);
  white-space: nowrap;
}

.feature-desc {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

/* ── CTA 按钮 ── */
.start-btn {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  padding: 14px 36px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  animation: btn-breathe 3s ease-in-out infinite;
}

.start-btn:hover {
  transform: scale(1.04);
  box-shadow: 0 0 32px rgba(16, 185, 129, 0.35);
}

.start-btn:active {
  transform: scale(0.97);
}

@keyframes btn-breathe {
  0%, 100% { box-shadow: 0 0 16px rgba(16, 185, 129, 0.2); }
  50% { box-shadow: 0 0 28px rgba(16, 185, 129, 0.4); }
}

/* ── 右侧数字人 ── */
.hero-avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}

.avatar-pedestal {
  position: absolute;
  bottom: 40px;
  width: 200px;
  height: 24px;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(196, 155, 76, 0.25) 0%, transparent 70%);
  filter: blur(8px);
}

.avatar-wrapper {
  position: relative;
  z-index: 1;
  width: min(300px, 40vw);
  aspect-ratio: 3 / 4;
  max-height: 60vh;
}

.avatar-fallback,
.avatar-svg {
  width: 100%;
  height: 100%;
}

.avatar-label {
  margin-top: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
  letter-spacing: 0.12em;
  text-align: center;
}

/* ── 响应式 ── */
@media (max-width: 900px) {
  .home-hero {
    grid-template-columns: 1fr;
    padding: 0 24px 32px;
    gap: 24px;
  }

  .hero-avatar {
    order: -1;
  }

  .avatar-wrapper {
    width: min(240px, 50vw);
  }

  .title-line {
    font-size: 32px;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style>
