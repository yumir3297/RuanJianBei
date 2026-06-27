# 前端文化化设计实施计划

## 目标

依据《前端设计优化-去AI味-实施方案》完成 P0 与 P1 改造，在不改变问答、语音、图片识别和来源跳转逻辑的前提下：

1. 将游客端技术文案改为导游服务语言。
2. 建立佛像金、禅境绿、宣纸白的统一视觉主题。
3. 为数字人补充“小灵”人设和首次欢迎语。
4. 将来源编号和图片识别结果改为游客可理解的展示方式。
5. 验证桌面端、移动端布局和生产构建。

## 涉及文件

- `frontend/src/style.css`
- `frontend/src/App.vue`
- `frontend/src/views/tourist/ChatView.vue`
- `frontend/src/components/interaction/GoalSelector.vue`
- `frontend/src/components/AvatarDisplay.vue`
- `frontend/src/composables/useAvatar.js`

## 验收标准

- 页面不再公开显示 SSE、Provider、Qwen 等实现术语。
- 游客页使用灵山文化色彩，消息与来源层级清晰。
- 首次进入时出现“小灵”欢迎语，重复切换页面不重复插入。
- 引文点击仍能定位并高亮对应资料。
- `npm run build` 通过，桌面和移动视口无明显溢出。
