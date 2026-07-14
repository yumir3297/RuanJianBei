<template>
  <div class="landing">
    <div class="visual">
      <div class="img-stack">
        <img
          v-for="slide in slides"
          :key="slide.id"
          :src="slide.src"
          :alt="slide.label"
          :class="{ active: slide.id === activeImage }"
        />
      </div>
      <div class="scene-label">
        <span class="scene-dot"></span>
        <span class="scene-name">{{ currentLabel }}</span>
      </div>
    </div>

    <section class="panel">
      <div class="panel-accent"></div>

      <div class="link-list">
        <button
          class="nav-link"
          :class="{ active: activeLink === 'tourist' }"
          @mouseenter="activateLink('tourist')"
          @click="enterTourist"
        >
          游客端
          <span class="link-arrow">
            <svg width="150" height="28" viewBox="0 0 150 28" fill="none">
              <path d="M0.5 14H149M149 14L136 1.5M149 14L136 26.5" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </span>
        </button>

        <button
          class="nav-link"
          :class="{ active: activeLink === 'admin' }"
          @mouseenter="activateLink('admin')"
          @click="enterAdmin"
        >
          管理后台
          <span class="link-arrow">
            <svg width="150" height="28" viewBox="0 0 150 28" fill="none">
              <path d="M0.5 14H149M149 14L136 1.5M149 14L136 26.5" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </span>
        </button>
      </div>

      <p class="panel-desc">
        指尖轻触，开启灵山胜境智慧之旅。<br>
        AI 数字人导游伴您遍览胜境风华。
      </p>

      <div class="panel-divider"></div>

      <div class="tags">
        <span class="tag">RAG 知识增强</span>
        <span class="tag">多模态交互</span>
        <span class="tag">知识盲区闭环</span>
      </div>

      <footer class="panel-footer">灵山胜境景区 &copy; 2026 | 软件杯参赛作品</footer>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

const LANDING_STORAGE_KEY = "a5-landing-images-v1";

const router = useRouter();

const defaultSlides = [
  { id: "buddha", src: "/assets/slides/灵山大佛.png", label: "灵山大佛" },
  { id: "palace", src: "/assets/slides/灵山梵宫.png", label: "灵山梵宫" },
  { id: "dragon", src: "/assets/slides/九龙灌浴.png", label: "九龙灌浴" },
  { id: "gate", src: "/assets/slides/五智门.png", label: "五智门" },
  { id: "bodhi", src: "/assets/slides/菩提大道.png", label: "菩提大道" },
  { id: "street", src: "/assets/slides/香月花街.png", label: "香月花街" },
];

function loadLandingImages() {
  try {
    const raw = localStorage.getItem(LANDING_STORAGE_KEY);
    if (!raw) return null;
    const images = JSON.parse(raw);
    if (!Array.isArray(images) || !images.length) return null;
    return images.map((img, idx) => ({
      id: `landing-${idx}`,
      src: img.src,
      label: img.name.replace(/\.[^.]+$/, ""),
    }));
  } catch {
    return null;
  }
}

const landingSlides = loadLandingImages();
const slides = landingSlides || defaultSlides;

const activeLink = ref("tourist");
const activeImage = ref(slides[0]?.id || "");
const currentLabel = ref(slides[0]?.label || "");

const linkMap = computed(() => ({
  tourist: slides[0]?.id || "",
  admin: slides[1]?.id || slides[0]?.id || "",
}));

const labelMap = computed(() => ({
  tourist: slides[0]?.label || "",
  admin: slides[1]?.label || slides[0]?.label || "",
}));

function activateLink(link) {
  activeLink.value = link;
  activeImage.value = linkMap.value[link];
  currentLabel.value = labelMap.value[link];
}

function enterTourist() {
  router.push("/tourist/welcome");
}

function enterAdmin() {
  router.push("/admin/dashboard");
}
</script>

<style scoped>
.landing {
  position: relative;
  height: 100vh;
  height: 100dvh;
  background: #1a1612;
  overflow: hidden;
}

.visual {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 70%;
  overflow: hidden;
}

.visual::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to right,
    #1a1612 0%,
    rgba(11, 11, 15, 0.8) 5%,
    rgba(11, 11, 15, 0.35) 15%,
    transparent 25%
  );
  pointer-events: none;
  z-index: 2;
}

.img-stack {
  position: absolute;
  inset: 0;
}

.img-stack img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0;
  transition: opacity 0.9s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: opacity;
}

.img-stack img.active {
  opacity: 1;
}

.scene-label {
  position: absolute;
  bottom: 36px;
  right: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 22px;
  border-radius: 999px;
  background: rgba(11, 11, 15, 0.5);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  z-index: 3;
}

.scene-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #248550;
  box-shadow: 0 0 8px #248550;
  flex-shrink: 0;
}

.scene-name {
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.85);
}

.panel {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 30%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 48px;
  z-index: 3;
}

.panel-accent {
  width: 36px;
  height: 3px;
  border-radius: 2px;
  background: #248550;
  margin-bottom: 32px;
}

.link-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 28px;
}

.nav-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border: none;
  background: none;
  color: rgba(255, 255, 255, 0.25);
  font-size: clamp(36px, 4.2vw, 56px);
  font-weight: 500;
  letter-spacing: 0.03em;
  cursor: pointer;
  text-align: left;
  transition: color 0.45s cubic-bezier(0.22, 1, 0.36, 1);
  font-family: inherit;
  line-height: 1.15;
}

.nav-link:hover,
.nav-link.active {
  color: rgba(255, 255, 255, 0.65);
}

.link-arrow {
  display: inline-flex;
  align-items: center;
  color: rgba(255, 255, 255, 0.25);
  transform: scale(0.35, 0.55);
  transform-origin: left center;
  transition: transform 0.55s cubic-bezier(0.22, 1, 0.36, 1), color 0.45s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}

.link-arrow svg {
  display: block;
}

.nav-link:hover .link-arrow,
.nav-link.active .link-arrow {
  transform: scale(1, 1);
  color: rgba(255, 255, 255, 0.65);
}

.panel-desc {
  color: rgba(255, 255, 255, 0.35);
  font-size: 15px;
  line-height: 1.75;
  margin-bottom: 32px;
  max-width: 380px;
}

.panel-divider {
  height: 1px;
  background: rgba(255, 250, 242, 0.07);
  margin-bottom: 24px;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 40px;
}

.tag {
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.02em;
  background: rgba(36, 133, 80, 0.12);
  border: 1px solid rgba(36, 133, 80, 0.18);
  color: rgba(59, 130, 246, 0.8);
}

.panel-footer {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.18);
  letter-spacing: 0.03em;
}

@media (max-width: 860px) {
  .panel {
    width: 100%;
    top: auto;
    bottom: 0;
    padding: 40px 28px;
    background: linear-gradient(to top, rgba(11, 11, 15, 0.92) 0%, rgba(11, 11, 15, 0.4) 60%, transparent 100%);
  }

  .visual {
    width: 100%;
  }

  .visual::before {
    background: linear-gradient(
      to bottom,
      #1a1612 0%,
      rgba(11, 11, 15, 0.5) 15%,
      transparent 30%
    );
  }

  .nav-link {
    font-size: clamp(28px, 6vw, 40px);
  }

  .scene-label {
    bottom: 24px;
    right: 24px;
  }
}
</style>
