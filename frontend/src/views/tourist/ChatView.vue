<template>
  <section class="tourist-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <!-- ① 顶栏 -->
    <button type="button" class="back-btn" @click="handleChangeMode">← 返回</button>
    <div class="top-right">
      <span class="top-brand">灵山智能导览系统</span>
    </div>

    <div class="tourist-stage">
      <div class="chat-center">
        <div class="top-caption">
          <span class="crowd-indicator" data-level="green">
            <span class="crowd-dot"></span>当前景区人数：舒适
          </span>
          <span class="caption-kicker">{{ avatarDisplaySubtitle }}</span>
          <span class="caption-weather" v-if="!weatherCaption">灵山 · 智慧导览</span>
          <span class="caption-weather caption-weather-live" v-else>{{ weatherCaption }}</span>
        </div>
        <div class="avatar-stage">
          <ThreeAvatar
            v-if="!avatarError"
            :preset="avatarConfig.modelKey"
            :emotion="avatar.currentEmotion.value"
            :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
            :speech-progress="speechProgress"
            :speech-elapsed-ms="speechElapsedMs"
            :speech-duration-ms="speechDurationMs"
            :speech-sync-active="activeAudioSegments > 0"
            :viseme-timeline="visemeTimeline"
            :avatar-state="avatarState"
            @loaded="handleAvatarLoaded"
            @error="handleAvatarLoadError"
          />
          <AvatarDisplay v-else :state="avatarState" :emotion="avatar.currentEmotion.value" />
        </div>
      </div>

      <!-- ③ 左卡片：对话/来源 Tab -->
      <aside class="side-card" :class="{ speaking: chatStore.streaming }">
        <div class="side-card-head">
          <div class="side-card-tabs">
            <button :class="['side-card-tab', { active: activeTab === 'chat' }]" @click="activeTab = 'chat'">对话</button>
            <button :class="['side-card-tab', { active: activeTab === 'source' }]" @click="activeTab = 'source'">来源</button>
          </div>
        </div>
        <div :class="['side-card-body', { hidden: activeTab !== 'chat' }]" ref="messageListRef">
          <article v-for="(message, index) in chatStore.messages" :key="`${message.role}-${index}`" :class="['msg-item', message.role, { collapsed: message.role === 'user' && index < chatStore.messages.length - 1 && chatStore.messages[index + 1]?.role === 'assistant' }]">
            <div v-if="message.role === 'assistant'" class="msg-bubble" v-html="renderAnswer(message.content, index === chatStore.messages.length - 1)" @click="handleCitationClick"></div>
            <div v-else class="msg-bubble">{{ message.content }}</div>
            <div v-if="message.role === 'assistant' && message.content && !chatStore.streaming" class="answer-feedback" aria-label="回答评价">
              <span>这条讲解有帮助吗？</span>
              <button type="button" :class="{ active: message.feedbackRating === 'positive' }" :disabled="message.feedbackSubmitting" @click="chatStore.submitFeedback(message, 'positive')">👍 有帮助</button>
              <button type="button" :class="{ active: message.feedbackPendingRating === 'negative' || message.feedbackRating === 'negative' }" :disabled="message.feedbackSubmitting" @click="message.feedbackPendingRating = message.feedbackPendingRating === 'negative' ? null : 'negative'">👎 需改进</button>
              <div v-if="message.feedbackPendingRating === 'negative'" class="feedback-reasons">
                <span>请选择原因：</span>
                <button v-for="reason in feedbackReasons" :key="reason.value" type="button" :disabled="message.feedbackSubmitting" @click="chatStore.submitFeedback(message, 'negative', reason.value)">{{ reason.label }}</button>
              </div>
              <span v-if="message.feedbackError" class="feedback-error">{{ message.feedbackError }}</span>
            </div>
            <span v-if="message.role === 'assistant' && chatStore.streaming && index === chatStore.messages.length - 1 && message.content.length > 0" class="typing-cursor">|</span>
          </article>
          <div v-if="chatStore.followups.length" class="followup-panel">
            <button v-for="item in chatStore.followups" :key="item.query" type="button" :disabled="chatStore.streaming" @click="handleFollowup(item.query)">{{ item.label }}</button>
          </div>
          <div v-if="chatStore.userStopped && !chatStore.streaming" class="stop-notice" role="status">已停止输出</div>
          <div v-if="chatStore.errorMessage && !chatStore.streaming" class="error-notice" role="alert">{{ chatStore.errorMessage }}</div>
        </div>
        <div :class="['side-card-body', { hidden: activeTab !== 'source' }]">
          <ul class="source-list" v-if="chatStore.sources.length">
            <li v-for="(item, index) in chatStore.sources" :key="`${item.title}-${index}`" :class="['source-item', { highlight: sourceHighlightIndex === index }]" :data-source-index="index">
              <h4><span class="source-num">{{ index + 1 }}</span>{{ item.title }}</h4>
              <p>{{ item.snippet }}</p>
              <span class="source-meta">{{ item.source }}</span>
            </li>
          </ul>
          <p v-else class="source-empty">提问后这里会显示参考资料</p>
        </div>
      </aside>

      <!-- ④ 右卡片：快捷服务 -->
      <aside class="right-card">
        <div class="right-card-head">
          <span>{{ explanationLevelLabel }}</span>
          <span class="right-card-head-status">
            <span :class="['status-inline-dot', avatarReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">数字人</span>
            <span :class="['status-inline-dot', voiceReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">语音</span>
            <span :class="['status-inline-dot', replyStatusClass.replace('status-pill--','status-inline-dot--')]">回答</span>
          </span>
        </div>
        <div class="right-card-body">
          <div class="service-grid">
            <button class="explore-card explore-card--scenic" @click="handleQuickAction('recommend')">
              <span class="explore-card-icon">🏯</span>
              <span class="explore-card-title">景点推荐</span>
              <span class="explore-card-desc">热门景点导览</span>
            </button>
            <button class="explore-card explore-card--area" @click="handleQuickAction('photo')">
              <span class="explore-card-icon">📸</span>
              <span class="explore-card-title">拍照识景</span>
              <span class="explore-card-desc">实时景区识别</span>
            </button>
            <button class="explore-card explore-card--type" @click="handleQuickAction('route')">
              <span class="explore-card-icon">🗺️</span>
              <span class="explore-card-title">路线推荐</span>
              <span class="explore-card-desc">智能路线规划</span>
            </button>
            <button class="explore-card explore-card--photo" @click="handleQuickAction('style')">
              <span class="explore-card-icon">⚙️</span>
              <span class="explore-card-title">讲解方式</span>
              <span class="explore-card-desc">{{ explanationLevelLabel }}</span>
            </button>
          </div>
          <div class="style-selector" v-if="showStyleSelector">
            <button v-for="s in styleOptions" :key="s.key" :class="{ active: explanationLevel === s.key }" @click="explanationLevel = s.key; showStyleSelector = false">{{ s.label }}</button>
          </div>
        </div>
      </aside>
    </div>

    <!-- ⑤ 底部输入栏 -->
    <div class="input-row">
      <button class="image-btn" @click="toggleVisionPanel">拍照识景</button>
      <input class="input-field" v-model="query" :placeholder="`想去哪里？我帮你规划…`" @keyup.enter="handleSubmit" :disabled="chatStore.streaming" autocomplete="off" name="tourist-query" />
      <button class="voice-btn" :class="{ recording: speechListening || isRecording }" @click="toggleRecording" :disabled="chatStore.streaming || transcribing">{{ speechListening ? '结束语音' : isRecording ? `录音中 ${durationSeconds}s` : '语音提问' }}</button>
    </div>

    <!-- ⑥ 移动端底部 Tab 栏 + 抽屉 -->
    <nav class="mobile-tab-bar">
      <button :class="{ active: mobileTab === 'chat' }" @click="toggleMobileDrawer('chat')">💬 对话</button>
      <button :class="{ active: mobileTab === 'quick' }" @click="toggleMobileDrawer('quick')">⚡ 快捷</button>
    </nav>

    <transition name="drawer-fade">
      <div v-if="showMobileDrawer" class="mobile-drawer-overlay" @click="closeMobileDrawer"></div>
    </transition>
    <transition name="drawer-slide">
      <aside v-if="showMobileDrawer" class="mobile-drawer-panel">
        <div class="mobile-drawer-handle"></div>
        <template v-if="mobileTab === 'chat'">
          <div class="side-card-tabs" style="margin-bottom: 0;">
            <button :class="['side-card-tab', { active: activeTab === 'chat' }]" @click="activeTab = 'chat'">对话</button>
            <button :class="['side-card-tab', { active: activeTab === 'source' }]" @click="activeTab = 'source'">来源</button>
          </div>
          <div :class="['side-card-body', { hidden: activeTab !== 'chat' }]">
            <article v-for="(message, index) in chatStore.messages" :key="`m-${message.role}-${index}`" :class="['msg-item', message.role, { collapsed: message.role === 'user' && index < chatStore.messages.length - 1 && chatStore.messages[index + 1]?.role === 'assistant' }]">
              <div v-if="message.role === 'assistant'" class="msg-bubble" v-html="renderAnswer(message.content, index === chatStore.messages.length - 1)" @click="handleCitationClick"></div>
              <div v-else class="msg-bubble">{{ message.content }}</div>
              <div v-if="message.role === 'assistant' && message.content && !chatStore.streaming" class="answer-feedback">
                <span>这条讲解有帮助吗？</span>
                <button type="button" :class="{ active: message.feedbackRating === 'positive' }" :disabled="message.feedbackSubmitting" @click="chatStore.submitFeedback(message, 'positive')">👍 有帮助</button>
                <button type="button" :class="{ active: message.feedbackPendingRating === 'negative' || message.feedbackRating === 'negative' }" :disabled="message.feedbackSubmitting" @click="message.feedbackPendingRating = message.feedbackPendingRating === 'negative' ? null : 'negative'">👎 需改进</button>
                <div v-if="message.feedbackPendingRating === 'negative'" class="feedback-reasons">
                  <span>请选择原因：</span>
                  <button v-for="reason in feedbackReasons" :key="reason.value" type="button" :disabled="message.feedbackSubmitting" @click="chatStore.submitFeedback(message, 'negative', reason.value)">{{ reason.label }}</button>
                </div>
                <span v-if="message.feedbackError" class="feedback-error">{{ message.feedbackError }}</span>
              </div>
              <span v-if="message.role === 'assistant' && chatStore.streaming && index === chatStore.messages.length - 1 && message.content.length > 0" class="typing-cursor">|</span>
            </article>
            <div v-if="chatStore.followups.length" class="followup-panel">
              <button v-for="item in chatStore.followups" :key="item.query" type="button" :disabled="chatStore.streaming" @click="handleFollowup(item.query)">{{ item.label }}</button>
            </div>
            <div v-if="chatStore.userStopped && !chatStore.streaming" class="stop-notice" role="status">已停止输出</div>
            <div v-if="chatStore.errorMessage && !chatStore.streaming" class="error-notice" role="alert">{{ chatStore.errorMessage }}</div>
          </div>
          <div :class="['side-card-body', { hidden: activeTab !== 'source' }]">
            <ul class="source-list" v-if="chatStore.sources.length">
              <li v-for="(item, index) in chatStore.sources" :key="`${item.title}-${index}`" :class="['source-item', { highlight: sourceHighlightIndex === index }]" :data-source-index="index">
                <h4><span class="source-num">{{ index + 1 }}</span>{{ item.title }}</h4>
                <p>{{ item.snippet }}</p>
                <span class="source-meta">{{ item.source }}</span>
              </li>
            </ul>
            <p v-else class="source-empty">提问后这里会显示参考资料</p>
          </div>
        </template>
        <template v-if="mobileTab === 'quick'">
          <div class="right-card-head">
            <span>{{ explanationLevelLabel }}</span>
            <span class="right-card-head-status">
              <span :class="['status-inline-dot', avatarReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">数字人</span>
              <span :class="['status-inline-dot', voiceReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">语音</span>
              <span :class="['status-inline-dot', replyStatusClass.replace('status-pill--','status-inline-dot--')]">回答</span>
            </span>
          </div>
          <div class="right-card-body">
            <div class="service-grid">
              <button class="explore-card explore-card--scenic" @click="handleQuickAction('recommend'); closeMobileDrawer()">
                <span class="explore-card-icon">🏯</span>
                <span class="explore-card-title">景点推荐</span>
                <span class="explore-card-desc">热门景点导览</span>
              </button>
              <button class="explore-card explore-card--area" @click="handleQuickAction('photo'); closeMobileDrawer()">
                <span class="explore-card-icon">📸</span>
                <span class="explore-card-title">拍照识景</span>
                <span class="explore-card-desc">实时景区识别</span>
              </button>
              <button class="explore-card explore-card--type" @click="handleQuickAction('route'); closeMobileDrawer()">
                <span class="explore-card-icon">🗺️</span>
                <span class="explore-card-title">路线推荐</span>
                <span class="explore-card-desc">智能路线规划</span>
              </button>
              <button class="explore-card explore-card--photo" @click="handleQuickAction('style'); closeMobileDrawer()">
                <span class="explore-card-icon">⚙️</span>
                <span class="explore-card-title">讲解方式</span>
                <span class="explore-card-desc">{{ explanationLevelLabel }}</span>
              </button>
            </div>
            <div class="style-selector" v-if="showStyleSelector">
              <button v-for="s in styleOptions" :key="s.key" :class="{ active: explanationLevel === s.key }" @click="explanationLevel = s.key; showStyleSelector = false">{{ s.label }}</button>
            </div>
          </div>
        </template>
      </aside>
    </transition>

    <div v-if="chatStore.errorMessage && !chatStore.streaming" class="voice-error-bar" role="alert">{{ chatStore.errorMessage }}</div>

    <!-- 语音状态条 -->
    <div v-if="speechListening" class="speech-bar" aria-live="polite">
      <span class="speech-pulse" aria-hidden="true"></span>
      <strong>正在聆听</strong>
      <span>{{ speechPreviewText || '请开始说话…' }}</span>
      <span v-if="transcriptionConfidence >= 0" class="confidence-dot" :class="confidenceLevelClass" :title="`置信度 ${Math.round(transcriptionConfidence * 100)}%`"></span>
    </div>

    <!-- 录音转写确认条 -->
    <div v-if="showConfirmBar" class="confirm-bar">
      <span class="confirm-text">你刚说的是 "<strong>{{ confirmedTranscript }}</strong>" 吗？</span>
      <button class="confirm-btn confirm-btn--yes" @click="confirmAndSubmit">确认</button>
      <button class="confirm-btn confirm-btn--retry" @click="retryRecording">重新说</button>
      <button class="confirm-btn confirm-btn--dismiss" @click="dismissConfirmBar">手动输入</button>
      <div v-if="transcriptionCandidates.length > 1" class="confirm-candidates">
        <span class="confirm-candidates-label">也可能是：</span>
        <button v-for="c in transcriptionCandidates" :key="c.text" class="confirm-candidate-chip" @click="selectCandidate(c.text)">{{ c.text }}</button>
      </div>
    </div>

    <!-- 语音错误提示 -->
    <div v-if="voiceErrorMessage" class="voice-error-bar">
      <span>{{ voiceErrorMessage }}</span>
    </div>

    <!-- 浏览器兼容提示 -->
    <div v-if="showBrowserHint && voiceSupported" class="browser-hint-bar">
      <span>推荐使用 Chrome 浏览器以获得最佳语音识别体验</span>
      <button class="browser-hint-close" @click="dismissBrowserHint">知道了</button>
    </div>

    <!-- Vision panel (hidden file input) -->
    <input ref="visionFileInputRef" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="handleVisionFileChange" />

    <!-- Vision result modal -->
    <div v-if="visionPanelOpen" class="vision-modal" @click.self="closeVisionPanel">
      <div class="vision-modal-content">
        <button class="modal-close" @click="closeVisionPanel">✕</button>
        <h3>拍照识景</h3>
        <button :disabled="visionAnalyzing || chatStore.streaming" @click="openVisionFilePicker">选择图片</button>
        <button :disabled="visionAnalyzing || !visionFile || chatStore.streaming" @click="handleAnalyzeImage">
          {{ visionAnalyzing ? '识别中…' : '识别图片' }}
        </button>
        <button v-if="visionFile || visionResult" :disabled="visionAnalyzing" @click="clearVisionPanel">清除</button>
        <div v-if="visionFile">
          <img v-if="visionPreviewUrl" :src="visionPreviewUrl" style="max-width:200px" />
          <strong>{{ visionFile.name }}</strong>
        </div>
        <div v-if="visionError" class="vision-error">{{ visionError }}</div>
        <div v-if="visionResult" class="vision-result">
          <p class="vision-summary">{{ visionResult.scene_summary || '暂未识别出明确场景。' }}</p>
          <div v-if="visionResult.candidate_attractions?.length">
            <span class="vision-label">可能是</span>
            <span v-for="item in visionResult.candidate_attractions" :key="item" class="vision-tag">{{ item }}</span>
          </div>
          <div v-if="visionResult.visual_tags?.length">
            <span class="vision-label">画面特征</span>
            <span v-for="item in visionResult.visual_tags" :key="item" class="vision-tag">{{ item }}</span>
          </div>
          <div class="vision-meta">识别把握：{{ formatConfidence(visionResult.confidence) }}</div>
          <button :disabled="chatStore.streaming || !visionResult.retrieval_query" @click="askFromImage">请小灵讲讲这里</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import ThreeAvatar from "../../components/ThreeAvatar.vue";
import AvatarDisplay from "../../components/AvatarDisplay.vue";
import { analyzeImage } from "../../api/vision";
import { transcribeAudio } from "../../api/voice";
import { useAudioPlayer } from "../../composables/useAudioPlayer";
import { renderMarkdown } from "../../composables/useMarkdown";
import { useRecorder } from "../../composables/useRecorder";
import { useSpeechRecognition } from "../../composables/useSpeechRecognition";
import { useScenicBackground } from "../../composables/useScenicBackground";
import { fetchAvatarConfig } from "../../api/admin";
import { normalizeAvatarPresetFromModelPath, DEFAULT_AVATAR_PRESET } from "../../utils/avatarConfig";
import { GUIDE_PERSONA, useAvatar } from "../../composables/useAvatar";
import { useWeather } from "../../composables/useWeather";
import { useChatStore } from "../../stores/chat";
import { useInteractionStore } from "../../stores/interaction";

const router = useRouter();
const feedbackReasons = [
  { value: "accuracy", label: "内容不准确" },
  { value: "detail", label: "信息不够" },
  { value: "recommendation", label: "建议不合适" },
  { value: "latency", label: "响应太慢" },
  { value: "other", label: "其他" },
];
const chatStore = useChatStore();
const interactionStore = useInteractionStore();
const { scenicBgUrl } = useScenicBackground();
const {
  isRecording,
  isSupported: recorderSupported,
  durationSeconds,
  start: startRecording,
  stop: stopRecording,
} = useRecorder();
const {
  isListening: speechListening,
  interimText: speechInterimText,
  finalText: speechFinalText,
  isSupported: speechSupported,
  error: speechError,
  showBrowserHint,
  start: startSpeechRecognition,
  stop: stopSpeechRecognition,
  abort: abortSpeechRecognition,
  dismissHint: dismissBrowserHint,
} = useSpeechRecognition();
const avatar = useAvatar();
const { displayText: weatherCaption, startPolling: startWeather, stopPolling: stopWeather } = useWeather();
const audioPlayer = useAudioPlayer();
const avatarState = avatar.currentState;
const avatarError = ref(false);

const GUIDE_STYLE_STORAGE_KEY = "a5-pending-guide-style-v1";
const avatarConfig = ref({ modelKey: DEFAULT_AVATAR_PRESET, voiceType: "gentle-female" });

const AVATAR_MODEL_MAP = {
  monk: { name: "明彻法师", subtitle: "明彻法师 · 佛学文化导游" },
  hanfu: { name: "清岚", subtitle: "清岚 · 文化叙事导游" },
  modern: { name: "景行", subtitle: "景行 · 智能导览导游" },
};

const avatarDisplayName = computed(() => AVATAR_MODEL_MAP[avatarConfig.value.modelKey]?.name || "小灵");
const avatarDisplaySubtitle = computed(() => AVATAR_MODEL_MAP[avatarConfig.value.modelKey]?.subtitle || "清岚 · 数字人导游");

async function loadAvatarConfig() {
  try {
    const config = await fetchAvatarConfig();
    avatarConfig.value.modelKey = normalizeAvatarPresetFromModelPath(config?.model_path, DEFAULT_AVATAR_PRESET);
    avatarConfig.value.voiceType = config?.voice_type || "gentle-female";
  } catch {
    // use default
  }
}

const query = ref("");
const explanationLevel = ref("adult");
const transcribing = ref(false);
const transcriptionConfidence = ref(-1);
const showConfirmBar = ref(false);
const transcriptionCandidates = ref([]);
const confirmedTranscript = ref("");
const speechBaseQuery = ref("");
const speechSessionActive = ref(false);
const recorderError = ref("");
const messageListRef = ref(null);
const visionFileInputRef = ref(null);
const visionFile = ref(null);
const visionPreviewUrl = ref("");
const visionResult = ref(null);
const visionAnalyzing = ref(false);
const visionError = ref("");
const visionPanelOpen = ref(false);
const speechProgress = ref(0);
const speechElapsedMs = ref(0);
const speechDurationMs = ref(0);
const visemeTimeline = ref(null);
const activeAudioSegments = ref(0);
const sourceHighlightIndex = ref(-1);
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const activeTab = ref('chat')
const mobileTab = ref('chat')
const showMobileDrawer = ref(false)

function toggleMobileDrawer(tab) {
  if (mobileTab.value === tab && showMobileDrawer.value) {
    showMobileDrawer.value = false
  } else {
    mobileTab.value = tab
    showMobileDrawer.value = true
  }
}

function closeMobileDrawer() {
  showMobileDrawer.value = false
}
const showStyleSelector = ref(false)
const styleOptions = [
  { key: 'child', label: '儿童' },
  { key: 'adult', label: '标准' },
  { key: 'expert', label: '专业' },
]
const quickQuestions = [
  "灵山大佛有多高？",
  "推荐游览路线是什么？",
  "这里有什么代表性的文化典故？",
  "附近适合拍照的景点有哪些？",
];
let greetingTimer = null;

function handleQuickAction(action) {
  if (chatStore.streaming) return
  if (action === 'recommend') submitQuery('推荐灵山值得去的景点')
  else if (action === 'photo') toggleVisionPanel()
  else if (action === 'route') submitQuery('帮我规划一条灵山游览路线')
  else if (action === 'style') showStyleSelector.value = !showStyleSelector.value
}

function closeVisionPanel() {
  visionPanelOpen.value = false
}

function clearVisionPanel() {
  clearVisionState()
}

const voiceSupported = computed(() => speechSupported.value || recorderSupported.value);
const speechPreviewText = computed(() => speechInterimText.value || speechFinalText.value);
const confidenceLevelClass = computed(() => {
  if (transcriptionConfidence.value >= 0.7) return "conf-high";
  if (transcriptionConfidence.value >= 0.4) return "conf-mid";
  if (transcriptionConfidence.value >= 0) return "conf-low";
  return "";
});
const voiceErrorMessage = computed(
  () => getSpeechErrorMessage(speechError.value) || recorderError.value,
);

const avatarReady = computed(() => !avatarError.value);
const voiceReady = computed(() => voiceSupported.value);
const replyStatusClass = computed(() => {
  if (chatStore.streaming) return 'status-pill--live';
  if (avatarState.value === 'thinking') return 'status-pill--loading';
  return 'status-pill--ready';
});
const replyStatusText = computed(() => {
  if (chatStore.streaming) return '正在回答';
  if (avatarState.value === 'thinking') return '思考中';
  return '等待提问';
});

const explanationLevelLabel = computed(() => ({
  child: "亲子游",
  adult: "休闲游",
  expert: "文化深度游",
}[explanationLevel.value] || "休闲游"));

const visionDisplayHints = computed(() => {
  const result = visionResult.value;
  if (!result) {
    return [];
  }
  return normalizeVisionHints([
    ...(result.candidate_attractions || []),
    result.detected_text,
    ...(result.query_hints || []),
    ...(result.visual_tags || []),
  ]).slice(0, 18);
});

function renderAnswer(content, isLastMessage) {
  const isStreaming = chatStore.streaming && isLastMessage;
  return renderMarkdown(content, chatStore.sources, isStreaming);
}

function handleCitationClick(event) {
  const cite = event.target.closest(".citation");
  if (!cite) return;
  const evidenceId = cite.dataset.evidenceId;
  highlightSource(evidenceId);
}

function highlightSource(evidenceId) {
  const index = chatStore.sources.findIndex(
    source => source.evidence_id === `证据${evidenceId}`,
  );
  if (index >= 0) {
    activeTab.value = "source";
    sourceHighlightIndex.value = index;
    nextTick(() => {
      document.querySelector(`[data-source-index="${index}"]`)?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
    setTimeout(() => {
      sourceHighlightIndex.value = -1;
    }, 2000);
  }
}

function handleChangeMode() {
  if (chatStore.streaming || speechListening.value || isRecording.value) {
    return;
  }
  chatStore.stopOutput();
  audioPlayer.stop();
  router.push("/tourist/select");
}

function toggleVisionPanel() {
  visionPanelOpen.value = !visionPanelOpen.value;
}

function scrollToBottom() {
  nextTick(() => {
    const el = messageListRef.value;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  });
}

watch(
  () => chatStore.messages.length,
  () => scrollToBottom(),
);

watch(
  () => {
    const messages = chatStore.messages;
    return messages.length > 0 ? messages[messages.length - 1].content : "";
  },
  () => scrollToBottom(),
);

watch(
  () => chatStore.streaming,
  (streaming) => {
    if (!streaming && activeAudioSegments.value === 0) {
      setTimeout(() => {
        if (
          activeAudioSegments.value === 0
          && (avatar.currentState.value === "speaking" || avatar.currentState.value === "thinking")
        ) {
          avatar.setState("idle");
        }
      }, 600);
    }
  },
);

watch([speechFinalText, speechInterimText], ([finalText, interimText]) => {
  if (!speechSessionActive.value) {
    return;
  }
  query.value = mergeSpeechInput(speechBaseQuery.value, finalText, interimText);
});

watch(speechListening, (listening, wasListening) => {
  if (!listening && wasListening && speechSessionActive.value) {
    query.value = mergeSpeechInput(speechBaseQuery.value, speechFinalText.value, "");
    speechSessionActive.value = false;
    avatar.setState("idle");
  }
});

onMounted(() => {
  interactionStore.initialize();
  loadAvatarConfig();

  startWeather();

  try {
    const pendingStyle = window.sessionStorage.getItem(GUIDE_STYLE_STORAGE_KEY);
    if (pendingStyle && ["child", "adult", "expert"].includes(pendingStyle)) {
      explanationLevel.value = pendingStyle;
      window.sessionStorage.removeItem(GUIDE_STYLE_STORAGE_KEY);
    }
  } catch {}

  if (chatStore.messages.length === 0) {
    greetingTimer = window.setTimeout(() => {
      if (chatStore.messages.length === 0) {
        chatStore.messages.push({
          role: "assistant",
          content: `您好！我是灵山智慧导游${avatarDisplayName.value}，很高兴陪您一起游览。想了解景点故事、规划路线，或认一认眼前的风景，都可以问我。`,
        });
      }
      greetingTimer = null;
    }, 800);
  }
});

onBeforeUnmount(() => {
  if (greetingTimer) {
    window.clearTimeout(greetingTimer);
  }
  chatStore.stopOutput();
  audioPlayer.stop();
  abortSpeechRecognition();
  revokeVisionPreview();
  avatar.setState("idle");
  stopWeather();
});

function handleSubmit() {
  if (speechListening.value || isRecording.value || transcribing.value) {
    return;
  }
  submitQuery(query.value);
}

function handleAvatarLoadError() {
  avatarError.value = true;
}

function handleAvatarLoaded() {
  avatarError.value = false;
}

function handleFollowup(followupQuery) {
  submitQuery(followupQuery);
}

function handleQuickQuestion(question) {
  submitQuery(question);
}

function submitQuery(rawQuery, extraOptions = {}) {
  const value = rawQuery.trim();
  if (!value || chatStore.streaming) {
    return;
  }
  const levelPrefix = {
    child: "请用小朋友能听懂的语言解释：",
    adult: "",
    expert: "请给出专业详细的解释：",
  }[explanationLevel.value];
  const finalQuery = `${levelPrefix}${value}`;
  avatar.setState("thinking");
  try {
    chatStore.sendMessage(finalQuery, interactionStore.selectionPayload, {
      ttsConfig: {
        voiceType: avatarConfig.value.voiceType,
        speechRate: 100,
        volume: 80,
      },
      onContext: (selection) => interactionStore.applyResolvedSelection(selection),
      onAvatar: (payload) => {
        try {
          avatar.handleAvatarEvent(payload);
        } catch {
          avatarError.value = true;
        }
      },
      onAudioStart: () => {
        activeAudioSegments.value += 1;
        avatar.setState("speaking");
      },
      onAudioEnded: () => {
        activeAudioSegments.value = Math.max(activeAudioSegments.value - 1, 0);
        if (activeAudioSegments.value === 0) {
          avatar.setState("idle");
          speechProgress.value = 0;
          speechElapsedMs.value = 0;
          speechDurationMs.value = 0;
          visemeTimeline.value = null;
        }
      },
      onSpeechProgress: (progress, elapsedMs, timeline, actualDurationMs) => {
        speechProgress.value = progress;
        speechElapsedMs.value = elapsedMs;
        speechDurationMs.value = actualDurationMs;
        visemeTimeline.value = timeline;
      },
      ...extraOptions,
    });
  } catch {
    avatarError.value = true;
  }
  query.value = "";
}

async function toggleRecording() {
  if (chatStore.streaming || transcribing.value) {
    return;
  }

  recorderError.value = "";

  if (speechListening.value) {
    stopSpeechRecognition();
    return;
  }

  if (isRecording.value) {
    const audioBlob = await stopRecording();
    if (!audioBlob) {
      avatar.setState("idle");
      return;
    }
    transcribing.value = true;
    try {
      const result = await transcribeAudio(audioBlob);
      if (!result || !result.text) {
        recorderError.value = "没听清楚，请靠近麦克风重新说一遍，或直接打字输入。";
        if (result && Array.isArray(result.candidates) && result.candidates.length > 0) {
          transcriptionCandidates.value = result.candidates.slice(0, 3);
        }
        showConfirmBar.value = false;
        transcriptionConfidence.value = -1;
        avatar.setState("idle");
        return;
      }

      transcriptionConfidence.value = typeof result.confidence === "number" ? result.confidence : -1;
      transcriptionCandidates.value = Array.isArray(result.candidates) ? result.candidates : [];

      if (result.confidence >= 0.7 && !result.needs_confirmation) {
        query.value = result.text;
        showConfirmBar.value = false;
        confirmedTranscript.value = result.text;
      } else if (result.confidence >= 0.4 || result.needs_confirmation) {
        query.value = result.text;
        confirmedTranscript.value = result.text;
        showConfirmBar.value = true;
      } else {
        query.value = "";
        confirmedTranscript.value = "";
        showConfirmBar.value = false;
        if (transcriptionCandidates.value.length > 0) {
          recorderError.value = "没听清楚，请靠近麦克风重新说一遍，选择候选项或直接打字输入。";
        } else {
          recorderError.value = "没听清楚，请靠近麦克风重新说一遍，或直接打字输入。";
        }
      }
    } catch {
      recorderError.value = "录音转写失败，请改用文字输入。";
      showConfirmBar.value = false;
      transcriptionConfidence.value = -1;
    } finally {
      transcribing.value = false;
    }
    avatar.setState("idle");
    return;
  }

  audioPlayer.stop();

  if (speechSupported.value) {
    speechBaseQuery.value = query.value.trim();
    speechSessionActive.value = true;
    avatar.setState("listening");
    const started = startSpeechRecognition();
    if (!started) {
      speechSessionActive.value = false;
      avatar.setState("idle");
    }
    return;
  }

  avatar.setState("listening");
  await startRecording();
  if (!isRecording.value) {
    recorderError.value = "当前浏览器无法使用麦克风，请改用文字输入。";
    avatar.setState("idle");
  }
}

function dismissConfirmBar() {
  showConfirmBar.value = false;
  recorderError.value = "";
  transcriptionCandidates.value = [];
}

function confirmAndSubmit() {
  showConfirmBar.value = false;
  recorderError.value = "";
  transcriptionCandidates.value = [];
  if (query.value.trim()) {
    handleSubmit();
  }
}

function retryRecording() {
  showConfirmBar.value = false;
  recorderError.value = "";
  transcriptionCandidates.value = [];
  query.value = confirmedTranscript.value;
  avatar.setState("listening");
  startRecording();
}

function selectCandidate(candidateText) {
  showConfirmBar.value = false;
  recorderError.value = "";
  transcriptionCandidates.value = [];
  query.value = candidateText;
  handleSubmit();
}

function mergeSpeechInput(baseText, finalText, interimText) {
  return [baseText, finalText, interimText]
    .map((item) => item.trim())
    .filter(Boolean)
    .join(" ");
}

function getSpeechErrorMessage(errorCode) {
  if (!errorCode || errorCode === "aborted") {
    return "";
  }
  const messages = {
    "not-allowed": "麦克风权限被拒绝，请在浏览器地址栏中允许麦克风后重试。",
    "service-not-allowed": "浏览器未允许语音识别服务，请检查网站权限。",
    "audio-capture": "没有检测到可用麦克风，请检查设备连接。",
    "no-speech": "没有识别到语音，请靠近麦克风后重试。",
    network: "浏览器语音识别服务暂时不可用，请检查网络或改用文字输入。",
    "language-not-supported": "当前浏览器不支持中文语音识别。",
    "not-supported": "当前浏览器不支持语音识别，请使用 Chrome 或改用文字输入。",
    "start-failed": "语音识别启动失败，请稍后重试。",
    InvalidStateError: "语音识别正在运行，请结束当前识别后重试。",
  };
  return messages[errorCode] || `语音识别失败（${errorCode}），请重试或改用文字输入。`;
}

function openVisionFilePicker() {
  visionFileInputRef.value?.click();
}

function handleVisionFileChange(event) {
  const file = event.target.files?.[0];
  visionError.value = "";
  visionResult.value = null;
  if (!file) {
    return;
  }
  if (!file.type.startsWith("image/")) {
    visionError.value = "请选择图片文件。";
    event.target.value = "";
    return;
  }
  if (file.size > MAX_IMAGE_BYTES) {
    visionError.value = "图片不能超过 5MB。";
    event.target.value = "";
    return;
  }
  visionFile.value = file;
  revokeVisionPreview();
  visionPreviewUrl.value = URL.createObjectURL(file);
}

async function handleAnalyzeImage() {
  if (!visionFile.value || visionAnalyzing.value) {
    return;
  }
  visionAnalyzing.value = true;
  visionError.value = "";
  visionResult.value = null;
  try {
    visionResult.value = await analyzeImage(
      visionFile.value,
      "这张图片可能对应景区哪个位置？请提取可用于景区资料检索的线索。",
    );
  } catch (error) {
    visionError.value = `图片识别失败：${error.message}`;
  } finally {
    visionAnalyzing.value = false;
  }
}

function askFromImage() {
  const retrievalQuery = visionResult.value?.retrieval_query?.trim();
  if (!retrievalQuery) {
    return;
  }
  const prompt = [
    "请根据这张图片识别出的线索，基于官方资料介绍它最可能对应的景区景点。",
    "图片识别线索如下，仅用于检索官方资料，不作为事实来源：",
    retrievalQuery,
  ].join("\n");
  submitQuery(limitChatQuery(prompt), { visionContext: visionResult.value });
}

function clearVisionState() {
  visionFile.value = null;
  visionResult.value = null;
  visionError.value = "";
  if (visionFileInputRef.value) {
    visionFileInputRef.value.value = "";
  }
  revokeVisionPreview();
}

function revokeVisionPreview() {
  if (visionPreviewUrl.value) {
    URL.revokeObjectURL(visionPreviewUrl.value);
    visionPreviewUrl.value = "";
  }
}

function limitChatQuery(value) {
  const maxLength = 950;
  return value.length > maxLength ? `${value.slice(0, maxLength)}…` : value;
}

function normalizeVisionHints(values) {
  const seen = new Set();
  const hints = [];
  values.flatMap(flattenVisionHint).forEach((value) => {
    const normalized = String(value ?? "").replace(/\s+/g, " ").trim();
    if (!normalized || normalized === "[]" || normalized === "{}" || normalized.toLowerCase() === "null") {
      return;
    }
    if (seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    hints.push(normalized);
  });
  return hints;
}

function flattenVisionHint(value) {
  if (Array.isArray(value)) {
    return value.flatMap(flattenVisionHint);
  }
  if (value && typeof value === "object") {
    return [value.text || value.content || value.value || ""];
  }
  return [value];
}

function formatBytes(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatConfidence(value) {
  if (typeof value !== "number") {
    return "未知";
  }
  return `${Math.round(value * 100)}%`;
}
</script>

<style scoped>
/* ============================================================
   DARK THEME TOURIST PAGE - aligned to design-redesign spec
   ============================================================ */
.tourist-page {
  position: relative;
  width: 100%; height: 100vh; height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #1a1612;
  color: #f0ece5;
  color-scheme: dark;
}

.scenic-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
.scenic-bg-img {
  position: absolute; inset: 0;
  background-position: center; background-repeat: no-repeat; background-size: cover;
  filter: blur(10px) saturate(0.3) brightness(0.4);
  transform: scale(1.06);
}
.scenic-bg-overlay {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 60% 40% at 50% 35%, transparent 0%, rgba(20,16,10,0.55) 80%),
    radial-gradient(ellipse 80% 50% at 50% 100%, rgba(22,18,10,0.5) 0%, transparent 70%);
}

.back-btn {
  position: absolute; top: clamp(10px, 2vw, 32px); left: clamp(10px, 2vw, 32px); z-index: 25;
  display: inline-flex; align-items: center; gap: 6px;
  padding: clamp(8px, 0.9vw, 14px) clamp(16px, 1.8vw, 28px);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 999px;
  background: rgba(255,250,242,0.05);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  color: rgba(232,228,219,0.55);
  font-family: inherit; font-size: clamp(14px, 1.2vw, 20px);
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
  outline: none;
}
.back-btn:hover {
  border-color: rgba(255,250,242,0.19);
  background: rgba(255,255,255,0.09);
  color: rgba(232,228,219,0.85);
}
.back-btn:focus-visible { outline: 2px solid #d9a441; outline-offset: 3px; }

.top-right {
  position: absolute; top: clamp(10px, 2vw, 32px); right: clamp(10px, 2vw, 32px); z-index: 20;
  display: flex; flex-direction: column;
  align-items: flex-end; gap: 8px;
}
.top-brand {
  color: rgba(232,228,219,0.88);
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: clamp(24px, 2.8vw, 40px);
  font-weight: 400;
  letter-spacing: 0.12em;
  text-shadow: 0 0 30px rgba(217,164,65,0.1);
  line-height: 1.2;
}
.top-status-row {
  display: flex; flex-direction: column; gap: 5px;
}
.status-item {
  display: flex; align-items: center; gap: 8px;
  font-size: clamp(13px, 0.9vw, 17px); font-weight: 400;
  letter-spacing: 0.06em;
  color: rgba(232,228,219,0.55);
  font-family: system-ui, sans-serif;
}
.status-dot {
  width: 12px; height: 12px;
  border-radius: 50%; flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
}
.status-dot--ready  { background: #d9a441; box-shadow: 0 0 4px rgba(217,164,65,0.5); }
.status-dot--live   { background: #5ec9a4; box-shadow: 0 0 4px rgba(94,201,164,0.5); }
.status-dot--weather { background: #6bb8e8; box-shadow: 0 0 4px rgba(107,184,232,0.5); }

.tourist-stage {
  position: relative; z-index: 10;
  flex: 1; min-height: 0;
  display: grid;
  grid-template-columns: minmax(clamp(160px, 12vw, 260px), clamp(240px, 17vw, 350px)) 1fr minmax(clamp(160px, 12vw, 260px), clamp(240px, 17vw, 350px));
  gap: clamp(8px, 1vw, 16px);
  align-items: stretch;
  padding: 20px clamp(10px, 1.5vw, 24px) 0;
  margin-top: 0;
}

.chat-center {
  grid-column: 2; grid-row: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  position: relative; z-index: 2;
  width: 100%; height: 100%;
  min-height: 0;
  padding: 0 8px;
}
.top-caption {
  position: absolute;
  top: 16px; left: 50%; transform: translateX(-50%);
  z-index: 20;
  display: flex; align-items: baseline; justify-content: center; gap: 12px;
  white-space: nowrap;
}
.caption-kicker {
  color: #f8e7bb;
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(18px, 2vw, 28px); font-weight: 700; letter-spacing: 0.1em;
  text-shadow: 0 0 20px rgba(217,164,65,0.15);
}
.caption-weather {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba(23,18,14,0.6);
  color: rgba(232,228,219,0.38);
  font-family: system-ui, sans-serif;
  font-size: clamp(12px, 0.8vw, 14px); font-weight: 400;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.caption-weather-live {
  color: rgba(232,228,219,0.55);
}
.crowd-indicator {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba(23,18,14,0.6);
  font-size: 13px; font-weight: 400;
  color: rgba(232,228,219,0.55);
  letter-spacing: 0.04em;
  font-family: system-ui, sans-serif;
  white-space: nowrap;
  cursor: default;
}
.crowd-dot {
  width: 12px; height: 12px;
  border-radius: 50%; flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
}
.crowd-indicator[data-level="green"] .crowd-dot { background: #5ec9a4; }

.avatar-stage {
  position: relative; z-index: 2;
  width: min(clamp(360px, 34vw, 650px), 100vw);
  height: calc(min(clamp(360px, 42vh, 560px), 66vh) + 140px);
  padding-top: 140px;
  margin: -140px auto 0;
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  background: transparent;
  box-sizing: border-box;
}
.avatar-stage::after {
  content: "";
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 140px;
  z-index: 3;
  pointer-events: none;
  background: linear-gradient(to bottom, transparent 0%, #1a1612 100%);
}
.avatar-stage :deep(.three-wrapper),
.avatar-stage :deep(.avatar-display) {
  width: 100%; height: 100%;
  transform: translateY(8%);
}

.side-card {
  position: absolute;
  left: clamp(12px, 1.5vw, 28px); bottom: clamp(60px, 7vh, 120px);
  z-index: 15;
  width: clamp(260px, 17vw, 420px); height: clamp(340px, 52vh, 500px);
  background: rgba(23,18,14,0.88);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 10px;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.side-card.speaking {
  animation: card-breathe 3s ease-in-out infinite;
}
@keyframes card-breathe {
  0%, 100% { box-shadow: 0 0 0 rgba(217,164,65,0); }
  50% { box-shadow: 0 0 40px rgba(217,164,65,0.08); }
}
.side-card-head {
  flex-shrink: 0;
  position: relative;
}
.side-card-tabs {
  display: flex;
}
.side-card-tab {
  flex: 1;
  padding: 7px 0;
  border: none;
  background: transparent;
  color: rgba(232,228,219,0.35);
  font-family: inherit; font-size: clamp(14px, 0.9vw, 17px);
  font-weight: 600; letter-spacing: 0.06em;
  cursor: pointer;
  transition: color 0.25s ease;
  position: relative;
}
.side-card-tab:hover { color: rgba(232,228,219,0.7); }
.side-card-tab.active { color: rgba(232,228,219,0.75); }
.side-card-tab.active::after {
  content: "";
  position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 24px; height: 2px;
  border-radius: 1px;
  background: #d9a441;
}
.side-card-body {
  flex: 1; min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px 12px;
  display: flex; flex-direction: column;
  gap: 10px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.15) transparent;
}
.side-card-body.hidden { display: none; }
.side-card-body::-webkit-scrollbar { width: 4px; }
.side-card-body::-webkit-scrollbar-track { background: transparent; }
.side-card-body::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.15); border-radius: 2px; }
.side-card-body::-webkit-scrollbar-thumb:hover { background: rgba(217,164,65,0.25); }

.msg-item { display: flex; flex-direction: column; }
.msg-item.assistant { align-items: flex-start; }
.msg-item.user { align-items: flex-end; }
.msg-item.user.collapsed { gap: 4px; }
.msg-item.user.collapsed .msg-bubble {
  max-height: 24px; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis;
  opacity: 0.45; font-size: 16px;
  padding: 4px 10px; border-radius: 6px;
  border-bottom-right-radius: 2px;
}
.msg-bubble {
  max-width: 90%;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 15px; line-height: 1.5;
  letter-spacing: 0.03em;
  word-break: break-word;
}
.msg-item.user .msg-bubble {
  background: rgba(217,164,65,0.12);
  border: none;
  color: rgba(232,228,219,0.9);
  border-bottom-right-radius: 4px;
}
.msg-item.assistant .msg-bubble {
  background: rgba(232,228,219,0.05);
  border: none;
  color: rgba(232,228,219,0.85);
  border-bottom-left-radius: 4px;
}
.typing-cursor {
  animation: blink 0.8s infinite;
  color: #d9a441;
  font-weight: 700; font-size: 16px; margin-left: 4px;
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

.followup-panel {
  display: flex; flex-wrap: wrap; gap: 8px;
  padding: 12px;
  border: 1px solid rgba(248,231,187,0.16);
  border-radius: 14px;
  background: rgba(255,248,232,0.06);
}
.followup-panel button {
  padding: 8px 14px;
  border: 1px solid rgba(248,231,187,0.2);
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  color: #f8e7bb; font-size: clamp(13px, 0.8vw, 15px);
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}
.followup-panel button:hover:not(:disabled) {
  background: rgba(255,255,255,0.16);
  border-color: rgba(248,231,187,0.42);
  transform: translateY(-1px);
}
.followup-panel button:disabled { opacity: 0.5; cursor: not-allowed; }

.source-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
.source-item {
  padding: 10px;
  border: 1px solid rgba(232,228,219,0.08);
  border-radius: 8px;
  background: rgba(232,228,219,0.04);
  transition: border-color 0.3s ease, background 0.3s ease;
}
.source-item:hover { border-color: rgba(232,228,219,0.20); background: rgba(232,228,219,0.08); }
.source-item.highlight {
  border-color: rgba(217,164,65,0.5);
  background: rgba(217,164,65,0.08);
}
.source-item h4 {
  display: flex; align-items: center; gap: 6px;
  margin: 0 0 5px;
  color: rgba(232,228,219,0.85); font-size: 18px; font-weight: 600;
}
.source-num {
  display: inline-flex; flex-shrink: 0;
  align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 50%;
  background: rgba(217,164,65,0.2);
  color: #d9a441; font-size: 13px; font-weight: 700;
}
.source-item p {
  margin: 0 0 3px;
  color: rgba(232,228,219,0.55); font-size: 14px; line-height: 1.5;
}
.source-meta { color: rgba(232,228,219,0.3); font-size: 13px; }
.source-empty { color: rgba(240,242,236,0.52); text-align: center; padding: 60px 0; font-size: 15px; }

.stop-notice { text-align: center; padding: 8px; color: rgba(248,231,187,0.6); font-size: 14px; }
.error-notice { text-align: center; padding: 8px; color: #f87171; font-size: 14px; }

.right-card {
  position: absolute;
  right: clamp(12px, 1.5vw, 28px); top: clamp(80px, 8vh, 130px); bottom: clamp(60px, 7vh, 120px);
  z-index: 15;
  width: clamp(270px, 18vw, 450px);
  background: rgba(23,18,14,0.88);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 10px;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.right-card-head {
  flex-shrink: 0;
  position: relative;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(232,228,219,0.06);
  color: rgba(232,228,219,0.5);
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(12px, 0.8vw, 14px); font-weight: 600;
  letter-spacing: 0.06em;
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
}
.right-card-body {
  flex: 1; min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px 12px;
  display: flex; flex-direction: column;
  gap: 6px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.15) transparent;
}
.right-card-body::-webkit-scrollbar { width: 4px; }
.right-card-body::-webkit-scrollbar-track { background: transparent; }
.right-card-body::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.15); border-radius: 2px; }
.right-card-body::-webkit-scrollbar-thumb:hover { background: rgba(217,164,65,0.25); }

.service-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 8px;
}
.explore-card {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: clamp(6px, 0.5vw, 10px);
  padding: clamp(10px, 1.2vw, 18px) clamp(6px, 0.8vw, 14px);
  border-radius: 8px;
  border: 1px solid rgba(232,228,219,0.10);
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  text-align: center; min-height: 0;
  transition: border-color 0.3s ease, background 0.3s ease;
  outline: none; position: relative; overflow: hidden;
  font-family: inherit; color: inherit;
}
.explore-card:hover {
  border-color: rgba(217,164,65,0.35);
  background: rgba(217,164,65,0.06);
}
.explore-card:active { transform: scale(0.96); }
.explore-card:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.explore-card-icon {
  width: clamp(44px, 3vw, 64px); height: clamp(44px, 3vw, 64px); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: clamp(22px, 1.6vw, 32px); flex-shrink: 0;
  transition: transform 0.3s ease;
}
.explore-card:hover .explore-card-icon { transform: scale(1.1); }
.explore-card--scenic .explore-card-icon { background: rgba(217,164,65,0.15); color: #d9a441; }
.explore-card--area   .explore-card-icon { background: rgba(94,201,164,0.15); color: #5ec9a4; }
.explore-card--type   .explore-card-icon { background: rgba(107,184,232,0.15); color: #6bb8e8; }
.explore-card--photo  .explore-card-icon { background: rgba(232,168,64,0.15); color: #e8a840; }
.explore-card-title {
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: clamp(16px, 1.3vw, 24px); font-weight: 600;
  color: rgba(232,228,219,0.82);
  letter-spacing: 0.05em; line-height: 1.3;
}
.explore-card-desc {
  font-size: clamp(12px, 0.8vw, 15px); font-weight: 400;
  color: rgba(232,228,219,0.3);
  letter-spacing: 0.04em; line-height: 1.2;
  font-family: system-ui, sans-serif;
}

.style-selector {
  display: flex; gap: 10px;
  padding: 14px;
  border: 1px solid rgba(248,231,187,0.16);
  border-radius: 16px;
  background: rgba(255,255,255,0.05);
}
.style-selector button {
  flex: 1;
  padding: 10px 0;
  border: 1px solid rgba(248,231,187,0.18);
  border-radius: 999px;
  background: rgba(255,255,255,0.06);
  color: rgba(240,242,236,0.74);
  font-size: 16px; font-weight: 600;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
  font-family: inherit;
}
.style-selector button:hover {
  border-color: rgba(248,231,187,0.38);
  background: rgba(255,255,255,0.12);
  color: #f8e7bb;
}
.style-selector button.active {
  border-color: #f8e7bb;
  background: rgba(248,231,187,0.2);
  color: #f8e7bb;
  box-shadow: 0 0 14px rgba(248,231,187,0.16);
}

.input-row {
  position: absolute;
  bottom: clamp(24px, 2.5vh, 40px); left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  width: min(clamp(420px, 42vw, 800px), 88vw);
  display: flex; align-items: center; justify-content: center; gap: 12px;
}
.input-field {
  flex: 1;
  height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(16px, 1.5vw, 28px);
  border: 1px solid rgba(232,228,219,0.12);
  border-radius: 10px;
  background: rgba(23,18,14,0.78);
  color: rgba(232,228,219,0.82);
  font-family: inherit; font-size: clamp(16px, 1.2vw, 24px);
  letter-spacing: 0.03em;
  outline: none;
  transition: border-color 0.25s ease;
}
.input-field::placeholder { color: rgba(232,228,219,0.25); font-size: clamp(15px, 1.1vw, 22px); }
.input-field:focus { border-color: rgba(217,164,65,0.35); }
.input-field:disabled { opacity: 0.5; }

.voice-btn {
  flex-shrink: 0; width: auto; height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(14px, 1.8vw, 32px);
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(217,164,65,0.3);
  border-radius: 999px;
  background: rgba(217,164,65,0.14);
  color: #d9a441;
  font-family: inherit; font-size: clamp(16px, 1.2vw, 24px); font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
  outline: none; white-space: nowrap;
}
.voice-btn:hover:not(:disabled) {
  border-color: rgba(217,164,65,0.45);
  background: rgba(217,164,65,0.2);
  box-shadow: 0 0 20px rgba(217,164,65,0.15);
}
.voice-btn:active { transform: scale(0.95); }
.voice-btn:focus-visible { outline: 2px solid #d9a441; outline-offset: 3px; }
.voice-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.voice-btn.recording {
  border-color: #b84c3b;
  background: rgba(184,76,59,0.22);
  color: #f0c0c0;
  animation: voice-active 1.2s ease-in-out infinite;
}
@keyframes voice-active {
  0%,100% { box-shadow: 0 0 0 0 rgba(184,76,59,0.3); }
  50% { box-shadow: 0 0 0 8px rgba(184,76,59,0); }
}

.image-btn {
  flex-shrink: 0; width: auto; height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(14px, 1.4vw, 28px);
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(94,201,164,0.25);
  border-radius: 999px;
  background: rgba(94,201,164,0.1);
  color: #5ec9a4;
  font-family: inherit; font-size: clamp(15px, 1.1vw, 22px); font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
  outline: none; white-space: nowrap;
}
.image-btn:hover {
  border-color: rgba(94,201,164,0.45);
  background: rgba(94,201,164,0.2);
  box-shadow: 0 0 20px rgba(94,201,164,0.15);
}
.image-btn:active { transform: scale(0.95); }
.image-btn:focus-visible { outline: 2px solid #5ec9a4; outline-offset: 3px; }

.speech-bar {
  position: absolute;
  bottom: 106px; left: 50%;
  transform: translateX(-50%);
  z-index: 25;
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  padding: 12px 20px;
  border: 1px solid rgba(240,180,155,0.24);
  border-radius: 16px;
  background: rgba(30,20,14,0.92);
  backdrop-filter: blur(14px);
  color: #f0b49b; font-size: 16px;
}
.speech-bar > span:last-child { color: rgba(240,242,236,0.68); }
.speech-pulse {
  width: 10px; height: 10px; border-radius: 999px;
  background: #f87171;
  box-shadow: 0 0 0 rgba(248,113,113,0.36);
  animation: speech-pulse 1.35s ease-out infinite;
}
@keyframes speech-pulse {
  0% { box-shadow: 0 0 0 0 rgba(248,113,113,0.34); }
  70% { box-shadow: 0 0 0 10px rgba(248,113,113,0); }
  100% { box-shadow: 0 0 0 0 rgba(248,113,113,0); }
}

.confidence-dot {
  width: 12px; height: 12px; border-radius: 50%;
  flex-shrink: 0; margin-left: 2px;
  border: 1px solid rgba(255,250,242,0.18);
}
.confidence-dot.conf-high { background: #5ec9a4; box-shadow: 0 0 6px rgba(94,201,164,0.5); }
.confidence-dot.conf-mid  { background: #e8a840; box-shadow: 0 0 6px rgba(232,168,64,0.5); }
.confidence-dot.conf-low  { background: #f87171; box-shadow: 0 0 6px rgba(248,113,113,0.5); }

.confirm-bar {
  position: absolute;
  bottom: 106px; left: 50%;
  transform: translateX(-50%);
  z-index: 26;
  display: flex; flex-wrap: wrap; align-items: center; gap: 10px;
  padding: 14px 20px;
  border: 1px solid rgba(248,231,187,0.28);
  border-radius: 16px;
  background: rgba(28,24,18,0.94);
  backdrop-filter: blur(14px);
  max-width: 600px;
}
.confirm-text { color: rgba(232,228,219,0.82); font-size: 16px; white-space: nowrap; }
.confirm-text strong { color: #f8e7bb; font-weight: 700; }
.confirm-btn {
  padding: 8px 18px;
  border-radius: 999px;
  font-family: inherit; font-size: 15px; font-weight: 600;
  cursor: pointer; border: 1px solid transparent;
  transition: background 0.18s ease, border-color 0.18s ease;
  white-space: nowrap;
}
.confirm-btn--yes {
  background: rgba(94,201,164,0.18); border-color: rgba(94,201,164,0.35);
  color: #5ec9a4;
}
.confirm-btn--yes:hover { background: rgba(94,201,164,0.3); }
.confirm-btn--retry {
  background: rgba(217,164,65,0.14); border-color: rgba(217,164,65,0.3);
  color: #d9a441;
}
.confirm-btn--retry:hover { background: rgba(217,164,65,0.25); }
.confirm-btn--dismiss {
  background: rgba(232,228,219,0.06); border-color: rgba(232,228,219,0.15);
  color: rgba(232,228,219,0.55);
}
.confirm-btn--dismiss:hover { background: rgba(232,228,219,0.12); }

.confirm-candidates {
  width: 100%;
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(232,228,219,0.08);
}
.confirm-candidates-label { color: rgba(232,228,219,0.35); font-size: 13px; }
.confirm-candidate-chip {
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid rgba(248,231,187,0.2);
  background: rgba(255,255,255,0.05);
  color: rgba(232,228,219,0.7);
  font-family: inherit; font-size: 14px;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease;
}
.confirm-candidate-chip:hover {
  background: rgba(248,231,187,0.12);
  border-color: rgba(248,231,187,0.4);
}

.vision-modal {
  position: fixed; inset: 0;
  z-index: 50;
  display: flex; align-items: center; justify-content: center;
  background: rgba(4,6,5,0.72);
  backdrop-filter: blur(10px);
}
.vision-modal-content {
  position: relative;
  width: min(500px, 90vw);
  max-height: 80vh;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 28px 24px;
  border: 1px solid rgba(233,240,235,0.16);
  border-radius: 24px;
  background: rgba(20,26,22,0.94);
  box-shadow: 0 28px 72px rgba(4,8,6,0.55);
  backdrop-filter: blur(18px);
  display: grid; gap: 14px;
  color: rgba(255,255,255,0.88);
}
.vision-modal-content h3 { margin: 0; color: #f8e7bb; font-family: "STKaiti","KaiTi",serif; font-size: 24px; }
.vision-modal-content button {
  padding: 12px 22px;
  border: 1px solid rgba(248,231,187,0.22);
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.9);
  font-size: 16px; font-weight: 600;
  cursor: pointer; font-family: inherit;
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}
.vision-modal-content button:hover:not(:disabled) {
  background: rgba(255,255,255,0.16);
  border-color: rgba(248,231,187,0.44);
  transform: translateY(-1px);
}
.vision-modal-content button:disabled { opacity: 0.5; cursor: not-allowed; }
.modal-close {
  position: absolute;
  top: 14px; right: 16px;
  padding: 6px 12px;
  border: none; background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.7); font-size: 18px;
  cursor: pointer;
}
.vision-error { color: #f87171; font-size: 14px; }
.voice-error-bar {
  position: absolute;
  bottom: 106px; left: 50%;
  transform: translateX(-50%);
  z-index: 25;
  padding: 10px 18px;
  border: 1px solid rgba(248,113,113,0.3);
  border-radius: 12px;
  background: rgba(40,16,16,0.92);
  color: rgba(255,180,160,0.92);
  font-size: 14px;
}

.browser-hint-bar {
  position: absolute;
  bottom: 106px; left: 50%;
  transform: translateX(-50%);
  z-index: 26;
  display: flex; align-items: center; gap: 14px;
  padding: 10px 18px;
  border: 1px solid rgba(107,184,232,0.3);
  border-radius: 12px;
  background: rgba(14,22,36,0.94);
  color: rgba(160,200,240,0.9);
  font-size: 14px;
  white-space: nowrap;
}
.browser-hint-close {
  padding: 4px 12px;
  border: 1px solid rgba(107,184,232,0.25);
  border-radius: 6px;
  background: rgba(107,184,232,0.1);
  color: rgba(160,200,240,0.9);
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
}
.browser-hint-close:hover { background: rgba(107,184,232,0.2); }

.mobile-tab-bar { display: none; }

.mobile-drawer-overlay {
  display: none;
}
.mobile-drawer-panel {
  display: none;
}
.mobile-drawer-handle {
  display: none;
}

@media (max-width: 720px) {
  .tourist-page { overflow: hidden; padding: 0; }
  .tourist-stage { display: flex; flex-direction: column; padding: 0; margin-top: 40px; gap: 0; flex: 1; min-height: 0; padding-bottom: 48px; }
  .side-card { display: none; }
  .right-card { display: none; }
  .chat-center { flex: 1; padding: 0; min-height: 0; }
  .avatar-stage { width: min(52vh, 78vw); height: 100%; min-height: 0; flex: 1; }
  .avatar-stage :deep(.three-wrapper),
  .avatar-stage :deep(.avatar-display) { transform: translateY(10%); }
  .avatar-stage::after { height: 80px; }
  .input-row { position: absolute; bottom: 56px; left: 0; right: 0; transform: none; width: auto; gap: 6px; padding: 0 10px; margin: 0; }
  .input-field { height: 48px; font-size: 16px; padding: 0 14px; }
  .input-field::placeholder { font-size: 14px; }
  .back-btn { top: 6px; left: 6px; padding: 5px 12px; font-size: 14px; }
  .top-right { top: 6px; right: 6px; }
  .top-brand { font-size: 15px; }
  .top-caption { flex-wrap: wrap; gap: 4px; }
  .caption-kicker { font-size: 15px; }
  .caption-weather { font-size: 10px; padding: 3px 8px; }
  .crowd-indicator { font-size: 10px; padding: 3px 8px; }
  .service-grid { grid-template-columns: 1fr 1fr; gap: 8px; }
  .voice-btn { padding: 0 12px; height: 44px; font-size: 15px; }
  .image-btn { padding: 0 12px; height: 44px; font-size: 14px; }
  .explore-card { padding: 10px 6px; }
  .explore-card-icon { width: 40px; height: 40px; font-size: 22px; }
  .explore-card-title { font-size: 16px; }
  .explore-card-desc { font-size: 12px; }
  .speech-bar { bottom: 118px; font-size: 13px; padding: 8px 14px; }
  .confirm-bar { bottom: 118px; max-width: calc(100vw - 20px); font-size: 14px; padding: 10px 14px; }
  .voice-error-bar { bottom: 118px; font-size: 12px; }
  .browser-hint-bar { bottom: 118px; font-size: 11px; }
  .vision-modal-content { padding: 18px 14px; }
  .vision-modal-content h3 { font-size: 20px; }

  .mobile-tab-bar {
    display: flex;
    position: absolute;
    bottom: 0; left: 0; right: 0;
    z-index: 30;
    height: 48px;
    background: rgba(18,14,8,0.94);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 16px 16px 0 0;
    border-top: 1px solid rgba(255,250,242,0.08);
  }
  .mobile-tab-bar button {
    flex: 1;
    padding: 0;
    border: none;
    background: transparent;
    color: rgba(232,228,219,0.38);
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    font-family: inherit;
    letter-spacing: 0.04em;
    transition: color 0.2s ease;
    position: relative;
    display: flex; align-items: center; justify-content: center; gap: 5px;
  }
  .mobile-tab-bar button.active {
    color: #d9a441;
  }
  .mobile-tab-bar button.active::after {
    content: "";
    position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
    width: 28px; height: 3px;
    border-radius: 2px;
    background: #d9a441;
  }

  .mobile-drawer-overlay {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 35;
    background: rgba(4,6,5,0.55);
    backdrop-filter: blur(3px);
    -webkit-backdrop-filter: blur(3px);
  }

  .mobile-drawer-panel {
    display: flex;
    flex-direction: column;
    position: fixed;
    bottom: 0; left: 0; right: 0;
    z-index: 36;
    height: 45vh;
    background: rgba(20,16,10,0.97);
    border-radius: 20px 20px 0 0;
    border-top: 1px solid rgba(255,250,242,0.10);
    overflow: hidden;
    box-shadow: 0 -8px 40px rgba(0,0,0,0.4);
  }
  .mobile-drawer-handle {
    display: block;
    width: 36px;
    height: 4px;
    border-radius: 2px;
    background: rgba(232,228,219,0.2);
    margin: 10px auto 6px;
    flex-shrink: 0;
  }

  .drawer-fade-enter-active,
  .drawer-fade-leave-active { transition: opacity 0.25s ease; }
  .drawer-fade-enter-from,
  .drawer-fade-leave-to { opacity: 0; }

  .drawer-slide-enter-active,
  .drawer-slide-leave-active { transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1); }
  .drawer-slide-enter-from { transform: translateY(100%); }
  .drawer-slide-leave-to { transform: translateY(100%); }
}

@media (prefers-reduced-motion: reduce) {
  .side-card.speaking { animation: none; }
  .voice-btn.recording { animation: none; }
  .speech-pulse { animation: none; }
}

/* ---- status inline dots (scoped override) ---- */
.status-inline-dot {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 400;
  letter-spacing: 0.03em;
  color: rgba(232,228,219,0.45);
  font-family: system-ui, "Noto Sans SC", sans-serif;
  white-space: nowrap;
}
.status-inline-dot::before {
  content: "";
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
  transition: background 0.3s ease, box-shadow 0.3s ease;
}
.status-inline-dot--ready::before { background: #5ec9a4; box-shadow: 0 0 5px rgba(94,201,164,0.35); }
.status-inline-dot--loading::before { background: #e8a840; box-shadow: 0 0 5px rgba(232,168,64,0.35); animation: dot-pulse 1.6s ease-in-out infinite; }
.status-inline-dot--live::before { background: #d9a441; box-shadow: 0 0 5px rgba(217,164,65,0.35); }
.right-card-head-status {
  display: inline-flex; align-items: center; gap: 10px;
  flex-shrink: 0;
}
.answer-feedback { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 8px; color: rgba(232,228,219,.62); font-size: 11px; }
.answer-feedback button { border: 1px solid rgba(232,228,219,.2); border-radius: 999px; background: rgba(255,255,255,.04); color: rgba(255,250,242,.82); padding: 4px 7px; font-size: 11px; cursor: pointer; }
.answer-feedback button:hover, .answer-feedback button.active { border-color: rgba(94,201,164,.75); background: rgba(94,201,164,.14); color: #b8f1dd; }
.answer-feedback button:disabled { cursor: wait; opacity: .55; }
.feedback-reasons { display: flex; flex-basis: 100%; flex-wrap: wrap; align-items: center; gap: 6px; padding-top: 2px; }
.feedback-error { flex-basis: 100%; color: #ffb4a8; }
@keyframes dot-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
