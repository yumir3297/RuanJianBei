<template>
  <section class="knowledge-layout">
    <header class="panel-card knowledge-hero">
      <div class="hero-copy">
        <span class="hero-kicker">SCENIC KNOWLEDGE OPS</span>
        <h2>知识资产管理</h2>
        <p>
          统一维护景区讲解资料、游客高频问题与运营补录内容，让导览回答可检索、可追溯，也更适合现场答辩展示。
        </p>
        <div class="hero-pills">
          <span class="hero-pill">
            <el-icon><Collection /></el-icon>
            知识池共 {{ formatNumber(entries.length) }} 条
          </span>
          <span class="hero-pill muted">覆盖 {{ formatNumber(categoryCount) }} 个知识分类</span>
          <span v-if="lastUpdatedAt" class="hero-pill muted">更新于 {{ lastUpdatedAt }}</span>
        </div>
      </div>

      <div class="hero-side">
        <div class="hero-status">
          <span class="hero-status-label">当前状态</span>
          <strong>{{ statusSummary }}</strong>
          <p>{{ statusDescription }}</p>
        </div>
        <div class="hero-actions">
          <el-button :icon="RefreshRight" :loading="loading" @click="loadEntries">刷新快照</el-button>
          <el-button type="primary" :icon="Plus" @click="openDialog()">新增知识</el-button>
        </div>
      </div>
    </header>

    <el-alert
      v-if="error"
      type="warning"
      :title="error"
      :closable="false"
      show-icon
    >
      <template #default>
        <el-button link type="primary" @click="loadEntries">重新加载</el-button>
      </template>
    </el-alert>

    <div class="stat-grid" v-loading="loading && !entries.length">
      <article
        v-for="card in summaryCards"
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
        <p class="stat-note">{{ card.note }}</p>
      </article>
    </div>

    <div class="knowledge-main">
      <article class="panel-card knowledge-table-card">
        <div class="card-heading">
          <div>
            <span class="card-kicker">ASSET SNAPSHOT</span>
            <h3>知识资产快照</h3>
            <p>围绕景区知识池进行检视、筛选与编辑，支撑讲解内容、游客问答与后续盲区补录。</p>
          </div>
          <div class="heading-meta">
            <span>{{ formatNumber(filteredEntries.length) }} / {{ formatNumber(entries.length) }} 条</span>
            <el-tag
              v-if="activeFilterCount"
              size="small"
              type="warning"
              effect="plain"
            >
              已启用 {{ activeFilterCount }} 项筛选
            </el-tag>
          </div>
        </div>

        <div class="filter-toolbar">
          <el-input
            v-model="searchQuery"
            clearable
            class="search-input"
            placeholder="搜索标题、来源、别名"
          />
          <el-select
            v-model="selectedCategory"
            clearable
            class="category-select"
            placeholder="全部分类"
          >
            <el-option
              v-for="category in categoryOptions"
              :key="category"
              :label="category"
              :value="category"
            />
          </el-select>
        </div>

        <el-skeleton v-if="loading" :rows="6" animated />
        <el-empty v-else-if="!entries.length" description="暂无知识条目，可先同步官方资料或手动新增" />
        <el-empty v-else-if="!filteredEntries.length" description="当前筛选条件下暂无符合条目" />
        <div v-else class="table-shell">
          <el-table :data="pagedEntries" stripe class="knowledge-table">
            <el-table-column prop="title" label="标题" min-width="240">
              <template #default="{ row }">
                <div class="title-cell">
                  <strong>{{ row.title }}</strong>
                  <p>{{ summarizeContent(row.content) }}</p>
                </div>
              </template>
            </el-table-column>

            <el-table-column prop="category" label="分类" width="132">
              <template #default="{ row }">
                <el-tag class="category-tag" effect="plain">{{ row.category || "未分类" }}</el-tag>
              </template>
            </el-table-column>

            <el-table-column prop="source" label="来源" min-width="220">
              <template #default="{ row }">
                <div class="source-cell">
                  <span>{{ sourceLabel(row.source) }}</span>
                  <small>{{ sourceNote(row.source) }}</small>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="别名" min-width="200">
              <template #default="{ row }">
                <div v-if="row.aliases?.length" class="alias-list">
                  <el-tag
                    v-for="alias in row.aliases.slice(0, 3)"
                    :key="alias"
                    size="small"
                    effect="plain"
                  >
                    {{ alias }}
                  </el-tag>
                  <span v-if="row.aliases.length > 3" class="alias-more">+{{ row.aliases.length - 3 }}</span>
                </div>
                <span v-else class="muted-text">暂无别名</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="156" fixed="right">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button type="primary" size="small" @click="openDialog(row)">编辑</el-button>
                  <el-button type="danger" size="small" plain @click="handleDelete(row)">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="filteredEntries.length > pageSize" class="pagination-wrap">
          <div class="pagination-note">
            当前显示第 {{ formatNumber(visibleStart) }} - {{ formatNumber(visibleEnd) }} 条
          </div>
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            :total="filteredEntries.length"
            layout="total, prev, pager, next"
            background
          />
        </div>
      </article>

      <aside class="knowledge-side">
        <article class="panel-card side-card">
          <div class="side-heading">
            <div>
              <span class="card-kicker">OPERATIONS</span>
              <h3>运营动作区</h3>
            </div>
            <el-tag size="small" type="success" effect="plain">核心操作</el-tag>
          </div>

          <div class="action-list">
            <div class="action-item">
              <div class="action-copy">
                <strong>同步官方资料</strong>
                <p>将景区官方资料同步进知识池，适合答辩前统一口径与内容底稿。</p>
              </div>
              <el-button :icon="UploadFilled" :loading="syncing" @click="handleSync">立即同步</el-button>
            </div>

            <div class="action-item">
              <div class="action-copy">
                <strong>重建向量索引</strong>
                <p>知识内容更新后重建检索索引，保证讲解问答命中率与资料可追溯性。</p>
              </div>
              <el-button :icon="Operation" :loading="rebuilding" @click="handleRebuildIndex">开始重建</el-button>
            </div>

            <div class="action-item compact">
              <div class="action-copy">
                <strong>人工补录知识</strong>
                <p>补充现场讲解口径、文化细节与游客常见追问，体现运营闭环能力。</p>
              </div>
              <el-button type="primary" plain :icon="EditPen" @click="openDialog()">新增条目</el-button>
            </div>
          </div>
        </article>

        <article class="panel-card side-card">
          <div class="side-heading">
            <div>
              <span class="card-kicker">STATUS BOARD</span>
              <h3>当前工作面</h3>
            </div>
          </div>

          <div class="status-list">
            <div class="status-row">
              <span>页面状态</span>
              <strong :class="statusToneClass">{{ statusSummary }}</strong>
            </div>
            <div class="status-row">
              <span>当前筛选</span>
              <strong>{{ filterSummary }}</strong>
            </div>
            <div class="status-row">
              <span>当前分页</span>
              <strong>第 {{ currentPage }} / {{ totalPages }} 页</strong>
            </div>
            <div class="status-row">
              <span>最近刷新</span>
              <strong>{{ lastUpdatedAt || "尚未加载" }}</strong>
            </div>
          </div>
        </article>

        <article class="panel-card side-card guidance-card">
          <div class="side-heading">
            <div>
              <span class="card-kicker">GOVERNANCE</span>
              <h3>录入规范提示</h3>
            </div>
          </div>
          <ul>
            <li>标题尽量贴近游客提问口径，便于讲解与检索统一。</li>
            <li>来源字段优先填写官方资料、运营补录或专题整理渠道。</li>
            <li>别名建议补充口语表达和景点俗称，提升问答命中率。</li>
          </ul>
        </article>
      </aside>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑知识条目' : '新增知识条目'"
      width="640px"
      class="knowledge-dialog"
    >
      <div class="dialog-intro">
        <span class="card-kicker">EDITOR</span>
        <p>维护可展示、可检索、可回答的景区知识内容，建议同步补齐来源与别名。</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="88px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入知识标题" />
        </el-form-item>

        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择分类">
            <el-option label="景点信息" value="景点信息" />
            <el-option label="历史文化" value="历史文化" />
            <el-option label="建筑艺术" value="建筑艺术" />
            <el-option label="游览路线" value="游览路线" />
            <el-option label="实用贴士" value="实用贴士" />
            <el-option label="景区概况" value="景区概况" />
          </el-select>
        </el-form-item>

        <el-form-item label="内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            placeholder="请输入知识内容"
          />
        </el-form-item>

        <el-form-item label="来源">
          <el-input v-model="form.source" placeholder="默认：管理员手动录入" />
        </el-form-item>

        <el-form-item label="别名">
          <el-input
            v-model="aliasInput"
            placeholder="输入别名后回车添加"
            @keyup.enter="addAlias"
          />
          <div class="dialog-aliases">
            <el-tag
              v-for="(alias, idx) in form.aliases"
              :key="`${alias}-${idx}`"
              closable
              effect="plain"
              @close="form.aliases.splice(idx, 1)"
            >
              {{ alias }}
            </el-tag>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">提交</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import {
  Collection,
  EditPen,
  Files,
  Operation,
  Plus,
  RefreshRight,
  Tickets,
  UploadFilled,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import {
  createKnowledge,
  deleteKnowledge,
  fetchKnowledgeList,
  updateKnowledge,
} from "../../api/knowledge";
import { rebuildVectorIndex, syncOfficialData } from "../../api/admin";

const entries = ref([]);
const loading = ref(false);
const error = ref("");
const syncing = ref(false);
const rebuilding = ref(false);
const lastUpdatedAt = ref("");

const searchQuery = ref("");
const selectedCategory = ref("");
const currentPage = ref(1);
const pageSize = 15;

const dialogVisible = ref(false);
const isEdit = ref(false);
const submitting = ref(false);
const formRef = ref(null);
const aliasInput = ref("");
const currentId = ref(null);

const form = ref({
  title: "",
  category: "",
  content: "",
  source: "管理员手动录入",
  aliases: [],
});

const rules = {
  title: [{ required: true, message: "请输入标题", trigger: "blur" }],
  category: [{ required: true, message: "请选择分类", trigger: "change" }],
  content: [{ required: true, message: "请输入内容", trigger: "blur" }],
};

const numberFormatter = new Intl.NumberFormat("zh-CN");

const categoryOptions = computed(() =>
  [...new Set(entries.value.map((entry) => entry.category).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "zh-CN"),
  ),
);

const categoryCount = computed(() => categoryOptions.value.length);

const filteredEntries = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase();

  return entries.value.filter((entry) => {
    const categoryMatch = !selectedCategory.value || entry.category === selectedCategory.value;
    if (!categoryMatch) {
      return false;
    }

    if (!keyword) {
      return true;
    }

    const haystacks = [
      entry.title,
      entry.category,
      entry.source,
      ...(Array.isArray(entry.aliases) ? entry.aliases : []),
    ];

    return haystacks.some((item) => String(item || "").toLowerCase().includes(keyword));
  });
});

const totalPages = computed(() => Math.max(1, Math.ceil(filteredEntries.value.length / pageSize)));

const pagedEntries = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredEntries.value.slice(start, start + pageSize);
});

const visibleStart = computed(() =>
  filteredEntries.value.length ? (currentPage.value - 1) * pageSize + 1 : 0,
);
const visibleEnd = computed(() =>
  filteredEntries.value.length
    ? Math.min(currentPage.value * pageSize, filteredEntries.value.length)
    : 0,
);

const aliasConfiguredCount = computed(() =>
  entries.value.filter((entry) => Array.isArray(entry.aliases) && entry.aliases.length > 0).length,
);

const manualEntryCount = computed(() =>
  entries.value.filter((entry) => isManualSource(entry.source)).length,
);

const activeFilterCount = computed(
  () => Number(Boolean(searchQuery.value.trim())) + Number(Boolean(selectedCategory.value)),
);

const filterSummary = computed(() => {
  if (!activeFilterCount.value) {
    return "未启用筛选";
  }

  const fragments = [];
  if (selectedCategory.value) {
    fragments.push(selectedCategory.value);
  }
  if (searchQuery.value.trim()) {
    fragments.push(`关键词：${searchQuery.value.trim()}`);
  }
  return fragments.join(" / ");
});

const statusSummary = computed(() => {
  if (loading.value) {
    return "加载中";
  }
  if (syncing.value) {
    return "资料同步中";
  }
  if (rebuilding.value) {
    return "索引重建中";
  }
  if (entries.value.length) {
    return "知识池可用";
  }
  return "等待录入";
});

const statusDescription = computed(() => {
  if (loading.value) {
    return "正在读取当前知识资产快照，请稍候。";
  }
  if (syncing.value) {
    return "官方资料正在回流至知识池，完成后会自动刷新当前快照。";
  }
  if (rebuilding.value) {
    return "检索索引正在更新，完成后可提升问答与引用定位效果。";
  }
  if (entries.value.length) {
    return "当前页面可直接进行筛选、补录、同步与索引维护。";
  }
  return "当前尚无知识条目，建议先同步官方资料或手动新增。";
});

const statusToneClass = computed(() => {
  if (loading.value || syncing.value || rebuilding.value) {
    return "tone-busy";
  }
  if (entries.value.length) {
    return "tone-ready";
  }
  return "tone-waiting";
});

const summaryCards = computed(() => [
  {
    key: "knowledge-total",
    kicker: "KNOWLEDGE",
    value: entries.value.length,
    label: "知识资产总量",
    note: "支撑景区讲解、问答与资料追溯的底层内容。",
    icon: Collection,
    accent: "#0f766e",
    soft: "#dcf7f1",
  },
  {
    key: "category-coverage",
    kicker: "COVERAGE",
    value: categoryCount.value,
    label: "分类覆盖",
    note: "反映当前景区知识维度是否完整、清晰。",
    icon: Files,
    accent: "#b8894f",
    soft: "#f8ecd8",
  },
  {
    key: "aliases",
    kicker: "ALIAS",
    value: aliasConfiguredCount.value,
    label: "已配置别名",
    note: "便于识别游客口语化问法与景点俗称。",
    icon: Tickets,
    accent: "#2563eb",
    soft: "#e1ebff",
  },
  {
    key: "manual-entry",
    kicker: "CURATION",
    value: manualEntryCount.value,
    label: "人工补录条目",
    note: "体现后台持续维护与运营补充能力。",
    icon: EditPen,
    accent: "#c2410c",
    soft: "#ffeadc",
  },
]);

watch([searchQuery, selectedCategory], () => {
  currentPage.value = 1;
});

watch(filteredEntries, () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value;
  }
});

function formatNumber(value) {
  return numberFormatter.format(Number(value) || 0);
}

function formatUpdatedAt() {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function isManualSource(source) {
  return !source || /管理员|手动|录入/.test(String(source));
}

function sourceLabel(source) {
  return source || "管理员手动录入";
}

function sourceNote(source) {
  return isManualSource(source) ? "运营补录" : "资料来源";
}

function summarizeContent(content) {
  const text = String(content || "").replace(/\s+/g, " ").trim();
  if (!text) {
    return "暂无内容摘要";
  }
  return text.length > 46 ? `${text.slice(0, 46)}...` : text;
}

async function loadEntries() {
  loading.value = true;
  error.value = "";
  currentPage.value = 1;

  try {
    const data = await fetchKnowledgeList();
    entries.value = Array.isArray(data) ? data : [];
    lastUpdatedAt.value = formatUpdatedAt();
  } catch (e) {
    error.value = `加载失败: ${e?.response?.data?.detail || e.message}`;
  } finally {
    loading.value = false;
  }
}

function openDialog(row = null) {
  isEdit.value = !!row;

  if (row) {
    currentId.value = row.id;
    form.value = {
      title: row.title,
      category: row.category,
      content: row.content,
      source: row.source || "管理员手动录入",
      aliases: [...(row.aliases || [])],
    };
  } else {
    currentId.value = null;
    form.value = {
      title: "",
      category: "",
      content: "",
      source: "管理员手动录入",
      aliases: [],
    };
  }

  aliasInput.value = "";
  dialogVisible.value = true;
}

function addAlias() {
  const value = aliasInput.value.trim();
  if (value && !form.value.aliases.includes(value)) {
    form.value.aliases.push(value);
    aliasInput.value = "";
  }
}

async function submitForm() {
  if (!formRef.value) {
    return;
  }

  await formRef.value.validate(async (valid) => {
    if (!valid) {
      return;
    }

    submitting.value = true;
    try {
      if (isEdit.value) {
        await updateKnowledge(currentId.value, form.value);
        ElMessage.success("知识更新成功");
      } else {
        await createKnowledge(form.value);
        ElMessage.success("知识创建成功");
      }

      dialogVisible.value = false;
      await loadEntries();
    } catch (e) {
      ElMessage.error(`提交失败: ${e?.response?.data?.detail || e.message}`);
    } finally {
      submitting.value = false;
    }
  });
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除知识 "${row.title}" 吗？`, "提示", { type: "warning" });
    await deleteKnowledge(row.id);
    ElMessage.success("删除成功");
    await loadEntries();
  } catch (e) {
    if (e !== "cancel") {
      ElMessage.error(`删除失败: ${e?.response?.data?.detail || e.message}`);
    }
  }
}

async function handleSync() {
  syncing.value = true;
  try {
    const res = await syncOfficialData();
    ElMessage.success(`数据同步完成，耗时约 ${(res.report.duration_ms / 1000).toFixed(1)}s`);
    await loadEntries();
  } catch (e) {
    ElMessage.error(`同步失败: ${e?.response?.data?.detail || e.message}`);
  } finally {
    syncing.value = false;
  }
}

async function handleRebuildIndex() {
  try {
    await ElMessageBox.confirm("重建向量索引是重量级操作，约需 10-30 秒，确定继续？", "提示", {
      type: "warning",
    });
    rebuilding.value = true;
    const res = await rebuildVectorIndex();
    lastUpdatedAt.value = formatUpdatedAt();
    ElMessage.success(
      `索引重建完成，耗时约 ${(res.report.duration_ms / 1000).toFixed(1)}s，共 ${res.report.indexed_chunks} 条`,
    );
  } catch (e) {
    if (e !== "cancel") {
      ElMessage.error(`重建失败: ${e?.response?.data?.detail || e.message}`);
    }
  } finally {
    rebuilding.value = false;
  }
}

onMounted(() => {
  loadEntries();
});
</script>

<style scoped>
.knowledge-layout {
  display: grid;
  gap: 20px;
}

.knowledge-hero {
  position: relative;
  display: flex;
  justify-content: space-between;
  gap: 28px;
  overflow: hidden;
  padding: 28px 30px;
  background:
    linear-gradient(118deg, rgba(42, 75, 58, 0.98), rgba(87, 104, 74, 0.94)),
    var(--lingshan-green-deep);
  color: #fff;
}

.knowledge-hero::after {
  position: absolute;
  top: -88px;
  right: 7%;
  width: 248px;
  height: 248px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  box-shadow:
    0 0 0 34px rgba(255, 255, 255, 0.04),
    0 0 0 78px rgba(255, 255, 255, 0.025);
  content: "";
}

.knowledge-hero > * {
  position: relative;
  z-index: 1;
}

.hero-kicker,
.card-kicker,
.stat-kicker {
  font-family: Georgia, "Times New Roman", serif;
  letter-spacing: 0.14em;
}

.hero-kicker {
  color: #f7ddb7;
  font-size: 11px;
}

.hero-copy h2 {
  margin: 10px 0 8px;
  font-family: Georgia, "STSong", serif;
  font-size: clamp(28px, 4vw, 40px);
  font-weight: 600;
}

.hero-copy p {
  max-width: 720px;
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.7;
}

.hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 13px;
  white-space: nowrap;
}

.hero-pill.muted {
  color: rgba(255, 255, 255, 0.78);
}

.hero-side {
  display: grid;
  align-content: end;
  gap: 14px;
  min-width: 320px;
}

.hero-status {
  padding: 16px 18px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(8px);
}

.hero-status-label {
  display: inline-block;
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;
}

.hero-status strong {
  display: block;
  margin-bottom: 6px;
  font-size: 22px;
}

.hero-status p {
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  font-size: 13px;
  line-height: 1.65;
}

.hero-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  position: relative;
  display: grid;
  gap: 8px;
  min-height: 172px;
  overflow: hidden;
  padding: 20px;
  border: 1px solid color-mix(in srgb, var(--accent) 18%, white);
  border-radius: 18px;
  background:
    radial-gradient(circle at 100% 0, var(--accent-soft), transparent 44%),
    rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.07);
}

.stat-card::after {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 56%;
  height: 4px;
  border-radius: 0 999px 0 0;
  background: var(--accent);
  content: "";
}

.stat-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.stat-icon {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 12px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 19px;
}

.stat-kicker {
  color: color-mix(in srgb, var(--accent) 72%, #64748b);
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
  color: #475569;
  font-size: 13px;
}

.stat-note {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.knowledge-main {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 16px;
  align-items: start;
}

.knowledge-table-card,
.side-card {
  padding: 22px;
}

.card-heading,
.side-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.card-heading h3,
.side-heading h3 {
  margin: 5px 0 4px;
  color: #0f172a;
  font-family: Georgia, "STSong", serif;
  font-size: 21px;
}

.card-heading p,
.side-heading p {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.card-kicker {
  color: #0f766e;
  font-size: 9px;
}

.heading-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

.filter-toolbar {
  display: flex;
  gap: 12px;
  margin: 18px 0 16px;
  padding: 14px;
  border: 1px solid rgba(102, 128, 107, 0.12);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(245, 247, 242, 0.92), rgba(255, 255, 255, 0.96));
}

.search-input {
  flex: 1;
}

.category-select {
  width: 220px;
  flex: none;
}

.table-shell {
  overflow: hidden;
  border: 1px solid rgba(93, 105, 92, 0.12);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
}

.title-cell strong,
.source-cell span {
  display: block;
  color: #20352a;
}

.title-cell p,
.source-cell small {
  display: block;
  margin: 5px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.55;
}

.source-cell small {
  color: var(--lingshan-gold-deep);
}

.category-tag {
  border-color: rgba(102, 128, 107, 0.18);
  color: var(--lingshan-green-deep);
  background: rgba(232, 240, 233, 0.72);
}

.alias-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.alias-more,
.muted-text {
  color: #94a3b8;
  font-size: 12px;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.pagination-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 18px;
}

.pagination-note {
  color: #64748b;
  font-size: 12px;
}

.action-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.action-item {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(93, 105, 92, 0.1);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(252, 250, 245, 0.95), rgba(255, 255, 255, 0.96));
}

.action-copy strong {
  display: block;
  color: #20352a;
  font-size: 15px;
}

.action-copy p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.65;
}

.action-item.compact {
  background: rgba(239, 247, 242, 0.82);
}

.status-list {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 13px 14px;
  border-radius: 14px;
  background: #f8faf8;
  color: #475569;
  font-size: 13px;
}

.status-row strong {
  text-align: right;
}

.tone-ready {
  color: #0f766e;
}

.tone-busy {
  color: #b45309;
}

.tone-waiting {
  color: #64748b;
}

.guidance-card ul {
  margin: 16px 0 0;
  padding-left: 18px;
  color: #475569;
}

.guidance-card li {
  margin-bottom: 8px;
  line-height: 1.65;
}

.dialog-intro {
  margin-bottom: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(93, 105, 92, 0.12);
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(245, 247, 242, 0.95), rgba(255, 255, 255, 0.96));
}

.dialog-intro p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.dialog-aliases {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

:deep(.knowledge-table .el-table__header th) {
  background: #f4f6f1;
  color: #42594b;
  font-weight: 700;
}

:deep(.knowledge-table .el-table__row td) {
  background: transparent;
}

:deep(.knowledge-table .el-table__row:hover td) {
  background: #fcfaf5 !important;
}

:deep(.knowledge-dialog .el-dialog__header) {
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(93, 105, 92, 0.1);
}

:deep(.knowledge-dialog .el-dialog__title) {
  color: #20352a;
  font-family: "STKaiti", "KaiTi", "FangSong", serif;
  font-size: 24px;
}

@media (max-width: 1320px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .knowledge-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .knowledge-hero,
  .card-heading,
  .side-heading,
  .pagination-wrap {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-side {
    min-width: 0;
    width: 100%;
  }

  .hero-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .filter-toolbar {
    flex-direction: column;
  }

  .category-select {
    width: 100%;
  }

  .stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
