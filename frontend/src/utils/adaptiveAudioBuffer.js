// Experimental policy for PCM playback after a network underrun. Times are
// AudioContext seconds. It does not buffer the first chunk or change audio data.
export function createAdaptiveAudioBuffer() {
  const underrunThreshold = 0.08;
  const recoveryBuffer = 0.08;
  const cooldown = 2.0;
  let lastAdjustment = -Infinity;
  return {
    schedule(now, nextTime) {
      const earliest = Math.max(now, nextTime);
      if (now - nextTime >= underrunThreshold && now - lastAdjustment >= cooldown) {
        lastAdjustment = now;
        return earliest + recoveryBuffer;
      }
      return earliest;
    },
  };
}
