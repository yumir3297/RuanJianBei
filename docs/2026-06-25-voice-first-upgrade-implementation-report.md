# Voice-First 语音输入升级实施报告

## 1. 已完成内容

本轮已将游客端输入方向调整为 Voice-First 的最小闭环。

完成项：

1. 新增执行计划文档：`docs/2026-06-25-voice-first-upgrade-execution-plan.md`。
2. 后端 ASR 改为配置化 Provider。
3. 新增百炼 ASR 任务式服务骨架：`backend/app/services/asr/bailian.py`。
4. 扩展 ASR 返回结果，增加 `provider`、`duration_ms`、`confidence_source`、`error_message`、`needs_confirmation`。
5. `/api/asr/transcribe` 保持入口不变，但返回更完整的元数据。
6. 游客端底部输入区改为大麦克风主入口。
7. 文字输入改为折叠降级入口。
8. 前端停止在游客页主链路使用 Chrome Web Speech API。
9. 增加 ASR 结果分流：高可信自动发送，中低可信确认，Stub/不可用时降级到文字。

## 2. 关键实现说明

### 2.1 百炼 ASR 的限制处理

百炼 Paraformer 录音文件识别通常需要公网可访问的音频 `file_url`。

因此本轮没有把浏览器录制的本地 blob 伪装成可直接上传识别，而是加入：

1. `ASR_PUBLIC_AUDIO_BASE_URL`。
2. `ASR_UPLOAD_DIR`。
3. `/api/asr/files/{file_name}` 临时音频访问入口。

如果部署环境配置了公网域名或内网穿透地址，后端会把录音保存到 `ASR_UPLOAD_DIR`，再拼成公网 URL 提交给百炼任务。

如果没有配置公网访问地址，百炼模式会返回 `bailian_unavailable`，前端会提示并展开文字输入。

### 2.2 置信度策略

当前百炼录音文件识别不保证稳定返回原生置信度，所以本轮做了可审计字段：

1. `confidence_source=provider`：供应商原生置信度。
2. `confidence_source=heuristic`：后端启发式置信度。
3. `confidence_source=stub`：本地占位。
4. `confidence_source=unavailable`：服务不可用。

前端不会把 `stub` 或 `unavailable` 自动发送到聊天链路。

## 3. 修改文件

1. `backend/app/core/config.py`
2. `backend/app/api/voice.py`
3. `backend/app/services/asr/base.py`
4. `backend/app/services/asr/stub.py`
5. `backend/app/services/asr/bailian.py`
6. `backend/.env.example`
7. `backend/app/tests/test_asr_bailian.py`
8. `backend/app/tests/test_voice_api.py`
9. `frontend/src/views/tourist/ChatView.vue`
10. `docs/2026-06-25-voice-first-upgrade-execution-plan.md`

## 4. 验证结果

后端测试：

```powershell
cd D:\桌面\软件杯\backend
.\.venv\Scripts\python.exe -m pytest app\tests\test_asr_bailian.py app\tests\test_voice_api.py app\tests\test_pipeline.py -q
```

结果：

```text
11 passed
```

前端构建：

```powershell
cd D:\桌面\软件杯\frontend
npm.cmd run build
```

结果：

```text
✓ built
```

仍存在 Vite chunk 体积警告，这是此前已有的构建体积问题，不影响本轮功能。

## 5. 仍需注意的问题

1. 本地未配置 `ASR_PUBLIC_AUDIO_BASE_URL` 时，百炼录音文件识别不能真实跑通。
2. 如果要本地演示真实 ASR，需要提供公网可访问地址，例如部署域名或内网穿透地址。
3. 文件式 ASR 可能达不到最终语音链路小于 5 秒，后续可能需要升级到实时 WebSocket ASR。
4. 当前仍未接入真实 TTS，语音输出和口型同步不是本轮范围。
5. `useSpeechRecognition.js` 文件仍保留，但游客页主链路已不再使用它，后续确认无其它用途后可删除。

## 6. 下一步建议

1. 本地启动前后端，检查游客页 Voice-First 交互视觉和文字降级是否符合预期。
2. 配置 `ASR_PROVIDER=bailian`、`ASR_API_KEY`、`ASR_PUBLIC_AUDIO_BASE_URL` 后做真实单段语音测试。
3. 如果真实 ASR 延迟过长，进入实时 WebSocket ASR 方案设计。
