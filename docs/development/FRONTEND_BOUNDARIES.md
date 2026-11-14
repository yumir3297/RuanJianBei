# 游客端与管理端开发边界

当前是一个仓库、两套 Vue/Vite 应用、一个共享 FastAPI 服务。游客端和管理端可用不同 origin、不同静态发布目录；数据库、API、K01 知识任务和 W02 worker 仍属于共享后端运行面。

## 入口与产物

| 应用 | 源码入口 | 本机地址 | 构建产物 | 主要能力 |
|---|---|---|---|---|
| 游客端 | `frontend/apps/tourist/` | `http://localhost:5173` | `frontend/dist/tourist/` | ChatView、数字人、地图/路线、匿名游览、设备交互 |
| 管理端 | `frontend/apps/admin/` | `http://localhost:5174` | `frontend/dist/admin/` | 登录、知识/资源管理、分析、后台数字人预览 |

```sh
# cwd: frontend/
npm ci
npm run dev:tourist
npm run dev:admin
npm run build:tourist
npm run build:admin
npm run check:app-boundaries
npm run check:build-boundaries
npm run check:build-isolation
```

`npm run dev` 是游客端别名，`npm run build` 构建两端。`build:legacy`/`preview:legacy` 只用于旧单体包兼容，不作为任一独立站点产物。两个 dev server 都把 `/api` 与 `/ui-assets` 代理到开发 API；dev proxy 不等于生产站点已配好。

## 身份和模块归属

- `src/api/transport.js` 只创建不带身份的 Axios client。
- 游客请求经 `src/api/http.js`、`src/api/visitorConfig.js` 等游客 API；游客 Axios 与 SSE fetch 均不得读取或转发管理员 token。
- 管理端 `src/api/adminHttp.js` 独立注入管理员 bearer token；后台 token 不得用于匿名行程 owner 权限。
- 共享组件/工具应保持身份中立。若行为只属于单一应用，优先放在该 app 下，避免游客图把 Element Plus、ECharts、管理员存储和后台 API 打进来。
- 游客聊天、匿名游览与媒体/定位生命周期由游客应用拥有；管理端可以有数字人预览，不应复用游客 ChatView 或接管游客播放状态。
- 对 API、SSE、请求数据、cookie/CSRF 或配置刷新作改动时，检查 `docs/ARCHITECTURE.md` 的服务端链路和 `backend/app/api` 对应 schema/service；双端共用同一后端，不要借前端拆分改变 API 契约。

## 发布和服务器边界

每个构建包带 `release.json`，记录 app、source SHA、Vite 锁定版本、文件 SHA256 和所需后端能力。发布工具保留两端独立 `web-root/releases/<id>`、`current`、`previous`；静态发布/回滚不得运行数据库迁移、重启 API/W02 或覆盖另一端文件。

生产可将游客和管理端放在不同 HTTPS origin，但必须在目标服务器明确 Host/TLS、CORS/CSRF trusted origins、cookie 属性和 `/api` 代理路由。已有游客身份依赖 Cookie；迁移游客域名不是纯静态切换。管理端在新 origin 需重新登录，不能复制游客浏览器中的管理员 token。服务器路径和 origin 未确认前，Compose `.env` 示例与 `guide.example.org` 只是候选配置。

## 当前不在边界承诺内

- 没有 service worker，不把后台身份、API 响应、游客聊天或行程写入离线缓存。
- CASS/离线资源若后续开发，须从游客专属入口接入，逐项定义资源许可/缓存过期/清理策略；不复制旧分支整份 ChatView，不在管理端共享离线状态。
- 静态 manifest/自动化测试不能代替浏览器登录、游客匿名 owner 隔离、数字人渲染、麦克风、定位或目标手机验收；见 [多端矩阵](../COMPATIBILITY.md) 和 [实施计划最终验收](../deployment/split-v2/IMPLEMENTATION_PLAN.md)。
