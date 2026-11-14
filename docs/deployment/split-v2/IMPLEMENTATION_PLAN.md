# 管理端、游客端与服务器部署拆分 Implementation Plan V2（实施跟踪）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking. 仅在用户选择时采用多代理实施，不默认并行改共享文件。

**Goal:** 在继续新增功能的同时，建立独立管理端/游客端、可复现服务器运行包、可独立发布回滚的静态站点，并保留既有导览和数据契约。

**Architecture:** 同仓两个Vue入口与独立产物，一个共享FastAPI进程及既有W02 worker。先在开发环境完成权限/配置与入口拆分，再准备单机运行和代理；真实语音/RAG/手机/目标数据库按FINAL-ACCEPTANCE-01集中验收。

**Tech Stack:** 现有Vue3/Pinia/Vite7、Three.js/VRM；Element Plus/ECharts限管理端；FastAPI0.116.1/Uvicorn0.35.0、SQLAlchemy/Alembic/PostgreSQL、Chroma CPU模型、pytest/node:test；推荐Linux+NGINX+Docker Compose首发。

**Spec:** [V2设计](DESIGN.md)。

**Assessment:** [本次复核与技术依据](ASSESSMENT.md)。

**Status:** 用户已授权按本计划开始实现；Task 0 已执行，Task 1–8 以各自测试和环境门槛为准。真实生产上线仍须单独授权。V2取代旧拆分计划的后续执行入口；旧审计保留历史用途。

## Global Constraints

- 基线工作树/Users/yumir/RuanJianBei-integration-ai-workbench，integration/ai-workbench-final@7f9f4433f85ef57feee0d1034d107dd118d5c93e，当前核实干净；执行前重新确认。
- 不修改sources、master、旧location/offline整分支；从确认集成提交创建隔离拆分工作树。
- 先完成公开配置/认证与双前端，再以拆分提交继续接线新功能；不等待全部功能新增结束。
- 一个API进程、一个现有W02 worker；不拆数据库、不新增Redis/K8s、不搬K01 worker、不直接扩多API实例。
- 不改SSE事件/取消上下文、录音WAV与图片raw body、游客Cookie/CSRF/owner、知识revision/epoch、行程CAS和幂等契约。
- 生产保留游客origin优先；已有身份且要换域名时另立迁移前置。管理员新域名重新登录，不传/复制token。
- 新配置可见时60,000ms刷新，图片预加载15,000ms，忙→闲立即应用，失败保留最近成功值。
- 前端发布不重启后端、不执行迁移、不覆盖数据；后端迁移由同版本一次性命令执行，首发允许维护窗口。
- 不因本次规划重跑真实模型/语音/手机/生产库；遵循FINAL-ACCEPTANCE-01。假供应商与静态检查不能代表实际验收。
- 部署只使用有效凭据，不带入最新工程交接中已标记暴露/待撤销的旧凭据；本轮不读取、复制或调用它们。
- Linux amd64、Python3.13 CPU、Compose为候选，不预先承诺锁依赖安装或机器容量。目标机条件不符时先修运行封装，不能偷偷替换业务契约。

## Review Focus

1. 未登录游客与登录过后台的浏览器得到同一有效配置，游客不读取管理员token（1/2）。
2. 配置写入/图片预加载/轮询与播报并发，不能默认值闪回、旧图片覆盖、换音色串音（1/2）。
3. 空库首次部署ready503仍可进入后台导入；重启不重复迁移、不注入演示数据（4/7）。
4. ASR210s客户端、180s供应商+转换、SSE心跳与代理读取间隔共同工作；多文件限额不能误套单文件阈值（5/7）。
5. 发布和回滚两个方向均保留活跃页面依赖的旧/新hash资源；数据不随静态版本回滚（5/8）。

## 执行顺序、暂停点与功能协作

| 阶段 | 任务 | 现在能否开始 | 完成门槛 |
|---|---|---|---|
| A 固定输入 | 0 | 可；当前在途语音修改已提交 | 核实新HEAD、基线、文件归属 |
| B 修边界 | 1–2 | A后 | 匿名配置正确、认证分离、刷新安全 |
| C 拆前端 | 3 | B后 | 两套可运行/构建、自包含产物 |
| D 准备服务器 | 4–5 | C后；缺服务器仍能写包和测试 | 迁移/初始化、依赖封装、代理/限额与发布工具 |
| E 继续功能 | 6 | C后即可；共享入口改动需先集成 | 新功能依照两端边界接线 |
| F 最终验收 | 7 | 目标机/域名/真实数据/设备可用时 | FINAL-ACCEPTANCE-01实际通过 |
| G 上线回滚 | 8 | F后 | 真实切换、回滚、交接有证据 |

Task 4–5与纯业务功能可以分批推进，但不默认多人同时修改main、router、ChatView、Vite和public；由同一集成者逐提交整合。用户已授权按计划继续实施；真实生产上线仍须单独授权。

### Task 0：确认本轮基线与部署输入

**Files:** 读取AGENTS、frontend/AGENTS、backend/AGENTS、REPO_MAP、HANDOFF、TASK_BOARD；新增docs/deployment/SPLIT_INPUTS.md。

**Interfaces:** 输入确认设计；输出base SHA、隔离工作树、当前功能接口、服务器参数占位和存量身份判定。

- [x] 执行git status --short --branch、git rev-parse HEAD、git worktree list --porcelain；确认当前 HEAD `aa83aedd47a7aeb931e105d5d70930e3b18fe268` 是计划基线 `7f9f4433f85ef57feee0d1034d107dd118d5c93e` 的后代；当前部署工具和文档有未提交改动，按清单逐项保留。
- [x] 基于已确认基线使用隔离工作树；发现当前及 CASS 工作树都有独立改动后，未覆盖或把未审阅的 CASS 改动直接搬入。
- [x] V2设计、技术评估、拆分输入和执行计划均在本工作树的 `docs/deployment/split-v2/` 与 `docs/deployment/` 下，可随交付审阅。
- [x] 记录服务器 OS/CPU/RAM/磁盘、容器/反代、域名/TLS、数据库、游客origin、模型及供应商连通性；未知项保留为上线输入，见 [SPLIT_INPUTS](../SPLIT_INPUTS.md)。
- [x] 当前路由索引为88条并有地图校验结果；新增 CASS bootstrap/decision 路由均归游客匿名策略。计划记录 Alembic 单 head `91a0c5e2f347`，仍需目标 PostgreSQL 副本复核。历史测试数只作历史记录。
- [ ] 输入文档/实现尚未提交；本沙箱对共享 worktree Git index 无写权限，未提交密钥或真实 `.env`。保留可审阅工作树，提交需在有 Git 元数据写权限的执行环境完成。

### Task 1：公开有效配置与可靠服务器读取

**Files:**

- Create backend/app/schemas/visitor_config.py、app/services/visitor_config.py、app/api/visitor_config.py。
- Modify backend/app/api/router.py、app/services/display_assets.py、docs/REPO_MAP.md。
- Test backend/app/tests/test_visitor_config_api.py、test_display_assets_atomic.py。

**Interfaces:**

- PublicAvatarConfig(model_key:Literal["monk","hanfu","modern"],voice_type:现有四种逻辑音色)。
- PublicVisitorConfig(avatar:PublicAvatarConfig,display:PublicDisplayAssets)。
- VisitorConfigService(session:AsyncSession,settings:Settings).read()->PublicVisitorConfig。
- GET /api/visitor-config，匿名可读、no-store；DisplayAssetService.get_assets(*,strict:bool=False)，新入口strict=True。

- [x] 写test_anonymous_reads_active_config_without_admin_token：匿名200包含后台激活预设/逻辑音色/公开展示；不含id/model_path/内部路径/密钥。
- [x] 写test_admin_operations_remain_protected：管理列表/激活/修改匿名401；不能通过放开admin router解决读取。
- [x] 写test_missing_and_legacy_avatar_mapping：无记录回退hanfu/gentle-female；无激活按最小id；支持旧音色映射，未知值安全回退。
- [x] 写test_manifest_atomic_replace与test_strict_read_does_not_return_false_defaults：隔离tmp_path内读者只见完整旧/新JSON；替换失败原文件不变且temp清理；已有损坏/无权限文件新接口503，首次不存在文件200默认。
- [x] backend/运行选定venv python -m pytest app/tests/test_visitor_config_api.py app/tests/test_display_assets_atomic.py -q，确认未实现失败。
- [x] 实现schema、service、router及同目录私有temp+os.replace；新入口不调用带权限的管理API handler；不顺带做跨机器或多写者事务。
- [x] 重跑新测试与test_default_hotline_verification.py；更新地图并执行python3 scripts/check_repo_map.py；提交兼容后端接口。

### Task 2：认证客户端与配置刷新分离

**Files:**

- Create frontend/src/api/{transport,adminHttp,adminInsights,visitorConfig}.js、src/utils/{adminAuthStorage,visitorConfigRefresh}.js、src/composables/useVisitorConfig.js。
- Modify src/api/http.js、admin.js、knowledge.js、knowledgeImports.js、knowledgePublications.js、insights.js；stores/auth.js；views/tourist/ChatView.vue；composables/useScenicBackground.js；相关views/admin页面。
- Test frontend/tests/{http-boundaries,admin-auth,visitor-config-refresh,visitor-config-integration}.test.mjs；修改publication-api-integration.test.mjs实际拦截新管理客户端。

**Interfaces:**

- createHttpClient(baseUrl:string):AxiosInstance，不处理权限。
- getAdminToken():string|null、setAdminToken(token:string):void、clearAdminToken():void；store与拦截器读同一响应式状态，支持内存降级。
- fetchVisitorConfig():Promise<PublicVisitorConfig>。
- createVisitorConfigRefresher({fetchConfig,clock,isVisible,isIdle,onApply})->{start,refresh,flushPending,setVisible,dispose}。
- useVisitorConfig({isIdle:()=>boolean})->{avatar,display,loading,refresh}。

- [x] 写tourist_never_reads_admin_token、admin_401_clears_store_and_memory、disabled_storage_keeps_current_login：即使已登录后台，游客Axios/SSE无管理Bearer；401立即失效且管理导航回登录。
- [x] 写visible_poll_and_hidden_pause、single_flight_and_dispose、busy_to_idle_flush_without_next_fetch：fake clock覆盖60s、隐藏/恢复、旧响应、Vue watch+nextTick立即应用。
- [x] 写same_config_does_not_reload_model、image_timeout_and_404_keep_last_good、late_onload_cannot_replace_new_background：图片URL解析/15s降级保留；忙时模型与音色不变，当前播放器所有权不变。
- [x] 补回归：当前背景图再次被选中时会使不同的待加载图失效，迟到的旧图不能覆盖最新配置；`background-assets.test.mjs` 覆盖 A→待加载 B→重新选择 A。
- [x] 运行四份新测试，确认缺失模块/行为失败；仅使用fake和Vite middlewareMode，不启动真实后端/供应商。
- [x] 实现transport/token与管理API迁移；游客http保留API_BASE_URL供SSE，游客反馈与adminInsights拆开，ChatView删除对api/admin依赖。
- [x] 实现刷新器及Vue watch接线；保留管理员invalidate兼容入口，移除游客对storage事件的跨域依赖。后台图集标明本机草稿、不清旧数据；语速/音量为本机预览。
- [x] 运行新测试及publication-api-integration、publication-recovery、sse-stream、audio-playback-session、chat-replay、speech-cancel；通过后提交。本任务不改当前heartbeat producer或210s ASR语义。

### Task 3：两个独立应用与发布产物

**Files:**

- Create frontend/apps/tourist/{index.html,main.js,App.vue,router.js}、apps/admin同名四文件。
- Create frontend/vite.shared.js、vite.tourist.config.js、vite.admin.config.js；env/tourist/.env.example、env/admin/.env.example。
- Create frontend/scripts/{prepare-public,check-app-boundaries,check-build-boundaries}.mjs。
- Modify frontend/package.json、vite.config.js（保留legacy）、.gitignore；游客端删除管理入口，管理端保留查看游客端链接。
- Test frontend/tests/{app-boundaries,public-assets,build-boundaries}.test.mjs。

**Interfaces:** dev默认游客，dev:tourist/dev:admin/build:tourist/build:admin；build依次构建；端口5173/5174且strictPort；产物dist/tourist、dist/admin，各含一个index入口及完整manifest/chunk。

- [x] 写tourist_graph_excludes_admin_auth_and_charts、admin_graph_keeps_preview_without_chat：遍历相对静态/动态imports，游客不可达管理员状态/API、ElementPlus/ECharts；后台可达ThreeAvatar，不可达游客ChatView/Router。
- [x] 写asset_allowlist、self_contained_manifest：两端排除tester，游客保留worklet，后台不含录音worklet；模型/动作和中文VRM正常；每个产物引用全部在本产物内存在。
- [x] 运行新测试确认当前单入口不满足，然后实现独立root/router/shell，保留现有src业务路径，不整体移动目录。
- [x] 游客保留旧/tourist工具重定向并移除管理入口；后台可访问/admin/dashboard，跨端查看只允许由管理端向游客端使用固定HTTPS/开发本机HTTP普通链接。复查发现游客端旧链接曾因源码改动残留在Vite哈希资源中，现已删除该链接与配置，并把每端outDir改为安全清理本端旧资源；回归测试覆盖此边界。
- [x] Vite7配置明确envDir、fs.allow、独立outDir，public白名单复制到每端独立staging；不复制真实.env，不通过缩小环境目录误漏必要公开配置。
- [x] package新增两个构建/开发/预览和临时legacy命令；单端构建不得清理另一个outDir。
- [x] 执行npm run build:tourist、npm run build:admin和边界脚本；重复只构建一端后另一端全量文件hash不变。检查模型、动作、图像与worklet存在性。
- [x] 浏览器手工冒烟：桌面内置浏览器确认游客入口加载、`/tourist/map` 重定向到 `?tool=map` 且地图工具可见、数字人模型和文字输入框可用；管理端跳转到未登录页面。并行启动两端时复现共享 Vite 优化缓存导致游客懒加载 504/白屏，隔离 cacheDir 并新增回归测试后复测恢复。本轮用临时 SQLite、仅本机测试管理员口令和 LLM/ASR/VISION/TTS stub 启动本地 API：管理端登录后数字人模型可见；游客端提交“连接测试：请介绍一个景点”后收到 API 无资料兜底回答。embedding 模型不可用且无已核验景区资料，因此只证明页面/API请求响应联通，不证明 RAG/真实问答、真实LLM、TTS/ASR、HTTPS、目标浏览器或服务器行为；未保存配置、未发起语音播放。

### Task 4：生产启动职责与可复现运行包

**Files:**

- Create backend/app/cli/{__init__,deployment}.py、backend/app/db/deployment.py；deploy/backend.Dockerfile、deploy/compose.yaml、deploy/compose.postgres.yaml、deploy/runtime.env.example、.dockerignore。
- Create deploy/locks/linux-amd64-py313.txt与deploy/backend-release.json（目标环境解析/构建时生成，不在本轮虚构锁内容）。
- Modify backend/main.py、app/core/config.py、app/db/bootstrap.py、backend/.env.example。
- Test backend/app/tests/{test_deployment_lifecycle,test_deployment_cli,test_frontend_mount_mode}.py。
- Create docs/deployment/RUNTIME.md。

**Interfaces:**

- AUTO_MIGRATE_ON_STARTUP、BOOTSTRAP_ON_STARTUP、SERVE_FRONTEND：兼容开发默认true，生产模板false。
- migrate_database(settings:Settings)->None，check_schema_head(settings:Settings)->None，initialize_database(settings:Settings,*,include_demo:bool=False)->None。
- python -m app.cli.deployment migrate|initialize；CLI不导入main，不启动API/模型/任务循环。
- Compose运行单元gateway/api/tool-worker/migrate/initialize；postgres只由可选override增加。API/worker/CLI使用同一镜像digest和环境。

- [x] 写production_restart_does_not_migrate_seed_or_add_demo：生产false标志不执行迁移/bootstrap；显式production initialize即使误传include_demo也只写基础种子；开发sample数据有独立断言。
- [x] 写unmigrated_schema_fails_without_upgrade、cli_has_no_app_startup_side_effects：schema不符直接错误，CLI导入不触发main/API启动；显式 `check-schema` 只读并输出核验后的当前单一head。
- [x] 写spa_mount_requires_root_index：关闭SERVE_FRONTEND或仅有双端目录时不挂根SPA，兼容旧根index的行为有独立断言。
- [x] 运行新增测试并抽离生命周期职责；生产只初始化quick topics/avatar，demo仅开发明确开启；K01留在API，W02单独运行。
- [x] 实现候选Linux运行镜像：固定Python基础版本，安装FFmpeg/ffprobe，非root UID/GID、确定工作目录；构建上下文排除敏感配置/上传/缓存/测试资料，不烘焙模型私有目录。
- [ ] 目标架构未定；linux-amd64/Python 3.13 的完整传递依赖hash锁、目标镜像digest与同平台重建还未生成/验证，必须待服务器架构确认后完成，不以候选 requirements 安装冒充生产锁。
- [x] 制定持久目录与UID/GID，API/W02私网只由gateway对外暴露；已有数据库可走外部URL，Compose没有强制覆盖；/health进程检查、/ready内容就绪用途有文档。Docker真实解析仍待安装环境。
- [x] 实现后端维护脚本：明确维护确认与W02 drained 输入；构建并校验镜像元数据后获取全局发布锁、停gateway/API/W02、检查进程退出、备份PostgreSQL与APP_STATE_ROOT、迁移/初始化、API/W02启动前后两次核对schema head，再做匿名/管理员边界契约检查、gateway `nginx -t` 后原子更新current backend-release。任一步失败会停止API/W02/gateway，不自动覆盖数据库。
- [x] 写migration_cannot_start_while_old_api_or_worker_is_running：隔离fake Docker/PostgreSQL执行验证停机/备份先于迁移；进程未退出或数据库备份失败则不迁移、不恢复gateway。静态发布脚本不调用后端维护命令。
- [x] 运行部署生命周期/SPA/startup/security/W02聚焦测试与后端全量 `app/tests`（本轮 727 passed、19 skipped）；生产自动迁移关闭时，lifespan 在模型和 worker 启动前只读校验 schema head。Compose YAML静态解析通过。当前无Docker CLI，`docker compose config --quiet`/镜像构建未执行；供应链锁和服务器恢复仍待目标机。运行封装已写入工作树。

### Task 5：代理、运行限制、独立发布与数据备份工具

**Files:**

- Create deploy/api-surface.json、deploy/nginx/{tourist.conf.template,admin.conf.template,common-api.conf}。
- Create scripts/render_api_policy.py、deploy/scripts/{publish-static,rollback-static,deploy-backend,backup-state,restore-state}.sh。
- Create scripts/check_release_compatibility.py、scripts/package_frontend_release.py、scripts/package_backend_release.py；deploy/scripts/{static_release.py,backup_restore.py,dump_postgres.py}；Test scripts/tests/{test_release_compatibility,test_release_assets,test_backup_restore,test_deploy_backend_order,test_backend_release_package}.py。
- Create backend/app/schemas/runtime_limits.py、frontend/src/api/adminRuntime.js；Modify backend/app/api/admin.py、frontend/src/views/admin/KnowledgeManage.vue及components/knowledge/ImportBatchPanel.vue、运行配置模板。
- Test backend/app/tests/test_admin_runtime_limits.py、frontend/tests/import-limits.test.mjs、scripts/tests/{test_api_surface,test_proxy_templates,test_release_assets}.py。

**Interfaces:**

- GET /api/admin/runtime-limits，管理员可读，返回knowledge_import:{max_files,max_file_bytes}与display_assets:{max_image_bytes}，不返回其他配置。
- 首发生产KNOWLEDGE_IMPORT_MAX_FILES=1，KNOWLEDGE_IMPORT_MAX_FILE_BYTES=52428800；开发默认批次数仍可保留20，UI以服务器实际返回值约束，不写死为所有环境都1。
- api-surface逐项{method,path,boundary,sites}，当前覆盖88条（含CASS游客端bootstrap/decision；以实现后的静态索引为准）；新增未分类接口拒绝发布。
- release.json包含源码SHA、应用名、构建工具、文件hash、所需后端能力；脚本只接收明确端名tourist|admin与release-id。
- 后端能力从已部署并核验的current/backend-release.json读取，字段image_digest/source_sha/schema_head/capabilities；前端required_backend_capabilities须为当前能力子集。后端升级验证所有仍支持前端的需求，不能只检查当前单一页面。

- [x] 写runtime_limits_requires_admin_and_matches_settings：匿名401，有token返回实际安全限额；测试自定义值，确认不暴露其他settings。UI限额获取失败时阻止上传并给重试，不猜默认大批量值。
- [x] 写multi_file_selection_matches_server_max与gateway_budget_includes_multipart：生产每批1×50MiB、网关55MiB；默认20环境渲染为1009MiB，按实际批量预算设置。
- [x] 写api_surface_complete_and_method_sensitive：insights统计GET只管理，feedback POST游客，W02 execution游客owner；88条路由全覆盖，新增未知路由导致清单检查失败。
- [x] 写missing_api_asset_is_not_html、sse_no_buffer、asr_timeout_budget：静态资源404、413 JSON；SSE关闭代理缓冲；proxy_read_timeout240s，客户端 ASR 210s、供应商180s+转换语义不变。NGINX 二进制未安装，真实 `nginx -t` 留待可用环境。
- [x] 写publish_and_rollback_preserve_both_active_asset_sets：临时目录A→B→A验证当前web root可解析新旧manifest的文件，拒绝资源同名异内容及跨端目录；以本次游客/管理构建产物实际打包并在隔离临时目录完成两端各自A→B→A，游客63个、管理130个manifest资源齐全，切换任一端时另一端current不变；再以本机短生命周期HTTP服务逐端验证A、B、回滚后的入口和引用JS/CSS均为200。演练使用临时兼容性metadata，不代表真实后端镜像或生产部署；真实NGINX、TLS、Host和目标机访问仍待验收。
- [x] 写static_release_never_changes_database_or_other_app：脚本只操作显式端站点目录，不调用docker/迁移；端名限制为tourist|admin、release-id阻止路径穿越。
- [x] 写publish_and_rollback_reject_missing_backend_capability、backend_upgrade_preserves_supported_frontends：严格要求完整image digest/source SHA/schema head/capabilities；publish/rollback及backend upgrade均验证所需能力，不从health推断。
- [x] 实现管理限额与UI、网关方法/路径策略和独立web release/current/previous目录。Host/HTTPS信任仍按目标拓扑配置，不放宽Origin/CSRF；/api不剥前缀。
- [x] 实现静态发布前完整校验与资源保留：发布与回滚都合并当前/目标版本manifest内的非HTML资源；资源文件同名异内容拒绝，HTML no-cache、缺失资源404，私有导入文件不加入静态包。
- [x] 修正部署发布执行路径：迁移后 schema 检查明确运行 Python CLI；未认证管理员探针使用多行有效 Python，并有脚本测试解析；发布目录/资源在严格 umask 下仍为 NGINX 可遍历、可读权限。
- [x] 实现check_release_compatibility并接入静态发布/回滚及后端部署前检查；静态发布/回滚与后端部署用同一绝对lock互斥，后端脚本只在明确维护窗口停止服务、备份、迁移和初始化，并在停机前核验镜像ID与OCI源码SHA标签、迁移后核验schema head/API契约/NGINX语法，全部通过后才原子更新current backend-release。
- [x] 实现显式备份/恢复工具：停写后PostgreSQL快照+APP_STATE_ROOT归档；校验内容hash；恢复只到新`restore-*`暂存目录，不覆盖生产目录。目标机的真实还原演练仍未完成。
- [x] 跑新增自动测试、全scripts unittest（46项通过）、前端测试（214项通过）与后端全量测试（727 passed、19 skipped）、bash语法、Compose YAML解析、地图与diff检查。2026-11-09在当前工作树重新运行后，前端214项、后端727 passed/19 skipped/9 warnings、scripts 46项通过；实际打包/发布/回滚HTTP演练详见上项。当前环境无Docker/NGINX，`docker compose config`与真实`nginx -t`未执行；fake工具演练覆盖锁冲突、API镜像解析、迁移前失败、源码标签、schema/API/NGINX gate。未操作真实服务。工具已写入工作树。

### Task 6：在新边界上继续功能新增并完成开发交付

**Files:** docs/development/FRONTEND_BOUNDARIES.md、docs/REPO_MAP.md、ARCHITECTURE.md、DEVELOPMENT.md、COMPATIBILITY.md、frontend/AGENTS.md、README；按实际后续功能另开小任务。

**Interfaces:** 输出双端开发入口、共享模块归属、CASS/offline接入规则和开发验收记录；后续功能必须基于Task3或之后集成提交。

- [x] 文档和边界测试明确游客入口、管理入口、身份客户端、public 资源、两个 router/Vite 配置的归属；共享入口按单一集成者顺序合入，不建立长期互相覆盖分支。见 `docs/development/FRONTEND_BOUNDARIES.md`。
- [x] 按既有 CASS 计划集成 `src/guide`、`useGuideContext`、后端确定性策略/API和独立组件；保留单一 ChatView、播放器、定位和 V01/W02 提案流程，只移植经审阅的功能差异，不复制整个旧 ChatView，也不修改 CASS 源工作树。CASS 默认关闭，demo 单独开关默认关闭；不代表真实安全数据、后台接警或离线资源已接入。
- [x] 当前未引入 service worker；开发边界明确未来离线功能只归游客端，并要求未来管理 API/身份/聊天不得缓存。本轮没有虚报离线验收。
- [x] 开发验证：前端 `npm test` 当前 214 项通过，包含游客端不暴露管理入口及双 Vite cacheDir、背景图竞态和 CASS 延迟响应回归；`npm run build`、`check:app-boundaries`、`check:build-boundaries`、`check:build-isolation` 均通过；确认单端重建清除自身旧哈希包、不触碰另一端产物。游客构建产物中未发现管理入口文案/链接或`/admin`路由。Vite preview 本机HTTP：游客端与管理端入口、引用JS/CSS均返回200。构建仍报告多个 >500 kB chunk，需后续按性能目标评估拆包。后端全量 `app/tests` 为 727 passed、19 skipped；生产 lifespan 的不匹配 schema 检查已在模型启动前验证；本机浏览器和 stub 联调范围见 Task 3，真实RAG/供应商、语音、位置与目标机仍待验。
- [x] 根目录 `check_repo_map.py`、scripts unittest（46项）、Compose YAML parse、shell `bash -n`、`git diff --check` 通过；未安装临时 overlay。
- [x] 开发文档现记录两个入口、K01/W02、生产显式迁移、静态版本目录及身份/origin边界；最终服务器验收继续按 Task 7/FINAL-ACCEPTANCE-01 执行。
- [x] 可评审代码与交接文档已准备在当前 worktree；未自动合并master或部署。当前沙箱对共享 Git 元数据只读，不能写 Git index/提交。

### Task 7：目标服务器统一最终验收

**Files:** docs/deployment/FINAL_ACCEPTANCE.md、docs/deployment/SERVER_INVENTORY.md，更新既有FINAL-ACCEPTANCE-01实际结果。

**Interfaces:** 输入真实服务器/域名/TLS/已核验资料和设备；输出精确版本/环境、逐项证据、故障恢复和放量结论。

- [x] 创建 [SERVER_INVENTORY](../SERVER_INVENTORY.md) 与 [FINAL_ACCEPTANCE](../FINAL_ACCEPTANCE.md)，明确输入字段、候选阈值、Must通过规则和证据位置；服务器/设备输入仍未定，因此以下真实验收尚未开始。
- [x] 在隔离临时 PostgreSQL 17.11 新集群上实跑生产显式 `migrate` 到 `91a0c5e2f347`，并重复 `initialize --include-demo`；只读核对基础种子稳定为 avatar_configs=3、quick_topics=8，KnowledgeEntry 与 demo feedback 均为0。仅是本机PG17新库证据，不代表目标PG版本/既有库/容器或恢复演练。
- [x] 在第二个隔离 PostgreSQL 17.11 临时集群上完成 `pg_dump` custom archive → 仓库 `backup_restore.py` hash校验/隔离暂存 → `pg_restore` 到新库；恢复库 head 为 `91a0c5e2f347`、avatars=3、quick_topics=8，单独 app-state 测试标记一致。仅验证本地新库和通用归档流程，不含真实 revision/chunks/uploads/Chroma 一致性、既有库或目标机证据。
- [ ] 核实目标OS/架构、镜像digest、Python和完整锁依赖安装、模型缓存/权重、FFmpeg/ffprobe；不用Mac venv或隔离overlay替代。检查API+worker+导入/预热峰值RSS/CPU/磁盘，记录实际容量，不承诺固定机器规格。
- [ ] 在新建测试PostgreSQL或经备份的隔离副本验证迁移到唯一head、初始化只写基础种子；重启API不迁移/不demo；空库ready503但后台能导入，正式发布后ready达标。
- [ ] 真实景区资料经导入/草稿/发布，确认返回当前revision的真实vector来源；未发布/下架内容不泄漏，不把22条示例或synthetic source当景区事实验证。
- [ ] 双真实origin经HTTPS代理：匿名游客配置正确、后台保存后游客前台60s内发起刷新且空闲应用；Cookie Secure/HttpOnly与Host/scheme一致；错误Origin/CSRF拒绝，另一owner不越权，后台token不扩大行程权限。
- [ ] 有授权设备麦克风做短真实方言/口音输入→ASR→用户确认→聊天RAG→TTS播放，验证停止/重播/字幕/嘴型；拒绝麦克风时保留文字/上传降级，不尝试绕过权限。
- [ ] 覆盖目标手机Safari/Android/微信实际组合、相机/GPS/软键盘/弱网；按具体设备记录，不泛称全部兼容。
- [ ] 验证SSE心跳/增量/取消、ASR延迟预算、各端上传边界/413、模型/动作/worklet中文路径和缺失404；检查HTTPS字体和静态资源真实可达。
- [ ] W02 worker停机时排队、重启后领取/恢复，K01知识任务不重复执行；进程检查、排队时间与失败状态如实展示，ready不冒充worker健康。
- [ ] 测一致性备份恢复到隔离SQL/目录后，检查发布revision/chunks/素材hash/行程归属；验证磁盘不足、供应商不可用、重启和日志轮转。
- [ ] 逐项标已通过/失败/未测；权限、数据可见性、媒体串流、恢复任一关键项失败不放量，修复后仅补相关和必要回归。

### Task 8：真实部署切换、回滚与交接

**Files:** Create docs/deployment/ROLLOUT_RUNBOOK.md、RELEASE_MATRIX.md；真实部署后更新 docs/agent-operations/HANDOFF.md。

**Interfaces:** 输出两个独立current/previous release、后端镜像/迁移记录、可执行回滚操作和实际验收边界。

- [x] 编写未执行的目标机操作模板与逐次发布矩阵；命令和恢复说明明确真实 restore 仍须隔离 PostgreSQL 演练。见 [ROLLOUT_RUNBOOK](../ROLLOUT_RUNBOOK.md)、[RELEASE_MATRIX](../RELEASE_MATRIX.md)。
- [ ] 提供可审阅的真实域名/TLS/持久目录、后端配置键名和release hash；不输出密钥。只有用户明确授权实际部署后执行真实写操作，本计划请求不等于上线授权。
- [ ] 如已有游客origin，保持它；必须换域且有匿名任务时，先完成单独身份迁移方案，不静默把旧用户送到新身份。
- [ ] 后端兼容接口先部署；先关闭写入口、排空并确认旧API/K01/W02全部退出，再一致性备份和用本镜像显式migrate/必要initialize；启动检查成功后更新真实能力元数据、恢复入口。停止/启动窗口有记录，不运行两份API抢本地索引。
- [ ] 切管理站点，重新登录，确认配置和知识发布；保留旧游客再验证新后台/旧游客组合。旧游客存在的管理员配置401是历史缺陷，兼容窗口只保证旧行为不被额外破坏，不能声称旧包也被新接口自动修好。
- [ ] 切游客静态产物，确认无需API重启。实测两个方向单端回滚，另一端current与SQL/上传/知识发布不变，活跃页面懒加载成功。
- [ ] 关键验收失败即回滚相关静态端；后端schema不兼容暂停并按恢复/前滚方案处理，不盲目downgrade。维护窗口与用户侧中断如实记录。
- [ ] 留存版本矩阵、备份恢复证据与未完成设备范围；验收后再决定移除legacy入口/旧hash，遵循明确兼容窗口，不删除业务持久数据。

## 现在可以做与后续条件

Task0–6的实现与本地自动验证目前位于当前工作树，其中包含经审阅的 CASS 集成及双 Vite cacheDir 隔离修复；未提交改动仍待可写 Git 元数据的环境提交。本地临时 SQLite + stub 环境已完成管理端数字人模型预览和游客端API请求/响应冒烟；因embedding模型和核验资料缺失，RAG/真实问答未通过或未验证。真实供应商、语音播放/识别、目标平台依赖锁/真实Compose运行，以及Task7–8真实服务器、数据、域名和设备验收仍待完成。服务器条件尚未提供，不写死购买规格或承诺容量；未测项不算通过。

## 自审覆盖

- 当前干净基线、ASR210s和最新SSE修复：0/2/5。
- 公开配置/权限、manifest原子写入与真实Vue/图片接线：1/2。
- 独立产物/共享preview/资源白名单与功能并行边界：3/6。
- Linux锁依赖、FFmpeg、迁移/初始化/演示数据、空库启动：4/7。
- mixed API策略、实际批量上传、SSE/ASR超时：5/7。
- 本地数据持久化/一致性备份、双向资源回滚：5/7/8。
- 剩余真实验收集中安排、当前文档与历史测试证据区分：6/7。

本计划是持续实施跟踪；勾选项按当前源码和真实命令结果更新。未勾选项仍是待完成或待目标环境证据，不因计划文档存在而视为实现。

已完成[只读独立审阅及修订](REVIEW.md)；最终校验仅检查文档/源码证据，不重复真实功能验收。
