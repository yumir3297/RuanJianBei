# 离线伴游与应急页 · 现状审计（阶段 A）

> 审计日期：2026-10-31
> 基线分支：`master`
> 基线 SHA：`80bd403233441032c4e5717742aa2c438b971cab`
> 开发分支：`feature/offline-companion`（独立 Worktree：`../RuanJianBei-offline`）
> 审计方式：本地真实代码逐文件阅读（非远程快照推断）

---

## 1. 仓库与 Git 状态

| 项目 | 事实 |
|---|---|
| 主工作树 | `/Users/yumir/Documents/Trae-CN/temp_20261020_01/RuanJianBei`，分支 `master`，HEAD `80bd403` |
| 主工作树未提交改动 | `.gitignore`、`README.md`、`backend/requirements.txt`、`evaluation/*`、`frontend/package-lock.json`、`frontend/一键启动前端.md`、`docs/optimization/`（均与本需求无关，**未搬运、未覆盖**） |
| 功能 Worktree | `/Users/yumir/Documents/Trae-CN/temp_20261020_01/RuanJianBei-offline`，分支 `feature/offline-companion`，从 `80bd403` 创建 |
| `AGENTS.md` | 不存在（全仓库 `-iname AGENTS.md` 无结果） |
| 代码映射库 | 不存在 `CODE_MAP.md`；无 `docs/plans/2026-10-27-feature-roadmap.md`。现有架构资料为 `docs/superpowers/plans/`、`docs/superpowers/specs/`、`docs/design/`、根目录 `DESIGN.md`、`README.md` |
| 前端测试 | 无测试目录、无 `test`/`lint`/`typecheck` 脚本；仅有 `scripts/compress-vrm.mjs` |
| 后端测试 | `backend/app/tests/`（pytest，需数据库与模型，不用于本次离线功能门禁） |

**结论：映射库与 AGENTS 规范均不存在，本审计按源码建立本功能涉及的最小定位表，不编造文件。**

---

## 2. 本功能涉及的最小代码定位表

| 真实路径 | 关键事实（已核对） | 本需求处置 |
|---|---|---|
| `frontend/src/router/index.js` | `createWebHistory()`；`/tourist` → `TouristView`；旧工具 URL 用 `guideRedirect` 重定向到 `/tourist?tool=xxx` | **不改路由**，离线页走独立静态入口，不进入 Vue Router |
| `frontend/src/views/tourist/TouristView.vue` | 仅 `<ChatView />` 两行 | 不改 |
| `frontend/src/views/tourist/ChatView.vue` | 1271 行；集成 ThreeAvatar、语音、工具面板、景区服务热线 `handleHotline`（仅把号码写入聊天消息，见 L416-L424） | 只追加 1 个组件的挂载点，不重构 |
| `frontend/src/views/tourist/MapView.vue` | Leaflet + 高德在线矢量/影像瓦片（L170-L171），含“模拟巡游”（L36） | 不作为离线地图，不改动 |
| `frontend/src/constants/mapSpots.js` | 首行注明“演示坐标（GCJ-02 近似，非测绘数据）” | 不在应急图中使用 |
| `frontend/src/composables/useGeolocation.js` | 真实定位 + “模拟巡游兜底”，WGS84→GCJ-02 纠偏 | 离线页**完全不接定位**，不显示“你在这里” |
| `frontend/src/api/http.js` | axios 同源 `/api`，超时 10s，注入 Authorization | 健康探针不复用 axios，避免拦截器与凭据泄漏 |
| `frontend/src/main.js`、`App.vue` | 全局注入 Pinia / Router / Element Plus，且在 `main.js` 静态引入全量 `element-plus/dist/index.css` | 离线页**不进入该启动包**，独立 HTML 入口 |
| `frontend/vite.config.js` | 仅 `@vitejs/plugin-vue`；代理 `/api`、`/ui-assets`，无 `/health` | 增加 `/health` 代理、`offline.html` 多入口、预缓存清单插件 |
| `frontend/package.json` | 仅 `dev`/`build`/`preview`；无测试与 lint 工具 | 仅新增 `test`（`node --test`，零依赖）与 E2E 脚本；不虚报原有脚本 |
| `backend/main.py` | `GET /health` 返回 `{status:'ok', service}`（L111-L114）；`GET /ready` 检查 DB/凭据（L116-L139）；`SPAStaticFiles` 对非 `api/` 的 404 回落 `index.html`（L36-L49） | 复用 `/health` 为探针；`/offline.html` 是 dist 真实文件，静态挂载会直接命中，不触发回落 |
| `frontend/src/composables/useScenicBackground.js` | 默认热线常量 `0510-85688631 / 400-168-0303转5 / 0510-85688120`（L31-L35），后台可改 | **未被官方核验**，离线页按 `status: unverified` 处理，不展示“拨打” |
| `frontend/src/views/admin/DisplayAssets.vue` | 后台可编辑同组热线 | 不改 |

---

## 3. 现状缺口（已扫描）

1. **无 PWA / Service Worker**：`grep -rniE "serviceWorker|workbox|manifest.json"` 在全前端源码与 `index.html` 中零命中。
2. **无连通性检测**：全仓库无 `navigator.onLine`、无健康探针调用；断网时游客端只会由业务请求失败自然报错。
3. **无独立离线入口**：仅 `index.html`（Vue 主站）与两个静态调试页 `public/map-tester.html`、`public/motion-tester.html`。
4. **主站首屏依赖在线**：`index.html` 引用 Google Fonts；`main.js` 引入全量 Element Plus 样式；`ChatView` 依赖 VRM 模型与在线地图。这些**一律不进离线预缓存**。
5. **地图不可离线**：瓦片全部来自 `is.autonavi.com`，且 `mapSpots.js` 坐标自述非测绘数据。
6. **热线不可作为救援依据**：`handleHotline` 只把字符串写入聊天，无核验元数据（来源/时间/状态）。

---

## 4. 离线入口技术决策

| 决策点 | 结论 | 理由 |
|---|---|---|
| 入口形态 | Vite **多入口** `offline.html` → 输出 `dist/offline.html` | 与主站完全解耦，不加载 Vue/Element Plus/Three/VRM/Leaflet |
| 运行时框架 | 无框架，原生 ES Module + Canvas 2D | 体积与首屏优先，游戏无需引擎 |
| 离线缓存 | 手写 Service Worker + 构建期生成的**精确预缓存清单** | 避免 Workbox 额外依赖；清单由 `generateBundle` 从真实产物图（entry chunk → imports → CSS）推导，不猜测哈希文件名 |
| 探针 | 同源 `GET /health`，`cache:'no-store'`、`redirect:'error'`、`AbortController` 2500ms，校验 JSON `status==='ok'` | 复用后端既有端点；拒绝 HTML 登录页/伪 200 |
| 存储 | IndexedDB 单库单表 + localStorage 降级 + 内存降级 | 版本化快照，失败不阻塞应急功能 |
| 地图 | 单张静态 SVG + 自研缩放/平移（wheel / 双指 / 拖拽 / 按钮） | 完全无瓦片、无定位 |
| 电话 | 本地 JSON（含 `verifiedAt/source/status`）+ 条件渲染 `tel:` | `tel:` 仅在 `status==='verified'` 时出现 |

### 4.1 预缓存白名单（构建期由插件生成）

- `/offline.html`
- 离线入口的 entry chunk 及其全部静态 import chunk（含跨入口共享 chunk）
- 上述 chunk 的 `viteMetadata.importedCss`
- `public/offline/**`（`contacts.json`、`map/map-meta.json`、地图 SVG）
- `/favicon.svg`
- `/offline-precache-manifest.json`（构建插件生成，页面用它校验缓存完整性）

**明确不缓存**：`/api/**`、`/health`、`/ui-assets/**`、`/assets/**` 中的主站大包（Three/VRM/Element Plus/ECharts/Leaflet）、主站图片与模型、任何账号或聊天数据。

---

## 5. 冻结的接口契约

### 5.1 `ConnectivityMonitor`（`frontend/src/offline/connectivity.js`）

```ts
type ConnectivityState = 'UNKNOWN'|'ONLINE'|'SUSPECT'|'DEGRADED'|'RECOVERING'
interface ProbeResult { ok: boolean; time: number; reason?: string }
interface ConnectivityMonitor {
  getState(): ConnectivityState
  start(): void
  stop(): void
  subscribe(fn: (state: ConnectivityState) => void): () => void
  probeNow(): Promise<ProbeResult>
}
createConnectivityMonitor(options?): ConnectivityMonitor
```

默认参数：`probeUrl='/health'`、`intervalMs=5000`、`hiddenIntervalMs=30000`、`timeoutMs=2500`、`degradedFails=3`、`degradedMinMs=15000`、`recoverSuccesses=2`、`recoverMinGapMs=3000`。
依赖注入（`now` / `fetchImpl` / `documentRef`）用于确定性单测。

### 5.2 `OfflineSnapshot`（`frontend/src/offline/offline-storage.js`）

```json
{
  "schemaVersion": 1,
  "appVersion": "string",
  "sessionId": "local-uuid",
  "bestScore": 0,
  "lastScore": 0,
  "returnTarget": "/tourist",
  "returnConsumedAt": null,
  "mapVersion": "string",
  "contactsVersion": "string",
  "updatedAt": "ISO8601"
}
```

白名单约束：`returnTarget` 只允许 `/tourist` 或 `/tourist?tool=map|explore|route|quiz`；不含 token、聊天、位置、电话记录。

### 5.3 应急数据 Schema

`public/offline/help/contacts.json`
```json
{
  "siteId": "string", "regionName": "string", "contactsVersion": "string",
  "verifiedAt": "ISO8601|null", "source": "string|null", "status": "verified|unverified|expired",
  "entries": [{ "id": "", "group": "emergency|service", "label": "", "phoneDisplay": "", "phoneUri": "tel:...", "verifiedAt": null, "source": null, "status": "unverified" }]
}
```

`public/offline/map/map-meta.json`
```json
{ "mapVersion": "", "regionName": "", "file": "relative svg path", "status": "verified|unverified|missing", "source": null, "license": null, "verifiedAt": null, "usableForEmergency": false }
```

---

## 6. 计划修改/新增文件

**新增**
- `frontend/offline.html`
- `frontend/src/offline/{main,game,game-state,connectivity,offline-storage,offline-map,offline-help,offline-registration}.js`
- `frontend/src/offline/offline.css`
- `frontend/src/components/OfflineEntryPrompt.vue`
- `frontend/src/offline/service-worker.js`（模板，构建期注入清单）
- `frontend/scripts/offline-sw-plugin.mjs`
- `frontend/public/offline/help/contacts.json`
- `frontend/public/offline/map/map-meta.json`
- `frontend/public/offline/map/placeholder-scenic-map.svg`（**明确标注“未核验示意图”，不可用于救援**）
- `frontend/tests/*.test.js`（node:test）
- `docs/implementation/OFFLINE_ACCEPTANCE.md`

**修改**
- `frontend/vite.config.js`（多入口、`/health` 代理、SW 插件、`preview.proxy`）
- `frontend/package.json`（`test` 脚本）
- `frontend/src/views/tourist/ChatView.vue`（仅追加 `<OfflineEntryPrompt />` 与 1 行 import）
- `README.md`（离线伴游使用说明）

**不改动**：`ThreeAvatar`、RAG/ASR/TTS、地图在线逻辑、管理端、路由表、后端接口语义。

---

## 7. 测试矩阵与本环境可执行性

| 组 | 计划手段 | 当前阻塞 |
|---|---|---|
| 状态机 / 游戏 / URL 白名单 / 数据 schema | `node --test`（零新增依赖） | 无 |
| 离线缓存、断网刷新、恢复返回 | Node 静态服务器 + Chrome 无头浏览器真实断网 | 需本机浏览器二进制（已存在 `~/Library/Caches/ms-playwright/chromium_headless_shell-1243`），以实际安装结果为准 |
| 真机 iOS/微信/安卓 | 人工 | **BLOCKED**：无真机 |
| 景区电话核验 | 人工 + 官方资料 | **BLOCKED**：仓库内无核验记录，不自行认定官方号码 |
| 景区离线简图 | 合法授权资源 | **BLOCKED**：仓库内无可用离线图源；仅提供明确标注的未核验示意图占位 |

---

## 8. 已知阻塞与风险

1. **应急电话未核验（BLOCKED）**：现有热线来自景区后台默认配置，无来源/核验时间。离线页按 `unverified` 渲染：不做“官方救援”表述、不出 `tel:` 拨打按钮、显著提示“请向附近工作人员求助”。
2. **离线地图未核验（BLOCKED）**：无合法可离线分发的实测图。占位 SVG 仅说明方位与景区名，画布内嵌“未核验/不可用于救援”水印，`usableForEmergency:false`。
3. `/offline.html` 依赖生产构建产物存在；开发模式（vite dev）可访问但无 SW，会如实显示“离线包未就绪”。
4. 主工作树存在与本需求无关的未提交改动，本分支不触碰。

---

## 9. 审计门禁结论

- 主站接入面已收敛为「1 个组件 + 1 行模板挂载」，**不会重构 ChatView**。
- 离线闭环与主站解耦，可先独立验收。
- 安全数据缺失属外部前置条件，按任务书要求以显式缺失状态交付，**不宣称正式可用于救援**。
