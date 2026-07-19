import { ref } from "vue";

let sharedAudioPlayer = null;

export function useAudioPlayer() {
  if (sharedAudioPlayer) return sharedAudioPlayer;

  const isPlaying = ref(false);
  const queue = ref([]);
  const mouthEnergy = ref(0);
  const mouthAnalysisActive = ref(false);
  const isPCMStreaming = ref(false);

  let audioContext = null;
  let currentSource = null;
  let currentUtterance = null;
  let stopGeneration = 0;
  let analyserNode = null;
  let analysisSinkNode = null;
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
      analyserNode.smoothingTimeConstant = 0.2;
      analysisSinkNode = ctx.createGain();
      analysisSinkNode.gain.value = 0;
      analyserNode.connect(analysisSinkNode);
      analysisSinkNode.connect(ctx.destination);
      analyserData = new Uint8Array(analyserNode.fftSize);
    }
    return analyserNode;
  }

  function startMouthLoop() {
    stopMouthLoop();
    mouthAnalysisActive.value = true;
    const tick = () => {
      if (!analyserNode || !analyserData) { mouthRaf = requestAnimationFrame(tick); return; }
      analyserNode.getByteTimeDomainData(analyserData);
      let sum = 0;
      for (let i = 0; i < analyserData.length; i++) {
        const v = (analyserData[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / analyserData.length);
      const normalized = Math.min(Math.max((rms - 0.012) / (0.22 - 0.012), 0), 1);
      const raw = normalized > 0 ? Math.pow(normalized, 0.72) : 0;
      const attack = 0.48, decay = 0.14;
      if (raw > lastMouth) lastMouth += (raw - lastMouth) * attack;
      else lastMouth += (raw - lastMouth) * decay;
      if (raw === 0 && lastMouth < 0.018) lastMouth = 0;
      mouthEnergy.value = lastMouth;
      mouthRaf = requestAnimationFrame(tick);
    };
    mouthRaf = requestAnimationFrame(tick);
  }

  function stopMouthLoop() {
    if (mouthRaf) { cancelAnimationFrame(mouthRaf); mouthRaf = null; }
    lastMouth = 0;
    mouthEnergy.value = 0;
    mouthAnalysisActive.value = false;
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
      gainNode.connect(ctx.destination);

      const analyser = ensureAnalyser();
      if (analyser) source.connect(analyser);

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
        source.disconnect();
        gainNode.disconnect();
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

  function generateFrontendVisemeTimeline(text, totalDurationMs) {
    const chars = [...text];
    if (!chars.length || !totalDurationMs) return [];
    const charDuration = totalDurationMs / chars.length;
    const timeline = [];
    for (let i = 0; i < chars.length; i++) {
      const start = i * charDuration;
      const end = (i + 1) * charDuration;
      const ch = chars[i];
      const isPunct = /[，。！？、；：""''（）《》【】\s,\.!\?;:'"()\[\]{}]/.test(ch);
      const isOpen = /[啊哦呃衣乌鱼阿喔鹅依呜吁āáǎàōóǒòēéěèīíǐìūúǔùǖǘǚǜ]/.test(ch);
      if (isPunct) {
        timeline.push({ start, end, value: 0.02, form: 0.05 });
      } else if (isOpen) {
        timeline.push({ start, end, value: 0.75, form: 0.4 });
      } else {
        timeline.push({ start, end, value: 0.25, form: 0.12 });
      }
    }
    return timeline;
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
      const visemeTimeline = generateFrontendVisemeTimeline(text, estimatedDuration);
      let progressTimer = null;
      const reportProgress = (p) => onProgress?.(
        Math.min(Math.max(p, 0), 1),
        Date.now() - startTime,
        estimatedDuration,
        visemeTimeline,
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
      } else if (
        current.text
        && speechSynthSupported
        && current.playbackOptions?.allowBrowserSpeech === true
      ) {
        current.playbackOptions?.onMode?.("browser");
        await playSpeechSynthesis(current.text, current.durationMs, current.onProgress, current.playbackOptions);
      } else {
        current.playbackOptions?.onMode?.("silent");
        current.onProgress?.(0, 0, current.durationMs);
        // Invalid or missing audio must not imitate playback or delay the answer.
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
    // 同时停止 PCM 流
    resetPCMStream(true);
    isPlaying.value = false;
  }

  // ── PCM 流式播放 ──
  let pcmStream = null;
  let pcmAccumulatedMs = 0;
  let pcmOnProgress = null;
  let pcmOnAudioEnded = null;
  let pcmProgressTimer = null;
  let pcmEndTimer = null;
  let pcmTimeline = [];

  function resetPCMStream(stopSources = false) {
    if (stopSources && pcmStream?.sources) {
      pcmStream.sources.forEach((source) => { try { source.stop(); } catch {} });
    }
    pcmStream = null;
    pcmAccumulatedMs = 0;
    pcmOnProgress = null;
    pcmOnAudioEnded = null;
    pcmTimeline = [];
    isPCMStreaming.value = false;
    if (pcmProgressTimer) { clearInterval(pcmProgressTimer); pcmProgressTimer = null; }
    if (pcmEndTimer) { clearTimeout(pcmEndTimer); pcmEndTimer = null; }
  }

  function base64PCMToAudioBuffer(base64String, sampleRate = 24000, channels = 1, bits = 16) {
    const ctx = ensureContext();
    if (!ctx || !base64String) return null;
    try {
      const normalized = base64String.includes(",") ? base64String.slice(base64String.indexOf(",") + 1) : base64String;
      const binary = atob(normalized);
      if (!binary.length) return null;
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const dataView = new DataView(bytes.buffer);

      // 16-bit PCM samples
      const totalSamples = Math.floor(bytes.length / (bits / 8));
      const audioBuffer = ctx.createBuffer(channels, totalSamples, sampleRate);
      const channelData = audioBuffer.getChannelData(0);

      if (bits === 16) {
        for (let i = 0; i < totalSamples; i++) {
          channelData[i] = dataView.getInt16(i * 2, true) / 32768.0;
        }
      } else if (bits === 8) {
        for (let i = 0; i < totalSamples; i++) {
          channelData[i] = (bytes[i] - 128) / 128.0;
        }
      }

      return audioBuffer;
    } catch { return null; }
  }

  function startPCMStream(onProgress, onAudioEnded) {
    resetPCMStream(true);
    pcmOnProgress = onProgress;
    pcmOnAudioEnded = onAudioEnded;
    pcmAccumulatedMs = 0;
    isPCMStreaming.value = true;
    isPlaying.value = true;
    startMouthLoop();
  }

  function feedPCMChunk(base64String, sampleRate = 24000, channels = 1, bits = 16) {
    const ctx = ensureContext();
    if (!ctx || !base64String) return;
    if (ctx.state === "suspended") ctx.resume();

    const audioBuffer = base64PCMToAudioBuffer(base64String, sampleRate, channels, bits);
    if (!audioBuffer) return;

    if (pcmEndTimer) { clearTimeout(pcmEndTimer); pcmEndTimer = null; }

    const chunkDurationMs = (audioBuffer.length / sampleRate) * 1000;

    if (!pcmStream) {
      // 第一个块：从当前时间开始播放
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0.8;
      source.connect(gainNode);
      gainNode.connect(ctx.destination);
      const analyser = ensureAnalyser();
      if (analyser) source.connect(analyser);
      source.start(0);

      pcmStream = {
        startTime: ctx.currentTime,
        nextTime: ctx.currentTime + audioBuffer.duration,
        lastSource: source,
        sources: new Set([source]),
      };

      // 进度上报
      if (pcmOnProgress) {
        pcmProgressTimer = setInterval(() => {
          const elapsedMs = Math.max((ctx.currentTime - pcmStream.startTime) * 1000, 0);
          const durationMs = Math.max(pcmAccumulatedMs, pcmTimeline.at(-1)?.end || 0, 1);
          pcmOnProgress(
            Math.min(elapsedMs / durationMs, 1),
            elapsedMs,
            durationMs,
            pcmTimeline,
          );
        }, 30);
      }

      source.onended = () => {
        source.disconnect();
        gainNode.disconnect();
        pcmStream?.sources?.delete(source);
        if (pcmStream?.lastSource === source) pcmStream.lastSource = null;
      };
    } else {
      // 后续块：在前一块结束后播放
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0.8;
      source.connect(gainNode);
      gainNode.connect(ctx.destination);
      const analyser = ensureAnalyser();
      if (analyser) source.connect(analyser);
      source.start(pcmStream.nextTime);

      pcmStream.nextTime += audioBuffer.duration;
      pcmStream.lastSource = source;
      pcmStream.sources.add(source);

      source.onended = () => {
        source.disconnect();
        gainNode.disconnect();
        pcmStream?.sources?.delete(source);
        if (pcmStream?.lastSource === source) {
          pcmStream.lastSource = null;
        }
      };
    }

    pcmAccumulatedMs += chunkDurationMs;
  }

  function updatePCMVisemeTimeline(timeline = []) {
    if (!Array.isArray(timeline) || timeline.length === 0) return;
    const byRange = new Map(pcmTimeline.map((item) => [`${item.start}:${item.end}`, item]));
    timeline.forEach((item) => byRange.set(`${item.start}:${item.end}`, item));
    pcmTimeline = [...byRange.values()].sort((a, b) => a.start - b.start);
  }

  function endPCMStream() {
    if (!isPCMStreaming.value) return;
    const ctx = ensureContext();
    const remainingMs = pcmStream && ctx
      ? Math.max((pcmStream.nextTime - ctx.currentTime) * 1000, 0)
      : 0;
    const drainDelayMs = Math.max(remainingMs + 80, 120);

    if (pcmEndTimer) clearTimeout(pcmEndTimer);
    pcmEndTimer = setTimeout(() => {
      pcmEndTimer = null;
      stopMouthLoop();
      if (pcmProgressTimer) { clearInterval(pcmProgressTimer); pcmProgressTimer = null; }
      isPlaying.value = false;
      const onAudioEnded = pcmOnAudioEnded;
      resetPCMStream();
      onAudioEnded?.();
    }, drainDelayMs);
  }

  sharedAudioPlayer = {
    queue, isPlaying, isSupported, mouthEnergy, mouthAnalysisActive, isPCMStreaming,
    enqueue, flush, stop,
    // PCM 流式播放
    startPCMStream, feedPCMChunk, updatePCMVisemeTimeline, endPCMStream,
  };
  return sharedAudioPlayer;
}
