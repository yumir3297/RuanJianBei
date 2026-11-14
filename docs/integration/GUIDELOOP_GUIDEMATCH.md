# GuideLoop / GuideMatch 本地接入记录

## 范围与位置

本接入从 `aa83aed` 出发，选择性整理 GuideLoop 和 GuideMatch。用户已选择功能整合程度最高的本地比赛集成工作区作为主线；该工作区还有其他未提交的比赛功能。来源为本地 GuideLoop 训练交接包及比赛集成工作区。

- 管理端：`frontend/src/views/admin/BlindSpotManage.vue` 中的 `GuideLoopPilotPanel.vue`，经 `frontend/src/api/guideLoop*.js` 和管理员认证接口维护观察、草稿、审核、发布、复测及确认。管理员发布须绑定当前 K01 知识版本并人工复核来源。
- 游客端：原聊天入口 `backend/app/api/chat.py`、`backend/app/services/qa/pipeline.py`；服务端按景点知识范围选择 GuideLoop 候选，并检查当前发布版本、审核、复测、关闭状态及有效期。游客不能提交管理复测上下文；撤回或知识下架后旧答案不可用。
- GuideMatch：`backend/app/services/qa/guidematch_gate.py` 为非精确 FAQ 和 GuideLoop 相近别名提供复用判断；模型不可用时不复用非精确候选。可识别的景点、意图及明确日期词冲突由规则保守拦截；结构化日期尚未贯通。
- 数据与迁移：`backend/app/models/guide_loop.py`、`repositories/guide_loop.py`、`services/guide_loop/` 和 Alembic GuideLoop 迁移链。管理接口只暴露于管理站网关策略。

## 本机运行

模型不进入 Git。从可信交接包执行 `python scripts/install_guidematch_model.py <交接包>/models/guidematch_final`，脚本校验 8 个文件后安装到 `.cache/guidematch/seed13`，已有目录不会覆盖。权重 SHA-256：`c999999e8f78149bdfdbb9830a4590b43046c0e47e79c05a363cf2c0a0d0842e`。训练代码和冻结数据在 `training_packages/guidematch_windows_training_bundle_v1/`。

本机演示使用 `APP_ENV=test` 或 `development`、`GUIDE_LOOP_PILOT_ENABLED=true`、`GUIDE_LOOP_VISITOR_ENABLED=true`、`GUIDEMATCH_ENABLED=true`、`GUIDEMATCH_DEVICE=cpu`、`GUIDEMATCH_MODEL_DIR=<模型目录>`；管理端开发服务器另需 `VITE_GUIDE_LOOP_PILOT=1`。这些功能默认关闭且仅限开发和测试。管理复测存在景点特定模拟规则，游客路径不执行这些规则。

本次浏览器验证使用临时 Python 3.14.7 环境、PyTorch 2.15.0 和 transformers 4.57.3，并非仓库的完整锁定环境。仓库依赖中的 `torch==2.12.0+cpu` 不能直接作为 macOS 安装说明；迁移到另一台机器时须按目标平台安装兼容版本并重新验证。模型配置和 tokenizer 从本地目录加载，不依赖运行时下载。

## 验证与边界

2026-11-14：隔离 SQLite / Chroma、本机 CPU 模型、stub LLM/TTS、双 Vite 与 Chrome 下，管理端绑定 K01、审核发布、复测确认，游客页面提交相近问句并收到 GuideLoop SSE 回答；知识下架后旧答案不再返回。为避免双 Vite 并行时依赖优化缓存互相干扰，按应用隔离缓存目录。测试使用合成资料，不能在真实业务库运行。

复现入口为 `frontend/tests/e2e/guide-loop-binding-smoke.mjs`。先启动使用全新隔离数据库与存储的后端（端口 8000），并按上述开关启动管理端 5174 和游客端 5173；从 `frontend` 目录设置 `DEMO_SYNTHETIC_CONFIRM=1`、隔离环境的 `DEMO_ADMIN_PASSWORD`，必要时设置 `PLAYWRIGHT_EXECUTABLE_PATH`，再执行 `node tests/e2e/guide-loop-binding-smoke.mjs`。脚本会创建和下架合成知识，运行前必须确认两个前端均连接该隔离后端。相关后端专项在 SQLite 环境下 55 项通过，前端测试 192 项通过；Alembic 当前只有 `c2a8e17f5b40` 一个 head。

分别在两个新建 SQLite 库中从 `91a0c5e2f347` 和 `6f0ecdb27c41` 升级到 `c2a8e17f5b40`，升级前插入的独立哨兵数据均保留。此检查不等于真实业务数据或 PostgreSQL 的迁移验收。

与远程的关系：本地比赛集成基线 `aa83aed` 与 `origin/master` 的 `6723f7d` 已分叉。对两个提交运行 Git 合并预检发现聊天、知识、前端和文档等多处冲突；尚未将比赛主线合并或推送到远程。

原集成工作区的真实 HTTP 开关对照中，开启模型后不再把大佛 FAQ 错用于灌浴问题，精确问题仍命中。同源合成开发集 135 条仅用于选型，不能代表真实游客泛化。日期结构化信息、真实景区资料、独立评测、模型许可、真实 PostgreSQL、多进程以及并发换版尚未完成验证。
