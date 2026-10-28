# Frontend guidance

遵守仓库根目录 [AGENTS.md](../AGENTS.md)，定位见 [功能地图](../docs/REPO_MAP.md)。

- 运行目录 `frontend/`；实际脚本只有 `npm run dev`、`npm run build`、`npm run preview`。
- Node 条件以锁文件 engines 为准；当前 Vite 要求 `^20.19.0 || >=22.12.0`。
- `src/router/index.js` 是路由事实来源。游客旧路由多数重定向到统一舞台的 query 工具。
- `TouristView.vue` 只包裹 `ChatView.vue`；不能因旧文件存在就认定为独立路由页面。
- UI 编排在 views，状态在 Pinia stores，设备生命周期在 composables，HTTP 在 api。
- `api/http.js` 管理 `VITE_API_BASE_URL` 与普通请求；SSE 使用 fetch POST 和 `useSSEStream.js`，不是 EventSource。
- 开发期 `/api`、`/ui-assets` 由 Vite 代理；生产同源反代另行配置，不能依赖 dev proxy。
- 录音输出单声道 WAV；识图上传原始文件 body。不要改为 multipart 而不同时修改后端。
- `ChatView.vue` 使用 `ThreeAvatar.vue`，加载失败走 `AvatarDisplay.vue`；不要引入第二个人物画布。
- `guide-page.css` 有多轮覆盖，检查文件后部；游客断点与后台断点不相同。
- 相机、麦克风、音频、定位、WebGL 和弹层变更按 [多端矩阵](../docs/COMPATIBILITY.md) 验证。
- 浏览器关闭能力或拒绝权限时保留现有降级；不根据 UA 字符串承诺支持。
- 改 Markdown 展示时保留 `useMarkdown.js` 的 DOMPurify 清洗。
- 先构建验证，再按实际设备记录结果。仓库当前没有已配置的前端自动化 test/lint 命令。
