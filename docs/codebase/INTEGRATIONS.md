# External Integrations

> “代码支持”不代表“当前部署已启用”。以下状态综合代码、`.env.example` 与团队于 2026-07-19 确认的比赛演示配置；未读取真实密钥内容。

## Core Sections (Required)

### 1) Integration Inventory

| 集成 | 用途 | 实现 | 示例默认 |
|---|---|---|---|
| DeepSeek | 基于证据生成回答 | OpenAI-compatible HTTP/SSE | 演示已启用 |
| Qwen Vision | 拍照识景、文字/景点/视觉线索提取并辅助 RAG 检索 | DashScope 兼容 HTTP，`qwen3.7-plus` | 演示已启用 |
| 百炼 ASR | 演示语音识别 | 云端 HTTP/任务式接口 | 演示已启用 |
| Qwen/SenseVoice | 其他云端或本地 ASR 实现 | 原始音频、sherpa-onnx | 代码支持，非已确认主路径 |
| 百炼 CosyVoice | TTS、音色、字时间戳 | HTTP/WebSocket PCM | 演示已启用 |
| 浏览器 Web Speech | TTS 最终降级 | Browser API | 演示已启用，按浏览器能力 |
| Coze | 特定意图动态路由 | HTTP | 禁用 |
| 实时景区数据 | 天气/客流抽象 | Provider | `mock` |
| OpenWeatherMap | 前端天气 | 浏览器 HTTP | 演示已启用；代码内含 key，需限制/轮换 |
| VRM/GLB | 数字人模型与动作 | Three.js 静态资源 | 本地启用 |

### 2) Data Stores

- PostgreSQL 是主业务库，保存游客、会话、知识、FAQ、缓存、路线、反馈、行为摘要和知识盲区。
- ChromaDB 是本地持久化向量库；BGE embedding/reranker 与可选 SenseVoice 从本地模型目录加载。
- VRM、GLB、音频等由文件系统/静态目录提供。
- Paraformer 文件式 ASR 会把音频写入公开上传目录；当前未发现自动清理。
- FAQ 索引、模型与部分服务为进程内缓存，不跨实例共享。
- 团队数据策略：后台统计、反馈、画像与知识改进所需数据可以持久化；其他临时数据应在游客退出时删除。公开 ASR 音频的自动清理尚未落实。

### 3) Secrets and Credentials Handling

- 后端密钥预期位于 `backend/.env`，由 Pydantic Settings 读取；示例文件应仅保留占位符。
- 管理员认证使用 HMAC 时戳 token，不是 JWT。
- 高风险：`frontend/src/composables/useWeather.js` 硬编码 OpenWeatherMap key；应撤销/轮换并迁移到后端代理或设置域名/额度限制。
- 高风险：示例与配置存在默认管理员密码和签名 secret，不适合公网部署。
- `[TODO]` 未见密钥管理器、轮换流程、分环境策略或 secrets scanning。

### 4) Reliability and Failure Behavior

- provider 普遍设置超时；pipeline 通过 FAQ、缓存、本地模型、stub、HTTP TTS 或浏览器语音降级。
- LLM 与 TTS 并行，少量多次发送文本/音频，降低慢网和整段等待的首响延迟。
- 启动时迁移、引导数据并预加载检索模型；模型缺失可能使应用在运行期降级前就启动失败。
- `[TODO]` 未见统一指数退避、熔断、限流、幂等、SSE 断点恢复或跨实例会话策略。

### 5) Observability for Integrations

- 标准 logging 记录外部调用和错误；`/health`、`/ready` 提供存活与准备度检查。
- 管理端提供反馈、行为、情绪趋势、体验报告和知识盲区等业务指标。
- `[TODO]` 未见 OpenTelemetry、Prometheus、APM、集中日志或 provider SLO 告警；建议补充首 token、首音频、成功率、降级率和耗时指标。

### 6) Evidence

- `backend/.env.example`
- `backend/.env`（仅核验 `VISION_PROVIDER`、`VISION_BASE_URL`、`VISION_MODEL`）
- `backend/app/core/config.py`
- `backend/app/core/auth.py`
- `backend/app/db/session.py`
- `backend/app/api/voice.py`
- `backend/app/services/llm/`
- `backend/app/services/vision/`
- `backend/app/services/asr/`
- `backend/app/services/tts/`
- `backend/app/services/coze/`
- `backend/app/services/live_data/`
- `frontend/src/composables/useWeather.js`
