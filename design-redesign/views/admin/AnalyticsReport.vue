<template>
  <section class="analytics-layout">
    <header class="panel-card analytics-hero">
      <div class="hero-copy">
        <span class="eyebrow">OPERATIONS INTELLIGENCE</span>
        <h2>运营分析与知识盲区</h2>
        <p>把游客问答、景点关注和知识缺口放在同一张运营视图中，便于答辩展示与后台运营闭环。</p>
        <div class="hero-tags">
          <span class="hero-tag">真实数据优先</span>
          <span class="hero-tag">支持盲区补录</span>
          <span class="hero-tag">适配答辩展示</span>
        </div>
      </div>
      <div class="hero-actions">
        <span v-if="lastUpdatedAt" class="updated-at">更新于 {{ lastUpdatedAt }}</span>
        <el-button :loading="loading.page" @click="loadAnalytics">刷新数据</el-button>
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
        <el-button link type="primary" @click="loadAnalytics">重新加载</el-button>
      </template>
    </el-alert>

    <div class="summary-grid">
      <article
        v-for="card in summaryCards"
        :key="card.key"
        class="summary-card"
        :style="{ '--accent': card.accent, '--accent-soft': card.soft }"
      >
        <div class="summary-top">
          <span class="summary-kicker">{{ card.kicker }}</span>
          <span class="summary-label">{{ card.label }}</span>
        </div>
        <strong class="summary-value">{{ card.value }}</strong>
        <p class="summary-note" :title="card.note">{{ card.note }}</p>
      </article>
    </div>

    <div class="chart-grid">
      <article class="panel-card chart-card">
        <div class="card-heading">
          <div>
            <span class="card-kicker">ATTENTION HEATMAP</span>
            <h3>景点关注度排名</h3>
            <p>基于历史问答来源统计，帮助判断游客最关注的景点内容。</p>
          </div>
          <span class="card-total">{{ formatNumber(spotAttentionTotal) }} 次</span>
        </div>
        <el-skeleton v-if="loading.spotChart" :rows="6" animated />
        <el-empty v-else-if="!spotAttention.length" class="chart-empty" description="暂无景点关注数据" />
        <div v-else ref="spotChartRef" class="chart-box" aria-label="景点关注度排名图" />
      </article>

      <article class="panel-card chart-card">
        <div class="card-heading">
          <div>
            <span class="card-kicker">AUDIENCE PROFILE</span>
            <h3>游客群体构成</h3>
            <p>来自游客画像与偏好标签，用于判断讲解内容和服务重点。</p>
          </div>
          <span class="card-total">{{ formatNumber(visitorAudienceTotal) }} 人</span>
        </div>
        <el-skeleton v-if="loading.visitorChart" :rows="6" animated />
        <el-empty v-else-if="!visitorAudience.length" class="chart-empty" description="暂无游客画像数据" />
        <template v-else>
          <div ref="visitorPieRef" class="chart-box" aria-label="游客群体构成图" />
          <div v-if="topVisitorTags.length" class="tag-cloud">
            <span class="tag-cloud-label">热门偏好</span>
            <span
              v-for="item in topVisitorTags"
              :key="item.tag"
              class="tag-chip"
            >
              {{ item.tag }} · {{ formatNumber(item.count) }}
            </span>
          </div>
        </template>
      </article>
    </div>

    <div class="chart-grid">
      <article class="panel-card chart-card">
        <div class="card-heading">
          <div>
            <span class="card-kicker">THIRTY DAY TREND</span>
            <h3>近 30 天问答量趋势</h3>
            <p>直接读取真实问答日志，用于展示近阶段服务热度与波峰变化。</p>
          </div>
          <span class="card-total">{{ formatNumber(trendTotal) }} 次</span>
        </div>
        <el-skeleton v-if="loading.trendChart" :rows="6" animated />
        <el-empty v-else-if="!trendDays.length" class="chart-empty" description="近 30 天暂无问答记录" />
        <div v-else ref="trendChartRef" class="chart-box" aria-label="近三十天问答量趋势图" />
      </article>

      <article class="panel-card chart-card">
        <div class="card-heading">
          <div>
            <span class="card-kicker">ANSWER ROUTES</span>
            <h3>问答路径分布</h3>
            <p>观察 FAQ、RAG 与盲区命中结构，判断知识库与回答路径的健康度。</p>
          </div>
          <span class="card-total">{{ formatNumber(hitDistributionTotal) }} 次</span>
        </div>
        <el-skeleton v-if="loading.hitChart" :rows="6" animated />
        <el-empty v-else-if="!hitDistribution.length" class="chart-empty" description="暂无问答路径数据" />
        <div v-else ref="hitChartRef" class="chart-box" aria-label="问答路径分布图" />
      </article>
    </div>

    <div class="detail-grid">
      <article class="panel-card blind-card">
        <div class="card-heading">
          <div>
            <div class="title-line">
              <span class="card-kicker">BLIND SPOT BACKLOG</span>
              <el-tag size="small" type="warning" effect="plain">待补录</el-tag>
            </div>
            <h3>知识库待补充问题 Top 10</h3>
            <p>高频未命中问题可直接转为 FAQ，是后台运营闭环的重点入口。</p>
          </div>
          <span class="card-total">{{ blindSpots.length }} 项</span>
        </div>
        <el-skeleton v-if="loading.blindTable" :rows="5" animated />
        <el-empty v-else-if="!blindSpots.length" description="当前没有待补问题" />
        <el-table v-else :data="blindSpots" stripe class="blind-table">
          <el-table-column label="排名" width="88">
            <template #default="{ row }">
              <span class="rank-badge">{{ String(row.rank).padStart(2, "0") }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="query" label="游客问题" min-width="260" />
          <el-table-column label="提问次数" width="120" align="right">
            <template #default="{ row }">
              <span class="hit-count">{{ formatNumber(row.hit_count) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </article>

      <article class="panel-card metrics-card">
        <div class="card-heading">
          <div>
            <span class="card-kicker">OPERATION SNAPSHOT</span>
            <h3>运营指标快照</h3>
            <p>用于答辩时快速说明知识资产、游客样本和后台当前服务规模。</p>
          </div>
          <span class="card-total">{{ analyticsItems.length }} 项</span>
        </div>
        <el-skeleton v-if="loading.metrics" :rows="5" animated />
        <el-empty v-else-if="!analyticsItems.length" description="暂无运营指标数据" />
        <div v-else class="metrics-list">
          <div
            v-for="(item, index) in analyticsItems"
            :key="item.label"
            class="metric-item"
          >
            <span class="metric-index">{{ String(index + 1).padStart(2, "0") }}</span>
            <span class="metric-label">{{ item.label }}</span>
            <strong>{{ formatNumber(item.value) }}</strong>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import * as echarts from "echarts";

import { fetchAdminAnalytics, fetchAdminOverview } from "../../api/admin";
import {
  fetchBlindSpotTop,
  fetchQATrend,
  fetchSpotAttention,
  fetchVisitorGroups,
} from "../../api/insights";

const spotChartRef = ref(null);
const visitorPieRef = ref(null);
const trendChartRef = ref(null);
const hitChartRef = ref(null);

const overview = ref({});
const analyticsItems = ref([]);
const blindSpots = ref([]);
const spotAttention = ref([]);
const visitorGroups = ref({
  audience_distribution: [],
  top_tags: [],
});
const trendPayload = ref({
  daily_trend: [],
  hit_distribution: [],
});

const loading = ref({
  page: false,
  spotChart: true,
  visitorChart: true,
  trendChart: true,
  hitChart: true,
  blindTable: true,
  metrics: true,
});

const errorMessage = ref("");
const lastUpdatedAt = ref("");

let spotChart = null;
let visitorPieChart = null;
let trendChart = null;
let hitChart = null;
let resizeObserver = null;

const numberFormatter = new Intl.NumberFormat("zh-CN");

const avgLatency = computed(() => {
  const avg = overview.value.avg_latency_ms ?? overview.value.avg_latency;
  if (avg != null) {
    return (Number(avg) / 1000).toFixed(1);
  }
  return overview.value.chat_log_count > 0 ? "--" : "0.0";
});

const trendDays = computed(() =>
  trendPayload.value.daily_trend.map((item) => item.date),
);
const hitDistribution = computed(() => trendPayload.value.hit_distribution || []);
const visitorAudience = computed(() =>
  visitorGroups.value.audience_distribution || [],
);
const topVisitorTags = computed(() =>
  (visitorGroups.value.top_tags || []).slice(0, 6),
);

const trendTotal = computed(() =>
  trendPayload.value.daily_trend.reduce(
    (total, item) => total + (Number(item.count) || 0),
    0,
  ),
);
const hitDistributionTotal = computed(() =>
  hitDistribution.value.reduce(
    (total, item) => total + (Number(item.count) || 0),
    0,
  ),
);
const visitorAudienceTotal = computed(() =>
  visitorAudience.value.reduce(
    (total, item) => total + (Number(item.count) || 0),
    0,
  ),
);
const spotAttentionTotal = computed(() =>
  spotAttention.value.reduce(
    (total, item) => total + (Number(item.count) || 0),
    0,
  ),
);
const hotBlindSpot = computed(() => blindSpots.value[0] || null);

const summaryCards = computed(() => [
  {
    key: "consultation",
    kicker: "CONSULTATION",
    label: "总咨询量",
    value: formatNumber(overview.value.chat_log_count || 0),
    note: "累计问答日志规模，体现导览服务使用热度。",
    accent: "#0f766e",
    soft: "#dff7f2",
  },
  {
    key: "latency",
    kicker: "LATENCY",
    label: "平均响应",
    value: `${avgLatency.value}s`,
    note:
      overview.value.chat_log_count > 0
        ? "按已记录问答日志计算的平均响应时长。"
        : "当前还没有足够的响应时长样本。",
    accent: "#c2410c",
    soft: "#ffeadc",
  },
  {
    key: "visitor",
    kicker: "VISITOR",
    label: "活跃游客",
    value: formatNumber(overview.value.visitor_count || 0),
    note:
      visitorAudience.value.length > 0
        ? `当前已沉淀 ${visitorAudience.value.length} 类游客分层。`
        : "等待更多游客画像与偏好数据沉淀。",
    accent: "#1d4ed8",
    soft: "#e3edff",
  },
  {
    key: "blind-spot",
    kicker: "BLIND SPOT",
    label: "待补高频问题",
    value: hotBlindSpot.value
      ? formatNumber(hotBlindSpot.value.hit_count)
      : formatNumber(blindSpots.value.length),
    note: hotBlindSpot.value
      ? hotBlindSpot.value.query
      : "当前没有高频待补问题。",
    accent: "#a16207",
    soft: "#fff4cf",
  },
]);

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

function setPartialWarning(failures) {
  if (!failures.length) {
    errorMessage.value = "";
    return;
  }

  if (failures.length >= 6) {
    errorMessage.value = "运营分析数据加载失败，请检查后端服务状态。";
    return;
  }

  errorMessage.value = `部分模块加载失败：${failures.join("、")}，其余数据已正常展示。`;
}

function renderSpotChart() {
  if (!spotChartRef.value || !spotAttention.value.length) {
    spotChart?.dispose();
    spotChart = null;
    return;
  }

  const data = [...spotAttention.value].slice(0, 8);
  spotChart ||= echarts.init(spotChartRef.value);
  spotChart.setOption(
    {
      animationDuration: 700,
      grid: {
        top: 18,
        right: 18,
        bottom: 14,
        left: 124,
      },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: ([item]) =>
          `${item.name}<br/>关注次数：${formatNumber(item.value)} 次`,
      },
      xAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#edf2f7" } },
        axisLabel: { color: "#64748b" },
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: data.map((item) => item.name),
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: {
          color: "#475569",
          width: 100,
          overflow: "truncate",
        },
      },
      series: [
        {
          type: "bar",
          data: data.map((item) => item.count),
          barMaxWidth: 16,
          itemStyle: {
            borderRadius: [0, 8, 8, 0],
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: "#7e9a83" },
                { offset: 1, color: "#4f6f58" },
              ],
            },
          },
        },
      ],
    },
    true,
  );
}

function renderVisitorPie() {
  if (!visitorPieRef.value || !visitorAudience.value.length) {
    visitorPieChart?.dispose();
    visitorPieChart = null;
    return;
  }

  visitorPieChart ||= echarts.init(visitorPieRef.value);
  visitorPieChart.setOption(
    {
      animationDuration: 700,
      color: ["#0f766e", "#3b82f6", "#d97706", "#e05a36", "#7c3aed"],
      tooltip: {
        trigger: "item",
        formatter: ({ marker, name, value, percent }) =>
          `${marker}${name}<br/>${formatNumber(value)} 人 · ${percent}%`,
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
          name: "游客群体",
          type: "pie",
          radius: ["46%", "72%"],
          center: ["50%", "43%"],
          avoidLabelOverlap: true,
          itemStyle: {
            borderColor: "#ffffff",
            borderWidth: 3,
            borderRadius: 8,
          },
          label: {
            color: "#334155",
            formatter: "{b}\n{d}%",
            lineHeight: 18,
          },
          data: visitorAudience.value.map((item) => ({
            name: item.group_label,
            value: item.count,
          })),
        },
      ],
    },
    true,
  );
}

function renderTrendChart() {
  if (!trendChartRef.value || !trendDays.value.length) {
    trendChart?.dispose();
    trendChart = null;
    return;
  }

  trendChart ||= echarts.init(trendChartRef.value);
  trendChart.setOption(
    {
      animationDuration: 800,
      tooltip: {
        trigger: "axis",
        valueFormatter: (value) => `${formatNumber(value)} 次`,
      },
      grid: {
        top: 22,
        right: 18,
        bottom: 30,
        left: 48,
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
          type: "line",
          smooth: true,
          data: trendPayload.value.daily_trend.map((item) => item.count),
          symbolSize: 7,
          lineStyle: {
            width: 3,
            color: "#b8894f",
          },
          itemStyle: {
            color: "#b8894f",
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(184, 137, 79, 0.32)" },
              { offset: 1, color: "rgba(184, 137, 79, 0.04)" },
            ]),
          },
        },
      ],
    },
    true,
  );
}

function renderHitChart() {
  if (!hitChartRef.value || !hitDistribution.value.length) {
    hitChart?.dispose();
    hitChart = null;
    return;
  }

  const data = [...hitDistribution.value].sort(
    (left, right) => right.count - left.count,
  );

  hitChart ||= echarts.init(hitChartRef.value);
  hitChart.setOption(
    {
      animationDuration: 700,
      grid: {
        top: 18,
        right: 18,
        bottom: 14,
        left: 116,
      },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: ([item]) =>
          `${item.name}<br/>命中次数：${formatNumber(item.value)} 次`,
      },
      xAxis: {
        type: "value",
        splitLine: { lineStyle: { color: "#f1f5f9" } },
        axisLabel: { color: "#64748b" },
      },
      yAxis: {
        type: "category",
        inverse: true,
        data: data.map((item) => item.label),
        axisTick: { show: false },
        axisLine: { show: false },
        axisLabel: {
          color: "#475569",
          width: 94,
          overflow: "truncate",
        },
      },
      series: [
        {
          type: "bar",
          data: data.map((item) => item.count),
          barMaxWidth: 16,
          itemStyle: {
            borderRadius: [0, 8, 8, 0],
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: "#e6c89d" },
                { offset: 1, color: "#b8894f" },
              ],
            },
          },
        },
      ],
    },
    true,
  );
}

function renderCharts() {
  renderSpotChart();
  renderVisitorPie();
  renderTrendChart();
  renderHitChart();
}

function handleResize() {
  spotChart?.resize();
  visitorPieChart?.resize();
  trendChart?.resize();
  hitChart?.resize();
}

function observeCharts() {
  resizeObserver?.disconnect();

  if (typeof ResizeObserver === "undefined") {
    window.addEventListener("resize", handleResize);
    return;
  }

  resizeObserver = new ResizeObserver(handleResize);
  if (spotChartRef.value) resizeObserver.observe(spotChartRef.value);
  if (visitorPieRef.value) resizeObserver.observe(visitorPieRef.value);
  if (trendChartRef.value) resizeObserver.observe(trendChartRef.value);
  if (hitChartRef.value) resizeObserver.observe(hitChartRef.value);
}

async function loadAnalytics() {
  if (loading.value.page) {
    return;
  }

  loading.value.page = true;

  const failures = [];
  const results = await Promise.allSettled([
    fetchAdminOverview(),
    fetchAdminAnalytics(),
    fetchSpotAttention(),
    fetchVisitorGroups(),
    fetchQATrend(),
    fetchBlindSpotTop(),
  ]);

  const [
    overviewResult,
    analyticsResult,
    spotResult,
    visitorResult,
    trendResult,
    blindResult,
  ] = results;

  if (overviewResult.status === "fulfilled") {
    overview.value = overviewResult.value || {};
  } else {
    failures.push("后台总览");
  }

  if (analyticsResult.status === "fulfilled") {
    analyticsItems.value = analyticsResult.value || [];
  } else {
    failures.push("运营指标");
  }
  loading.value.metrics = false;

  if (spotResult.status === "fulfilled") {
    spotAttention.value = spotResult.value || [];
  } else {
    failures.push("景点关注度");
  }
  loading.value.spotChart = false;

  if (visitorResult.status === "fulfilled") {
    visitorGroups.value = visitorResult.value || {
      audience_distribution: [],
      top_tags: [],
    };
  } else {
    failures.push("游客群体");
  }
  loading.value.visitorChart = false;

  if (trendResult.status === "fulfilled") {
    trendPayload.value = trendResult.value || {
      daily_trend: [],
      hit_distribution: [],
    };
  } else {
    failures.push("问答趋势");
  }
  loading.value.trendChart = false;
  loading.value.hitChart = false;

  if (blindResult.status === "fulfilled") {
    blindSpots.value = blindResult.value || [];
  } else {
    failures.push("知识盲区");
  }
  loading.value.blindTable = false;

  setPartialWarning(failures);
  lastUpdatedAt.value = formatUpdatedAt();

  await nextTick();
  renderCharts();
  observeCharts();
  loading.value.page = false;
}

onMounted(async () => {
  await loadAnalytics();
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  window.removeEventListener("resize", handleResize);
  spotChart?.dispose();
  visitorPieChart?.dispose();
  trendChart?.dispose();
  hitChart?.dispose();
  spotChart = null;
  visitorPieChart = null;
  trendChart = null;
  hitChart = null;
});
</script>

<style scoped>
.analytics-layout {
  display: grid;
  gap: 20px;
}

.analytics-hero {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  overflow: hidden;
  padding: 30px;
  background:
    linear-gradient(118deg, rgba(49, 68, 55, 0.98), rgba(102, 128, 107, 0.95)),
    #55745e;
  color: #ffffff;
}

.analytics-hero::after {
  position: absolute;
  top: -92px;
  right: 6%;
  width: 250px;
  height: 250px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  box-shadow:
    0 0 0 34px rgba(255, 255, 255, 0.04),
    0 0 0 78px rgba(255, 255, 255, 0.025);
  content: "";
}

.analytics-hero > * {
  position: relative;
  z-index: 1;
}

.eyebrow,
.summary-kicker,
.card-kicker {
  font-family: Georgia, "Times New Roman", serif;
  letter-spacing: 0.14em;
}

.eyebrow {
  color: #e8d2ac;
  font-size: 11px;
}

.hero-copy h2 {
  margin: 8px 0 8px;
  font-family: Georgia, "STSong", serif;
  font-size: clamp(26px, 4vw, 38px);
  font-weight: 600;
}

.hero-copy p {
  max-width: 760px;
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.7;
}

.hero-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.updated-at {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  white-space: nowrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.summary-card {
  position: relative;
  display: grid;
  min-height: 170px;
  gap: 8px;
  overflow: hidden;
  padding: 22px;
  border: 1px solid color-mix(in srgb, var(--accent) 16%, white);
  border-radius: 18px;
  background:
    radial-gradient(circle at 100% 0, var(--accent-soft), transparent 46%),
    rgba(255, 253, 248, 0.96);
  box-shadow: 0 14px 32px rgba(57, 70, 58, 0.07);
}

.summary-card::after {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 56%;
  height: 4px;
  border-radius: 0 999px 0 0;
  background: var(--accent);
  content: "";
}

.summary-top {
  display: grid;
  gap: 6px;
}

.summary-kicker {
  color: color-mix(in srgb, var(--accent) 78%, #64748b);
  font-size: 10px;
}

.summary-label {
  color: #475569;
  font-size: 14px;
}

.summary-value {
  color: #0f172a;
  font-family: Georgia, "Times New Roman", serif;
  font-size: clamp(30px, 4vw, 42px);
  line-height: 1;
}

.summary-note {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.chart-grid,
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.chart-card,
.blind-card,
.metrics-card {
  min-width: 0;
  padding: 22px;
}

.card-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.card-heading h3 {
  margin: 5px 0 4px;
  color: #0f172a;
  font-family: Georgia, "STSong", serif;
  font-size: 20px;
}

.card-heading p {
  max-width: 470px;
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.65;
}

.card-kicker {
  color: var(--lingshan-green-deep);
  font-size: 9px;
}

.title-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-total {
  padding: 6px 10px;
  border-radius: 999px;
  background: #f4efe6;
  color: var(--lingshan-gold-deep);
  font-weight: 700;
  white-space: nowrap;
}

.chart-box {
  width: 100%;
  height: 310px;
  margin-top: 10px;
}

.chart-empty {
  min-height: 310px;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.tag-cloud-label {
  align-self: center;
  color: #64748b;
  font-size: 12px;
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border: 1px solid rgba(102, 128, 107, 0.18);
  border-radius: 999px;
  background: #f4f8f5;
  color: var(--lingshan-green-deep);
  font-size: 12px;
}

.blind-table {
  margin-top: 14px;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 28px;
  padding: 0 8px;
  border-radius: 999px;
  background: #f3e5cf;
  color: #7b572d;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 12px;
  font-weight: 700;
}

.hit-count {
  color: var(--lingshan-gold-deep);
  font-family: Georgia, "Times New Roman", serif;
  font-size: 18px;
  font-weight: 700;
}

.metrics-list {
  display: grid;
  gap: 10px;
  margin-top: 16px;
}

.metric-item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 10px;
  align-items: center;
  padding: 13px 14px;
  border: 1px solid rgba(102, 128, 107, 0.12);
  border-radius: 12px;
  background: #f8faf8;
}

.metric-index {
  color: #94a3b8;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 11px;
}

.metric-label {
  color: #475569;
  font-size: 13px;
}

.metric-item strong {
  color: var(--lingshan-green-deep);
  font-family: Georgia, "Times New Roman", serif;
  font-size: 18px;
}

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .chart-grid,
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .analytics-hero {
    align-items: flex-start;
    flex-direction: column;
    padding: 24px;
  }

  .hero-actions {
    width: 100%;
    justify-content: space-between;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .card-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .chart-box {
    height: 280px;
  }
}
</style>
