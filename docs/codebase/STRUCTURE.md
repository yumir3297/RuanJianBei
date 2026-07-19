# Codebase Structure

> 这是一个前后端分离但同仓管理的应用仓库，同时保留数据处理、评测、设计稿和原型资产。当前没有工作区或 monorepo 编排工具。

## Core Sections (Required)

### 1) Top-Level Map

| 路径 | 职责 | 当前判断 |
|---|---|---|
| `backend/` | FastAPI API、业务服务、数据库、迁移和自动化测试 | 主后端，可运行代码 |
| `frontend/` | Vue SPA、游客端、管理端、数字人和静态资源 | 主前端，可运行代码 |
| `data/processed/` | 清洗后的官方景区数据 | RAG/初始化数据输入 |
| `kb/` | 知识库原始或整理材料 | 知识工程输入 |
| `eval/` | E2E runner、数据集、联网 smoke 脚本和测试 | 系统级验证 |
| `evaluation/` | 问答指标计算与报告生成 | 离线质量评估 |
| `docs/`、`设计文档/` | 设计、决策、交付物和进度说明 | 意图参考；部分内容早于现实现 |
| `scripts/` | 辅助处理脚本 | 开发/数据维护工具 |
| `assets/`、`frontend/public/` | 图片、VRM、动作、音频等资源 | 运行时及展示资产 |
| `design-redesign/`、`design-reference/`、`lingshan-redesign/` | UI 设计探索和原型 | 团队确认可归档，不再作为主线维护 |
| `outputs/` | 生成结果/报告 | 派生产物，不应作为唯一事实源 |

扫描约 978 个可见文件、约 5.8 万行可计数源码；Vue 单文件组件未被扫描器完整计入语言统计，因此该数字只用于规模感知，不作为精确代码量指标。

### 2) Entry Points

- 后端启动：`backend/main.py` 导出 FastAPI `app`；实际应用组装位于 `backend/app/main.py`。
- 后端 HTTP 路由：`backend/app/api/`，包括认证、聊天、知识库、推荐、快捷选择、视觉、语音、运营洞察和管理接口。
- 前端启动：`frontend/src/main.js`，挂载 Vue、Pinia、Vue Router 和 Element Plus。
- 前端路由：`frontend/src/router/index.js`，划分游客端与管理端页面，并为管理端增加登录守卫。
- 前端 API：`frontend/src/api/`；聊天流由 `frontend/src/composables/useSSEStream.js` 消费。
- 数据库迁移：`backend/alembic/env.py`；数据初始化见 `backend/app/db/bootstrap.py` 和 `bootstrap_showcase_data.py`。
- 评测入口：`evaluation/evaluate.py` 与 `eval/e2e_runner.py`。

### 3) Module Boundaries

后端按层组织：

```text
app/api -> app/schemas -> app/services -> app/repositories -> app/models/db
                |              |
                +---------- app/core（配置、依赖、认证、异常）
```

- `api/` 负责协议、参数校验、依赖注入和响应组装，不应承载复杂领域逻辑。
- `services/` 负责问答编排、RAG、情绪、语音、视觉、数字人、推荐、洞察和数据导入。
- `repositories/` 封装 SQLAlchemy 查询与持久化。
- `models/` 定义 ORM，`schemas/` 定义外部契约，避免把数据库对象直接作为 API 契约。
- `core/` 提供配置、认证、异常和共享依赖；`db/` 管理会话、迁移及初始化。

前端按“基础设施 + 功能页面”组织：

- `views/tourist/`：欢迎、模式选择、对话、探索、路线、问答游戏。
- `views/admin/`：登录、仪表盘、知识管理、数字人配置、素材展示、分析报告、体验报告与知识盲区。
- `components/`：Three.js 数字人和跨页面组件。
- `composables/`：SSE、录音、音频、数字人、背景等可组合逻辑。
- `stores/`：Pinia 会话/认证等状态；`api/`：HTTP 契约；`utils/`：纯工具。

跨边界的核心契约是 `/api` JSON 接口和聊天 SSE 事件。前端不直接访问数据库或模型服务。

### 4) Naming and Organization Rules

- Python 模块使用 `snake_case.py`，测试使用 `test_*.py`；类使用 PascalCase，函数/变量使用 snake_case。
- Vue 页面和组件使用 `PascalCase.vue`；composable 使用 `useXxx.js`；普通 JS 模块按职责使用小写或 camelCase 文件名。
- 后端优先使用 `app.*` 绝对导入；前端当前使用相对导入，未配置 `@` 路径别名。
- 新业务优先进入现有层，而不是继续扩大 `api` 或单一页面文件；`ChatView.vue`、`pipeline.py`、`ThreeAvatar.vue` 已经承担较多职责。
- 静态展示资产应放入 `frontend/public/` 的明确子目录；训练/源资产和运行时资产应避免多份重复。
- 团队确认仅数字人动作与表情系统相关设计/资产继续维护，其余设计原型可归档；本次仅记录范围，没有移动或删除文件。

### 5) Evidence

- `backend/main.py`
- `backend/app/main.py`
- `backend/app/api/`
- `backend/app/services/`
- `backend/app/repositories/`
- `backend/app/models/`
- `backend/app/schemas/`
- `backend/app/core/`
- `backend/app/db/`
- `backend/alembic/`
- `frontend/src/main.js`
- `frontend/src/router/index.js`
- `frontend/src/api/`
- `frontend/src/components/`
- `frontend/src/composables/`
- `frontend/src/stores/`
- `frontend/src/views/`
- `eval/`
- `evaluation/`
- `docs/CURRENT_TASK_SUMMARY.md`
