# 数字人当前开发运行测试报告

## 1. 总体结论

当前数字人完成度属于“链路骨架已接通，真实演示闭环未完成”。

综合状态：

```text
前端生产构建：通过
Live2D 远程资源：通过
Cubism 口型与表情参数：通过
前端 Avatar 状态机：通过
后端 AvatarConfig API：通过
后端 avatar SSE 事件：通过
Live2D/Pixi 运行时兼容：未通过
真实 TTS 音频：未通过
真实音频口型同步：未通过
流式回答情感映射：未通过
后台配置驱动游客端形象：未通过
模型失败可见降级：未通过
浏览器最终视觉自动验收：当前环境无法执行
```

因此目前不建议把数字人描述为“真实语音驱动、口型同步完整的数字人”。更准确的说法是：已接入 Live2D 模型、SSE 状态驱动和模拟口型，真实 TTS 与稳定运行仍待修复。

## 2. 已通过项目

### 2.1 前端构建

执行：

```text
npm.cmd run build
```

结果：通过。

构建仍有既有的大 chunk 警告，主包体积约 `1.9 MB`，主要包含 Live2D/Pixi。

### 2.2 Cubism Core 与模型资源

实际联网检查全部返回 HTTP 200：

1. Cubism Core：约 207 KB。
2. Haru `model3.json`。
3. `moc3`：约 385 KB。
4. 物理配置。
5. 姿态配置。
6. 两张贴图：合计约 2.7 MB。
7. 8 个表情文件。

模型响应包含：

```text
Access-Control-Allow-Origin: *
```

浏览器跨域下载条件满足。

### 2.3 参数匹配

模型实际口型参数：

```text
ParamMouthOpenY
```

与 `Live2DAvatar.vue` 使用的参数一致。

代码表情映射：

```text
neutral -> f00
happy -> f01
apology -> f04
```

模型中 `f00`、`f01`、`f04` 均存在。

### 2.4 前端状态机

模拟测试通过：

1. 初始状态 `idle`。
2. `idle -> thinking`。
3. avatar 事件触发 `speaking`。
4. `happy` 表情状态。
5. `apology` 表情状态。
6. 音频结束后回到 `idle`。
7. 非法状态被忽略。
8. `viseme_text` 可保存。

### 2.5 后端 Pipeline

`backend/app/tests/test_pipeline.py`：

```text
5 passed
```

实际事件链可产生：

```text
audio -> avatar -> text -> followups -> done
```

直接回答出口使用 `faq_l1` 时，avatar 事件可得到：

```json
{
  "emotion": "happy"
}
```

### 2.6 AvatarConfig

隔离 SQLite 测试：

1. 创建 3 个预设。
2. 列表查询成功。
3. 当前激活项查询成功。
4. 切换激活项成功。
5. 切换后仅保留一个激活项。

当前真实数据库中有：

```text
僧袍法师：激活
汉服导游：未激活
现代导游：未激活
```

## 3. 未通过与风险

### 3.1 P0：Live2D 与 Pixi 主版本不兼容

当前安装：

```text
pixi-live2d-display@0.4.0
pixi.js@7.4.3
```

但 `pixi-live2d-display@0.4.0` 官方 peerDependencies 要求 Pixi 6。

当前依赖树同时包含：

```text
插件内部 @pixi/* 6.5.10
项目 pixi.js 7.4.3
```

运行时类检查结果：

```text
Live2DModel extends project PIXI.DisplayObject = false
```

这表示 Live2DModel 与当前 Pixi 7 Stage 并非同一套 DisplayObject 体系。构建能通过，但真实 WebGL 渲染存在高概率运行错误或不稳定行为。

状态：未通过，属于当前首要阻塞。

### 3.2 P0：没有真实 TTS 音频

`StubTTSService` 只是：

```text
将回答文本 UTF-8 编码后再做 base64
```

该数据不是 MP3、WAV 或其他可播放音频。

前端音频解码失败后只等待一个模拟时长，因此：

1. 用户听不到语音。
2. `<5s` 语音响应指标无法验收。
3. 数字人“播报”目前只是状态模拟。

状态：未通过。

### 3.3 P0：口型不是音频同步

当前口型逻辑每 150ms 在以下值间循环：

```text
ParamMouthOpenY = 0
ParamMouthOpenY = 0.8
```

它没有使用 phoneme、viseme 时间戳或音频能量。

状态：未通过，只能称为“说话动画”，不能称为“真实口型同步”。

### 3.4 P1：流式回答情感始终 neutral

直接回答出口 `_emit_final_answer()` 会调用 `_answer_emotion()`。

但主要流式回答路径 `_queue_audio()` 直接使用：

```text
StubAvatarService.emotion = neutral
```

实际运行得到：

```json
{
  "emotion": "neutral"
}
```

因此真实 RAG/LLM 流式回答不会根据成功、盲区或降级切换表情。

状态：未通过。

### 3.5 P1：后台数字人配置未接入游客端

后端当前激活项为：

```text
僧袍法师 / preset:monk / male_calm
```

游客页没有调用 `/api/admin/avatar-configs/active`，而是始终使用硬编码的远程 Haru 模型。

管理端 `AvatarConfig.vue` 也仍是占位页面。

状态：未通过。

### 3.6 P1：模型失败没有可见降级

`Live2DAvatar.vue` 加载失败时只执行：

```text
console.error(...)
```

它没有向父组件发送错误事件。游客页中的 `avatarError` 只会在处理 SSE 状态时异常才被设置。

结果：

1. 断网或 CDN 失败时容器可能保持空白。
2. 已存在的 `AvatarDisplay.vue` SVG 组件没有作为降级显示。
3. 文本问答仍可用，但数字人区域没有明确提示或替代形象。

状态：未通过。

### 3.7 P2：状态机没有完整驱动 Live2D

游客页只向 Live2D 传入：

```text
emotion
isSpeaking
```

`listening` 和 `thinking` 状态没有传给 Live2D，因此不会产生对应视觉反馈。

`currentViseme` 虽然被保存，但没有传给 Live2D。

状态：部分通过。

### 3.8 P2：模型加载期间可能错过状态

Live2D 模型需要下载约 3 MB 资源。

如果 `emotion` 或 `isSpeaking` 在模型加载完成前变化，watch 回调会因 `model` 为空直接返回；模型加载完成后没有重新应用当前状态。

可能表现：

1. 首次回答已经开始，但模型加载后嘴不动。
2. 首次 `happy/apology` 表情丢失。

状态：存在运行风险。

### 3.9 P2：依赖安全告警

`pixi-live2d-display@0.4.0` 依赖 `gh-pages@4.0.0`，npm 审计为严重告警。

该依赖理论上属于发布工具，不应作为浏览器运行依赖打包，但当前包将其列为 production dependency。

自动修复建议涉及版本变更，未擅自执行。

## 4. 浏览器验收限制

当前桌面会话的内置浏览器执行环境无法创建临时运行资源，因此未完成自动截图和控制台采集。

已完成的替代验证：

1. 前端生产构建。
2. 远程模型全资源联网检查。
3. 依赖主版本与类继承检查。
4. 状态机模拟运行。
5. 后端 Pipeline 实际事件运行。
6. AvatarConfig 隔离数据库运行。

## 5. 当前演示可用性

### 可以演示

1. 页面存在数字人区域。
2. 网络正常且运行时兼容未触发错误时，可尝试显示 Haru 模型。
3. 回答期间可触发模拟开合口型。
4. 直接回答路径可产生 `happy/apology` 情感数据。

### 不能可靠承诺

1. Live2D 必定稳定显示。
2. 数字人有真实语音。
3. 口型与语音同步。
4. 后台切换形象或音色后游客端生效。
5. 流式回答表情正确联动。
6. 断网时数字人有可靠降级。

## 6. 建议修复顺序

需要用户确认后再实施：

1. 统一 Pixi 运行时版本，先解决 Live2D 稳定渲染。
2. 增加 Live2D 加载错误事件和 SVG Avatar 降级。
3. 修复流式路径情感映射。
4. 将激活的 AvatarConfig 接入游客页。
5. 接入真实 TTS，再设计基于音频或 viseme 的口型同步。

本轮没有成功调用 DeepSeek 或 Qwen，没有产生可确认的模型调用费用。

