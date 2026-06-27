# 前端设计优化：去AI味，贴合数字人导游主题

> 本文档提供明确的代码修改指令，可直接执行，无需额外解释

---

## 优先级说明

- **P0（立即执行）**：文案本地化、色彩主题 - 30分钟完成，效果明显
- **P1（次优先）**：数字人人设、去技术暴露 - 1小时完成
- **P2（可选）**：布局优化、交互增强 - 后续迭代

**本次实施范围：P0 + P1（核心改造）**

---

## P0-1：文案本地化（去技术术语）

### 目标

将"SSE流式问答"、"证据来源"等技术词汇替换为游客友好表达。

### 文件：`frontend/src/views/tourist/ChatView.vue`

#### 修改1：页面标题和副标题

**位置**：第 21-22 行

**修改前**：
```vue
<h2 class="section-title">游客交互端</h2>
<p class="section-subtitle">选择上下文、SSE流式问答与证据来源在同一页面协作。</p>
```

**修改后**：
```vue
<h2 class="section-title">灵山智慧导游</h2>
<p class="section-subtitle">随时解答您的游览疑问，就像真人导游陪伴身边</p>
```

#### 修改2：输入框占位符

**位置**：第 179 行

**修改前**：
```vue
placeholder="请输入景区问题，例如：灵山大佛有多高？"
```

**修改后**：
```vue
placeholder="问我关于灵山的任何问题，比如：大佛有多高？"
```

#### 修改3：右侧来源面板标题

**位置**：第 220-221 行

**修改前**：
```vue
<h3 class="section-title">检索来源</h3>
<p class="section-subtitle">用于后续做问答可追溯、评测和答辩展示。</p>
```

**修改后**：
```vue
<h3 class="section-title">资料来源</h3>
<p class="section-subtitle">所有回答均来自官方景区资料，点击数字可查看详情。</p>
```

#### 修改4：空状态提示

**位置**：第 222 行

**修改前**：
```vue
<el-empty v-if="chatStore.sources.length === 0" description="当前还没有来源信息" />
```

**修改后**：
```vue
<el-empty v-if="chatStore.sources.length === 0" description="提问后这里会显示参考资料" />
```

#### 修改5：发送按钮文案

**位置**：第 201 行

**修改前**：
```vue
发送问题
```

**修改后**：
```vue
向导游提问
```

#### 修改6：语音按钮文案

**位置**：第 213 行

**修改前**：
```vue
<template v-else>语音输入</template>
```

**修改后**：
```vue
<template v-else>语音提问</template>
```

---

## P0-2：色彩主题文化化

### 目标

从科技蓝色调改为灵山文化配色（佛像金 + 禅境绿）

### 文件：`frontend/src/style.css`

#### 修改1：定义文化色彩变量

**位置**：在 `:root` 块中（第 1-7 行之后）添加

**添加内容**：
```css
:root {
  color-scheme: light;
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  color: #1f2937;
  
  /* 灵山文化配色 */
  --lingshan-gold: #d4a574;
  --lingshan-gold-light: #f0dcc4;
  --lingshan-green: #6b9e78;
  --lingshan-green-light: #e8f4ea;
  --lingshan-stone: #7d7d7d;
  --lingshan-paper: #faf8f5;
  
  background:
    radial-gradient(circle at top left, rgba(212, 165, 116, 0.08), transparent 35%),
    linear-gradient(180deg, var(--lingshan-paper) 0%, #f5f1eb 100%);
}
```

### 文件：`frontend/src/views/tourist/ChatView.vue`（样式部分）

#### 修改2：用户消息气泡

**位置**：第 659-661 行（样式块）

**修改前**：
```css
.message-item.user {
  background: #e0f2fe;
}
```

**修改后**：
```css
.message-item.user {
  background: linear-gradient(135deg, #fff8f0, #fff);
  border-left: 3px solid var(--lingshan-gold);
}
```

#### 修改3：助手消息气泡

**位置**：第 663-665 行

**修改前**：
```css
.message-item.assistant {
  background: #f8fafc;
}
```

**修改后**：
```css
.message-item.assistant {
  background: var(--lingshan-green-light);
  border-left: 3px solid var(--lingshan-green);
}
```

### 文件：`frontend/src/style.css`（引文标签）

#### 修改4：引文标签色彩

**位置**：第 180-185 行左右（`.citation` 样式块）

**修改前**：
```css
.citation {
  /* ... */
  background: #f0fdfa;
  border: 1px solid #5eead4;
  color: #0f766e;
  /* ... */
}

.citation:hover {
  background: #ccfbf1;
  border-color: #0f766e;
  /* ... */
}
```

**修改后**：
```css
.citation {
  /* ... */
  background: var(--lingshan-gold-light);
  border: 1px solid var(--lingshan-gold);
  color: #8b6914;
  /* ... */
}

.citation:hover {
  background: #f5e5cc;
  border-color: #b8935f;
  /* ... */
}
```

---

## P0-3：快捷功能场景化

### 目标

将"儿童/标准/专业"改为"亲子游/休闲游/文化深度游"

### 文件：`frontend/src/views/tourist/ChatView.vue`

#### 修改：讲解深度选择器

**位置**：第 166-172 行

**修改前**：
```vue
<div class="explanation-mode">
  <span>讲解深度</span>
  <el-radio-group v-model="explanationLevel" size="small">
    <el-radio-button value="child">儿童</el-radio-button>
    <el-radio-button value="adult">标准</el-radio-button>
    <el-radio-button value="expert">专业</el-radio-button>
  </el-radio-group>
</div>
```

**修改后**：
```vue
<div class="explanation-mode">
  <span>游览方式</span>
  <el-radio-group v-model="explanationLevel" size="small">
    <el-radio-button value="child">👶 亲子游</el-radio-button>
    <el-radio-button value="adult">🚶 休闲游</el-radio-button>
    <el-radio-button value="expert">📚 文化深度游</el-radio-button>
  </el-radio-group>
</div>
```

**同步修改样式**（在 `<style scoped>` 中添加）：

**位置**：样式块末尾添加

```css
.explanation-mode .el-radio-button__inner {
  padding: 8px 12px;
  font-size: 13px;
}
```

---

## P1-1：数字人人设化

### 目标

为数字人添加导游人格，初次见面有欢迎语

### 文件：`frontend/src/composables/useAvatar.js`

#### 修改：添加导游人设常量

**位置**：文件开头，import 之后

**添加内容**：
```javascript
// 导游人设
const GUIDE_PERSONA = {
  name: "小灵",
  greeting: "您好！我是灵山智慧导游小灵，很高兴为您服务。",
  contextIntro: {
    general: "让我为您介绍一下：",
    photo: "让我看看您拍到了什么...",
    route: "为您规划游览路线...",
  },
};

export { GUIDE_PERSONA };
```

### 文件：`frontend/src/views/tourist/ChatView.vue`

#### 修改1：导入人设

**位置**：import 区域（第 253 行左右）

**添加**：
```javascript
import { useAvatar, GUIDE_PERSONA } from "../../composables/useAvatar";
```

#### 修改2：初始化时显示欢迎语

**位置**：`onMounted` 函数中（第 358 行左右）

**修改前**：
```javascript
onMounted(() => {
  interactionStore.initialize();
});
```

**修改后**：
```javascript
onMounted(() => {
  interactionStore.initialize();
  
  // 数字人欢迎语
  if (chatStore.messages.length === 0) {
    setTimeout(() => {
      chatStore.messages.push({
        role: 'assistant',
        content: GUIDE_PERSONA.greeting
      });
    }, 800);
  }
});
```

---

## P1-2：去除技术暴露

### 目标

隐藏"证据N"编号，改为友好的"来源1、2、3"

### 文件：`frontend/src/views/tourist/ChatView.vue`

#### 修改：来源列表显示格式

**位置**：第 237-243 行

**修改前**：
```vue
<li
  v-for="(item, index) in chatStore.sources"
  :key="`${item.title}-${index}`"
  :data-source-index="index"
  :class="{ 'source-highlight': sourceHighlightIndex === index }"
>
  <h4>
    <span v-if="item.evidence_id">[{{ item.evidence_id }}] </span>{{ item.title }}
  </h4>
  <p>{{ item.snippet }}</p>
  <span>{{ item.source }}</span>
</li>
```

**修改后**：
```vue
<li
  v-for="(item, index) in chatStore.sources"
  :key="`${item.title}-${index}`"
  :data-source-index="index"
  :class="{ 'source-highlight': sourceHighlightIndex === index }"
>
  <h4>
    <span class="source-number">{{ index + 1 }}</span>
    {{ item.title }}
  </h4>
  <p>{{ item.snippet }}</p>
  <span class="source-meta">{{ item.source }}</span>
</li>
```

**同步添加样式**（在 `<style scoped>` 中）：

**位置**：`.source-list` 相关样式后添加

```css
.source-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-right: 8px;
  border-radius: 11px;
  background: var(--lingshan-gold-light);
  color: var(--lingshan-gold);
  font-size: 12px;
  font-weight: 700;
  vertical-align: middle;
}

.source-meta {
  color: var(--lingshan-stone);
  font-size: 12px;
}
```

---

## 验证清单

完成所有修改后，按以下步骤验证：

### 1. 启动服务

```bash
# 后端
cd backend && .venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend && npm run dev
```

### 2. 视觉验证

访问 http://localhost:5173，检查：

- [ ] 页面标题显示"灵山智慧导游"而非"游客交互端"
- [ ] 副标题不再包含"SSE"等技术词汇
- [ ] 页面整体色调偏暖（金色+绿色），不是冷色调科技蓝
- [ ] 用户消息气泡有金色左边框
- [ ] 助手消息气泡是浅绿色背景
- [ ] 数字人出现后自动说欢迎语（约0.8秒后）
- [ ] "讲解深度"改为"游览方式"，带emoji图标

### 3. 功能验证

提问"灵山大佛有多高？"，检查：

- [ ] 回答中的 `[证据1]` 显示为金色小标签
- [ ] 右侧"资料来源"面板不显示"证据1"字样，显示序号"1"
- [ ] 点击回答中的引文标签，右侧对应来源高亮（黄色边框）
- [ ] 输入框占位符显示友好文案

### 4. 响应式验证

缩小浏览器窗口到手机尺寸，检查：

- [ ] 布局不错乱
- [ ] 文字可读
- [ ] 按钮可点击

---

## 回滚方案

如果修改后出现问题，执行：

```bash
cd /d/桌面/软件杯
git diff  # 查看改动
git checkout -- frontend/src/views/tourist/ChatView.vue  # 回滚指定文件
git checkout -- frontend/src/style.css
```

---

## 后续优化（P2，可选）

以下优化可在评审反馈后再做：

1. **布局改为侧边栏式** - 数字人固定左侧，对话占主区域
2. **添加快捷提问卡片** - 常见问题一键提问
3. **音频波形可视化** - 语音输入时显示音波
4. **深色模式** - 夜间游览友好

---

## 文件清单

本次修改涉及以下文件：

```
frontend/src/views/tourist/ChatView.vue  ← 主要改动
frontend/src/style.css                   ← 色彩变量
frontend/src/composables/useAvatar.js    ← 人设定义
```

**预计总耗时：1.5小时**

完成后运行 `git diff` 查看所有改动，确认无误后提交。
