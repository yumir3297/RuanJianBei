import { defineStore } from "pinia";

import { deleteVisitorMemory, streamChat } from "../api/chat";
import { submitVisitorFeedback } from "../api/insights";
import { useAudioPlayer } from "../composables/useAudioPlayer";
import { createChatMetrics, rememberChatMetrics } from "../utils/chatMetrics";

const audioPlayer = useAudioPlayer();

const DEFAULT_STATUS_TEXT = "等待提问";
const STOPPED_STATUS_TEXT = "已停止输出";
const UPDATED_CONTEXT_STATUS_TEXT = "已更新游览方向";
const ANSWER_DONE_STATUS_TEXT = "回答完成";
const FALLBACK_STATUS_TEXT = "云端语音暂不可用，已保留文字回答";
const FALLBACK_DONE_STATUS_TEXT = "文字回答完成，语音暂不可用";
const INCOMPLETE_STATUS_TEXT = "讲解未完成";
const GENERIC_ERROR_TEXT = "抱歉，导览服务暂时没有响应。请稍后再试，或换一个问题问问我。";

let activeStreamController = null;
let activeStreamToken = 0;
let activePlaybackSession = null;
let activeFlushPending = null;
let lastFailedRequest = null;
const SESSION_STORAGE_KEY = "a5-chat-session-id";
const VISITOR_STORAGE_KEY = "a5-visitor-id";

/**
 * 稳定的匿名游客标识，存在 localStorage（跨会话保留）。
 * session_id 仍然只存活在 sessionStorage，两者用途不同：
 * session_id 标识"这一次游览"，visitor_id 标识"这个人"。
 */
export function getVisitorId() {
  const fallbackId = `visitor-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  if (typeof localStorage === "undefined") return fallbackId;
  try {
    const existing = localStorage.getItem(VISITOR_STORAGE_KEY);
    // 长度上限与后端 ChatRequest.visitor_id 的 max_length=64 对齐：
    // 脏数据若超长会让整个 /chat/stream 请求 422，宁可重发一个新标识。
    if (existing && existing.length <= 64) return existing;
    const visitorId = globalThis.crypto?.randomUUID?.() || fallbackId;
    localStorage.setItem(VISITOR_STORAGE_KEY, visitorId);
    return visitorId;
  } catch {
    // 无痕模式等场景 localStorage 会抛异常，降级为内存 id，不影响聊天
    return fallbackId;
  }
}

export function clearVisitorMemory() {
  try {
    localStorage.removeItem(VISITOR_STORAGE_KEY);
  } catch {
    // 忽略：清理失败不应阻断聊天
  }
}

/**
 * 隐私入口：先清服务端记忆，再丢掉本地标识。
 * 服务端不可用时也要清掉本地标识——否则用户以为清干净了、实际仍会被认出来。
 */
export async function clearVisitorMemoryEverywhere() {
  const existing = (() => {
    try {
      return localStorage.getItem(VISITOR_STORAGE_KEY);
    } catch {
      return null;
    }
  })();
  let deleted = 0;
  if (existing) {
    try {
      ({ deleted } = await deleteVisitorMemory(existing));
    } catch {
      // 服务端清除失败不阻断本地清理
    }
  }
  clearVisitorMemory();
  return deleted ?? 0;
}

export function getSessionId() {
  const fallbackId = `visitor-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  if (typeof sessionStorage === "undefined") return fallbackId;
  try {
    const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
    const sessionId = globalThis.crypto?.randomUUID?.() || fallbackId;
    sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    return sessionId;
  } catch {
    return fallbackId;
  }
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
    // 逐字字幕时间轴：[{text, begin_time, end_time, sentence_index}]，整段累计毫秒
    subtitleWords: [],
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
      activeFlushPending?.();
      activeFlushPending = null;
      if (this.streaming) {
        this.userStopped = true;
        const currentMessage = this.messages.at(-1);
        if (currentMessage?.role === "assistant") currentMessage.completion = "stopped";
      }
      activeStreamToken += 1;
      if (activeStreamController) {
        activeStreamController.abort();
        activeStreamController = null;
      }
      if (activePlaybackSession) audioPlayer.stop(activePlaybackSession.id, "chat-stopped");
      activePlaybackSession = null;
      this.subtitleWords = [];
      this.streaming = false;
      this.voiceFallback = false;
      if (this.userStopped) {
        this.statusText = STOPPED_STATUS_TEXT;
      }
    },
    clearSubtitleWords() {
      this.subtitleWords = [];
    },
    async sendMessage(query, selection = null, options = {}) {
      if (!query.trim()) {
        return;
      }

      this.stopOutput();
      this.errorMessage = "";
      this.userStopped = false;
      const requestToken = activeStreamToken;
      const metrics = createChatMetrics();
      const streamController = new AbortController();
      activeStreamController = streamController;
      const isCurrentRequest = () =>
        requestToken === activeStreamToken && activeStreamController === streamController;
      const isCurrentGeneration = () => requestToken === activeStreamToken;
      const playbackSession = audioPlayer.claimPlayback("chat", (reason) => {
        options.onPlaybackStopped?.();
        if (!isCurrentGeneration()) return;
        activePlaybackSession = null;
        // Losing audio support must preserve the text stream and retry state.
        if (reason === "unavailable" || reason === "stream-error") return;
        flushPendingText();
        if (this.streaming) assistantMessage.completion = "stopped";
        activeStreamToken += 1;
        streamController.abort();
        if (activeStreamController === streamController) activeStreamController = null;
        this.subtitleWords = [];
        this.streaming = false;
        this.userStopped = reason !== "replaced";
        this.statusText = reason === "replaced" ? "讲解已由其他播放接管" : STOPPED_STATUS_TEXT;
      });
      activePlaybackSession = playbackSession;
      let pcmStarted = false;
      let receivedDone = false;

      this.messages.push({ role: "user", content: options.displayQuery || query });
      this.messages.push({ role: "assistant", content: "", completion: "streaming", sources: [] });
      // Mutate the reactive entry, not the original object pushed into Pinia.
      const assistantMessage = this.messages.at(-1);
      let pendingText = "";
      let textTimer = null;
      const flushPendingText = () => {
        if (textTimer !== null) globalThis.clearTimeout(textTimer);
        textTimer = null;
        if (pendingText && isCurrentGeneration()) assistantMessage.content += pendingText;
        pendingText = "";
      };
      activeFlushPending = flushPendingText;
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
            audience: options.audience || null,
            visitor_id: getVisitorId(),
            tts_voice: options.ttsConfig?.voiceType || null,
            // Speech rate is applied by the browser player. Keep the transport
            // request neutral so providers cannot apply a second rate change.
            tts_rate: 100,
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
              if (warnings.includes("vision_scope_unconfirmed")) {
                assistantMessage.warning = "照片中的景点尚未确认，请核对后再参考讲解。";
              }
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
              assistantMessage.sources = Array.isArray(docs) ? JSON.parse(JSON.stringify(docs)) : [];
              this.sources = assistantMessage.sources;
            },
            text_chunk: ({ token }) => {
              if (!isCurrentRequest()) {
                return;
              }
              if (token) metrics.mark("text_received");
              pendingText += token || "";
              if (textTimer === null) textTimer = globalThis.setTimeout(flushPendingText, 16);
            },
            text: ({ text, is_complete }) => {
              if (!isCurrentRequest()) {
                return;
              }
              flushPendingText();
              if (text) metrics.mark("text_received");
              assistantMessage.content = text;
              if (is_complete) {
                this.statusText = ANSWER_DONE_STATUS_TEXT;
              }
            },
            audio: async ({ base64, duration_ms, text, viseme_timeline, provider }) => {
              if (!isCurrentRequest()) {
                return;
              }
              flushPendingText();
              const isFallback = provider === "bailian_unavailable" || provider === "stub";
              const hasAudio = typeof base64 === "string" && base64.trim().length > 0;
              if (hasAudio) metrics.mark("audio_received");
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
                () => { if (isCurrentGeneration()) options.onAudioEnded?.(); },
                text || "",
                (progress, elapsedMs, actualDurationMs) =>
                  isCurrentGeneration() && options.onSpeechProgress?.(
                    progress, elapsedMs, viseme_timeline || null, actualDurationMs,
                  ),
                {
                  sessionId: playbackSession.id,
                  rate: options.ttsConfig?.playbackRate ?? 1,
                  volume: (options.ttsConfig?.volume ?? 80) / 100,
                  allowBrowserSpeech: false,
                  onScheduled: () => { if (isCurrentGeneration()) metrics.mark("audio_scheduled"); },
                  onMode: (mode) => {
                    if (!isCurrentGeneration()) return;
                    if (mode === "silent") {
                      this.voiceFallback = true;
                      this.statusText = FALLBACK_STATUS_TEXT;
                    }
                  },
                },
              );
            },
            audio_chunk: ({ base64, viseme_timeline, word_timeline, sentence_index, sample_rate, channels, bits }) => {
              if (!isCurrentRequest()) {
                return;
              }
              // 流式 PCM 音频块
              if (base64) {
                metrics.mark("audio_received");
                if (!audioPlayer.isPCMStreaming.value) {
                  const started = audioPlayer.startPCMStream(
                    (progress, elapsedMs, durationMs, timeline) =>
                      isCurrentGeneration() && options.onSpeechProgress?.(progress, elapsedMs, timeline, durationMs),
                    () => {
                      if (!isCurrentGeneration()) return;
                      options.onAudioEnded?.();
                      audioPlayer.flush();
                    },
                    () => { if (isCurrentGeneration()) metrics.mark("audio_scheduled"); },
                    {
                      sessionId: playbackSession.id,
                      rate: options.ttsConfig?.playbackRate ?? 1,
                      adaptive: import.meta.env.VITE_GUIDE_ADAPTIVE_AUDIO === "1",
                      onBufferEvent: ({ gapMs, extraBufferMs }) => {
                        if (isCurrentGeneration()) metrics.recordAudioGap(gapMs, extraBufferMs);
                      },
                      onUnavailable: () => {
                        if (!isCurrentGeneration()) return;
                        audioPlayer.stop(playbackSession.id, "unavailable");
                        this.voiceFallback = true;
                        this.statusText = FALLBACK_STATUS_TEXT;
                        options.onAudioUnavailable?.({ provider: "browser_unavailable" });
                      },
                    },
                  );
                  if (!started) {
                    this.voiceFallback = true;
                    this.statusText = FALLBACK_STATUS_TEXT;
                    options.onAudioUnavailable?.({ provider: "browser_unavailable" });
                    return;
                  }
                  pcmStarted = true;
                  options.onAudioStart?.();
                }
                if (!audioPlayer.feedPCMChunk(base64, sample_rate || 24000, channels || 1, bits || 16, playbackSession.id)) {
                  audioPlayer.stop(playbackSession.id, "unavailable");
                  this.voiceFallback = true;
                  this.statusText = FALLBACK_STATUS_TEXT;
                  options.onAudioUnavailable?.({ provider: "audio_decode_failed" });
                }
              }
              // 字级别时间戳 → viseme 时间线
              if (viseme_timeline) {
                audioPlayer.updatePCMVisemeTimeline(viseme_timeline, playbackSession.id);
              }
              // 逐字字幕时间轴：后端按句下发（整段累计毫秒），直接拼接
              if (word_timeline?.length) {
                for (const word of word_timeline) {
                  this.subtitleWords.push({
                    text: word.text || "",
                    begin_time: word.begin_time || 0,
                    end_time: word.end_time || 0,
                    sentence_index: sentence_index ?? 0,
                  });
                }
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
            done: ({ chat_log_id: chatLogId, completion } = {}) => {
              if (!isCurrentRequest()) {
                return;
              }
              flushPendingText();
              if (completion === "incomplete") {
                throw new Error("回答未完成，连接或生成过程已中断。可重新尝试。");
              }
              receivedDone = true;
              assistantMessage.completion = "complete";
              // 结束 PCM 流（如果在用流式模式）
              if (pcmStarted || audioPlayer.isPCMStreaming.value) {
                audioPlayer.endPCMStream(playbackSession.id);
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
          throw new Error("回答连接提前中断，内容未完成。可重新尝试。");
        }
      } catch (error) {
        if (!isCurrentRequest()) return;
        flushPendingText();
        if (isAbortError(error)) {
          if (this.userStopped) {
            this.statusText = STOPPED_STATUS_TEXT;
          }
          return;
        }
        audioPlayer.stop(playbackSession.id, "stream-error");
        pcmStarted = false;
        assistantMessage.completion = "incomplete";
        if (!assistantMessage.content) assistantMessage.content = GENERIC_ERROR_TEXT;
        this.streaming = false;
        this.statusText = INCOMPLETE_STATUS_TEXT;
        this.errorMessage = error?.message || "导览服务暂时不可用，请稍后重试。";
        lastFailedRequest = { query, selection, options };
      } finally {
        if (textTimer !== null) globalThis.clearTimeout(textTimer);
        if (activeFlushPending === flushPendingText) activeFlushPending = null;
        rememberChatMetrics(metrics.finish(assistantMessage.completion));
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
    async retryLastMessage(overrides = {}) {
      if (!lastFailedRequest || this.streaming) return;
      const request = lastFailedRequest;
      const options = { ...request.options, ...overrides };
      if (request.options?.ttsConfig || overrides.ttsConfig) {
        options.ttsConfig = { ...request.options?.ttsConfig, ...overrides.ttsConfig };
      }
      await this.sendMessage(request.query, request.selection, options);
    },
  },
});
