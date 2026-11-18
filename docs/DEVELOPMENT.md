# 开发与运行

## 环境

前端使用 Node.js `^20.19.0 || >=22.12.0`；后端使用 Python 3.13、PostgreSQL。需要 FFmpeg 处理非 WAV 语音。后端通过 `backend/.env.example` 配置数据库、模型和语音服务；游客端及管理端可分别参考 `frontend/env/tourist/.env.example` 和 `frontend/env/admin/.env.example`。

准备 PostgreSQL 数据库 `a5_scenic_guide`，并将 `DATABASE_URL` 改为本机连接信息。按实际服务填写 `LLM_API_KEY`、语音供应商凭据；启动前需要准备模型缓存。`ADMIN_PASSWORD` 和 `ADMIN_TOKEN_SECRET` 为本地示例，部署前必须替换为独立的强随机值。不要提交真实 `.env` 或密钥。

## 准备模型

项目启动时从本地缓存读取 embedding 与 reranker 模型。在安装后端依赖后，于 `backend/` 目录执行以下命令，将默认模型下载至 `../.cache/huggingface`：

```sh
.venv/bin/python -c 'from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer("BAAI/bge-small-zh-v1.5", cache_folder="../.cache/huggingface"); CrossEncoder("BAAI/bge-reranker-base", cache_folder="../.cache/huggingface")'
```

Windows PowerShell 使用 `.\.venv\Scripts\python.exe` 代替 `.venv/bin/python`。若在 `.env` 修改模型名称或 `MODEL_CACHE_DIR`，准备相应模型和目录。

## 后端

在 `backend/` 目录执行：

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，指向本项目新建的数据库，按上节准备模型缓存
.venv/bin/python import_official_data.py
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell 可执行 `python -m venv .venv`、`.\.venv\Scripts\python.exe -m pip install -r requirements.txt`、`Copy-Item .env.example .env`，编辑配置并准备模型后，首次运行先执行 `.\.venv\Scripts\python.exe import_official_data.py`，再执行 `.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000`。

首次导入会迁移目标数据库，并同步 `data/processed/` 中的景区知识、FAQ 和路线资料。启动两端后，使用配置的管理员密码登录管理端，在知识管理中核对草稿，选中相应条目并发布。游客端检索使用已发布的知识版本。

开发配置默认启动时迁移并初始化数据库。生产环境应先备份，再按[服务器运行指南](deployment/RUNTIME.md)执行显式迁移。行程提案使用独立 worker，在另一个终端、`backend/` 目录启动：

```sh
.venv/bin/python -m app.services.tool_execution.worker
```

API 启动后可访问 `http://127.0.0.1:8000/health` 检查进程，访问 `http://127.0.0.1:8000/ready` 检查依赖与配置状态。

Windows worker 命令为 `.\.venv\Scripts\python.exe -m app.services.tool_execution.worker`。

## 前端

在 `frontend/` 目录执行：

```sh
npm ci
npm run dev:tourist
# 在另一个终端启动管理端
npm run dev:admin
```

前端开发服务器代理 `/api` 和 `/ui-assets` 到 `127.0.0.1:8000`。默认同源 API 可不填写前端环境变量。Vite 从 `frontend/` 根目录读取 `.env.local`，可参考 `frontend/env/` 的模板在该文件填写配置；管理端部署时可设置 `VITE_TOURIST_APP_URL` 指向游客端 HTTPS 地址。

执行 `npm run build` 可分别构建游客端和管理端。生产部署、数据库迁移和站点配置见 [服务器运行指南](deployment/RUNTIME.md)。
