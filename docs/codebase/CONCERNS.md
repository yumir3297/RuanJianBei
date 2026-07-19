# Codebase Concerns

> 团队已确认当前目标是比赛演示，不是公网生产部署。以下优先级按演示场景调整；若后续转为真实景区运营，需要重新提高认证、隐私、监控和高可用要求。

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| 优先级 | 风险 | 影响/建议 |
|---|---|---|
| P1 | 前端硬编码天气 API key | 演示仍会暴露并可能耗尽额度；设置域名/额度限制，演示后轮换，转生产前迁移后端。 |
| P1 | 默认管理员密码与签名 secret | 演示环境必须隔离；任何公网/生产部署都应拒绝默认值。 |
| P1 | 未知异常把 `str(exc)` 返回客户端 | 可能泄漏路径、SQL 或 provider 信息；客户端返回统一错误码，细节仅入脱敏日志。 |
| P1 | ASR 音频写入公开目录且未见清理 | 游客语音存在隐私、磁盘和越权访问风险；增加鉴权、短期签名 URL、TTL 清理和告知。 |
| P1 | 启动强依赖本地检索模型预加载 | 缺模型/内存不足可能令整个 API 不可用；把准备度、延迟加载和降级边界明确化。 |
| P1 | 前端没有自动化测试 | SSE、音频队列、数字人和复杂页面易回归；优先覆盖状态机和关键游客路径。 |
| P2 | 缺少 CI、覆盖率、lint 和 secrets scanning | 质量与安全依赖人工；建立最小 PR 门禁。 |

### 2) Technical Debt

- `ChatView.vue`、`ExploreView.vue`、`RouteView.vue`、`QuizView.vue`、`pipeline.py`、`ThreeAvatar.vue` 文件体积大、职责多，应拆为状态机/子服务/子组件。
- README 和历史文档仍有 Live2D、SQLite 等旧描述，与当前 VRM、PostgreSQL 实现漂移。
- Qwen Vision 已在实际演示配置中启用；实时景区综合数据仍为 mock、Coze 仍禁用，宣传材料必须区分已接通能力与预留接口。
- 根目录含大型压缩包、重复 VRM/GLB 和多套设计原型。团队确认仅数字人动作/表情系统继续维护，其余设计原型可归档。
- `[TODO]` 明确生成物、模型、源资产和运行时资产的版本管理/LFS/归档规则。

### 3) Security Concerns

- 自定义 HMAC 管理员 token 只有单一身份、无撤销/角色管理；符合当前比赛演示的简化边界，但不满足成熟后台安全要求。
- 公开反馈与游客接口未见统一 rate limit，可能被刷接口、消耗模型额度或污染运营数据。
- 外部服务和日志缺少统一脱敏/审计规范；`.env.example` 的演示默认值容易被误用于生产。
- Markdown 已通过 DOMPurify 清洗，这是现有正向控制；上传也有体积/MIME 检查，但需要补生命周期与访问控制。

### 4) Performance and Scaling Concerns

- embedding/reranker/FAQ 等进程内单例在多 worker 下重复占内存且不共享更新。
- PostgreSQL 连接池已配置，但没有压测基线；流式对话会长期占用连接、任务和外部并发额度。
- SSE 没有跨实例恢复/消息队列；扩容时需负载均衡粘性或外置会话/事件层。
- 少量多次 token/音频改善感知延迟，但事件过细也会增加网络和渲染开销，应以首 token/首音频/卡顿率实测调节 chunk。
- 缺少 provider 熔断、统一重试和限流，外部抖动可能放大为请求堆积。

### 5) Fragile/High-Churn Areas

- 最近提交中高频变化集中在 `ModeSelectView.vue`、`router/index.js`、`stores/chat.js`、`ChatView.vue`、`pipeline.py`、`ThreeAvatar.vue` 和 `admin.py`。
- 上述文件同时位于核心体验链路且体积较大，修改需重点回归：首屏进入、文字/语音/图片问答、断流降级、音画同步、管理鉴权、知识更新闭环。
- 当前工作区存在大量未提交的业务与媒体资源改动；本次文档以该工作树为事实快照，后续提交拆分应避免丢失来源和意图。

### 6) `[ASK USER]` Questions

无待确认项。团队已于 2026-07-19 确认：

1. 当前交付目标为比赛演示。
2. 演示启用 DeepSeek LLM、百炼 TTS、百炼 ASR、Qwen Vision、OpenWeatherMap 和浏览器语音。
3. 仅数字人动作/表情系统相关设计与资产继续维护，其余设计原型可归档。
4. 后台运营所需数据允许持久化，其他临时数据应在游客退出时删除。
5. Python 3.13+、Node.js 20+ 是正式运行时要求。

现存“意图—实现”差距：退出即删除策略尚未在公开 ASR 音频等临时资源上完整实现；版本要求也尚未写入机器可读锁定配置。

### 7) Evidence

- `frontend/src/composables/useWeather.js`
- `backend/.env.example`
- `backend/app/core/config.py`
- `backend/app/core/auth.py`
- `backend/app/core/exceptions.py`
- `backend/app/api/voice.py`
- `backend/app/main.py`
- `backend/app/services/qa/pipeline.py`
- `backend/app/services/qa/runtime.py`
- `backend/app/db/session.py`
- `frontend/package.json`
- `frontend/src/views/tourist/ChatView.vue`
- `frontend/src/components/ThreeAvatar.vue`
- `README.md`
- `docs/CURRENT_TASK_SUMMARY.md`
