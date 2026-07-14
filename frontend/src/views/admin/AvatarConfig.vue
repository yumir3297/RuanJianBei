<template>
  <section class="avatar-admin-layout">
    <header class="panel-card avatar-hero">
      <div>
        <h2>数字人配置</h2>
        <p>统一维护游客端导览形象与语音表现，让数字人页面既能讲得清楚，也能展示得更有景区气质。</p>
      </div>
      <div class="hero-actions">
        <span v-if="lastUpdatedAt" class="hero-updated">更新于 {{ lastUpdatedAt }}</span>
        <el-button :loading="pageLoading" @click="loadPageData">刷新配置</el-button>
      </div>
    </header>

    <div class="stat-grid" v-loading="pageLoading && !initialized">
      <article
        v-for="card in summaryCards"
        :key="card.key"
        class="stat-card"
        :style="{ '--accent': card.accent, '--accent-soft': card.soft }"
      >
        <span class="stat-kicker">{{ card.kicker }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
        <span class="stat-label">{{ card.label }}</span>
        <p class="stat-note">{{ card.note }}</p>
      </article>
    </div>

    <article class="panel-card avatar-workbench">
      <div class="section-heading">
        <div>
          <h3>数字人工作台</h3>
          <p>调整游客端当前使用的形象、语音音色和演示状态，保存后可直接应用到导览页。</p>
        </div>
      </div>

      <div class="workbench-grid">
        <div class="workbench-left">
          <div class="sub-block">
            <div class="block-head">
              <strong>外观形象</strong>
              <small>三套数字人导览气质可切换</small>
            </div>
            <div class="model-grid">
              <button
                v-for="model in modelList"
                :key="model.key"
                type="button"
                :class="['model-card', { active: selectedPreset === model.key }]"
                @click="selectModel(model.key)"
              >
                <div class="model-preview">
                  <div class="model-placeholder" :class="`preview-${model.cssClass || model.key}`">
                    <span class="model-initial">{{ model.label[0] }}</span>
                  </div>
                  <div v-if="selectedPreset === model.key" class="model-check">✓</div>
                </div>
                <div class="model-info">
                  <strong>{{ model.label }}</strong>
                  <small>{{ model.description }}</small>
                </div>
              </button>
            </div>
          </div>

          <div class="sub-block">
            <div class="block-head">
              <strong>语音音色</strong>
              <small>保存后应用到游客端回答语音</small>
            </div>

            <el-form label-width="84px" class="voice-form">
              <el-form-item label="音色">
                <el-select v-model="voiceType" placeholder="选择音色">
                  <el-option label="温柔女声 · 龙婉" value="gentle-female" />
                  <el-option label="知性女声 · 龙小夏" value="calm-female" />
                  <el-option label="沉稳男声 · 龙三叔" value="deep-male" />
                  <el-option label="活泼女声 · 龙安亲" value="lively-female" />
                </el-select>
              </el-form-item>
              <el-divider content-position="left">
                <span style="font-size:12px;color:#6c757d">以下为本机演示偏好，不影响游客端</span>
              </el-divider>
              <el-form-item label="语速">
                <el-slider v-model="speechRate" :min="80" :max="150" :step="5" show-input />
              </el-form-item>
              <el-form-item label="音量">
                <el-slider v-model="volume" :min="50" :max="100" :step="5" show-input />
              </el-form-item>
            </el-form>
          </div>
        </div>

        <div class="workbench-right">
          <div class="sub-block preview-block">
            <div class="block-head">
              <strong>实时预览</strong>
              <small>用于答辩前快速确认人物状态</small>
            </div>
            <div class="preview-area">
              <div class="preview-canvas-wrapper">
                <div v-if="previewError" class="preview-error-overlay">
                  <span>模型加载失败</span>
                </div>
                <ThreeAvatar
                  v-if="!previewError"
                  :preset="selectedPreset"
                  :emotion="previewEmotion"
                  :is-speaking="previewSpeaking"
                  :reaction-token="previewReactionToken"
                  gesture="wave"
                  :gesture-token="previewGestureToken"
                  @loaded="handlePreviewLoaded"
                  @error="handlePreviewError"
                />
              </div>
              <div class="preview-controls">
                <el-button-group>
                  <el-button
                    @click="previewEmotion = 'neutral'; previewSpeaking = false"
                    :type="previewEmotion === 'neutral' && !previewSpeaking ? 'primary' : 'default'"
                  >
                    空闲
                  </el-button>
                  <el-button
                    @click="previewEmotion = 'happy'; previewSpeaking = true; previewReactionToken += 1"
                    :type="previewEmotion === 'happy' ? 'primary' : 'default'"
                  >
                    微笑
                  </el-button>
                  <el-button
                    @click="previewEmotion = 'apology'; previewSpeaking = false; previewReactionToken += 1"
                    :type="previewEmotion === 'apology' ? 'primary' : 'default'"
                  >
                    致歉
                  </el-button>
                </el-button-group>
                <el-button @click="previewSpeaking = !previewSpeaking" :type="previewSpeaking ? 'warning' : 'default'">
                  {{ previewSpeaking ? "停止说话" : "模拟说话" }}
                </el-button>
                <el-button @click="previewGestureToken += 1">Welcome wave</el-button>
              </div>
            </div>
          </div>

          <div class="workbench-actions">
            <el-button type="primary" size="large" :loading="saving" @click="handleSave">保存数字人配置</el-button>
            <el-button size="large" :disabled="saving" @click="handleReset">恢复默认</el-button>
          </div>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import ThreeAvatar from "../../components/ThreeAvatar.vue";
import {
  fetchAvatarConfigs,
  saveAvatarConfig,
  updateAvatarConfig,
} from "../../api/admin";
import {
  DEFAULT_AVATAR_PRESET,
  DEFAULT_AVATAR_VOICE,
  normalizeAvatarPreset,
  normalizeAvatarPresetFromModelPath,
  normalizeAvatarVoiceType,
} from "../../utils/avatarConfig";

const STORAGE_KEY = "a5-avatar-config-v1";

const modelList = [
  { key: "monk", label: "明彻法师", description: "庄重安定 · 佛教文化讲解", cssClass: "monk" },
  { key: "hanfu", label: "清岚", description: "雅致温润 · 文化叙事导览", cssClass: "hanfu" },
  { key: "modern", label: "景行", description: "亲切利落 · 现代智能导览", cssClass: "modern" },
];

function loadLocalPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        speechRate: typeof parsed.speechRate === "number" ? parsed.speechRate : 100,
        volume: typeof parsed.volume === "number" ? parsed.volume : 80,
      };
    }
  } catch {
    // ignore invalid local cache
  }
  return { speechRate: 100, volume: 80 };
}

const localPrefs = loadLocalPrefs();
const initialized = ref(false);
const pageLoading = ref(false);
const saving = ref(false);
const lastUpdatedAt = ref("");
const presetToConfigId = ref({});
const previewEmotion = ref("neutral");
const previewSpeaking = ref(false);
const previewReactionToken = ref(0);
const previewGestureToken = ref(0);
const previewError = ref(false);

const selectedPreset = ref(DEFAULT_AVATAR_PRESET);
const voiceType = ref(DEFAULT_AVATAR_VOICE);
const speechRate = ref(localPrefs.speechRate);
const volume = ref(localPrefs.volume);

const currentAvatarLabel = computed(() => {
  return modelList.find((item) => item.key === selectedPreset.value)?.label || "未选择";
});

const voiceLabel = computed(() => {
  return {
    "gentle-female": "温柔女声",
    "calm-female": "知性女声",
    "deep-male": "沉稳男声",
    "lively-female": "活泼女声",
  }[voiceType.value] || "默认音色";
});

const summaryCards = computed(() => [
  {
    key: "avatar",
    kicker: "",
    value: currentAvatarLabel.value,
    label: "当前数字人形象",
    note: "决定游客端的第一人物印象与讲解气质。",
    accent: "#0f766e",
    soft: "#dcf7f1",
  },
  {
    key: "voice",
    kicker: "",
    value: voiceLabel.value,
    label: "当前语音音色",
    note: "会直接影响游客端回答播放时的服务感。",
    accent: "#b8894f",
    soft: "#f8ecd8",
  },
]);

function formatNow() {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function selectModel(key) {
  selectedPreset.value = key;
  previewError.value = false;
}

function handlePreviewError(err) {
  previewError.value = true;
  ElMessage.error(`数字人模型加载失败：${err?.message || "网络异常"}`);
}

function handlePreviewLoaded() {
  previewError.value = false;
}

async function loadAvatarConfigs() {
  const configs = await fetchAvatarConfigs();
  presetToConfigId.value = {};
  configs.forEach((cfg) => {
    const preset = normalizeAvatarPresetFromModelPath(cfg.model_path);
    presetToConfigId.value[preset] = cfg.id;
    if (cfg.is_active) {
      selectedPreset.value = preset;
      voiceType.value = normalizeAvatarVoiceType(cfg.voice_type, DEFAULT_AVATAR_VOICE);
    }
  });
}

async function loadPageData() {
  pageLoading.value = true;
  try {
    await loadAvatarConfigs();
    initialized.value = true;
    lastUpdatedAt.value = formatNow();
  } catch (error) {
    ElMessage.error(`配置读取失败：${error?.response?.data?.detail || error.message || "请检查后端服务"}`);
  } finally {
    pageLoading.value = false;
  }
}

async function handleSave() {
  if (saving.value) return;
  saving.value = true;

  const targetConfigId = presetToConfigId.value[selectedPreset.value];
  if (!targetConfigId) {
    saving.value = false;
    ElMessage.warning("当前选中的形象在后端无对应配置记录");
    return;
  }

  try {
    await saveAvatarConfig(targetConfigId);
  } catch (error) {
    saving.value = false;
    ElMessage.error(`形象激活失败：${error?.response?.data?.detail || error.message || "请检查后端服务"}`);
    return;
  }

  try {
    const updated = await updateAvatarConfig(targetConfigId, voiceType.value);
    voiceType.value = normalizeAvatarVoiceType(updated.voice_type, DEFAULT_AVATAR_VOICE);
  } catch (error) {
    saving.value = false;
    ElMessage.warning(`形象已激活，但音色保存失败：${error?.response?.data?.detail || error.message}`);
    return;
  }

  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    speechRate: speechRate.value,
    volume: volume.value,
  }));

  saving.value = false;
  lastUpdatedAt.value = formatNow();
  ElMessage.success("数字人配置已保存并同步到游客端");
}

function handleReset() {
  selectedPreset.value = DEFAULT_AVATAR_PRESET;
  voiceType.value = DEFAULT_AVATAR_VOICE;
  speechRate.value = 100;
  volume.value = 80;
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ speechRate: 100, volume: 80 }));
  ElMessage.info("已恢复默认配置");
}

onMounted(() => {
  loadPageData();
});
</script>

<style scoped>
.avatar-admin-layout {
  display: grid;
  gap: 12px;
}

.avatar-hero {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  overflow: hidden;
  padding: 20px 24px;
  background: linear-gradient(155deg, #241d16 0%, #2e2620 50%, #3a3028 100%);
  border: 1px solid #342d26;
  color: #fff7eb;
}

.avatar-hero > * {
  position: relative;
  z-index: 1;
}

.avatar-hero h2 {
  margin: 8px 0 6px;
  font-size: clamp(22px, 3vw, 30px);
  font-weight: 600;
}

.avatar-hero p {
  max-width: 760px;
  margin: 0;
  color: rgba(255, 247, 235, 0.56);
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.stat-card {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: #fffaf2;
  box-shadow: none;
}

.stat-value {
  color: #0f172a;
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

.avatar-workbench {
  padding: 22px;
}

.section-heading,
.block-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.section-heading h3 {
  margin: 5px 0 4px;
  color: #0f172a;
  font-size: 17px;
}

.section-heading p,
.block-head small {
  margin: 0;
  color: #64748b;
  font-size: 12px;
  line-height: 1.58;
}

.workbench-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.9fr);
  gap: 8px;
  margin-top: 18px;
}

.workbench-left,
.workbench-right {
  display: grid;
  gap: 8px;
}

.sub-block {
  padding: 16px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: #f0e9dc;
}

.block-head strong {
  color: #20352a;
  font-size: 15px;
}

.model-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.model-card {
  display: grid;
  gap: 10px;
  padding: 15px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  background: rgba(255, 255, 255, 0.92);
  cursor: pointer;
  transition: border-color 160ms ease, transform 160ms ease;
}

.model-card:hover {
  transform: translateY(-2px);
  border-color: rgba(15, 118, 110, 0.28);
}

.model-card.active {
  border-color: #0f766e;
  background: #f0fdfa;
}

.model-preview {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto;
}

.model-placeholder {
  width: 100%;
  height: 100%;
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.preview-monk { background: linear-gradient(135deg, #8b4513, #a06a2c); }
.preview-hanfu { background: linear-gradient(135deg, #7daa92, #4f6b63); }
.preview-modern { background: linear-gradient(135deg, #243447, #2f7f79); }

.model-check {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #0f766e;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}

.model-info {
  text-align: center;
}

.model-info strong {
  display: block;
  font-size: 14px;
}

.model-info small {
  display: block;
  margin-top: 4px;
  color: #6c757d;
  font-size: 12px;
  line-height: 1.5;
}

.voice-form {
  margin-top: 14px;
}

.preview-block {
  height: 100%;
}

.preview-area {
  display: grid;
  gap: 14px;
  margin-top: 14px;
}

.preview-canvas-wrapper {
  position: relative;
  width: 100%;
  height: 520px;
  border: 1px solid #d4c8b8;
  border-radius: 0;
  overflow: hidden;
  background: #f8f9fa;
}

.preview-error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  color: #dc2626;
  font-size: 14px;
  font-weight: 600;
  z-index: 2;
}

.preview-controls {
  display: grid;
  gap: 12px;
}

.workbench-actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 1280px) {
  .workbench-grid {
    grid-template-columns: 1fr;
  }

  .stat-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .avatar-hero,
  .hero-actions,
  .workbench-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .model-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
