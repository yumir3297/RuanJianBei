# 2026-06-22 Three.js 数字人替换最终执行版（给 Claude）

## 1. 文档定位

本文件是 `2026-06-22-threejs-avatar-replacement-plan-v2.md` 的收敛执行版，供 Claude 直接按步骤实施。

输入依据：

1. 当前仓库代码现状
2. `docs/2026-06-22-threejs-avatar-replacement-plan-v2.md`
3. `docs/2026-06-22-threejs-avatar-character-design-draft.md`

目标：

1. 吸收 v2 中正确且高价值的技术细化
2. 修正 v2 中与当前项目真实结构不一致的地方
3. 输出一份更适合直接编码执行的最终版任务文档

本文件优先考虑：

1. 真实可落地
2. 尽量少返工
3. 尽量不扩大后端 schema 改动
4. 先完成闭环，再做旧栈清理

## 2. 对 v2 的评估结论

## 2.1 直接采纳的内容

以下内容直接采纳：

1. 将任务按 Phase 分组，而不是平铺 12 个步骤
2. 将 `visemeTimeline` 迁移单独列为高风险 Phase
3. 将 `ThreeAvatar` 的 preset 构建拆到独立目录，避免组件膨胀
4. 明确指出 `AvatarConfig.vue` 的保存语义存在 bug
5. 明确指出 `frontend/index.html` 里 Live2D CDN 需要最终清理
6. 明确指出 `ThreeAvatar` 当前 `emotion` 监听为空实现，需要补表达层
7. 明确要求游客端和管理端最终都只保留 Three.js 渲染链

## 2.2 采纳但需要修正的内容

以下内容方向正确，但必须按本文件修正后执行：

### A. visemeTimeline 的时钟方案

v2 正确指出：

1. `ThreeAvatar` 当前是连续能量驱动模型
2. 后端 `visemeTimeline` 是离散口型时间线
3. 需要统一时钟源

但 v2 示例中隐含使用“秒级 timeline”，这与当前项目真实数据不一致。

当前项目后端 `visemeTimeline` 的 `start/end` 单位是 **毫秒**，不是秒。

最终要求：

1. 所有口型时间线计算在前端统一使用 **毫秒**
2. `AudioContext.currentTime` 如被使用，必须在使用前转换为毫秒
3. `speechProgress * totalDuration` 的 fallback 也必须以毫秒计算

### B. 管理端配置真源

v2 正确指出 `remoteConfigId` 固定为首次加载 ID 的问题，但它默认前端已经持有全部配置列表，这一点当前代码中并不存在。

当前真实情况：

1. `frontend/src/api/admin.js` 只有 `fetchAvatarConfig()`，只拿当前激活项
2. 后端其实已经有 `/admin/avatar-configs` 列表接口

最终要求：

1. 前端新增 `fetchAvatarConfigs()`，调用现有后端列表接口
2. 管理端保存时，通过 `preset -> model_path -> config row` 匹配正确的配置 ID
3. 不允许继续沿用“首次 active 配置 ID 固定不变”的逻辑

### C. 后端持久化范围

v2 提到要把 `voiceType / speechRate / volume` 一起同步保存，但当前后端表结构里只有 `voice_type`，没有 `speech_rate` 和 `volume`。

最终要求：

1. 本任务 **不新增数据库字段**
2. 后端只负责跨端持久化：
   - 当前激活 preset
   - `voice_type`
3. `speechRate` 和 `volume` 继续保留在前端 `localStorage`
4. 若未来需要跨设备同步 `speechRate` 和 `volume`，另起独立任务

### D. 默认角色策略

v2 建议把默认 preset 改成 `modern`，但当前后端种子数据默认激活的是 `preset:monk`，且这更符合项目文化场景。

最终要求：

1. 保持后端种子默认激活项为 `preset:monk`
2. 前端默认 fallback 也统一为 `monk`
3. 不在本任务中修改默认激活角色为 `modern`

原因：

1. 与当前数据库种子一致
2. 更贴合景区佛教文化场景
3. 避免无必要的数据迁移与产品决策变更

## 2.3 本轮不采纳的内容

以下内容本轮不作为必须项：

1. 管理端卡片必须改成风格化缩略图
2. 明确写死“PixiJS 会减少多少 gzip”
3. 在第一轮就做动态 import 懒加载 avatar preset

处理原则：

1. 卡片视觉优化可以做，但不是阻塞项
2. 包体变化只需实测并记录，不预设具体数值
3. 先跑通功能闭环，再做性能微调

## 3. 最终执行目标

Claude 需要完成以下最终状态：

1. 游客端数字人只使用 `ThreeAvatar`
2. 管理端预览只使用 `ThreeAvatar`
3. 三套预设为：
   - `monk`
   - `hanfu`
   - `modern`
4. `visemeTimeline` 成为主口型驱动
5. `mouthEnergy` 只作为降级兜底
6. 情绪 `neutral / happy / apology` 有可见差异
7. 后端激活配置与前端 preset 一致
8. 后端 `voice_type` 与前端管理端选择一致
9. `speechRate` / `volume` 继续本地保存
10. 移除 Live2D / Pixi 旧链路和 CDN 脚本

## 4. 设计输入约束

Claude 在做 Three.js 三角色时，必须参考：

`docs/2026-06-22-threejs-avatar-character-design-draft.md`

其中角色视觉基线已确定：

1. `monk`：明彻法师
2. `hanfu`：清岚
3. `modern`：景行

允许在不背离文档主方向的前提下做轻微实现级调整，但不得将三者做成只有颜色差异的同一人。

## 5. 实施约束

### 5.1 不允许做的事

1. 不引入 `glTF` / `VRM` / `FBX`
2. 不引入 Blender 协作流程
3. 不新增数据库字段
4. 不改变后端 SSE 协议结构
5. 不删除旧栈，直到新链路验证通过

### 5.2 允许做的最小后端改动

本任务允许的最小后端 API 改动只有：

1. 使用已有 `GET /admin/avatar-configs`
2. 新增一个最小更新接口，仅更新 `voice_type`

推荐接口：

```text
PATCH /admin/avatar-configs/{config_id}
body: { "voice_type": "male_calm" }
```

说明：

1. 不改 schema
2. 不改 `model_path`
3. 不改 `preview_url`
4. 只补足当前管理端真正可保存的字段

## 6. 最终执行步骤

## Phase 1：预设层重构

### 目标

把当前 `useModelManager.js` 从 Live2D 模型切换器改成 Three.js preset 注册表。

### 必做事项

1. 重构 `frontend/src/composables/useModelManager.js`
2. 引入新的语义：
   - `AVATAR_PRESETS`
   - `DEFAULT_PRESET_KEY`
   - `normalizePresetKey()`
   - `presetToModelPath()`
   - `modelPathToPreset()`
   - `getPresetList()`
3. 预设键固定为：
   - `monk`
   - `hanfu`
   - `modern`
4. 与后端映射固定为：
   - `monk -> preset:monk`
   - `hanfu -> preset:hanfu`
   - `modern -> preset:modern`

### 建议实现方式

```js
export const AVATAR_PRESETS = {
  monk: { ... },
  hanfu: { ... },
  modern: { ... },
};

export const DEFAULT_PRESET_KEY = "monk";

export function normalizePresetKey(value) { ... }
export function presetToModelPath(key) { ... }
export function modelPathToPreset(modelPath) { ... }
export function getPresetList() { ... }
```

### 兼容要求

为减少一次性大改，允许在过渡期保留以下兼容导出：

```js
export const AVATAR_MODELS = AVATAR_PRESETS;
export const DEFAULT_MODEL_KEY = DEFAULT_PRESET_KEY;
```

但在最终清理阶段，如果全项目不再引用旧名字，可移除兼容别名。

### 相关文件

1. `frontend/src/composables/useModelManager.js`

## Phase 2：ThreeAvatar 渲染层重构

### 目标

让 `ThreeAvatar` 从“单一程序化头像”升级成“三预设角色 + 情绪表达 + 可重建 preset”的正式组件。

### 必做事项

1. 将 `frontend/src/components/ThreeAvatar.vue` 拆分 preset 构建逻辑
2. 新建目录：

```text
frontend/src/components/avatar-presets/
  index.js
  monk.js
  hanfu.js
  modern.js
```

3. `ThreeAvatar` 新增 props：
   - `preset`
   - `visemeTimeline`
   - `speechProgress`
   - `speechSyncActive`
4. 构建共享基础面部结构：
   - 头
   - 眼
   - 瞳孔
   - 嘴
   - 眉
5. 预设差异必须至少体现在：
   - 发型
   - 服装轮廓
   - 配饰
   - 配色

### 明确要求

不得把三套 preset 做成：

1. 同一发型
2. 同一服装结构
3. 仅靠颜色区分

### 情绪映射要求

至少完成以下映射：

1. `neutral`
   - 默认眉眼
   - 默认嘴角
   - 默认头部姿态
2. `happy`
   - 嘴角上扬
   - 眼部略收
   - 头部轻微抬起或偏转
3. `apology`
   - 眉形下压或内收
   - 嘴角下收
   - 头部轻微下倾

### 相关文件

1. `frontend/src/components/ThreeAvatar.vue`
2. `frontend/src/components/avatar-presets/index.js`
3. `frontend/src/components/avatar-presets/monk.js`
4. `frontend/src/components/avatar-presets/hanfu.js`
5. `frontend/src/components/avatar-presets/modern.js`

## Phase 3：visemeTimeline 迁移与高风险验证

### 目标

将 `visemeTimeline` 变为 ThreeAvatar 的主口型驱动，并保证单位与时钟一致。

### 最重要的约束

**当前项目的 viseme timeline 单位是毫秒。**

Claude 在实现时必须：

1. 用毫秒进行 timeline 定位
2. 不允许把 timeline 当成秒直接用

### 建议方案

在 `frontend/src/composables/useAudioPlayer.js` 中新增统一播放时钟状态：

1. `playbackMode`
   - `idle`
   - `audio`
   - `browser`
   - `silent`
2. `playbackStartAudioTime`
   - AudioContext 时钟，单位秒，仅 `audio` 模式使用
3. `playbackStartWallMs`
   - 浏览器时间戳，单位毫秒，`browser` 模式使用
4. `playbackDurationMs`
   - 本次播放持续时间，单位毫秒

### 实现要求

`ThreeAvatar` 中应新增一个“解析当前口型状态”的方法，逻辑如下：

1. 若 `speechSyncActive=false` 或 `visemeTimeline` 为空：
   - 使用 `mouthEnergy` 降级
2. 若 `playbackMode === "audio"`：
   - 用 `(audioContext.currentTime - playbackStartAudioTime) * 1000` 计算当前 elapsedMs
3. 若 `playbackMode === "browser"`：
   - 用 `Date.now() - playbackStartWallMs` 计算 elapsedMs
4. 若上述信息不可用，但 `speechProgress` 有值：
   - 用 `speechProgress * totalDurationMs` 作为 fallback
5. 用 `elapsedMs` 对 `visemeTimeline` 做二分定位
6. 采用线性插值或等价平滑策略，驱动：
   - `mouthOpen`
   - `mouthForm`

### 技术要求

1. 口型主驱动不得依赖随机波动
2. 口型主驱动不得只依赖 `mouthEnergy`
3. `mouthEnergy` 只能作为 timeline 缺失时的兜底

### 阶段验收门槛

如果本阶段失败，不要进入旧栈删除阶段。

失败判定包括：

1. 嘴型明显与语音不同步
2. 口型抖动严重
3. timeline 驱动比当前 Live2D 版本明显更差

### 相关文件

1. `frontend/src/composables/useAudioPlayer.js`
2. `frontend/src/components/ThreeAvatar.vue`

## Phase 4：页面接入统一

## 4A 游客端

### 目标

彻底移除游客端对 `Live2DAvatar` 的分支依赖。

### 必做事项

1. 修改 `frontend/src/views/tourist/ChatView.vue`
2. 删除：
   - `Live2DAvatar` import
   - `is3DModel` 分支判断
   - Live2D 条件渲染分支
3. 永远渲染 `ThreeAvatar`
4. 保留 `AvatarDisplay` 作为 Three.js 初始化失败的降级组件
5. 传入以下 props：
   - `preset`
   - `emotion`
   - `isSpeaking`
   - `visemeTimeline`
   - `speechProgress`
   - `speechSyncActive`

## 4B 管理端

### 目标

彻底移除管理端预览对 `Live2DAvatar` 的分支依赖。

### 必做事项

1. 修改 `frontend/src/views/admin/AvatarConfig.vue`
2. 删除：
   - `Live2DAvatar` import
   - `selectedIs3D`
   - `previewAvatarRef.switchModel()` 逻辑
3. 预览区始终使用 `ThreeAvatar`
4. 模型卡片只展示三项：
   - `monk`
   - `hanfu`
   - `modern`
5. 卡片网格从 4 列改为 3 列

### 相关文件

1. `frontend/src/views/tourist/ChatView.vue`
2. `frontend/src/views/admin/AvatarConfig.vue`

## Phase 5：配置真源与保存逻辑修复

### 目标

让“当前激活 preset”和“voice_type”真正可保存、可刷新、可跨端读取。

### 必做事项

#### A. 前端 API 层

修改 `frontend/src/api/admin.js`：

1. 保留 `fetchAvatarConfig()`
2. 新增 `fetchAvatarConfigs()`
   - 调用已有 `GET /admin/avatar-configs`
3. 新增 `updateAvatarConfig(configId, payload)`
   - 调用新建的最小 patch/update 接口

#### B. 后端 API 层

在 `backend/app/api/admin.py` 新增一个最小更新接口，仅允许更新 `voice_type`。

建议：

1. 新增 request schema
2. 路径使用 `PATCH /admin/avatar-configs/{config_id}`
3. 只更新 `voice_type`

#### C. 管理端保存逻辑

在 `AvatarConfig.vue` 中：

1. onMounted 时加载完整配置列表
2. `selectedPreset` 来自：
   - `modelPathToPreset(activeConfig.model_path)`
3. `handleSave()` 时：
   - 根据 `selectedPreset` 找到对应 config row
   - 如 `voiceType` 与该行不同，先 patch 更新 `voice_type`
   - 再调用 activate 接口激活该行
   - 最后把 `speechRate` 和 `volume` 存到 `localStorage`

### 明确要求

1. 不新增后端 `speech_rate` 和 `volume` 字段
2. 不扩展本任务为“全量数字人配置中心”
3. 只修当前真正影响执行闭环的保存逻辑

### 游客端读取规则

在 `ChatView.vue` 中，配置读取优先级改为：

1. 优先读后端 active config
   - `model_path -> preset`
   - `voice_type`
2. 若后端不可用，则 fallback 到 `localStorage`
3. `speechRate` / `volume` 只从本地读取

### 相关文件

1. `frontend/src/api/admin.js`
2. `frontend/src/views/admin/AvatarConfig.vue`
3. `frontend/src/views/tourist/ChatView.vue`
4. `backend/app/api/admin.py`
5. 如有需要：`backend/app/schemas/admin.py`

## Phase 6：降级、清理、验证

### 6A 降级与兜底

必须保留以下降级路径：

1. 游客端：
   - Three.js 初始化失败 -> `AvatarDisplay`
2. 管理端：
   - 预览失败 -> 错误提示
   - 但不影响配置卡片选择和保存逻辑

### 6B 旧栈清理

只有在 Phase 1-5 验收通过后，才允许执行：

1. 删除 `frontend/src/components/Live2DAvatar.vue`
2. 从 `frontend/package.json` 移除：
   - `pixi.js`
   - `pixi-live2d-display`
3. 从 `frontend/index.html` 移除 Live2D CDN 脚本
4. 清理项目中所有 Live2D / Pixi 残留引用

### 6C 构建与回归验证

必须执行：

```text
npm.cmd run build
```

必须验证：

1. 游客端聊天页可正常加载
2. 三个 preset 都可切换
3. 三个 preset 肉眼可区分
4. `happy` 和 `apology` 有可见差异
5. 说话时口型由 timeline 主导
6. timeline 缺失时能用 `mouthEnergy` 降级
7. 管理端保存后刷新仍能读取正确激活角色
8. `frontend/index.html` 无 Live2D CDN

### 6D 性能收尾

只做轻量级收尾：

1. 粒子数可从 200 降到 100
2. 部分几何细分可适度降低
3. 如无必要，不要在本轮再做复杂懒加载架构

## 7. 关键实现决策总结

Claude 执行时请遵守以下最终决策：

1. 默认 preset 保持 `monk`
2. `visemeTimeline` 单位按毫秒处理
3. `voice_type` 走后端持久化
4. `speechRate` / `volume` 保持前端本地持久化
5. Three.js preset 必须有结构差异，不只是颜色差异
6. 先完成闭环，再删除 Live2D 旧栈

## 8. 交付物要求

Claude 完成后应至少产出：

1. 代码改动
2. 变更说明
3. 构建验证结果
4. 三 preset 差异说明
5. 口型同步实现说明
6. 仍存在的残余风险说明

## 9. 停止条件

如果出现以下情况，Claude 应停止继续删除旧栈，并提交中间状态说明：

1. `visemeTimeline` 驱动明显失真
2. 三角色无法做出足够结构化差异
3. 管理端保存后游客端仍无法稳定读到正确 preset
4. 删除 Live2D 后构建或运行出现不可快速修复的问题

## 10. 建议执行顺序

按以下顺序执行，不要乱序：

```text
Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6
```

其中：

1. Phase 3 完成后先做一次口型专项检查
2. 通过后再进入 Phase 4-6

## 11. 本文档优先级

执行中若本文件与以下文档冲突：

1. `2026-06-22-threejs-avatar-replacement-plan-v2.md`
2. 之前的 DeepSeek review 计划文档

以本文件为准。
