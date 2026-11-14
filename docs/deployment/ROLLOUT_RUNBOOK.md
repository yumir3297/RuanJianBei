# 管理端/游客端拆分发布与回滚手册

状态：**操作模板，尚未在目标服务器执行**。真实域名、路径、镜像平台、数据库版本、维护窗口和恢复目标仍须填写 [SERVER_INVENTORY](SERVER_INVENTORY.md)。本文件不构成生产发布授权。

## 0. 发布前置条件

开始前必须满足：

- 当前源码在已审阅的干净提交上；记录完整 Git SHA。不能从包含未提交变更的工作树生成可发布包。
- 目标 OS/CPU、Docker Engine/Compose、NGINX/TLS入口、PostgreSQL版本、两个站点 origin、状态/备份目录及UID/GID已写入服务器清单。
- `deploy/runtime.env` 由部署账户在服务器侧维护，权限受限；真实密钥只从秘密管理器注入，不写本手册、命令行参数、release manifest 或 Git。
- `APP_STATE_ROOT`、游客/管理站点根、NGINX配置根和备份根均为服务器独立绝对路径，存储容量和所有权已核实。
- 前端 capability manifest 与候选后端 capability set 兼容；后端候选镜像 ID、OCI源码 SHA 标签、Alembic head一致。
- 已有 PostgreSQL 及 app state 的备份位置、负责人、可恢复副本和维护窗口已确认。真实恢复演练未通过前不放量。
- 本机/CI `npm --prefix frontend test`、两端构建与边界检查、后端相关测试、`python3 -m unittest discover -s scripts/tests -p 'test_*.py'`、地图/语法/diff 检查均有本次输出记录。

缺少任一条件时只准备候选包，不运行停机或迁移步骤。

本手册命令中的 `$TOURIST_WEB_ROOT`、`$ADMIN_WEB_ROOT`、release IDs 等须由非敏感部署配置提供；Compose `--env-file` 不会把变量导出到当前 shell。不要 `source deploy/runtime.env`，其中含凭据的运行配置不是 shell 脚本。

## 1. 目标机配置与服务预检

1. 填完 [SERVER_INVENTORY](SERVER_INVENTORY.md)，审核 origin、现存游客身份、数据库/schema、持久路径和容量；保留当前游客 origin，若必须变更则先单独批准身份迁移方案。
2. 部署账户将 `deploy/runtime.env.example` 复制成服务器私有 `deploy/runtime.env`，设置最终确认的 `SOURCE_SHA`、`APP_STATE_ROOT`、`TOURIST_WEB_ROOT`、`ADMIN_WEB_ROOT`、`NGINX_CONFIG_ROOT`、数据库 URL、端口和安全配置。不得将运行文件加进版本库。
3. 按真实 host 与生产上传限制渲染站点和 API 路由表：

   ```sh
   python3 scripts/render_api_policy.py --check
   python3 scripts/render_api_policy.py --render-nginx "$NGINX_CONFIG_ROOT" \
     --tourist-host "$TOURIST_HOST" --admin-host "$ADMIN_HOST" \
     --max-files "$KNOWLEDGE_IMPORT_MAX_FILES" \
     --max-file-bytes "$KNOWLEDGE_IMPORT_MAX_FILE_BYTES"
   ```

4. 在不启动/迁移/写业务数据库的前提下检查目标路径、UID/GID、磁盘、证书、服务端版本和 secrets 注入。
5. Compose 使用 `config --format json` 按命名 `api` service 读取候选镜像；部署主机必须使用支持该格式的 Docker Compose v2。先做配置解析，输出不得泄漏敏感值：

   ```sh
   docker compose --env-file deploy/runtime.env -f deploy/compose.yaml config --quiet
   ```

目标主机的 Docker Compose 版本未核实前，不执行停机发布。

## 2. 构建并暂存候选版本

在已审阅的干净提交上记录同一 `SOURCE_SHA`。构建游客与管理端并制作各自的不可变静态包：

```sh
SOURCE_SHA="$(git rev-parse HEAD)"
npm --prefix frontend test
npm --prefix frontend run build:tourist
npm --prefix frontend run build:admin
npm --prefix frontend run check:app-boundaries
npm --prefix frontend run check:build-boundaries
npm --prefix frontend run check:build-isolation
python3 scripts/package_frontend_release.py --app tourist \
  --release-id "$TOURIST_RELEASE_ID" --dist frontend/dist/tourist \
  --output "$RELEASES_DIR/tourist/$TOURIST_RELEASE_ID"
python3 scripts/package_frontend_release.py --app admin \
  --release-id "$ADMIN_RELEASE_ID" --dist frontend/dist/admin \
  --output "$RELEASES_DIR/admin/$ADMIN_RELEASE_ID"
```

按目标平台构建候选后端镜像；生成完整 wheel/hash 锁并确认同平台重建后，才能把其作为生产候选。当前 Dockerfile/requirements 尚不是完整 hash 锁证明：

```sh
docker compose --env-file deploy/runtime.env -f deploy/compose.yaml build api
docker image inspect --format '{{.Id}}' "scenic-guide-backend:$RELEASE_TAG"
```

使用实际 image ID、同提交 Alembic head 和经审阅的能力列表写入**新**候选 metadata 文件；确保 `SOURCE_SHA` 同时写入镜像 OCI revision 标签。候选 metadata 不覆盖 `current/backend-release.json`。后端部署脚本会再次核对镜像 ID 和源码标签。

## 3. 首次部署与后续后端升级

### 首次部署

1. 先完成已核实的静态产物构建和 manifest；将候选前端 manifest 路径传给后端脚本，作为兼容性检查输入，不代表已对外发布。
2. 复核目标数据库为空库/隔离副本或已有库升级方案；首发允许的维护时间、写入停用、W02 drain、备份位置均逐项确认。
3. 由秘密管理器向脚本进程注入数据库连接环境变量。此处不在 shell 历史或命令行写密码。
4. 在双人复核/维护窗口下调用 `deploy/scripts/deploy-backend.sh`，确认参数指向目标机的绝对路径、候选 metadata 和实际两个前端 manifest。脚本会：校验能力兼容→取得共享发布锁→构建并核对 API 镜像 ID/源码 SHA→停 gateway/API/W02→确认旧进程退出→备份 PostgreSQL 与 app state→显式迁移/初始化→迁移前后核验 schema head→API契约检查→启动 gateway 并执行 NGINX 语法检查→提升 backend current metadata。
5. 任一步失败时脚本保持 gateway/API/W02 停止状态以待人工诊断；**不自动 restore、不自动 downgrade、不自动继续放流量**。按失败阶段检查备份、数据库和服务状态。
6. backend metadata 成功提升后，分别发布游客和管理静态站点（第 4 节），再执行目标机最小 smoke 与全部 Must 验收。

### 后续后端升级

1. 用当前实际仍支持的游客/管理 release manifest 做兼容输入；不只检查新版本页面。
2. 做隔离数据库迁移/恢复演练、容量审阅和维护窗口批准。
3. 运行后端发布脚本；脚本生成快照和状态归档，但不替代完整 restore rehearsal。
4. 实际运行版本、schema head、能力集、backup IDs 和健康/契约证据写入 [RELEASE_MATRIX](RELEASE_MATRIX.md)。

## 4. 游客与管理静态站点独立发布

确认 current backend 能力后，每次只切一个站点；以部署账户运行并使用共同绝对 `DEPLOY_LOCK_FILE`：

```sh
deploy/scripts/publish-static.sh --app tourist \
  --web-root "$TOURIST_WEB_ROOT" \
  --backend-release "$CURRENT_BACKEND_RELEASE" \
  --release-dir "$RELEASES_DIR/tourist/$TOURIST_RELEASE_ID" \
  --lock-file "$DEPLOY_LOCK_FILE"

deploy/scripts/publish-static.sh --app admin \
  --web-root "$ADMIN_WEB_ROOT" \
  --backend-release "$CURRENT_BACKEND_RELEASE" \
  --release-dir "$RELEASES_DIR/admin/$ADMIN_RELEASE_ID" \
  --lock-file "$DEPLOY_LOCK_FILE"
```

每端切换后分别核验真实 HTTPS origin、登录与匿名权限、入口路由、深链、hash 资源、字体/模型/动作/worklet，以及缺失静态资源返回 404。静态发布不重启后端、不运行迁移、不改业务数据；有任何差异立即只回滚该站点。

## 5. 静态回滚与后端故障处理

游客端或管理端静态回滚：

```sh
deploy/scripts/rollback-static.sh --app tourist \
  --web-root "$TOURIST_WEB_ROOT" \
  --backend-release "$CURRENT_BACKEND_RELEASE" \
  --release-id "$KNOWN_GOOD_TOURIST_RELEASE_ID" \
  --lock-file "$DEPLOY_LOCK_FILE"
```

管理端回滚需将 app 和 release id 改为经验证的管理版本。回滚后核对另一端 current、API/worker 进程、数据库、上传/发布revision均未变化。脚本保留当前与目标 manifest 的非 HTML 资源，避免活跃旧页面懒加载失败。

后端失败不得通过降级镜像掩盖不兼容 schema。先保持入口关闭，核验已产生的快照和状态归档；把 `restore-state.sh` 恢复到全新 `restore-*` 目录后，在隔离 PostgreSQL 与隔离数据路径实际执行数据库恢复及一致性比对。该脚本本身**只校验和暂存归档，不执行 `pg_restore`，也不触碰线上数据库**。只有隔离恢复验证通过并完成批准的前滚/恢复决策后，才重新开放流量。

## 6. 验收、放量与交接

按 [FINAL_ACCEPTANCE](FINAL_ACCEPTANCE.md) 的 M1–M8 逐项记录通过/失败/未测、时间、版本、真实 URL、设备、命令/日志/截图证据和负责人。目标平台依赖锁、真实 PostgreSQL restore、双 origin、真实供应商、设备矩阵、批准的容量/SLO、备份保留/RPO/RTO均属 Must 条件；任一未测即暂缓放量。

通过后填写 [RELEASE_MATRIX](RELEASE_MATRIX.md)，归档备份地址与恢复报告，记录遗留设备范围、维护窗口和静态/后端回滚版本。不得将密钥、数据库转储或游客个人数据放入交接文档或 Git。
