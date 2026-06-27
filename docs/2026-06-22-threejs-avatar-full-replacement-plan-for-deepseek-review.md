# 2026-06-22 Three.js 数字人彻底替换执行方案（供 DeepSeek 审阅）

## 1. 结论

本项目将数字人方案从 `Live2D + PIXI` 彻底切换为 `Three.js` 的“类 3D、风格化、非写实”数字人，是可行的。

当前仓库不是从零开始：

1. 前端依赖中已经包含 `three`。
2. 游客端聊天页已经接入了 `ThreeAvatar` 原型。
3. 后端已经能输出情绪和口型时间线数据，可复用到 Three.js 数字人。
4. 管理端、配置链路、口型驱动方式仍存在 Live2D 遗留，需要统一。

本方案只定义执行步骤，不启动实现。

## 2. 本次替换的目标边界

### 2.1 最终目标

将当前数字人能力统一为一套 Three.js 方案，满足以下要求：

1. 游客端只使用 Three.js 数字人。
2. 管理端预览只使用 Three.js 数字人。
3. 保留并强化现有情绪、说话状态、口型同步能力。
4. 支持 3 套风格化 3D 预设形象：
   - `monk`
   - `hanfu`
   - `modern`
5. 后端配置与前端预设一一对应，不再依赖 Live2D 模型地址。
6. 最终可移除 `pixi.js` 与 `pixi-live2d-display` 依赖。

### 2.2 明确不做

本轮不做以下内容：

1. 不引入写实级真人数字人。
2. 不引入 `GLB / VRM / FBX` 外部高精模型资产管线。
3. 不接 Blender 建模协作流程。
4. 不改变后端问答主链路、TTS 主链路和 SSE 事件结构。

## 3. 当前仓库现状摘要

### 3.1 已存在的 Three.js 基础

1. `frontend/package.json` 已包含 `three` 依赖。
2. `frontend/src/components/ThreeAvatar.vue` 已有可运行的程序化 3D 数字人原型。
3. `frontend/src/views/tourist/ChatView.vue` 模板层已经切到 `ThreeAvatar`。

### 3.2 尚未完成的替换项

1. 管理端预览仍使用 `Live2DAvatar.vue`。
2. `ThreeAvatar.vue` 目前只接收 `emotion` 和 `isSpeaking`，未接入 `modelKey`、`speechProgress`、`speechSyncActive`、`visemeTimeline`。
3. 现有 Three.js 口型驱动主要依赖音频能量，不是主用后端下发的口型时间线。
4. 前端仍保留 `useModelManager.js` 中的 Live2D 模型配置。
5. 后端 `avatar_configs` 仍是 `model_path / preview_url / voice_type` 的旧思路。
6. 管理端“保存配置”当前更接近“激活已有配置”，不是完整更新当前选择。

### 3.3 当前可复用的后端能力

以下能力可直接复用到 Three.js 替换中：

1. `avatar` SSE 事件中的 `emotion`
2. `audio` 事件中的 `viseme_timeline`
3. 前端 `speechProgress`
4. 前端 `useAvatar` 状态机
5. 前端 `useAudioPlayer` 的音频播放与 `mouthEnergy`

结论：后端数据链路不需要重做，重点是前端渲染层和配置层统一。

## 4. 目标技术路线

本次采用“程序化类 3D 预设方案”，而不是“外部高精模型资产方案”。

原因：

1. 当前仓库没有现成 `glb/gltf/vrm` 资产。
2. 当前 `ThreeAvatar` 已具备原型基础，扩展成本低。
3. 对比赛演示、游客端展示、管理端预览来说，风格化 3D 已足够形成明显升级感。
4. 口型同步、情绪切换、三形象切换比“写实程度”更影响当前项目完成度。

## 5. 执行总原则

1. 先统一功能，再删除旧栈。
2. 先保证游客端和管理端都能用，再做依赖清理。
3. 先用程序化 3D 预设跑通三形象和口型，再考虑后续高精资产。
4. 后端接口能复用则复用，优先不改 SSE 协议。
5. 每一步都应保持系统可回退、可构建、可验收。

## 6. 具体执行步骤

下表中的“可由 Codex 直接完成”表示该步骤可以由我直接实现，不依赖外部建模或额外人工素材。

| 步骤 | 目标 | 具体动作 | 涉及文件 | 前置依赖 | 可由 Codex 直接完成 |
|---|---|---|---|---|---|
| 1 | 固化替换目标 | 明确最终方案为“风格化类 3D、非写实、三预设形象”，并将后端已有 `preset:monk / preset:hanfu / preset:modern` 作为唯一正式形象入口。 | `backend/app/db/bootstrap.py` | 已确认 | 是 |
| 2 | 统一前端预设层 | 重构前端模型配置，使 `useModelManager.js` 从“Live2D URL 列表”转为“Three.js 预设定义表”，包含 `key`、`label`、`description`、`runtime`、颜色、服装、发型、配饰等参数。保留兼容映射，确保 `preset:*` 与 `modelKey` 一致。 | `frontend/src/composables/useModelManager.js` | 步骤 1 | 是 |
| 3 | 升级 ThreeAvatar 接口 | 扩展 `ThreeAvatar.vue`，支持 `modelKey`、`speechProgress`、`speechSyncActive`、`visemeTimeline`、`switchModel()`。将“多形象切换”和“口型时间线驱动”纳入正式实现。 | `frontend/src/components/ThreeAvatar.vue` | 步骤 2 | 是 |
| 4 | 用口型时间线替代随机/能量式主驱动 | 将现有 Live2D 中的 `visemeTimeline + speechProgress` 逻辑迁移到 `ThreeAvatar`。音频能量 `mouthEnergy` 保留为降级策略，而不是主策略。 | `frontend/src/components/ThreeAvatar.vue`、`frontend/src/composables/useAudioPlayer.js` | 步骤 3 | 是 |
| 5 | 游客端彻底切换 | 清理 `ChatView.vue` 中残留的 `Live2DAvatar` 依赖，确保游客端只保留 `ThreeAvatar` 和 `AvatarDisplay` 降级逻辑；并保证 `emotion / speaking / visemeTimeline / speechProgress` 全链路仍正常。 | `frontend/src/views/tourist/ChatView.vue` | 步骤 3、4 | 是 |
| 6 | 管理端预览切换 | 将管理端的实时预览从 `Live2DAvatar` 替换为 `ThreeAvatar`。让模型卡片真正驱动 `monk / hanfu / modern` 三套预设，支持预览说话、情绪切换、切换形象。 | `frontend/src/views/admin/AvatarConfig.vue` | 步骤 3 | 是 |
| 7 | 修正配置持久化语义 | 改造前后端配置逻辑，使管理端保存的不是“一个 Live2D 风格配置 ID 的激活动作”，而是与 Three.js 预设真实一致的配置结果。可选策略有两种：A. 继续保留 `avatar_configs` 表，但让每条记录与一个 Three 预设绑定；B. 增加更新接口，让 `model_path` 明确存储 `preset:*`。推荐先做 A，改动小。 | `frontend/src/api/admin.js`、`frontend/src/views/admin/AvatarConfig.vue`、`backend/app/api/admin.py`、`backend/app/models/avatar_config.py` | 步骤 1、6 | 是 |
| 8 | 校正默认值与初始化 | 统一前端默认值、后端种子数据、管理端读取逻辑、游客端读取逻辑，确保默认形象一致，且刷新后不出现游客端与管理端不一致的问题。 | `frontend/src/composables/useModelManager.js`、`frontend/src/views/tourist/ChatView.vue`、`frontend/src/views/admin/AvatarConfig.vue`、`backend/app/db/bootstrap.py` | 步骤 7 | 是 |
| 9 | 保留兼容降级 | 若 Three.js 初始化失败，游客端继续降级为 `AvatarDisplay.vue`；管理端在预览失败时继续显示错误提示，但不影响配置操作。 | `frontend/src/views/tourist/ChatView.vue`、`frontend/src/views/admin/AvatarConfig.vue` | 步骤 5、6 | 是 |
| 10 | 移除 Live2D 旧栈 | 在游客端、管理端、配置链路均跑通后，删除 `Live2DAvatar.vue` 及其接入代码，移除 `pixi.js` 和 `pixi-live2d-display` 依赖，清理无用导入和旧文案。 | `frontend/src/components/Live2DAvatar.vue`、`frontend/package.json`、相关引用文件 | 步骤 5、6、7、8 验收通过 | 是 |
| 11 | 验证构建与回归 | 执行前端构建，检查游客端聊天、管理端预览、形象切换、语音播放、口型同步、情绪切换、错误降级路径。 | `frontend` 全局 | 步骤 10 | 是 |
| 12 | 性能与包体收尾 | 根据构建结果，对 ThreeAvatar 做轻量性能收尾，包括降低粒子数、减少几何复杂度、必要时按页面做懒加载。若主包过大，再做分包。 | `frontend/src/components/ThreeAvatar.vue`、`frontend/vite.config.*`（如需要） | 步骤 11 | 是 |

## 7. 建议执行顺序

推荐按以下顺序推进：

1. 步骤 1 到 4：把 Three.js 数字人补成正式可用组件。
2. 步骤 5 到 6：让游客端和管理端都切到 Three.js。
3. 步骤 7 到 8：统一配置语义与默认值。
4. 步骤 9：保留降级与错误兜底。
5. 步骤 10 到 12：删除旧栈、构建验证、性能收尾。

## 8. 风险与对应策略

### 风险 1：ThreeAvatar 当前只是原型，形象差异度不够

表现：

1. 三套预设可能只是颜色和细节差异，不够“像三个人”。

策略：

1. 第一阶段先保证形象结构、服装、配色、发型、配饰都可区分。
2. 若演示效果仍不够，再进入下一阶段引入外部 `GLB/VRM` 资产。

### 风险 2：口型不如 Live2D 自然

表现：

1. Three.js 自定义嘴型可能比 Live2D 参数化嘴型更机械。

策略：

1. 主用 `visemeTimeline` 插值驱动。
2. `mouthEnergy` 仅做兜底。
3. 增加平滑过渡、张合幅度曲线和嘴型圆展参数。

### 风险 3：管理端保存配置与游客端加载配置不一致

表现：

1. 本地 `localStorage`、后端激活配置、默认值三者可能出现冲突。

策略：

1. 明确单一真源。
2. 建议以“后端激活配置”为跨端真源，本地缓存仅作临时优化。

### 风险 4：旧栈删除过早导致回退困难

表现：

1. 如果在游客端和管理端都稳定前就删掉 Live2D，排障成本会上升。

策略：

1. 必须在步骤 11 验收通过后再做步骤 10。

### 风险 5：前端主包继续变大

表现：

1. 当前前端主包已经偏大，Three.js 替换后若处理不当会进一步增大。

策略：

1. 优先复用已有 `three`。
2. 不额外引入重量级控制库、后处理库或外部模型解码器。
3. 必要时让数字人组件按页面懒加载。

## 9. 验收标准

完成替换后，应满足以下验收口径：

1. 游客端不再渲染 Live2D，数字人仅由 Three.js 提供。
2. 管理端预览不再渲染 Live2D，数字人仅由 Three.js 提供。
3. 三套预设形象可明确区分。
4. 情绪状态 `neutral / happy / apology` 可见。
5. 说话状态可见，口型由 `visemeTimeline` 驱动。
6. 若口型时间线缺失，仍能以 `mouthEnergy` 进行降级说话动画。
7. 配置保存后，游客端刷新仍能加载正确形象与音色。
8. `vite build` 通过。
9. 删除 Live2D 依赖后，项目仍可正常构建运行。

## 10. 我可以直接完成的步骤清单

以下步骤可以由 Codex 直接完成，不依赖外部建模或额外人工素材：

1. 步骤 1：统一预设命名与替换目标
2. 步骤 2：重构 `useModelManager.js`
3. 步骤 3：升级 `ThreeAvatar.vue`
4. 步骤 4：迁移口型时间线驱动
5. 步骤 5：游客端彻底切换
6. 步骤 6：管理端预览切换
7. 步骤 7：配置持久化逻辑修正
8. 步骤 8：默认值与初始化统一
9. 步骤 9：降级与错误兜底
10. 步骤 10：移除 Live2D 旧栈
11. 步骤 11：构建与功能回归验证
12. 步骤 12：轻量性能收尾

## 11. 当前不需要外部协作的原因

本轮选择程序化类 3D 方案，因此暂时不需要：

1. 外部建模师
2. Blender 文件
3. 贴图绘制协作
4. `GLB / VRM` 资产采购或下载

如果后续审阅意见认为“三预设形象辨识度仍不足”，再进入第二阶段资产化升级。

## 12. 建议给 DeepSeek 重点审阅的问题

建议外部审阅时重点看以下几点：

1. 当前“程序化类 3D 预设方案”是否足以满足项目展示目标。
2. 步骤 7 的配置持久化方案是否优先采用“保留表结构、绑定 Three 预设”的低改动策略。
3. `visemeTimeline` 迁移到 Three.js 后，是否还需要补充更细的嘴型状态层。
4. 三套预设是否需要在第一轮就做到更强差异化，例如头饰、服装轮廓、发型轮廓明显不同。
5. 是否建议在步骤 10 之前保留短期切换开关，以便回退。

## 13. 执行建议

若 DeepSeek 审阅通过，建议下一步直接进入：

**步骤 2 到步骤 6**

原因：

1. 这是最短的“功能闭环”。
2. 一旦游客端和管理端都完成切换，后续配置修正和旧栈清理就会非常明确。
3. 这几步都可以由 Codex 直接完成，不依赖外部素材。
