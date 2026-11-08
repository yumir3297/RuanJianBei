# Linux 运行封装（候选）

本文件提供可复现的运行结构，服务器 OS/CPU、内存/磁盘、Docker、数据库、域名/TLS 仍由用户确认后才能冻结为生产配置。当前 Dockerfile 的 Python patch tag 和系统包安装方式是构建候选，**不是**平台 digest 锁或生产供应链证明；平台专用完整 wheel/hash 锁应在目标架构确认后生成。

## 进程职责

| 单元 | 职责 | 启动行为 |
|---|---|---|
| `gateway` | NGINX 静态服务与 `/api`、`/ui-assets` 代理 | 唯一发布宿主机 HTTP 端口；TLS/正式域名待 Task 5/目标拓扑 |
| `api` | FastAPI、知识导入/发布 K01 worker、聊天/ASR/TTS 请求 | `AUTO_MIGRATE_ON_STARTUP=false`、`BOOTSTRAP_ON_STARTUP=false`、`SERVE_FRONTEND=false` |
| `tool-worker` | W02 持久化工具任务 worker | 与 API 同镜像、同配置和持久数据卷 |
| `migrate` | 单次 Alembic upgrade | 仅 `docker compose run --rm migrate` 显式运行 |
| `initialize` | 补齐幂等 quick topics/avatar 基础行 | 仅显式运行；默认不写演示内容 |
| `postgres`（可选 override） | 隔离测试或单机试跑数据库 | 只由 `compose.postgres.yaml` 加入；已有数据库用外部 `DATABASE_URL` |

API 和 worker 共用 `app-state` 与 `model-cache` 持久卷，容器 UID/GID 为 `10001:10001`。绝对路径在 Compose environment 中声明。数据库和向量数据、上传文件、UI 资源 manifest/文件需要一致性备份；正式备份/恢复流程由 Task 5 补齐。Compose 不会在 `up` 时自动迁移或初始化。

## 本机静态配置检查

```sh
cp deploy/runtime.env.example deploy/runtime.env
# 编辑 deploy/runtime.env：填强随机管理员密码/token secret、数据库 URL 和供应商凭据。
docker compose --env-file deploy/runtime.env -f deploy/compose.yaml config --quiet
```

PostgreSQL 可选 override：

```sh
docker compose --env-file deploy/runtime.env \
  -f deploy/compose.yaml -f deploy/compose.postgres.yaml config --quiet
```

候选镜像构建上下文是仓库根目录：

```sh
docker build -f deploy/backend.Dockerfile -t scenic-guide-backend:candidate .
```

部署前须确认镜像平台和最终 digest；`requirements.txt` 含 Torch CPU index 且部分传递依赖没有版本/hash，当前 Dockerfile 不使用 `--require-hashes`。目标机确认后生成完整平台锁，验证安装清单后再替换候选安装层。

## 一次性数据库动作

先阻止新写入，停止旧 API/K01/W02 并确认进程退出，完成数据库和文件状态备份，再执行：

```sh
docker compose --env-file deploy/runtime.env -f deploy/compose.yaml run --rm migrate
docker compose --env-file deploy/runtime.env -f deploy/compose.yaml run --rm initialize
```

Compose 文件不会代替维护窗口、旧进程排空、数据库备份或恢复验证。`migrate` 与 `initialize` 都使用同一候选 API 镜像和环境；重复初始化只补缺失基础数据，不覆盖运营行。

启动前需在仓库根目录执行 `npm --prefix frontend run build`，生成 `frontend/dist/tourist` 与 `frontend/dist/admin`；NGINX 分别只读挂载这两个目录。当前 NGINX 文件仅供本地结构演练，正式域名、HTTPS、CSRF trusted origin、请求预算和 SSE 代理策略由 Task 5 按目标拓扑配置。

## 状态端点

- `/health` 是进程活性检查；它不证明数据库 schema、知识内容或模型已可用。
- `/ready` 检查数据库与检索/供应商可用状态，可在空库或模型缺失时返回 503；不能把它当作进程重启策略。
- API 的 schema head 检查通过 CLI `python -m app.cli.deployment` 显式执行；API 启动不会自动修复 schema。

最终生产验收仍需目标 OS/架构、真实数据库副本、镜像 digest、容量峰值和真实 HTTPS 域名；此文件不代表已部署。
