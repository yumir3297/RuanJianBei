<template>
  <section class="analytics-layout">
    <header class="panel-card analytics-hero">
      <div class="hero-copy">
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
          <span class="summary-label">{{ card.label }}</span>
        </div>
        <strong class="summary-value">{{ card.value }}</strong>
        <p class="summary-note" :title="card.note">{{ card.note }}</p>
      </article>
    </div>

    <section class="panel-card emotion-dashboard">
      <div class="card-heading emotion-heading">
        <div>
          <div class="title-line">
            <el-tag size="small" type="success" effect="plain">多模态情感分析</el-tag>
          </div>
          <h3>游客情绪与服务响应</h3>
          <p>融合文字语义与语音情绪，帮助景区发现困惑、不满、焦虑及紧急需求。</p>
        </div>
        <span class="card-total">{{ formatNumber(emotionInsights.total_analyzed) }} 次分析</span>
      </div>

      <el-skeleton v-if="loading.emotion" :rows="8" animated />
      <template v-else>
        <div class="emotion-kpi-grid">
          <article v-for="card in emotionCards" :key="card.key" class="emotion-kpi-card">
            <span>{{ card.label }}</span>
            <strong>{{ formatNumber(card.value) }}</strong>
            <small>{{ card.note }}</small>
          </article>
        </div>

        <div class="emotion-content-grid">
          <div class="emotion-distribution-panel">
            <h4>融合情绪分布</h4>
            <el-empty v-if="!emotionInsights.total_analyzed" description="暂无情绪分析记录" />
            <div v-else class="emotion-bars">
              <div v-for="item in emotionInsights.distribution" :key="item.emotion" class="emotion-bar-row">
                <span class="emotion-name"><i :class="['emotion-dot', `emotion-dot--${item.emotion}`]"></i>{{ item.label }}</span>
                <div class="emotion-bar-track">
                  <span :class="['emotion-bar-fill', `emotion-bar-fill--${item.emotion}`]" :style="{ width: `${Math.max(item.ratio * 100, item.count ? 3 : 0)}%` }"></span>
                </div>
                <strong>{{ formatNumber(item.count) }}</strong>
                <small>{{ formatPercent(item.ratio) }}</small>
              </div>
            </div>
          </div>

          <div class="emotion-recent-panel">
            <div class="emotion-recent-title">
              <h4>最近分析记录</h4>
              <span>最近 {{ emotionInsights.recent.length }} 条</span>
            </div>
            <el-empty v-if="!emotionInsights.recent.length" description="暂无最近记录" />
            <el-table v-else :data="emotionInsights.recent" size="small" stripe max-height="360">
              <el-table-column prop="query" label="游客问题" min-width="180" show-overflow-tooltip />
              <el-table-column label="分析模态" width="105">
                <template #default="{ row }">
                  <el-tag size="small" effect="plain" :type="row.modalities.includes('audio') ? 'success' : 'info'">
                    {{ row.modalities.includes('audio') ? '文字+语音' : '文字' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="融合结果" width="92">
                <template #default="{ row }">
                  <span :class="['emotion-result', `emotion-result--${row.fused_emotion}`]">{{ emotionLabel(row.fused_emotion) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="置信度" width="76" align="right">
                <template #default="{ row }">{{ formatPercent(row.confidence) }}</template>
              </el-table-column>
              <el-table-column label="响应策略" min-width="105">
                <template #default="{ row }">{{ strategyLabel(row.response_strategy) }}</template>
              </el-table-column>
              <el-table-column label="时间" width="138">
                <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </template>
    </section>

    <div class="chart-grid">
      <article class="panel-card chart-card">
        <div class="card-heading">
          <div>
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
  fetchEmotionSummary,
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
const emotionInsights = ref({
  total_analyzed: 0,
  multimodal_count: 0,
  conflict_count: 0,
  attention_count: 0,
  urgent_count: 0,
  distribution: [],
  recent: [],
});

const loading = ref({
  page: false,
  spotChart: true,
  visitorChart: true,
  trendChart: true,
  hitChart: true,
  blindTable: true,
  metrics: true,
  emotion: true,
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
const emotionCards = computed(() => [
  {
    key: "analyzed",
    label: "情绪分析总量",
    value: emotionInsights.value.total_analyzed,
    note: "每次问答均进行文字情绪分析",
  },
  {
    key: "multimodal",
    label: "文字+语音融合",
    value: emotionInsights.value.multimodal_count,
    note: "语音提问参与多模态融合",
  },
  {
    key: "conflict",
    label: "模态差异",
    value: emotionInsights.value.conflict_count,
    note: "文字与声音信号存在差异",
  },
  {
    key: "attention",
    label: "需关注咨询",
    value: emotionInsights.value.attention_count,
    note: `含紧急事件 ${formatNumber(emotionInsights.value.urgent_count)} 次`,
  },
]);

const EMOTION_LABELS = {
  positive: "积极",
  neutral: "中性",
  confused: "困惑",
  dissatisfied: "不满",
  anxious: "焦虑",
  urgent: "紧急",
};
const STRATEGY_LABELS = {
  positive: "积极回应",
  neutral: "自然讲解",
  confused: "澄清引导",
  dissatisfied: "安抚与补救",
  anxious: "安抚说明",
  urgent: "安全优先",
  clarify: "澄清引导",
  service_recovery: "安抚与补救",
  reassure: "安抚说明",
  safety_first: "安全优先",
};

const summaryCards = computed(() => [
  {
    key: "consultation",
    kicker: "",
    label: "总咨询量",
    value: formatNumber(overview.value.chat_log_count || 0),
    note: "累计问答日志规模，体现导览服务使用热度。",
    accent: "#0f766e",
    soft: "#dff7f2",
  },
  {
    key: "latency",
    kicker: "",
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
    kicker: "",
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
    kicker: "",
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

function formatPercent(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`;
}

function emotionLabel(value) {
  return EMOTION_LABELS[value] || value || "中性";
}

function strategyLabel(value) {
  return STRATEGY_LABELS[value] || value || "自然讲解";
}

function formatDateTime(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
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

  if (failures.length >= 7) {
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
    fetchEmotionSummary(),
  ]);

  const [
    overviewResult,
    analyticsResult,
    spotResult,
    visitorResult,
    trendResult,
    blindResult,
    emotionResult,
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

  if (emotionResult.status === "fulfilled") {
    emotionInsights.value = emotionResult.value || emotionInsights.value;
  } else {
    failures.push("情绪分析");
  }
  loading.value.emotion = false;

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
  gap: 12px;
}

.analytics-hero {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  overflow: hidden;
  padding: 20px 24px;
  background: linear-gradient(155deg, #241d16 0%, #2e2620 50%, #3a3028 100%);
  border: 1px solid #342d26;
  color: #fff7eb;
}

.analytics-hero > * {
  position: relative;
  z-index: 1;
}

.hero-copy h2 {
  margin: 8px 0 8px;
  font-size: clamp(22px, 3vw, 30px);
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
  gap: 8px;
}

.summary-card {
  position: relative;
  display: grid;
  min-height: auto;
  gap: 8px;
  overflow: hidden;
  padding: 12px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: #fffaf2;
  box-shadow: none;
}

.summary-top {
  display: grid;
  gap: 6px;
}

.summary-label {
  color: #475569;
  font-size: 14px;
}

.summary-value {
  color: #0f172a;
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

.emotion-dashboard {
  min-width: 0;
  padding: 16px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
}

.emotion-heading {
  margin-bottom: 14px;
}

.emotion-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.emotion-kpi-card {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid #e3d9cb;
  background: #fffaf2;
}

.emotion-kpi-card span {
  color: #64748b;
  font-size: 12px;
}

.emotion-kpi-card strong {
  color: #2f5f4a;
  font-size: 28px;
  line-height: 1.1;
}

.emotion-kpi-card small {
  color: #94a3b8;
  font-size: 11px;
}

.emotion-content-grid {
  display: grid;
  grid-template-columns: minmax(280px, 0.72fr) minmax(0, 1.5fr);
  gap: 12px;
}

.emotion-distribution-panel,
.emotion-recent-panel {
  min-width: 0;
  padding: 12px;
  border: 1px solid #e3d9cb;
  background: #fff;
}

.emotion-distribution-panel h4,
.emotion-recent-panel h4 {
  margin: 0 0 12px;
  color: #334155;
  font-size: 15px;
}

.emotion-bars {
  display: grid;
  gap: 14px;
}

.emotion-bar-row {
  display: grid;
  grid-template-columns: 74px minmax(80px, 1fr) 34px 42px;
  align-items: center;
  gap: 8px;
}

.emotion-name {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #475569;
  font-size: 12px;
}

.emotion-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.emotion-bar-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #eef2f4;
}

.emotion-bar-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #94a3b8;
}

.emotion-bar-row > strong {
  color: #334155;
  font-size: 12px;
  text-align: right;
}

.emotion-bar-row > small {
  color: #94a3b8;
  font-size: 11px;
  text-align: right;
}

.emotion-dot--positive, .emotion-bar-fill--positive { background: #43a383; }
.emotion-dot--neutral, .emotion-bar-fill--neutral { background: #8b98a9; }
.emotion-dot--confused, .emotion-bar-fill--confused { background: #4f91c7; }
.emotion-dot--dissatisfied, .emotion-bar-fill--dissatisfied { background: #d08a31; }
.emotion-dot--anxious, .emotion-bar-fill--anxious { background: #cb7056; }
.emotion-dot--urgent, .emotion-bar-fill--urgent { background: #d84d4d; }

.emotion-recent-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.emotion-recent-title span {
  color: #94a3b8;
  font-size: 11px;
}

.emotion-result {
  font-weight: 700;
  color: #64748b;
}

.emotion-result--positive { color: #268264; }
.emotion-result--confused { color: #337eae; }
.emotion-result--dissatisfied { color: #aa681d; }
.emotion-result--anxious { color: #b85743; }
.emotion-result--urgent { color: #c93434; }

.chart-grid,
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.chart-card,
.blind-card,
.metrics-card {
  min-width: 0;
  padding: 12px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
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
  font-size: 20px;
}

.card-heading p {
  max-width: 470px;
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.65;
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
  font-size: 12px;
  font-weight: 700;
}

.hit-count {
  color: var(--lingshan-gold-deep);
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
  padding: 8px 10px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: #f8faf8;
}

.metric-index {
  color: #94a3b8;
  font-size: 11px;
}

.metric-label {
  color: #475569;
  font-size: 13px;
}

.metric-item strong {
  color: var(--lingshan-green-deep);
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

  .emotion-content-grid {
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

  .emotion-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
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
