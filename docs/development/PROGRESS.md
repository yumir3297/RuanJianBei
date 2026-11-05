2026-11-05：复验 worktree 审计中的目录递归差异计数：主 checkout `frontend/tests/` 为 15 相同/1 不同/22 集成额外；W02 itinerary 为 1 相同/3 不同/3 集成额外。发现旧表漏写 W02 集成目录的 `__init__.py` 包标记，已修正并记录；主 checkout fixtures/research/selling-points、W02/W02-V01 tool_execution 目录计数复核与分类证据一致。仅改审计文档，没有碰源 worktree、快照或 `sources/`。完整细节见 [WORKTREE_AUDIT_2026-11-05.md](WORKTREE_AUDIT_2026-11-05.md)。

2026-11-05：从集成 `ca577e8` 将 FAQ-before-cache 资格和读取顺序抽到 `answer_knowledge_path_resolver.py`。直接 FAQ 返回时不访问 cache；FAQ 改写路径保留原始权威答案与检索证据，再按 vision/memory/emotion 资格读取共享缓存；vision 问题跳过无 scope 绑定的 FAQ，cache 命中仍经既有 epoch 校验和 persona 润色。Pipeline 继续拥有 SSE/error/持久化及进入 RAG/generation 的流程。新增三项行为测试先因模块缺失失败，再覆盖 direct FAQ short circuit、FAQ rewrite 与 cache 同存、个性化/视觉 cache 隔离。定向 FAQ/cache/Pipeline 集 71 passed，指定 AI/流式回归 166 passed；Python 3.12 compileall 与 diff check 通过。Pipeline 从 714 降至 708 行。测试使用本地替身，不代表真实语义索引、cache store 或 provider 验收。起始集成/ref `ca577e8`；原 checkout `672a104`/95 路径，V01/W02/W02-V01 为 49/35/39；保护快照存在，phase3 prunable 未清理，`sources/` clean，node_modules 未跟踪。提交 `330e6e6` 后，原仓库同名集成 ref 已同步。

2026-11-05：从集成 `3be6356` 将完成回答的持久化 effects 抽到 `chat_interaction_persister.py`。Pipeline wrapper 只将请求级 emotion state 与 answer 参数交给 persister；persister 负责 chat log 基础字段、音频回答的 speech profile fingerprint/cache key、真实 ChatLogRepository 的情绪字段，以及后置 visitor profile/跨会话记忆更新。保留 chat log 先提交、画像/记忆失败只记录并继续的顺序。行为测试先因模块缺失失败，再覆盖字段/更新顺序和辅助存储失败降级；定向 persister/Pipeline/audience/memory 集 62 passed，指定 AI/流式回归 163 passed。Python 3.12 compileall 和 diff check 通过。Pipeline 从 753 降至 714 行。使用本地替身，不代表真实数据库或部署库验收。起始集成/ref `3be6356`；原 checkout `672a104`/95 路径，V01/W02/W02-V01 49/35/39；快照保留，phase3 prunable 未清理，`sources/` clean，node_modules 未跟踪。提交后同步集成 ref。

2026-11-05：从集成 `11c28f1` 将不可核实开放时间、不可核实票价与静态路线的优先级解析抽到 `deterministic_answer_resolver.py`。规则顺序保持 schedule→ticket→static route；vision 和非 `static_route` intent 跳过静态路线；路线未命中则回到原 FAQ/cache/RAG 路由。Pipeline 仍持有最终答案 SSE、epoch fence、持久化与终态事件。四项新行为测试先因模块缺失失败，再覆盖优先级、vision/intent 门控与未命中回退；定向 Pipeline/route/fast-path 回归 66 passed，指定 AI/流式回归 161 passed。Python 3.12 compileall 与 diff check 通过。Pipeline 从 776 降至 753 行。使用本地替身，不代表真实模型/景区时刻表/provider/设备验收。起始集成/ref `11c28f1`；原 checkout `672a104`/95 路径，V01/W02/W02-V01 为 49/35/39；快照保留，phase3 仍 prunable 未清理，`sources/` clean，node_modules 未跟踪。提交后同步集成 ref。

2026-11-05：从集成 `3a4afdc` 将逐句 HTTP TTS/avatar SSE 发布抽到 `queued_speech_publisher.py`。`StreamTurn` 仍拥有句级任务、semaphore、FIFO drain、取消和 epoch fence；publisher 只渲染单句并按 avatar→audio 顺序发布，TTS 异常仍以空音频降级保留文本流。行为测试先因模块缺失按预期失败，再覆盖事件顺序、TTS 故障降级及取消不发布部分事件。指定 AI/流式集合 156 passed；Python 3.12 compileall 与 diff check 通过。Pipeline 从 808 降至 776 行。测试用替身，不代表真实 TTS/provider/设备验收。当前 worktree：集成起点/ref `3a4afdc`，原 checkout `672a104`/95 路径，V01/W02/W02-V01 为 49/35/39，五个保护快照存在，phase3 仍 prunable 且未清理；`sources/` 未变，node_modules 保持未跟踪。逐路径差异分类见 WORKTREE_AUDIT；本轮未改其他 worktree、未合并原 checkout；提交 `c2497a3` 后，集成 checkout 与原仓库同名 ref 均为 `c2497a3`。

2026-11-05：从集成 `4111147` 将检索问题/归一化问题/意图决策的上下文组合抽到 `request_query_context.py`。视觉 retrieval hint 只拼入 retrieval query（最多 1000 字符），视觉请求默认不继承旧 context；selection resolver 若提供 `active_subject`，则替换旧 subject 并保留 history summary；intent 始终用原始游客 query 和已解析 selection。新增行为测试覆盖视觉/intent query 隔离、active subject 替换和普通文本 context 复用。Intent/vision/retrieval/FAQ/cache/epoch/stream/TTS/SSE 指定集 160 passed；Python 3.12 compileall 与 diff check 通过。测试使用替身，不代表真实视觉模型、向量库、provider 或设备验收。Pipeline 从 810 降至 808 行，FAQ/cache/RAG 路由仍由 Pipeline 控制。Worktree 起点/ref `4111147`；原 checkout 95 path、V01/W02/W02-V01 为 49/35/39，集成 node_modules 单独未跟踪；phase3 仍登记 prunable 未清理。提交后同步集成 ref，原 checkout 不合并。

2026-11-05：在生成/完成 SSE owner 提交后补充显式 task cancellation 行为覆盖。`StreamAnswerRun` 在 generation await 中取消时必须关闭底层 generation source 且不调用 completion factory；在 completion await 中取消时必须关闭 completion iterator，并将 `CancelledError` 传播给调用方。新增两项测试后，指定 FAQ/cache/RAG/evidence/epoch/generation/completion/TTS/SSE 集合 **151 passed**。Python 3.12 compileall 与 diff check 通过。工作树审计表覆盖复验：按当前 porcelain 状态逐项匹配主 checkout、V01、W02、W02/V01 集成树的路径名或目录汇总行，95/49/35/39 项均有记录，未发现未覆盖路径；这证明分类覆盖，不代替各行语义判定。当前原 checkout/ref、三个源 worktree、快照和 phase3 prunable 登记保持不变；未合并或清理。

2026-11-05：从集成 `d14000e` 将 request/evidence/context 到 `StreamGenerationRun` 的映射抽到 `stream_answer_generation_factory.py`。factory 以显式参数绑定受众、游客记忆、确认后的视觉标题、FAQ 证据、共享缓存资格、FAQ 原始权威答案、hit level/provider、文本/语音模式与请求 epoch callback；不改变 `StreamTurnFactory` 内实际 producer/TTS 生命周期。行为测试分别覆盖 FAQ 改写与视觉/记忆上下文传递、RAG 空个性化上下文及缓存资格保留。FAQ/cache/RAG/evidence/epoch/生成完成/TTS/SSE 指定集合 149 passed；Python 3.12 compileall 与 diff check 通过。仍是本地替身测试，不代表真实模型/provider/设备/数据库验收。Pipeline 从 817 降至 810 行；`TARGET.md` 已补入证据选择、generation/completion stream owner 与两侧 factory 职责。Worktree 起点/ref `d14000e`，原 checkout `672a104`/95 路径；V01/W02/W02-V01 为 `098553f`/49、`a8c2837`/35、`098553f`/39，五个保护快照仍存在；phase3 仍登记 prunable，未清理；集成 node_modules 未跟踪，sources 无状态。本轮未改其他 worktree。提交后同步集成 ref，原 checkout 保持隔离。

2026-11-05：从集成 `880ec46` 将最终回答后的 per-request effects 与 `StreamCompletionCoordinator` 参数装配抽到 `stream_answer_completion_factory.py`。Pipeline 现在只绑定领域回调和当前请求数据，再由 factory 根据 canonical finalized outcome 创建 effects；共享缓存仍仅在 terminal policy `should_cache` 时传入，降级盲点记录、FAQ 完整文本、流式 TTS 标志、persist/followups/done 元数据均维持原契约。新增行为测试检查 canonical answer、FAQ/TTS 资格、cache write 参数、persist 输入和 degraded fallback 记录。指定 FAQ/cache/RAG/evidence/epoch/TTS/SSE 回归 147 passed；Python 3.12 compileall 与 diff check 通过。测试只使用本地替身，不代表真实模型/provider/设备/数据库验收。Pipeline 从 842 行降至 817 行。Worktree 起始/ref `880ec46`，原 checkout `672a104`/95 状态路径，V01/W02/W02-V01 49/35/39，五个保护快照仍存在；phase3 保持 prunable，未清理；sources 无状态、集成 node_modules 未跟踪。本轮未改动其他 worktree，提交后仍需同步原仓库集成 ref。

2026-11-05：从集成 `002c77a` 新增 `StreamAnswerRun`，将请求级生成事件 drain、generation error 短路、正常 outcome 校验和 completion SSE 事件流的打开/关闭统一到一个 owner。Pipeline 不再手动在 `StreamGenerationRun` 与 `StreamCompletionCoordinator` 之间搬运 outcome/error 和嵌套 `aclosing`；只在同步 completion factory 中绑定 per-request cache/persist/FAQ/TTS 参数。行为测试验证生成错误被转发且不调用 completion、关闭生成流会关闭底层 source 且跳过 completion、关闭 completion 流会关闭其 generator。FAQ/cache/RAG/evidence/epoch/TTS/SSE 组合指定回归 145 passed；Python 3.12 compileall 与 diff check 通过。替身测试不代表真实 LLM/provider/设备/数据库。Pipeline 从 855 降至 842 行，生成后的具体副作用顺序仍由 `StreamCompletionCoordinator` 管理。Worktree 起始/ref `002c77a`，原 checkout `672a104`/95 状态路径；V01/W02/W02-V01 为 `098553f`/49、`a8c2837`/35、`098553f`/39，保护快照均保留，phase3 仍 prunable 未清理；`sources/` 无状态，集成 `frontend/node_modules` 未跟踪。本轮未改其他 worktree，未将集成分支合回原 checkout。

2026-11-05：从集成 `a97c302` 将 FAQ/RAG 证据选择、来源 SSE 发布和请求 epoch fence 抽到 `stream_evidence_run.py`。RAG 检索继续接收已解析 scope，并通过既有 `retrieve_evidence()` 生成 chunk/revision 绑定来源；FAQ 路径继续跳过 RAG。两条路径均在来源事件前复核 epoch，并在 source SSE yield 后再次复核；过期时 outcome 不提供证据给生成阶段。行为测试覆盖 FAQ 不落入 RAG、scoped RAG 参数/来源绑定保留、检索后 stale 阻止来源发布、source 事件期间 epoch 变化后停止，以及取消证据流时清理进行中的检索。扩展 AI/stream/FAQ/cache/RAG/evidence/epoch/TTS/SSE 回归 142 passed；Python 3.12 compileall 与 diff check 通过。试图纳入 API SSE 模块的上轮收集因缺 `asyncpg` 未完成，当前结果仍不代表全后端、真实模型/provider/设备或部署库验收。Pipeline 从 864 降至 855 行；FAQ/cache/RAG 路由与后续生成仍在 Pipeline 中，下一步继续评估 generation/completion 装配边界。Worktree 起点/ref `a97c302`，原 checkout `672a104`/95 状态路径；V01/W02/W02-V01 仍为 `098553f`/49、`a8c2837`/35、`098553f`/39；五个保护快照保留；phase3 登记仍 prunable 且未清理，集成 node_modules 链接未跟踪。逐路径分类见 [WORKTREE_AUDIT_2026-11-05.md](WORKTREE_AUDIT_2026-11-05.md)；原 checkout 不变，未将集成分支合入原 checkout。

2026-11-05：从集成 `b6db5c2` 开始，将 FAQ 匹配门控与命中解析抽到 `faq_path_resolver.py`。该边界负责跳过视觉问题和有景点范围的问题，再调用既有 FAQ matcher/answer resolver；Pipeline 仍在直接 FAQ 答案发送前，以及 FAQ 证据送入生成前检查知识 epoch。保留 FAQ 原文用于 LLM 降级，避免拆分后降级文本改变。新增测试覆盖视觉/景点范围跳过、普通命中和未命中；回归中发现并修复首次拆分遗漏的 FAQ 原文传递，确认原有降级行为仍通过。FAQ、Pipeline、缓存、RAG、证据、epoch、stream/TTS/SSE 指定集合 137 passed。另尝试纳入 chat SSE API 的联合命令未能收集，因临时 venv 缺 `asyncpg`；剔除 API 模块后完整指定集合通过。compileall 与 diff check 在提交前复核。实现和进度记录已作为一个原子提交写入集成分支，同名原仓库引用由共享 Git 元数据同步到该提交。测试使用本地替身，不代表真实模型/provider/设备验收。Pipeline 仍 864 行；FAQ matching 本身已离开主流程，流式分支路由、请求参数装配及 SSE 状态机仍待渐进拆解。Worktree 已复核：原 checkout `672a104`/95 状态路径；集成与原仓库同名 ref 在本轮起点 `b6db5c2` 对齐；V01/W02/W02-V01 仍为 `098553f`/49、`a8c2837`/35、`098553f`/39；五个保护快照可解析；phase3 仍登记 prunable 且未清理；集成 `frontend/node_modules` 未跟踪，`sources/` 无状态。逐项分类仍见 [WORKTREE_AUDIT_2026-11-05.md](WORKTREE_AUDIT_2026-11-05.md)。未将集成分支合入原 checkout。

**2026-11-05 本轮：请求上下文准备拆分。** 在集成基线 `a8f2928` 新增 `RequestContextResolver`，承接文本/音频情绪融合、显式景点选择失效检查、受众、游客记忆 fail-soft 读取、视觉确认/当前发布目录核验和 retrieval/intent query context 构造。`QAPipeline` 继续执行知识 epoch 前置检查、发送原有错误及 context→emotion→intent SSE，并控制 FAQ/cache/RAG 和生成生命周期。新测试覆盖失效选择先于记忆/视觉、记忆故障降级且视觉提示与原始 intent 分开、过期视觉确认在 rewrite 前停止。请求状态仅在完整解析后写入当前 ContextVar，不改变后续请求隔离。

本轮定向 resolver/Pipeline/选择/视觉/查询集合 71 passed；扩展 FAQ/cache/RAG/evidence/epoch、记忆/情绪、生成/完成/取消、TTS/SSE 集合 196 passed。Python 3.12 compileall 与 `git diff --check` 通过。测试使用 stub/fake 与隔离 SQLite，不代表真实模型、知识库、provider、设备或生产数据库验收。临时 `/private/tmp/guide-ai-arch-venv` 已消失；重建环境时项目固定 CPU PyTorch wheel 无 macOS 架构包，故安装适配当前机器的轻量测试依赖并运行选定回归，未运行全后端套件。

本轮起点集成 checkout `a8f2928` 与原仓库同名集成 ref 一致；原活动 checkout `codex/repository-map@672a104` 默认 porcelain 95 路径不变，V01/W02/W02-V01 分别 `098553f`/49、`a8c2837`/35、`098553f`/39。五个保全快照 refs 均可解析，`/private/tmp/ai-guide-phase3` 仍登记 prunable 且未 prune；集成 `frontend/node_modules` 仍为未跟踪链接，`sources/` 无状态。本阶段只改集成副本代码、测试和架构/进度文档；未改源 worktree、快照或原 checkout，也未将集成分支合入原 checkout。现有逐项差异状态分类不变；不能按祖先关系推断源 worktree 脏改动全部已合并。

**限定范围进度重估：约 77%（阶段性估算，不是验收结论）**。Worktree 保全与逐路径审计约 85%：原 95 路径、V01/W02 两源差异及快照均记录，尚无合回原活动 checkout 的安全迁移窗口；个别语义等价仍须结合后续源码/测试确认。AI 架构拆分约 79%：流生成、完成、取消、TTS/SSE、请求上下文、早答优先级、FAQ/cache/RAG、证据选择和 epoch fence 已有独立 owner/factory；Pipeline 现 677 行，主流程仍控制关键业务路由，流式生成、取消、TTS 调度和 SSE 生命周期的局部职责尚可继续收拢。验证约 77%：本轮扩展指定 AI/流式集合 196 passed，compileall 与 diff check 通过；不是全后端 pytest，真实模型/provider/设备、PostgreSQL 与部署库仍未验收。该估算基于当前源码、测试和迁移审计，不沿用此前百分比或初始 60% 评估。

本阶段原子提交 `f3ed6d1`（`refactor: extract request context resolver`）已从集成副本同步到原仓库 `codex/competition-integration` ref；两处引用均指向 `f3ed6d1`。原活动 checkout 仍为 95 个状态路径，未合并集成分支。

后续只读核对主 checkout 未提交的旧 `backend/app/services/qa/pipeline.py`：其 FAQ 禁流式 TTS、HTTP TTS 并发/FIFO、取消时任务回收、FAQ 降级原文和 incomplete 终态，已逐项映射到当前 `StreamTurnFactory`、`StreamTurn`/`AudioTaskGroup`、`StreamMuxConsumer`、`finalize_stream_generation()` 与 `StreamCompletionCoordinator`。相应 11 个流生命周期/TTS/完成测试 49 passed。该差异归为“被后续实现替代”，没有复制旧文件或变更原 worktree；逐项证据补入 [Worktree 审计](WORKTREE_AUDIT_2026-11-05.md)。真实 provider 与设备仍未验收。

2026-11-05：在 `StreamGenerationRun` 提交 `292612f` 后补做 Python 3.12 直接行为检查：关闭 run 的事件生成器时，底层 `StreamTurn` 源的 `finally` 在 `aclose()` 返回前完成；检查通过。系统 Python 和临时 venv 均没有 pytest，新增的 `test_stream_generation_run.py` pytest 用例尚未执行；对应 FAQ 降级、epoch error 不定稿和取消清理由等价标准库脚本覆盖，但不能替代项目 pytest 回归。工作树当前集成/ref 为 `67bd5e6`，原 checkout 仍 `672a104`/95 路径，所有活动 worktree 状态数、保护 refs 及 phase3 prunable 情况已复核且未改变。

2026-11-05：恢复 `/private/tmp/guide-ai-arch-venv` 并安装 pytest 与 Pipeline 测试所需轻量依赖（未安装完整 RAG/模型栈）。`test_pipeline.py`、`test_pipeline_audience.py`、`test_stream_generation_run.py` 定向集合 58 passed；Python 3.12 compileall 与 diff check 通过。第一次收集时缺 pydantic/websockets，安装后有一个 SQLite persistence 用例因缺 aiosqlite 失败；补齐后同一集合 58 项全部通过。此前直接行为脚本结果仍有效。此结果不等于完整 220 项 AI 回归，也不代表真实 provider/设备验收。工作树集成 checkout/ref 起点 `d3916cf`，原 checkout仍 95 个未提交路径，未触及来源目录、未改其他 worktree。

2026-11-05：在集成基线 `7156d1c` 上补齐 SSE 关闭传播。先用阻塞式 LLM 行为测试复现：消费方关闭 `QAPipeline.stream_chat()` 后，`aclose()` 已返回但 LLM 源清理尚未完成。Pipeline 现在在外层 `_stream_chat`、StreamTurn、completion、快路径答案和所有快速答案分支显式使用 `aclosing`；测试断言在 `aclose()` 返回前 LLM 源 `finally` 已执行。定向验证及扩展 AI/stream/FAQ/RAG/epoch/TTS 集共 220 passed、1 条 Starlette/httpx 弃用警告；Python 3.12 compileall 与 diff check 通过。无协议字段、回答、缓存、证据或 epoch 语义变化；所有验证仍为本地替身，不代表真实 provider/设备验收。Pipeline 仍有 FAQ/cache/retrieval/generation 整体分支编排待继续拆分。Worktree 起点集成 checkout/ref `7156d1c`；原 checkout `672a104`/95 状态路径、V01/W02/W02-V01 49/35/39、五个快照 refs 和 phase3 prunable 状态均复核保持；`sources/` clean，集成 node_modules 链接未暂存。路径级迁移结论继续见 [WORKTREE_AUDIT_2026-11-05.md](WORKTREE_AUDIT_2026-11-05.md)。

2026-11-05：从已同步集成基线 `ab1604f` 修复 `FinalAnswerSpeechEmitter` 的并发尾段清理：TTS 或 avatar 一侧异常/外部取消后，取消仍运行的同伴并等待其退出，再传播原异常/取消。两项行为测试覆盖一侧失败取消同伴，以及调用方取消时清理两侧并传播取消；第一项先失败，证实旧 `asyncio.gather` 异常路径未取消阻塞中的 avatar。修复提交 `4f4b56a` 已同步到原仓库同名集成 ref。修复后发射器、快路径协调器和 Pipeline 定向集 61 passed；扩展 AI/stream/FAQ/RAG/知识可见性/epoch/TTS 集 219 passed、1 条 Starlette/httpx 弃用警告。Python 3.12 compileall 与 diff check 通过。全量 `app/tests` 收集因临时 venv 缺少 `python-multipart` 在 3 个 API 测试模块导入时报错（其余尚未执行），未安装依赖或联网。以上全部为替身/本地测试，不代表真实 TTS、数字人设备或供应商验收。

Worktree 本轮复核：原 checkout `codex/repository-map@672a104` 仍为 95 个状态路径；V01/W02/W02-V01 分别 `098553f`/49、`a8c2837`/35、`098553f`/39；集成 checkout 与原仓库 `codex/competition-integration` ref 起点均为 `ab1604f`。五个快照 refs 仍在；`/private/tmp/ai-guide-phase3` 仍登记为 prunable，未清理；集成 `frontend/node_modules` 唯一未跟踪；`sources/` 无状态。逐路径分类仍以 [WORKTREE_AUDIT_2026-11-05.md](WORKTREE_AUDIT_2026-11-05.md) 为准：已合并/后续实现替代的代码保留源快照、不用旧版本覆盖；范围外前端与旧材料改动标为未合并并保留；原 checkout 不合入。AI 分层继续保留显式 Pipeline；当前 Pipeline 857 行，本阶段未触及 FAQ、缓存、RAG、证据绑定、知识 epoch 或降级策略。后续仍需拆分主流程剩余的流式生成、取消及 SSE 生命周期边界，并补足全量测试依赖后再运行整库回归；真实 provider、设备、PostgreSQL 与部署库验收未完成。

2026-11-05：在 quick-path epoch fence 提交 `024362b` 后联合复跑 AI/stream、V01 itinerary、W02 worker 与 migration 选定集合：252 passed、3 skipped、20 warnings、2 subtests passed；compileall 与 diff check 通过。3 skips 为未配置 `GUIDE_TEST_POSTGRES_URL` 的 opt-in PostgreSQL 用例；warnings 包含 Starlette、Alembic config 和 SQLite datetime adapter 弃用。该合集由本地替身和合成 SQLite 构成，不证明真实 provider/设备、PostgreSQL 或部署库。集成 checkout/ref 起点 `024362b`；原 checkout 95 状态路径，V01/W02/W02-V01 49/35/39，五个快照 refs 保持，phase3 prunable 未清理，`sources/` clean。

2026-11-05：修复 `FastPathAnswerCoordinator` 在可见答案/语音后遗漏的知识 epoch fence。新增行为测试先失败复现 epoch 在语音后变化时仍 persist/followups/done；现在语音成功后、聊天记录持久化前复查 epoch，持久化返回后再检查并抑制 stale followups/done。text-only 不合成语音的既有路径也覆盖新 fence。Pipeline/FAQ/knowledge visibility/TTS/SSE 定向集合 93 passed、1 条 Starlette 弃用警告；Python 3.12 compileall 与 diff check 通过。若 epoch 在持久化事务自身期间变化，已提交记录不能由本协调器回滚，这一残余窗口明确保留。起点集成 HEAD/ref `38e7f53`；原 checkout 95 状态路径，V01/W02/W02-V01 49/35/39，5 个快照 refs 保持，phase3 prunable 未清理，`sources/` clean。

2026-11-05：重新执行 V01 行程/API 与 W02 durable execution 语义回归（intent、progress、provenance、proposal diff/catalog staleness、budget/session API、tool execution acceptance、worker lifecycle/runtime review、opt-in PostgreSQL test），81 passed、3 skipped、2 subtests passed；3 skips 为未配置 `GUIDE_TEST_POSTGRES_URL` 的 PostgreSQL 专项。此结果支持审计表中“同步行程提案已由 durable proposal/job 替代”“progress/provenance 已扩展”“旧 W02 execution 文件不覆盖当前实现”等判定，但不证明真实 PostgreSQL 并发或部署数据库。起始集成 HEAD/ref `fb90453`；原 checkout 95 状态路径，V01/W02/W02-V01 49/35/39，5 个快照 refs 保持，phase3 prunable 未清理，`sources/` clean。

2026-11-05：在 `StreamCompletionCoordinator` 定位并修复 FAQ 改写的 generation-complete epoch 窗口：生成流结束到 completion 协调开始之间若知识 epoch 改变，旧代码先发完整 FAQ answer 和音频再报错。新增行为测试先失败复现 `text→audio→error`；现完整 FAQ text 前重新校验 epoch，过期时取消已排队音频、仅发 error，不启动尾段音频，也不缓存/持久化/发 followups/done。Pipeline/FAQ/RAG/epoch/TTS/SSE 扩展集合 165 passed、1 条 Starlette 弃用警告；compileall/diff check 通过。测试使用 stub，不代表真实模型、TTS provider 或设备；未做 PostgreSQL 并发验收。起点集成 HEAD/ref `2cb11fe`，主 checkout 95 状态路径，V01/W02/W02-V01 为 49/35/39，5 个快照 refs 保留，phase3 prunable 未清理，`sources/` clean，node_modules 未跟踪。

2026-11-05：复核 Worktree 审计表发现 W02 execution 小节仍保留新增领取后 fence 测试前的旧结论，已按当前测试 `test_claimed_job_is_fenced_when_tour_progress_changes_before_worker_start` 更新三处描述：SQLite 顺序交错已验证 lease 之后、attempt 之前的 progress fence；真正并行 claim 与 progress commit 的 PostgreSQL 时序仍未验证。同步收紧审计顶部未完成项，区分已做的 SQLite migration/lineage 实证与部署/真实旧库和 PG concurrency 缺口。文档证据对应既有 W02 专项测试，不将其夸大成并发验收；集成基线 `a6688cf`，主 checkout 95 状态路径及其余 worktree/快照保持，未动源 worktree。

2026-11-05：在集成基线 `f614da9` 联合重跑扩展 AI 与 migration lineage 回归：同一次 pytest 命令选取 Pipeline/FAQ/RAG/Intent/LLM/SSE/memory/cache/epoch/TTS/stream tests 和 3 组 Alembic SQLite tests，共 170 passed、20 warnings（1 条 Starlette 弃用警告，其余为 Alembic config 与 SQLite datetime 弃用）；compileall 与 diff check 通过。测试均为本地替身/合成 SQLite，不代表真实模型、provider、设备、PostgreSQL 或部署库。重新核实集成 checkout/ref 对齐；主 checkout 95 个状态路径、V01/W02/W02-V01 49/35/39、5 个快照 refs 保持，phase3 prunable 未清理，`sources/` clean，集成 `frontend/node_modules` 是唯一未跟踪项。

2026-11-05：为 Worktree migration lineage 差异重跑 `test_speech_metadata_migration.py`、`test_knowledge_workspace_migration.py`、`test_w02_sqlite_recovery_experiment.py`，合成 SQLite 专项 6 passed、19 条 Alembic/SQLite 弃用警告。确认的范围仍仅为测试数据库升级/回退与 lineage guard；未连接 PostgreSQL、部署库或真实旧库。本轮起始集成 HEAD/ref `f02ea06`；原 checkout 95 状态路径，V01/W02/W02-V01 为 49/35/39，5 个快照 refs 保留；phase3 仍登记 prunable 未 prune，`sources/` clean，集成 `frontend/node_modules` 未跟踪。

2026-11-05：在架构契约文档提交 `f0d1722` 后重跑 stream-generation-finalizer 对应的扩展 AI 回归集合，仍为 164 passed、1 条 Starlette 弃用警告；Python 3.12 compileall 与 diff check 通过。测试源码未变，此次确认已同步的实现/契约组合可重现。该集合不是历史命令的 139 项逐字复跑，也不覆盖真实 LLM/TTS/设备。工作树重新核对：集成 ref 起点 `f0d1722`，原 checkout 95、V01/W02/W02-V01 49/35/39 状态路径，5 个快照 refs 均在；phase3 prunable 未清理，`sources/` clean，`frontend/node_modules` 是唯一集成未跟踪项。

2026-11-05：从 `ef1441d` 继续拆分生成完成策略：新增 `stream_generation_finalizer.finalize_stream_generation`，将 LLM terminal metadata（降级/完整度/hit level/provider/cache 资格）与最终答案（降级 FAQ 恢复权威答案）组合成一个不可拆分的定稿结果，Pipeline 消费该结果后再交给既有 `StreamCompletionCoordinator`。保留 stream terminal policy/finalization 兼容函数。两个行为测试先因新模块不存在而失败，再验证 FAQ fallback 不缓存、RAG interruption 保留部分答案并标 incomplete；扩展 AI 回归（Pipeline、受众、FAQ、RAG、Intent、LLM 兼容、聊天 SSE、记忆、缓存、知识可见性、TTS adapter 与流式生命周期）164 passed、1 条 Starlette 弃用警告，包含的定向集合 62 passed。Python 3.12 `compileall` 与 `git diff --check` 通过。Pipeline 从 860 降至 857 行。该扩展集不是历史记录中 139 项集合的逐字复跑；测试使用 stub，不覆盖真实 LLM/provider/TTS 或设备；临时环境缺 Torch/Chroma。集成 ref 起点 `ef1441d`，原 checkout 95 项和 V01/W02/W02-V01 49/35/39 项、快照 refs、phase3 prunable 状态均保留，`sources/` 未变，node_modules 仍唯一未跟踪项。

2026-11-05：补上 W02 领取窗口的隔离行为回归：任务领取后、worker `start_attempt` 前游览进度版本变化，worker 不建立执行 attempt，任务标记为 stale。该测试先因断言误把保留的 stale step 当作“无 step”而失败，按实际持久化契约修正后通过；与 stream completion、StreamTurn、FastPath coordinator、W02 acceptance/runtime review 合计 34 passed。Python 3.12 `compileall` 与 `git diff --check` 通过。该交错用 SQLite 单会话顺序模拟，不等于 PostgreSQL 真并发竞争；源码审查确认 progress command 与 worker 的 `start_attempt`/`mark_external_call` 都更新或锁定 `TourSession` 行，执行前有 progress fence。临时 venv 仅安装轻量测试依赖，无 Torch、Chroma、BM25 或真实 provider。集成 HEAD/ref 开始为 `009fbda`；原 checkout `672a104` 的 95 个状态路径、V01/W02/W02-V01 的 49/35/39 个路径、5 个快照 ref 保持；phase3 仍登记 prunable 且未 prune，`sources/` 无状态，`frontend/node_modules` 仍是唯一集成未跟踪项。

2026-11-05：重新执行 Worktree 路径覆盖核验：用每个活动树 `git status --short` 与对应审计章节逐路径/目录前缀比对，主 checkout 95、V01 49、W02 35、W02/V01 39 个状态项均有审计记录，未发现漏项。此验证只证明记录覆盖，不证明内容等价；W02 claim 与 progress 真正同时竞争的 race、真实部署数据库仍未验证。起始集成 checkout/ref 为 `0616bb6`；原 checkout 95 项、其他 worktree 和快照保持，phase3 未 prune，`sources/` clean，node_modules 未跟踪；未向原活动 checkout 合并任何内容。

2026-11-05：为 `FastPathAnswerCoordinator` 增加 `text_only` 回归，断言不调用 TTS、但仍持久化并发送 followups/done；本轮标准库 `unittest` 4 passed，Python 3.12 compileall 与 `git diff --check` 通过。此补测不构成 pytest 集合或真实语音验收。集成分支起始 HEAD/ref `85e62f0`；原 checkout 95 个未提交路径及 V01/W02/W02-V01 的 49/35/39 个差异保持，快照和 prunable phase3 未动，`sources/` clean；`frontend/node_modules` 仍未跟踪。

2026-11-05：将非流式快速答案的 SSE 生命周期从 Pipeline 拆至 `FastPathAnswerCoordinator`：sources→text→可选 avatar/audio→persist→followups→done，保留两处知识 epoch fence、FAQ/cache/route 策略和请求上下文回调。新增 3 个标准库 `unittest` 行为用例，覆盖正常顺序、sources 后 epoch 变化停止文本/持久化、speech epoch 错误不持久化；先因 coordinator 模块缺失而失败，实现后 Python 3.12 `unittest` 3 passed。`pipeline.py` 当前 860 行；`compileall`/`git diff --check` 通过。完整 Pipeline pytest 未能运行，因为测试 venv 依赖缺失、DNS 无法恢复 SQLAlchemy/pytest；标准库测试未替代完整回归。起始集成 checkout/ref 为 `1493138`，原 checkout 95 项与 V01/W02/W02-V01 49/35/39 项、快照、phase3 prunable 状态均未改变，`sources/` clean；未合入原活动 checkout。

2026-11-05：在 pytest 环境仍缺失时，用本机 Python 3.12 运行临时 asyncio 行为脚本，实际导入并执行 `StreamTurnFactory` 与 `StreamCompletionCoordinator`：确认已确认景点标题按 JSON 数据上下文传递、text-only 不创建 streaming TTS session；当知识 epoch 在 cache 写入期间变化，只输出 error 且不调用 persist。两组脚本断言通过；这是独立行为检查，不是 pytest 回归，也不替代上一轮 175 passed 的正式测试输出。Python 3.12 compileall 和 `git diff --check` 通过。起始集成 checkout/ref 为 `312248d`；原 checkout 95、V01/W02/W02-V01 为 49/35/39 个脏路径，五个快照 refs 仍在，phase3 未 prune，`sources/` clean。完整 pytest 仍因包源 DNS 不可用而未重跑。

2026-11-05：再次核对集成基线，checkout/ref 均为 `731787c`；原 checkout `672a104` 仍 95 个脏路径，V01/W02/W02-V01 为 `098553f`/49、`a8c2837`/35、`098553f`/39，五个 snapshot refs 可解析，phase3 保持 prunable、未 prune，`sources/` clean。尝试恢复测试环境：本机 Python 3.12 无 pytest；临时 venv 已重建，但安装 `backend/requirements.txt` 受 DNS 限制，无法访问 `download.pytorch.org`。因此本轮没有新的 pytest 结果；上一轮扩展 AI 回归的 175 passed 仍是最近可用结果。没有改动任何源 worktree，集成工作树的 `frontend/node_modules` 继续未跟踪。后续保持架构/Worktree 审核推进，待包源可用后重跑 AI 集合。

2026-11-05：恢复目标后重新核对基线：集成 checkout 与原仓库 `codex/competition-integration` ref 均为 `742326e`；原活动 checkout `codex/repository-map@672a104` 的 95 个未提交路径仍在；V01/W02/W02-V01 worktree 为 `098553f`/49、`a8c2837`/35、`098553f`/39；五个 snapshot refs 在原仓库均可解析，phase3 仍 prunable 且未 prune，`sources/` 无状态，集成副本只有 `frontend/node_modules` 未跟踪。临时 venv 目录此前消失，本轮以本机 Python 3.12 重建空环境；安装项目依赖在访问 `download.pytorch.org` 时因 DNS 失败，故当前无法重跑 pytest。上一轮 factory 改造的 175 passed 是最近一次 AI 集合结果，非本轮复跑。原 checkout 未改、未合并；后续需恢复依赖后重跑回归，并继续对范围内 source worktree 差异收集语义证据。

2026-11-05：增量抽出 `qa/stream_turn_factory.StreamTurnFactory`，将视觉证据约束 query 组装、FAQ/text-only 对流式 TTS 的准入、LLM stream 创建及 `StreamTurn` 依赖装配从 Pipeline 移出；Pipeline 减少 25 行（883→858），仍保留路由、FAQ/RAG、cache policy、证据绑定和终态策略。新行为测试先因 factory 模块不存在而收集失败；实现后 4 项 factory 测试通过，覆盖已确认标题的 JSON 转义/问题透传、流式 TTS 资格及 producer/session 关闭。流/Pipeline/视觉定向集 105 passed；扩展 AI 回归 175 passed、1 条 Starlette 弃用警告。测试结束后临时 venv 路径消失，当前用系统 Python 3.14 完成 compileall 与 `git diff --check`；未能在当前状态重跑 pytest。测试用替身，不代表真实模型或 TTS 设备验收。Worktree 复核：集成提交 `cf8f741` 已同步至原仓库同名 ref；原 checkout `672a104` 的 95 个脏路径、V01/W02/W02-V01 的 49/35/39 个脏路径、五个快照和 prunable phase3 均未变；sources clean，node_modules 仍未跟踪。完整后端仍需可选依赖修复后的整套回归，迁移的部署库和真实 provider/设备验收仍待完成。

2026-11-05：在 `StreamCompletionCoordinator` 的缓存与聊天记录持久化之间增加知识 epoch fence。代码审查发现旧顺序只在缓存前、持久化后检查 epoch；若缓存写入期间知识发布，仍会写入基于旧证据的聊天记录。新行为测试先失败并复现该路径，修复后确认只缓存旧 epoch 命名空间、不持久化、不发 terminal events；正常顺序测试也断言额外检查位置。流完成/StreamTurn/Pipeline/SSE 定向回归 70 passed，扩展 AI 回归（FAQ/RAG/视觉/游客记忆/缓存/epoch/流生命周期等）159 passed，均各有 1 条 Starlette 弃用警告；Python compileall 与 `git diff --check` 通过。该回归使用合成数据及替身，不是真实模型/provider/设备验收。缓存键按 epoch 隔离；真实部署库与设备验证仍未完成。代码与文档提交 `268d760`，原仓库同名集成 ref 已同步；原 checkout 95 个脏路径、其余 worktree 和快照均保持，不合入原活动 checkout。

2026-11-05：重新核对全部 Git worktree、refs 和当前集成状态。该次核对时集成 checkout 与原仓库 `codex/competition-integration` ref 均为 `d1fdf8a`，集成工作树只保留未跟踪的 `frontend/node_modules` 本机链接；原活动 checkout 仍为 `codex/repository-map@672a104`，95 个未提交路径原样保留。V01/W02/W02-V01 worktree 分别为 `098553f`/49、`a8c2837`/35、`098553f`/39，五个保全快照 refs 可解析，phase3 仍登记为 prunable 且未 prune，`sources/` 无状态。迁移专项在当前 `/private/tmp/guide-ai-arch-venv` 运行：`test_speech_metadata_migration.py`、`test_knowledge_workspace_migration.py`、`test_w02_sqlite_recovery_experiment.py` 共 6 passed、6 warnings；这验证合成 SQLite 迁移升级/回退与 lineage guard，不代表 PostgreSQL、部署库或真实旧库验收。上次完整后端回归为 597 passed、19 skipped、3 failed，失败由临时环境缺 `numpy`/`rank_bm25` 引起；不会把替身或合成数据库测试描述为真实模型/设备/生产库验收。Worktree audit 的历史环境说明已更正；未将集成分支合入原活动 checkout。下一阶段继续拆分 Pipeline 的流生成/取消/TTS/SSE 边界，并补齐未完成的迁移冲突语义审查。

2026-11-05：`StreamTurn` 新增 `check_generation_result()`，接管 producer 错误和 knowledge visibility 失效后的资源收尾，移除 Pipeline 中重复的 audio cancel/error 分支。LLM producer 异常行为测试先按缺少方法失败，随后确认异常透传且挂起句级 TTS 任务被取消；原 visibility 失效 SSE 错误仍走现有 Pipeline 回归。定向 stream/turn/audio/Pipeline/SSE 集合 72 passed、1 条 Starlette 弃用警告；完整后端 597 passed、19 skipped、3 failed（临时环境缺 numpy/rank_bm25）；compileall 和 diff check 通过。Pipeline 从 887 降至 883 行。Git 起点 `1361225`；集成 HEAD/ref 对齐，原 checkout 仍有 95 个未提交路径，V01/W02/W02-V01 为 49/35/39；五个快照保留，phase3 未 prune，`sources/` 无状态。没有合入原活动 checkout；真实 Provider/设备未验收。

2026-11-05：在最终音频 SSE 转发后显式关闭外层流，最小复现发现协调器未关闭内层 `final_audio_events()`，且未调用音频任务取消。新增行为测试先失败，再让 `StreamCompletionCoordinator` 显式 `aclose()` 内层迭代器，并在 GeneratorExit/异常/取消时调用 `StreamTurn.cancel_audio()`；正常音频耗尽仍保持 FIFO drain。另验证直接关闭 `StreamTurn.final_audio_events()` 会取消后续排队音频。流完成/StreamTurn/音频交付/Pipeline/SSE 定向测试 71 passed、1 条 Starlette 弃用警告；完整后端测试 596 passed、19 skipped、3 failed，失败仍是环境缺 numpy 与 rank_bm25；Python 3.12 compileall 和 diff check 通过。起始 Git 为 `9bcc678`；原 checkout 95 个未提交路径、V01/W02/W02-V01 49/35/39 路径、五个快照及 prunable phase3 均保持，`sources/` 无状态。此修复未做真实 Provider/设备/断网验收。

2026-11-05：验证 Worktree audit 路径覆盖：以四个活动 worktree 的 `git status --porcelain` 与对应审计章节逐路径/目录前缀比对，原 checkout 95、V01 49、W02 35、W02/V01 39 个状态路径均有审计行，无漏记。最新集成 HEAD/ref `59adabf`；该覆盖校验只证明脏路径被纳入审计，不表示内容均已合并。审计表将范围外差异标为未合并且保留源 worktree/快照；五个快照仍存在，phase3 未 prune，`sources/` 无状态，原活动 checkout 未合入。

2026-11-05：继续核对 Worktree 审计表剩余差异：将 41 个此前标为“需语义审查/需逐项核验”的 frontend 视图、样式、播放器/store 与旧文档/研究/卖点材料明确分类为未合并、保留在原 worktree/快照，原因是当前范围排除前端改版及旧文档/材料迁移；不会误报为已集成，也没有改动其来源文件。对照证据为原路径与集成路径均存在且内容不同、对应原 worktree 脏状态与快照 refs 仍在。当前重核集成 HEAD/ref `27527ec`；原 checkout `672a104` 保留 95 个脏路径，V01/W02/W02-V01 为 49/35/39，五个快照保留，phase3 未 prune，`sources/` 无状态，集成 `frontend/node_modules` 未跟踪。Worktree audit 仍保留这些范围外改动，以便将来单独决定；本阶段不合入原活动 checkout。

2026-11-05：新增 `StreamCompletionCoordinator`，将流生成完成后的 SSE 与副作用次序从 Pipeline 主流程收拢：FAQ 完整文本仍先发，随后由 `StreamTurn` drain HTTP 音频；检查 epoch 后再缓存和持久化，持久化后再次检查 epoch，最后发送回答文本、follow-ups 和 `done`。保留答案路由、FAQ/RAG/cache policy、来源绑定与持久化参数在 Pipeline。协调器测试覆盖事件与 side-effect 顺序、音频 epoch 失效时不缓存/持久化/完成；Pipeline/SSE/证据定向集合 71 passed、1 条 Starlette 弃用警告。完整后端测试为 594 passed、19 skipped、3 failed：本地 SenseVoice 测试因临时环境缺 numpy，2 项 BM25 测试因缺 `rank_bm25`；未安装依赖。完整集合先暴露旧 `test_answer_evidence_claims.py` 仍导入 `bd70eff` 已迁出的私有 FAQ helper，已改为使用当前 `resolve_faq_path` 边界并独立提交。需要准备可选依赖后再获得全套绿灯；替身不等于真实模型/设备验收。Git 起点 `9e21816`，集成副本仅保留未跟踪 `frontend/node_modules`；原 checkout `672a104` 的 95 个脏路径、V01/W02/W02-V01 的 49/35/39 个脏路径及五个快照均保留，phase3 worktree 未 prune，`sources/` 无状态。原 checkout 活动分支仍未合入集成分支。

2026-11-05：逐项审计 W02 `backend/app/services/itinerary/` 的四个源文件：`candidates.py` 与集成版相同；旧 `intent.py` 的 diff 生成被规范化 candidate diff 替代；`progress.py` 和 `provenance.py` 由后续实现扩展，包含剩余预算/估算时长与截止时间检查、景点替换和目录修订导致的证据降级。对应 intent/progress/budget/provenance 行为测试已在 AI/Worktree 指定回归中覆盖（261 passed，1 条 Starlette 弃用警告）。W02 原差异仍留在快照；没有覆盖源 worktree。当前重核：集成 HEAD/ref `8c022fc`，原 checkout `672a104` 仍有 95 个脏路径，V01/W02/W02-V01 为 49/35/39；5 个快照保留，phase3 仍 prunable 且未清理，`frontend/node_modules` 未跟踪，`sources/` 无状态。Pipeline 当前 881 行；替身测试不构成真实模型、Alembic 或设备验收。Worktree 审计仍有其他未逐项语义核对路径。

2026-11-05：从 `83d342a` 继续收拢生成后音频生命周期。`StreamTurn.final_audio_events()` 现在按 `final_audio_segments` 补排未发送尾句、等待句级 HTTP TTS 完成、按 FIFO 发布事件并检查知识 epoch；Pipeline 不再组装 `AudioTaskDrainer`/`AudioEventDelivery`，仍控制 FAQ 文本、缓存、持久化与终态。两个新行为测试先在缺少方法时按预期失败，随后验证正常 `avatar`→`audio` 尾句交付、epoch 变化时抑制音频并发送错误。Pipeline 从 899 降至 881 行。定向 stream/Pipeline/epoch 集合 70 passed；AI/Worktree 指定回归 261 passed、1 条 Starlette `BlockingPortal` 弃用警告；Python 3.12 `compileall` 和 `git diff --check` 通过。替身测试不等于真实 Provider/TTS 设备验收。起始时集成 HEAD 与原仓库同名 ref 均为 `83d342a`，原 checkout 95 路径和其他 worktree 49/35/39 未变，5 个快照仍在，phase3 未 prune、`frontend/node_modules` 仍未跟踪、`sources/` 无状态。剩余工作仍有 Pipeline 的答案路由、cache/persist/final SSE 协调、未完成的 worktree 路径审查、Alembic/真实 provider 与设备验证。

2026-11-05：核对 V01/W02/W02-V01 的 `frontend/src/stores/tourSessions.js` 与集成版差异。确认新增的 durable proposal 恢复/手工重试、重复时间戳提案显式选择、迟到 open/save/progress/budget 请求隔离、保存期间草稿编辑保留及 progress refresh fence；这些是 W02/V01 集成后的状态一致性增强，不是界面改版或旧文件可覆盖内容。相关 proposal/store/helper Node 行为测试 43 passed，1 条 Node experimental localStorage 警告；第一次从 repo root 运行时 Vite 根路径错误，改从 `frontend/` 根目录后全通过。集成 Python/AI/Worktree 回归重跑 259 passed、1 条 Starlette 弃用警告。起始 HEAD 与原仓库集成 ref `83bf879` 一致，原 checkout 95 个脏路径、活动 worktree 和快照未动，phase3 未 prune，node_modules 软链接保持未跟踪；逐路径结论已更新 audit。

2026-11-05：继续语义核对 V01/W02/W02-V01 行程 API 客户端。V01 `frontend/src/api/tourSessions.js` 与集成版逐字节相同；W02 与 W02/V01 旧版预算查询缺少 `current_stop_remaining_minutes`，集成版补上参数构造，后端允许 0，Node 行为测试 1 passed。三份快照均不含或未完整支持 durable proposal list/retry API；集成版连接当前 GET proposal list / POST manual retry endpoints，并在 retry 要求 duplicate-risk 确认和传递 AbortSignal。W02 worker acceptance 覆盖未知外部结果需显式重试，扩展 AI 回归中该测试通过；旧文件不覆盖。仅核对客户端/服务端数据契约，没有做界面改版；差异分类更新到 Worktree audit。

2026-11-05：主 checkout AI 测试语义复核：其 `test_stream_knowledge_integration.py` 与集成版逐字节相同。`test_pipeline.py` 的旧测试要求由 retrieval `evidence_id` 自动追加 inline `[证据1]`，而集成版对应测试验证保持原文；当前实现与 CONTRACTS 说明 source IDs 仅用于知识版本追踪、不等价于来源对回答的支持，因此旧断言已被后续证据契约替代，不应迁回。集成对应测试定向 1 passed，分类已写入 Worktree audit；原 checkout 未运行测试或修改文件。

2026-11-05：从 `7adb18c` 继续拆分 AI 流式装配。新增 `qa/stream_turn.StreamTurn`，收拢单次生成的 mux queue、LLM/TTS producers、mux state/consumer、streaming TTS controller、答案缓冲与句级 HTTP 音频任务；Pipeline 保留 FAQ/RAG/cache/来源事件、terminal policy、HTTP 音频 drain、epoch 持久化 fence 与最终 SSE 顺序，文件从 931 行降到 899 行。行为测试覆盖正常 token/finish 元数据，以及关闭流时取消音频并关闭 LLM source。该测试先触发缺少 StreamTurn 的收集错误，随后发现并修复 `stream_response_scope` 在 `GeneratorExit` 异步生成器关闭下的 `RuntimeError`，现在显式关闭同样取消音频并收尾 producer。流/Pipeline/epoch 定向集合 91 passed；AI/Worktree 扩展集合 259 passed、1 条 Starlette `BlockingPortal` 弃用警告；Python 3.12 `compileall`、`git diff --check` 通过。仅为替身回归，不是真实模型/provider/TTS 设备验收。起始 Git `7adb18c`，原 checkout `672a104` 的 95 个脏路径保留；V01/W02/W02-V01 状态为 49/35/39，5 个快照 refs 保留，phase3 worktree 未 prune，集成 `frontend/node_modules` 保持未跟踪，`sources/` 未改。尚余 Pipeline 中请求/知识路由、持久化和最终终态协调，真实 Alembic/provider/设备验证及活动 worktree 的未决语义差异。

2026-11-05：重新盘点所有登记 worktree 与活动 refs：原 checkout `672a104` 仍有 95 个未提交路径；V01/W02/W02-V01 worktree 分别为 `098553f`/49、`a8c2837`/35、`098553f`/39；5 个保全快照 refs 均可解析。集成分支 HEAD 和原仓库 `codex/competition-integration` ref 均为 `6015817`，集成工作树仅保留未跟踪的 `frontend/node_modules` 本机链接。`/private/tmp/ai-guide-phase3` 仍登记为 prunable，未 prune；`sources/` 无 Git 状态。AI/Worktree 扩展回归 257 passed、1 条 Starlette `BlockingPortal` 弃用警告；Python 3.12 `compileall` 与 `git diff --check` 均通过。该集合使用替身，不代表真实模型、供应商、设备或 Alembic upgrade/downgrade 验收；继续保留显式 Pipeline 与请求/SSE 生命周期分层，不引入运行时 Agent 框架。未完成：完整迁移冲突逐项收尾、Alembic 往返、真实 provider/设备验证，以及 Pipeline 主编排中剩余 SSE 生命周期协调拆分。

2026-11-05：进一步语义审计 V01 api/tour_sessions.py 与 models/tour_session.py。快照 API 同步调用 ItineraryIntentService 并返回 201；集成版改为同事务 proposal reservation + durable itinerary.proposal job，返回 202，写入 execution_job_id，并以 base_snapshot_json 恢复核验 proposal diff。proposal replay/stale-progress、catalog staleness 与恢复测试 36 passed。审计表将 API/schema 差异标为后续 durable worker/schema 替代；快照保留，Alembic migration upgrade/downgrade 仍未实跑。

2026-11-05：继续核对 V01 快照中的两份进度测试。逐文件 diff 证明集成版 `test_itinerary_progress.py` 保留 V01 测试并新增“估算时长不验证预算”和“过期 deadline 即使当前剩余为 0 仍冲突”；`test_tour_budget_api.py` 保留原查询/显式剩余时长测试并增加剩余时长命令幂等重放、版本递增与非法值拒绝。集成版这两文件定向回归 17 passed。审计表已从“需语义审查”更新为“已覆盖并扩展”；源 worktree/快照仍保留，未复制或覆盖。当前原 checkout 95 路径、V01/W02/W02-V01 49/35/39 路径不变，同名集成 ref 与集成 HEAD 起点均为 `3a5569b`。

2026-11-05：新增 `qa/audio_event_delivery.AudioEventDelivery`，将音频 drainer 的事件发布、消费异常时取消剩余音频、知识 epoch 变化错误事件从 Pipeline 主流程收拢。Pipeline 仍根据 delivery 的 stale 标志停止后续缓存/持久化。行为测试覆盖 avatar/audio FIFO、异常取消及 epoch 错误；定向 stream/Pipeline/epoch 集合 57 passed；扩展 AI/Worktree 集合 233 passed、1 条 Starlette 弃用警告；compileall 和 diff check 通过。Git 起点 `a84f011`；原 checkout 95 个未提交路径不变、集成 ref 在上一提交同步后一致、node_modules 仍为唯一集成副本未跟踪链接；phase3 未清理、sources 未改。fake 回归不证明真实 provider/设备验收。

2026-11-05：在 `qa/stream_lifecycle.py` 增加 `stream_response_scope`，把 mux consumer 周围的取消协议从 Pipeline 主流程抽出：consumer 异常/取消时取消并 join HTTP 音频任务；所有退出路径关闭 LLM/TTS producer 和 streaming session。正常完成不提前取消已排队音频。行为测试覆盖正常及异常退出；定向 lifecycle/Pipeline/epoch 集合 59 passed；扩展 AI/Worktree 集合 230 passed、1 条 Starlette 弃用警告；compileall/diff check 通过。Git 复核起点为 `07af09b`，原 checkout 95 个未提交路径、其他 V01/W02 worktree 状态计数和快照 ref 不变；prunable phase3 未清理、sources 未改。fake 测试不代表真实 provider/设备；Pipeline 仍负责事件 yield 与终态协调。

2026-11-05：新增 `qa/stream_terminal_policy.resolve_terminal_policy`，集中根据 LLM finish reason 与 FAQ/cache 条件决定 degraded、incomplete、completion、hit_level、provider 和是否缓存；Pipeline 仍控制 epoch fence、回答选择、音频 drain、持久化及 SSE 发射时机。测试覆盖 fallback 禁止缓存、FAQ interruption 保持完整、非 FAQ interruption 标记 incomplete。定向 Pipeline/终态/epoch 回归 54 passed；扩展 AI/Worktree 集合 228 passed、1 条 Starlette 弃用警告；本阶段 compileall/diff check 在提交前执行。替身验证，不代表真实供应商或设备；`pipeline.py` 仍是生命周期编排入口。

2026-11-05：新增 `qa/stream_finalization.resolve_final_answer`，将流式生成完成后的唯一答案选择提取为纯策略：仅在受众 FAQ 改写降级时回到权威 FAQ 文本；策略在最终 text/audio 排队前运行，故可见文本、TTS、缓存判断和持久化共享同一答案。移除 drain 之后重复执行的同一 FAQ 回退。行为测试覆盖 degraded FAQ、普通回答与非 FAQ 降级；定向集合 59 passed，扩展 AI/Worktree 集合 226 passed、1 条 Starlette 弃用警告；Python 3.12 compileall 和 diff check 通过。测试使用替身；完整 requirements 的 Torch/RAG 组件与真实 provider/设备仍未验证。当前集成 Pipeline 约 935 行。提交和分支 ref 同步记录在本条后续提交中。

2026-11-05：临时测试环境此前消失，本轮用 Python 3.12 重建并安装 core backend + pytest 依赖（不含 CPU Torch、Chroma/向量模型等 RAG 重依赖；完整 `requirements.txt` 因 macOS ARM 无匹配 `torch==2.12.0+cpu` wheel 而未安装）。重新执行 AI/Worktree 指定扩展集合 224 passed、1 条 Starlette 弃用警告；Pipeline/知识 epoch/stream completion/emitter 定向集合 57 passed。Python 3.12 `compileall` 与 `git diff --check` 通过。该结果证明所选替身测试集，不是全后端、真实模型/设备或 RAG provider 验收；整库测试仍受旧测试 helper 导入及依赖/迁移收集限制。

2026-11-05：新增 `qa/final_answer_speech_emitter.FinalAnswerSpeechEmitter`，把快路径答案的可选语音尾段从 Pipeline 抽出：FAQ 语音摘要截断、TTS/数字人并发合成、合成后的知识 epoch 复核，以及 `avatar`→`audio`/过期错误事件顺序。答案修饰、引用、FAQ/RAG/cache 路由、持久化和最终 `done` 仍归 Pipeline。新行为测试覆盖顺序、长 FAQ 句界截断和 epoch 变更；定向回归 55 passed；扩展 AI/Worktree 相关集合 224 passed、1 条 Starlette 弃用警告。完整 `backend/app/tests` 收集未成功：证据测试导入已迁出的私有 helper，5 个 migration/API/实验测试受 Alembic 导入冲突影响；不能据此声称全后端通过。当前 Pipeline 939 行。复核原 checkout `672a104` / 95 路径，V01 49、W02 35、W02/V01 集成 39，快照 refs 均存在；实现提交 `ef51a88` 已将原仓库同名分支 ref 从 `3687e7f` 同步前进，集成副本仅余 `frontend/node_modules` 本机链接，`sources/` 无状态变化；`/private/tmp/ai-guide-phase3` 仍 prunable，未清理。测试完成后临时 venv 路径消失；compileall 和 diff 检查改由系统 Python 验证。真实模型、TTS 供应商、设备和 Alembic migration 往返仍未验收。

2026-11-05：补审 W02 `ItineraryProposal` schema、`alembic/env.py`、router 与 model registry。`base_snapshot_json` 支持恢复时重算 proposal diff 并拒绝无法核验的 apply，`execution_job_id` 链接 durable job；proposal recovery 与 API 重放测试覆盖这些用途。W02 f1 migration 父 revision/字段均与集成分支不同，已分类为被 merge migration 和后续 proposal-execution schema 替代，不可 cherry-pick；env.py 为导入格式差异，router/model registry 为后续 V01/knowledge 路由及模型注册扩展。migration upgrade/downgrade 仍未真实执行，详见 Worktree audit。

2026-11-05：在 `qa/stream_completion.py` 增加 `AudioTaskDrainer`，将 HTTP TTS task 顺序等待、完成后的知识 epoch fence、FIFO SSE drain 与过期后取消剩余任务从 Pipeline 收拢。行为测试覆盖多任务完成顺序、事件 FIFO、epoch 变化时不发旧事件并取消剩余任务；流音频和 Pipeline 定向回归 65 passed；扩展 AI/整合回归 189 passed、1 条 Starlette 弃用警告；compileall 与 `git diff --check` 通过。开始本轮时集成树和原仓库同名引用均为 `571c06c`；原 checkout 95 个状态路径、V01 49、W02 35、W02/V01 集成 39 未变，快照保留，`ai-guide-phase3` 仍 prunable 且未 prune。Pipeline 当前 952 行；组件化带入边界/类型代码，不能单看行数衡量拆分完成度。fake 测试不代表真实供应商、设备或 Alembic migration 验收。

2026-11-05：新增 `qa/stream_completion.final_audio_segments`，将生成收尾的最终 TTS 文本选择独立出来：FAQ 使用完整答案；流式 TTS 失败时从已确认字符偏移补播；HTTP TTS 路径补播未完成句；text-only 不排队音频。行为测试覆盖优先级、中文字偏移、尾句和 text-only。定向 Pipeline/FAQ/TTS/知识 epoch 回归 65 passed；扩展 AI/整合回归 185 passed、1 条 Starlette 弃用警告；compileall 和 `git diff --check` 通过。测试使用 fake provider，不代表真实设备。开始核对时集成树为 `c48c921`、原仓库同名分支引用一致；原 checkout 95 路径、V01 49、W02 35、W02/V01 集成 39 仍在，快照保留；`ai-guide-phase3` 仍 prunable、未清理。详见 [WORKTREE_AUDIT](WORKTREE_AUDIT_2026-11-05.md)。

2026-11-05：逐项对照 W02 `services/tool_execution/` 六个文件与集成实现，并检查 repository 与运行时测试：集成 transaction callback、worker CLI engine dispose、progress_version guard/fence、unknown external state 均是对旧版本的后续扩展，未以旧文件覆盖。新增两项隔离 SQLite 回归：旧 progress version 创建任务时拒绝且不插 ToolJob；任务排队后 progress 更新时 `claim_next` 不发 lease，维护后标 stale。W02 tool execution acceptance/runtime review 子集 8 passed；本轮扩展 AI/整合回归 182 passed、1 条 Starlette 弃用警告，compileall 与 `git diff --check` 通过。真正同时 claim/进度提交的 race 及 Alembic migration 往返尚未验证。逐文件分类与证据见 [WORKTREE_AUDIT](WORKTREE_AUDIT_2026-11-05.md)。

2026-11-05：逐行复核 V01 snapshot 与当前集成实现的 `itinerary/intent.py`、`provenance.py` 和相关行为测试，不仅依靠 merge 祖先关系。intent 的源版本直接用生成器 diff，集成实现从规范化 candidate 计算 diff；测试明确断言模型伪造景点名不会进入 proposal diff。provenance 集成版额外处理景点替换后旧时长/路线段证据失效、发布 revision 变化时 source-based 时长降级、AI 时长归因为 estimate；当前 provenance 测试覆盖这些场景并强化源 revision 变化断言。审计表已将这几项从“待核验”改为“已被后续实现替代/覆盖”，快照和源 worktree 均保留，未复制旧文件。

2026-11-05：新增 `qa/stream_mux_consumer.StreamMuxConsumer`，把主生成循环中的 mux 消费、知识 epoch fence、TTS 事件适配、usage/finish 收集、答案 token 累积、HTTP 句级音频任务调度和 streaming TTS flush 顺序移出 Pipeline；Pipeline 保留 producer 建立/关闭、FAQ/RAG/cache 决策、FAQ 降级补读、epoch 终态错误、偏移补音及持久化。行为测试覆盖 text chunk、usage/finish 保存与 text-only 不调度音频。扩展 AI/整合回归 180 passed、1 条 Starlette 弃用警告；lifecycle/mux/Pipeline/audience/chat SSE/knowledge epoch/FAQ fallback 定向集合 78 passed；compileall 与 `git diff --check` 通过。运行中测试曾发现抽取对象漏传 streaming_requested，已在完整回归前修正。`pipeline.py` 从 989 降至 948 行；原仓库集成分支引用已同步至 `f67b60d`。测试使用 stub/fake，不代表真实供应商/设备或数据库 migration 验收。

2026-11-05：新增 `qa/stream_mux.get_epoch_guarded_message`，集中队列读取前与收到 mux 消息后的两次知识 epoch 检查；版本变化后丢弃刚读到的事件并沿现有错误路径停止输出。新增测试覆盖读取前已过期及等待期间 epoch 变化。扩展 AI/整合回归 179 passed、1 条 Starlette 弃用警告；Pipeline/FAQ/RAG/stream/TTS/itinerary/W02 指定回归 179 项，`compileall` 与 `git diff --check` 通过。复核原 checkout 95 项、V01 49 项、W02 35 项、W02/V01 集成 39 项状态路径仍在，sources 未改，phase3 仍为 prunable；本轮未改原 worktree 或清理路径。测试使用替身；真实供应商、设备和 Alembic migration 往返未验证。

2026-11-05：新增 `qa/stream_lifecycle.StreamProducerGroup`，将 LLM/TTS producer task 的创建、请求结束时取消并 join、streaming TTS session 关闭从 Pipeline 收拢到单一生命周期边界；Pipeline 的 mux/epoch/SSE 决策未移动。行为测试覆盖取消后 producer finally 清理和 TTS session close。扩展 AI/整合回归 177 passed、1 条 Starlette 弃用警告；其中 lifecycle/Pipeline/audience/chat SSE/knowledge epoch 定向集合 78 passed；compileall 与 `git diff --check` 通过。已提交为 `2ae9657`，并将原仓库集成分支引用同步至该提交。使用 stub/fake；真实供应商、设备和 migration 往返未验证。`pipeline.py` 当前 989 行。

2026-11-05：在提交 `0ec66ef` 时复核 Git：原活动 checkout 为 `codex/repository-map@672a104`、95 个未提交路径；原仓库中的集成分支引用与当时的集成树 HEAD 相同。V01 (`098553f`)、W02 (`a8c2837`) 和 W02/V01 集成 worktree (`098553f`) 仍在，`/private/tmp/ai-guide-phase3` 仍标记 prunable，未清理；快照与旧 worktree 未覆盖。随后将架构索引状态更新并提交至 `f4d9f47`。复核时集成树仅有架构索引改动及 `frontend/node_modules` 本机软链接；扩展回归重跑 176 passed、1 条 Starlette 弃用警告；`compileall`（qa/tool_execution/itinerary）和 `git diff --check` 通过。该轮回归是选定集合，不与上方 193 项结果等同；使用临时数据库/替身，未验证真实模型、TTS 供应商、设备或 Alembic migration 往返。彼时 Pipeline 为 998 行，mux 消费循环仍持有 epoch fence、SSE 次序、TTS 调度/偏移、缓存和持久化；后续拆分须继续保留这些行为，并逐项完成尚未定论的 worktree 差异审查。架构索引：[CURRENT.md](../architecture/CURRENT.md)。

2026-11-05：新增 `qa/stream_answer.StreamAnswerBuffer`，将回答文本累计和 HTTP TTS 可播句切分从 Pipeline 主循环分离，保留中文句读及逗号满 8 字触发条件；Pipeline 仍控制 FAQ 原文回退、SSE 完整度、cache、流式 TTS offset 和降级调度。新增 buffer 行为测试。覆盖 stream/Pipeline/FAQ/RAG/SSE/TTS 与 V01 itinerary、W02 execution/worker 的扩展集合 193 passed、1 条 Starlette 弃用警告；`compileall` 与 `diff --check` 通过。回归使用 stub/fake，不代表真实供应商或设备。

2026-11-05：在 `3f9309f` 上重跑扩展 AI/整合回归：Pipeline、audience、FAQ、RAG、intent、兼容 LLM、chat SSE、memory、selection cache、knowledge epoch、TTS adapter/controller/buffer、queued SSE、V01 itinerary intent/provenance/progress/proposal staleness、W02 tool execution/worker/runtime review 共 191 passed、1 条 Starlette 弃用警告；`compileall` 覆盖 qa/tool_execution/itinerary 服务，`diff --check` 通过。此合集有意加入 V01/W02 相关测试，与历史 139 项原始集合不同；不含真实供应商或 Alembic 数据库迁移往返。

2026-11-05：新增 `qa/queued_stream_events.QueuedStreamEvents`，集中管理后台 HTTP TTS 产生的 avatar/audio SSE 事件 FIFO 写入、单批通知与非阻塞 drain；Pipeline 仍决定 mux/epoch 时机并逐项 yield，不改变 FAQ、text_chunk、来源或 done 顺序。新增事件批次顺序、通知发生于发布后、drain 清空行为测试；stream queue/controller/mux/lifecycle、Pipeline/受众、chat SSE、knowledge epoch、speech adapter、TTS、FAQ fallback 共 84 passed、1 条 Starlette 弃用警告；compileall/diff --check 通过。查找本地 Python 环境未发现可执行 Alembic CLI；迁移往返仍未验证。

2026-11-05：新增 `qa/streaming_tts_controller.StreamingTTSController`，将流式 TTS chunk 发送、尾段 drain、finish 请求一次性通知及 send/finish 异常转 HTTP fallback 从 Pipeline 主循环提取。Pipeline 仍控制 mux/epoch、FAQ/RAG 文本与 SSE 顺序和降级补读偏移。行为测试覆盖 flush+finish 一次性、发送失败标记和 fallback；流 mux/lifecycle/TTS buffer/controller、Pipeline/受众、chat SSE、知识 epoch、speech adapter、TTS service、FAQ fallback 回归 82 passed、1 条 Starlette 弃用警告；compileall/diff --check 通过。首次测试文本长度没达到原有 flush 阈值，修复测试输入后通过。真实供应商未验证。

2026-11-05：逐字段核对 W02 migration 分叉：快照 `f1b4c9d76e20` 父为 `e9f4c2b8016a`，集成同 revision 父为 `8ab42c17d3e9` 并加入 itinerary proposal 的 base snapshot/execution job 列。集成 `8ab` 合并 V01 `5c81` 与 speech metadata `c3b7`；后续 `6e1a` 检查/补偿 speech metadata、`7d2e`/`91a0` 拒绝已知不完整 W02/knowledge schema。判为旧 W02 migration 被集成迁移合并/修复替代，不得单独 cherry-pick。W02 execution acceptance、worker lifecycle、runtime review 17 passed；迁移专项因临时 venv 缺少 Alembic `command` API 收集失败，未声称 migration upgrade 验证，需在具备 Alembic 的隔离库环境重跑。细节见 worktree audit。

2026-11-05：将字节比较扩展到 V01/W02/W02-V01 integration 三个活动 worktree，并将路径状态、snapshot 命中、集成对象及递归目录核验写入 [WORKTREE_AUDIT_2026-11-05.md](WORKTREE_AUDIT_2026-11-05.md)。V01 当前 49 路径（24 与集成树完全相同、25 同路径差异）；W02 35 路径（6 相同、25 差异、4 目录）；W02/V01 integration 39 路径（8 相同、29 差异、2 目录）。差异文件均保留 snapshot；差异 backend 进一步标注已被后续执行 fence/锁/幂等及 itinerary 提案实现替代的候选，仍保留迁移图/schema、意图/来源断言和目录材料等未决项，不执行 cherry-pick 或覆盖。核对同时区分 W02 主 worktree 缺少的 acceptance 测试和后续 integration worktree 中保留并扩充的测试。

2026-11-05：对原活动 checkout 当前 95 个 porcelain 路径生成逐项内容清单 [WORKTREE_AUDIT_2026-11-05.md](WORKTREE_AUDIT_2026-11-05.md)：70 个文件与集成树逐字节一致；21 个同路径内容不同并按影响类别标注；4 个目录递归比较（3 个内容相同，`frontend/tests/` 有 15 个相同文件、1 个不同文件，集成树另含 22 个文件）。文件均能在 `codex/preserved-uncommitted-2026-11-04` 快照找到。不同项中后端 chat/config/schema/Pipeline/main 版本会移除现集成版的视觉确认、FAQ语义初始化、epoch/证据保护或就绪/worker 路径，标记为已被后续实现替代；原 checkout 的 TTS 协议文件及 chat SSE 测试是完全相同，判为已合并。前端、产品介绍和历史设计文档内容保留但按本任务范围暂不迁移。未改原工作区，仍为 95 项；此清单是字节级证据与初步语义分类，不替代后续迁移冲突审查。

2026-11-05：将流式 TTS 文本 chunk 缓冲与 flush 策略抽至 `qa/streaming_tts_buffer.StreamingTTSBuffer`，保留原标点/长度触发条件；finish 时 drain 尾部文本，空 buffer 不重复发送。新增标点 flush、逗号长度边界和一次性尾部 drain 行为测试。含 stream mux/lifecycle、Pipeline/受众、chat SSE、知识 epoch、语音适配、TTS 流、FAQ fallback 回归 80 passed、1 条 Starlette 弃用警告；compileall 与 diff --check 通过。Pipeline 仍决定供应商 send/finish、失败降级和 SSE 事件时序。

2026-11-05：新增 `qa/stream_mux.StreamMuxState`，将 LLM/TTS mux 消息到请求生命周期状态的转换从主生成循环拆出：LLM done/error、TTS connect/error/done、字时间戳确认字符偏移、audio-ready 信号由状态对象更新/路由；Pipeline 仍负责 epoch fence、LLM usage/finish、回答文本、SSE 适配、TTS send/finish 和降级调度。新增 mux 状态行为测试，覆盖 TTS midstream 失败偏移与连接失败；stream mux/lifecycle、Pipeline/受众、chat SSE、knowledge epoch、语音适配、TTS 流和 FAQ fallback 回归 78 passed、1 条 Starlette 弃用警告；compileall 与 diff --check 通过。尚未真实供应商/设备验收。

2026-11-05：将 HTTP TTS 句子任务调度与请求级取消收敛到 `qa/stream_lifecycle.AudioTaskGroup`：保留并发上限 3、此前任务依赖、audio-ready 通知和取消后 join。Pipeline 继续处理音频/SSE 消费、epoch 变化取消及 provider 降级。新增任务取消后等待 worker `finally` 清理的行为测试；流生命周期、Pipeline/受众、chat SSE、knowledge epoch、语音适配、TTS 流与 FAQ fallback 回归 76 passed、1 条 Starlette 弃用警告；compileall 与 diff --check 通过。一次初始运行发现测试 worker 缺少 `notify` 参数，修正后回归通过。

2026-11-05：按文件内容逐项比对 V01/W02 当前工作树与集成树（不是只看祖先关系）：V01 中 `5c81a1e...` migration、`schemas/itinerary.py`、`itinerary/candidates.py` 字节相同；tour_sessions API、model/repository、intent/progress/provenance 及相关测试均不同于集成版，标记为“集成已有后续实现，具体差异已识别，等价性未全部确认”，没有拷贝。W02 中 tool_execution API/model/schema 与集成树相同；迁移、repository、commands/handlers/registry/runner/worker 内容不同，集成树包含这些对应路径和新增生命周期/验收测试，标记为“功能已整合，当前实现存在后续差异”，没有用旧文件覆盖。`code/w02-integration` 的 acceptance 测试与集成树也不同，worker lifecycle 测试为集成树新增；原 W02 worktree 中两测试文件缺失。主 checkout 检查的六个 AI/SSE/TTS 文件中 `stream_events.py`、两个 TTS 流服务、chat-stream API 测试与集成树逐字节相同；`pipeline.py` 和 `test_pipeline.py` 不同，集成版保留请求状态隔离、epoch fence、FAQ/RAG 和证据处理，分类为旧实现由后续 Pipeline 替代，未移植。保存快照的逐文件差异仍有未分类项；主工作区其余 95 项逐项迁移冲突审查仍未完成。

2026-11-05：将流式 TTS 会话 connect/receive、12 秒完成事件超时与异常 mux 信号转至 `qa/stream_lifecycle.forward_tts_events`。Pipeline 仍拥有 finish/send 时机、失败状态与 HTTP TTS 降级、epoch fence、SSE 发出及 partial-character 对齐。新增队列行为测试覆盖连接事件、音频事件和 done；流生命周期、Pipeline/受众、chat SSE、知识 epoch、语音适配、TTS 流和 FAQ fallback 回归 75 passed、1 条 Starlette 弃用警告；compileall 与 diff --check 通过。未验证真实 TTS 供应商/设备。

2026-11-05：集成分支在提交 `dc4b1c8` 后经本地 fetch 同步到原仓库 Git 元数据中的 `refs/heads/codex/competition-integration`；原活动 checkout 仍为 `672a104`，95 个未提交路径逐项仍显示未提交，没有切换或合并。复核时 V01 (`098553f`) 与 W02 (`a8c2837`) 活动 worktree 的未提交文件仍存在；V01 的进度/提案服务和 W02 的工具执行相关文件在集成树中已有对应实现及后续修复，分类为“后续实现已整合/替代”；两边尚有修改版迁移、模型/API/前端和测试差异，不能仅按路径判定等价，本次未复制。快照 `3805943`、`48ef626`、`5433557` 在各自 worktree 数据库中可读取；`/private/tmp/ai-guide-phase3` 在原仓库 worktree 列表仍为 prunable，本次未 prune。原仓库工作区完整路径清单与快照差异尚未逐条完成，仍是整合未完成项。

2026-11-05：将 LLM 异步生成流的转发、异常信号和完成信号收敛到 `qa/stream_lifecycle.forward_events`；request query 的视觉证据约束、模型参数和主 mux 消费逻辑不变。新增生产流失败时仍发出 done 的 asyncio 行为测试；完整指定 AI 回归子集在此拆分后重跑为 102 passed、1 条 Starlette 弃用警告（较上次多 1 项生命周期测试）；compileall 与 diff --check 通过。此次不覆盖 TTS producer、真实供应商或设备。

2026-11-05：提交 `a6461de` 后重跑 AI 回归集合（Pipeline、受众、FAQ 降级/语义索引、RAG、IntentRouter、兼容 LLM、讲解 API、聊天 SSE、游客记忆、缓存键、知识 epoch、语音事件适配及新生命周期测试），101 passed、1 条 Starlette 弃用警告；compileall、diff --check 通过。首次回归命令引用了不存在的 `test_rag_pipeline.py`，未执行测试，改用实际存在的 `test_rag.py` 后成功。该当前测试集不同于历史 139 passed 集合。未验证真实模型、TTS 供应商或设备。

2026-11-04：复核实际 Git 状态：`integration-work/v01` 的 `codex/competition-integration` 与本地分支引用均为 `87b6c1c`；原 checkout `code/RuanJianBei` 为 `672a104`，95 个未提交路径仍在，未触碰。V01 (`v01-worktree`, `codex/v01-editable-itinerary`) 与 W02 (`code/w02-worktree`, `codex/w02-durable-execution`) 的未提交文件仍存在，保存提交 `3805943`、`48ef626`、`5433557` 可从 Git 对象读取；此轮未把它们复制覆盖集成版。集成历史有对应 itinerary proposal/progress 与 durable execution 实现，原 worktree 剩余未提交文件逐项仍需基于快照和文件内容完成分类，不能把“功能提交已合入”外推成所有差异已合入。`/private/tmp/ai-guide-phase3` 不在当前 worktree 列表，未执行 prune；`frontend/node_modules` 仍是集成副本的未跟踪本机软链接。AI Pipeline 本次将 LLM/TTS 后台任务的取消和 join 收敛到 `qa/stream_lifecycle.py`，并以真实 asyncio task 测试取消后等待 `finally` 清理；Pipeline 的知识 epoch fence、流事件处理和 TTS 降级逻辑不变。定向流式/Pipeline/TTS 回归 61 passed、1 条 Starlette 弃用警告；compileall 与 diff 检查通过。真实模型、TTS 供应商和设备未验收。后续仍需拆分事件多路复用与 SSE/TTS 编排，并完成 V01/W02/主 checkout 未提交差异逐文件清单。

2026-11-04：Worktree 状态复核：集成分支 `codex/competition-integration` 当时为 `14e5def`；V01/W01/K01 与 W02 durable execution 的功能提交（含 `e7dca5c` 后续修复）在历史中。V01 与两个 W02 原始 worktree 仍有未提交内容，其保存检查点 `3805943`、`48ef626`、`5433557` 保留；与集成分支对照显示集成版在提案目录校验、幂等回放、锁冲突和 worker 生命周期上已有更新实现，未把旧快照覆盖进来。`/private/tmp/ai-guide-phase3` 路径不存在但登记仍在，本次未 prune；对应分支已整合。原主工作区仍有 95 个未提交路径，保存快照 `4acaa53`、`e115eab` 可查，未触碰；尚未将 integration 分支合回原 checkout。任何源 worktree 均未删除。详情见 [当前架构索引](../architecture/CURRENT.md)。

2026-11-04：抽取 `qa/answer_fast_paths.py`，将 FAQ 结果解析为默认受众直答或非默认受众唯一证据，并集中判断视觉、游客记忆和非中性情绪是否允许共享缓存；Pipeline 继续控制 epoch 检查、缓存 IO、SSE、RAG 与 LLM 时序。新增 3 项节点测试；AI 指定回归集合 136 passed、1 条 Starlette 弃用警告，compileall 与 diff 检查通过。未声称延迟改善，模型调用规则由既有 Pipeline 回归覆盖。

2026-11-04：继续扩展 `qa/answer_fast_paths.py`，将“开放时间/演出时间”和“门票价格/优惠”数据不可核实拦截条件一并集中；响应文案、hit level、空来源和绕过模型/缓存的既有执行由 Pipeline 保持。新增规则测试，完整指定 AI 回归集合 138 passed、1 条 Starlette 弃用警告；compileall 与 diff 检查通过。未接入实时票务或开放时间数据，也未改变其可信状态。

2026-11-04：新增 `qa/evidence_retrieval.py`，以 `RetrievedEvidence` 成对返回 RAG 文档和来源记录，来源记录包含证据序号及知识条目、修订和分块 ID；检索 query、normalized query 和 scope 原样透传，Pipeline 继续负责 epoch 校验和 SSE。节点、Pipeline、视觉和 knowledge-stream 相关测试 56 passed；完整指定 AI 回归集合 139 passed、1 条 Starlette 弃用警告，compileall 与 diff 检查通过。测试未证明真实资料授权或答案对证据的事实忠实度。

2026-11-04：同步 `architecture/TARGET.md` 工作流图，明确开放时间/票价核验拦截、FAQ 直答/分众证据、共享缓存资格、RAG 来源绑定和 SSE/TTS 事件适配；选型仍为显式业务节点与 Pipeline，不表示最终性能收益或真实模型/设备已验证。

2026-11-04：为主工作区未提交内容建立只读保全检查点 `codex/preserved-uncommitted-2026-11-04`（`4acaa53`，父提交 `672a104`），使用独立临时 Git 索引捕获 115 个路径，明确排除 `frontend/node_modules`。原工作区索引、文件和 95 项状态记录保持不变；检查点已取入集成仓库供后续逐项比较，不等于已合入功能分支。

2026-11-04：在集成分支运行前端聊天流、SSE 与 PCM 错误专项 `node --test`，23 passed。覆盖服务端 `completion=incomplete` 的前端处理、部分回答保留与重试、迟到请求隔离、SSE heartbeat/超时和 PCM 错误回退；此为本地模拟测试，不验证真实浏览器或设备。

2026-11-04：只读对照主工作区未提交 AI/SSE/TTS 改动与集成分支，纠正“应整体移植”的初步判断。TTS 有界并发/取消、FAQ 降级文本、部分回答完成状态、SSE heartbeat、PCM 采样率及前端状态消费已在集成版找到实现和针对性回归；主工作区的 `pipeline.py`、测试及 chat store 基于较早基线，覆盖会丢失请求状态隔离、知识 epoch fence、确认景点核验和路线时长约束。故未复制或合并该批差异；只保留集成分支增量提交。详见 [当前架构索引](../architecture/CURRENT.md)。

2026-11-04：对 QAPipeline 做赋值点 AST 审计：除构造函数初始化的依赖外，请求期间仅写入情绪、表达策略、文本/音频情绪和游客记忆四类字段，均由 ContextVar 代理。源码同时显示 chat 与 guide 入口当前各自调用 `build_pipeline`，多个大型模型资源和 FAQ matcher 通过缓存/运行时对象共享；本次不据此宣称所有依赖可并发共享，其线程安全和重载一致性由各自专项继续验证。

2026-11-04：将无状态的整小时路线预算解析从 `QAPipeline` 提取到 `qa/route_constraints.py`，保留 Pipeline 内兼容导入，未改变路由行为。新模块边界测试先因模块不存在而失败，提取后通过；Pipeline 路线测试及 AI 回归集合共 122 passed、1 warning，语法编译与 diff 检查通过。该拆分减少领域文本解析与流式编排的耦合，不代表整个 Pipeline 已完成拆分。

2026-11-04：继续拆分 AI 问答边界：画像推断与兴趣提取迁至 `qa/request_profile.py`，确定性预设路线回答迁至 `qa/route_fast_path.py`，`QAPipeline` 保留兼容方法并委托新业务节点。新节点测试在模块缺失时先失败；完成委托后，路由、Pipeline、FAQ、RAG、SSE、记忆等 AI 回归共 123 passed、1 warning。未改变路线回答策略；真实模型、语音和设备验收不在本次结果内。

2026-11-04：将图片确认目录校验和检索范围绑定从 `QAPipeline` 拆至 `qa/vision_evidence.py`，明确区分已确认、未确认和过期确认；未确认图片不沿用历史景点范围，确认过期会显式停止问答。增加节点级与 Pipeline 回归，覆盖匹配发布版本、过期版本停止 RAG 和历史范围隔离。指定 AI 回归集合 129 passed、1 条 Starlette 弃用警告。测试使用临时 Python 3.12 环境和替身目录/RAG/LLM，不证明真实视觉服务或设备链路。

2026-11-04：刷新开源框架调研，交叉检查官方 GitHub release、PyPI 元数据和文档；记录 LangGraph、Pydantic AI、OpenAI Agents SDK、Langfuse、Ragas 的版本、许可、Python 下限和当前取舍。结论仍为保留显式 Pipeline、暂不加运行时框架；这只是源码与官方资料对照，没有框架性能 PoC，也没有安装候选包。

2026-11-04：更新 `architecture/TARGET.md` 的工作流图，使其对应当前代码路径：视觉确认绑定发布目录，FAQ/缓存/RAG 走轻量问答，复杂行程由持久 worker 执行。图描述的是当前增量目标，不表示真实视觉设备链路或框架性能已验收。

2026-11-04：将 PCM、逐字时间戳、文本口型和数字人句首事件的 SSE 转换迁至 `qa/speech_event_adapter.py`；`QAPipeline` 保留旧方法并委托适配器，TTS 调度与原事件字段不变。适配器新增 4 项协议测试，联合现有 Pipeline/TTS AI 回归共 133 passed、1 条 Starlette 弃用警告。测试为本地事件和替身流，不代表真实 TTS 音质或移动设备同步验收。

2026-11-04：扩大 AI 回归范围：Pipeline、Pipeline audience、FAQ 系列、RAG 系列、IntentRouter、OpenAI-compatible LLM、guide narration API、chat SSE、visitor memory、selection cache key 和 knowledge-stream integration 共 121 passed、1 warning。只覆盖列明测试文件，不代表全后端或真实模型/设备通过。

2026-11-04：AI 架构增量改造将 QAPipeline 的情绪、表达策略和游客记忆状态从共享实例字段隔离到每次 `stream_chat` 的 ContextVar 请求上下文，并在流结束、异常或取消时恢复上下文。强制交错的共享 Pipeline 回归分别验证情绪/数字人策略和两个游客的记忆提示：旧实现按预期错配失败，新实现通过；另显式关闭聊天流，确认默认状态恢复。Pipeline、聊天 SSE 与游客记忆相关测试共 57 passed、1 warning。测试依赖仅安装于 `/private/tmp/guide-ai-arch-venv`。未触及原主工作区的未提交改动。Worktree 核对显示 V01、W02、K01 整合分支为 `codex/competition-integration` 祖先；已建立主工作区保全检查点供后续选择性比较。

2026-11-04：隔离 PostgreSQL ASGI 测试在提案确认持锁后取消请求，另一会话成功下架且行程未新增修订，专项 1 passed；使用合成数据及身份保护替身、metadata 建表，实例已停止。未覆盖真实浏览器断网或提交期间取消。

2026-11-04：隔离 SQLite ASGI 测试确认请求在持目录锁后取消：会话关闭后另一会话成功下架，行程未新增修订，专项 1 passed。身份保护使用替身；该测试不证明真实浏览器断网、提交时取消或 PostgreSQL 行为。

2026-11-04：隔离 PostgreSQL 实测发布先持 knowledge_state 锁但尚未提交时，旧提案确认实际进入锁等待；发布提交后确认返回 409 且不新增行程修订，专项 1 passed。使用真实发布服务与 ASGI、合成数据，嵌入/向量及身份保护为替身，metadata 建表；实例已停止。未覆盖真实供应商、进程崩溃或生产数据。

2026-11-04：隔离 PostgreSQL 验证真实知识发布先提交并改变目录后，旧提案经 ASGI 确认返回 409、未新增行程修订，专项 1 passed。使用合成数据、fake embedder/vector 和身份保护替身，数据库由 metadata 建表且临时服务已停止；不覆盖发布与确认真正同时竞争、真实模型或部署数据库。

2026-11-04：隔离 PostgreSQL 真实 ASGI 提案确认与知识发布服务组合交错专项 1 passed；确认持锁时发布等待，提交后发布成功且景点目录摘要变化。测试使用合成景点、fake embedder/vector、身份保护替身和 metadata 建表，服务已停止。初次重跑因测试复用固定发布幂等键而超时，改为唯一键后通过；未覆盖反向顺序、真实服务及崩溃恢复。

2026-11-04：隔离文件 SQLite 真实 ASGI 提案确认与知识发布服务交错专项 1 passed：确认持锁时发布写入等待，确认提交后发布成功且只新增一份行程修订。嵌入、向量存储和身份保护为测试替身；未覆盖 PostgreSQL 的该组合及真实服务。

2026-11-04：隔离 PostgreSQL 实测真实知识发布服务在模拟确认事务持有 knowledge_state 锁时等待，锁释放后发布成功，专项 1 passed。嵌入和向量存储使用替身；数据库以 metadata 建表并使用合成数据，临时实例已停止。此实验未调用实际确认 API，不证明崩溃、死锁或旧版本进程安全。

2026-11-04：隔离文件 SQLite 测试验证真实知识发布服务在状态写锁持有时等待，释放后完成发布，专项 1 passed；使用 fake embedder/vector store，持锁模拟确认事务，未调用确认 API、PostgreSQL 或真实模型。

2026-11-04：隔离 PostgreSQL ASGI 实测目录状态行锁超时：事务设置 100ms lock_timeout，接口返回 503、无新增修订；释放锁后同幂等键成功，专项 1 passed。使用临时 Unix socket、metadata 建表和合成数据，服务已停止；不证明死锁、提交断连或真实部署的行为。

2026-11-03：提案确认对 SQLite BUSY/LOCKED 及指定 PostgreSQL 锁/事务冲突码回滚并返回可重试 503，提示同请求重试；其他数据库异常不归类。文件 SQLite 真实锁超时测试先复现 500，修复后验证无新修订、释放后同键成功；后端全套 530 passed、9 skipped、7 warnings。PostgreSQL 实际锁超时/死锁映射及提交断连不确定性尚未实测。

2026-11-03：隔离 PostgreSQL 双会话相同幂等键确认专项 1 passed：控制两次初始重放均未命中，两个结果相同且仅新增一个行程修订。使用临时 Unix socket、metadata 建表与合成数据，实例已停止；该测试未证明实际事务锁等待方向、跨进程压力或真实服务。

2026-11-03：隔离 PostgreSQL 临时库执行真实 ASGI 提案确认与知识下架交错测试：下架先提交时旧提案被拒绝；确认先取得状态锁时下架等待提交，2 passed。数据库为本地 Unix socket、SQLAlchemy metadata 建表与合成数据，非 Alembic 迁移或业务库；服务已停止。尚未覆盖发布路径、进程崩溃、锁超时、旧版本写入及真实供应商。

2026-11-03：在专用临时 PostgreSQL 实例（仅 Unix socket）执行状态行锁实验：持锁时观察到真实下架会话进入 Lock 等待，释放后下架完成；专项 1 passed。数据库通过 SQLAlchemy metadata 建表并插入合成数据，不是 Alembic 迁移或业务库；实例已停止。实验只验证该锁顺序，不证明完整提案 API 并发、锁超时、旧版本写入或真实数据安全。

2026-11-03：在集成代码 50cca85 复核评测准备：评测工具回归 22 passed；100 题格式检查 valid、0 错误，包含 94 题有证据回答与 6 题无证据拒答预期。此仅验证工具及格式，题目事实、真实模型响应和新旧性能对照仍未完成；临时报告位于 /private/tmp/guide-eval-validation-nov03.json。

2026-11-03：目录保护补充隔离 SQLite 回归：知识状态行缺失时拒绝新确认且不新增修订；已成功确认的相同请求即使状态行和目录随后变化仍可重放，同键不同内容仍拒绝。相关专项 7 passed；该测试不证明真实数据库故障恢复或 PostgreSQL 并发。

2026-11-03：提案仓库确认方法对新确认请求强制要求景区目录保护，并核对行程所属景区；原直调竞态测试不再 xfail。仓库测试迁移到真实发布目录、状态行和计算摘要；后端全套 528 passed、6 skipped、7 warnings，随后新增站点不匹配断言并重跑目录专项 4 passed。成功幂等重放仍按既有记录处理；PostgreSQL、锁超时和旧版本写入路径未验收。

2026-11-03：修复相同提案并发确认在等待目录锁后未重查幂等记录的问题；取锁后重放已提交结果并刷新提案状态，版本冲突回滚前保存版本号，避免读取过期 ORM 对象。隔离 SQLite 双会话测试先复现 MissingGreenlet 后通过；后端全套 527 passed、6 skipped、1 xfailed、7 warnings。PostgreSQL 与锁超时仍未验收。

2026-11-03：行程确认 API 增加事务内 knowledge_state 写锁，再刷新读取目录并核对摘要，缺状态行时拒绝确认；目录查询刷新 ORM 缓存。文件 SQLite 接口测试覆盖下架先提交时拒绝及确认先持锁时下架等待；后端全套 526 passed、6 skipped、1 xfailed、7 warnings。剩余 xfail 为直接调用仓库且不提供目录保护参数的旧路径，不能用于正式确认；PostgreSQL、锁超时及旧版本/不遵守 epoch 的写入路径未验证，部署前仍须暂停并发发布/下架并核对目录。

2026-11-03：目录竞态补充真实 ASGI 接口回归：在首次目录读取后、仓库确认前由另一 SQLite 会话真实下架并提交，现接口仍返回 200；该测试先按期望 409 失败，暂标 strict xfail。仓库与接口两项复现均 xfailed；修复仍需保证锁内重新读取到提交的原子顺序，不能仅新增一次未受保护读取。此测试的交错钩子等待写入提交，若改为读取前取锁则须调整为验证写入等待及合理串行顺序。

2026-11-03：新增仅接受 /private/tmp Unix socket 与 guide_test_ 专用数据库的 PostgreSQL 目录锁实验，观察下架事务的真实锁等待；当前未设置专用数据库时 1 skipped。尝试初始化隔离 PostgreSQL 时 shmget 被环境以 Operation not permitted 拒绝，未取得 PostgreSQL 运行证据。实验仅供专用可丢弃数据库，不能用于业务库；目录竞态和生产修复仍未完成。

2026-11-03：目录竞态锁方案的隔离实验：文件 SQLite 独立会话中，对已存在的 knowledge_state 行执行无变化 UPDATE 并持有事务时，真实景点下架的写入等待；释放后下架完成并递增 epoch。专项 1 passed、原竞态 1 xfailed。该实验未接入生产路径，不证明 PostgreSQL、缺失状态行、崩溃、超时或所有写入路径安全；已有未见调用的 KnowledgeRepository.delete 不更新 epoch。发布和下架先写景点再更新状态行，方案须审查锁顺序和死锁。目录竞态仍未修复。

2026-11-03：文件 SQLite 两个独立会话复现目录确认竞态：读取真实 K01 目录后，另一会话通过知识服务下架并提交，仓库仍用旧快照应用提案。新增严格 xfail 回归 `test_itinerary_catalog_race.py`（1 xfailed）；直接调用仓库模拟接口检查后的窗口，不代表 PostgreSQL 或真实并行压力结果。风险未修复；提案确认期间应暂停知识发布/下架，确认后核对景点版本。事务修复须覆盖目录读取到提案提交及所有目录写入路径，并验证死锁、失败回滚、幂等和两种数据库。

2026-11-03：修复提案确认成功后目录变化导致同一请求无法幂等重放；先按用户及请求内容查询成功记录，首次确认仍检查目录。隔离 ASGI/SQLite 测试先复现 409 后通过，并覆盖同 key 不同内容仍拒绝及首次目录过期拒绝；后端全套 523 passed、5 skipped、7 warnings。目录检查和提交间并发发布窗口仍待复现，真实服务未验收。

2026-11-03：历史 V2 提案读取及确认时重新运行现有确定性行程校验；若发现必去/排除或预算冲突，旧 pass/unverified 返回 conflict 并拒绝确认，未验证条件只降级不升级，原始存储不修改。隔离 SQLite 回归先失败后通过，后端全套 523 passed、5 skipped、7 warnings。该规则不验证无障碍、实际路网或游客自然语言是否被完整表达。

2026-11-03：服务端拒绝应用校验状态为 conflict 或未知的 ready 提案，避免绕过前端确认限制；允许 pass 和 unverified，后者仍须游客确认。隔离 SQLite 回归先复现错误写入后通过，后端全套 522 passed、5 skipped、7 warnings。此保护不等于重新计算历史提案所有约束，真实环境仍待验收。

2026-11-03：行程提案页面明确通过状态仅涉及预算及必去/排除景点，步行和无障碍条件需现场核实；校验冲突或未知状态不再显示通过，页面禁用确认并提供重新生成。前端 155 tests passed，runner 构建成功且有大包警告；此为界面防护，不代表服务端已验证无障碍，历史异常状态与直接 API 调用仍需核查。

2026-11-03：补齐历史提案展示：可解析的 V2 候选若设置休息间隔，旧有 pass 在返回时降为 unverified；不修改存储的原始校验结果，也不证明休息安排可行。隔离 SQLite 回归先失败后通过，后端全套 520 passed、5 skipped、7 warnings；真实浏览器与旧数据范围仍待验收。

2026-11-03：修复新生成行程提案对休息间隔未验证却显示通过的问题；当前只要设置休息间隔即标为待核实，前端提示涵盖该项，并不声称已计算休息安排。隔离回归先失败后通过，后端全套 519 passed、5 skipped、7 warnings；前端 runner 构建成功且有大包警告。已有历史提案的校验结果不会自动重算，须重新生成；真实模型与设备待验收。

2026-11-03：修复 /ready 对火山 TTS 和本地 SenseVoice 错误要求通用云 API Key 的问题；火山 TTS 改按实际凭据配置检查，本地 ASR 不要求云密钥。隔离 ASGI 测试先失败后通过，后端全套 518 passed、5 skipped、7 warnings。此检查不验证本地模型文件或语音供应商真实连通性。

2026-11-03：修复成功的进度命令恢复状态后仍显示先前同步失败提示的问题；保留其他错误。相关 Pinia 模拟 HTTP 回归先失败后通过，前端全套 153 passed；真实浏览器仍待验收。

2026-11-03：进度交错测试补充刷新失败和命令失败：刷新失败时同一行程的成功命令结果可恢复进度；刷新改变对象后失败命令仍提示错误。两项 Pinia store 模拟 HTTP 测试先失败后通过；前端 153 passed，runner 构建成功并有大包警告，真实浏览器及跨标签页仍待验收。

2026-11-03：复现并修复保存刷新先返回、较新进度命令后返回时结果被丢弃的问题；同一行程下仅接受版本更高的命令结果，并以当前点状态核对剩余时间。真实 Pinia store 模拟 HTTP 的交错测试先失败后通过，前端全套 151 passed、runner 构建成功且有大包警告；随后微调当前点比较并重跑相关专项 30 passed。真实浏览器及跨标签页仍待验收。

2026-11-03：修复手动保存后的旧进度刷新覆盖已完成的新进度操作；预算刷新同样核对当前进度和剩余时间。Pinia store 模拟延迟测试先失败后通过，前端全套 150 passed，runner 构建成功且有大包警告。反向返回顺序（进度命令仍在请求时刷新先到）尚待测试，真实浏览器和跨标签页未验收。

2026-11-03：复审手动保存时复现重新打开同一行程读到旧版本的问题；现在该行程保存及刷新结束前暂不重复打开，并提示稍后重试。真实 Pinia store 延迟测试先失败后通过；前端全套 149 passed，runner 构建成功，有大包警告。模拟 HTTP 不替代真实浏览器及跨标签页验收。

2026-11-03：修复手动保存异步竞态：固定请求的行程及草稿快照，响应和后续刷新检查当前行程，保存期间的新编辑保留为未保存草稿。真实 Pinia store 的两项延迟响应测试先复现覆盖问题后通过；前端全套 148 passed，runner 构建成功并有大包警告。测试使用模拟 HTTP，真实浏览器及跨标签页仍待验收。

2026-11-03：源码审查发现手动保存的异步竞态：`stores/tourSessions.js` 的 `save()` 在等待认证和请求期间使用可变的当前行程与草稿，成功后无会话检查直接覆盖当前行程和草稿；切换行程或继续编辑可能导致错误目标或丢失页面中的未保存修改。此为源码推断，尚未用交错测试复现，优先增加回归并修复；确认提案已有独立请求代次与草稿保留逻辑，不能据此推断手动保存也安全。

2026-11-03：重新核查原仓库分支祖先关系：V01 保全快照 `3805943` 是集成分支 `747b9a9` 的祖先；W02 原快照 `48ef626` 和 W02 集成快照 `5433557` 均不是其祖先。W02 的功能整合须结合本目录 W02 集成记录中的逐项对照与测试判断，不能称为快照已整体合并。清理原任务要求先等待稳定集成基线；真实服务、旧库和设备仍待验收，保留清理候选及独立准备分支，不执行删除。

2026-11-03：行程编辑界面根据已保存的锁禁止不兼容的时长编辑、删除及位置变更，包括删除其他点造成锁定位置偏移；支持解除字段与位置锁并提示先保存。前端 146 tests passed，runner 模式构建成功且有大包警告；测试覆盖锁定规则函数，真实浏览器操作及与服务端的完整链路仍待验收。

2026-11-03：修复手动编辑停留分钟时未同步时长依据，填写标记为用户输入、清空标记为未知，未改变的数值保留原依据；前端 143 tests passed，runner 模式构建成功且有大包警告。测试覆盖编辑函数而非真实浏览器，真实设备及保存链路待验收。只读审计发现已保存锁定点界面仍允许尝试编辑或删除，服务端会拒绝；需先解锁并保存后再修改，界面提示仍待改进。

# 开发进度

2026-11-03：照片提问不再把视觉模型返回的检索线索拼入游客问题；线索仍通过视觉上下文供后端检索，已确认景点仍单独传递。前端测试 141 passed，runner 构建通过并有大包警告；这只缩小一条注入路径，不保证检索或模型抗注入，真实照片、浏览器及模型待验收。

2026-11-03：未确认图片线索的问答生成增加约束：线索仅供检索，不应断言照片身份，身份不明时请游客确认。隔离替身验证实际传入模型的内容，后端全套 517 passed、5 skipped；这只是提示约束，不能保证模型遵守，真实照片、模型和误识别率仍待验收。

2026-11-03：复核 FAQ 版本刷新和就绪状态，未发现可确定复现的新 P0 缺陷；FAQ 快速通道隔离测试 1 passed（直接构造 Pipeline，不测真实模型、runtime 重载或延迟）。`/ready` 的 FAQ 故障仅反映响应进程，不能代表所有 worker；向量模型启动缺失需重启后重检，PostgreSQL 并发与压力仍待验收。

2026-11-03：修复 FAQ 语义索引恢复后重载故障标记仍残留的问题；区分语义构建故障与其他重载故障，语义恢复不会清除独立数据库故障。隔离回归先复现再通过，后端全套 517 passed、5 skipped；真实模型与多进程故障恢复仍待验收。

2026-11-03：FAQ 自动刷新在锁内重新检查当前知识版本，避免同一进程并发请求重复重建；空 FAQ 在版本未变化时不再反复加载。并发回归先复现 3 次加载再验证只加载 1 次，后端全套 516 passed、5 skipped；真实模型耗时及多进程压力未测。

2026-11-03：语义 FAQ 重建失败但新精确索引已发布时，请求可取用新索引降级；构建问答 Pipeline 时重取当前 matcher，避免持有旧对象。隔离替身测试覆盖两个入口，后端全套 514 passed、5 skipped；测试未在改动前重跑旧版，真实模型与多进程故障仍待验收。

2026-11-03：FAQ 重载改为独立候选构建、版本核对后切换，避免加载中清空已有请求持有的索引；语义构建失败且版本稳定时发布精确/模糊索引并标记故障。延迟加载回归先复现再通过，后端全套 512 passed、5 skipped；真实多进程高并发、PostgreSQL 和模型构建耗时仍待验证。

2026-11-03：独立 Python worker 加载旧 FAQ 后，父进程在临时 SQLite 同事务更新 FAQ 和 epoch；worker 下一次读取新答案。FAQ 版本专项 3 passed，Windows 因管道 select 不支持跳过跨进程用例；未验证 PostgreSQL、真实服务、模型或并发压力。

2026-11-03：FAQ runtime 在请求获取时比较数据库知识 epoch，不一致时串行重载；加载前后版本不一致则报错并标记故障，请求绑定的 matcher 版本与请求版本不一致时停止回答。隔离 SQLite 覆盖另一会话更新后重载，替身覆盖加载中版本变化及恢复、旧 matcher 请求拒绝；后端全套 510 passed、5 skipped。当前仍原地重载 matcher，重载期间可能暂时走无 FAQ 路径；真实多进程、PostgreSQL、加载并发和延迟影响尚未验收。

2026-11-03：将 FAQ runtime 更新后仍返回旧答案的隔离 SQLite 复现保存为 strict xfail 回归；专项 1 xfailed，表示问题仍存在。索引加载过程中再次更新、运行中请求与真实多进程仍未覆盖；修复须绑定 matcher 与知识版本并避免旧请求混用新版本。

2026-11-03：隔离 SQLite 复现 FAQ 跨进程同步风险的核心状态：一个 runtime 已加载旧 FAQ，另一个数据库 session 提交新答案并将 epoch 从 1 改为 2 后，再次获取该 runtime 的 matcher 仍返回旧答案。此为单进程内模拟另一个写入者，并非实际多进程或真实服务测试；未修改真实数据。需设计带版本绑定和原子切换的重载，避免旧 matcher 配新 epoch 及加载期间再次更新。

2026-11-02：盲区转 FAQ 将知识 epoch 递增和缓存清理与 FAQ 更新同事务提交；隔离 SQLite 测试覆盖成功及失败回滚，后端全套 507 passed、5 skipped。多 worker 的 FAQ 内存索引仍不会随 epoch 自动刷新，旧索引跨进程一致性及真实 PostgreSQL 待处理。

2026-11-02：processed-data 同步将知识 epoch 递增和数据库缓存清理纳入资料提交事务；隔离 SQLite 验证成功递增、失败回滚及同步后旧 epoch 缓存写入不会被新 epoch 读取。后端全套 505 passed、5 skipped。未模拟完整 LLM 并发或真实 PostgreSQL，多 worker FAQ 内存索引重载仍未解决。

2026-11-02：四个可访问原工作区的 Git 可见现存普通文件分别与主快照 `e115eab`、V01 `3805943`、W02 `48ef626`、W02 集成 `5433557` 比较，未发现内容差异；不覆盖忽略项、符号链接、缺失文件或外部资源。V01 与 W02 集成快照新增保全分支到原仓库；临时 phase3 worktree 路径缺失但分支仍在，未清理。

资料同步并发风险待复现：processed-data 同步未见知识 epoch 更新；旧 FAQ 改写请求可能在缓存清理后写回旧答案。当前仅为源码交错分析，尚未通过测试复现；FAQ 当前进程重载不代表其他 worker 已重载。

2026-11-02：重新将原主工作区 Git 可见的现存普通文件与集成副本 `snapshot-main` 比较内容哈希，未发现不同或快照缺少的文件；比较跳过符号链接、缺失文件和 Git 忽略项，不证明运行数据、外部资源或删除状态。将该快照提交 `e115eab` 另保存为原仓库分支 `codex/main-preserved-snapshot`，未切换或覆盖原工作区。保全不等于最终合并。

2026-11-02：剩余预算含估算时明确提示估算，页面以“已计入剩余”标注数值，避免将估算称为已知。行程专项 35 passed，前端 runner 构建通过并有大包警告；真实浏览器及数据待验收。

2026-11-02：修复剩余预算校验将估算停留或路段时长报告为通过的问题；估算值仍参与预算计算，未超预算时标为待核实，超预算仍报冲突。隔离回归先复现再通过，后端全套 503 passed、5 skipped；真实行程数据和设备待验收。

2026-11-02：本机静态构建通过临时仅本机服务在桌面内置浏览器打开游客首页和智能路线：界面展示数字人就绪、游览读取失败提示及离线预设，明确路线未结合实时客流。此次无后端、真实模型和手机设备，仅验证离线提示与入口可见，不证明完整导览链路；临时页面和服务已关闭。

2026-11-02：回收站恢复的迟到失败不再污染新游览；恢复成功但回收站刷新失败时明确提示已恢复。两项回归先复现再通过，前端全套 140 passed，runner 构建通过但仍有大包警告；真实浏览器和弱网待验收。

2026-11-02：修复从回收站恢复游览时，迟到请求覆盖新选游览的竞态；在确认当前请求后再更新游览及其进度、预算和版本。服务端恢复可能已成功，即使用户已切换页面。延迟及正常恢复回归通过，前端全套 138 passed，runner 构建通过并有大包警告；真实浏览器和弱网待验收。

2026-11-02：修复恢复历史版本时切换游览，迟到的恢复及后续刷新响应可能覆盖新游览的竞态；服务端操作可能已完成。延迟回归先复现再通过，前端全套 136 passed、runner 构建通过并有大包警告。删除游览恢复路径的类似竞态、真实浏览器和弱网仍待核查。

2026-11-02：重新定位独立历史清理的只读扫描及原任务来源；准备分支 `codex/legacy-cleanup-prep` 仍在较早的 `4054485`，不能直接当作当前集成基线。当前集成树对扫描中三份 2026-10-03 旧设计文档的完整文件名搜索未发现引用；尚未复核其他候选、真实运行验收或执行删除。按原任务先等稳定基线，再在独立分支逐项核验并处理。

2026-11-02：此前临时测试环境被清理后，重新建立 Python 3.13 隔离环境，在集成版本 `2201b69` 运行后端全套：502 passed、5 skipped、7 warnings。该环境仅安装测试所需的部分依赖，不含完整向量/语音模型；不证明真实供应商、设备或生产数据。系统 Python 3.14 安装所固定 Pydantic 依赖时编译失败，不据此宣称项目支持 3.14。

2026-11-02：有限静态复核 FAQ、缓存和 RAG 来源事件：输出前检查知识 epoch，无检索文档时走无证据答复；未发现可确定复现的新错配。引用是否支持具体答案仍须真实模型及人工核验。本次尝试重跑问答专项时发现此前 `/private/tmp/guide-faq-resume` 环境已不存在，系统 Python 也缺 FastAPI；因此本次未运行后端测试，历史测试结果仍仅适用于各自记录的版本和环境。

2026-11-02：修复保存行程提案时检查后台提案导致保存状态卡住的竞态，保存期间暂停相关提案操作。延迟回归先复现再通过；前端全套 135 passed，runner 构建通过且仍有大包警告；真实浏览器及弱网待验收。

2026-11-02：修复提案应用成功、进度仍在刷新且应用结果与草稿相同时，重复确认可能发起第二次保存的问题；新增独立保存中状态与按钮提示。Pinia 延迟回归先复现再通过；前端全套 134 passed，runner 构建通过、仍有大包警告。真实浏览器和弱网未验收。

2026-11-02：修复确认行程提案后，旧游览的进度、版本或预算请求迟到时覆盖新游览状态的竞态；应用成功不等于后续刷新完成。Pinia 模拟延迟回归先复现问题；前端全套 133 passed，runner 构建通过但仍有大包警告。真实浏览器、弱网和多设备交互仍待验收。

2026-11-02：复核原 W02 任务读取/取消/重试入口，路由文件与原快照一致；集成仓库增加进度 fence 和外部结果不确定性等保护。任务验收及游览提案专项 28 passed；真实供应商、浏览器与全部并发行为仍待验收，详见 W02 集成记录。

2026-11-02：景点目录绑定发生变化时，保守地将原 `source` 停留时长标为估算待核实，保留已有引用；游客填写时长保持原来源。`reference_id` 与景点版本没有明确绑定，生产代码未发现创建 source 时长的路径，此处理主要覆盖历史或外部数据，并可能对仍有效的独立资料保守降级。回归先复现，后端全套 502 passed、5 skipped；真实目录及浏览器待验收。

2026-11-02：补齐历史提案在景点和停留时长同时变化时的证据清理，预览改按 AI 估算处理并与确认结果一致；隔离测试覆盖时长变化及不变，后端全套 501 passed、5 skipped。景点目录版本改变而旧时长证据仍被保留的可能性待进一步核实；真实模型和浏览器未验收。

2026-11-02：读取历史行程提案时，对比原草稿并移除替换景点所继承的旧时长和路段证据，原本显示通过的改为待核实；返回时重算差异，不改写历史记录。隔离回归覆盖预览和确认的时长/路段证据一致，后端全套 500 passed、5 skipped；真实模型和浏览器待验收。

2026-11-02：修复替换景点时沿用旧景点停留时长证据的问题：原时长保留为待核实估算；直接编辑快照时，端点景点变化的路段时长和证据清除。回归先复现问题，后端全套 499 passed、5 skipped；历史已保存提案、真实模型及浏览器仍需验收。

2026-11-02：隔离 SQLite 外键开启并显式 SQL BEGIN 的候选补齐实验，在三个阶段注入异常后，代表性结构与数据回滚且重试的知识关联检查通过；其中知识迁移后回滚及重试已加入隔离回归，迁移专项 4 passed。未覆盖进程终止、全部 schema 或真实旧库，重试结果未提交，尚不能作为生产恢复方案。

2026-11-02：独立 PostgreSQL 17 临时实例通过 asyncpg 和 Alembic Operations 实验旧 W02 结构补齐；一条合成知识和分块关联到 `legacy_47`。未检查游览、任务、缓存、完整 schema、故障恢复及真实数据，未设置 Alembic 版本；实例已停止，不构成旧库迁移验收。SQLite 外键开启的知识迁移片段加入可重复隔离实验；后端全套 496 passed、5 skipped，实验不提供旧库修复功能。

2026-11-02：SQLite 实验进一步对照共有列类型、可空性、默认值及可反射 unique/check，未见差异；三个实验新增外键匿名，与新库命名约束不同。合成建表后异常实验显示 DDL 可部分持久化。隔离 PostgreSQL 实例已启动并停止，但同步驱动缺失，迁移未测；真实库、完整约束及故障恢复仍待验收。

2026-11-02：外键开启的隔离 SQLite 上，以原生增列替换知识迁移表重建的实验保留合成知识、游览和任务关联，外键检查为空；表、列名、外键指向及索引对照新库，仅差实验未执行的语音字段补齐。类型、约束、失败恢复、真实数据和 PostgreSQL 未验收；尚无可用于生产的修复方案。

2026-11-02：旧 W02 恢复候选在合成 SQLite 上作有限实验：外键关闭时知识版本、游览和任务关联保留、问答缓存清空；显式开启外键后知识表批量重建触发约束错误。未修改真实数据库或 Alembic 版本；完整 schema、异常恢复、真实数据和 PostgreSQL 均未验证，候选不能直接用于修复，详见 W02 集成记录。

2026-11-02：补充知识工作区表与关键字段的迁移检查；隔离 SQLite 复现部分结构缺失后检查可中止，后端全套 495 passed、5 skipped。检查不修复旧库或证明完整 schema，原知识迁移会回填版本并清空问答缓存；真实旧库及 PostgreSQL 仍需副本验证。

2026-11-02：对照原始 W02 快照发现其任务迁移的父节点是 `e9f4c2b8016a`，此前测试模拟的 `5c81a1e74f2b` 路径并非原始路径。隔离 SQLite 切换集成版升级至当时 head 后，行程提案表、游览进度表和部分知识工作区结构仍缺失；语音列已补。新增迁移检查关键结构并阻止不完整库继续升级，不自动修复且不是完整 schema 验证。后端全套 494 passed、5 skipped；真实旧库与 PostgreSQL 仍需在备份副本验收，详见 W02 集成记录。

2026-11-02：赛事模式使用 stub 语言模型时，`/ready` 报告 `llm_stub_not_competition_ready`，开发模式的 stub 路径保留。专项先复现再修复，后端全套 493 passed、5 skipped；配置检查不证明真实模型、视觉或语音服务连通。

2026-11-02：复核五个框架的 PyPI 页面版本、包许可与 Python 下限；Pydantic AI 和 Langfuse 当前页面均要求 Python 3.11 以上，旧 3.10 交集不再适用于当前版本。记录见框架调研；未安装框架或进行真实业务性能对照。

2026-11-02：将此前仅在工作区保存的开源框架调研快照纳入仓库，并修正目标架构和决策文档的引用；内容为 2026-10-30 快照，不代表当前版本或真实性能对照。

2026-11-02：增加管理员鉴权的当前进程 FAQ 单独重载接口及后台入口，不重新导入或修改资料；界面提示其他进程及语义索引需另查。后端全套 492 passed、5 skipped；前端 runner 构建通过并有大包警告，仓库地图检查通过。实际浏览器管理流程、跨 worker 同步及真实模型恢复仍待验收。

2026-11-02：盲区补充 FAQ 与 processed-data 同步在数据库提交后若 FAQ 刷新失败，返回 503 及 `faq_saved_reload_failed`，明确资料已保存并提示核对、避免重复提交；管理页面识别并展示警告。隔离数据库验证盲区 FAQ 已提交，另以替身覆盖同步路径，相关测试 7 passed；前端 runner 构建通过且有大包警告。旧客户端需兼容结构化错误，真实浏览器故障及跨 worker 索引恢复仍待验收。

2026-11-02：FAQ 重载失败增加进程内故障标记，`/ready` 返回 `faq_reload_failed`；只有后续完整重载成功才清除，避免数据库短暂恢复后误报就绪。隔离测试覆盖失败、恢复及就绪接口；后端全套 489 passed、5 skipped。该状态不跨 worker 汇总，真实数据库故障和运维恢复仍待验收。

2026-11-02：隔离模拟确认 FAQ 重载时数据库读取失败会先清空进程内 FAQ。保留旧索引的候选改动已撤回：后台数据可能已更新，静默继续使用旧答案会损害知识一致性。当前行为导致精确 FAQ 暂不可用，需后续设计显式故障提示及安全恢复；未验证真实数据库故障。

2026-11-02：FAQ 语义索引运行中构建或重载失败记录进程内故障，`/ready` 报告该故障；后续成功构建可清除标记。隔离测试覆盖失败、恢复和就绪状态；后端全套 488 passed、5 skipped。标记不跨 worker 共享，不能代替多进程健康汇总或真实模型故障验收；向量模型启动缺失状态仍需重启后重新检查。

2026-11-01：FAQ 从数据库重载后若语义向量重建失败，移除失败索引并继续向调用方抛错，新加载的精确 FAQ 保留；隔离回归先复现问题，FAQ/启动专项 8 passed。后台操作可能已持久化后才遇到重载错误，不表示数据库更改已回滚；运行中故障的 `/ready` 状态及真实模型恢复仍待进一步处理。

2026-11-01：启动先加载精确/模糊 FAQ；语义索引预热失败时继续启动并在 `/ready` 标记 `faq_semantic_index_unavailable`。语义索引改为构建成功后再替换，避免失败的半成品对象；启动和索引回归先复现问题，后端全套 485 passed、5 skipped。失败场景为隔离模拟，真实模型故障及运行中恢复仍待验收；数据库加载错误仍会阻止启动。

2026-11-01：在临时 SQLite 写入明确标为测试的合成 FAQ 后，以缺少向量模型的真实本机服务请求 `/api/chat/stream`；收到测试回答与 `faq_exact`、`provider=local`、`completion=complete` 事件。此为本地 FAQ 快速通道及 SSE 工程检查，不是景区资料、真实模型质量、检索质量或性能基准；`/ready` 仍为未就绪。临时服务已停止。

2026-11-01：使用真实本机后端进程、临时 SQLite 和 stub 配置，在桌面浏览器验证已创建游览升级 V2、刷新后恢复、添加 15 分钟休息点及保存至第 3 版；并发现列表将休息点计为“景点”，已改为“停留点”，runner 构建通过、有大包警告。该 UI 文案修改后未重新浏览器复查；测试未调用真实模型、未验证景点目录、移动设备或生产数据。隔离服务已停止。

2026-11-01：修复启动时强制预加载缺失的向量模型导致服务直接退出的问题；模型不可用时允许启动并由 `/ready` 返回 `embedding_model_unavailable`，运行期问答沿用已有 FAQ/数据库检索回退，模型可用性在启动时检查、需重启重新评估。测试先复现失败；后端全套 483 passed、5 skipped。另用临时 SQLite、stub 配置启动真实本机进程：`/ready` 返回 503（还包含知识分块为空和语音凭据缺失），桌面浏览器可创建隔离空白游览；未验证真实 AI、语音、数据真实性或移动端。临时服务已停止。

2026-11-01：在桌面内置浏览器以 390×844 视口、仅本机静态构建及无后端环境检查 `f084d15`：游客首页显示数字人，智能路线面板可打开并显示离线提示，键盘输入可输入并启用发送按钮；未发送问题。此为视口模拟，不代表手机真机、触控、软键盘、麦克风、定位或 AI 问答可用。已恢复浏览器视口并停止临时服务。

2026-11-01：修正读取游览失败时同时显示空列表的误导提示；加载中或报错时不再显示“还没有保存的游览”，报错时不显示回收站为空。runner 构建通过（仍有大包警告），本机桌面浏览器在无后端时验证读取失败提示出现且空列表文字不出现；成功加载及真实弱网仍待验收。临时服务已停止。

2026-11-01：桌面浏览器无后端环境核查离线历史文化路线详情，确认展开内容含未经逐项核验的尺寸、历史说法及演出体验；详情现提示尚未逐项核验及活动以当日公告为准。runner 构建通过并有大包警告，浏览器已复查提示；原有内容仍需来源核验，不能据此宣称事实或活动真实可用。临时服务已停止。

2026-11-01：本机浏览器使用仅本机静态构建、无后端环境打开游客首页及智能路线，确认显示服务不可用和离线预设提示；发现路线卡中的“第一”类及历史年代描述缺少本次核验依据，移除所见三处宣传文字后重新构建并在浏览器复查。此为桌面浏览器的有限离线检查，不验证真实 AI、移动设备或完整业务链；路线详情及 `public/map-tester.html` 等其他资料仍含未逐条核实内容。临时服务已停止；构建仍有大包警告。

2026-11-01：继续对照 W02 前端：原有行程 API 和 store 命名导出均可找到，集成版增加提案恢复及需确认风险的重试；相关模拟恢复测试存在。此为接口结构及局部代码核对，不证明大型页面变更完全等价，真实浏览器待验收。

2026-11-01：对原 W02 与当前集成的七个核心 Python 文件核对函数/类名称并抽查任务执行 diff；原名称未消失，当前含进度版本、行程 handler 与结果持久化等适配。此为结构检查，不证明所有行为等价；详见 W02 集成记录。

2026-11-01：对 W02 原快照 `48ef626` 相对 W01 `a8c2837` 的 43 个变更路径与当前集成树逐文件比较：7 个内容相同、35 个内容不同、1 个历史执行记录原先缺失。该执行记录已恢复并标记为历史；不同内容包含后续适配和修复，尚未逐 hunk 证明全部原意得到保留，不能按路径存在认定功能均已整合。

2026-11-01：复核 W02 原开发目录 `code/w02-worktree`：43 个 Git 可见修改文件与其保全快照 `48ef626` 逐字节一致；其中 22 个与另一份 W02 集成快照 `5433557` 不同，不能简单按文件相同视为已集成。已将 `48ef626` 导入原仓库独立分支 `codex/w02-preserved-snapshot`，未切换或覆盖工作区；其快照分支保全不等于已合并。检查不含 Git 忽略文件和外部资源。

2026-11-01：在全新隔离 PostgreSQL 17.11 数据库对 `97ab671` 联合运行完整 PostgreSQL 任务专项，跨进程两种中断路径与原有会话竞争/fence 测试共 3 passed；服务已停止。结果不涵盖真实外部请求、自然租约等待或生产压力。

2026-11-01：扩展隔离 PostgreSQL 跨进程崩溃测试：写入外部调用开始标记后终止进程，手动过期租约及维护后进入 `waiting_user` 且不自动重新领取；与调用前恢复共 2 passed。未实际发出外部请求，不能代表真实供应商行为。

2026-11-01：隔离 PostgreSQL 扩展跨进程专项，实际终止领取任务且已记录尝试的进程，手动使租约过期并维护后，替代执行者取得更高 fence 并开始新尝试；专项 1 passed。仅验证外部调用前中断，不代表自然超时或真实供应商崩溃恢复。

2026-11-01：新增独立进程竞争领取的 PostgreSQL 专项，并在仅监听临时 Unix socket 的 PostgreSQL 17.11 空数据库验证 1 passed；两个进程仅一个获得任务。未证明事务实际重叠，也未验证外部调用或进程崩溃，详见 W02 集成记录。

2026-11-01：在集成版本 `6e6461b` 复核评测工具：22 项测试通过，100 题格式校验通过、错误 0。此次未请求模型，不能得出问答正确率、引用忠实度、时延或新旧架构收益；题目来源及人工标注仍需核验。

2026-11-01：集成版本 `0d764e3` 前端 Node 测试 132 passed，`vite build --configLoader runner` 构建通过并提示大于 500 kB 的分块；不代表真实浏览器、移动端或弱网验收。当前依赖通过 `frontend/node_modules` 软链接提供，普通构建路径的沙箱限制仍需在目标环境复核。

2026-11-01：对集成版本 `b1e9dd1` 重新运行后端全套，临时 Python 3.13 环境补齐 NumPy 和 BM25 后为 482 passed、3 skipped、4 warnings。此环境未安装完整向量及语音模型依赖；结果不证明真实模型、移动设备或实际数据库验收。

2026-11-01：在 `5c3d02e` 对提案确认及任务接口补跑隔离回归，稳定目录确认、发布目录撤回与任务身份/恢复相关测试共 11 passed；使用模拟模型，不代表真实供应商或完整浏览器验证。

2026-11-01：确认旧提案时重新检查相对原草稿新增或替换的景点；无景点代码或不在当前已发布目录时拒绝应用，未改变的游客自填地点保留。隔离回归覆盖历史无目录景点及原有手工地点，行程专项 38 passed；真实模型和浏览器尚待验收。

2026-11-01：恢复历史提案时，若原校验状态为通过而候选存在相对原草稿新增或变更的停留时长、或明确标记估算的停留/路段时长，返回状态保守降为待核实，不改写原数据库记录；隔离行程专项 36 passed。此检查不证明实际时长、所有约束或模型语义正确。

2026-11-01：AI 行程操作新增或替换景点必须提供已发布目录中的景点代码，拒绝无目录依据的自由文本景点；手工添加自由文本仍可用并标记待核实。隔离回归先复现问题，修复后行程专项 36 passed；真实模型和目录资料真实性仍待验收。

2026-11-01：AI 生成的停留时长在操作约束检查阶段即标为估算；包含估算停留或路段时长的方案标记为待核实，不因预算计算通过而声称验证完成。超预算仍阻止提案，提示改为计划时长超预算；后端全套 479 passed、3 skipped。历史已保存提案的校验状态不会自动重算，真实时长和模型仍待验证。

2026-11-01：修复确认 AI 提案时将游客未保存草稿中的手工时长误标为 AI 估算：来源规范化以创建提案时服务端保存的草稿为参照，锁定约束仍对照当前已保存行程。隔离回归覆盖手工时长保留与 AI 新增时长分别标记；后端全套 478 passed、3 skipped。真实浏览器、模型和已有历史记录仍待验收。

2026-11-01：提案读取时从已保存的 V2 原始及候选快照重算差异，覆盖旧提案中不一致的持久化差异；原始快照缺失或不合法时标记 `diff_verifiable=false`，服务端拒绝应用，界面提供按当前草稿重新生成。隔离数据库回归覆盖旧差异和缺失快照，相关后端 23 passed；前端 runner 构建通过、有大包警告。该变更不修改历史数据库记录，真实浏览器和模型仍待验收。

2026-11-01：修复 AI 提案差异先于景点目录及来源规范化生成的问题，新增差异现在使用最终候选行程，避免确认界面展示模型编造的景点名称；界面提醒 AI 建议时长需核对。模拟模型的回归先复现后通过，相关后端 22 passed；前端 132 passed、runner 构建成功且有大包警告。已持久化旧提案的差异不会自动修复，真实模型及浏览器仍待验收。

2026-11-01：修复 AI 提案新增或变更时长被错误标为游客填写的问题，改为估算来源并要求确认；不变时长保留原来源，手工更改仍为游客输入。来源、意图及任务验收专项 21 passed（含模拟模型）；历史记录不自动更正，真实模型和界面显示仍待验收。

2026-11-01：在仅监听临时 Unix socket 的隔离 PostgreSQL 17.11 验证 `6e1a4c7d9b20`：模拟旧 W02 链与全新安装均升级成功，降级后语音字段仍存在。实验未写入业务行，不证明 PostgreSQL 上已有数据保留或真实数据库升级；临时服务已停止。初次沙箱内初始化因共享内存被拒，提权隔离实验首次使用 SQL_ASCII 遇到驱动编码错误，改用 UTF-8 后通过。

2026-11-01：新增后继迁移 `6e1a4c7d9b20`，为旧 W02 迁移漏掉的语音元数据字段做在线检查及补齐；已存在时不重复添加，降级保留字段及数据。隔离 SQLite 旧链和新链迁移测试通过；后端全套 474 passed、3 skipped，随后增加降级数据保留断言专项通过。该修复不覆盖其他未知 schema 差异或 PostgreSQL，不能替代对实际数据库备份和副本验证；迁移不支持离线 `--sql`。

2026-11-01：用隔离 SQLite 模拟旧 W02 迁移后切换到集成迁移，确认 `upgrade head` 不会补上缺失的 `chat_logs.speech_metadata`，尽管版本已显示 `f1b4c9d76e20`。详见 [W02 集成记录](W02_INTEGRATION.md)；实际数据库状态未知，不能仅根据版本号升级或直接操作。原项目三个开发目录未发现非依赖目录下的 SQLite 文件或 `backend/.env`，但这不能排除外部数据库、其他配置路径或忽略目录中的数据。

2026-11-01：将集成副本的 `2756f48` 以本地 fetch 导入原仓库新分支 `codex/competition-integration`，未切换原工作区分支，也未覆盖其文件。导入后原工作区仍在 `672a104`，115 个 Git 可见修改文件逐字节与 `e115eab` 保全快照一致；此检查不覆盖 Git 忽略文件、数据库或外部资源。新分支可供独立检出与审阅，不代表已合并到原工作区当前分支；持久数据库迁移仍需单独确认。

2026-11-01：复核集成版本 `fba5cbe`：隔离 Python 环境后端全套 473 passed、3 skipped，前端 Node 测试 132 passed；结果不证明真实模型、语音或浏览器可用。集成分支距主工作区保全快照 `e115eab` 有 150 个提交；原主工作区仍有未提交修改，尚未合回。更新当前架构索引中已过时的测试与基线说明。

2026-11-01：行程提案列表与详情的成功响应增加 `Cache-Control: no-store`，降低游客需求及提案内容被遵循 HTTP 缓存指令的客户端或中间缓存保存的风险；ASGI/SQLite 接口测试先复现缺失响应头，修复后执行任务验收测试 9 passed。此项不覆盖其他包含个人信息的接口、非遵循指令的客户端或生产代理配置。

2026-11-01：为提案列表新增的原始需求字段验证匿名身份隔离：隔离 ASGI/SQLite 测试中，另一身份访问同一游览列表得到 404 且响应不含需求文本；相关专项 1 passed。该测试不代表多租户或生产部署安全验收。

2026-11-01：补充同时间戳提案手动选择的两个模拟乱序回归：切换游览后旧详情不得覆盖新行程，连续选择时旧响应不得覆盖新选择；前端 132 tests passed。真实浏览器及 worker 并发仍待验收。

2026-11-01：提案时间并列时，游客可按最近十条中的原始需求和状态主动选择查看，不再只能联系管理员；查看走现有受身份约束的详情接口，不启动新模型调用。后端列表增加请求文本；后端全套 473 passed、3 skipped，新增列表字段专项通过；前端 130 tests passed、runner 构建成功并有大包警告。并发切换和真实浏览器/worker 仍待验收。

2026-11-01：修正同时间戳提案恢复提示：先等待后台并请管理员核查，避免建议游客直接重发造成重复调用费用。前端 130 tests passed、runner 构建成功并有大包警告；同时间戳任务仍缺自动消歧界面。

2026-11-01：提案列表按创建时间和随机 ID 排序，同时间戳不能可靠区分先后；前端发现最新两条时间相同时不自动恢复，提示基于当前行程重新生成。前端 130 tests passed、runner 构建成功且有大包警告。此为保守回退，尚无跨数据库的单调任务序号；真实并发和浏览器待验收。

2026-11-01：恢复行程提案时严格依据最新任务状态，失败状态可见，已应用状态不会复活旧的待确认提案；模拟恢复测试先复现问题，前端 129 tests passed、runner 构建成功且有大包警告。真实浏览器和持久 worker 故障恢复仍待验收。

2026-11-01：行程确认界面保留原始请求与差异展示，并明确约束检查只覆盖已识别内容，提醒游客核对遗漏和误改。前端 127 tests passed、runner 构建成功且有大包警告；真实用户测试与浏览器验收尚未进行。

2026-11-01：路线时间解析不再把“1小时30分钟”或“3小时以上”误作确定的最长预算；后端 473 passed、3 skipped（当前环境无 Chroma）。该规则仍覆盖有限表达，不代替通用约束解析或真实多轮验收。

2026-11-01：路线时间冲突澄清事件使用 `route_clarification` 并标记本地来源，不再冒充预设路线或 RAG；后端 473 passed、3 skipped（当前环境无 Chroma）。完成事件表示消息结束，不代表游客任务完成；真实多轮体验仍待验证。

2026-11-01：路线时间冲突澄清明确提示重新选择或清除旧时间设置，并验证更正后可继续；后端 473 passed、3 skipped（当前环境无 Chroma）。网页聊天选择目前发送空的 `available_hours`，其他 API 客户端须自行更新选择；真实多轮界面尚未验证。

2026-11-01：更正先前“显式选择预算优先”的静默覆盖：当界面预算与问题中可明确识别的整小时不同，聊天路线请求先提示确认、不输出路线。后端 473 passed、3 skipped（本环境无 Chroma）；模糊表达及真实多轮交互仍需验证。

2026-11-01：对“至少三小时”“三小时后到”等无法当作最长预算的表达不再推断预算；含模糊时长时提示游客核对。后端 472 passed、3 skipped（当前环境未安装 Chroma）；规则仍非通用语言理解，真实模型及实地耗时待验证。

2026-11-01：为自然语言整小时路线预算补充流式问答入口验证，检查意图、路线和完成事件；当前隔离环境后端 471 passed、3 skipped。该环境未装 Chroma，真实 Chroma 专项被跳过；真实模型、语音和设备仍未验收。

2026-11-01：聊天预设路线支持从明确的单一整小时表达（如“两个小时”）提取预算，并优先匹配标注时长；显式选择预算优先。小数、半小时、范围及冲突表达不解析为预算，仍需游客核对；不构成通用自然语言理解。隔离环境问答与推荐专项 47 passed，未运行真实模型、完整后端或实地性能测试。

2026-11-01：重新只读比较三个原始开发目录中 Git 可见的未提交路径与集成时保全快照：主工作区 115/115 与 `e115eab` 一致，V01 49/49 与 `3805943` 一致，W02 44/44 与独立副本 `integration-work/w02-integration` 的 `5433557` 一致。比较逐路径读取快照文件字节，不检查被 Git 忽略的文件、运行数据库或外部资源；W02 是按增量审阅集成，不表示其旧版本文件逐个覆盖到当前基线。原工作区未修改，当前集成分支仍未合回原工作区。

2026-11-01：景点失效后清空已缓存景点目录并要求重载；刷新失败时不复用旧匹配。前端 127 tests passed、runner 构建成功且有大包警告；并发刷新和真实浏览器待验收。

2026-11-01：前端收到景点失效错误后清除选择并禁止用旧 ID 重试；模拟 SSE 回归先失败后通过，前端 126 tests passed、runner 构建成功且有大包警告。真实浏览器和发布并发仍待验收。

2026-11-01：显式景点 ID 已下架或不可用时，问答返回重新选择错误，不再退回历史景点或无范围检索。模拟失效选择回归先失败后通过；后端 472 passed、2 skipped。真实浏览器提示与并发发布场景仍待验收。

2026-11-01：景点目录首次加载失败后，再次选择时可重新加载；加载期间切换工具或忙状态变化会阻止旧选择提交。前端 125 tests passed、runner 构建成功且有大包警告；异步界面完整行为和真实弱网仍待浏览器验收。

2026-11-01：地图及景点工具按名称发问时，若已发布目录无唯一匹配则提示并停止提交，避免静默沿用旧会话景点；前端 124 tests passed、runner 构建成功且有大包警告。目录加载失败时该入口不可用；浏览器完整链路仍待验收。

2026-11-01：地图景点自动讲解当前使用演示坐标，因此仅允许模拟定位触发；真实定位下保留手动景点讲解，界面明确说明限制。前端 123 tests passed、runner 构建成功且有大包警告。已发布的真实坐标接入自动触发、真机与定位精度仍待验证；不能宣称真实到点自动导览已实现。

2026-11-01：自动讲解请求返回后再次检查位置状态与距离；定位失效或已离开时不启动迟到音频，手动重播不受该检查约束。前端 122 tests passed、runner 构建成功且有大包警告；位置判断采用模拟回归，尚未验证真实手机、请求时序和音频播放。

2026-11-01：自动讲解触发同步异常或异步拒绝时清除未完成状态，允许后续重试，并防止旧失败覆盖新任务；前端 121 tests passed、runner 构建成功且有大包警告。回归为模拟异常，真实设备与供应商仍待验收。

2026-11-01：地图讲解状态加入请求代次，避免旧请求结束后重置新请求状态；模拟乱序回归先失败后通过，前端 119 tests passed、runner 构建成功且有大包警告。真实浏览器音频与设备仍待验收。

2026-11-01：地图讲解排队超时时，只有确认中断地图自身音频后才继续，避免抢占聊天或其他音频；模拟状态回归先失败后通过。前端 118 tests passed、runner 构建成功并有大包警告；真实浏览器和设备尚待验收。

2026-11-01：排队讲解被新景点替换时，清除旧任务的未播放标记，避免重访时无法讲解；前端 117 tests passed、runner 构建成功且有大包警告。定位和音频测试使用模拟状态，真机待验收。

2026-11-01：定位失效丢弃排队讲解时清除未播放的触发标记，定位恢复可重新触发；前端 116 tests passed、runner 构建成功且有大包警告。定位和音频回归使用模拟状态，真机待验收。

2026-11-01：修复排队讲解在位置失效或离开范围后仍可能先中断当前音频的问题，先验证位置和距离再处理中断；前端 115 tests passed、runner 构建成功且有大包警告。测试使用模拟状态，真机音频仍待验证。

2026-11-01：自动讲解只读取有效真实或显式模拟位置；精度不足、景区外及停止定位时不再用旧坐标触发，位置清空时地图移除旧标记。前端 114 tests passed、runner 构建成功并有大包警告；回归使用模拟定位，真实手机和弱网尚待验收。

2026-11-01：修复定位模式混淆：景区外真实坐标不再声称已切换模拟，进入模拟时不再沿用上次真实坐标，并保留定位失败提示；地图无障碍名称改为示意地图。前端 113 tests passed、runner 构建成功且有大包警告；测试使用模拟定位回调，真实设备与地图坐标仍待核验。

2026-11-01：聊天路线在显式预算下没有已知时长符合的模板时，明确告知游客再展示参考路线；后端 471 passed、2 skipped。提示仅依据模板标签，不证明实地耗时或自然语言预算抽取。

2026-11-01：聊天路线选择在显式选择可用小时数时，先按已知模板时长筛选，再处理亲子等偏好；无已知匹配仍返回需核对的参考路线。隔离回归覆盖两小时预算与六小时亲子路线冲突，后端 470 passed、2 skipped。自然语言时间抽取、真实路网和实测时长仍未完成验证。

2026-11-01：聊天中的预设路线答复明确提示未结合实时路况和客流，三小时请求不再把截取的景点称为已验证的三小时路线，两点问路不再断言实际步行通路。后端 469 passed、2 skipped；仍未接入真实路网、客流或实测时长，真实 TTS 待验收。

2026-11-01：路线详情直接展示推荐理由及路线、时长和客流限制，原先理由藏在默认折叠内容中；推荐标签改为“预设路线”。前端 112 tests passed，runner 构建成功且有大包警告；真实浏览器与移动端展示待验证。

2026-11-01：路线推荐优先在标注时长不超过游客可用时间的模板中选择；没有已知匹配时仍返回建议并提示自行核对。后端全套 468 passed、2 skipped；随后新增无匹配回退专项，推荐模块 6 passed。模板时长并非真实路网或实测，无法保证实际行程符合预算。

2026-11-01：新增前后端路线快照契约测试，执行真实前端快照函数，通过 ASGI 接口和隔离 SQLite 保存、读取未设置预算的行程；后端 467 passed、2 skipped。该测试不涉及真实浏览器或模型。

2026-11-01：修正 `2460032` 的设计错误：预设路线估算时长不应成为游客的可用时间预算。新建路线预算留空，更新已有路线保留游客原有约束；前端 112 tests passed，runner 模式构建成功且有大包警告。历史已保存的预算不会自动更改，需游客核对。

2026-11-01：推荐路线时长无法解析时接口 `duration_hours` 返回 null，前端显示“时长待确认”，不再用游客预算虚构路线耗时。此字段由必填整数改为可空，其他 API 客户端升级前须兼容 null。后端 466 passed、2 skipped；前端 111 passed，runner 构建成功并有大包警告。真实路网与耗时仍未验证。

2026-11-01：推荐器不再将可解析的预设路线时长截断为游客预算；整数小时字段按区间上限向上取整，保留原始标签。推荐理由不再宣称备选路线低拥挤或已验证步行/室内条件，明确现场核对；后端 466 passed、2 skipped。未接入真实路网或客流；无法解析时仍沿用可用时间作为兼容回退，不能当作实测路线时长。

2026-11-01：保存路线时保留小数时长，区间使用上限，无法解析时不再臆造两小时；页面注明路线与时长为参考，去除预设路线中未经验证的客流断言。前端 111 tests passed，runner 模式构建成功且有大包警告；实际时长、路网与真机操作仍未验证。

2026-11-01：部分明确票价和票务优惠问法绕过旧 FAQ、缓存及检索，提示核对官方票务信息；旧 FAQ 误输出价格的回归先失败后通过，后端 463 passed、2 skipped。关键词不覆盖所有问法，可能拦截历史价格问题；未接入实时票务，风险尚未关闭。

2026-11-01：推荐问题移除预填票价、优惠和具体交通路线，并去掉未核实的“世界最高”卡片描述；前端 110 tests passed、runner 模式构建成功且有大包警告。问答后端对票价与交通仍可能检索到陈旧内容，不能将此改动视为动态数据风险关闭。

2026-11-01：开放时间推荐问题不再内置未经核实的场馆时刻，改为询问并提示查看当日官方公告；前端 110 tests passed，`vite build --configLoader runner` 成功且仍有大包警告。常规构建因 node_modules 软链接指向沙箱外、Vite 无法写临时配置而失败；真实浏览器、其他推荐问题的资料时效仍待检查。

2026-11-01：对“开放时间、营业时间、演出时间、什么时候开放、几点开放、几点开门、几点关门”明确问法，问答入口返回无法核实时效及以当日官方信息为准的提示，绕过旧 FAQ、缓存和检索；隔离测试覆盖文本和模拟语音，后端 462 passed、2 skipped。该关键词保护不覆盖所有问法或其他场景，可能拦截历史问题，不代表动态数据风险关闭；实际数据库、旧客户端和真实语音仍需核验。

2026-11-01：集成代码 `a5e8726` 在隔离 macOS ARM / Python 3.13 环境运行后端全套 460 passed、2 skipped；该环境包含 ChromaDB 1.5.9，实际 Chroma 的两个专项包含在通过数中。未安装完整嵌入模型及语音模型依赖；通过结果不代表真实模型、移动设备或 PostgreSQL 多进程验收。

2026-11-01：修复评测来源命中率把未配置预期来源的拒答题计为命中的问题；报告限定有效题目并给出分母。回归先复现 0.5 的错误结果，修复后评测工具 22 passed；旧报告口径不同，不能直接对比。

2026-11-01：真实本地 Chroma 专项增加重复 ID 导致重建写入失败的验证：旧索引仍可查询，临时 collection 被清理；专项 2 passed。该测试不覆盖进程崩溃、断电、跨进程写入竞争或真实嵌入模型。

2026-11-01：macOS ARM、Python 3.13 隔离环境使用 ChromaDB 1.5.9、Pydantic 2.11.7，通过真实本地 Chroma 持久化测试（1 passed）：合成向量的替换、过滤、增删及新进程重开。未验证真实嵌入模型、检索质量、并发或完整项目依赖；缺少 Chroma 时该专项跳过。

2026-10-31：依赖清单显式启用 SQLAlchemy 的 asyncio extra，避免部分平台安装后缺少 greenlet；在 macOS ARM、Python 3.13 上使用 pip dry-run 验证解析包含 greenlet。完整模型依赖及其他平台仍需各自验证。

2026-10-31：模型回答的供应商标识改用配置值，评测报告增加后端自报路径和降级统计，并增加回归测试。隔离 Python 3.13 环境中后端 458 passed、2 skipped，评测工具 21 passed；未安装完整模型与向量依赖。配置值不是外部调用凭证，真实调用仍需脱敏日志核验，真实服务及设备待验收。

2026-10-31：向量候选经数据库片段验证后，再按真实片段的景点 ID 和类别核对检索范围；不匹配则使用现有回退。缓存键更新为 v9。隔离 SQLite 和假向量回归先复现再通过，后端 457 passed、2 skipped；真实 Chroma 和检索性能待验收。

2026-10-31：损坏的向量条目 ID 不再使检索直接报错；跳过该候选，无有效候选时回退数据库。隔离测试先复现再通过，后端 457 passed、2 skipped；真实 Chroma 与弱网仍待验收。

2026-10-31：向量候选经发布片段归属验证后，从数据库读取正文、标题和来源，避免向量存储中不一致的文本被当作证据；缓存键升至 v8。隔离 SQLite 和假向量测试覆盖伪造文本，后端 456 passed、2 skipped。向量排序仍依赖索引，真实 Chroma、性能和来源本身的真实性仍待验收。

2026-10-31：向量候选增加数据库片段归属校验，片段须存在且属于当前可见的条目修订；不匹配时回退数据库。缓存键升至 v7，避免沿用未做归属校验的结果。隔离 SQLite 与假向量测试覆盖伪造片段，后端 456 passed、2 skipped；向量正文与数据库正文一致性、真实 Chroma 与检索性能仍待验证。

2026-10-31：向量结果的片段元数据与记录 ID 明确冲突时拒绝该结果，并在无其他候选时回退数据库；隔离测试先复现再通过，后端 456 passed、2 skipped。旧索引缺少片段字段时仍兼容，且当前版本可见性检查尚不校验片段与数据库版本的归属或正文一致性；不能将此称为完整证据校验，真实 Chroma 待测。

2026-10-31：景点限定问题不再使用缺少景点绑定信息的通用 FAQ，改走限定检索；普通未限定问题保留 FAQ 快速通道。缓存键升至 v6，避免复用旧的限定景点 FAQ 改写结果。隔离回归先复现再通过；后端全套 455 passed、2 skipped。限定路径可能增加延迟，真实模型及设备须测量，不能宣称已满足性能目标。

2026-10-31：语音确认界面不再将启发式固定数值展示为置信度百分比，仅展示有效的供应商置信度；它仍不是识别准确率。前端 110 tests passed、构建成功，真实语音与设备待验收。

2026-10-31：ASR 的启发式固定置信度不再触发自动发送，转写须由游客确认；真实供应商置信度仍按现有阈值处理。回归先复现再通过，后端全套 454 passed、2 skipped；真实语音识别和手机操作仍未验收。

2026-10-31：补齐接口允许的 confused、urgent 语音状态映射，紧急状态保留输入置信度而不人为抬高；隔离回归先失败后通过，后端全套 453 passed、2 skipped。这是协议一致性修复，不证明模型能可靠识别情绪，也不构成真实救援服务。

2026-10-31：非中性语音交互状态不再复用中性生成缓存，避免跳过表达策略；模拟音频情绪与模型的回归先复现再通过。后端全套 452 passed、2 skipped；不证明情绪识别准确性或真实语音体验。

2026-10-31：回答缓存键增加模型实际接收的原始问题，避免不同原文归一化成同一检索词后串用生成结果；隔离模拟模型回归先复现再通过。后端 451 passed、2 skipped；真实模型与设备仍待验收。

2026-10-31：模型角色会影响生成内容，现将角色加入共享回答缓存键，避免不同数字人角色串用生成结果；缓存键和两轮模拟问答测试通过。该轮后端全套 449 passed、2 skipped；随后新增角色串用专项 1 passed，真实模型表现仍待验收。

2026-10-31：修复共享问答缓存与游客记忆混用：有效记忆参与生成时跳过共享缓存读写，缓存键由 v4 升至 v5，避免命中可能包含个性化内容的旧缓存。隔离测试覆盖先通用后个性化、先个性化后匿名；后端 448 passed、2 skipped。v4 记录未被本次代码自动删除，部署环境的历史缓存及聊天记录需按实际数据管理策略单独处理；真实供应商与隐私验收仍待完成。

2026-10-31：修复 processed-data 同步整体删除历史分块的问题；现只重建未发布条目的分块，已发布及历史修订分块不被同步覆盖。隔离 SQLite 完整同步回归保留当前与历史片段，后端 447 passed、2 skipped。此前已经删除的历史分块不会自动恢复；导入报告的 `chunk_imported` 表示本次刷新未发布分块数，不是当前索引数。真实索引和资料可追溯性仍待验收。

2026-10-31：processed-data 导入加入与发布、重建相同的本地索引写锁，并在取消时等待导入事务结束再释放。隔离测试先复现绕锁后验证等待；后端全套 446 passed、2 skipped。导入不自动更新向量索引；真实 Chroma、Windows、跨进程完整服务及旧版本进程仍未验收，重建前仍建议停止其他写入并核对结果。

2026-10-31：发布与全量重建已使用同一索引目录的进程间写入锁：重建持锁覆盖片段快照至索引切换，发布持锁覆盖向量写入及数据库提交；取消时等待写线程/提交结束再释放。隔离假存储交错测试及进程锁测试通过，后端全套 445 passed、2 skipped。**暂不宣布 P0 全面关闭**：旧 processed-data 导入未接入此锁，真实 Chroma、跨进程完整服务、Windows 和共享网络文件系统未验证；旧版本进程不会遵守新锁。重建前继续停所有写入进程，核对已发布版本与检索。

2026-10-31：为索引写入协调新增本地文件系统跨进程锁组件；本机测试验证竞争超时、持锁进程被终止后释放及协程取消释放。该阶段尚未接入发布和重建，后端全套 441 passed、2 skipped、1 xfailed；后续接入情况见上文。

2026-10-31：发现全量索引重建与知识发布缺少跨进程协调：发布在重建快照之后、索引切换之前写入旧 collection 时，切换会丢失新向量。`test_rebuild_preserves_publication_that_occurs_after_snapshot` 用假存储确定性交错复现，标记 strict xfail；真实 Chroma 并发未测。暂行限制：停掉所有发布/导入写入及相关 worker、确认无进行中任务后才重建，期间禁止启动发布；重建完成核对数据库已发布版本及检索结果。只停管理页面不等于停后台进程。修复需跨进程协调覆盖发布 upsert 与数据库提交、重建切换及失败恢复，不能只在读取前后比较 epoch。此项为 P0 未解决风险。

2026-10-31：修复全量索引重建时根据条目、修订和序号重新拼接片段 ID 的问题；现在使用数据库片段主键，与发布路径一致。隔离 SQLite 和假向量存储覆盖非标准 ID、可见性及重建；后端全套 439 passed、2 skipped。本环境缺少 `chromadb`，未验证真实 Chroma，旧索引必须在隔离环境检查重建后再验收。

2026-10-31：向量检索的来源可携带真实片段 ID；数据库回退和旧数据允许为空。修复新发布时附加元数据可覆盖系统来源字段的问题，并在片段元数据与向量记录 ID 不一致时不输出片段 ID。后端全套 439 passed、2 skipped。已有向量索引不会自动修复；部署前需隔离检查并以当前代码重建，不能宣称历史索引均可信。来源与回答是否相符仍需人工核验。

2026-10-31：检索回答的来源事件保留可用的知识条目 ID 和发布版本 ID；隔离 SQLite 测试覆盖流式来源、聊天记录及跨 Pipeline 缓存读取。后端全套 437 passed、2 skipped。字段允许为空；FAQ 和片段级标识、引用是否支持回答与真实资料权威性仍需核验。

2026-10-31：补充隔离 HTTP→持久任务→worker→提案查询→确认/幂等重放的行程链路测试；稳定目录下仅增加一个版本，目录下架时拒绝应用且不改变行程。测试使用 SQLite、假目录及假模型结果，未运行真实浏览器或模型。后端完整测试 436 passed、2 skipped。

2026-10-31：补充开始游览和当前停留时间查询的异步状态保护，防止跨行程响应覆盖和多次输入的乱序覆盖；模拟乱序回归先失败后通过。前端全套 109 passed、构建成功，仍有大包警告；真实设备弱网未验收。

2026-10-31：修复进度命令及其预算刷新在切换行程后迟到时覆盖新行程状态的问题；两项竞态回归先复现再修复。前端完整测试 107 passed、构建成功（仍有大包警告）；实际浏览器及弱网测试仍待验收。

2026-10-31：补充进行中游览的手动剩余时间调整，确认时以服务端时间计算新截止时间，进度版本递增并记录旧/新截止时间；重复请求幂等，保留已游状态并使旧任务进度失效。后端 435 passed、2 skipped；前端 105 passed。自然语言提案尚不能把“从现在起剩余多少时间”直接纳入同一次确认；浏览器与真机体验仍待验收。

2026-10-31：发现进行中的提案/API 可修改总预算但未同步截止时间；拒绝该更改并保留其他提案编辑，避免产生互相矛盾的状态。该阶段后端全套 434 passed、2 skipped；随后添加了上文所述独立的手动剩余时间命令。

2026-10-31：修复进行中行程超过截止时间、当前点剩余时长为零时误报符合预算的问题；行程页面展示服务端包含估算条件的说明。固定时间测试先复现旧错误；后端全套 432 passed、2 skipped，前端 105 passed、构建成功（仍有大包警告）。实际设备与真实服务验收仍未完成。

2026-10-31：修复行程提案缺少总预算时错误显示通过的问题；与剩余预算检查一致，标记为待核实，前端提示覆盖预算、时长和景点约束。回归先复现旧行为再修复；后端全套 431 passed、2 skipped，前端 105 passed，构建成功（仍有大包警告）。真实模型与浏览器/手机链路尚未验收。

2026-10-31 补充至 `7b6ce0a`：PostgreSQL 17 隔离数据库从空库迁移至当前 head，发现并修复任务父子记录写入顺序；两数据库会话竞争领取、租约过期及旧 fence 拒绝已验证。后端全套 430 passed、2 skipped（包括默认跳过的 PostgreSQL 专项），专项在真实隔离 PostgreSQL 上通过。随后取消与完成的会话竞争回归连续 6 次通过；不代表真实供应商、多进程压力或崩溃恢复验收。隔离数据库服务已停止。

2026-10-31 当前代码基线 `2d09492`：最新后端全套 430 passed、1 skipped；前端 105 passed、构建成功。真实浏览器、外部供应商、PostgreSQL 并发、移动设备及官方赛题原文仍未完成验收。独立工作目录为 `integration-work/v01`，原有 worktree 和快照保留；已有保存的服务电话未被默认配置变更，须管理员核实。

2026-10-30，集成分支 `codex/competition-integration`，基线 `ec3f7a6`。这是独立本地副本；原 worktree 及四份快照仍保留。`frontend/node_modules` 是本机依赖软链接，不属于源码交付。

已整合 K01、W01、V01、主工作区稳定性/语音和 W02 初版。后端 389 通过、1 跳过；前端 94 通过、构建通过；隔离 SQLite 迁移升级/回退通过。W02 真实浏览器与 worker、真实供应商、PostgreSQL 多 worker、移动设备和弱网仍未验证。真实旧 W02 数据库的迁移兼容尚未确认。

当前行动：独立审阅并运行 W02 完整任务链；核对官方评分与交付要求；保留清理候选，稳定基线后按原清理任务独立处理。随后构建真实服务评测集和重复测量基线，选择旗舰链路，分阶段实现与验收。

补充至 `1f96944`：修复 worker 调用前中断重试预算和 CLI 退出问题，后端 397 passed、1 skipped；评测器支持固定种子的类别分层选样，16 项测试通过。16 题离线选样覆盖 8 类，未调用模型。浏览器访问被 Work 设置禁用；隔离 PostgreSQL 初始化受共享内存限制，未验证多 worker。真实供应商与设备未验收。官方赛道规则正文未取得，评分矩阵中的权重仍是用户提供的工作依据。历史回答的来源归属和视觉候选的检索范围问题正在修复，不能把当前识景链描述为已验收。

补充至 `dcf3374`：历史回答的来源按消息绑定；视觉候选未经确认时开放检索，游客可从已发布目录明确选择并由服务端核对版本。错误候选、下架/更新和过期重试有自动化覆盖；拍照与识别竞态增加守卫。最后一次全量记录为后端 416 passed、1 skipped，前端 99 passed；后续修改需重跑。组件挂载测试所需 DOM 依赖当前缺失：离线缓存不可用，在线 npm 访问返回 DNS ENOTFOUND；浏览器禁用条件仍然存在。自动化和 fake provider 不能证明真实识景、引用忠实性、音画效果或手机体验。
2026-11-05：从已同步集成基线 `d54af02` 抽出 `StreamGenerationRun`，将单次 `StreamTurn` 创建、事件转发、LLM/epoch 结果检查和 canonical answer/terminal policy 定稿从 `QAPipeline` 移出；outcome 按 run 实例持有，避免并发请求共享结果状态。新增行为测试覆盖正常 FAQ 降级定稿和 epoch 错误禁止定稿。临时 `/private/tmp/guide-ai-arch-venv` 已不存在，系统 Python 3.12 无 pytest、FastAPI/Pydantic/SQLAlchemy，因此 pytest 用例本轮无法执行；使用 Python 3.12 直接运行等价行为脚本，FAQ 降级答案回权威文本、降级不可缓存、epoch 错误不定稿均通过。Python 3.14 compileall 与 diff check 通过。当前 Pipeline 880 行；结构职责进一步外移但传入配置行数令主文件总行数略增，后续要把 FAQ/cache/RAG 决策边界与生成运行参数进一步归并，不能以行数作为拆分完成标准。此轮未改缓存资格、来源绑定、FAQ/RAG 检索、知识 epoch 规则或降级 policy。工作树基线集成/ref `d54af02`；原 checkout `672a104`/95 状态路径、V01/W02/W02-V01 49/35/39、保护快照 5 个、phase3 prunable 均复核；集成 node_modules 未跟踪，`sources/` clean。真实 LLM/provider/TTS/设备及 PostgreSQL/部署库仍未验收。
2026-11-05：从集成基线 `8e481a4` 将生成完成后的缓存/持久化/fallback blind-spot/done 回调绑定抽至单请求 `StreamCompletionEffects`，并保持 `StreamCompletionCoordinator` 独占调用顺序和 epoch fence；Pipeline 从 880 降至 855 行。新行为测试验证 cache 参数、持久化上下文、fallback 记录和 done 元数据绑定。Pipeline、受众、generation runner/finalizer、completion、StreamTurn、producer lifecycle、fast path speech 合并回归 94 passed；Python 3.12 compileall 与 diff check 通过。测试使用本地替身，不代表真实模型/provider/设备验收。测试环境由前一阶段建立的临时 venv 提供轻量依赖。未改 FAQ 匹配、RAG 证据、缓存资格、知识 epoch 或降级 policy；原 checkout/活动 worktree/快照维持既有状态，`sources/` clean，`frontend/node_modules` 未跟踪。
2026-11-05：在集成基线 `c6bb750` 抽出 `resolve_cached_answer()`，承接已获准的共享 cache lookup、知识 epoch 复查和 persona 润色。`shared_cache_allowed()` 仍在 Pipeline 上游决定，stale hit 仍发送原有 error，miss 和 hit 的 SSE 顺序不变。新缓存路径行为测试加 Pipeline/FAQ/epoch/generation/completion/stream/TTS 回归共 97 passed；Python 3.12 compileall 与 diff check 通过。测试使用本地替身；真实模型/provider/设备未验收。当前 Pipeline 864 行（比前阶段增加 9 行，因边界调用展开；缓存读取逻辑单独归属，不以行数判断拆分价值）。原 checkout 95 个脏路径、V01/W02/W02-V01 49/35/39、五个快照及 phase3 prunable 均复核未变；`sources/` clean，集成 node_modules 保持未跟踪。后续仍需提取 FAQ/RAG 解析编排并扩大 AI 回归范围。
