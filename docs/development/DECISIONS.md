# 技术决策

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
