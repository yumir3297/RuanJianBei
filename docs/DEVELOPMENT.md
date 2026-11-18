# 开发与运行

## 环境

前端使用 Node.js `^20.19.0 || >=22.12.0`；后端使用 Python 3.13、PostgreSQL。模型和外部语音服务通过环境变量配置，配置项见 `backend/.env.example`，前端模板位于 `frontend/env/`。

## 后端

在 `backend/` 目录执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，配置数据库和模型服务
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Windows 使用 `.venv\Scripts\python.exe` 代替 `.venv/bin/python`。行程提案使用独立 worker，在另一个终端、`backend/` 目录启动：

```sh
.venv/bin/python -m app.services.tool_execution.worker
```

## 前端

在 `frontend/` 目录执行：

```sh
npm ci
npm run dev:tourist
# 在另一个终端启动管理端
npm run dev:admin
```

执行 `npm run build` 可分别构建游客端和管理端。生产部署、数据库迁移和站点配置见 [服务器运行指南](deployment/RUNTIME.md)。
