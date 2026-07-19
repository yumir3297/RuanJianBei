<template>
  <section class="display-assets-layout">
    <header class="assets-hero">
      <div>
        <h2>页面资源替换</h2>
        <p>统一管理游客端视觉资源，支持风景背景与轮播配图的上传替换。</p>
      </div>
      <div class="hero-actions">
        <span v-if="lastUpdatedAt" class="hero-updated">更新于 {{ lastUpdatedAt }}</span>
        <el-button :loading="pageLoading" @click="loadPageData" size="small" class="hero-refresh-btn">刷新配置</el-button>
      </div>
    </header>

    <div class="stat-row" v-loading="pageLoading && !initialized">
      <article class="stat-item">
        <div class="stat-icon stat-icon-blue">
          <el-icon :size="16"><PictureFilled /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-title">游客端风景背景</div>
          <div class="stat-desc">
            {{ backgroundAsset.asset_url ? "已接入自定义景区背景图" : "当前使用内置默认背景" }}
          </div>
        </div>
        <span :class="['stat-badge', { 'stat-badge-set': backgroundAsset.asset_url }]">
          {{ backgroundAsset.asset_url ? "已设置" : "未设置" }}
        </span>
      </article>
      <article class="stat-item">
        <div class="stat-icon stat-icon-gold">
          <el-icon :size="16"><Collection /></el-icon>
        </div>
        <div class="stat-body">
          <div class="stat-title">Landing 页景区背景</div>
          <div class="stat-desc">
            {{ landingImages.length ? `已上传 ${landingImages.length} 张景区实景照片` : "当前使用默认景区图集" }}
          </div>
        </div>
        <span :class="['stat-badge', { 'stat-badge-set': landingImages.length }]">
          {{ landingImages.length ? `${landingImages.length} 张` : "未设置" }}
        </span>
      </article>
    </div>

    <article class="panel-card">
      <div class="section-heading">
        <div>
          <h3>游客端欢迎语</h3>
          <p>首页及导览入口页的欢迎文案，用于建立第一印象。</p>
        </div>
        <el-button v-if="!welcomeTextEditing" size="small" @click="welcomeTextEditing = true">编辑</el-button>
      </div>
      <div v-if="!welcomeTextEditing" class="welcome-display">
        <p>{{ welcomeTextValue || DEFAULT_WELCOME }}</p>
      </div>
      <div v-else class="welcome-edit-area">
        <textarea v-model="welcomeTextValue" rows="3" placeholder="请输入游客端欢迎语" class="welcome-textarea"></textarea>
        <div class="welcome-edit-actions">
          <el-button size="small" type="primary" :loading="welcomeTextSaving" @click="handleSaveWelcomeText">保存</el-button>
          <el-button size="small" :disabled="welcomeTextSaving" @click="handleCancelWelcomeText">取消</el-button>
        </div>
      </div>
    </article>

    <article class="panel-card">
      <div class="section-heading">
        <div>
          <h3>游客端风景背景</h3>
          <p>替换数字人对话页面中的风景背景图。</p>
        </div>
        <el-tag size="small" type="success" effect="plain">已接入</el-tag>
      </div>

      <div class="card-body">
        <div class="field-hint">支持 JPG / PNG / WEBP，建议横向景区实景图</div>

        <div class="asset-preview" @click="openBackgroundPicker">
          <img
            v-if="backgroundPreviewUrl"
            :src="backgroundPreviewUrl"
            alt="游客端背景预览"
          />
          <div v-else class="asset-placeholder">
            <el-icon :size="30"><UploadFilled /></el-icon>
            <strong>点击上传游客端背景图</strong>
            <span>支持 JPG / PNG / WEBP，建议横向实景照片</span>
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
          <el-button @click="openBackgroundPicker" size="small">选择图片</el-button>
          <el-button
            type="primary"
            size="small"
            :loading="backgroundUploading"
            :disabled="!selectedBackgroundFile"
            @click="handleUploadBackground"
          >
            应用背景
          </el-button>
          <el-button
            size="small"
            :disabled="!backgroundAsset.asset_url || backgroundUploading"
            @click="handleClearBackground"
          >
            清除
          </el-button>
        </div>
      </div>
    </article>

    <article class="panel-card">
      <div class="section-heading">
        <div>
          <h3>Landing 页景区背景图</h3>
          <p>上传景区实景照片，自动替换 Landing 页右侧大图区轮播背景。</p>
        </div>
        <el-tag size="small" :type="landingImages.length ? 'success' : 'info'" effect="plain">
          {{ landingImages.length ? `${landingImages.length} 张` : "0 张" }}
        </el-tag>
      </div>

      <div class="card-body">
        <div
          class="landing-upload-zone"
          @click="openLandingPicker"
        >
          <el-icon :size="32"><UploadFilled /></el-icon>
          <strong>点击上传景区背景图</strong>
          <span>支持 JPG / PNG / WEBP，建议横向实景照片，可批量选择</span>
        </div>

        <input
          ref="landingInputRef"
          class="hidden-input"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          multiple
          @change="handleLandingFileSelect"
        />

        <div v-if="landingImages.length" class="landing-gallery">
          <div
            v-for="(img, idx) in landingImages"
            :key="img.id"
            class="landing-gallery-item"
          >
            <img :src="img.src" :alt="img.name" />
            <div class="landing-item-overlay">
              <span class="landing-item-name">{{ img.name }}</span>
              <button
                type="button"
                class="landing-item-remove"
                @click.stop="removeLandingImage(idx)"
                title="删除"
              >&times;</button>
            </div>
          </div>
        </div>

        <div class="asset-actions">
          <el-button @click="openLandingPicker" size="small">选择图片</el-button>
          <el-button
            type="primary"
            size="small"
            :disabled="!landingImages.length"
            @click="handleApplyLanding"
          >
            应用轮播背景
          </el-button>
          <el-button
            size="small"
            :disabled="!landingImages.length"
            @click="handleClearLanding"
          >
            清空全部
          </el-button>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Collection, PictureFilled, UploadFilled } from "@element-plus/icons-vue";

import {
  clearTouristBackground,
  fetchDisplayAssets,
  uploadTouristBackground,
  updateWelcomeText,
} from "../../api/admin";
import { API_BASE_URL } from "../../api/http";
import { invalidateScenicBackground } from "../../composables/useScenicBackground";

const LANDING_STORAGE_KEY = "a5-landing-images-v1";

const initialized = ref(false);
const pageLoading = ref(false);
const lastUpdatedAt = ref("");
const backgroundInputRef = ref(null);
const landingInputRef = ref(null);
const selectedBackgroundFile = ref(null);
const selectedBackgroundPreviewUrl = ref("");
const backgroundUploading = ref(false);
const backgroundAsset = ref({
  asset_url: "",
  file_name: "",
  updated_at: "",
});

const DEFAULT_WELCOME = "欢迎来到灵山胜境，愿您在此感受禅佛意韵，尽享山水景致。";
const welcomeTextValue = ref(DEFAULT_WELCOME);
const welcomeTextEditing = ref(false);
const welcomeTextSaving = ref(false);

const landingImages = ref([]);

const backgroundPreviewUrl = computed(() =>
  selectedBackgroundPreviewUrl.value || resolveAssetUrl(backgroundAsset.value.asset_url),
);

function resolveAssetUrl(assetUrl) {
  if (!assetUrl) return "";
  if (/^https?:\/\//i.test(assetUrl)) return assetUrl;
  return new URL(assetUrl, `${API_BASE_URL}/`).href;
}

function formatNow() {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
  }).format(new Date());
}

function formatUpdatedAt(value) {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
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

function openBackgroundPicker() { backgroundInputRef.value?.click(); }

function handleBackgroundFileChange(event) {
  const file = event.target?.files?.[0] || null;
  selectedBackgroundFile.value = file;
  revokeBackgroundPreview();
  if (file) selectedBackgroundPreviewUrl.value = URL.createObjectURL(file);
}

function loadLandingImages() {
  try { const raw = localStorage.getItem(LANDING_STORAGE_KEY); if (raw) landingImages.value = JSON.parse(raw); }
  catch { landingImages.value = []; }
}

function saveLandingImages() {
  try {
    const payload = JSON.stringify(landingImages.value);
    localStorage.setItem(LANDING_STORAGE_KEY, payload);
    return true;
  } catch (e) {
    const sizeMB = (new Blob([JSON.stringify(landingImages.value)]).size / 1024 / 1024).toFixed(1);
    ElMessage.error(`图片存储失败（约 ${sizeMB}MB），超出浏览器 localStorage 容量限制。请减少图片数量或使用更小的文件。`);
    return false;
  }
}

function openLandingPicker() { landingInputRef.value?.click(); }

function handleLandingFileSelect(event) {
  const files = event.target?.files;
  if (!files || !files.length) return;
  let loaded = 0;
  const total = files.length;
  for (const file of files) {
    const reader = new FileReader();
    reader.onload = (e) => {
      landingImages.value.push({
        id: Date.now() + Math.random().toString(36).slice(2),
        name: file.name,
        src: e.target.result,
      });
      loaded++;
      if (loaded === total) {
        const saved = saveLandingImages();
        lastUpdatedAt.value = formatNow();
        if (saved) {
          ElMessage.success(`已添加 ${total} 张背景图`);
        }
      }
    };
    reader.onerror = () => {
      loaded++;
      ElMessage.error(`"${file.name}" 读取失败`);
    };
    reader.readAsDataURL(file);
  }
  if (landingInputRef.value) landingInputRef.value.value = "";
}

function removeLandingImage(idx) {
  landingImages.value.splice(idx, 1);
  const saved = saveLandingImages();
  if (saved) {
    lastUpdatedAt.value = formatNow();
    ElMessage.success("已移除背景图");
  }
}

function handleApplyLanding() {
  const saved = saveLandingImages();
  lastUpdatedAt.value = formatNow();
  if (saved) ElMessage.success("Landing 页轮播背景已应用，刷新 Landing 页面即可查看");
}

function handleClearLanding() {
  ElMessageBox.confirm("确定清空所有 Landing 页背景图吗？", "提示", { type: "warning" })
    .then(() => { landingImages.value = []; saveLandingImages(); lastUpdatedAt.value = formatNow(); ElMessage.success("已清空全部背景图"); })
    .catch(() => {});
}

async function loadDisplayAssetState() {
  const assets = await fetchDisplayAssets();
  backgroundAsset.value = {
    asset_url: assets?.tourist_background?.asset_url || "",
    file_name: assets?.tourist_background?.file_name || "",
    updated_at: assets?.tourist_background?.updated_at || "",
  };
  welcomeTextValue.value = assets?.welcome_text || DEFAULT_WELCOME;
}

async function loadPageData() {
  pageLoading.value = true;
  try {
    await loadDisplayAssetState();
    loadLandingImages();
    initialized.value = true;
    lastUpdatedAt.value = formatNow();
  } catch (error) {
    ElMessage.error(`配置读取失败：${error?.response?.data?.detail || error.message || "请检查后端服务"}`);
  } finally {
    pageLoading.value = false;
  }
}

async function handleUploadBackground() {
  if (!selectedBackgroundFile.value) return;
  backgroundUploading.value = true;
  try {
    const response = await uploadTouristBackground(selectedBackgroundFile.value);
    backgroundAsset.value = {
      asset_url: response.asset?.asset_url || "",
      file_name: response.asset?.file_name || "",
      updated_at: response.asset?.updated_at || "",
    };
    if (backgroundInputRef.value) backgroundInputRef.value.value = "";
    selectedBackgroundFile.value = null;
    revokeBackgroundPreview();
    lastUpdatedAt.value = formatNow();
    invalidateScenicBackground();
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
    if (backgroundInputRef.value) backgroundInputRef.value.value = "";
    selectedBackgroundFile.value = null;
    revokeBackgroundPreview();
    lastUpdatedAt.value = formatNow();
    invalidateScenicBackground();
    ElMessage.success("自定义背景已清除");
  } catch (error) {
    if (error !== "cancel") ElMessage.error(`清除失败：${error?.response?.data?.detail || error.message}`);
  } finally {
    backgroundUploading.value = false;
  }
}

async function handleSaveWelcomeText() {
  if (welcomeTextSaving.value) return;
  welcomeTextSaving.value = true;
  try {
    const response = await updateWelcomeText(welcomeTextValue.value);
    welcomeTextValue.value = response.welcome_text;
    welcomeTextEditing.value = false;
    lastUpdatedAt.value = formatNow();
    invalidateScenicBackground();
    ElMessage.success("欢迎语已更新");
  } catch (error) {
    ElMessage.error(`欢迎语保存失败：${error?.response?.data?.detail || error.message}`);
    await loadDisplayAssetState();
  } finally {
    welcomeTextSaving.value = false;
  }
}

function handleCancelWelcomeText() {
  welcomeTextEditing.value = false;
  loadDisplayAssetState();
}

onMounted(() => { loadPageData(); });
onBeforeUnmount(() => { revokeBackgroundPreview(); });
</script>

<style scoped>
.display-assets-layout {
  display: grid;
  gap: 12px;
}

.assets-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 20px 24px;
  background: linear-gradient(155deg, #241d16 0%, #2e2620 50%, #3a3028 100%);
  border: 1px solid #342d26;
  color: #fff7eb;
}

.assets-hero h2 {
  margin: 0 0 6px;
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.assets-hero p {
  max-width: 640px;
  margin: 0;
  color: rgba(255, 247, 235, 0.56);
  font-size: 12px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.hero-updated {
  color: rgba(255, 247, 235, 0.45);
  font-size: 11px;
}

.hero-refresh-btn {
  --el-button-bg-color: rgba(255, 255, 255, 0.08);
  --el-button-border-color: rgba(255, 255, 255, 0.14);
  --el-button-text-color: rgba(255, 247, 235, 0.8);
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #d4c8b8;
  background: #fffaf2;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
}

.stat-icon-blue {
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
}

.stat-icon-gold {
  background: rgba(184, 137, 79, 0.1);
  color: #8a5d22;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-title {
  font-size: 12px;
  color: #675a4e;
}

.stat-desc {
  font-size: 11px;
  color: #241d16;
  margin-top: 2px;
}

.stat-badge {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  min-height: 22px;
  padding: 0 10px;
  font-size: 11px;
  color: #675a4e;
  background: rgba(103, 90, 78, 0.08);
}

.stat-badge-set {
  color: #1c6c42;
  background: rgba(36, 133, 80, 0.1);
}

.panel-card {
  border: 1px solid #d4c8b8;
  background: #fffaf2;
  overflow: hidden;
}

.section-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px 0;
}

.section-heading h3 {
  margin: 0 0 4px;
  color: #241d16;
  font-size: 17px;
  font-weight: 600;
}

.section-heading p {
  margin: 0;
  color: #675a4e;
  font-size: 12px;
  line-height: 1.5;
}

.card-body {
  padding: 14px 18px 18px;
}

.field-hint {
  color: #675a4e;
  font-size: 11px;
  margin-bottom: 10px;
}

.asset-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 140px;
  border: 2px dashed #d4c8b8;
  overflow: hidden;
  background: #f0e9dc;
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.asset-preview:hover {
  border-color: #248550;
}

.asset-preview img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  display: block;
}

.asset-placeholder {
  display: grid;
  gap: 6px;
  text-align: center;
  color: #675a4e;
}

.asset-placeholder .el-icon {
  margin: 0 auto;
  color: #675a4e;
  opacity: 0.45;
}

.asset-file-meta {
  display: grid;
  gap: 4px;
  margin-top: 10px;
}

.asset-file-meta strong {
  color: #241d16;
  font-size: 13px;
}

.asset-file-meta span {
  color: #675a4e;
  font-size: 11px;
}

.asset-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.hidden-input {
  display: none;
}

.welcome-display {
  padding: 12px 18px 18px;
}

.welcome-display p {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid #e3d9cc;
  background: #f0e9dc;
  color: #241d16;
  font-size: 13px;
  line-height: 1.65;
}

.welcome-edit-area {
  padding: 0 18px 18px;
}

.welcome-textarea {
  width: 100%;
  min-height: 80px;
  padding: 10px 12px;
  border: 1px solid #d4c8b8;
  background: #fffaf2;
  color: #241d16;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
  outline: none;
  resize: vertical;
  box-sizing: border-box;
}

.welcome-textarea:focus {
  border-color: #248550;
  box-shadow: 0 0 0 3px rgba(36, 133, 80, 0.1);
}

.welcome-edit-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.landing-upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 120px;
  border: 2px dashed #d4c8b8;
  background: #f0e9dc;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
  padding: 20px;
}

.landing-upload-zone:hover {
  border-color: #248550;
  background: rgba(36, 133, 80, 0.03);
}

.landing-upload-zone .el-icon {
  color: #675a4e;
  opacity: 0.45;
}

.landing-upload-zone strong {
  font-size: 12px;
  color: #675a4e;
}

.landing-upload-zone span {
  font-size: 11px;
  color: #948c80;
}

.landing-gallery {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}

.landing-gallery-item {
  position: relative;
  border: 1px solid #e3d9cc;
  overflow: hidden;
  background: #faf7f0;
  height: 80px;
}

.landing-gallery-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.landing-item-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 3px 6px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.5));
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.landing-item-name {
  font-size: 9px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 68%;
}

.landing-item-remove {
  width: 16px;
  height: 16px;
  border: none;
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 1;
}

.landing-item-remove:hover {
  background: rgba(239, 68, 68, 0.65);
}

@media (max-width: 1280px) {
  .stat-row {
    grid-template-columns: 1fr;
  }
  .landing-gallery {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .assets-hero,
  .hero-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .landing-gallery {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
