<template>
  <section class="dashboard-layout">
    <header class="dashboard-hero">
      <div>
        <h1>管理总览</h1>
        <p>查看知识内容、游客问答和索引维护入口。</p>
      </div>
      <div class="hero-status">
        <button type="button" class="refresh-button" :disabled="loading" @click="loadDashboard">
          {{ loading ? "刷新中…" : lastUpdatedAt ? `数据更新于 ${lastUpdatedAt}` : "刷新数据" }}
        </button>
      </div>
    </header>

    <el-alert v-if="errorMessage" type="warning" :title="errorMessage" :closable="false" show-icon>
      <template #default><el-button link type="primary" @click="loadDashboard">重新加载</el-button></template>
    </el-alert>

    <section class="stat-grid" v-loading="loading" aria-label="核心运营指标">
      <article v-for="card in topCards" :key="card.key" class="stat-card" :style="{ '--accent': card.accent, '--accent-soft': card.soft }">
        <div class="stat-card-top">
          <div>
            <p class="stat-label">{{ card.label }}</p>
            <strong class="stat-value">{{ formatNumber(card.value) }}</strong>
          </div>
          <span class="stat-icon"><el-icon><component :is="card.icon" /></el-icon></span>
        </div>
      </article>
    </section>

    <article class="rag-card">
      <div class="section-heading"><h2>RAG 索引与数据同步</h2><p>官方资料同步与检索索引维护</p></div>
      <div class="rag-health">
        <div class="rag-copy"><div><strong>索引与数据同步</strong><span>将官方资料同步到知识库，或重新构建检索索引。</span></div></div>
        <div class="rag-actions">
          <button type="button" class="outline-action" :disabled="actionLoading" @click="handleSync">{{ actionLoading === "sync" ? "同步中…" : "同步景区数据" }}</button>
          <button type="button" class="primary-action" :disabled="actionLoading" @click="handleRebuild">{{ actionLoading === "rebuild" ? "构建中…" : "构建向量索引" }}</button>
        </div>
      </div>
    </article>

    <section class="chart-row">
      <article class="chart-card">
        <div class="section-heading"><h2>知识资产构成</h2><p>景区导览知识库按内容类型分布统计</p></div>
        <div v-if="assetTotal > 0" ref="pieChartRef" class="chart-box" aria-label="知识资产构成环形图" />
        <el-empty v-else class="chart-empty" :description="overview ? '暂无知识资产数据' : '知识数据暂不可用'">
          <el-button v-if="overview?.knowledge_count === 0" type="primary" @click="$router.push('/admin/knowledge')">新增知识条目</el-button>
        </el-empty>
      </article>
      <article class="chart-card">
        <div class="section-heading"><h2>问答趋势</h2><p>近 7 日游客 AI 问答交互量趋势</p></div>
        <el-empty v-if="trendEmpty" class="chart-empty" :description="trendAvailable ? '暂无趋势数据' : '趋势数据暂不可用'" />
        <div v-else ref="barChartRef" class="chart-box" aria-label="近七天问答量趋势柱状图" />
      </article>
    </section>

    <article class="blind-spots-card">
      <div class="section-heading blind-spots-heading">
        <div><h2>待补充的游客问法</h2><p>根据游客未命中知识库的问题排序</p></div>
        <RouterLink class="text-link" to="/admin/blind-spots">查看全部盲区</RouterLink>
      </div>
      <el-skeleton v-if="blindSpotsLoading" :rows="3" animated />
      <el-empty v-else-if="blindSpots === null" :description="blindSpotsError || '盲区数据暂不可用'" />
      <el-empty v-else-if="!blindSpots.length" description="暂无待处理的游客问法" />
      <div v-else class="blind-spots-list">
        <RouterLink v-for="spot in blindSpots.slice(0, 5)" :key="spot.rank" to="/admin/blind-spots" class="blind-spot-row">
          <span class="blind-spot-query">{{ spot.query }}</span>
          <span class="blind-spot-count">{{ formatNumber(spot.hit_count) }} 次</span>
        </RouterLink>
      </div>
    </article>

    <article class="operation-card">
      <div class="section-heading"><h2>运营明细</h2></div>
      <el-skeleton v-if="loading && !operationRows.length" :rows="4" animated />
      <div v-else-if="operationRows.length" class="operation-table-wrap">
        <table class="operation-table"><thead><tr><th>指标</th><th>当前</th></tr></thead>
          <tbody><tr v-for="item in operationRows" :key="item.label"><td><strong>{{ item.label }}</strong></td><td>{{ formatNumber(item.value) }}</td></tr></tbody>
        </table>
      </div>
      <el-empty v-else :description="overview ? '暂无详细统计数据' : '统计数据暂不可用'" />
    </article>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import { ChatDotRound, Collection, Tickets, UserFilled } from "@element-plus/icons-vue";
import { BarChart, PieChart } from "echarts/charts";
import { AriaComponent, GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { init, use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { fetchBlindSpotTop, fetchQATrend } from "../../api/insights";
import { rebuildVectorIndex, syncOfficialData } from "../../api/admin";
import { useAdminStore } from "../../stores/admin";

use([AriaComponent, BarChart, CanvasRenderer, GridComponent, LegendComponent, PieChart, TooltipComponent]);

const adminStore = useAdminStore();
const pieChartRef = ref(null);
const barChartRef = ref(null);
const loading = ref(false);
const actionLoading = ref("");
const errorMessage = ref("");
const lastUpdatedAt = ref("");
const trendDays = ref([]);
const trendValues = ref([]);
const trendAvailable = ref(false);
const blindSpots = ref([]);
const blindSpotsLoading = ref(true);
const blindSpotsError = ref("");
const trendEmpty = computed(() => {
  if (!trendDays.value.length) return true;
  return trendValues.value.every((v) => v === 0);
});
const numberFormatter = new Intl.NumberFormat("zh-CN");
let pieChart = null;
let barChart = null;
let resizeObserver = null;

const overview = computed(() => adminStore.overview);
const topCards = computed(() => [
  { key: "knowledge", label: "知识条目", value: overview.value?.knowledge_count, icon: Collection, accent: "#248550", soft: "#dff0df" },
  { key: "chat-log", label: "问答日志", value: overview.value?.chat_log_count, icon: ChatDotRound, accent: "#8faab3", soft: "#edf1f2" },
  { key: "visitor", label: "游客画像", value: overview.value?.visitor_count, icon: UserFilled, accent: "#c8922c", soft: "#fbf1dd" },
  { key: "faq", label: "FAQ 条目", value: overview.value?.faq_count, icon: Tickets, accent: "#248550", soft: "#e1eee2" },
]);
const pieData = computed(() => [
  { name: "FAQ 条目", value: overview.value?.faq_count },
  { name: "知识条目", value: overview.value?.knowledge_count },
  { name: "知识切块", value: overview.value?.chunk_count },
  { name: "路线模板", value: overview.value?.route_count },
].filter((item) => item.value > 0));
const assetTotal = computed(() => pieData.value.reduce((sum, item) => sum + item.value, 0));
const operationRows = computed(() => (adminStore.analytics || []).map((item) => ({
  label: item.label,
  value: item.value,
})));

function formatNumber(value) {
  const number = Number(value);
  return value === null || value === undefined || !Number.isFinite(number)
    ? "—"
    : numberFormatter.format(number);
}
function formatUpdatedAt() { return new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit" }).format(new Date()); }

function renderPieChart() {
  if (!pieChartRef.value || !pieData.value.length) { pieChart?.dispose(); pieChart = null; return; }
  pieChart ||= init(pieChartRef.value);
  pieChart.setOption({
    animationDuration: 700,
    color: ["#285a46", "#71867a", "#9b8064", "#a8b8ad"],
    tooltip: { trigger: "item", formatter: ({ marker, name, value, percent }) => `${marker}${name}<br/>${formatNumber(value)} 项 · ${percent}%` },
    legend: { bottom: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, itemGap: 14, textStyle: { color: "#59645d", fontSize: 11 } },
    series: [{ name: "知识资产", type: "pie", radius: ["55%", "79%"], center: ["50%", "43%"], itemStyle: { borderColor: "#fff", borderWidth: 3 }, label: { show: false }, data: pieData.value }],
  }, true);
}
function renderBarChart() {
  if (!barChartRef.value || trendEmpty.value) { barChart?.dispose(); barChart = null; return; }
  barChart ||= init(barChartRef.value);
  barChart.setOption({
    animationDuration: 700,
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (value) => `${formatNumber(value)} 次` },
    grid: { top: 18, right: 12, bottom: 34, left: 40 },
    xAxis: { type: "category", data: trendDays.value, axisTick: { show: false }, axisLine: { lineStyle: { color: "#cbd6cf" } }, axisLabel: { color: "#59645d", fontSize: 11 } },
    yAxis: { type: "value", minInterval: 1, splitLine: { lineStyle: { color: "#e5e9e6" } }, axisLabel: { color: "#59645d", fontSize: 11 } },
    series: [{ name: "问答量", type: "bar", data: trendValues.value, barMaxWidth: 38, itemStyle: { color: "#285a46", borderRadius: [4, 4, 0, 0] } }],
  }, true);
}
async function renderCharts() { await nextTick(); renderPieChart(); renderBarChart(); }
async function loadDashboard() {
  if (loading.value) return;
  loading.value = true; errorMessage.value = "";
  try {
    await adminStore.loadDashboard();
    const trendData = await fetchQATrend();
    const recentTrend = Array.isArray(trendData?.daily_trend) ? trendData.daily_trend.slice(-7) : [];
    trendDays.value = recentTrend.map((item) => {
      const date = new Date(item.date);
      return Number.isNaN(date.getTime()) ? item.date : new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" }).format(date);
    });
    trendValues.value = recentTrend.map((item) => Number(item.count) || 0);
    trendAvailable.value = true;
    lastUpdatedAt.value = formatUpdatedAt();
    await renderCharts();
  } catch (error) { errorMessage.value = `数据加载失败：${error?.response?.data?.detail || error.message || "请检查后端服务"}`; }
  finally { loading.value = false; }
}
async function loadBlindSpots() {
  blindSpotsLoading.value = true;
  blindSpotsError.value = "";
  try { blindSpots.value = await fetchBlindSpotTop(); }
  catch (error) { blindSpots.value = null; blindSpotsError.value = error?.response?.data?.detail || "盲区数据暂不可用"; }
  finally { blindSpotsLoading.value = false; }
}
async function runRagAction(type, action) {
  if (actionLoading.value) return;
  actionLoading.value = type; errorMessage.value = "";
  try { await action(); await loadDashboard(); }
  catch (error) { errorMessage.value = `${type === "sync" ? "数据同步" : "索引构建"}失败：${error?.response?.data?.detail || error.message || "请稍后重试"}`; }
  finally { actionLoading.value = ""; }
}
function handleSync() { return runRagAction("sync", syncOfficialData); }
function handleRebuild() { return runRagAction("rebuild", rebuildVectorIndex); }
function handleResize() { pieChart?.resize(); barChart?.resize(); }
function observeCharts() {
  if (typeof ResizeObserver === "undefined") { window.addEventListener("resize", handleResize); return; }
  resizeObserver = new ResizeObserver(handleResize);
  if (pieChartRef.value) resizeObserver.observe(pieChartRef.value);
  if (barChartRef.value) resizeObserver.observe(barChartRef.value);
}
onMounted(async () => { await Promise.all([loadDashboard(), loadBlindSpots()]); await nextTick(); observeCharts(); });
onBeforeUnmount(() => { resizeObserver?.disconnect(); window.removeEventListener("resize", handleResize); pieChart?.dispose(); barChart?.dispose(); pieChart = null; barChart = null; });
</script>

<style scoped>
.dashboard-layout { display: grid; width: min(1280px, 100%); gap: 12px; margin: 0 auto; color: #241d16; }
.dashboard-hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 18px 20px; border: 1px solid #342d26; border-radius: 2px; background: linear-gradient(155deg, #241d16 0%, #2e2620 50%, #3a3028 100%); box-shadow: 0 2px 6px rgba(23, 18, 14, .12); }
.dashboard-hero h1, .section-heading h2 { margin: 0; font-weight: 700; }
.dashboard-hero h1 { color: #fff7eb; font-size: clamp(28px, 3vw, 40px); line-height: 1.08; letter-spacing: -.03em; }
.dashboard-hero p { max-width: 860px; margin: 11px 0 0; color: rgba(255, 247, 235, .64); font-size: 15px; line-height: 1.7; }
.hero-status { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding-top: 4px; }
.system-badge, .refresh-button { display: inline-flex; align-items: center; min-height: 38px; padding: 0 14px; border: 1px solid rgba(255, 247, 235, .15); border-radius: 2px; background: rgba(255, 247, 235, .08); color: #fff7eb; font-size: 12px; font-weight: 600; white-space: nowrap; }
.system-badge i, .operation-table b i { width: 8px; height: 8px; margin-right: 8px; border-radius: 2px; background: #44c07a; box-shadow: 0 0 6px rgba(68, 192, 122, .55); }
.refresh-button { cursor: pointer; transition: background .16s ease; }.refresh-button:hover:not(:disabled) { background: rgba(255,247,235,.14); }.refresh-button:disabled { cursor: wait; opacity: .65; }
.stat-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.stat-card, .rag-card, .chart-card, .operation-card { border: 1px solid #d4c8b8; border-radius: 2px; background: #fffaf2; box-shadow: 0 1px 3px rgba(23, 18, 14, .07); }
.stat-card { display: flex; min-height: 138px; flex-direction: column; justify-content: space-between; gap: 12px; padding: 16px 18px; background: linear-gradient(180deg, #fffaf2 0%, color-mix(in srgb, var(--accent) 4%, #fffaf2) 100%); transition: transform .22s ease, box-shadow .22s ease; }.stat-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(23,18,14,.12); }
.stat-card-top { display: flex; justify-content: space-between; gap: 14px; }.stat-label { margin: 0; color: #675a4e; font-size: 12px; }.stat-value { display: block; margin-top: 9px; color: #241d16; font-size: clamp(32px, 3.2vw, 42px); line-height: 1; letter-spacing: -.03em; }.stat-icon { display: grid; width: 36px; height: 36px; flex: 0 0 auto; place-items: center; border-radius: 2px; background: var(--accent-soft); color: var(--accent); font-size: 18px; }
.rag-card, .chart-card, .operation-card { padding: 16px 20px 18px; }.section-heading h2 { font-size: 22px; line-height: 1.1; letter-spacing: -.03em; }.section-heading p { margin: 8px 0 0; color: #675a4e; font-size: 12px; line-height: 1.6; }
.rag-health { display: flex; align-items: center; gap: 16px; margin-top: 12px; padding: 12px; border: 1px solid #d4c8b8; border-radius: 6px; background: #f0e9dc; }.rag-copy { display: flex; align-items: center; gap: 12px; }.status-pulse { width: 12px; height: 12px; flex: 0 0 auto; border-radius: 2px; background: #2fa363; box-shadow: 0 0 0 0 rgba(47,163,99,.35); animation: status-pulse 2s ease-in-out infinite; }.rag-copy strong { display: block; font-size: 13px; }.rag-copy span { display: block; margin-top: 4px; color: #675a4e; font-size: 12px; }.rag-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-left: auto; }.outline-action, .primary-action { min-height: 38px; padding: 0 15px; border-radius: 2px; font-size: 12px; font-weight: 600; cursor: pointer; }.outline-action { border: 1px solid #d4c8b8; background: #fffaf2; color: #241d16; }.primary-action { border: 1px solid #248550; background: #248550; color: #fff; box-shadow: 0 2px 8px rgba(36,133,80,.3); }.outline-action:disabled, .primary-action:disabled { cursor: wait; opacity: .6; }.rag-metrics { display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 12px; margin-top: 14px; }.rag-metrics div { display: grid; gap: 5px; padding: 12px; border: 1px solid #d4c8b8; border-radius: 6px; background: color-mix(in srgb, #248550 4%, #fffaf2); }.rag-metrics div:nth-child(2) { background: color-mix(in srgb, #d9a441 4%, #fffaf2); }.rag-metrics div:nth-child(3) { background: color-mix(in srgb, #8faab3 4%, #fffaf2); }.rag-metrics span { color: #675a4e; font-size: 10px; }.rag-metrics strong { font-size: 22px; }
.chart-row { display: grid; grid-template-columns: minmax(0,1.1fr) minmax(0,.9fr); gap: 12px; }.chart-box { width: 100%; height: 280px; margin-top: 6px; }.chart-empty { min-height: 280px; }
.operation-table-wrap { margin-top: 14px; overflow-x: auto; }.operation-table { width: 100%; border-collapse: collapse; }.operation-table th { padding: 0 0 12px; color: #675a4e; font-family: monospace; font-size: 11px; letter-spacing: .1em; text-align: right; }.operation-table th:first-child { text-align: left; }.operation-table td { padding: 12px; border-top: 1px solid #e3d9cc; color: #241d16; font-size: 13px; text-align: right; white-space: nowrap; }.operation-table td:first-child { min-width: 180px; padding-left: 0; text-align: left; white-space: normal; }.operation-table td:first-child strong, .operation-table td:first-child span { display: block; }.operation-table td:first-child span { margin-top: 4px; color: #675a4e; font-size: 11px; }.operation-table td:nth-child(2) { font-weight: 700; }.operation-table td:nth-child(3) { color: #675a4e; }.operation-table td:last-child { padding-right: 0; }.operation-table b { display: inline-flex; align-items: center; min-height: 28px; padding: 0 9px; border-radius: 2px; background: rgba(47,163,99,.12); color: #248550; font-size: 12px; font-weight: 500; }.operation-table b i { width: 6px; height: 6px; margin-right: 5px; box-shadow: none; }
@keyframes status-pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(47,163,99,.35); } 50% { box-shadow: 0 0 0 6px rgba(47,163,99,0); } }
@media (max-width: 900px) { .dashboard-hero, .rag-health { align-items: flex-start; flex-direction: column; }.rag-actions { margin-left: 0; }.chart-row { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .dashboard-layout { gap: 10px; }.stat-grid, .rag-metrics { grid-template-columns: 1fr; }.dashboard-hero, .rag-card, .chart-card, .operation-card { padding: 16px; }.hero-status { padding-top: 0; flex-wrap: wrap; }.hero-status .refresh-button { white-space: normal; }.operation-table th:nth-child(3), .operation-table td:nth-child(3) { display: none; } }
.dashboard-layout { width: min(1280px, 100%); gap: 16px; color: #202723; }
.dashboard-hero { align-items: center; padding: 20px 24px; border: 1px solid #dce2dd; border-radius: 10px; background: #fff; box-shadow: none; }
.dashboard-hero h1 { color: #202723; font-size: 26px; line-height: 1.3; letter-spacing: 0; }
.dashboard-hero p { margin-top: 6px; color: #59645d; font-size: 14px; }
.refresh-button { border-color: #cbd6cf; border-radius: 6px; background: #fff; color: #285a46; font-size: 13px; }
.refresh-button:hover:not(:disabled) { background: #e8f0ea; }
.stat-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.stat-card, .rag-card, .chart-card, .operation-card, .blind-spots-card { border: 1px solid #dce2dd; border-radius: 10px; background: #fff; box-shadow: none; }
.stat-card { min-height: 112px; padding: 16px; background: #fff; }
.stat-card:hover { transform: none; box-shadow: 0 3px 12px rgba(32, 39, 35, .06); }
.stat-label, .section-heading p, .rag-copy span, .operation-table th, .operation-table td:first-child span { color: #59645d; }
.stat-value { color: #202723; font-size: 32px; letter-spacing: 0; }
.stat-icon { border-radius: 8px; }
.rag-card, .chart-card, .operation-card, .blind-spots-card { padding: 18px 20px; }
.section-heading h2 { color: #202723; font-size: 17px; letter-spacing: 0; }
.section-heading p { font-size: 13px; }
.rag-health { border-color: #dce2dd; border-radius: 8px; background: #f5f6f4; }
.status-pulse { display: none; }
.outline-action, .primary-action { min-height: 40px; border-radius: 6px; font-size: 13px; }
.outline-action { border-color: #cbd6cf; background: #fff; color: #285a46; }
.primary-action { border-color: #285a46; background: #285a46; box-shadow: none; }
.chart-row { gap: 16px; }
.operation-table td { border-color: #e5e9e6; color: #202723; }
.blind-spots-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.text-link { color: #285a46; font-size: 13px; text-decoration: none; }
.text-link:hover { text-decoration: underline; }
.blind-spots-list { margin-top: 12px; }
.blind-spot-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 0; border-top: 1px solid #e5e9e6; color: #202723; text-decoration: none; }
.blind-spot-row:hover .blind-spot-query { color: #285a46; }
.blind-spot-query { min-width: 0; overflow-wrap: anywhere; }
.blind-spot-count { flex: 0 0 auto; color: #59645d; font-size: 13px; }
@media (max-width: 640px) { .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.dashboard-hero, .rag-card, .chart-card, .operation-card, .blind-spots-card { padding: 16px; } }
</style>
