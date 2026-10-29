<template>
  <article class="panel-card import-panel">
    <div class="panel-heading">
      <div><h3>批量导入 PDF / JSON</h3><p>上传后先进入草稿区；同一来源文档可填写文档 ID 进行重导。</p></div>
      <div class="panel-actions">
        <el-select v-if="batches.length" v-model="selectedBatchId" size="small" @change="loadSelectedBatch">
          <el-option v-for="item in batches" :key="item.id" :label="`${item.id.slice(0, 8)} · ${item.state}`" :value="item.id" />
        </el-select>
        <el-button v-if="batch" :loading="refreshing" @click="refresh">刷新任务</el-button>
      </div>
    </div>
    <div class="upload-controls">
      <el-upload v-model:file-list="files" drag multiple :auto-upload="false" accept=".pdf,.json">
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖放文件到此处，或 <em>点击选择</em></div>
        <template #tip><div class="el-upload__tip">支持 PDF 和 JSON，可一次选择多个文件。</div></template>
      </el-upload>
      <div class="upload-actions">
        <el-input v-model="documentId" clearable placeholder="重导时填写来源文档 ID（新文档留空）" />
        <el-button type="primary" :loading="uploading" :disabled="!files.length" @click="submit">上传并解析</el-button>
      </div>
    </div>
    <div v-if="batch" class="batch-result">
      <div class="batch-title">
        <strong>任务 {{ batch.id }}</strong>
        <div class="batch-actions">
          <el-tag :type="batch.state === 'succeeded' ? 'success' : batch.state === 'failed' ? 'danger' : 'warning'">{{ batch.state }}</el-tag>
          <el-button v-if="['failed', 'partial'].includes(batch.state)" size="small" :loading="retrying" @click="retry">重试失败文件</el-button>
        </div>
      </div>
      <el-alert v-if="batch.error" :title="batch.error" type="warning" :closable="false" />
      <div v-for="job in batch.jobs" :key="job.id" class="job-card">
        <div class="job-title"><strong>{{ job.filename }}</strong><el-tag size="small" effect="plain">{{ job.stage }}</el-tag></div>
        <p v-if="job.error" class="job-error">{{ job.error }}</p>
        <p class="job-meta">来源文档 ID：{{ job.document_id || "—" }} · 草稿条目：{{ job.knowledge_entry_ids?.length || 0 }}</p>
        <div v-for="conflict in job.conflicts || []" :key="conflict.id" class="conflict-card">
          <div class="conflict-heading"><strong>来源内容与人工草稿有冲突</strong><el-tag size="small" type="danger">{{ conflict.state }}</el-tag></div>
          <div class="conflict-columns">
            <div><small>当前草稿</small><strong>{{ conflict.current_revision?.title }}</strong><p>{{ conflict.current_revision?.content }}</p></div>
            <div><small>新来源</small><strong>{{ conflict.incoming_revision?.title }}</strong><p>{{ conflict.incoming_revision?.content }}</p></div>
          </div>
          <div v-if="conflict.state === 'pending'" class="conflict-actions">
            <el-button size="small" @click="resolve(conflict, 'keep_current')">保留当前草稿</el-button>
            <el-button size="small" type="primary" plain @click="resolve(conflict, 'use_incoming')">采用新来源</el-button>
            <el-button size="small" type="primary" @click="merge(conflict)">编辑合并</el-button>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { UploadFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { fetchKnowledgeImport, fetchRecentKnowledgeImports, resolveKnowledgeConflict, retryKnowledgeImport, uploadKnowledgeFiles } from "../../api/knowledgeImports";

const props = defineProps({ entries: { type: Array, default: () => [] } });
const emit = defineEmits(["changed"]);
const files = ref([]);
const documentId = ref("");
const batch = ref(null);
const batches = ref([]);
const selectedBatchId = ref("");
const uploading = ref(false);
const refreshing = ref(false);
const retrying = ref(false);

async function submit() {
  uploading.value = true;
  try {
    batch.value = await uploadKnowledgeFiles(files.value.map((item) => item.raw), { documentId: documentId.value.trim() });
    selectedBatchId.value = batch.value.id;
    files.value = [];
    emit("changed");
    await refresh();
    await loadRecent();
    ElMessage.success("文件已进入导入队列");
  } catch (error) {
    ElMessage.error(`上传失败：${error?.response?.data?.detail || error.message}`);
  } finally {
    uploading.value = false;
  }
}

async function refresh() {
  if (!batch.value?.id) return;
  refreshing.value = true;
  try {
    batch.value = await fetchKnowledgeImport(batch.value.id);
    replaceRecent(batch.value);
    if (["queued", "processing"].includes(batch.value.state)) {
      window.setTimeout(refresh, 1800);
    } else {
      emit("changed");
    }
  } catch (error) {
    ElMessage.error(`读取导入状态失败：${error?.response?.data?.detail || error.message}`);
  } finally {
    refreshing.value = false;
  }
}

async function loadRecent() {
  try {
    batches.value = await fetchRecentKnowledgeImports();
    if (batches.value.length && !selectedBatchId.value) selectedBatchId.value = batches.value[0].id;
    if (selectedBatchId.value) await loadSelectedBatch();
  } catch (error) {
    ElMessage.error(`读取历史导入任务失败：${error?.response?.data?.detail || error.message}`);
  }
}

async function loadSelectedBatch() {
  if (!selectedBatchId.value) return;
  try {
    batch.value = await fetchKnowledgeImport(selectedBatchId.value);
    replaceRecent(batch.value);
    if (["queued", "processing"].includes(batch.value.state)) window.setTimeout(refresh, 1800);
  } catch (error) {
    ElMessage.error(`读取导入任务失败：${error?.response?.data?.detail || error.message}`);
  }
}

function replaceRecent(updated) {
  const index = batches.value.findIndex((item) => item.id === updated.id);
  if (index >= 0) batches.value[index] = updated;
  else batches.value.unshift(updated);
  selectedBatchId.value = updated.id;
}

async function retry() {
  if (!batch.value?.id) return;
  retrying.value = true;
  try {
    batch.value = await retryKnowledgeImport(batch.value.id);
    await refresh();
  } catch (error) {
    ElMessage.error(`重试导入失败：${error?.response?.data?.detail || error.message}`);
  } finally {
    retrying.value = false;
  }
}

async function resolve(conflict, choice, mergedPayload = null) {
  const entry = props.entries.find((item) => item.id === conflict.knowledge_entry_id);
  if (!entry) {
    ElMessage.error("找不到对应知识条目，请先刷新工作区");
    return;
  }
  try {
    await resolveKnowledgeConflict(conflict.id, { choice, expected_version: entry.lock_version, merged_payload: mergedPayload });
    ElMessage.success("冲突已处理");
    await refresh();
    emit("changed");
  } catch (error) {
    ElMessage.error(`处理冲突失败：${error?.response?.data?.detail || error.message}`);
  }
}

async function merge(conflict) {
  const entry = props.entries.find((item) => item.id === conflict.knowledge_entry_id);
  if (!entry) return ElMessage.error("找不到对应知识条目，请先刷新工作区");
  try {
    const { value } = await ElMessageBox.prompt("编辑合并后的完整内容", "合并来源与人工修改", {
      inputType: "textarea",
      inputValue: `${conflict.current_revision?.content || ""}\n\n${conflict.incoming_revision?.content || ""}`,
      inputValidator: (value) => Boolean(value.trim()) || "合并内容不能为空",
      confirmButtonText: "保存合并草稿",
    });
    const source = conflict.incoming_revision;
    await resolve(conflict, "merge", {
      title: source.title,
      category: source.category || entry.category,
      content: value,
      source: source.source || entry.source,
      aliases: source.aliases || entry.aliases || [],
      metadata_json: source.metadata_json || null,
      source_document_version_id: null,
    });
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error(`合并失败：${error?.message || error}`);
  }
}

onMounted(loadRecent);

</script>

<style scoped>
.import-panel { padding: 18px; border: 1px solid #d4c8b8; background: #fffaf2; }
.panel-heading,.batch-title,.job-title,.conflict-heading { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.panel-actions { display:flex; align-items:center; gap:8px; }
.batch-actions { display:flex; align-items:center; gap:8px; }
.panel-heading h3 { margin:0 0 4px; color:#241d16; font-size:17px; }
.panel-heading p,.job-meta { margin:0; color:#675a4e; font-size:12px; }
.upload-controls { display:grid; grid-template-columns:minmax(240px,1fr) minmax(300px,1fr); gap:16px; margin-top:16px; }
.upload-actions { display:grid; align-content:center; gap:12px; }
.upload-icon { font-size:28px; }
.batch-result { display:grid; gap:10px; margin-top:18px; }
.job-card,.conflict-card { display:grid; gap:8px; padding:12px; border:1px solid #d4c8b8; background:#fff; }
.job-error { margin:0; color:#b42318; font-size:12px; }
.conflict-card { margin-top:8px; border-color:#e6c6a8; }
.conflict-columns { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.conflict-columns > div { padding:10px; background:#faf7f2; }
.conflict-columns small { display:block; margin-bottom:4px; color:#8b735b; }
.conflict-columns strong { display:block; }
.conflict-columns p { max-height:120px; overflow:auto; margin:6px 0 0; white-space:pre-wrap; font-size:12px; }
.conflict-actions { display:flex; justify-content:flex-end; gap:8px; }
@media(max-width:800px) { .upload-controls,.conflict-columns { grid-template-columns:1fr; } }
</style>
