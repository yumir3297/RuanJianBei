# 数字人（Avatar）完善 — 任务书（Claude）

> 日期：2026-06-18
> E3 已完成后端，现在补前端配置页 + 动画打磨

---

## 当前状态

后端 AvatarConfig 已完成（Codex 做的）：
- 数据库表 `avatar_configs`：name / model_path / voice_type / is_active / preview_url
- 种子数据 3 条（"僧袍法师" / "汉服导游" / "现代导游"）
- 3 个 API 端点：列表 / 获取当前激活 / 切换激活

前端状态：
- `components/AvatarDisplay.vue`：SVG 头像 + 6 种状态动画，已接入 ChatView
- `composables/useAvatar.js`：6 状态机 + SSE avatar 事件处理
- `views/admin/AvatarConfig.vue`：**空壳**（el-result 占位，只显示一行提示文字）
- `api/admin.js`：**没有 avatar 相关 API 函数**

---

## 任务 1：AvatarConfig 前端配置页（P0）

### 目标

把 `/admin/avatar` 从占位信息页升级为可用的数字人配置管理页面。

### 需要展示的内容

**顶部**：当前激活的数字人卡片（大卡片风格，显示名称、声线、状态标签）

**下方**：所有可用的数字人预设列表（el-table 或卡片网格）：
| 名称 | 声线类型 | 状态 | 操作 |
|------|---------|------|------|
| 僧袍法师 | male_calm | 当前激活 | 按钮灰掉 |
| 汉服导游 | female_warm | 未激活 | "切换为此形象"按钮 |
| 现代导游 | male_enthusiastic | 未激活 | "切换为此形象"按钮 |

**声线中文映射**：
- male_calm → 沉稳男声
- female_warm → 温柔女声
- male_enthusiastic → 热情男声

### API（在 api/admin.js 中新增）

```js
export async function fetchAvatarConfigs() {
  const { data } = await http.get("/admin/avatar-configs");
  return data;
}

export async function fetchActiveAvatarConfig() {
  const { data } = await http.get("/admin/avatar-configs/active");
  return data;
}

export async function activateAvatarConfig(id) {
  const { data } = await http.put(`/admin/avatar-configs/${id}/activate`);
  return data;
}
```

### 后端返回结构

```json
{
  "id": 1,
  "name": "僧袍法师",
  "model_path": "monk",
  "preview_url": "",
  "voice_type": "male_calm",
  "is_active": true
}
```

### 交互

1. 进入页面 → 加载配置列表 → 显示当前激活项
2. 点击"切换为此形象" → PUT 请求 → 刷新列表 → 显示成功消息
3. 激活成功后原激活项的标签变为"未激活"，新激活项标签变为"当前激活"
4. 三种状态处理：loading（el-skeleton）、error（el-alert）、空列表（el-empty）

---

## 任务 2：Avatar 动画打磨（P1）

当前 Avatar 的嘴巴动画只有一个通用开合（`mouthTalk` 0.25s），没有区分不同音节的口型。

### 目标

把单一的口腔开合动画升级为基础 viseme 系统。

**不需要真实 TTS viseme 数据**——当前 stub TTS 返回的 `viseme_text` 是空字符串。在真实 TTS 接入前，可以用一个基于时间的简单策略。

### 实现方式

在 `AvatarDisplay.vue` 中，给 mouth 组件增加几个基础口型 class：

```css
/* 闭嘴休息 */
.mouth.idle { d: path("M38 62 Q50 68 62 62"); }

/* 小开口（"i"/"e"类音） */
.mouth.open-small { d: path("M34 58 Q50 70 66 58"); }

/* 大开口（"a"类音） */
.mouth.open-wide { d: path("M30 54 Q50 78 70 54"); }

/* 圆唇（"o"/"u"类音） */
.mouth.rounded { d: path("M32 58 Q50 74 68 58"); }
```

`useAvatar.js` 在 `speaking` 状态下，用一个定时器循环切换口型 class：

```js
const visemeCycle = ['idle', 'open-small', 'open-wide', 'rounded', 'open-small', 'idle'];
let visemeIndex = 0;
let visemeTimer = null;

function startSpeakingAnimation() {
  visemeIndex = 0;
  visemeTimer = setInterval(() => {
    currentViseme.value = visemeCycle[visemeIndex % visemeCycle.length];
    visemeIndex++;
  }, 150); // 每 150ms 切换一个口型
}

function stopSpeakingAnimation() {
  if (visemeTimer) { clearInterval(visemeTimer); visemeTimer = null; }
  currentViseme.value = 'idle';
}
```

AvatarDisplay.vue 的嘴巴根据 `currentViseme` 切换 CSS class。

**注意**：当真实 TTS 接入后（有 phoneme 时间戳），把 `startSpeakingAnimation` 替换为 `handleAvatarEvent` 中读取真实 viseme 数据的逻辑即可，不影响其他地方。

### 保持现有功能

- 6 种状态动画都保留不动（idle/listening/thinking/speaking/happy/apology）
- happy/apology 状态下的嘴巴不管 viseme，用现有的 smile/frown path
- 腮红、光环、弹跳、鞠躬动画全部保留

---

## 文件清单

```
frontend/src/api/admin.js              ← 新增 3 个 avatar API 函数
frontend/src/views/admin/AvatarConfig.vue  ← 重写（从占位到真实配置页）
frontend/src/composables/useAvatar.js  ← 新增 viseme 循环 + 定时器
frontend/src/components/AvatarDisplay.vue ← 嘴巴组件支持 4 种口型 class
```

## 不碰的文件

- ❌ 不修改后端任何代码
- ❌ 不修改数据库中已有数据
- ❌ 不碰 SSE 事件格式
- ❌ 不增加 npm 依赖

## 验证方式

```powershell
cd frontend
npm.cmd run build
```

1. 打开 `/admin/avatar` → 看到 3 个数字人预设卡片，有一个高亮为"当前激活"
2. 点击另一个的"切换为此形象" → 标签切换
3. 回到游客端 → 发送问题 → Avatar 说话时嘴巴有 4 种口型交替变化
