# 2026-06-22 Three.js 数字人替换 4A 验收结论与修复建议（交 Claude）

## 1. 验收范围

本次按 `4A` 验收，目标不是“所有 Live2D 清理完毕”，而是先确认以下事项是否成立：

1. 游客端主展示数字人已经切到 `ThreeAvatar`。
2. 游客端不再依赖旧的 Live2D 运行时判断作为主路径。
3. Three.js 数字人能吃到 `preset / visemeTimeline / speechProgress / speechSyncActive`。
4. 当前激活的数字人配置能真实影响游客端，而不是只存在于本地浏览器缓存。

结论：**当前版本不建议通过 4A 验收。**

补充说明：

1. `frontend` 的 `vite build` 能通过，说明目前不是“项目构建已损坏”。
2. 问题主要集中在游客端接线层、配置源统一、以及后台激活逻辑，而不是 Three.js 组件完全不可用。

## 2. 当前结论

目前代码已经有明显进展：

1. `ThreeAvatar` 已经接入 `preset / visemeTimeline / speechProgress / speechSyncActive`。
2. 口型时间线逻辑在 `ThreeAvatar` 内已经存在，不是空壳。
3. `useModelManager` 已经切换到 `monk / hanfu / modern` 这套 preset 语义。

但 4A 仍然卡在以下几个阻塞点。

## 3. 阻塞问题

### P0-1 游客端默认不会稳定走 Three.js 主路径

文件：

1. `frontend/src/views/tourist/ChatView.vue`
2. `frontend/src/composables/useModelManager.js`

现状：

1. 游客端模板仍然是：
   - `ThreeAvatar` 仅在 `is3DModel` 为真时渲染。
   - 否则走 `Live2DAvatar`。
2. `DEFAULT_MODEL_KEY` 现在已经等于 `monk`。
3. 但 `is3DModel` 仍然按旧逻辑判断 `modelKey === "3d"`。

结果：

1. 默认配置下，游客端不会自然进入 Three.js 主路径。
2. 这不是“代码没清理干净”那么简单，而是主入口判断已经和现有 preset 体系脱节。

关键位置：

1. `frontend/src/views/tourist/ChatView.vue:22-39`
2. `frontend/src/views/tourist/ChatView.vue:340-346`
3. `frontend/src/composables/useModelManager.js:22-25`

### P0-2 Live2D 回退分支已不再是安全兼容路径

文件：

1. `frontend/src/components/Live2DAvatar.vue`
2. `frontend/src/composables/useModelManager.js`

现状：

1. `Live2DAvatar` 仍然会调用 `modelManager.switchModel(modelKey)`。
2. 但 `useModelManager` 现在的 `switchModel()` 已经按 preset 工作，不再返回真实的 Live2D 模型实例。
3. 也就是说，游客端一旦误走 `Live2DAvatar` 分支，结果大概率不是“继续显示旧模型”，而是空白、空对象或异常状态。

关键位置：

1. `frontend/src/components/Live2DAvatar.vue:101-127`
2. `frontend/src/composables/useModelManager.js:81-105`

### P1-1 游客端仍然只读 localStorage，没有接入后端“当前激活配置”

文件：

1. `frontend/src/views/tourist/ChatView.vue`
2. `frontend/src/api/admin.js`
3. `backend/app/api/admin.py`

现状：

1. 管理页保存时会调用后端激活接口。
2. 但游客端没有读取 `/admin/avatar-configs/active`。
3. 游客端仍然只从 `localStorage` 读 `a5-avatar-config-v1`。

结果：

1. “保存并同步到游客端”在真实链路上并不成立。
2. 这个行为只对当前浏览器、当前设备近似有效。
3. 换设备、换浏览器、清缓存之后，游客端未必拿到后台当前激活配置。

关键位置：

1. `frontend/src/views/tourist/ChatView.vue:339-346`
2. `frontend/src/api/admin.js:33-40`
3. `backend/app/api/admin.py:195-222`

### P1-2 管理页保存时激活的后端配置 id 可能是错的

文件：

1. `frontend/src/views/admin/AvatarConfig.vue`

现状：

1. `remoteConfigId` 只在页面初次加载时记录“当前激活配置”的 id。
2. 用户后续切换到别的角色卡片时，这个 id 没有同步更新。
3. `handleSave()` 仍然调用 `saveAvatarConfig(remoteConfigId.value)`。

结果：

1. 前端界面看起来像是选中了新的角色。
2. 但真正发给后端激活的，可能还是最初加载的那条配置。

关键位置：

1. `frontend/src/views/admin/AvatarConfig.vue:161-167`
2. `frontend/src/views/admin/AvatarConfig.vue:178-182`
3. `frontend/src/views/admin/AvatarConfig.vue:189-205`

### P1-3 管理页把 `model_path` 直接当 `selectedModel` 使用，映射已错位

文件：

1. `frontend/src/views/admin/AvatarConfig.vue`
2. `frontend/src/composables/useModelManager.js`
3. `backend/app/db/bootstrap.py`

现状：

1. 后端种子数据保存的是：
   - `preset:monk`
   - `preset:hanfu`
   - `preset:modern`
2. 管理页加载远端数据时，直接把 `remote.model_path` 赋值给 `selectedModel`。
3. 同时 `selectedIs3D` 还在检查 `.runtime === "3d"`，但当前 preset 定义里已经没有这个字段。

结果：

1. 管理页预览判断会跑偏。
2. 角色选择和后端数据语义不再对齐。

关键位置：

1. `backend/app/db/bootstrap.py:14-35`
2. `frontend/src/views/admin/AvatarConfig.vue:138-140`
3. `frontend/src/views/admin/AvatarConfig.vue:167-170`
4. `frontend/src/composables/useModelManager.js:1-25`

### P2-1 游客端显示文案仍然沿用旧角色 key

文件：

1. `frontend/src/views/tourist/ChatView.vue`

现状：

1. `guideDisplayName` 仍然只认识 `3d / chitose / hibiki / haru`。
2. 当前 preset 是 `monk / hanfu / modern`。

结果：

1. 即使后续渲染链路修好，角色展示名称也会回退或不准确。

关键位置：

1. `frontend/src/views/tourist/ChatView.vue:348-350`

## 4. 建议修改内容

下面这部分是建议 Claude 直接执行的改法，按顺序做会最稳。

### A. 先把游客端彻底收口到 ThreeAvatar

目标：

1. `ChatView.vue` 不再用旧的 `"3d"` 逻辑判断主路径。
2. 游客端在 `!avatarError` 时直接渲染 `ThreeAvatar`。
3. `Live2DAvatar` 至少在游客页不再参与主渲染。

建议动作：

1. 删除游客页模板中的 `Live2DAvatar` 分支。
2. 移除 `is3DModel` 计算逻辑。
3. `ThreeAvatar` 始终吃：
   - `preset`
   - `emotion`
   - `is-speaking`
   - `speech-progress`
   - `speech-sync-active`
   - `viseme-timeline`
4. `AvatarDisplay` 仅保留为真正的兜底错误态。

最小目标：

1. 默认 `monk` 配置刷新页面后，游客端就显示 Three.js 数字人。

### B. 把游客端配置源从“本地缓存优先”改为“后端激活配置优先”

目标：

1. 游客端真实读取后端当前激活配置。
2. `localStorage` 只作为降级兜底，而不是唯一事实来源。

建议动作：

1. 在游客端增加对 `fetchAvatarConfig()` 的调用。
2. 读取到 `model_path` 后，用 `modelPathToPreset()` 转成前端 preset key。
3. 将游客端当前配置统一为：
   - `preset`
   - `voiceType`
   - 其他确有必要的展示字段
4. 保留 localStorage 作为接口失败时的 fallback，但优先级放到后面。

注意：

1. 不建议继续让游客端依赖 `modelKey === "3d"` 这种旧形态字段。

### C. 管理页不要再把“选中角色”和“初始激活 id”混在一起

目标：

1. 用户选择哪个 preset，就激活对应哪条后端配置。
2. 不能继续使用初始页面加载时的 `remoteConfigId` 作为唯一写回 id。

建议动作：

1. 管理页改为拉取 `/admin/avatar-configs` 列表，而不是只拿 active。
2. 通过 `model_path <-> preset` 建立映射关系。
3. 选中 `monk / hanfu / modern` 时，能找到对应配置记录的 `id`。
4. `handleSave()` 调用 `saveAvatarConfig(targetConfigId)`，其中 `targetConfigId` 来自当前选中 preset 的映射结果。

如果你想少改后端：

1. 当前后端已有 `GET /admin/avatar-configs` 和 `PUT /admin/avatar-configs/{id}/activate`。
2. 这已经足够完成“选中 preset -> 激活对应配置”的闭环。
3. 本轮不一定必须新增 patch/update 接口。

### D. 管理页预览逻辑改成和 preset 体系一致

目标：

1. 管理页预览不再依赖旧 runtime 判断。
2. 管理页预览与游客端保持同一种渲染组件。

建议动作：

1. 预览区直接使用 `ThreeAvatar`。
2. `selectedIs3D` 可以删除，或者改为恒真并最终删掉。
3. `selectedModel` 建议重构为 `selectedPreset` 为主，避免再出现 `preset:monk` 被塞进 `selectedModel` 的混用问题。

### E. 同步修正文案与小型映射残留

建议动作：

1. 将 `guideDisplayName` 改成基于 `monk / hanfu / modern`。
2. 清理游客页和管理页中所有仍然依赖：
   - `3d`
   - `chitose`
   - `hibiki`
   - `haru`
   的展示和判断逻辑。

## 5. 推荐实施顺序

建议按下面顺序改，风险最低：

1. 先改游客页渲染分支，只保留 `ThreeAvatar` 主路径。
2. 再接游客端远端激活配置读取，并把 `model_path` 正规映射到 preset。
3. 再修管理页列表加载和“选中 preset -> 激活正确 id”的关系。
4. 最后统一清理旧 key、旧判断、旧文案。

## 6. 本轮最小通过标准

只要满足下面几点，我认为 4A 就可以通过：

1. 游客页不再导入或渲染 `Live2DAvatar` 作为主数字人。
2. 默认激活配置为 `preset:monk` 时，刷新游客页能直接看到 Three.js 数字人。
3. 后台切换 `monk / hanfu / modern` 后，游客页刷新能反映当前激活角色。
4. 口型参数仍然从 `speechProgress + visemeTimeline` 驱动，没有回退成单纯静态嘴巴。
5. `npm run build` 继续通过。

## 7. 非阻塞项

以下问题建议后续继续收尾，但不一定阻塞 4A：

1. `frontend/index.html` 里仍然保留了 Live2D CDN 脚本。
2. `Live2DAvatar.vue` 和 Live2D 依赖尚未彻底删除。
3. 前端打包产物 chunk 仍然偏大，属于后续优化项。

## 8. 给 Claude 的一句话执行建议

请优先把“游客端数字人主路径”和“后台激活配置到游客端的真实生效链路”修通，再处理 Live2D 彻底清理；当前阻塞 4A 的不是 ThreeAvatar 组件本身，而是旧字段和旧分支仍在控制入口。
