# 浏览器语音识别接入 — 任务书（Codex）

> 目标：用 Chrome 内置 Web Speech API 替换 stub ASR，实现零成本真实语音交互。
> 时间：1 小时
> 不改后端，不新增依赖

---

## 当前状态

录音链路已就绪：`useRecorder.js`（MediaRecorder）→ `POST /asr/transcribe` → stub 返回占位文本 → 填入输入框 → 发送。

问题：后端 stub ASR 永远返回 "语音输入示例文本"，语音交互是假的。

---

## 目标

不做 MediaRecorder → 上传 → 后端 stub 这条路。改用浏览器自带语音识别：

```
用户点"语音输入" → Chrome 弹出麦克风权限 → 说话 → 文字实时出现在输入框 → Enter 发送
```

Chrome 的 `webkitSpeechRecognition` 是免费内置的，中文识别效果可用。不需要上传音频到后端。

---

## 修改 1：新建 `useSpeechRecognition.js`

**文件**：`frontend/src/composables/useSpeechRecognition.js`（新建）

```js
import { ref } from "vue";

export function useSpeechRecognition() {
  const isListening = ref(false);
  const interimText = ref("");
  const finalText = ref("");
  const isSupported = ref(false);
  const error = ref("");

  let recognition = null;

  const SpeechRecognition =
    typeof window !== "undefined" &&
    (window.SpeechRecognition || window.webkitSpeechRecognition);

  isSupported.value = !!SpeechRecognition;

  function start() {
    if (!SpeechRecognition || isListening.value) return;

    error.value = "";
    interimText.value = "";
    finalText.value = "";

    recognition = new SpeechRecognition();
    recognition.lang = "zh-CN";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          final += transcript;
        } else {
          interim += transcript;
        }
      }
      if (final) finalText.value = final;
      interimText.value = interim;
    };

    recognition.onerror = (event) => {
      error.value = event.error;
      stop();
    };

    recognition.onend = () => {
      isListening.value = false;
    };

    recognition.start();
    isListening.value = true;
  }

  function stop() {
    if (recognition) {
      recognition.stop();
      recognition = null;
    }
    isListening.value = false;
  }

  return { isListening, interimText, finalText, isSupported, error, start, stop };
}
```

不需要 npm 依赖。`webkitSpeechRecognition` 是 Chrome 自带 API。

---

## 修改 2：升级 `useRecorder.js` 的 `isSupported` 检测

**文件**：`frontend/src/composables/useRecorder.js`

当前 `isSupported` 只检测 MediaRecorder。加一个导出，让兼容检测同时覆盖 Web Speech API：

```js
// 在 return 里新增
speechSupported: SpeechRecognitionSupported,
```

其中 `SpeechRecognitionSupported` 是同一模块顶部定义的：
```js
export const SpeechRecognitionSupported =
  typeof window !== "undefined" &&
  !!(window.SpeechRecognition || window.webkitSpeechRecognition);
```

如果太复杂可以不做这一步，直接在 ChatView 里检测。

---

## 修改 3：ChatView.vue 集成语音识别

**文件**：`frontend/src/views/tourist/ChatView.vue`

### 3.1 导入

```js
import { useSpeechRecognition } from "../../composables/useSpeechRecognition";
```

### 3.2 初始化

```js
const speech = useSpeechRecognition();
```

### 3.3 修改 `voiceSupported` 检测

```js
const voiceSupported = computed(() => 
  recorder.isSupported.value || speech.isSupported.value
);
```

### 3.4 修改 `toggleRecording`

```js
async function toggleRecording() {
  if (speech.isListening.value) {
    speech.stop();
    if (speech.finalText.value) {
      query.value = speech.finalText.value;
    }
    return;
  }
  if (isRecording.value) {
    const blob = await stop();
    if (blob) {
      transcribing.value = true;
      try {
        const result = await transcribeAudio(blob);
        if (result?.text) query.value = result.text;
      } catch {}
      transcribing.value = false;
    }
    avatar.setState("idle");
    return;
  }
  // 优先使用 Web Speech
  if (speech.isSupported.value) {
    speech.start();
    avatar.setState("listening");
    return;
  }
  // 降级为 MediaRecorder
  await start();
  avatar.setState("listening");
}
```

### 3.5 语音输入按钮状态

按钮文字和 loading 需要反映 speech 状态：

```html
<el-button
  v-if="voiceSupported"
  :type="speech.isListening ? 'danger' : isRecording ? 'danger' : 'default'"
  :loading="transcribing"
  @click="toggleRecording"
>
  <template v-if="speech.isListening">结束语音 (说话中)</template>
  <template v-else-if="isRecording">结束录音 ({{ durationSeconds }}s)</template>
  <template v-else>语音输入</template>
</el-button>
```

### 3.6 实时识别文字展示（可选）

录音时在输入框上方显示一句话：

```html
<div v-if="speech.isListening && speech.interimText" class="speech-interim">
  🎤 {{ speech.interimText }}
</div>

<div v-if="speech.isListening && speech.finalText" class="speech-final">
  识别结果：{{ speech.finalText }}
</div>
```

---

## 降级顺序

```
1. Web Speech API (Chrome 内置，零成本首选)
2. MediaRecorder → stub ASR (当前方案，降级备选)
3. 文本输入框 (永远可用)
```

---

## 验证

```
cd frontend
npm.cmd run build
```

在 Chrome 中打开页面，点击"语音输入"，弹出麦克风权限，说"灵山大佛有多高"，文字出现在输入框，按 Enter 发送。

---

## 文件清单

```
frontend/src/composables/useSpeechRecognition.js  ← 新建
frontend/src/views/tourist/ChatView.vue           ← 修改 toggleRecording + 按钮
```

不改后端、不新增 npm 依赖、不改 SSE 协议。
