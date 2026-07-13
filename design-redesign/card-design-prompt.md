# 四张功能卡片视觉设计任务

> 本文件是给 GPT 的设计指令。请通读全文后，在 select-preview.html 中设计四张卡片的视觉表现。

---

## 1. 先看现有设计（建立审美对齐）

在开始设计前，请先阅读以下三个已有文件，理解这个项目已确立的设计语言：

| 文件 | 路径 |
|---|---|
| 首页 Landing | `design-redesign/landing-preview.html` |
| 游客欢迎页 | `design-redesign/welcome-preview.html` |
| 3D 数字人组件 | `design-redesign/avatar-3d-preview.html` |

### 已确立的设计规范摘要

```
配色：        暖米白文字 #e8e4db + 淡金点缀 #d4a853 + 深黑底 #0d0c0a
字体：        楷体优先 STKaiti / KaiTi / STSong + system-ui fallback
风格：        古风、沉浸、克制、不炫技
按钮：        玻璃拟态 (backdrop-filter blur + rgba 半透明 + 金色弱光)
              少用实色/硬边框/大圆角
交互反馈：    过渡用 cubic-bezier(0.22, 1, 0.36, 1)
              时间 350ms ~ 480ms，不过度弹跳
玻璃卡片：    background: rgba(255,255,255,0.04~0.08)
              border: 1px solid rgba(255,255,255,0.06~0.12)
              border-radius: 12px~24px
              backdrop-filter: blur(14~20px)
              box-shadow 弱且克制
```

---

## 2. 要修改的文件

**`design-redesign/select-preview.html`**

这个文件已经实现了完整的轮播框架：中央主卡片 + 左右预览 + 边缘露出 + 箭头/拖拽/键盘切换 + 底部分页/动态按钮。轮播逻辑不需要修改。

### 2.1 已实现的轮播框架（参考，不改）

轮播已在工作。卡片使用 `data-level` 属性和 JS 驱动的 CSS transform 实现层级切换：

```
中央主卡片       data-level="0"      scale=1      opacity=1       z-index=10
左右次级卡片     data-level="±1"     scale=0.87   opacity=0.65    z-index=5
左右边缘卡片     data-level="±2"     scale=0.76   opacity=0.3     z-index=1
```

切换动画参数：`0.48s cubic-bezier(0.22,1,0.36,1)`

### 2.2 当前卡片 DOM 结构（你的设计区域）

```html
<div class="feature-card" data-level="0">
  <div class="card-accent-line" style="background:#8b9cf7"></div>
  <span class="card-index" style="color:#8b9cf7">01</span>
  <div class="card-title">数字人导游</div>
  <p class="card-desc">与虚拟导游实时对话，获取景点讲解与个性化服务</p>
  <div class="card-arrow-hint">→</div>
</div>
```

### 2.3 当前卡片 CSS（你的起点）

```css
.feature-card {
  position: absolute;
  left: 50%; top: 50%;
  width: 360px;
  padding: 28px 24px 22px;
  border-radius: 24px;
  border: 1px solid rgba(255,255,255,0.07);
  background: rgba(16,14,10,0.82);
  backdrop-filter: blur(18px);
  cursor: pointer;
  transform-origin: center center;
  /* transition 由 JS 控制 */
  will-change: transform, opacity;
  display: flex; flex-direction: column;
  outline: none;
}
```

---

## 3. 四张卡片的业务数据

数据由 JS 中的 `features` 数组驱动，已存在，不改：

```js
const features = [
  {
    id: "guide",
    index: 0,
    title: "数字人导游",
    description: "与虚拟导游实时对话，获取景点讲解与个性化服务",
    themeColor: "#8b9cf7",   // 蓝紫
    actionLabel: "进入数字人导游",
    route: "/tourist",
  },
  {
    id: "explore",
    index: 1,
    title: "景点探索",
    description: "发现热门景点、特色文化与精选游览内容",
    themeColor: "#5ec9a4",   // 青绿
    actionLabel: "探索热门景点",
    route: "/tourist",
  },
  {
    id: "route",
    index: 2,
    title: "智能路线",
    description: "根据时间、兴趣与位置生成个性化游览计划",
    themeColor: "#e8a840",   // 橙黄
    actionLabel: "开始规划路线",
    route: "/tourist",
  },
  {
    id: "quiz",
    index: 3,
    title: "文化问答",
    description: "通过智能问答深入了解地方历史与文化知识",
    themeColor: "#d478a8",   // 紫红
    actionLabel: "进入文化问答",
    route: "/tourist",
  },
];
```

### 主题色用途

每个 `themeColor` 可以用于：
- 卡片顶部 accent line 的颜色
- 编号文字的颜色
- 卡片 hover 时的边框高亮色
- 卡片内部装饰元素的颜色

四个主题色之间应保持统一饱和度/明度，使四张卡片看起来是同一套设计。

---

## 4. 你的设计任务

### 你必须做的事

1. **仅修改卡片内部的视觉设计**
   - 修改 `feature-card` 的 CSS（背景、边框、阴影、圆角等）
   - 修改卡片内部元素（.card-index、.card-title、.card-desc、.card-arrow-hint、.card-accent-line）的 CSS
   - 可以在 `.feature-card[data-level="0"]`、`[data-level="1"]` 等选择器中为不同层级卡片设置不同表现

2. **可以在卡片 DOM 中插入新的视觉元素**
   - 当前卡片 innerHTML 在 `card.innerHTML` 处构建（select-preview.html 约第 511 行）
   - 你可以在这里插入新的 HTML 结构，如装饰性 SVG、分隔线、图标等
   - 但必须保留 .card-index、.card-title、.card-desc、.card-arrow-hint 这四个功能元素的语义内容不变

3. **可以插入新的 CSS 变量或规则**

### 你不能做的事

- ❌ 不要修改轮播逻辑（goTo、layoutCards、拖拽/键盘事件等 JS）
- ❌ 不要修改 features 数据数组的内容（标题、描述、路由等字段保持不变）
- ❌ 不要修改页面整体布局（顶部标题、底部按钮区域、背景层）
- ❌ 不要破坏现有响应式断点（桌面 ≥1200px / 平板 769-1199px / 移动 <768px）
- ❌ 不要使用外部图片 URL（所有视觉用 CSS/SVG 内联实现）
- ❌ 不要引入新的 JS 依赖或库

### 设计目标

四张卡片在视觉上应该：

1. **统一且各有辨识度** —— 同一套卡片模板，通过主题色区分功能，不要四张卡像四个毫不相关的设计
2. **中央主卡片突出** —— 主卡片在 opacity=1 时完整、清晰、有分量感
3. **次级卡片可预览** —— opacity=0.65 时仍能辨认出是卡片和功能名，但视觉权重明显降低
4. **符合古风克制审美** —— 与 welcome-preview.html 的风格一致，不霓虹、不弹跳、不过度装饰
5. **卡片有足够的内容呼吸空间** —— 目前只有编号+标题+描述+箭头，如果你加入装饰元素，不要填满所有空白

### 可选方向建议（选一个或融合）

- **方向 A：简约文字优先** —— 卡片以大标题为核心，主题色编号作点缀，底部暗色线条分隔 + 箭头，极简干净
- **方向 B：色彩渐变微装饰** —— 卡片顶部有主题色的微弱渐变条带，编号做半透明大字背景水印效果，hover 时微光扩散
- **方向 C：国风印章/纹理** —— 编号做成印章风格，卡片带微弱的纹理背景或古风边框装饰，标题字号略大

### 验收标准

- [ ] 四张卡在当前页正常展示，中央卡片清晰突出
- [ ] 卡边之间视觉统一，不出现四种完全不同风格
- [ ] 次级/边缘卡片的降级效果合理（模糊、缩略、文字淡出）
- [ ] 鼠标拖拽切换仍然流畅
- [ ] 没有引入明显性能问题（避免大量 box-shadow 叠加、滤镜叠加）
- [ ] 桌面/平板/移动端三档响应式正常
- [ ] 与 welcome-preview.html 打开对比，风格协调不割裂

---

## 5. 预览方法

```
# 终端1：启动 Vite（供背景图和模型引用）
cd frontend && npm run dev

# 终端2：启动预览服务器
python -m http.server 9999 --directory design-redesign

# 浏览器打开
http://localhost:9999/select-preview.html
```

两个服务器必须同时运行，因为 select-preview.html 通过 `http://localhost:5173/assets/slides/bg-alt.jpg` 引用背景图。

---

## 6. 交付物

修改后的 `design-redesign/select-preview.html`，并附一段简短说明你做了什么设计选择、为什么这样做。
