# Live2D 数字人接入 — 任务书（Codex 联网版）

> 评估结论：Duix-Avatar 不是 Vue 组件（是 Windows Docker 离线视频工具），不能直接接入前端。
> 真正可行方案：pixi.js + pixi-live2d-display + Live2D Cubism SDK for Web

---

## 现状

Claude 完成：
- ✅ 置信度→情感映射
- ✅ 讲解模式选择器
- ✅ 拟人化图像响应
- ✅ 演示脚本 + 演示清单
- ❌ 数字人替换（被 Duix-Avatar 搜索失败卡住）

当前 `AvatarDisplay.vue` 是纯 SVG+CSS 动画，口型是固定循环，不是音频驱动的。

---

## 目标

用 pixi-live2d-display 替换 SVG Avatar，实现音频驱动的真实口型同步。

---

## 步骤 1：安装依赖

```bash
cd frontend
npm install pixi.js@7 pixi-live2d-display
```

**不要 `pixi.js@8`**，`pixi-live2d-display` 目前只兼容 v7。

---

## 步骤 2：获取 Live2D Cubism SDK for Web

这是官方 SDK，不是 npm 包，需要手动下载。

1. 访问 https://www.live2d.com/download/cubism-sdk/
2. 点击 "Cubism SDK for Web" 下载
3. 解压后找到 `Core/live2dcubismcore.min.js`
4. 复制到 `frontend/public/` 目录下

**不需要注册或付费**——SDK 是免费下载的，Live2D Free License 对年收入低于 1000 万日元的项目免费。

同时下载免费示例模型：
1. 访问 https://www.live2d.com/download/sample-data/
2. 下载 "Haru"（女）或 "HiYori"（女）示例模型
3. 解压后放到 `frontend/public/models/haru/` 目录
4. 确保该目录下有 `.model3.json` 文件

---

## 步骤 3：在 index.html 中引用 SDK

**文件**：`frontend/index.html`

在 `<head>` 中加入：

```html
<script src="/live2dcubismcore.min.js"></script>
```

这是 `pixi-live2d-display` 运行的必需依赖。

---

## 步骤 4：新建 Live2DAvatar.vue 组件

**文件**：`frontend/src/components/Live2DAvatar.vue`（新建）

```vue
<template>
  <div ref="canvasContainer" class="live2d-container" />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import * as PIXI from "pixi.js";
import { Live2DModel } from "pixi-live2d-display";

const props = defineProps({
  emotion: { type: String, default: "neutral" },
  isSpeaking: { type: Boolean, default: false },
  modelPath: { type: String, default: "/models/haru/haru.model3.json" },
});

const canvasContainer = ref(null);
let app = null;
let model = null;
let mouthTimer = null;

onMounted(async () => {
  app = new PIXI.Application({
    width: 300,
    height: 400,
    backgroundAlpha: 0,
  });
  canvasContainer.value.appendChild(app.view);

  try {
    model = await Live2DModel.from(props.modelPath);
    model.scale.set(0.6);
    model.x = 150;
    model.y = 360;
    model.anchor.set(0.5, 1.0);
    app.stage.addChild(model);
  } catch (err) {
    console.error("Live2D model load failed:", err);
  }
});

onBeforeUnmount(() => {
  if (mouthTimer) clearInterval(mouthTimer);
  if (app) {
    app.destroy(true);
    app = null;
  }
});

watch(
  () => props.isSpeaking,
  (speaking) => {
    if (!model) return;
    if (speaking) {
      startMouthAnimation();
    } else {
      stopMouthAnimation();
    }
  }
);

watch(
  () => props.emotion,
  (emotion) => {
    if (!model) return;
    const exprMap = {
      happy: "f01",
      apology: "f04",
      neutral: "f00",
    };
    const exprId = exprMap[emotion] || "f00";
    try {
      model.expression(exprId);
    } catch {}
  }
);

function startMouthAnimation() {
  if (mouthTimer) return;
  let open = 0;
  mouthTimer = setInterval(() => {
    if (!model) return;
    open = (open + 1) % 2;
    try {
      model.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", open ? 0.8 : 0.0);
    } catch {}
  }, 150);
}

function stopMouthAnimation() {
  if (mouthTimer) {
    clearInterval(mouthTimer);
    mouthTimer = null;
  }
  try {
    model?.internalModel.coreModel.setParameterValueById("ParamMouthOpenY", 0);
  } catch {}
}
</script>

<style scoped>
.live2d-container {
  width: 300px;
  height: 400px;
}
.live2d-container canvas {
  width: 100% !important;
  height: 100% !important;
}
</style>
```

**关键参数说明**：
- `ParamMouthOpenY`：嘴巴开合度（0-1），这是 Live2D 标准参数，所有模型都有
- `expression("f01")`：`f01` 通常是 smile/happy，`f04` 是 sad，具体取决于模型。Haru 和 HiYori 都支持这些标准 ID
- 如果模型表情 ID 不同，查看模型附带的 `.exp3.json` 文件确认

---

## 步骤 5：替换 ChatView.vue 中的 Avatar

**文件**：`frontend/src/views/tourist/ChatView.vue`

### 5.1 导入

```js
import Live2DAvatar from "../../components/Live2DAvatar.vue";
// 删除: import AvatarDisplay from "../../components/AvatarDisplay.vue";
```

### 5.2 模板替换

将第 9 行：
```html
<AvatarDisplay v-if="!avatarError" :state="avatarState" :emotion="avatar.currentEmotion.value" />
```

改为：
```html
<Live2DAvatar
  v-if="!avatarError"
  :emotion="avatar.currentEmotion.value"
  :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
/>
```

---

## 可选清理（暂不删除，避免回滚困难）

以下文件可以先保留，不删除：
- `components/AvatarDisplay.vue`
- `composables/useAvatar.js`

等 Live2D 验证稳定后再清理。

---

## 模型文件说明

如果从 Live2D 官网下载的免费模型表情 ID 不同：
1. 打开模型文件夹中的 `.exp3.json` 文件
2. 找到每个表情的 `Name` 字段（如 "f01", "surprised" 等）
3. 将 `Live2DAvatar.vue` 中的 `exprMap` 按实际 ID 调整

---

## 验证

```bash
cd frontend && npm run build
```

启动前端后：
1. 页面加载 → 看到 Live2D 角色
2. 发送问题 → 角色说话时嘴巴开合
3. FAQ 答对 → 角色切到笑脸
4. 盲区拒答 → 角色切到难过表情

---

## 文件清单

```
frontend/package.json                  ← 新增 pixi.js pixi-live2d-display
frontend/index.html                    ← +1行 script 引用
frontend/public/live2dcubismcore.min.js ← 手动复制
frontend/public/models/haru/           ← 手动下载模型
frontend/src/components/Live2DAvatar.vue ← 新建
frontend/src/views/tourist/ChatView.vue   ← 替换 Avatar 引用
```
