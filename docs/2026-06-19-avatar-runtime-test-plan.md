# 数字人当前开发运行测试计划

## 1. 测试目标

对当前数字人实现做一次只读运行审查，确认以下链路能否真正工作：

```text
后端回答
-> avatar SSE 事件
-> chat store 分发
-> useAvatar 状态机
-> Live2D 表情与口型动画
```

本轮以测试和记录为主，不擅自替换数字人供应商、模型或依赖。

## 2. 当前实现基线

1. 游客页使用 `Live2DAvatar.vue`。
2. Live2D 渲染依赖 `pixi.js` 和 `pixi-live2d-display/cubism4`。
3. 默认模型来自 jsDelivr 上的远程 Haru 测试模型。
4. `useAvatar.js` 负责 `idle/listening/thinking/speaking/happy/apology` 状态。
5. 后端 Avatar 与 TTS 仍使用 Stub Provider。
6. 后端已有 AvatarConfig 数据模型和管理 API。
7. 管理端 `AvatarConfig.vue` 仍是占位信息页。
8. 旧 `AvatarDisplay.vue` SVG 组件仍存在，但当前游客页没有把它作为 Live2D 失败降级。

## 3. 测试项目

### 3.1 构建与依赖

1. 前端生产构建。
2. Live2D/Pixi 模块解析。
3. Cubism 4 Runtime 前置条件。
4. 默认模型 JSON 和引用资源可访问性。

### 3.2 前端状态机

1. 初始状态为 `idle`。
2. 提问后进入 `thinking`。
3. 收到 avatar SSE 后进入 `speaking`。
4. `happy` 和 `apology` 表情状态映射。
5. 音频结束后回到 `idle`。
6. 非法状态不会污染状态机。

### 3.3 后端数字人链路

1. AvatarConfig 表和种子配置。
2. 列表、当前激活项和切换接口。
3. Pipeline 是否产生 avatar SSE。
4. FAQ/直接回答路径的情感映射。
5. 流式 LLM 路径是否仍固定为 `neutral`。

### 3.4 页面运行

1. 游客页路由可访问。
2. 前后端健康检查。
3. Live2D 模型加载失败是否有用户可见降级。
4. 浏览器控制可用时检查 canvas、控制台错误和页面状态。

## 4. 明确不做

1. 不真实调用 DeepSeek 或 Qwen。
2. 不安装或更换数字人依赖。
3. 不接受摄像头或麦克风权限。
4. 不修改数据库结构。
5. 不修复测试中发现的问题，先形成报告并由用户确认下一步。

## 5. 预期输出

生成运行测试报告，逐项标记：

```text
通过 / 部分通过 / 未通过 / 无法自动验证
```

并说明当前数字人是否达到比赛演示条件，以及需要优先修复的阻塞项。
