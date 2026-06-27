# Dashboard 图表化升级执行计划

## 1. 当前状态

管理后台 `Dashboard.vue` 当前只展示四个数字卡片和文字统计列表。现有后端已经提供：

1. `GET /api/admin/overview`：8 个真实概览指标。
2. `GET /api/admin/analytics`：7 个真实汇总指标。

本轮按照 `docs/Dashboard图表化升级-任务书-Codex.md` 升级管理总览页。

## 2. 本轮实施范围

### 2.1 安装 ECharts

在 `frontend` 项目内安装 `echarts`，依赖和缓存仍位于 D 盘项目环境，不安装到系统盘。

### 2.2 重写 Dashboard

修改 `frontend/src/views/admin/Dashboard.vue`：

1. 四张核心指标卡片。
2. 使用真实 overview 数据绘制“知识资产构成”环形图。
3. 绘制“近 7 天问答量趋势”柱状图。
4. 柱状图因当前后端没有逐日趋势接口，按任务书使用演示数据，并在页面明确标注，避免冒充真实数据。
5. 展示 7 项真实详细统计。
6. 增加加载、错误、空数据和重试状态。
7. 图表支持窗口缩放和组件卸载清理。

### 2.3 ECharts 接入方式

采用 `echarts/core` 按需导入：

1. `PieChart`。
2. `BarChart`。
3. `TooltipComponent`、`LegendComponent`、`GridComponent`。
4. `CanvasRenderer`。

不使用完整包全量注册，控制新增构建体积。

## 3. 数据真实性说明

1. 指标卡、环形图和详细统计均来自现有真实 API。
2. 当前 API 无法计算 FAQ、LLM、盲区的真实回答路径占比，因此不使用“回答路径分布”这一误导名称。
3. 当前 API 没有近 7 天逐日问答量，柱状图将明确标记为演示趋势。
4. 本轮不为补趋势数据而修改后端，遵守任务书边界。

## 4. 明确不做

1. 不修改后端 API。
2. 不修改 `ChatView.vue`。
3. 不修改 `index.html`。
4. 不修改数据库和 SSE。
5. 不接入付费 API。
6. 不更改 Live2D 依赖和数字人链路。

## 5. 验收标准

1. `echarts` 安装到前端本地依赖。
2. `/admin/dashboard` 显示四张指标卡、环形图、柱状图和详细统计。
3. API 失败时显示错误和重试入口。
4. 空数据时图表不崩溃。
5. 桌面和窄屏布局可用。
6. `npm.cmd run build` 通过。
7. 页面浏览器检查无运行时错误。
