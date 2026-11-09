# 架构与业务链路

> 2026-10-29 工作副本增量：ASR 与视觉接口支持可选 `Idempotency-Key`，按接口、键和请求 fingerprint 做 5 分钟进程内 single-flight 与 JSON 结果缓存；同键不同请求返回 409，超过 128 条/1 MiB 响应上限时拒绝新任务或淘汰过期/最近最少使用结果。不保存上传内容；旧客户端兼容。该能力不跨多 worker 或重启，聊天 SSE 和 K01 发布仍未接入持久幂等。实现入口见 [功能地图](REPO_MAP.md)。
> 真实 ASR provider 收到非 WAV 音频时，在占用既有 ASR 容量后通过 [audio_duration](../backend/app/services/audio_duration.py) 用受限 ffprobe 检查系统私有临时文件，校验音轨和时长后才调用 provider；结束后删除临时文件，最长运行时间可配置。该路径需部署系统安装 FFmpeg；游客录音器固定输出 WAV，不依赖它。当前只检查容器探测出的时长，不承诺完整解码验证。
> 生产环境 `APP_ENV=production` 时，管理员默认密码/签名密钥或过短值会阻止应用启动；`/ready` 同步报告配置缺项，不回显秘密。游客 API 仍公开；[CapacityLimiter](../backend/app/services/capacity.py) 只管单进程并发，不是时间窗口速率限制或多实例防刷。
> 2026-10-28 工作副本增量：聊天 SSE 在原有事件上补充心跳、连接/无数据/无进展/总时限与 `done.completion`；中断保留部分文本并停止音频。普通 TTS 句子并发合成、按序发送；分众 FAQ 在确定最终结果后输出一致的文字和语音。上传采用有界读取、图片容器尺寸检查及 WAV 时长检查，聊天/ASR/视觉使用可配置的单进程并发上限。实际实现与测试入口见 [功能地图](REPO_MAP.md)；K01 跨分支整合、非 WAV 时长及设备验收见专项记录。

核验于 2026-10-28，源码基线 `540568e`。这是现有实现的导航，未把路线图中的待办纳入已实现架构。
功能入口见 [REPO_MAP.md](REPO_MAP.md)，运行条件见 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 边界

```mermaid
flowchart LR
  UI[Vue 页面和工具] --> State[Pinia 与 composables]
  State --> Client[Axios 或 fetch SSE]
  Client --> API[FastAPI 路由与 schemas]
  API --> Service[QA / 视觉 / 语音 / 推荐]
  Service --> Repo[repositories]
  Repo --> DB[(SQL 数据库)]
  Service --> Index[(Chroma 与本地模型)]
  Service --> Provider[外部 AI 与天气服务]
```

- [main.js](../frontend/src/main.js) 安装 Pinia、Router、Element Plus；[App.vue](../frontend/src/App.vue) 区分游客舞台和后台布局。
- [router/index.js](../frontend/src/router/index.js) 决定实际页面；游客用一个持久舞台，探索/地图/路线/问答由 ChatView 展开。
- [api/router.py](../backend/app/api/router.py) 注册完整 `/api` 前缀；业务服务不直接决定 Web URL。
- [config.py](../backend/app/core/config.py) 是配置事实来源，设置和模型名称可被环境变量覆盖，不固定承诺某个模型版本。
- [models](../backend/app/models/) 定义 SQL 数据，[repositories](../backend/app/repositories/) 访问数据；Chroma 是另一存储层，更新 SQL 不等于更新向量索引。

## 1. 聊天 / RAG / 语音输出

1. [ChatView](../frontend/src/views/tourist/ChatView.vue) 的 `submitQuery` 收集问题、selection、受众和可选视觉/情绪上下文。
2. [chat store](../frontend/src/stores/chat.js) `sendMessage` 先停止旧输出，再建立新的 AbortController 与请求 token；`session_id` 和 `visitor_id` 分别关联会话及跨会话偏好。
3. [chat API](../frontend/src/api/chat.js) 调用 [useSSEStream](../frontend/src/composables/useSSEStream.js) 的 fetch POST；接口为 `POST /api/chat/stream`。
4. [chat.py](../backend/app/api/chat.py) 的 `build_pipeline` 组合 repository、FAQ、RAG、LLM、TTS 与记忆服务。
5. [QAPipeline.stream_chat](../backend/app/services/qa/pipeline.py) 根据问题、缓存、FAQ/检索证据及所选口径产出事件。具体分支以此函数为准，不能假设每个问题必经所有检索和供应商。
6. [StreamEvent.to_sse](../backend/app/services/qa/stream_events.py) 生成 UTF-8 `event:`/`data:` 帧；前端解析分块、消费文字/证据/音频，并驱动 [useAudioPlayer](../frontend/src/composables/useAudioPlayer.js) 和数字人。

历史回答重播走独立 `POST /api/chat/replay`：前端提交 `chat_log_id` 和当前 `session_id`；[ChatLogRepository](../backend/app/repositories/chat_log.py) 联合匹配归属后，API 仅把已保存的 `answer` 交给 TTS factory，不构建 QA pipeline。聊天保存时记录 answer SHA-256 与非秘密 TTS profile；[ReplayAudioCache](../backend/app/services/tts/replay_cache.py) 按内容指纹和完整 profile 复用合成结果，TTL 30 分钟、最多 128 项、编码音频总计不超过 16 MiB，缓存仅在单进程内有效。重播优先使用记录的生成音色；旧记录回退请求音色。前端共享播放器应用当前本机语速，TTS 未配置或音频无法解码时可回退浏览器朗读。语速偏好不跨设备同步；等 W01 定义游客身份与授权后再评估。

修改协议至少联读：服务端 `StreamEvent`、`QAPipeline`、前端 `useSSEStream`、`chat store`、[流式契约测试](../backend/app/tests/test_chat_stream_api.py)。新增事件须确认所有消费者，不能只改服务端名称。

普通 Axios 请求走 [http.js](../frontend/src/api/http.js) 的 bearer 拦截器；流式 fetch 使用自己的请求头，不自动继承 Axios 拦截器。认证策略变更时分别检查。

降级边界：`build_pipeline` 对部分向量/重排初始化异常有 fallback，TTS 可退回 stub；但 [main.py](../backend/main.py) 的 lifespan 会预加载本地模型，不可据此推断“没有模型也一定能启动”。

## 2. 录音和图像输入

- **录音**：[useRecorder](../frontend/src/composables/useRecorder.js) 优先 AudioWorklet，失败尝试 ScriptProcessor，输出 WAV；[voice API](../frontend/src/api/voice.js) 上传原始音频 body 到 `POST /api/asr/transcribe`。转写确认后再进入聊天。浏览器 [SpeechRecognition](../frontend/src/composables/useSpeechRecognition.js) 是另一能力通路，存在构造器不代表服务可用。
- **相机/相册**：[useCamera](../frontend/src/composables/useCamera.js) 返回 File，ChatView 或 file input 选择文件；[vision API](../frontend/src/api/vision.js) 以文件 MIME 上传原始 body 到 `POST /api/vision/analyze`，不是 multipart。
- **识别结果到回答**：[vision.py](../backend/app/api/vision.py) 校验 MIME/大小并返回候选景点、文字、检索查询等；ChatView 的 `askFromImage` 把识别结果送入聊天。视觉识别和有证据的最终讲解是两个阶段。
- `.heic`、GIF 等不在当前 JPEG/PNG/WebP 白名单内；不得把“能打开相册”视为所有相册格式都能识别。
- 权限拒绝或设备不支持时使用已有文字输入/文件上传入口；回收 track 和对象 URL 的位置在 composables 与 ChatView 生命周期。

## 3. 定位和自动讲解

[MapView](../frontend/src/views/tourist/MapView.vue) → [useGeolocation](../frontend/src/composables/useGeolocation.js) / [useNarration](../frontend/src/composables/useNarration.js) → [narration API](../frontend/src/api/narration.js) → `POST /api/guide/narration` → [guide.py](../backend/app/api/guide.py)。

讲解接口复用 QA 生成文本，再合成整段音频，以景点/音色/模型/知识代次缓存并合并并发；不可用时返回 `available=False`，TTS 缺失也可返回文本。触发/排队状态机在 useNarration；请求、静态简介回退和播放编排在 MapView 的 `playNarration`，浏览器朗读在 useAudioPlayer。

定位层包含真实与模拟状态，坐标变换和触发阈值见 [narration 常量](../frontend/src/constants/narration.js)。当前 `onSuccess` 直接把 `pos.coords` 传给 `evaluate`，后者读取 `lat/lng`；原生浏览器坐标为 `latitude/longitude`，这是需要修复或通过真实定位回归澄清的静态风险，本次仅建图未改行为。模拟成功不能证明 GPS 链路正常。

## 4. 管理、数据与资源

- 登录与 token：[auth.py](../backend/app/api/auth.py)、[auth store](../frontend/src/stores/auth.js)。接口是否受保护以具体路由依赖为准，前端路由守卫只是导航控制。
- 知识 CRUD：[knowledge API](../backend/app/api/knowledge.py)；导入：[data_import](../backend/app/services/data_import/)；索引：[index_builder](../backend/app/services/rag/index_builder.py)。同步官方数据和重建索引会写入数据，不能作为只读健康检查。
- 数据新鲜度通过 [KnowledgeGeneration](../backend/app/models/knowledge_generation.py) 追踪。后台单条 CRUD 在同一 DB 事务中更新条目、切块、持久化答案缓存和知识代次；知识代次落后向量代次时，新 QA 请求走当前数据库回退检索。向量候选也会按当前切块校验，并补充当前数据库候选，防止索引重建期间使用陈旧文本。重建先准备未激活的集合，再以条件代次更新锁定发布版本后切换活动指针；若知识已变化则丢弃暂存集合，不改变活动索引。
- 百炼录音识别需要公开 URL 时，服务在识别完成后立即删除临时音频；进程重启和后续读取/上传会清理超过配置保留期的残留文件（默认 3600 秒）。
- [QACache](../backend/app/services/qa/cache.py) 使用内存及 [持久化缓存](../backend/app/repositories/qa_cache.py)，TTL 在 config 中默认七天；聊天缓存 namespace 包含知识代次，因此旧请求晚到写入旧代次缓存后，不会被新代次请求命中。
- [RAGIndexBuilder](../backend/app/services/rag/index_builder.py) 把完整索引写入新 Chroma collection，再原子切换活动 collection 指针。写入失败时旧 collection 保持可用。`build-rag-index` 只在构建期间知识代次未变化时标记索引为当前；状态可由 `GET /api/admin/knowledge-index-status` 查询。处理资料同步仍是全量源数据导入，不是保留人工改动的草稿发布流程；导入/发布工作区见 K01 设计。
- 盲区：QA tracker → [knowledge_blind_spot repository](../backend/app/repositories/knowledge_blind_spot.py) → 管理员 FAQ 解决闭环。
- 背景/欢迎语：[display_assets service](../backend/app/services/display_assets.py) 存储配置和上传资源；公开读取与后台写操作分开，URL 经 [display.js](../frontend/src/api/display.js) 解析。
- 记忆：[visitor_memory repository](../backend/app/repositories/visitor_memory.py) 和 [memory/profile.py](../backend/app/services/memory/profile.py)；浏览器本地标识并不代表跨设备账号同步。

## 5. 运行与部署

- `backend/main.py` 启动时执行 Alembic、bootstrap 与模型预热；先备好数据库、处理数据与模型缓存。
- `GET /health` 是进程级响应；`GET /ready` 检查部分数据库/配置条件，两者都不等于完整外部 AI 验收。
- Vite dev server 监听 `0.0.0.0:5173`，代理 `/api` 与 `/ui-assets` 到开发机后端；设置见 [vite.config.js](../frontend/vite.config.js)。
- 构建后的 `frontend/dist` 存在时，FastAPI 在最后挂载 SPA；外部反代需保留 API、上传资源、静态资源、history 路由回退和 SSE 流式传输。
- 生产手机访问需安全上下文。仅开放 Vite LAN 地址不能保证相机、录音和定位可用，见 [多端矩阵](COMPATIBILITY.md)。
