# Voice-First 语音输入升级执行计划

## 1. 本轮目标

将游客端输入方式从“文字主输入、语音辅助按钮”升级为“语音主输入、文字降级入口”。

本轮优先完成最小闭环：

1. 游客端底部输入区改为大麦克风主入口。
2. 文字输入默认折叠，作为清晰可见的降级通道。
3. 语音统一走 `MediaRecorder -> 后端 /api/asr/transcribe`。
4. 后端 ASR 从固定 Stub 改成配置化 Provider。
5. 前端按识别可信度做自动发送、候选确认、低可信度降级。

## 2. 关键修正

原方案方向可取，但需要修正以下点：

1. 百炼 Paraformer 录音文件识别不是简单的 base64 单次 POST，而是“提交任务、轮询任务、解析转写结果”的异步链路。
2. 热词不直接写死为数组参数，后端预留 `ASR_VOCABULARY_ID`，用于接入百炼热词表。
3. Provider 不保证返回真实置信度和多候选，因此后端响应需要标记 `confidence_source` 和 `needs_confirmation`。
4. “松手自动发送”只适合高可信结果；不确定结果必须让游客确认，避免把误识别直接送进 RAG/LLM。
5. Web Speech API 先退出主链路，避免 Chrome/非 Chrome 行为不一致，也避免依赖 Google 云端识别。

## 3. 不变范围

1. 不修改聊天 SSE、RAG、FAQ、缓存、证据链主逻辑。
2. 不修改 `ChatRequest` 结构。
3. 不修改图片识别、数字人、管理端主功能。
4. 不批量调用真实付费 ASR，只完成可配置代码与本地测试。
5. Stub 降级保留，但前端需要识别并提示“语音服务未配置/当前为占位结果”。

## 4. 后端改造

### 4.1 配置项

在 `Settings` 中增加：

1. `asr_provider`: 默认 `stub`。
2. `asr_api_key`: 百炼 API Key。
3. `asr_model`: 默认 `paraformer-v2`。
4. `asr_base_url`: 百炼提交任务地址。
5. `asr_task_url`: 百炼查询任务地址。
6. `asr_vocabulary_id`: 热词表 ID，可为空。
7. `asr_timeout_seconds`: 单次识别总超时。
8. `asr_poll_interval_seconds`: 任务轮询间隔。
9. `asr_max_audio_bytes`: 最大音频大小。

### 4.2 服务层

新增 `backend/app/services/asr/bailian.py`。

职责：

1. 提交录音识别任务。
2. 轮询任务状态。
3. 解析转写文本。
4. 返回统一 `ASRResult`。
5. 接口异常时返回低可信错误结果，而不是让前端崩溃。

### 4.3 API 层

修改 `backend/app/api/voice.py`：

1. 从配置选择 `BailianASRService` 或 `StubASRService`。
2. 检查音频大小上限。
3. 返回统一字段：

```json
{
  "text": "识别文本",
  "confidence": 0.72,
  "confidence_source": "provider|heuristic|stub|unavailable",
  "needs_confirmation": true,
  "candidates": [],
  "duration_ms": 1200,
  "provider": "bailian"
}
```

## 5. 前端改造

修改 `frontend/src/views/tourist/ChatView.vue`：

1. 大麦克风按钮成为底部主操作。
2. 按住说话和点击开始/结束两种操作都支持。
3. 录音结束后上传后端 ASR。
4. 高可信度自动发送。
5. 中可信度显示确认面板。
6. 低可信度展开文字输入，提示重说或打字。
7. 文字输入保留，但默认折叠。

前端暂时不删除 `useSpeechRecognition.js`，避免一次改动过大；本轮只停止在游客页主路径中使用它。

## 6. 验收标准

1. `npm run build` 通过。
2. 后端 ASR API 的 stub 模式测试通过。
3. 前端游客页可以看到语音主入口。
4. 后端未配置真实 ASR 时，用户不会误以为已经完成真实识别。
5. 文字输入仍然可用。

## 7. 后续阶段

1. 配置真实百炼 ASR 并做单张/单段手工测试。
2. 如录音文件识别延迟不可控，再切换实时 WebSocket ASR。
3. 接入真实 TTS 后，统一优化语音输入、语音输出、数字人口型的全链路体验。
