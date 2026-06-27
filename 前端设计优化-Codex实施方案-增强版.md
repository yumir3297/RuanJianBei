# 前端设计优化 — Codex 实施方案（增强版）

> 给 Codex 执行。不要试图一次性改完所有文件。按 Step 顺序逐个做，每完成一个 Step 后先编译验证，再进入下一步。

---

## 0. 设计目标与执行原则

### 0.1 总体设计方向

采用 **左数字人 + 右对话 + 底部证据来源** 的三区布局。

目标不是做“炫酷 AI 大屏”，而是做一个 **可信、克制、清晰、适合评委演示的景区 AI 数字导游前端**。

视觉关键词：

- 白底
- 浅灰细线边框
- 高对比度文字
- 大字号
- 克制的青绿色品牌强调
- 去掉 AI 生成感装饰
- 数字人有存在感，但对话仍是核心任务

必须删除或避免：

- 多层渐变背景
- 毛玻璃
- 大圆角卡片堆叠
- 发光边框
- 彩色装饰条
- 大圆环伪元素
- 英文小标签，例如 `SCENIC INTELLIGENCE`、`GUIDED START`
- 没有实际功能的装饰性波形、光点、纹理

---

## 1. 执行前必须注意

### 1.1 不要用 `npm run dev` 作为自动验证命令

原指令里的 `npm run dev` 会启动常驻开发服务器，Codex 可能会卡住不退出。

每完成一个 Step，优先运行：

```bash
cd frontend
npm run build
```

如果项目已有这些命令，再补充运行：

```bash
npm run lint
npm run type-check
```

`npm run dev` 只用于人工预览，不作为 Codex 自动验证命令。

### 1.2 修改全局 CSS 前必须先查看原文件

不要无脑完全覆盖 `frontend/src/style.css`。

先查看原文件内容，如果其中已有以下内容，必须保留：

- `@import`
- Element Plus 全局修正
- `html/body/#app` 高度设置
- 全局滚动条样式
- 路由过渡样式
- 其他已有基础 reset

只替换或补充变量与基础样式部分。

### 1.3 拍照识景入口必须始终可见

不要写成：

```html
<details v-if="visionResult || visionFile" class="vision-details">
```

这样会导致初始状态下 `visionResult` 和 `visionFile` 都为空，用户第一次根本看不到“选择图片”入口。

拍照入口必须始终可见。可以用以下两种方式之一：

- 在输入区右侧放一个“拍照”按钮，点击后打开图片选择器。
- 保留 `details` 区域，但不能加 `v-if="visionResult || visionFile"`。

### 1.4 音频波形动画必须有错峰变量

如果 CSS 使用：

```css
animation-delay: calc(var(--i, 0) * 0.08s);
```

模板里必须写：

```html
<span
  v-for="i in 12"
  :key="i"
  class="audio-meter-bar"
  :style="{ '--i': i }"
/>
```

否则所有波形柱会同步动画，看起来像假动效。

### 1.5 页面高度由 App 容器控制，ChatView 不要重复计算

不要在 ChatView 内部直接写：

```css
height: calc(100vh - 60px);
```

因为 App.vue 的 `.page-body` 还有 padding，容易造成页面高度溢出和双滚动条。

推荐：

- App.vue 控制页面可用高度。
- ChatView 使用 `height: 100%`。

### 1.6 证据来源采用“双层证据”

不要只放底部 40px 来源条。底条容易被忽略。

最终方案：

- AI 回复气泡下方显示 1-2 个主要来源。
- 底部来源栏显示完整来源列表。
- 来源 chip 保持克制，不要做成发光卡片。

---

# Step 0：统一 CSS 变量（必须先做）

**文件**：`frontend/src/style.css`

## 0.1 操作方式

不要直接完全替换整个文件。请先读取文件内容，然后：

1. 保留已有必要的 `@import`、全局 reset、`html/body/#app` 高度、Element Plus 修正。
2. 将颜色、字号、间距、圆角变量统一替换为以下版本。
3. 如果原文件没有 `html, body, #app` 高度设置，则补上。

## 0.2 推荐全局样式

```css
:root {
  /* 品牌色（灵山青绿） */
  --brand:        #0f766e;
  --brand-light:  #14b8a6;
  --brand-bg:     #f0fdfa;

  /* 强调色（金黄 / 棕黄，少量用于提示和重点状态） */
  --accent:       #b45309;
  --accent-bg:    #fffbeb;

  /* 中性色 */
  --bg:           #f8f9fa;
  --surface:      #ffffff;
  --border:       #dee2e6;
  --border-light: #e9ecef;

  /* 文字 */
  --text:            #212529;
  --text-secondary:  #6c757d;
  --text-tertiary:   #adb5bd;

  /* 间距（4px 体系） */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 20px;
  --space-2xl: 24px;
  --space-3xl: 32px;

  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;

  /* 字号（户外可读、评委演示优先） */
  --text-xs:  12px;
  --text-sm:  13px;
  --text-base: 15px;
  --text-lg:  17px;
  --text-xl:  20px;
  --text-2xl: 24px;

  /* 顶栏高度，由 App.vue 统一使用 */
  --topbar-height: 60px;

  /* 阴影只保留一个，且极度克制；能不用就不用 */
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  width: 100%;
  height: 100%;
}

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: var(--text-base);
  line-height: 1.65;
  color: var(--text);
  background: var(--bg);
}

a {
  color: var(--brand);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
```

## 0.3 完成后验证

```bash
cd frontend
npm run build
```

---

# Step 1：简化 App.vue 顶栏与页面高度

**文件**：`frontend/src/App.vue`

## 1.1 顶栏样式

删除 `.topbar` 的：

- `backdrop-filter`
- 半透明 `rgba` 背景
- 多层阴影
- 渐变或装饰性背景

改为纯白背景 + 底部浅灰边框：

```css
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  min-height: var(--topbar-height);
  padding: 12px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}
```

## 1.2 标题文案

删除原本正式展示不需要的描述文字，例如“首版骨架……”之类。

保留一个清晰标题：

```html
<h1>灵山胜境 AI 数字导游</h1>
```

标题建议样式：

```css
.topbar h1 {
  margin: 0;
  font-size: 22px;
  line-height: 1.3;
  font-weight: 650;
  color: var(--text);
}
```

## 1.3 导航样式

`.topbar-nav` 里的 RouterLink 简化为普通 14px 文字，不要大圆角胶囊按钮，不要强阴影。

```css
.topbar-nav {
  display: flex;
  align-items: center;
  gap: 16px;
}

.topbar-nav a {
  font-size: 14px;
  color: var(--text-secondary);
}

.topbar-nav a.router-link-active {
  color: var(--brand);
}
```

## 1.4 页面主体高度

`.page-body` 改为由 App.vue 控制高度，避免 ChatView 里重复写 `calc(100vh - 60px)`。

```css
.page-body {
  height: calc(100vh - var(--topbar-height));
  padding: 24px;
  overflow: hidden;
}
```

## 1.5 完成后验证

```bash
cd frontend
npm run build
```

---

# Step 2：重做 ChatView 布局（核心）

**文件**：`frontend/src/views/tourist/ChatView.vue`

这是改动最大的文件。当前结构是一堆面板纵向堆叠。新结构是：

- 左栏：数字人 + 状态 + 导览意图选择器
- 右栏：消息列表 + 快捷追问 + 输入区
- 底栏：完整证据来源
- AI 气泡下方：当前回答的主要证据来源

## 2.1 模板结构

替换 `<template>` 全部内容。

注意：

1. 拍照入口始终可见。
2. 音频波形要设置 `--i`。
3. AI 回复气泡下方增加“主要来源”。
4. 底部来源栏保留完整来源。
5. 输入区属于右侧对话区是合理的，左栏只负责数字人和导览目标，不要把发送/语音按钮分散到左栏。

```html
<template>
  <div class="guide-layout">
    <!-- ======== 左栏：数字人 + 导览目标 ======== -->
    <aside class="guide-left">
      <div class="avatar-zone">
        <Live2DAvatar
          v-if="!avatarError"
          :emotion="avatar.currentEmotion.value"
          :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
          @load-error="handleAvatarLoadError"
        />
        <AvatarDisplay
          v-else
          :state="avatarState"
          :emotion="avatar.currentEmotion.value"
        />
        <div class="avatar-status">{{ chatStore.statusText }}</div>
      </div>

      <div v-if="avatarState === 'speaking' || avatarState === 'listening'" class="audio-bar">
        <span class="audio-bar-label">{{ avatarState === 'listening' ? '聆听中' : '播报中' }}</span>
        <div class="audio-meter" aria-hidden="true">
          <span
            v-for="i in 12"
            :key="i"
            class="audio-meter-bar"
            :style="{ '--i': i }"
          />
        </div>
      </div>

      <div class="guide-intent-title">我想了解</div>
      <GoalSelector />
    </aside>

    <!-- ======== 右栏：对话 + 输入 ======== -->
    <section class="guide-chat">
      <div ref="messageListRef" class="message-list">
        <article
          v-for="(message, index) in chatStore.messages"
          :key="`${message.role}-${index}`"
          :class="['message-item', message.role]"
        >
          <p>
            {{ message.content }}
            <span
              v-if="message.role === 'assistant' && chatStore.streaming && index === chatStore.messages.length - 1 && message.content.length > 0"
              class="typing-cursor"
            >|</span>
          </p>

          <!-- AI 回复气泡下方显示主要来源：只展示最新助手回复的前 2 条来源，避免信息过载 -->
          <div
            v-if="message.role === 'assistant' && index === chatStore.messages.length - 1 && chatStore.sources.length"
            class="message-sources"
          >
            <span class="message-sources-label">依据</span>
            <span
              v-for="(item, idx) in chatStore.sources.slice(0, 2)"
              :key="idx"
              class="message-source-chip"
            >
              [{{ item.evidence_id || idx + 1 }}] {{ item.title }}
            </span>
          </div>
        </article>
      </div>

      <div v-if="chatStore.followups.length" class="followup-row">
        <button
          v-for="item in chatStore.followups"
          :key="item.query"
          :disabled="chatStore.streaming"
          @click="handleFollowup(item.query)"
        >
          {{ item.label }}
        </button>
      </div>

      <!-- 拍照识景：入口必须始终存在，不能加 visionResult/visionFile 的 v-if -->
      <details class="vision-details">
        <summary>拍照识景</summary>
        <div class="vision-content">
          <input
            ref="visionFileInputRef"
            class="vision-file-input"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            @change="handleVisionFileChange"
          />
          <div class="vision-actions">
            <el-button
              size="small"
              :disabled="visionAnalyzing || chatStore.streaming"
              @click="openVisionFilePicker"
            >
              选择图片
            </el-button>
            <el-button
              size="small"
              type="primary"
              :loading="visionAnalyzing"
              :disabled="!visionFile || chatStore.streaming"
              @click="handleAnalyzeImage"
            >
              识别
            </el-button>
            <el-button
              v-if="visionResult || visionFile"
              size="small"
              :disabled="visionAnalyzing"
              @click="clearVisionState"
            >
              清除
            </el-button>
          </div>

          <el-alert
            v-if="visionError"
            type="error"
            :title="visionError"
            :closable="false"
          />

          <div v-if="visionFile && !visionResult" class="vision-inline">
            <span>已选择图片，可点击“识别”生成检索线索。</span>
          </div>

          <div v-if="visionResult" class="vision-inline">
            <span>{{ visionResult.scene_summary || '已生成检索线索' }}</span>
            <el-button
              size="small"
              type="success"
              :disabled="chatStore.streaming"
              @click="askFromImage"
            >
              根据线索提问
            </el-button>
          </div>
        </div>
      </details>

      <div class="composer">
        <div class="composer-row">
          <span class="composer-label">讲解风格</span>
          <el-radio-group v-model="explanationLevel" size="small">
            <el-radio-button value="child">儿童</el-radio-button>
            <el-radio-button value="adult">标准</el-radio-button>
            <el-radio-button value="expert">专业</el-radio-button>
          </el-radio-group>
          <span v-if="interactionStore.breadcrumbs.length" class="composer-hint">
            {{ interactionStore.breadcrumbs.join(' / ') }}
          </span>
        </div>

        <div class="composer-input-row">
          <el-input
            v-model="query"
            placeholder="输入景区问题…"
            @keydown.enter.exact.prevent="handleSubmit"
          />
          <el-button
            type="primary"
            :loading="chatStore.streaming"
            :disabled="speechListening || isRecording || transcribing"
            @click="handleSubmit"
          >
            发送
          </el-button>
          <el-button
            v-if="voiceSupported"
            :disabled="chatStore.streaming || transcribing"
            @click="toggleRecording"
          >
            {{ speechListening ? '停止' : isRecording ? `结束(${durationSeconds}s)` : '语音' }}
          </el-button>
          <el-button
            :disabled="chatStore.streaming || visionAnalyzing"
            @click="openVisionFilePicker"
          >
            拍照
          </el-button>
        </div>

        <div v-if="speechListening" class="speech-hint">
          <span class="speech-dot" /> 正在聆听 — {{ speechPreviewText || '请说话…' }}
        </div>

        <el-alert
          v-if="voiceErrorMessage"
          type="warning"
          :title="voiceErrorMessage"
          :closable="false"
          show-icon
        />
      </div>
    </section>

    <!-- ======== 底栏：完整证据来源 ======== -->
    <footer v-if="chatStore.sources.length" class="source-bar">
      <span class="source-bar-title">依据来源</span>
      <div class="source-bar-items">
        <span
          v-for="(item, idx) in chatStore.sources"
          :key="idx"
          class="source-chip"
        >
          [{{ item.evidence_id || idx + 1 }}] {{ item.title }}
        </span>
      </div>
    </footer>
  </div>
</template>
```

## 2.2 样式结构

替换 `<style scoped>` 全部内容。

```css
/* ===== 三区主布局 ===== */
.guide-layout {
  display: grid;
  grid-template-columns: clamp(280px, 24vw, 340px) 1fr;
  grid-template-rows: 1fr auto;
  gap: 0;
  height: 100%;
  min-height: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  overflow: hidden;
}

/* ===== 左栏 ===== */
.guide-left {
  border-right: 1px solid var(--border);
  background: var(--bg);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  min-width: 0;
}

.avatar-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px 16px;
}

.avatar-status {
  margin-top: 8px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.audio-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px 16px;
  gap: 8px;
}

.audio-bar-label {
  font-size: var(--text-xs);
  color: var(--brand);
}

.audio-meter {
  display: flex;
  gap: 3px;
  align-items: flex-end;
  height: 24px;
}

.audio-meter-bar {
  width: 4px;
  background: var(--brand);
  border-radius: 2px;
  animation: meterPulse 0.6s ease-in-out infinite alternate;
  animation-delay: calc(var(--i, 0) * 0.08s);
}

@keyframes meterPulse {
  from { height: 4px; }
  to { height: 20px; }
}

.guide-intent-title {
  padding: 0 20px 8px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
  font-weight: 600;
}

/* ===== 右栏 ===== */
.guide-chat {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message-item {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  line-height: 1.65;
}

.message-item p {
  margin: 0;
}

.message-item.user {
  align-self: flex-end;
  background: var(--border-light);
  color: var(--text);
}

.message-item.assistant {
  align-self: flex-start;
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--brand);
}

.message-sources {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--border-light);
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.message-sources-label {
  color: var(--text-tertiary);
}

.message-source-chip {
  padding: 1px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  white-space: nowrap;
}

.typing-cursor {
  animation: blink 0.8s infinite;
  color: var(--brand);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 快捷追问 */
.followup-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 20px;
  border-top: 1px solid var(--border-light);
}

.followup-row button {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  font-size: var(--text-sm);
  cursor: pointer;
  color: var(--brand);
}

.followup-row button:hover:not(:disabled) {
  background: var(--brand-bg);
  border-color: var(--brand);
}

.followup-row button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 拍照识景 */
.vision-details {
  border-top: 1px solid var(--border-light);
  font-size: var(--text-sm);
}

.vision-details summary {
  padding: 8px 20px;
  cursor: pointer;
  color: var(--text-secondary);
}

.vision-content {
  padding: 8px 20px 16px;
}

.vision-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.vision-file-input {
  display: none;
}

.vision-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 8px;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

/* 输入区 */
.composer {
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.composer-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.composer-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
}

.composer-hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer-input-row {
  display: flex;
  gap: 8px;
}

.composer-input-row .el-input {
  flex: 1;
}

.speech-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--accent);
}

.speech-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  animation: speechPulse 1.2s ease-out infinite;
}

@keyframes speechPulse {
  0% { box-shadow: 0 0 0 0 rgba(180, 83, 9, 0.35); opacity: 1; }
  100% { box-shadow: 0 0 0 8px rgba(180, 83, 9, 0); opacity: 0.4; }
}

/* ===== 底部完整证据来源 ===== */
.source-bar {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 44px;
  padding: 8px 20px;
  border-top: 1px solid var(--border);
  background: var(--bg);
  font-size: var(--text-sm);
  overflow-x: auto;
}

.source-bar-title {
  color: var(--text-secondary);
  white-space: nowrap;
  font-weight: 600;
}

.source-bar-items {
  display: flex;
  gap: 12px;
}

.source-chip {
  padding: 2px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  font-size: var(--text-xs);
  color: var(--text-secondary);
  white-space: nowrap;
}
```

## 2.3 script 部分

`<script setup>` 部分尽量不动，但允许做以下必要清理：

- 删除旧的 `source-panel` 相关引用。
- 保留所有 composable、store、watch、scrollToBottom 逻辑。
- 确认 `visionFileInputRef`、`openVisionFilePicker`、`handleVisionFileChange`、`handleAnalyzeImage`、`clearVisionState`、`askFromImage` 仍然存在。
- 如果原逻辑没有 `visionFileInputRef`，不要强行写死模板，先根据现有实现补齐对应 ref 和方法。

## 2.4 完成后重点检查

- 消息列表是否能滚动。
- 发送消息是否正常。
- 流式输出时光标是否正常。
- 语音按钮是否正常。
- 拍照按钮是否初始可见。
- 选择图片后是否能识别。
- 识别结果是否能“根据线索提问”。
- AI 回复下方是否显示 1-2 个主要来源。
- 底部来源栏是否显示完整来源。
- 页面是否没有双滚动条。

## 2.5 完成后验证

```bash
cd frontend
npm run build
```

---

# Step 3：GoalSelector 去装饰并重组为“导览意图入口”

**文件**：`frontend/src/components/interaction/GoalSelector.vue`

GoalSelector 不要像一个复杂营销卡片，而要像真实导游入口。

建议信息结构：

```text
我想了解
[景点讲解] [路线推荐]
[文化故事] [自由提问]

当前景点
灵山大佛 ▾
```

## 3.1 删除 AI 味装饰

删除以下内容：

1. `.guide-selector::after` 整个 block。
2. 所有大圆环伪元素。
3. `.guide-selector` 里的 `linear-gradient(...)`、`repeating-linear-gradient(...)`。
4. `.selector-kicker` 英文标签，例如 `GUIDED START`。
5. 过重的 `box-shadow`。
6. 过大的 `border-radius: 16px` 或 `20px`。

## 3.2 推荐样式

```css
.guide-selector {
  margin: 0 16px 20px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.selector-title {
  margin: 0 0 12px;
  font-size: var(--text-base);
  font-weight: 650;
  color: var(--text);
}

.goal-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.goal-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  padding: 10px;
}

.goal-card:hover {
  border-color: var(--brand);
  background: var(--brand-bg);
}

.selector-details {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
  background: var(--surface);
}
```

## 3.3 完成后验证

```bash
cd frontend
npm run build
```

---

# Step 4：Dashboard 去装饰

**文件**：`frontend/src/views/admin/Dashboard.vue`

后台也要去掉 AI 味，但不需要像游客端一样强数字人存在感。后台重点是信息效率。

## 4.1 删除内容

只改 `<style scoped>`，删除：

1. `.dashboard-hero::after` 大圆环伪元素。
2. `.stat-card::after` 卡片底部彩色装饰条。
3. `.dashboard-hero` 过重阴影。
4. 渐变背景和纹理背景。

## 4.2 调整内容

```css
.stat-card {
  min-height: 120px;
}

.dashboard-hero {
  box-shadow: none;
  background: var(--surface);
  border: 1px solid var(--border);
}
```

## 4.3 完成后验证

```bash
cd frontend
npm run build
```

---

# Step 5：管理后台其他页面增强

这一步不要自由发挥 UI 风格，必须延续白底、细线、高对比度、少阴影。

---

## 5.1 KnowledgeManage.vue

**目标**：知识库页面要像“资料管理工具”，不要像展示页。

增加表格上方工具栏：

- 搜索输入框：`<el-input placeholder="搜索知识..." />`
- 分类筛选：`<el-select>`
- 状态筛选：可选，例如“已启用 / 待审核 / 盲区补充”
- 页码或总数显示

布局建议：

```text
[搜索知识...] [分类筛选 v] [状态筛选 v]                 共 128 条
---------------------------------------------------------------
表格
```

注意：

- 不要加渐变背景。
- 不要加大圆角彩色卡片。
- 工具栏高度要紧凑。

完成后验证：

```bash
cd frontend
npm run build
```

---

## 5.2 AnalyticsReport.vue

**目标**：数据报告页能体现演示价值，但不能变成花哨大屏。

参照 `Dashboard.vue` 的 ECharts 接入方式，增加：

1. 趋势折线图：展示问答量 / 语音使用量 / 图片识别量趋势。
2. 饼图：展示问题类型分布或景点关注度。

数据来源：

```js
adminStore.analytics
```

要求：

- 图表容器白底。
- 细线边框。
- 不用发光、不用深色大屏背景。
- 图表标题要说明业务含义，例如“近 7 日交互趋势”，不要写抽象标题。

完成后验证：

```bash
cd frontend
npm run build
```

---

## 5.3 AvatarConfig.vue

**目标**：数字人配置页不能再是空占位，要能体现系统完整性。

把占位 `el-result` 替换为实际内容：

1. 数字人预览区：可使用 `AvatarDisplay` 组件。
2. 情绪状态切换测试按钮：普通、讲解中、开心、思考、聆听。
3. Provider 状态指示：Live2D / TTS / ASR / LipSync。
4. 简单配置说明：例如当前模型、当前语音、口型同步状态。

注意：

- 按配置表单风格排布，不要做成炫酷展板。
- 状态颜色克制，成功用品牌绿，警告用棕黄，错误用系统红。

完成后验证：

```bash
cd frontend
npm run build
```

---

# Step 6：最终人工检查清单

全部 Step 完成后，再做一次完整检查。

## 6.1 视觉检查

确认没有以下残留：

- 英文装饰标签
- 大面积渐变
- 毛玻璃
- 发光边框
- 大圆环伪元素
- 过大的 16px / 20px 圆角
- 过重阴影
- 彩色装饰条
- 意义不明的小图标和装饰线

## 6.2 游客端功能检查

必须逐项检查：

- 数字人区域是否足够明显。
- 对话区是否仍是主要阅读区域。
- 输入框是否明显。
- 发送是否正常。
- 语音入口是否正常。
- 拍照入口是否初始可见。
- 图片识别是否能触发。
- 快捷追问是否正常。
- AI 回复气泡下方是否显示主要来源。
- 底部来源栏是否显示完整来源。
- 页面是否没有双滚动条。
- 小屏或窗口缩小时右侧对话是否不会被左栏挤死。

## 6.3 后台检查

必须逐项检查：

- Dashboard 是否不再像 AI 大屏。
- KnowledgeManage 是否有可用搜索和筛选。
- AnalyticsReport 是否有真实图表区域。
- AvatarConfig 是否不再是空占位。
- 后台整体风格是否统一。

## 6.4 最终验证命令

```bash
cd frontend
npm run build
```

如果项目支持，再运行：

```bash
npm run lint
npm run type-check
```

---

# 期望成品对照

```text
┌─────────────────────┬──────────────────────────────────┐
│                     │                                  │
│    ╭─────────╮      │   游客: 灵山大佛有多高？           │
│    │ Live2D  │      │                                  │
│    │ 数字人   │      │   AI: 灵山大佛通高88米，其中       │
│    │ 展示区   │      │   佛体高79米，莲花瓣高9米…          │
│    ╰─────────╯      │   依据 [1] 灵山大佛章 [2] 官方资料  │
│                     │                                  │
│    ▂▃▅▃▂ 播报中     │   [儿童|标准|专业]  灵山大佛/景点    │
│                     │   ┌──────────────┬────┬────┬────┐ │
│   我想了解           │   │ 输入景区问题… │发送│语音│拍照│ │
│   [景点讲解] [路线]  │   └──────────────┴────┴────┴────┘ │
│   [文化故事] [提问]  │                                  │
│                     │                                  │
│   当前景点           │                                  │
│   灵山大佛 ▾         │                                  │
├─────────────────────┴──────────────────────────────────┤
│ 依据来源  [1]灵山大佛章  [2]景区概况章  [3]官方资料       │
└────────────────────────────────────────────────────────┘
```

---

# 最终原则

不要把页面做“更炫”。

要把页面做得：

- 更可信
- 更清楚
- 更像真实产品
- 更方便评委理解系统能力
- 更少 AI 生成设计痕迹

优先级顺序：

1. 功能入口不能消失。
2. 编译不能崩。
3. 用户动线要清楚。
4. 证据来源要能被评委看见。
5. 视觉保持克制。
