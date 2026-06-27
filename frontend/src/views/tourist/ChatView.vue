<template>
  <section class="tourist-page">
    <div class="chat-layout">
      <section class="chat-panel panel-card">
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="chat-guide-avatar">
              <ThreeAvatar
                v-if="!avatarError"
                :preset="avatarConfig.modelKey"
                :emotion="avatar.currentEmotion.value"
                :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
                :speech-progress="speechProgress"
                :speech-sync-active="activeAudioSegments > 0"
                :viseme-timeline="visemeTimeline"
                @loaded="handleAvatarLoaded"
                @error="handleAvatarLoadError"
              />
              <AvatarDisplay
                v-else
                :state="avatarState"
                :emotion="avatar.currentEmotion.value"
              />
            </div>
            <div class="chat-guide-copy">
              <span class="guide-kicker">灵山随行讲解</span>
              <h2 class="section-title">灵山智慧导游</h2>
              <p class="section-subtitle">
                {{
                  interactionStore.breadcrumbs.length
                    ? interactionStore.breadcrumbs.join(" / ")
                    : "随时解答您的游览疑问，就像真人导游陪伴身边"
                }}
              </p>
            </div>
          </div>

          <div class="chat-header-actions">
            <el-button
              text
              :disabled="chatStore.streaming || speechListening || isRecording"
              @click="handleChangeMode"
            >
              更换问答模式
            </el-button>
            <el-tag size="small" type="info">{{ chatStore.statusText }}</el-tag>
          </div>
        </div>

        <div ref="messageListRef" class="message-list">
          <article
            v-for="(message, index) in chatStore.messages"
            :key="`${message.role}-${index}`"
            :class="['message-item', message.role]"
          >
            <strong class="message-speaker">{{ message.role === "user" ? "您" : GUIDE_PERSONA.name }}</strong>
            <div
              v-if="message.role === 'assistant'"
              class="answer-content"
              v-html="renderAnswer(message.content, index === chatStore.messages.length - 1)"
              @click="handleCitationClick"
            ></div>
            <p v-else>{{ message.content }}</p>
            <span
              v-if="message.role === 'assistant' && chatStore.streaming && index === chatStore.messages.length - 1 && message.content.length > 0"
              class="typing-cursor"
            >|</span>
          </article>
        </div>

        <div v-if="chatStore.followups.length" class="followup-panel" aria-label="快捷追问">
          <div class="followup-heading">
            <span>继续探索</span>
            <small>选择一个方向接着问</small>
          </div>
          <div class="followup-list">
            <button
              v-for="item in chatStore.followups"
              :key="item.query"
              type="button"
              :disabled="chatStore.streaming"
              @click="handleFollowup(item.query)"
            >
              <strong>{{ item.label }}</strong>
              <span>{{ item.query }}</span>
            </button>
          </div>
        </div>

        <div
          v-show="visionPanelOpen || visionFile || visionResult"
          class="vision-panel"
          aria-label="图片识别入口"
        >
          <div class="vision-heading">
            <div>
              <span>拍照识景</span>
              <small>选择一张景物照片，小灵会结合景区资料继续讲解。</small>
            </div>
            <el-button text @click="visionPanelOpen = false">收起</el-button>
          </div>

          <input
            ref="visionFileInputRef"
            class="vision-file-input"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            @change="handleVisionFileChange"
          />

          <div class="vision-actions">
            <el-button :disabled="visionAnalyzing || chatStore.streaming" @click="openVisionFilePicker">
              选择图片
            </el-button>
            <el-button
              type="primary"
              :loading="visionAnalyzing"
              :disabled="!visionFile || chatStore.streaming"
              @click="handleAnalyzeImage"
            >
              识别图片
            </el-button>
            <el-button v-if="visionResult || visionFile" :disabled="visionAnalyzing" @click="clearVisionState">
              清除
            </el-button>
          </div>

          <div v-if="visionFile" class="vision-file-card">
            <img v-if="visionPreviewUrl" :src="visionPreviewUrl" alt="待识别图片预览" />
            <div>
              <strong>{{ visionFile.name }}</strong>
              <span>{{ formatBytes(visionFile.size) }}</span>
            </div>
          </div>

          <el-alert
            v-if="visionError"
            class="vision-alert"
            type="error"
            :title="visionError"
            :closable="false"
          />

          <div v-if="visionResult" class="vision-result-card">
            <p class="vision-summary">{{ visionResult.scene_summary || "暂未识别出明确场景。" }}</p>
            <p v-if="visionResult.candidate_attractions?.length" class="vision-greeting">
              我看到这可能是{{ visionResult.candidate_attractions[0] }}，让我为您介绍它。
            </p>
            <div v-if="visionResult.candidate_attractions?.length" class="vision-tags">
              <span>可能是</span>
              <el-tag
                v-for="item in visionResult.candidate_attractions"
                :key="`attraction-${item}`"
                type="success"
              >
                {{ item }}
              </el-tag>
            </div>
            <div v-if="visionResult.visual_tags?.length" class="vision-tags">
              <span>画面特征</span>
              <el-tag v-for="item in visionResult.visual_tags" :key="`tag-${item}`">
                {{ item }}
              </el-tag>
            </div>
            <div class="vision-meta">
              <span>识别把握：{{ formatConfidence(visionResult.confidence) }}</span>
            </div>
            <div class="vision-query">
              <span>发现的景物特征</span>
              <div v-if="visionDisplayHints.length" class="vision-query-chips">
                <el-tag
                  v-for="item in visionDisplayHints"
                  :key="`hint-${item}`"
                  effect="plain"
                  type="warning"
                >
                  {{ item }}
                </el-tag>
              </div>
              <p v-else class="vision-query-note">暂时没有发现明确特征，仍可根据图片概述继续询问。</p>
              <small class="vision-query-note">这些结果只作为检索线索，最终讲解仍以景区资料为准。</small>
            </div>
            <el-button
              type="success"
              :disabled="chatStore.streaming || !visionResult.retrieval_query"
              @click="askFromImage"
            >
              请小灵讲讲这里
            </el-button>
          </div>
        </div>

        <div class="composer">
          <div class="composer-topline">
            <div class="explanation-mode">
              <span>讲解方式</span>
              <el-radio-group v-model="explanationLevel" size="small">
                <el-radio-button value="child">亲子游</el-radio-button>
                <el-radio-button value="adult">休闲游</el-radio-button>
                <el-radio-button value="expert">文化深度游</el-radio-button>
              </el-radio-group>
            </div>
            <span v-if="interactionStore.breadcrumbs.length" class="composer-context">
              {{ interactionStore.breadcrumbs.join(" / ") }}
            </span>
          </div>
          <el-input
            v-model="query"
            type="textarea"
            :rows="2"
            resize="none"
            placeholder="问我关于灵山的任何问题，比如：大佛有多高？"
            @keydown.enter.exact.prevent="handleSubmit"
          />
          <div v-if="speechListening" class="speech-listening" aria-live="polite">
            <span class="speech-pulse" aria-hidden="true"></span>
            <strong>正在聆听</strong>
            <span>{{ speechPreviewText || "请开始说话，识别文字会实时出现在输入框中。" }}</span>
          </div>
          <el-alert
            v-if="voiceErrorMessage"
            class="speech-alert"
            type="warning"
            :title="voiceErrorMessage"
            :closable="false"
            show-icon
          />
          <div class="composer-actions">
            <div class="secondary-actions">
              <el-button :disabled="chatStore.streaming" @click="toggleVisionPanel">
                拍照识景
              </el-button>
              <el-button
                v-if="voiceSupported"
                :type="speechListening || isRecording ? 'danger' : 'default'"
                :loading="transcribing"
                :disabled="chatStore.streaming || transcribing"
                @click="toggleRecording"
              >
                <template v-if="speechListening">结束语音</template>
                <template v-else-if="isRecording">结束录音（{{ durationSeconds }}s）</template>
                <template v-else>语音提问</template>
              </el-button>
            </div>
            <el-button
              type="primary"
              class="submit-button"
              :loading="chatStore.streaming"
              :disabled="speechListening || isRecording || transcribing"
              @click="handleSubmit"
            >
              发送问题
            </el-button>
          </div>
        </div>
      </section>

      <aside class="source-panel panel-card">
        <span class="source-kicker">景区资料</span>
        <h3 class="section-title">资料来源</h3>
        <p class="section-subtitle">所有回答均来自官方景区资料，点击数字可查看详情。</p>
        <el-empty v-if="chatStore.sources.length === 0" description="提问后这里会显示参考资料" />
        <ul v-else class="source-list">
          <li
            v-for="(item, index) in chatStore.sources"
            :key="`${item.title}-${index}`"
            :data-source-index="index"
            :class="{ 'source-highlight': sourceHighlightIndex === index }"
          >
            <h4>
              <span class="source-number">{{ index + 1 }}</span>
              {{ item.title }}
            </h4>
            <p>{{ item.snippet }}</p>
            <span class="source-meta">{{ item.source }}</span>
          </li>
        </ul>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, nextTick, watch } from "vue";
import { useRouter } from "vue-router";

import ThreeAvatar from "../../components/ThreeAvatar.vue";
import AvatarDisplay from "../../components/AvatarDisplay.vue";
import { useChatStore } from "../../stores/chat";
import { useInteractionStore } from "../../stores/interaction";
import { useRecorder } from "../../composables/useRecorder";
import { useSpeechRecognition } from "../../composables/useSpeechRecognition";
import { GUIDE_PERSONA, useAvatar } from "../../composables/useAvatar";
import { useAudioPlayer } from "../../composables/useAudioPlayer";
import { renderMarkdown } from "../../composables/useMarkdown";
import { transcribeAudio } from "../../api/voice";
import { analyzeImage } from "../../api/vision";

const router = useRouter();
const chatStore = useChatStore();
const interactionStore = useInteractionStore();
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
  start: startSpeechRecognition,
  stop: stopSpeechRecognition,
  abort: abortSpeechRecognition,
} = useSpeechRecognition();
const avatar = useAvatar();
const audioPlayer = useAudioPlayer();
const avatarState = avatar.currentState;
const avatarError = ref(false);

const STORAGE_KEY = "a5-avatar-config-v1";
const avatarConfig = ref({ modelKey: "hanfu" });
try {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw) {
    avatarConfig.value = { ...JSON.parse(raw), modelKey: "hanfu" };
  }
} catch {}

const query = ref("");
const explanationLevel = ref("adult");
const transcribing = ref(false);
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
const visemeTimeline = ref(null);
const activeAudioSegments = ref(0);
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const sourceHighlightIndex = ref(-1);
const sourceDrawerOpen = ref(false);
let greetingTimer = null;

const voiceSupported = computed(() => speechSupported.value || recorderSupported.value);
const speechPreviewText = computed(
  () => speechInterimText.value || speechFinalText.value,
);
const voiceErrorMessage = computed(
  () => getSpeechErrorMessage(speechError.value) || recorderError.value,
);

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
    s => s.evidence_id === `证据${evidenceId}`
  );
  if (index >= 0) {
    sourceHighlightIndex.value = index;
    nextTick(() => {
      document.querySelector(`[data-source-index="${index}"]`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      });
    });
    setTimeout(() => sourceHighlightIndex.value = -1, 2000);
  }
}

function toggleSourceDrawer() {
  sourceDrawerOpen.value = !sourceDrawerOpen.value;
}

function handleChangeMode() {
  if (chatStore.streaming || speechListening.value || isRecording.value) {
    return;
  }
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
    const msgs = chatStore.messages;
    return msgs.length > 0 ? msgs[msgs.length - 1].content : "";
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
  if (chatStore.messages.length === 0) {
    greetingTimer = window.setTimeout(() => {
      if (chatStore.messages.length === 0) {
        chatStore.messages.push({
          role: "assistant",
          content: GUIDE_PERSONA.greeting,
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
  audioPlayer.stop();
  abortSpeechRecognition();
  revokeVisionPreview();
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

function submitQuery(rawQuery) {
  const value = rawQuery.trim();
  if (!value || chatStore.streaming) {
    return;
  }
  const levelPrefix = {
    child: '请用小朋友能听懂的语言解释：',
    adult: '',
    expert: '请给出专业详细的解释：',
  }[explanationLevel.value];
  const finalQuery = levelPrefix + value;
  avatar.setState("thinking");
  try {
    chatStore.sendMessage(finalQuery, interactionStore.selectionPayload, {
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
          visemeTimeline.value = null;
        }
      },
      onSpeechProgress: (progress, elapsedMs, timeline) => {
        speechProgress.value = progress;
        visemeTimeline.value = timeline;
      },
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
      if (result && result.text) {
        query.value = result.text;
      }
    } catch {
      recorderError.value = "录音转写失败，请改用文字输入。";
    } finally {
      transcribing.value = false;
    }
    avatar.setState("idle");
    return;
  }

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
  submitQuery(limitChatQuery(prompt));
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
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
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
.tourist-page {
  display: grid;
  gap: 20px;
  animation: page-reveal 480ms ease-out both;
}

@keyframes page-reveal {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(300px, 0.85fr);
  gap: 20px;
  align-items: start;
}

.chat-panel,
.source-panel {
  padding: 24px;
}

.chat-panel {
  overflow: hidden;
}

.source-panel {
  position: sticky;
  top: 20px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--lingshan-line);
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 20px;
  min-width: 0;
}

.chat-header-actions {
  display: grid;
  gap: 10px;
  justify-items: end;
  flex-shrink: 0;
}

.chat-guide-avatar {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  width: 136px;
  height: 172px;
  flex: 0 0 136px;
  overflow: hidden;
  border: 1px solid var(--lingshan-line);
  border-radius: 16px 6px 16px 6px;
  background: linear-gradient(180deg, var(--lingshan-green-light), #fffdf8);
}

.chat-guide-avatar :deep(.three-wrapper),
.chat-guide-avatar :deep(.avatar-display) {
  width: 100%;
  height: 100%;
}

.chat-guide-avatar :deep(.three-wrapper) {
  min-height: 100%;
}

.chat-guide-copy {
  min-width: 0;
}

.chat-guide-copy .section-title {
  margin-bottom: 6px;
}

.guide-kicker,
.source-kicker {
  display: block;
  margin-bottom: 6px;
  color: var(--lingshan-gold-deep);
  font-family: "FangSong", "STFangsong", serif;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 220px;
  max-height: 480px;
  overflow-y: auto;
  margin: 24px 0;
  scroll-behavior: smooth;
}

.message-item {
  position: relative;
  width: min(92%, 760px);
  padding: 15px 17px;
  border-radius: 5px 16px 16px 16px;
  box-shadow: 0 5px 16px rgba(55, 71, 59, 0.05);
}

.message-item.user {
  align-self: flex-end;
  border-right: 3px solid var(--lingshan-gold);
  border-radius: 16px 5px 16px 16px;
  background: linear-gradient(135deg, #fff7e9, #fffdf8);
}

.message-item.assistant {
  align-self: flex-start;
  border-left: 3px solid var(--lingshan-green);
  background: var(--lingshan-green-light);
}

.message-speaker {
  color: var(--lingshan-green-deep);
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 15px;
}

.message-item p {
  margin: 8px 0 0;
  line-height: 1.7;
}

.typing-cursor {
  animation: blink 0.8s infinite;
  color: var(--lingshan-green-deep);
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.composer {
  display: grid;
  gap: 12px;
}

.composer-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.speech-listening {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(220, 38, 38, 0.18);
  border-radius: 12px;
  background: linear-gradient(135deg, #fff7ed, #fff 76%);
  color: #7f1d1d;
  font-size: 13px;
}

.speech-listening > span:last-child {
  color: #475569;
}

.speech-pulse {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #dc2626;
  box-shadow: 0 0 0 rgba(220, 38, 38, 0.36);
  animation: speech-pulse 1.35s ease-out infinite;
}

.speech-alert {
  margin: 0;
}

@keyframes speech-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.34);
  }
  70% {
    box-shadow: 0 0 0 9px rgba(220, 38, 38, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(220, 38, 38, 0);
  }
}

.vision-panel {
  display: grid;
  gap: 12px;
  margin: -4px 0 20px;
  padding: 16px;
  border: 1px solid rgba(102, 128, 107, 0.22);
  border-radius: 16px 6px 16px 6px;
  background:
    radial-gradient(circle at top left, rgba(184, 137, 79, 0.12), transparent 34%),
    linear-gradient(135deg, var(--lingshan-green-light), #fffdf8 72%);
}

.vision-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.vision-heading div {
  display: grid;
  gap: 4px;
}

.vision-heading span {
  color: var(--lingshan-green-deep);
  font-family: "STKaiti", "KaiTi", serif;
  font-weight: 700;
}

.vision-heading small {
  color: #64748b;
  line-height: 1.5;
}

.vision-file-input {
  display: none;
}

.vision-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.vision-file-card {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
}

.vision-file-card img {
  width: 88px;
  height: 64px;
  object-fit: cover;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(54, 88, 71, 0.14);
}

.vision-file-card div {
  display: grid;
  gap: 4px;
}

.vision-file-card span,
.vision-meta {
  color: #64748b;
  font-size: 13px;
}

.vision-alert {
  margin: 0;
}

.vision-result-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: inset 0 0 0 1px rgba(54, 88, 71, 0.08);
}

.vision-summary,
.vision-query-note {
  margin: 0;
  color: #334155;
  line-height: 1.65;
}

.vision-greeting {
  color: var(--lingshan-green-deep);
  font-weight: 500;
  margin: 8px 0;
}

.explanation-mode {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 10px;
  border-left: 3px solid var(--lingshan-gold);
  background: #f8f2e8;
  font-size: 13px;
}

.explanation-mode span {
  color: var(--lingshan-stone);
  font-weight: 700;
}

.explanation-mode :deep(.el-radio-button__inner) {
  padding: 8px 12px;
  font-size: 13px;
}

.vision-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.vision-tags > span,
.vision-query > span {
  color: var(--lingshan-green-deep);
  font-size: 13px;
  font-weight: 700;
}

.vision-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.vision-query {
  display: grid;
  gap: 6px;
  padding: 10px;
  border-radius: 12px;
  background: #f6f3eb;
}

.vision-query-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.vision-query-note {
  color: #64748b;
  font-size: 12px;
}

.followup-panel {
  display: grid;
  gap: 10px;
  margin: -8px 0 20px;
  padding: 14px;
  border: 1px solid rgba(184, 137, 79, 0.26);
  border-radius: 16px 6px 16px 6px;
  background: linear-gradient(135deg, #fbf3e5, #fffdf8 72%);
}

.followup-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  color: #92400e;
}

.followup-heading span {
  font-family: "STKaiti", "KaiTi", serif;
  font-weight: 700;
}

.followup-heading small {
  color: #8b7355;
}

.followup-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.followup-list button {
  display: grid;
  gap: 4px;
  padding: 11px 12px;
  border: 1px solid #f1d6a8;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.88);
  color: #543b24;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;
}

.followup-list button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--lingshan-gold);
  box-shadow: 0 8px 18px rgba(146, 64, 14, 0.1);
}

.followup-list button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.followup-list strong {
  color: #92400e;
  font-size: 13px;
}

.followup-list span {
  font-size: 12px;
  line-height: 1.45;
}

.composer-context {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 9px 12px;
  border-radius: 10px;
  background: var(--lingshan-green-light);
  color: var(--lingshan-green-deep);
  font-size: 13px;
}

.composer-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
}

.secondary-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.secondary-actions .el-button + .el-button {
  margin-left: 0;
}

.submit-button {
  min-width: 126px;
}

.source-list {
  list-style: none;
  padding: 0;
  margin: 20px 0 0;
  display: grid;
  gap: 12px;
}

.source-list li {
  padding: 16px;
  border: 1px solid transparent;
  border-radius: 14px 5px 14px 5px;
  background: #f6f3eb;
  transition: border-color 180ms ease, background 180ms ease, transform 180ms ease;
}

.source-list li:hover {
  border-color: rgba(184, 137, 79, 0.34);
  background: #fffaf0;
  transform: translateY(-1px);
}

.source-list h4 {
  display: flex;
  align-items: center;
  margin: 0 0 8px;
  color: var(--lingshan-ink);
}

.source-list p {
  margin: 0 0 8px;
  color: #334155;
  line-height: 1.6;
}

.source-number {
  display: inline-flex;
  flex: 0 0 22px;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-right: 8px;
  border-radius: 50%;
  background: var(--lingshan-gold-light);
  color: var(--lingshan-gold-deep);
  font-family: Georgia, serif;
  font-size: 12px;
  font-weight: 700;
}

.source-meta {
  color: var(--lingshan-stone);
  font-size: 13px;
}

@media (max-width: 980px) {
  .chat-layout {
    grid-template-columns: 1fr;
  }

  .source-panel {
    position: static;
    max-height: none;
  }
}

@media (max-width: 560px) {
  .chat-panel,
  .source-panel {
    padding: 18px;
  }

  .chat-header,
  .chat-header-left,
  .chat-header-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .chat-guide-avatar {
    width: 120px;
    height: 152px;
    flex-basis: 120px;
  }

  .message-item {
    width: 96%;
  }

  .composer-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .composer-actions .el-button {
    width: 100%;
    margin-left: 0;
  }

  .followup-list {
    grid-template-columns: 1fr;
  }

  .vision-file-card {
    align-items: flex-start;
  }
}
</style>
