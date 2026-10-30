# AI 数字人智能导览平台

> 传智杯全国 IT 技能大赛 · AI Web 网页开发挑战赛（Web+AI 赛道）

## 项目简介

面向各类景区的通用 AI 数字人导览平台：景区名称、导游形象、欢迎语、语音热词等均按景区自设置，无需修改业务代码。默认内置"灵山胜境"示例景区数据用于演示。支持景点讲解、路线推荐、知识问答，集成 Three.js/VRM 数字人、语音交互、多模态图片识别、管理后台数据看板等功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Three.js/VRM |
| 后端 | Python FastAPI + Uvicorn |
| AI | DeepSeek V4 Pro（LLM）/ Qwen3.7-Plus（视觉）/ BGE（嵌入&精排） |
| 检索 | ChromaDB 向量库 + BM25 + Reranker |
| TTS | 阿里云百炼 CosyVoice |

## 快速启动

> 当前仓库的跨系统启动、依赖条件与验证命令见 [开发指南](./docs/DEVELOPMENT.md)。旧版部署说明和作品启动指南未包含在当前 Git 快照中。

行程提案需额外启动独立 worker；配置和命令见[开发指南](./docs/DEVELOPMENT.md#持久行程提案-worker)。API 已启动不代表 worker 正在处理任务。

### 前置要求

- Python 3.13+
- Node.js 满足 `^20.19.0 || >=22.12.0`（当前 Vite 锁文件要求）

### 1. 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
copy .env.example .env          # 编辑 .env 填入 API Key
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 2. 数据初始化（首次）

```powershell
curl -X POST http://127.0.0.1:8000/api/admin/sync-processed-data
curl -X POST http://127.0.0.1:8000/api/admin/build-rag-index
```

### 3. 前端

```powershell
cd frontend
npm install
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

产品演进方向为“游客智能伴游 + 景区 AI 运营工作台”：让游客规划、修改、执行并保存游览，让运营人员导入资料、生产讲解、审核发布并处理反馈。以下均为规划，不代表已实现。

- [阶段路线图](./docs/plans/2026-10-27-feature-roadmap.md)：双端闭环、阶段依赖与交付门槛。
- [待开发清单](./docs/plans/2026-10-28-ai-workbench-backlog.md)：工作包、状态、验收与原 14 项需求追溯。
- [已确认的知识工作区设计](./docs/superpowers/specs/2026-10-27-knowledge-workspace-design.md)：永久草稿、批量上传、版本发布与下架，待实施。

建议先完成运营知识发布和游客可编辑行程两个闭环，再接入识景、统一播放、讲解生产、成果导出和运营待办。定位、客流、求助与扩展体验按依赖推进；弱网、多端和性能持续验收。

继续使用现有 Vue 3 + FastAPI，逐步重构职责与任务协作。更换语言或技术框架仍暂缓。原有总结导出、美图、社区、OCR、情绪与容量需求均保留在待开发清单中。
