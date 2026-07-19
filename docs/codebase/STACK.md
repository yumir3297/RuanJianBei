# Technology Stack

> 本文描述 2026-07-19 当前工作区中的实际实现。依赖版本以清单文件为准；运行时版本要求以项目 README 为准，尚未通过 CI 约束。

## Core Sections (Required)

### 1) Runtime Summary

| 层次 | 运行时/平台 | 仓库证据 | 说明 |
|---|---|---|---|
| Web 前端 | Node.js 20+、浏览器 ES Modules | `README.md`、`frontend/package.json`、团队确认（2026-07-19） | Vue 单页应用，由 Vite 开发和构建。Node.js 20+ 是正式要求，但 `package.json` 尚未设置 `engines`。 |
| API 后端 | Python 3.13+、ASGI | `README.md`、`backend/main.py`、团队确认（2026-07-19） | FastAPI 应用通过 Uvicorn 启动。Python 3.13+ 是正式要求，但尚未通过 `.python-version`/`pyproject.toml` 锁定。 |
| 主数据库 | PostgreSQL | `backend/.env.example`、`backend/app/db/session.py` | SQLAlchemy 2 异步引擎，驱动为 `asyncpg`，迁移由 Alembic 管理。 |
| 本地 AI 推理 | CPU/PyTorch、ONNX Runtime | `backend/requirements.txt` | 用于 BGE 向量/重排模型与可选的本地 SenseVoice ASR。 |
| 三维数字人 | WebGL | `frontend/src/components/ThreeAvatar.vue` | Three.js + `@pixiv/three-vrm` 加载 VRM，配合 GLB 动作、口型和表情。 |

### 2) Production Frameworks and Dependencies

前端核心依赖：

- Vue `3.5.18`、Vue Router `4.5.1`、Pinia `3.0.3`：页面、路由和会话状态。
- Element Plus `2.11.1`：后台和通用 UI；ECharts `6.1.0`：运营分析可视化。
- Axios `1.11.0`：常规 HTTP；聊天流式响应由浏览器 `fetch`/`ReadableStream` 直接消费。
- Marked `18.0.5` + DOMPurify `3.4.11`：Markdown 渲染及 XSS 清洗。
- Three `0.184.0` + `@pixiv/three-vrm` `3.5.4`：VRM 数字人、动作、表情与口型驱动。

后端核心依赖：

- FastAPI `0.116.1`、Uvicorn `0.35.0`、Pydantic `2.11.7`/Pydantic Settings `2.10.1`。
- SQLAlchemy `2.0.43`、Alembic `1.15.2`、asyncpg `0.30.0`、psycopg `3.2.6`。
- HTTPX `0.28.1`、WebSockets `16.0`：调用大模型、视觉、语音服务及流式 TTS。
- ChromaDB `1.5.9`、Sentence Transformers `5.5.1`、rank-bm25 `0.2.2`：混合检索、向量召回与重排。
- PyTorch `2.12.0` CPU、sherpa-onnx `1.13.4`：本地模型和离线 ASR。
- pytest `8.4.1`：后端与评测测试。

外部 AI/数据能力不是一个统一 SDK，而是由后端 provider 适配器接入：DeepSeek 兼容接口、阿里云百炼/通义 ASR、TTS、视觉、可选 Coze，以及当前为 mock 的实时景区数据源。具体启用状态见 `INTEGRATIONS.md`。

### 3) Development Toolchain

- 前端包管理：npm，锁文件为 `frontend/package-lock.json`。
- 前端构建：Vite `7.1.2`、`@vitejs/plugin-vue` `6.0.1`。
- 后端依赖：`pip install -r backend/requirements.txt`；仓库未提供 Poetry/PDM/uv 锁文件。
- 数据库迁移：`backend/alembic.ini` 和 `backend/alembic/`。
- 测试：pytest；独立质量评估入口位于 `evaluation/evaluate.py`。
- `[TODO]` 仓库未发现 ESLint、Prettier、Ruff、Black、mypy、覆盖率阈值、Docker 或 CI 配置，需补充可重复的质量门禁。

### 4) Key Commands

```powershell
# 后端（从 backend 目录）
python -m uvicorn main:app --host 127.0.0.1 --port 8000

# 前端（从 frontend 目录）
npm install
npm run dev
npm run build
npm run preview

# 后端测试（从 backend 目录）
python -m pytest app/tests -q

# 端到端评测测试（从仓库根目录）
python -m pytest eval/tests -q

# 问答质量评估（从仓库根目录）
python evaluation/evaluate.py
```

上述命令来自 README、脚本清单和测试布局；本次知识采集没有执行完整测试或联网评测，因此不代表当前全部通过。

### 5) Environment and Config

- 后端配置集中在 `backend/app/core/config.py`，由 Pydantic Settings 从 `backend/.env` 读取；示例见 `backend/.env.example`。
- 前端通过 `VITE_API_BASE_URL` 配置 API 根地址；开发态由 `frontend/vite.config.js` 将 `/api` 代理到 `127.0.0.1:8000`。
- 主要配置域包括数据库、管理员认证、CORS、模型路径、DeepSeek、视觉、ASR、TTS、Coze、实时数据和比赛模式。
- 大部分外部能力采用 provider 开关。比赛演示当前启用 DeepSeek LLM、百炼 TTS、百炼 ASR、Qwen Vision、OpenWeatherMap 和浏览器语音；实际运行配置为 `VISION_PROVIDER=qwen`、`VISION_MODEL=qwen3.7-plus`。实时数据 provider 仍为 `mock`，Coze 禁用。
- `[TODO]` 将正式运行时要求写入机器可读配置，例如 `package.json#engines` 与 `.python-version`，避免只依赖文档和团队约定。

### 6) Evidence

- `README.md`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/vite.config.js`
- `frontend/src/main.js`
- `frontend/src/components/ThreeAvatar.vue`
- `backend/requirements.txt`
- `backend/main.py`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/.env.example`
- `backend/.env`（仅核验非敏感的视觉 Provider 与模型选择项）
- `backend/alembic.ini`
- `evaluation/evaluate.py`
