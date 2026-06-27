# 数字人形象多样化选择 — 给 Claude 实施

> **赛题要求**：可配置数字人的外观形象、语音音色、服装等，即形象多样化选择。
> **评分相关**：数字人技术 15 分 + 交互自然度 20 分中形象切换是直观亮点。

---

## 核心挑战：Cubism 版本兼容性

当前代码使用的导入路径：
```javascript
import { Live2DModel } from "pixi-live2d-display/cubism4";
// ↑ 只能加载 Cubism 4 格式模型（.model3.json + .moc3）
```

而网络上绝大部分免费 Live2D 模型是 **Cubism 2.1** 格式（`.model.json` + `.moc`），两者不兼容。

---

## 解决方案总览

| 维度 | 怎么做 | 难度 | 效果 |
|------|--------|------|------|
| **多模型切换** | 切换 Live2D model.json → 重新加载 | ⭐⭐ | 效果最好，换一个人物 |
| **纹理换装** | 修改 model3.json 里 Textures 路径指向不同 PNG | ⭐⭐⭐ | 同一人物换衣服 |
| **语音音色** | 后端 TTS 引擎选不同音色 → 前端只做 UI 配置 | ⭐ | 依赖后端，前端只传参 |

**核心机制**：pixi-live2d-display 的模型切换 = `destroy()` 旧模型 + `Live2DModel.from()` 加载新模型。PIXI.Application（Canvas）在整个生命周期内保持不变，只换里面的 Live2DModel 实例。

---

# 📦 Step 0：切换导入路径（必须先做）

**原因**：当前 `cubism4` 导入只能加载 Cubism 4 模型。改为基础导入后，既能加载现有的 Shizuku（Cubism 4），也能加载 xiazeyu 仓库的 7+ 个免费 Cubism 2.1 模型。

**文件**：`frontend/src/components/Live2DAvatar.vue`

**操作**：将第 12 行：

```javascript
import { Live2DModel } from "pixi-live2d-display/cubism4";
```

改为：

```javascript
import { Live2DModel } from "pixi-live2d-display";
```

**验证**：`npm run dev` → 确认现有 Shizuku 模型依然正常加载渲染。

> 如果 Shizuku 加载失败，回退到 `cubism4` 导入，只使用 Cubism 4 模型资源（仍然有 2-3 个可选）。

---

# 📦 一阶段：多模型切换系统

## Step 1.1：创建模型配置 + 切换管理器

**新建文件**：`frontend/src/composables/useModelManager.js`

```javascript
import { Live2DModel } from "pixi-live2d-display";

/**
 * 模型配置表
 * 每个模型有：key（唯一标识）、label（中文名）、url（CDN地址）、description（适用场景）
 */
export const AVATAR_MODELS = {
  shizuku: {
    key: "shizuku",
    label: "小诗",
    description: "青春活泼 · 适合轻松游览",
    url: "https://cdn.jsdelivr.net/gh/guansss/pixi-live2d-display@0.5.1/test/assets/shizuku/shizuku.model.json",
    defaultScale: 0.18,
  },
  hibiki: {
    key: "hibiki",
    label: "小响",
    description: "成熟优雅 · 适合文化讲解",
    url: "https://cdn.jsdelivr.net/gh/xiazeyu/live2d-widget-models@master/packages/live2d-widget-model-hibiki/assets/hibiki.model.json",
    defaultScale: 0.16,
  },
  haru: {
    key: "haru",
    label: "小春",
    description: "阳光开朗 · 适合户外景点",
    url: "https://cdn.jsdelivr.net/gh/xiazeyu/live2d-widget-models@master/packages/live2d-widget-model-haru/01/assets/haru.model.json",
    defaultScale: 0.16,
  },
  // 以下为可选扩展模型（需要时取消注释即可）
  // chitose: {
  //   key: "chitose",
  //   label: "小千",
  //   description: "温柔知性 · 适合博物馆",
  //   url: "https://cdn.jsdelivr.net/gh/xiazeyu/live2d-widget-models@master/packages/live2d-widget-model-chitose/assets/chitose.model.json",
  //   defaultScale: 0.16,
  // },
  // izumi: {
  //   key: "izumi",
  //   label: "小泉",
  //   description: "干练专业 · 适合政务接待",
  //   url: "https://cdn.jsdelivr.net/gh/xiazeyu/live2d-widget-models@master/packages/live2d-widget-model-izumi/assets/izumi.model.json",
  //   defaultScale: 0.15,
  // },
};

/** 默认模型 */
export const DEFAULT_MODEL_KEY = "shizuku";

/**
 * 模型管理器
 * @param {PIXI.Application} app - 共享的 PIXI 实例
 */
export function useModelManager(app) {
  let currentModel = null;
  let currentModelKey = DEFAULT_MODEL_KEY;

  /** 获取模型列表（给 UI 使用） */
  function getModelList() {
    return Object.values(AVATAR_MODELS).map((m) => ({
      key: m.key,
      label: m.label,
      description: m.description,
    }));
  }

  /** 获取当前模型信息 */
  function getCurrentModelInfo() {
    return AVATAR_MODELS[currentModelKey] || AVATAR_MODELS[DEFAULT_MODEL_KEY];
  }

  /**
   * 切换模型
   * @param {string} modelKey
   * @param {object} options - { x, y, scale, onProgress }
   * @returns {Live2DModel}
   */
  async function switchModel(modelKey, options = {}) {
    const config = AVATAR_MODELS[modelKey];
    if (!config) {
      console.warn(`Unknown model: ${modelKey}, falling back to default`);
      return switchModel(DEFAULT_MODEL_KEY, options);
    }

    // 1. 销毁旧模型
    if (currentModel) {
      try {
        app.stage.removeChild(currentModel);
        currentModel.destroy({ texture: true, baseTexture: true });
      } catch (e) {
        console.warn("Failed to destroy old model:", e);
      }
      currentModel = null;
    }

    // 2. 加载新模型
    if (options.onProgress) options.onProgress("loading");
    const model = await Live2DModel.from(config.url);

    // 3. 设置变换
    const canvasWidth = app.view?.width || app.screen?.width || 480;
    const canvasHeight = app.view?.height || app.screen?.height || 720;
    model.anchor.set(0.5, 0.5);
    model.x = options.x ?? canvasWidth / 2;
    model.y = options.y ?? canvasHeight / 2;
    const scale = options.scale ?? config.defaultScale;
    model.scale.set(Number.isFinite(scale) && scale > 0 ? scale : 0.15);

    // 4. 挂载
    app.stage.addChild(model);
    currentModel = model;
    currentModelKey = modelKey;

    if (options.onProgress) options.onProgress("done");
    return model;
  }

  /** 获取当前模型实例（供口型/表情驱动使用） */
  function getModel() {
    return currentModel;
  }

  /** 销毁 */
  function destroy() {
    if (currentModel) {
      currentModel.destroy({ texture: true, baseTexture: true });
      currentModel = null;
    }
  }

  return {
    getModelList,
    getCurrentModelInfo,
    getModel,
    switchModel,
    destroy,
  };
}
```

---

## Step 1.2：改造 `Live2DAvatar.vue` — 适配模型切换

**文件**：`frontend/src/components/Live2DAvatar.vue`

在现有 props 基础上新增 `modelKey` prop；在 script 中集成 `useModelManager`；暴露 `switchModel` 方法。

**关键改动说明**（在现有代码基础上增量改）：

**1. 新增 props：**
```javascript
// 在现有 props 对象末尾添加：
modelKey: { type: String, default: "shizuku" },
```

**2. 改造 `onMounted` 中的初始化逻辑**（替换原有的模型加载部分）：

```javascript
// 原有代码：
// model = await Live2DModel.from(props.modelPath);
// fitModelToCanvas();
// app.stage.addChild(model);

// 改为：
import { useModelManager, AVATAR_MODELS } from "../composables/useModelManager";

// 在 setup 顶部（app 创建后）：
const modelManager = useModelManager(app);

// onMounted 中替换为：
try {
  const config = AVATAR_MODELS[props.modelKey] || AVATAR_MODELS[DEFAULT_MODEL_KEY];
  model = await Live2DModel.from(config.url);
  fitModelToCanvas();
  app.stage.addChild(model);
  applyEmotion(props.emotion);
  startIdleAnimations();
  loading.value = false;
} catch (err) { /* 保持现有错误处理 */ }
```

**3. 暴露 `switchModel` 给父组件：**

```javascript
// 新增方法，放在 setup 末尾 defineExpose 中
async function handleSwitchModel(key) {
  loading.value = true;
  error.value = "";
  try {
    model = await modelManager.switchModel(key, {
      x: CANVAS_WIDTH / 2,
      y: CANVAS_HEIGHT / 2,
      onProgress: (status) => {
        if (status === "loading") loading.value = true;
        if (status === "done") loading.value = false;
      },
    });
    applyEmotion(props.emotion);
    startIdleAnimations();
  } catch (err) {
    error.value = "模型切换失败";
    loading.value = false;
    emit("load-error", err);
  }
}

defineExpose({ switchModel: handleSwitchModel, playMotion }); // playMotion 来自三阶段代码
```

**4. `onBeforeUnmount` 中增加销毁：**

```javascript
onBeforeUnmount(() => {
  stopIdleAnimations();
  if (visemeTimer) clearInterval(visemeTimer);
  modelManager.destroy(); // ★ 新增
  if (app) { app.destroy(true); app = null; }
});
```

---

## Step 1.3：改造管理端 `AvatarConfig.vue` — 完整形象配置页

**文件**：`frontend/src/views/admin/AvatarConfig.vue`

**操作**：用以下内容完整替换：

```vue
<template>
  <section class="avatar-config-page">
    <div class="config-header">
      <h2>数字人形象配置</h2>
      <p>为游客选择不同的导游形象、语音音色和展示风格。</p>
    </div>

    <!-- ====== 模型选择卡片 ====== -->
    <div class="section-block">
      <h3 class="section-label">外观形象</h3>
      <div class="model-grid">
        <div
          v-for="m in modelList"
          :key="m.key"
          :class="['model-card', { active: selectedModel === m.key }]"
          @click="selectModel(m.key)"
        >
          <div class="model-preview">
            <div class="model-placeholder" :class="`preview-${m.key}`">
              <span class="model-initial">{{ m.label[0] }}</span>
            </div>
            <div v-if="selectedModel === m.key" class="model-check">
              <el-icon><Check /></el-icon>
            </div>
          </div>
          <div class="model-info">
            <strong>{{ m.label }}</strong>
            <small>{{ m.description }}</small>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 预览区 ====== -->
    <div class="section-block">
      <h3 class="section-label">实时预览</h3>
      <div class="preview-area">
        <div class="preview-canvas-wrapper">
          <Live2DAvatar
            ref="previewAvatarRef"
            :model-key="selectedModel"
            :emotion="previewEmotion"
            :is-speaking="previewSpeaking"
            @load-error="handlePreviewError"
          />
        </div>
        <div class="preview-controls">
          <el-button-group>
            <el-button @click="previewEmotion = 'neutral'; previewSpeaking = false" :type="previewEmotion === 'neutral' && !previewSpeaking ? 'primary' : 'default'">
              空闲
            </el-button>
            <el-button @click="previewEmotion = 'happy'; previewSpeaking = true" :type="previewEmotion === 'happy' ? 'primary' : 'default'">
              微笑
            </el-button>
            <el-button @click="previewEmotion = 'surprised'" :type="previewEmotion === 'surprised' ? 'primary' : 'default'">
              惊喜
            </el-button>
            <el-button @click="previewEmotion = 'apology'" :type="previewEmotion === 'apology' ? 'primary' : 'default'">
              致歉
            </el-button>
          </el-button-group>
          <el-button @click="previewSpeaking = !previewSpeaking" :type="previewSpeaking ? 'warning' : 'default'">
            {{ previewSpeaking ? '停止说话' : '模拟说话' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- ====== 语音音色 ====== -->
    <div class="section-block">
      <h3 class="section-label">语音音色</h3>
      <el-card shadow="never">
        <el-form label-width="100px">
          <el-form-item label="音色">
            <el-select v-model="voiceType" placeholder="选择音色">
              <el-option label="温柔女声" value="gentle-female" />
              <el-option label="知性女声" value="calm-female" />
              <el-option label="沉稳男声" value="deep-male" />
              <el-option label="活泼女声" value="lively-female" />
            </el-select>
            <span class="form-hint">将传给后端 TTS 引擎</span>
          </el-form-item>
          <el-form-item label="语速">
            <el-slider v-model="speechRate" :min="80" :max="150" :step="5" show-input />
          </el-form-item>
          <el-form-item label="音量">
            <el-slider v-model="volume" :min="50" :max="100" :step="5" show-input />
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- ====== 服饰配色（纹理换装） ====== -->
    <div class="section-block">
      <h3 class="section-label">服饰配色</h3>
      <el-card shadow="never">
        <p class="form-desc">
          同一导游形象的服装配色变体。通过修改 Live2D 模型的纹理贴图实现，不需要重新制作模型。
          <el-tag size="small" type="info" style="margin-left: 8px;">计划中</el-tag>
        </p>
        <el-form label-width="100px">
          <el-form-item label="当前配色">
            <el-radio-group v-model="costume" disabled>
              <el-radio-button value="default">默认配色</el-radio-button>
              <el-radio-button value="spring">春日（粉绿）</el-radio-button>
              <el-radio-button value="autumn">秋韵（暖棕）</el-radio-button>
            </el-radio>
            <span class="form-hint">换装需提供替换纹理 PNG，当前展示配置能力</span>
          </el-form-item>
        </el-form>
      </el-card>
    </div>

    <!-- 保存按钮 -->
    <div class="config-actions">
      <el-button type="primary" size="large" @click="handleSave">
        保存配置并应用到游客端
      </el-button>
      <el-button size="large" @click="handleReset">恢复默认</el-button>
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from "vue";
import { Check } from "@element-plus/icons-vue";
import Live2DAvatar from "../../components/Live2DAvatar.vue";
import { AVATAR_MODELS, DEFAULT_MODEL_KEY } from "../../composables/useModelManager";

const STORAGE_KEY = "a5-avatar-config-v1";

// ---- 模型列表 ----
const modelList = computed(() =>
  Object.values(AVATAR_MODELS).map((m) => ({
    key: m.key,
    label: m.label,
    description: m.description,
  }))
);

// 从 localStorage 恢复上次选择
function loadConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return null;
}
const saved = loadConfig();

const selectedModel = ref(saved?.modelKey || DEFAULT_MODEL_KEY);
const voiceType = ref(saved?.voiceType || "gentle-female");
const speechRate = ref(saved?.speechRate || 100);
const volume = ref(saved?.volume || 80);
const costume = ref("default");

// ---- 预览状态 ----
const previewAvatarRef = ref(null);
const previewEmotion = ref("neutral");
const previewSpeaking = ref(false);

function selectModel(key) {
  selectedModel.value = key;
  // Live2DAvatar 的 modelKey prop 变化时会自动重新加载
}

function handlePreviewError(err) {
  console.warn("Preview avatar load error:", err);
}

// ---- 保存/重置 ----
function handleSave() {
  const config = {
    modelKey: selectedModel.value,
    voiceType: voiceType.value,
    speechRate: speechRate.value,
    volume: volume.value,
    costume: costume.value,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
  ElMessage.success("形象配置已保存，游客端刷新后生效");
}

function handleReset() {
  selectedModel.value = DEFAULT_MODEL_KEY;
  voiceType.value = "gentle-female";
  speechRate.value = 100;
  volume.value = 80;
  costume.value = "default";
  localStorage.removeItem(STORAGE_KEY);
  ElMessage.info("已恢复默认配置");
}
</script>

<style scoped>
.avatar-config-page {
  padding: 24px;
  max-width: 960px;
}
.config-header {
  margin-bottom: 32px;
}
.config-header h2 {
  margin: 0 0 8px;
  font-size: 22px;
}
.config-header p {
  margin: 0;
  color: #6c757d;
}

/* Section */
.section-block {
  margin-bottom: 28px;
}
.section-label {
  margin: 0 0 14px;
  font-size: 16px;
  font-weight: 600;
  color: #212529;
}
.form-desc {
  margin: 0 0 12px;
  color: #6c757d;
  font-size: 13px;
  line-height: 1.6;
}
.form-hint {
  margin-left: 10px;
  color: #adb5bd;
  font-size: 12px;
}

/* 模型卡片网格 */
.model-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.model-card {
  padding: 16px;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fff;
}
.model-card:hover {
  border-color: #0f766e;
  box-shadow: 0 2px 8px rgba(15, 118, 110, 0.1);
}
.model-card.active {
  border-color: #0f766e;
  background: #f0fdfa;
}

/* 模型预览占位（圆形头像模拟） */
.model-preview {
  position: relative;
  width: 72px;
  height: 72px;
  margin: 0 auto 10px;
}
.model-placeholder {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}
.preview-shizuku { background: linear-gradient(135deg, #06b6d4, #3b82f6); }
.preview-hibiki  { background: linear-gradient(135deg, #a855f7, #6366f1); }
.preview-haru   { background: linear-gradient(135deg, #f59e0b, #ef4444); }
.preview-chitose { background: linear-gradient(135deg, #10b981, #14b8a6); }
.preview-izumi  { background: linear-gradient(135deg, #64748b, #334155); }

.model-check {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #0f766e;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}
.model-info {
  text-align: center;
}
.model-info strong {
  display: block;
  font-size: 14px;
}
.model-info small {
  display: block;
  margin-top: 4px;
  color: #6c757d;
  font-size: 12px;
}

/* 预览区 */
.preview-area {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
.preview-canvas-wrapper {
  flex-shrink: 0;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  overflow: hidden;
  background: #f8f9fa;
}
.preview-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

/* 底部按钮 */
.config-actions {
  display: flex;
  gap: 12px;
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #e9ecef;
}

@media (max-width: 768px) {
  .model-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .preview-area {
    flex-direction: column;
  }
}
</style>
```

---

# 📦 二阶段：纹理换装系统（加分项，可选）

## 原理

Live2D 模型的外观由两部分决定：
1. `.moc`/`.moc3` — 骨骼网格（不变）
2. PNG 纹理贴图 — 皮肤、服装、头发颜色（可替换）

换装 = 创建多个 `.model.json` 副本，指向不同的 PNG 纹理文件，按需加载。

## 实施（仅给有这个能力的模型做）

```
假设模型目录结构：
public/models/shizuku/
  shizuku.model.json         ← 原版（默认服装）
  shizuku.spring.model.json  ← 副本，Textures 指向 "shizuku_spring.png"
  shizuku.autumn.model.json  ← 副本，Textures 指向 "shizuku_autumn.png"
  shizuku.moc                ← 骨骼（三套共用）
  shizuku_00.png             ← 默认纹理
  shizuku_spring.png         ← 春日纹理（自行制作或从网络获取）
  shizuku_autumn.png         ← 秋日纹理
```

model.json 中修改的字段：
```json
{
  "FileReferences": {
    "Moc": "shizuku.moc",
    "Textures": ["shizuku_spring.png"],   // ← 改这里
    "Physics": "shizuku.physics.json"
  }
}
```

**换装切换代码**（在 `useModelManager.js` 中追加）：
```javascript
const COSTUME_URLS = {
  shizuku: {
    default: "public/models/shizuku/shizuku.model.json",
    spring: "public/models/shizuku/shizuku.spring.model.json",
    autumn: "public/models/shizuku/shizuku.autumn.model.json",
  },
};

async function switchCostume(modelKey, costumeKey) {
  const url = COSTUME_URLS[modelKey]?.[costumeKey];
  if (!url) return;
  // 跟 switchModel 一样的逻辑：destroy + Live2DModel.from(url)
  await switchModel(modelKey, { /* 使用 costume 特定的 url 覆盖 */ });
}
```

> ⚠️ **誠実说明**：换装需要对应模型的备用纹理 PNG 文件，这些文件需要自行制作（Photoshop 调色）或从 Live2D 官方素材市场获取。比赛演示中，**多模型切换**已经足够展示"形象多样化"，换装属于锦上添花。

---

# 📦 三阶段：游客端接入配置

## Step 3.1：ChatView 读取配置

**文件**：`frontend/src/views/tourist/ChatView.vue`

在 `<script setup>` 中新增：

```javascript
import { DEFAULT_MODEL_KEY } from "../../composables/useModelManager";

const STORAGE_KEY = "a5-avatar-config-v1";

// 读取管理端保存的形象配置
const avatarConfig = ref({ modelKey: DEFAULT_MODEL_KEY });
try {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw) avatarConfig.value = JSON.parse(raw);
} catch {}
```

然后将 Live2DAvatar 的 `model-key` 绑定为配置值：

```html
<Live2DAvatar
  v-if="!avatarError"
  :model-key="avatarConfig.modelKey"
  :emotion="avatar.currentEmotion.value"
  :is-speaking="avatarState === 'speaking' || avatarState === 'happy'"
  :speech-progress="speechProgress"
  :viseme-timeline="visemeTimeline"
  @load-error="handleAvatarLoadError"
/>
```

---

# 🧪 验证清单

```
□ Step 0 导入路径切换后 Shizuku 仍正常加载
□ 管理端 /admin/avatar 可见 3 个模型卡片
□ 点击不同卡片 → 预览区数字人切换为新模型
□ 预览区按钮可切换表情 + 模拟说话
□ 保存配置 → localStorage 有正确数据
□ 刷新游客端 → 显示管理端配置的模型
□ 切换模型时无报错、无白屏
□ 语音音色选择器正常交互
```

---

# ⚠️ 注意事项

1. **Step 0 最重要**：导入路径从 `cubism4` 改为 `pixi-live2d-display` 后，如果 Shizuku 加载失败，立即回退并告知我
2. hibiki 和 haru 模型来自 xiazeyu 的 CDN，国内访问可能慢。如果加载超时，可将模型文件下载到 `frontend/public/models/` 本地托管
3. **不要新增 npm 依赖**
4. 模型切换时 PIXI.Application 不重建，只替换内部的 Live2DModel 实例
5. 如果 xiazeyu CDN 不可用，回退方案：只展示 Shizuku 一张卡片 + 说明"更多形象开发中"
