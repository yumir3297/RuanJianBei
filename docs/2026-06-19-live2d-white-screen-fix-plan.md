# Live2D 白屏修复计划

## 1. 已确认根因

浏览器报错：

```text
Could not find Cubism 2 runtime.
This plugin requires live2d.min.js to be loaded.
```

当前 `Live2DAvatar.vue` 导入了：

```js
import { Live2DModel } from "pixi-live2d-display";
```

该根入口同时注册 Cubism 2 和 Cubism 4。页面只加载了 Cubism 4 Core，因此模块初始化时因缺少 Cubism 2 Runtime 直接抛错，Vue 尚未挂载就出现全页白屏。

另外，当前项目直接依赖 `pixi.js@7.4.3`，而 `pixi-live2d-display@0.4.0` 的 peerDependencies 要求 Pixi 6。即使只修导入入口，仍可能遇到不同 Pixi 主版本的 DisplayObject/Stage 运行时冲突。

## 2. 本轮修复

1. 将 Live2D 导入改为仅包含 Cubism 4 的 `pixi-live2d-display/cubism4`。
2. 将项目 `pixi.js` 统一到插件兼容的 `6.5.10`。
3. 删除 `index.html` 中无意义的 `window.PIXI = {}` 占位，避免在模块加载前暴露错误对象。
4. Live2D 加载失败时向父组件发送错误事件。
5. 游客页在 Live2D 失败时显示现有 SVG `AvatarDisplay`，确保数字人故障不再导致空白区域或整页不可用。
6. 模型加载完成后重新应用当前表情和说话状态，避免首次状态丢失。
7. 清理 Vite 旧依赖预构建缓存并重新构建。

## 3. 不做

1. 不增加 Cubism 2 Runtime。
2. 不改后端、数据库、SSE 或模型供应商。
3. 不接真实 TTS。
4. 不修改 Live2D 模型地址。

## 4. 验收标准

1. Vite 不再预构建 `pixi-live2d-display` 根入口。
2. 控制台不再出现 Cubism 2 Runtime 错误。
3. `Live2DModel` 与项目 `PIXI.DisplayObject` 属于同一继承体系。
4. 前端生产构建通过。
5. Live2D 加载失败时游客页显示 SVG 数字人，而不是白屏。
