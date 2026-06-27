# 阶段 D 语音闭环 — TTS 方案对比

> 日期：2026-06-20
> 目的：为阶段 D 的 TTS 语音合成选择最优方案，供审查决策
> 当前状态：后端 TTS 为 StubTTSService（base64 编码纯文本，不可播放），ASR 输入已通过浏览器 Web Speech API 解决

---

## 一、当前 TTS 链路现状

```
回答文本 → StubTTSService.synthesize()
         → base64(text.encode("utf-8"))   ← 不是音频！
         → SSE "audio" 事件
         → chat.js → audioPlayer.enqueue()
         → AudioContext.decodeAudioData() ← 解码失败，走 setTimeout 降级
         → 无声
```

前端 `useAudioPlayer.js` 具备真实 `AudioContext.decodeAudioData()` 解码播放能力，管道也完整串联了 SSE 音频事件队列。唯一缺口：**没有真实音频数据进入管道**。

---

## 二、方案 A：浏览器内置 SpeechSynthesis API

### 概述

直接使用浏览器原生 `window.speechSynthesis`，不经过后端，不消耗任何 API 额度。

### 技术原理

```javascript
const utterance = new SpeechSynthesisUtterance(text);
utterance.lang = "zh-CN";
utterance.rate = 1.0;   // 语速
utterance.pitch = 1.1;  // 音调
utterance.volume = 1.0;
// 可选：选择特定中文语音
const voices = speechSynthesis.getVoices();
utterance.voice = voices.find(v => v.lang.startsWith("zh-CN"));

// 事件驱动
utterance.onstart = () => { /* 数字人切 speaking */ };
utterance.onend = () => { /* 数字人切 idle */ };
utterance.onboundary = (e) => {
  // e.charIndex：当前朗读到的字符位置
  // 可驱动口型张合节奏
};

speechSynthesis.speak(utterance);
```

`onboundary` 事件在不同浏览器中实现差异较大（Chrome 较稳定触发），可作为口型同步的驱动源。

### 集成方式

改动范围：**仅修改前端**，后端不动。

```
方案：
1. 前端收到服务端 SSE "answer" 文本后，不再依赖 SSE "audio" 事件
2. 改为前端直接调用 speechSynthesis.speak()
3. 口型通过 onboundary 事件驱动（或回退为句级开合）
4. 后端 TTS stub 保持不变，或者前端忽略 audio 事件
```

更干净的方案：**在后端换一个"浏览器TTS前端适配层"** — StubTTSService 照常产出 SSE audio 事件（只不过 base64 内容改为真实可播放格式），然后前端 `useAudioPlayer` 改为双重策略：优先 Web Audio 解码，失败时走 `speechSynthesis`。

但最简方式：**在 ChatView.vue 中，收到完整回答或足够长度文本后，直接调 speechSynthesis.speak()**。这让数字人可以"说话"，同时不破坏任何现有后端链路。

### 前端改动

```
修改文件：
├── frontend/src/composables/useAudioPlayer.js  ← 新增 speechSynthesis 播放策略
│   - 检测 AudioContext 是否可用
│   - 不可用时走 speechSynthesis 而非 setTimeout 静默降级
│   - 维护 speak 队列防止重叠
│   - onboundary 驱动口型回调
├── frontend/src/views/tourist/ChatView.vue      ← 不需要改动
└── frontend/src/stores/chat.js                  ← 不需要改动
```

### API 改动

**无**。不新增端点，不修改路由。

### 依赖

**零**。SpeechSynthesis 是 W3C 标准，Chrome/Edge/Firefox/Safari 均支持。`zh-CN` 中文语音是所有现代浏览器预装的。

### 优缺点

| 维度 | 评价 |
|------|------|
| **成本** | 零，无 API 调用费 |
| **延迟** | 极低（本地合成，无网络请求） |
| **集成复杂度** | 低（仅改前端一个文件） |
| **音质** | ✅ 可接受，Chrome 中文女声清晰自然 |
| **口型同步** | onboundary 提供字符级进度，可驱动节奏 |
| **语速/音调** | 可精确控制 |
| **离线可用性** | ✅ 是（部分浏览器支持离线语音包） |
| **跨浏览器一致性** | ⚠️ 不同浏览器/系统的内置语音不同（Windows 用 Microsoft Huihui，macOS 用 Tingting） |
| **多音色切换** | ⚠️ 受限于系统预装语音，无法自定义音色 |
| **情感表达** | ❌ 无法根据内容调整语气，所有内容同一语调 |
| **长文本稳定性** | ⚠️ Chrome speechSynthesis 超长文本可能中途截断，需手动分段 |
| **onboundary 兼容性** | ⚠️ 各浏览器触发行为和精度不一致 |

### 验收标准

- 发送问题后，数字人说出中文回答
- 说一句话时数字人口型张合
- 说完后数字人回到 idle
- 连续提问不卡顿、不重叠播放
- 浏览器不支持时降级为静默（不影响文本展示）
- 前端生产构建通过

---

## 三、方案 B：阿里云百炼 TTS API

### 概述

复用已有的百炼账号和 API Key（已用于 Qwen Vision），接入百炼的 TTS 服务。音频在后端合成，通过 SSE base64 下发到前端，前端用 AudioContext 解码播放。

### 技术原理

```
游客提问
  → QA Pipeline 生成文本答案
  → 句级切分（同现有逻辑）
  → 每句调用百炼 TTS API：
      POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-to-speech
      Headers: Authorization: Bearer {DASHSCOPE_API_KEY}
      Body: { model: "cosyvoice-v1", input: { text: "..." }, parameters: { voice: "zhixiaobai" } }
  → 返回 base64 MP3/WAV/PCM
  → 放入 SSE "audio" 事件
  → 前端 AudioContext 解码 → 真实播放
  → 数字人口型通过音频持续时间驱动
```

### 后端改动

```
新增文件：
├── backend/app/services/tts/bailian.py     ← BailianTTSService 实现
│   - 继承 BaseTTSService
│   - synthesize(text) → TTSAudio
│   - 调用百炼 CosyVoice API
│   - 返回真实 base64 MP3 + 实际 duration_ms
│   - 超时控制、错误降级
│   - 批量/并发限制

修改文件：
├── backend/app/core/config.py              ← 新增配置项
│   TTS_PROVIDER: str = "bailian"
│   TTS_API_KEY: str = ""          (复用 DASHSCOPE_API_KEY)
│   TTS_MODEL: str = "cosyvoice-v1"
│   TTS_VOICE: str = "zhixiaobai"
│   TTS_TIMEOUT_SECONDS: int = 30

├── backend/app/api/chat.py                 ← build_pipeline() 注入 BailianTTSService
│   - 当 TTS_PROVIDER == "bailian" 时构建真实服务
│   - 否则回退 StubTTSService

├── backend/.env.example                    ← 新增 TTS 配置示例
```

### API 接口设计

百炼 CosyVoice 文本转语音 API：

```
POST https://dashscope.aliyuncs.com/api/v1/services/aigc/text-to-speech
Content-Type: application/json
Authorization: Bearer sk-xxx

{
  "model": "cosyvoice-v1",
  "input": {
    "text": "灵山大佛高88米"
  },
  "parameters": {
    "voice": "zhixiaobai",
    "format": "mp3",
    "sample_rate": 16000
  }
}

→ 返回 JSON:
{
  "output": {
    "audio": {
      "data": "base64_encoded_mp3_data...",
      "expires_at": 1234567890
    }
  },
  "usage": {
    "characters": 8
  }
}
```

### 百炼 TTS 可选音色

| 音色 ID | 描述 | 适用场景 |
|---------|------|---------|
| `zhixiaobai` | 知小白 — 标准女声，清晰正式 | 默认导游 |
| `zhixiaoxia` | 知小夏 — 活泼女声 | 儿童模式 |
| `zhixiaobei` | 知小北 — 沉稳男声 | 专业模式 |
| `zhimao` | 知猫 — 可爱风格 | - |
| `zhijia` | 知佳 — 温柔女声 | 情感模式 |

支持 MP3 / WAV / PCM 三种输出格式。

### 前端改动

```
修改文件：
├── frontend/src/composables/useAudioPlayer.js  ← 增强
│   - 传入的 base64 现在是真实 MP3，decodeAudioData 可以解码
│   - 播放成功后触发 onEnded → avatar.onAudioEnded()
│   - AudioContext 不可用时用 <audio> 元素降级
│   - 播放失败时用 speechSynthesis 再降级

不需要修改：
├── frontend/src/stores/chat.js    ← SSE audio handler 不变
├── frontend/src/views/tourist/ChatView.vue
└── frontend/src/api/voice.js      ← 不需要
```

### 依赖

**无新增 Python 依赖**。百炼 TTS 走标准 HTTP POST + JSON，用现有的 `httpx` 即可。

### 优缺点

| 维度 | 评价 |
|------|------|
| **成本** | CosyVoice 按字符计费，约 ¥2/万字符（需核实最新定价）。100 字回答约 ¥0.02 |
| **延迟** | 网络请求 + 合成 ≈ 500ms-2s 每句 |
| **集成复杂度** | 中（需新增 Provider 实现 ~80 行，配置 4 项，工厂注入 1 处） |
| **音质** | ✅ 专业级，清晰自然，超越浏览器内置 |
| **口型同步** | 可精确获取音频时长 `duration_ms`，驱动口型开合节奏 |
| **多音色** | ✅ 5+ 音色可选，可关联讲解模式 |
| **情感表达** | ✅ 不同音色适配不同场景（严肃/活泼/温柔） |
| **离线可用性** | ❌ 依赖网络 |
| **一致性** | ✅ 所有浏览器、所有系统一致音色 |
| **超时风险** | ⚠️ 需设置合理超时 + 降级 |
| **并发风险** | ⚠️ 句级流式可能产生 5-10 个并发 TTS 请求，需限制并发数 |

### 验收标准

- 发送问题后，后端调用真实百炼 TTS，返回可播放的 MP3 音频
- 前端 AudioContext 成功解码并播放
- 数字人口型随音频时长节奏张合
- 百炼 TTS 超时/失败时，前端自动降级为静默（文本仍展示）
- 后端完整回归全部通过
- 编译检查通过

---

## 四、两种方案对比总表

| 维度 | A. 浏览器 SpeechSynthesis | B. 阿里云百炼 TTS |
|------|--------------------------|-------------------|
| **音质** | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐⭐ 专业级 |
| **成本** | ⭐⭐⭐⭐⭐ 零 | ⭐⭐⭐⭐ 极低（约 ¥0.02/次） |
| **延迟** | ⭐⭐⭐⭐⭐ 本地即时 | ⭐⭐⭐ 网络 500ms-2s |
| **集成工作量** | ⭐⭐⭐⭐⭐ 极低（1 文件） | ⭐⭐⭐ 中等（3-4 文件） |
| **多音色** | ⭐⭐ 受限于系统 | ⭐⭐⭐⭐⭐ 5+ 可选 |
| **情感表达** | ⭐ 单一语调 | ⭐⭐⭐⭐ 可映射 |
| **一致性** | ⭐⭐⭐ 浏览器差异 | ⭐⭐⭐⭐⭐ 完全一致 |
| **离线可用** | ✅ | ❌ |
| **口型驱动** | onboundary（不稳定） | duration_ms（稳定） |
| **修改后端** | 不需要 | 需要 |
| **修改前端** | 需要 | 少量 |
| **演示可用** | ✅ | ✅ |
| **赛题印象** | 一般 | 更好 |
| **比赛加分** | 无 | ✅ 真实接入第三方 AI 服务 |

---

## 五、推荐策略：A+B 分层降级

**最佳实践不是二选一，而是分层降级：**

```
                  ┌─ 百炼 TTS 可用？ ──→ 方案 B：专业音质 + 精确时长
                  │
  回答文本到达 ──┤
                  │
                  └─ 百炼失败/超时？ ──→ 方案 A：浏览器 SpeechSynthesis 降级
                                          │
                                          └─ SpeechSynthesis 不可用？ ──→ 静默模式（文本照常展示）
```

### 实施顺序

1. **先做方案 A**（30 分钟）— 跑通完整语音闭环，数字人立刻能说话
2. **再做方案 B**（1 小时）— 接入百炼 TTS，提升音质和演示效果
3. **联调降级链**（15 分钟）— 确保 B 降级到 A，A 降级到静默

### 最终架构

```
SSE "audio" 事件
  ├─ 真实 MP3 base64（来自百炼） → AudioContext 解码 → 播放
  │    └─ 失败 → speechSynthesis 降级
  └─ 或 Stub base64 → decodeAudioData 失败 → speechSynthesis 降级
       └─ 失败 → setTimeout 静默降级
```

前端 `useAudioPlayer.js` 包含完整的 AudioContext / speechSynthesis / setTimeout 三级降级。后端百炼 TTS 成功时走第一级，失败或未配置时走第二/三级。

---

## 六、实施影响面汇总

### 方案 A

| 文件 | 操作 | 行数 |
|------|------|------|
| `frontend/src/composables/useAudioPlayer.js` | 新增 speechSynthesis 策略 | ~60 行 |
| **总计** | **1 文件** | **~60 行** |

### 方案 B

| 文件 | 操作 | 行数 |
|------|------|------|
| `backend/app/services/tts/bailian.py` | 新建 BailianTTSService | ~80 行 |
| `backend/app/core/config.py` | 新增 4 个配置项 | ~8 行 |
| `backend/app/api/chat.py` | 工厂注入逻辑 | ~8 行 |
| `backend/.env.example` | 配置示例 | ~5 行 |
| `frontend/src/composables/useAudioPlayer.js` | 降级链增强 | ~20 行 |
| **总计** | **5 文件** | **~120 行** |

### 方案 A+B 组合

| 阶段 | 工作 |
|------|------|
| Step 1: 方案 A | 前端 speechSynthesis，数字人立即可说话 |
| Step 2: 方案 B | 后端百炼 TTS，提升音质 |
| Step 3: 降级链 | A 作为 B 的降级，AudioContext 失败走 speechSynthesis |
| Step 4: 口型同步 | duration_ms 驱动口型节奏 |

---

## 七、待确认问题

1. **预算**：是否接受百炼 TTS 的按量计费？（约 ¥2/万字符，单次演示约 500-1000 字 = ¥0.1-0.2）
2. **音色选择**：默认导游音色建议用 `zhixiaobai`（标准女声），儿童模式用 `zhixiaoxia`（活泼女声），是否认可？
3. **实施顺序**：是否同意先 A 后 B 的分层策略？
4. **其他对话约束**：是否有其他 Agent 对话中关于 TTS 的方向限制需要合并？
