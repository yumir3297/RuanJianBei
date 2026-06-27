# Live2D 白屏修复报告

## 1. 故障现象

游客页全白，Chrome Console 报错：

```text
Uncaught Error: Could not find Cubism 2 runtime.
This plugin requires live2d.min.js to be loaded.
```

## 2. 根因

当时 `Live2DAvatar.vue` 导入：

```js
import { Live2DModel } from "pixi-live2d-display";
```

该根包会同时注册 Cubism 2 与 Cubism 4。项目只引入 Cubism 4 Core，因此模块加载阶段因缺少 Cubism 2 Runtime 抛错。错误发生在 Vue 挂载前，所以不是数字人区域空白，而是整个页面白屏。

同时发现：

```text
pixi-live2d-display@0.4.0 要求 Pixi 6
项目原先安装 pixi.js@7.4.3
```

两套 Pixi 的 DisplayObject 类不兼容，属于白屏修复后的下一层运行风险。

## 3. 已实施修复

### Cubism 入口

改为只加载 Cubism 4：

```js
import { Live2DModel } from "pixi-live2d-display/cubism4";
```

没有增加 Cubism 2 Runtime。

### Pixi 版本统一

将项目调整为：

```text
pixi-live2d-display@0.4.0
pixi.js@6.5.10
```

依赖树只保留一套 `@pixi/* 6.5.10`。

类继承验证：

```text
Live2DModel instanceof project PIXI.DisplayObject = true
```

### 降级显示

1. `Live2DAvatar.vue` 加载失败时发送 `load-error`。
2. `ChatView.vue` 收到错误后切换到现有 `AvatarDisplay.vue`。
3. CDN、WebGL 或模型错误不再导致数字人区域完全空白。

### 首次状态同步

模型加载成功后立即应用当前：

1. `emotion`
2. `isSpeaking`

避免模型下载期间已经开始回答，但加载完成后不张嘴或不切表情。

### 全局脚本清理

删除 `index.html` 中：

```js
window.PIXI = window.PIXI || {};
```

由 `Live2DAvatar.vue` 在导入真实 Pixi 模块后设置 `window.PIXI`。

## 4. 缓存处理

已删除旧的：

```text
frontend/node_modules/.vite
```

并使用 `--force` 强制重新预构建。

新的 Vite 缓存：

```text
browserHash = 55e4d308
```

优化依赖中只包含：

```text
pixi-live2d-display/cubism4
pixi.js
```

不再包含：

```text
pixi-live2d-display
```

## 5. 验证结果

```text
前端生产构建：通过
Pixi 版本兼容检查：通过
构建产物 Cubism 2 报错检索：不存在
Vite 开发缓存 Cubism 2 报错检索：不存在
修复版开发服务：HTTP 200
实际下发组件：pixi-live2d-display_cubism4.js
游客页 SVG 降级：已编译
```

修复后主 JS 由约 `1.91 MB` 降至约 `1.73 MB`，重复 Pixi 运行时已移除。

## 6. 用户侧操作

截图中的旧模块 URL 带有：

```text
?v=9699980e
```

这是旧 Vite 服务的缓存版本。代码修改后必须：

1. 关闭原来运行前端的终端。
2. 重新执行 `npm.cmd run dev`。
3. Chrome 按 `Ctrl + Shift + R` 强制刷新。

本轮验证用修复版地址：

```text
http://127.0.0.1:5174/
```

如果继续使用常规端口，重启后访问：

```text
http://127.0.0.1:5173/
```

## 7. 尚未处理

本轮只修复白屏和可见降级。以下仍按数字人运行报告保留：

1. TTS 仍为 stub。
2. 口型仍是模拟开合。
3. 流式回答情感仍需补齐。
4. 后台 AvatarConfig 尚未驱动游客页模型。

