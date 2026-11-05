# 技术决策

## 2026-11-05：将逐句 HTTP TTS/avatar SSE 发布从 Pipeline 中拆出

问题：`QAPipeline._queue_audio()` 同时处理 TTS 降级、avatar 生成、上一句音频等待和 avatar/audio 队列发布，生命周期较难与 `StreamTurn` 的取消及并发上限职责对照审查。

选择：新增 `QueuedSpeechPublisher` 作为注入 `StreamTurnFactory` 的 `audio_worker`。`StreamTurn` 继续拥有任务创建、semaphore、FIFO drain、取消和 epoch fence；publisher 只负责单句渲染与有序发布。TTS 普通异常仍改为空音频后继续文字/avatar 输出，task cancellation 仍传播且不发布未完整渲染的事件对。

验证：新增行为测试覆盖渲染/前序任务/发布顺序、TTS 故障降级和取消无部分发布；新模块缺失时三项测试均按预期失败，抽取后均通过。指定 AI/流式回归 156 passed；Python 3.12 compileall 与 diff check 通过。测试使用替身，不代表真实 TTS/provider/设备验收。

回滚：如果事件 FIFO、失败降级或取消行为改变，可将 `QueuedSpeechPublisher.__call__` 恢复为 Pipeline `_queue_audio` 并将该方法重新注入 StreamTurnFactory，保留三项契约测试。

## 2026-11-05：隔离 retrieval query 与原始 intent query 的上下文解析

问题：Pipeline 同时准备视觉检索提示、active-subject/history rewrite context、归一化检索 query，并将意图路由留在 raw user query 上；内联逻辑容易把视觉候选文本误送给意图检测，或在确认范围变化时继承旧景点上下文。

选择：新增 `request_query_context.py`，返回 retrieval_query、normalized_query 和 IntentDecision。vision retrieval hint 只追加到检索 query，最多 1000 字符；有 vision 时默认不传旧会话 context；若选择解析得到 active subject，则以其替换历史 subject 且保留 history summary；intent 始终基于原始 query 和已解析 selection。FAQ、缓存资格、RAG scope 和答案路由继续留在 Pipeline。

验证：行为测试覆盖 vision hint/raw intent 隔离、active subject 覆盖与 history summary 保留、普通文本请求原 context 复用。Intent/vision/retrieval/FAQ/cache/epoch/stream/TTS/SSE 指定集 160 passed；Python 3.12 compileall 与 diff check 通过。使用替身，不代表真实视觉模型或向量库验收。

回滚：若 vision 文本影响 intent、历史 subject 泄漏、或 history summary 丢失，将 query/context 组合恢复至 Pipeline 内联，保留三项行为测试；不要把 context resolver 扩展为 scope/FAQ/cache 决策。

## 2026-11-05：显式验证 generation/completion 两阶段的任务取消

问题：已有 GeneratorExit/`aclose()` 测试分别覆盖关闭 generation 和 completion iterator，但 SSE 请求也可能在等待其中一个阶段时被任务取消；必须证明 `CancelledError` 不会吞掉，并且底层异步生成器的 `finally` 清理已执行。

选择：保持 `StreamAnswerRun` 的异步 `aclosing` owner 实现，新增两项独立 task cancellation 测试，分别在 generation source 和 completion source await 中取消消费者。取消需向调用方传播，关闭当前 source，generation 取消时不得调用 completion factory。

验证：扩展 FAQ/cache/RAG/evidence/epoch/generation/completion/TTS/SSE 指定集合 151 passed；Python 3.12 compileall 与 diff check 通过。上述均为本地异步替身，不代表真实 ASGI 客户端断开或供应商取消验收。

## 2026-11-05：将请求与证据到生成配置的映射收进 generation factory

问题：Pipeline 在事件主流程中手工构造 `StreamGenerationRun` 的两组字典，将请求 persona/audience、游客记忆、视觉确认标题、FAQ 原文、cache eligibility、hit level/provider 和 epoch callback 映射到 StreamTurn 与最终定稿参数。此处字段缺失会影响证据或降级语义。

选择：新增 `StreamAnswerGenerationFactory`，显式接收当前 ChatRequest、已选文档和请求上下文，将配置映射成既有 `StreamGenerationRun`。factory 不重新计算 cache eligibility、不修改证据/FAQ 路由，也不承担底层 producer/TTS；这些仍分别由 Pipeline 与 `StreamTurnFactory` 负责。

验证：两项行为测试覆盖受众/游客记忆/确认视觉标题、FAQ 原始答案/fallback metadata、缓存资格、RAG 空上下文以及 text-only 标志。与 StreamAnswerRun/completion factory/Pipeline/FAQ/RAG/epoch/TTS/SSE 指定集合 149 passed；compileall 与 diff check 通过。用本地替身，非真实 provider/设备验收。

回滚：若 factory 传参改变 FAQ 降级答案、缓存准入、epoch check、视觉证据或 TTS 资格，恢复 Pipeline 内的 `StreamGenerationRun` 构造并保留映射测试；不要把业务路由推入此 factory。

## 2026-11-05：独立绑定定稿答案与完成期 effects

问题：`StreamAnswerRun` 已拥有 generation 与 completion 两段事件流，但 Pipeline 仍内联把 canonical outcome 转为 `StreamCompletionEffects` 和 coordinator 参数，包含 cache 准入、FAQ 文本、TTS、fallback 记录及终态元数据映射。

选择：新增 `StreamAnswerCompletionFactory`，将单个 finalized outcome 和当前请求上下文绑定为 completion event iterator。factory 只按 terminal policy 配置 cache callback，不执行完成期副作用；`StreamCompletionCoordinator` 继续唯一控制音频 drain、epoch fence、cache/persist、followups/done 顺序。Pipeline 继续提供 cache/persist 与请求级业务回调。

验证：工厂行为测试覆盖 canonical answer 传递、FAQ/TTS 参数、cache write/persist 参数、degraded 请求禁用缓存及 fallback blind spot 记录。AI/stream/FAQ/cache/RAG/evidence/epoch/TTS/SSE 指定集合 147 passed；Python 3.12 compileall 与 diff check 通过。使用本地替身，不是生产 provider/设备验收。

回滚：若 terminal policy 与 cache callback 准入不一致、FAQ/TTS 标志或 fallback 记录改变，恢复 Pipeline 原有 `StreamCompletionEffects` 装配，保留测试，并确认未改变 `StreamCompletionCoordinator` 的副作用和 epoch 检查顺序。

## 2026-11-05：统一拥有生成到完成的 SSE 流生命周期

问题：Pipeline 分别 drain `StreamGenerationRun.events()`、检查 outcome/error、构造完成期副作用并 drain `StreamCompletionCoordinator.events()`；两段流的资源关闭协议由主流程手动衔接，容易在取消/错误分支留下不一致行为。

选择：新增请求级 `StreamAnswerRun` 作为生成与完成的流 owner。它先 drain 并关闭 generation iterator；error 原样发出并直接返回；正常结果必须有 canonical finalization，才调用 completion factory 并 drain/关闭 completion iterator。cache/persist/blind spot/followup/done 绑定留在 Pipeline 提供的 factory，事件顺序继续由 `StreamCompletionCoordinator` 控制；没有改变 FAQ、cache 资格、RAG evidence、epoch fence 或 terminal policy。

验证：新增行为测试证明 generation error 短路 completion、关闭 generation 时关闭其 source 并不进入 completion、关闭 completion 时关闭嵌套 iterator。加入 FAQ/cache/RAG/evidence/epoch/TTS/SSE 集合后 145 passed；compileall 与 diff check 通过。测试是本地替身，不代表真实模型/provider/设备/数据库。

回滚：若错误短路、canonical finalization 要求或任一层异步生成器关闭行为变化，恢复 Pipeline 对两段流的显式 drain 和 `aclosing`，保留新增生命周期测试；不要移动 cache/persist/terminal event 的次序或取消 completion epoch gate。

## 2026-11-05：隔离流式证据选择与来源事件的 epoch 边界

问题：FAQ 证据与 RAG 证据都要先生成来源 SSE，再进入同一 LLM 生成路径；Pipeline 内联两种来源选择、source 事件及 epoch 检查，容易在拆分时遗漏 scope、来源修订绑定或 source yield 后的可见性变化。

选择：新增请求级 `StreamEvidenceRun`，封装 FAQ/RAG evidence selection、既有 `retrieve_evidence()` 调用与 sources/status 事件。FAQ 分支不触碰 RAG；RAG 保持原查询和 scope 参数及 revision/chunk source binding。两条分支均在来源事件发布前检查 epoch，发布后再检查；任一 stale 返回错误 outcome，不让生成阶段获得证据。缓存资格、FAQ 命中判定、无证据回答和后续 StreamGenerationRun 不迁入此组件。

验证：新增行为测试覆盖 FAQ 不触发 RAG、RAG scope/修订/分块证据保留、检索后 epoch stale 阻止 source SSE、source SSE 交付期间 epoch 改变后阻止证据进入生成，以及取消证据流时关闭进行中的 RAG 检索。Pipeline/FAQ/cache/RAG/evidence/epoch/stream/TTS/SSE 指定集合 142 passed；Python 3.12 compileall 和 diff check 通过。使用本地替身，不是生产知识库或真实模型验收。

回滚：若 source event 顺序、FAQ 快速路径、检索 scope/source identity 或 epoch stale 行为发生改变，恢复 Pipeline 原有 FAQ/RAG 分支并保留 `retrieve_evidence()`，保留新测试覆盖其中已明确的边界；不要移除检索来源绑定或 post-source epoch fence。

## 2026-11-05：将 FAQ 匹配门控移出 Pipeline，保留 epoch 所有权

问题：FAQ答案转换此前已位于 `answer_fast_paths.py`，但 Pipeline 仍直接完成 matcher 调用、视觉/景点范围排除和 FAQ 路径解析；这些条件与后续 epoch 检查及 FAQ 降级原文传递交织在主生成流程中。

选择：新增 `faq_path_resolver.py`，接收 matcher、标准化问题和请求范围标志，封装“是否允许匹配 FAQ”以及既有 `resolve_faq_path()` 决策。FAQ matcher 不在有视觉输入或已解析景点范围时调用。Pipeline 仍拥有请求 epoch 的读取与检查，并在发送直接答案或把 FAQ 证据交给生成前 fence；`FAQPathDecision.source_answer` 显式保留原始权威文本供 LLM 降级使用。未迁移 FAQ matcher 实例、知识 epoch、缓存资格、RAG 或来源绑定。

验证：行为测试覆盖视觉/景点范围跳过、普通命中和未命中；第一次扩展回归发现拆分后遗漏原始 FAQ 答案传递，修复为 `source_answer` 后 FAQ fallback 与 Pipeline 行为回归通过。FAQ/Pipeline/cache/RAG/evidence/epoch/stream/TTS/SSE 指定集合 137 passed；将 chat SSE API 加入同次收集时因临时 venv 缺 `asyncpg` 无法收集，剔除该 API 模块后的指定回归通过。所有可执行测试使用本地替身，不代表真实模型/provider/设备。

回滚：若直接 FAQ 快路径、景点范围排除、受众润色、FAQ 降级、来源、缓存资格或 epoch 检查行为变化，将 Pipeline 恢复为直接调用 matcher 与 `resolve_faq_path()`，保留新增行为测试并检查 `source_answer` 契约；暂不回退既有 FAQ path decision 组件。

## 2026-11-05：将流生成定稿作为单一输出

问题：Pipeline 分别调用 terminal policy 和 final answer 解析。两项结果共同决定 SSE 是否 incomplete、答案是否回退为权威 FAQ、hit level/provider 与能否缓存；分开调用容易让最终语音、缓存和持久化基于不一致的答案或策略。

选择：新增 `qa/stream_generation_finalizer.py`，一次返回 canonical answer 与不可变 terminal policy。FAQ 降级仍恢复已审核 FAQ 答案，其他中断保留当前生成文本；后续 `StreamCompletionCoordinator` 继续唯一负责音频、epoch fence、缓存/持久化及终态 SSE 次序。保留原有两个纯策略函数，避免不必要的兼容面变化。

验证：行为测试覆盖 FAQ provider fallback 禁止缓存、RAG network interruption 保留部分文本并设置 incomplete；Pipeline/FAQ/RAG/epoch/TTS/SSE 扩展集合 164 passed、1 条 Starlette 弃用警告，compileall 与 diff check 通过。测试用 stub，不代表真实 LLM、provider、TTS 或设备验收。

回滚：若 canonical answer 与 hit level/cache policy 不匹配，或 FAQ 降级/中断回归失败，将 Pipeline 恢复为直接调用两个纯策略函数；保留失败案例测试和 StreamCompletionCoordinator 的事件顺序契约。

## 2026-11-05：让 StreamTurn 校验生成完成状态并取消不完整语音

`QAPipeline` 曾在 `StreamTurn.events()` 结束后检查 LLM producer 错误和知识可见性变化，并在两条分支里分别取消音频；这使流生成的资源收尾散落在业务主流程。新增 `StreamTurn.check_generation_result()` 统一处理：producer 错误时先取消并等待句级音频任务，再原样重抛错误；epoch/visibility 失效时取消剩余音频并返回同一 SSE 错误事件；无错误时返回空值。Pipeline 仍负责是否返回 SSE 错误以及后续 FAQ/cache/RAG 业务。

验证：真实 producer 异常后有挂起音频任务的行为测试先因缺少方法失败，修复后确认异常原样传播且任务取消；StreamTurn/完成协调器/音频事件/Pipeline/chat SSE 定向集合 72 passed、1 条 Starlette 弃用警告。完整后端测试 597 passed、19 skipped、3 failed，失败为本地环境缺 `numpy` 和 `rank_bm25`；compileall/diff check 通过。Pipeline 从 887 降至 883 行。仅为本地替身回归，不代表真实 Provider 或设备验收。

## 2026-11-05：将生成完成后的 SSE 与提交顺序移入协调器

生成回答后的主流程仍把音频尾段交付、过期 epoch 检查、fallback 盲点记录、缓存、聊天记录持久化及最终 `text/followups/done` 顺序写在 `QAPipeline.stream_chat`。新增 `StreamCompletionCoordinator` 负责协调这些已有步骤：FAQ 完整文本仍先于语音发出；HTTP 音频按 `StreamTurn` 顺序 drain；音频交付失效时停止；随后检查 epoch，再按原策略缓存与持久化，并在持久化后再次检查 epoch，才发送最终文本和终态事件。FAQ/RAG/cache 资格决策、答案降级策略、来源证据、请求构造仍留在 Pipeline。

验证：协调器测试覆盖 audio→epoch→cache→persist→epoch→text/followups/done 次序与过期音频时禁止后续副作用；Pipeline/聊天 SSE/证据契约定向集合 71 passed、1 条 Starlette 弃用警告。后端完整测试当前为 594 passed、19 skipped、3 failed：一个环境缺少 numpy 导致本地 ASR 预期路径测试失败，两个 BM25 测试因缺少 `rank_bm25` 失败；未安装依赖或将其报告为代码回归。测试集合先暴露 `test_answer_evidence_claims.py` 仍导入 `bd70eff` 已迁出的 `_faq_evidence_document`，已改为通过 `resolve_faq_path` 测试当前公开边界。以上是替身/本地测试，不是模型、TTS 设备或生产并发验收。

## 2026-11-05：关闭生成完成阶段时取消剩余音频

最小复现发现，客户端在 `StreamCompletionCoordinator.events()` 已转发一个最终音频 SSE 事件后关闭外层异步生成器，Python 的 `async for` 不会替外层消费者关闭内层 `final_audio_events()`；内层迭代器未关闭，音频任务取消回调也未运行。协调器现在显式 `aclose()` 内层音频事件迭代器，并在生成完成阶段任何异常/取消/客户端关闭时调用 `StreamTurn.cancel_audio()`。正常耗尽仍按 FIFO drain 完整音频后才继续缓存和持久化。

验证：新增的外层 close 行为测试在修复前失败，修复后确认内层 generator 已关闭且音频取消回调已调用；流完成/StreamTurn/音频交付/Pipeline/SSE 定向集合 71 passed、1 条 Starlette 弃用警告。完整后端测试为 596 passed、19 skipped、3 failed（临时环境缺 `numpy`、`rank_bm25`）；Python 3.12 compileall、diff check 通过。未验证真实 TTS Provider、客户端网络断开或设备播放。

## 2026-11-05：由 StreamTurn 管理生成后的 HTTP 音频尾段与交付

生成结束后的音频尾段选择、任务 drain、SSE FIFO 发布和 epoch 失效处理与 mux 消费共享同一请求的音频任务/队列。新增 `StreamTurn.final_audio_events()` 统一这些动作，避免 Pipeline 手动拼装 drainer/delivery；Pipeline 仍决定 FAQ 完整文本何时发出，并负责缓存、持久化、follow-up 与 done，不迁移 FAQ/RAG/cache 或终态策略。

验证：StreamTurn/音频/Pipeline/epoch 定向集合 70 passed；AI/Worktree 指定回归 261 passed、1 条 Starlette 弃用警告；Python 3.12 compileall 与 diff check 通过。使用替身，不代表真实模型、TTS Provider 或设备验收。

## 2026-11-05：用作用域管理流式消费的取消清理

流式 mux 消费期间，异常或客户端关闭必须取消并等待句级 HTTP TTS；正常结束、异常或取消都必须关闭 producer task 与 streaming TTS session。新增 `stream_response_scope` async context manager 承担这项清理协议；Pipeline 继续产出 SSE，并在后续处理 mux/epoch 状态。验证覆盖正常结束与消费异常，定向 59 passed，扩展集合 230 passed、1 条 Starlette 弃用警告。

## 2026-11-05：集中计算流式终态策略

LLM finish reason 影响 degraded 标记、FAQ interruption 是否完整、done 的 hit level/provider，以及共享缓存是否允许写入。新增纯函数 `qa/stream_terminal_policy.resolve_terminal_policy` 一次计算这些字段；Pipeline 仍控制 epoch 检查和事件/持久化顺序。这样可单独检验降级语义并降低主流程重复条件。

验证：终态/Pipeline/epoch 子集 54 passed；扩展 AI/Worktree 集合 228 passed、1 条 Starlette 弃用警告。使用替身，不代表真实 provider 或设备验收。

## 2026-11-05：在音频排队前统一选择流式答案

FAQ 改写失败时必须在最终 text 和音频补播前恢复权威 FAQ 答案；如果等到音频 drain 后才决定，语音与持久化可能读取不同文本。新增纯策略 `qa/stream_finalization.resolve_final_answer`，将这个判断收拢，并移除 drain 后重复的回退赋值。Pipeline 仍负责降级标记、缓存禁写、epoch fence、持久化和 done 顺序。

验证：定向 59 passed；扩展 AI/Worktree 集合 226 passed、1 条 Starlette 弃用警告；compileall/diff check 通过。仅用替身；真实供应商/设备和完整 RAG 依赖未验收。

## 2026-11-05：将快速答案的语音尾段移出 Pipeline

问题：FAQ、缓存和确定性路径共享最终答案发射入口，但非 text-only 请求还要并发合成 TTS/数字人、复核知识 epoch，并保持 SSE 事件次序。若这段继续内联，会让快路径决策和音频表现生命周期耦合。

选择：新增 `qa/final_answer_speech_emitter.py`，只接收已修饰答案、命中级别、来源数量和期望 epoch，返回 `avatar`、`audio` 或过期错误事件。Pipeline 继续拥有答案引用与来源、事件前检查、持久化、follow-up 和 `done`；FAQ 文本截短规则与后合成 epoch fence 保持在 emitter 内。没有引入 Agent 运行时。

验证：定向 Pipeline/stream/knowledge 集合 55 passed；扩展 AI 与 V01/W02 相关集合 224 passed、1 条 Starlette 弃用警告。整库测试收集另有 6 个导入错误，分别是旧证据测试引用已迁出的 helper，以及 Alembic 包导入问题；真实 provider、设备和 migration 往返未验证。

## 2026-10-30：先保留现有问答流水线

问题：需要提升复杂任务编排，同时保护 FAQ、缓存、SSE 和语音快速路径。候选为现有 pipeline 增量分层、LangGraph 最小图、其他轻量 Agent SDK。当前选择前者作为对照基线，并复用既有 W02 持久执行器。

预期减少迁移面；代价是状态追踪、取消和幂等仍需自行维护。证据限于源码与自动化测试，并未证明性能优越。用同一真实任务集对比延迟、质量、失败恢复与成本；若复杂任务明显受限或轻量方案不能可靠恢复，隔离实验其他方案。失败或退化时回滚至基线 `ec3f7a6`。框架调研见[调研快照](../architecture/FRAMEWORK_RESEARCH.md)，版本与许可证需在使用前复核。

## 2026-10-30：隔离副本集成

四份含未提交内容的工作区分别保存本地快照并逐文件校验，再在独立副本整合。W02 迁移重挂见 [W02 集成记录](W02_INTEGRATION.md)；现有环境或已部署数据库不可假设迁移兼容。

## 2026-11-04：显式隔离问答请求状态，暂不引入图编排框架

问题：`QAPipeline` 将当前情绪、回答表达策略、模态情绪和游客记忆保存在实例字段中；若一个实例处理交错请求，后到请求可能覆盖前一请求正在流式读取的状态。候选为保留实例字段并强制每请求构造实例、把这些字段迁入请求局部状态，或把完整问答链迁入 LangGraph/Agent 框架。

选择：用 `ContextVar` 将上述纯请求状态限定于 `stream_chat` 的异步生成上下文，并在正常结束、异常或流关闭时 reset；其余 FAQ、缓存、RAG、模型、SSE/TTS 和工具执行路径不迁移。继续采用显式 Pipeline，因为当前复杂、可持久化的行程任务已有独立执行器，而普通问答主要是确定性路由、检索和流式生成；尚无实测证据证明图框架能改善问答正确率、延迟或恢复。

验证：同一 Pipeline 的强制交错测试分别证明旧代码会串用情绪/数字人策略和不同游客记忆，在新代码上均通过；显式关闭流后检查状态恢复；Pipeline、聊天 SSE 和游客记忆相关测试 57 passed、1 warning。此结果只证明所测 asyncio 请求状态和相关回归，不证明模型、缓存、FAQ matcher 或 TTS 注入依赖可并发共享，也不代替真实设备测量。

风险与回滚：若并发回归发现请求状态泄漏，或真实工作负载显示上下文封装引发事件错配/性能退化，撤销 `63855db` 与后续状态类型/关闭测试提交，恢复原有每请求构造 Pipeline 的调用约束。若 Pipeline 的条件分支继续增加导致复杂任务难以追踪，再用同一业务链和固定测试集评估局部图编排，不据此直接迁移 FAQ/缓存快速通道。

## 2026-11-04：将图片确认与发布知识证据绑定

问题：视觉识别候选和历史选择都不是当前照片对应的可信景点事实；若未确认输入保留旧检索范围，RAG 可能答对了旧景点却答错游客当前所见。候选方案为继续把目录核验内联在 `QAPipeline`、提取独立视觉证据解析节点，或允许候选/模型置信度直接产生检索范围。

选择：使用 `qa/vision_evidence.py` 节点；只有 `site_id + spot_code + published_revision_id` 全部匹配当前发布目录后，才将当前知识条目作为检索范围并将发布标题作为生成上下文。未确认视觉输入会清空继承范围并附加 `vision_scope_unconfirmed`；目录缺失、查询失败、已下架或版本过期会显式返回 `vision_confirmation_stale`，由 Pipeline 结束该请求。

预期收益是让“游客确认 → 当前发布条目 → 精确 RAG 范围 → 讲解标题”成为可测试的职责边界，并避免静默串用旧景点。风险是当前只在合成目录和替身 RAG/LLM 上验证，不能证明真实视觉识别质量或真实知识来源完整。

验证：3 个节点单测覆盖已确认、未确认和旧发布版本；3 个 Pipeline 回归验证确认后的范围进入 RAG、过期确认在检索前停止、未确认时历史景点范围被移除。AI 指定回归集合 129 passed、1 条 Starlette 弃用警告。若目录绑定、错误事件或检索 scope 在集成链路不一致，回滚为 `pipeline.py` 内联核验并保留原有 stale-confirmation 行为；不要放宽为基于候选或模型置信度检索。

## 2026-11-04：拆分数字人语音事件适配

问题：`QAPipeline` 同时负责编排 LLM/TTS、SSE 生命周期及 PCM、逐字字幕、口型和数字人事件转换，导致多模态事件协议难以独立验证。候选为继续内联、把 TTS 调度整体移出 Pipeline，或只拆纯事件转换。

选择：新增 `qa/speech_event_adapter.py` 负责 PCM base64 事件、逐字时间线、文本口型生成及句首数字人事件；Pipeline 保留旧方法作为兼容委托，并继续管理异步任务调度、请求级情绪和 SSE 时序。这样缩小协议适配模块的边界，不迁移取消、并发限制和音频回退语义。

验证：新增 4 项适配器协议测试，确认事件字段、PCM 编码、时间轴和请求情绪；原 Pipeline 音频与逐字时间轴专项继续通过，指定 AI 回归集合 133 passed、1 条 Starlette 弃用警告。测试不验证真实 TTS Provider 音质、网络中断或设备端同步。

回滚：若 SSE 事件形状或前端播放器同步回归，撤销委托并恢复 Pipeline 内联转换，同时保留可独立重跑的协议测试；不回退已有的 TTS 并发取消与文本保留策略。

## 2026-11-04：拆分 FAQ 与共享缓存资格决策

问题：Pipeline 在同一段流式控制代码里判断 FAQ 命中后是零模型直答还是作为唯一证据做受众改写，并另外判断视觉上下文、游客记忆和情绪是否允许共享缓存。这些规则影响模型调用次数、证据来源和个性化隔离。

选择：新增纯决策模块 `qa/answer_fast_paths.py`，将 FAQ 命中解析为直接答案或单条 FAQ 证据，集中表达共享缓存资格，并解析开放时间/票价问题的不可核实答复；异步 epoch 检查、缓存 IO、SSE 顺序、RAG 和模型调度仍由 Pipeline 控制。这样抽离稳定业务判断，避免把异步生命周期塞入新抽象，也让无实时数据依据的规则在检索/生成前确定执行。

验证：新增 5 个节点测试覆盖默认受众零文档直答、儿童受众唯一 FAQ 证据、共享缓存隔离和开放时间/票价匹配边界。完整指定 AI 回归集合 138 passed、1 条 Starlette 弃用警告。测试未测量真实 LLM 延迟，也不证明 TTS Provider 或设备体验。

回滚：若默认受众 FAQ 新增模型调用、非默认受众不再以 FAQ 为唯一证据，或个性化上下文进入共享缓存，恢复 Pipeline 内联判定并保留复现回归。

## 2026-11-04：将检索结果与来源记录作为同一证据束返回

问题：Pipeline 在 RAG 返回后临时将片段编号并复制标题、来源、得分和知识修订/分块标识；检索到答案证据与传给前端、聊天日志的引用字段分处两个步骤，容易在重构时失配。

选择：新增 `qa/evidence_retrieval.py`，统一调用既有 RAG scope，并按返回顺序生成 `RetrievedEvidence(documents, sources)`；FAQ 受众改写继续使用 FAQ 唯一证据，视觉目录确认仍由 `vision_evidence.py` 负责。Pipeline 仍负责 epoch fence、SSE 事件、空证据拒答和 LLM 生命周期。

验证：新增节点测试确认 query、normalized_query 和 scope 原样传入，来源证据 ID 与 entry/revision/chunk ID 对应。完整指定 AI 回归集合 139 passed、1 条 Starlette 弃用警告；真实知识源和在线引用忠实度尚未验证。

回滚：如果来源事件或聊天日志丢失、重排或错绑片段，恢复 Pipeline 原有映射逻辑并保留节点契约测试。
