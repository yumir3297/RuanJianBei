<template>
  <section class="avatar-admin-layout">
    <header class="panel-card avatar-hero">
      <div>
        <h2>数字人配置</h2>
        <p>设置游客端使用的形象和音色。语速、音量仅保存在当前浏览器。</p>
      </div>
      <div class="hero-actions">
        <el-tag v-if="hasUnsavedChanges" type="warning" effect="plain">有未保存更改</el-tag>
        <span v-if="lastUpdatedAt" class="hero-updated">更新于 {{ lastUpdatedAt }}</span>
        <el-button :loading="pageLoading" @click="loadPageData">刷新配置</el-button>
      </div>
    </header>

    <el-alert
      v-if="pageLoadError"
      type="warning"
      :title="pageLoadError"
      :closable="false"
      show-icon
    >
      <template #default><el-button link type="primary" @click="loadPageData">重新加载</el-button></template>
    </el-alert>

    <article class="panel-card avatar-workbench">
      <div class="section-heading">
        <div>
          <h3>数字人工作台</h3>
            <p>选择要启用的形象与音色。表情、动作和口型只用于本页预览。</p>
        </div>
      </div>

      <div class="workbench-grid">
        <div class="workbench-preview">
          <div class="sub-block preview-block">
            <div class="block-head">
              <strong>实时预览</strong>
              <small>外观切换和表情动作在此预览</small>
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
                  :action="previewAction"
                  :action-key="previewActionKey"
                  @loaded="handlePreviewLoaded"
                  @error="handlePreviewError"
                />
              </div>
              <div class="preview-controls">
                <div class="preview-control-row">
                  <span>表情</span>
                  <el-button-group>
                    <el-button @click="setPreviewExpression('happy')" :type="previewEmotion === 'happy' ? 'primary' : 'default'">亲切微笑</el-button>
                    <el-button @click="setPreviewExpression('relaxed')" :type="previewEmotion === 'relaxed' ? 'primary' : 'default'">专注聆听</el-button>
                    <el-button @click="setPreviewExpression('apology')" :type="previewEmotion === 'apology' ? 'primary' : 'default'">安抚歉意</el-button>
                  </el-button-group>
                </div>
                <div class="preview-control-row">
                  <span>动作</span>
                  <el-button-group>
                    <el-button @click="playPreviewAction('two_hand_wave')">双手欢迎</el-button>
                    <el-button @click="playPreviewAction('guide_narrate')">导览讲解</el-button>
                    <el-button @click="playPreviewAction('applaud')">热烈鼓掌</el-button>
                    <el-button @click="playPreviewAction('vrma_standard_greet')">VRMA 问候</el-button>
                  </el-button-group>
                </div>
                <el-button @click="previewSpeaking = !previewSpeaking" :type="previewSpeaking ? 'warning' : 'default'">
                  {{ previewSpeaking ? "停止口型预览" : "预览讲解口型" }}
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <div class="workbench-settings">
          <div class="sub-block">
            <div class="block-head">
              <strong>外观形象</strong>
              <small>选择游客端使用的人物</small>
            </div>
            <div class="model-grid">
              <button
                v-for="model in modelList"
                :key="model.key"
                type="button"
                :class="['model-card', { active: selectedPreset === model.key }]"
                :aria-pressed="selectedPreset === model.key"
                :disabled="initialized && !presetToConfigId[model.key]"
                @click="selectModel(model.key)"
              >
                <div class="model-preview">
                  <div class="model-placeholder" :class="`preview-${model.cssClass || model.key}`">
                    <span class="model-initial">{{ model.label[0] }}</span>
                  </div>
                  <div v-if="selectedPreset === model.key" class="model-check">✓</div>
                </div>
                <div class="model-info"><strong>{{ model.label }}</strong></div>
              </button>
            </div>
          </div>

          <div class="sub-block">
            <div class="block-head">
              <strong>语音音色</strong>
              <small>保存后用于游客端回答语音</small>
            </div>
            <el-form label-width="72px" class="voice-form">
              <el-form-item label="音色">
                <el-select v-model="voiceType" placeholder="选择音色">
                  <el-option label="温柔女声 · 龙婉" value="gentle-female" />
                  <el-option label="知性女声 · 龙小夏" value="calm-female" />
                  <el-option label="沉稳男声 · 龙三叔" value="deep-male" />
                  <el-option label="活泼女声 · 龙安亲" value="lively-female" />
                </el-select>
                <el-button class="voice-preview-btn" :loading="voicePreviewLoading" @click="handleVoicePreview">试听音色</el-button>
                <div class="voice-provider-note">
                  服务商音色：<code>{{ selectedVoiceOption.providerVoice }}</code>
                  <span>{{ selectedVoiceOption.description }}</span>
                </div>
              </el-form-item>
              <el-divider content-position="left">仅保存在当前浏览器</el-divider>
              <el-form-item label="语速">
                <el-slider v-model="speechRate" :min="80" :max="150" :step="5" show-input />
              </el-form-item>
              <el-form-item label="音量">
                <el-slider v-model="volume" :min="50" :max="100" :step="5" show-input />
              </el-form-item>
            </el-form>
          </div>

          <div class="workbench-actions">
            <el-button type="primary" size="large" :loading="saving" :disabled="!initialized || !presetToConfigId[selectedPreset]" @click="handleSave">保存数字人配置</el-button>
            <el-button size="large" :disabled="saving" @click="handleReset">恢复默认</el-button>
          </div>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { onBeforeRouteLeave } from "vue-router";

import ThreeAvatar from "../../components/ThreeAvatar.vue";
import {
  fetchAvatarConfigs,
  previewAvatarVoice,
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
  { key: "monk", label: "宁灵", description: "庄重安定 · 国风文化讲解", cssClass: "monk" },
  { key: "hanfu", label: "清岚", description: "雅致温润 · 文化叙事导览", cssClass: "hanfu" },
  { key: "modern", label: "景行", description: "亲切利落 · 现代智能导览", cssClass: "modern" },
];

const voiceOptions = [
  { value: "gentle-female", label: "温柔女声 · 龙婉", providerVoice: "longwan_v3", description: "温暖亲切，适合欢迎与陪伴导览" },
  { value: "calm-female", label: "知性女声 · 龙小夏", providerVoice: "longxiaoxia_v3", description: "清晰沉静，适合文化知识讲解" },
  { value: "deep-male", label: "沉稳男声 · 龙三叔", providerVoice: "longsanshu_v3", description: "稳重厚实，适合历史文化讲解" },
  { value: "lively-female", label: "活泼女声 · 龙安琴", providerVoice: "longanqin_v3", description: "明快活泼，适合亲子互动场景" },
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
const pageLoadError = ref("");
const saving = ref(false);
const lastUpdatedAt = ref("");
const presetToConfigId = ref({});
const previewEmotion = ref("neutral");
const previewSpeaking = ref(false);
const previewReactionToken = ref(0);
const previewAction = ref("");
const previewActionKey = ref(0);
const previewError = ref(false);
const voicePreviewLoading = ref(false);
let previewAudio = null;

const selectedPreset = ref(DEFAULT_AVATAR_PRESET);
const voiceType = ref(DEFAULT_AVATAR_VOICE);
const speechRate = ref(localPrefs.speechRate);
const volume = ref(localPrefs.volume);
const savedSettings = ref(null);
const hasUnsavedChanges = computed(() =>
  Boolean(savedSettings.value) && JSON.stringify({
    preset: selectedPreset.value,
    voice: voiceType.value,
    speechRate: speechRate.value,
    volume: volume.value,
  }) !== JSON.stringify(savedSettings.value),
);

const selectedVoiceOption = computed(() =>
  voiceOptions.find((item) => item.value === voiceType.value) || voiceOptions[0],
);

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

function setPreviewExpression(emotion) {
  previewEmotion.value = emotion;
  previewSpeaking.value = false;
  previewReactionToken.value += 1;
}

function playPreviewAction(action) {
  previewAction.value = action;
  previewActionKey.value += 1;
}

async function handleVoicePreview() {
  if (voicePreviewLoading.value) return;
  voicePreviewLoading.value = true;
  previewAudio?.pause();
  previewAudio = null;
  try {
    const result = await previewAvatarVoice(
      voiceType.value,
      "您好，欢迎来到本景区，我将为您提供智慧导览服务。",
    );
    previewAudio = new Audio(`data:${result.audio_mime_type || "audio/mpeg"};base64,${result.base64_audio}`);
    await previewAudio.play();
    ElMessage.success(`正在播放真实音色：${result.provider_voice}`);
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.message || "音色试听失败，请检查 TTS 服务配置");
  } finally {
    voicePreviewLoading.value = false;
  }
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
  if (hasUnsavedChanges.value) {
    try {
      await ElMessageBox.confirm("重新读取会覆盖当前未保存的设置。", "重新加载配置？", {
        type: "warning",
        confirmButtonText: "重新加载",
        cancelButtonText: "继续编辑",
      });
    } catch {
      return;
    }
  }
  pageLoading.value = true;
  pageLoadError.value = "";
  try {
    await loadAvatarConfigs();
    initialized.value = true;
    savedSettings.value = {
      preset: selectedPreset.value,
      voice: voiceType.value,
      speechRate: speechRate.value,
      volume: volume.value,
    };
    lastUpdatedAt.value = formatNow();
  } catch (error) {
    pageLoadError.value = `配置读取失败：${error?.response?.data?.detail || error.message || "请检查后端服务"}`;
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
  savedSettings.value = {
    preset: selectedPreset.value,
    voice: voiceType.value,
    speechRate: speechRate.value,
    volume: volume.value,
  };
  lastUpdatedAt.value = formatNow();
  ElMessage.success("数字人配置已保存并同步到游客端");
}

function handleReset() {
  selectedPreset.value = DEFAULT_AVATAR_PRESET;
  voiceType.value = DEFAULT_AVATAR_VOICE;
  speechRate.value = 100;
  volume.value = 80;
  ElMessage.info("已恢复表单默认值，保存后应用");
}

onBeforeRouteLeave(async () => {
  if (!hasUnsavedChanges.value) return true;
  try {
    await ElMessageBox.confirm("离开后将丢弃当前未保存的数字人设置。", "离开配置页？", {
      type: "warning",
      confirmButtonText: "离开页面",
      cancelButtonText: "继续编辑",
    });
    return true;
  } catch {
    return false;
  }
});

onMounted(() => {
  loadPageData();
});

onBeforeUnmount(() => {
  previewAudio?.pause();
  previewAudio = null;
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
  grid-template-columns: minmax(360px, 0.9fr) minmax(440px, 1.1fr);
  gap: 18px;
  margin-top: 18px;
}

.workbench-preview,
.workbench-settings {
  display: grid;
  align-content: start;
  gap: 16px;
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

.voice-form :deep(.el-form-item:first-child .el-form-item__content) {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.voice-provider-note {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.5;
}

.voice-provider-note code {
  color: #0f766e;
  font-weight: 700;
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
  height: 440px;
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

.preview-control-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.preview-control-row > span {
  width: 38px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.workbench-actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 1280px) {
  .workbench-grid {
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

  .preview-canvas-wrapper { height: 360px; }
}
</style>
