# ChatView 沉浸式氛围改造方案 — 给 Claude 实施

> **目标**：把当前"工具感白底 + 窄侧边栏数字人"变成 character.ai 风格：大幅角色 + 沉浸背景 + 对话浮层。
> **原则**：只改 CSS 和少量 HTML 结构，不动组件逻辑、Live2D、后端。

---

## 一、当前布局 vs 目标

```
当前（工具感）：                    目标（沉浸感）：
┌────────┬──────────────┐          ┌─────────────────────┐
│        │              │          │                     │
│  数字人 │   对话列表    │          │   数字人（全屏背景）  │
│ (28%)  │              │          │                     │
│        │              │          │  ┌────────────────┐ │
│ 标签文字 │              │          │  │  对话气泡（半透） │ │
│        │              │          │  └────────────────┘ │
│        │   输入框      │          │                     │
└────────┴──────────────┘          │    输入框（底部）    │
                                   └─────────────────────┘
```

**核心差异**：
- 数字人从侧边栏配角 → **全屏视觉中心**
- 背景从白底 → **深色氛围渐变**
- 对话从硬面板 → **半透明浮层**
- 去掉顶部的 `tourist-context-bar` → **最简导航**

---

# 📦 Step 1：改造 ChatView 布局（只改 template + style）

**文件**：`frontend/src/views/tourist/ChatView.vue`

**操作 1**：找到 `<template>` 块，完整替换 `tourist-context-bar` 和 `chat-layout-new` 两个区域：

```html
<template>
  <div class="chat-immersive">
    <!-- ★ 新顶栏：极简 -->
    <header class="chat-topbar">
      <button class="topbar-back" @click="handleChangeMode"
        :disabled="chatStore.streaming || speechListening || isRecording">
        ← 切换模式
      </button>
      <span class="topbar-guide-name">{{ guideDisplayName }}</span>
      <span class="topbar-status">{{ chatStore.statusText }}</span>
    </header>

    <!-- ★ 新布局：数字人全背景 + 对话浮层 -->
    <div class="chat-stage">
      <!-- 数字人铺满背景 -->
      <div class="avatar-backdrop">
        <div class="avatar-backdrop-gradient" />
        <div class="avatar-backdrop-ornament" />
        <div class="avatar-hero">
          <Live2DAvatar
            v-if="!avatarError"
            :model-key="avatarConfig.modelKey"
            :emotion="avatar.currentEmotion.value"
            :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
            :speech-progress="speechProgress"
            :speech-sync-active="activeAudioSegments > 0"
            :viseme-timeline="visemeTimeline"
            @load-error="handleAvatarLoadError"
          />
          <AvatarDisplay
            v-else
            :state="avatarState"
            :emotion="avatar.currentEmotion.value"
          />
        </div>
      </div>

      <!-- 对话浮层（右下） -->
      <div class="chat-overlay">
        <div ref="messageListRef" class="bubble-list">
          <article
            v-for="(message, index) in chatStore.messages"
            :key="`${message.role}-${index}`"
            :class="['chat-bubble', message.role]"
          >
            <div class="bubble-avatar">
              {{ message.role === 'user' ? '我' : guideDisplayName[0] }}
            </div>
            <div class="bubble-body">
              <div class="bubble-name">{{ message.role === 'user' ? '我' : guideDisplayName }}</div>
              <div
                v-if="message.role === 'assistant'"
                class="bubble-text answer-content"
                v-html="renderAnswer(message.content, index === chatStore.messages.length - 1)"
                @click="handleCitationClick"
              />
              <div v-else class="bubble-text">{{ message.content }}</div>
              <span
                v-if="message.role === 'assistant' && chatStore.streaming && index === chatStore.messages.length - 1 && message.content.length > 0"
                class="typing-cursor"
              >|</span>
            </div>
          </article>
        </div>

        <!-- 快捷追问 -->
        <div v-if="chatStore.followups.length" class="followup-strip">
          <button
            v-for="item in chatStore.followups"
            :key="item.query"
            :disabled="chatStore.streaming"
            @click="handleFollowup(item.query)"
          >{{ item.label }}</button>
        </div>

        <!-- 语音提示 -->
        <div v-if="speechListening" class="speech-indicator" aria-live="polite">
          <span class="speech-dot" />
          {{ speechPreviewText || '正在聆听...' }}
        </div>

        <!-- 输入区（极简） -->
        <div class="composer-bar">
          <div class="composer-row">
            <input
              v-model="query"
              class="composer-input"
              placeholder="跟小灵聊聊灵山..."
              @keydown.enter="handleSubmit"
              :disabled="chatStore.streaming || speechListening || isRecording"
            />
            <button
              class="composer-send"
              :disabled="chatStore.streaming || speechListening || isRecording || !query.trim()"
              @click="handleSubmit"
            >
              <span v-if="chatStore.streaming">...</span>
              <span v-else>发送</span>
            </button>
            <button
              v-if="voiceSupported"
              class="composer-voice"
              :class="{ active: speechListening || isRecording }"
              :disabled="chatStore.streaming || transcribing"
              @click="toggleRecording"
            >
              <template v-if="speechListening">⏹</template>
              <template v-else-if="isRecording">{{ durationSeconds }}s</template>
              <template v-else>🎤</template>
            </button>
          </div>
          <div class="composer-extras">
            <button class="extra-btn" :disabled="chatStore.streaming" @click="toggleVisionPanel">📷 识景</button>
            <div class="explanation-tabs">
              <button
                v-for="opt in talkModes"
                :key="opt.value"
                :class="{ active: explanationLevel === opt.value }"
                @click="explanationLevel = opt.value"
              >{{ opt.label }}</button>
            </div>
          </div>
        </div>

        <!-- 资料来源 -->
        <div class="source-strip" :class="{ open: sourceDrawerOpen }">
          <button class="source-strip-toggle" @click="toggleSourceDrawer">
            参考资料
            <span v-if="chatStore.sources.length" class="source-count">{{ chatStore.sources.length }}</span>
          </button>
          <div v-if="sourceDrawerOpen" class="source-strip-list">
            <div v-for="(s, i) in chatStore.sources" :key="i" class="source-item" :class="{ highlight: sourceHighlightIndex === i }">
              <strong>{{ s.title }}</strong>
              <p>{{ s.snippet }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片识别面板（按需弹出） -->
    <div v-if="visionPanelOpen || visionFile || visionResult" class="vision-overlay">
      <!-- 内容保持现有 vision-panel 逻辑不变 -->
    </div>
  </div>
</template>
```

**操作 2**：在 `<script setup>` 顶部新增变量（放到 `import` 之后、`const router` 之后）：

```javascript
import { computed } from "vue"; // 已有则跳过

const guideDisplayName = computed(() => {
  // 根据当前模型显示对应名字
  const modelKey = avatarConfig.value?.modelKey || DEFAULT_MODEL_KEY;
  const modelMap = { shizuku: '小诗', hibiki: '小响', haru: '小春' };
  return modelMap[modelKey] || GUIDE_PERSONA.name;
});

const talkModes = [
  { label: '亲子', value: 'child' },
  { label: '休闲', value: 'adult' },
  { label: '深度', value: 'expert' },
];
```

**操作 3**：找到所有 `<style scoped>` 块，**完整替换**为：

```css
/* ===== ★ 全屏沉浸布局 ===== */
.chat-immersive {
  position: fixed;
  inset: 0;
  top: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #0f172a; /* 深色基底 */
}

/* ---- 极简顶栏 ---- */
.chat-topbar {
  position: relative;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 20px;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
  min-height: 48px;
}
.topbar-back {
  background: none; border: 1px solid rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.6); font-size: 13px;
  padding: 4px 12px; border-radius: 999px; cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}
.topbar-back:hover:not(:disabled) { border-color: rgba(255,255,255,0.3); color: #fff; }
.topbar-back:disabled { opacity: 0.4; cursor: not-allowed; }
.topbar-guide-name {
  flex: 1; color: #fff; font-size: 15px; font-weight: 600;
  font-family: "STKaiti", "KaiTi", serif;
}
.topbar-status {
  color: rgba(255,255,255,0.4); font-size: 12px;
}

/* ---- 数字人全幅背景 ---- */
.chat-stage {
  flex: 1;
  position: relative;
  display: flex;
  overflow: hidden;
  min-height: 0;
}
.avatar-backdrop {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(ellipse 80% 60% at 50% 45%, rgba(15, 118, 110, 0.18) 0%, transparent 60%),
    radial-gradient(ellipse 60% 80% at 30% 60%, rgba(180, 83, 9, 0.06) 0%, transparent 50%),
    radial-gradient(ellipse 40% 40% at 70% 30%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
    linear-gradient(180deg, #0f172a 0%, #1a2332 40%, #162032 100%);
}
.avatar-backdrop-gradient {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.015) 0%, transparent 50%);
}
/* 装饰光点 */
.avatar-backdrop-ornament {
  position: absolute;
  width: 200px; height: 200px; border-radius: 50%;
  top: 15%; left: 60%;
  background: radial-gradient(circle, rgba(184, 137, 79, 0.1), transparent 70%);
  animation: ornament-float 8s ease-in-out infinite;
}
@keyframes ornament-float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-30px, 20px); }
}

.avatar-hero {
  position: relative;
  z-index: 2;
  /* 数字人自适应缩放 */
  width: min(50vw, 540px);
  height: min(85vh, 780px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.avatar-hero :deep(.live2d-wrapper) {
  width: 100% !important;
  height: 100% !important;
}
.avatar-hero :deep(.live2d-container) {
  border-radius: 0 !important;
  background: transparent !important;
}

/* ---- 对话浮层（右下） ---- */
.chat-overlay {
  position: relative;
  z-index: 10;
  width: 420px;
  max-width: 44vw;
  display: flex;
  flex-direction: column;
  margin: 0 0 0 auto;
  padding: 16px 20px 12px;
  background: rgba(15, 23, 42, 0.72);
  backdrop-filter: blur(20px);
  border-left: 1px solid rgba(255, 255, 255, 0.06);
  overflow-y: auto;
}

/* ---- 气泡 ---- */
.bubble-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding: 8px 0 16px;
  min-height: 0;
  scroll-behavior: smooth;
}
.chat-bubble {
  display: flex;
  gap: 10px;
  max-width: 100%;
  animation: bubble-in 0.3s ease-out;
}
@keyframes bubble-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.chat-bubble.user { flex-direction: row-reverse; }

.bubble-avatar {
  width: 34px; height: 34px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600; flex-shrink: 0;
}
.chat-bubble.user .bubble-avatar {
  background: linear-gradient(135deg, #b8894f, #d4a76a);
  color: #1a1206;
}
.chat-bubble.assistant .bubble-avatar {
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #fff;
}

.bubble-body {
  max-width: 78%;
}
.bubble-name {
  font-size: 11px; color: rgba(255,255,255,0.4);
  margin-bottom: 3px;
}
.chat-bubble.user .bubble-body { text-align: right; }

.bubble-text {
  padding: 10px 14px; border-radius: 16px;
  font-size: 14px; line-height: 1.65;
  word-break: break-word;
  color: #e2e8f0;
}
.chat-bubble.user .bubble-text {
  background: rgba(184, 137, 79, 0.18);
  border: 1px solid rgba(184, 137, 79, 0.2);
  border-radius: 16px 4px 16px 16px;
  margin-left: auto;
}
.chat-bubble.assistant .bubble-text {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 4px 16px 16px 16px;
}

/* 回答内容中的 markdown 覆盖 */
.bubble-text :deep(p) { margin: 0 0 6px; }
.bubble-text :deep(p:last-child) { margin: 0; }
.bubble-text :deep(strong) { color: #fbbf24; }
.bubble-text :deep(.citation) {
  background: rgba(184, 137, 79, 0.25);
  border-color: rgba(184, 137, 79, 0.3);
}

.typing-cursor {
  color: #14b8a6; animation: blink 0.8s infinite;
}
@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0; } }

/* ---- 快捷追问 ---- */
.followup-strip {
  display: flex; flex-wrap: wrap; gap: 8px;
  padding: 10px 0 12px;
}
.followup-strip button {
  padding: 6px 14px; border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04); color: #94a3b8;
  font-size: 12px; cursor: pointer;
  transition: background 0.2s, border-color 0.2s, color 0.2s;
}
.followup-strip button:hover:not(:disabled) {
  background: rgba(15, 118, 110, 0.2); border-color: rgba(15, 118, 110, 0.3); color: #5eead4;
}
.followup-strip button:disabled { opacity: 0.3; cursor: not-allowed; }

/* ---- 语音提示 ---- */
.speech-indicator {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; margin-bottom: 8px;
  border-radius: 10px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.15);
  color: #fca5a5; font-size: 13px;
}
.speech-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #ef4444;
  animation: speech-pulse 1.2s ease-out infinite;
}
@keyframes speech-pulse {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5); }
  70% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

/* ---- 输入区 ---- */
.composer-bar {
  border-top: 1px solid rgba(255,255,255,0.06);
  padding-top: 10px;
}
.composer-row {
  display: flex; gap: 8px; align-items: center;
}
.composer-input {
  flex: 1; padding: 10px 14px;
  border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.04); color: #e2e8f0;
  font-size: 14px; outline: none;
  transition: border-color 0.2s;
}
.composer-input:focus { border-color: rgba(15, 118, 110, 0.4); }
.composer-input::placeholder { color: rgba(255,255,255,0.2); }
.composer-input:disabled { opacity: 0.4; }

.composer-send {
  padding: 10px 20px; border-radius: 12px; border: none;
  background: linear-gradient(135deg, #0f766e, #14b8a6);
  color: #fff; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: opacity 0.2s, transform 0.15s;
}
.composer-send:hover:not(:disabled) { opacity: 0.9; transform: scale(1.02); }
.composer-send:disabled { opacity: 0.35; cursor: not-allowed; }

.composer-voice {
  width: 42px; height: 42px; border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.04); color: #94a3b8;
  font-size: 16px; cursor: pointer; transition: 0.2s;
  display: flex; align-items: center; justify-content: center;
}
.composer-voice.active {
  background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.3); color: #fca5a5;
}
.composer-voice:disabled { opacity: 0.3; cursor: not-allowed; }

.composer-extras {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 8px;
}
.extra-btn {
  background: none; border: 1px solid rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.35); font-size: 12px;
  padding: 3px 10px; border-radius: 999px; cursor: pointer;
}
.extra-btn:hover:not(:disabled) { border-color: rgba(255,255,255,0.2); color: #94a3b8; }
.extra-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.explanation-tabs {
  display: flex; gap: 2px;
}
.explanation-tabs button {
  padding: 3px 10px; border-radius: 999px;
  border: 1px solid transparent; background: none;
  color: rgba(255,255,255,0.25); font-size: 12px; cursor: pointer;
  transition: 0.2s;
}
.explanation-tabs button.active {
  background: rgba(15, 118, 110, 0.2); border-color: rgba(15, 118, 110, 0.3); color: #5eead4;
}
.explanation-tabs button:hover:not(.active) { color: rgba(255,255,255,0.5); }

/* ---- 资料来源 ---- */
.source-strip {
  margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.04);
}
.source-strip-toggle {
  width: 100%; padding: 8px 0; background: none; border: none;
  color: rgba(255,255,255,0.25); font-size: 12px; cursor: pointer;
  text-align: left; display: flex; align-items: center; gap: 6px;
}
.source-count {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  background: rgba(15, 118, 110, 0.25); color: #5eead4; font-size: 11px;
}
.source-strip-list {
  display: grid; gap: 8px; padding-bottom: 8px;
}
.source-item {
  padding: 10px 12px; border-radius: 8px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.04);
  font-size: 12px; color: #94a3b8;
}
.source-item strong { display: block; color: #e2e8f0; margin-bottom: 3px; }
.source-item p { margin: 0; line-height: 1.5; }
.source-item.highlight { border-color: rgba(184,137,79,0.4); background: rgba(184,137,79,0.08); }

/* ---- 图片面板 ---- */
.vision-overlay {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  padding: 40px;
}

/* ---- 响应式 ---- */
@media (max-width: 900px) {
  .chat-stage { flex-direction: column; }
  .avatar-backdrop { position: relative; height: 45vh; }
  .avatar-hero { width: 70vw; height: 40vh; }
  .chat-overlay { width: 100%; max-width: 100%; border-left: none; border-top: 1px solid rgba(255,255,255,0.06); }
}

@media (max-width: 500px) {
  .chat-topbar { padding: 8px 12px; }
  .chat-overlay { padding: 12px; }
  .bubble-text { font-size: 13px; }
}
```

---

# 📦 Step 2：改造 App.vue — 游客端隐藏通用页壳

**文件**：`frontend/src/App.vue`

ChatView 已经是 `position: fixed; inset: 0` 全屏沉浸式，所以当路由在游客端时，App.vue 的 `.topbar` 和 `.page-body` padding 会影响显示。

**操作**：在 `<script setup>` 中新增一个计算属性，模板中用 `v-if` 控制：

```javascript
const isTourist = computed(() => {
  return route.path === '/tourist' || route.path === '/tourist/select' || route.path === '/';
});
```

模板改写：

```html
<template>
  <div class="app-shell" :class="{ 'tourist-mode': isTourist }">
    <header v-if="!isTourist" class="topbar">
      <!-- 保持现有内容不变 -->
    </header>
    <main v-if="!isTourist" class="page-body">
      <nav v-if="isAdminRoute" class="admin-nav">
        <!-- 保持现有 -->
      </nav>
      <RouterView />
    </main>
    <!-- 游客端：直接渲染，不套壳 -->
    <RouterView v-if="isTourist" />
  </div>
</template>
```

新增 CSS（在 `<style scoped>` 末尾）：

```css
.tourist-mode {
  background: #0f172a;
}
```

**但这样做会导致两个 RouterView 同时存在。更好的做法：**

```html
<template>
  <div class="app-shell">
    <header v-if="!isTourist" class="topbar">
      <!-- 现有 -->
    </header>
    <main :class="{ 'page-body': !isTourist, 'tourist-shell': isTourist }">
      <nav v-if="isAdminRoute && !isTourist" class="admin-nav">
        <!-- 现有 -->
      </nav>
      <RouterView />
    </main>
  </div>
</template>
```

新增 CSS：

```css
.tourist-shell {
  padding: 0;
  width: 100%;
  max-width: none;
  margin: 0;
  background: #0f172a;
  min-height: 100vh;
}
```

---

# 📦 Step 3：后端角色人格 System Prompt

**文件**：`backend/app/services/llm/prompt_builder.py`（找到你现有的 prompt 文件）

**操作**：在现有系统 Prompt **末尾追加**角色人格设定（不删除已有的事实准确性约束）：

```python
# ===== 角色人格设定 =====
你现在的身份是「灵山胜境」的AI数字导游。你叫 {guide_name}，是一位青春活泼、温柔亲切的导览伙伴。

【对话风格】
- 像朋友一样自然聊天，不要机器人式的逐条罗列
- 适度使用语气词和口语化表达："呢"、"哦"、"哇"、"呀"
- 回答控制在 2-4 句以内，像边走边聊，而不是背导游词
- 每次回答结尾可以自然地引导游客继续话题

【情感表达】
- 介绍美景时：带一点惊喜和赞叹，"您看前面那片竹林，风吹过去沙沙响，特别治愈~"
- 回答不上来时：坦诚而温暖，"这个问题小灵也不太确定呢，要不咱们换个角度看看？"
- 游客表达喜欢时：开心回应，"您也喜欢这里呀！好多游客都说这是灵山最让人流连的角落呢"

【禁止行为】
- 不要说"根据资料显示"、"查询到以下信息"等机器感表述
- 不要超过 5 句话（除非游客明确要求详细介绍）
- 不要编造景区事实——不知道就承认不知道，可以转而介绍旁边的景点
```

---

# 📦 Step 4：微调 Live2D 颜色氛围匹配

**文件**：`frontend/src/components/Live2DAvatar.vue`

在 `<style>` 中加一行（让数字人在深色背景上更突出）：

```css
.live2d-container {
  filter: brightness(1.08) contrast(1.02);
}
```

> 这个值很轻，只是让模型在深色背景上稍微亮一点，不改变原有色彩。

---

# 🧪 验证

```bash
cd frontend && npm run dev
```

逐项检查：

```
□ 游客端全屏深色背景，无白边
□ 数字人大幅居中，占据至少 50% 画面宽度
□ 导航栏极简（半透明深色）
□ 对话气泡圆角、半透明、右侧浮层
□ 输入区底部精致，配色统一
□ 发送消息 → 气泡动画弹出
□ 后退到管理端 → 恢复原有白底工具风格（互不影响）
□ 移动端自适应（900px 以下数字人缩小到上半屏）
□ Console 无报错
□ 已有功能（语音/拍照/快捷追问）正常运作
```

---

# ⚠️ 注意

1. **只改 CSS 和少量 HTML**，不改任何 JS 逻辑——所有现有功能（SSE、语音、图片识别）原封不动
2. **不要动 Live2DAvatar 组件的行为代码**，只加了一行 filter CSS
3. 管理端 `/admin/*` 路径不受影响——`isTourist` computed 只对游客端生效
4. 深色背景 + 半透明面板 = 即使景区资料图片也能透过背景若隐若现，氛围感强
5. 如果 `GUIDE_PERSONA.name` 和模型名字不一致，以 `guideDisplayName` computed 为准
