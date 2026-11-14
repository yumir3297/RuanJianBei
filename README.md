# AI 数字人智能导览平台

> 传智杯全国 IT 技能大赛 · AI Web 网页开发挑战赛（Web+AI 赛道）

## 项目简介

面向景区游客的 AI 数字人导览平台，提供景点讲解、路线编辑、知识问答、Three.js/VRM 数字人、语音和图片交互，以及管理后台。项目包含灵山相关示例资料；实际景区配置、资料来源和使用许可需在部署前核实。模型服务需要独立配置，默认配置不能作为真实 AI 服务已接通的证据。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | 游客端、管理端两个 Vue 3/Vite 应用；Three.js/VRM 复用于展示，Element Plus/ECharts 由管理应用使用 |
| 后端 | Python FastAPI + Uvicorn |
| AI | 可配置的 OpenAI 兼容模型、视觉模型和 BGE 检索组件；实际供应商以环境配置为准 |
| 检索 | ChromaDB 向量库 + BM25 + Reranker |
| TTS | 可配置语音服务，具体可用性取决于供应商和环境 |

## 快速启动

> 跨系统依赖、开发运行与验证命令见 [开发指南](./docs/DEVELOPMENT.md)。本地运行由游客端、管理端两个 Vite server 加一个 FastAPI 后端组成；生产部署结构见 [RUNTIME](./docs/deployment/RUNTIME.md)。

行程提案需额外启动独立 W02 worker；配置和命令见[开发指南](./docs/DEVELOPMENT.md#持久行程提案-worker)。API 已启动不代表 worker 正在处理任务。

游客端默认地址为 `http://localhost:5173`，管理端为 `http://localhost:5174`。本地 API 就绪检查为 `http://127.0.0.1:8000/ready`；503 表示存在未就绪项，`/health` 只表示进程响应。

开发模式保留启动时迁移/bootstrap 兼容选项；生产模板关闭自动迁移、bootstrap 和 FastAPI 静态挂载。已有数据库须先备份并在隔离副本检查迁移。游客端和管理端入口、认证边界及命令见[双端边界说明](./docs/development/FRONTEND_BOUNDARIES.md)。

默认 provider 或 stub 响应不证明真实模型、语音或景区资料已接通。`ENABLE_SAMPLE_DATA=true` 加载的灵山示例数据不能直接当作经核验事实；知识导入、审核和发布见[知识工作区操作指南](./docs/knowledge-workspace-operations.md)。

## AI 开发与仓库地图

- [AGENTS.md](./AGENTS.md)：Codex 开发规则与按任务阅读入口
- [功能地图](./docs/REPO_MAP.md)：功能 → 前端 → API → 服务/数据 → 验证位置
- [架构链路](./docs/ARCHITECTURE.md)：聊天、语音、图像、定位与管理数据流
- [开发指南](./docs/DEVELOPMENT.md)：Windows、macOS、Linux 环境及测试命令
- [多端矩阵](./docs/COMPATIBILITY.md)：手机、平板、桌面和浏览器能力的现状与验收
- [双端边界](./docs/development/FRONTEND_BOUNDARIES.md)：两套入口、身份、构建和服务器发布规则
- [服务器运行包](./docs/deployment/RUNTIME.md)：候选 Compose、显式迁移、站点发布与备份恢复

地图维护校验（仓库根目录，无业务依赖）：`python scripts/check_repo_map.py`。
其他代码助手也可直接读取这些 Markdown；`--json` 可导出实时 API 索引。

## 项目结构

```
├── backend/           # FastAPI 后端
│   ├── app/
│   │   ├── api/       # 接口路由
│   │   ├── core/      # 配置
│   │   ├── db/        # 数据库
│   │   ├── models/    # ORM 模型
│   │   ├── schemas/   # Pydantic 模型
│   │   └── services/  # 业务逻辑（LLM/RAG/ASR/TTS/Avatar）
│   ├── main.py        # 入口
│   └── requirements.txt
├── frontend/          # 游客端与管理端 Vue 3/Vite 应用
│   ├── apps/tourist/  # 游客入口与 router
│   ├── apps/admin/    # 管理入口与 router
│   ├── src/
│   │   ├── views/     # 页面（游客端/管理后台）
│   │   ├── components/# 组件（Three.js/VRM/交互）
│   │   ├── composables/# 组合式函数
│   │   ├── stores/    # Pinia 状态
│   │   └── api/       # 接口调用
│   └── package.json
├── data/              # 景区原始数据
├── docs/              # 开发文档 & 启动指南
├── 设计文档/           # 架构设计文档
├── eval/              # 评测脚本 & 数据集
├── scripts/           # 辅助脚本
├── deploy/            # Compose、NGINX 模板与独立发布/备份脚本
├── assets/            # UI 设计稿
└── kb/                # 知识库索引
    └── faq_index/     # FAQ 语义索引
```

## 许可

内部学术竞赛项目

## 后续改进方向

当前已整合知识发布、可编辑行程及持久提案执行；真实模型、手机、弱网和完整浏览器链路尚待验收。当前功能、证据与缺口见[开发进度](./docs/development/PROGRESS.md)、[评分矩阵](./docs/competition/SCORE_MATRIX.md)和[架构选择](./docs/architecture/TARGET.md)。历史路线图和方案仅供追溯，不作为当前需求清单。
