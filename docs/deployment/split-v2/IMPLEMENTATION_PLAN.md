# 管理端、游客端与服务器部署拆分 Implementation Plan V2（评审草案）

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

Task 4–5与纯业务功能可以分批推进，但不默认多人同时修改main、router、ChatView、Vite和public；由同一集成者逐提交整合。实际实施方法待用户选择，本轮只交付计划。

### Task 0：确认本轮基线与部署输入

**Files:** 读取AGENTS、frontend/AGENTS、backend/AGENTS、REPO_MAP、HANDOFF、TASK_BOARD；新增docs/deployment/SPLIT_INPUTS.md。

**Interfaces:** 输入确认设计；输出base SHA、隔离工作树、当前功能接口、服务器参数占位和存量身份判定。

- [ ] 执行git status --short --branch、git rev-parse HEAD、git worktree list --porcelain；与7f9f443比较。本轮已干净，不再把已提交的SSE/ASR修复当未完成任务重做。
- [ ] 若出现后续提交/脏文件，先审阅受影响路径并记录归属，不覆盖在途工作；按using-git-worktrees从确认基线创建隔离工作树。
- [ ] 把已批准的V2设计/计划及复核资料带入新工作树docs；不只引用外层项目的不可携带路径。
- [ ] 填部署输入：OS/CPU架构/内存/磁盘、是否已有Docker/反代、两域名/TLS、现有数据库、游客origin与匿名行程、模型和供应商可达性；未知值保留为上线输入，不阻断开发拆分。
- [ ] 记录当前静态84条路由与单一migration head；新增自动测试以本轮真实执行结果为准，687/164仅是工程历史记录。
- [ ] 提交仅包含本任务输入文档；不得读取/提交真实.env或密钥。

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

- [ ] 写test_anonymous_reads_active_config_without_admin_token：匿名200包含后台激活预设/逻辑音色/公开展示；不含id/model_path/内部路径/密钥。
- [ ] 写test_admin_operations_remain_protected：管理列表/激活/修改匿名401；不能通过放开admin router解决读取。
- [ ] 写test_missing_and_legacy_avatar_mapping：无记录回退hanfu/gentle-female；无激活按最小id；支持旧音色映射，未知值安全回退。
- [ ] 写test_manifest_atomic_replace与test_strict_read_does_not_return_false_defaults：隔离tmp_path内读者只见完整旧/新JSON；替换失败原文件不变且temp清理；已有损坏/无权限文件新接口503，首次不存在文件200默认。
- [ ] backend/运行选定venv python -m pytest app/tests/test_visitor_config_api.py app/tests/test_display_assets_atomic.py -q，确认未实现失败。
- [ ] 实现schema、service、router及同目录私有temp+os.replace；新入口不调用带权限的管理API handler；不顺带做跨机器或多写者事务。
- [ ] 重跑新测试与test_default_hotline_verification.py；更新地图并执行python3 scripts/check_repo_map.py；提交兼容后端接口。

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

- [ ] 写tourist_never_reads_admin_token、admin_401_clears_store_and_memory、disabled_storage_keeps_current_login：即使已登录后台，游客Axios/SSE无管理Bearer；401立即失效且管理导航回登录。
- [ ] 写visible_poll_and_hidden_pause、single_flight_and_dispose、busy_to_idle_flush_without_next_fetch：fake clock覆盖60s、隐藏/恢复、旧响应、Vue watch+nextTick立即应用。
- [ ] 写same_config_does_not_reload_model、image_timeout_and_404_keep_last_good、late_onload_cannot_replace_new_background：图片URL解析/15s降级保留；忙时模型与音色不变，当前播放器所有权不变。
- [ ] 运行四份新测试，确认缺失模块/行为失败；仅使用fake和Vite middlewareMode，不启动真实后端/供应商。
- [ ] 实现transport/token与管理API迁移；游客http保留API_BASE_URL供SSE，游客反馈与adminInsights拆开，ChatView删除对api/admin依赖。
- [ ] 实现刷新器及Vue watch接线；保留管理员invalidate兼容入口，移除游客对storage事件的跨域依赖。后台图集标明本机草稿、不清旧数据；语速/音量为本机预览。
- [ ] 运行新测试及publication-api-integration、publication-recovery、sse-stream、audio-playback-session、chat-replay、speech-cancel；通过后提交。本任务不改当前heartbeat producer或210s ASR语义。

### Task 3：两个独立应用与发布产物

**Files:**

- Create frontend/apps/tourist/{index.html,main.js,App.vue,router.js}、apps/admin同名四文件。
- Create frontend/vite.shared.js、vite.tourist.config.js、vite.admin.config.js；env/tourist/.env.example、env/admin/.env.example。
- Create frontend/scripts/{prepare-public,check-app-boundaries,check-build-boundaries}.mjs。
- Modify frontend/package.json、vite.config.js（保留legacy）、.gitignore、新游客运营入口/后台查看链接。
- Test frontend/tests/{app-boundaries,public-assets,build-boundaries}.test.mjs。

**Interfaces:** dev默认游客，dev:tourist/dev:admin/build:tourist/build:admin；build依次构建；端口5173/5174且strictPort；产物dist/tourist、dist/admin，各含一个index入口及完整manifest/chunk。

- [ ] 写tourist_graph_excludes_admin_auth_and_charts、admin_graph_keeps_preview_without_chat：遍历相对静态/动态imports，游客不可达管理员状态/API、ElementPlus/ECharts；后台可达ThreeAvatar，不可达游客ChatView/Router。
- [ ] 写asset_allowlist、self_contained_manifest：两端排除tester，游客保留worklet，后台不含录音worklet；模型/动作和中文VRM正常；每个产物引用全部在本产物内存在。
- [ ] 运行新测试确认当前单入口不满足，然后实现独立root/router/shell，保留现有src业务路径，不整体移动目录。
- [ ] 游客保留旧/tourist工具重定向并移除管理入口；后台/到/admin/dashboard，跨端查看使用仅允许部署固定https/开发本机http的普通链接。
- [ ] Vite7配置明确envDir、fs.allow、独立outDir，public白名单复制到.public-build；不复制真实.env，不通过缩小环境目录误漏必要公开配置。
- [ ] package新增两个构建/开发/预览和临时legacy命令；单端构建不得清理另一个outDir。
- [ ] 执行npm run build:tourist、npm run build:admin和两个边界脚本；重复只构建一端后另一端manifest/hash不变。检查缺模型、动作、图像与worklet引用。
- [ ] 开发双端页面验证路由、未登录管理跳转、后台预览和游客文字输入；不因权限未给手机而阻断结构交付。提交后作为下一批功能接线基线。

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

- [ ] 写production_restart_does_not_migrate_seed_or_add_demo：spy验证生产false标志下不执行迁移/bootstrap；不论是否误打开bootstrap，生产都不注入sample/demo反馈，原有记录不删除；必要基础种子只由initialize执行。
- [ ] 写unmigrated_schema_fails_without_upgrade、cli_has_no_app_startup_side_effects：schema不符直接错误，不自动upgrade；CLI仅执行选定动作，不触发预热或K01循环；兼容开发行为有独立断言。
- [ ] 写spa_mount_requires_root_index：SERVE_FRONTEND=false不挂SPA；true且dist/index.html存在才兼容旧包；仅有dist/tourist/admin不挂根。
- [ ] 运行新增测试确认失败，随后抽离生命周期职责；生产最小初始化quick topics/avatar，演示数据仅开发明确开启。保留K01在API、W02外部单进程。
- [ ] 实现候选Linux运行镜像：固定基础镜像/工具版本，安装FFmpeg/ffprobe与项目锁依赖，非root、确定工作目录；排除.env、venv、node_modules、uploads、缓存、备份和测试凭据，不烘焙模型私有目录。
- [ ] 目标架构未定时先交构建定义和静态检查。目标可用后核验现有顶层版本，解析所有传递依赖并生成含wheel hash的完整平台锁；镜像用pip --require-hashes -r完整锁安装并记录系统包/Python/平台/最终digest。同平台重建检查安装清单一致；失败单独做兼容PR，禁止换overlay冒充通过。不在此任务抢跑真实模型/供应商。
- [ ] 制定绝对持久路径与UID/GID，Compose私网只向外开放gateway；已有数据库用外部连接，不新建同名覆盖；/health作进程检查，/ready作为后续放量检查。
- [ ] 发布脚本顺序明确：关闭写入口→排空停止旧API/K01/W02并确认退出→一致性备份→数据库可连→本镜像migrate成功→必要initialize→新api/tool-worker/契约检查→恢复入口。初次安装也确认没有旧进程。每次后端release显式运行一次性步骤并记录镜像digest/head，不能沿用旧exited0状态；前端release不调用这些步骤。
- [ ] 写migration_cannot_start_while_old_api_or_worker_is_running：用发布步骤spy验证停写/退出/备份在迁移之前，任一步失败后续不执行；仅静态发布不触发该维护流程。
- [ ] 运行聚焦新增测试和test_startup_degraded、test_production_security_config、test_tool_worker_lifecycle；有Docker时docker compose config --quiet，输出不得展开秘密。提交运行封装。

### Task 5：代理、运行限制、独立发布与数据备份工具

**Files:**

- Create deploy/api-surface.json、deploy/nginx/{tourist.conf.template,admin.conf.template,common-api.conf}。
- Create scripts/render_api_policy.py、deploy/scripts/{publish-static,rollback-static,deploy-backend,backup-state,restore-state}.sh。
- Create scripts/check_release_compatibility.py；Test scripts/tests/test_release_compatibility.py。
- Create backend/app/schemas/runtime_limits.py、frontend/src/api/adminRuntime.js；Modify backend/app/api/admin.py、frontend/src/views/admin/KnowledgeManage.vue及components/knowledge/ImportBatchPanel.vue、运行配置模板。
- Test backend/app/tests/test_admin_runtime_limits.py、frontend/tests/import-limits.test.mjs、scripts/tests/{test_api_surface,test_proxy_templates,test_release_assets}.py。

**Interfaces:**

- GET /api/admin/runtime-limits，管理员可读，返回knowledge_import:{max_files,max_file_bytes}与display_assets:{max_image_bytes}，不返回其他配置。
- 首发生产KNOWLEDGE_IMPORT_MAX_FILES=1，KNOWLEDGE_IMPORT_MAX_FILE_BYTES=52428800；开发默认批次数仍可保留20，UI以服务器实际返回值约束，不写死为所有环境都1。
- api-surface逐项{method,path,boundary,sites}，覆盖新增后预期86条（以实现后的静态索引为准）；新增未分类接口拒绝发布。
- release.json包含源码SHA、应用名、构建工具、文件hash、所需后端能力；脚本只接收明确端名tourist|admin与release-id。
- 后端能力从已部署并核验的current/backend-release.json读取，字段image_digest/source_sha/schema_head/capabilities；前端required_backend_capabilities须为当前能力子集。后端升级验证所有仍支持前端的需求，不能只检查当前单一页面。

- [ ] 写runtime_limits_requires_admin_and_matches_settings：匿名401，有token返回实际安全限额；测试自定义值，确认不暴露其他settings。UI限额获取失败时阻止上传并给重试，不猜默认大批量值。
- [ ] 写multi_file_selection_matches_server_max与gateway_budget_includes_multipart：生产每批1×50MiB、网关55MiB；默认20环境不得被误渲染为整批55MiB，必须按实际批量预算渲染或拒绝未声明预算。
- [ ] 写api_surface_complete_and_method_sensitive：insights统计GET只管理，feedback POST游客，W02 execution游客owner；所有路由覆盖，无未知项自动放行。
- [ ] 写missing_api_asset_is_not_html、sse_no_buffer、asr_timeout_budget：网关缺失资源404/413为JSON或明确文本；SSE逐帧不缓冲；proxy_read_timeout240s是读间隔，保持客户端ASR210s和供应商180s+转换边界。
- [ ] 写publish_and_rollback_preserve_both_active_asset_sets：在临时目录完成A→B→A，两个方向旧/新manifest引用的hash文件均HTTP可达；只保留旧目录但当前路径不可达判失败；拒绝hash同名不同内容与跨端目录覆盖。
- [ ] 写static_release_never_changes_database_or_other_app：脚本操作限制在指定端web目录，无docker全栈重启/迁移/数据卷写入；未知端名和越界release-id拒绝。
- [ ] 写publish_and_rollback_reject_missing_backend_capability、backend_upgrade_preserves_supported_frontends：缺visitor-config-v1/admin-runtime-limits-v1或缺后端metadata即拒绝新包切换；前端回滚同样检查；后端删除仍受支持旧包需要的能力时拒绝。legacy必须有显式已确认映射，不从health推断。
- [ ] 实现管理限额与UI、网关方法/路径策略和分别持久web目录。Host/HTTPS信任按目标拓扑配置，不放宽Origin/CSRF；/api不剥前缀。
- [ ] 实现静态发布前完整校验与资源保留：按仍受支持release manifest合并hash资源；回滚目标也补齐活跃hash资源。HTML不缓存、无hash资源重验证，后台私有导入文件不暴露到/ui-assets。
- [ ] 实现check_release_compatibility并接入发布/回滚/后端升级；核对实际容器digest与schema/契约后才更新backend-release.json。字段声明不代替真实契约测试，但缺少声明不得继续切换。
- [ ] 实现备份/恢复脚本为显式维护操作：停API/worker写入后协调SQL、manifest、uploads、Chroma；恢复只能指定隔离目标，默认不覆盖现存生产目录。迁移前必须有恢复证据。
- [ ] 运行新增自动测试；目标NGINX可用时nginx -t，尚无NGINX则记录未执行。shell脚本先做bash -n和隔离目录演练，不操作真实服务。提交工具。

### Task 6：在新边界上继续功能新增并完成开发交付

**Files:** docs/development/FRONTEND_BOUNDARIES.md、docs/REPO_MAP.md、ARCHITECTURE.md、DEVELOPMENT.md、COMPATIBILITY.md、frontend/AGENTS.md、README；按实际后续功能另开小任务。

**Interfaces:** 输出双端开发入口、共享模块归属、CASS/offline接入规则和开发验收记录；后续功能必须基于Task3或之后集成提交。

- [ ] 划定入口/认证/构建文件的集成负责者；纯业务功能可继续编写，但ChatView/router/Vite/public改动按顺序合入，不建立长期互相覆盖分支。
- [ ] CASS按既有独立计划接src/guide、useGuideContext与服务模块，不复制旧分支整个ChatView；媒体/定位仍一个来源。拆分本身不批准CASS安全数据、后台接警或离线资源。
- [ ] 离线真正实施时仅加游客专属入口与白名单；有service worker才新增scope/缓存清理测试，管理API/身份/聊天不缓存。本轮不为未实现离线虚构通过结果。
- [ ] 开发交付时统一跑一次frontend npm test、npm run build及边界脚本；backend使用可用已声明测试环境跑pytest app/tests -q。环境缺失如实记录，不安装临时overlay绕过目标验证。
- [ ] 根目录跑地图检查、scripts unittest、git diff --check；记录新增测试与基线已有问题。无需每个文档改动都重跑全部业务测试。
- [ ] 文档准确记录当前K01/W02进程、两个入口、.env模板、产物和兼容窗口；保留FINAL-ACCEPTANCE-01待最终环境集中完成，不将其作为继续新增功能的阻断。
- [ ] 提交可评审开发交付，不自动合并master/部署生产。

### Task 7：目标服务器统一最终验收

**Files:** docs/deployment/FINAL_ACCEPTANCE.md、docs/deployment/SERVER_INVENTORY.md，更新既有FINAL-ACCEPTANCE-01实际结果。

**Interfaces:** 输入真实服务器/域名/TLS/已核验资料和设备；输出精确版本/环境、逐项证据、故障恢复和放量结论。

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

**Files:** docs/deployment/ROLLOUT_RUNBOOK.md、RELEASE_MATRIX.md、agent-operations/HANDOFF.md。

**Interfaces:** 输出两个独立current/previous release、后端镜像/迁移记录、可执行回滚操作和实际验收边界。

- [ ] 提供可审阅的真实域名/TLS/持久目录、后端配置键名和release hash；不输出密钥。只有用户明确授权实际部署后执行真实写操作，本计划请求不等于上线授权。
- [ ] 如已有游客origin，保持它；必须换域且有匿名任务时，先完成单独身份迁移方案，不静默把旧用户送到新身份。
- [ ] 后端兼容接口先部署；先关闭写入口、排空并确认旧API/K01/W02全部退出，再一致性备份和用本镜像显式migrate/必要initialize；启动检查成功后更新真实能力元数据、恢复入口。停止/启动窗口有记录，不运行两份API抢本地索引。
- [ ] 切管理站点，重新登录，确认配置和知识发布；保留旧游客再验证新后台/旧游客组合。旧游客存在的管理员配置401是历史缺陷，兼容窗口只保证旧行为不被额外破坏，不能声称旧包也被新接口自动修好。
- [ ] 切游客静态产物，确认无需API重启。实测两个方向单端回滚，另一端current与SQL/上传/知识发布不变，活跃页面懒加载成功。
- [ ] 关键验收失败即回滚相关静态端；后端schema不兼容暂停并按恢复/前滚方案处理，不盲目downgrade。维护窗口与用户侧中断如实记录。
- [ ] 留存版本矩阵、备份恢复证据与未完成设备范围；验收后再决定移除legacy入口/旧hash，遵循明确兼容窗口，不删除业务持久数据。

## 现在可以做与后续条件

现在可执行Task0–3，在明确目标架构后准备Task4–5；Task6承接新的功能。Task7–8等待真实环境与明确部署授权，不反过来阻断开发结构拆分。服务器资源/域名未提供，不写死购买规格或承诺天数。

## 自审覆盖

- 当前干净基线、ASR210s和最新SSE修复：0/2/5。
- 公开配置/权限、manifest原子写入与真实Vue/图片接线：1/2。
- 独立产物/共享preview/资源白名单与功能并行边界：3/6。
- Linux锁依赖、FFmpeg、迁移/初始化/演示数据、空库启动：4/7。
- mixed API策略、实际批量上传、SSE/ASR超时：5/7。
- 本地数据持久化/一致性备份、双向资源回滚：5/7/8。
- 剩余真实验收集中安排、当前文档与历史测试证据区分：6/7。

本轮仅制定计划；以上文件/接口/命令中标为Create的均是未来交付，不代表已经存在。

已完成[只读独立审阅及修订](REVIEW.md)；最终校验仅检查文档/源码证据，不重复真实功能验收。
