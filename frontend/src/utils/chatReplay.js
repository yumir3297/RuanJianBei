export function createChatReplayController({
  requestReplay,
  audioPlayer,
  getSessionId,
  getVoice,
  getRate,
  onMode,
  onProgress,
  onEnded,
} = {}) {
  let requestGeneration = 0;

  async function replay(message) {
    if (
      !message?.chatLogId
      || !message.content
      || message.completion !== "complete"
      || typeof requestReplay !== "function"
      || !audioPlayer
    ) return false;

    const generation = ++requestGeneration;
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      if (generation !== requestGeneration) return;
      message.replayPlaying = false;
      message.replayLoading = false;
      onEnded?.(message);
    };
    message.replayError = "";
    message.replayLoading = true;
    message.replayPlaying = false;

    let playback;
    try {
      playback = audioPlayer.claimPlayback("chat-replay", finish);
      // Start the browser's audio-context resume while the click's user
      // activation is still available; the network request may take time.
      audioPlayer.unlock?.();
      const audio = await requestReplay({
        chat_log_id: message.chatLogId,
        session_id: getSessionId(),
        tts_voice: getVoice() || null,
      });
      if (
        generation !== requestGeneration
        || !audioPlayer.isCurrentPlaybackSession(playback.id)
      ) return false;

      message.replayLoading = false;
      message.replayPlaying = true;
      const durationMs = Math.max(Number(audio?.duration_ms) || 0, message.content.length * 180, 800);
      await audioPlayer.enqueue(
        audio?.base64_audio || "",
        durationMs,
        finish,
        message.content,
        onProgress ? (...args) => onProgress(message, ...args) : undefined,
        {
          sessionId: playback.id,
          rate: getRate(),
          volume: 0.8,
          // If the returned audio cannot be decoded by the current browser,
          // the shared player can still speak the saved answer locally.
          allowBrowserSpeech: true,
          onMode: (mode) => onMode?.(message, mode),
        },
      );
      return true;
    } catch (error) {
      if (generation === requestGeneration) {
        message.replayError = error?.response?.data?.detail || error?.message || "重播失败，请稍后重试。";
        finish();
      }
      return false;
    } finally {
      if (generation === requestGeneration && !message.replayPlaying) {
        message.replayLoading = false;
      }
    }
  }

  return { replay };
}
