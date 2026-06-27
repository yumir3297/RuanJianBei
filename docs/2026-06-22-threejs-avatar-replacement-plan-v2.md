# Three.js 数字人彻底替换方案（改进版 v2）

## 1 结论

将数字人方案从 `Live2D + PIXI` 彻底切换为 Three.js 程序化类 3D 风格化数字人，方向正确且可行。当前仓库已有 Three.js 依赖和 `ThreeAvatar` 原型，后端 viseme 时间线和情绪链路可复用。本方案在原 Codex 方案基础上，补全了 visemeTimeline 迁移技术设计、三套预设参数草案、配置持久化修正细节、以及被低估的技术难点。

## 2 目标边界

### 2.1 最终目标

1. 游客端和管理端预览均只使用 Three.js 数字人。
2. 保留并强化情绪、说话状态、口型同步能力。
3. 支持 `monk`/`hanfu`/`modern` 三套风格化 3D 预设形象，可明确区分。
4. 后端配置与前端预设一一对应，不再依赖 Live2D 模型地址。
5. 最终移除 `pixi.js`、`pixi-live2d-display` 依赖及 CDN 脚本。

### 2.2 不做

1. 不引入 `glTF`/`VRM`/`FBX` 外部高精模型资产。
2. 不接 Blender 建模协作流程。
3. 不改后端问答主链路、TTS 主链路和 SSE 协议结构。

## 3 当前状态分析

### 3.1 已有基础

- `frontend/package.json` 已含 `three` 依赖。
- `frontend/src/components/ThreeAvatar.vue` 已有可运行的程序化 3D 头像原型（280 行，纯几何体拼接）。
- `ChatView.vue` 模板层已接入 `ThreeAvatar` 作为默认渲染器。
- 后端 `viseme_timeline`、`emotion` 数据链路完好，`bootstrap.py` 已写入 `preset:monk`/`preset:hanfu`/`preset:modern` 种子数据。

### 3.2 关键缺口

1. `ThreeAvatar` 口型驱动依赖 `mouthEnergy`（音频 RMS 能量），未使用后端下发的 `visemeTimeline`。
2. `useModelManager.js` 仍维护 Live2D 的 URL 列表和 `runtime` 分支逻辑。
3. 管理端 `AvatarConfig.vue` 仍条件渲染 `Live2DAvatar`，且 `saveAvatarConfig` 存在语义 Bug：`remoteConfigId` 始终指向 onMounted 加载时的那一行，用户切换模型后保存的实际仍是旧行。
4. `ThreeAvatar` 的 `emotion` 监听函数为空注释，无表情映射。
5. `index.html` 包含 Live2D CDN 脚本标签，需一并清理。

## 4 被原方案低估的关键技术问题

### 4.1 visemeTimeline 迁移：信号模型不兼容

当前 `ThreeAvatar` 口型驱动是**连续信号**模型：

```js
// 每帧读取 audioPlayer 的连续能量值
let mouthOpen = audioPlayer.mouthEnergy?.value || 0;  // 0~1 浮点
mouthMesh.scale.y = 1 + mouthOpen * 1.2;
```

后端 `visemeTimeline` 是**离散事件列表**：

```json
[
  { "start": 0.0,  "end": 0.15, "value": 0.8, "form": 0 },
  { "start": 0.15, "end": 0.30, "value": 0.3, "form": 1 }
]
```

迁移需要解决三个子问题：

| 子问题 | 说明 | 方案 |
|--------|------|------|
| 时钟同步 | `speechProgress` 来自 `setInterval` 回调，与 `requestAnimationFrame` 不在同一时钟域 | 在 `animate()` 中以 `audioPlayer` 的 `AudioContext.currentTime` 为唯一时钟源，自行推算播放进度 |
| 二分定位 | 每帧根据当前播放时间在 timeline 中定位所在区间 | 在 `animate()` 开头用二分查找当前 viseme 索引 |
| 线性插值 | 相邻 viseme 区间边界处需平滑过渡 | 在区间内按 `(t - start) / (end - start)` 的比例对 `value` 和 `form` 做线性插值，避免口型跳变 |

统一时钟源方案（在 `useAudioPlayer` 中暴露播放起始时间）：

```js
// useAudioPlayer 新增暴露
let playbackStartTime = 0;  // ctx.currentTime when source.start() was called
let playbackDuration = 0;

// ThreeAvatar animate() 中：
const elapsed = audioPlayer.playbackStartTime
  ? ctx.currentTime - audioPlayer.playbackStartTime
  : 0;
const progress = Math.min(elapsed / audioPlayer.playbackDuration, 1);
// 用 progress 在 visemeTimeline 中二分定位
```

### 4.2 预设参数化：280 行组件将膨胀

当前 `buildScene()` 所有几何体参数硬编码。三套预设需要独立的服装轮廓、发型和配色。如不拆分，组件可能膨胀到 800+ 行。

策略：将每套预设的构建函数抽取为独立文件：

```
frontend/src/components/avatar-presets/
├── index.js          # 导出 PRESETS 配置表 + createPresetScene()
├── monk.js           # 僧袍法师：光头 + 桶形袈裟 + 念珠
├── hanfu.js          # 汉服导游：发髻 + 交领宽袖 + 腰带
└── modern.js         # 现代导游：短发 + 西装轮廓 + 领带
```

每个文件导出一个 `buildHeadModifiers(scene, headGroup, params)` / `buildBody(scene, bodyGroup, params)` 函数，由 `ThreeAvatar.vue` 根据 `preset` prop 调用。

### 4.3 三套预设差异化方案

三类形象需要在以下维度达到肉眼可辨的差异：

| 维度 | monk（僧袍法师） | hanfu（汉服导游） | modern（现代导游） |
|------|------------------|-------------------|-------------------|
| 发型 | 光头（无头发几何体） | 发髻（顶部 Cylinder + 簪子） | 短发（多层 PlaneGeometry 刘海） |
| 服装 | 桶形袈裟（扁椭球 + 偏红棕色） | 交领宽袖（多个 Plane 拼接 + 深红） | 西装领（Torus 领子 + 深蓝灰） |
| 配饰 | 颈部念珠（多个小球 + Torus 串） | 腰带（Torus + 玉佩方块） | 领带（扁 Plane 垂于胸前） |
| 肤色 | 偏深 `0xd4a574` | 偏白 `0xf5d5b8` | 中间 `0xe8c4a0` |
| 服装色 | `0x8B4513`（赭褐） | `0xc41e3a`（朱红） | `0x2d3748`（深蓝灰） |

### 4.4 情感表情映射

当前 `ThreeAvatar` 的 `emotion` watch 为空。新方案需要以下映射：

| emotion | 头部 | 眼睛 | 嘴巴 | 身体 |
|---------|------|------|------|------|
| `neutral` | 默认姿态 | 默认状态 | 默认弧度 | 默认呼吸 |
| `happy` | 头微倾 3° | 眼眯 `scaleY=0.55` | Torus 弧度旋转 +12°（嘴角上扬），颜色变浅 | — |
| `apology` | 头低 8°（rotation.x += 0.14） | 眉毛新增（需添加眉部几何体），下压 | Torus 弧度旋转 -8°，颜色变暗 | — |

注意：`apology` 需要新增**眉毛几何体**（当前没有）。建议用两个细长 Plane 或 Box，挂载在 `headGroup` 上，位置在眼睛上方。

## 5 执行步骤（改进版）

### Phase 1：定义层 — 预设参数与配置重构

**步骤 1：固化替换目标**

确认 `preset:monk` / `preset:hanfu` / `preset:modern` 为唯一正式形象入口。后端 `bootstrap.py` 已包含三行种子数据，无需修改。需确认 `AvatarConfig.model_path` 字段只接受 `preset:*` 格式。

涉及文件：`backend/app/db/bootstrap.py`（确认即可，无需改动）。

**步骤 2：设计预设参数表并重构 `useModelManager`**

将当前以 Live2D URL 为核心的 `AVATAR_MODELS` 替换为以 Three.js 预设参数为核心的配置表：

```js
export const AVATAR_PRESETS = {
  monk: {
    key: 'monk', label: '僧袍法师', description: '智慧庄严',
    skin: 0xd4a574, cloth: 0x8B4513, hair: null, // null = 光头
    accessory: 'beads', // 念珠
  },
  hanfu: {
    key: 'hanfu', label: '汉服导游', description: '古典优雅',
    skin: 0xf5d5b8, cloth: 0xc41e3a, hair: 'bun', // 发髻
    accessory: 'jade', // 玉佩腰带
  },
  modern: {
    key: 'modern', label: '现代导游', description: '专业活力',
    skin: 0xe8c4a0, cloth: 0x2d3748, hair: 'short', // 短发
    accessory: 'tie', // 领带
  },
};

export const DEFAULT_PRESET_KEY = 'modern';
```

`useModelManager` 不再管理"模型加载/销毁"（那是 PIXI 时代的职责），改为：
- `getPresetList()` — 返回三套预设的元信息
- `getCurrentPreset()` — 返回当前激活预设的参数对象

涉及文件：`frontend/src/composables/useModelManager.js`

### Phase 2：渲染层 — ThreeAvatar 升级

**步骤 3：多形象切换 + 预设文件拆分**

1. 创建 `frontend/src/components/avatar-presets/` 目录结构。
2. 将 `ThreeAvatar.vue` 的 `buildScene()` 拆分为：基础头面部（共用）+ 按预设加载发型/服装/配饰（从 preset 文件导入）。
3. 组件接收新 prop：`preset: { type: String, default: 'modern' }`。
4. `watch(preset)` 触发时，销毁旧服装/发型 group，调用对应 preset 文件重建。

涉及文件：
- `frontend/src/components/ThreeAvatar.vue`
- `frontend/src/components/avatar-presets/index.js`
- `frontend/src/components/avatar-presets/monk.js`
- `frontend/src/components/avatar-presets/hanfu.js`
- `frontend/src/components/avatar-presets/modern.js`

### Phase 3：口型层 — visemeTimeline 驱动迁移

**步骤 4：口型时间线驱动机**

这是技术难度最高的步骤，建议独立验证后再推进。

4.1 `useAudioPlayer` 暴露播放时间戳：

```js
// 新增暴露：
const playbackStartTime = ref(0);
const playbackDuration = ref(0);

// 在 playAudioBuffer 中记录：
playbackStartTime.value = ctx.currentTime;
playbackDuration.value = audioBuffer.duration / playbackRate;
```

4.2 `ThreeAvatar` 接收新 props：

```js
const props = defineProps({
  emotion: String,
  isSpeaking: Boolean,
  preset: String,
  visemeTimeline: Array,    // 新增
  speechProgress: Number,   // 新增
  speechSyncActive: Boolean,// 新增
});
```

4.3 在 `animate()` 中实现 viseme 驱动：

```js
let currentVisemeValue = 0;
let currentVisemeForm = 0;

function updateViseme() {
  if (!props.speechSyncActive || !props.visemeTimeline?.length) {
    // 降级到 mouthEnergy
    currentVisemeValue = audioPlayer.mouthEnergy?.value || 0;
    currentVisemeForm = 0;
    return;
  }

  const t = audioPlayer.playbackStartTime.value
    ? audioCtx.currentTime - audioPlayer.playbackStartTime.value
    : 0;

  // 二分查找当前 viseme 区间
  const tl = props.visemeTimeline;
  let lo = 0, hi = tl.length - 1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (tl[mid].start <= t) lo = mid;
    else hi = mid - 1;
  }

  const curr = tl[lo];
  if (curr && t >= curr.start && t <= curr.end) {
    currentVisemeValue = curr.value;  // 开口度
    currentVisemeForm = curr.form;    // 圆展度
  }
}

// animate() 循环中：
updateViseme();
mouthMesh.scale.y = 1 + currentVisemeValue * 1.2;
mouthMesh.scale.x = 1 + currentVisemeForm * 0.3;  // form=1 圆唇时加宽
```

涉及文件：
- `frontend/src/components/ThreeAvatar.vue`
- `frontend/src/composables/useAudioPlayer.js`

### Phase 4：切换层 — 页面统一

**步骤 5：游客端彻底切换**

`ChatView.vue` 中移除 `Live2DAvatar` 的条件分支，始终渲染 `ThreeAvatar`，prop 从 `modelKey` 切换为 `preset`：

```vue
<ThreeAvatar
  :preset="avatarConfig.preset"
  :emotion="avatar.currentEmotion.value"
  :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
  :viseme-timeline="visemeTimeline"
  :speech-progress="speechProgress"
  :speech-sync-active="activeAudioSegments > 0"
/>
```

涉及文件：`frontend/src/views/tourist/ChatView.vue`

**步骤 6：管理端预览切换**

`AvatarConfig.vue` ：
1. 移除 `Live2DAvatar` 导入和条件渲染。
2. 模型卡片网格从 4 列改为 3 列（`repeat(3, 1fr)`）。
3. 预览区始终渲染 `ThreeAvatar`，通过 `preset` prop 切换形象。
4. 去掉 `selectedIs3D` computed。
5. 卡片占位图从纯色圆形改为风格化缩略图（如僧袍/汉服/西装的简洁渐变圆形）。

涉及文件：`frontend/src/views/admin/AvatarConfig.vue`

### Phase 5：配置层 — 持久化一致性

**步骤 7：修正 saveAvatarConfig 语义 Bug**

根因：`remoteConfigId` 在 `onMounted` 时固定为首次加载的 config 行 ID，切换模型后未更新。

修复方案：在 `selectModel()` 中同步更新 `remoteConfigId`：

```js
function selectModel(key) {
  selectedModel.value = key;
  previewError.value = false;
  // 根据 preset key 匹配对应的 config 行
  const matched = remoteConfigs.value?.find(
    c => c.model_path === `preset:${key}`
  );
  if (matched) remoteConfigId.value = matched.id;
}
```

`handleSave()` 中增加 voiceType/speechRate/volume 的同步保存逻辑（当前仅激活行，不更新行的属性）。

涉及文件：
- `frontend/src/views/admin/AvatarConfig.vue`
- `frontend/src/api/admin.js`（可能需要增加 PUT 更新行属性的接口）

**步骤 8：统一默认值与初始化**

1. 统一 `DEFAULT_PRESET_KEY = 'modern'` 为前端唯一默认值。
2. 后端 `is_active` 默认设为 `modern` 行（与前端一致）。
3. 游客端加载时优先读后端 `/avatar-configs/active`（跨端真源），本地 `localStorage` 仅作离线缓存。

涉及文件：
- `frontend/src/composables/useModelManager.js`
- `frontend/src/views/tourist/ChatView.vue`
- `frontend/src/views/admin/AvatarConfig.vue`
- `backend/app/db/bootstrap.py`（确认 `modern` 首行 is_active）

### Phase 6：清理层 — 删除旧栈与验证

**步骤 9：降级与错误兜底**

`ThreeAvatar` 初始化失败时（WebGL 不可用等），游客端降级为 `AvatarDisplay` SVG 头像；管理端显示错误提示但不影响配置操作。

涉及文件：`ChatView.vue`、`AvatarConfig.vue`

**步骤 10：移除 Live2D 旧栈**

在步骤 5/6/7/8 全部验通过后执行：

1. 删除 `Live2DAvatar.vue` 组件文件。
2. 从 `package.json` 移除 `pixi.js` 和 `pixi-live2d-display`。
3. 从 `index.html` 移除 Live2D CDN 脚本标签。
4. 清理 `useModelManager.js` 中的 Live2D 模型配置和 `switchModel`/`destroy` 逻辑。
5. 全局搜索残留引用并清理。

涉及文件：
- `frontend/src/components/Live2DAvatar.vue`
- `frontend/package.json`
- `frontend/index.html`
- `frontend/src/composables/useModelManager.js`
- 及其他引用文件

**步骤 11：构建验证与功能回归**

1. `npm run build` 通过。
2. 验证项：游客端聊天、管理端预览、形象切换（三套均可区分）、语音播放、口型同步、情绪切换、降级路径。
3. 检查包体积变化（预期：移除 PixiJS ~450KB gzip，主包减小）。

涉及文件：`frontend` 全局

**步骤 12：性能收尾**

1. 粒子数量从 200 降至 100。
2. 降低部分几何体分段数（头发 Plane 8x8 可降至 4x4）。
3. 必要时对 avatar-presets 目录做动态 import 懒加载。

涉及文件：`ThreeAvatar.vue`、avatar-presets 文件

## 6 执行顺序

```
Phase 1: 步骤 1 → 2      （定义层：预设参数 + 配置重构）
Phase 2: 步骤 3           （渲染层：多形象切换 + 文件拆分）
Phase 3: 步骤 4           （口型层：visemeTimeline 迁移 — 独立验证）
Phase 4: 步骤 5 → 6      （切换层：游客端 + 管理端统一）
Phase 5: 步骤 7 → 8      （配置层：Bug 修复 + 默认值统一）
Phase 6: 步骤 9→10→11→12 （清理层：降级 → 删旧栈 → 验证 → 性能）
```

Phase 3（步骤 4）是技术难度最高的独立子任务，建议在 Phase 2 完成后单独验证口型效果，再推进后续步骤。

## 7 风险与策略

| 风险 | 表现 | 策略 |
|------|------|------|
| 三套预设辨识度不足 | monk/hanfu/modern 仅是颜色差异，不像三个不同的人 | Phase 2 必须保证发型/服装轮廓有结构性差异（光头 vs 发髻 vs 短发），不满足则阻断推进 |
| visemeTimeline 时钟不同步 | 嘴型比音频滞后 1-2 帧 | 以 `AudioContext.currentTime` 为唯一时钟源，统一驱动 animate 循环和 viseme 定位 |
| 口型不如 Live2D 自然 | 几何体嘴型机械感强 | 主用 visemeTimeline 插值驱动；mouthEnergy 仅做降级；增加 form 参数控制圆展度 |
| 组件膨胀 | 三套预设分支导致 800+ 行 | 按 Phase 2 设计拆分到独立文件，每套预设 60-100 行 |
| 管理端与游客端配置不一致 | localStorage / 后端激活配置 / 默认值冲突 | 以后端 `/avatar-configs/active` 为跨端真源，本地缓存仅做离线兜底 |
| 旧栈删除过早 | 回退困难 | 必须在步骤 11 验证通过后才执行步骤 10 |
| 情感表达缺乏眉毛 | apology 表情无法实现 | Phase 2 中为基础头面部增加眉毛几何体（二个细 Box/Pane），由 emotion watch 控制 |

## 8 验收标准

1. 游客端和管理端均不再渲染 Live2D。
2. 三套预设形象（monk/hanfu/modern）在发型、服装、配饰维度可明确区分。
3. 情绪状态 `neutral` / `happy` / `apology` 通过几何体变化可见。
4. 说话状态由 `visemeTimeline` 驱动口型；timeline 缺失时降级为 `mouthEnergy` 驱动。
5. 配置保存后，游客端刷新加载正确形象与音色。
6. `vite build` 通过，且主包体积较替换前减小（移除了 PixiJS）。
7. 删除 `Live2DAvatar.vue`、`pixi.js`、`pixi-live2d-display` 及 CDN 脚本标签后，项目正常运行。
8. 降级路径正常：Three.js 初始化失败时游客端显示 `AvatarDisplay` SVG 头像。

## 9 与原方案的关键差异

| 维度 | 原方案 | 改进版 |
|------|--------|--------|
| visemeTimeline 迁移 | 仅写"迁移逻辑"三字 | 给出时钟同步方案、二分查找、插值方法的具体设计 |
| 预设参数设计 | 未给出草案 | 给出三套预设的参数维度和差异点对照表 |
| 文件拆分策略 | 未提及 | 提出 `avatar-presets/` 目录结构，防止组件膨胀 |
| 情感表情映射 | 未定义 | 给出 emotion→几何体参数的精确映射表（含新增眉毛几何体） |
| saveAvatarConfig Bug | 仅发现未修 | 给出 `selectModel` 同步更新 `remoteConfigId` 的具体修复代码 |
| 执行顺序 | 扁平 12 步 | 6 个 Phase 分组，Phase 3 独立验证口型 |
| 时钟同步风险 | 未涉及 | 新增风险 6，提出 AudioContext.currentTime 统一时钟方案 |
| CDN 清理 | 未提及 | 明确列出 `index.html` 中需清理的 Live2D 脚本标签 |
