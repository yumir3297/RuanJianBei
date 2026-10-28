# Repository guidance

本仓库是 AI 数字人导览 Web 应用：Vue 3/Vite 前端 + FastAPI 后端。
游客主要入口是 `TouristView.vue → ChatView.vue`，数字人实现是 Three.js/VRM。

## 按任务读取

- 先看 [功能地图](docs/REPO_MAP.md)，只打开本次功能所需文件。
- 改接口、流式事件、数据或服务依赖时看 [架构与业务链路](docs/ARCHITECTURE.md)。
- 启动、安装依赖、测试时看 [跨系统开发指南](docs/DEVELOPMENT.md)。
- 改页面、录音、图片、定位、数字人或部署地址时看 [多端验证矩阵](docs/COMPATIBILITY.md)。
- 前端约定见 [frontend/AGENTS.md](frontend/AGENTS.md)；后端见 [backend/AGENTS.md](backend/AGENTS.md)。
- 现有产品方向见 [功能路线图](docs/plans/2026-10-27-feature-roadmap.md)，其中待办不代表已实现。

## 工作约定

- 以源码与本次实际命令结果为准；历史设计和测试报告可能过时。
- 用相对路径及符号名定位；跨系统路径不要写个人盘符或本机绝对目录。
- 确认当前 cwd。后端运行目录是 `backend/`，入口是 `main:app`，不是 `app.main:app`。
- 先读 `package.json`/锁文件和 `requirements.txt`，不要虚构 lint、test 或安装命令。
- 不把 `.env`、令牌、API key、上传文件、模型缓存、数据库写入文档或提交。
- 不因生成地图而启动服务、迁移数据库、调用付费模型或重建索引。
- 服务层承载业务，API 层负责校验与编排，repository 层负责持久化；沿用现有边界。
- 改流式事件时同步核对服务端事件、前端解析和 store 消费；保持停止/重试隔离。
- 改设备能力时保留文字输入、上传图片等已有降级入口；实际验证后再声称兼容。
- 修改功能入口、路由、验证命令或模块职责时，同步更新对应地图；不复制整份源码。

## 验证

从仓库根目录执行；`python` 指向选定的 Python 3，macOS/Linux 常用 `python3`。

```sh
python scripts/check_repo_map.py
python -m unittest discover -s scripts/tests -p "test_*.py"
git diff --check
```

业务变更另按开发指南运行对应后端测试/前端构建。地图校验通过不代表应用或设备验收通过。
交付时说明改动、实际运行的检查和未验证范围。
