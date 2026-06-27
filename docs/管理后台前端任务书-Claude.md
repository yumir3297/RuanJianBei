# 管理后台前端实现任务书（Claude / Cursor）

## 项目背景

我们在做一个比赛作品：**灵山胜境（无锡 5A 景区）的 AI 数字人导游系统**。游客端已经完成（文本问答 + DeepSeek 真实 LLM + 主动选择景点/话题/路线 + 快捷追问 + 知识盲区追踪）。现在需要补齐管理后台的前端页面。

**你不需要了解后端怎么工作的**——所有 API 已经就绪，你只需要调接口、做 UI。

如果想完整理解项目在做什么，读 `docs/作品说明手册-报告与视频组.md`。

---

## 技术栈（全是现成的，直接写即可）

- **Vue 3**（Composition API，`<script setup>` 语法）
- **Element Plus**（`el-table`, `el-button`, `el-tag`, `el-empty`, `el-skeleton`, `el-select`, `el-alert`, `el-dialog`, `el-input`, `el-form` 等）
- **Pinia**（状态管理，已有 `useAdminStore`）
- **Axios**（`frontend/src/api/http.js` 封装好了 baseURL）
- **Vite**（开发时 `npm run dev` 即可）
- **Vue Router**（`frontend/src/router/index.js`，路由已定义好占位）

---

## 现有代码风格（必须遵守）

参考 `frontend/src/views/admin/Dashboard.vue` 和 `frontend/src/views/tourist/ChatView.vue`：

1. 页面顶层用 `<section class="panel-card admin-panel">` 包裹
2. 标题用 `<h2 class="section-title">`，副标题用 `<p class="section-subtitle">`
3. Element Plus 组件全部用 `el-` 前缀
4. 全中文界面（按钮文字、表格列名、提示语）
5. CSS 用 `scoped`，颜色主题是**深青色系**（`#0f766e` 主色、`#f0fdfa` 背景、`#64748b` 辅助文字）
6. 数据加载状态：loading 时显示 `<el-skeleton :rows="5" animated />`，错误时显示 `<el-alert type="warning" />`

---

## 五页任务清单（按优先级）

### 页 1：知识库管理（KnowledgeManage.vue）— 已有骨架，需完善

**当前状态**：`frontend/src/views/admin/KnowledgeManage.vue` 只有一个只读表格。
**API 已就绪**：`frontend/src/api/knowledge.js`（fetchKnowledgeList / createKnowledge / updateKnowledge / deleteKnowledge）
**后端**：`GET/POST/PUT/DELETE /api/knowledge/`

**需要添加的功能**：

1. **新增按钮 + 对话框**：点击后弹出 el-dialog，表单字段：
   - title（文本，必填）
   - category（下拉选择："景点信息"、"历史文化"、"建筑艺术"、"游览路线"、"实用贴士"、"景区概况"）
   - content（textarea，必填）
   - source（文本，默认 "管理员手动录入"）
   - aliases（标签输入，可选）

2. **编辑功能**：表格每行加操作列（编辑/删除），编辑复用同一个对话框

3. **删除确认**：`el-message-box` 二次确认后调用 delete API

4. **列表刷新**：新增/编辑/删除成功后自动刷新列表

**数据结构**（来自后端）：
```json
{
  "id": 1,
  "title": "灵山大佛",
  "category": "景点信息",
  "content": "...",
  "source": "official.docx",
  "aliases": ["大佛", "灵山大佛"],
  "metadata_json": null
}
```

---

### 页 2：知识盲区处理（新页面，BlindSpotManage.vue）

**API 需要新增**：在 `frontend/src/api/admin.js` 中添加两个函数：
```js
export async function fetchBlindSpots(status = "open", limit = 50) {
  const { data } = await http.get("/admin/blind-spots", { params: { status, limit } });
  return data;
}

export async function resolveBlindSpotWithFAQ(id, payload) {
  const { data } = await http.post(`/admin/blind-spots/${id}/resolve-with-faq`, payload);
  return data;
}
```

**后端**：
- `GET /api/admin/blind-spots?status=open&limit=50` → 返回盲区列表（按 hit_count 降序）
- `POST /api/admin/blind-spots/{id}/resolve-with-faq` → 补录 FAQ 并标记已解决

**需实现的功能**：

1. **双 TAB 切换**："待处理"和"已解决"（用 `el-tabs`，切换时重新请求 API 传不同的 `status` 参数）

2. **待处理列表**：每行显示：
   - 规范问题（`normalized_query`）
   - 游客原始问法（`raw_query_samples`，用 tag 展示）
   - 被问次数（`hit_count`，用 `el-tag` 高亮）
   - 首次/最近出现时间
   - 操作按钮："补充 FAQ"

3. **补充 FAQ 对话框**：点击后弹出 `el-dialog`，表单字段：
   - faq_id（文本，必填，如 "faq_restroom_001"）
   - category（下拉："实用信息"、"景点信息"、"历史文化" 等）
   - aliases（输入框，一行一个，至少一个。提示：游客原始问法会自动合并）
   - answer（textarea，必填）
   - sources（输入框，每行一个，至少一个非空。提示：必须注明信息来源）

4. **提交后处理**：弹窗关闭 → 刷新盲区列表 → 通知"已补充 FAQ " + 显示 `faq_reload_ms` 和 `faq_index_count`

5. **已解决 TAB**：展示 `status="resolved"` 的盲区，显示 `resolution_type`（faq）、`resolved_faq_id`、`resolved_at`

**后端 API 请求格式（POST resolve-with-faq）**：
```json
{
  "faq_id": "faq_admin_restroom_001",
  "category": "实用信息",
  "aliases": ["景区卫生间位置"],
  "answer": "卫生间位置信息请以景区现场导览标识为准。",
  "sources": ["景区运营后台人工核验"]
}
```

**后端响应格式**：
```json
{
  "message": "Knowledge blind spot resolved with FAQ.",
  "blind_spot": { "id": 1, "status": "resolved", ... },
  "faq_id": "faq_admin_restroom_001",
  "faq_reload_ms": 7.5,
  "faq_index_count": 89,
  "semantic_alias_count": 205
}
```

**路由**：在 `router/index.js` 中添加 `/admin/blind-spots` → `BlindSpotManage.vue`

---

### 页 3：数据大屏（升级 AnalyticsReport.vue）

**现有 API**：`GET /api/admin/overview` 和 `GET /api/admin/analytics`（已在 `admin.js` 中封装）

**当前状态**：`AnalyticsReport.vue` 是空壳占位。

**需要做的**：

1. **顶部四个指标卡片**（用 `stat-grid` 风格，参考 Dashboard.vue）：
   - 知识条目数、FAQ 条目数、问答日志数、路线模板数
   
2. **统计摘要表格**：列出 overview 的全部字段（knowledge_count, chunk_count, chat_log_count, visitor_count, cache_count, faq_count, route_count）

3. **不需要引入图表库**（ECharts 等），用 Element Plus 的 `el-card` + `el-row`/`el-col` 布局即可。评委会看重"能看到数据"而不是"图表多炫"

4. `useAdminStore` 已经封装了 `loadDashboard()`，直接复用 store

---

### 页 4：数字人配置（升级 AvatarConfig.vue）

**当前状态**：`AvatarConfig.vue` 是空壳占位。
**后端目前没有 Avatar 配置 API**（Avatar 还是 stub）。

**需要做的**：

1. 用一个表单页面展示**预留配置项**（名称、性别、音色、语速、表情策略），用 `el-form` 布局
2. 表单顶部加一个 `el-alert type="info"` 提示："数字人配置将在接入真实 Avatar 引擎后激活，当前展示为预留配置结构。"
3. 表单字段都是**纯前端 placeholder**，不需要调后端——数字人还没做，后端只有 stub
4. 样式与 KnowledgeManage 保持一致

---

### 页 5：游客感受度报告（新页面，SentimentReport.vue）

**后端 API**：当前 `GET /api/admin/analytics` 返回了基础数据。游客行为数据在 `behavior_summary` 中。

**需要做的**：

1. 展示 "行为样本行数"（来自 analytics 中的 `behavior_summary_count`）
2. 用 `el-empty` 显示"情感分析和感受度报告将在接入真实大模型交互后生成"——因为情感分析（SnowNLP）还没接到主链路
3. 保留一个概述区域，列出当前可用的游客数据维度

**路由**：`/admin/sentiment` → `SentimentReport.vue`

---

## 不需要你做的事

- ❌ 不需要改后端任何代码（Python/FastAPI/Chroma/SQLAlchemy 都不需要懂）
- ❌ 不需要改 `http.js`、`main.js`、`App.vue`
- ❌ 不需要做登录/权限（比赛作品不需要）
- ❌ 不需要移动端适配（管理后台都是桌面端使用）
- ❌ 不需要做数据同步/索引构建的后端调用（这些是运维操作，演示时手动触发即可）
- ❌ 不需要引入新的 npm 依赖

---

## 文件结构（你涉及的）

```
frontend/src/
├── api/
│   └── admin.js              ← 新增 fetchBlindSpots + resolveBlindSpotWithFAQ
├── stores/
│   └── admin.js              ← 已存在，可扩展
├── views/admin/
│   ├── Dashboard.vue          ← 已存在，不需要改
│   ├── KnowledgeManage.vue    ← 需要增强（加新增/编辑/删除功能）
│   ├── BlindSpotManage.vue    ← 新建
│   ├── AnalyticsReport.vue    ← 需要升级（从空壳变成数据页面）
│   ├── AvatarConfig.vue       ← 需要升级（从空壳变成预留配置表单）
│   └── SentimentReport.vue    ← 新建
├── router/
│   └── index.js              ← 新增 2 条路由
```

---

## 启动方式

```powershell
cd frontend
npm run dev
# → http://localhost:5173/

# 管理后台入口：
# http://localhost:5173/admin/dashboard
```

后端需要单独启动（但你应该已经知道怎么启动了，如果需要我可以提供命令）。

---

## API 速查表

| 操作 | 方法 | URL | 说明 |
|------|------|-----|------|
| 管理概览 | GET | `/api/admin/overview` | 返回各种计数 |
| 统计分析 | GET | `/api/admin/analytics` | 返回 label/value 列表 |
| 盲区列表 | GET | `/api/admin/blind-spots?status=open&limit=50` | status 可选 open/resolved |
| 解决盲区 | POST | `/api/admin/blind-spots/{id}/resolve-with-faq` | 补录 FAQ |
| 知识列表 | GET | `/api/knowledge/` | 返回全部知识条目 |
| 新增知识 | POST | `/api/knowledge/` | body: KnowledgeCreate schema |
| 更新知识 | PUT | `/api/knowledge/{id}` | body: KnowledgeUpdate schema |
| 删除知识 | DELETE | `/api/knowledge/{id}` | - |

---

## 设计风格速记

```css
/* 主色调 */
--primary: #0f766e;        /* 深青色，按钮/边框/强调 */
--primary-light: #f0fdfa;  /* 极浅青，背景 */
--amber: #d97706;          /* 琥珀色，警告/亮点 */
--text-primary: #1e293b;   /* 主文字 */
--text-secondary: #64748b; /* 辅助文字 */
--border: #e2e8f0;         /* 边框 */
```

- 卡片：白色背景 + `border-radius: 24px` + 浅阴影
- 卡片类名：`panel-card`
- 标题类名：`section-title`（h2/h3）+ `section-subtitle`（p）
- 表格：`el-table` + `stripe`
- 骨架屏：`<el-skeleton :rows="5" animated />`
- 空状态：`<el-empty description="..." />`

---

## 开发顺序建议

```
1. KnowledgeManage.vue 增强     ← 最简单，熟悉代码库风格
2. BlindSpotManage.vue 新建     ← 核心功能页，有 API 调用
3. AnalyticsReport.vue 升级     ← 复用已有 store
4. AvatarConfig.vue 升级        ← 纯前端 placeholder
5. SentimentReport.vue 新建     ← 数据有限，主要展示 placeholder
```
