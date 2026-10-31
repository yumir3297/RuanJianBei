# AI 数字人智能导览平台

> 传智杯全国 IT 技能大赛 · AI Web 网页开发挑战赛（Web+AI 赛道）

## 项目简介

面向各类景区的通用 AI 数字人导览平台：景区名称、导游形象、欢迎语、语音热词等均按景区自设置，无需修改业务代码。默认内置"灵山胜境"示例景区数据用于演示。支持景点讲解、路线推荐、知识问答，集成 Live2D 数字人、语音交互、多模态图片识别、管理后台数据看板等功能。

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

## 离线伴游与应急页

弱网/断网时可进入独立的轻量页面 `/offline.html`：Q 版跑酷、可缩放的静态景区示意图、应急联系电话。该页不加载 Vue、Element Plus、Three/VRM、Leaflet 或在线瓦片。

- **入口**：游客页右下角在持续不可达（≥3 次探针失败且 ≥15 s）时出现“进入离线伴游”横幅；用户点击后才跳转，不会自动切页。
- **离线包**：主站首次在线访问时后台注册 Service Worker，并校验 `/offline.html`、入口 JS/CSS、地图、通讯录是否全部进入 Cache Storage，全部成功才显示“已就绪”。预缓存清单由 `scripts/offline-sw-plugin.mjs` 在构建期按真实产物图生成。
- **连通性**：同源 `GET /health`（`no-store` + `redirect:'error'` + 2.5 s 超时 + JSON `status==='ok'` 校验），不使用 `navigator.onLine` 作为结论；Vite 开发与预览均已代理 `/health`。
- **数据文件**：
  - `frontend/public/offline/help/contacts.json`（`status` 为 `verified` 且 `phoneUri` 合规时才渲染 `tel:` 拨号按钮）
  - `frontend/public/offline/map/map-meta.json`（`status`、`source`、`license`、`verifiedAt`、`usableForEmergency`）
  - 当前两者均为 **unverified**，页面会显著提示“未核验、请向附近工作人员求助”，不得当作官方救援依据。替换为经核验数据后重新构建即可生效。

```bash
cd frontend
npm run build      # 生成 dist/offline.html、dist/sw.js 与预缓存清单
npm test           # 状态机/游戏/存储/数据 schema 单元测试（node:test，无额外依赖）
npm run test:e2e   # 生产构建 + 真实浏览器断网验收（需 playwright-core 与本机 Chromium）
```

开发模式（`npm run dev`）不注册 Service Worker，离线页可访问但会如实显示“离线包未就绪”。详见 [离线审计](docs/implementation/OFFLINE_AUDIT.md) 与 [验收记录](docs/implementation/OFFLINE_ACCEPTANCE.md)。

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
