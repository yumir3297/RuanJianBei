# 设计原型工程化实现计划

> 将 design-redesign/ 下的两个静态原型移植到 Vue 生产代码中。

**Goal:** 把 select-preview.html 的四类服务入口轮播和 chat-preview.html 的三栏聊天布局写入 ModeSelectView.vue 和 ChatView.vue，保留所有现有业务逻辑。

**Architecture:** 采用"替换模板+样式、保留 `<script setup>`"策略。ModeSelectView 获得新视觉（轮播卡片）、ChatView 获得新视觉（三栏布局+Tab切换+快捷服务面板）、内核逻辑全部不动。

**Tech Stack:** Vue 3 + Pinia + Element Plus + Three.js (ThreeAvatar)

---

### 文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `frontend/src/views/tourist/ModeSelectView.vue` | 替换模板+样式为新版轮播 |
| 修改 | `frontend/src/views/tourist/ChatView.vue` | 替换模板+样式为新版三栏布局 |
| 不修改 | `frontend/src/router/index.js` | 路由无需改动 |
| 不修改 | `frontend/src/stores/interaction.js` | 讲解风格逻辑已在 ChatView 中可用 |
| 不修改 | `frontend/src/stores/chat.js` | SSE 流、来源、追问逻辑完整 |
| 不修改 | `frontend/src/composables/useSpeechRecognition.js` | 完整 |
| 不修改 | `frontend/src/api/vision.js` | 完整 |
| 不修改 | `frontend/src/components/ThreeAvatar.vue` | 完整 |

---

### Task 1: ModeSelectView.vue — 四类智慧服务轮播入口

**Files:**
- Modify: `d:\桌面\软件杯\frontend\src\views\tourist\ModeSelectView.vue`

**目标:** 将旧版"亲子/休闲/深度/自由"选择界面替换为 select-preview.html 的 4张轮播卡片（数字人导游/景点探索/智能路线/文化问答），保留讲解风格选择逻辑作为确认后的第二步或嵌入聊天页内。

**Step 1: 备份旧文件**

```powershell
Copy-Item 'd:\桌面\软件杯\frontend\src\views\tourist\ModeSelectView.vue' 'd:\桌面\软件杯\frontend\src\views\tourist\ModeSelectView.vue.bak'
```

**Step 2: 读取 select-preview.html 的模板结构**

从 `d:\桌面\软件杯\design-redesign\select-preview.html` 提取：
- 轮播容器 `.carousel-stage`
- 4张 `.feature-card` 的 HTML 结构
- 左右箭头 `.carousel-arrow`
- 底部分页点 `.carousel-dots`
- CSS 样式全部（背景、卡片、动画、响应式）

**Step 3: 编写新版 ModeSelectView.vue 模板**

```vue
<template>
  <div class="select-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <header class="select-top">
      <button type="button" class="top-back" @click="goHome">← 返回</button>
      <span class="top-brand">灵山智慧导览</span>
      <div class="top-right">
        <span class="top-weather">☀️ 27°C 晴</span>
        <span class="top-crowd">🟢 舒适</span>
      </div>
    </header>

    <div class="carousel-stage" ref="stageRef"
         @mousedown="dragStart" @mousemove="dragMove" @mouseup="dragEnd"
         @touchstart.passive="dragStart" @touchmove="dragMove" @touchend="dragEnd">
      <div class="carousel-track" :style="{ transform: `translateX(calc(-${activeIndex * 100}% + ${dragOffset}px))` }">
        <div v-for="(service, i) in services" :key="i"
             class="feature-card" :class="{ active: i === activeIndex }"
             @click="confirmService(i)">
          <div class="card-icon">{{ service.icon }}</div>
          <h2 class="card-title">{{ service.title }}</h2>
          <p class="card-desc">{{ service.desc }}</p>
          <span class="card-hint">点击进入 →</span>
        </div>
      </div>
    </div>

    <div class="carousel-dots">
      <button v-for="(_, i) in services" :key="i"
              :class="['dot', { active: i === activeIndex }]"
              @click="activeIndex = i" />
    </div>

    <div class="style-panel" v-if="showStylePicker">
      <p>选择讲解深度</p>
      <div class="style-options">
        <button v-for="s in styleOptions" :key="s.key"
                @click="selectStyle(s.key)"
                :class="{ picked: selectedStyle === s.key }">
          {{ s.label }}
        </button>
      </div>
      <button class="go-btn" @click="enterApp" :disabled="!selectedStyle">开始导览</button>
    </div>
  </div>
</template>
```

**Step 4: 编写 `<script setup>`**

```js
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useInteractionStore } from '@/stores/interaction'

const GUIDE_STYLE_STORAGE_KEY = 'a5-pending-guide-style-v1'
const router = useRouter()
const interactionStore = useInteractionStore()

const services = [
  { icon: '🎙️', title: '数字人导游', desc: '与虚拟导游「清岚」实时对话 · AI 语音互动', route: '/tourist', mode: 'free_chat' },
  { icon: '🏯', title: '景点探索', desc: '热门景点一览 · 特色文化深度解读 · 拍照识景', route: '/tourist', mode: 'attraction' },
  { icon: '🗺️', title: '智能路线', desc: '基于你的时间与兴趣智能规划 · 最优游览路径推荐', route: '/tourist', mode: 'route' },
  { icon: '💬', title: '文化问答', desc: '佛教文化 · 建筑美学 · 历史典故 · 随问随答', route: '/tourist', mode: 'topic' },
]

const styleOptions = [
  { key: 'child', label: '儿童（简单生动）' },
  { key: 'adult', label: '标准（适中）' },
  { key: 'expert', label: '专业（深度讲解）' },
]

const activeIndex = ref(0)
const showStylePicker = ref(false)
const selectedStyle = ref('adult')
const dragOffset = ref(0)
const isDragging = ref(false)
let dragStartX = 0

function confirmService(index) {
  activeIndex.value = index
  const svc = services[index]
  interactionStore.setMode(svc.mode)
  showStylePicker.value = true
}

function selectStyle(key) { selectedStyle.value = key }

function enterApp() {
  sessionStorage.setItem(GUIDE_STYLE_STORAGE_KEY, selectedStyle.value)
  router.push('/tourist')
}

function goHome() { router.push('/') }

// Carousel drag
function dragStart(e) {
  isDragging.value = true
  dragStartX = e.touches ? e.touches[0].clientX : e.clientX
}
function dragMove(e) {
  if (!isDragging.value) return
  const x = e.touches ? e.touches[0].clientX : e.clientX
  dragOffset.value = x - dragStartX
}
function dragEnd() {
  if (!isDragging.value) return
  isDragging.value = false
  const threshold = 80
  if (dragOffset.value > threshold && activeIndex.value > 0) activeIndex.value--
  else if (dragOffset.value < -threshold && activeIndex.value < services.length - 1) activeIndex.value++
  dragOffset.value = 0
}
</script>
```

**Step 5: 编写 `<style scoped>`**

直接从 select-preview.html 复制全部 CSS 并适配 Vue scoped 语法（将 `.class {}` 替换为已存在的 scoped 写法，关键尺寸保持不变：背景暗色、卡片 280×360、圆角12px、标题 24px、描述 14px）。

---

### Task 2: ChatView.vue — 三栏布局 + 对话/来源Tab + 快捷服务面板

**Files:**
- Modify: `d:\桌面\软件杯\frontend\src\views\tourist\ChatView.vue`

**目标:** 将 chat-preview.html 的三栏布局、对话/来源 Tab 切换、右侧快捷服务面板、拍照按钮、语音按钮的视觉结构移植到 ChatView.vue，保留所有 `<script setup>` 业务逻辑。

**Step 1: 备份旧文件**

```powershell
Copy-Item 'd:\桌面\软件杯\frontend\src\views\tourist\ChatView.vue' 'd:\桌面\软件杯\frontend\src\views\tourist\ChatView.vue.bak'
```

**Step 2: 重写模板结构（共3个区块）**

```vue
<template>
  <section class="tourist-page">
    <!-- 背景层 -->
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <!-- ① 顶栏 -->
    <button type="button" class="back-btn" @click="goBack">← 返回</button>
    <div class="top-right">
      <span class="top-brand">{{ GUIDE_PERSONA.name }}</span>
      <div class="top-status-row">
        <span class="status-item"><span class="status-dot status-dot--ready"></span>{{ avatarConfig.modelLabel || '人物模型' }}</span>
        <span class="status-item"><span class="status-dot status-dot--live"></span>{{ ttsProviderLabel }}</span>
        <span class="status-item"><span class="status-dot status-dot--weather"></span>语音识别就绪</span>
      </div>
    </div>

    <!-- ② 中央舞台 -->
    <div class="tourist-stage">
      <div class="chat-center">
        <div class="top-caption">
          <span class="caption-kicker">清岚 · 数字人导游</span>
          <span class="caption-weather">☀️ 27°C 晴</span>
        </div>
        <div class="crowd-indicator" data-level="green">
          <span class="crowd-dot"></span>当前景区人数：舒适
        </div>
        <div class="avatar-stage">
          <ThreeAvatar ... />
        </div>
      </div>

      <!-- ③ 左卡片：对话/来源 Tab -->
      <aside class="side-card" :class="{ speaking: chatStore.streaming }">
        <div class="side-card-head">
          <div class="side-card-tabs">
            <button :class="['side-card-tab', { active: activeTab === 'chat' }]" @click="activeTab = 'chat'">对话</button>
            <button :class="['side-card-tab', { active: activeTab === 'source' }]" @click="activeTab = 'source'">来源</button>
          </div>
        </div>
        <!-- 对话视图 -->
        <div :class="['side-card-body', { hidden: activeTab !== 'chat' }]" ref="messageListRef">
          <article v-for="(message, index) in chatStore.messages" :key="`${message.role}-${index}`" :class="['msg-item', message.role]">
            <div class="msg-bubble" v-html="message.role === 'assistant' ? renderAnswer(message.content, index === chatStore.messages.length - 1) : message.content" />
          </article>
        </div>
        <!-- 来源视图 -->
        <div :class="['side-card-body', { hidden: activeTab !== 'source' }]">
          <ul class="source-list" v-if="chatStore.sources.length">
            <li v-for="(source, i) in chatStore.sources" :key="i" class="source-item">
              <h4><span class="source-num">{{ i + 1 }}</span>{{ source.title || source.filename }}</h4>
              <p>{{ source.snippet || source.text?.slice(0, 120) }}</p>
              <span class="source-meta">{{ source.filename || source.source }}</span>
            </li>
          </ul>
          <p v-else class="source-empty">暂无资料来源，开始提问后将展示引用</p>
        </div>
      </aside>

      <!-- ④ 右卡片：快捷服务 -->
      <aside class="right-card">
        <div class="right-card-head">快捷服务</div>
        <div class="right-card-body">
          <div class="service-grid">
            <button class="explore-card explore-card--scenic" @click="handleQuickAction('recommend')">
              <span class="explore-card-icon">🏯</span>
              <span class="explore-card-title">景点推荐</span>
              <span class="explore-card-desc">热门景点导览</span>
            </button>
            <button class="explore-card explore-card--area" @click="handleQuickAction('photo')">
              <span class="explore-card-icon">📸</span>
              <span class="explore-card-title">拍照识景</span>
              <span class="explore-card-desc">实时景区识别</span>
            </button>
            <button class="explore-card explore-card--type" @click="handleQuickAction('route')">
              <span class="explore-card-icon">🗺️</span>
              <span class="explore-card-title">路线推荐</span>
              <span class="explore-card-desc">智能路线规划</span>
            </button>
            <button class="explore-card explore-card--photo" @click="handleQuickAction('style')">
              <span class="explore-card-icon">⚙️</span>
              <span class="explore-card-title">讲解方式</span>
              <span class="explore-card-desc">{{ explanationLevelLabel }}</span>
            </button>
          </div>
        </div>
      </aside>
    </div>

    <!-- ⑤ 底部输入栏 -->
    <div class="input-row">
      <input class="input-field" v-model="userInput" placeholder="想去哪里？清岚帮你规划…" @keyup.enter="handleSend" />
      <button class="voice-btn" :class="{ recording: speechListening }" @click="handleVoice">语音提问</button>
      <button class="image-btn" @click="handleImageCapture">拍照识景</button>
    </div>

    <input ref="imageInputRef" type="file" accept="image/*" capture="environment" hidden @change="handleImageUpload" />
  </section>
</template>
```

**Step 3: 修改 `<script setup>`**

保留现有所有 import 和逻辑不变。新增：
```js
const activeTab = ref('chat')

function handleQuickAction(action) {
  switch(action) {
    case 'recommend': handleSendPreset('推荐灵山值得去的景点'); break
    case 'photo': handleImageCapture(); break
    case 'route': handleSendPreset('帮我规划一条灵山游览路线'); break
    case 'style': showStyleSelector.value = !showStyleSelector.value; break
  }
}
```

**Step 4: 编写 `<style scoped>`**

完全替换为 chat-preview.html 的 CSS（即我们之前在 route-preview.html 上迭代优化的那套暗色三栏布局样式：480×520 side-card、450 auto right-card、700×64 input-row、18px msg-bubble 等）。

---

### Task 3: 路由与讲解风格适配

**Files:**
- 无修改

**说明:**
- `/tourist/select` → ModeSelectView（现已是四类服务入口，非风格选择）
- `/tourist` → ChatView（聊天页内保留讲解风格调节能力）
- 讲解风格（child/adult/expert）从 sessionStorage `a5-pending-guide-style-v1` 读取，兼容旧逻辑

---

### Task 4: Playwright 端到端验证

**Files:**
- 测试脚本: `c:\Users\李洵\.trae-cn\work\6a544d1e709443bb7404450c\test_vue_port.py`

**验证点:**
1. ModeSelectView 加载 → 4张卡片渲染 → 轮播可用 → 点击可进入样式选择 → 确认后跳转 /tourist
2. ChatView 加载 → 三栏布局渲染 → 对话/来源 Tab 切换 → 快捷服务按钮可点击 → 输入框/语音/拍照按钮可用
3. 桌面(1440×900)、笔记本(1200×800)、平板(1024×768) 三个视口无重叠

---

### 执行顺序

```
Task 1 (ModeSelectView) → Task 2 (ChatView) → Task 3 (验证无路由冲突) → Task 4 (Playwright 测试)
```

各 Task 可独立提交，互不阻塞（Task 2 不依赖 Task 1）。
