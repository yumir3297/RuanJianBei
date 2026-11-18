# AI 数字人智能导览平台

传智杯全国大学生数智创新与AI应用大赛 · AI WEB网页开发挑战赛

## 项目介绍

面向景区游客的 AI 数字人导览平台，提供景点讲解、知识问答、行程规划、语音与图片交互，并提供景区资料管理和发布功能。

## 技术架构

- 游客端与管理端：Vue 3、Vite、Pinia；数字人使用 Three.js 和 VRM。
- 后端：Python、FastAPI、SQLAlchemy；独立 worker 处理行程提案任务。
- AI 与检索：可配置的语言模型、视觉和语音服务，结合向量检索、BM25 和重排序。
- 数据与部署：PostgreSQL、ChromaDB，提供 Docker Compose 和 NGINX 配置。

## 安装与运行

请先阅读[开发运行指南](docs/DEVELOPMENT.md)，按模板配置数据库、模型服务和环境变量。游客端默认地址为 `http://localhost:5173`，管理端为 `http://localhost:5174`。部署说明见[服务器运行指南](docs/deployment/RUNTIME.md)。

## 目录

- `backend/`：后端接口、业务服务和数据库迁移。
- `frontend/`：游客端、管理端、数字人及静态资源。
- `data/`：景区数据。
- `deploy/`：部署配置和脚本。
- `docs/`：运行、部署和资料来源说明。
- `blender/`：数字人资源。

## 团队信息

- 学校：广州南方学院
- 队长：罗粤文
- 队员：赖嘉慧、何禹铭
- 指导老师：李志中
