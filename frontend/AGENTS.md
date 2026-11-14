# Frontend guidance

遵守仓库根目录 [AGENTS.md](../AGENTS.md)，定位见 [功能地图](../docs/REPO_MAP.md)。

- 运行目录 `frontend/`；游客端和管理端有独立入口：`npm run dev:tourist`（5173）、`npm run dev:admin`（5174）、`npm run build:tourist`、`npm run build:admin`。`npm run dev` 默认游客端；`npm run build` 构建两端；`npm test` 使用 Node 内置测试。
- Node 条件以锁文件 engines 为准；当前 Vite 要求 `^20.19.0 || >=22.12.0`。
- 应用路由以 `apps/tourist/router.js`、`apps/admin/router.js` 为事实来源；`src/router/index.js` 仅供兼容 legacy 入口。游客旧路由多数重定向到统一舞台的 query 工具。
- `TouristView.vue` 只包裹 `ChatView.vue`；不能因旧文件存在就认定为独立路由页面。
- UI 编排在 views，状态在 Pinia stores，设备生命周期在 composables，HTTP 在 api。
- `api/http.js` 管理 `VITE_API_BASE_URL` 与普通请求；SSE 使用 fetch POST 和 `useSSEStream.js`，不是 EventSource。
- 开发期 `/api`、`/ui-assets` 由 Vite 代理；生产同源反代另行配置，不能依赖 dev proxy。
- 录音输出单声道 WAV；识图上传原始文件 body。不要改为 multipart 而不同时修改后端。
- `ChatView.vue` 使用 `ThreeAvatar.vue`，加载失败走 `AvatarDisplay.vue`；不要引入第二个人物画布。
- 游客入口位于 `apps/tourist/`，不得导入管理 token/store、后台 API、Element Plus 或 ECharts；管理入口位于 `apps/admin/`，不得挂游客聊天/匿名行程舞台。改入口依赖后运行 `npm run check:app-boundaries` 和 `npm run check:build-isolation`。
- `src/api/transport.js` 不带身份；游客客户端不读取管理员 token，管理员客户端只在 `adminHttp.js` 附加 token。禁止把 token 放进共享 transport、URL、游客请求或游客构建产物。
- 两套独立构建产物为 `dist/tourist`、`dist/admin`。改 public 资源时检查 `prepare-public.mjs` 和 build boundary，只有游客需要的录音 worklet 不应进入管理端。
- 生产发布按 [双端边界说明](../docs/development/FRONTEND_BOUNDARIES.md) 打包 release manifest；不要把 `dist/legacy` 当作游客或管理端发布物。
- `guide-page.css` 有多轮覆盖，检查文件后部；游客断点与后台断点不相同。
- 相机、麦克风、音频、定位、WebGL 和弹层变更按 [多端矩阵](../docs/COMPATIBILITY.md) 验证。
- 浏览器关闭能力或拒绝权限时保留现有降级；不根据 UA 字符串承诺支持。
- 改 Markdown 展示时保留 `useMarkdown.js` 的 DOMPurify 清洗。
- 先运行 `npm test` 和构建，再按实际设备记录结果。仓库当前没有已配置的 lint 命令。
