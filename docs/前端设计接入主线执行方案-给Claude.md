# 灵山导览系统 — 前端设计接入主线执行方案

> 本文档是**设计稿 → Vue 项目**的完整执行方案，可交给 Claude / Codex 直接执行。

---

## 零、背景与设计目标

### 当前项目结构
```
d:\桌面\软件杯\frontend\src\
├── style.css                          # 全局样式 + CSS 变量
├── App.vue                            # 根组件（顶栏 + router-view）
├── router/index.js                    # 路由配置
├── views/
│   ├── HomePage.vue                   # 首页（双卡片入口）
│   ├── tourist/ModeSelectView.vue     # 讲解方式选择（全屏选择页）
│   └── tourist/ChatView.vue           # 游览中（40/60 分栏）
├── components/
│   ├── ThreeAvatar.vue                # 3D 数字人组件
│   ├── AvatarDisplay.vue              # SVG 头像降级组件
│   └── interaction/GoalSelector.vue   # 讲解方式卡片选择器
```

### 设计稿来源
参考设计画布项目：`d:\桌面\软件杯\lingshan-redesign\`

### 核心设计原则
1. **数字人始终居中突出**，是所有页面的绝对视觉中心
2. **色彩体系**：深青绿 `#2D5A4B` + 暖金 `#C49B4C` + 温润纸面 `#F5F2EC`
3. **三个页面统一风格**：欢迎页 → 讲解方式选择 → 游览中，数字人在画面中位置不变

---

## 一、CSS 变量替换（`style.css`）

**文件**：`d:\桌面\软件杯\frontend\src\style.css`
**风险**：低（只改颜色值，不影响结构）
**时间**：10 分钟

### 1.1 替换 `:root` 中的颜色变量

将现有第 5-14 行的变量替换为：

```css
:root {
  color-scheme: light;
  font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  color: #2C3A33;
  --lingshan-primary: #2D5A4B;
  --lingshan-accent: #C49B4C;
  --lingshan-accent-light: #f5ecd8;
  --lingshan-gold: #C49B4C;
  --lingshan-gold-deep: #8B6D2B;
  --lingshan-gold-light: #f5ecd8;
  --lingshan-green: #2D5A4B;
  --lingshan-green-deep: #1B2E25;
  --lingshan-green-light: #eaf0eb;
  --lingshan-stone: #6B7A72;
  --lingshan-paper: #F5F2EC;
  --lingshan-ink: #2C3A33;
  --lingshan-line: rgba(45, 90, 75, 0.14);
  --el-color-primary: #2D5A4B;
  --el-color-primary-light-3: #4d7565;
  --el-color-primary-light-5: #7a9a8c;
  --el-color-primary-light-7: #a8bfb5;
  --el-color-primary-light-8: #c5d4ce;
  --el-color-primary-light-9: #e3ebe7;
  --el-color-primary-dark-2: #1B2E25;
}
```

### 1.2 替换 `:root` 的 `background`

将第 22-25 行的 `background` 替换为：

```css
  background:
    radial-gradient(ellipse 60% 40% at 50% 45%, rgba(196, 155, 76, 0.08), transparent),
    linear-gradient(180deg, var(--lingshan-paper) 0%, #ede8e0 100%);
```

### 1.3 新增背景图片 CSS 变量（可替换设计）

在 `:root` 块末尾添加：

```css
  /* 景区背景图 — 替换此处路径即可换背景 */
  --lingshan-scenic-bg: url('/assets/bg-scenic.png');
```

### 1.4 修改顶栏颜色

`App.vue` scoped style 中 `.tourist-shell` 的背景从 `#0f172a` 改为 `var(--lingshan-paper)`。

### 1.5 把梵宫背景图复制到前端项目

```bash
copy "d:\桌面\软件杯\lingshan-redesign\assets\bg-fangong.png" "d:\桌面\软件杯\frontend\public\assets\bg-scenic.png"
```

### 1.6 修改 Element Plus 的 CSS 变量关联色

在 `style.css` 中，确保 `--el-color-primary` 已改为 `#2D5A4B`（见上文），其他 `light-*` 和 `dark-2` 变量按色阶更新。

---

## 二、HomePage.vue — 欢迎页改造

**文件**：`d:\桌面\软件杯\frontend\src\views\HomePage.vue`
**风险**：中（布局结构改变，但逻辑简单）
**时间**：30 分钟

### 设计目标
- 数字人（ThreeAvatar）居中显示，占首屏 55-65% 高度
- 背景使用梵宫模糊图 + 径向渐变遮罩
- 底部引导语 + "开始游览"按钮，与数字人同一中轴线

### 完整模板替换

将 `<template>` 整体替换为：

```html
<template>
  <div class="home-page">
    <!-- 景区背景层 -->
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <div class="home-content">
      <!-- 顶部轻量标题 -->
      <header class="home-top">
        <span class="home-brand">灵山智慧导游</span>
      </header>

      <!-- 数字人区域 -->
      <div class="home-avatar">
        <div class="avatar-glow"></div>
        <div class="avatar-wrapper">
          <ThreeAvatar
            v-if="!avatarError"
            :preset="'hanfu'"
            :emotion="'happy'"
            :is-speaking="false"
            @error="avatarError = true"
          />
          <div v-else class="avatar-fallback">
            <svg viewBox="0 0 280 400" class="avatar-svg">
              <defs>
                <linearGradient id="guideGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#2D5A4B" stop-opacity="0.95"/>
                  <stop offset="100%" stop-color="#1f4638" stop-opacity="0.85"/>
                </linearGradient>
              </defs>
              <ellipse cx="140" cy="55" rx="32" ry="28" fill="url(#guideGrad)" opacity="0.9"/>
              <ellipse cx="140" cy="80" rx="26" ry="30" fill="url(#guideGrad)"/>
              <rect x="132" y="108" width="16" height="12" rx="3" fill="url(#guideGrad)" opacity="0.8"/>
              <path d="M90 125 Q100 118 140 122 Q180 118 190 125 L210 180 Q195 185 185 200 L175 280 Q170 310 160 340 L140 345 L120 340 Q110 310 105 280 L95 200 Q85 185 70 180 Z" fill="url(#guideGrad)"/>
              <path d="M70 180 Q50 200 35 260 Q25 310 20 360 Q18 385 30 395 L60 390 Q55 360 65 320 Q75 270 90 220 Z" fill="url(#guideGrad)" opacity="0.6"/>
              <path d="M210 180 Q230 200 245 260 Q255 310 260 360 Q262 385 250 395 L220 390 Q225 360 215 320 Q205 270 190 220 Z" fill="url(#guideGrad)" opacity="0.6"/>
              <path d="M90 220 Q100 230 120 260 Q140 290 140 310 Q140 290 160 260 Q180 230 190 220 L185 350 Q180 380 170 395 L140 398 L110 395 Q100 380 95 350 Z" fill="url(#guideGrad)" opacity="0.5"/>
              <path d="M90 130 Q70 145 62 175 Q58 195 65 210 Q68 200 72 185 Q78 165 88 148 Z" fill="url(#guideGrad)" opacity="0.75"/>
              <path d="M190 130 Q210 145 218 175 Q222 195 215 210 Q212 200 208 185 Q202 165 192 148 Z" fill="url(#guideGrad)" opacity="0.75"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- 引导文案 + CTA -->
      <div class="home-cta">
        <p class="guide-text">您好，我将陪您游览灵山</p>
        <button class="start-button" @click="enterTourist">开始游览</button>
      </div>

      <!-- 管理端入口（底部小字） -->
      <div class="home-footer-link">
        <a @click="enterAdmin">管理后台</a>
      </div>
    </div>
  </div>
</template>
```

### 修改 `<script setup>`

保持不变，但去掉 `enterAdmin` 中的 `/admin/dashboard` 跳转（如果不想在欢迎页显示），或者改为跳转 `/`（首页）以外的路径。当前可保留。

```js
import { ref } from "vue";
import { useRouter } from "vue-router";
import ThreeAvatar from "../components/ThreeAvatar.vue";

const router = useRouter();
const avatarError = ref(false);

function enterTourist() {
  router.push("/tourist/select");
}
function enterAdmin() {
  router.push("/admin/dashboard");
}
```

### 完整 `<style scoped>` 替换

```css
.home-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  background: var(--lingshan-paper);
}

/* 景区背景层 */
.scenic-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.scenic-bg-img {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(6px) saturate(0.5) brightness(0.45);
}
.scenic-bg-overlay {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse 65% 50% at 50% 55%, transparent 0%, rgba(27,46,37,0.45) 70%, rgba(15,25,18,0.6) 100%);
}

/* 内容层 */
.home-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  min-height: 100vh;
  padding: 20px 24px 32px;
}

/* 顶部标题 */
.home-top {
  padding-top: 12px;
}
.home-brand {
  font-family: "STKaiti", "KaiTi", "STSong", serif;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.16em;
}

/* 数字人区域 */
.home-avatar {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
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
  background: radial-gradient(circle, rgba(196,155,76,0.18) 0%, transparent 70%);
}
.avatar-wrapper {
  position: relative;
  z-index: 1;
  width: 280px;
  height: 420px;
}
.avatar-fallback .avatar-svg {
  width: 100%;
  height: 100%;
}

/* CTA区 */
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
  box-shadow: 0 0 28px rgba(196,155,76,0.3);
}
.start-button:active {
  transform: scale(0.97);
}
@keyframes home-cta-breathe {
  0%, 100% { box-shadow: 0 0 16px rgba(196,155,76,0.2); }
  50% { box-shadow: 0 0 32px rgba(196,155,76,0.4); }
}

/* 管理入口 */
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

@media (prefers-reduced-motion: reduce) {
  .start-button { animation: none; }
}
```

### 注意事项
1. `ThreeAvatar` 组件已存在于 `d:\桌面\软件杯\frontend\src\components\ThreeAvatar.vue`，直接复用
2. 如果 ThreeAvatar 加载失败，显示 SVG 降级占位
3. `bg-scenic.png` 需要确保路径 `d:\桌面\软件杯\frontend\public\assets\bg-scenic.png` 存在（从设计项目复制），前端通过 `/assets/bg-scenic.png` 引用

---

## 三、ModeSelectView.vue + GoalSelector.vue — 讲解方式选择改造

**文件**：`ModeSelectView.vue` 和 `GoalSelector.vue`
**风险**：中（交互逻辑不变，只改布局和样式）
**时间**：45 分钟

### 设计目标
- 数字人保持在画面中央（和欢迎页位置一致）
- 四个讲解方式卡片在底部半透明面板中展示
- **不要**像现在这样全屏覆盖数字人

### ModeSelectView.vue 改造

**方案**：直接在该页面嵌入 ThreeAvatar + 底部选择面板，不再单独渲染 GoalSelector 的全屏选择器。将 GoalSelector 的卡片逻辑内联到 ModeSelectView 中。

将 `<template>` 替换为：

```html
<template>
  <div class="mode-select-page">
    <!-- 景区背景层（同 HomePage） -->
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <div class="mode-content">
      <!-- 顶部 -->
      <header class="mode-top">
        <button class="back-btn" @click="goHome">← 返回</button>
        <span class="mode-brand">灵山智慧导游</span>
      </header>

      <!-- 数字人（同首页位置） -->
      <div class="mode-avatar">
        <div class="avatar-glow"></div>
        <ThreeAvatar
          v-if="!avatarError"
          :preset="'hanfu'"
          :emotion="'happy'"
          :is-speaking="false"
          @error="avatarError = true"
        />
        <!-- 降级 SVG 同 HomePage -->
      </div>

      <!-- 引导文字 -->
      <p class="mode-guide">请选择您偏好的游览方式</p>

      <!-- 四个讲解方式卡片 -->
      <div class="mode-cards">
        <div
          v-for="mode in modes"
          :key="mode.key"
          :class="['mode-card', { selected: selectedMode === mode.key }]"
          @click="selectMode(mode.key)"
        >
          <span v-if="mode.recommended" class="mode-badge">推荐</span>
          <strong class="mode-name">{{ mode.label }}</strong>
          <p class="mode-desc">{{ mode.desc }}</p>
        </div>
      </div>

      <!-- 确认按钮 -->
      <button
        :class="['confirm-btn', { active: selectedMode }]"
        :disabled="!selectedMode"
        @click="confirmMode"
      >确认选择</button>
    </div>
  </div>
</template>
```

`<script setup>` 改造：

```js
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import ThreeAvatar from "../../components/ThreeAvatar.vue";
import { useInteractionStore } from "../../stores/interaction";
import { useChatStore } from "../../stores/chat";

const router = useRouter();
const interactionStore = useInteractionStore();
const chatStore = useChatStore();
const avatarError = ref(false);
const selectedMode = ref(null);

const scenicBgUrl = computed(() => 'var(--lingshan-scenic-bg)' in document.documentElement.style 
  ? 'var(--lingshan-scenic-bg)' 
  : 'url(/assets/bg-scenic.png)'
);

const modes = [
  { key: 'child', label: '亲子游', desc: '适合家庭轻松出行', recommended: true },
  { key: 'leisure', label: '休闲游', desc: '轻松体验，随走随听', recommended: false },
  { key: 'expert', label: '文化深度游', desc: '深入解读历史与文化', recommended: false },
  { key: 'free', label: '自由游览', desc: '按需陪伴，不过度打扰', recommended: false },
];

function selectMode(key) {
  selectedMode.value = selectedMode.value === key ? null : key;
}

function confirmMode() {
  if (!selectedMode.value) return;
  // 根据选择的模式设置 interactionStore
  const mode = modes.find(m => m.key === selectedMode.value);
  if (mode) {
    interactionStore.setMode('free_chat');
    // 如果需要传递讲解级别参数，可扩展 interactionStore
    chatStore.resetConversationContext();
    router.push("/tourist");
  }
}

function goHome() {
  router.push("/");
}
```

**注意**：如果原来的 `interactionStore` 有复杂的模式选择逻辑（景点/话题/路线），建议暂时不删掉 GoalSelector.vue，而是新增一个轻量模式覆盖在 ModeSelectView 中。原有逻辑通过 `interactionStore.setMode('free_chat')` 避开引导链路。

### 样式

```css
.mode-select-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--lingshan-paper);
}
.scenic-bg { /* 同 HomePage */ }
.scenic-bg-img { /* 同 HomePage */ }
.scenic-bg-overlay { /* 同 HomePage */ }

.mode-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100vh;
  padding: 16px 20px 28px;
}
.mode-top {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.back-btn {
  background: none;
  border: none;
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  cursor: pointer;
}
.mode-brand {
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 16px;
  color: rgba(255,255,255,0.85);
  letter-spacing: 0.12em;
}
.mode-avatar {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  width: 220px;
  height: 340px;
  margin-bottom: 10px;
}
.mode-guide {
  margin: 0 0 16px;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 16px;
  color: var(--lingshan-ink);
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
  padding: 18px 12px;
  border: 1px solid var(--lingshan-line);
  border-radius: 14px;
  background: rgba(250,248,244,0.75);
  backdrop-filter: blur(8px);
  cursor: pointer;
  transition: all 0.18s ease;
  text-align: center;
}
.mode-card:hover {
  border-color: var(--lingshan-accent);
  transform: translateY(-2px);
}
.mode-card.selected {
  background: var(--lingshan-primary);
  color: #fff;
  border-color: var(--lingshan-accent);
  border-left: 3px solid var(--lingshan-accent);
}
.mode-card.selected .mode-name,
.mode-card.selected .mode-desc {
  color: #fff;
}
.mode-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--lingshan-ink);
  margin-bottom: 4px;
}
.mode-desc {
  font-size: 12px;
  color: var(--lingshan-stone);
  margin: 0;
  line-height: 1.5;
}
.mode-badge {
  position: absolute;
  top: 6px;
  right: 6px;
  padding: 2px 8px;
  border-radius: 8px;
  background: var(--lingshan-accent);
  color: #3D2E14;
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
  transition: opacity 0.2s;
}
.confirm-btn.active {
  opacity: 1;
  cursor: pointer;
}
.confirm-btn.active:hover {
  filter: brightness(1.08);
}
```

---

## 四、ChatView.vue — 游览中页面改造

**文件**：`d:\桌面\软件杯\frontend\src\views\tourist\ChatView.vue`
**风险**：高（核心页面，逻辑复杂，改动大）
**时间**：2-3 小时

### 设计目标
- 数字人居中（从 40% 左侧 → 画面正中央）
- 左侧：轻量对话气泡区（~280px，半透明，只显示最近 2-3 条）
- 右侧：竖向浮动快捷操作面板（~200px，半透明）
- 底部：导览助手输入栏（语音按钮优先级不低于文本输入）

### 改造策略

由于 ChatView.vue 约 700 行，包含大量 SSE 流式对话、语音识别、拍照识景等复杂逻辑，**不建议全量重写**。采用以下策略：

**保留**
- 所有 `<script setup>` 中的业务逻辑（`sendMessage`, `handleSSE`, `voiceRecognition` 等）
- 所有导入的 composables 和 stores
- `explanationLevel` 讲解方式切换
- `visionPanel` 拍照识景面板

**修改**
- `<template>` 外层布局结构
- `<style scoped>` 全部样式

### 新的布局结构（仅改 HTML/CSS）

将 `<template>` 的顶层结构改为：

```html
<template>
  <section class="tourist-page" :style="touristPageStyle">
    <!-- 景区背景层 -->
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <!-- 顶部轻量栏 -->
    <header class="tourist-top">
      <span class="tourist-brand">灵山智慧导游</span>
      <div class="tourist-top-right">
        <span class="explanation-tag">{{ explanationLevelLabel }}</span>
        <button class="switch-mode-btn" @click="handleChangeMode">切换模式</button>
      </div>
    </header>

    <div class="tourist-three-col">
      <!-- 左：对话气泡（~260px，半透明） -->
      <aside class="chat-left">
        <div ref="messageListRef" class="message-list">
          <article
            v-for="(message, index) in chatStore.messages"
            :key="`${message.role}-${index}`"
            :class="['message-item', message.role]"
          >
            <strong class="message-speaker">
              {{ message.role === "user" ? "游客" : guideDisplayName }}
            </strong>
            <div
              v-if="message.role === 'assistant'"
              class="answer-content"
              v-html="renderAnswer(message.content, index === chatStore.messages.length - 1)"
              @click="handleCitationClick"
            ></div>
            <p v-else>{{ message.content }}</p>
            <span
              v-if="message.role === 'assistant' && chatStore.streaming && index === chatStore.messages.length - 1"
              class="typing-cursor"
            >|</span>
          </article>
        </div>
        <!-- 资料来源折叠 -->
        <div v-if="chatStore.sources.length" class="source-fold">
          <details>
            <summary>本次回答基于 {{ chatStore.sources.length }} 条资料</summary>
            <ul class="source-list">
              <li v-for="(item, i) in chatStore.sources" :key="i">
                <strong>{{ item.title }}</strong>
                <p>{{ item.snippet }}</p>
              </li>
            </ul>
          </details>
        </div>
      </aside>

      <!-- 中：数字人 -->
      <div class="chat-center">
        <div class="avatar-glow"></div>
        <ThreeAvatar
          v-if="!avatarError"
          :preset="avatarConfig.preset || 'hanfu'"
          :emotion="avatar.currentEmotion.value"
          :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
          @loaded="handleAvatarLoaded"
          @error="handleAvatarLoadError"
        />
        <AvatarDisplay v-else :state="avatarState" :emotion="avatar.currentEmotion.value" />
      </div>

      <!-- 右：快捷操作（~180px） -->
      <aside class="chat-right">
        <div class="quick-section">
          <span class="quick-label">常用提问</span>
          <button v-for="q in quickQuestions" :key="q" @click="handleClusterPrompt(q)">{{ q }}</button>
        </div>
        <div class="mode-section">
          <span class="quick-label">讲解方式</span>
          <el-radio-group v-model="explanationLevel" size="small">
            <el-radio-button value="child">亲子</el-radio-button>
            <el-radio-button value="adult">休闲</el-radio-button>
            <el-radio-button value="expert">深度</el-radio-button>
          </el-radio-group>
        </div>
        <!-- 拍照识景入口 -->
        <button class="vision-trigger" @click="toggleVisionPanel">
          📷 拍照识景
        </button>
      </aside>
    </div>

    <!-- 拍照识景面板（展开时显示） -->
    <div v-if="visionPanelOpen || visionFile || visionResult" class="vision-drawer">
      <!-- 保持原有的 vision 面板 HTML，样式微调 -->
    </div>

    <!-- 底部输入栏 -->
    <div class="tourist-input-bar">
      <button class="input-btn" @click="openVisionFilePicker">📷 拍照</button>
      <div class="input-wrapper">
        <input
          v-model="query"
          type="text"
          placeholder="想了解什么？我来为您讲解…"
          @keydown.enter.exact="handleSubmit"
        />
      </div>
      <button class="send-btn" @click="handleSubmit">发送</button>
      <button
        class="voice-btn"
        :class="{ recording: isRecording }"
        @pointerdown="handleVoicePressStart"
        @pointerup="handleVoicePressEnd"
      >
        🎤 语音
      </button>
    </div>

    <!-- 语音识别确认面板（保持原有逻辑） -->
    <div v-if="asrReviewOpen" class="asr-panel">
      <!-- 保持原有 asr-review HTML -->
    </div>
  </section>
</template>
```

### 关键 CSS

```css
.tourist-page {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
.scenic-bg { /* 同 HomePage */ }
.scenic-bg-img { /* 同 HomePage，但 blur 降低 */ filter: blur(5px) saturate(0.5) brightness(0.48); }
.scenic-bg-overlay { /* 同 HomePage */ }

.tourist-top {
  position: relative;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 20px;
  background: rgba(250,248,244,0.5);
  backdrop-filter: blur(10px);
}
.tourist-brand {
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 15px;
  color: var(--lingshan-ink);
  letter-spacing: 0.1em;
}
.tourist-top-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 三列布局 */
.tourist-three-col {
  position: relative;
  z-index: 10;
  flex: 1;
  display: flex;
  gap: 0;
  overflow: hidden;
}

/* 左列 */
.chat-left {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 12px;
  background: rgba(250,248,244,0.78);
  backdrop-filter: blur(8px);
  border-right: 1px solid var(--lingshan-line);
}
.message-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}
.message-item {
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
}
.message-item.assistant {
  background: var(--lingshan-green-light);
  border-left: 3px solid var(--lingshan-primary);
  align-self: flex-start;
}
.message-item.user {
  background: rgba(196,155,76,0.12);
  align-self: flex-end;
}
.message-speaker {
  font-size: 11px;
  font-weight: 600;
  color: var(--lingshan-green-deep);
  display: block;
  margin-bottom: 4px;
}

/* 中列 */
.chat-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  position: relative;
}
.avatar-glow {
  position: absolute;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(196,155,76,0.15) 0%, transparent 70%);
}
/* ThreeAvatar 保持其原有 size */

/* 右列 */
.chat-right {
  width: 200px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: rgba(250,248,244,0.78);
  backdrop-filter: blur(8px);
  border-left: 1px solid var(--lingshan-line);
  overflow-y: auto;
}
.quick-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.quick-section button {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--lingshan-line);
  border-radius: 10px;
  background: rgba(250,248,244,0.8);
  color: var(--lingshan-ink);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}
.quick-section button:hover {
  border-color: var(--lingshan-accent);
  background: rgba(196,155,76,0.08);
}
.quick-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--lingshan-stone);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

/* 底部输入栏 */
.tourist-input-bar {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: rgba(250,248,244,0.88);
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--lingshan-line);
}
.input-wrapper {
  flex: 1;
  min-width: 0;
}
.input-wrapper input {
  width: 100%;
  height: 42px;
  padding: 0 16px;
  border: 1px solid var(--lingshan-line);
  border-radius: 21px;
  background: rgba(248,246,240,0.9);
  color: var(--lingshan-ink);
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s;
}
.input-wrapper input:focus {
  border-color: var(--lingshan-primary);
}

.input-btn, .send-btn {
  flex-shrink: 0;
  padding: 10px 14px;
  border: 1px solid var(--lingshan-line);
  border-radius: 12px;
  background: rgba(250,248,244,0.8);
  color: var(--lingshan-stone);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.input-btn:hover, .send-btn:hover {
  background: rgba(45,90,75,0.08);
  color: var(--lingshan-primary);
}

/* 语音按钮 — 强调态，与文本输入同级 */
.voice-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 20px;
  height: 44px;
  border: 2px solid var(--lingshan-accent);
  border-radius: 22px;
  background: var(--lingshan-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  box-shadow: 0 0 20px rgba(196,155,76,0.25);
  animation: voice-pulse 2.5s ease-in-out infinite;
}
.voice-btn:hover {
  transform: scale(1.04);
  box-shadow: 0 0 30px rgba(196,155,76,0.4);
}
.voice-btn.recording {
  background: #a3412f;
  border-color: #e07b5a;
  animation: recording-pulse 1s ease-in-out infinite;
}
@keyframes voice-pulse {
  0%, 100% { box-shadow: 0 0 20px rgba(196,155,76,0.25); }
  50% { box-shadow: 0 0 36px rgba(196,155,76,0.45); }
}
@keyframes recording-pulse {
  0%, 100% { box-shadow: 0 0 20px rgba(163,65,47,0.3); }
  50% { box-shadow: 0 0 40px rgba(163,65,47,0.5); }
}

@media (prefers-reduced-motion: reduce) {
  .voice-btn { animation: none; }
}
```

### 需要 `<script setup>` 新增的内容

```js
// 新增导入
import { computed } from "vue";

// 新增计算属性
const scenicBgUrl = computed(() => `url(/assets/bg-scenic.png)`);

const quickQuestions = [
  "灵山大佛有多高？",
  "灵山有哪些必看景点？",
  "推荐游览路线是什么？",
  "灵山有什么好吃的？"
];

const explanationLevelLabel = computed(() => ({
  child: '亲子游', adult: '休闲游', expert: '文化深度游'
}[explanationLevel.value] || '休闲游'));

const sourceHighlightIndex = ref(-1);
const sourceDrawerOpen = ref(false);
```

### 注意事项
1. ⚠️ **保留所有原有的 composables、stores、API 调用逻辑**，只改布局 HTML 和 CSS
2. ⚠️ 原有的 `isFreeChatMode` 两种布局统一为新布局，不再区分自由提问/引导模式
3. ⚠️ `explanationLevel` 原在底部输入区，现在移到右侧面板
4. ⚠️ `visionPanel` 拍照识景保留原逻辑，移到上方展开区域
5. ⚠️ `asrReviewOpen` 语音识别确认面板保留原逻辑

---

## 五、执行顺序

按以下顺序执行，每步完成后验证无报错：

| 序号 | 步骤 | 文件 | 预计耗时 | 验证方式 |
|------|------|------|---------|---------|
| 1 | 复制梵宫背景图 | 文件复制 | 1 分钟 | 文件存在 |
| 2 | CSS 变量替换 | `style.css` | 10 分钟 | `npm run dev` 无报错 |
| 3 | HomePage 改造 | `HomePage.vue` | 30 分钟 | 首页显示新布局 |
| 4 | ModeSelectView 改造 | `ModeSelectView.vue` | 45 分钟 | 选择页新布局 |
| 5 | ChatView 改造 | `ChatView.vue` | 2 小时 | 对话、语音、识景正常 |
| 6 | 回归测试 | 全项目 | 30 分钟 | 管理端功能不受影响 |

---

## 六、回滚方案

如果某一步改动导致问题，执行以下回滚：

```bash
# CSS 回滚
git checkout -- frontend/src/style.css

# 页面回滚
git checkout -- frontend/src/views/HomePage.vue
git checkout -- frontend/src/views/tourist/ModeSelectView.vue
git checkout -- frontend/src/views/tourist/ChatView.vue
```

建议在改造前先 `git commit` 当前状态。

---

## 七、验收清单

- [ ] `npm run dev` 正常启动
- [ ] 首页显示数字人居中 + 梵宫背景，点击「开始游览」→ 跳转讲解方式选择
- [ ] 选择页数字人位置同首页，选卡片 + 确认 → 跳转游览中
- [ ] 游览中数字人中央，左对话右操作，语音按钮有呼吸光效且与文本输入同级
- [ ] 语音识别（按住说话）正常工作
- [ ] 拍照识景正常
- [ ] 资料来源正常展示
- [ ] 管理后台页面不受影响
- [ ] Element Plus 组件（el-tag, el-button 等）颜色符合新绿金色系

---

*文档路径：d:\桌面\软件杯\docs\前端设计接入主线执行方案-给Claude.md*
*色彩参考：d:\桌面\软件杯\lingshan-redesign\colors_and_type.css*
*设计稿预览：http://localhost:8899/pages/home.html（需先启动服务器）*
