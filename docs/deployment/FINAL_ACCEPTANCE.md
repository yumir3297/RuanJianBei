# 管理端/游客端拆分最终验收

状态：**本地代码与自动化验收持续进行；目标服务器/域名/设备均未提供，生产验收未开始，不具备上线结论。**

## 通过规则

- 每项记录 `通过 / 失败 / 未测`，并附版本、实际 URL、设备/服务环境、命令或截图/日志证据。
- 静态清单、stub供应商、fake Docker/PostgreSQL 和 Compose YAML解析只证明对应自动检查；不得替代真实容器、真实数据库、真实供应商或真机验收。
- 数据权限、Cookie/CSRF、SSE停止隔离、资料发布可见性、恢复任一关键项失败时不放量；修复后重跑失败项与必要回归。
- 最终通过要求：目标机环境锁定、所有 Must 项有实证、恢复演练成功、用户接受并记录容量/SLO/备份目标。

## 明确放行界限

验收分为两个结论，不能用本地工程通过替代服务器放量通过：

1. **本地开发交付可评审**：双端独立构建及边界测试通过；后端测试通过；发布/回滚/兼容性/备份部署脚本自动测试通过；地图、Compose YAML静态解析、shell语法和diff检查通过。此结论只表示代码可进入目标机验收准备，不代表服务已能部署或上线。
2. **目标服务器允许放量**：SERVER_INVENTORY必填项补齐；下列 Must 门槛全部标为“通过”并附目标环境证据；RPO/RTO、保留策略、并发与延迟SLO已由运营方确认。任一 Must 为“失败/未测”，或这些目标仍为空，结论就是“暂缓放量”。

### Must 放量门槛

| 门槛 | 通过条件 | 当前状态 |
|---|---|---|
| M1 环境与来源可追溯 | 锁定 OS/CPU、平台依赖、镜像 digest、源码 SHA；镜像标签与候选清单匹配；游客/管理 HTTPS origin、TLS终止和持久目录明确 | 未测：服务器输入未定 |
| M2 身份与数据边界 | 匿名游客配置返回200且无内部/管理员字段；管理接口无身份时401/403；非法Origin/CSRF被拒；不同游客owner不可互读；管理员凭据不授予游客行程权限 | 未测：仅有本地自动测试 |
| M3 数据迁移与恢复 | 隔离目标库迁移到唯一schema head；初始化幂等且不注入演示数据；真实 PostgreSQL dump 与状态目录恢复到隔离目标成功，revision/chunks/uploads/Chroma一致 | 部分本地证据：临时 PostgreSQL 17.11 新库迁移/初始化/pg_dump/pg_restore通过；未验证目标版本或既有库，也未恢复真实revision/chunks/uploads/Chroma，故M3仍未通过 |
| M4 端到端业务 | 经许可的真实景区资料可导入、审核、发布并检索正确revision；真实供应商完成聊天/ASR/TTS链路；取消/重试不串请求；生产不得使用 `simple-dev-embedder` 或其他合成 provider | 部分本地门禁通过：生产配置拒绝 `simple-dev-embedder`；真实资料、供应商链路和目标机仍未测 |
| M5 独立发布回滚 | 游客、管理分别A→B→A；每次静态切换不重启API、不迁移、不改业务数据；旧/新活跃HTML引用资源均可经目标HTTP入口取到 | 未测：仅隔离目录自动测试 |
| M6 运行容量与可靠性 | 在批准的并发和延迟SLO下完成压测；代码默认chat/asr/vision=8/4/4时，达到上限可完成或正确排队，超额请求明确返回429及Retry-After；峰值CPU/RAM/磁盘有实测余量 | 未测：8/4/4是候选保护值，不是容量承诺；延迟SLO待确认 |
| M7 设备与降级 | SERVER_INVENTORY中最终批准的浏览器/微信WebView设备逐台实测；麦克风/相机/GPS拒绝后文字/上传降级仍可用 | 未测：设备矩阵未定 |
| M8 备份目标 | 每日7份+每周4份、RPO≤24小时、RTO≤4小时仅作为候选；运营方确认最终值，按该值验证保留和真实恢复耗时 | 未测：候选值未确认 |

文件上传目前候选服务限制为每批最多1个文件、单文件50 MiB、网关请求上限55 MiB；服务器验收必须用边界内文件成功、超限请求413验证，并确认生产配置与API实际限制一致。若运营方要提高上限，先同步调整API和网关预算并重新验收，不能只改其中一层。

## 当前本地证据

| 验收项 | 当前状态 | 证据范围/限制 |
|---|---|---|
| 游客/管理独立入口、构建闭包和产物隔离 | 自动化通过；本地浏览器冒烟通过；游客端无管理导航 | 回归测试确认游客 UI 无管理链接、游客 router 未注册管理路由；本次重建清理旧哈希资源后，游客产物内无管理入口文案/链接。桌面内置浏览器验证游客入口和管理端登录页，不代表目标设备/HTTPS代理验收 |
| 管理数字人预览与游客 API 请求/响应冒烟 | 管理端模型预览通过；游客 API 请求/响应联通 | 临时 SQLite、本机测试管理员凭据、LLM/ASR/VISION/TTS stub；浏览器看到管理端 VRM 模型，游客文字请求收到无资料兜底回答。embedding 模型不可用且无核验景区资料，RAG/真实问答不算通过；未验证真实模型供应商、TTS/ASR播放链路、目标服务器或手机 |
| 游客不读/发管理 token，公开配置与管理限额边界 | 自动化通过 | 前端/API 测试；未过真实 HTTPS 反代 |
| 游客/管理静态发布、回滚与哈希资源保留 | 隔离目录 A→B→A 自动测试通过；本次游客/管理构建分别打包后在临时站点实际 A→B→A，manifest 中游客63个、管理130个文件齐全，单端切换不改变另一端 current；短生命周期本机HTTP服务逐个读取A、B、回滚阶段入口与JS/CSS均返回200；严格 umask 下 nginx 可读权限通过 | 发布器演练使用合成兼容性 metadata，只证明本地文件发布/回滚链路；Python静态HTTP不等于真实 NGINX 路由/TLS/Host、生产后端兼容或跨 CDN 缓存验收；M5目标机门槛仍未通过 |
| CASS 情境规则、来源时效、调度与提案入口 | 自动化通过，情境变化时旧评估结果失效 | 前端组件/状态机与后端策略/API已测；未做真实位置或现场天气验证；CASS默认关闭 |
| 后端部署维护顺序 | fake Docker/PostgreSQL演练通过，部署命令/probe回归通过 | 覆盖停服务、备份失败、旧进程未退出；并校验 Compose 迁移检查命令及管理员探针语法；不是实际 Docker/数据库升级 |
| 数据库迁移/初始化/启动 | 本地 SQLite与自动测试通过；隔离 PostgreSQL 17.11 新库迁移/生产初始化通过 | 实跑显式迁移到 `91a0c5e2f347`，重复初始化后 avatar_configs=3、quick_topics=8、demo knowledge=0、demo feedback=0。不是目标 PostgreSQL 版本/既有库演练；Compose 和 API 重启路径仍未测 |
| 目标 Compose 配置/容器构建 | 未测 | 当前环境无 Docker CLI |
| NGINX 配置语法/TLS/Host/cookie | 未测 | 当前环境无 NGINX，真实域名和TLS终止点未定 |
| 备份恢复到隔离 PostgreSQL和状态目录 | 本机 PostgreSQL 17.11 新库 dump/restore 冒烟通过；业务一致性仍未测 | `pg_dump` custom archive 经仓库 `backup_restore.py` hash校验并隔离暂存，再 `pg_restore` 到新库；schema head、基础种子和单独 app-state 标记一致。未包含真实 revision/chunks/uploads/Chroma，亦非目标机/既有库恢复演练 |
| 真实景区资料、LLM/ASR/TTS、天气供应商 | 未测 | 等经许可真实资料与有效测试凭据 |
| 目标浏览器、摄像头/麦克风/GPS/弱网 | 未测 | 目标设备/WebView组合未提供 |
| 当前自动化回归 | 通过：最新前端回归 **260 项**；后端主线记录 **787 passed、20 skipped、12 warnings**；统一本地比赛入口通过知识双 origin、普通问答、行程、GuideLoop、CASS 与离线陪游 **16/16** | 统一入口使用虚构资料、stub 音频、`simple-dev-embedder` 和 Playwright 模拟断网；这些结果不替代真实供应商、Docker/NGINX、目标服务器和设备验收 |

## 最终目标机执行清单

依据 [SERVER_INVENTORY](SERVER_INVENTORY.md) 填妥实际环境，并按 [多端矩阵](../COMPATIBILITY.md) 执行：

1. 锁定 OS/架构、Python/系统包、完整 hash 依赖、镜像 digest、模型权重和 ffmpeg/ffprobe；实测 API+W02+模型预热+导入峰值 CPU/RAM/磁盘。
2. 对隔离 PostgreSQL 备份副本运行迁移到唯一 Alembic head；验证基础 initialize 幂等、API restart 不迁移、不写 demo。
3. 用实际许可的景区资料走导入→冲突处理→草稿→发布；核验 revision、chunks/vector来源、未发布/下架不可检索。
4. 经两个真实 HTTPS origin 验证 `/api` method/path 规则、CORS/CSRF、Secure/HttpOnly cookie、游客 owner 隔离、后台 token不扩大游客权限、公开配置60秒内刷新。
5. 验证聊天SSE增量/心跳/取消、ASR→确认→RAG→TTS、重播/字幕/数字人嘴型、图片上传/413、静态hash资源和缺失资源404。
6. 在选定设备验证文字输入降级、麦克风/相机/GPS授权/拒绝、软键盘/弱网、页面切后台和微信WebView；逐设备记录，不概括为“手机兼容”。
7. 执行 `deploy-backend.sh` 的隔离 PostgreSQL演练；核实 W02停机排队/重启恢复、K01不重复执行、备份还原 revision/chunks/uploads/Chroma一致。
8. 做游客端和管理端各一次独立发布、A→B→A回滚；证明两套 current 独立、活跃页面旧新资源均可HTTP读取，静态操作不改变数据库/服务进程。
9. 按已批准的并发、延迟、备份保留、RPO/RTO跑压测/恢复演练；更新每项状态和证据，运营方决定放量或暂缓。

目标服务器条件仍为“未定”时，继续交付本地代码和自动化；不得将本清单里的未测项标为通过。
