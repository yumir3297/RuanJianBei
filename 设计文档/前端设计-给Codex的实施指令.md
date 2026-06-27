# 前端设计优化 — Codex 实施方案

> 给 Codex 执行，不要试图一次性改完所有文件。按 Step 顺序逐个做，每完成一个 Step 运行 `npm run dev` 确认不崩。

## 总体设计方向

**左数字人 + 右对话 + 底证据** 三区布局，去 AI 装饰味（删所有渐变圆环、纹样背景、英文小标签、多层阴影），追求工具感——白底、浅灰细线边框、高对比度、大字号。

---

## Step 0：统一 CSS 变量（必须先做）

**文件**：`frontend/src/style.css`

**操作**：用以下内容**完全替换**文件现有内容：

```css
:root {
  /* 品牌色（灵山青绿） */
  --brand:        #0f766e;
  --brand-light:  #14b8a6;
  --brand-bg:     #f0fdfa;

  /* 强调色（金黄） */
  --accent:       #b45309;
  --accent-bg:    #fffbeb;

  /* 中性色 */
  --bg:           #f8f9fa;
  --surface:      #ffffff;
  --border:       #dee2e6;
  --border-light: #e9ecef;

  /* 文字 */
  --text:         #212529;
  --text-secondary: #6c757d;
  --text-tertiary:  #adb5bd;

  /* 间距（4px 体系） */
  --space-xs: 4px;  --space-sm: 8px;
  --space-md: 12px; --space-lg: 16px;
  --space-xl: 20px; --space-2xl: 24px;
  --space-3xl: 32px;

  /* 圆角 */
  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px;

  /* 字号（户外可读优先） */
  --text-xs:  12px; --text-sm:  13px;
  --text-base: 15px; --text-lg:  17px;
  --text-xl:  20px; --text-2xl: 24px;

  /* 只有一个阴影，极度克制 */
  --shadow: 0 1px 3px rgba(0,0,0,0.06);
}

* { box-sizing: border-box; }

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: var(--text-base);
  line-height: 1.65;
  color: var(--text);
  background: var(--bg);
}

a { color: var(--brand); text-decoration: none; }
a:hover { text-decoration: underline; }
```

---

## Step 1：简化 App.vue 顶栏

**文件**：`frontend/src/App.vue`

**改动**：

1. **样式部分**：删除 `.topbar` 的 `backdrop-filter: blur(14px)`、`rgba` 半透明背景，改为纯白背景 + 底部浅灰边框：

```css
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
}
```

2. 把 `h1` 字号从 28px 降到 22px；删掉 `p` 的描述文字（那行"首版骨架…"在正式展示里不必要），替换为：

```html
<h1>灵山胜境 AI 数字导游</h1>
```

3. `.topbar-nav` 里的 RouterLink 样式简化——不需要 `font-weight: 600`，普通 14px 文字即可。

4. `.page-body` padding 改为 `24px`（去掉 40px 底部）。

---

## Step 2：重做 ChatView 布局（核心）

**文件**：`frontend/src/views/tourist/ChatView.vue`

这是改动最大的文件。当前结构是一堆面板纵向堆叠。新结构是**左栏（数字人+选择器）+ 右栏（对话）+ 底条（来源）**。

### 2.1 模板结构（替换 `<template>` 全部内容）

```html
<template>
  <div class="guide-layout">
    <!-- ======== 左栏：数字人 + 选择器 ======== -->
    <aside class="guide-left">
      <!-- 数字人展示区 -->
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

      <!-- 音频波形占位 -->
      <div v-if="avatarState === 'speaking' || avatarState === 'listening'" class="audio-bar">
        <span class="audio-bar-label">{{ avatarState === 'listening' ? '聆听中' : '播报中' }}</span>
        <div class="audio-meter">
          <span v-for="i in 12" :key="i" class="audio-meter-bar" />
        </div>
      </div>

      <!-- 目标选择器（紧凑版） -->
      <GoalSelector />
    </aside>

    <!-- ======== 右栏：对话 + 输入 ======== -->
    <section class="guide-chat">
      <!-- 消息列表 -->
      <div ref="messageListRef" class="message-list">
        <article
          v-for="(message, index) in chatStore.messages"
          :key="`${message.role}-${index}`"
          :class="['message-item', message.role]"
        >
          <p>
            {{ message.content }}
            <span
              v-if="message.role==='assistant' && chatStore.streaming && index===chatStore.messages.length-1 && message.content.length>0"
              class="typing-cursor"
            >|</span>
          </p>
        </article>
      </div>

      <!-- 快捷追问 -->
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

      <!-- 拍照识景区（可展开横条） -->
      <details v-if="visionResult || visionFile" class="vision-details">
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
            <el-button size="small" :disabled="visionAnalyzing || chatStore.streaming" @click="openVisionFilePicker">
              选择图片
            </el-button>
            <el-button size="small" type="primary" :loading="visionAnalyzing" :disabled="!visionFile || chatStore.streaming" @click="handleAnalyzeImage">
              识别
            </el-button>
            <el-button size="small" v-if="visionResult || visionFile" :disabled="visionAnalyzing" @click="clearVisionState">清除</el-button>
          </div>
          <el-alert v-if="visionError" type="error" :title="visionError" :closable="false" />
          <div v-if="visionResult" class="vision-inline">
            <span>{{ visionResult.scene_summary || '已生成检索线索' }}</span>
            <el-button size="small" type="success" :disabled="chatStore.streaming" @click="askFromImage">根据线索提问</el-button>
          </div>
        </div>
      </details>

      <!-- 输入区 -->
      <div class="composer">
        <div class="composer-row">
          <el-radio-group v-model="explanationLevel" size="small">
            <el-radio-button value="child">儿童</el-radio-button>
            <el-radio-button value="adult">标准</el-radio-button>
            <el-radio-button value="expert">专业</el-radio-button>
          </el-radio-group>
          <span class="composer-hint" v-if="interactionStore.breadcrumbs.length">{{ interactionStore.breadcrumbs.join(' / ') }}</span>
        </div>
        <div class="composer-input-row">
          <el-input
            v-model="query"
            placeholder="输入景区问题…"
            @keydown.enter.exact.prevent="handleSubmit"
          />
          <el-button type="primary" :loading="chatStore.streaming" :disabled="speechListening || isRecording || transcribing" @click="handleSubmit">
            发送
          </el-button>
          <el-button v-if="voiceSupported" :disabled="chatStore.streaming || transcribing" @click="toggleRecording">
            {{ speechListening ? '停止' : isRecording ? `结束(${durationSeconds}s)` : '语音' }}
          </el-button>
        </div>
        <div v-if="speechListening" class="speech-hint">
          <span class="speech-dot" /> 正在聆听 — {{ speechPreviewText || '请说话…' }}
        </div>
        <el-alert v-if="voiceErrorMessage" type="warning" :title="voiceErrorMessage" :closable="false" show-icon />
      </div>
    </section>

    <!-- ======== 底条：检索来源 ======== -->
    <footer v-if="chatStore.sources.length" class="source-bar">
      <span class="source-bar-title">依据来源</span>
      <div class="source-bar-items">
        <span v-for="(item, idx) in chatStore.sources" :key="idx" class="source-chip">
          [{{ item.evidence_id || idx + 1 }}] {{ item.title }}
        </span>
      </div>
    </footer>
  </div>
</template>
```

### 2.2 样式（替换 `<style scoped>` 全部内容）

```css
/* ===== 三区主布局 ===== */
.guide-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  grid-template-rows: 1fr auto;
  gap: 0;
  height: calc(100vh - 60px);
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

/* ===== 右栏 ===== */
.guide-chat {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.message-list {
  flex: 1;
  overflow-y: auto;
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

.message-item p { margin: 0; }

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

.vision-file-input { display: none; }

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
  gap: 16px;
}

.composer-hint {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.composer-input-row {
  display: flex;
  gap: 8px;
}

.composer-input-row .el-input { flex: 1; }

.speech-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--accent);
}

.speech-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent);
  animation: speechPulse 1.2s ease-out infinite;
}

@keyframes speechPulse {
  0% { box-shadow: 0 0 0 0 var(--accent); opacity: 1; }
  100% { box-shadow: 0 0 0 8px transparent; opacity: 0.4; }
}

/* ===== 底条 ===== */
.source-bar {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 16px;
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

### 2.3 script 保留

**script `<script setup>` 部分几乎不动**。只需要：
- 删掉 `messageListRef` 旁的 `source-panel` 相关引用（如果有的话），因为来源面板已经从右侧移到底部
- 保留所有现有 composable、store、watch 逻辑
- `scrollToBottom` 逻辑保持不变

---

## Step 3：GoalSelector 去装饰

**文件**：`frontend/src/components/interaction/GoalSelector.vue`

**只改 `<style scoped>`**，删除以下内容：

1. 删掉 `.guide-selector::after`（那个 position:absolute 的大圆环伪元素）——**整个 block 删掉**
2. 删掉 `.guide-selector` 的 `background: linear-gradient(...) repeating-linear-gradient(...)`，改成：

```css
.guide-selector {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
}
```

3. 删掉 `.selector-kicker` 那个英文标签（"GUIDED START"），模板中也删掉对应行
4. `.goal-card` 的 `border-radius: 16px` 改成 `8px`
5. `.guide-selector` 的 `box-shadow` 删掉
6. `.selector-details` 的 `background: rgba(255,255,255,0.72)` 改成 `background: var(--surface)`

---

## Step 4：Dashboard 去装饰

**文件**：`frontend/src/views/admin/Dashboard.vue`

**只改 `<style scoped>`**：

1. 删掉 `.dashboard-hero::after`（大圆环伪元素）
2. 删掉 `.stat-card::after`（卡片底部的彩色装饰条）
3. `.stat-card` 的 `min-height: 154px` 改为 `120px`
4. `.dashboard-hero` 的 `box-shadow` 删掉

---

## Step 5：管理后台其他页面

**KnowledgeManage.vue**：
- 表格上方加一行搜索栏：`<el-input placeholder="搜索知识..." />` + `<el-select>` 分类筛选 + 页码显示

**AnalyticsReport.vue**：
- 参照 `Dashboard.vue` 的 ECharts 接入方式，加一个趋势折线图和一个饼图（代码结构照抄 Dashboard 的 `renderBarChart` 和 `renderPieChart`，数据从 `adminStore.analytics` 取）

**AvatarConfig.vue**：
- 把占位 `el-result` 替换为实际内容：一个数字人预览区（可用 AvatarDisplay 组件）+ 情绪状态切换测试按钮 + Provider 状态指示

---

## 执行纪律

1. **每完成一个 Step，立即运行** `cd frontend ; npm run dev` **确认不崩**
2. **不要跨 Step 改动**——做完 Step 0 再做 Step 1
3. Step 2 改动最大，做完后重点检查：消息列表滚动、发送消息、语音按钮、拍照识景是否都正常
4. 如果某个 Step 改完后页面乱了，**立刻回滚该文件**，不要接着改下一个
5. 所有 CSS 改动只改 `<style scoped>`，不动 `<script>` 部分（除 Step 2 模板重构外）

---

## 期望成品对照

```
┌─────────────────────┬──────────────────────────────────┐
│                     │                                  │
│    ╭─────────╮      │   游客: 灵山大佛有多高？           │
│    │ Live2D  │      │                                  │
│    │ 数字人   │      │   AI: 灵山大佛通高88米，其中       │
│    │ 展示区   │      │   佛体高79米，莲花瓣高9米…          │
│    ╰─────────╯      │                                  │
│                     │                                  │
│    ▂▃▅▃▂ 播报中     │   [儿童|标准|专业]  灵山大佛/景点    │
│                     │   ┌──────────────────┬────┬────┐ │
│   [景点讲解] [话题]  │   │ 输入景区问题…     │发送│语音│ │
│   [路线]  [自由提问] │   └──────────────────┴────┴────┘ │
│                     │                                  │
│   选择景点:          │                                  │
│   灵山大佛 ▾         │                                  │
│                     │                                  │
├─────────────────────┴──────────────────────────────────┤
│ 📎 依据来源  [1]灵山大佛章  [2]景区概况章  [3]官方资料    │
└────────────────────────────────────────────────────────┘
```
