# 真实供应商评测准备（2026-10-30）

## 当前状态

只检查了 `integration-work/v01` 的代码和静态数据；未读取环境变量值、密钥或 `.env`，未启动后端、访问真实数据库或调用供应商。真实模型质量、费用、网络、凭据和线上表现均未验证。

不付费基线：使用现有虚拟环境运行 `check_e2e_testset.py --testset eval/testset/e2e_qa_100.json --report /private/tmp/codex-eval-validation.json`，100 题、0 格式错误；分类分别为事实30、历史15、景点15、路线10、实用10、引导选择8、追问6、盲区6；94 题要求带证据回答，6 题要求拒答。`python -m pytest -q -p no:cacheprovider eval/tests`：9 passed。格式有效和 mock 测试通过不表示真实问答准确。

## 现有工具与边界

- `eval/scripts/run_e2e_chat_eval.py` 默认 dry-run，验证题集并写报告，不请求接口；显式 `--mode local-server` 或 `sampled-real` 且 `--allow-network` 才请求后端。后端即使在 localhost，也可能向真实模型或其他服务付费调用。`sampled-real` 默认取前 5 条，非随机或分层样本；`--limit` 同样取前 N 条。
- 每题发送 `text_only=true`，固定 session ID `b2-eval-{id}`，顺序运行；首题被标为 cold，实际不保证冷启动。它不测试 ASR/TTS、并发或数字人，重复运行可能命中缓存或旧会话。每 10 题暂停 2 秒，P95 不代表并发服务水平。
- 评分为字符串规则：要求事实/来源字词、`[证据` 标记及 `done` 事件，拒答依据固定关键词；不验证引用是否支持所述事实，可能误判同义表达、数字及拒答。报告包含完整答案、来源和错误信息，应按数据敏感度保存。需抽样人工核对证据一致性、事实时效与误拒/漏拒，并保留逐题结果；6 条拒答案例不足以可靠估计总体安全性。
- `evaluation/evaluate.py` 是另一套旧评测，会请求实际 `/api/chat/stream` 并在 evaluation 写入报告；其 README 的历史结果和所谓竞赛阈值未经本次验证，不应当作当前系统或官方赛题结论。两个 100 题集及打分方法不同，不能直接混合比较。
- `deepseek_smoke.py`、`qwen_vision_smoke.py`、`vision_rag_smoke.py`、`qwen_api_diagnostics.py`、`tts_diagnostics.py` 可能请求真实接口；TTS 诊断脚本会打印密钥前缀，不建议将其日志共享。默认报告路径可能覆盖已有报告，必须指定新的隔离输出路径；检查每个脚本参数及副作用后再运行。

## 配置名称（仅查源码）

`backend/app/core/config.py` 使用 Pydantic Settings，读取工作目录 `.env` 与环境变量；常用名称包括 `LLM_PROVIDER`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`LLM_TEMPERATURE`、`LLM_MAX_TOKENS` 和超时配置；视觉为 `VISION_PROVIDER`、`VISION_API_KEY`、`VISION_BASE_URL`、`VISION_MODEL`；语音为 `TTS_PROVIDER`、`TTS_API_KEY`、`TTS_BASE_URL`、`TTS_MODEL`、`TTS_VOICE`，火山引擎另有 `VOLCENGINE_TTS_API_KEY` 或 `VOLCENGINE_TTS_APP_ID` 与 `VOLCENGINE_TTS_ACCESS_KEY`。数据与隔离涉及 `DATABASE_URL`、`CHROMA_PERSIST_DIR`、`MODEL_CACHE_DIR`、`SITE_ID`、`ENABLE_SAMPLE_DATA`；天气等也有独立外部服务配置。变量存在与权限、模型可用性均未检查。切勿打印凭据或复制 `.env` 到报告。

## 建议执行流程

1. 确定测试景区、题集与知识版本；人工复核标准答案、来源与时效，记录题集哈希、代码版本、知识发布版本、模型标识和参数。准备隔离数据库、索引、缓存和 session，禁用不需要的真实供应商；不要使用或更改生产数据。检查启动过程可能迁移、初始化、预热或下载模型。
2. 明确供应商额度、成本上限和使用数据授权，运行专用隔离服务。先对每项模型做一条可控 smoke，验证模型实际被调用、可用性及输出，无需打印 key；记录调用次数、token、错误和计费。故障即停止，不无限重试。
3. 用各类别人工分层抽样的独立题集开展小批量运行；不要把脚本前 5 题称为代表性随机抽样。评测命令示例（仅在隔离服务及供应商已准备好后执行）：`python eval/scripts/run_e2e_chat_eval.py --testset <分层样本.json> --mode sampled-real --allow-network --endpoint http://127.0.0.1:8000/api/chat/stream --report <新的隔离报告路径>`。指定非生产地址并确认样本全部被运行；报告文件是写操作。
4. 检查每题命中层与供应商调用日志：FAQ/缓存命中不能归因于真实 LLM；分别汇报端到端和真实模型子集。根据结果再决定是否运行 100 题，重复实验记录冷/暖、缓存策略、批次和成本。对失败案例做人工判定，保留分母和不确定性；未经实测不声称语音、并发或设备性能。

无外部调用的复查命令应明确指定 `/private/tmp` 报告路径，避免覆盖仓库历史结果。实际评测前检查授权、数据及价格；本报告不批准或执行任何付费请求。
