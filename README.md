# A5 灵山胜境智能导游系统

> 2026 年中国大学生计算机设计大赛 · 软件应用与开发类

## 项目简介

面向灵山胜境景区游客的智能问答导游系统。支持景点讲解、路线推荐、知识问答，集成 Live2D 数字人、语音交互、多模态图片识别、管理后台数据看板等功能。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + ECharts + Live2D |
| 后端 | Python FastAPI + Uvicorn |
| AI | DeepSeek V4 Pro（LLM）/ Qwen3.7-Plus（视觉）/ BGE（嵌入&精排） |
| 检索 | ChromaDB 向量库 + BM25 + Reranker |
| TTS | 阿里云百炼 CosyVoice |

## 快速启动

> 详细指南见 [队友部署说明.md](./队友部署说明.md) 和 [作品启动指南.md](./作品启动指南.md)

### 前置要求

- Python 3.13+
- Node.js v20+

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
│   │   ├── components/# 组件（Live2D/Avatar/交互）
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
