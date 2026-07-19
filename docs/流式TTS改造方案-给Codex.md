# 流式 TTS 改造方案

## 背景

当前百炼 TTS 走 HTTP 请求-响应模式，每句话都是独立 HTTP 调用：发送 → 等待整段 MP3 返回 → 播放。首句延迟 300-800ms，且依赖网络。

## 改造目标

将 HTTP TTS 升级为 WebSocket 流式 TTS，实现：

- **首句延迟 50-200ms**（省去 HTTP 握手 + 等整段音频）
- **口型用 TTS 返回的字级时间戳驱动**（替代 pypinyin 估算，精度毫秒级）
- **一次对话只建一次 WebSocket 连接**（省去每句重复握手）
- **LLM 生成与 TTS 并行**（不阻塞 LLM 继续输出）

## 改动清单

### 后端（3 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/tts/streaming.py` | **新建** | `StreamingTTSSession`：WebSocket 连接到 `wss://dashscope.aliyuncs.com/api-ws/v1/inference`，支持 `connect()` → `send_text()`(可多次) → `finish()` → `try_receive()`(非阻塞取事件)。返回 PCM 音频块 + 字级时间戳。 |
| `backend/app/services/qa/pipeline.py` | **修改** | 新增 `streaming_tts_service` 参数，流式模式下 LLM 每个 token 直接 `send_text()` 喂入 TTS，音频块/字时间戳通过 SSE `audio_chunk` 事件下发。流式失败自动降级 HTTP。 |
| `backend/app/api/chat.py` | **修改** | 创建 `StreamingTTSService` 实例并传入 `QAPipeline`。 |

### 前端（2 个文件）

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/composables/useAudioPlayer.js` | **修改** | 新增 `startPCMStream()` / `feedPCMChunk()` / `endPCMStream()`。将 base64 PCM 解码为 AudioBuffer，多块通过 `AudioContext.currentTime` 无缝排期播放。 |
| `frontend/src/stores/chat.js` | **修改** | 新增 `audio_chunk` SSE 事件处理：base64 → `feedPCMChunk()`；viseme_timeline → `onSpeechProgress()`。`done` 事件时调用 `endPCMStream()`。 |

## 数据流对比

```
【改造前】
LLM → 等句子完整 → HTTP POST → 等整段 MP3 → SSE audio → 前端 decode → 播

【改造后】
LLM → send_text(token) → WebSocket ─┬→ PCM 块 (SSE audio_chunk) → 前端直接播
                                    └→ 字时间戳 → viseme_timeline → ThreeAvatar 口型
```

## 向后兼容

- HTTP TTS 路径完整保留，流式连接失败时自动降级
- 流式模式下，LLM token 仍正常通过 `text_chunk` SSE 事件下发，前端文本显示不受影响
- 不依赖新 pip 包（`websockets` 已在现有依赖中）

## 口型数据格式

服务端返回 `sentence-end` 事件包含：

```json
{"words": [
  {"text": "你", "begin_time": 0,   "end_time": 180},
  {"text": "好", "begin_time": 180, "end_time": 350}
]}
```

后端 `_words_to_viseme_timeline()` 结合 pypinyin 开口度/圆展度，转换为前端已有格式：

```json
[
  {"start": 0, "end": 180, "value": 0.22, "form": 0.18},
  {"start": 180, "end": 350, "value": 0.52, "form": 0.12}
]
```

`ThreeAvatar` 已支持此格式，无需改动。

## 注意事项

1. 需要 `word_timestamp_enabled: true`，`cosyvoice-v3-flash` 需实测确认是否支持
2. 服务端 `dashscope.aliyuncs.com` 域名需可访问
3. PCM 音频为 24kHz/16bit/单声道，前端按此参数解码
