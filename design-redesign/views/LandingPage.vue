<template>
  <div class="landing-page">
    <!-- 左侧 70%：景区图片轮播 -->
    <section class="landing-visual" aria-label="景区实景展示">
      <div class="slideshow">
        <TransitionGroup name="slide-fade">
          <img
            v-for="(slide, index) in slides"
            v-show="index === currentSlide"
            :key="slide.src"
            :src="slide.src"
            :alt="slide.label"
            class="slide-image"
            loading="eager"
          />
        </TransitionGroup>
        <!-- 底部渐变叠加 -->
        <div class="slide-overlay"></div>
      </div>
      <!-- 底部景点标注 -->
      <div class="slide-caption-pill">
        <span class="caption-dot"></span>
        <span class="caption-text">{{ slides[currentSlide].label }}</span>
      </div>
      <!-- 轮播指示器 -->
      <div class="slide-dots">
        <button
          v-for="(slide, index) in slides"
          :key="slide.src"
          class="slide-dot"
          :class="{ active: index === currentSlide }"
          @click="goSlide(index)"
        ></button>
      </div>
    </section>

    <!-- 右侧 30%：入口面板 -->
    <section class="landing-panel">
      <div class="panel-content">
        <div class="panel-accent"></div>
        <h1 class="panel-title">灵山智慧导览</h1>
        <p class="panel-subtitle">AI 数字人智慧导览系统</p>
        <div class="panel-divider"></div>

        <div class="entry-cards">
          <button type="button" class="entry-card" @click="enterTourist">
            <div class="entry-icon tourist-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <div class="entry-info">
              <span class="entry-name">游客端</span>
              <span class="entry-desc">与数字人导游互动</span>
            </div>
            <svg class="entry-arrow" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"/></svg>
          </button>

          <button type="button" class="entry-card" @click="enterAdmin">
            <div class="entry-icon admin-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
            </div>
            <div class="entry-info">
              <span class="entry-name">管理后台</span>
              <span class="entry-desc">知识库与运营管理</span>
            </div>
            <svg class="entry-arrow" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"/></svg>
          </button>
        </div>

        <!-- 特性标签 -->
        <div class="feature-tags">
          <span class="tag">RAG 知识增强</span>
          <span class="tag">多模态交互</span>
          <span class="tag">知识盲区闭环</span>
        </div>

        <footer class="panel-footer">
          灵山胜境景区 &copy; 2026 | 软件杯参赛作品
        </footer>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

const slides = [
  { src: "/assets/slides/灵山大佛.png", label: "灵山大佛" },
  { src: "/assets/slides/灵山梵宫.png", label: "灵山梵宫" },
  { src: "/assets/slides/九龙灌浴.png", label: "九龙灌浴" },
  { src: "/assets/slides/五智门.png", label: "五智门" },
  { src: "/assets/slides/菩提大道.png", label: "菩提大道" },
  { src: "/assets/slides/香月花街.png", label: "香月花街" },
];

const currentSlide = ref(0);
let timer = null;

function goSlide(index) {
  currentSlide.value = index;
}

function startSlideshow() {
  timer = setInterval(() => {
    currentSlide.value = (currentSlide.value + 1) % slides.length;
  }, 5000);
}

function enterTourist() {
  router.push("/tourist/welcome");
}

function enterAdmin() {
  router.push("/admin/dashboard");
}

onMounted(startSlideshow);
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<style scoped>
.landing-page {
  display: grid;
  grid-template-columns: 7fr 3fr;
  min-height: 100vh;
  background: #0e1115;
}

/* ── 左侧轮播 ── */
.landing-visual {
  position: relative;
  overflow: hidden;
}

.slideshow {
  position: relative;
  width: 100%;
  height: 100%;
}

.slide-image {
  position: absolute;
  inset: -4px;
  width: calc(100% + 8px);
  height: calc(100% + 8px);
  object-fit: cover;
  image-rendering: auto;
  filter: blur(1.5px) brightness(0.95) saturate(1.1);
}

.slide-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(14, 17, 21, 0.7) 0%,
    rgba(14, 17, 21, 0.15) 40%,
    transparent 70%
  );
  pointer-events: none;
}

.slide-caption-pill {
  position: absolute;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  border-radius: 999px;
  background: rgba(14, 17, 21, 0.55);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.caption-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #0065fd;
}

.caption-text {
  color: rgba(255, 255, 255, 0.88);
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.06em;
}

.slide-dots {
  position: absolute;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
}

.slide-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  cursor: pointer;
  padding: 0;
  transition: background 0.3s, transform 0.3s;
}

.slide-dot.active {
  background: #0065fd;
  transform: scale(1.3);
}

/* ── 轮播过渡 ── */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: opacity 1.2s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
}

/* ── 右侧面板 ── */
.landing-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0e1115;
  border-left: 1px solid rgba(255, 255, 255, 0.06);
}

.panel-content {
  width: 100%;
  max-width: 360px;
  padding: 48px 32px;
}

.panel-accent {
  width: 40px;
  height: 3px;
  border-radius: 2px;
  background: #0065fd;
  margin-bottom: 24px;
}

.panel-title {
  margin: 0 0 8px;
  color: #f0f2f5;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1.3;
}

.panel-subtitle {
  margin: 0 0 20px;
  color: #7f8d9f;
  font-size: 14px;
  letter-spacing: 0.02em;
}

.panel-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin-bottom: 28px;
}

/* ── 入口卡片 ── */
.entry-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 28px;
}

.entry-card {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 16px 18px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  color: #f0f2f5;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  text-align: left;
}

.entry-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}

.entry-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.entry-icon svg {
  width: 20px;
  height: 20px;
}

.tourist-icon {
  background: rgba(0, 101, 253, 0.12);
  color: #0065fd;
  border-left: 3px solid #0065fd;
}

.admin-icon {
  background: rgba(127, 141, 159, 0.12);
  color: #7f8d9f;
}

.entry-info {
  flex: 1;
  min-width: 0;
}

.entry-name {
  display: block;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.3;
}

.entry-desc {
  display: block;
  font-size: 12px;
  color: #7f8d9f;
  margin-top: 2px;
}

.entry-arrow {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  color: #4a5568;
}

/* ── 特性标签 ── */
.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 36px;
}

.tag {
  padding: 5px 12px;
  border-radius: 6px;
  background: rgba(0, 101, 253, 0.08);
  border: 1px solid rgba(0, 101, 253, 0.15);
  color: rgba(0, 101, 253, 0.8);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.02em;
}

/* ── 页脚 ── */
.panel-footer {
  color: #4a5568;
  font-size: 11px;
  letter-spacing: 0.02em;
}

/* ── 响应式 ── */
@media (max-width: 900px) {
  .landing-page {
    grid-template-columns: 1fr;
    grid-template-rows: 45vh 1fr;
  }

  .landing-visual {
    order: 1;
  }

  .landing-panel {
    order: 2;
    border-left: none;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }

  .panel-content {
    max-width: 100%;
    padding: 32px 24px;
  }
}
</style>
