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

整体实施顺序、功能链路、验收标准与待讨论事项见 [功能改进整体链路与分阶段路线图](./docs/plans/2026-10-27-feature-roadmap.md)。后续按文档顺序逐项讨论，当前暂缓语言／技术架构重构。

1.总结图片导出功能
2.美图功能
3.读图功能链路优化
4.高并发优化
5.防御性设计
6.社区系统（上传并讨论），游客讨论小贴士等能力
7.上传内容解析，多文本内容不限（把我们那个ocr扫描件内置进来）
8.把语言架构改一下
9.多端适配可以怎么优化一下？
10.整体链路优化，适应网络不稳定场景
11.GPS 位置实时调用、人流优化与人身安全支持
12.一键求救（通讯链路优化）
13.游客情绪分析优化
14.讲解速度调整，讲解重播，
