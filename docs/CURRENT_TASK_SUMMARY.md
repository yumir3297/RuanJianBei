# 当前任务摘要

- 更新时间：2026-06-26
- 当前状态：已进入管理端设计契约接入与运营报表升级阶段；语音 A/B 输出、浏览器降级和 Live2D 口型进度链路已修正，仍需桌面 Chrome/Edge 人工听测
- 主线依据：[10-最终总体设计与开发主线.md](</D:/桌面/软件杯/设计文档/10-最终总体设计与开发主线.md>)
- 维护规则：每次用户确认下一步后，先更新本文件或生成对应实施报告，再开始编码

## 最终作品目标

构建一套可运行、可运营、可演示的景区导览 AI 数字人系统：游客端支持文本、语音、图片和主动选择；回答基于官方资料的 RAG 证据；数字人提供语音、口型和表情；后台支持知识、数字人配置、游客分析和数据大屏。

## 赛题硬指标

1. 至少 1 个多模态大模型真实参与业务。
2. 景区事实问答准确率不低于 90%。
3. 语音响应目标小于 5 秒。
4. 数字人口型与表情自然联动。
5. 官方景区资料包是核心事实源。

## 当前已完成

1. Vue 3 + FastAPI + SQLite 前后端骨架与 SSE 链路。
2. 官方资料提取、清洗、入库、同步与数据库驱动 FAQ/路线。
3. KnowledgeChunk、BGE Embedding、Chroma 真实索引与检索。
4. CrossEncoder、BM25、原向量顺序三级降级。
5. 30 题真实检索与重排评测。
6. `SelectionContext`、QuickTopic 配置和景点/路线 bootstrap API。
7. 游客端目标/景点/话题/路线选择、面包屑、localStorage 和聊天请求携带选择。
8. 服务端选择校验、文字实体冲突纠正、Chroma/SQL范围筛选和选择感知缓存。
9. D 盘 Embedding 模型离线加载、离线 Chroma 检索和运行时向量链路修复。
10. 受控快捷追问、可信连续上下文、5 轮主体保持和前端快捷交互。
11. Reranker 参数矩阵评测、条件式安全跳过与 CPU 性能闸门。
12. FAQ L3 实体/意图双门控、预计算语义索引、阈值评测与聊天主链路接入。
13. 知识盲区自动聚合、管理查询、FAQ 补录解决、索引刷新和同步保护。
14. 游客端灵山文化主题、导游“小灵”人设、游客化文案、来源编号和桌面/移动响应式改造。
15. 百炼音频与 SpeechSynthesis 分层降级、句级文本/口型时间线事件、播放进度和 Live2D 口型同步。

最新前端实施报告：

- `docs/2026-06-19-frontend-cultural-design-implementation-report.md`
- `docs/2026-06-21-voice-ab-acceptance-corrections-report.md`
- `docs/2026-06-26-design-integration-and-analytics-upgrade-report.md`

当前前端重点：

- 建立项目级 `DESIGN.md` 设计约束，统一游客端与管理端的视觉契约。
- 先完成管理后台 `AnalyticsReport` 页面升级，再推进知识库管理与盲区管理的风格拉齐。

当前真实基线：

```text
原始 Recall@1 = 96.67%
原始 Recall@5 = 100.00%
原始 MRR = 98.33%
重排 Recall@1 = 100.00%
重排 Recall@5 = 100.00%
重排 MRR = 100.00%
优化后 Reranker P50 = 661.82ms
优化后 Reranker P95 = 833.43ms
```

## 当前未完成

1. 真实多模态 LLM 与图片识别。
2. 真实 ASR、TTS 和 Avatar。
3. 管理后台前端完整运营闭环，包括盲区管理页面。
4. `link-knowledge` 与显式 Chroma 重建联动。
5. 100 题端到端评测与小于 5 秒语音验收。

## 当前开发主线

1. 阶段 A：主动选择、Reranker 性能、FAQ L3/盲区三个独立轨道。
2. 阶段 B：真实多模态 LLM、证据回答和图片识别。
3. 阶段 C：管理后台可运营闭环。
4. 阶段 D：ASR + TTS 语音闭环。
5. 阶段 E：数字人口型、表情与配置闭环。
6. 阶段 F：100 题、延迟、降级和演示保障。

## 阶段 A1 第一切片结果

1. 实施报告：[2026-06-12-stage-a1-selection-bootstrap-implementation-report.md](</D:/桌面/软件杯/docs/2026-06-12-stage-a1-selection-bootstrap-implementation-report.md>)。
2. 新增 `GET /api/quick-select/bootstrap`。
3. 真实接口返回 `8` 个话题、`22` 个景点、`3` 条路线。
4. 专项测试 `2 passed`，完整后端回归 `22 passed`，`compileall` 通过。
5. 未修改前端和问答 Pipeline。

## 阶段 A1 第二切片结果

1. 实施报告：[2026-06-12-stage-a1-frontend-guided-selection-implementation-report.md](</D:/桌面/软件杯/docs/2026-06-12-stage-a1-frontend-guided-selection-implementation-report.md>)。
2. 前端生产构建通过。
3. 后端完整回归 `22 passed`。
4. SelectionContext 请求校验与 dist 产物检查通过。
5. 未修改后端 Pipeline、RAG 和依赖。
6. 浏览器自动化视觉检查因当前会话缺少可用控制接口而未执行，已记录为验证缺口。

## 阶段 A1 第三切片结果

1. 实施报告：[2026-06-15-stage-a1-server-selection-aware-retrieval-report.md](</D:/桌面/软件杯/docs/2026-06-15-stage-a1-server-selection-aware-retrieval-report.md>)。
2. 完成数据库ID校验和文字实体优先冲突规则。
3. 完成Chroma/SQL统一范围筛选和选择感知缓存键。
4. SSE返回服务端可信上下文，前端同步更新选择。
5. 完整后端回归 `30 passed`，前端生产构建和compileall通过。
6. 真实SSE冲突与真实Chroma metadata筛选均通过。

## 下一次编码前的动作

1. 优化后的阶段 B 计划见 `docs/2026-06-15-stage-b-multimodal-and-evidence-execution-plan.md`。
2. B0 实测 `deepseek-v4-pro` HTTP 200，首 token `2609.65ms`，总耗时 `2612.16ms`，共 32 token。
3. 现进入 B1；自动化测试使用模拟 Provider，不继续消耗额度。视觉 Provider 在 B3 前另行确认，但视觉仍是阶段 B 硬性必做项。

## 阶段 A3.1 最终结果

1. 方案报告：[2026-06-15-stage-a3-faq-l3-and-blind-spot-plan.md](</D:/桌面/软件杯/docs/2026-06-15-stage-a3-faq-l3-and-blind-spot-plan.md>)。
2. 实施报告：[2026-06-15-stage-a3-faq-l3-implementation-report.md](</D:/桌面/软件杯/docs/2026-06-15-stage-a3-faq-l3-implementation-report.md>)。
3. 首轮全库单阈值方案失败并保留 v1 报告，未将失败方案接入主链路。
4. 最终采用“可信实体 + 受控意图双门控 -> 候选内语义排序”，运行阈值为 `0.60`。
5. 最终 21 条正例准确率 100%，13 条盲区负例拒绝率 100%，错误命中 0。
6. 202 个别名构建 `274.87ms`，查询 P50 `10.92ms`、P95 `13.51ms`。
7. FAQ 与向量 RAG 共享本地 Embedder；真实 Pipeline 为 `VectorBackedRAGService`。
8. 后端完整回归 `46 passed`，评测测试 `3 passed`。

## 阶段 A3.2 最终结果

1. 执行摘要：[2026-06-15-stage-a3-blind-spot-execution-summary.md](</D:/桌面/软件杯/docs/2026-06-15-stage-a3-blind-spot-execution-summary.md>)。
2. 实施报告：[2026-06-15-stage-a3-blind-spot-implementation-report.md](</D:/桌面/软件杯/docs/2026-06-15-stage-a3-blind-spot-implementation-report.md>)。
3. RAG 无证据问题按规范化查询唯一聚合，最多保留 5 个去重样本。
4. 新增管理查询和 `resolve-with-faq` 两个后端接口。
5. 补录 FAQ 强制非空来源，提交后刷新 L1/L2/L3。
6. 官方资料同步保护已解决盲区引用的人工 FAQ。
7. 真实 `app.db` 新表和 GET 接口验证通过。
8. 后端完整回归 `52 passed`，评测测试 `3 passed`，编译通过。

## 阶段 A2 结果

1. 实施报告：[2026-06-15-stage-a2-reranker-performance-gate-implementation-report.md](</D:/桌面/软件杯/docs/2026-06-15-stage-a2-reranker-performance-gate-implementation-report.md>)。
2. 参数矩阵报告：`eval/reports/reranker_gate_v1.json`。
3. 推荐组合为 `candidate_k=5、max_length=128`，30 题 Recall@1、Recall@5、MRR 均为 100%。
4. Reranker P50 为 `661.82ms`，P95 为 `833.43ms`，较旧 P95 约下降 86%。
5. 单候选或精确景点作用域内全部候选进入 Top-K 时安全跳过 CrossEncoder。
6. 无作用域和话题分类请求仍执行真实 CrossEncoder，BM25 与稳定顺序降级保持不变。
7. 真实关键题总检索约 `555.45ms`；精确景点检索约 `32.63ms`。
8. 后端完整回归 `40 passed`，评测测试 `3 passed`，编译通过。

## 阶段 A1 第四切片结果

1. 实施报告：[2026-06-15-stage-a1-controlled-followups-context-implementation-report.md](</D:/桌面/软件杯/docs/2026-06-15-stage-a1-controlled-followups-context-implementation-report.md>)。
2. 新增景点、话题、路线和自由提问四类受控快捷追问模板。
3. `context` SSE 返回可信 `last_subject`，前端在当前页面连续携带。
4. 所有回答路径在 `done` 前发送 `followups`，前端支持点击继续提问。
5. 清除选择时同步清除旧对话主体，防止历史景点污染。
6. 自动化 5 轮主体保持 `5/5`，真实两轮 SSE 连续追问保持 `attraction_id=13`。
7. 后端完整回归 `35 passed`，前端生产构建和编译检查通过。

## Embedding 离线加载修复结果

1. 实施报告：[2026-06-15-embedding-offline-loading-implementation-report.md](</D:/桌面/软件杯/docs/2026-06-15-embedding-offline-loading-implementation-report.md>)。
2. `SentenceTransformerEmbedder` 支持 `local_files_only`，聊天运行时固定为本地加载。
3. `HF_HUB_OFFLINE=1` 条件下成功生成 512 维向量并查询 66 条记录的现有 Chroma 集合。
4. 聊天 Pipeline 验证为 `VectorBackedRAGService`，实际检索模式为 `vector`。
5. Embedder 专项测试 `2 passed`，完整后端回归 `32 passed`，应用和评测脚本编译通过。

## 关键约束

1. 不创建五层编排抽象，不把所有逻辑堆进 `pipeline.py`。
2. 景点和路线复用现有数据库，不复制景区事实。
3. 选择、图片和 ASR 结果只作为检索线索，不作为事实来源。
4. 多模态模型必须真实处理图片或其他模态，不能只调用文本接口。
5. CrossEncoder 改为条件式路径，参数和阈值必须由评测确定。
6. 未经确认不修改 Schema、公共 API、依赖或模型供应商。

## 阶段 B1 结果（2026-06-16）

1. 实施报告：`docs/2026-06-16-stage-b1-deepseek-evidence-implementation-report.md`。
2. 已接入 DeepSeek `deepseek-v4-pro` 文本流式问答，接口仍走现有 `POST /api/chat/stream`。
3. 回答提示词升级为证据约束模式，模型必须基于检索资料并使用 `[证据N]` 引用。
4. 修复旧 QA 缓存污染：缓存键升级为 `qa:v3`，并纳入回答生成器命名空间，旧占位答案不会再短路真实 LLM。
5. 真实问题“玄奘为什么把马山命名为小灵山？”闭环通过，命中“小灵山的佛教缘起”，答案含 `[证据1]`。
6. DeepSeek 用量记录：`prompt_tokens=1072`，`completion_tokens=223`，`total_tokens=1295`。
7. 当前首 token 约 `30332.97ms`，功能闭环已通，但性能尚未达到最终演示指标。
8. 后端回归 `58 passed`，评测脚本 `6 passed`，专项测试 `15 passed`，前端生产构建通过。
9. 下一步进入 B2：100 题端到端准确率、证据引用率、拒答合规率和延迟评测。

## 阶段 B2 计划（2026-06-16）

1. 计划文档：`docs/2026-06-16-stage-b2-e2e-evaluation-development-plan.md`。
2. 当前尚未开始批量真实调用 DeepSeek，也未开始 B3 图片识别。
3. 建议下一步先执行 B2.1：评测框架骨架、10 题 seed 数据、离线校验和单元测试。
4. 小样本真实评测和 100 题批量评测前需要再次确认预算与题量。

## 阶段 B2.1 结果（2026-06-16）

1. 实施报告：`docs/2026-06-16-stage-b2-e2e-evaluation-framework-report.md`。
2. 已完成端到端评测框架骨架，新增 `check_e2e_testset.py`、`run_e2e_chat_eval.py` 和评分核心模块。
3. 已采纳 DeepSeek 审查建议：明确 `expected_behavior.must_pass`，新增 Mock 后端评分测试，延迟统计区分冷启动与热运行。
4. 新增 10 题 seed 评测集，覆盖事实、历史、景点、路线、实用信息、主动选择、追问和盲区拒答。
5. 本轮没有调用 DeepSeek，没有产生 API 费用。
6. 验证结果：新增 Mock 测试 `2 passed`，eval 全量测试 `8 passed`，编译检查通过，dry-run 报告已生成。
7. 下一步进入 B2.2：整理 100 题评测集，并先进行离线校验与 dry-run，不直接真实调用模型。

## 阶段 B2.2 结果（2026-06-16）

1. 实施报告：`docs/2026-06-16-stage-b2-e2e-100-testset-report.md`。
2. 新增 `eval/scripts/build_e2e_qa_100.py` 和 `eval/testset/e2e_qa_100.json`。
3. 100 题分布为：事实问答 30、历史文化 15、景点详情 15、路线规划 10、实用信息 10、主动选择 8、连续追问 6、知识盲区 6。
4. 行为分布为：证据回答 94、知识盲区拒答 6。
5. 已生成离线报告：`eval/reports/e2e_eval_b2_100_dry_run.json`。
6. 本轮没有启动后端，没有调用 DeepSeek，没有产生 API 费用。
7. 验证结果：`check_e2e_testset.py` 通过，`run_e2e_chat_eval.py --mode dry-run` 通过，eval 测试 `9 passed`，编译检查通过。
8. 下一步进入 B2.3 前需要用户确认是否进行小样本真实评测、题量和预算。

## 阶段 B2.3 结果（2026-06-16）

1. 执行计划：`docs/2026-06-16-stage-b2-sampled-real-evaluation-plan.md`。
2. 实施报告：`docs/2026-06-16-stage-b2-sampled-real-evaluation-report.md`。
3. 已按确认范围执行 5 题小样本真实评测，使用 `sampled-real` 模式请求本地临时后端 `127.0.0.1:8010`。
4. 首轮评测发现 FAQ/缓存/直答路径存在“有 sources 但答案正文缺少 `[证据N]`”的问题；事实命中和来源命中正常。
5. 已在 `backend/app/services/qa/pipeline.py` 的最终答案出口补齐直答类答案的内联证据编号，并新增对应后端测试。
6. 已修复 `eval/scripts/e2e_eval_core.py` 对纯 `text` SSE 事件的首文本时间统计，并新增 Mock 覆盖。
7. 修复后 5 题复测通过：`accuracy=1.0`、`evidence_rate=1.0`、`source_hit_rate=1.0`、`failure_count=0`。
8. 延迟已区分冷启动与热运行：首文本热运行 P50 约 `44.98ms`、P95 约 `52.74ms`；冷启动首题约 `16953.98ms`。
9. 首轮真实 DeepSeek 文本调用记录为 `prompt_tokens=645`、`completion_tokens=262`、`total_tokens=907`；本轮没有扩大到 100 题批量真实调用。
10. 验证结果：后端测试 `59 passed`，eval 测试 `9 passed`，100 题结构校验通过，编译检查通过；临时后端已关闭。
11. 下一步建议先让 DeepSeek 审查 B2.3 报告与修复点，再确认是否进入 10 到 20 题受控真实评测；100 题真实批量评测仍需再次确认预算。

## 阶段 B3.1 结果（2026-06-17）

1. 执行计划：`docs/2026-06-17-stage-b3-vision-provider-skeleton-plan.md`。
2. 实施报告：`docs/2026-06-17-stage-b3-vision-provider-skeleton-report.md`。
3. 已新增 `backend/app/services/vision/`，包含 `BaseVisionService`、`VisionResult` 和 `StubVisionService`。
4. `VisionResult.as_retrieval_query()` 将场景描述、OCR 文本、候选景点、视觉标签和用户问题合并为 RAG 检索线索。
5. 图片识别结果仍只作为 RAG 检索线索，不作为景区事实来源。
6. 本阶段未新增公共 HTTP API、未修改数据库 Schema、未新增依赖、未调用真实图片识别 API。
7. 验证结果：vision 专项测试 `2 passed`，后端完整回归 `61 passed`，编译检查通过。
8. B3.2 前仍需确认真实 Provider：阿里云百炼 Qwen 视觉理解或智谱 GLM-5V-Turbo，以及 API Key、模型名、预算和前端上传入口。

## 阶段 B3.2 结果（2026-06-17）

1. 执行计划：`docs/2026-06-17-stage-b3-qwen-vision-provider-plan.md`。
2. 实施报告：`docs/2026-06-17-stage-b3-qwen-vision-provider-report.md`。
3. 已在 `Settings` 中读取 `VISION_PROVIDER`、`VISION_API_KEY`、`VISION_BASE_URL`、`VISION_MODEL` 等配置。
4. 已新增 `QwenVisionService`，通过 OpenAI-compatible Chat Completions 方式发送 base64 图片给百炼视觉模型。
5. 已新增 `POST /api/vision/analyze`，接收图片二进制请求体，并返回 `retrieval_query`。
6. 接口返回结果只作为 RAG 检索线索，不作为景区事实来源。
7. 已更新 `backend/.env.example`，真实 `backend/.env` 中的 Key 未写入仓库文档。
8. 本轮没有执行真实 Qwen 网络调用，没有消耗百炼额度。
9. 验证结果：B3 专项测试 `6 passed`，后端完整回归 `65 passed`，路由 `/api/vision/analyze` 已注册，编译检查通过。
10. 下一步 B3.3 需要用户指定 1 张本地测试图片，并确认允许进行 1 次真实百炼调用。

## 阶段 B3.3 准备结果（2026-06-17）

1. 执行计划：`docs/2026-06-17-stage-b3-qwen-vision-smoke-plan.md`。
2. 准备报告：`docs/2026-06-17-stage-b3-qwen-vision-smoke-prep-report.md`。
3. 当前项目目录内未发现适合景区业务烟测的图片，虚拟环境依赖包自带图片不作为业务测试图。
4. 已新增受控烟测脚本 `eval/scripts/qwen_vision_smoke.py`，必须显式传入 `--image` 和 `--allow-network` 才会真实调用百炼。
5. 已修正守门逻辑：未传 `--allow-network` 或图片不存在时，不写正式烟测报告。
6. 验证结果：脚本编译通过，后端完整回归 `65 passed`，守门验证通过。
7. 本轮未进行真实 Qwen 网络调用，未消耗百炼额度。
8. 真实调用前仍需用户提供 1 张本地测试图片路径，并确认允许 1 次真实 Qwen 图片识别调用。

## 阶段 B3.3 真实烟测结果（2026-06-17）

1. 真实烟测报告：`docs/2026-06-17-stage-b3-qwen-vision-smoke-report.md`。
2. 用户提供图片目录：`D:\桌面\软件杯测试图片`。
3. 首次烟测图片：`D:\桌面\软件杯测试图片\BHIBGIFHFFGBA-mZwPOX6MrF.png`，内容为清晰的灵山大佛地标图。
4. 已执行 1 次真实百炼 Qwen 图片识别调用。
5. 烟测未通过：`ok=false`，模型 `qwen3.7-plus`，错误类型 `ReadTimeout`，耗时约 `22692.21ms`。
6. 降级链路生效，未把图片模型失败结果当作景区事实。
7. 已修复烟测脚本误判问题：fallback retrieval_query 不再被标记为成功。
8. 验证结果：B3 专项测试 `7 passed`，后端完整回归 `66 passed`，编译检查通过。
9. 下一步需要用户确认：是否将视觉超时调大后对同一张图片再重试 1 次，或先回百炼控制台核对更合适的视觉模型名。

## 阶段 B3.4 计划（2026-06-17）

1. 执行计划：`docs/2026-06-17-stage-b3-qwen-api-diagnostics-plan.md`。
2. 目标是先诊断 Qwen API Key、Base URL 和模型名是否可用，不直接重试图片识别。
3. 新增受控脚本 `eval/scripts/qwen_api_diagnostics.py`，必须显式传入 `--allow-network` 才会联网。
4. 诊断内容包括 `GET /models` 和 `max_tokens=1` 的最小 `POST /chat/completions`。
5. 诊断报告输出到 `eval/reports/qwen_api_diagnostics.json`，不输出完整 API Key。

## 阶段 B3.4 结果（2026-06-17）

1. 诊断报告：`docs/2026-06-17-stage-b3-qwen-api-diagnostics-report.md`。
2. 已执行 1 次低成本 Qwen API 诊断，没有发送图片。
3. `GET /models` 成功：`status_code=200`，模型列表包含 `qwen3.7-plus`。
4. `POST /chat/completions` 最小文本请求成功：`status_code=200`，返回 `OK`。
5. 本次诊断产生 usage：`prompt_tokens=13`、`completion_tokens=34`、`total_tokens=47`。
6. 结论：百炼 Base URL、API Key 和 `qwen3.7-plus` 模型名可用；B3.3 图片失败更可能是图片请求超时或视觉输入路径问题。
7. 下一步建议进入 B3.5：先调大视觉超时，对同一张图片只重试 1 次；若仍失败，再核对百炼视觉模型名或图片输入格式。

## 阶段 B3.5 结果（2026-06-17）

1. 执行计划：`docs/2026-06-17-stage-b3-qwen-vision-timeout-retry-plan.md`。
2. 实施报告：`docs/2026-06-17-stage-b3-qwen-vision-timeout-retry-report.md`。
3. 本轮未永久修改 `.env`，只临时覆盖 `VISION_READ_TIMEOUT_SECONDS=60` 和 `VISION_TOTAL_TIMEOUT_SECONDS=90`。
4. 对同一张灵山大佛图片执行 1 次真实 Qwen 图片识别重试。
5. 重试成功：`ok=true`，模型 `qwen3.7-plus`，耗时约 `20686.45ms`，置信度 `0.95`。
6. Qwen 返回候选景点：`灵山大佛`、`灵山胜境`、`祥符禅寺`、`无锡灵山景区`。
7. 视觉结果已生成 `retrieval_query`，但仍只作为 RAG 检索线索，不作为景区事实来源。
8. 验证结果：B3 专项测试 `7 passed`，编译检查通过。
9. 下一步建议进入 B3.6：将图片识别 `retrieval_query` 接入后端 RAG 问答闭环，确保最终答案引用官方资料 `[证据N]`。

## 阶段 B3.6 计划（2026-06-17）

1. 执行计划：`docs/2026-06-17-stage-b3-vision-rag-closed-loop-plan.md`。
2. 目标是跑通 `图片 -> Qwen 识别 -> retrieval_query -> 官方资料 RAG -> 带证据回答`。
3. 新增受控脚本 `eval/scripts/vision_rag_smoke.py`，必须显式传入 `--image` 和 `--allow-network` 才会真实调用。
4. 脚本会调用 Qwen 图片识别和现有 QA Pipeline；最终答案必须包含 sources 和 `[证据N]`。
5. 本阶段不接前端、不保存原图、不让 Qwen 直接回答景区事实。

## 阶段 B3.6 结果（2026-06-17）

1. 实施报告：`docs/2026-06-17-stage-b3-vision-rag-closed-loop-report.md`。
2. 已新增 `eval/scripts/vision_rag_smoke.py`。
3. 已对灵山大佛图片执行 1 次真实闭环烟测。
4. 闭环成功：`overall_ok=true`、`vision_ok=true`、`qa_ok=true`。
5. Qwen 识别候选景点：`无锡灵山大佛`、`灵山胜境`、`祥符禅寺`，置信度 `0.95`。
6. QA Pipeline 返回官方资料来源和 `[证据1]`。
7. 最终回答命中 `灵山胜境 景点结构化数据集.docx - 灵山胜境 / 灵山大佛`。
8. 本轮 QA 命中 FAQ/快速证据路径，没有触发 DeepSeek 生成，但已完成图片识别线索到官方资料证据回答的闭环。
9. 验证结果：后端完整回归 `66 passed`，编译检查通过。
10. 下一步建议接前端图片上传入口，或单独做“图片识别 + DeepSeek 生成式讲解”路径烟测。

## 阶段 B3.7 结果（2026-06-17）

1. 执行计划：`docs/2026-06-17-stage-b3-frontend-vision-upload-plan.md`。
2. 实施报告：`docs/2026-06-17-stage-b3-frontend-vision-upload-report.md`。
3. 已新增 `frontend/src/api/vision.js`，调用 `POST /api/vision/analyze`，并为图片识别设置 `120000ms` 前端超时。
4. 已在游客端聊天页增加“拍照识景”区域，支持图片选择、预览、识别、结果展示和清除。
5. 前端展示候选景点、视觉标签、置信度、Provider 与 `retrieval_query`。
6. 已新增“一键根据图片线索提问”，将识别线索送入现有聊天/RAG 流。
7. 已将后端视觉默认超时调整为 B3.5 验证成功的 `60s/90s`，并更新 `.env.example`。
8. 本轮没有主动上传真实图片调用 Qwen，没有消耗图片识别额度。
9. 验证结果：前端生产构建通过，后端完整回归 `66 passed`，编译检查通过。
10. 浏览器自动化检查因当前会话未暴露 `node_repl js` 工具未执行；后续建议本地启动前后端做一次人工端到端验收。

## 阶段 B3.8 运行结果（2026-06-17）

1. 执行计划：`docs/2026-06-17-stage-b3-frontend-e2e-manual-acceptance-plan.md`。
2. 运行报告：`docs/2026-06-17-stage-b3-frontend-e2e-manual-acceptance-run-report.md`。
3. 后端服务已启动：`http://127.0.0.1:8000`。
4. 后端健康检查通过：`GET /health -> 200`。
5. 前端服务已启动：`http://127.0.0.1:5173/`。
6. 前端页面访问通过：`GET / -> 200`。
7. 本轮没有自动上传图片，也没有自动调用 Qwen。
8. 用户可在页面“拍照识景”区域手动选择图片并执行端到端验收。

## 阶段 B3.9 暂停点（2026-06-17）

1. 用户在本地页面发现“拍照识景”的“检索线索”区域显示内容像乱码。
2. 判断结果：不是前端编码乱码，而是把内部 RAG 检索串 `retrieval_query` 原样展示给游客；其中还混入 Qwen 空 OCR 数组 `[]` 和重复关键词。
3. 本轮计划文档：`docs/2026-06-17-stage-b3-vision-query-display-fix-plan.md`。
4. 已修复后端 `backend/app/services/vision/qwen.py`：`detected_text` 支持空数组、数组文本、空对象和 `null` 的归一化，避免 `[]` 进入检索串。
5. 已新增后端测试 `backend/app/tests/test_qwen_vision_service.py`，覆盖空 OCR 数组不污染 `as_retrieval_query()`。
6. 已修复前端 `frontend/src/views/tourist/ChatView.vue`：“检索线索”不再展示内部长串，改为展示去重后的游客可读标签。
7. “根据图片线索提问”按钮仍使用后端 `retrieval_query`，RAG 检索闭环未改变。
8. 验证结果：图片识别相关后端测试 `8 passed`；前端 `npm.cmd run build` 通过，只有既有 Rollup 注释和大 chunk 警告。
9. 本轮没有真实调用 Qwen，没有产生图片识别费用。
10. 明天继续建议：刷新前端页面后用同一张灵山大佛图人工复测展示；若显示清爽，再进入 B3 下一步“图片线索提问后的回答体验优化/证据展示优化”。

## 阶段 D1 浏览器语音识别结果（2026-06-19）

1. 执行计划：`docs/2026-06-19-stage-d1-browser-speech-recognition-plan.md`。
2. 实施报告：`docs/2026-06-19-stage-d1-browser-speech-recognition-report.md`。
3. 新增 `frontend/src/composables/useSpeechRecognition.js`，接入 Chrome Web Speech API。
4. 中文识别使用 `zh-CN`，支持临时结果、最终结果和分段文本累积。
5. 游客端语音文字实时进入问题输入框，识别结束后由游客确认并发送，不自动提交。
6. 增加聆听状态、权限拒绝、无语音、无麦克风和网络异常提示。
7. Web Speech 不支持时保留 MediaRecorder + 现有 ASR 接口降级，文本输入始终可用。
8. 本轮不修改后端、不新增依赖、不修改 SSE、数据库或公共 API。
9. 验证结果：语法检查通过；模拟正常识别和错误路径通过；前端生产构建通过。
10. 当前待办：在 Chrome 中允许麦克风，说“灵山大佛有多高”，完成人工真实识别验收。

## Dashboard 图表化升级结果（2026-06-19）

1. 执行计划：`docs/2026-06-19-dashboard-chart-upgrade-plan.md`。
2. 实施报告：`docs/2026-06-19-dashboard-chart-upgrade-report.md`。
3. 已在 D 盘前端项目安装 `echarts@6.1.0`。
4. 已将管理总览页升级为四张指标卡、知识资产环形图、近 7 天趋势柱状图和详细统计。
5. 指标卡、环形图和详细统计均使用现有后端真实数据。
6. 因后端暂无逐日趋势接口，柱状图明确标记为演示数据，不冒充真实运营统计。
7. 已增加加载、错误、空数据、重试、刷新时间、响应式布局和图表销毁。
8. Dashboard 改为路由级懒加载，ECharts 只在进入管理总览页时加载。
9. 验证结果：真实 endpoint 数据读取通过；开发路由 HTTP 200；前端生产构建通过。
10. 当前待办：人工打开 `/admin/dashboard` 做最终视觉检查；依赖审计告警另行评估，不在本轮强制修复。

## 数字人运行测试结果（2026-06-19）

1. 测试计划：`docs/2026-06-19-avatar-runtime-test-plan.md`。
2. 测试报告：`docs/2026-06-19-avatar-runtime-test-report.md`。
3. 前端生产构建通过，Cubism Core、Haru 模型、MOC、贴图、物理、姿态和表情资源全部 HTTP 200。
4. 模型口型参数 `ParamMouthOpenY` 与代码匹配，`f00/f01/f04` 表情 ID 存在。
5. `useAvatar` 的 idle、thinking、speaking、happy、apology 和回退状态模拟测试通过。
6. 后端 Pipeline 测试 `5 passed`，AvatarConfig 3 个预设的查询与切换在隔离数据库中通过。
7. 首要阻塞：`pixi-live2d-display@0.4.0` 基于 Pixi 6，项目使用 Pixi 7，运行时 DisplayObject 类检查不兼容。
8. 当前 TTS 仍是文本 base64 stub，不是可播放音频；口型只是 150ms 固定开合，不是真实同步。
9. 流式 RAG/LLM 路径的情感仍为 `neutral`；后台激活配置没有接到游客页，游客页固定使用 Haru。
10. 模型加载失败没有 SVG 降级，listening/thinking/currentViseme 也没有完整驱动 Live2D。
11. 当前结论：数字人骨架和资源准备完成，但尚不满足“真实语音、稳定渲染、自然口型与表情联动”的最终验收。

## Live2D 白屏修复结果（2026-06-19）

1. 修复计划：`docs/2026-06-19-live2d-white-screen-fix-plan.md`。
2. 修复报告：`docs/2026-06-19-live2d-white-screen-fix-report.md`。
3. 白屏根因是 `Live2DAvatar.vue` 导入 `pixi-live2d-display` 根包，触发未加载的 Cubism 2 Runtime 检查。
4. 已改为 `pixi-live2d-display/cubism4`，只注册项目实际使用的 Cubism 4。
5. 已将 `pixi.js` 从 7.4.3 统一为插件兼容的 6.5.10，DisplayObject 类兼容检查通过。
6. 已删除 Vite 旧缓存并强制重新预构建，新缓存只包含 Cubism 4 入口。
7. 已增加 Live2D 加载失败事件，游客页会自动降级到 SVG `AvatarDisplay`。
8. 模型加载成功后会补应用当前表情和说话状态。
9. 前端生产构建通过，构建产物与开发缓存中均不存在 Cubism 2 缺失错误。
10. 用户侧需要重启旧 5173 前端服务并 `Ctrl + Shift + R` 强刷，或直接测试修复版 `http://127.0.0.1:5174/`。

## Live2D 尺寸与定位修复结果（2026-06-19）

1. 修复计划：`docs/2026-06-19-live2d-size-fit-plan.md`。
2. 修复报告：`docs/2026-06-19-live2d-size-fit-report.md`。
3. 已移除固定 `scale=0.6`、底部锚点和固定模型坐标。
4. 模型现在根据实际宽高自动等比缩放并居中。
5. 桌面画布为 `180x220`，窄屏显示区域为 `140x172`。
6. 前端生产构建通过，修复版 5174 服务已下发新逻辑。
7. Cubism 4、Pixi 6.5.10 和 SVG 降级逻辑保持有效。

## 修复版前端 5174 CORS 结果（2026-06-19）

1. 执行计划：`docs/2026-06-19-cors-5174-fix-plan.md`。
2. 实施报告：`docs/2026-06-19-cors-5174-fix-report.md`。
3. 后端 CORS 白名单已加入 localhost/127.0.0.1 的 5174，同时保留 5173。
4. 后端完成模型预加载后健康检查返回 200。
5. 5173 与 5174 的四个 Origin 预检全部返回 200 和正确 Allow-Origin。
6. 修复版前端已可访问后端聊天接口，不再因端口白名单出现 `Failed to fetch`。
7. 自动验证后端进程未常驻；本地启动后需等待约 30–40 秒模型预加载完成。
