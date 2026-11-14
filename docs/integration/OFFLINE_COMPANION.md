# 离线陪游双端集成记录

## 来源与当前实现

来源为 Trae `feature/offline-companion`，基线 `0a5f77e`；同时纳入来源工作区未提交的页面、游戏、样式、键盘与 E2E 更新（未提交 patch 保存在集成工作目录之外的工作文件中）。原工作区未修改。此前来源的验收报告属于历史证据，并非本次结果。

游客端入口 `frontend/apps/tourist/offline.html`，页面使用 `frontend/src/offline/`，入口提示挂载在 `ChatView.vue`。游客 Vite 构建额外产生 `dist/tourist/offline.html`、`sw.js`、缓存清单及离线静态资料；`prepare-public.mjs` 只向游客公共目录复制 `public/offline/`。管理端没有接入离线功能。

游客开发服务器的 `/health` 代理及游客 Nginx 配置的 `/health` 转发为连通性探针提供同源后端；Service Worker、清单和离线页配置为不使用长缓存。构建版本包含固定 URL 的离线静态文件、worker、HTML 和 favicon 内容，使这些文件更新时生成不同的缓存版本。真实部署反向代理和实际访问尚需验证。

## 使用和边界

离线包须先联网完成准备。离线页提供游戏、离线示意图和求助信息；地图与电话的资料仍未核验，不能作官方救援依据。游戏/页面细节以代码和本次验证为准。Service Worker 的作用域与缓存更新见 [联网调研](RESEARCH.md)。

## 验证

- 本地用户界面端到端断网测试：执行 `npm run build` 后运行 `npm run test:offline-e2e`；可用 `PLAYWRIGHT_EXECUTABLE_PATH` 指定浏览器，`OFFLINE_EVIDENCE_DIR` 指定证据目录。2026-11-13 使用系统 Chrome 和本地静态测试服务器完成 16/16 项；含预缓存后断网打开、缺失关键缓存、网络恢复与返回。该测试使用 Playwright 模拟断网，并在关键缓存故障场景同步断开测试服务器，不能替代真机蜂窝网络。
- 本次离线源码接入后 `npm test`：240 通过（在新增离线缓存版本测试之前）；`node --test tests/offline-build.test.mjs` 通过；双端构建、应用依赖边界和构建边界通过。
- Service Worker 跨版本升级、生产反向代理及 iOS/微信/安卓真机尚未验收。手机、外部服务和已核验地图/联系方式是单独的验证条件。

2026-11-13：新增 `frontend/tests/e2e/offline-upgrade.e2e.mjs`，以游客构建产物的临时副本模拟第二版 worker、清单和合成求助数据，在本机 Chrome 两次通过：旧受控页面仍读旧数据；关闭旧页后新缓存激活、旧缓存清除；模拟断网后离线页可打开并读取新数据。脚本使用无业务脚本的测试页触发 worker 更新，第二版通过修改副本模拟，并非两次独立发布构建；不证明主站注册流程、更新失败恢复、生产代理或真机升级通过。运行前构建游客端，可指定 `PLAYWRIGHT_EXECUTABLE_PATH`，脚本只改临时目录。

2026-11-13（失败恢复）：`frontend/tests/e2e/offline-update-failure.e2e.mjs` 在真实游客主站注册后，以临时构建副本模拟新版缺失求助资料；本机 Chrome 两次观察到新 worker 安装失败，旧包仍可在模拟断网后打开离线页并读取求助资料。此检查未验证失败后恢复新版、两次独立构建、生产代理或真机，且求助资料仍是未核验的演示数据。
