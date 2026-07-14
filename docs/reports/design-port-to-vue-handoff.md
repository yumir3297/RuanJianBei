# 设计原型工程化 — 技术交接报告

> **受众** 接手前端开发的工程师或 AI 工具。本报告列出哪些代码是已有的、哪些是新写入的、哪些被替换了，方便快速理解仓库现状。

---

## 1 已有生产代码（已修改或继续使用）

以下文件在原 Vue 项目中已存在，本次进行了修改或继续使用：

| 文件 | 职责 | 本次状态 |
|------|------|----------|
| `frontend/src/stores/chat.js` | Pinia store — 管理消息列表、流式 SSE 回答 (`streamChat()`)、资料来源 (`sources`)、追问建议 (`followups`) | 修改：`onSpeechProgress` 回调新增 `actualDurationMs` 参数 |
| `frontend/src/stores/interaction.js` | Pinia store — 管理模式 (free_chat / attraction / topic / route)、景点/话题/路线选择、讲解风格持久化 | 未修改 |
| `frontend/src/composables/useSpeechRecognition.js` | 封装浏览器 `SpeechRecognition` API | 未修改 |
| `frontend/src/composables/useRecorder.js` | 封装 `MediaRecorder` API | 未修改 |
| `frontend/src/composables/useSSEStream.js` | SSE 流解析器 | 未修改 |
| `frontend/src/composables/useAudioPlayer.js` | TTS 音频播放，控制 viseme 同步 | 修改：`onProgress` 回调新增第三参数 `actualDurationMs` |
| `frontend/src/api/chat.js` | `/api/chat/stream` 请求封装 | 未修改 |
| `frontend/src/api/vision.js` | `/api/vision/analyze` 图像识别请求封装 | 未修改 |
| `frontend/src/components/ThreeAvatar.vue` | Three.js + VRM 3D 数字人组件，支持 viseme 口型同步 | 修改：新增 `speechElapsedMs`/`speechDurationMs` props，优化 viseme 时序计算 |
| `frontend/src/components/avatar-presets/index.js` | 数字人预设配置表 (monk/hanfu/modern) | 修改：modern 预设新增 `modelUrl: "/models/male-guide.vrm"` |
| `frontend/src/composables/useAvatar.js` | 数字人状态管理 (idle / listening / thinking / speaking / happy) | 未修改 |
| `frontend/src/composables/useMarkdown.js` | Markdown 渲染，含引文编号渲染 | 未修改 |
| `frontend/src/router/index.js` | Vue Router 配置 | **修改：新增 3 条懒加载路由** `/tourist/explore`、`/tourist/routes`、`/tourist/quiz` |
| `frontend/src/views/HomePage.vue` | 游客欢迎页 | 修改：切换为 `useScenicBackground` + 动态头像预设读取 |

---

## 2 设计原型文件（仅视觉参考，未接入代码）

以下文件位于 `design-redesign/`，是纯 HTML 设计稿，不含 Vue 响应式逻辑和 API 调用：

| 文件 | 作用 | 本次工程化状态 |
|------|------|----------------|
| `select-preview.html` | 四类智慧服务入口轮播（数字人导游 / 景点探索 / 智能路线 / 文化问答） | 视觉已移植到 ModeSelectView.vue |
| `chat-preview.html` | 三栏聊天布局（左对话卡 + 中数字人 + 右快捷服务） | 视觉已移植到 ChatView.vue |
| `explore-preview.html` | 景点探索页 | **已移植 → ExploreView.vue** |
| `quiz-preview.html` | 文化问答页 | **已移植 → QuizView.vue** |
| `route-preview.html` | 智能路线页 | **已移植 → RouteView.vue** |
| `admin-dashboard.html` | 管理后台数据总览 | 已有对应 Vue 页面 `Dashboard.vue` |

---

## 3 本次新增 / 重写的文件

### 3.1 ModeSelectView.vue

**路径** `frontend/src/views/tourist/ModeSelectView.vue`
**行数** 1189 行
**操作** 完整重写

**旧版** 是一个"讲解风格选择"页，展示 4 种风格卡片（亲子游 / 休闲游 / 文化深度游 / 自由游览），确认后跳转聊天页。

**新版** 改为"四类智慧服务"轮播入口页：

- 4 张轮播卡片，每张对应一个服务模式：
  - 数字人导游 (`mode: 'free_chat'`)
  - 景点探索 (`mode: 'attraction'`)
  - 智能路线 (`mode: 'route'`)
  - 文化问答 (`mode: 'topic'`)
- "数字人导游"卡片点击后弹出"讲解深度"面板（儿童版 / 标准版 / 专业版），确认后跳转 `/tourist`
- **景点探索、智能路线、文化问答三张卡片**点击后分别通过 `router.push` 跳转 `/tourist/explore`、`/tourist/routes`、`/tourist/quiz`，不再弹出 "正在开发" 提示。
- **暗色主题**（`#1a1612` 背景），支持鼠标拖拽和触控轮播，键盘左右箭头导航，底部分页点
- **保留旧全部交互逻辑**：`interactionStore`、`chatStore.resetSession()`、sessionStorage 连通性

### 3.2 ChatView.vue

**路径** `frontend/src/views/tourist/ChatView.vue`
**行数** 1825 行
**操作** 模板和样式完整重写，`<script setup>` 保留并小幅扩充

**模板变更** 三栏暗色绝对定位布局：左侧对话/来源 Tab 卡片 + 中央数字人舞台 + 右侧快捷服务卡片 + 底部输入栏。详情见上一版报告。

### 3.3 三个新增游客端页面

本次完整新增了三个独立页面，作为 ModeSelectView 卡片跳转的目标：

| 页面 | 路径 | 行数 | 路由 | 职责 |
|------|------|------|------|------|
| ExploreView | `frontend/src/views/tourist/ExploreView.vue` | 201 | `/tourist/explore` | 景点探索 — 含拍照识景、景点推荐卡片、对话/来源双Tab |
| RouteView | `frontend/src/views/tourist/RouteView.vue` | 161 | `/tourist/routes` | 智能路线 — 含路线推荐卡片、路线列表、对话面板 |
| QuizView | `frontend/src/views/tourist/QuizView.vue` | 147 | `/tourist/quiz` | 文化问答 — 含佛教文化、历史人文等分类卡片、对话面板 |

**三页共同特征：**
- 复用 `@import '../../assets/tourist-page.css'` 共享样式
- 通过 `useScenicBackground()` 读取后台可配置的景区背景图（兼容 `var(--lingshan-scenic-bg)` 兜底）
- 通过 `fetchAvatarConfig()` + `normalizeAvatarPresetFromModelPath()` 读取头像配置，回退 `DEFAULT_AVATAR_PRESET`
- 使用 `useChatStore` / `useInteractionStore` 进行对话交互
- 懒加载路由，Vite 生产构建生成独立 JS + CSS chunk

### 3.4 共享基础设施

| 文件 | 职责 |
|------|------|
| `frontend/src/assets/tourist-page.css` | 游客端共享 CSS（背景、卡片、消息气泡、输入栏、响应式），被 ExploreView、RouteView、QuizView 引用 |
| `frontend/src/composables/useScenicBackground.js` | 景区背景图 composable — 缓存后台配置的背景图，兜底 `var(--lingshan-scenic-bg)`，5 分钟 TTL 缓存。被 HomePage / ChatView / ExploreView / RouteView / QuizView / ModeSelectView 共 6 个页面引用 |
| `frontend/public/models/male-guide.vrm` | "景行"（modern 预设）的 VRM 3D 模型文件，被 `avatar-presets/index.js` 引用 |

---

## 4 数据流通确认

**讲解风格桥接** — ModeSelectView 和 ChatView 之间通过 `sessionStorage` key `a5-pending-guide-style-v1` 传递：

```
ModeSelectView.vue (确认时)           ChatView.vue (onMounted)
    │                                    │
    │ sessionStorage.setItem(             │ const pendingStyle =
    │   'a5-pending-guide-style-v1',     │   sessionStorage.getItem(
    │   selectedStyle)                   │     'a5-pending-guide-style-v1')
    │                                    │
    │ router.push('/tourist')            │ explanationLevel = pendingStyle
    │                                    │ sessionStorage.removeItem(...)
    ▼                                    ▼
```

**路由** — 已从 2 条扩展到 5 条游客端路由：

| 路径 | 路由名 | 组件 | 类型 |
|------|--------|------|------|
| `/` | `home` | LandingPage | 入口 |
| `/tourist/welcome` | `tourist-welcome` | HomePage | 欢迎 |
| `/tourist/select` | `tourist-mode-select` | ModeSelectView | 服务选择 |
| `/tourist` | `chat` | ChatView | 数字人导游对话 |
| `/tourist/explore` | `tourist-explore` | ExploreView | 景点探索（新增） |
| `/tourist/routes` | `tourist-routes` | RouteView | 智能路线（新增） |
| `/tourist/quiz` | `tourist-quiz` | QuizView | 文化问答（新增） |

**头像配置** — 三个新页面与 ChatView 一致，均通过 `fetchAvatarConfig()` + `normalizeAvatarPresetFromModelPath()` 从后台读取，回退 `DEFAULT_AVATAR_PRESET ("hanfu")`。

---

## 5 编译验证

```bash
cd frontend
npm.cmd run build
# ✓ built in 20.48s
# 退出码 0，零编译错误
```

**生产产物：** 三个新页面各自生成独立的懒加载 chunk：

| 页面 | JS Chunk | CSS Chunk |
|------|----------|-----------|
| ExploreView | `ExploreView-Q6oSAIGq.js` (9.2 KB) | `ExploreView-B4biU-_Q.css` (13.7 KB) |
| RouteView | `RouteView-C67YjsF0.js` (7.9 KB) | `RouteView-klDVAO8L.css` (13.0 KB) |
| QuizView | `QuizView-CKIWhMxU.js` (7.4 KB) | `QuizView-COh1qr82.css` (12.5 KB) |

---

## 6 TL;DR 总结

- **修改** `stores/chat.js`、`composables/useAudioPlayer.js`、`components/ThreeAvatar.vue` — 语音同步时序优化（`actualDurationMs` 传递链路）
- **修改** `router/index.js` — 新增 `/tourist/explore`、`/tourist/routes`、`/tourist/quiz` 三条懒加载路由
- **修改** `HomePage.vue` — 切换为 `useScenicBackground` + 动态头像读取
- **修改** `avatar-presets/index.js` — modern 预设关联 `male-guide.vrm`
- **重写** `ModeSelectView.vue` — 从风格选择页变为四类服务轮播入口页，三张非导游卡片跳转对应新页面
- **重写** `ChatView.vue` 模板+样式 — 三栏暗色绝对定位布局
- **新增** `ExploreView.vue` (`/tourist/explore`)、`RouteView.vue` (`/tourist/routes`)、`QuizView.vue` (`/tourist/quiz`)
- **新增** `tourist-page.css` — 游客端共享样式
- **新增** `useScenicBackground.js` — 背景图 composable（被 6 个页面引用）
- **新增** `male-guide.vrm` — "景行" 数字人的 VRM 模型
- **不妥协** sessionStorage 桥接、讲解风格调节、拍照识景流程、语音识别流程、SSE 流式回答 — 全部保留
