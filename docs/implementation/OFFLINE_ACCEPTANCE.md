# 离线伴游与应急页 · 验收记录

> 验收日期：2026-10-31
> 基线：`master` @ `80bd403233441032c4e5717742aa2c438b971cab`
> 功能分支：`feature/offline-companion`（独立 Worktree `/Users/yumir/Documents/Trae-CN/temp_20261020_01/RuanJianBei-offline`）
> 环境：macOS / Node v24.11.0 / npm 11.6.1 / Vite 7.3.3 / playwright-core 1.63.0（Chromium headless shell 1243）

---

## 1. 交付内容

| 模块 | 文件 | 说明 |
|---|---|---|
| 独立离线入口 | `frontend/offline.html` | Vite 多入口，输出 `dist/offline.html` |
| 离线页逻辑 | `frontend/src/offline/main.js`、`offline.css` | 页面编排、浮层、状态展示 |
| 跑酷（规则） | `frontend/src/offline/game-state.js` | 纯函数状态机、碰撞、随机种子、dt 钳制 |
| 跑酷（渲染） | `frontend/src/offline/game.js` | Canvas 2D + rAF + DPR + ResizeObserver |
| 连通性 | `frontend/src/offline/connectivity.js` | `ConnectivityMonitor` + 纯 reducer，主站/离线页共用 |
| 本地快照 | `frontend/src/offline/offline-storage.js` | IndexedDB → localStorage → 内存三级降级 |
| 静态地图 | `frontend/src/offline/offline-map.js` | 单图缩放/拖动/双指/键盘，无瓦片无定位 |
| 电话 | `frontend/src/offline/offline-help.js` | schema 校验、`tel:` 白名单、复制、未核验提示 |
| SW 注册/校验 | `frontend/src/offline/offline-registration.js` | 预缓存完整性校验，注册成功 ≠ 就绪 |
| Service Worker | `frontend/src/offline/service-worker.js` | 构建期注入清单；`/health`、`/api/**` 永不缓存 |
| 构建插件 | `frontend/scripts/offline-sw-plugin.mjs` | 从真实产物图生成 `sw.js` 与 `offline-precache-manifest.json` |
| 主站入口 | `frontend/src/components/OfflineEntryPrompt.vue` + `ChatView.vue` 2 行接入 | 弱网横幅、用户点击才跳转 |
| 数据 | `frontend/public/offline/help/contacts.json`、`map/map-meta.json`、`map/placeholder-scenic-map.svg` | 均标记 `unverified` |
| 测试 | `frontend/tests/*.test.js`、`frontend/tests/e2e/offline.e2e.mjs`、`frontend/scripts/offline-test-server.mjs` | 单元 + 生产构建 E2E |

---

## 2. 网络状态机实现摘要

- 探针：同源 `GET /health`，`cache:'no-store'`、`redirect:'error'`、`Accept: application/json`、`AbortController` 2500 ms。
- 判定：HTTP 200 **且** `Content-Type` 含 `application/json` **且** JSON `status === 'ok'`；HTML 门户页、伪 200、错误 JSON 一律失败。
- 状态：`UNKNOWN → ONLINE / SUSPECT → DEGRADED → RECOVERING → ONLINE`。
  - 首帧即成功（此前无失败）→ 立即 `ONLINE`；否则恢复需 **连续 2 次成功且间隔 ≥3 s**。
  - `DEGRADED` 需 **≥3 次连续失败且距首次失败 ≥15 s**；失败即重置恢复计数。
- 主站周期 5 s、离线页 10 s，隐藏页降频 30 s；`visibilitychange` / `online` / `offline` 只触发即时复测，不直接改状态结论。
- 单实例单飞：并发 `probeNow()` 复用同一 Promise；`stop()` 后迟到响应被代际号拦截，不会覆盖新状态。
- 主站与离线页各自持有监测器，不共享内存定时器；不读取 `localStorage.online` 之类的旧标记。
- 只代表“网页服务可达”，恢复文案写“网页服务已恢复”，不宣称 ASR/LLM/TTS 全部恢复。

---

## 3. 离线预缓存清单与体积（实测）

构建命令：`cd frontend && npm run build`（buildId `2c75d6e0281b`，10 项）。

| 文件 | gzip 传输 | 原始 |
|---|---:|---:|
| `/assets/offline-DpUdszlD.js`（入口+游戏+存储） | 11,087 B | 30,726 B |
| `/assets/offline-CeWFqxwZ.css` | 4,406 B | 17,644 B |
| `/assets/offline-registration-9U6C3C84.js`（与主站共享 chunk） | 3,896 B | 10,059 B |
| `/offline.html` | 2,706 B | 8,338 B |
| `/offline/map/placeholder-scenic-map.svg` | 1,084 B | 2,676 B |
| `/offline/help/contacts.json` | 510 B | 1,095 B |
| `/assets/modulepreload-polyfill-B5Qt9EMX.js` | 399 B | 711 B |
| `/offline/map/map-meta.json` | 377 B | 457 B |
| `/offline-precache-manifest.json` | 318 B | 534 B |
| `/favicon.svg` | 179 B | 201 B |
| **合计** | **24,962 B ≈ 24.4 KB** | **72,441 B ≈ 70.7 KB** |
| `sw.js`（首次注册额外下载） | 1,657 B | 3,039 B |
| **离线包首次下载合计** | **≈ 26.6 KB** | ≈ 75.5 KB |

对照预算：≤1.0 MB 合格 / ≤500 KB 推荐 → **PASS（约为上限的 2.6%）**。
清单中**不含** `models/*.vrm`、`motions/*`、Element Plus/ECharts/Leaflet/Three 主站包与任何 API 响应（E2E 断言）。

---

## 4. 自动化测试结果

### 4.1 单元测试（`npm test`，node:test，零新增运行时依赖）

```
ℹ tests 26   ℹ pass 26   ℹ fail 0
```

覆盖：状态机全部阈值与恢复滞回、单飞/迟到响应、`/health` 响应校验、返回地址白名单、跳跃/碰撞/dt 钳制/确定性随机、存储 schema 与三级降级、电话 schema 与 `tel:` 白名单。

### 4.2 端到端（`npm run test:e2e`，生产构建 + 真实 Chromium + `context.setOffline`）

```
PASS   1540ms  OFF-01 首次在线访问主站后完成离线包准备
PASS      0ms  PERF-01 预缓存体积远低于 1MB 上限
PASS     78ms  OFF-02/03 断网后新标签页直接导航 /offline.html 仍可用
PASS    107ms  SAFE-02 断网打开地图，可缩放且无在线瓦片请求
PASS   1205ms  SAFE-08 打开地图时游戏自动暂停，关闭后恢复
PASS    416ms  SAFE-01/06 求助面板可见、号码可复制且未核验时不出现拨号按钮
PASS   1435ms  GAME-01 断网下点击画面开始并计分
PASS      2ms  OFF-07 离线时 /health 不会读到 Service Worker 伪造的缓存
PASS    475ms  OFF-05 删除关键缓存后不崩溃并明确提示未就绪
PASS   9771ms  NET-05/06 连续两次探针成功后出现返回提示，跑酷不被中断也不自动跳转
PASS     70ms  GAME-06 点击返回只跳转一次且落在白名单路径
PASS     43ms  OFF-04 从未在线准备时断网打开不会显示伪造的可用页面
PASS  22852ms  NET-02/03 主站持续不可达 15s 后出现进入离线伴游横幅，不自动跳转
PASS   8536ms  NET-09 主站可达但业务接口失败时不冒充设备离线
PASS     57ms  UI-01 360px 窄屏无横向溢出
PASS    201ms  REG-01 主站页面在离线组件接入后仍可渲染游客界面
16/16 PASS
```

**完整 E2E 演示链路（已自动执行）**：主站在线并完成离线包 → 断网 → 新标签页直接打开 `/offline.html` → 打开地图/求助、跑酷计分 → 断网下 `/health` 失败 → 删除关键缓存后重载显示“未就绪” → 恢复网络 → 两次探针确认后出现“网页服务已恢复”且不自动跳转 → 点击返回 `/tourist` 仅一次。

### 4.3 证据文件

- `docs/implementation/evidence/offline-home.jpg`（断网首屏：地图/求助大按钮、纸雕跑酷、离线使用提示）
- `docs/implementation/evidence/offline-game.jpg`（断网跑酷进行中：朱砂印章计分、墨线小人、石灯障碍）
- `docs/implementation/evidence/offline-map.jpg`（断网打开手卷式地图、放大后、未核验警示）
- `docs/implementation/evidence/offline-help.jpg`（求助面板：未核验徽标、复制号码、无拨号按钮）
- `docs/implementation/evidence/main-offline-banner.jpg`（主站持续不可达后的“进入离线伴游”纸卡横幅，未遮挡导览）
- 以上截图均为 390×844 @2x JPEG（quality 82）；构建日志：`[offline-sw] buildId=2c75d6e0281b 预缓存 10 项`（`/tmp/offline-build.log`，本文第 3 节为最终 dist 实测）

---

## 5. 验收矩阵逐项结论

### 5.1 离线 & 缓存（P0）

| ID | 结论 | 证据/说明 |
|---|---|---|
| OFF-01 | **PASS** | E2E：SW 激活且 `offline.html`/contacts/map 全部入 Cache 后才显示就绪 |
| OFF-02 | **PASS** | E2E：断网后点击入口/导航均进入离线页，无网络请求依赖 |
| OFF-03 | **PASS** | E2E：断网新标签页直接导航 + 刷新均可渲染游戏/地图/电话 |
| OFF-04 | **PASS** | E2E：全新上下文断网打开失败，未显示任何“已缓存”伪状态 |
| OFF-05 | **PASS** | E2E：删除 contacts 缓存后显示缺失文案 + “离线包未就绪”，不崩溃 |
| OFF-06 | **PARTIAL** | 设计为“新版 install 成功才 activate，激活后删旧缓存”，install 失败保留旧版；**未做双版本构建自动化**，需人工发版演练 |
| OFF-07 | **PASS** | E2E：离线 `fetch('/health')` 失败；SW 对 `/health`、`/api/**` 直接放行不缓存 |
| OFF-08 | **PARTIAL** | 地图/求助不依赖 rAF（独立模块）；E2E 覆盖“游戏运行中打开地图/求助”。**游戏抛错场景未自动化** |

### 5.2 网络状态机（P0）

| ID | 结论 | 证据 |
|---|---|---|
| NET-01 | PASS | 单测：单次失败 → `SUSPECT`，不切换 |
| NET-02 | PASS | E2E：≥15 s 后出现横幅，URL 不变 |
| NET-03 | PASS | E2E：网络在线、`/health` 被 abort → `DEGRADED` |
| NET-04 | PASS | 单测：一次成功只到 `RECOVERING` |
| NET-05 | PASS | E2E：两次成功（间隔 ≥3 s）后出现恢复提示 |
| NET-06 | PASS | E2E：恢复期间分数不回退、不跳转 |
| NET-07 | PASS | 单测：HTML/错误 JSON 判失败 |
| NET-08 | PASS | 单测：单飞 + stop 后迟到响应不覆盖 |
| NET-09 | PASS | E2E：`/api/**` 全失败但 `/health` 正常时无离线横幅 |
| NET-10 | PASS | 设计上主站与离线页均无自动跳转；E2E 验证单次返回。**多次往返网络抖动的长稳压测未自动化** |

### 5.3 地图与紧急求助（上线门槛，P0）

| ID | 结论 | 证据/说明 |
|---|---|---|
| SAFE-01 | PASS | E2E 390px/360px 首屏地图与求助按钮均可见，游戏在其下方 |
| SAFE-02 | PASS | E2E 断网打开、缩放生效、图片来自 `/offline/map/`，无瓦片域名请求 |
| SAFE-03 | **BLOCKED** | 无合法可离线分发的实测景区简图；占位图明确标注“未核验、不可用于救援”，`usableForEmergency:false` |
| SAFE-04 | **BLOCKED** | 现有号码仅来自后台默认配置，无来源/核验时间；界面显示“号码未核验” |
| SAFE-05 | **BLOCKED** | 因未核验，按规则**不渲染 `tel:` 按钮**；`tel:` 白名单逻辑已单测。真机拨号需人工验证 |
| SAFE-06 | PASS | E2E：未核验时只显示文本+复制+求助提示，无伪热线/伪坐标/伪路线 |
| SAFE-07 | PASS | 离线模块不引用 `useGeolocation`，页面无“你在这里”标记 |
| SAFE-08 | PASS | E2E：游戏运行中打开地图自动暂停，关闭后恢复 |

### 5.4 游戏、状态与兼容性（P1）

| ID | 结论 | 证据 |
|---|---|---|
| GAME-01 | PASS | E2E 点击计分；单测跳跃/碰撞/重开；空格监听对按钮焦点让行 |
| GAME-02 | **PARTIAL** | DPR 适配与 ResizeObserver 已实现、E2E 验证 360/390 无溢出；**未做高 DPI 像素级断言** |
| GAME-03 | PASS | 单测 dt 钳制；`visibilitychange` 暂停 + 恢复重置时间戳 |
| GAME-04 | **PARTIAL** | 存储单测覆盖持久化；**“跑完一局 → 刷新 → 最佳分保留”未在 E2E 中断言** |
| GAME-05 | PASS | 单测：IDB 不可用降级 localStorage；全不可用仍可玩并提示不保存 |
| GAME-06 | PASS | E2E：返回只发生一次且落在 `/tourist` |
| UI-01 | PASS | E2E 360px 无横向溢出；390px 首屏证据截图 |
| UI-02 | **BLOCKED** | 无 iOS Safari / 微信内置浏览器真机 |
| PERF-01 | PASS | 预缓存 gzip ≈22.4 KB，主站大包未入清单 |
| REG-01 | PASS | 主站构建成功、游客页渲染、控制台无致命错误；`ChatView` 仅 +2 行 |

---

## 6. 未覆盖 / 阻塞与复现路径

| 项 | 状态 | 需要什么才能关闭 |
|---|---|---|
| 景区应急电话核验 | **BLOCKED** | 运营方书面确认号码、适用景区、有效期；填入 `contacts.json` 并把 `status` 改 `verified`，重新构建 |
| 景区离线简图 | **BLOCKED** | 可合法离线分发的官方/自制核验 SVG；替换 `map-meta.json` 的 `file/status/source/license/verifiedAt` |
| 真机（iOS Safari / 微信 / 安卓） | **BLOCKED** | 真机手测清单：首访缓存、断网刷新、拨号、横竖屏、存储清理 |
| OFF-06 版本升级演练 | 未自动化 | 连续两次构建 + 发版脚本，验证旧缓存保留与切换 |
| GAME-02 高 DPI / GAME-04 刷新保留最佳分 | 未自动化 | 增加 Playwright 设备像素比与 IndexedDB 往返断言 |

`/health` 的跨域反代、真实 FastAPI 静态挂载未在本轮启动后端验证；E2E 使用行为对齐的静态测试服务器（`scripts/offline-test-server.mjs`），`GET /offline.html` 命中真实 dist 文件，不经过 SPA 回落。

---

## 7. 回归与影响面

- 修改的既有文件仅 4 个：`vite.config.js`（多入口/代理/插件/define）、`package.json`（新增 2 个脚本 + `playwright-core` devDependency）、`ChatView.vue`（+1 import、+1 组件标签）、`README.md`（新增说明）。
- 未改动：路由、ThreeAvatar、RAG/ASR/TTS、MapView 在线地图、管理端、后端接口。
- 主站新增一个共享 chunk（`offline-registration`）与底部横幅组件，仅在弱网时出现。

---

## 8. 最终报告

```text
基线分支与 SHA：master @ 80bd403233441032c4e5717742aa2c438b971cab
读取的代码映射/规范文件：无 AGENTS.md / CODE_MAP.md（已确认不存在）；
  实读 README.md、DESIGN.md、docs/superpowers/{plans,specs}、docs/design、
  frontend/src/{router,views/tourist,composables,constants,api}、backend/main.py
Worktree 路径与分支：../RuanJianBei-offline / feature/offline-companion
新增/修改文件：见本文第 1 节与第 7 节
网络状态机实现摘要：见本文第 2 节
离线预缓存清单与总下载体积（实测）：10 项，gzip 24,962 B + sw.js 1,657 B ≈ 26.6 KB
地图来源、许可、核验记录：无（BLOCKED）；仅提供明确标注的未核验占位示意图
求助电话来源、核验记录：无官方核验记录（BLOCKED）；来自景区后台默认配置，标记 unverified
单元测试 PASS/FAIL：26 PASS / 0 FAIL
Playwright E2E PASS/FAIL：16 PASS / 0 FAIL
实机测试 PASS/FAIL/BLOCKED：BLOCKED（无 iOS/微信/安卓真机）
主站回归 PASS/FAIL：PASS（构建成功、游客页渲染、无致命控制台错误）
本地提交 SHA：64b10b9（功能实现与测试；本文件的 SHA 回填为后续文档提交）
未完成/阻塞项与复现路径：见本文第 6 节
是否可以正式演示：是（游戏/地图交互/弱网切换/离线缓存闭环均已自动化验证）
是否可以对游客上线：否（应急电话与离线简图未核验；真机未验收）
```

---

## 9. 合并建议

1. 该分支可直接合入 `master`：改动面小、无后端依赖、所有既有功能未触碰。
2. 合入后需 **重新执行 `npm run build`**（离线清单含构建哈希，必须与线上产物一致）。
3. 上线前必须完成应急电话与离线地图的人工核验；在此之前页面会如实显示“未核验”，**不得对外宣传为官方救援入口**。
4. 主工作树存在与本需求无关的未提交改动（`.gitignore`、`README.md`、`evaluation/` 等），合并前请先确认基线。

---

## 10. 视觉重设计记录（v1.1）

### 10.1 参考与调研结论

| 参考 | 借鉴点 |
|---|---|
| **Tengami**（Nyamyam，纸片立体书） | 分层纸片山峦、纸边高光、低饱和的自然色阶（赭/黛/松/金） |
| **Alto's Odyssey**（Snowman） | 剪影视差层次、极简 HUD、“每一帧都是一张壁纸”的构图 |
| 移动端 HUD 设计通识 | 计分固定在左上、按钮锚定四角、扁平矢量+高对比在移动端最易读、避免装饰字体影响读分 |

### 10.2 设计决策

- **色板**：宣纸 `#F4EDDC`、纸卡 `#FBF6EA`、墨 `#242B26`、黛青 `#55685C`、松绿 `#6F8A72`、远山 `#C2CFBE`、朱砂 `#B4462F`（只用于求助、计分印章与警示）。
- **字体**：标题/数字用宋体（Songti SC / Noto Serif SC），正文与按钮用系统无衬线；数字统一 `tabular-nums`。
- **版式**：整页作为一张“纸卷”，顶部品牌印章 + 状态胶囊，安全入口为两枚 64px 纸签，跑酷装在纸卡里，追加“离线使用提示”填补长屏空白，桌面端收为居中纸页（不再拉伸留白）。
- **画布**：三层撕纸山脊（高斯峰 + 首尾等高无缝拼接 + 纸边高光/浅影）、朱砂日轮、纸云、归鸟、近景灌木、草簇与碎石；Q 版墨线小人（发髻/发簪/衣襟/腰带/双飘带 + 跑动摆臂）；障碍改为山石 / 石灯 / 枯松三种剪影。
- **浮层**：地图改成“手卷”（上下卷轴杆），求助改成“信笺”，未核验信息用朱砂左规线标注。
- **主站横幅**：同步改为纸卡 + 朱砂主按钮。

### 10.3 自检与迭代

- 用 Playwright 以 390×844 @2x、360×740、768×900、844×390（横屏）、1280×960 多种视口渲染截图，共迭代 5 轮（初版 → 加高山脊/放大角色 → 纸云/草地/叠纸阴影 → 游戏化布局与拇指区 → 模型放大与横屏双栏）。
- 检查项：首屏地图/求助可见且 ≥44px、无横向溢出、计分可读、`prefers-reduced-motion` 下停止视差与落叶、遮罩不拦截点击。
- 仅动视觉与交互层：`ConnectivityMonitor`、存储、Service Worker、URL/电话白名单、测试契约均未改；`WORLD` 尺寸/障碍尺寸调整后，26 项单测与 16 项 E2E 全部通过。
- 体积影响：预缓存 gzip 由 22.4 KB 增至 26.6 KB（仍为 1 MB 上限的 2.6%）。

### 10.4 v1.2 游戏化布局、模型放大与多端适配

**布局（依据“拇指区”研究结论重排）**

- 上方为信息区：品牌 + 网络/离线状态；游戏画面成为首屏主体（`clamp(190px, 38dvh, 320px)` 高，等比缩放、底部对齐，容器变高只增加天空，不拉伸地物）。
- 计分印章、最佳分、暂停/重开收进画面右上，HUD 不再占用独立一行。
- 主 CTA 只有一个：画面中央的圆形播放键（READY）/重玩键（GAME_OVER）/继续键（PAUSED）。
- 跳跃键固定在画面下方右侧的拇指区（64px），点击画面任意位置同样可跳；桌面端显示 `空格 / ↑ / W 跳跃 · P 暂停 · R 重开`。
- 景区地图与紧急求助移到游戏下方的拇指区，两枚 64px 纸签始终可见；离线提示改为可折叠 `<details>`，减少首屏噪音。
- 横屏（高度 ≤560px）切换为双栏：左侧游戏 + 跳跃键，右侧竖排地图/求助、提示与页脚。

**模型与障碍整体放大**

| 元素 | v1.1 | v1.2 | 变化 |
|---|---|---|---|
| 角色可视高度 | ≈58 世界像素 | ≈85（1.45× 绘制） | +46% |
| 山石 `rock` | 30×28 | 54×44 | +93% / +57% |
| 石灯 `sign` | 24×50 | 40×78 | +67% / +56% |
| 枯松 `crate` | 32×34 | 52×58 | +63% / +71% |
| 跳跃初速 / 重力 | -760 / 2200 | -790 / 2300 | 保证可跨越 78px 石灯 |
| 生成间隔 | 0.72–1.18s | 0.82–1.32s | 适配更大障碍的通过时间 |

碰撞盒随角色/障碍同步调整（角色 24×48），未出现“看着没碰到却判定碰撞”的偏差。

**多端与输入**

- 断点：≤380（小屏）、381–759（手机）、≥760（平板/桌面 640px 纸页）、≥1080（720px）、横屏双栏。
- 触控：画面 `touch-action: none`、`-webkit-tap-highlight-color: transparent`、跳跃键与播放键均为真实 `<button>`、点击/触摸均可跳跃、支持 `navigator.vibrate(8)` 轻震（不支持则静默）。
- 键盘与读屏：空格/↑/W 跳跃、P 暂停、R 重开；按钮均有 `aria-label`，状态文案通过 `aria-live` 播报。
- 安全区：页面与浮层使用 `env(safe-area-inset-*)`，避开 iPhone 底部手势条与灵动岛。
- `prefers-reduced-motion`：停止山体视差、飘叶与跑动摆动外的装饰运动。

