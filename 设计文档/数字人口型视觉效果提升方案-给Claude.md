# 数字人口型视觉效果提升方案 — 给 Claude 实施

> **核心问题**：当前口型基于纯数学（正弦波/进度百分比猜），与真实音频信号零关联，2D 模型视觉上尤显机械。
> **核心方案**：用 Web Audio API AnalyserNode 实时分析音频振幅/频谱，驱动口型参数 + 视觉包装（头部微动、眼睑联动、物理包络）。

---

## 一、为什么 2D 模型的口型看起来"不好"

```
真实人说话：
  振幅自然波动 ──→ 嘴开合深度变化 ──→ 辅音闭嘴/元音张合 ──→ 头部微微点头
                    ├─ 快攻慢退（attack 快 decay 慢）
                    └─ 停顿时完全闭嘴

当前 2D Live2D 说话：
  Math.sin(frame * 0.15) * 0.5 ──→ 匀速正弦波 ──→ 嘴匀速张合
                                     ├─ 节奏完全规律（机器人感）
                                     ├─ 从不完全闭嘴（50% baseline）
                                     └─ 头部静止
```

**2D 模型的天然劣势**：只有 `ParamMouthOpenY` 一个口型参数（经查 haru_greeter_t03 的 LipSync Group 仅此一项），无法像 3D 那样做复杂口型形状 morph。所以更需要用**真实音频信号 + 物理包络 + 头部联动**来弥补。

---

## 二、方案核心：AnalyserNode 实时音频驱动（改动 useAudioPlayer.js）

### 原理

```
Web Audio 音频图：

  source (BufferSource)
    │
    ├──→ analyserNode ──→ ctx.destination (扬声器)
    │         │
    │     每帧读取 fftData
    │         │
    │     RMS 振幅 → 0~1
    │         │
    └─────────┴──→ Live2DAvatar 拿振幅驱动 ParamMouthOpenY
```

### Step 1：改造 useAudioPlayer.js

**文件**：`frontend/src/composables/useAudioPlayer.js`

**操作**：用以下内容**完整替换**文件（改动标注了 ★ 号）：

```javascript
import { ref } from "vue";

// ★ 暴露给外部读取的口型值（模块级单例）
let analyserNode = null;
let analyserData = null;
let lastMouthEnergy = 0;

export function useAudioPlayer() {
  const isPlaying = ref(false);
  const queue = ref([]);
  const mouthEnergy = ref(0); // ★ 0~1，实时音频振幅 → 口型值

  let audioContext = null;
  let currentSource = null;
  let currentUtterance = null;
  let stopGeneration = 0;
  let mouthSimTimer = null; // ★ 方案B 语音模拟口型用

  const checkSupported =
    typeof window !== "undefined" &&
    typeof window.AudioContext !== "undefined";

  const isSupported = ref(checkSupported);

  const speechSynthSupported =
    typeof window !== "undefined" &&
    typeof window.speechSynthesis !== "undefined";

  function ensureContext() {
    if (!audioContext && checkSupported) {
      try {
        audioContext = new AudioContext();
      } catch {
        isSupported.value = false;
      }
    }
    return audioContext;
  }

  // ★ 创建/获取共享的 AnalyserNode
  function ensureAnalyser() {
    const ctx = ensureContext();
    if (!ctx) return null;
    if (!analyserNode) {
      analyserNode = ctx.createAnalyser();
      analyserNode.fftSize = 512; // 512 采样点，足够分辨振幅变化
      analyserNode.smoothingTimeConstant = 0.4;
      analyserNode.connect(ctx.destination);
      analyserData = new Uint8Array(analyserNode.fftSize);
    }
    return analyserNode;
  }

  // ★ 从 analyser 读取当前振幅 → 口型值
  function readMouthEnergy() {
    if (!analyserNode || !analyserData) return 0;
    analyserNode.getByteTimeDomainData(analyserData);

    // RMS (root mean square) = 实际音频能量
    let sum = 0;
    for (let i = 0; i < analyserData.length; i++) {
      const v = (analyserData[i] - 128) / 128; // -1 ~ 1
      sum += v * v;
    }
    const rms = Math.sqrt(sum / analyserData.length);

    // 映射到 0~1：RMS 一般 0~0.3 是正常音量，乘 3.5 映射到 0~1 左右
    // 用物理包络：快速攀升、缓慢衰减
    const raw = Math.min(rms * 3.5, 1);
    const attack = 0.25;  // 攻击速度（快）
    const decay = 0.08;   // 衰减速度（慢）→ 模拟真实说话

    if (raw > lastMouthEnergy) {
      lastMouthEnergy += (raw - lastMouthEnergy) * attack;
    } else {
      lastMouthEnergy += (raw - lastMouthEnergy) * decay;
    }
    return lastMouthEnergy;
  }

  // ★ 启动 rAF 循环持续读取振幅
  function startMouthLoop() {
    stopMouthLoop();
    const tick = () => {
      mouthEnergy.value = readMouthEnergy();
      mouthSimTimer = requestAnimationFrame(tick);
    };
    mouthSimTimer = requestAnimationFrame(tick);
  }

  function stopMouthLoop() {
    if (mouthSimTimer) {
      cancelAnimationFrame(mouthSimTimer);
      mouthSimTimer = null;
    }
    lastMouthEnergy = 0;
    mouthEnergy.value = 0;
  }

  async function base64ToAudioBuffer(base64String) {
    const ctx = ensureContext();
    if (!ctx || !base64String) return null;

    try {
      if (ctx.state === "suspended") await ctx.resume();
      const normalized = base64String.includes(",")
        ? base64String.slice(base64String.indexOf(",") + 1)
        : base64String;
      const binary = atob(normalized);
      if (!binary.length) return null;
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      return await ctx.decodeAudioData(bytes.buffer.slice(0));
    } catch {
      return null;
    }
  }

  async function playAudioBuffer(audioBuffer, onProgress) {
    const ctx = ensureContext();
    if (!ctx || audioBuffer === null) return 0;

    return new Promise((resolve) => {
      const source = ctx.createBufferSource();
      currentSource = source;
      source.buffer = audioBuffer;

      // ★ 关键改动：source → analyser → destination
      const analyser = ensureAnalyser();
      if (analyser) {
        source.connect(analyser);
        // analyser 已经 connect 到 destination
      } else {
        source.connect(ctx.destination);
      }

      startMouthLoop(); // ★ 开始持续读取振幅

      const startTime = ctx.currentTime;
      const duration = audioBuffer.duration;

      let progressTimer = null;
      if (onProgress) {
        progressTimer = setInterval(() => {
          const elapsed = (ctx.currentTime - startTime) * 1000;
          const progress = Math.min(elapsed / (duration * 1000), 1);
          onProgress(progress, elapsed);
        }, 30);
      }

      source.onended = () => {
        currentSource = null;
        stopMouthLoop(); // ★ 停止读取
        if (progressTimer) {
          clearInterval(progressTimer);
          if (onProgress) onProgress(1, duration * 1000);
        }
        resolve(audioBuffer.duration * 1000);
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
      const finish = () => {
        if (settled) return;
        settled = true;
        window.speechSynthesis.removeEventListener("voiceschanged", handleVoicesChanged);
        resolve(getChineseVoice());
      };
      const handleVoicesChanged = () => finish();
      window.speechSynthesis.addEventListener("voiceschanged", handleVoicesChanged);
      window.setTimeout(finish, timeoutMs);
    });
  }

  // ★ 方案B 口型模拟：根据文字内容生成人工口型轨迹
  function generateMouthFromText(text) {
    if (!text) return;
    const chars = [...text];
    const totalMs = chars.length * 180;
    let elapsed = 0;
    const interval = 50; // 50ms 一帧

    stopMouthLoop();
    let energy = 0;

    const vowelChars = new Set(
      "aeiouAEIOUaeiouvnm龙空红中公宫翁东通送aeliouvnmàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþāăąċčďđēėęěĝğġģĥħĩīĭįıĳĵķĺļľŀłńņňŋōŏőœŕŗřśŝşšţťŧũūŭůűųŵŷźżž"
    );

    mouthSimTimer = setInterval(() => {
      elapsed += interval;
      if (elapsed > totalMs) {
        stopMouthLoop();
        mouthEnergy.value = 0;
        return;
      }

      const idx = Math.floor(elapsed / (totalMs / chars.length));
      const char = chars[Math.min(idx, chars.length - 1)];

      // 元音/鼻音 → 高能量，辅音 → 低能量
      const isVowel = vowelChars.has(char);
      const targetEnergy = isVowel ? 0.3 + Math.random() * 0.5 : 0.05 + Math.random() * 0.1;

      // 同样的物理包络
      if (targetEnergy > energy) {
        energy += (targetEnergy - energy) * 0.25;
      } else {
        energy += (targetEnergy - energy) * 0.08;
      }

      mouthEnergy.value = Math.min(energy, 1);
    }, interval);
  }

  async function playSpeechSynthesis(text, durationMs, onProgress) {
    if (!speechSynthSupported) return 0;

    return new Promise((resolve) => {
      if (currentUtterance) window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "zh-CN";
      utterance.rate = 1.0;
      utterance.pitch = 1.1;
      utterance.volume = 1.0;

      const startTime = Date.now();
      const estimatedDuration = Math.max(durationMs || text.length * 180, 800);
      let progressTimer = null;

      const reportProgress = (p) => {
        onProgress?.(Math.min(Math.max(p, 0), 1), Date.now() - startTime);
      };

      const finish = (duration) => {
        if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
        stopMouthLoop();
        reportProgress(1);
        currentUtterance = null;
        resolve(duration);
      };

      utterance.onstart = () => {
        reportProgress(0);
        generateMouthFromText(text); // ★ 方案B 口型模拟启动
        progressTimer = setInterval(() => {
          reportProgress((Date.now() - startTime) / estimatedDuration);
        }, 50);
      };

      utterance.onboundary = (event) => {
        if (text.length > 0 && Number.isFinite(event.charIndex)) {
          reportProgress(event.charIndex / text.length);
        }
      };

      utterance.onend = () => finish(Date.now() - startTime);
      utterance.onerror = () => finish(0);

      waitForChineseVoice().then((zhVoice) => {
        if (zhVoice) utterance.voice = zhVoice;
        currentUtterance = utterance;
        window.speechSynthesis.speak(utterance);
      });
    });
  }

  async function enqueue(base64, durationMs = 800, onEnded, text = "", onProgress) {
    queue.value.push({ base64, durationMs, onEnded, text, onProgress });
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
        await playAudioBuffer(audioBuffer, current.onProgress);
      } else if (current.text && speechSynthSupported) {
        await playSpeechSynthesis(current.text, current.durationMs, current.onProgress);
      } else {
        current.onProgress?.(0, 0);
        await new Promise((r) => setTimeout(r, Math.min(current.durationMs, 3000)));
        current.onProgress?.(1, current.durationMs);
      }

      if (generation === stopGeneration && current.onEnded) current.onEnded();
    }
    isPlaying.value = false;
    stopMouthLoop(); // ★ 安全兜底
  }

  function stop() {
    stopGeneration += 1;
    stopMouthLoop(); // ★
    if (currentSource) { try { currentSource.stop(); } catch {} currentSource = null; }
    if (currentUtterance) { window.speechSynthesis.cancel(); currentUtterance = null; }
    queue.value = [];
    isPlaying.value = false;
  }

  return {
    queue,
    isPlaying,
    isSupported,
    mouthEnergy, // ★ 暴露给 Live2DAvatar
    enqueue,
    flush,
    stop,
  };
}
```

**改动总结**：
- 第 13~16 行：模块级 `analyserNode` / `analyserData` / `lastMouthEnergy`
- 第 18 行：暴露 `mouthEnergy` ref
- 第 54~62 行：`ensureAnalyser()` 创建共享 AnalyserNode
- 第 65~88 行：`readMouthEnergy()` — **核心**：RMS 振幅 + attack/decay 物理包络
- 第 91~103 行：`startMouthLoop()` / `stopMouthLoop()` — rAF 持续驱动
- 第 115 行：`playAudioBuffer` 中 `source.connect(analyser)` 而非直接连 destination
- 第 174~206 行：`generateMouthFromText()` — 方案B 的文本→口型模拟
- 第 254 行：返回 `mouthEnergy`

---

## 三、Step 2：Live2DAvatar 听觉化驱动（替换文件）

**文件**：`frontend/src/components/Live2DAvatar.vue`

**操作**：用以下内容**完整替换**。核心改动：用 `mouthEnergy` 替代 `speechProgress`/`visemeTimeline`；新增头部微动 + 眼睑联动 + 口型平滑。

```vue
<template>
  <div class="live2d-wrapper">
    <div v-if="loading" class="live2d-loading">加载中...</div>
    <div v-if="error" class="live2d-error">{{ error }}</div>
    <div ref="canvasContainer" class="live2d-container" />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as PIXI from "pixi.js";

import { DEFAULT_MODEL_KEY, useModelManager } from "../composables/useModelManager";
import { useAudioPlayer } from "../composables/useAudioPlayer";

window.PIXI = PIXI;

const audioPlayer = useAudioPlayer(); // ★ 拿取音频口型值

const emit = defineEmits(["load-error"]);

const props = defineProps({
  emotion: { type: String, default: "neutral" },
  isSpeaking: { type: Boolean, default: false },
  modelKey: { type: String, default: DEFAULT_MODEL_KEY },
});

const canvasContainer = ref(null);
const loading = ref(true);
const error = ref("");

const CANVAS_WIDTH = 480;
const CANVAS_HEIGHT = 720;
const MODEL_PADDING_X = 28;
const MODEL_PADDING_TOP = 44;
const MODEL_PADDING_BOTTOM = 24;

let app = null;
let model = null;
let modelManager = null;
let animFrameId = null;

// ★ 口型物理状态
let mouthCurrent = 0;       // 当前口型值（平滑后）
let headBounceOffset = 0;   // 头部上下偏移
let headPhase = 0;          // 头部动画相位
let idleBreathValue = 0;    // 空闲呼吸值
let idleBlinkTimer = null;

// ---- 空闲动画（呼吸 + 眨眼） ----
function startIdleAnimations() {
  stopIdleAnimations();
  idleBlinkTimer = setTimeout(scheduleBlink, 2000 + Math.random() * 3000);
}

let idleAnimPhase = 0;
let idleAnimTimer = null;

function startIdleLoop() {
  stopIdleLoop();
  idleAnimTimer = setInterval(() => {
    if (!model) return;
    idleAnimPhase += 0.03;
    // 呼吸
    const breath = 0.5 + 0.5 * Math.sin(idleAnimPhase);
    try {
      model.internalModel.coreModel.setParameterValueById("ParamBreath", breath);
    } catch {}
  }, 50);
}

function stopIdleLoop() {
  if (idleAnimTimer) { clearInterval(idleAnimTimer); idleAnimTimer = null; }
}

function stopIdleAnimations() {
  stopIdleLoop();
  if (idleBlinkTimer) { clearTimeout(idleBlinkTimer); idleBlinkTimer = null; }
}

function scheduleBlink() {
  idleBlinkTimer = setTimeout(() => {
    if (!model) return;
    try {
      model.internalModel.coreModel.setParameterValueById("ParamEyeLOpen", 0);
      model.internalModel.coreModel.setParameterValueById("ParamEyeROpen", 0);
    } catch {}
    setTimeout(() => {
      if (!model) return;
      try {
        model.internalModel.coreModel.setParameterValueById("ParamEyeLOpen", 1);
        model.internalModel.coreModel.setParameterValueById("ParamEyeROpen", 1);
      } catch {}
      scheduleBlink();
    }, 100);
  }, 2000 + Math.random() * 3000);
}

// ---- ★ 核心：音频驱动的口型 + 头部 + 眼睑 ----
function startSpeechAnimation() {
  if (animFrameId) return;
  stopIdleAnimations();

  const tick = () => {
    if (!model) {
      animFrameId = requestAnimationFrame(tick);
      return;
    }

    // 1. 口型：从 audioPlayer 读取实时振幅
    const rawEnergy = audioPlayer.mouthEnergy.value || 0;
    // 平滑过渡（lerp 0.3 保证跟得上音频节奏）
    mouthCurrent += (rawEnergy - mouthCurrent) * 0.3;
    const mouth = Math.min(Math.max(mouthCurrent, 0), 1);

    try {
      model.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", mouth);
    } catch {}

    // 2. ★ 头部微动：说话时轻微点头 / 左右晃动
    headPhase += 0.04;
    const headNod = Math.sin(headPhase * 1.7) * 1.8 * mouth;  // 张嘴时点头幅度大
    const headTilt = Math.cos(headPhase * 0.9) * 0.6 * mouth; // 轻微歪头

    try {
      // 尝试设置头部相关参数（如果模型支持）
      model.internalModel.coreModel.setParameterValueById("ParamAngleX", headTilt);
      model.internalModel.coreModel.setParameterValueById("ParamAngleY", headNod);
      model.internalModel.coreModel.setParameterValueById("ParamAngleZ", headTilt * 0.5);
    } catch {}

    // 3. ★ 身体呼吸：说话时不完全静止
    const bodySway = Math.sin(headPhase * 0.6) * 1.5 * mouth;
    try {
      model.internalModel.coreModel.setParameterValueById("ParamBodyAngleX", bodySway * 0.3);
      model.internalModel.coreModel.setParameterValueById("ParamBodyAngleY", bodySway);
    } catch {}

    // 4. ★ 眼睑微动：说话时眼睛微微眯起（自然反应）
    const eyeSquint = 1 - mouth * 0.15;
    try {
      model.internalModel.coreModel.setParameterValueById("ParamEyeLOpen", eyeSquint);
      model.internalModel.coreModel.setParameterValueById("ParamEyeROpen", eyeSquint);
    } catch {}

    animFrameId = requestAnimationFrame(tick);
  };

  animFrameId = requestAnimationFrame(tick);
}

function stopSpeechAnimation() {
  if (animFrameId) {
    cancelAnimationFrame(animFrameId);
    animFrameId = null;
  }
  // 逐渐回到空闲
  mouthCurrent = 0;
  headPhase = 0;
  try {
    model?.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", 0);
    model?.internalModel.coreModel.setParameterValueById("ParamEyeLOpen", 1);
    model?.internalModel.coreModel.setParameterValueById("ParamEyeROpen", 1);
    model?.internalModel.coreModel.setParameterValueById("ParamAngleX", 0);
    model?.internalModel.coreModel.setParameterValueById("ParamAngleY", 0);
    model?.internalModel.coreModel.setParameterValueById("ParamAngleZ", 0);
    model?.internalModel.coreModel.setParameterValueById("ParamBodyAngleX", 0);
    model?.internalModel.coreModel.setParameterValueById("ParamBodyAngleY", 0);
  } catch {}
  startIdleAnimations();
}

// ---- 表情 ----
function applyEmotion(emotion) {
  if (!model) return;
  const map = { happy: "f01", apology: "f04", neutral: "f00" };
  try { model.expression(map[emotion] || "f00"); } catch {}
}

// ---- 模型 ----
function fitModelToCanvas() {
  if (!model) return;
  model.scale.set(1);
  const bounds = model.getLocalBounds();
  const availableWidth = CANVAS_WIDTH - MODEL_PADDING_X * 2;
  const availableHeight = CANVAS_HEIGHT - MODEL_PADDING_TOP - MODEL_PADDING_BOTTOM;
  const fitScale = Math.min(availableWidth / bounds.width, availableHeight / bounds.height);
  const safeScale = Number.isFinite(fitScale) && fitScale > 0 ? fitScale : 0.1;
  model.scale.set(safeScale);
  model.pivot.set(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);
  model.position.set(CANVAS_WIDTH / 2, MODEL_PADDING_TOP + availableHeight / 2);
}

// ---- 生命周期 ----
onMounted(async () => {
  try {
    app = new PIXI.Application({
      width: CANVAS_WIDTH, height: CANVAS_HEIGHT,
      backgroundAlpha: 0, antialias: true,
    });
    canvasContainer.value.appendChild(app.view);
    modelManager = useModelManager(app);
    await loadModel(props.modelKey);
  } catch (err) { handleLoadError(err, "数字人加载失败"); }
});

onBeforeUnmount(() => {
  stopSpeechAnimation();
  stopIdleAnimations();
  modelManager?.destroy();
  if (app) { app.destroy(true); app = null; }
});

watch(() => props.emotion, (e) => applyEmotion(e));

watch(() => props.isSpeaking, (speaking) => {
  if (!model) return;
  if (speaking) startSpeechAnimation();
  else stopSpeechAnimation();
});

async function loadModel(modelKey) {
  loading.value = true; error.value = "";
  model = await modelManager.switchModel(modelKey, {
    x: CANVAS_WIDTH / 2, y: CANVAS_HEIGHT / 2,
    onProgress: (s) => { loading.value = s === "loading"; },
  });
  fitModelToCanvas();
  requestAnimationFrame(() => fitModelToCanvas());
  applyEmotion(props.emotion);
  if (props.isSpeaking) startSpeechAnimation();
  else startIdleAnimations();
  loading.value = false;
}

function handleLoadError(err, msg) {
  console.error("Live2D error:", err);
  error.value = msg; loading.value = false;
  emit("load-error", err);
}

async function handleSwitchModel(key) {
  try { await loadModel(key); }
  catch (err) { handleLoadError(err, "模型切换失败"); }
}

defineExpose({ switchModel: handleSwitchModel });
</script>

<style>
.live2d-wrapper { position: relative; width: 480px; height: 720px; }
.live2d-container { width: 100%; height: 100%; overflow: hidden; border-radius: 12px; }
.live2d-container canvas { width: 100% !important; height: 100% !important; }
.live2d-loading, .live2d-error {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  padding: 12px 20px; border-radius: 8px;
  background: rgba(255, 255, 255, 0.9); font-size: 14px; z-index: 10;
}
.live2d-error { color: #f56c6c; }
</style>
```

**改动总结**（相比当前代码）：

| 改动 | 效果 |
|------|------|
| `import { useAudioPlayer }` + `const audioPlayer = useAudioPlayer()` | 直接读取音频振幅 |
| `startSpeechAnimation()` 用 rAF 替代 setInterval | 流畅 60fps 驱动 |
| `mouthCurrent = audioPlayer.mouthEnergy` + lerp 0.3 | 口型 = 真实音频信号 |
| `ParamAngleX/Y/Z` 随 mouth 联动 | 说话时点头/歪头 |
| `ParamEyeLOpen/ROpen = 1 - mouth*0.15` | 说话时微眯眼 |
| `ParamBodyAngleX/Y` | 身体轻微晃动 |
| `startIdleAnimations()` / `startIdleLoop()` | 不说话时呼吸+眨眼 |
| 删除 `speechProgress` / `visemeTimeline` / `speechSyncActive` props | 不再需要这些，由音频直接驱动 |

---

## 四、Step 3：ChatView 清理（可选，向后兼容）

**文件**：`frontend/src/views/tourist/ChatView.vue`

Live2DAvatar 不再需要 `:speech-progress` 和 `:viseme-timeline` props。可以删除这两行绑定（不删也不会报错，Vue 会忽略多余 props）。

```html
<!-- 删除这两行 -->
:speech-progress="speechProgress"
:viseme-timeline="visemeTimeline"
```

同时删除对应的 ref：

```javascript
// 删除
const speechProgress = ref(0);
const visemeTimeline = ref([]);
```

以及 `submitQuery` 中的 `onSpeechProgress` 回调。

---

## 五、效果对比

| | 当前 | 改造后 |
|------|------|------|
| 口型驱动源 | `Math.sin(frameCount*0.15)*0.5` | **Web Audio API 实时音频振幅** |
| 更新频率 | 50ms setInterval | **requestAnimationFrame (60fps)** |
| 是否跟随音频 | ❌ 完全无关 | ✅ **真实音频 → 口型** |
| 闭嘴时机 | 正弦波默认 50% baseline | **静音时真正闭嘴** |
| 头部动作 | ❌ 静止不动 | ✅ 点头 + 微歪头（随说话幅度） |
| 眼睛 | ❌ 无变化 | ✅ 说话时微眯 |
| 身体 | ❌ 僵硬 | ✅ 轻微自然晃动 |
| 空闲态 | ❌ 无动画 | ✅ 呼吸 + 随机眨眼 |
| 攻击/衰减 | 无 | ✅ fast attack + slow decay 物理包络 |
| 方案B兼容 | 固定正弦波 | ✅ 文本→元音频率模拟 |

---

## 六、验证

```bash
cd frontend && npm run dev
```

1. 打开游客端，发送问题
2. Chrome DevTools → 开一个 Console tab，观察无报错
3. 观察数字人嘴：应该能看到**张嘴幅度随音频节奏变化**，停顿时闭嘴
4. 观察头部：说话时微微点头
5. 观察眼睛：说话时稍微眯眼
6. 不说话时：呼吸 + 眨眼空闲动画

**方案B 验证**（断网或后端 TTS 失败时）：
7. 听到浏览器原生语音时，嘴应该跟随文字元音规律张合

---

## ⚠️ 注意

1. `useAudioPlayer` **作为模块级单例**被 `chat.js` 和 `Live2DAvatar.vue` 同时引用——这是设计意图，确保 AnalyserNode 是同一个实例
2. 如果某些 Live2D 参数（ParamAngleX 等）在特定模型上不存在，catch 会静默忽略，不影响渲染
3. `fftSize = 512`，采样点足够区分振幅变化，也不需要太高性能消耗
4. `attack = 0.25` / `decay = 0.08` 是人为调参值，可以微调但不能差太多（attack 过慢 → 嘴跟不上声音；decay 过快 → 嘴抽搐感）
