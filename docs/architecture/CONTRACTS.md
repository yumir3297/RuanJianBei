# 当前接口与状态边界

单次生成由 `StreamGenerationRun` 独立持有 `StreamTurn`、事件 drain 与最终 outcome。它必须在所有流事件耗尽后检查 LLM/epoch 结果；有错误事件时不得定稿/进入缓存或持久化；正常完成时须使用 `finalize_stream_generation()` 将 canonical answer 和 terminal policy 一起返回，保证降级 FAQ 回到权威 FAQ 文本、RAG 中断保留 partial answer 并标 incomplete，降级结果不得进入共享缓存。`QAPipeline` 只在 outcome 正常完成后进入缓存/持久化和终态 SSE 协调。

`StreamCompletionEffects` 只绑定本轮 answer 的缓存写入、聊天持久化、降级盲点记录、followups 和 done 事件元数据；是否写缓存仍由 terminal policy 决定。`StreamCompletionCoordinator` 独占这些 effects 的调用顺序与 epoch fence：音频和可选 FAQ 文本完成后才记录 fallback、缓存和持久化，持久化后再次检查 epoch，再发 final text/followups/done。effects 对象按请求创建，不得放到共享 Pipeline 状态中。

`resolve_cached_answer()` 只处理已通过 `shared_cache_allowed()` 的共享缓存读取：资格为 false 时不得访问 cache；cache miss 返回无结果；命中后必须复查请求 epoch，过期命中只返回 stale 标志，不泄露缓存文本；当前命中才执行 persona 润色。游客记忆、图片上下文和非中性情绪的共享缓存资格仍由 Pipeline 上游判定。

`resolve_faq_path_for_request()` 只在没有视觉输入且没有已解析景点范围时调用 FAQ matcher，因为 FAQ 记录不携带可验证的景点绑定。它返回既有 `FAQPathDecision`（包含最终答案/FAQ 证据和原始权威答案）；Pipeline 在直接答案发出前及 FAQ 证据进入生成前继续检查请求知识 epoch。LLM 改写降级必须使用 `source_answer`，不得把润色版当成新的权威来源。FAQ 路径不能绕过 epoch fence、RAG 范围或来源绑定约束。

`StreamEvidenceRun` 负责 FAQ/RAG 证据进入生成阶段前的事件顺序。RAG 分支必须将当前已解析 scope 传入 `retrieve_evidence()`，保持来源中的 `entry_id`、`revision_id`、`chunk_id` 与返回片段绑定；FAQ 证据不再发起 RAG 检索。两条路径均须在 source SSE 前验证请求 epoch，source 事件交付后再验证一次；任一道 fence 失败都不得把证据 outcome 交给 LLM 生成。若客户端关闭证据事件流，关闭必须传播到底层检索协程。

`StreamAnswerRun` 拥有 `StreamGenerationRun` 到 `StreamCompletionCoordinator` 的单请求 SSE 生命周期：必须先 drain 并关闭 generation event iterator；generation error 事件原样转发并短路，不得构造 completion 或触发 cache/persist/followups/done；正常 outcome 必须带 canonical finalization 后才启动 completion；外部 GeneratorExit 或 task cancellation 时必须关闭当前 generation 或 completion iterator，且将取消传播给调用方。completion 的音频 drain、epoch fence、副作用与终态事件顺序仍由 `StreamCompletionCoordinator` 实现。

`StreamAnswerCompletionFactory` 只从 finalized generation outcome 构造本轮 completion effects 和 coordinator 参数。应使用 canonical answer；只有 terminal policy `should_cache` 为真时才传入 cache callback；保留 FAQ 完整文本、streaming TTS 状态、degraded blind spot、persist 参数和 done 元数据。该 factory 不自行执行副作用，最终顺序仍归 `StreamCompletionCoordinator`，epoch fence 不得绕过。

`StreamAnswerGenerationFactory` 只负责将当前 `ChatRequest` 与已选证据、受众/记忆/视觉上下文、FAQ 来源及共享缓存资格映射到 `StreamGenerationRun`。FAQ 改写使用 FAQ 原始权威答案作为 fallback input；请求 epoch callback 必须传入实际 StreamTurn 与 generation checks；`cache_allowed` 是上游判定结果，factory 不得自行放宽。实际 LLM query、TTS producer 和取消仍由 `StreamTurnFactory`/`StreamTurn` 管理。

`resolve_request_query_context()` 将标准化检索 query 与意图路由输入分开：视觉 `retrieval_query`（去首尾空格并截断至 1000 字符）只追加到 retrieval query，intent 始终检查游客原始 query；有 vision 时不继承旧 conversation context，除非 selection resolution 提供 `active_subject`，此时构造以当前 subject 为准且保留 history summary 的新上下文。对未带 vision 且无新 subject 的文本请求，应将原 context 交给 QueryRewriter。此解析器不决定 FAQ/cache/RAG 或 scope。

当前以实际代码和 OpenAPI 为准；下列是集成核对提纲，不是已统一的新协议。

- Pipeline 生命周期：情绪、表达策略、音频/文本情绪和游客记忆保存在 `stream_chat` 的请求上下文中（`ContextVar`），并在流结束、异常或取消时恢复上下文；这些字段不会跨请求共享。`QAPipeline` 对 `_stream_chat`、StreamTurn、completion 和快速答案的内层事件生成器使用 `aclosing`；关闭外层 SSE 时必须在 `aclose()` 返回前关闭当前内层生成器并等待其 owner 清理。`StreamTurn.events()` 关闭时取消并 join 句级音频任务和 LLM/TTS producer，关闭 streaming TTS session；`check_generation_result()` 在流消费完成后原样重抛 LLM producer 错误并取消音频，或在 visibility/epoch 失效时取消音频并返回错误事件。`final_audio_events()` 只补发尚未由 streaming TTS 确认的内容，在每个 HTTP 音频任务完成后检查知识 epoch，再按 FIFO 发布其 SSE 事件；epoch 变化时取消剩余音频并发 `error`，不继续缓存/持久化/follow-up/`done`。`finalize_stream_generation()` 必须将 canonical answer 与 terminal policy 一起返回：降级 FAQ 使用权威 FAQ 文本，非 FAQ 中断保留 partial answer 并标 incomplete，降级结果不得进入共享缓存。FAQ 改写生成完成后、发送完整答案前还必须重新检查 epoch；若已变化，取消已排队语音，只发 error，不发送完整旧答案/音频/缓存/持久化/终态事件。`StreamCompletionCoordinator` 要求完整 FAQ 文本（若有）先于尾段音频，音频完成后先运行降级记录和 epoch fence，再按定稿 policy 执行缓存；缓存完成后再次检查 epoch，过期时不持久化聊天记录。聊天记录持久化后再验证 epoch，过期时不得发最终 text/followups/done。缓存键含请求知识 epoch，因此过期写入不会被新 epoch 的缓存读取命中。客户端在任何阶段关闭外层 SSE 时，协调器显式关闭内层音频事件生成器并取消剩余音频任务；正常耗尽不提前取消待发送音频。异常、任务取消及异步生成器显式关闭均须走清理。模型、FAQ matcher、缓存及其他注入依赖仍须分别评估线程与并发安全，因此共享整个 Pipeline 仍须经过回归验证。最新扩展 AI/流式回归为 196 passed；该集合由 stub/fake 和隔离 SQLite 构成，不代表真实模型/provider/设备、全后端 pytest 或部署数据库验收。
- `RequestContextResolver.resolve()` 在进入主 FAQ/cache/RAG/生成阶段前串联文本/音频情绪融合、显式选择解析、受众解析、可选游客记忆读取、视觉发布目录确认和查询上下文构造。失效显式景点选择必须在读记忆、视觉核验和 query rewrite 前返回 `attraction_selection_stale`；过期视觉确认必须在 query rewrite/意图路由及检索前返回原视觉错误。游客记忆仓储异常为 fail-soft，继续无记忆回答。视觉 retrieval hint 只追加至检索 query，intent 必须保持基于游客原始 query；resolver 不发 SSE、不访问 FAQ/cache/RAG，也不修改知识 epoch fence 或降级策略。`QAPipeline` 仍在 resolver 成功后按既有顺序发 context、emotion、intent 事件。
- `FastPathAnswerFactory` 为每个确定性/FAQ/cache/无证据快速答案绑定表达前缀和引用处理、请求级持久化参数、followups 与 done 元数据，再交给 `FastPathAnswerCoordinator`。factory 负责关闭其内部 coordinator 事件迭代器，调用方关闭 factory 流时必须同步关闭底层事件源；factory 不自行发 SSE、不合成语音、不做 epoch 判断、不执行持久化；coordinator 保留 sources→text→speech→epoch gate→persist→epoch gate→followups→done 顺序，语音 error 继续短路持久化及终态事件。RAG/FAQ 主证据选择、cache eligibility/IO 和生成 fallback 不属于此 factory。
- 问答：`backend/app/api/chat.py`、`services/qa/stream_events.py` 定义 SSE；消费者是 `frontend/src/composables/useSSEStream.js` 和 `stores/chat.js`。协议修改要同时核对服务端、解析及消费者，保留停止、重试与迟到结果隔离。
- 快速答案 SSE：`FastPathAnswerCoordinator` 对确定性/缓存/FAQ 答案统一先检查 epoch、准备并补充引用的答案、发送来源事件、再复查 epoch，之后发送完整 text；若需要语音则等待 `FinalAnswerSpeechEmitter`，遇到 speech `error` 停止持久化和终态。语音完成后、持久化前必须再次检查 epoch；持久化返回后也要复查，过期时不发送 followups/done。若 epoch 在持久化操作本身进行时变化，数据库写入可能已提交，当前边界只能抑制后续终态 SSE，不能回滚已提交聊天记录。来源事件已发后 epoch 失效时会发送 error，不发送 text 或写入聊天记录。
- 快速答案语音尾段：`FinalAnswerSpeechEmitter` 接收已补引用的答案，只在 `text_only=false` 时由 Pipeline 调用；TTS 与数字人合成并发，成功且 epoch 仍相同时按 `avatar` 后 `audio` 发出。任一渲染任务异常或调用方取消时，必须取消仍运行的同伴任务并等待其清理，再传播原异常/取消；不能让尾段 provider 工作脱离请求生命周期。epoch 变化时只发 `error`，Pipeline 必须停止该分支后续持久化/follow-up/`done`。长 FAQ 的语音文本可截短，SSE 可见答案仍为完整内容；合成失败行为由注入服务及其既有兜底契约决定。
- 路线预算冲突以 `hit_level=route_clarification`、`provider=local` 标识；`done.completion=complete` 仅表示本轮消息结束，不表示行程规划任务完成。普通预设路线亦标为本地处理，未知事件值的消费者应按兼容策略处理。
- 游览：`api/tour_sessions.py`、`repositories/tour_session.py` 管理 owner/site、修订和游览进度；客户端 `stores/tourSessions.js` 维护手动草稿与服务端版本，不能让提案恢复覆盖用户编辑。
- 剩余时间：进行中的游客可通过 `set_remaining_budget` 进度命令明确确认 1–720 分钟；新截止时间以服务端接收时间为锚，进度版本与事件同时更新，幂等重放不重置锚点。它不同于行程草稿的总时长；自然语言提案与此命令的联合确认尚未实现。
- 执行：`api/tool_execution.py` 和 `services/tool_execution/registry.py` 定义受控任务，`runner.py` 管理租约与 fence；外部结果未知时等待用户确认重复调用风险。每个任务、会话、交互和数字人表现的状态不同，不应把它们压成一个共享对象。
- 行程模型会同时生成候选操作与 `required_operations`；候选筛选验证后者是否包含在候选中，但两者来自同一次模型输出，不能独立证明必需操作完整表达了游客原话。游客必须查看差异并确认；真实任务完成率应对照原始请求逐项人工核验，记录遗漏、误增与澄清，不以规则通过或模型自评代替。
- AI 提案新增或修改的停留时长标记为 `estimate` 并注明需游客确认，不宣称由游客直接填写；原有未修改时长沿用已保存来源，手工修改仍标记为游客输入。既有历史记录不会自动回填修正。
- 证据：知识发布与检索链路由 `services/knowledge/`、`services/rag/` 和 QA pipeline 承担；需继续验证来源与消息绑定、发布后的缓存与语音失效。
- FAQ 恢复：管理员可通过 `POST /api/admin/refresh-faq` 仅重载处理该请求进程的 FAQ，不重新写入资料。成功不证明所有 worker 或语义索引可用；语义故障仍需查看健康状态并恢复。资料已提交但刷新失败时接口返回 `faq_saved_reload_failed`，调用方应先核对保存结果，避免重复提交。
- 回答缓存：带有效游客记忆的模型生成不读取或写入共享答案缓存；v5 键不命中可能含个性化内容的 v4 记录。旧记录不会自动删除，需按部署的数据管理策略处理。
- RAG 来源事件保留检索结果中可用的 `entry_id`、`revision_id` 和 `chunk_id`，均可为空；数据库回退、历史缓存和 FAQ 可能没有片段 ID。它们用于追踪知识版本，不代表来源真实、片段支持回答或已完成逐句引用核验。旧索引元数据不因升级自动修复，须隔离检查并重建。
- 已配置可见性服务的向量检索仅使用向量结果选候选和排序；经过片段归属验证后，从数据库已发布片段读取正文与来源。数据库回退和未配置可见性服务的其他调用路径需分别评估。
- processed-data 同步只刷新未发布的分块，不删除已发布和历史修订分块；此前已删除的历史数据不会自动恢复，导入结果的分块数量是本次未发布分块刷新数。
- 全量索引重建、新版发布和 processed-data 导入使用同一索引目录的跨进程写锁；旧版本进程未纳入锁，导入不自动更新向量索引，真实 Chroma/多进程及 Windows 仍未验收。重建时暂须停掉所有写入与发布 worker，细节见 `docs/development/PROGRESS.md`。
- 图片问答：`vision_context.confirmation` 可携带游客明确选择的 `site_id`、`spot_code`、`published_revision_id`；服务端重新核验当前站点已发布目录后才限定检索。未确认时开放检索并提示；选项已更新、下架或跨站点时拒绝。选中景点不证明照片识别正确，且知识库当前仅支持单站点边界。
- W02 迁移、启动和未验证边界见 [集成记录](../development/W02_INTEGRATION.md)。新增协议须说明版本、序列化、错误和取消语义，并增加兼容测试。


`QueuedSpeechPublisher` 拥有单句 HTTP TTS 与 avatar 渲染后发布的事件对：TTS 异常降级为空音频事件以保留文本与 avatar 输出；取消必须向上传播且不得发布部分事件；`previous` 音频任务完成前不得发布当前句，队列内 avatar 事件必须先于 audio 事件。并发上限由 `StreamTurn` 提供的 semaphore 控制，发布通知仍由队列接收方传入。


`DeterministicAnswerResolver` 保持早答决策优先级：不可核实开放/演出时间先于不可核实票价，二者均先于静态路线；静态路线只允许在无 vision 且 intent 为 `static_route` 时调用，builder 未命中则回到后续 FAQ/cache/RAG 流程。该 resolver 只返回决策和可选 status 文本，不发送 SSE、不读写缓存/知识、不持久化；Pipeline 对早答仍执行原 epoch fence、引用准备、语音、持久化和终态顺序。


`ChatInteractionPersister` 先创建 chat log，再尽力更新 visitor profile 与 visitor memory；后两项失败只能记录异常，不能使已完成回答的持久化调用失败。speech profile metadata 只附在非 text-only 回答；emotional fields 只在 `ChatLogRepository` 路径写入，保留 request-scoped emotion values。缓存写入仍由 completion terminal policy 控制，此 persister 不访问答案缓存或 RAG。


`AnswerKnowledgePathResolver` 先解析 FAQ，再尝试共享 cache：直接 FAQ 命中必须短路 cache；需 LLM 改写的 FAQ 保留 `source_answer`、FAQ documents 和 sources 后再计算 cache 资格；vision/scoped-attraction 跳过无景点绑定的 FAQ；vision、memory prompt 或非 neutral emotion 不得读取共享 cache。cache 读取通过 `resolve_cached_answer()` 执行，继续校验 epoch 并按 persona 润色。该 resolver 不发送 SSE、不触发 RAG/generation，也不改变 direct FAQ 的 Pipeline epoch fence。
