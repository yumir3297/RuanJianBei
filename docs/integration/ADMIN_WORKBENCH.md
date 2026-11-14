# 管理端浅色工作台接入

## 实现

拆分管理端入口 `frontend/apps/admin/main.js` 加载 `frontend/src/assets/admin-workbench.css`；`frontend/apps/admin/App.vue` 负责白色侧栏、浅绿选中态、分组导航和窄屏横向导航。各路由继续使用 `frontend/src/views/admin/` 中的业务页面，鉴权、管理 API 和游客端入口保持独立。知识管理在列表加载失败时区分不可用与空列表；旧快照明确标记可能过期，并暂停发布选中草稿。

参考设计为管理端浅色交互稿与原 `admin-workbench.css`。它们是工作台的视觉依据，实际页面保留现有知识导入、发布、GuideLoop 和其他已接入能力，不能用演示稿替换真实业务。

## 验证（2026-11-14）

- 在隔离 SQLite、模拟模型供应商、本地 API、双 Vite 和 Chrome 中，以 1440、736、390 像素检查七个管理路由、选中导航、侧栏配色与页面横向溢出；无浏览器页面异常。
- 相同隔离服务下完成 GuideLoop 绑定知识、审核发布、复测确认、游客 SSE 回答及下架后失效。测试数据为合成数据。
- 使用模拟接口返回 503，确认知识列表不可用时不显示空库提示；见 `frontend/tests/e2e/admin-workbench-smoke.mjs`。该脚本默认要求显式 `DEMO_SYNTHETIC_CONFIRM=1` 和隔离环境密码，`DEMO_MOCK_API=1` 可用来模拟 API 错误。
- 前端单元测试 273 项、双端构建、应用依赖与构建隔离检查通过。构建存在大资源块警告；这些检查不代表真机、真实资料或生产环境验收。

管理员工作台颜色和布局仅作用于 `.admin-layout`；游客应用不引入管理端样式。涉及布局、路由或验证方式的变更应同步本文件及 `docs/REPO_MAP.md`。
