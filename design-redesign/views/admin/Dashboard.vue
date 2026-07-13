<template>
  <section class="dashboard-layout">
    <header class="panel-card dashboard-hero">
      <div>
        <span class="eyebrow">SCENIC INTELLIGENCE</span>
        <h2>管理后台总览</h2>
        <p>汇集知识资产、游客服务与运营样本，快速了解 AI 导览系统当前状态。</p>
      </div>
      <div class="hero-actions">
        <span v-if="lastUpdatedAt" class="updated-at">更新于 {{ lastUpdatedAt }}</span>
        <el-button :loading="loading" @click="loadDashboard">刷新数据</el-button>
      </div>
    </header>

    <el-alert
      v-if="errorMessage"
      type="warning"
      :title="errorMessage"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadDashboard">重新加载</el-button>
      </template>
    </el-alert>

    <div class="stat-grid" v-loading="loading">
      <article
        v-for="card in topCards"
        :key="card.key"
        class="stat-card"
        :style="{ '--accent': card.accent, '--accent-soft': card.soft }"
      >
        <div class="stat-card-top">
          <span class="stat-icon">
            <el-icon><component :is="card.icon" /></el-icon>
          </span>
          <span class="stat-kicker">{{ card.kicker }}</span>
        </div>
        <strong class="stat-value">{{ formatNumber(card.value) }}</strong>
        <span class="stat-label">{{ card.label }}</span>
      </article>
    </div>

    <div class="chart-row">
      <article class="panel-card chart-card">
        <div class="chart-heading">
          <div>
            <span class="chart-kicker">REAL DATA</span>
            <h3>知识资产构成</h3>
            <p>基于当前数据库中的 FAQ、知识条目、切块与路线模板。</p>
          </div>
          <span class="chart-total">{{ formatNumber(assetTotal) }} 项</span>
        </div>
        <div v-if="assetTotal > 0" ref="pieChartRef" class="chart-box" aria-label="知识资产构成环形图" />
        <el-empty v-else class="chart-empty" description="暂无知识资产数据" />
      </article>

      <article class="panel-card chart-card">
        <div class="chart-heading">
          <div>
            <div class="chart-title-line">
              <span class="chart-kicker">TREND PREVIEW</span>
              <el-tag size="small" type="warning" effect="plain">演示数据</el-tag>
            </div>
            <h3>近 7 天问答量趋势</h3>
            <p>当前后端尚未提供逐日趋势接口，此图仅用于展示大屏能力。</p>
          </div>
          <span class="chart-total">{{ formatNumber(trendTotal) }} 次</span>
        </div>
        <div ref="barChartRef" class="chart-box" aria-label="近七天问答量演示柱状图" />
      </article>
    </div>

    <article class="panel-card detail-card">
      <div class="detail-heading">
        <div>
          <span class="chart-kicker">OPERATION SNAPSHOT</span>
          <h3>详细统计</h3>
        </div>
        <span>{{ adminStore.analytics.length }} 项指标</span>
      </div>

      <el-skeleton v-if="loading && !adminStore.analytics.length" :rows="3" animated />
      <div v-else-if="adminStore.analytics.length" class="detail-grid">
        <div
          v-for="(item, index) in adminStore.analytics"
          :key="item.label"
          class="detail-item"
        >
          <span class="detail-index">{{ String(index + 1).padStart(2, "0") }}</span>
          <span class="detail-label">{{ item.label }}</span>
          <strong>{{ formatNumber(item.value) }}</strong>
        </div>
      </div>
      <el-empty v-else description="暂无详细统计数据" />
    </article>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import {
  ChatDotRound,
  Collection,
  Tickets,
  UserFilled,
} from "@element-plus/icons-vue";
import { BarChart, PieChart } from "echarts/charts";
import {
  AriaComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import { init, use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";

import { useAdminStore } from "../../stores/admin";
import { fetchQATrend } from "../../api/insights";

use([
  AriaComponent,
  BarChart,
  CanvasRenderer,
  GridComponent,
  LegendComponent,
  PieChart,
  TooltipComponent,
]);

const adminStore = useAdminStore();
const pieChartRef = ref(null);
const barChartRef = ref(null);
const loading = ref(false);
const errorMessage = ref("");
const lastUpdatedAt = ref("");

const trendDays = ref([]);
const trendValues = ref([]);
const numberFormatter = new Intl.NumberFormat("zh-CN");

let pieChart = null;
let barChart = null;
let resizeObserver = null;

const topCards = computed(() => {
  const overview = adminStore.overview || {};
  return [
    {
      key: "knowledge",
      label: "知识条目",
      kicker: "KNOWLEDGE",
      value: overview.knowledge_count ?? 0,
      icon: Collection,
      accent: "#0f766e",
      soft: "#dff7f2",
    },
    {
      key: "chat-log",
      label: "问答日志",
      kicker: "CONVERSATION",
      value: overview.chat_log_count ?? 0,
      icon: ChatDotRound,
      accent: "#c2410c",
      soft: "#ffeadc",
    },
    {
      key: "visitor",
      label: "游客画像",
      kicker: "VISITOR",
      value: overview.visitor_count ?? 0,
      icon: UserFilled,
      accent: "#1d4ed8",
      soft: "#e3edff",
    },
    {
      key: "faq",
      label: "FAQ 条目",
      kicker: "FAST ANSWER",
      value: overview.faq_count ?? 0,
      icon: Tickets,
      accent: "#a16207",
      soft: "#fff4cf",
    },
  ];
});

const pieData = computed(() => {
  const overview = adminStore.overview || {};
  return [
    { name: "FAQ 条目", value: overview.faq_count ?? 0 },
    { name: "知识条目", value: overview.knowledge_count ?? 0 },
    { name: "知识切块", value: overview.chunk_count ?? 0 },
    { name: "路线模板", value: overview.route_count ?? 0 },
  ].filter((item) => item.value > 0);
});

const assetTotal = computed(() =>
  pieData.value.reduce((total, item) => total + item.value, 0),
);
const trendTotal = computed(() =>
  trendValues.value.reduce((total, value) => total + value, 0),
);

function formatNumber(value) {
  return numberFormatter.format(Number(value) || 0);
}

function formatUpdatedAt() {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());
}

function renderPieChart() {
  if (!pieChartRef.value || !pieData.value.length) {
    pieChart?.dispose();
    pieChart = null;
    return;
  }

  pieChart ||= init(pieChartRef.value);
  pieChart.setOption(
    {
      animationDuration: 700,
      color: ["#0f766e", "#2563eb", "#d97706", "#e05a36"],
      aria: {
        enabled: true,
        decal: { show: true },
      },
      tooltip: {
        trigger: "item",
        formatter: ({ marker, name, value, percent }) =>
          `${marker}${name}<br/>${formatNumber(value)} 项 · ${percent}%`,
      },
      legend: {
        bottom: 0,
        icon: "circle",
        itemWidth: 9,
        itemHeight: 9,
        textStyle: { color: "#475569" },
      },
      series: [
        {
          name: "知识资产",
          type: "pie",
          radius: ["48%", "72%"],
          center: ["50%", "43%"],
          avoidLabelOverlap: true,
          itemStyle: {
            borderColor: "#ffffff",
            borderRadius: 7,
            borderWidth: 3,
          },
          label: {
            color: "#334155",
            formatter: "{b}\n{d}%",
            lineHeight: 18,
          },
          labelLine: {
            length: 12,
            length2: 8,
          },
          data: pieData.value,
        },
      ],
    },
    true,
  );
}

function renderBarChart() {
  if (!barChartRef.value) {
    return;
  }

  barChart ||= init(barChartRef.value);
  barChart.setOption(
    {
      animationDuration: 800,
      aria: { enabled: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        valueFormatter: (value) => `${formatNumber(value)} 次`,
      },
      grid: {
        top: 24,
        right: 12,
        bottom: 28,
        left: 44,
      },
      xAxis: {
        type: "category",
        data: trendDays.value,
        axisTick: { show: false },
        axisLine: { lineStyle: { color: "#cbd5e1" } },
        axisLabel: { color: "#64748b" },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        splitLine: { lineStyle: { color: "#edf2f7" } },
        axisLabel: { color: "#64748b" },
      },
      series: [
        {
          name: "问答量",
          type: "bar",
          data: trendValues.value,
          barMaxWidth: 36,
          itemStyle: {
            borderRadius: [8, 8, 2, 2],
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: "#14b8a6" },
                { offset: 1, color: "#0f766e" },
              ],
            },
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 16,
              shadowColor: "rgba(15, 118, 110, 0.28)",
            },
          },
        },
      ],
    },
    true,
  );
}

async function renderCharts() {
  await nextTick();
  renderPieChart();
  renderBarChart();
}

async function loadDashboard() {
  if (loading.value) {
    return;
  }

  loading.value = true;
  errorMessage.value = "";
  try {
    await adminStore.loadDashboard();

    const trendData = await fetchQATrend();
    if (Array.isArray(trendData?.daily_trend)) {
      const recentTrend = trendData.daily_trend.slice(-7);
      trendDays.value = recentTrend.map(item => {
        const date = new Date(item.date);
        return Number.isNaN(date.getTime())
          ? item.date
          : new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(date);
      });
      trendValues.value = recentTrend.map(item => Number(item.count) || 0);
    } else {
      trendDays.value = [];
      trendValues.value = [];
    }

    lastUpdatedAt.value = formatUpdatedAt();
    await renderCharts();
  } catch (error) {
    errorMessage.value = `数据加载失败：${error?.response?.data?.detail || error.message || "请检查后端服务"}`;
  } finally {
    loading.value = false;
  }
}

function handleResize() {
  pieChart?.resize();
  barChart?.resize();
}

function observeCharts() {
  if (typeof ResizeObserver === "undefined") {
    window.addEventListener("resize", handleResize);
    return;
  }

  resizeObserver = new ResizeObserver(handleResize);
  if (pieChartRef.value) {
    resizeObserver.observe(pieChartRef.value);
  }
  if (barChartRef.value) {
    resizeObserver.observe(barChartRef.value);
  }
}

onMounted(async () => {
  await loadDashboard();
  await nextTick();
  observeCharts();
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  window.removeEventListener("resize", handleResize);
  pieChart?.dispose();
  barChart?.dispose();
  pieChart = null;
  barChart = null;
});
</script>

<style scoped>
.dashboard-layout {
  display: grid;
  gap: 20px;
}

.dashboard-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 30px;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: none;
}

.eyebrow,
.chart-kicker,
.stat-kicker {
  font-family: Georgia, "Times New Roman", serif;
  letter-spacing: 0.14em;
}

.eyebrow {
  color: var(--text-secondary);
  font-size: 11px;
}

.dashboard-hero h2 {
  margin: 8px 0 6px;
  font-size: 24px;
  font-weight: 600;
  color: var(--text);
}

.dashboard-hero p {
  max-width: 680px;
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.65;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.updated-at {
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  display: grid;
  min-height: 120px;
  gap: 6px;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
}

.stat-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.stat-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 12px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 20px;
}

.stat-kicker {
  color: color-mix(in srgb, var(--accent) 74%, #64748b);
  font-size: 9px;
}

.stat-value {
  margin-top: 10px;
  color: #0f172a;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(30px, 4vw, 42px);
  line-height: 1;
}

.stat-label {
  color: #64748b;
  font-size: 13px;
}

.chart-row {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
  gap: 16px;
}

.chart-card,
.detail-card {
  min-width: 0;
  padding: 22px;
}

.chart-heading,
.detail-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.chart-heading h3,
.detail-heading h3 {
  margin: 5px 0 4px;
  color: #0f172a;
  font-family: Georgia, "STSong", serif;
  font-size: 20px;
}

.chart-heading p {
  max-width: 460px;
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.chart-kicker {
  color: #0f766e;
  font-size: 9px;
}

.chart-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-total {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f0fdfa;
  color: #0f766e;
  font-weight: 700;
  white-space: nowrap;
}

.chart-box {
  width: 100%;
  height: 310px;
  margin-top: 8px;
}

.chart-empty {
  min-height: 310px;
}

.detail-heading {
  align-items: flex-end;
  padding-bottom: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.detail-heading > span {
  color: #64748b;
  font-size: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.detail-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 13px 14px;
  border-radius: 12px;
  background: #f8fafc;
}

.detail-index {
  color: #94a3b8;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 11px;
}

.detail-label {
  color: #475569;
  font-size: 13px;
}

.detail-item strong {
  color: #0f766e;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 18px;
}

@media (max-width: 1080px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chart-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .dashboard-hero {
    align-items: flex-start;
    flex-direction: column;
    padding: 24px;
  }

  .hero-actions {
    width: 100%;
    justify-content: space-between;
  }

  .stat-grid {
    grid-template-columns: 1fr;
  }

  .chart-heading,
  .detail-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .chart-box {
    height: 280px;
  }
}
</style>
