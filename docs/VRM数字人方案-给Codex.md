# VRoid → @pixiv/three-vrm 数字人改造方案

> 写给 Codex 审查用。描述当前数字人现状、改造决策、已准备资产、已执行调整与待完成步骤。

---

## 一、背景与决策

当前项目三套数字人角色（明彻法师、清岚、景行）通过 Three.js 原生几何体程序化拼装（`avatar-presets/monk.js` 586行 / `hanfu.js` 233行 / `modern.js` 227行），球体+Box+Cylinder 构建面部五官和服装。距离"真人感"差距过大。

**决策：引入 VRoid Studio 建模，导出 `.vrm`，通过 `@pixiv/three-vrm`（MIT 协议，pixiv 官方维护，v3.5.3，GitHub 1.2k dependents）加载进 Three.js，替换现有程序化模型。**

核心收益：
- VRM 自带面部纹理、法线、BlendShape（A/I/U/E/O viseme + happy/sad 等表情），一字不改映射到现有 emotion/visemeTimeline 接口
- SpringBone 物理（头发飘动）和 MToon 材质（日式动画渲染）开箱即用
- VRoid 捏脸是拉滑块，不需要绘画或手动建模

---

## 二、现有代码接口（不可变）

`ThreeAvatar.vue` 的 Props 接口：

```js
props: {
  preset: String,       // "monk" | "hanfu" | "modern"
  emotion: String,      // "neutral" | "happy" | "apology"
  isSpeaking: Boolean,
  visemeTimeline: Array, // [{ start: ms, end: ms, value: 0~1, form: 0~1 }]
  speechProgress: Number,
  speechSyncActive: Boolean,
}
```

`buildAvatarByPreset(preset)` 返回结构：

```js
{ group, head, leftEye, rightEye, leftPupil, rightPupil, mouth, leftBrow, rightBrow }
```

后端 `bootstrap.py` 种子数据：`monk` 为默认激活角色，`model_path` 字段存 `preset:monk` / `preset:hanfu` / `preset:modern`。

**改造约束：上面的 Props 接口和返回结构不能变，`buildAvatarByPreset` 签名不变，改为内部走 VRM 加载。**

---

## 三、已获取资产

### 数字人1 — 清岚汉服套装

```
D:\桌面\数字人1\
├── hanfu_tops.vroidcustomitem      3.9 MB  汉服上衣（5层纹理）
├── hanhu_bottoms.vroidcustomitem   1.3 MB  汉服下装
├── lower_body_inner.vroidcustomitem 227 KB 内衬打底
└── shoes.vroidcustomitem           303 KB  鞋子
```

`.vroidcustomitem` 格式，拖入 VRoid Studio 可直接穿戴。来源 Booth，条款允许改変和商用。

### 数字人2 — 西装制服纹理（景行用）

```
D:\桌面\数字人2\
├── ddlc_scool_blazer_m1.png   907 KB  男款西装纹理
├── ddlc_scool_blazer_f2.png   914 KB  女款西装纹理
└── ddlc_scool_blazer_config.png 125 KB 参数参考图
```

纹理主色为 `#4D465D`（灰紫深藏青），已在 `modern.js` 配色调整中参考。`.png` 纹理需要手动在 VRoid 里导入衣服图层。

### 已安装的 npm 包

```
@pixiv/three-vrm@3     → 即 3.5.3
```

目前仅安装，尚未接入 `ThreeAvatar.vue`。

---

## 四、已执行调整（2026-06-23）

### 4.1 景行配色对齐西装纹理

`frontend/src/components/avatar-presets/modern.js`

| 颜色 | 旧值 | 新值 | 依据 |
|------|------|------|------|
| NAVY 制服 | `#243447` | `#3D394B` | 纹理主色 `#4D465D` |
| CREAM 内衬 | `#E6E2D3` | `#DAD1C8` | 纹理内衬 `#A37F7F` 暖调 |
| TEAL 领口 | `#2F7F79` | `#465A78` | 纹理领口 `#5A628D` |
| HAIR | `#2D1B0E` | `#332014` | 与灰紫制服协调 |
| AMBER | `#E39B43` | `#D68935` | 降饱和 |
| BADGE_BG | `#1E2D40` | `#302D3E` | 深灰紫 |

服装廓形调整：
- 躯干从 `topRadius=0.88, bottomRadius=1.18`（下宽锥形）改为 `topRadius=1.00, bottomRadius=1.10`（上宽下微收，西装廓形）
- 肩部从 `radius=1.35` 改为 `1.42`（更挺括垫肩）
- 翻领片加长加大，V 形开口更明显

### 4.2 清岚配色与服装结构调整

`frontend/src/components/avatar-presets/hanfu.js`

| 改动 | 旧 | 新 |
|------|----|----|
| 外袍主色 | 青绿 | 米白（与下载的汉服纹理一致） |
| 右领颜色 | 青绿 | 墨青（左右统一 Y 字交叠） |
| 皮肤 | `#E8C4A8` | `#EDD0B4` |
| 唇色 | `#C87070` | `#D4908A`（暖粉） |
| 青绿 | `#7DAA92` | `#729987`（更沉静） |

交领结构调整：
- 左右领片加长加宽（`0.30→0.32` / `0.65→0.72`）
- 领缘金线加长到 `0.60`
- 披帛前缘加长到 `0.74`
- 外袍内衬缩窄（`0.42→0.38`），更贴身

### 4.3 编译验证

`npm run build` 通过（20.78s），`npm run dev` 可正常驱动 SSE 问答与口型。

---

## 五、待执行步骤

### 5.1 VRoid 建模（用户操作）

在 VRoid Studio 中创建三个角色：

1. **清岚**：女体，鹅蛋脸，盘发 + 玉簪，拖入数字人1的 `.vroidcustomitem` 套装。导出 `.vrm`。
2. **景行**：男体，方圆脸，干净短发，导入数字人2的 `.png` 西装纹理，改色为深藏青。导出 `.vrm`。
3. **明彻法师**：男体，偏长椭圆脸，净头（无发层）。僧袍纹理目前缺素材，两条路：Booth 搜免费"袈裟""坊主"纹理，或由 AI 生成赭黄亚麻质感纹理。导出 `.vrm`。

三个 `.vrm` 文件统一放到 `frontend/public/models/` 目录。

### 5.2 ThreeAvatar.vue 接入 VRM 加载

在现有 `buildAvatarByPreset` 内部新增 VRM 加载分支：

```
buildAvatarByPreset(preset) → 若 public/models/{preset}.vrm 存在 → VRMLoader 加载
                            → 否则 → 回退现有程序化建模
```

`@pixiv/three-vrm` 加载方式：

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin } from '@pixiv/three-vrm';

const loader = new GLTFLoader();
loader.register(parser => new VRMLoaderPlugin(parser));
loader.load(`/models/${preset}.vrm`, (gltf) => {
  const vrm = gltf.userData.vrm;
  // vrm.scene 作为 avatarParts.group
  // vrm.expressionManager / vrm.lookAt 后续用于表情和注视
});
```

### 5.3 接口映射（不需要改上层代码）

**Viseme（口型）映射**：

现有 `visemeTimeline: [{ start, end, value, form }]` 驱动 `mouth.scale.y/x`。

VRM 接入后改为调用 `vrm.expressionManager.setValue("A", value)` 等标准 BlendShape。

映射建议：
- `value`（开口度）→ blend `A`（大开口）为主
- `form`（圆展度）→ blend `U`（圆唇）和 `I`（展唇）

降级兜底保留 `useAudioPlayer.mouthEnergy` → `vrm.expressionManager.setValue("A", energy)`。

**Emotion（表情）映射**：

| 现有值 | VRM BlendShape |
|--------|---------------|
| `neutral` | 清空所有 expression |
| `happy` | `happy` = 0.8 |
| `apology` | `sad` = 0.5, 头部下压通过 `vrm.lookAt` 或手动旋转 |

`isSpeaking` 控制眨眼的上下文判断不变。

**LookAt 注视**：

`vrm.lookAt.target` 设为场景中固定注视点（相机方向偏游客），让模型眼神自然。

### 5.4 回退路径

- Three.js WebGL 初始化失败 → SVG `AvatarDisplay`
- VRM 文件加载失败 → 降级到现有程序化建模（不改 `buildAvatarByPreset` 签名）
- 表情/口型 BlendShape 不存在 → 静默忽略，不抛错

### 5.5 后端适配

`backend/app/db/bootstrap.py` 的 `DEFAULT_AVATAR_CONFIGS` 中 `model_path` 字段目前存 `preset:monk` 等。VRM 路径可改为 `vrm:monk` 或在 preset 体系内自动检测文件存在决定走哪个分支。不需要改数据库 Schema。

---

## 六、设计风险与对策

| 风险 | 对策 |
|------|------|
| VRoid 导出 .vrm 文件过大（5–15MB） | Three.js GLTFLoader 支持渐进加载；首帧可先显示 SVG 占位 |
| @pixiv/three-vrm 与当前 Three.js 版本不兼容 | 仓库用 r180 兼容范围足够（three-vrm v3 要求 ≥ r167） |
| VRM BlendShape 名不标准（部分作者自定义） | 首版只映射 A/I/U/E/O + happy/sad，其余静默跳过 |
| 明彻法师僧袍纹理暂无素材 | Booth 搜免费项；若 48h 内无果则 AI 生成赭黄亚麻纹理 |
| 游客端默认不走 Three.js 主路径（P0-1 已知 bug） | 需在 `useModelManager` 里修 `is3DModel` 判断逻辑 |

---

## 七、不在此范围内的

- 不引入 `GLB/FBX/glTF` 外部高精资产（VRoid 闭环就够）
- 不重建 `SelectionContext`、SSE 链路、visemeTimeline 生成逻辑
- 不改 `composables/useAvatar.js` 的对外 API
- 不对 monk.js 做程序化建模增强（反正要替换为 VRM）
- 不改后端数据库 Schema 或路由

---

## 八、当前阻塞

1. 用户尚未在 VRoid 中完成角色建模和 .vrm 导出
2. 明彻法师僧袍纹理未获取（Booth 或 AI 生成待定）
3. @pixiv/three-vrm 已安装但未接入 ThreeAvatar.vue
