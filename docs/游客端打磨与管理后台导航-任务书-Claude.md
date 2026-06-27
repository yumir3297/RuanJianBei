# 游客端体验打磨 + 管理后台导航 — 任务书（Claude）

> 日期：2026-06-16
> 2 个小任务，改动范围小，不涉及新 API

---

## 任务 1：管理后台子导航

### 现状

`App.vue` 顶部栏已经有"游客端"和"管理后台"两个顶导链接。但进入管理后台页面后，5 个管理页面之间没有互相导航——你得手动在地址栏敲 URL。

游客端只有一个页面所以不需要子导航，但管理后台有 5 个：
```
/admin/dashboard      → Dashboard.vue
/admin/knowledge      → KnowledgeManage.vue
/admin/blind-spots    → BlindSpotManage.vue
/admin/analytics      → AnalyticsReport.vue
/admin/avatar         → AvatarConfig.vue
```

### 需求

在管理后台页面区域（不是全局顶栏）加一个横向导航条，5 个 tab 对应 5 个页面，当前激活的 tab 高亮。

**不放在 App.vue**——游客端不需要管理后台的导航。只有当前路由匹配 `/admin/*` 时才显示这个子导航。

### 实现方式

方案 A（更简单，推荐）：在 App.vue 的 `page-body` 顶部加一个条件渲染的管理导航条。

方案 B：新建一个 `AdminLayout.vue` 包裹组件，路由配置为嵌套路由。

**建议用方案 A**，改动最小，且在路由中已经有现成路由名可以做映射。

### 具体代码

在 `App.vue` 的 `<main class="page-body">` 内、`<RouterView />` 上方，加条件渲染：

```html
<main class="page-body">
  <nav v-if="isAdminRoute" class="admin-nav">
    <RouterLink
      v-for="item in adminLinks"
      :key="item.path"
      :to="item.path"
      class="admin-nav-link"
      :class="{ active: route.path === item.path }"
    >
      <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
      <span>{{ item.label }}</span>
    </RouterLink>
  </nav>
  <RouterView />
</main>
```

```js
// App.vue <script setup> 中
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const isAdminRoute = computed(() => route.path.startsWith("/admin"));

const adminLinks = [
  { path: "/admin/dashboard", label: "总览", icon: "DataLine" },
  { path: "/admin/knowledge", label: "知识库", icon: "Document" },
  { path: "/admin/blind-spots", label: "知识盲区", icon: "Warning" },
  { path: "/admin/analytics", label: "数据大屏", icon: "Monitor" },
  { path: "/admin/avatar", label: "数字人配置", icon: "UserFilled" },
];
```

需要从 `@element-plus/icons-vue` 中导入用到的图标组件（`DataLine`, `Document`, `Warning`, `Monitor`, `UserFilled`）。Element Plus Icons 已在 `package.json` 的依赖中，无需 `npm install`。

### 样式要求

```css
.admin-nav {
  display: flex;
  gap: 4px;
  padding: 12px 0 0;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 20px;
  overflow-x: auto;
}

.admin-nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 10px 10px 0 0;
  color: #64748b;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 160ms, background 160ms;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.admin-nav-link:hover {
  color: #0f766e;
  background: #f0fdfa;
}

.admin-nav-link.active {
  color: #0f766e;
  background: #f0fdfa;
  border-bottom-color: #0f766e;
}
```

### 效果

```
[总览]  [知识库]  [知识盲区]  [数据大屏]  [数字人配置]
─── 激活的标签有深青色底部边框和浅青背景 ───
```

---

## 任务 2：游客端体验打磨

### 2.1 Enter 发送消息

**当前行为**：输入框是 `el-input type="textarea"`，Enter 是换行。必须点"发送问题"按钮。

**改为**：Enter 发送，Shift+Enter 换行。

在 `el-input` 上添加：

```html
<el-input
  v-model="query"
  type="textarea"
  :rows="3"
  resize="none"
  placeholder="请输入景区问题，例如：灵山大佛有多高？"
  @keydown.enter.exact.prevent="handleSubmit"
/>
```

`.exact` 确保只有单独的 Enter 才触发发送，Shift+Enter 不做处理（保留默认换行行为）。`.prevent` 阻止 Enter 在 textarea 中产生换行。

### 2.2 消息列表自动滚动到底部

**当前行为**：新消息出现后，消息列表不滚动，用户看不到最新回复。

**改为**：新消息出现 / 流式回答更新时，消息列表自动滚到底部。

在 `message-list` 上添加 `ref`：

```html
<div ref="messageListRef" class="message-list">
```

在 `<script setup>` 中添加：

```js
import { nextTick, watch } from "vue";

const messageListRef = ref(null);

function scrollToBottom() {
  nextTick(() => {
    const el = messageListRef.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

// 监听消息变化（无论用户消息还是助手回答更新都触发）
watch(
  () => chatStore.messages.length,
  () => scrollToBottom(),
);

// 流式更新时也滚动（助手回答内容变化）
watch(
  () => {
    const msgs = chatStore.messages;
    return msgs.length > 0 ? msgs[msgs.length - 1].content : "";
  },
  () => scrollToBottom(),
);
```

同时给 `.message-list` 加一个最大高度和滚动：

```css
.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 320px;
  max-height: 480px;          /* 新增 */
  overflow-y: auto;           /* 新增 */
  margin: 24px 0;
  scroll-behavior: smooth;    /* 新增：平滑滚动 */
}
```

### 2.3 流式回答时消息区域提示（顺手做）

助手回答区域内，在流式输出中显示一个闪烁光标动画，让用户知道"AI 正在打字"：

在消息 p 标签后加一个条件渲染的光标：

```html
<p>
  {{ message.content }}<span v-if="message.role==='assistant' && chatStore.streaming && index===chatStore.messages.length-1 && message.content.length>0" class="typing-cursor">|</span>
</p>
```

```css
.typing-cursor {
  animation: blink 0.8s infinite;
  color: #0f766e;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
```

---

## 文件修改清单（仅 2 个文件）

```
frontend/src/App.vue          ← 管理后台子导航（约 +30 行 JS + 40 行 CSS）
frontend/src/views/tourist/
  ChatView.vue                ← Enter 发送 + 自动滚动 + 闪烁光标（约 +25 行）
```

## 验证方式

```powershell
cd frontend
npm run dev
```

1. 打开 `http://localhost:5173/admin/dashboard`，确认顶部出现管理导航条，点击各 tab 能正常切换
2. 游客端输入问题后按 Enter → 发送成功
3. Shift+Enter → 换行
4. 发送多轮问题 → 消息列表自动滚动到最新消息
5. 流式回答中 → 消息末尾有闪烁光标
