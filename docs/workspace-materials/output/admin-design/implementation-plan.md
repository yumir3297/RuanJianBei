# 管理端视觉重构 Implementation Plan

> **For agentic workers:** 执行时按任务逐项完成，并复核当前工作区已有修改。

**Goal:** 将管理员端改为以景区知识运营为中心、密度适中且状态可信的浅色后台。

**Architecture:** 保留 Vue 3、Element Plus、现有路由、stores、API 和业务数据定义。用后台专属 token 与壳布局统一导航；逐页调整现有 admin views 的信息层级，避免更改游客共享样式。只展示当前真实 API 提供的能力。

**Tech Stack:** Vue 3、Vite、Element Plus、现有 ECharts。

**Spec:** `output/admin-design/design-review.md` 与 `output/admin-design/design.md`。

## Global Constraints

- 不改 `sources/`。
- 不重写用户现有未提交改动；不修改共享 `guide-page.css`。
- 不新增 API 字段、指标含义或待开发操作。
- 管理操作维持现有鉴权和 API 行为。
- 移动端 390px 无横向页面溢出，编辑输入字号至少 16px。

## Review Focus

- 空/失败数据不可显示成有效的零值。
- 长知识标题、正文和游客问法须能换行查看。
- 页面导航名称和现有路由保持对应。
- 编辑返回不得丢失未保存更改。
- 资源保存与游客端发布状态不得混淆。

## Files

- Modify `frontend/src/App.vue`：后台导航分组、无虚构的状态/账号、管理壳响应式样式。
- Create `frontend/src/assets/admin-workbench.css`：后台独立的色彩、间距、表格、表单与响应式 token。
- Modify `frontend/src/main.js`：导入后台样式。
- Modify `frontend/src/views/admin/Dashboard.vue`：突出待处理事项，整理真实统计和运维工具。
- Modify `frontend/src/views/admin/KnowledgeManage.vue`：整理查询、列表、编辑工作区，保留现有数据/API。
- Modify `frontend/src/views/admin/BlindSpotManage.vue`：突出游客原问法与处理动作。
- Modify `frontend/src/views/admin/AvatarConfig.vue`：预览与设置分栏，维持真实控件。
- Modify `frontend/src/views/admin/DisplayAssets.vue`：按品牌、模块、媒体分组，使用现有字段。
- Modify `frontend/src/views/admin/AnalyticsReport.vue` 与 `ExperienceReport.vue`：简化重复卡片及分析层级，不更改统计口径。
- Existing tests untouched; build used as compilation validation.

## Steps

1. 更新 App admin nav，使用导航分组、业务用语、移除硬编码运行状态/虚构邮箱。保留全部路径。
2. 新增后台 CSS token 和 scoped-safe 元素，接入 main；核对游客页面的样式隔离。
3. 重排 Dashboard、KnowledgeManage、BlindSpotManage 页面，以现有加载、空、错误和提交态为准。
4. 重排 AvatarConfig、DisplayAssets 页面，不提供未接入功能的伪按钮。
5. 整理两张分析报告，不引入新指标，不把缺失数据显示为零。
6. 运行 `npm run build` 并查看 `git diff --check`；审阅所有后台页面改动是否修改 API 和数据边界。

## 实施与验收记录

状态：前端重构完成。

- 管理导航、后台专属样式与 7 个管理员路由均已实施；游客共享样式与 API 契约未纳入本次改动。
- 总览、知识管理、知识盲区、数字人配置、页面与素材、问答分析、游客反馈均使用隔离的空数据接口完成浏览器渲染检查。
- 390px、736px、1024px 视口下，7 个路由均无页面横向溢出；浏览器未报告页面运行异常。
- 空库入口、数据不可用/空状态、未保存更改保护已纳入检查；构建命令 `npm run build` 与 `git diff --check` 通过。
- 本次浏览器检查使用隔离模拟 API。真实后端未启动：当前启动生命周期会执行数据库迁移、写入演示记录并预加载约 1.5GB 的嵌入与重排模型，因此本次不将其作为前端布局验收的前置条件；真实业务数据与接口端到端流程仍需在完整本地服务环境验证。
