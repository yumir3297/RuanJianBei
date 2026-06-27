# 数字人开发执行方案 — 给 Claude 实施

> 按阶段顺序执行，每完成一个阶段运行 `npm run dev` 确认不崩，再进入下一阶段。
> 所有改动都在 `frontend/` 下，后端暂时不动。

---

## 当前数字人现状速览

```
Live2DAvatar.vue   ← PIXI + pixi-live2d-display 渲染 Shizuku 模型 ✅
useAvatar.js       ← 状态机（idle/listening/thinking/speaking/happy/apology）✅
AvatarDisplay.vue  ← SVG 降级头像（6 种状态动画）✅
useAudioPlayer.js  ← TTS 音频队列播放 ✅
chat.js store      ← SSE 流式接收 avatar/audio/text_chunk 事件 ✅
AvatarConfig.vue   ← 占位页，只有一句提示文字 ❌
```

**核心差距：口型同步目前只是 150ms 简单 toggle，不是真正的 viseme 音素同步。**

---

## 🎯 赛题评分中数字人相关项

| 赛题要求 | 来源图片 | 现状 | 优先级 |
|----------|----------|------|--------|
| 口型同步，"说话时嘴动" | 02 口型与表情驱动要求 | ❌ 150ms toggle | 🔴 P0 |
| 表情配合语义与情感 | 02 表情配合 | ⚠️ 仅 3 种表情 | 🟡 P1 |
| 形象多样化选择（管理端配置） | 01 形象要求 | ❌ 占位页 | 🟡 P1 |
| 风格逼真、贴合景区氛围 | 01 形象要求 | ✅ Shizuku 可接受 | 🟢 已就绪 |
| 动作（点头、指向等）加分项 | 02 动作可选 | ❌ 无 motion | 🟢 P2 加分 |
| 2D 数字人 | 02 2D/3D | ✅ 已选 2D | 🟢 已就绪 |

---

# 📦 一阶段：真口型同步 + TTS 音频联动（P0，约15分）

## 1.1 目标

让数字人在播放 TTS 语音时，嘴巴开合跟随音素序列精确运动，而非当前 150ms 盲 toggle。

## 1.2 数据流约定

```
后端 SSE 事件格式（需要后端配合给出）：
event: avatar
data: {"visemes": [{"time_ms": 0, "value": 0.8}, {"time_ms": 150, "value": 0.0}, ...], "emotion": "happy"}

event: audio  
data: {"base64": "...", "duration_ms": 3200, "viseme_timeline": [{"t": 0, "mouth": 0.8}, {"t": 120, "mouth": 0.0}, ...]}
```

**如果后端暂时没有 viseme_timeline**，前端用纯客户端方案兜底：基于音频播放进度 + 正弦波模拟口型。

---

## 1.3 修改步骤

### Step 1.1：改造 `useAudioPlayer.js` — 支持播放进度回调

**文件**：`frontend/src/composables/useAudioPlayer.js`

**操作**：完整替换文件内容为：

```javascript
import { ref } from "vue";

export function useAudioPlayer() {
  const isPlaying = ref(false);
  const queue = ref([]);
  const currentProgress = ref(0); // 0~1
  const currentDuration = ref(0);

  let audioContext = null;

  const checkSupported =
    typeof window !== "undefined" &&
    typeof window.AudioContext !== "undefined";

  const isSupported = ref(checkSupported);

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

  async function base64ToAudioBuffer(base64String) {
    const ctx = ensureContext();
    if (!ctx) return null;
    const binary = atob(base64String);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    try {
      return await ctx.decodeAudioData(bytes.buffer.slice(0));
    } catch {
      return null;
    }
  }

  /**
   * 播放单段音频，同时回调进度
   * @param {AudioBuffer} audioBuffer
   * @param {Function|null} onProgress - (progress01: number, elapsedMs: number) => void
   * @returns {number} 音频时长 ms
   */
  async function playAudioBuffer(audioBuffer, onProgress) {
    const ctx = ensureContext();
    if (!ctx || audioBuffer === null) return 0;

    return new Promise((resolve) => {
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      const startTime = ctx.currentTime;
      const durationSec = audioBuffer.duration;

      // 用定时器模拟进度（每 30ms 回调一次，约 33fps 驱动口型足够）
      let timer = null;
      const startWall = performance.now();

      timer = setInterval(() => {
        const elapsed = (ctx.currentTime - startTime) * 1000;
        const progress = Math.min(elapsed / (durationSec * 1000), 1);
        currentProgress.value = progress;
        currentDuration.value = durationSec * 1000;
        if (onProgress) {
          onProgress(progress, elapsed);
        }
        if (progress >= 1 && timer) {
          clearInterval(timer);
        }
      }, 30);

      source.onended = () => {
        if (timer) clearInterval(timer);
        currentProgress.value = 1;
        if (onProgress) onProgress(1, durationSec * 1000);
        resolve(durationSec * 1000);
      };
      source.start(0);
    });
  }

  /** enqueue 新增 onProgress 回调 */
  async function enqueue(base64, durationMs = 800, onEnded, onProgress) {
    queue.value.push({ base64, durationMs, onEnded, onProgress });
    if (!isPlaying.value) {
      await flush();
    }
  }

  async function flush() {
    if (isPlaying.value) return;
    isPlaying.value = true;

    while (queue.value.length > 0) {
      const current = queue.value.shift();
      const audioBuffer = await base64ToAudioBuffer(current.base64);
      if (audioBuffer) {
        await playAudioBuffer(audioBuffer, current.onProgress);
      } else {
        await new Promise((r) =>
          window.setTimeout(r, Math.min(current.durationMs, 3000))
        );
      }
      if (current.onEnded) current.onEnded();
    }
    isPlaying.value = false;
    currentProgress.value = 0;
  }

  return {
    queue,
    isPlaying,
    isSupported,
    currentProgress,
    currentDuration,
    enqueue,
    flush,
  };
}
```

---

### Step 1.2：重写 `Live2DAvatar.vue` 口型系统

**文件**：`frontend/src/components/Live2DAvatar.vue`

**操作**：用以下内容完整替换文件（关键改动在第 89~145 行的口型方法）：

```vue
<template>
  <div class="live2d-wrapper">
    <div v-if="loading" class="live2d-loading">加载中...</div>
    <div v-if="error" class="live2d-error">{{ error }}</div>
    <div ref="canvasContainer" class="live2d-container" />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import * as PIXI from "pixi.js";
import { Live2DModel } from "pixi-live2d-display/cubism4";

window.PIXI = PIXI;

const emit = defineEmits(["load-error"]);

const props = defineProps({
  emotion: { type: String, default: "neutral" },
  isSpeaking: { type: Boolean, default: false },
  /** 音频播放进度 0~1 */
  speechProgress: { type: Number, default: 0 },
  /** viseme 时间线 [{t: ms, mouth: 0~1}] */
  visemeTimeline: { type: Array, default: () => [] },
  modelPath: {
    type: String,
    default: "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display/test/assets/shizuku/shizuku.model.json"
  },
});

const canvasContainer = ref(null);
const loading = ref(true);
const error = ref("");
const CANVAS_WIDTH = 480;
const CANVAS_HEIGHT = 720;
const MODEL_PADDING = 24;

let app = null;
let model = null;
let idleBreathTimer = null;
let blinkTimer = null;

// ---- 内置空闲动作（呼吸 + 眨眼） ----
const BREATH_PERIOD = 3800; // ms，一个呼吸周期

function startIdleAnimations() {
  stopIdleAnimations();
  if (!model) return;

  // 呼吸动画：ParamBreath 在 0~1 之间缓慢浮动
  let breathPhase = 0;
  idleBreathTimer = setInterval(() => {
    if (!model) return;
    breathPhase += 0.05;
    const breath = 0.5 + 0.5 * Math.sin(breathPhase);
    try {
      model.internalModel.coreModel.setParameterValueById("ParamBreath", breath);
    } catch {}
  }, 50);

  // 眨眼：随机间隔 2~5 秒闭眼 100ms
  const scheduleBlink = () => {
    blinkTimer = setTimeout(() => {
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
  };
  scheduleBlink();
}

function stopIdleAnimations() {
  if (idleBreathTimer) { clearInterval(idleBreathTimer); idleBreathTimer = null; }
  if (blinkTimer) { clearTimeout(blinkTimer); blinkTimer = null; }
}

// ---- 核心：viseme 驱动口型 ----
let visemeTimer = null;
let lastMouthValue = 0;

/**
 * 根据 viseme 时间线 + 当前播放进度计算口型值
 * @param {Array} timeline [{t: ms, mouth: 0~1}]
 * @param {number} elapsedMs 当前播放到第几毫秒
 */
function applyVisemeFromTimeline(timeline, elapsedMs) {
  if (!model || !timeline || timeline.length === 0) return;

  // 找到当前时间所在的区间，线性插值
  let targetValue = 0;
  for (let i = 0; i < timeline.length; i++) {
    if (elapsedMs < timeline[i].t) {
      if (i === 0) {
        targetValue = timeline[0].mouth;
      } else {
        const prev = timeline[i - 1];
        const curr = timeline[i];
        const ratio = (elapsedMs - prev.t) / (curr.t - prev.t);
        targetValue = prev.mouth + (curr.mouth - prev.mouth) * ratio;
      }
      break;
    }
    if (i === timeline.length - 1) {
      targetValue = timeline[i].mouth;
    }
  }
  // 平滑过渡
  lastMouthValue = lastMouthValue + (targetValue - lastMouthValue) * 0.35;
  try {
    model.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", lastMouthValue);
  } catch {}
}

/**
 * 兜底方案：纯正弦波口型（无 viseme 时间线时使用）
 * @param {number} elapsedMs 
 */
function applyFallbackMouth(elapsedMs) {
  if (!model) return;
  // 频率约 4~6 Hz，模拟说话节奏
  const mouth = 0.3 + 0.5 * Math.abs(Math.sin(elapsedMs * 0.025));
  lastMouthValue = lastMouthValue + (mouth - lastMouthValue) * 0.3;
  try {
    model.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", lastMouthValue);
  } catch {}
}

function resetMouth() {
  lastMouthValue = 0;
  try {
    model?.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", 0);
  } catch {}
}

// ---- 表情系统 ----
function applyEmotion(emotion) {
  if (!model) return;
  const exprMap = {
    happy: "f01",
    sad: "f02",
    surprised: "f03",
    apology: "f04",
    angry: "f05",
    thinking: "f06",
    neutral: "f00",
  };
  const exprId = exprMap[emotion] || "f00";
  try {
    model.expression(exprId);
  } catch {}
}

// ---- 模型初始化 ----
function fitModelToCanvas() {
  if (!model) return;
  model.scale.set(1);
  const availableWidth = CANVAS_WIDTH - MODEL_PADDING * 2;
  const availableHeight = CANVAS_HEIGHT - MODEL_PADDING * 2;
  const fitScale = Math.min(
    availableWidth / model.width,
    availableHeight / model.height
  );
  model.scale.set(Number.isFinite(fitScale) && fitScale > 0 ? fitScale : 0.1);
  model.anchor.set(0.5, 0.5);
  model.position.set(CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2);
}

onMounted(async () => {
  try {
    app = new PIXI.Application({
      width: CANVAS_WIDTH,
      height: CANVAS_HEIGHT,
      backgroundAlpha: 0,
      antialias: true,
    });
    canvasContainer.value.appendChild(app.view);

    model = await Live2DModel.from(props.modelPath);
    fitModelToCanvas();
    app.stage.addChild(model);
    applyEmotion(props.emotion);
    startIdleAnimations();
    if (props.isSpeaking) {
      // 初始进入 speaking，先用兜底方案
    }
    loading.value = false;
  } catch (err) {
    console.error("Live2D model load failed:", err);
    error.value = "数字人加载失败";
    loading.value = false;
    emit("load-error", err);
  }
});

onBeforeUnmount(() => {
  stopIdleAnimations();
  if (visemeTimer) clearInterval(visemeTimer);
  if (app) { app.destroy(true); app = null; }
});

// ---- 响应 props 变化 ----

// 说话状态
watch(() => props.isSpeaking, (speaking) => {
  if (!model) return;
  if (speaking) {
    stopIdleAnimations(); // 说话时停掉空闲动画
  } else {
    resetMouth();
    startIdleAnimations();
  }
});

// 表情
watch(() => props.emotion, (em) => applyEmotion(em));

// 音频进度变化时驱动口型
let lastElapsed = 0;
watch(() => props.speechProgress, (progress, oldProgress) => {
  if (!model || !props.isSpeaking) return;
  // progress 下降说明新音频开始
  if (progress < (oldProgress || 0)) lastElapsed = 0;
  const elapsed = progress * (props.visemeTimeline?.length
    ? (props.visemeTimeline[props.visemeTimeline.length - 1]?.t || 3000)
    : 3000);
  lastElapsed = elapsed;

  if (props.visemeTimeline && props.visemeTimeline.length > 0) {
    applyVisemeFromTimeline(props.visemeTimeline, elapsed);
  } else {
    applyFallbackMouth(elapsed);
  }
});
</script>

<style scoped>
.live2d-wrapper {
  position: relative;
  width: 480px;
  height: 720px;
}
.live2d-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 12px;
}
.live2d-container canvas {
  width: 100% !important;
  height: 100% !important;
}
.live2d-loading,
.live2d-error {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 12px 20px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  z-index: 10;
}
.live2d-error { color: #f56c6c; }
</style>
```

---

### Step 1.3：`chat.js` store 中对接新的口型数据

**文件**：`frontend/src/stores/chat.js`

**操作**：找到 `audio:` handler（约第 73~77 行），替换为：

```javascript
audio: async ({ base64, duration_ms, viseme_timeline }) => {
  await audioPlayer.enqueue(
    base64,
    duration_ms,
    () => {
      options.onAudioEnded?.();
    },
    (progress, elapsedMs) => {
      // 播放进度回调 → 传给 Live2D 驱动口型
      options.onSpeechProgress?.(progress, elapsedMs, viseme_timeline || null);
    }
  );
},
```

在同一个 `streamChat` handler 对象中，`avatar:` handler 保持不变：

```javascript
avatar: ({ viseme_text, emotion }) => {
  options.onAvatar?.({ viseme_text, emotion });
},
```

确认 `done:` handler 在结束时不残留状态（已有的保持不变即可）。

---

### Step 1.4：`ChatView.vue` 中传入 speechProgress + visemeTimeline

**文件**：`frontend/src/views/tourist/ChatView.vue`

**操作 1**：在 `<script setup>` 顶部新增两个 ref：

```javascript
const speechProgress = ref(0);
const visemeTimeline = ref([]);
```

**操作 2**：找到 Live2DAvatar 的使用处（约第 22~26 行），添加新 props：

```html
<Live2DAvatar
  v-if="!avatarError"
  :emotion="avatar.currentEmotion.value"
  :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
  :speech-progress="speechProgress"
  :viseme-timeline="visemeTimeline"
  @load-error="handleAvatarLoadError"
/>
```

**操作 3**：在 `submitQuery` 的 options 对象中，新增 `onSpeechProgress` 回调：

```javascript
chatStore.sendMessage(finalQuery, interactionStore.selectionPayload, {
  onContext: (selection) => interactionStore.applyResolvedSelection(selection),
  onAvatar: (payload) => {
    try {
      avatar.handleAvatarEvent(payload);
    } catch {
      avatarError.value = true;
    }
  },
  onAudioEnded: () => {
    avatar.onAudioEnded();
    speechProgress.value = 0;
    visemeTimeline.value = [];
  },
  // ★ 新增
  onSpeechProgress: (progress, elapsedMs, timeline) => {
    speechProgress.value = progress;
    if (timeline) visemeTimeline.value = timeline;
  },
});
```

---

### Step 1.5：验证

```bash
cd frontend
npm run dev
```

1. 打开 `http://localhost:5173/tourist`
2. 发送一条问题
3. 观察数字人的嘴是否跟随语音节奏开合（不是固定 150ms toggle）
4. 说话结束后嘴自动闭合，回到呼吸 + 眨眼空闲状态

✅ 一阶段完成标志：**数字人说话时嘴动画频率变化明显、闭嘴时回到呼吸眨眼态**

---

# 📦 二阶段：表情丰富 + 情感联动（P1）

## 2.1 目标

- Live2D 表情从 3 种扩展到 7 种
- 后端 LLM 回答时标注情感，前端驱动对应表情
- AvatarConfig 管理页有基本功能

## 2.2 修改步骤

### Step 2.1：Live2D 表情映射已在一阶段代码中完成

一阶段的重写代码中 `applyEmotion` 已支持 7 种表情映射（f00~f06），此步无需重复。

### Step 2.2：`useAvatar.js` 中新增更细粒度的情感状态映射

**文件**：`frontend/src/composables/useAvatar.js`

**操作**：在 `handleAvatarEvent` 函数中，替换现有的 emotion 映射逻辑：

```javascript
// 在 handleAvatarEvent 中，替换 emotion 部分：
function handleAvatarEvent(payload) {
  if (payload.emotion) {
    // 后端传回的情感映射到前端状态
    currentEmotion.value = payload.emotion;
    const emotionToState = {
      happy: "happy",
      sad: "apology",
      surprised: "thinking",
      angry: "apology",
      thinking: "thinking",
      neutral: "idle",
    };
    const targetState = emotionToState[payload.emotion] || "speaking";
    if (targetState === "happy" || targetState === "apology") {
      setState(targetState);
      return;
    }
  }
  if (payload.viseme_text !== undefined) {
    currentViseme.value = payload.viseme_text || "";
    if (currentState.value !== "happy" && currentState.value !== "apology") {
      setState("speaking");
    }
  }
}
```

### Step 2.3：实现 AvatarConfig.vue 管理页

**文件**：`frontend/src/views/admin/AvatarConfig.vue`

**操作**：用以下内容完整替换：

```vue
<template>
  <section class="avatar-config-page">
    <div class="config-header">
      <h2>数字人配置</h2>
      <p>管理数字导游的外观形象、语音音色和表情策略。</p>
    </div>

    <div class="config-grid">
      <!-- 外观形象 -->
      <el-card class="config-card">
        <template #header>
          <span>外观形象</span>
        </template>
        <el-form label-width="100px">
          <el-form-item label="当前模型">
            <el-tag type="success">Shizuku（导游形象）</el-tag>
          </el-form-item>
          <el-form-item label="模型来源">
            <el-select v-model="modelSource" placeholder="选择模型加载方式">
              <el-option label="在线 CDN（默认）" value="cdn" />
              <el-option label="本地文件" value="local" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="modelSource === 'local'" label="模型文件">
            <el-upload
              action="#"
              :auto-upload="false"
              :limit="1"
              accept=".json,.model3.json"
            >
              <el-button type="primary">上传 Live2D 模型</el-button>
            </el-upload>
          </el-form-item>
          <el-form-item label="显示尺寸">
            <el-slider v-model="avatarScale" :min="50" :max="150" :step="5" show-input />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 语音音色 -->
      <el-card class="config-card">
        <template #header>
          <span>语音音色</span>
        </template>
        <el-form label-width="100px">
          <el-form-item label="音色选择">
            <el-select v-model="voiceType" placeholder="选择音色">
              <el-option label="温柔女声（默认）" value="gentle-female" />
              <el-option label="知性女声" value="calm-female" />
              <el-option label="沉稳男声" value="deep-male" />
              <el-option label="活泼女声" value="lively-female" />
            </el-select>
          </el-form-item>
          <el-form-item label="语速">
            <el-slider v-model="speechRate" :min="80" :max="150" :step="5" show-input />
          </el-form-item>
          <el-form-item label="音量">
            <el-slider v-model="volume" :min="50" :max="100" :step="5" show-input />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 表情策略 -->
      <el-card class="config-card">
        <template #header>
          <span>表情策略</span>
        </template>
        <el-form label-width="100px">
          <el-form-item label="表情丰富度">
            <el-slider v-model="expressionIntensity" :min="1" :max="5" :step="1" show-stops />
            <span class="slider-hint">越高表情变化越明显</span>
          </el-form-item>
          <el-form-item label="欢迎表情">
            <el-select v-model="greetingEmotion">
              <el-option label="微笑" value="happy" />
              <el-option label="平静" value="neutral" />
              <el-option label="惊喜" value="surprised" />
            </el-select>
          </el-form-item>
          <el-form-item label="致歉表情">
            <el-select v-model="apologyEmotion">
              <el-option label="抱歉" value="apology" />
              <el-option label="难过" value="sad" />
            </el-select>
          </el-form-item>
          <el-form-item label="口型同步强度">
            <el-slider v-model="lipSyncIntensity" :min="50" :max="100" :step="10" show-input />
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 动作配置（加分项） -->
      <el-card class="config-card">
        <template #header>
          <span>肢体动作</span>
          <el-tag size="small" type="warning" style="margin-left: 8px;">加分项</el-tag>
        </template>
        <el-form label-width="100px">
          <el-form-item label="启用动作">
            <el-switch v-model="motionEnabled" />
          </el-form-item>
          <el-form-item label="点头频率">
            <el-select v-model="nodFrequency" :disabled="!motionEnabled">
              <el-option label="偶尔" value="rare" />
              <el-option label="适中" value="normal" />
              <el-option label="频繁" value="frequent" />
            </el-select>
          </el-form-item>
          <el-form-item label="欢迎挥手">
            <el-switch v-model="greetingWave" :disabled="!motionEnabled" />
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <div class="config-actions">
      <el-button type="primary" @click="handleSave">保存配置</el-button>
      <el-button @click="handleReset">恢复默认</el-button>
      <el-button @click="handlePreview">预览效果</el-button>
    </div>

    <!-- 预览弹窗 -->
    <el-dialog v-model="previewVisible" title="数字人预览" width="540px">
      <div class="preview-container">
        <Live2DAvatar
          :emotion="previewEmotion"
          :is-speaking="previewSpeaking"
        />
      </div>
      <template #footer>
        <el-button @click="previewEmotion = 'neutral'; previewSpeaking = false">空闲</el-button>
        <el-button @click="previewEmotion = 'happy'; previewSpeaking = true">微笑说话</el-button>
        <el-button @click="previewEmotion = 'surprised'">惊喜</el-button>
        <el-button @click="previewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { ref } from "vue";
import Live2DAvatar from "../../components/Live2DAvatar.vue";

const modelSource = ref("cdn");
const avatarScale = ref(100);
const voiceType = ref("gentle-female");
const speechRate = ref(100);
const volume = ref(80);
const expressionIntensity = ref(3);
const greetingEmotion = ref("happy");
const apologyEmotion = ref("apology");
const lipSyncIntensity = ref(80);
const motionEnabled = ref(false);
const nodFrequency = ref("normal");
const greetingWave = ref(false);
const previewVisible = ref(false);
const previewEmotion = ref("neutral");
const previewSpeaking = ref(false);

function handleSave() {
  ElMessage.success("数字人配置已保存（当前为前端演示模式）");
}

function handleReset() {
  modelSource.value = "cdn";
  avatarScale.value = 100;
  voiceType.value = "gentle-female";
  speechRate.value = 100;
  volume.value = 80;
  expressionIntensity.value = 3;
  greetingEmotion.value = "happy";
  apologyEmotion.value = "apology";
  lipSyncIntensity.value = 80;
  motionEnabled.value = false;
  nodFrequency.value = "normal";
  greetingWave.value = false;
  ElMessage.info("已恢复默认配置");
}

function handlePreview() {
  previewEmotion.value = "neutral";
  previewSpeaking.value = false;
  previewVisible.value = true;
}
</script>

<style scoped>
.avatar-config-page {
  padding: 24px;
}
.config-header {
  margin-bottom: 24px;
}
.config-header h2 {
  margin: 0 0 8px;
}
.config-header p {
  margin: 0;
  color: #6c757d;
}
.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}
.config-card {
  border: 1px solid var(--border, #dee2e6);
}
.slider-hint {
  margin-left: 12px;
  font-size: 12px;
  color: #6c757d;
}
.config-actions {
  display: flex;
  gap: 12px;
}
.preview-container {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  background: #f0fdfa;
  border-radius: 12px;
}
@media (max-width: 900px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

---

# 📦 三阶段：动作系统 + 形象切换（P2 加分项）

## 3.1 目标

- Live2D motions（点头、挥手等）按语境触发
- 支持切换本地 Live2D 模型
- AvatarConfig 存储的配置在游客端生效

## 3.2 修改步骤

### Step 3.1：Live2DAvatar 增加 motion 方法

**文件**：`frontend/src/components/Live2DAvatar.vue`

在 script 中新增以下代码（expose 给父组件调用）：

```javascript
// 暴露给父组件调用的动作
const motionMap = {
  nod: "Nod",
  shake_head: "Shake",
  wave: "Wave",
  point: "Point",
};

function playMotion(name) {
  if (!model) return;
  const motionName = motionMap[name] || name;
  try {
    // pixi-live2d-display 的 motion 按 group 名称查找
    model.motion(motionName);
  } catch {
    console.warn(`Motion "${motionName}" not found`);
  }
}

// 随机微动作（每隔 8~20 秒）
let randomMotionTimer = null;
function startRandomMotions() {
  const schedule = () => {
    randomMotionTimer = setTimeout(() => {
      if (!model) return;
      const keys = Object.keys(motionMap);
      // 只偶尔动一下，避免太频繁
      if (Math.random() < 0.4) {
        const randMotion = keys[Math.floor(Math.random() * keys.length)];
        try {
          model.motion(motionMap[randMotion]);
        } catch {}
      }
      schedule();
    }, 8000 + Math.random() * 12000);
  };
  schedule();
}
function stopRandomMotions() {
  if (randomMotionTimer) { clearTimeout(randomMotionTimer); randomMotionTimer = null; }
}

// 添加 motion 相关到 onBeforeUnmount
// 把 stopRandomMotions() 加入现有的 onBeforeUnmount 中

defineExpose({ playMotion });
```

并在 `onMounted` 中调用 `startRandomMotions()`，在 `onBeforeUnmount` 中调用 `stopRandomMotions()`。

### Step 3.2：AvatarConfig 配置持久化到 localStorage

**文件**：`frontend/src/views/admin/AvatarConfig.vue`

在 `handleSave` 中增加：

```javascript
function handleSave() {
  const config = {
    modelSource: modelSource.value,
    avatarScale: avatarScale.value,
    voiceType: voiceType.value,
    speechRate: speechRate.value,
    volume: volume.value,
    expressionIntensity: expressionIntensity.value,
    greetingEmotion: greetingEmotion.value,
    apologyEmotion: apologyEmotion.value,
    lipSyncIntensity: lipSyncIntensity.value,
    motionEnabled: motionEnabled.value,
    nodFrequency: nodFrequency.value,
    greetingWave: greetingWave.value,
  };
  localStorage.setItem("a5-avatar-config-v1", JSON.stringify(config));
  ElMessage.success("数字人配置已保存并生效");
}
```

---

# 🧪 最终联调验证清单

按顺序逐项检查：

```
□ 游客端 ChatView 页面正常渲染（不白屏不报错）
□ Live2D 模型加载成功
□ 发送问题 → 数字人进入 thinking 状态
□ TTS 播报时 → 口型随音频节奏变化（非固定频率）
□ 停顿时嘴巴闭合 → 回到呼吸+眨眼
□ 表情随回答情感变化（happy 微笑 / apology 道歉）
□ /admin/avatar 页面可见完整配置表单
□ 配置页预览弹窗可切换表情
□ 移动端 / 900px 以下布局不崩
□ 浏览器 Console 无红色报错
```

---

# ⚠️ 注意事项

1. **每次只改一个文件**，改完立刻 `npm run dev` 确认不崩再改下一个
2. **不要动 `node_modules/`、`package.json`、`vite.config.js`**
3. **不要新增 npm 依赖**，只用已有的 pixi.js、pixi-live2d-display、vue
4. **viseme_timeline 数据格式**：如果后端暂时没传，前端兜底方案（正弦波）会自动工作
5. **如果 `ParamBreath` 或 `ParamEyeLOpen` 在当前模型上不存在**，catch 块会静默忽略，不影响渲染
6. 所有改动集中在前端，后端不动
