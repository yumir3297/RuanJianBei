# AI 数字人智能导览平台

> 传智杯全国 IT 技能大赛 · AI Web 网页开发挑战赛（Web+AI 赛道）

## 项目简介

面向景区游客的 AI 数字人导览平台，提供景点讲解、路线编辑、知识问答、Three.js/VRM 数字人、语音和图片交互，以及管理后台。项目包含灵山相关示例资料；实际景区配置、资料来源和使用许可需在部署前核实。模型服务需要独立配置，默认配置不能作为真实 AI 服务已接通的证据。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Three.js/VRM |
| 后端 | Python FastAPI + Uvicorn |
| AI | 可配置的 OpenAI 兼容模型、视觉模型和 BGE 检索组件；实际供应商以环境配置为准 |
| 检索 | ChromaDB 向量库 + BM25 + Reranker |
| TTS | 可配置语音服务，具体可用性取决于供应商和环境 |

## 快速启动

> 当前仓库的跨系统启动、依赖条件与验证命令见 [开发指南](./docs/DEVELOPMENT.md)。旧版部署说明和作品启动指南未包含在当前 Git 快照中。

行程提案需额外启动独立 worker；配置和命令见[开发指南](./docs/DEVELOPMENT.md#持久行程提案-worker)。API 已启动不代表 worker 正在处理任务。

启动后可检查 `http://127.0.0.1:8000/ready`；503 表示存在所列未就绪项。`/health` 仅表示服务响应，不能证明真实模型或知识库可用。FAQ 故障恢复和多进程限制见[开发指南](./docs/DEVELOPMENT.md)。

### 前置要求

- Python 3.13+
- Node.js 满足 `^20.19.0 || >=22.12.0`（当前 Vite 锁文件要求）

### 1. 后端

后端启动会自动运行数据库迁移。已有数据库尤其是旧 W02 数据库，启动前须先备份，并在隔离副本核对结构及迁移兼容性；不能仅凭版本号直接升级。已知限制见 [W02 集成记录](./docs/development/W02_INTEGRATION.md)。首次试用建议使用独立空数据库。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
copy .env.example .env          # 配置数据库及需要的供应商；不要提交密钥
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 2. 数据与知识发布

首次启动会执行数据库初始化；是否加载示例数据由 `ENABLE_SAMPLE_DATA` 控制，示例数据不能作为真实景区事实。请先确认数据库、景区资料来源和模型缓存路径，使用隔离环境验收。知识导入、审核、发布和索引恢复的具体步骤见[知识工作区操作指南](./docs/knowledge-workspace-operations.md)。

管理员接口需要认证。旧的 `sync-processed-data` 与 `build-rag-index` 是会写入数据库或索引的管理操作，并非无认证的首次启动步骤；不要直接对已有数据执行。知识导入草稿与面向游客的已发布版本是不同状态。

### 3. 前端

```powershell
cd frontend
npm ci
npm run dev
```

浏览器打开 `http://localhost:5173`

## AI 开发与仓库地图

- [AGENTS.md](./AGENTS.md)：Codex 开发规则与按任务阅读入口
- [功能地图](./docs/REPO_MAP.md)：功能 → 前端 → API → 服务/数据 → 验证位置
- [架构链路](./docs/ARCHITECTURE.md)：聊天、语音、图像、定位与管理数据流
- [开发指南](./docs/DEVELOPMENT.md)：Windows、macOS、Linux 环境及测试命令
- [多端矩阵](./docs/COMPATIBILITY.md)：手机、平板、桌面和浏览器能力的现状与验收

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
├── frontend/          # Vue 3 前端
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
├── assets/            # UI 设计稿
└── kb/                # 知识库索引
    └── faq_index/     # FAQ 语义索引
```

## 许可

内部学术竞赛项目

## 后续改进方向

当前已整合知识发布、可编辑行程及持久提案执行；真实模型、手机、弱网和完整浏览器链路尚待验收。当前功能、证据与缺口见[开发进度](./docs/development/PROGRESS.md)、[评分矩阵](./docs/competition/SCORE_MATRIX.md)和[架构选择](./docs/architecture/TARGET.md)。历史路线图和方案仅供追溯，不作为当前需求清单。
