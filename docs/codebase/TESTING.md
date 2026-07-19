# Testing Patterns

> 本次知识采集只盘点测试结构，没有执行完整测试、联网 smoke 或质量评估；当前通过率不可由静态扫描推断。

## Core Sections (Required)

### 1) Test Stack and Commands

- 后端与评测使用 pytest `8.4.1`。
- `cd backend; python -m pytest app/tests -q`：后端测试。
- `python -m pytest eval/tests -q`：E2E runner 的离线测试。
- `python evaluation/evaluate.py`：基于固定问题集生成问答质量报告。
- `cd frontend; npm run build`：目前唯一机器可执行的前端质量检查，不等同于测试。
- 联网 smoke 位于 `eval/scripts/`，依赖真实密钥和显式网络授权。

### 2) Test Layout

- `backend/app/tests/`：38 个 `test_*.py`，覆盖 API、pipeline、RAG、语音、情绪、洞察、引导选择、推荐和初始化。
- `eval/tests/`：3 个 `test_*.py`，验证 E2E runner、报告/指标等评测基础设施。
- `evaluation/`：独立问答评估脚本、数据与历史报告。
- 前端没有 `*.spec.*`/`*.test.*` 框架配置或测试依赖。

### 3) Test Scope Matrix

| 范围 | 状态 | 代表证据 |
|---|---|---|
| 纯函数/规则 | 有 | 情绪、引导选择、推荐、查询处理测试 |
| 问答 pipeline | 有 | dummy provider 验证分支、事件和降级 |
| API 契约 | 有 | Knowledge、Voice 等 TestClient 测试 |
| 外部 HTTP 适配 | 有 | HTTPX MockTransport、假响应 |
| 数据库/初始化 | 部分有 | 依赖覆盖、bootstrap 测试 |
| E2E 评测基础设施 | 有 | `eval/tests/` 与固定 100 问数据 |
| 真实云服务 | 独立 smoke | 默认测试不依赖真实网络 |
| 前端组件/交互 | 无自动化 | `[TODO]` |
| 性能/并发/慢网 | 有脚本或设计，缺少持续门禁 | `[TODO]` |

### 4) Mocking and Isolation Strategy

- 通过 dummy LLM/ASR/TTS/retriever 和内存事件验证编排，不消耗外部配额。
- HTTP 集成用 HTTPX `MockTransport` 模拟状态码、SSE 和错误。
- FastAPI 通过依赖覆盖隔离认证和数据库。
- 临时路径/测试数据库用于文件与持久化测试；真实联网验证与离线测试分离。
- 异步测试多使用 `asyncio.run`，仓库未依赖 pytest-asyncio。

### 5) Coverage and Quality Signals

- 现有测试覆盖后端核心路径，尤其 pipeline/provider 的分支和失败行为。
- `[TODO]` 未发现 coverage 配置、最低阈值或 CI；当前覆盖率和当前测试通过状态未知。
- `[TODO]` 前端缺少组件、store、SSE 解析、音频队列和数字人状态机测试，是最明显质量缺口。
- 评测报告可反映某次运行的问答质量，但不能替代回归测试，也不能证明当前代码结果未漂移。

### 6) Evidence

- `backend/requirements.txt`
- `backend/app/tests/`
- `backend/app/tests/test_pipeline.py`
- `backend/app/tests/test_llm_openai_compatible.py`
- `backend/app/tests/test_tts_streaming.py`
- `backend/app/tests/test_emotion.py`
- `eval/tests/`
- `eval/scripts/`
- `eval/data/e2e_fixed_100.json`
- `evaluation/evaluate.py`
- `frontend/package.json`

