# 多端能力与验收矩阵

核验于 2026-10-28。这里“源码已核对”表示找到了实现；“待实测”表示尚无本次设备运行证据。
建图本身不改变浏览器行为，也不等于把当前应用改造成所有终端均可用。

## 1. 目标终端与证据

依据 [产品路线图](plans/2026-10-27-feature-roadmap.md)：手机扫码网页优先，兼顾电脑和平板；微信内置浏览器、iOS Safari、Android 常用浏览器优先验证。

| 终端 | 本次确认 | 本次运行状态 |
|---|---|---|
| iOS Safari / 微信 iOS | 共享 Vue 业务、设备能力 composables、响应式 CSS | 待真机；记录 OS/浏览器/微信版本及权限状态 |
| Android 浏览器 / 微信 Android | 同一套页面及录音/拍照/定位入口 | 待真机；不能用桌面 Chrome 仿真替代 |
| iPad / Android 平板 | 游客 768–999px 等断点和横屏规则存在 | 待竖横屏、触摸与软键盘实测 |
| 桌面 Chrome / Edge / Firefox / Safari | 同一 Web 入口，桌面面板布局 | 待实际浏览器；不承诺所有 Web Speech/媒体能力一致 |
| 原生 App / 小程序 | 本次未发现对应独立客户端工程 | 不属于当前兼容承诺；微信内置网页不等于小程序 |

地图自身使用 UTF-8 Markdown、相对链接和标准库 Python；不依赖本机路径、专用 UI 或联网索引。
Windows/Linux 的校验命令已提供，当前仅在 macOS 主机执行；其他 OS 仍应实际复跑。

## 2. 页面、方向与交互

事实来源：[guide-page.css](../frontend/src/assets/guide-page.css)、[guide-tools.css](../frontend/src/assets/guide-tools.css)、[App.vue](../frontend/src/App.vue)、[index.html](../frontend/index.html)。

- 游客主要断点：`>=1000px`、`768–999px`、`<=767px`，另有矮屏与横屏规则；同一 CSS 后部存在覆盖。
- 后台另有 900px、560px 断点，不能直接套游客布局结论。
- `100vh/100dvh`、底部 safe-area 和 viewport 设置已经存在；仍需验证浏览器地址栏和键盘改变可视高度时是否遮挡。
- ChatView 桌面用 dialog 的 `show()`，小屏用 `showModal()`；需验证焦点、关闭、返回键、滚动锁定。

推荐验收尺寸（CSS px，是测试用例，不是支持范围保证）：

| 用例 | 重点 |
|---|---|
| 320×568 / 390×844 | 默认舞台、输入、拍照、文本与工具弹层；无横向溢出、主要操作可触达 |
| 768×1024 / 1024×768 | 跨断点、工具切换、图表与地图 resize、触摸和方向切换 |
| 844×390 | 短横屏、输入键盘、人物与按钮；只保留一个人物画布 |
| 1280×720 / 1440×900 | 单/双侧面板、长回答、表格、焦点导航 |
| 200% 缩放、减少动态效果 | 标签不丢失、关键操作能用，检查 prefers-reduced-motion 分支 |

## 3. 浏览器能力、回退与代码定位

| 能力 | 现有定位 | 必须验证的条件与回退 |
|---|---|---|
| 摄像头 | [useCamera](../frontend/src/composables/useCamera.js)、ChatView 的 captureFromCamera | HTTPS/权限允许、拒绝、无摄像头、占用、前后摄像头；失败后仍可上传文件；关闭后释放 track |
| 麦克风/录音 | [useRecorder](../frontend/src/composables/useRecorder.js)、[recorder-worklet](../frontend/public/recorder-worklet.js) | getUserMedia、AudioContext、Worklet 加载；ScriptProcessor 降级在主线程高负载下的质量；停止、取消、切后台后 track 释放 |
| 语音识别 | [useSpeechRecognition](../frontend/src/composables/useSpeechRecognition.js)、[voice API](../frontend/src/api/voice.js) | 浏览器 SpeechRecognition 和录音上传 ASR 分开测；服务失败、超时、无网时可改文字 |
| 播放和嘴型 | [useAudioPlayer](../frontend/src/composables/useAudioPlayer.js)、[chat store](../frontend/src/stores/chat.js) | 用户点击后解锁音频、打断、再次播放、蓝牙/扬声器、后台恢复；语音失败时文字继续可读 |
| GPS/模拟 | [useGeolocation](../frontend/src/composables/useGeolocation.js)、[useNarration](../frontend/src/composables/useNarration.js) | HTTPS、权限、真实坐标、低精度/景区外、模拟状态可辨别；原生 coords 字段适配风险见架构，不能用模拟巡游代验真 GPS |
| 3D 人物 | [ThreeAvatar](../frontend/src/components/ThreeAvatar.vue)、[AvatarDisplay](../frontend/src/components/AvatarDisplay.vue) | WebGL/模型加载失败、低端机温升、切形象和多次开关工具；失败保留 SVG 降级和输入功能 |
| 图像上传 | [vision API](../frontend/src/api/vision.js)、[vision.py](../backend/app/api/vision.py) | JPEG/PNG/WebP、空文件、超过服务端上限、相册 HEIC；不支持格式应有可恢复提示 |
| 游客标识/后台 token | [chat store](../frontend/src/stores/chat.js)、[auth store](../frontend/src/stores/auth.js) | 存储受限、隐私模式、退出/401、清除记忆失败；不把本地标识描述为跨设备登录 |
| 流式网络 | [useSSEStream](../frontend/src/composables/useSSEStream.js) | 建连超时、分块边界、连接中断、连续重试、停止后晚到消息；不承诺离线问答 |

安全上下文和媒体策略参考 [MDN getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)、[Geolocation](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API)、[Autoplay](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay)。
远程手机访问开发机 HTTP LAN IP 通常不具备 localhost 的安全上下文条件；不要以禁用浏览器安全保护作为正式验收方案。

## 4. 网络与服务矩阵

每个目标终端至少覆盖正常网络、限速高延迟、请求中断、刷新/重新进入。分别测试：

1. 文字问答 → 出字 → 来源 → 完成；停止后旧音频和旧文字不继续覆盖。
2. 录音 → 转写 → 确认 → 回答；拒绝权限后能输入文字。
3. 相册/拍照 → 识别 → 用户确认提问；失败或不支持格式时能重新选择。
4. 地图工具 → 真实定位或明确标识的模拟 → 景点讲解；网络失败后静态内容仍可理解。
5. 管理员登录 → 知识/资源页面 → 受保护操作；失败后状态不伪装成功。
6. 模型/天气/TTS 缺配置与超时；文本和错误提示符合实际响应，不冒充真实模型结果。

## 5. 验收记录格式

每次实测记录以下字段，不直接把模板或历史截图当本次证据：

| 字段 | 内容 |
|---|---|
| 版本 | commit + 未提交变更说明 |
| 环境 | 设备型号、OS、浏览器/微信版本、视口与方向 |
| 部署 | URL 是否 HTTPS、前后端地址模式、服务/provider 模式；不要写 key |
| 场景 | 对应矩阵用例、权限和网络前提 |
| 结果 | 通过/失败/未测，实际行为和截图或日志路径 |
| 回归 | 问题对应的源码入口、修复后复测结果 |

本次地图建设结果：源码定位已核对；地图校验与工具测试结果见本次交付；业务服务与上述终端体验均未在本次实测。
