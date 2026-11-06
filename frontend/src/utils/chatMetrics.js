const FIELDS = Object.freeze({
  text_received: "text_received_ms",
  audio_received: "audio_received_ms",
  audio_scheduled: "audio_scheduled_ms",
});
const recent = [];
const MAX_SAMPLES = 20;

// Session-local diagnostics contain only relative durations and the outcome.
// They are neither persisted nor sent over the network.
export function createChatMetrics(now = () => globalThis.performance.now()) {
  const started = now();
  const sample = {};
  return {
    mark(name) {
      const field = FIELDS[name];
      if (field && sample[field] === undefined) sample[field] = Math.max(0, Math.round(now() - started));
    },
    recordAudioGap(gapMs, extraBufferMs) {
      if (!Number.isFinite(gapMs) || gapMs <= 0) return;
      sample.pcm_underrun_count = (sample.pcm_underrun_count || 0) + 1;
      sample.pcm_gap_ms = (sample.pcm_gap_ms || 0) + Math.round(gapMs);
      sample.pcm_extra_buffer_ms = (sample.pcm_extra_buffer_ms || 0)
        + Math.max(0, Math.round(Number.isFinite(extraBufferMs) ? extraBufferMs : 0));
    },
    finish(outcome) {
      if (sample.outcome === undefined) {
        sample.outcome = ["complete", "incomplete", "stopped"].includes(outcome) ? outcome : "incomplete";
        sample.duration_ms = Math.max(0, Math.round(now() - started));
      }
      return sample;
    },
  };
}

export function rememberChatMetrics(sample) {
  recent.push(sample);
  if (recent.length > MAX_SAMPLES) recent.shift();
}

export function getRecentChatMetrics() {
  return recent.map((sample) => ({ ...sample }));
}

// Development-only inspection; production never exposes or uploads the samples.
if (import.meta.env.DEV && typeof window !== "undefined") {
  window.getGuideChatMetrics = getRecentChatMetrics;
}
