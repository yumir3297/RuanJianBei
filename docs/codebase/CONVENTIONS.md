# Coding Conventions

> 以下是仓库中可观察到的惯例，不是尚未落地的团队规范。

## Core Sections (Required)

### 1) Naming Rules

- Python 文件、函数和变量使用 `snake_case`，类/Schema/ORM Model 使用 `PascalCase`，常量和环境变量使用 `UPPER_SNAKE_CASE`，内部辅助函数以 `_` 开头。
- Vue 页面和组件使用 `PascalCase.vue`；composable 使用 `useXxx.js`；JavaScript 变量和函数使用 `camelCase`。
- 测试文件统一使用 `test_*.py`；前端页面分别位于 `views/tourist` 和 `views/admin`。

### 2) Formatting and Linting

- Python 以 4 空格缩进、类型注解、docstring 和分组导入为主；Vue/JavaScript 以 2 空格缩进为主。
- Vue 组件通常按 `<script setup>`、`<template>`、`<style scoped>` 组织。
- `[TODO]` 未发现 Ruff/Black/isort/mypy、ESLint/Prettier/Stylelint、pre-commit 或 CI 质量门禁；新代码应先遵循邻近文件，并补充机器可执行规范。

### 3) Import and Module Conventions

- 后端使用 `app.*` 绝对导入，通常按标准库、第三方库、项目模块分组。
- API 契约由 `app/schemas` 定义，ORM 对象不应直接代替外部契约；跨域逻辑优先通过 service/repository 交互。
- 前端使用相对导入，Vite 配置中未见统一路径别名。
- 新外部服务实现应遵循所在能力目录的 Base/Provider 接口，并在配置/组装位置注册。

### 4) Error and Logging Conventions

- API 业务拒绝通常使用 FastAPI `HTTPException`；共享异常处理位于 `backend/app/core/exceptions.py`。
- provider 普遍设置超时、包装外部异常；问答 pipeline 决定回退到 FAQ、缓存、本地服务或 stub。
- 后端使用标准库 `logging`，常记录 provider、状态与 request ID。日志不应输出完整密钥、原始音频或游客敏感文本。
- `[TODO]` 未见正式的脱敏、结构化日志字段和全链路 correlation 规范。
- 当前未知异常处理会把 `str(exc)` 返回客户端，这是待修复偏差，不是推荐惯例。

### 5) Testing Conventions

- 后端测试位于 `backend/app/tests/test_*.py`，系统评测测试位于 `eval/tests/test_*.py`。
- 使用 pytest 普通 `assert`；异步路径常以 `asyncio.run` 执行。
- 外部 HTTP 通过 HTTPX `MockTransport` 或 dummy provider 隔离；路由通过 TestClient/依赖覆盖测试。
- 真实网络 smoke 脚本位于 `eval/scripts`，不应进入默认离线测试。
- 前端当前没有自动化测试工具；修改后至少运行 `npm run build` 并手工回归关键游客链路。

### 6) Evidence

- `backend/app/core/config.py`
- `backend/app/core/exceptions.py`
- `backend/app/api/chat.py`
- `backend/app/services/asr/base.py`
- `backend/app/services/qa/pipeline.py`
- `backend/app/tests/test_pipeline.py`
- `backend/app/tests/test_llm_openai_compatible.py`
- `frontend/src/router/index.js`
- `frontend/src/composables/useSSEStream.js`
- `frontend/src/components/ThreeAvatar.vue`
- `frontend/package.json`
- `frontend/vite.config.js`

