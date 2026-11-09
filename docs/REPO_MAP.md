# AI 数字人导览：功能与代码地图

核验日期：2026-10-29（Asia/Shanghai）。源码基线：`540568e`。
2026-10-28 补充：工作副本在 `672a104` 上有尚未提交的流式体验改动；下述新增入口和测试以当前工作副本为准。K01 在另一分支，勿把其能力当作本分支已合并。
2026-10-29 补充：当前工作副本新增游客语速偏好与 PCM/AudioBuffer/浏览器朗读统一调速、按会话归属重播历史回答、聊天语音 profile 元数据及有界重播缓存；详情见“合成语音、字幕、嘴型与语速偏好”行；变更仍未提交。
本文件说明定位和验证入口；不代表下列功能均已在真实设备或外部服务上通过验收。
2026-10-29 补充：评委体验验收发现并修复 1000–1399px 桌面窗口下地图栏过窄的问题；验收范围、实测结果与未覆盖边界见[评委体验验收记录](superpowers/plans/2026-10-29-judge-experience-acceptance.md)。
所有链接相对仓库，适用于 GitHub、本地编辑器及能读取 Markdown 的代码助手。

## 使用方法

1. 按用户任务找到功能行，先读 UI 入口及对应 API，再沿服务和数据层定位。
2. 涉及跨层修改时看 [架构](ARCHITECTURE.md)；启动和测试看 [开发指南](DEVELOPMENT.md)。
3. 涉及手机、平板、桌面或浏览器能力时看 [兼容性矩阵](COMPATIBILITY.md)。
4. 修改后更新相应行，并执行 `python scripts/check_repo_map.py`。
5. `python scripts/check_repo_map.py --json` 从当前源码导出实时 API 索引；它不是 OpenAPI，也不包含完整调用图。

## 首先定位这些入口

| 问题 | 事实来源 |
|---|---|
| 应用如何挂载 | [main.js](../frontend/src/main.js)、[App.vue](../frontend/src/App.vue) |
| 实际打开哪个页面 | [router/index.js](../frontend/src/router/index.js)：`/` 到 `/tourist`；`/tourist` 挂载 [TouristView](../frontend/src/views/tourist/TouristView.vue)，其内部为 [ChatView](../frontend/src/views/tourist/ChatView.vue) |
| 地图、探索、路线、问答工具 | 旧 `/tourist/map`、`/tourist/explore`、`/tourist/routes`、`/tourist/quiz` 重定向为统一舞台 query；组件由 ChatView 按工具展开 |
| 后端入口和路由 | [main.py](../backend/main.py) 的 `create_app`，及 [api/router.py](../backend/app/api/router.py) |
| 配置与数据连接 | [config.py](../backend/app/core/config.py)、[session.py](../backend/app/db/session.py)、[deps.py](../backend/app/core/deps.py) |
| 产品待办 | [路线图](plans/2026-10-27-feature-roadmap.md)、[双端 AI 工作台待开发清单](plans/2026-10-28-ai-workbench-backlog.md)；规划、旧报告均不能代替当前实现证据 |
| 对外介绍技术价值 | [卖点文书](selling-points/README.md)；每项卖点都链接到实现、测试和适用边界，不代表行业首创或未测性能 |

`HomePage.vue`、`LandingPage.vue` 等文件的存在不代表当前有对应路由。
当前数字人由 ThreeAvatar 使用 Three.js/VRM 实现；技术栈以当前组件与依赖为准。

## 2026-11-08 手机地图重构

游客地图由 `ChatView.vue` 的 `map-task` 容器承载，`MapView.vue` 使用 `assets/map-workspace.css` 固定铺满容器；仅一个景点/路线/图层/园区面板可展开，列表滚动限定在面板内。地点卡可直接播放现有景点讲解；地图发起聊天不再自动收起地图。独立“我的位置”调用浏览器单次定位并显示拒绝状态，不调用模拟降级定位；自动讲解沿用原生命周期并显示真实/模拟模式。路线仅为预设示意。

地图标记由 [mapMarkers](../frontend/src/utils/mapMarkers.js) 生成统一 SVG，并按屏幕距离聚合；[标记回归](../frontend/tests/map-markers.test.mjs) 检查聚合不改动地理数据及选中点优先。`mapSpots.js` 仍是未核验的演示近似坐标；地图与地点卡明确显示提示。

地图坐标审核见 [mapCoordinateAudit](../frontend/src/constants/mapCoordinateAudit.js)、[路线站点](../frontend/src/constants/mapCoordinateAudit.js)、[复核记录](../reports/2026-11-09-map-coordinate-recalibration.md) 和 [审核测试](../frontend/tests/map-coordinate-audit.test.mjs)：目录内15处高德 GCJ-02 POI 参考点，另有5处路线专用 POI，地图共20处参考标记；1处目录景点仍待核验，6处其它景区项目不在此落点。POI参考点不代表入口或测绘边界。步行路径由服务端 `/api/guide/map/walking-route` 按高德路线规划逐段获取，不再连接虚线示意；未核验景点不参与路线。旧 `mapSpots.js` 坐标仅保留热度演示输入，不代表审核通过。名称标签由 mapMarkers 的屏幕避让逻辑决定，不能移动地理坐标来避让。

## 游客功能

| 功能 | 前端入口及状态 | 后端入口与业务 | 验证位置 |
|---|---|---|---|
| 聊天、流式回答、停止输出 | [ChatView](../frontend/src/views/tourist/ChatView.vue) `submitQuery` → [chat store](../frontend/src/stores/chat.js) `sendMessage/stopOutput` → [chat API](../frontend/src/api/chat.js) → [SSE](../frontend/src/composables/useSSEStream.js) | `POST /api/chat/stream`；[chat.py](../backend/app/api/chat.py) `build_pipeline/stream_chat` → [QAPipeline](../backend/app/services/qa/pipeline.py) | [流式契约测试](../backend/app/tests/test_chat_stream_api.py)、[pipeline 测试](../backend/app/tests/test_pipeline.py)；浏览器检查停止后无旧消息/音频回流 |
| 景点/主题选择与分众讲解 | [interaction store](../frontend/src/stores/interaction.js)、[quickSelect](../frontend/src/api/quickSelect.js)、[touristCatalog](../frontend/src/constants/touristCatalog.js) | `GET /api/quick-select/bootstrap`；[quick_select.py](../backend/app/api/quick_select.py)、[guided_selector](../backend/app/services/qa/guided_selector.py)、[prompt_builder](../backend/app/services/llm/prompt_builder.py) | [quick select](../backend/app/tests/test_quick_select.py)、[受众](../backend/app/tests/test_pipeline_audience.py)、[选择缓存键](../backend/app/tests/test_selection_cache_key_audience.py) |
| FAQ、RAG 与证据引用 | [chat store](../frontend/src/stores/chat.js) `sources`、ChatView 引用点击、[Markdown 清洗](../frontend/src/composables/useMarkdown.js) | 聊天共用入口；[FAQ runtime](../backend/app/services/qa/runtime.py)、[FAQ matcher](../backend/app/services/qa/faq_matcher.py)、[Chroma 检索](../backend/app/services/rag/chroma_retriever.py)、[reranker](../backend/app/services/rag/resilient_reranker.py) | [FAQ matcher](../backend/app/tests/test_faq_matcher.py)、[语义门控](../backend/app/tests/test_faq_semantic_gate.py)、[检索](../backend/app/tests/test_rag_retriever.py)、[评测说明](../eval/README.md) |
| 录音识别与语音输入 | ChatView `toggleRecording`；[useRecorder](../frontend/src/composables/useRecorder.js)、[worklet](../frontend/public/recorder-worklet.js)、[useSpeechRecognition](../frontend/src/composables/useSpeechRecognition.js)、[voice API](../frontend/src/api/voice.js)、[idempotencyKey](../frontend/src/utils/idempotencyKey.js) | `POST /api/asr/transcribe`；[voice.py](../backend/app/api/voice.py) → [asr 服务](../backend/app/services/asr/)；百炼需要公开 URL 时录音在识别完成后立即删除，过期残留按 `ASR_PUBLIC_AUDIO_RETENTION_SECONDS` 清理；[幂等协调器](../backend/app/services/idempotency.py)；真实 provider 非 WAV 时经 [audio_duration](../backend/app/services/audio_duration.py) 调用受限 ffprobe | [voice API](../backend/app/tests/test_voice_api.py)、[音频探测器](../backend/app/tests/test_audio_duration.py)、[幂等协调器](../backend/app/tests/test_idempotency.py)、[前端幂等键](../frontend/tests/idempotency-key.test.mjs)、[本地 ASR](../backend/app/tests/test_asr_local_sensevoice.py)；游客录音器输出 WAV；部署非 WAV ASR 需安装 ffprobe |
| 合成语音、字幕、嘴型、语速偏好与重播 | [useAudioPlayer](../frontend/src/composables/useAudioPlayer.js) 以会话 ID 隔离播放所有权，并统一调节 AudioBuffer、PCM、浏览器朗读速度；[speechRatePreference](../frontend/src/utils/speechRatePreference.js) 保存游客本机偏好；[chatReplay](../frontend/src/utils/chatReplay.js) 与 [ChatView](../frontend/src/views/tourist/ChatView.vue) 重播已完成回答；[chat store](../frontend/src/stores/chat.js) 绑定聊天会话并使用中性后端速率；[MapView](../frontend/src/views/tourist/MapView.vue) 绑定地图讲解并在 KeepAlive 隐藏时清理；[useAvatar](../frontend/src/composables/useAvatar.js) | 欢迎语 `GET /api/chat/welcome-audio`；重播 `POST /api/chat/replay` 通过 [ChatLogRepository](../backend/app/repositories/chat_log.py) 按日志 ID/session ID 读取已保存答案和 `speech_metadata`，按答案指纹及 TTS profile 查 [ReplayAudioCache](../backend/app/services/tts/replay_cache.py)，未命中后调用 [TTS factory](../backend/app/services/tts/factory.py)；profile 与指纹见 [speech_profile](../backend/app/services/tts/speech_profile.py)；schema 迁移见 [chat speech metadata migration](../backend/alembic/versions/c3b7e1d9a62f_add_chat_speech_metadata.py)；流式 TTS 事件与 [viseme](../backend/app/services/avatar/viseme.py) | [播放器回归](../frontend/tests/audio-player.test.mjs)、[重播控制测试](../frontend/tests/chat-replay.test.mjs)、[偏好存储测试](../frontend/tests/speech-rate-preference.test.mjs)、[重播 API 测试](../backend/app/tests/test_chat_replay_api.py)、[profile 测试](../backend/app/tests/test_tts_speech_profile.py)、[缓存测试](../backend/app/tests/test_tts_replay_cache.py)、[repository 测试](../backend/app/tests/test_chat_log_repository.py)；供应商 TTS 与真机播放/打断/切后台/字幕和嘴型仍待验收 |
| 拍照/上传识景 → 问答 | ChatView `captureFromCamera/handleAnalyzeImage/askFromImage`；[useCamera](../frontend/src/composables/useCamera.js)、[vision API](../frontend/src/api/vision.js)、[idempotencyKey](../frontend/src/utils/idempotencyKey.js) | `POST /api/vision/analyze`；[vision.py](../backend/app/api/vision.py) → [Qwen vision](../backend/app/services/vision/qwen.py)；识别结果转换为查询及 `vision_context` 后走聊天；带键请求复用[进程内幂等协调器](../backend/app/services/idempotency.py) | [vision API](../backend/app/tests/test_vision_api.py)、[幂等协调器](../backend/app/tests/test_idempotency.py)、[前端幂等键](../frontend/tests/idempotency-key.test.mjs)、[Qwen](../backend/app/tests/test_qwen_vision_service.py)；JPEG/PNG/WebP、相册/摄像头、过大与不支持格式 |
| 地图定位、靠近景点讲解 | [MapView](../frontend/src/views/tourist/MapView.vue)、[useGeolocation](../frontend/src/composables/useGeolocation.js)、[useNarration](../frontend/src/composables/useNarration.js)、[mapSpots](../frontend/src/constants/mapSpots.js)、[narration 常量](../frontend/src/constants/narration.js)；[ChatView](../frontend/src/views/tourist/ChatView.vue) 在地图工具激活时添加 `map-open`；[guide-page.css](../frontend/src/assets/guide-page.css) 的 `map-task` 容器与 [map-workspace.css](../frontend/src/assets/map-workspace.css) 提供全幅地图和互斥任务面板 | `POST /api/guide/narration`；[guide.py](../backend/app/api/guide.py) 复用 QA/TTS，缓存整段讲解 | 本次地图界面已以七视口浏览器任务回归替代旧左栏宽度源码断言；[讲解 API](../backend/app/tests/test_guide_narration_api.py)；GPS、拒绝、低精度、模拟标识、重复触发需浏览器验证 |
| 路线推荐 | [RouteView](../frontend/src/views/tourist/RouteView.vue)、[recommend API](../frontend/src/api/recommend.js) | `POST /api/recommend/`；[recommend.py](../backend/app/api/recommend.py)、[RecommendEngine](../backend/app/services/recommend/engine.py)、[route repository](../backend/app/repositories/route.py) | [舒适度推荐](../backend/app/tests/test_recommend_comfort.py)；地图坐标/路线显示需人工验收 |
| 探索/知识问答工具 | [ExploreView](../frontend/src/views/tourist/ExploreView.vue)、[QuizView](../frontend/src/views/tourist/QuizView.vue)，由 ChatView 接收工具问题 | 按组件请求与问答事件复用现有接口；当前没有独立 `/api/quiz` | 工具展开、问题提交、返回舞台需人工验证；不能仅用后端测试证明工具 UI |
| 游客记忆与反馈 | [chat store](../frontend/src/stores/chat.js) `getVisitorId/clearVisitorMemoryEverywhere`、[insights API](../frontend/src/api/insights.js) | `DELETE /api/chat/visitor-memory/{visitor_id}`、`POST /api/insights/feedback`；[记忆画像](../backend/app/services/memory/profile.py)、[记忆 repository](../backend/app/repositories/visitor_memory.py) | [记忆 API](../backend/app/tests/test_visitor_memory_api.py)、[记忆 prompt](../backend/app/tests/test_memory_prompt.py)；跨标签页/清除失败与重试需前端验收 |
| 天气与景区提醒 | [useWeather](../frontend/src/composables/useWeather.js)、[weather API](../frontend/src/api/weather.js) | `GET /api/weather/current`；[weather.py](../backend/app/api/weather.py)，服务端代理和缓存 | 当前无专门 weather 测试文件；缺配置/网络失败/默认坐标需验证 |

## 管理与运营功能

后台页面路由见 `router/index.js`，壳和导航见 App.vue。前端路由守卫不替代后端鉴权。

| 功能 | 前端入口 | 后端与数据 | 验证位置 |
|---|---|---|---|
| 管理员登录 | [AdminLogin](../frontend/src/views/admin/AdminLogin.vue)、[auth store](../frontend/src/stores/auth.js) | `POST /api/auth/login`；[auth.py](../backend/app/api/auth.py) 的 `require_admin_token`；受保护范围见 [admin.py](../backend/app/api/admin.py)、[knowledge.py](../backend/app/api/knowledge.py)、[insights.py](../backend/app/api/insights.py) 的实际依赖 | 当前无独立 auth 测试文件；验收匿名访问、错误密码、token 过期及 401 |
| 知识增删改查/导入/索引/旧答案 | [KnowledgeManage](../frontend/src/views/admin/KnowledgeManage.vue)、[knowledge API](../frontend/src/api/knowledge.js) | [knowledge.py](../backend/app/api/knowledge.py)、[admin.py](../backend/app/api/admin.py) 的 `sync_processed_data/build_rag_index/knowledge_index_status`、[importer](../backend/app/services/data_import/importer.py)、[切块 repository](../backend/app/repositories/knowledge_chunk.py)、[代次 repository/model](../backend/app/repositories/knowledge_generation.py)、[index_builder](../backend/app/services/rag/index_builder.py)、[QA 缓存](../backend/app/services/qa/cache.py)；详见下方“知识更新后仍返回旧答案” | [知识 API](../backend/app/tests/test_knowledge_api.py)、[代次与陈旧索引回退](../backend/app/tests/test_knowledge_generation.py)、[索引状态 API](../backend/app/tests/test_knowledge_index_admin.py)、[安全索引切换](../backend/app/tests/test_vector_store_generations.py)、[当前知识过滤](../backend/app/tests/test_rag_knowledge_consistency.py)、[导入](../backend/app/tests/test_data_import.py) |
| 知识盲区闭环 | [BlindSpotManage](../frontend/src/views/admin/BlindSpotManage.vue)、[admin API](../frontend/src/api/admin.js) | `GET /api/admin/blind-spots`；[BlindSpotTracker](../backend/app/services/qa/blind_spot_tracker.py)、[resolution](../backend/app/services/qa/blind_spot_resolution.py)、[repository](../backend/app/repositories/knowledge_blind_spot.py) | [管理测试](../backend/app/tests/test_blind_spot_admin.py)、[追踪](../backend/app/tests/test_blind_spot_tracker.py) |
| 数字人/音色配置 | [AvatarConfig](../frontend/src/views/admin/AvatarConfig.vue)、[ThreeAvatar](../frontend/src/components/ThreeAvatar.vue)、[形象预设](../frontend/src/components/avatar-presets/)、[SVG 降级](../frontend/src/components/AvatarDisplay.vue) | `GET /api/admin/avatar-configs/active`；[admin.py](../backend/app/api/admin.py)、[avatar model](../backend/app/models/avatar_config.py)、[TTS voices](../backend/app/services/tts/voices.py) | [音色预设](../backend/app/tests/test_tts_voice_presets.py)；模型加载失败/低性能/切形象需人工验收 |
| 背景、欢迎语、展示设置 | [DisplayAssets](../frontend/src/views/admin/DisplayAssets.vue)、[useScenicBackground](../frontend/src/composables/useScenicBackground.js) | `GET /api/display-assets/`；[display API](../backend/app/api/display_assets.py)、[display service](../backend/app/services/display_assets.py)、[admin.py](../backend/app/api/admin.py) | 上传/清除/失败占位、公开读与受保护写、跨标签刷新需人工验证；没有专门展示资源测试文件 |
| 数据看板、情绪、体验报告 | [Dashboard](../frontend/src/views/admin/Dashboard.vue)、[AnalyticsReport](../frontend/src/views/admin/AnalyticsReport.vue)、[ExperienceReport](../frontend/src/views/admin/ExperienceReport.vue) | [insights.py](../backend/app/api/insights.py)、[emotion](../backend/app/services/emotion/)、[insights/emotion.py](../backend/app/services/insights/emotion.py)、[experience_report.py](../backend/app/services/experience_report.py) | [情绪](../backend/app/tests/test_emotion.py)、[情绪统计](../backend/app/tests/test_emotion_insights.py)、[标签](../backend/app/tests/test_insights_labels.py)；图表和报告 UI 需人工验收 |

## 按症状排查：知识更新后仍返回旧答案

当前后台知识 CRUD 在单个数据库事务中写入条目、切块、缓存失效和知识代次；接口失败会回滚并返回失败步骤。向量索引作为可重建副本：知识代次变化后，问答先直接使用数据库当前条目，直到索引构建并标记为同代次。索引重建先写未激活的 collection，再以条件代次更新锁定发布版本后原子切换指针；知识在构建期间变化则丢弃暂存 collection，活动索引不变。讲解缓存键也包含知识代次。仍需区分“处理数据同步”与人工编辑：同步导入仍以处理数据为准，并非草稿/冲突审阅工作区。

| 层次 | 直接定位 | 当前边界 |
|---|---|---|
| 知识条目与切块 | [api/knowledge.py](../backend/app/api/knowledge.py) `create/update/delete_knowledge` → [KnowledgeRepository](../backend/app/repositories/knowledge.py)、[KnowledgeChunkRepository](../backend/app/repositories/knowledge_chunk.py)、[KnowledgeChunker](../backend/app/services/data_import/chunker.py) | 条目、对应切块、答案缓存删除和知识代次在同一个事务中提交；切块准备失败回滚条目变更并返回阶段错误 |
| 向量索引 | [admin.build_rag_index](../backend/app/api/admin.py) → [RAGIndexBuilder.build](../backend/app/services/rag/index_builder.py) → [ChromaVectorStore](../backend/app/services/rag/vector_store.py) | `POST /api/admin/build-rag-index` 从当前切块构建新 generation collection 后原子替换活动指针；失败保留旧 collection。构建时知识代次有变化则拒绝标记为当前。|
| 查询过渡与可见性 | [VectorBackedRAGService](../backend/app/services/rag/chroma_retriever.py)、[RepositoryBackedRAGService](../backend/app/services/rag/retriever.py)、[KnowledgeGeneration](../backend/app/models/knowledge_generation.py) | 索引代次落后时新 QA 请求直接查数据库；向量候选按当前切块文本核对，且合并当前数据库结果。状态由 `GET /api/admin/knowledge-index-status` 返回，管理页显示索引重建提示 |
| 答案缓存 | [QACache](../backend/app/services/qa/cache.py)、[QACacheRepository](../backend/app/repositories/qa_cache.py)、[build_answer_cache_namespace](../backend/app/api/chat.py) | 知识代次包含在缓存 namespace；变更事务同步清空持久化缓存，迟到的旧代次缓存写入不影响新代次请求。TTL 在 config 中默认七天，可配置 |
| FAQ 运行时 | [qa/runtime.py](../backend/app/services/qa/runtime.py) 的 `reload_runtime_faq_matcher`、[admin.py](../backend/app/api/admin.py) | FAQ 运行时与 Chroma/答案缓存是不同层；查明回答来自哪条分支再处理 |

验证覆盖新增/修改/删除到切块、缓存和代次的同步；准备失败回滚；代次落后时回退到数据库；旧向量候选验证；索引构建失败保留旧代次；构建中知识变化不会发布暂存索引；索引重建成功后代次对齐；讲解缓存按代次隔离。FAQ 运行时是独立数据面，官方资料同步后仍由同步接口重载；本链路不把 FAQ 编辑或草稿发布并入知识 CRUD。K01 文档导入冲突工作区仍按[设计](superpowers/specs/2026-10-27-knowledge-workspace-design.md)单独实现。

## 共用基础设施

| 职责 | 位置与变更注意 |
|---|---|
| API 基址、超时、普通请求鉴权 | [http.js](../frontend/src/api/http.js)；普通请求与流式 fetch 是不同通路 |
| 流式恢复与播放诊断 | [useSSEStream](../frontend/src/composables/useSSEStream.js)、[chat store](../frontend/src/stores/chat.js)、[chatMetrics](../frontend/src/utils/chatMetrics.js)、[音频缓冲实验](../frontend/src/utils/adaptiveAudioBuffer.js)；前端 `npm test` 覆盖中断、代际、PCM、指标和模拟轨迹，验证边界见[验收记录](superpowers/plans/2026-10-28-ai-stream-validation.md) |
| 上传与单进程并发保护 | [bounded_body](../backend/app/api/bounded_body.py)、[capacity](../backend/app/services/capacity.py)、[图片容器检查](../backend/app/services/vision/image_headers.py)；并发限制不是多进程全局限流，WAV 时长与图片头部检查的边界见[验收记录](superpowers/plans/2026-10-28-ai-stream-validation.md) |
| 管理员生产鉴权配置 | [auth.py](../backend/app/api/auth.py) 使用 HMAC Bearer token；[Settings.production_security_failures](../backend/app/core/config.py) 检查生产密码与 token secret，[main lifespan](../backend/main.py) 在迁移/预热前 fail-fast；访客接口仍公开，时间窗口限流待设计 |
| ASR/视觉重试幂等 | [idempotency coordinator](../backend/app/services/idempotency.py)按接口/键/请求 SHA-256 合并请求，前端键生成器见 [idempotencyKey](../frontend/src/utils/idempotencyKey.js)；限进程内 5 分钟、128 项及 1 MiB JSON 结果，不保存上传原文，不跨 worker/重启共享；同键不同请求 409 |
| 非 WAV ASR 时长边界 | [audio_duration](../backend/app/services/audio_duration.py) 将有界请求写入系统私有临时文件交给 ffprobe，限制协议、探测参数和超时，结束后清理；仅真实 provider 的非 WAV 路径启用；通过 `ASR_FFPROBE_PATH` 与 `ASR_PROBE_TIMEOUT_SECONDS` 配置，部署需提供 ffprobe |
| 发布恢复适配 | [publicationRecovery](../frontend/src/utils/publicationRecovery.js) 保存同一浏览器会话中的待确认请求；K01 接入位于[集成补丁](superpowers/plans/2026-10-28-k01-stream-integration.patch)，联合测试结果与应用边界见[验收记录](superpowers/plans/2026-10-28-ai-stream-validation.md) |
| 开发代理 | [vite.config.js](../frontend/vite.config.js)；前端不是让手机直连手机自身的 localhost 后端 |
| 请求/响应契约 | [schemas](../backend/app/schemas/)、[StreamEvent](../backend/app/services/qa/stream_events.py) |
| 数据库/迁移 | [models](../backend/app/models/)、[repositories](../backend/app/repositories/)、[alembic](../backend/alembic/)；启动会迁移与 bootstrap |
| 景区数据与检索索引 | [data](../data/)、`kb/chroma_db`、模型缓存；后两者被忽略，克隆不会带齐本地模型和数据库 |
| 质量与延迟评估 | [eval/scripts](../eval/scripts/)、[eval/tests](../eval/tests/)、[evaluation](../evaluation/README.md)；执行前读脚本参数与服务条件 |
| 既有 Windows 检查 | [competition_check.ps1](../scripts/competition_check.ps1)；依赖 `.venv/Scripts/python.exe` 和 `cmd`，不能当作跨系统入口 |

## 维护和核验边界

- 重命名文件/移动模块：更新对应功能行与本地链接。
- 修改接口：更新本文件中的方法与完整路径，核对 frontend API、schema、测试。
- 修改链路/降级：更新架构；设备能力变更更新兼容性矩阵。
- 新功能按既有行格式记录入口、服务、数据、验证；找不到测试时明确写人工验证或缺口。
- 校验器检查这套地图的文件链接和显式 API 引用，并从实际 router 注册生成 JSON；不验证 Markdown 锚点、远程网页、权限配置、动态路由或 UI 运行效果。
- 历史“19 failed / 104 passed”等报告不是本次基线，需重新运行方可引用为当前结果。
- 实际任务导航、迁移和故障注入的验证记录见 [地图可用性测试](REPO_MAP_USABILITY.md)。
