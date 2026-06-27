# 语音输出 A/B 方案实施验收报告

> 检测时间：2026-06-20  
> 范围：从后端 SSE 下发 → 前端播放 → Live2D 口型驱动的全链路

> 2026-06-21 修正状态：本文指出的核心断点已完成代码修正。以下原始检测内容保留用于追溯，最新结果见文末“八、修正后复验”。

---

## 一、先看结论

```
方案A（后端TTS base64音频）:  ⚠️ 基础通路可用，口型同步断裂
方案B（浏览器SpeechSynthesis）: ✅ 兜底可用，口型同步断裂

两条通路都能"出声"，但都没有打通到 Live2D 口型的桥梁——
数字人张嘴仍是随机频率，不跟随任何一方的音频节奏。
```

---

## 二、方案 A：后端 TTS（Bailian 阿里云百炼）

### 2.1 后端链路

```
.config       TTS_PROVIDER=bailian ✅（.env 第21行有API Key）
               ↓
chat.py       if tts_provider == "bailian" and api_key:
                 tts_service = BailianTTSService(...) ✅
               ↓
pipeline.py   audio = await self.tts_service.synthesize(sentence)
               ↓ 返回 TTSAudio(base64_audio=..., duration_ms=...)
pipeline.py   yield StreamEvent(type="audio",
                   data={"base64": audio.base64_audio,
                         "duration_ms": audio.duration_ms})
               ↓ SSE 下发到前端
```

**BailianTTSService 实际行为：**

```python
# bailian.py
async def synthesize(self, text: str) -> TTSAudio:
    response = httpx.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2speech/synthesis",
        json={"model": "cosyvoice-v1", "input": {"text": text},
              "parameters": {"voice": "zhixiaobai", "format": "mp3"}},
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    audio_data = response["output"]["audio"]   # 真正的 MP3 base64
    return TTSAudio(base64_audio=audio_data, duration_ms=char_count * 200)
```

**下发的事件格式（实际）：**
```
event: audio
data: {"base64": "//uQxAAAA...真实MP3音频base64...", "duration_ms": 3200}
```

### 2.2 前端链路（直播追踪）

```
chat.js:73   audio: async ({ base64, duration_ms }) => {
                 options.onAudioStart?.()  ← ✅ 触发 Avatar → speaking 状态
                 audioPlayer.enqueue(base64, duration_ms, onEnded, text)
             }
                  ↓
useAudioPlayer.js:123
             enqueue(base64, durationMs, onEnded, text)
             → 推入 queue → auto flush()
                  ↓
useAudioPlayer.js:139  flush()
             audioBuffer = await base64ToAudioBuffer(base64)  ← atob → Uint8Array → decodeAudioData
             if (audioBuffer) {
                 await playAudioBuffer(audioBuffer)  ← ✅ 真实播放MP3
             } else if (text) {
                 await playSpeechSynthesis(text)     ← → 跳到方案B
             }
```

### 2.3 方案A 口型同步链路（关键断裂点）

```
playAudioBuffer(audioBuffer, onProgress)
     │                        ↑
     │  第66-71行已有定时器     flush() 第141行调用时：playAudioBuffer(audioBuffer)
     │  if (onProgress) {      没有传 onProgress！← 第一处断裂
     │    setInterval(30ms)
     │    onProgress(progress, elapsed)
     │  }
     ↓
(progress 数据未出来)
     ↓
chat.js  audio handler —— 没有接收 onProgress 参数   ← 第二处断裂
     ↓
ChatView.vue —— 没有 speechProgress ref              ← 第三处断裂
     ↓
Live2DAvatar.vue —— 没有 :speech-progress prop        ← 第四处断裂
     ↓
口型驱动 —— 随机 Math.random() toggle（第86行）       ← 最终结果
```

**具体证据：**

| 文件 | 行号 | 当前代码 | 应有代码 |
|------|------|----------|----------|
| useAudioPlayer.js | 141 | `playAudioBuffer(audioBuffer)` | `playAudioBuffer(audioBuffer, current.onProgress)` |
| useAudioPlayer.js | 123 | `enqueue(base64, durationMs, onEnded, text)` | `enqueue(base64, durationMs, onEnded, text, onProgress)` |
| chat.js | 73 | `audio: async ({ base64, duration_ms })` | `audio: async ({ base64, duration_ms, viseme_timeline })` |
| chat.js | 76 | `enqueue(base64, duration_ms, onEnded, currentText)` | `enqueue(base64, duration_ms, onEnded, text, onProgress)` |
| ChatView.vue | — | 无 `speechProgress` ref | 需新增 |
| ChatView.vue | — | 无 `:speech-progress="speechProgress"` | 需新增绑定 |
| Live2DAvatar.vue | — | 无 `speechProgress` prop | 需新增 |
| Live2DAvatar.vue | 86 | `Math.random() * 0.6 + 0.2` | 应读 `speechProgress` 驱动口型 |

---

## 三、方案 B：浏览器 SpeechSynthesis 兜底

### 3.1 触发条件

方案B在两个路径触发：

**路径1：Bailian API 返回空**
```python
# bailian.py line 40-41
if not audio_data:
    return TTSAudio(base64_audio="", duration_ms=0)
# → base64="" → atob("") = "" → decodeAudioData("") 失败 → audioBuffer=null
# → flush() 检测到 text 存在 → playSpeechSynthesis(text)
```

**路径2：StubTTS 模式（当前未被使用，仅做兜底设计）**
```python
# stub.py
payload = base64.b64encode(text.encode("utf-8")).decode("utf-8")
# → base64=文字的base64，不是音频 → decodeAudioData失败 → audioBuffer=null
# → → playSpeechSynthesis(text)
```

### 3.2 方案B 实际路径

```
backend → SSE audio 事件 (base64为空或无效)
    ↓
useAudioPlayer → base64ToAudioBuffer 失败 → audioBuffer = null
    ↓
if (current.text && speechSynthSupported)  ← chat.js 传了 text（第78行 currentText）
    ↓
playSpeechSynthesis(text)
    ↓
new SpeechSynthesisUtterance(text)
    lang="zh-CN", rate=1.0, pitch=1.1, volume=1.0
    voice = 第一个 zh-* 语音
    ↓
window.speechSynthesis.speak(utterance)
    ↓
浏览器原生读出中文 ✅
```

### 3.3 方案B 口型同步：全无

```
SpeechSynthesis 不提供进度回调 API
  → useAudioPlayer 没有 onProgress
    → chat.js 没有 onSpeechProgress
      → ChatView 没有 speechProgress
        → Live2DAvatar 嘴部 = Math.random()
```

方案B 唯一能做到的：`onAudioStart` 让数字人进入 "speaking" 状态（张嘴），`onAudioEnded` 让数字人闭嘴。

---

## 四、后端 SSE 下发的完整事件序列

以"什么是灵山大佛"为例，一次典型请求的 SSE 事件流：

```
第1帧  event: context   data: {"selection":{...},"warnings":[...]}
第2帧  event: status    data: {"text":"正在查找答案..."}
第3帧  event: status    data: {"text":"正在检索景区知识..."}
第4帧  event: sources   data: {"docs":[{...3条知识文档...}]}
第5帧  event: text_chunk  data: {"token":"灵"}
第6帧  event: text_chunk  data: {"token":"山"}
第7帧  event: text_chunk  data: {"token":"大"}
...     (持续流式输出 tokens)
第N帧  event: text_chunk  data: {"token":"。"}
        ← 遇到句号 → 触发 _queue_audio(sentence)
        → 并行执行 TTS + Avatar
第N+1帧  event: avatar   data: {"viseme_text":"灵山大佛是...","emotion":"neutral"}
第N+2帧  event: audio    data: {"base64":"//uQxAAAA...","duration_ms":2400}
...     (后续句子继续 text_chunk → avatar → audio)
第M帧  event: text      data: {"text":"完整回答","is_complete":true}
第M+1帧  event: followups data: {"items":[{...2-4个快捷追问...}]}
第M+2帧  event: done     data: {}
```

**关键发现：avatar 事件只发送了 emotion 和 viseme_text，没有发送 viseme_timeline（口型时间线序列）。**

---

## 五、额外发现的问题

### 5.1 时长估算粗糙

```python
# bailian.py line 52
def _estimate_duration(self, text: str) -> int:
    return int(len(text) * 200)  # 每字 200ms
```

"灵山大佛高88米" = 8字 → 1600ms 估算。实际百炼返回的 MP3 音频时长可能不同。前端如果将来要做精确口型同步，应该用实际音频时长而非估算值。

### 5.2 SpeechSynthesis voices 异步加载

```javascript
// useAudioPlayer.js line 98
const voices = window.speechSynthesis.getVoices();
```

`getVoices()` 首次调用可能返回空数组（voices 通过异步事件加载）。正确做法是监听 `voiceschanged` 事件。当前代码如果 voices 为空，`find(v => v.lang.startsWith("zh"))` 返回 undefined，会用系统默认语音（可能是英文）。

### 5.3 播放中无法更新口型

```javascript
// useAudioPlayer.js line 139-146 - flush() 的核心播放循环
const audioBuffer = await base64ToAudioBuffer(current.base64);
if (audioBuffer) {
    await playAudioBuffer(audioBuffer);  // ← await 阻塞直到播放完
}
```

`flush()` 用了 `await playAudioBuffer`，所以队列中每条音频是串行播完才处理下一条。但 `playAudioBuffer` 里虽然有 onProgress 定时器，在 flush 中却没有接出来——这就是整个口型同步链路断裂的根源。

---

## 六、修复方案（对照方案文档）

修复重点仍然是之前检测报告中的 P0 口型链路，文件从上到下：

| 序号 | 文件 | 改动 | 工时 |
|------|------|------|------|
| 1 | `useAudioPlayer.js:123` | `enqueue` 加第5参数 `onProgress`，`flush` 中传 `current.onProgress` 给 `playAudioBuffer` | 10min |
| 2 | `chat.js:73-78` | `audio` handler 读 `viseme_timeline`，`enqueue` 传 onProgress 回调 | 5min |
| 3 | `ChatView.vue` | 新增 `speechProgress` ref + `:speech-progress` prop 绑定 + `onSpeechProgress` 回调 | 10min |
| 4 | `Live2DAvatar.vue` | 新增 `speechProgress` prop，watch 驱动 `applyVisemeFromTimeline` / `applyFallbackMouth` | 30min |

**方案B 的语音也能间接受益**：如果 SpeechSynthesis 也走同一个 onProgress 通路（用文本长度估算总时长 + 定时器模拟进度），方案B 的嘴也能跟语音大致吻合。

---

## 七、最终判定

```
方案A（Bailian TTS）:  ✅ 能播放真实中文语音    ❌ 口型不同步
方案B（SpeechSynthesis）: ✅ 浏览器自动读中文     ❌ 口型不同步

两条路都能出声，但"声音"和"嘴"之间没有桥梁。
核心修复 = 打通 useAudioPlayer.onProgress → chat.js → ChatView → Live2DAvatar 这条管道。
```

---

## 八、修正后复验（2026-06-21）

### 8.1 已修正

1. `useAudioPlayer.enqueue()` 现同时保存 `base64`、`durationMs`、`text` 和 `onProgress`。
2. 真实音频解码成功时，`playAudioBuffer()` 每 30ms 回传实际播放进度。
3. 音频为空或解码失败时，使用对应句子 `text` 调用 SpeechSynthesis，不再静默等待。
4. SpeechSynthesis 会等待 `voiceschanged`，优先选择中文音色。
5. SpeechSynthesis 使用 `boundary` 事件回传字符进度，并以定时器作为兼容性兜底。
6. SSE `audio` 事件新增 `text` 与 `viseme_timeline`。
7. `ChatView.vue` 使用待播放语音段计数，SSE `done` 不会提前结束仍在进行的播报。
8. `Live2DAvatar.vue` 在外部进度生效时停用内部固定口型定时器，避免两个驱动互相覆盖。
9. 最后一段音频结束后立即关闭口型并回到待机。
10. 百炼音频响应兼容 base64 字符串、data URI、音频 URL、嵌套对象和直接音频响应。
11. 百炼请求超时新增 `TTS_TIMEOUT_SECONDS` 配置。

### 8.2 修正后的事件格式

```text
event: audio
data: {
  "base64": "...",
  "duration_ms": 2400,
  "text": "灵山大佛高八十八米。",
  "viseme_timeline": [
    {"start": 0, "end": 200, "value": 0.32},
    ...
  ]
}
```

### 8.3 验证结果

```text
前端生产构建：通过
后端语音专项测试：9 passed
后端完整回归：71 passed
后端 compileall：通过
游客页浏览器加载：通过，无控制台错误、无横向溢出
```

### 8.4 仍需人工听测

当前内置自动化浏览器没有暴露 SpeechSynthesis，因此无法在该环境中完成方案 B 的真实声音听测。还需在桌面 Chrome/Edge 中确认：

1. 百炼不可用时能否自动使用系统中文语音。
2. 连续两到三句播报是否顺序正确、无重叠。
3. 口型是否持续到最后一个字结束，并在结束后立即闭合。
4. 不同 Windows 机器上的中文音色是否符合演示要求。
