# 阶段 D（语音闭环）与阶段 E（数字人闭环）准备方案

> 版本：2026-06-17  
> 状态：待审查，当前仅做低风险准备工作，不执行真实外部 API 接入  
> 主线依据：[10-最终总体设计与开发主线.md](../设计文档/10-最终总体设计与开发主线.md)

---

## 一、背景与当前进度

项目整体进度见 [CURRENT_TASK_SUMMARY.md](./CURRENT_TASK_SUMMARY.md)：

- 阶段 A（主动选择 + Reranker 性能 + FAQ L3 / 盲区）—— 已完成
- 阶段 B（真实多模态 LLM + 证据回答 + 图片识别）—— B3.2 已完成，等待 Qwen 真实烟测
- 阶段 C（管理后台可运营闭环）—— 未开始
- **阶段 D（语音闭环）—— 未开始**
- **阶段 E（数字人闭环）—— 未开始**
- 阶段 F（最终评测与演示保障）—— 未开始

后端 `services/asr/`、`services/tts/`、`services/avatar/` 已有抽象基类 + 桩实现框架。前端 `useRecorder.js`、`useAudioPlayer.js` 为纯占位桩。本次准备的目的是在不需要任何外部 API 账号的前提下，把内部架构、前后端联调和基础交互先跑通，让阶段 D/E 正式启动时只需接入真实 Provider 即可闭环。

---

## 二、阶段 D 与 E 的最终目标（来源：主线文档）

### 阶段 D：语音闭环

1. 真实录音与 ASR endpoint
2. 热词、置信度和候选确认
3. 句级流式 TTS
4. 统计 ASR、检索、LLM、TTS 各段延迟
5. 端到端 P95 向 5 秒以内收敛

### 阶段 E：数字人闭环

1. 轻量 2D Avatar 状态机
2. TTS 时间信息或音量驱动口型
3. 情感 / 回答状态驱动表情
4. 后台切换形象、声音和表情策略
5. 评估是否需要 Duix-Avatar 增强，不破坏已有降级链路

### 硬性验收门槛（来源：主线文档第十二节）

| 能力 | 最低验收门槛 |
|------|------------|
| 语音 | 端到端响应目标小于 5 秒，报告 P50/P95 |
| 数字人 | 播报时有口型，状态/情感有表情，失败可降级 |

---

## 三、现有架构盘点

### 3.1 后端

```
backend/app/services/
├── asr/
│   ├── __init__.py          # package marker
│   ├── base.py              # BaseASRService + ASRResult(text, confidence)
│   └── stub.py              # StubASRService 返回占位文本
├── tts/
│   ├── __init__.py          # package marker
│   ├── base.py              # BaseTTSService + TTSAudio(base64_audio, duration_ms)
│   └── stub.py              # StubTTSService base64 编码文本
├── avatar/
│   ├── __init__.py          # package marker
│   ├── base.py              # BaseAvatarService + AvatarPayload(viseme_text, emotion)
│   └── stub.py              # StubAvatarService 原样返回 viseme_text
└── qa/
    ├── pipeline.py          # QAPipeline 已串联 TTS + Avatar（流式逐句、非流式整体）
    └── stream_events.py     # 定义 audio 和 avatar SSE 事件类型
```

关键集成点 — `pipeline.py` 中的 TTS/Avatar 调用：

- **流式模式**：LLM 每输出一个完整句子（以 。！？结尾），后台异步调用 `tts.synthesize()` + `avatar.drive()`，结果放入 `asyncio.Queue` 逐条输出 SSE
- **非流式模式**：`_emit_final_answer()` 内调用 TTS + Avatar，输出 `audio` 和 `avatar` SSE 事件
- **构建入口**：`backend/app/api/chat.py` 的 `build_pipeline()` 中固定注入 `StubTTSService()` 和 `StubAvatarService()`

现状：Pipeline 中的 TTS/Avatar 串联逻辑已经完备，但由于 Provider 是 stub，产出的是无效 base64 文本而非真实音频，avatar 事件也只有 `emotion: "neutral"`。

### 3.2 前端

| 文件 | 当前状态 | 差距 |
|------|---------|------|
| `src/composables/useRecorder.js` | 仅切换 `isRecording` 布尔值 | 无真实 MediaRecorder API |
| `src/composables/useAudioPlayer.js` | 仅 `setTimeout` 延时模拟 | 无 AudioContext 或 `<audio>` 播放 |
| `src/stores/chat.js` | 已注册 `audio` SSE handler | `avatar` 事件未处理 |
| `src/views/tourist/ChatView.vue` | 有"语音录制占位"按钮 | 无录音上传、无数字人渲染区 |
| `src/views/admin/AvatarConfig.vue` | 纯占位提示页 | 无形象选择、音色切换等功能 |
| `src/composables/useSSEStream.js` | 通用 SSE 解析器 | 已可用于 audio/avatar 分派 |

### 3.3 后端配置

`backend/app/core/config.py` 当前没有任何 ASR/TTS/Avatar 配置项。阶段 D/E 正式接入真实 Provider 时需要新增：

- `ASR_PROVIDER` / `ASR_API_KEY` / `ASR_MODEL` / `ASR_HOTWORDS`
- `TTS_PROVIDER` / `TTS_API_KEY` / `TTS_VOICE` / `TTS_MODEL`
- `AVATAR_PROVIDER` / `AVATAR_MODEL_PATH` 等

本次准备阶段暂不接入真实 Provider，因此也不新增 .env 配置依赖。仅在代码层面为新配置项预留好位置。

---

## 四、设计约束与原则

以下约束来自 [DECISIONS.md](./DECISIONS.md) 和 [10-最终总体设计与开发主线.md](../设计文档/10-最终总体设计与开发主线.md)，阶段 D/E 所有工作均需遵守：

### 架构原则

1. **Graceful Degradation**：ASR / TTS / Avatar 任一模块故障不得阻塞文本问答。文本输入和主动选择始终作为降级通道
2. **Provider 可替换**：所有外部服务通过抽象基类接入，替换 Provider 只改工厂函数，不影响 Pipeline 和前端
3. **不作为事实源**：ASR 转录文本和置信度候选只作为检索线索，不作为景区事实证据
4. **首版轻量**：2D 方案优先，重型 Duix-Avatar 留到阶段 E 末尾评估

### 执行纪律（来源：主线文档第十三节）

1. 每次正式编码前先生成或更新本轮任务总结
2. 修改公共 API、数据库 Schema、依赖或模型方案前必须获得用户确认
3. 每完成一个 Step 就运行测试并做审查
4. 遇到走不通的供应商账号、API Key、依赖或性能路线时立即停止并说明，不擅自换方案

---

## 五、本次准备任务

以下 6 个任务均为低风险、不依赖外部 API 账号的内部工作。完成后意味着阶段 D/E 的架构骨架和前后端数据链路完全跑通，正式接入阿里云 NLS、真实 TTS 和 2D Avatar 时只需替换 Provider 实现即可。

---

### D1：前端录音器真实化

**文件**：`frontend/src/composables/useRecorder.js`

**当前状态**：仅切换 `isRecording` 布尔值，无真实音频采集。

**目标**：接入 `navigator.mediaDevices.getUserMedia` + `MediaRecorder` API，实现真实的录音 / 停止 / 获取音频 Blob 能力。

**改动内容**：

1. `start()` 请求麦克风权限，创建 `MediaRecorder` 实例，收集 `audio/webm` chunks
2. `stop()` 停止录制，返回 `Promise<Blob>`（音频 blob + MIME 类型）
3. 新增 `isSupported` 响应式属性，浏览器不支持时前端不展示录音按钮
4. 新增 `onerror` 回调，权限拒绝或设备不可用时通知调用方

**不涉及**：音频上传、ASR 请求、WebSocket 流式传输（这些属于阶段 D 正式工作）

**验收**：
- 控制台能拿到 `audio/webm` Blob 对象
- 权限拒绝时不抛异常，而是返回 `isSupported = false`
- 前端生产构建通过

---

### D2：后端 ASR HTTP 端点

**文件**：`backend/app/api/voice.py`（新建）+ 路由注册

**当前状态**：后端没有独立的 ASR 端点，聊天链路也未接入 ASR。

**目标**：新增 `POST /api/asr/transcribe`，接收音频二进制数据，返回 ASR 文本和置信度。首轮使用 stub 实现（后续替换为真实 Provider）。

**接口设计**：

```
POST /api/asr/transcribe
Content-Type: audio/webm （或其他 MIME）

Response 200:
{
  "text": "灵山大佛怎么走",
  "confidence": 0.95,
  "candidates": []
}
```

**改动内容**：

1. 新建 `backend/app/api/voice.py`，包含 `POST /transcribe` 端点
2. 端点从请求 body 读取音频字节，调用 `Depends` 注入的 `BaseASRService`
3. `ASRResult` 扩展 `candidates: list[ASRCandidate]` 字段（可选，为置信度降级预留）
4. 在 `backend/app/api/router.py` 注册 `/api/asr` 路由前缀
5. HTTP 层不做方言改写和置信度分流，这些留在 Pipeline 层处理
6. `build_asr_service()` 工厂目前返回 `StubASRService()`，后续切换为 `AliyunASRService()` 即可

**依赖**：无新增第三方库

**不涉及**：真实 ASR Provider 调用、热词注入、流式识别

**验收**：
- `POST /api/asr/transcribe` 返回 stub 文本和 `confidence: 1.0`
- 后端完整回归所有通过
- compileall 编译检查通过

---

### D3：前后端录音联调链路

**文件**：`frontend/src/api/chat.js`（或新建 voice api 模块）、`frontend/src/stores/chat.js`、`frontend/src/views/tourist/ChatView.vue`

**当前状态**：前端录音按钮不产生任何数据流，未连接后端 ASR 端点。

**目标**：打通 "前端录音 → 上传音频 → 后端 ASR 转录 → 文本填入输入框 → 自动发送问答" 的完整链路，当前阶段使用 stub 数据验证交互。

**前端改动**：

1. 新增 `frontend/src/api/voice.js`：
   - `transcribeAudio(audioBlob)` — POST Blob 到 `/api/asr/transcribe`，返回 `{ text, confidence }`
2. `ChatView.vue` 改造录音按钮：
   - 点击开始录音 → 按钮变红 / 显示时长
   - 点击结束录音 → 上传 blob → 获取文本 → 填入输入框
   - 低置信度（后续阈值）暂不处理，仅打印日志
3. 从 `useRecorder` 获取 `isSupported`，不支持时不展示录音按钮
4. 文本输入框始终可用，作为降级通道

**不涉及**：ASR 置信度降级 UI、方言候选确认弹窗（属于阶段 D 正式工作）

**验收**：
- 浏览器中点击录音按钮 → 结束录音 → 输入框自动填入 stub 文本
- 浏览器不支持麦克风时录音按钮不显示
- 文本输入框始终可用
- 前端生产构建通过

---

### E1：前端 Avatar 状态机 + 视觉反馈

**文件**：`frontend/src/composables/useAvatar.js`（新建）+ `frontend/src/views/tourist/ChatView.vue`

**当前状态**：前端无任何 Avatar 视觉元素，`avatar` SSE 事件完全丢弃。

**目标**：实现 Avatar 状态机和基础视觉容器，SSE `avatar` 事件能驱动状态切换和表情变化。

**状态机定义**（来源于主线文档第八节）：

```
idle      → 默认待机状态，轻微微笑
listening → 录音中，身体微前倾，耳部高亮
thinking  → 加载中，思考动画（如眨眼 / 光环旋转）
speaking  → 播报中，口型张合
happy     → 回答正向内容时微笑 / 点头
apology   → 无法回答时歉意表情
```

**改动内容**：

1. 新建 `frontend/src/composables/useAvatar.js`：
   - `currentState`：响应式状态值
   - `currentEmotion`：当前表情
   - `currentViseme`：当前口型文本
   - `setState(state)`：切换状态
   - `handleAvatarEvent(payload)`：消费 `{ viseme_text, emotion }` SSE 数据
   - 状态自动回退：`speaking` → `idle`（音频结束后 500ms 未收到新数据）
2. 新建 `frontend/src/components/AvatarDisplay.vue`：
   - 纯 CSS/SVG 实现的轻量 2D 头像（圆形头像 + 状态指示环）
   - 根据 `state` 切换 CSS class 动画（idle 呼吸 / listening 脉动 / thinking 旋转 / speaking 口型 / happy 弹跳 / apology 低头）
   - 不需要任何 3D 库、VRM 模型或外部图片资源
3. `frontend/src/stores/chat.js`：
   - 注册 `avatar` SSE 事件 handler，调用 `avatar.handleAvatarEvent()`
4. `ChatView.vue`：
   - 在聊天区域顶部或侧边渲染 `<AvatarDisplay />`
   - 发送消息时切换 `thinking` → `speaking` → `idle`
   - 录音时切 `listening`
   - 收到 emotion 时映射到对应状态

**不涉及**：真实音视频同步、VRM 3D 模型、Duix-Avatar（这些属于阶段 E 正式工作）

**验收**：
- 页面加载时 Avatar 处于 `idle` 状态，有呼吸动画
- 发送消息后 Avatar 依次经历 `thinking` → `speaking` → `idle`
- 收到 `avatar` SSE 事件后表情随 emotion 字段变化
- Avatar 区域渲染异常不影响聊天功能（Graceful Degradation）
- 前端生产构建通过

---

### E2：前端真实音频播放

**文件**：`frontend/src/composables/useAudioPlayer.js`

**当前状态**：仅 setTimeout 延时模拟，未真实播放音频。

**目标**：将 base64 音频数据解码并通过 Web Audio API 或 `<audio>` 元素真实播放。

**改动内容**：

1. 实现 base64 → ArrayBuffer 解码
2. 使用 `AudioContext.decodeAudioData()` 或 `<audio>` 元素播放
3. 维护播放队列，逐条播放（与现有 `enqueue / flush` 接口兼容）
4. 播放结束后触发 `onEnded` 回调（供 Avatar 状态回退使用）
5. 新增 `isSupported` 属性（AudioContext 不可用时降级为静默模式）

**不涉及**：与 TTS viseme 时间戳的精确口型同步（需要 TTS Provider 返回 phoneme 时间信息）

**验收**：
- 收到 `audio` SSE 事件后能听到声音（TTS 真实化前为 stub 音频）
- 多条音频排队播放，不重叠
- AudioContext 不可用时不抛异常
- 前端生产构建通过

---

### E3：AvatarConfig 数据模型与管理 API 骨架

**文件**：`backend/app/models/avatar_config.py`（新建）、`backend/app/api/admin.py`（扩展）

**当前状态**：设计文档中有 `AvatarConfig` 数据模型规划 ([07-本轮修改指令.md](../设计文档/07-本轮修改指令.md#L446-L462))，但代码中未实现。

**目标**：创建数据库模型 + 种子数据 + 管理 API 骨架，为阶段 E 的后台配置页面做数据层准备。

**数据模型**（来源于 [06-赛题遗漏维度补充方案.md](../设计文档/06-赛题遗漏维度补充方案.md#L141-L150)）：

```python
class AvatarConfig(Base):
    __tablename__ = "avatar_configs"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]            # "僧袍法师" / "汉服导游" / "现代导游"
    model_path: Mapped[str]      # 首版使用 CSS avatar 预设 key，后续扩展为 VRM 路径
    preview_url: Mapped[str]     # 缩略图路径或数据 URI
    voice_type: Mapped[str]      # "male_calm" / "female_warm" / "male_enthusiastic"
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime]
```

**API**（来源于 [07-本轮修改指令.md](../设计文档/07-本轮修改指令.md#L454-L460)）：

```
GET  /api/admin/avatar-configs          # 列出所有预设形象
PUT  /api/admin/avatar-configs/{id}/activate  # 切换激活的形象
GET  /api/admin/avatar-configs/active   # 游客端获取当前激活的形象
```

**改动内容**：

1. 新建 `backend/app/models/avatar_config.py`，创建 `AvatarConfig` 模型
2. 在 `backend/app/db/base.py` 注册模型（`create_all` 创建新表）
3. 在 `backend/app/db/bootstrap.py` 添加 3 条种子数据
4. 在 `backend/app/api/admin.py` 新增 3 个端点
5. 新增 `backend/app/schemas/admin.py` 中的 `AvatarConfigResponse` Pydantic schema
6. 在 `backend/app/core/config.py` 预留 `DEFAULT_AVATAR_VOICE` 配置项（暂不强制使用）

**不涉及**：
- 前端 `AvatarConfig.vue` 页面重建（属于阶段 C/E 正式前端工作）
- VRM 模型文件准备
- 真实声音切换逻辑（TTS Provider 需支持 voice 参数）

**验收**：
- `AvatarConfig` 表创建成功，种子数据包含 3 条记录
- `GET /api/admin/avatar-configs` 返回列表
- `PUT /api/admin/avatar-configs/{id}/activate` 切换 `is_active`
- `GET /api/admin/avatar-configs/active` 返回当前激活项
- 后端完整回归全部通过
- compileall 编译检查通过

---

## 六、任务执行顺序

```
D1（前端录音器）──┐
                  ├──→ D3（前后端录音联调）
D2（后端ASR端点）─┘

E1（Avatar状态机）─┐
                   ├──→ 前端集成验证
E2（真实音频播放）──┘

E3（AvatarConfig模型）──→ 独立，可与 D/E 并行
```

- D1 + D2 是 D3 的前置依赖，须先完成
- E1 + E2 互不依赖，可并行
- E3 为纯后端工作，可与前面任意任务并行
- D 线和 E 线之间互不依赖，可以交替推进

---

## 七、不做的事项

以下明确不在本次准备范围：

1. 不接入真实 ASR Provider（阿里云 NLS / FunASR）—— 需用户确认账号和预算
2. 不接入真实 TTS Provider —— 需用户确认账号和预算
3. 不接入 Duix-Avatar 或 VRM 3D 模型 —— 需额外的模型资源和评估
4. 不新增 Python 或 Node.js 依赖 —— 全部使用浏览器原生 API 和现有框架
5. 不修改数据库已有表结构 —— 仅 `create_all` 创建新表 `avatar_configs`
6. 不做 ASR 置信度降级 UI —— 交互细节属于阶段 D 正式工作
7. 不做方言改写 —— 需要 LLM 参与，属于阶段 D 正式工作
8. 不做延迟评测 —— 需要真实 Provider 才有意义
9. 不做语音全链路 < 5 秒验收 —— 需要真实 TTS + ASR 接入

---

## 八、预估影响面

| 维度 | 影响 |
|------|------|
| 新增后端文件 | `api/voice.py`、`models/avatar_config.py`、`schemas/` 中新增响应类 |
| 修改后端文件 | `api/router.py`（注册路由）、`api/admin.py`（新增端点）、`db/base.py`（注册模型）、`db/bootstrap.py`（种子数据）、`core/config.py`（预留配置项） |
| 新增前端文件 | `composables/useAvatar.js`、`components/AvatarDisplay.vue`、`api/voice.js` |
| 修改前端文件 | `composables/useRecorder.js`、`composables/useAudioPlayer.js`、`stores/chat.js`、`views/tourist/ChatView.vue` |
| 新增数据库表 | `avatar_configs`（1 张新表） |
| 新增依赖 | 无 |
| 现有功能影响 | ChatView 新增 Avatar 显示区和录音按钮升级，文本问答功能不受影响 |

---

## 九、与阶段 C 的关系

阶段 C（管理后台可运营闭环）包含：

1. 知识 CRUD、同步和重建索引页面
2. 盲区处理页面
3. 数字人配置页面
4. 数据大屏与感受度报告

本次 E3 任务创建了 `AvatarConfig` 数据模型和管理 API，为阶段 C 的数字人配置页面做了后端准备。但阶段 C 的前端 `AvatarConfig.vue` 页面改造（从占位变为真实交互）留到阶段 C 正式执行，不在本次范围。

---

## 十、审批要求

按照主线文档第十三节执行纪律，以下内容需要用户在正式开始编码前确认：

1. 是否同意 D1-D3 + E1-E3 六个任务的编码范围和顺序
2. 是否同意新创数据库表 `avatar_configs`（`create_all` 创建）
3. 是否有额外的阶段 D/E 设计文档需要我参考
4. 是否有"另一个对话"中的方向性约束需要我合并进来

审批通过后，我将按照 D1 → D2 → D3 → E1 → E2 → E3 的顺序逐个执行，每个 Step 完成后运行测试并报告。
