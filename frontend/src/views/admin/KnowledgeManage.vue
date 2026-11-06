<template>
  <section class="knowledge-layout">
    <header class="panel-card knowledge-hero">
      <div class="hero-copy">
        <h2>知识资产管理</h2>
        <p>维护景点讲解、游客常见问题和运营补充资料。</p>
      </div>

      <div class="hero-actions">
        <span v-if="lastUpdatedAt" class="updated-at">读取于 {{ lastUpdatedAt }}</span>
        <el-button :icon="RefreshRight" :loading="loading" @click="loadEntries">刷新</el-button>
        <el-button type="primary" :icon="Plus" @click="openDialog()">新增知识</el-button>
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

    <div class="knowledge-main">
      <article class="panel-card knowledge-table-card">
        <div class="card-heading">
          <h3>知识条目</h3>
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
          <el-button v-if="activeFilterCount" @click="clearFilters">清除筛选</el-button>
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

            <el-table-column prop="source" label="来源" width="160" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="source-text">{{ sourceLabel(row.source) }}</span>
              </template>
            </el-table-column>

            <el-table-column label="别名" width="160">
              <template #default="{ row }">
                <div v-if="row.aliases?.length" class="alias-list">
                  <el-tag
                    v-for="alias in row.aliases.slice(0, 2)"
                    :key="alias"
                    size="small"
                    effect="plain"
                  >
                    {{ alias }}
                  </el-tag>
                  <span v-if="row.aliases.length > 2" class="alias-more">+{{ row.aliases.length - 2 }}</span>
                </div>
                <span v-else class="muted-text">暂无别名</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="148">
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
        <section class="knowledge-maintenance" aria-label="知识库维护">
          <h3>知识库维护</h3>
          <p>新增或编辑知识后，按需同步资料并重建检索索引。</p>
          <el-button :icon="UploadFilled" :loading="syncing" @click="handleSync">同步官方资料</el-button>
          <el-button :icon="Operation" :loading="rebuilding" @click="handleRebuildIndex">重建检索索引</el-button>
        </section>
        <details class="knowledge-guidance">
          <summary>知识录入建议</summary>
          <ul>
            <li>标题使用游客容易想到的景点名称或问题。</li>
            <li>标明资料来源，方便后续核对。</li>
            <li>补充常用别名和口语问法。</li>
          </ul>
        </details>
      </aside>
    </div>

    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑知识条目' : '新增知识条目'"
      width="min(640px, calc(100vw - 32px))"
      class="knowledge-dialog"
      :before-close="requestCloseDialog"
    >
      <div class="dialog-intro">
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
        <el-button @click="requestCloseDialog()">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">提交</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { onBeforeRouteLeave } from "vue-router";
import {
  Operation,
  Plus,
  RefreshRight,
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
const formBaseline = ref("");

const form = ref({
  title: "",
  category: "",
  content: "",
  source: "管理员手动录入",
  aliases: [],
});
const hasUnsavedChanges = computed(() =>
  Boolean(formBaseline.value) && JSON.stringify(form.value) !== formBaseline.value,
);

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

const activeFilterCount = computed(
  () => Number(Boolean(searchQuery.value.trim())) + Number(Boolean(selectedCategory.value)),
);

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

function sourceLabel(source) {
  return source || "管理员手动录入";
}

function clearFilters() {
  searchQuery.value = "";
  selectedCategory.value = "";
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

  formBaseline.value = JSON.stringify(form.value);
  aliasInput.value = "";
  dialogVisible.value = true;
}

async function requestCloseDialog(done) {
  if (submitting.value) return;
  if (hasUnsavedChanges.value) {
    try {
      await ElMessageBox.confirm("关闭后将丢弃当前未保存的修改。", "放弃更改？", {
        type: "warning",
        confirmButtonText: "放弃修改",
        cancelButtonText: "继续编辑",
      });
    } catch {
      return;
    }
  }
  if (typeof done === "function") done();
  else dialogVisible.value = false;
}

onBeforeRouteLeave(async () => {
  if (!dialogVisible.value || !hasUnsavedChanges.value) return true;
  try {
    await ElMessageBox.confirm("离开后将丢弃当前未保存的知识条目。", "离开编辑？", {
      type: "warning",
      confirmButtonText: "离开页面",
      cancelButtonText: "继续编辑",
    });
    return true;
  } catch {
    return false;
  }
});

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
  gap: 12px;
}

.knowledge-hero {
  position: relative;
  display: flex;
  justify-content: space-between;
  gap: 28px;
  overflow: hidden;
  padding: 20px 24px;
  background: linear-gradient(155deg, #241d16 0%, #2e2620 50%, #3a3028 100%);
  border: 1px solid #342d26;
  color: #fff7eb;
}

.knowledge-hero > * {
  position: relative;
  z-index: 1;
}

.hero-copy h2 {
  margin: 10px 0 8px;
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 600;
}

.hero-copy p {
  max-width: 720px;
  margin: 0;
  color: rgba(255, 247, 235, 0.56);
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
  border-radius: 0;
  background: rgba(255, 255, 255, 0.1);
  font-size: 13px;
  white-space: nowrap;
}

.hero-pill.muted {
  color: rgba(255, 255, 255, 0.78);
}

.hero-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.updated-at { color: #59645d; font-size: 12px; }

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: #fffaf2;
  box-shadow: none;
  overflow: hidden;
}

.stat-card-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.stat-icon {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 2px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 17px;
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 2px;
}

.stat-value {
  color: #241d16;
  font-size: 17px;
  font-weight: 700;
  line-height: 1;
}

.stat-label {
  color: #675a4e;
  font-size: 12px;
}

.stat-note {
  margin: 0;
  color: #675a4e;
  font-size: 11px;
  line-height: 1.5;
}

.knowledge-main {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 12px;
  align-items: start;
}

.knowledge-table-card,
.side-card {
  padding: 18px;
  border: 1px solid #d4c8b8;
  background: #fffaf2;
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
  color: #241d16;
  font-size: 17px;
  font-weight: 600;
}

.card-heading p,
.side-heading p {
  margin: 0;
  color: #675a4e;
  font-size: 12px;
  line-height: 1.55;
}

.heading-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #675a4e;
  font-size: 12px;
  white-space: nowrap;
}

.filter-toolbar {
  display: flex;
  gap: 12px;
  margin: 18px 0 16px;
  padding: 14px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: #fffaf2;
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
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: rgba(255, 255, 255, 0.9);
}

.source-text {
  color: #202723;
  font-size: 13px;
}

.title-cell strong {
  display: block;
  color: #202723;
}

.title-cell p {
  display: block;
  margin: 5px 0 0;
  color: #59645d;
  font-size: 12px;
  line-height: 1.55;
}

.category-tag {
  border-color: #dce2dd;
  color: #46574c;
  background: #f5f7f5;
}

.alias-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.alias-more,
.muted-text {
  color: #59645d;
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
  color: #59645d;
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
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: #fffaf2;
}

.action-copy strong {
  display: block;
  color: #241d16;
  font-size: 14px;
}

.action-copy p {
  margin: 6px 0 0;
  color: #675a4e;
  font-size: 12px;
  line-height: 1.65;
}

.action-item.compact {
  background: rgba(247, 240, 230, 0.82);
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
  border-radius: 0;
  background: #f0e9dc;
  color: #675a4e;
  font-size: 13px;
}

.status-row strong {
  text-align: right;
}

.tone-ready {
  color: #8a5d22;
}

.tone-busy {
  color: #c47c4a;
}

.tone-waiting {
  color: #675a4e;
}

.guidance-card ul {
  margin: 16px 0 0;
  padding-left: 18px;
  color: #675a4e;
}

.guidance-card li {
  margin-bottom: 8px;
  line-height: 1.65;
}

.dialog-intro {
  margin-bottom: 14px;
  padding: 14px 16px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: #fffaf2;
}

.dialog-intro p {
  margin: 6px 0 0;
  color: #675a4e;
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
  background: #f6f8f6;
  color: #59645d;
  font-weight: 500;
}

:deep(.knowledge-table .el-table__row td) {
  background: transparent;
}

:deep(.knowledge-table .el-table__row:hover td) {
  background: #f6f8f6 !important;
}

:deep(.knowledge-table .el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: #fafbfa;
}

:deep(.knowledge-dialog .el-dialog__header) {
  padding-bottom: 8px;
  border-bottom: 1px solid #dce2dd;
}

:deep(.knowledge-dialog .el-dialog__title) {
  color: #202723;
  font-family: inherit;
  font-size: 20px;
}

:deep(.knowledge-hero .el-button) {
  --el-button-bg-color: #fff;
  --el-button-border-color: #dce2dd;
  --el-button-text-color: #202723;
  --el-button-hover-bg-color: #f0f2f0;
  --el-button-hover-border-color: #cbd4ce;
  --el-button-hover-text-color: #202723;
}

:deep(.knowledge-table-card .el-pagination.is-background .el-pager li:not(.is-disabled).is-active) {
  --el-pagination-bg-color: #285a46;
  --el-pagination-text-color: #fff;
}

:deep(.table-actions .el-button--primary) {
  --el-button-bg-color: #285a46;
  --el-button-border-color: #285a46;
  --el-button-text-color: #fff;
  --el-button-hover-bg-color: #204a39;
  --el-button-hover-border-color: #204a39;
  --el-button-hover-text-color: #fff;
}

:deep(.table-actions .el-button--danger) {
  --el-button-text-color: #b33a31;
}

:deep(.knowledge-hero .el-button--primary) {
  --el-button-bg-color: #285a46;
  --el-button-border-color: #285a46;
  --el-button-text-color: #fff;
  --el-button-hover-bg-color: #204a39;
  --el-button-hover-border-color: #204a39;
  --el-button-hover-text-color: #fff;
}

:deep(.side-card .el-tag--success) {
  --el-tag-bg-color: rgba(138, 93, 34, 0.08);
  --el-tag-border-color: rgba(138, 93, 34, 0.18);
  --el-tag-text-color: #8a5d22;
}

:deep(.action-item .el-button) {
  --el-button-bg-color: #fffaf2;
  --el-button-border-color: #d4c8b8;
  --el-button-text-color: #241d16;
  --el-button-hover-bg-color: #f0e9dc;
  --el-button-hover-border-color: #b8a890;
  --el-button-hover-text-color: #241d16;
  --el-button-active-bg-color: #e8dfd2;
  --el-button-active-border-color: #b8a890;
  --el-button-active-text-color: #241d16;
  box-shadow: none;
  outline: none;
}

:deep(.action-item .el-button .el-icon) {
  color: var(--el-button-text-color);
}

:deep(.action-item .el-button.is-loading .el-icon) {
  color: #675a4e;
}

:deep(.action-item .el-button:focus-visible) {
  outline: 2px solid #8a5d22;
  outline-offset: 1px;
}

:deep(.action-item .el-button--primary) {
  --el-button-bg-color: #241d16;
  --el-button-border-color: #241d16;
  --el-button-text-color: #fff7eb;
  --el-button-hover-bg-color: #3a3028;
  --el-button-hover-border-color: #3a3028;
  --el-button-hover-text-color: #fff7eb;
  --el-button-active-bg-color: #1a1510;
  --el-button-active-border-color: #1a1510;
  --el-button-active-text-color: #fff7eb;
  box-shadow: none;
  outline: none;
}

:deep(.action-item .el-button--primary.is-plain) {
  --el-button-bg-color: rgba(36, 29, 22, 0.06);
  --el-button-border-color: #241d16;
  --el-button-text-color: #241d16;
  --el-button-hover-bg-color: #241d16;
  --el-button-hover-border-color: #241d16;
  --el-button-hover-text-color: #fff7eb;
  --el-button-active-bg-color: #1a1510;
  --el-button-active-border-color: #1a1510;
  --el-button-active-text-color: #fff7eb;
  box-shadow: none;
  outline: none;
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
