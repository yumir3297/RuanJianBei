# AI 数字人导览：功能与代码地图

核验日期：2026-10-28（Asia/Shanghai）。源码基线：`540568e`。
本文件说明定位和验证入口；不代表下列功能均已在真实设备或外部服务上通过验收。
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
| 产品待办 | [路线图](plans/2026-10-27-feature-roadmap.md)；规划、旧报告均不能代替当前实现证据 |

`HomePage.vue`、`LandingPage.vue` 等文件的存在不代表当前有对应路由。
当前数字人由 ThreeAvatar 使用 Three.js/VRM 实现；技术栈以当前组件与依赖为准。

## 游客功能

| 功能 | 前端入口及状态 | 后端入口与业务 | 验证位置 |
|---|---|---|---|
| 聊天、流式回答、停止输出 | [ChatView](../frontend/src/views/tourist/ChatView.vue) `submitQuery` → [chat store](../frontend/src/stores/chat.js) `sendMessage/stopOutput` → [chat API](../frontend/src/api/chat.js) → [SSE](../frontend/src/composables/useSSEStream.js) | `POST /api/chat/stream`；[chat.py](../backend/app/api/chat.py) `build_pipeline/stream_chat` → [QAPipeline](../backend/app/services/qa/pipeline.py) | [流式契约测试](../backend/app/tests/test_chat_stream_api.py)、[pipeline 测试](../backend/app/tests/test_pipeline.py)；浏览器检查停止后无旧消息/音频回流 |
| 景点/主题选择与分众讲解 | [interaction store](../frontend/src/stores/interaction.js)、[quickSelect](../frontend/src/api/quickSelect.js)、[touristCatalog](../frontend/src/constants/touristCatalog.js) | `GET /api/quick-select/bootstrap`；[quick_select.py](../backend/app/api/quick_select.py)、[guided_selector](../backend/app/services/qa/guided_selector.py)、[prompt_builder](../backend/app/services/llm/prompt_builder.py) | [quick select](../backend/app/tests/test_quick_select.py)、[受众](../backend/app/tests/test_pipeline_audience.py)、[选择缓存键](../backend/app/tests/test_selection_cache_key_audience.py) |
| FAQ、RAG 与证据引用 | [chat store](../frontend/src/stores/chat.js) `sources`、ChatView 引用点击、[Markdown 清洗](../frontend/src/composables/useMarkdown.js) | 聊天共用入口；[FAQ runtime](../backend/app/services/qa/runtime.py)、[FAQ matcher](../backend/app/services/qa/faq_matcher.py)、[Chroma 检索](../backend/app/services/rag/chroma_retriever.py)、[reranker](../backend/app/services/rag/resilient_reranker.py) | [FAQ matcher](../backend/app/tests/test_faq_matcher.py)、[语义门控](../backend/app/tests/test_faq_semantic_gate.py)、[检索](../backend/app/tests/test_rag_retriever.py)、[评测说明](../eval/README.md) |
| 录音识别与语音输入 | ChatView `toggleRecording`；[useRecorder](../frontend/src/composables/useRecorder.js)、[worklet](../frontend/public/recorder-worklet.js)、[useSpeechRecognition](../frontend/src/composables/useSpeechRecognition.js)、[voice API](../frontend/src/api/voice.js) | `POST /api/asr/transcribe`；[voice.py](../backend/app/api/voice.py) → [asr 服务](../backend/app/services/asr/) | [voice API](../backend/app/tests/test_voice_api.py)、[本地 ASR](../backend/app/tests/test_asr_local_sensevoice.py)；真机权限、拒绝、停止录音、WAV/超时回退 |
| 合成语音、字幕、嘴型 | [useAudioPlayer](../frontend/src/composables/useAudioPlayer.js)、[useAvatar](../frontend/src/composables/useAvatar.js)、[chat store](../frontend/src/stores/chat.js) | 聊天事件；[TTS factory](../backend/app/services/tts/factory.py)、[流式 TTS](../backend/app/services/tts/streaming.py)、[viseme](../backend/app/services/avatar/viseme.py)；欢迎语 `GET /api/chat/welcome-audio` | [TTS factory](../backend/app/tests/test_tts_factory.py)、[流式](../backend/app/tests/test_tts_streaming.py)、[嘴型](../backend/app/tests/test_viseme.py)；真机播放/打断/切后台 |
| 拍照/上传识景 → 问答 | ChatView `captureFromCamera/handleAnalyzeImage/askFromImage`；[useCamera](../frontend/src/composables/useCamera.js)、[vision API](../frontend/src/api/vision.js) | `POST /api/vision/analyze`；[vision.py](../backend/app/api/vision.py) → [Qwen vision](../backend/app/services/vision/qwen.py)；识别结果转换为查询及 `vision_context` 后走聊天 | [vision API](../backend/app/tests/test_vision_api.py)、[Qwen](../backend/app/tests/test_qwen_vision_service.py)；JPEG/PNG/WebP、相册/摄像头、过大与不支持格式 |
| 地图定位、靠近景点讲解 | [MapView](../frontend/src/views/tourist/MapView.vue)、[useGeolocation](../frontend/src/composables/useGeolocation.js)、[useNarration](../frontend/src/composables/useNarration.js)、[mapSpots](../frontend/src/constants/mapSpots.js)、[narration 常量](../frontend/src/constants/narration.js) | `POST /api/guide/narration`；[guide.py](../backend/app/api/guide.py) 复用 QA/TTS，缓存整段讲解 | [讲解 API](../backend/app/tests/test_guide_narration_api.py)；GPS、拒绝、低精度、模拟标识、重复触发需浏览器验证 |
| 路线推荐 | [RouteView](../frontend/src/views/tourist/RouteView.vue)、[recommend API](../frontend/src/api/recommend.js) | `POST /api/recommend/`；[recommend.py](../backend/app/api/recommend.py)、[RecommendEngine](../backend/app/services/recommend/engine.py)、[route repository](../backend/app/repositories/route.py) | [舒适度推荐](../backend/app/tests/test_recommend_comfort.py)；地图坐标/路线显示需人工验收 |
| 探索/知识问答工具 | [ExploreView](../frontend/src/views/tourist/ExploreView.vue)、[QuizView](../frontend/src/views/tourist/QuizView.vue)，由 ChatView 接收工具问题 | 按组件请求与问答事件复用现有接口；当前没有独立 `/api/quiz` | 工具展开、问题提交、返回舞台需人工验证；不能仅用后端测试证明工具 UI |
| 游客记忆与反馈 | [chat store](../frontend/src/stores/chat.js) `getVisitorId/clearVisitorMemoryEverywhere`、[insights API](../frontend/src/api/insights.js) | `DELETE /api/chat/visitor-memory/{visitor_id}`、`POST /api/insights/feedback`；[记忆画像](../backend/app/services/memory/profile.py)、[记忆 repository](../backend/app/repositories/visitor_memory.py) | [记忆 API](../backend/app/tests/test_visitor_memory_api.py)、[记忆 prompt](../backend/app/tests/test_memory_prompt.py)；跨标签页/清除失败与重试需前端验收 |
| 天气与景区提醒 | [useWeather](../frontend/src/composables/useWeather.js)、[weather API](../frontend/src/api/weather.js) | `GET /api/weather/current`；[weather.py](../backend/app/api/weather.py)，服务端代理和缓存 | 当前无专门 weather 测试文件；缺配置/网络失败/默认坐标需验证 |

## 管理与运营功能

后台页面路由见 `router/index.js`，壳和导航见 App.vue。前端路由守卫不替代后端鉴权。

| 功能 | 前端入口 | 后端与数据 | 验证位置 |
|---|---|---|---|
| 管理员登录 | [AdminLogin](../frontend/src/views/admin/AdminLogin.vue)、[auth store](../frontend/src/stores/auth.js) | `POST /api/auth/login`；[auth.py](../backend/app/api/auth.py) 的 `require_admin_token`；受保护范围见 [admin.py](../backend/app/api/admin.py)、[knowledge.py](../backend/app/api/knowledge.py)、[insights.py](../backend/app/api/insights.py) 的实际依赖 | 当前无独立 auth 测试文件；验收匿名访问、错误密码、token 过期及 401 |
| 知识增删改查/导入/索引/旧答案 | [KnowledgeManage](../frontend/src/views/admin/KnowledgeManage.vue)、[knowledge API](../frontend/src/api/knowledge.js) | [knowledge.py](../backend/app/api/knowledge.py)、[admin.py](../backend/app/api/admin.py) 的 `sync_processed_data/build_rag_index`、[importer](../backend/app/services/data_import/importer.py)、[分块 repository](../backend/app/repositories/knowledge_chunk.py)、[index_builder](../backend/app/services/rag/index_builder.py)、[QA 缓存](../backend/app/services/qa/cache.py)；详见下方“知识更新后仍返回旧答案” | [知识 API](../backend/app/tests/test_knowledge_api.py)、[导入](../backend/app/tests/test_data_import.py)、[索引构建](../backend/app/tests/test_rag_index_builder.py)；编辑到答案新鲜度的完整回归尚未验证 |
| 知识盲区闭环 | [BlindSpotManage](../frontend/src/views/admin/BlindSpotManage.vue)、[admin API](../frontend/src/api/admin.js) | `GET /api/admin/blind-spots`；[BlindSpotTracker](../backend/app/services/qa/blind_spot_tracker.py)、[resolution](../backend/app/services/qa/blind_spot_resolution.py)、[repository](../backend/app/repositories/knowledge_blind_spot.py) | [管理测试](../backend/app/tests/test_blind_spot_admin.py)、[追踪](../backend/app/tests/test_blind_spot_tracker.py) |
| 数字人/音色配置 | [AvatarConfig](../frontend/src/views/admin/AvatarConfig.vue)、[ThreeAvatar](../frontend/src/components/ThreeAvatar.vue)、[形象预设](../frontend/src/components/avatar-presets/)、[SVG 降级](../frontend/src/components/AvatarDisplay.vue) | `GET /api/admin/avatar-configs/active`；[admin.py](../backend/app/api/admin.py)、[avatar model](../backend/app/models/avatar_config.py)、[TTS voices](../backend/app/services/tts/voices.py) | [音色预设](../backend/app/tests/test_tts_voice_presets.py)；模型加载失败/低性能/切形象需人工验收 |
| 背景、欢迎语、展示设置 | [DisplayAssets](../frontend/src/views/admin/DisplayAssets.vue)、[useScenicBackground](../frontend/src/composables/useScenicBackground.js) | `GET /api/display-assets/`；[display API](../backend/app/api/display_assets.py)、[display service](../backend/app/services/display_assets.py)、[admin.py](../backend/app/api/admin.py) | 上传/清除/失败占位、公开读与受保护写、跨标签刷新需人工验证；没有专门展示资源测试文件 |
| 数据看板、情绪、体验报告 | [Dashboard](../frontend/src/views/admin/Dashboard.vue)、[AnalyticsReport](../frontend/src/views/admin/AnalyticsReport.vue)、[ExperienceReport](../frontend/src/views/admin/ExperienceReport.vue) | [insights.py](../backend/app/api/insights.py)、[emotion](../backend/app/services/emotion/)、[insights/emotion.py](../backend/app/services/insights/emotion.py)、[experience_report.py](../backend/app/services/experience_report.py) | [情绪](../backend/app/tests/test_emotion.py)、[情绪统计](../backend/app/tests/test_emotion_insights.py)、[标签](../backend/app/tests/test_insights_labels.py)；图表和报告 UI 需人工验收 |

## 按症状排查：知识更新后仍返回旧答案

按下表逐层核对；“保存成功”只说明对应写入完成，不代表整个检索发布链已经同步。

| 层次 | 直接定位 | 当前边界 |
|---|---|---|
| 知识条目 | [api/knowledge.py](../backend/app/api/knowledge.py) `update_knowledge` → [KnowledgeRepository.update](../backend/app/repositories/knowledge.py) → [KnowledgeEntry](../backend/app/models/knowledge.py) | CRUD 只写条目；当前调用链没有同步生成分块、重建 Chroma 或清理答案缓存 |
| 检索分块 | [ProcessedDataImporter.sync/_sync_knowledge_chunks](../backend/app/services/data_import/importer.py) → [KnowledgeChunker](../backend/app/services/data_import/chunker.py) → [KnowledgeChunkRepository.replace_all](../backend/app/repositories/knowledge_chunk.py)、[分块 model](../backend/app/models/knowledge_chunk.py) | `POST /api/admin/sync-processed-data` 同步处理数据、生成分块、清理持久化 QA 缓存，随后重载运行时 FAQ；它不是仅发布后台编辑的操作，须先核对输入数据会不会覆盖编辑 |
| 向量索引 | [admin.build_rag_index](../backend/app/api/admin.py) → [RAGIndexBuilder.build](../backend/app/services/rag/index_builder.py) | `POST /api/admin/build-rag-index` 从既有 KnowledgeChunk 建索引；单独重建不能把尚未分块的新条目传播进索引 |
| 答案缓存 | [QACache.get/set/invalidate](../backend/app/services/qa/cache.py)、[QACacheRepository](../backend/app/repositories/qa_cache.py)、[build_answer_cache_namespace](../backend/app/api/chat.py) | [config.py](../backend/app/core/config.py) 的 `cache_ttl_seconds` 默认七天，可配置；namespace 含模型/prompt 等设置，没有知识修订号，不能假设知识编辑会自然换一个缓存键 |
| FAQ 运行时 | [qa/runtime.py](../backend/app/services/qa/runtime.py) 的 `reload_runtime_faq_matcher`、[admin.py](../backend/app/api/admin.py) | FAQ 运行时与 Chroma/答案缓存是不同层；查明回答来自哪条分支再处理 |

验证应覆盖“修改一条 → 对应分块变化 → 向量可检索 → 旧问题不命中旧答案”，同时检查 FAQ 和回退检索分支。
地图可导航到这些层，但本次没有执行数据写入、重建索引或该完整业务回归。

## 共用基础设施

| 职责 | 位置与变更注意 |
|---|---|
| API 基址、超时、普通请求鉴权 | [http.js](../frontend/src/api/http.js)；普通请求与流式 fetch 是不同通路 |
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
