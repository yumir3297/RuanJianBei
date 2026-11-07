# 管理端、游客端与服务器部署设计 V2（评审草案）

日期：2026-11-07。性质：用户要求的新计划及设计依据，不是实施或上线批准。推荐与参数默认值均为本轮技术判断。

## 目标与实施时机

在当前已提交的语音/流式基线上，先修权限/配置边界并拆前端，再继续功能新增；服务器运行包随后准备，真实语音、RAG、手机和目标PostgreSQL集中到FINAL-ACCEPTANCE-01。不以“全部功能都做完”作为拆分前提，也不要求先完成真实设备验收才可以改入口和构建。

源码基线 integration/ai-workbench-final@7f9f4433f85ef57feee0d1034d107dd118d5c93e，核实时工作树干净。执行时重新核对，不从旧镜像或location/offline分支整体覆盖。

## 方案比较与推荐

| 方案 | 适用性 | 结论 |
|---|---|---|
| 单SPA继续加功能，最后拆 | 当前修改少，但更多功能会依赖混合入口、认证和构建 | 不推荐继续累积 |
| 同仓双前端，共享单API；开发拆分与真实上线分阶段 | 独立发布、改动集中，不破坏现有数据链路 | 推荐 |
| 两个前端并拆API/数据库/向量服务 | 需解决任务、索引、迁移和跨进程状态，当前缺生产验证 | 后置专项 |

首发部署建议单台Linux、NGINX双站点、一个API进程、一个已有W02 worker、共享PostgreSQL与本地向量/素材。建议Compose固化运行；机器系统/架构/已有服务未知，实际选型先确认。若机器不支持此方案，只替换运行编排，不回改业务边界。不同时实现Compose与原生systemd两套首发方案。

## 前端代码与产物

保留frontend/package.json、锁文件和src业务路径，新增：

    frontend/apps/tourist/{index.html,main.js,App.vue,router.js}
    frontend/apps/admin/{index.html,main.js,App.vue,router.js}
    frontend/vite.shared.js
    frontend/vite.tourist.config.js
    frontend/vite.admin.config.js
    frontend/env/tourist/.env.example
    frontend/env/admin/.env.example
    frontend/scripts/{prepare-public,check-app-boundaries,check-build-boundaries}.mjs

游客路由保留/、/tourist与旧工具重定向，不注册管理路由；管理端保留/admin/*。后台查看游客端用校验后的固定VITE_TOURIST_URL普通链接，游客页移除运营入口。

游客入口不安装Element Plus、不引用ECharts、管理员store/API。管理端保留Element Plus/图表与ThreeAvatar预览；Three.js不是只归游客端。不重写ChatView/MapView内部播放器、定位、行程或QA协议。

每端独立root、envDir、outDir、manifest；产物为dist/tourist与dist/admin，不共享跨站点chunk。开发5173/5174、strictPort=true、fs.allow明确包含frontend；API同源代理保留Host。Vite配置依实际7.x写法，不升级框架。

npm dev默认游客；新增dev:tourist/dev:admin/build:tourist/build:admin/preview:tourist/preview:admin；build依次构建两端。临时dev:legacy/build:legacy只用于迁移验证，不发布第三个站点。

显式envDir=frontend/env/<端>。生产VITE_API_BASE_URL为空，VITE_TOURIST_URL只在管理构建。全部VITE_*为公开构建参数；后端密钥和DATABASE_URL不进入前端环境/产物。新服务器参数变化可能需要重建前端，不能承诺修改容器env就改变现有JS。

静态资源通过白名单复制到.public-build/<端>：两端assets/models/motions/favicon，游客另含recorder-worklet.js；不复制map-tester/motion-tester或未知文件。上传素材从/ui-assets读取，不随前端release复制。保留中文VRM文件名、动作URL和根路径资源。

## 身份与公开配置

游客api/http.js只处理游客HTTP并保留API_BASE_URL给SSE；管理api/adminHttp.js独立读token/处理401；transport.js只含无身份语义基础实例。adminAuthStorage的get/set/clear使用同一响应式内存状态并同步a5-admin-auth，存储禁用也能完成当前页面管理登录。游客依赖图不能包含token模块。

管理API、知识导入/发布及管理统计走adminHttp；游客反馈单独保留。insights按方法/路径分类；W02 execution继续使用游客Cookie和owner作用域。管理员token不扩大游客行程访问权。

新增GET /api/visitor-config：

    {
      "avatar": {"model_key": "hanfu", "voice_type": "gentle-female"},
      "display": <现有PublicDisplayAssets字段>
    }

仅公开已生效内容；model_key白名单monk/hanfu/modern，音色沿用现有逻辑四种与旧名归一。读取激活项，无激活时id最小项，无记录/未知映射回退hanfu/gentle-female。不返回内部路径、管理员列表、供应商秘密。旧管理接口保持鉴权，旧公开display接口保留兼容。Cache-Control:no-store。

manifest改同目录私有temp写完后os.replace，失败清理temp、保留原文件；新接口严格读取，已有文件损坏/不可读返回可恢复503，首次缺文件可用默认配置。原子替换不是多写者事务，不宣称跨机器一致性。

游客统一useVisitorConfig：初次、恢复可见及可见期间每60,000ms取配置；隐藏停止轮询，同刻最多一个请求，卸载/代际变化忽略迟到结果。失败保留最近成功值，首次用默认；内容不变不重挂形象，形象/音色待聊天/录音/地图播放空闲再应用。Vue watch忙→闲立即flushPending，不等下一轮轮询。保留背景URL解析、15s预加载、默认/最近成功图片及迟到onload隔离。

首页图集仍是本机草稿，UI明确“不发布到游客端”；不清旧存储，不复制跨域token。已有游客origin优先保持，避免匿名Cookie/本地行程标识断开；若换域名且有存量身份，另立迁移项目后再切。

## 功能新增期间的规则

- 入口、vite配置、public白名单、http与配置读取器由拆分改动集中维护，不让多个长分支同时重排。
- 当前语音/SSE修复保持已提交逻辑；CASS新增业务放src/guide、composables、services模块，继续复用一个播放器/定位源，不因拆端引入第二套。
- 纯业务模块可以继续开发；触及ChatView接线、router、main、Vite/package/public的功能，以拆分落地提交为基线再合入。拆分分支应小步集成，不能等所有大功能同时完工。
- 离线将来只为游客端另加offline.html/src/offline和明确构建产物；不能把整套旧location分支Vite/package/ChatView覆盖进来。若引入service worker，限定游客origin/scope，不缓存管理API、身份、聊天、精确位置；本轮不实现离线功能。

## 服务器运行契约

推荐运行单元如下；两个静态站点可由同一个NGINX进程服务，不需要各启一个Node服务：

| 单元 | 职责 | 发布/启动关系 |
|---|---|---|
| gateway | HTTPS、两端静态文件、方法/路径API策略、/ui-assets转发 | 挂载两个独立release/current，只暴露80/443 |
| api | Uvicorn main:app，workers=1；QA/ASR/TTS与K01循环 | 私有网络；不复制API |
| tool-worker | 现有python -m app.services.tool_execution.worker | 与API同后端镜像、DB、SITE_ID和密钥 |
| migrate | 一次性Alembic upgrade head | 后端版本变更时显式运行成功再启动依赖服务 |
| initialize | 一次性最小基础种子 | 仅quick topics/avatar，不注入示例资料或demo反馈 |
| postgres | 共享数据库 | 有现成数据库则沿用；首次新建才启用容器数据库配置 |

推荐镜像初始目标Linux amd64、Python3.13 CPU；只是可验证候选，不能假定支持所有锁依赖。按服务器实际架构确认后固定base image与依赖版本/digest。镜像安装FFmpeg/ffprobe、锁定Python依赖，不在启动时pip install。前端由独立构建阶段产出静态包，不向服务器复制node_modules、Mac venv或绝对本机模型路径。

当前exact lock在目标环境安装失败时，单独提交最小依赖兼容修复并回归；禁止临时overlay换Torch后继续宣称原锁已验证。镜像构建和模型准备可先用fake/无凭据检查；实际模型载入与供应商闭环留到统一验收。

这里的现有requirements只是顶层固定版本，不能视为完整解析锁。目标平台安装验证后，生成deploy/locks/linux-amd64-py313.txt，包含全部传递依赖的精确版本与wheel hash；镜像用pip --require-hashes -r该完整锁安装，并记录Python/平台/系统包清单与最终镜像digest。也可固定wheelhouse用于离线重装，但首发只采用一种解析产物；后续换架构重新解析，不沿用不匹配wheel。部署始终使用同一个不可变镜像digest，不承诺未固定系统包源的镜像能逐字节重建。

新增开关AUTO_MIGRATE_ON_STARTUP、BOOTSTRAP_ON_STARTUP、SERVE_FRONTEND，兼容开发默认true；生产模板三者false。API生产启动检查schema已是应用支持head，未迁移则失败；不自行执行迁移/基础种子。生产任何模式都不自动注入示例资料/demo反馈，已有demo数据不自动删除。K01两条循环仍在单API，W02单独运行，不在本轮搬迁知识worker。

新增无main导入副作用的CLI：python -m app.cli.deployment migrate 与 initialize。重用基础种子与Alembic配置，不复制migration lineage。生产初始化不发布未经核实资料；后台导入/发布为正式知识入口。

数据库依赖healthy；迁移是成功退出才继续的一次性步骤，可由service_completed_successfully或发布脚本exit code落实。本方案推荐发布脚本显式串行运行migrate、initialize，再启动API/worker，而不是仅依赖普通compose up。后续升级必须用本次后端镜像digest显式执行migrate并记录head，不能把旧容器exited0当作新版本已迁移。静态前端发布不运行migrate或重启api/worker。

/health用于进程可响应检查；/ready用于应用当前就绪判断。新库无chunks时ready503，不应因此阻止后台站点启动及导入；游客正式放量前必须解决。worker进程存活不证明领取/供应商成功，最终验收用隔离任务验证领取与恢复，并观察排队时间。容器restart策略只在退出等指定条件生效，不把unhealthy直接等同自动重启。

## 服务器目录、配置与备份

建议挂载布局：

    /srv/ai-guide/web/tourist/releases/<release-id>/
    /srv/ai-guide/web/tourist/current -> releases/<release-id>
    /srv/ai-guide/web/admin/releases/<release-id>/
    /srv/ai-guide/web/admin/current -> releases/<release-id>
    /srv/ai-guide/data/ui-assets/
    /srv/ai-guide/data/knowledge-uploads/
    /srv/ai-guide/data/config/display_assets.json
    /srv/ai-guide/data/chroma/
    /srv/ai-guide/cache/models/
    /srv/ai-guide/backups/

这是服务器约定，不要求本机创建这些目录。用应用支持的绝对配置路径映射：UI_ASSET_UPLOAD_DIR、KNOWLEDGE_UPLOAD_DIR、UI_ASSET_MANIFEST_PATH、CHROMA_PERSIST_DIR、MODEL_CACHE_DIR；processed data为只读输入，不当线上可变知识主库。PG数据卷由数据库单独管理。

API需要写uploads/config/chroma，worker按实际handler只挂必要目录；模型缓存准备后可只读。非root应用用户的UID/GID与目录权限在目标机验证；日志轮转、上传/向量磁盘余量和备份空间必须观测。

后端统一注入APP_ENV、DATABASE_URL、SITE_ID、SCENIC_NAME、生产强密码/签名密钥及DeepSeek/火山/天气配置；不写入Git、前端env、镜像层或日志。显式选择现有供应商，不使用stub冒充实际验收。

备份必须覆盖SQL、manifest、上传和对应索引状态；首版在停止API/worker写入的维护窗口作一致性备份，恢复到隔离目录/数据库验证。模型可重建缓存与业务数据分开；SQL/索引不匹配时按正式知识重建，不能直接回退发布指针。实际保留周期和异地存储由服务器条件确定，至少每次迁移前有可恢复备份。

## 代理、超时与上传

两域各自/api原路径反代同一API；保留Host含必要端口，设置真实X-Forwarded-Proto，Uvicorn只信任已确认代理IP。不剥离/api、不额外root_path=/api、不放宽Origin/CSRF/Cookie Domain。域名未定时配置为参数；未知Host拒绝。

方法+路径策略清单覆盖所有显式路由。游客拒绝管理员登录/管理接口；后台仅允许管理及预览所需公开接口，拒绝游客私人任务；服务端权限仍保留。运维探针仅内部访问。API、上传素材、模型、动作、worklet缺失必须真实错误，不走SPA fallback；页面fallback按本站已知路由。

SSE关闭proxy_buffering/proxy_cache，保留Content-Type与心跳，不改现有ContextVar producer实现。proxy_read_timeout建议240s，它是上游读间隔而不是整段请求总时长；ASR后端180s+转换20s，客户端210s，代理240s需按最终实测确认，不宣称能处理任意长度音频。

上传按端点设置，不一刀切：ASR默认10MiB raw可设网关12MiB；vision默认5MiB可设6MiB；背景默认8MiB multipart可设10MiB。知识导入当前20×50MiB；首发生产明确KNOWLEDGE_IMPORT_MAX_FILES=1、单文件50MiB、网关55MiB，并新增受保护GET /api/admin/runtime-limits给UI读取max_files/max_file_bytes/ui_image_bytes，调整前后端测试。不是把“单文件50MiB”误称整个现有批次上限。自定义服务端上限时同步渲染代理；网关超限返回可识别413，不向UI返回默认HTML错误页。

HTML与公开配置需重验证/no-store；只对构建manifest标识的hash资源长缓存，无hash图片/VRM/worklet不统一immutable。公开动态素材不与后台私有导入文档混用路径。

## 发布、兼容和回滚

前端发布单位分别为tourist.tar.gz、admin.tar.gz及release.json（源码SHA、构建工具、文件hash、所需后端能力）。后端以不可变镜像digest发布，API/worker/迁移同一版本；保留一个前后端兼容窗口。

后端构建生成backend-release.json，字段image_digest、source_sha、schema_head、capabilities，能力示例visitor-config-v1/admin-runtime-limits-v1/chat-sse-v1/tour-sessions-v1。部署成功确认实际容器digest、schema与契约探测后才原子更新服务器current/backend-release.json；不能用/health=200推断能力。前端发布及回滚脚本检查target release.json的required_backend_capabilities是当前已部署集合的子集，否则拒绝切current。后端升级也检查当前与仍支持的旧前端manifest需求；缺少metadata时只能使用经过确认的legacy矩阵，不能默认为兼容。

先添加兼容API，再切管理站点，验证管理发布闭环，最后切游客站点；尽量保留游客origin。新release合并仍在支持窗口的旧manifest引用hash文件，并由当前HTTP路径提供。单端回滚前，目标旧release也必须能提供仍打开的新版本页面所引用hash文件，资源保留需覆盖发布和回滚两个方向；不止保留不可访问旧目录。

每端current独立切换；前端回滚不逆向迁移SQL、不回滚知识数据、不覆盖uploads/config。API只有一个进程，后端升级允许明确维护窗口，不宣称后端零停机。schema不兼容时先停升级并恢复经验证备份/采用前滚修复，不盲目alembic downgrade。

已有后端升级的顺序为：网关进入维护/关闭写入口→排空并停止旧API（包含K01循环）与W02 worker，确认进程退出→一致性备份→新镜像migrate→必要initialize→新API/worker启动与契约检查→更新后端release元数据→恢复入口。不能先迁移再停止旧进程。首次空环境没有旧进程时仍验证该状态；静态前端发布不经过这一停写流程。

## 阶段验收

开发完成门槛：公开配置/认证正确、配置刷新不打断媒体、双产物自包含、源依赖/静态资源边界通过、启动职责和Compose/代理配置可验证。开发门槛不要求真实手机/供应商/生产库。

最终服务器门槛：目标精确依赖安装与模型、真实发布景区知识/vector、ready、ASR→确认→聊天RAG→TTS、权限/行程CAS/重启恢复、真实手机、上传限制、磁盘与备份恢复、两个方向静态回滚及W02独立进程。全部记录实际结果；基础设施参数缺失时只完成运行包，不宣称已部署。

对应实施任务及暂缓项见[新版计划](IMPLEMENTATION_PLAN.md)，源码事实与技术参考见[复核报告](ASSESSMENT.md)。
