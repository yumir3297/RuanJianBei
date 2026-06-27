# Dashboard 图表化升级实施报告

## 1. 实施结果

已按 `docs/Dashboard图表化升级-任务书-Codex.md` 将管理后台总览页从文字骨架升级为图表化运营看板。

本轮没有修改后端 API、数据库、游客端问答、SSE 或 Live2D 业务逻辑。

## 2. 依赖安装

在 D 盘前端项目中安装：

```text
echarts@6.1.0
```

修改文件：

1. `frontend/package.json`
2. `frontend/package-lock.json`

ECharts 使用按需模块：

1. `PieChart`
2. `BarChart`
3. `TooltipComponent`
4. `LegendComponent`
5. `GridComponent`
6. `AriaComponent`
7. `CanvasRenderer`

## 3. Dashboard 功能

重写 `frontend/src/views/admin/Dashboard.vue`，新增：

1. 知识条目、问答日志、游客画像、FAQ 条目四张核心指标卡。
2. 基于真实 `overview` 数据的“知识资产构成”环形图。
3. “近 7 天问答量趋势”柱状图。
4. 对趋势图明确标注“演示数据”，避免将模拟数据冒充真实运营数据。
5. 7 项真实详细统计。
6. 数据刷新时间和手动刷新按钮。
7. 加载、错误、空数据和重试状态。
8. ECharts `ResizeObserver` 自适应。
9. 组件卸载时图表实例销毁。
10. 桌面、平板和移动端响应式布局。

## 4. 数据真实性

当前 SQLite 真实数据验证结果：

```text
知识条目：38
知识切块：66
问答日志：272
游客画像：2
问答缓存：76
FAQ 条目：88
路线模板：3
行为样本：140447
```

知识资产环形图真实总量为 `195`：

```text
38 个知识条目 + 66 个知识切块 + 88 个 FAQ + 3 条路线
```

现有后端没有回答路径占比和逐日问答趋势接口，因此：

1. 不使用误导性的“回答路径分布”名称。
2. 环形图改为真实的“知识资产构成”。
3. 趋势柱状图按任务书使用演示数据，并在页面显式说明。

## 5. 性能处理

新增 Dashboard 路由级懒加载：

```text
/admin/dashboard -> Dashboard 独立异步块
```

生产构建产物：

```text
Dashboard JS：约 536 KB，gzip 约 184 KB
Dashboard CSS：约 4.5 KB，gzip 约 1.3 KB
```

ECharts 没有混入游客端主入口标识，只有进入管理总览页时才加载图表块。

## 6. 验证结果

```text
ECharts 安装：通过
路由脚本语法检查：通过
真实后端 endpoint 数据读取：通过
前端开发路由 HTTP：200
前端生产构建：通过
```

构建仍有项目既有的大 chunk 警告。当前主包体积主要来自游客端同步加载的 Live2D/Pixi，不属于本轮 Dashboard 图表块。

当前桌面会话的内置浏览器测试环境无法创建临时执行资源，因此没有完成自动截图式验收。需要人工打开：

```text
http://127.0.0.1:5173/admin/dashboard
```

检查四张指标卡、环形图、柱状图和详细统计的最终视觉效果。

## 7. 依赖安全审计

`npm audit --omit=dev` 显示 3 个现有生产依赖告警：

1. `axios -> form-data@4.0.5`：高危，可通过后续受控升级处理。
2. `pixi-live2d-display@0.4.0 -> gh-pages@4.0.0`：严重。
3. Live2D 的自动修复建议是降级到 `pixi-live2d-display@0.3.1`，属于跨主版本变更，可能破坏当前数字人，未擅自执行。

`echarts@6.1.0` 本身没有出现在漏洞列表中。

