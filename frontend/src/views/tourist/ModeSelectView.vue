<template>
  <div class="select-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="bg-veil"></div>
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
    </div>

    <button type="button" class="back-btn" @click="goBack">
      <span class="back-arrow">&larr;</span> 返回
    </button>

    <header class="select-header">
      <h1 class="header-title">选择智慧服务</h1>
      <p class="header-sub">滑动浏览不同功能，选择适合你的智慧文旅服务</p>
    </header>

    <div
      ref="carouselAreaRef"
      class="carousel-area"
      @mousedown="onDragStartMouse"
      @touchstart.passive="onDragStartTouch"
    >
      <button
        type="button"
        :class="['carousel-arrow', 'arrow-left', { disabled: activeIndex === 0 }]"
        aria-label="上一项"
        @click.stop="goTo(activeIndex - 1)"
      >&larr;</button>

      <div class="card-track">
        <button
          v-for="(svc, i) in services"
          :key="svc.id"
          type="button"
          class="feature-card"
          :data-index="i"
          :data-level="String(i - activeIndex)"
          :style="{
            '--card-theme': svc.themeColor,
            transform: cardTransform(i),
            transition: isDragging ? 'none' : undefined,
          }"
          :aria-current="i === activeIndex ? 'true' : 'false'"
          :tabindex="i === activeIndex ? 0 : -1"
          @click="handleCardClick(svc)"
        >
          <div class="card-accent-line" :style="{ background: svc.themeColor }"></div>
          <div class="card-heading">
            <span class="card-index">{{ padIndex(i) }}</span>
          </div>
          <div class="card-title">{{ svc.title }}</div>
          <p class="card-desc">{{ svc.description }}</p>
          <div class="card-footer">
            <span class="card-arrow-hint">&rarr;</span>
          </div>
        </button>
      </div>

      <button
        type="button"
        :class="['carousel-arrow', 'arrow-right', { disabled: activeIndex === services.length - 1 }]"
        aria-label="下一项"
        @click.stop="goTo(activeIndex + 1)"
      >&rarr;</button>
    </div>

    <div class="bottom-area">
      <div class="pagination">
        <button
          v-for="(svc, i) in services"
          :key="svc.id"
          type="button"
          :class="['pag-dot', { active: i === activeIndex }]"
          :aria-label="`切换到${svc.title}`"
          @click="goTo(i)"
        ></button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useScenicBackground } from "../../composables/useScenicBackground";

const router = useRouter();
const { scenicBgUrl } = useScenicBackground();

const services = [
  {
    id: "guide",
    title: "数字人导游",
    description: "与虚拟导游「清岚」实时对话 · AI 语音互动 · 身临其境的景点讲解与个性化导览服务",
    themeColor: "#c4964c",
    route: "/tourist",
  },
  {
    id: "explore",
    title: "景点探索",
    description: "热门景点一览 · 特色文化深度解读 · 拍照识景 · 发现灵山每一个角落的故事",
    themeColor: "#2d8a6e",
    route: "/tourist/explore",
  },
  {
    id: "route",
    title: "智能路线",
    description: "基于你的时间与兴趣智能规划 · 最优游览路径推荐 · 不错过每一处精华",
    themeColor: "#b84c3b",
    route: "/tourist/routes",
  },
  {
    id: "quiz",
    title: "智慧问答",
    description: "佛教文化 · 建筑美学 · 历史典故 · 随问随答，满足你的每一份好奇心",
    themeColor: "#4a6d8c",
    route: "/tourist/quiz",
  },
];

const activeIndex = ref(0);
const isDragging = ref(false);
const dragStartX = ref(0);
const dragDelta = ref(0);
const DRAG_THRESHOLD = 60;

const carouselAreaRef = ref(null);

function padIndex(i) {
  return `0${i + 1}`;
}

function getCardWidth() {
  if (typeof document === "undefined") return 340;
  const cards = document.querySelectorAll(".feature-card");
  if (!cards.length) return 340;
  const { width } = getComputedStyle(cards[0]);
  return parseFloat(width) || 340;
}

function cardTransform(i) {
  const cardW = getCardWidth();
  const gap = cardW * 0.38;
  const dist = i - activeIndex.value;
  let tx = dist * (cardW + gap);
  if (isDragging.value) tx += dragDelta.value;
  const absD = Math.abs(dist);
  let scale;
  if (absD === 0) scale = 1;
  else if (absD === 1) scale = 0.84;
  else scale = 0.7;
  return `translate(-50%, -50%) translateX(${tx}px) scale(${scale})`;
}

function goTo(index) {
  if (index === activeIndex.value) return;
  if (index < 0 || index >= services.length) return;
  activeIndex.value = index;
}

function handleCardClick(svc) {
  const idx = services.findIndex((s) => s.id === svc.id);
  if (idx !== activeIndex.value) {
    activeIndex.value = idx;
    return;
  }
  router.push(svc.route);
}

function goBack() {
  router.push("/tourist/welcome");
}

function onKeyDown(e) {
  if (e.key === "ArrowLeft") {
    e.preventDefault();
    if (activeIndex.value > 0) goTo(activeIndex.value - 1);
  } else if (e.key === "ArrowRight") {
    e.preventDefault();
    if (activeIndex.value < services.length - 1) goTo(activeIndex.value + 1);
  } else if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    router.push(services[activeIndex.value].route);
  }
}

function dragStart(clientX) {
  isDragging.value = true;
  dragStartX.value = clientX;
  dragDelta.value = 0;
}

function dragMove(clientX) {
  if (!isDragging.value) return;
  dragDelta.value = clientX - dragStartX.value;
}

function dragEnd() {
  if (!isDragging.value) return;
  isDragging.value = false;
  if (dragDelta.value < -DRAG_THRESHOLD && activeIndex.value < services.length - 1) {
    activeIndex.value++;
  } else if (dragDelta.value > DRAG_THRESHOLD && activeIndex.value > 0) {
    activeIndex.value--;
  }
  dragDelta.value = 0;
}

function onDragStartMouse(e) {
  if (e.target.closest(".carousel-arrow") || e.target.closest(".pag-dot")) return;
  if (e.target.closest(".feature-card")) return;
  dragStart(e.clientX);
  window.addEventListener("mousemove", onGlobalMouseMove);
  window.addEventListener("mouseup", onGlobalMouseUp);
}

function onGlobalMouseMove(e) {
  dragMove(e.clientX);
}

function onGlobalMouseUp() {
  window.removeEventListener("mousemove", onGlobalMouseMove);
  window.removeEventListener("mouseup", onGlobalMouseUp);
  dragEnd();
}

function onDragStartTouch(e) {
  if (e.target.closest(".carousel-arrow") || e.target.closest(".pag-dot")) return;
  if (e.target.closest(".feature-card")) return;
  dragStart(e.touches[0].clientX);
}

function onTouchMove(e) {
  if (isDragging.value) dragMove(e.touches[0].clientX);
}

function onTouchEnd() {
  dragEnd();
}

onMounted(() => {
  document.addEventListener("keydown", onKeyDown);
  const area = carouselAreaRef.value;
  if (area) {
    area.addEventListener("touchmove", onTouchMove, { passive: true });
    area.addEventListener("touchend", onTouchEnd);
  }
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", onKeyDown);
  window.removeEventListener("mousemove", onGlobalMouseMove);
  window.removeEventListener("mouseup", onGlobalMouseUp);
  const area = carouselAreaRef.value;
  if (area) {
    area.removeEventListener("touchmove", onTouchMove);
    area.removeEventListener("touchend", onTouchEnd);
  }
});
</script>

<style scoped>
.select-page {
  position: relative;
  width: 100%;
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #1a1612;
  color: #e8e4db;
  font-family: "Noto Serif SC", "STKaiti", "KaiTi", "STSong", ui-serif, serif;
  user-select: none;
}

.scenic-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.bg-img {
  position: absolute;
  inset: 0;
  background-position: center;
  background-size: cover;
  background-repeat: no-repeat;
  filter: blur(10px) saturate(0.3) brightness(0.4);
  transform: scale(1.06);
}

.bg-veil {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 60% 40% at 50% 35%, transparent 0%, rgba(20, 16, 10, 0.55) 80%),
    radial-gradient(ellipse 80% 50% at 50% 100%, rgba(22, 18, 10, 0.5) 0%, transparent 70%);
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(80px);
  opacity: 0.12;
}

.bg-orb-1 {
  width: 420px;
  height: 420px;
  top: -10%;
  left: -8%;
  background: radial-gradient(circle, #6366f1, transparent);
}

.bg-orb-2 {
  width: 360px;
  height: 360px;
  bottom: 5%;
  right: -6%;
  background: radial-gradient(circle, #d9a441, transparent);
}

.back-btn {
  position: absolute;
  top: 28px;
  left: 28px;
  z-index: 20;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  border: 1px solid rgba(255, 250, 242, 0.09);
  border-radius: 999px;
  background: rgba(255, 250, 242, 0.05);
  backdrop-filter: blur(16px);
  color: rgba(232, 228, 219, 0.55);
  font-family: inherit;
  font-size: 13px;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-btn:hover {
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 250, 242, 0.09);
  color: rgba(232, 228, 219, 0.8);
}

.back-arrow {
  display: inline-block;
  transition: transform 0.3s ease;
}

.back-btn:hover .back-arrow {
  transform: translateX(-3px);
}

.select-header {
  position: relative;
  z-index: 5;
  text-align: center;
  padding: 40px 20px 0;
  pointer-events: none;
}

.header-title {
  font-size: clamp(22px, 2.6vw, 34px);
  font-weight: 400;
  letter-spacing: 0.14em;
  color: rgba(232, 228, 219, 0.85);
  text-shadow: 0 0 40px rgba(217, 164, 65, 0.1);
  margin: 0;
}

.header-sub {
  margin: 8px 0 0;
  font-size: clamp(12px, 1vw, 15px);
  color: rgba(217, 164, 65, 0.45);
  letter-spacing: 0.08em;
}

.carousel-area {
  flex: 1;
  position: relative;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
  touch-action: pan-y;
}

.carousel-arrow {
  position: absolute;
  top: 50%;
  z-index: 15;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 250, 242, 0.11);
  border-radius: 50%;
  background: rgba(10, 8, 5, 0.55);
  backdrop-filter: blur(12px);
  color: rgba(232, 228, 219, 0.55);
  font-size: 28px;
  cursor: pointer;
  transition: all 0.3s ease;
  transform: translateY(-50%);
  outline: none;
}

.carousel-arrow:hover:not(.disabled) {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(10, 8, 5, 0.7);
  color: rgba(232, 228, 219, 0.85);
  box-shadow: 0 0 24px rgba(0, 0, 0, 0.3);
}

.carousel-arrow:active:not(.disabled) {
  transform: translateY(-50%) scale(0.93);
}

.carousel-arrow:focus-visible {
  outline: 2px solid #d9a441;
  outline-offset: 3px;
}

.carousel-arrow.disabled {
  opacity: 0.2;
  pointer-events: none;
}

.arrow-left {
  left: clamp(12px, 3vw, 48px);
}

.arrow-right {
  right: clamp(12px, 3vw, 48px);
}

.card-track {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.feature-card {
  --card-theme: #d9a441;
  position: absolute;
  left: 50%;
  top: 50%;
  width: 416px;
  height: 416px;
  padding: 30px 32px 22px;
  border-radius: 16px;
  border: 1px solid rgba(232, 228, 219, 0.14);
  background: rgba(22, 20, 15, 0.94);
  cursor: pointer;
  transform-origin: center center;
  transition: transform 0.48s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.48s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.48s ease,
    border-color 0.48s ease;
  will-change: transform, opacity;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  outline: none;
  color: inherit;
  font-family: inherit;
  text-align: left;
}

.card-accent-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--card-theme);
  opacity: 0.55;
  transition: opacity 0.48s ease, height 0.48s ease;
}

.card-heading {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.card-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 26px;
  padding: 0 13px;
  border-radius: 5px;
  background: color-mix(in srgb, var(--card-theme) 18%, transparent);
  color: var(--card-theme);
  font-family: "STKaiti", "KaiTi", "STSong", system-ui, sans-serif;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.06em;
  line-height: 1;
}

.card-title {
  font-size: 29px;
  font-weight: 700;
  letter-spacing: 0.06em;
  line-height: 1.2;
  color: rgba(232, 228, 219, 0.96);
  transition: opacity 0.48s ease, color 0.48s ease;
}

.card-desc {
  min-height: 43px;
  margin-top: 14px;
  font-size: 14px;
  line-height: 1.6;
  color: rgba(232, 228, 219, 0.58);
  letter-spacing: 0.04em;
  transition: opacity 0.48s ease, color 0.48s ease;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid rgba(232, 228, 219, 0.1);
  transition: opacity 0.48s ease;
}

.card-arrow-hint {
  width: 45px;
  height: 45px;
  min-width: 45px;
  min-height: 45px;
  border-radius: 50%;
  border: 1px solid rgba(232, 228, 219, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: rgba(232, 228, 219, 0.6);
  background: rgba(255, 250, 242, 0.05);
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1), background 0.35s ease, border-color 0.35s ease;
}

.feature-card[data-level="0"] {
  z-index: 10;
  filter: none;
  border-color: rgba(232, 228, 219, 0.22);
  box-shadow: 0 24px 56px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(232, 228, 219, 0.06);
}

.feature-card[data-level="0"] .card-arrow-hint {
  border-color: rgba(232, 228, 219, 0.28);
  color: #f0ece5;
}

.feature-card[data-level="1"],
.feature-card[data-level="-1"] {
  z-index: 5;
  filter: brightness(78%);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.32);
}

.feature-card[data-level="1"] .card-desc,
.feature-card[data-level="-1"] .card-desc {
  opacity: 0;
}

.feature-card[data-level="1"] .card-footer,
.feature-card[data-level="-1"] .card-footer {
  opacity: 0.35;
}

.feature-card[data-level="2"],
.feature-card[data-level="-2"] {
  z-index: 1;
  filter: brightness(48%);
  box-shadow: none;
  pointer-events: none;
}

.feature-card[data-level="2"] .card-desc,
.feature-card[data-level="-2"] .card-desc,
.feature-card[data-level="2"] .card-footer,
.feature-card[data-level="-2"] .card-footer {
  opacity: 0;
}

.feature-card[data-level="0"]:hover {
  border-color: rgba(232, 228, 219, 0.34);
  box-shadow: 0 32px 64px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(232, 228, 219, 0.08);
}
.feature-card[data-level="0"]:hover .card-accent-line {
  opacity: 0.85;
}
.feature-card[data-level="0"]:hover .card-arrow-hint {
  transform: translateX(4px);
  border-color: rgba(232, 228, 219, 0.44);
  background: rgba(255, 255, 255, 0.1);
}

.feature-card[data-level="1"]:hover,
.feature-card[data-level="-1"]:hover {
  filter: brightness(92%);
}

.feature-card[data-level="1"]:hover .card-desc,
.feature-card[data-level="-1"]:hover .card-desc {
  opacity: 1;
}

.feature-card:focus-visible[data-level="0"] {
  outline: 2px solid color-mix(in srgb, var(--card-theme) 70%, #e8e4db);
  outline-offset: 4px;
}

.bottom-area {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 20px 36px;
  gap: 18px;
}

.pagination {
  display: flex;
  gap: 10px;
  align-items: center;
}

.pag-dot {
  width: 8px;
  height: 8px;
  border-radius: 4px;
  border: none;
  background: rgba(255, 250, 242, 0.16);
  cursor: pointer;
  transition: all 0.35s ease;
  padding: 0;
  outline: none;
}

.pag-dot.active {
  width: 28px;
  background: #d9a441;
  box-shadow: 0 0 12px rgba(217, 164, 65, 0.3);
}

.pag-dot:focus-visible {
  outline: 2px solid #d9a441;
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  .feature-card {
    transition: transform 0.15s ease, opacity 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  }

  .feature-card[data-level="0"]:hover .card-arrow-hint {
    transform: none;
  }
}

@media (max-width: 1199px) and (min-width: 769px) {
  .feature-card {
    width: 420px;
    height: 420px;
    padding: 30px 32px 22px;
  }

  .card-heading {
    margin-bottom: 16px;
  }

  .card-title {
    font-size: 28px;
  }

  .card-desc {
    font-size: 15px;
  }

  .card-index {
    font-size: 15px;
    height: 26px;
    padding: 0 12px;
  }

  .card-arrow-hint {
    width: 48px;
    height: 48px;
    min-width: 48px;
    min-height: 48px;
    font-size: 14px;
  }

  .carousel-arrow {
    width: 56px;
    height: 56px;
    font-size: 22px;
  }

  .select-header {
    padding-top: 30px;
  }

}

@media (max-width: 768px) {
  .select-header {
    padding-top: 24px;
  }

  .header-title {
    font-size: 20px;
  }

  .feature-card {
    width: min(85vw, 340px);
    height: min(85vw, 340px);
    padding: 24px 24px 18px;
    border-radius: 12px;
  }

  .card-index {
    font-size: 14px;
    height: 24px;
    padding: 0 10px;
  }

  .card-heading {
    margin-bottom: 12px;
  }

  .card-title {
    font-size: 22px;
  }

  .card-desc {
    font-size: 13px;
    min-height: 40px;
  }

  .card-footer {
    padding-top: 10px;
  }

  .card-arrow-hint {
    width: 36px;
    height: 36px;
    min-width: 36px;
    min-height: 36px;
    font-size: 14px;
  }

  .carousel-arrow {
    display: none;
  }

  .back-btn {
    top: 14px;
    left: 14px;
    padding: 7px 16px;
    font-size: 12px;
  }

  .bottom-area {
    padding-bottom: 28px;
    gap: 14px;
  }
}
</style>
