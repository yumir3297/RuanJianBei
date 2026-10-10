import { ref } from "vue";

const WORKLET_URL = "/recorder-worklet.js";

function writeAscii(view, offset, value) {
  for (let index = 0; index < value.length; index += 1) {
    view.setUint8(offset + index, value.charCodeAt(index));
  }
}

function encodeMonoWav(chunks, sampleRate) {
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + sampleCount * 2);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + sampleCount * 2, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, sampleCount * 2, true);

  let offset = 44;
  for (const chunk of chunks) {
    for (let index = 0; index < chunk.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, chunk[index]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += 2;
    }
  }
  return new Blob([buffer], { type: "audio/wav" });
}

export function useRecorder() {
  const isRecording = ref(false);
  const isSupported = ref(false);
  const durationSeconds = ref(0);

  let stream = null;
  let audioContext = null;
  let sourceNode = null;
  let workletNode = null; // AudioWorklet 采集（独立音频线程）
  let processorNode = null; // ScriptProcessor 降级（主线程回调）
  let silentGainNode = null;
  let chunks = [];
  let capturing = false;
  let durationTimer = null;

  const AudioContextClass =
    typeof window !== "undefined" ? window.AudioContext || window.webkitAudioContext : null;
  isSupported.value = Boolean(
    typeof navigator !== "undefined"
      && navigator.mediaDevices?.getUserMedia
      && AudioContextClass,
  );

  async function start() {
    if (!isSupported.value || isRecording.value) {
      return null;
    }

    try {
      // 关闭浏览器音频处理（回声消除/降噪/自动增益）：
      // 部分设备上降噪会把人声误判为噪音，只放行开头一个音节后静音
      // （现象：ASR 只识别出第一个字）。手动按住录音期间不会同时播放 TTS，
      // 不依赖回声消除，采集原始信号交给 SenseVoice 处理。
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });
      audioContext = new AudioContextClass();
      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }
    } catch {
      await cleanup();
      return null;
    }

    chunks = [];
    capturing = false;
    durationSeconds.value = 0;
    sourceNode = audioContext.createMediaStreamSource(stream);
    silentGainNode = audioContext.createGain();
    silentGainNode.gain.value = 0;

    let captureMode = "worklet";
    try {
      // 首选 AudioWorklet：回调运行在音频渲染线程，主线程卡顿不会丢音频帧
      await audioContext.audioWorklet.addModule(WORKLET_URL);
      workletNode = new AudioWorkletNode(audioContext, "pcm-recorder", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1],
      });
      workletNode.port.onmessage = (event) => {
        if (capturing && event.data instanceof Float32Array && event.data.length > 0) {
          chunks.push(event.data);
        }
      };
      sourceNode.connect(workletNode);
      workletNode.connect(silentGainNode);
      silentGainNode.connect(audioContext.destination);
      workletNode.port.postMessage("start");
      capturing = true;
    } catch {
      // 降级 ScriptProcessor：主线程高负载（如 3D 数字人渲染）时可能静默丢帧
      captureMode = "script";
      if (workletNode) {
        try { workletNode.port.onmessage = null; } catch {}
        try { workletNode.disconnect(); } catch {}
        workletNode = null;
      }
      processorNode = audioContext.createScriptProcessor(4096, sourceNode.channelCount || 1, 1);
      processorNode.onaudioprocess = (event) => {
        if (!capturing) {
          return;
        }
        const input = event.inputBuffer;
        const channelCount = input.numberOfChannels;
        const mono = new Float32Array(input.length);
        for (let channel = 0; channel < channelCount; channel += 1) {
          const samples = input.getChannelData(channel);
          for (let index = 0; index < samples.length; index += 1) {
            mono[index] += samples[index] / channelCount;
          }
        }
        chunks.push(mono);
      };
      sourceNode.connect(processorNode);
      processorNode.connect(silentGainNode);
      silentGainNode.connect(audioContext.destination);
      capturing = true;
    }

    isRecording.value = true;
    durationTimer = window.setInterval(() => {
      durationSeconds.value += 1;
    }, 1000);
    console.debug(`[recorder] start (mode=${captureMode}, sampleRate=${audioContext.sampleRate})`);
    return null;
  }

  async function stop() {
    if (!isRecording.value || !audioContext) {
      await cleanup();
      return null;
    }

    isRecording.value = false;
    if (workletNode) {
      // 先通知 worklet 冲刷尾部缓冲，稍等它把最后一块采样发回来
      try { workletNode.port.postMessage("stop"); } catch {}
      await new Promise((resolve) => setTimeout(resolve, 60));
    }
    capturing = false;

    const recordedChunks = chunks;
    const sampleRate = audioContext.sampleRate;
    await cleanup();
    if (recordedChunks.length === 0) {
      return null;
    }
    const blob = encodeMonoWav(recordedChunks, sampleRate);
    const seconds = (blob.size - 44) / 2 / sampleRate;
    console.debug(`[recorder] stop → ${blob.size} bytes ≈ ${seconds.toFixed(2)}s`);
    return blob;
  }

  async function cleanup() {
    isRecording.value = false;
    capturing = false;
    if (durationTimer) {
      window.clearInterval(durationTimer);
      durationTimer = null;
    }
    if (workletNode) {
      try { workletNode.port.onmessage = null; } catch {}
      try { workletNode.disconnect(); } catch {}
      workletNode = null;
    }
    if (processorNode) {
      processorNode.onaudioprocess = null;
      processorNode.disconnect();
      processorNode = null;
    }
    sourceNode?.disconnect();
    silentGainNode?.disconnect();
    sourceNode = null;
    silentGainNode = null;
    stream?.getTracks().forEach((track) => track.stop());
    stream = null;
    if (audioContext && audioContext.state !== "closed") {
      try {
        await audioContext.close();
      } catch {}
    }
    audioContext = null;
    chunks = [];
  }

  return {
    isRecording,
    isSupported,
    durationSeconds,
    start,
    stop,
  };
}
