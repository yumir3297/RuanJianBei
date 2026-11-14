# Linux 运行封装（候选）

本文件提供可复现的运行结构，服务器 OS/CPU、内存/磁盘、Docker、数据库、域名/TLS 仍由用户确认后才能冻结为生产配置。当前 Dockerfile 的 Python patch tag 和系统包安装方式是构建候选，**不是**平台 digest 锁或生产供应链证明；平台专用完整 wheel/hash 锁应在目标架构确认后生成。

## 进程职责

| 单元 | 职责 | 启动行为 |
|---|---|---|
| `gateway` | NGINX 静态服务与 `/api`、`/ui-assets` 代理 | 唯一发布宿主机 HTTP 端口；TLS/正式域名待目标拓扑 |
| `api` | FastAPI、知识导入/发布 K01 worker、聊天/ASR/TTS 请求 | `AUTO_MIGRATE_ON_STARTUP=false`、`BOOTSTRAP_ON_STARTUP=false`、`SERVE_FRONTEND=false` |
| `tool-worker` | W02 持久化工具任务 worker | 与 API 同镜像、同配置和持久数据卷 |
| `migrate` | 单次 Alembic upgrade | 仅 `docker compose run --rm migrate` 显式运行 |
| `initialize` | 补齐幂等 quick topics/avatar 基础行 | 仅显式运行；默认不写演示内容 |
| `postgres`（可选 override） | 隔离测试或单机试跑数据库 | 只由 `compose.postgres.yaml` 加入；已有数据库用外部 `DATABASE_URL` |

API 和 worker 共用 `APP_STATE_ROOT`（宿主机目录挂载）与 `model-cache` 持久卷，容器 UID/GID 为 `10001:10001`。`APP_STATE_ROOT` 下包含 Chroma、上传文件和公开展示资源/manifest；模型缓存可按容量策略重建，不打进状态备份。游客端与管理端静态站点分别从 `TOURIST_WEB_ROOT`、`ADMIN_WEB_ROOT` 只读挂载；每个根目录用 `releases/<release-id>` 保存不可变版本，`current` symlink 原子指向当前版本，`previous` 记录上一个版本。使用 `deploy/scripts/publish-static.sh`、`rollback-static.sh` 独立切换站点，不重启 API/worker，也不运行迁移；静态切换与后端发布/回滚由共同的绝对 `DEPLOY_LOCK_FILE` 互斥。`deploy-backend.sh` 在停止网关/API/W02 后生成 PostgreSQL 快照和状态归档，再运行同镜像迁移/初始化并启动；备份恢复脚本只恢复到新的 `restore-*` 暂存目录，不直接改数据库或覆盖线上目录。Compose 不会在 `up` 时自动迁移或初始化。

CASS 情境导览通过 `CASS_ENABLED` 控制，运行模板默认关闭；开启后新增游客端 `GET /api/guide/bootstrap` 与 `POST /api/guide/decision`，不写行程、不替代 V01 用户确认。`CASS_DEMO_ENABLED` 仅在本地/比赛演示需要模拟场景时开启，生产默认必须保持关闭。游客 release manifest 声明 `guide-context-v1` 后端能力要求。

## 本机静态配置检查

```sh
cp deploy/runtime.env.example deploy/runtime.env
# 编辑 deploy/runtime.env：填强随机管理员密码/token secret、数据库 URL 和供应商凭据。
mkdir -p var/nginx/generated var/www/tourist var/www/admin var/lib/scenic-guide
python scripts/render_api_policy.py --check
python scripts/render_api_policy.py --render-nginx var/nginx/generated \
  --tourist-host guide.example.org --admin-host admin.example.org \
  --max-files 1 --max-file-bytes 52428800
# runtime.env 中 NGINX_CONFIG_ROOT 应为 ../var/nginx/generated。
docker compose --env-file deploy/runtime.env -f deploy/compose.yaml config --quiet
```

真实服务器要把 `APP_STATE_ROOT`、`TOURIST_WEB_ROOT`、`ADMIN_WEB_ROOT`、`NGINX_CONFIG_ROOT` 改成该机独立绝对路径；由部署账户创建并设置目录所有权。API 容器以 UID/GID `10001:10001` 访问 app state，静态发布账户需要写各站点 `releases/` 目录。不要把生产路径放到仓库 checkout 或临时目录。

PostgreSQL 可选 override：

```sh
docker compose --env-file deploy/runtime.env \
  -f deploy/compose.yaml -f deploy/compose.postgres.yaml config --quiet
```

候选镜像构建上下文是仓库根目录：

```sh
SOURCE_SHA="$(git rev-parse HEAD)"
docker build --build-arg SOURCE_SHA="$SOURCE_SHA" \
  -f deploy/backend.Dockerfile -t scenic-guide-backend:candidate .
```

只有工作树干净时才用该提交 SHA 打包候选清单；Compose 发布前也要在 `deploy/runtime.env` 中设置同一 `SOURCE_SHA`，避免构建标签与release metadata不一致。

部署前须确认镜像平台和最终 digest；`requirements.txt` 含 Torch CPU index 且部分传递依赖没有版本/hash，当前 Dockerfile 不使用 `--require-hashes`。目标机确认后生成完整平台锁，验证安装清单后再替换候选安装层。

后端部署候选清单由 `scripts/package_backend_release.py` 写入新文件；先在已锁定的源码提交上构建镜像，再从 Docker 读取不可变 image ID，并从同一源码核实 Alembic schema head。构建必须把相同 SHA 作为 `SOURCE_SHA` build arg 写入 OCI `org.opencontainers.image.revision` 标签；Compose 通过 `deploy/runtime.env` 要求显式设置它。能力列表逐项对应接口契约，游客当前要求包括 `visitor-config-v1`、`chat-sse-v1`、`tourist-feedback-v1`、`guide-context-v1`，不可从健康状态推断。`deploy-backend.sh` 使用 Docker Compose v2 `config --format json` 从命名的 `api` service 读取镜像，不能依赖 `config --images` 输出顺序；停机前再次比对真实构建 image ID 和标签 SHA，并在迁移后比对实时 schema head和接口响应；完成后原子提升 current 元数据。

## 一次性数据库动作

先阻止新写入，停止旧 API/K01/W02 并确认进程退出，完成数据库和文件状态备份，再执行：

```sh
docker compose --env-file deploy/runtime.env -f deploy/compose.yaml run --rm migrate
docker compose --env-file deploy/runtime.env -f deploy/compose.yaml run --rm initialize
```

Compose 文件不会代替维护窗口、旧进程排空、数据库备份或恢复验证。`migrate` 与 `initialize` 都使用同一候选 API 镜像和环境；重复初始化只补缺失基础数据，不覆盖运营行。

启动前需在仓库根目录执行两个独立构建。在干净的源码提交上分别打包；清单记录源码 SHA、锁定的 Vite 版本、后端能力需求和全部静态文件 SHA256。

```sh
npm --prefix frontend run build:tourist
npm --prefix frontend run build:admin
python scripts/package_frontend_release.py --app tourist --release-id tourist-20261108a --dist frontend/dist/tourist --output var/releases/tourist/tourist-20261108a
python scripts/package_frontend_release.py --app admin --release-id admin-20261108a --dist frontend/dist/admin --output var/releases/admin/admin-20261108a
deploy/scripts/publish-static.sh --app tourist --web-root "$TOURIST_WEB_ROOT" --backend-release var/backend-release.json --release-dir var/releases/tourist/tourist-20261108a --lock-file "$DEPLOY_LOCK_FILE"
deploy/scripts/publish-static.sh --app admin --web-root "$ADMIN_WEB_ROOT" --backend-release var/backend-release.json --release-dir var/releases/admin/admin-20261108a --lock-file "$DEPLOY_LOCK_FILE"
```

回滚使用相同的 `--app`、`--web-root`、`--backend-release`、`--lock-file` 参数和 `--release-id`。网关从 `current` 目录提供静态页；发布/回滚会在当前目录保留旧新包仍需访问的非 HTML 文件。目标服务器根目录、域名、HTTPS、CSRF trusted origin 仍须按实际拓扑确认。

示例命令中的站点根、后端清单、lock 和 release 目录须从已确认的服务器清单配置到当前 shell；Compose `--env-file` 不会自动导出 shell 变量。

后端发布仅允许维护窗口操作；先确认 W02 队列已经排空，且 API/K01/W02 写服务可停。`deploy-backend.sh` 要求操作者显式传 `--confirm-maintenance-window --w02-drained`，停止容器后检查旧进程、生成 PostgreSQL dump 和 app-state 归档、再迁移/初始化；在 API/W02 启动前会用一次性CLI核对数据库schema head，启动后再核对一次并做公开/受保护接口契约检查，然后启动gateway并运行容器内 `nginx -t`。全部通过后才原子更新 `current/backend-release.json`。执行shell的环境必须由秘密管理器提供 `DATABASE_URL`（脚本不会从Compose env file取密码，也不会把密码作为pg_dump argv参数），不要通过命令行裸写密码。部署失败会停止gateway/API/W02，等待复核备份和迁移结果；不会自动对生产库restore。

```sh
deploy/scripts/deploy-backend.sh --confirm-maintenance-window --w02-drained \
  --compose-file deploy/compose.yaml --env-file deploy/runtime.env \
  --candidate-release /srv/scenic-guide/releases/backend-candidate.json \
  --current-backend-release /srv/scenic-guide/releases/current/backend-release.json \
  --frontend-release /srv/scenic-guide/web/tourist/current/release.json \
  --frontend-release /srv/scenic-guide/web/admin/current/release.json \
  --state-root /srv/scenic-guide/state --backup-dir /srv/scenic-guide/backups \
  --lock-file /srv/scenic-guide/run/deploy.lock
```

生产模板按 `KNOWLEDGE_IMPORT_MAX_FILES` 和 `KNOWLEDGE_IMPORT_MAX_FILE_BYTES` 计算 multipart 总预算。当前 runtime 示例为 1×50 MiB，网关预算为 55 MiB；开发默认 20×50 MiB 会渲染为 1009 MiB。修改服务端限额后，须用相同参数重新生成 NGINX 站点配置，不得只改 API 环境值：

```sh
python scripts/render_api_policy.py --check
python scripts/render_api_policy.py --render-nginx var/nginx/generated \
  --tourist-host guide.example.org --admin-host admin.example.org \
  --max-files 1 --max-file-bytes 52428800
```

## 状态端点

- `/health` 是进程活性检查；它不证明数据库 schema、知识内容或模型已可用。
- `/ready` 检查数据库与检索/供应商可用状态，可在空库或模型缺失时返回 503；不能把它当作进程重启策略。
- API 的 schema head 检查通过 CLI `python -m app.cli.deployment` 显式执行；API 启动不会自动修复 schema。

最终生产验收仍需目标 OS/架构、真实数据库副本、镜像 digest、容量峰值和真实 HTTPS 域名；此文件不代表已部署。
