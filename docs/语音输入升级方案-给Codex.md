# 语音输入 Voice-First 升级方案

> 写给 Codex 审查。描述当前语音输入链路现状、目标升级路线、模块划分和执行顺序。

---

## 一、当前语音输入链路状态

### 1.1 架构总览

```
┌──────────────────────────────────────────────────┐
│  前端 ChatView.vue  toggleRecording()            │
│                                                    │
│  Chrome/Edge → Web Speech API (Google 云端)        │  ← 可用但依赖联网
│  Firefox/Safari → MediaRecorder → POST /asr/...    │  ← 不可用
└──────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│  backend/app/api/voice.py                         │
│    _asr_service = StubASRService()                │  ← 永远返回假数据
│                                                    │
│  backend/app/services/asr/stub.py                 │
│    return ASRResult(text="语音输入占位文本", ...)    │
└──────────────────────────────────────────────────┘
```

### 1.2 各路径可用性

| 浏览器 | 识别路径 | 真实可用？ |
|--------|---------|-----------|
| Chrome / Edge | `window.SpeechRecognition` → Google 云端 | ✅ 可用（需联网） |
| Firefox / Safari | `MediaRecorder` → `POST /api/asr/transcribe` → StubASR | ❌ 永远返回"语音输入占位文本" |
| 所有浏览器 | 文字输入 | ✅ 始终可用 |

### 1.3 与设计文档的差距

设计文档 `10-最终总体设计与开发主线.md` §8.1 要求：

> 1. 前端真实录音并上传
> 2. ASR Provider 返回文本、置信度、候选和耗时
> 3. 使用"灵山、大佛、九龙灌浴、梵宫、五印坛城"等景区热词
> 4. 文本输入和主动选景点始终作为降级通道
> 5. 置信度策略：高自动问答 / 中候选确认 / 低要求重说

当前三条全缺。

---

## 二、目标：Voice-First 交互

### 2.1 交互重心迁移

```
改前（Text-First）：                    改后（Voice-First）：
┌──────────────────────────────┐       ┌──────────────────────────────┐
│ [━━━━━━ 文字输入框 ━━━━━] [发] │       │           🎤                  │
│                     [🎤语音]  │       │        按住说话                │
│                               │       │                              │
│                               │       │   ─ 也可以打字提问 [展开] ─   │
└──────────────────────────────┘       └──────────────────────────────┘
```

大圆形麦克风按钮为底部视觉重心，按住开始录音、松手自动发送。文字输入默认折叠，点击"打字提问"才展开。

### 2.2 三级置信度分流

| 置信度 | 行为 |
|--------|------|
| ≥ 0.85 | 自动发送问答，不弹确认 |
| 0.50–0.85 | 显示识别文本 + 候选列表，用户确认或修改后发送 |
| < 0.50 | "没有听清楚，请再讲一遍" + 自动展开文字输入 |

---

## 三、升级模块

### 模块一：后端真实 ASR — Bailian Paraformer

> 和当前 TTS 走同一个百炼账号，不新增供应商。

**新增文件：** `backend/app/services/asr/bailian.py`

`BailianASRService` 继承 `BaseASRService`，实现 `transcribe(content: bytes) -> ASRResult`：

```python
class BailianASRService(BaseASRService):
    def __init__(self, api_key: str, hotwords: list[str] = None):
        ...

    async def transcribe(self, content: bytes) -> ASRResult:
        # 调用 DashScope Paraformer 文件转写 API
        # POST https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription
        # 请求体：{ model: "paraformer-v2", input: { audio: base64 }, parameters: { hotwords: [...] } }
        # 返回 ASRResult(text, confidence, candidates)
```

**修改文件：** `backend/app/api/voice.py`

```python
# 改前
_asr_service: BaseASRService = StubASRService()

# 改后
def get_asr_service(settings: Settings = Depends(get_app_settings)) -> BaseASRService:
    if settings.asr_provider == "bailian" and settings.asr_api_key:
        from app.services.asr.bailian import BailianASRService
        return BailianASRService(
            api_key=settings.asr_api_key,
            hotwords=settings.asr_hotwords,
        )
    return StubASRService()
```

**修改文件：** `backend/app/core/config.py`

新增 Settings 字段：

```python
asr_provider: str = "stub"
asr_api_key: str = ""
asr_hotwords: list[str] = Field(default_factory=list)
```

**修改文件：** `.env.example`

新增配置段：

```
# ASR (Automatic Speech Recognition)
ASR_PROVIDER=bailian
ASR_API_KEY=
ASR_HOTWORDS=灵山,大佛,九龙灌浴,梵宫,五印坛城,祥符禅寺,大照壁,阿育王柱,天下第一掌,五智门
```

---

### 模块二：前端 Voice-First 交互重构

**修改文件：** `frontend/src/views/tourist/ChatView.vue`

底部输入区改造（仅描述模板结构，不给出完整代码）：

```
原结构：
<div class="input-area">
  <el-input v-model="query" />
  <el-button @click="sendMessage">发送</el-button>
  <el-button @click="toggleRecording">语音提问</el-button>
</div>

新结构：
<div class="voice-first-footer">
  <!-- 主操作：大圆形麦克风按钮，视觉重心 -->
  <button class="mic-record-btn" @pointerdown="startVoice" @pointerup="stopVoice">
    <span>{{ recordingStateText }}</span>
  </button>

  <!-- 置信度候选面板（中置信度时弹出） -->
  <div v-if="showCandidates" class="candidate-panel">
    <p>识别为：</p>
    <button v-for="c in candidates" @click="confirmCandidate(c)">{{ c.text }}</button>
    <el-input v-model="query" placeholder="或手动修改后发送" />
  </div>

  <!-- 文字输入，默认折叠 -->
  <details ref="textInputDetails" class="text-input-fold">
    <summary>也可以打字提问</summary>
    <div class="text-input-row">
      <el-input v-model="query" @keyup.enter="sendMessage" />
      <el-button @click="sendMessage">发送</el-button>
    </div>
  </details>
</div>
```

交互逻辑变更：

```
按下麦克风 → avatar.setState("listening") → startRecording()
松手       → stopRecording() → get audioBlob
           → POST /api/asr/transcribe
           → 收到 { text, confidence, candidates }
           → confidence >= 0.85: 自动 set query + sendMessage()
           → 0.50 <= confidence < 0.85: 弹出候选面板
           → confidence < 0.50: 提示"没听清" + 展开文字输入
```

**停止使用 Web Speech API（Google 云端），统一走 MediaRecorder → 后端 ASR 路径。** 所有浏览器同一条路。文字输入作为降级通道始终可用。

---

### 模块三：置信度三级分流

**新增文件：** `backend/app/schemas/asr.py`

```python
class ASRTranscribeResponse(BaseModel):
    text: str
    confidence: float
    candidates: list[ASRCandidateItem] = Field(default_factory=list)
    duration_ms: int = 0

class ASRCandidateItem(BaseModel):
    text: str
    confidence: float
```

`BailianASRService.transcribe()` 返回的 `ASRResult` 已经包含 `confidence` 和 `candidates`。前端拿到后按以下规则分流：

| 置信度 | UI 行为 | 用户体验 |
|--------|--------|---------|
| ≥ 0.85 | `query = text`，自动调 `sendMessage()` | 无缝问答 |
| 0.50–0.85 | `showCandidates = true`，列出 `candidates` 供点选 | 半自动确认 |
| < 0.50 | `showToast("没有听清楚，请再讲一遍")`，自动展开文字输入 | 引导重试 |

---

### 模块四：热词注入

后端 `BailianASRService` 构造 API 请求时将 `settings.asr_hotwords` 注入 Paraformer 的 `hotwords` 参数。

热词列表（来自设计文档 + 灵山胜境知识库常用景点）：

```
灵山, 大佛, 九龙灌浴, 梵宫, 五印坛城, 祥符禅寺, 大照壁, 阿育王柱,
天下第一掌, 五智门, 降魔浮雕, 古银杏广场, 胜境门楼, 灵山胜境
```

前端不感知热词。

---

## 四、降级与兜底

| 场景 | 兜底行为 |
|------|---------|
| 百炼 ASR API Key 未配置 | 回退 StubASR（已知不可用），前端提示"语音服务未配置" |
| 麦克风权限拒绝 | 自动展开文字输入，不弹错误 |
| ASR 请求超时（15s） | 提示"识别超时，请改用文字输入"，展开输入框 |
| 不入 microphone | `navigator.mediaDevices` 不可用 | 主按钮显示为文字输入入口 |
| 文字输入 | 始终可用，按 `<details>` 折叠展开 |

---

## 五、改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/services/asr/bailian.py` | **新增** | Bailian Paraformer ASR 实现 |
| `backend/app/schemas/asr.py` | **新增** | ASR 响应模型 |
| `backend/app/api/voice.py` | 修改 | 替换 Stub → 按配置选择 Bailian / Stub |
| `backend/app/core/config.py` | 修改 | 新增 `asr_provider` / `asr_api_key` / `asr_hotwords` |
| `.env.example` | 修改 | 新增 ASR 配置段 |
| `frontend/src/views/tourist/ChatView.vue` | **重构** | 底部输入区 Voice-First 改造 |
| `frontend/src/style.css` | 修改 | 新增 `.voice-first-footer` / `.mic-record-btn` / `.candidate-panel` 样式 |
| `frontend/src/composables/useSpeechRecognition.js` | **可废弃** | Voice-First 不再依赖 Chrome Web Speech |

---

## 六、不变的范围

- 不修改 SSE 聊天链路、FAQ、RAG、缓存、Pipeline
- 不修改 `ChatRequest` Schema（语音转文本后 `query` 字段不变）
- 不修改 `SelectionContext`、`GuidedSelector`、`QueryRewriter`
- 不修改前端路由、状态管理 store
- 不做实时流式 ASR（WebSocket），只做文件转写
- 不在 ASR 路径内执行 LLM 方言改写（设计文档 §8.1 第 6 点明确定义了边界）

---

## 七、执行顺序

1. 模块一：后端 BailianASRService + voice.py 改造 + config + .env.example（纯后端，独立验证）
2. 模块二：前端 Voice-First UI 重构（依赖模块一后端可用）
3. 模块三：置信度三级分流（依赖模块一返回 confidence/candidates）
4. 模块四：热词注入（模块一内追加参数，不新增文件）
5. 端到端验收：Chrome + Firefox 各测试 1 次完整语音问答
