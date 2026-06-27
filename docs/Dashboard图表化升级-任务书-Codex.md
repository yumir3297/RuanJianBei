# Dashboard 图表化升级 — 任务书（Codex 联网版）

> 目标：把管理后台 Dashboard 从数字列表升级为真实数据大屏
> 时间：1 小时
> 不改后端 API，不改 ChatView 和 index.html

---

## 当前状态

`Dashboard.vue` 是纯骨架：4 个静态卡片 + 一个 `<li>` 列表。后端 API 已返回 15 个指标（overview 8 个 + analytics 7 个），但前端只展示为文字。

---

## 目标

```
┌─────────────────────────────────────────────────┐
│  🏠 管理后台总览                                   │
├───────────┬───────────┬───────────┬─────────────┤
│ 📄 知识条目│ 💬 问答日志 │ 👤 游客画像│ 🏷️ FAQ条目  │
│    52     │   1,247   │    89     │    88      │
├───────────┴───────────┴───────────┴─────────────┤
│           📊 回答路径分布（饼图）                    │
│         FAQ 68%│LLM 22%│盲区 10%                │
├─────────────────────────────────────────────────┤
│           📈 近7天问答量趋势（柱状图）                │
│          █▆█▇██▅█  —— 周一 ~ 周日               │
└─────────────────────────────────────────────────┘
```

---

## 步骤 1：安装 ECharts

```bash
cd frontend
npm install echarts
```

---

## 步骤 2：重写 Dashboard.vue

**文件**：`frontend/src/views/admin/Dashboard.vue`

### 2.1 模板

```html
<template>
  <section class="dashboard-layout">
    <div class="panel-card dashboard-hero">
      <h2 class="section-title">管理后台总览</h2>
      <p class="section-subtitle">景区 AI 导览系统运营数据看板</p>
    </div>

    <!-- 指标卡片行 -->
    <div class="stat-grid" v-loading="adminStore.loading">
      <article class="stat-card" v-for="card in topCards" :key="card.key">
        <span class="stat-icon">{{ card.icon }}</span>
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
      </article>
    </div>

    <!-- 图表行 -->
    <div class="chart-row">
      <div class="panel-card chart-card">
        <h3>回答路径分布</h3>
        <div ref="pieChartRef" class="chart-box" />
      </div>
      <div class="panel-card chart-card">
        <h3>近7天问答量趋势</h3>
        <div ref="barChartRef" class="chart-box" />
      </div>
    </div>

    <!-- 详细指标表 -->
    <div class="panel-card detail-card">
      <h3>详细统计</h3>
      <div class="detail-grid">
        <div v-for="item in adminStore.analytics" :key="item.label" class="detail-item">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
        </div>
      </div>
    </div>
  </section>
</template>
```

### 2.2 Script

```js
<script setup>
import { computed, onMounted, onBeforeUnmount, ref, nextTick } from "vue";
import * as echarts from "echarts";
import { useAdminStore } from "../../stores/admin";

const adminStore = useAdminStore();
const pieChartRef = ref(null);
const barChartRef = ref(null);
let pieChart = null;
let barChart = null;

// 顶部 4 个指标卡片，从 overview 取数据
const topCards = computed(() => {
  const o = adminStore.overview || {};
  return [
    { key: "knowledge", icon: "📄", label: "知识条目", value: o.knowledge_count ?? 0 },
    { key: "chatlog",  icon: "💬", label: "问答日志", value: o.chat_log_count ?? 0 },
    { key: "visitor",  icon: "👤", label: "游客画像", value: o.visitor_count ?? 0 },
    { key: "faq",      icon: "🏷️", label: "FAQ 条目", value: o.faq_count ?? 0 },
  ];
});

// 饼图数据：从 analytics 里推断分布
// analytics 包含: 知识条目数, 知识切块数, FAQ条目数, 路线模板数, 问答日志数, 游客画像数, 行为样本行数
// 问答日志中 FAQ 命中和 LLM 生成的比例无法从当前 API 精确获得，先用 FAQ条目数/总条目数做近似
// （后续可扩展后端 API 返回 real breakdown）
function buildPieData() {
  const o = adminStore.overview || {};
  const faq = o.faq_count ?? 0;
  const knowledge = o.knowledge_count ?? 0;
  const route = o.route_count ?? 0;
  const chunk = o.chunk_count ?? 0;
  return [
    { name: "FAQ 条目", value: faq },
    { name: "知识条目", value: knowledge },
    { name: "知识切块", value: chunk },
    { name: "路线模板", value: route },
  ].filter((d) => d.value > 0);
}

function initPieChart() {
  if (!pieChartRef.value) return;
  pieChart = echarts.init(pieChartRef.value);
  pieChart.setOption({
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
        label: { show: false },
        data: buildPieData(),
      },
    ],
  });
}

function initBarChart() {
  if (!barChartRef.value) return;
  barChart = echarts.init(barChartRef.value);

  // 近 7 天趋势暂时用固定 mock 数据
  // 后续接真实 API 后替换 /api/admin/chat-logs/daily-trend
  const days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
  const values = [42, 58, 35, 67, 89, 120, 75];

  barChart.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: days },
    yAxis: { type: "value", minInterval: 1 },
    series: [
      {
        type: "bar",
        data: values,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "#6366f1" },
            { offset: 1, color: "#a78bfa" },
          ]),
        },
      },
    ],
    grid: { top: 20, bottom: 30, left: 40, right: 20 },
  });
}

// 窗口缩放自适应
function handleResize() {
  pieChart?.resize();
  barChart?.resize();
}

onMounted(async () => {
  await adminStore.loadDashboard();
  await nextTick();
  initPieChart();
  initBarChart();
  window.addEventListener("resize", handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  pieChart?.dispose();
  barChart?.dispose();
});
</script>
```

### 2.3 Style

```css
<style scoped>
.dashboard-layout {
  display: grid;
  gap: 20px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.stat-icon {
  font-size: 24px;
}

.stat-label {
  color: #64748b;
  font-size: 13px;
}

.stat-value {
  font-size: 32px;
  color: #1e293b;
}

.chart-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  padding: 20px;
}

.chart-card h3 {
  margin: 0 0 12px;
}

.chart-box {
  width: 100%;
  height: 280px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 8px;
  background: #f8fafc;
}

@media (max-width: 980px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .chart-row {
    grid-template-columns: 1fr;
  }
}
</style>
```

---

## 数据来源

```
后端 API                    → 前端消费
GET /api/admin/overview     → adminStore.overview（8 个字段）
GET /api/admin/analytics    → adminStore.analytics（7 个条目）
```

**后端不改。** 柱状图先用 mock 数据展示图表能力，饼图用 real 数据。

---

## 验证

```bash
cd frontend
npm run build
```

导航到 `/admin` → 看到 4 个彩色指标卡片 + 饼图 + 柱状图。

---

## 文件清单

```
frontend/package.json                       ← 新增 echarts
frontend/src/views/admin/Dashboard.vue      ← 重写
```

不改后端，不改 ChatView，不改 index.html。和 Live2D 零冲突。
