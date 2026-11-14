# 本地比赛演示运行手册

目标是本机可重复演示，不代表生产部署或真实景区服务已通过。所有命令均从集成仓库执行；真实 key、数据库密码和模型缓存不写入文档。

## 1. 依赖与数据库

已验证的本轮环境：Node 26.7、Python 3.12、独立 Python venv、SQLite 测试迁移；前端依赖使用锁文件安装。推荐先准备 PostgreSQL，再用实际 `DATABASE_URL`；只有演示逻辑时可用 SQLite，但单 worker 和迁移差异需明确记录。

```sh
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# 编辑 .env：至少设置 DATABASE_URL；模型/服务商按演示条件配置
.venv/bin/python -m app.cli.deployment migrate
.venv/bin/python -m app.cli.deployment initialize
```

没有本地模型或真实供应商时，开发环境可用 stub；`/ready` 不代表真实模型、ASR、TTS 或视觉服务可用。训练包是独立资产，不作为启动依赖。纯合成知识目录联调可将 `EMBEDDING_MODEL_NAME` 显式设为 `simple-dev-embedder`，它是固定哈希向量，只能用于 development/test 的演示，不得当作真实语义模型结果。

## 2. 启动后端和 worker

```sh
cd backend
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
# 另一个终端；只有需要真实提案演示时启动
.venv/bin/python -m app.services.tool_execution.worker
```

先检查 `GET /health`；需要服务可用性时检查 `GET /ready`。行程提案 worker 不由 API 自动启动，未启动时提案可能停留在后台状态。

行程提案的 worker 在 `LLM_PROVIDER=stub` 时会返回模型未配置，不能用普通 stub 完成提案演示。`backend/scripts_local_demo_itinerary_provider.py` 是仅绑定本机、要求显式确认的合成服务原型；游客页面使用固定指令“演示：行程增加十分钟休息”。它不是 AI。使用该服务时，worker 必须设置 `LLM_PROVIDER=demo_synthetic`、`LLM_BASE_URL=http://127.0.0.1:18765/v1` 及非空的演示 key/model；该模式仅允许 development/test 和本机 HTTP，并在提案中保存模拟标记供游客界面显示。不要把合成服务配置为其他 provider，否则无法可靠标识。提案校验结果为 `unverified`。

后端隔离集成测试已覆盖同进程及独立 worker 执行、真实本机合成服务和确认保存。确认依赖知识状态记录，正常 Alembic 迁移负责建立；仅用 ORM 建表的临时库不等同于迁移后的演示库。2026-11-13 使用真实迁移的隔离 SQLite、本地 API、独立 worker、合成服务和 Chrome 通过新建、提案、确认及路线标识；真实模型和完整比赛流程仍需验收。

模拟标记保存在提案记录中；确认后新停留点和模拟时长的来源写入行程快照，路线编辑页显示提示。隔离后端测试覆盖历史版本恢复后保留来源；本机浏览器已验证新停留点提示，浏览器历史恢复仍需验收。新枚举值可能使旧版后端无法读取相关行程，回退前须处理数据兼容性。

### 隔离行程浏览器检查

本检查会创建游览和历史版本。只在全新临时目录运行，不连接现有数据库；先确认本机 8000、5173、18765 端口空闲。以下示例假定已经安装后端依赖和前端依赖、Chrome 可用，本地 embedding 路径按实际情况指定。终端一在仓库根目录运行：

```sh
export DEMO_REPO_DIR="$(pwd)"
export DEMO_PYTHON="$DEMO_REPO_DIR/backend/.venv/bin/python"
export DEMO_WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/itinerary-demo.XXXXXX")"
export DEMO_EMBEDDING_DIR='<本地 embedding 模型目录>'
cd "$DEMO_WORK_DIR"
env -i PATH="$PATH" PYTHONPATH="$DEMO_REPO_DIR/backend" \
  DATABASE_URL="sqlite+aiosqlite:///$DEMO_WORK_DIR/demo.sqlite" \
  APP_ENV=test SITE_ID=demo ENABLE_SAMPLE_DATA=false TTS_PROVIDER=stub LLM_PROVIDER=stub \
  ADMIN_TOKEN_SECRET=isolated-demo-secret HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  EMBEDDING_MODEL_NAME="$DEMO_EMBEDDING_DIR" RERANKER_MODEL_NAME="$DEMO_WORK_DIR/no-model" \
  CHROMA_PERSIST_DIR="$DEMO_WORK_DIR/chroma" KNOWLEDGE_UPLOAD_DIR="$DEMO_WORK_DIR/knowledge" \
  UI_ASSET_UPLOAD_DIR="$DEMO_WORK_DIR/ui" UI_ASSET_MANIFEST_PATH="$DEMO_WORK_DIR/display-assets.json" \
  "$DEMO_PYTHON" -m uvicorn main:app --host 127.0.0.1 --port 8000
```

如果依赖安装在其他虚拟环境，将 `DEMO_PYTHON` 改为该环境的 Python 绝对路径；各终端使用同一个路径。2026-11-13 使用已有独立虚拟环境和本地 embedding，按这些配置在新临时目录重跑通过；重排器使用降级实现。

在同一 shell 的新终端中重新设置上述四个 `DEMO_*` 变量（其中目录必须与终端一相同），分别启动合成服务和独立 worker：

```sh
cd "$DEMO_REPO_DIR/backend"
DEMO_SYNTHETIC_CONFIRM=1 "$DEMO_PYTHON" scripts_local_demo_itinerary_provider.py
```

```sh
cd "$DEMO_WORK_DIR"
env -i PATH="$PATH" PYTHONPATH="$DEMO_REPO_DIR/backend" \
  DATABASE_URL="sqlite+aiosqlite:///$DEMO_WORK_DIR/demo.sqlite" APP_ENV=test SITE_ID=demo \
  LLM_PROVIDER=demo_synthetic LLM_API_KEY=synthetic LLM_MODEL=synthetic \
  LLM_BASE_URL=http://127.0.0.1:18765/v1 ADMIN_TOKEN_SECRET=isolated-demo-secret \
  "$DEMO_PYTHON" -m app.services.tool_execution.worker --poll-seconds 0.2
```

另一个终端在 `frontend/` 启动 `npm run dev:tourist -- --host 127.0.0.1 --port 5173 --strictPort`。等待 API 启动完成后，在 `frontend/` 再运行：

```sh
DEMO_SYNTHETIC_CONFIRM=1 PLAYWRIGHT_EXECUTABLE_PATH='<Chrome 可执行文件>' \
  node tests/e2e/itinerary-real-service-smoke.mjs
```

成功时输出 `proposal, confirmation and route label PASS`。检查后停止四个服务；临时目录包含合成测试数据，可在确认路径后自行删除。缺失重排模型时使用降级重排，本检查不以此证明问答质量或 `/ready` 完整就绪。脚本固定访问本机端口，确认开关不能验证正在运行的数据库确实隔离，运行前须检查上述服务配置。

## 3. 启动双端

```sh
cd frontend
npm ci
npm run dev:tourist   # http://localhost:5173
npm run dev:admin     # http://localhost:5174
```

管理员登录后，在知识盲区页打开 GuideLoop 试验需要开发环境变量 `VITE_GUIDE_LOOP_PILOT=1`，并且后端 `GUIDE_LOOP_PILOT_ENABLED=true`、`APP_ENV=development|test`。它默认关闭。游客端不加载管理 token 或 GuideLoop 管理面板。

## 4. 推荐演示顺序

1. 管理端登录，打开知识导入/审核；若使用 GuideLoop，创建观察草稿、人工来源复核、发布并执行管理端复测。
2. 游客端进入统一舞台，打开地图，确认定位/模拟数据的性质；进行资料问答和 CASS 情境评估。
3. 运行 CASS 模拟天气/客流/预警；预警应先中断普通讲解，确认后按演示流程显式恢复。真实预警没有可靠解除证据时不会自动恢复。
4. 打开已缓存离线包后进入 `/offline.html`，验证页面和地图/求助资料的核验标记；本机 Chrome 模拟断网 E2E 已通过；真机与生产网关仍未验收。
5. 如需讲解回放，确认播放器报告完整音频完成；浏览器语音短片段、静默和中断不计为已听完。

## 5. 演示前门禁

```sh
cd frontend
npm test
npm run build
npm run check:app-boundaries
npm run check:build-boundaries
npm run check:build-isolation

cd ..
python3 scripts/check_repo_map.py
python3 scripts/render_api_policy.py --check
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
cd backend
.venv/bin/python -m pytest app/tests -q
```

本轮实际证据和未验收范围见 [总验收台账](ACCEPTANCE.md)。

## 一键本地比赛演示

在后端依赖已安装、Chrome 路径可用的机器上，可用统一入口创建临时 SQLite/Chroma，启动后端、知识 worker、行程 worker、合成 provider、游客端和管理端，并依次执行知识发布、行程提案、GuideLoop 与 CASS 检查：

```sh
DEMO_SYNTHETIC_CONFIRM=1 DEMO_ADMIN_PASSWORD='<本地演示密码>' \
DEMO_PYTHON="$PWD/backend/.venv/bin/python" \
PLAYWRIGHT_EXECUTABLE_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
./scripts/run_local_competition_demo.sh
```

脚本显式启用 GuideMatch 并以 CPU 预加载 `.cache/guidematch/seed13` 下的本地权重；可通过 `GUIDEMATCH_MODEL_DIR` 和 `GUIDEMATCH_DEVICE` 指定已准备的模型及设备。该目录被 Git 忽略，换机器需要从已核验的交接包恢复并安装兼容依赖。预加载失败会终止脚本。脚本通过后输出 `FULL LOCAL COMPETITION DEMO: PASS`，退出时自动清理临时目录和服务；普通游客问答会核对已发布 revision 的来源，离线检查会输出 `16/16 PASS`。2026-11-14 在本机临时 venv、SQLite、GuideMatch 权重、固定哈希演示向量和虚构资料上通过；实际 FAQ 差异另见 [GuideMatch 记录](GUIDEMATCH_TRAINING.md)。该入口使用 Playwright 模拟断网，不代表真实景区资料、真机或生产部署通过。

## 合成案例浏览器检查

仅在全新隔离演示数据库、已启用 CASS/GuideLoop 的本地服务上执行，测试会写入合成观察与版本并模拟来源确认，不用于真实运营资料。执行前保证没有同范围的现有 GuideLoop 版本；`DEMO_ADMIN_PASSWORD` 从本地环境提供。

```sh
cd frontend
DEMO_SYNTHETIC_CONFIRM=1 DEMO_ADMIN_PASSWORD='<本地演示密码>' \
PLAYWRIGHT_EXECUTABLE_PATH='<Chrome 可执行文件>' \
node tests/e2e/local-demo-smoke.mjs
```

2026-11-13 在隔离 SQLite 与 stub 环境通过同一交互流程；空库没有已发布景点，语义模型不可用，`/ready` 为 503，此结果不代表比赛演示全流程或真实知识来源已就绪。

## 合成知识发布与游客读取检查

在启用了 CASS、配置可用本地 embedding 和向量存储的隔离演示库上，可运行以下检查。它会新增并发布明确标注的虚构景点，勿用于真实业务库。

```sh
cd backend
DEMO_SYNTHETIC_CONFIRM=1 DEMO_ADMIN_PASSWORD='<本地演示密码>' \
.venv/bin/python scripts_local_demo_knowledge_smoke.py
```

检查草稿不进入游客目录、发布任务完成、目录含已发布修订、游客 SSE 来源含同一修订。需注意景点目录只纳入包含稳定 `attraction_id` 的已发布景点。2026-11-13 使用本地 BGE-small、SQLite、Chroma、stub LLM/TTS 和降级重排通过，未验证真实景区资料或真实供应商。

## 管理端到游客端分拆联调检查

下面的脚本把管理端发布、游客端目录读取和两个独立前端 origin 串在一次检查中。它只写入隔离演示库中的虚构景点；脚本输出中的 revision ID 是本次发布的唯一核对依据。

```sh
cd frontend
DEMO_SYNTHETIC_CONFIRM=1 DEMO_ADMIN_PASSWORD='<本地演示密码>' \
  DEMO_ADMIN_URL='http://127.0.0.1:5174' \
  DEMO_TOURIST_URL='http://127.0.0.1:5173' \
  PLAYWRIGHT_EXECUTABLE_PATH='<Chrome 可执行文件>' \
  node tests/e2e/knowledge-publish-tourist-smoke.mjs
```

通过条件是：草稿阶段游客目录没有该编号；发布任务成功；管理端 origin 和游客端自己的 origin 都读到相同的 `published_revision_id`；启用 CASS 时游客页面的景点选择器也出现该标题。2026-11-14 已在隔离 SQLite、双 Vite 和 Chrome 中通过。仍然是合成资料检查，不代表真实景区资料、真实模型或真机通过。
