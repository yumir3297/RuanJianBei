<template>
  <section class="experience-layout">
    <header class="experience-hero">
      <div>
        <h1>游客反馈</h1>
        <p>查看问答趋势、游客反馈和高频关注问题。</p>
      </div>
      <div class="hero-actions">
        <div class="range-switch"><button v-for="item in ranges" :key="item.key" type="button" :disabled="loading" :aria-pressed="range === item.key" :class="{ active: range === item.key }" @click="range = item.key; loadReport()">{{ item.label }}</button></div>
        <button class="refresh" :disabled="loading" @click="loadReport">{{ loading ? '刷新中…' : '刷新报告' }}</button>
      </div>
    </header>

    <el-alert v-if="report.data_mode === 'demo'" type="info" :closable="false" show-icon title="当前展示评委演示样本：数据来自数据库初始化记录；收到真实游客反馈后将自动切换为真实统计。" />
    <el-alert v-if="error" type="warning" :closable="false" :title="error" />

    <div class="metric-grid" v-loading="loading && !reportReady">
      <article v-for="item in cards" :key="item.label" class="metric-card"><span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.note }}</small></article>
    </div>

    <div class="content-grid">
      <article class="panel report-panel"><div class="panel-heading"><div><h2>满意度趋势</h2><p>{{ reportReady ? report.sentiment_summary : '等待报告数据' }}</p></div><b v-if="reportReady && report.satisfaction_rate !== null">{{ report.satisfaction_rate }}%</b></div><div v-if="hasTrend" ref="trendRef" class="chart" /><el-empty v-else :description="loading && !reportReady ? '正在加载报告' : reportReady ? '暂无有效反馈趋势' : '报告数据暂不可用'" /></article>
      <article class="panel report-panel"><div class="panel-heading"><div><h2>负向反馈归因</h2><p>仅统计游客选择“需改进”后的反馈原因。</p></div></div><div v-if="report.negative_reasons?.length" ref="reasonRef" class="chart" /><el-empty v-else :description="loading && !reportReady ? '正在加载报告' : reportReady ? '暂无负向反馈' : '报告数据暂不可用'" /></article>
    </div>

    <div class="content-grid lower-grid">
      <article class="panel"><div class="panel-heading"><div><h2>游客关注问题</h2><p>按当前周期的问答问题聚合。</p></div></div><el-empty v-if="!report.hot_questions?.length" :description="loading && !reportReady ? '正在加载报告' : reportReady ? '当前周期暂无问答日志' : '报告数据暂不可用'" /><ol v-else class="topic-list"><li v-for="(item, index) in report.hot_questions" :key="item.label"><span>{{ String(index + 1).padStart(2, '0') }}</span><p>{{ item.label }}</p><b>{{ item.count }} 次</b></li></ol></article>
      <article class="panel"><div class="panel-heading"><div><h2>服务建议</h2></div></div><el-empty v-if="!report.suggestions?.length" :description="loading && !reportReady ? '正在加载报告' : reportReady ? '暂无服务建议' : '报告数据暂不可用'" /><div v-else class="suggestions"><article v-for="item in report.suggestions" :key="item.title" :class="['suggestion', item.level]"><strong>{{ item.title }}</strong><p>{{ item.detail }}</p></article></div></article>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import * as echarts from "echarts";
import { fetchExperienceReport } from "../../api/insights";

const range = ref("week"); const loading = ref(false); const error = ref(""); const reportReady = ref(false);
const loadedRange = ref("");
const trendRef = ref(null); const reasonRef = ref(null); let trendChart = null; let reasonChart = null;
const report = ref({ data_mode: "empty", service_sessions: 0, interaction_count: 0, feedback_count: 0, feedback_coverage: 0, satisfaction_rate: null, trend: [], hot_questions: [], negative_reasons: [], suggestions: [] });
const ranges = [{ key: "today", label: "今日" }, { key: "week", label: "本周" }, { key: "month", label: "近30天" }];
const hasTrend = computed(() => reportReady.value && report.value.trend?.some((item) => item.positive || item.negative));
const displayNumber = (value) => reportReady.value && value !== null && value !== undefined ? value : "—";
const cards = computed(() => [
  { label: "服务人次", value: displayNumber(report.value.service_sessions), note: "按去重会话统计" },
  { label: "问答交互", value: displayNumber(report.value.interaction_count), note: "当前时间范围内" },
  { label: "游客满意度", value: !reportReady.value ? "—" : report.value.satisfaction_rate == null ? "暂无" : `${report.value.satisfaction_rate}%`, note: reportReady.value && report.value.feedback_coverage != null ? `反馈覆盖率 ${report.value.feedback_coverage}%` : "反馈覆盖率暂不可用" },
  { label: "有效反馈", value: displayNumber(report.value.feedback_count), note: report.value.data_mode === "demo" ? "演示数据" : "当前时间范围内" },
]);
function renderCharts() {
  if (hasTrend.value && trendRef.value) { trendChart ||= echarts.init(trendRef.value); trendChart.setOption({ color: ["#285a46", "#9b6a56"], tooltip: { trigger: "axis" }, legend: { bottom: 0, textStyle: { color: "#59645d" } }, grid: { top: 28, right: 18, bottom: 38, left: 38 }, xAxis: { type: "category", data: report.value.trend.map((x) => x.date), axisLabel: { color: "#59645d" } }, yAxis: { type: "value", minInterval: 1, axisLabel: { color: "#59645d" }, splitLine: { lineStyle: { color: "#e5e9e6" } } }, series: [{ name: "有帮助", type: "line", smooth: true, data: report.value.trend.map((x) => x.positive) }, { name: "需改进", type: "line", smooth: true, data: report.value.trend.map((x) => x.negative) }] }, true); }
  if (report.value.negative_reasons?.length && reasonRef.value) { reasonChart ||= echarts.init(reasonRef.value); reasonChart.setOption({ color: ["#9b6a56"], tooltip: { trigger: "axis" }, grid: { top: 16, right: 18, bottom: 22, left: 104 }, xAxis: { type: "value", minInterval: 1, axisLabel: { color: "#59645d" }, splitLine: { lineStyle: { color: "#e5e9e6" } } }, yAxis: { type: "category", inverse: true, data: report.value.negative_reasons.map((x) => x.label), axisLabel: { color: "#59645d" } }, series: [{ type: "bar", data: report.value.negative_reasons.map((x) => x.count), barMaxWidth: 22, itemStyle: { borderRadius: [0, 5, 5, 0] } }] }, true); }
}
async function loadReport() { if (loading.value) return; loading.value = true; error.value = ""; try { report.value = await fetchExperienceReport(range.value); loadedRange.value = range.value; reportReady.value = true; await nextTick(); renderCharts(); } catch (e) { error.value = `报告加载失败：${e?.response?.data?.detail || e.message || '请检查后端服务'}`; if (loadedRange.value) range.value = loadedRange.value; } finally { loading.value = false; } }
function resize() { trendChart?.resize(); reasonChart?.resize(); }
onMounted(() => { loadReport(); window.addEventListener("resize", resize); }); onBeforeUnmount(() => { window.removeEventListener("resize", resize); trendChart?.dispose(); reasonChart?.dispose(); });
</script>

<style scoped>
.experience-layout { display:grid; gap:12px; max-width:1280px; margin:0 auto; color:#241d16; }.experience-hero,.panel,.metric-card{border:1px solid #d4c8b8;border-radius:2px;background:#fffaf2;box-shadow:0 1px 3px rgba(23,18,14,.07)}.experience-hero{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:20px;background:linear-gradient(130deg,#241d16,#3a3028);color:#fff7eb}.eyebrow{margin:0;color:#d9a441;font-size:10px;letter-spacing:.2em}.experience-hero h1{margin:6px 0;font:700 32px "STKaiti","KaiTi",serif}.experience-hero p{margin:0;color:rgba(255,247,235,.68);font-size:13px}.hero-actions{display:flex;gap:8px;align-items:center}.range-switch{display:flex;padding:3px;background:rgba(255,255,255,.08)}button{cursor:pointer}.range-switch button,.refresh{border:0;background:transparent;color:#fff7eb;padding:8px 10px;font-size:12px}.range-switch button.active{background:#d9a441;color:#241d16;font-weight:700}.refresh{border:1px solid rgba(255,255,255,.22)}.metric-grid,.content-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric-card{padding:16px;display:grid;gap:7px}.metric-card span{color:#675a4e;font-size:12px}.metric-card strong{font-size:30px}.metric-card small{color:#8c8174}.content-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.panel{padding:18px}.panel-heading{display:flex;justify-content:space-between;gap:12px}.panel h2{margin:0;font-size:20px}.panel-heading p{margin:7px 0 0;color:#675a4e;font-size:12px;line-height:1.6}.panel-heading b{color:#248550;font-size:26px}.chart{height:260px;margin-top:8px}.topic-list{margin:16px 0 0;padding:0;list-style:none}.topic-list li{display:grid;grid-template-columns:36px 1fr auto;gap:10px;align-items:center;padding:10px 0;border-top:1px solid #e3d9cc}.topic-list span{color:#c8922c;font:700 12px monospace}.topic-list p{margin:0;font-size:13px}.topic-list b{color:#248550;font-size:12px}.suggestions{display:grid;gap:9px;margin-top:15px}.suggestion{padding:12px;border-left:3px solid #248550;background:#f5f8f4}.suggestion.attention{border-color:#c47c4a;background:#fff4ec}.suggestion.optimize{border-color:#c8922c;background:#fff9ed}.suggestion strong{font-size:13px}.suggestion p{margin:5px 0 0;color:#675a4e;font-size:12px;line-height:1.55}@media(max-width:900px){.metric-grid{grid-template-columns:repeat(2,1fr)}.experience-hero{align-items:flex-start;flex-direction:column}}@media(max-width:600px){.metric-grid,.content-grid{grid-template-columns:1fr}.hero-actions{width:100%;justify-content:space-between}.experience-hero{padding:16px}}
</style>
