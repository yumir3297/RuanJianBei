# Architecture

> 当前实现采用“Vue 单页应用 + FastAPI 分层后端 + PostgreSQL/Chroma + 多模型 provider”的模块化单体架构。核心价值不只是一次问答，而是将交互、数字人表达、用户画像和运营改进串成闭环。

部署边界已由团队确认为比赛演示，而非当前阶段的公网生产系统。演示配置实际使用 DeepSeek LLM、百炼 TTS、百炼 ASR、Qwen Vision、OpenWeatherMap 与浏览器语音。

## Core Sections (Required)

### 1) Architectural Style

- 部署形态：前后端分离；后端是模块化单体，不是微服务。
- 后端模式：API/Schema/Service/Repository/Model 分层，服务层内按 RAG、ASR、TTS、视觉、情绪、推荐、洞察等能力拆模块。
- 集成模式：外部 AI 能力采用 provider/strategy 适配器，可按配置替换云端、本地或 stub 实现。
- 数据模式：PostgreSQL 保存业务与运营数据；Chroma 保存向量索引；本地模型负责 embedding、rerank 和可选 ASR。
- 前端模式：Vue Router 组织游客端与管理端；Pinia 保存会话；composable 封装录音、播放、SSE 和数字人控制。

### 2) System Flow

核心游客问答链路：

```text
文字/语音/图片/快捷选择
  -> 前端标准化输入（录音先 ASR，图片进入多模态上下文）
  -> /api/chat 流式请求
  -> 情绪分析 + 游客画像/上下文 + 意图识别/问题改写
  -> 可选动态路由（Coze）或本地 FAQ/缓存/RAG/重排
  -> DeepSeek 基于证据生成
  -> SSE 多路事件：少量文本 token、音频片段、口型/表情/动作、来源、追问、完成
  -> 前端增量渲染并同步驱动 VRM 数字人
  -> 保存对话、反馈、行为与情绪统计
  -> 管理端发现知识盲区并补充知识库
  -> 后续检索和回答质量提升
```

数据生命周期约束：用于管理后台统计、反馈、画像和知识改进的数据可以持久化；其他会话级临时数据应在游客退出时删除。当前公开 ASR 上传音频尚未看到自动清理实现，因此该约束仍存在代码落地缺口。

“多次少量发送 token”的作用是降低首字等待并适配不稳定网络；流式 TTS 与 LLM 并行，将已稳定的文本片段尽早转成音频，避免等待整段回答。SSE 把文本、语音和数字人控制信息放在同一会话序列中，前端按到达顺序逐步播放与表达。代码依据是 `backend/app/api/chat.py`、`backend/app/services/qa/pipeline.py`、`backend/app/services/tts/streaming.py`、`frontend/src/composables/useSSEStream.js` 和 `frontend/src/stores/chat.js`。

情绪与体验闭环：

```text
输入情绪/表达特征
  -> 对话策略与数字人情绪呈现
  -> 互动、推荐、路线、探索、问答游戏
  -> 点赞/点踩/反馈 + 行为摘要 + 情绪趋势
  -> 体验报告/运营分析/知识盲区
  -> 管理员修订知识与服务内容
  -> 新一轮游客交互
```

### 3) Layer/Module Responsibilities

| 模块 | 责任 | 代表路径 |
|---|---|---|
| 接入与协议 | HTTP/SSE、鉴权、参数和错误映射 | `backend/app/api/`、`backend/app/schemas/` |
| 问答编排 | 意图、改写、FAQ、缓存、RAG、生成和事件编排 | `backend/app/services/qa/` |
| 知识检索 | 文档切分、索引、向量召回、BM25/重排 | `backend/app/services/rag/` |
| 感知与表达 | ASR、TTS、视觉、情绪、数字人事件 | `backend/app/services/asr/`、`tts/`、`vision/`、`emotion/`、`avatar/` |
| 游客服务 | 推荐、路线、快捷主题、体验报告 | `backend/app/services/recommend/`、`experience_report.py` |
| 运营闭环 | 反馈、情绪洞察、行为摘要、知识盲区 | `backend/app/services/insights/`、`backend/app/api/insights.py` |
| 数据访问 | ORM 查询、事务和持久化 | `backend/app/repositories/`、`models/`、`db/` |
| 游客体验 UI | 对话、探索、路线、游戏和数字人 | `frontend/src/views/tourist/`、`frontend/src/components/ThreeAvatar.vue` |
| 运营管理 UI | 知识、分析、体验和盲区管理 | `frontend/src/views/admin/` |

### 4) Reused Patterns

- Repository：屏蔽 SQLAlchemy 查询细节，Service 通过仓储处理业务数据。
- Provider/Strategy：ASR、TTS、视觉、实时数据和动态路由可按配置选择实现。
- Pipeline：问答步骤按优先级串联，形成“快捷命中—缓存—RAG—生成—降级”路径。
- Factory/依赖组装：API 层根据 Settings 创建 provider，并通过缓存函数复用重模型。
- Cache/Singleton：embedding、reranker、FAQ 语义索引等进程内复用，降低初始化成本。
- Fallback：云能力失败时回落到本地、stub、HTTP TTS 或浏览器语音等可用路径。
- Producer/Multiplexer：LLM 文本与流式 TTS 通过异步任务/队列合并为 SSE 事件。

### 5) Known Architectural Risks

- 启动阶段预加载 embedding、reranker 和 FAQ 索引；本地模型缺失可能使服务在进入运行期降级逻辑前就启动失败。
- 多个缓存和单例是进程内状态；水平扩容时实例间可能不一致，且重复加载模型占用大量内存。
- `pipeline.py`、`ChatView.vue`、`ThreeAvatar.vue` 等核心文件过大，编排、状态和表现耦合度持续增加。
- 外部 provider 有超时与降级，但未见统一重试、指数退避、熔断和限流层。
- SSE 和进程内异步任务适合当前演示/单体部署；中断恢复、跨实例粘性和后台作业持久化尚无专门基础设施。
- 演示实际启用 DeepSeek、百炼 TTS/ASR、Qwen Vision、OpenWeatherMap 和浏览器语音；实时景区综合数据和 Coze 仍分别是 mock 与 disabled，宣传材料需按此边界表述。

### 6) Evidence

- `backend/app/main.py`
- `backend/app/api/chat.py`
- `backend/app/services/qa/pipeline.py`
- `backend/app/services/qa/runtime.py`
- `backend/app/services/rag/retriever.py`
- `backend/app/services/tts/streaming.py`
- `backend/app/services/emotion/`
- `backend/app/services/insights/`
- `backend/app/repositories/`
- `backend/app/db/session.py`
- `frontend/src/router/index.js`
- `frontend/src/stores/chat.js`
- `frontend/src/composables/useSSEStream.js`
- `frontend/src/components/ThreeAvatar.vue`
- `frontend/src/views/tourist/ChatView.vue`
