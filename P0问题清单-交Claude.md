# P0 问题清单（交 Claude 修复）

> 创建日期：2026-06-22
> 说明：以下三个问题是当前项目最严重的缺陷，请逐一修复。只描述问题现象和涉及文件，不提供修复方案。

---

## 问题一：数字人口型同步管线断裂

### 现象

Live2D 数字人在语音播报时嘴巴随机张合，与音频完全不同步。当前使用 `Math.random()` 驱动口型。

### 涉及文件

- `frontend/src/composables/useAudioPlayer.js` — 音频播放器，`playAudioBuffer()` 需要输出实时播放进度
- `frontend/src/composables/useAvatar.js` — 数字人状态管理，当前只有 3 种表情，需要扩展到 7 种
- `frontend/src/stores/chat.js` — 聊天状态管理，SSE `audio` 事件处理、音频入队
- `frontend/src/views/tourist/ChatView.vue` — 主聊天界面，需要把播放进度传递给 Live2D
- `frontend/src/components/Live2DAvatar.vue` — Live2D 渲染组件，需要接收外部进度驱动口型

### 当前实际情况

- `Live2DAvatar.vue` 使用 `Math.random()` 在 `setInterval` 中驱动口型开合
- SSE 流中 `audio` 事件已携带 `viseme_timeline` 和 `text` 字段
- `useAudioPlayer.enqueue()` 已保存 `onProgress` 参数
- `playAudioBuffer()` 每 30ms 发送一次播放进度回调
- 但 `chat.js` 中 `enqueue()` 的第 4 个参数传的是 `text` 而不是 `onProgress`
- `ChatView.vue` 缺少 `speechProgress` 和 `visemeTimeline` 的响应式变量
- `Live2DAvatar.vue` 缺少接收外部进度的 props（`speechProgress`、`visemeTimeline`）
- `Live2DAvatar.vue` 缺少根据进度插值计算 viseme 的函数

### 期望效果

语音播报时，Live2D 数字人的嘴巴开合与音频真实同步（不是随机），播完后闭嘴回到 idle 状态。

---

## 问题二：真实大语言模型未接入

### 现象

当前聊天管线中的 LLM 使用的是 Stub（占位桩），返回预设的假回答，不是真正的 AI 生成。

### 涉及文件

- `backend/app/services/llm/openai_compatible.py` — LLM 服务，当前是 Stub 返回假数据
- `backend/app/core/config.py` — 配置文件，已有 DeepSeek 相关配置字段
- `backend/.env` — 环境变量，需要填入 DeepSeek API Key 和 Base URL
- `backend/app/services/qa/pipeline.py` — 问答编排主流程，当前调用的就是 stub

### 当前实际情况

- 已有完整的设计方案：`设计文档/12-阶段B-DeepSeek最终执行方案.md`
- LLM 选型已确定为 DeepSeek API（`deepseek-chat`，OpenAI 兼容接口）
- 配置文件 `config.py` 中已有 `llm_api_key`、`llm_base_url`、`llm_model` 等字段
- `.env` 中需要配置 DeepSeek 的 API Key
- Stub 代码结构已预留 OpenAI 兼容的 HTTP 流式请求框架
- SSE 流式输出格式已定义好，前端无需改动

### 期望效果

用户提问后，系统真正调用 DeepSeek API 流式生成回答，SSE 逐字推送到前端。

---

## 问题三：管理后台数据不真实

### 现象

管理后台多个模块展示的是假数据或空数据，无法体现真实运营闭环。

#### 3.1 知识盲区表始终为空

- **涉及表**：`knowledge_blind_spots`
- **当前数据**：0 行
- **实际应有**：已有 349 条聊天日志，其中应有大量 RAG 无法回答的问题
- **涉及文件**：
  - `backend/app/api/chat.py` — 聊天 API，需要在无证据路径写入盲区记录
  - `backend/app/repositories/` — 盲区相关 Repository
  - `backend/app/models/` — 盲区 ORM 模型

#### 3.2 游客画像表几乎为空

- **涉及表**：`visitor_profiles`
- **当前数据**：2 行
- **实际应有**：349 条聊天日志应对应大量游客
- **涉及文件**：
  - `backend/app/api/chat.py` — 聊天 API，需要每轮调用 VisitorRepository
  - `backend/app/repositories/` — 游客相关 Repository
  - `frontend/src/views/admin/Dashboard.vue` — 仪表盘展示

#### 3.3 仪表盘趋势图是硬编码假数据

- **涉及文件**：`frontend/src/views/admin/Dashboard.vue`
- **当前**：第 139-140 行使用硬编码数组 `[42,58,35,67,89,120,75]`
- **应有**：调用已存在的 `GET /api/insights/qa-trend` 接口获取真实数据
- **注意**：后端 `/api/insights/qa-trend` 接口已经实现并返回真实 SQL 查询结果

### 期望效果

管理后台的盲区列表、游客画像统计、问答趋势图全部展示真实的运营数据。

---

## 附加说明

- 所有修复不要引入新的依赖（DeepSeek API 调用使用已有的 `httpx` 或 `requests`）
- 修复后不要新增 lint 错误
- 保持前端原有 UI 布局不变
- 后端修改注意保持 API 路径不变，前端已有路由
- `.env` 中 DeepSeek API Key 留空即可，写明在哪里填入
