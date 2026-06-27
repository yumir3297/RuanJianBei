<template>
  <section class="panel-card admin-panel">
    <h2 class="section-title">知识盲区处理</h2>
    <p class="section-subtitle">游客提问但当前资料库无法回答的问题，可补充为 FAQ 后自动解决</p>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="待处理" name="open">
        <el-skeleton v-if="loading" :rows="5" animated />
        <el-alert v-else-if="error" type="warning" :title="error" show-icon />
        <el-empty v-else-if="!spots.length" description="暂无待处理盲区" />
        <el-table v-else :data="pagedSpots" stripe>
          <el-table-column prop="normalized_query" label="规范问题" min-width="200" />
          <el-table-column label="游客原始问法" min-width="250">
            <template #default="{ row }">
              <el-tag v-for="(q, idx) in row.raw_query_samples" :key="idx" size="small" style="margin: 2px">
                {{ q }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="被问次数" width="100">
            <template #default="{ row }">
              <el-tag type="warning">{{ row.hit_count }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="first_seen_at" label="首次出现" width="180" />
          <el-table-column prop="last_seen_at" label="最近出现" width="180" />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openResolveDialog(row)">补充 FAQ</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="已解决" name="resolved">
        <el-skeleton v-if="loading" :rows="5" animated />
        <el-alert v-else-if="error" type="warning" :title="error" show-icon />
        <el-empty v-else-if="!spots.length" description="暂无已解决盲区" />
        <el-table v-else :data="pagedSpots" stripe>
          <el-table-column prop="normalized_query" label="规范问题" min-width="200" />
          <el-table-column prop="resolution_type" label="解决方式" width="100" />
          <el-table-column prop="resolved_faq_id" label="FAQ ID" width="200" />
          <el-table-column prop="resolved_at" label="解决时间" width="180" />
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <div v-if="spots.length > pageSize" class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="spots.length"
        layout="total, prev, pager, next"
        background
      />
    </div>

    <el-dialog v-model="dialogVisible" title="补充 FAQ" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="FAQ ID" prop="faq_id">
          <el-input v-model="form.faq_id" placeholder="例如: faq_admin_卫生间位置_a3f2b1" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="form.category" placeholder="请选择分类">
            <el-option label="实用信息" value="实用信息" />
            <el-option label="景点信息" value="景点信息" />
            <el-option label="历史文化" value="历史文化" />
            <el-option label="游览路线" value="游览路线" />
            <el-option label="建筑艺术" value="建筑艺术" />
            <el-option label="景区概况" value="景区概况" />
          </el-select>
        </el-form-item>
        <el-form-item label="别名" prop="aliases">
          <el-input v-model="aliasInput" placeholder="输入别名后回车添加" @keyup.enter="addAlias" />
          <div style="margin-top: 8px">
            <el-tag v-for="(alias, idx) in form.aliases" :key="idx" closable @close="form.aliases.splice(idx, 1)" style="margin: 4px">
              {{ alias }}
            </el-tag>
          </div>
          <div style="color: #64748b; font-size: 12px; margin-top: 4px">提示: 游客原始问法会自动合并</div>
        </el-form-item>
        <el-form-item label="标准答案" prop="answer">
          <el-input v-model="form.answer" type="textarea" :rows="5" placeholder="请输入标准答案" />
        </el-form-item>
        <el-form-item label="信息来源" prop="sources">
          <el-input v-model="sourceInput" placeholder="输入来源后回车添加" @keyup.enter="addSource" />
          <div style="margin-top: 8px">
            <el-tag v-for="(src, idx) in form.sources" :key="idx" closable @close="form.sources.splice(idx, 1)" style="margin: 4px">
              {{ src }}
            </el-tag>
          </div>
          <div style="color: #64748b; font-size: 12px; margin-top: 4px">提示: 必须注明信息来源，至少一个非空</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitResolve" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { fetchBlindSpots, resolveBlindSpotWithFAQ } from "../../api/admin";

const activeTab = ref("open");
const loading = ref(false);
const error = ref("");
const spots = ref([]);

const currentPage = ref(1);
const pageSize = 15;

const pagedSpots = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return spots.value.slice(start, start + pageSize);
});

const dialogVisible = ref(false);
const submitting = ref(false);
const currentSpot = ref(null);
const formRef = ref(null);
const aliasInput = ref("");
const sourceInput = ref("");

const form = ref({
  faq_id: "",
  category: "",
  aliases: [],
  answer: "",
  sources: [],
});

const rules = {
  faq_id: [{ required: true, message: "请输入 FAQ ID", trigger: "blur" }],
  category: [{ required: true, message: "请选择分类", trigger: "change" }],
  answer: [{ required: true, message: "请输入标准答案", trigger: "blur" }],
};

async function loadSpots() {
  loading.value = true;
  error.value = "";
  currentPage.value = 1;
  try {
    spots.value = await fetchBlindSpots(activeTab.value, 50);
  } catch (e) {
    error.value = `加载失败: ${e?.response?.data?.detail || e.message}`;
  } finally {
    loading.value = false;
  }
}

function handleTabChange() {
  loadSpots();
}

function openResolveDialog(spot) {
  currentSpot.value = spot;
  const timestamp = Date.now().toString().slice(-6);
  const normalized = spot.normalized_query
    .replace(/[^a-zA-Z0-9\u4e00-\u9fa5_-]/g, "_")
    .replace(/_+/g, "_")
    .slice(0, 20)
    .replace(/^_|_$/g, "");
  form.value = {
    faq_id: `faq_admin_${normalized}_${timestamp}`,
    category: "实用信息",
    aliases: [],
    answer: "",
    sources: [],
  };
  aliasInput.value = "";
  sourceInput.value = "";
  dialogVisible.value = true;
}

function addAlias() {
  const val = aliasInput.value.trim();
  if (val && !form.value.aliases.includes(val)) {
    form.value.aliases.push(val);
    aliasInput.value = "";
  }
}

function addSource() {
  const val = sourceInput.value.trim();
  if (val && !form.value.sources.includes(val)) {
    form.value.sources.push(val);
    sourceInput.value = "";
  }
}

async function submitResolve() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    if (form.value.sources.length === 0) {
      ElMessage.warning("至少添加一个信息来源");
      return;
    }
    submitting.value = true;
    try {
      const res = await resolveBlindSpotWithFAQ(currentSpot.value.id, form.value);
      ElMessage.success(`已补充 FAQ，索引刷新耗时 ${res.faq_reload_ms.toFixed(1)}ms，共 ${res.faq_index_count} 条`);
      dialogVisible.value = false;
      loadSpots();
    } catch (e) {
      ElMessage.error(`提交失败: ${e?.response?.data?.detail || e.message}`);
    } finally {
      submitting.value = false;
    }
  });
}

onMounted(() => {
  loadSpots();
});
</script>

<style scoped>
.admin-panel {
  padding: 24px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>
