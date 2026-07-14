import { ref } from "vue";

let sharedAudioPlayer = null;

export function useAudioPlayer() {
  if (sharedAudioPlayer) return sharedAudioPlayer;

  const isPlaying = ref(false);
  const queue = ref([]);
  const mouthEnergy = ref(0);

  let audioContext = null;
  let currentSource = null;
  let currentUtterance = null;
  let stopGeneration = 0;
  let analyserNode = null;
  let analyserData = null;
  let mouthRaf = null;
  let lastMouth = 0;

  const checkSupported = typeof window !== "undefined" && typeof window.AudioContext !== "undefined";
  const isSupported = ref(checkSupported);
  const speechSynthSupported = typeof window !== "undefined" && typeof window.speechSynthesis !== "undefined";

  function ensureContext() {
    if (!audioContext && checkSupported) {
      try { audioContext = new AudioContext(); } catch { isSupported.value = false; }
    }
    return audioContext;
  }

  function ensureAnalyser() {
    const ctx = ensureContext();
    if (!ctx) return null;
    if (!analyserNode) {
      analyserNode = ctx.createAnalyser();
      analyserNode.fftSize = 512;
      analyserNode.smoothingTimeConstant = 0.4;
      analyserNode.connect(ctx.destination);
      analyserData = new Uint8Array(analyserNode.fftSize);
    }
    return analyserNode;
  }

  function startMouthLoop() {
    stopMouthLoop();
    const tick = () => {
      if (!analyserNode || !analyserData) { mouthRaf = requestAnimationFrame(tick); return; }
      analyserNode.getByteTimeDomainData(analyserData);
      let sum = 0;
      for (let i = 0; i < analyserData.length; i++) {
        const v = (analyserData[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / analyserData.length);
      const raw = Math.min(rms * 3.5, 1);
      const attack = 0.25, decay = 0.06;
      if (raw > lastMouth) lastMouth += (raw - lastMouth) * attack;
      else lastMouth += (raw - lastMouth) * decay;
      mouthEnergy.value = lastMouth;
      mouthRaf = requestAnimationFrame(tick);
    };
    mouthRaf = requestAnimationFrame(tick);
  }

  function stopMouthLoop() {
    if (mouthRaf) { cancelAnimationFrame(mouthRaf); mouthRaf = null; }
    lastMouth = 0;
    mouthEnergy.value = 0;
  }

  async function base64ToAudioBuffer(base64String) {
    const ctx = ensureContext();
    if (!ctx || !base64String) return null;
    try {
      if (ctx.state === "suspended") await ctx.resume();
      const normalized = base64String.includes(",") ? base64String.slice(base64String.indexOf(",") + 1) : base64String;
      const binary = atob(normalized);
      if (!binary.length) return null;
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      return await ctx.decodeAudioData(bytes.buffer.slice(0));
    } catch { return null; }
  }

  async function playAudioBuffer(audioBuffer, onProgress, playbackOptions = {}) {
    const ctx = ensureContext();
    if (!ctx || audioBuffer === null) return 0;
    return new Promise((resolve) => {
      const source = ctx.createBufferSource();
      currentSource = source;
      source.buffer = audioBuffer;
      const playbackRate = Math.min(Math.max(playbackOptions.rate || 1, 0.8), 1.5);
      const volume = Math.min(Math.max(playbackOptions.volume ?? 0.8, 0), 1);
      const gainNode = ctx.createGain();
      source.playbackRate.value = playbackRate;
      gainNode.gain.value = volume;
      source.connect(gainNode);

      const analyser = ensureAnalyser();
      if (analyser) { gainNode.connect(analyser); } else { gainNode.connect(ctx.destination); }

      startMouthLoop();

      const startTime = ctx.currentTime;
      const duration = audioBuffer.duration / playbackRate;
      let progressTimer = null;
      if (onProgress) {
        progressTimer = setInterval(() => {
          const elapsed = (ctx.currentTime - startTime) * 1000;
          onProgress(Math.min(elapsed / (duration * 1000), 1), elapsed, duration * 1000);
        }, 30);
      }
      source.onended = () => {
        currentSource = null;
        stopMouthLoop();
        if (progressTimer) { clearInterval(progressTimer); onProgress?.(1, duration * 1000, duration * 1000); }
        resolve(duration * 1000);
      };
      source.start(0);
    });
  }

  function getChineseVoice() {
    const voices = window.speechSynthesis.getVoices();
    return voices.find((v) => v.lang.toLowerCase().startsWith("zh")) || null;
  }

  async function waitForChineseVoice(timeoutMs = 600) {
    const existing = getChineseVoice();
    if (existing) return existing;
    return new Promise((resolve) => {
      let settled = false;
      const finish = () => { if (settled) return; settled = true; window.speechSynthesis.removeEventListener("voiceschanged", handleVoicesChanged); resolve(getChineseVoice()); };
      const handleVoicesChanged = () => finish();
      window.speechSynthesis.addEventListener("voiceschanged", handleVoicesChanged);
      window.setTimeout(finish, timeoutMs);
    });
  }

  async function playSpeechSynthesis(text, durationMs, onProgress, playbackOptions = {}) {
    if (!speechSynthSupported) return 0;
    return new Promise((resolve) => {
      if (currentUtterance) window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "zh-CN";
      utterance.rate = Math.min(Math.max(playbackOptions.rate || 1, 0.8), 1.5);
      utterance.pitch = 1.1;
      utterance.volume = Math.min(Math.max(playbackOptions.volume ?? 0.8, 0), 1);
      const startTime = Date.now();
      const playbackRate = Math.min(Math.max(playbackOptions.rate || 1, 0.8), 1.5);
      const estimatedDuration = Math.max((durationMs || text.length * 180) / playbackRate, 800);
      let progressTimer = null;
      const reportProgress = (p) => onProgress?.(
        Math.min(Math.max(p, 0), 1),
        Date.now() - startTime,
        estimatedDuration,
      );
      const finish = (d) => { if (progressTimer) { clearInterval(progressTimer); progressTimer = null; } stopMouthLoop(); reportProgress(1); currentUtterance = null; resolve(d); };
      utterance.onstart = () => { reportProgress(0); progressTimer = setInterval(() => reportProgress((Date.now() - startTime) / estimatedDuration), 50); };
      utterance.onboundary = (e) => { if (text.length > 0 && Number.isFinite(e.charIndex)) reportProgress(e.charIndex / text.length); };
      utterance.onend = () => finish(Date.now() - startTime);
      utterance.onerror = () => finish(0);
      waitForChineseVoice().then((zhVoice) => { if (zhVoice) utterance.voice = zhVoice; currentUtterance = utterance; window.speechSynthesis.speak(utterance); });
    });
  }

  async function enqueue(base64, durationMs = 800, onEnded, text = "", onProgress, playbackOptions = {}) {
    queue.value.push({ base64, durationMs, onEnded, text, onProgress, playbackOptions });
    if (!isPlaying.value) await flush();
  }

  async function flush() {
    if (isPlaying.value) return;
    isPlaying.value = true;
    const generation = stopGeneration;
    while (queue.value.length > 0) {
      if (generation !== stopGeneration) break;
      const current = queue.value.shift();
      const audioBuffer = await base64ToAudioBuffer(current.base64);
      if (audioBuffer) {
        current.playbackOptions?.onMode?.("audio");
        await playAudioBuffer(audioBuffer, current.onProgress, current.playbackOptions);
      } else if (current.text && speechSynthSupported) {
        current.playbackOptions?.onMode?.("browser");
        await playSpeechSynthesis(current.text, current.durationMs, current.onProgress, current.playbackOptions);
      } else {
        current.playbackOptions?.onMode?.("silent");
        current.onProgress?.(0, 0, current.durationMs);
        await new Promise((r) => setTimeout(r, Math.min(current.durationMs, 3000)));
        current.onProgress?.(1, current.durationMs, current.durationMs);
      }
      if (generation === stopGeneration && current.onEnded) current.onEnded();
    }
    isPlaying.value = false;
    stopMouthLoop();
  }

  function stop() {
    stopGeneration += 1;
    stopMouthLoop();
    if (currentSource) { try { currentSource.stop(); } catch {} currentSource = null; }
    if (currentUtterance) { window.speechSynthesis.cancel(); currentUtterance = null; }
    queue.value = [];
    isPlaying.value = false;
  }

  sharedAudioPlayer = { queue, isPlaying, isSupported, mouthEnergy, enqueue, flush, stop };
  return sharedAudioPlayer;
}
