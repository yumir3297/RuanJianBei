<template>
  <section class="tourist-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>

    <header class="tourist-top">
      <span class="tourist-brand">灵山智慧导览</span>
      <div class="tourist-top-right">
        <el-tag size="small" effect="plain">{{ explanationLevelLabel }}</el-tag>
        <el-tag size="small" type="info">{{ chatStore.statusText }}</el-tag>
        <el-button
          text
          :disabled="chatStore.streaming || speechListening || isRecording"
          @click="handleChangeMode"
        >
          切换讲解方式
        </el-button>
      </div>
    </header>

    <div class="tourist-stage">
      <aside class="chat-float left-float">
        <div class="float-head">
          <span>实时对话</span>
          <small>
            {{
              interactionStore.breadcrumbs.length
                ? interactionStore.breadcrumbs.join(" / ")
                : "我会跟随你的节奏讲解灵山景区"
            }}
          </small>
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
              v-if="
                message.role === 'assistant'
                && chatStore.streaming
                && index === chatStore.messages.length - 1
                && message.content.length > 0
              "
              class="typing-cursor"
            >|</span>
          </article>
        </div>

        <div v-if="chatStore.followups.length" class="followup-panel" aria-label="快捷追问">
          <div class="followup-heading">
            <span>继续探索</span>
            <small>选一个方向继续提问</small>
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
      </aside>

      <div class="chat-center">
        <div class="avatar-halo halo-outer"></div>
        <div class="avatar-halo halo-inner"></div>
        <div class="avatar-stage">
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
        <div class="center-caption">
          <span class="caption-kicker">数字导览中</span>
          <p>
            {{
              interactionStore.breadcrumbs.length
                ? interactionStore.breadcrumbs.join(" / ")
                : "随时问我关于灵山的路线、典故和景点"
            }}
          </p>
        </div>
      </div>

      <aside class="chat-float right-float">
        <div class="float-head">
          <span>快捷操作</span>
          <small>选择提问方向，或打开识景与资料面板</small>
        </div>

        <div class="quick-section">
          <button
            v-for="question in quickQuestions"
            :key="question"
            type="button"
            :disabled="chatStore.streaming"
            @click="handleQuickQuestion(question)"
          >
            {{ question }}
          </button>
        </div>

        <div class="explanation-card">
          <span class="card-label">讲解方式</span>
          <el-radio-group v-model="explanationLevel" size="small">
            <el-radio-button value="child">亲子游</el-radio-button>
            <el-radio-button value="adult">休闲游</el-radio-button>
            <el-radio-button value="expert">文化深度游</el-radio-button>
          </el-radio-group>
        </div>

        <div class="action-group">
          <button type="button" class="action-chip" @click="toggleVisionPanel">
            拍照识景
          </button>
          <button
            type="button"
            :class="['action-chip', { active: sourceDrawerOpen }]"
            @click="toggleSourceDrawer"
          >
            资料来源
            <em v-if="chatStore.sources.length">{{ chatStore.sources.length }}</em>
          </button>
        </div>
      </aside>
    </div>

    <section
      v-show="visionPanelOpen || visionFile || visionResult"
      class="overlay-panel vision-drawer"
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
          我看到这可能是 {{ visionResult.candidate_attractions[0] }}，让我为您介绍它。
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
          <p v-else class="vision-query-note">暂时没有发现明确特征，仍可根据图片概述继续提问。</p>
          <small class="vision-query-note">这些结果仅作为检索线索，最终讲解仍以景区资料为准。</small>
        </div>
        <el-button
          type="success"
          :disabled="chatStore.streaming || !visionResult.retrieval_query"
          @click="askFromImage"
        >
          请小灵讲讲这里
        </el-button>
      </div>
    </section>

    <aside
      v-show="sourceDrawerOpen || sourceHighlightIndex >= 0"
      class="overlay-panel source-drawer"
      aria-label="资料来源"
    >
      <div class="drawer-head">
        <div>
          <span>资料来源</span>
          <small>所有回答均来自景区官方资料，点击引文编号可高亮定位。</small>
        </div>
        <el-button text @click="sourceDrawerOpen = false">收起</el-button>
      </div>

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

    <div class="tourist-input-wrap">
      <div class="tourist-input-bar">
        <button type="button" class="input-chip" @click="toggleVisionPanel">
          拍照识景
        </button>

        <div class="input-main">
          <div class="input-topline">
            <span>
              {{
                interactionStore.breadcrumbs.length
                  ? interactionStore.breadcrumbs.join(" / ")
                  : "导览助手已准备好"
              }}
            </span>
            <span v-if="speechListening">{{ speechPreviewText || "正在聆听..." }}</span>
          </div>

          <el-input
            v-model="query"
            type="textarea"
            :rows="2"
            resize="none"
            placeholder="问我关于灵山的路线、景点和典故，例如：灵山大佛有多高？"
            @keydown.enter.exact.prevent="handleSubmit"
          />
        </div>

        <button
          type="button"
          class="send-btn"
          :disabled="chatStore.streaming || speechListening || isRecording || transcribing"
          @click="handleSubmit"
        >
          {{ chatStore.streaming ? "发送中" : "发送" }}
        </button>

        <button
          v-if="voiceSupported"
          type="button"
          :class="['voice-btn', { recording: speechListening || isRecording }]"
          :disabled="chatStore.streaming || transcribing"
          @click="toggleRecording"
        >
          <template v-if="speechListening">结束语音</template>
          <template v-else-if="isRecording">结束录音 {{ durationSeconds }}s</template>
          <template v-else>语音提问</template>
        </button>
      </div>

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
import { GUIDE_PERSONA, useAvatar } from "../../composables/useAvatar";
import { useChatStore } from "../../stores/chat";
import { useInteractionStore } from "../../stores/interaction";

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
const GUIDE_STYLE_STORAGE_KEY = "a5-pending-guide-style-v1";
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
const sourceHighlightIndex = ref(-1);
const sourceDrawerOpen = ref(false);
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const scenicBgUrl = "var(--lingshan-scenic-bg)";
const quickQuestions = [
  "灵山大佛有多高？",
  "推荐游览路线是什么？",
  "这里有什么代表性的文化典故？",
  "附近适合拍照的景点有哪些？",
];
let greetingTimer = null;

const voiceSupported = computed(() => speechSupported.value || recorderSupported.value);
const speechPreviewText = computed(() => speechInterimText.value || speechFinalText.value);
const voiceErrorMessage = computed(
  () => getSpeechErrorMessage(speechError.value) || recorderError.value,
);
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
    sourceDrawerOpen.value = true;
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

function handleQuickQuestion(question) {
  submitQuery(question);
}

function submitQuery(rawQuery) {
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
      onSpeechProgress: (progress, _elapsedMs, timeline) => {
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
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  padding: 16px 20px 20px;
  overflow: hidden;
  background: var(--lingshan-paper);
}

.scenic-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.scenic-bg-img {
  position: absolute;
  inset: 0;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  filter: blur(6px) saturate(0.5) brightness(0.42);
  transform: scale(1.04);
}

.scenic-bg-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 52%, rgba(196, 155, 76, 0.12), transparent 24%),
    radial-gradient(
      ellipse 65% 52% at 50% 56%,
      transparent 0%,
      rgba(27, 46, 37, 0.42) 68%,
      rgba(15, 25, 18, 0.7) 100%
    );
}

.tourist-top {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.tourist-brand {
  color: rgba(255, 255, 255, 0.9);
  font-family: "STKaiti", "KaiTi", "STSong", serif;
  font-size: 18px;
  letter-spacing: 0.16em;
}

.tourist-top-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.tourist-stage {
  position: relative;
  z-index: 10;
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(270px, 320px) minmax(0, 1fr) minmax(240px, 280px);
  align-items: center;
  gap: 18px;
}

.chat-float {
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-self: center;
  max-height: min(62vh, 700px);
  padding: 18px 16px;
  border: 1px solid rgba(233, 240, 235, 0.16);
  border-radius: 20px;
  background: rgba(247, 244, 237, 0.16);
  box-shadow: 0 22px 60px rgba(10, 18, 14, 0.2);
  backdrop-filter: blur(18px);
}

.float-head {
  display: grid;
  gap: 6px;
}

.float-head span,
.drawer-head span,
.vision-heading span,
.caption-kicker,
.card-label {
  color: #f8e7bb;
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.float-head small,
.drawer-head small,
.vision-heading small {
  color: rgba(240, 242, 236, 0.78);
  line-height: 1.55;
}

.message-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
  scroll-behavior: smooth;
}

.message-item {
  position: relative;
  width: 100%;
  max-width: 100%;
  padding: 13px 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  box-shadow: 0 8px 20px rgba(11, 17, 13, 0.12);
}

.message-item.user {
  align-self: flex-end;
  background: rgba(255, 248, 232, 0.9);
  border-right: 3px solid var(--lingshan-gold);
  color: #4b3a21;
}

.message-item.assistant {
  align-self: flex-start;
  background: rgba(234, 240, 235, 0.94);
  border-left: 3px solid var(--lingshan-green);
}

.message-speaker {
  color: var(--lingshan-green-deep);
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 14px;
}

.message-item p {
  margin: 8px 0 0;
  line-height: 1.68;
}

.typing-cursor {
  animation: blink 0.8s infinite;
  color: var(--lingshan-green-deep);
  font-weight: 700;
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0;
  }
}

.chat-center {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  height: 100%;
  padding: 34px 0 86px;
}

.avatar-halo {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  border-radius: 50%;
  pointer-events: none;
}

.halo-outer {
  bottom: 20%;
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(196, 155, 76, 0.18) 0%, transparent 70%);
  filter: blur(4px);
}

.halo-inner {
  bottom: 25%;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.12) 0%, transparent 72%);
}

.avatar-stage {
  position: relative;
  z-index: 2;
  width: min(360px, 36vw);
  height: min(580px, 66vh);
  min-height: 340px;
}

.avatar-stage :deep(.three-wrapper),
.avatar-stage :deep(.avatar-display) {
  width: 100%;
  height: 100%;
}

.center-caption {
  position: relative;
  z-index: 2;
  display: grid;
  gap: 8px;
  margin-top: 10px;
  text-align: center;
}

.center-caption p {
  margin: 0;
  color: rgba(255, 255, 255, 0.82);
  font-family: "STKaiti", "KaiTi", serif;
  font-size: 16px;
  letter-spacing: 0.06em;
}

.quick-section,
.action-group,
.explanation-card {
  display: grid;
  gap: 10px;
}

.quick-section button,
.action-chip {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid rgba(248, 231, 187, 0.2);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.quick-section button:hover:not(:disabled),
.action-chip:hover {
  transform: translateY(-1px);
  border-color: rgba(248, 231, 187, 0.4);
  background: rgba(255, 255, 255, 0.14);
}

.quick-section button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.explanation-card {
  padding: 14px 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(248, 231, 187, 0.16);
}

.explanation-card :deep(.el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.explanation-card :deep(.el-radio-button__inner) {
  min-width: 88px;
  padding: 8px 12px;
  border-radius: 999px;
}

.action-chip {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.action-chip em {
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(248, 231, 187, 0.18);
  color: #f8e7bb;
  font-style: normal;
  font-size: 12px;
  line-height: 22px;
  text-align: center;
}

.action-chip.active {
  border-color: rgba(248, 231, 187, 0.5);
  background: rgba(255, 255, 255, 0.16);
}

.overlay-panel {
  position: absolute;
  z-index: 30;
  padding: 16px;
  border: 1px solid rgba(233, 240, 235, 0.18);
  border-radius: 20px;
  background: rgba(17, 28, 22, 0.78);
  box-shadow: 0 22px 60px rgba(4, 8, 6, 0.35);
  backdrop-filter: blur(18px);
}

.vision-drawer {
  right: 20px;
  bottom: 126px;
  width: min(440px, calc(100vw - 40px));
  max-height: min(62vh, 640px);
  overflow-y: auto;
}

.source-drawer {
  left: 20px;
  bottom: 126px;
  width: min(360px, calc(100vw - 40px));
  max-height: min(62vh, 620px);
  overflow-y: auto;
}

.drawer-head,
.vision-heading {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.drawer-head div,
.vision-heading div {
  display: grid;
  gap: 4px;
}

.vision-file-input {
  display: none;
}

.vision-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.vision-file-card {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 14px;
  padding: 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
}

.vision-file-card img {
  width: 88px;
  height: 64px;
  object-fit: cover;
  border-radius: 12px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.18);
}

.vision-file-card div {
  display: grid;
  gap: 4px;
}

.vision-file-card strong,
.vision-summary,
.vision-greeting,
.source-list h4,
.source-list p {
  color: rgba(255, 255, 255, 0.92);
}

.vision-file-card span,
.vision-meta,
.vision-query-note,
.source-meta {
  color: rgba(240, 242, 236, 0.72);
  font-size: 13px;
}

.vision-alert,
.speech-alert {
  margin: 0;
}

.vision-result-card {
  display: grid;
  gap: 12px;
  margin-top: 14px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 0 0 1px rgba(248, 231, 187, 0.08);
}

.vision-summary,
.vision-query-note {
  margin: 0;
  line-height: 1.65;
}

.vision-greeting {
  margin: 0;
  font-weight: 500;
}

.vision-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.vision-tags > span,
.vision-query > span {
  color: #f8e7bb;
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
  background: rgba(255, 255, 255, 0.06);
}

.vision-query-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.followup-panel {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid rgba(248, 231, 187, 0.18);
  border-radius: 16px;
  background: rgba(255, 248, 232, 0.08);
}

.followup-heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  color: #f8e7bb;
}

.followup-heading span {
  font-family: "STKaiti", "KaiTi", serif;
  font-weight: 700;
}

.followup-heading small {
  color: rgba(240, 242, 236, 0.7);
}

.followup-list {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.followup-list button {
  display: grid;
  gap: 4px;
  padding: 11px 12px;
  border: 1px solid rgba(248, 231, 187, 0.18);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.88);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.followup-list button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(248, 231, 187, 0.38);
  background: rgba(255, 255, 255, 0.14);
}

.followup-list button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.followup-list strong {
  color: #f8e7bb;
  font-size: 13px;
}

.followup-list span {
  font-size: 12px;
  line-height: 1.45;
}

.source-list {
  list-style: none;
  padding: 0;
  margin: 18px 0 0;
  display: grid;
  gap: 12px;
}

.source-list li {
  padding: 14px;
  border: 1px solid rgba(248, 231, 187, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  transition: border-color 180ms ease, background 180ms ease, transform 180ms ease;
}

.source-list li:hover {
  border-color: rgba(248, 231, 187, 0.24);
  background: rgba(255, 255, 255, 0.1);
  transform: translateY(-1px);
}

.source-list h4 {
  display: flex;
  align-items: center;
  margin: 0 0 8px;
}

.source-list p {
  margin: 0 0 8px;
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
  background: rgba(248, 231, 187, 0.18);
  color: #f8e7bb;
  font-family: Georgia, serif;
  font-size: 12px;
  font-weight: 700;
}

.tourist-input-wrap {
  position: relative;
  z-index: 20;
  display: grid;
  gap: 10px;
}

.tourist-input-bar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(233, 240, 235, 0.16);
  border-radius: 24px;
  background: rgba(247, 244, 237, 0.16);
  box-shadow: 0 18px 40px rgba(10, 18, 14, 0.2);
  backdrop-filter: blur(18px);
}

.input-chip,
.send-btn {
  flex-shrink: 0;
  height: 46px;
  padding: 0 18px;
  border: 1px solid rgba(248, 231, 187, 0.2);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.92);
  font: inherit;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, opacity 0.18s ease;
}

.input-chip:hover,
.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(248, 231, 187, 0.4);
  background: rgba(255, 255, 255, 0.14);
}

.send-btn:disabled,
.voice-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.input-main {
  flex: 1;
  min-width: 0;
  display: grid;
  gap: 8px;
}

.input-topline {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: rgba(240, 242, 236, 0.76);
  font-size: 12px;
}

.input-main :deep(.el-textarea__inner) {
  min-height: 56px !important;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(248, 231, 187, 0.16);
  background: rgba(255, 255, 255, 0.84);
  color: var(--lingshan-ink);
  box-shadow: none;
}

.input-main :deep(.el-textarea__inner:focus) {
  border-color: var(--lingshan-accent);
}

.voice-btn {
  flex-shrink: 0;
  height: 50px;
  padding: 0 20px;
  border: 2px solid rgba(248, 231, 187, 0.74);
  border-radius: 999px;
  background: var(--lingshan-primary);
  color: #fff;
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 0 22px rgba(196, 155, 76, 0.26);
  animation: voice-pulse 2.5s ease-in-out infinite;
  transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
}

.voice-btn:hover:not(:disabled) {
  transform: scale(1.03);
  box-shadow: 0 0 30px rgba(196, 155, 76, 0.42);
  filter: brightness(1.05);
}

.voice-btn.recording {
  background: #a3412f;
  border-color: #f0b49b;
  animation: recording-pulse 1s ease-in-out infinite;
}

@keyframes voice-pulse {
  0%,
  100% {
    box-shadow: 0 0 20px rgba(196, 155, 76, 0.24);
  }

  50% {
    box-shadow: 0 0 36px rgba(196, 155, 76, 0.44);
  }
}

@keyframes recording-pulse {
  0%,
  100% {
    box-shadow: 0 0 18px rgba(163, 65, 47, 0.28);
  }

  50% {
    box-shadow: 0 0 34px rgba(163, 65, 47, 0.5);
  }
}

.speech-listening {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(240, 180, 155, 0.22);
  border-radius: 14px;
  background: rgba(255, 244, 236, 0.9);
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

@media (max-width: 1180px) {
  .tourist-page {
    overflow-y: auto;
  }

  .tourist-stage {
    grid-template-columns: 1fr;
    gap: 16px;
    padding: 8px 0 16px;
  }

  .chat-center {
    order: 1;
    min-height: 48vh;
    padding: 18px 0 16px;
  }

  .left-float {
    order: 2;
  }

  .right-float {
    order: 3;
  }

  .chat-float {
    max-height: none;
  }

  .avatar-stage {
    width: min(320px, 64vw);
    height: min(500px, 56vh);
  }

  .vision-drawer,
  .source-drawer {
    left: 20px;
    right: 20px;
    width: auto;
  }
}

@media (max-width: 720px) {
  .tourist-page {
    padding: 14px;
  }

  .tourist-top,
  .tourist-top-right,
  .tourist-input-bar {
    align-items: stretch;
    flex-direction: column;
  }

  .tourist-top-right {
    justify-content: flex-start;
  }

  .tourist-brand {
    font-size: 16px;
  }

  .chat-float,
  .overlay-panel {
    padding: 14px;
  }

  .avatar-stage {
    width: min(280px, 72vw);
    height: min(430px, 48vh);
    min-height: 280px;
  }

  .center-caption p {
    font-size: 15px;
  }

  .vision-drawer,
  .source-drawer {
    left: 14px;
    right: 14px;
    bottom: 96px;
  }

  .input-chip,
  .send-btn,
  .voice-btn {
    width: 100%;
  }

  .input-topline {
    flex-direction: column;
  }
}

@media (prefers-reduced-motion: reduce) {
  .voice-btn {
    animation: none;
  }
}
</style>
