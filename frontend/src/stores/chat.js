import { defineStore } from "pinia";

import { streamChat } from "../api/chat";
import { submitVisitorFeedback } from "../api/insights";
import { useAudioPlayer } from "../composables/useAudioPlayer";

const audioPlayer = useAudioPlayer();

const DEFAULT_STATUS_TEXT = "等待提问";
const STOPPED_STATUS_TEXT = "已停止输出";
const UPDATED_CONTEXT_STATUS_TEXT = "已更新游览方向";
const ANSWER_DONE_STATUS_TEXT = "回答完成";
const FALLBACK_STATUS_TEXT = "云端语音暂不可用，已保留文字回答";
const FALLBACK_DONE_STATUS_TEXT = "文字回答完成，语音暂不可用";
const OFFLINE_STATUS_TEXT = "暂时离线";
const GENERIC_ERROR_TEXT = "抱歉，导览服务暂时没有响应。请稍后再试，或换一个问题问问我。";

let activeStreamController = null;
let activeStreamToken = 0;
let lastFailedRequest = null;
const SESSION_STORAGE_KEY = "a5-chat-session-id";

export function getSessionId() {
  const fallbackId = `visitor-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  if (typeof sessionStorage === "undefined") return fallbackId;
  const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) return existing;
  const sessionId = globalThis.crypto?.randomUUID?.() || fallbackId;
  sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  return sessionId;
}

function isAbortError(error) {
  return error?.name === "AbortError";
}

export const useChatStore = defineStore("chat", {
  state: () => ({
    messages: [],
    sources: [],
    followups: [],
    conversationContext: null,
    emotionAnalysis: null,
    statusText: DEFAULT_STATUS_TEXT,
    streaming: false,
    voiceFallback: false,
    errorMessage: "",
    userStopped: false,
  }),
  actions: {
    resetConversationContext() {
      this.conversationContext = null;
      this.followups = [];
      this.sources = [];
      this.emotionAnalysis = null;
      this.statusText = DEFAULT_STATUS_TEXT;
    },
    resetSession() {
      this.stopOutput();
      this.messages = [];
      this.errorMessage = "";
      this.userStopped = false;
      lastFailedRequest = null;
      this.resetConversationContext();
    },
    stopOutput() {
      if (this.streaming) {
        this.userStopped = true;
      }
      activeStreamToken += 1;
      if (activeStreamController) {
        activeStreamController.abort();
        activeStreamController = null;
      }
      audioPlayer.stop();
      this.streaming = false;
      this.voiceFallback = false;
      if (this.userStopped) {
        this.statusText = STOPPED_STATUS_TEXT;
      }
    },
    async sendMessage(query, selection = null, options = {}) {
      if (!query.trim()) {
        return;
      }

      this.stopOutput();
      this.errorMessage = "";
      this.userStopped = false;
      const requestToken = activeStreamToken;
      const streamController = new AbortController();
      activeStreamController = streamController;
      const isCurrentRequest = () =>
        requestToken === activeStreamToken && activeStreamController === streamController;
      let pcmStarted = false;
      let receivedDone = false;

      const assistantMessage = {
        role: "assistant",
        content: "",
      };

      this.messages.push({ role: "user", content: options.displayQuery || query });
      this.messages.push(assistantMessage);
      this.sources = [];
      this.emotionAnalysis = null;
      this.followups = [];
      this.streaming = true;
      this.voiceFallback = false;
      options.onThinking?.();

      try {
        await streamChat(
          {
            query,
            session_id: getSessionId(),
            input_mode: options.inputMode || "text",
            text_only: false,
            persona: options.ttsConfig?.persona || null,
            tts_voice: options.ttsConfig?.voiceType || null,
            tts_rate: options.ttsConfig?.speechRate || 100,
            tts_volume: options.ttsConfig?.volume ?? 80,
            selection,
            context: this.conversationContext,
            vision_context: options.visionContext || null,
            emotion_context: options.emotionContext || null,
          },
          {
            context: ({ selection: resolvedSelection, conversation_context: conversationContext, warnings = [] }) => {
              if (!isCurrentRequest()) {
                return;
              }
              this.conversationContext = conversationContext || null;
              options.onContext?.(resolvedSelection);
              if (warnings.length) {
                this.statusText = UPDATED_CONTEXT_STATUS_TEXT;
              }
            },
            status: ({ text }) => {
              if (!isCurrentRequest()) {
                return;
              }
              this.statusText = text;
            },
            sources: ({ docs }) => {
              if (!isCurrentRequest()) {
                return;
              }
              this.sources = docs;
            },
            text_chunk: ({ token }) => {
              if (!isCurrentRequest()) {
                return;
              }
              assistantMessage.content += token;
            },
            text: ({ text, is_complete }) => {
              if (!isCurrentRequest()) {
                return;
              }
              assistantMessage.content = text;
              if (is_complete) {
                this.statusText = ANSWER_DONE_STATUS_TEXT;
              }
            },
            audio: async ({ base64, duration_ms, text, viseme_timeline, provider }) => {
              if (!isCurrentRequest()) {
                return;
              }
              const isFallback = provider === "bailian_unavailable" || provider === "stub";
              const hasAudio = typeof base64 === "string" && base64.trim().length > 0;
              if (isFallback || !hasAudio) {
                this.voiceFallback = true;
                this.statusText = FALLBACK_STATUS_TEXT;
                options.onAudioUnavailable?.({ provider });
                return;
              }
              options.onAudioStart?.();
              await audioPlayer.enqueue(
                base64,
                duration_ms,
                () => options.onAudioEnded?.(),
                text || "",
                (progress, elapsedMs, actualDurationMs) =>
                  options.onSpeechProgress?.(
                    progress,
                    elapsedMs,
                    viseme_timeline || null,
                    actualDurationMs,
                  ),
                {
                  rate: (options.ttsConfig?.speechRate || 100) / 100,
                  volume: (options.ttsConfig?.volume ?? 80) / 100,
                  allowBrowserSpeech: false,
                  onMode: (mode) => {
                    if (mode === "silent") {
                      this.voiceFallback = true;
                      this.statusText = FALLBACK_STATUS_TEXT;
                    }
                  },
                },
              );
            },
            audio_chunk: ({ base64, viseme_timeline, sample_rate, channels, bits }) => {
              if (!isCurrentRequest()) {
                return;
              }
              // 流式 PCM 音频块
              if (base64) {
                if (!audioPlayer.isPCMStreaming.value) {
                  pcmStarted = true;
                  options.onAudioStart?.();
                  audioPlayer.startPCMStream(
                    (progress, elapsedMs, durationMs, timeline) =>
                      options.onSpeechProgress?.(progress, elapsedMs, timeline, durationMs),
                    () => {
                      options.onAudioEnded?.();
                      audioPlayer.flush();
                    },
                  );
                }
                audioPlayer.feedPCMChunk(base64, sample_rate || 24000, channels || 1, bits || 16);
              }
              // 字级别时间戳 → viseme 时间线
              if (viseme_timeline) {
                audioPlayer.updatePCMVisemeTimeline(viseme_timeline);
              }
            },
            avatar: (payload = {}) => {
              if (!isCurrentRequest()) {
                return;
              }
              const { viseme_text, emotion, action } = payload;
              options.onAvatar?.({ viseme_text, emotion, action });
            },
            emotion: (payload) => {
              if (!isCurrentRequest()) {
                return;
              }
              this.emotionAnalysis = payload || null;
              options.onEmotion?.(payload);
            },
            followups: ({ items = [] }) => {
              if (!isCurrentRequest()) {
                return;
              }
              this.followups = items.filter(
                (item) => typeof item?.label === "string" && typeof item?.query === "string",
              );
            },
            error: ({ message } = {}) => {
              throw new Error(message || "导览服务处理回答时发生错误。");
            },
            done: ({ chat_log_id: chatLogId } = {}) => {
              if (!isCurrentRequest()) {
                return;
              }
              receivedDone = true;
              // 结束 PCM 流（如果在用流式模式）
              if (pcmStarted || audioPlayer.isPCMStreaming.value) {
                audioPlayer.endPCMStream();
                pcmStarted = false;
              }
              assistantMessage.chatLogId = Number(chatLogId) || null;
              this.streaming = false;
              if (!this.userStopped) {
                this.statusText = this.voiceFallback
                  ? FALLBACK_DONE_STATUS_TEXT
                  : DEFAULT_STATUS_TEXT;
              }
              lastFailedRequest = null;
            },
          },
          {
            signal: streamController.signal,
          },
        );
        if (isCurrentRequest() && !receivedDone) {
          if (!assistantMessage.content.trim()) {
            throw new Error("回答连接提前结束，未收到有效内容。");
          }
          if (pcmStarted || audioPlayer.isPCMStreaming.value) {
            audioPlayer.endPCMStream();
            pcmStarted = false;
          }
          this.streaming = false;
          this.statusText = this.voiceFallback
            ? FALLBACK_DONE_STATUS_TEXT
            : ANSWER_DONE_STATUS_TEXT;
          lastFailedRequest = null;
        }
      } catch (error) {
        if (isAbortError(error)) {
          if (this.userStopped) {
            this.statusText = STOPPED_STATUS_TEXT;
          }
          return;
        }
        if (pcmStarted || audioPlayer.isPCMStreaming.value) {
          audioPlayer.endPCMStream();
          pcmStarted = false;
        }
        assistantMessage.content = assistantMessage.content
          ? `${assistantMessage.content}\n\n（回答传输中断，可点击重试。）`
          : GENERIC_ERROR_TEXT;
        this.streaming = false;
        this.statusText = OFFLINE_STATUS_TEXT;
        this.errorMessage = error?.message || "导览服务暂时不可用，请稍后重试。";
        lastFailedRequest = { query, selection, options };
      } finally {
        if (activeStreamController === streamController) {
          activeStreamController = null;
        }
      }
    },
    async submitFeedback(message, rating, reasonCode = null) {
      if (!message || message.feedbackSubmitting) return;
      if (!message.chatLogId) {
        message.feedbackError = "回答记录尚未完成，请稍后再评价";
        return;
      }
      message.feedbackSubmitting = true;
      message.feedbackError = "";
      try {
        await submitVisitorFeedback({
          chat_log_id: message.chatLogId,
          session_id: getSessionId(),
          rating,
          reason_code: reasonCode,
        });
        message.feedbackRating = rating;
        message.feedbackPendingRating = null;
      } catch (error) {
        message.feedbackError = error?.response?.data?.detail || "评价提交失败，请稍后重试";
      } finally {
        message.feedbackSubmitting = false;
      }
    },
    async retryLastMessage() {
      if (!lastFailedRequest || this.streaming) return;
      const request = lastFailedRequest;
      if (this.messages.length >= 2) this.messages.splice(-2, 2);
      await this.sendMessage(request.query, request.selection, request.options);
    },
  },
});
