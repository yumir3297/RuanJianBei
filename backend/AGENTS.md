# Backend guidance

遵守仓库根目录 [AGENTS.md](../AGENTS.md)，链路见 [架构说明](../docs/ARCHITECTURE.md)。

- cwd `backend/`，启动 `python -m uvicorn main:app --host 127.0.0.1 --port 8000`。
- 测试入口 `python -m pytest app/tests -q`；优先跑功能地图指定文件，再按影响扩大。
- `main.py` 负责 lifespan、迁移、bootstrap、模型预热和静态挂载。导入/启动不视为无副作用探测。
- 配置入口 `app/core/config.py`；`.env` 相对 cwd 读取，不能把真实配置写入地图。
- `app/api/router.py` 统一注册 `/api` 子路由；修改前核对完整 prefix。
- 请求/响应模型在 schemas，持久化在 repositories/models，业务在 services。
- DB session 是 async SQLAlchemy；保持 await/事务边界，数据库结构调整使用 Alembic。
- 聊天事件由 `StreamEvent.to_sse` 编码；改字段同步核对前端 store 与契约测试。
- `build_pipeline` 的降级不代表 lifespan 模型预热一定能成功；不要承诺无模型即可启动。
- 单元测试可用已有 fake/stub；真实 LLM/ASR/TTS/视觉调用及其凭据属于另一验证层。
- `/health`、`/ready` 含义不同；就绪不保证每个供应商调用成功。
- 更新地图无需访问 `.env`、加载模型、运行迁移或请求外部服务。
- requirements 的 torch CPU 锁定和本地 ASR 默认 Windows 路径存在跨平台条件，见 [开发指南](../docs/DEVELOPMENT.md)。
