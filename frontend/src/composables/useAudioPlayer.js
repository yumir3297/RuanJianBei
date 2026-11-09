import { ref } from "vue";
import { createAdaptiveAudioBuffer } from "../utils/adaptiveAudioBuffer";

let sharedAudioPlayer = null;

function normalizePlaybackRate(value) {
  const rate = Number(value) || 1;
  return Math.min(Math.max(rate, 0.8), 1.5);
}

export function useAudioPlayer() {
  if (sharedAudioPlayer) return sharedAudioPlayer;

  const isPlaying = ref(false);
  const queue = ref([]);
  const mouthEnergy = ref(0);
  const mouthAnalysisActive = ref(false);
  const isPCMStreaming = ref(false);
  const activePlayback = ref(null);

  let audioContext = null;
  let currentSource = null;
  let currentUtterance = null;
  let currentUtteranceFinish = null;
  let stopGeneration = 0;
  let playbackSessionSequence = 0;
  let playbackSession = null;
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

  async function unlock() {
    const ctx = ensureContext();
    if (!ctx) return false;
    if (ctx.state === "suspended") {
      try { await ctx.resume(); } catch { return false; }
    }
    return ctx.state === "running";
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
    const generation = stopGeneration;
    return new Promise((resolve) => {
      const source = ctx.createBufferSource();
      currentSource = source;
      source.buffer = audioBuffer;
      const playbackRate = normalizePlaybackRate(playbackOptions.rate);
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
      const contentDuration = audioBuffer.duration;
      const playbackDuration = contentDuration / playbackRate;
      let progressTimer = null;
      if (onProgress) {
        progressTimer = setInterval(() => {
          if (generation !== stopGeneration) return;
          const elapsed = Math.min(Math.max((ctx.currentTime - startTime) * 1000 * playbackRate, 0), contentDuration * 1000);
          onProgress(Math.min(elapsed / (contentDuration * 1000), 1), elapsed, contentDuration * 1000);
        }, 30);
      }
      source.onended = () => {
        if (currentSource === source) currentSource = null;
        source.disconnect();
        gainNode.disconnect();
        if (generation === stopGeneration) stopMouthLoop();
        if (progressTimer) {
          clearInterval(progressTimer);
          if (generation === stopGeneration) onProgress?.(1, contentDuration * 1000, contentDuration * 1000);
        }
        resolve(playbackDuration * 1000);
      };
      source.start(0);
      if (ctx.state === "running") playbackOptions.onScheduled?.();
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
    const generation = stopGeneration;
    return new Promise((resolve) => {
      if (currentUtterance) window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "zh-CN";
      utterance.rate = normalizePlaybackRate(playbackOptions.rate);
      utterance.pitch = 1.1;
      utterance.volume = Math.min(Math.max(playbackOptions.volume ?? 0.8, 0), 1);
      const startTime = Date.now();
      const playbackRate = normalizePlaybackRate(playbackOptions.rate);
      const contentDuration = Math.max(durationMs || text.length * 180, 800);
      const estimatedPlaybackDuration = contentDuration / playbackRate;
      const visemeTimeline = generateFrontendVisemeTimeline(text, contentDuration);
      let progressTimer = null;
      let settled = false;
      const reportProgress = (p) => {
        if (generation !== stopGeneration || settled) return;
        const boundedProgress = Math.min(Math.max(p, 0), 1);
        const elapsedContentMs = boundedProgress >= 1
          ? contentDuration
          : Math.min((Date.now() - startTime) * playbackRate, contentDuration);
        onProgress?.(boundedProgress, elapsedContentMs, contentDuration, visemeTimeline);
      };
      const finish = (d) => {
        if (settled) return;
        if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
        if (generation === stopGeneration) { stopMouthLoop(); reportProgress(1); }
        settled = true;
        if (currentUtterance === utterance) currentUtterance = null;
        if (currentUtteranceFinish === finish) currentUtteranceFinish = null;
        resolve(d);
      };
      utterance.onstart = () => { if (generation !== stopGeneration || settled) return; reportProgress(0); progressTimer = setInterval(() => reportProgress((Date.now() - startTime) / estimatedPlaybackDuration), 50); };
      utterance.onboundary = (e) => { if (generation === stopGeneration && !settled && text.length > 0 && Number.isFinite(e.charIndex)) reportProgress(e.charIndex / text.length); };
      utterance.onend = () => finish(Date.now() - startTime);
      utterance.onerror = () => finish(0);
      waitForChineseVoice().then((zhVoice) => { if (generation !== stopGeneration) { finish(0); return; } if (zhVoice) utterance.voice = zhVoice; currentUtterance = utterance; currentUtteranceFinish = finish; window.speechSynthesis.speak(utterance); });
    });
  }

  function claimPlayback(owner, onStopped) {
    if (playbackSession) stop(playbackSession.id, "replaced");
    else if (isPlaying.value || isPCMStreaming.value) stop();
    const session = { id: ++playbackSessionSequence, owner, onStopped };
    playbackSession = session;
    activePlayback.value = { id: session.id, owner: session.owner };
    return { id: session.id, owner: session.owner };
  }

  function isCurrentPlaybackSession(sessionId) {
    return sessionId == null || playbackSession?.id === sessionId;
  }

  async function enqueue(base64, durationMs = 800, onEnded, text = "", onProgress, playbackOptions = {}) {
    if (!isCurrentPlaybackSession(playbackOptions.sessionId)) return false;
    queue.value.push({ base64, durationMs, onEnded, text, onProgress, playbackOptions });
    if (!isPlaying.value) await flush();
    return true;
  }

  async function flush() {
    if (isPlaying.value) return;
    isPlaying.value = true;
    const generation = stopGeneration;
    while (queue.value.length > 0) {
      if (generation !== stopGeneration) break;
      const current = queue.value.shift();
      if (!isCurrentPlaybackSession(current.playbackOptions?.sessionId)) continue;
      const audioBuffer = await base64ToAudioBuffer(current.base64);
      if (generation !== stopGeneration) break;
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
    if (generation === stopGeneration) {
      isPlaying.value = false;
      stopMouthLoop();
    }
  }

  function stop(sessionId = null, reason = "stopped") {
    if (sessionId != null && playbackSession?.id !== sessionId) return false;
    const stoppedSession = playbackSession;
    playbackSession = null;
    activePlayback.value = null;
    stopGeneration += 1;
    stopMouthLoop();
    if (currentSource) { try { currentSource.stop(); } catch {} currentSource = null; }
    if (currentUtterance) {
      const finishUtterance = currentUtteranceFinish;
      window.speechSynthesis.cancel();
      finishUtterance?.(0);
      currentUtterance = null;
      currentUtteranceFinish = null;
    }
    queue.value = [];
    // 同时停止 PCM 流
    resetPCMStream(true);
    isPlaying.value = false;
    try { stoppedSession?.onStopped?.(reason); } catch {}
    return true;
  }

  // ── PCM 流式播放 ──
  let pcmStream = null;
  let pcmAccumulatedMs = 0;
  let pcmOnProgress = null;
  let pcmOnAudioEnded = null;
  let pcmOnScheduled = null;
  let pcmProgressTimer = null;
  let pcmEndTimer = null;
  let pcmTimeline = [];
  let pcmPlaybackRate = 1;
  let pcmRunId = 0;
  let pcmBufferPolicy = null;
  let pcmOnBufferEvent = null;
  let pcmOnUnavailable = null;
  let pcmResumeTimer = null;

  function resetPCMStream(stopSources = false) {
    pcmRunId += 1;
    pcmBufferPolicy = null;
    pcmOnBufferEvent = null;
    pcmOnUnavailable = null;
    if (pcmResumeTimer) { clearTimeout(pcmResumeTimer); pcmResumeTimer = null; }
    if (stopSources && pcmStream?.sources) {
      pcmStream.sources.forEach((source) => { try { source.stop(); } catch {} });
    }
    pcmStream = null;
    pcmAccumulatedMs = 0;
    pcmOnProgress = null;
    pcmOnAudioEnded = null;
    pcmOnScheduled = null;
    pcmTimeline = [];
    pcmPlaybackRate = 1;
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

  function startPCMStream(onProgress, onAudioEnded, onScheduled, options = {}) {
    if (!isCurrentPlaybackSession(options.sessionId)) return false;
    resetPCMStream(true);
    if (!ensureContext()) return false;
    pcmBufferPolicy = options.adaptive ? createAdaptiveAudioBuffer() : null;
    pcmPlaybackRate = normalizePlaybackRate(options.rate);
    pcmOnBufferEvent = options.onBufferEvent || null;
    pcmOnUnavailable = options.onUnavailable || null;
    pcmOnProgress = onProgress;
    pcmOnAudioEnded = onAudioEnded;
    pcmOnScheduled = onScheduled;
    pcmAccumulatedMs = 0;
    isPCMStreaming.value = true;
    isPlaying.value = true;
    startMouthLoop();
    return true;
  }

  function feedPCMChunk(base64String, sampleRate = 24000, channels = 1, bits = 16, sessionId = null) {
    if (!isCurrentPlaybackSession(sessionId)) return false;
    const ctx = ensureContext();
    if (!ctx || !base64String) return false;
    const runId = pcmRunId;
    if (ctx.state === "suspended" && !pcmResumeTimer) {
      const failResume = () => {
        if (runId !== pcmRunId) return;
        const onUnavailable = pcmOnUnavailable;
        resetPCMStream(true);
        isPlaying.value = false;
        stopMouthLoop();
        onUnavailable?.();
      };
      pcmResumeTimer = setTimeout(failResume, 3000);
      Promise.resolve().then(() => ctx.resume()).then(() => {
        if (runId !== pcmRunId) return;
        if (ctx.state !== "running") { failResume(); return; }
        if (pcmResumeTimer) { clearTimeout(pcmResumeTimer); pcmResumeTimer = null; }
      }).catch(failResume);
    }

    const audioBuffer = base64PCMToAudioBuffer(base64String, sampleRate, channels, bits);
    if (!audioBuffer) return false;

    if (pcmEndTimer) { clearTimeout(pcmEndTimer); pcmEndTimer = null; }

    const chunkDurationMs = (audioBuffer.length / sampleRate) * 1000;

    if (!pcmStream) {
      // 第一个块：从当前时间开始播放
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.playbackRate.value = pcmPlaybackRate;
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0.8;
      source.connect(gainNode);
      gainNode.connect(ctx.destination);
      const analyser = ensureAnalyser();
      if (analyser) source.connect(analyser);
      source.start(0);
      if (ctx.state === "running") pcmOnScheduled?.();

      pcmStream = {
        startTime: ctx.currentTime,
        nextTime: ctx.currentTime + audioBuffer.duration / pcmPlaybackRate,
        lastSource: source,
        sources: new Set([source]),
      };

      // 进度上报
      if (pcmOnProgress) {
        pcmProgressTimer = setInterval(() => {
          if (runId !== pcmRunId || !pcmStream) return;
          const elapsedMs = Math.min(Math.max((ctx.currentTime - pcmStream.startTime) * 1000 * pcmPlaybackRate, 0), pcmAccumulatedMs);
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
        if (runId !== pcmRunId) return;
        pcmStream?.sources?.delete(source);
        if (pcmStream?.lastSource === source) pcmStream.lastSource = null;
      };
    } else {
      // 后续块：在前一块结束后播放
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.playbackRate.value = pcmPlaybackRate;
      const gainNode = ctx.createGain();
      gainNode.gain.value = 0.8;
      source.connect(gainNode);
      gainNode.connect(ctx.destination);
      const analyser = ensureAnalyser();
      if (analyser) source.connect(analyser);
      const scheduledTime = pcmBufferPolicy
        ? pcmBufferPolicy.schedule(ctx.currentTime, pcmStream.nextTime)
        : Math.max(pcmStream.nextTime, ctx.currentTime);
      const gapMs = Math.max(ctx.currentTime - pcmStream.nextTime, 0) * 1000;
      if (gapMs > 1) {
        pcmOnBufferEvent?.({ gapMs, extraBufferMs: Math.max(scheduledTime - Math.max(ctx.currentTime, pcmStream.nextTime), 0) * 1000 });
      }
      // A network stall must not cause later chunks to overlap or advance
      // subtitles through time in which no audio was available.
      pcmStream.startTime += Math.max(scheduledTime - pcmStream.nextTime, 0);
      source.start(scheduledTime);
      pcmStream.nextTime = scheduledTime + audioBuffer.duration / pcmPlaybackRate;
      pcmStream.lastSource = source;
      pcmStream.sources.add(source);

      source.onended = () => {
        source.disconnect();
        gainNode.disconnect();
        if (runId !== pcmRunId) return;
        pcmStream?.sources?.delete(source);
        if (pcmStream?.lastSource === source) {
          pcmStream.lastSource = null;
        }
      };
    }

    pcmAccumulatedMs += chunkDurationMs;
    return true;
  }

  function updatePCMVisemeTimeline(timeline = [], sessionId = null) {
    if (!isCurrentPlaybackSession(sessionId) || !Array.isArray(timeline) || timeline.length === 0) return;
    const byRange = new Map(pcmTimeline.map((item) => [`${item.start}:${item.end}`, item]));
    timeline.forEach((item) => byRange.set(`${item.start}:${item.end}`, item));
    pcmTimeline = [...byRange.values()].sort((a, b) => a.start - b.start);
  }

  function endPCMStream(sessionId = null) {
    if (!isCurrentPlaybackSession(sessionId)) return;
    if (!isPCMStreaming.value) return;
    const runId = pcmRunId;
    const ctx = ensureContext();
    if (pcmEndTimer) clearTimeout(pcmEndTimer);
    const checkDrained = () => {
      if (runId !== pcmRunId) return;
      if (ctx?.state === "suspended") {
        // Wall-clock time can pass while AudioContext time is stopped. Keep
        // the scheduled sources available for explicit stop or resume.
        pcmEndTimer = setTimeout(checkDrained, 250);
        return;
      }
      const remainingMs = pcmStream && ctx
        ? Math.max((pcmStream.nextTime - ctx.currentTime) * 1000, 0)
        : 0;
      if (remainingMs > 1 && ctx?.state !== "closed") {
        pcmEndTimer = setTimeout(checkDrained, Math.max(remainingMs + 80, 120));
        return;
      }
      pcmEndTimer = null;
      stopMouthLoop();
      if (pcmProgressTimer) { clearInterval(pcmProgressTimer); pcmProgressTimer = null; }
      isPlaying.value = false;
      const onAudioEnded = pcmOnAudioEnded;
      resetPCMStream(ctx?.state === "closed");
      onAudioEnded?.();
    };
    const remainingMs = pcmStream && ctx ? Math.max((pcmStream.nextTime - ctx.currentTime) * 1000, 0) : 0;
    pcmEndTimer = setTimeout(checkDrained, Math.max(remainingMs + 80, 120));
  }

  sharedAudioPlayer = {
    queue, isPlaying, isSupported, mouthEnergy, mouthAnalysisActive, isPCMStreaming, activePlayback,
    claimPlayback, enqueue, flush, stop, unlock,
    // PCM 流式播放
    startPCMStream, feedPCMChunk, updatePCMVisemeTimeline, endPCMStream,
  };
  return sharedAudioPlayer;
}
