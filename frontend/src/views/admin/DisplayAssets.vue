<template>
  <section class="display-assets-layout">
    <header class="panel-card assets-hero">
      <div>
        <span class="hero-kicker">SCENIC MATERIALS</span>
        <h2>页面资源替换</h2>
        <p>集中维护游客端页面中的可替换视觉资源。当前先开放数字人页面风景背景的管理入口。</p>
      </div>
      <div class="hero-actions">
        <span v-if="lastUpdatedAt" class="hero-updated">更新于 {{ lastUpdatedAt }}</span>
        <el-button :loading="pageLoading" @click="loadPageData">刷新配置</el-button>
      </div>
    </header>

    <div class="stat-grid" v-loading="pageLoading && !initialized">
      <article
        class="stat-card"
        :style="{ '--accent': '#2563eb', '--accent-soft': '#e1ebff' }"
      >
        <span class="stat-kicker">BACKGROUND</span>
        <strong class="stat-value">{{ backgroundAsset.asset_url ? "已设置" : "未设置" }}</strong>
        <span class="stat-label">游客端风景背景</span>
        <p class="stat-note">
          {{ backgroundAsset.asset_url ? "已接入自定义景区背景图。" : "当前仍使用内置默认背景。" }}
        </p>
      </article>
    </div>

    <article class="panel-card asset-card">
      <div class="section-heading">
        <div>
          <span class="section-kicker">ASSET REPLACEMENT</span>
          <h3>图片替换功能区</h3>
          <p>这里专门放页面可替换素材。第一阶段先接入游客端风景背景，后续可继续扩展按钮贴图、场景装饰等资源。</p>
        </div>
        <el-tag size="small" type="success" effect="plain">可扩展</el-tag>
      </div>

      <div class="asset-subcard">
        <div class="block-head">
          <strong>游客端风景背景</strong>
          <small>支持 JPG / PNG / WEBP，建议横向景区实景图</small>
        </div>

        <div class="asset-preview">
          <img
            v-if="backgroundPreviewUrl"
            :src="backgroundPreviewUrl"
            alt="游客端背景预览"
          />
          <div v-else class="asset-placeholder">
            <strong>当前未设置自定义背景</strong>
            <span>上传后将用于游客端数字人页面背景</span>
          </div>
        </div>

        <input
          ref="backgroundInputRef"
          class="hidden-input"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          @change="handleBackgroundFileChange"
        />

        <div class="asset-file-meta">
          <strong>{{ selectedBackgroundFile?.name || backgroundAsset.file_name || "尚未选择图片" }}</strong>
          <span>{{ backgroundAsset.updated_at ? `最近更新：${formatUpdatedAt(backgroundAsset.updated_at)}` : "上传后会自动记录更新时间" }}</span>
        </div>

        <div class="asset-actions">
          <el-button @click="openBackgroundPicker">选择图片</el-button>
          <el-button
            type="primary"
            :loading="backgroundUploading"
            :disabled="!selectedBackgroundFile"
            @click="handleUploadBackground"
          >
            应用背景
          </el-button>
          <el-button
            :disabled="!backgroundAsset.asset_url || backgroundUploading"
            @click="handleClearBackground"
          >
            清除自定义背景
          </el-button>
        </div>
      </div>

      <div class="asset-guidance">
        <strong>后续可继续加入</strong>
        <ul>
          <li>首页主视觉背景替换</li>
          <li>游客端功能卡装饰图替换</li>
          <li>答辩演示专用主题素材切换</li>
        </ul>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import {
  clearTouristBackground,
  fetchDisplayAssets,
  uploadTouristBackground,
} from "../../api/admin";
import { API_BASE_URL } from "../../api/http";

const initialized = ref(false);
const pageLoading = ref(false);
const lastUpdatedAt = ref("");
const backgroundInputRef = ref(null);
const selectedBackgroundFile = ref(null);
const selectedBackgroundPreviewUrl = ref("");
const backgroundUploading = ref(false);
const backgroundAsset = ref({
  asset_url: "",
  file_name: "",
  updated_at: "",
});

const backgroundPreviewUrl = computed(() =>
  selectedBackgroundPreviewUrl.value || resolveAssetUrl(backgroundAsset.value.asset_url),
);

function resolveAssetUrl(assetUrl) {
  if (!assetUrl) {
    return "";
  }
  if (/^https?:\/\//i.test(assetUrl)) {
    return assetUrl;
  }
  return new URL(assetUrl, `${API_BASE_URL}/`).href;
}

function formatNow() {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function formatUpdatedAt(value) {
  if (!value) {
    return "";
  }
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function revokeBackgroundPreview() {
  if (selectedBackgroundPreviewUrl.value) {
    URL.revokeObjectURL(selectedBackgroundPreviewUrl.value);
    selectedBackgroundPreviewUrl.value = "";
  }
}

function openBackgroundPicker() {
  backgroundInputRef.value?.click();
}

function handleBackgroundFileChange(event) {
  const file = event.target?.files?.[0] || null;
  selectedBackgroundFile.value = file;
  revokeBackgroundPreview();
  if (file) {
    selectedBackgroundPreviewUrl.value = URL.createObjectURL(file);
  }
}

async function loadDisplayAssetState() {
  const assets = await fetchDisplayAssets();
  backgroundAsset.value = {
    asset_url: assets?.tourist_background?.asset_url || "",
    file_name: assets?.tourist_background?.file_name || "",
    updated_at: assets?.tourist_background?.updated_at || "",
  };
}

async function loadPageData() {
  pageLoading.value = true;
  try {
    await loadDisplayAssetState();
    initialized.value = true;
    lastUpdatedAt.value = formatNow();
  } catch (error) {
    ElMessage.error(`配置读取失败：${error?.response?.data?.detail || error.message || "请检查后端服务"}`);
  } finally {
    pageLoading.value = false;
  }
}

async function handleUploadBackground() {
  if (!selectedBackgroundFile.value) {
    return;
  }
  backgroundUploading.value = true;
  try {
    const response = await uploadTouristBackground(selectedBackgroundFile.value);
    backgroundAsset.value = {
      asset_url: response.asset?.asset_url || "",
      file_name: response.asset?.file_name || "",
      updated_at: response.asset?.updated_at || "",
    };
    if (backgroundInputRef.value) {
      backgroundInputRef.value.value = "";
    }
    selectedBackgroundFile.value = null;
    revokeBackgroundPreview();
    lastUpdatedAt.value = formatNow();
    ElMessage.success("游客端背景已更新");
  } catch (error) {
    ElMessage.error(`背景上传失败：${error?.response?.data?.detail || error.message}`);
  } finally {
    backgroundUploading.value = false;
  }
}

async function handleClearBackground() {
  try {
    await ElMessageBox.confirm("确定清除当前游客端自定义背景吗？", "提示", { type: "warning" });
    backgroundUploading.value = true;
    const response = await clearTouristBackground();
    backgroundAsset.value = {
      asset_url: response.asset?.asset_url || "",
      file_name: response.asset?.file_name || "",
      updated_at: response.asset?.updated_at || "",
    };
    if (backgroundInputRef.value) {
      backgroundInputRef.value.value = "";
    }
    selectedBackgroundFile.value = null;
    revokeBackgroundPreview();
    lastUpdatedAt.value = formatNow();
    ElMessage.success("自定义背景已清除");
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error(`清除失败：${error?.response?.data?.detail || error.message}`);
    }
  } finally {
    backgroundUploading.value = false;
  }
}

onMounted(() => {
  loadPageData();
});

onBeforeUnmount(() => {
  revokeBackgroundPreview();
});
</script>

<style scoped>
.display-assets-layout {
  display: grid;
  gap: 20px;
}

.assets-hero {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  overflow: hidden;
  padding: 28px 30px;
  background:
    linear-gradient(120deg, rgba(37, 64, 94, 0.96), rgba(73, 112, 126, 0.92)),
    var(--lingshan-green-deep);
  color: #fff;
}

.assets-hero::after {
  position: absolute;
  top: -84px;
  right: 7%;
  width: 220px;
  height: 220px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 50%;
  box-shadow:
    0 0 0 32px rgba(255, 255, 255, 0.04),
    0 0 0 74px rgba(255, 255, 255, 0.02);
  content: "";
}

.assets-hero > * {
  position: relative;
  z-index: 1;
}

.hero-kicker,
.stat-kicker,
.section-kicker {
  font-family: Georgia, "Times New Roman", serif;
  letter-spacing: 0.14em;
}

.hero-kicker {
  color: #f4dcc0;
  font-size: 11px;
}

.assets-hero h2 {
  margin: 8px 0 6px;
  font-family: Georgia, "STSong", serif;
  font-size: clamp(28px, 4vw, 38px);
  font-weight: 600;
}

.assets-hero p {
  max-width: 720px;
  margin: 0;
  color: rgba(255, 255, 255, 0.78);
  line-height: 1.68;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hero-updated {
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
}

.stat-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.stat-card {
  display: grid;
  gap: 8px;
  min-height: 156px;
  padding: 20px;
  border: 1px solid color-mix(in srgb, var(--accent) 18%, white);
  border-radius: 18px;
  background:
    radial-gradient(circle at 100% 0, var(--accent-soft), transparent 44%),
    rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.07);
}

.stat-kicker {
  color: color-mix(in srgb, var(--accent) 72%, #64748b);
  font-size: 9px;
}

.stat-value {
  color: #0f172a;
  font-family: Georgia, "STSong", serif;
  font-size: clamp(28px, 3.6vw, 36px);
  line-height: 1.1;
}

.stat-label {
  color: #475569;
  font-size: 13px;
}

.stat-note {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.62;
}

.asset-card {
  padding: 22px;
}

.section-heading,
.block-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.section-heading h3 {
  margin: 5px 0 4px;
  color: #0f172a;
  font-family: Georgia, "STSong", serif;
  font-size: 21px;
}

.section-heading p,
.block-head small {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.58;
}

.section-kicker {
  color: #0f766e;
  font-size: 9px;
}

.asset-subcard,
.asset-guidance {
  padding: 16px;
  border: 1px solid rgba(93, 105, 92, 0.12);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(245, 247, 242, 0.95), rgba(255, 255, 255, 0.96));
}

.asset-subcard {
  margin-top: 18px;
}

.block-head strong,
.asset-guidance strong {
  color: #20352a;
  font-size: 15px;
}

.asset-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
  margin-top: 14px;
  overflow: hidden;
  border: 1px solid rgba(93, 105, 92, 0.12);
  border-radius: 18px;
  background: #f5f7f2;
}

.asset-preview img {
  width: 100%;
  height: 220px;
  object-fit: cover;
  display: block;
}

.asset-placeholder {
  display: grid;
  gap: 6px;
  text-align: center;
  color: #64748b;
}

.asset-file-meta {
  display: grid;
  gap: 4px;
  margin-top: 14px;
}

.asset-file-meta strong {
  color: #20352a;
  font-size: 14px;
}

.asset-file-meta span {
  color: #64748b;
  font-size: 12px;
}

.asset-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.asset-guidance {
  margin-top: 16px;
}

.asset-guidance ul {
  margin: 12px 0 0;
  padding-left: 18px;
  color: #475569;
}

.asset-guidance li {
  margin-bottom: 8px;
  line-height: 1.6;
}

.hidden-input {
  display: none;
}

@media (max-width: 760px) {
  .assets-hero,
  .hero-actions {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
