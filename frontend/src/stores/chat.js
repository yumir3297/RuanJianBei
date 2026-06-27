import { defineStore } from "pinia";

import { streamChat } from "../api/chat";
import { useAudioPlayer } from "../composables/useAudioPlayer";

const audioPlayer = useAudioPlayer();

const DEFAULT_STATUS_TEXT = "等待提问";
const UPDATED_CONTEXT_STATUS_TEXT = "已更新游览方向";
const ANSWER_DONE_STATUS_TEXT = "回答完成";
const FALLBACK_STATUS_TEXT = "云端语音不可用，已使用浏览器播报";
const FALLBACK_DONE_STATUS_TEXT = "浏览器语音降级";
const OFFLINE_STATUS_TEXT = "暂时离线";
const GENERIC_ERROR_TEXT = "抱歉，导览服务暂时没有响应。请稍后再试，或换一个问题问问我。";

let activeStreamController = null;
let activeStreamToken = 0;

function isAbortError(error) {
  return error?.name === "AbortError";
}

export const useChatStore = defineStore("chat", {
  state: () => ({
    messages: [],
    sources: [],
    followups: [],
    conversationContext: null,
    statusText: DEFAULT_STATUS_TEXT,
    streaming: false,
    voiceFallback: false,
  }),
  actions: {
    resetConversationContext() {
      this.conversationContext = null;
      this.followups = [];
      this.sources = [];
      this.statusText = DEFAULT_STATUS_TEXT;
    },
    resetSession() {
      this.stopOutput();
      this.messages = [];
      this.resetConversationContext();
    },
    stopOutput() {
      activeStreamToken += 1;
      if (activeStreamController) {
        activeStreamController.abort();
        activeStreamController = null;
      }
      audioPlayer.stop();
      this.streaming = false;
      this.voiceFallback = false;
      this.statusText = DEFAULT_STATUS_TEXT;
    },
    async sendMessage(query, selection = null, options = {}) {
      if (!query.trim()) {
        return;
      }

      this.stopOutput();
      const requestToken = activeStreamToken;
      const streamController = new AbortController();
      activeStreamController = streamController;
      const isCurrentRequest = () =>
        requestToken === activeStreamToken && activeStreamController === streamController;

      const assistantMessage = {
        role: "assistant",
        content: "",
      };

      this.messages.push({ role: "user", content: query });
      this.messages.push(assistantMessage);
      this.sources = [];
      this.followups = [];
      this.streaming = true;
      this.voiceFallback = false;

      try {
        await streamChat(
          {
            query,
            session_id: "demo-session",
            input_mode: "text",
            text_only: false,
            persona: options.ttsConfig?.persona || null,
            tts_voice: options.ttsConfig?.voiceType || null,
            tts_rate: options.ttsConfig?.speechRate || 100,
            tts_volume: options.ttsConfig?.volume ?? 80,
            selection,
            context: this.conversationContext,
            vision_context: options.visionContext || null,
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
              if (provider === "bailian_unavailable" || provider === "stub") {
                this.statusText = FALLBACK_STATUS_TEXT;
              }
              options.onAudioStart?.();
              await audioPlayer.enqueue(
                base64,
                duration_ms,
                () => options.onAudioEnded?.(),
                text || "",
                (progress, elapsedMs) =>
                  options.onSpeechProgress?.(progress, elapsedMs, viseme_timeline || null),
                {
                  rate: (options.ttsConfig?.speechRate || 100) / 100,
                  volume: (options.ttsConfig?.volume ?? 80) / 100,
                  onMode: (mode) => {
                    if (mode === "browser") {
                      this.voiceFallback = true;
                      this.statusText = FALLBACK_STATUS_TEXT;
                    }
                  },
                },
              );
            },
            avatar: ({ viseme_text, emotion }) => {
              if (!isCurrentRequest()) {
                return;
              }
              options.onAvatar?.({ viseme_text, emotion });
            },
            followups: ({ items = [] }) => {
              if (!isCurrentRequest()) {
                return;
              }
              this.followups = items.filter(
                (item) => typeof item?.label === "string" && typeof item?.query === "string",
              );
            },
            done: () => {
              if (!isCurrentRequest()) {
                return;
              }
              this.streaming = false;
              this.statusText = this.voiceFallback
                ? FALLBACK_DONE_STATUS_TEXT
                : DEFAULT_STATUS_TEXT;
            },
          },
          {
            signal: streamController.signal,
          },
        );
      } catch (error) {
        if (isAbortError(error)) {
          return;
        }
        assistantMessage.content = GENERIC_ERROR_TEXT;
        this.streaming = false;
        this.statusText = OFFLINE_STATUS_TEXT;
      } finally {
        if (activeStreamController === streamController) {
          activeStreamController = null;
        }
      }
    },
  },
});
