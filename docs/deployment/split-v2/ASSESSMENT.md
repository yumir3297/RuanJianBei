# 拆分与服务器部署复核（V2）

日期：2026-11-07（Asia/Shanghai）。范围：只读源码、Git、文档和静态路由复核；不执行功能实现、安装、迁移、付费调用或真实部署。

## 新结论

现在可以准备前端拆分，不必再等待上一次的在途语音改动：当前工作树干净，相关修改已提交。先做公开配置和认证边界，再建立两个独立前端入口与构建；在这个边界上继续新增功能。服务器运行封装可以随后准备，真实手机/语音/RAG/PostgreSQL验收继续按项目最新决定，集中到最终验收。

首发推荐单台 Linux 主机、两个静态站点、一个 API 进程和一个既有行程 worker；保持共享数据库与本地向量/素材存储。建议用 Docker Compose 固化运行环境和启动关系；这是本轮建议，尚不是用户已确认的服务器条件。服务器若已有成熟的原生进程管理，应复用相同运行契约，不同时维护两套首发方案。

## 相对上一轮的实际变化

| 项目 | 前次审计 | 本次核实 |
|---|---|---|
| HEAD | f33d168 | 7f9f4433f85ef57feee0d1034d107dd118d5c93e |
| 工作树 | 有 voice/stream 等未提交变更 | 干净 |
| SSE | 存在上下文修复的在途变更 | dc845d3 已提交，heartbeat 用独立 producer 保留上下文 |
| ASR | 旧客户端等待窗口 | 当前客户端 210s；后端供应商 180s，音频转换最多20s |
| readiness | 火山 ASR 配置检查待修 | 6701023 已提交，检查实际火山凭据 |
| 验收安排 | 外部条件未完成 | 625a33e 明确 FINAL-ACCEPTANCE-01：剩余真实验证集中到最后 |

源码根：/Users/yumir/RuanJianBei-integration-ai-workbench。不是外层项目 code/ 下的旧镜像。上述变化仅以本地 Git 和源码为据，没有检查远程 PR 最新状态。文档生成期间新增7f9f443，仅更新交接/任务/测试记录，业务代码未变；已复核该差异并更新最终摘要。

## 仍然成立的前端拆分事项

当前仍是一个 main.js、一个 App.vue/Router、一个 Vite build。游客调用管理员形象接口，Axios 共用管理员 token；展示变更通知依赖同源 storage；首页图集仅在本机 localStorage。公开接口、管理接口和游客所有者接口必须按方法/路径区分；insights 是混合路由，W02 execution 属于游客所有者。

静态路由仍为84条：37管理、1管理员登录、30游客所有者、14公开、2运维。该分类不是完整安全审计或运行时授权证明。

## 新增的服务器落地问题

1. **依赖尚未形成目标服务器上的可复现运行包。** requirements 固定 torch==2.12.0+cpu、sentence-transformers==5.5.1、chromadb==1.5.9，但主要是顶层包，Transformers等传递依赖仍会变化；项目记录里的隔离验收使用了不同 Torch/Transformers overlay，正常 venv 仍不完整。不能复制该 overlay 冒充已验证；目标平台需要完整解析的含hash依赖锁/固定wheelhouse，不能预先保证任意 Linux/ARM/Python 组合可安装。
2. **迁移和初始化绑在 API 启动。** main.py lifespan 执行 Alembic、基础 bootstrap、示例资料和演示反馈，再预热和启动 K01 循环。首发应把生产迁移/基础初始化交给一次性命令，API 重启仅做 schema 检查、预热和服务启动。
3. **演示反馈没有独立生产开关。** bootstrap_experience_demo_feedback 当前会在缺少 demo记录时写入 is_demo=true 的反馈。它不是“伪造真实反馈”，但生产不应在重启时自动新增演示记录。生产跳过示例种子，原有数据不自动清除。
4. **导入限制是每文件，不能直接当作整个 HTTP body。** 当前默认20文件×每文件50 MiB，一批理论内容上限约1000 MiB。直接设置网关55m会拒绝原来允许的多文件批次。建议首发明确每批1个文件、单文件50 MiB、网关55 MiB，并用管理员只读运行限制接口约束UI；大批导入后续再做总量预算。
5. **空知识库 /ready=503 是合理状态。** 新安装需先用后台导入/发布才能补齐知识；如果网关等待 /ready=200 才启动，可能把初始化入口一起挡住。容器进程检查用 /health；游客对外放量才以 /ready 和真实知识闭环为准。
6. **W02是单独进程，K01仍在API里。** 保留现有归属；不把两个前端解释为两份完整API。进程存在不证明任务可执行，应另外检查队列领取/恢复；容器 health 状态本身也不会自动修复所有故障。
7. **Chroma与上传/配置是有状态本地数据。** 前端 release、后端镜像、数据库、上传、manifest、向量目录、模型缓存必须分开。索引已有本地文件锁和发布epoch，但没有跨机器可用性证明。
8. **离线模块会改变构建和缓存边界。** CASS/offline仍是待开展/独立分支内容。双入口完成后再移植离线入口，service worker只能覆盖游客站点，不能缓存管理API、Cookie、聊天或精确位置。

## 当前证据与未验证范围

- 基线快照在本次计划原始工作区归档；新工作树以 `git rev-parse HEAD` 和 `git status --short --branch` 重新核对。
- 静态接口清单可从当前工作树用 `python3 scripts/check_repo_map.py --json` 生成；地图校验器不导入应用、不读取真实 `.env`。
- Alembic版本文件静态图只有91a0c5e2f347一个head；没有运行迁移或确认任何真实数据库结构。
- 最新工程文档记录687个后端测试通过/19跳过、164个前端测试通过。这是已有工程记录，本轮没有重跑，也不沿用为新方案实现通过证据。
- 本轮没有新增语音/手机/模型/生产数据库验收，遵循最终集中验收安排。

## 依据

- [Vite 7.3.3 环境变量](https://raw.githubusercontent.com/vitejs/vite/v7.3.3/docs/guide/env-and-mode.md)：VITE_*进入构建，envDir和构建期配置需明确。
- [FastAPI部署概念](https://fastapi.tiangolo.com/deployment/concepts/)：进程、内存、启动前步骤。
- [FastAPI容器部署](https://fastapi.tiangolo.com/deployment/docker/)：迁移等前置工作可由独立进程执行；容器不是自动扩容保障。
- [Compose启动顺序](https://docs.docker.com/compose/how-tos/startup-order/)：running不等于ready；service_healthy与service_completed_successfully含义不同。
- [NGINX代理模块](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)：SSE buffering、Host与读取超时；proxy_read_timeout不是响应总时长。
- [pip可重复安装](https://pip.pypa.io/en/stable/topics/repeatable-installs/)：完整依赖版本和hash，而非只固定顶层包。

完整方案见[新版设计](DESIGN.md)，执行顺序见[新版计划](IMPLEMENTATION_PLAN.md)。V2取代旧拆分文档的后续执行入口，保留旧审计作为历史证据。

已完成[独立审阅](REVIEW.md)，并纳入迁移前停写、完整传递依赖锁、后端能力发布校验三项修正。
