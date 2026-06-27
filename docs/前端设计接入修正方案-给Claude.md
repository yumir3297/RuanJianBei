# 前端接入修正方案 — App.vue 顶栏恢复

> **问题**：上一版执行方案中，`App.vue` 的 scoped style 被错误改写，导致管理后台顶栏从深绿渐变变成白色，后台页面视觉崩溃。
>
> **原因**：原方案"修改顶栏颜色"的指令不够精确——旅游页面需要新风格，但管理后台的顶栏和布局应该原样保留。
>
> **本次修改范围**：只改 `App.vue` 一个文件，不改 `style.css`、旅游页面、Vue Router、stores。

---

## 边界规则（最重要）

```
┌─────────────────────────────────────────────────────┐
│  旅游端 (/ /tourist/*)       管理端 (/admin/*)       │
│  ──────────────────         ──────────────          │
│  新风格：                   原风格（不动）：           │
│  · 数字人居中               · 深绿渐变顶栏 + 白字     │
│  · 梵宫模糊背景             · 白色卡片内容区           │
│  · 温润纸面色调             · admin-nav 横向导航      │
│  · Topbar 由各页自行渲染     · 原 layout 完全保留     │
└─────────────────────────────────────────────────────┘
```

---

## 修改文件

**只改一个文件**：`d:\桌面\软件杯\frontend\src\App.vue`

---

## 第一步：还原 `<template>`

当前 `App.vue` 的 `<template>` 缺少了旅游端/管理端的顶栏区分逻辑。替换为：

```html
<template>
  <div class="app-shell" :class="{ 'tourist-mode': isTouristRoute }">
    <header v-if="!isTouristRoute" class="topbar">
      <div class="brand">
        <h1>灵山胜境 AI 数字导游</h1>
      </div>
      <nav class="topbar-nav">
        <RouterLink to="/">开始游览</RouterLink>
        <RouterLink to="/admin/dashboard">运营管理</RouterLink>
      </nav>
    </header>

    <main :class="isTouristRoute ? 'tourist-shell' : 'page-body'">
      <nav v-if="isAdminRoute && !isTouristRoute" class="admin-nav">
        <RouterLink
          v-for="item in adminLinks"
          :key="item.path"
          :to="item.path"
          class="admin-nav-link"
          :class="{ active: route.path === item.path }"
        >
          <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </RouterLink>
        <span class="admin-nav-spacer" />
        <a class="admin-nav-link admin-nav-logout" @click="handleLogout">
          <span>退出</span>
        </a>
      </nav>
      <RouterView />
    </main>
  </div>
</template>
```

**说明**：
- 旅游端（`isTouristRoute === true`）：**不显示 `<header class="topbar">`**，三个旅游页面各自在自己的 scoped style 中用 `<header class="home-top">` / `<header class="mode-top">` / `<header class="tourist-top">` 渲染轻量标题栏
- 管理端（`isTouristRoute === false`）：显示原先的深绿色 `.topbar`，样式不变

---

## 第二步：还原 `<style scoped>`

当前 `App.vue` 的 scoped style 已被改写，需要完全替换为原来 + 少量修正：

```css
.app-shell.tourist-mode {
  background: var(--lingshan-paper);
}

.tourist-shell {
  padding: 0;
  width: 100%;
  max-width: none;
  margin: 0;
  background: var(--lingshan-paper);
  min-height: 100vh;
}

/* ===== 管理端顶栏：保持原有深绿渐变风格 ===== */
.topbar {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 20px max(32px, calc((100vw - 1480px) / 2));
  border-bottom: 1px solid rgba(255, 255, 255, 0.16);
  background:
    linear-gradient(108deg, rgba(42, 75, 58, 0.98), rgba(75, 102, 78, 0.95)),
    var(--lingshan-green-deep);
  color: #fff;
  box-shadow: 0 10px 30px rgba(46, 66, 53, 0.13);
}

.topbar::after {
  position: absolute;
  right: 12%;
  bottom: 0;
  width: 260px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(244, 218, 176, 0.75), transparent);
  content: "";
}

.topbar h1 {
  margin: 0 0 4px;
  font-family: "STKaiti", "KaiTi", "FangSong", serif;
  font-size: 27px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.topbar-nav {
  display: flex;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
}

.topbar-nav a {
  padding: 9px 14px;
  border: 1px solid transparent;
  border-radius: 999px;
  color: rgba(255, 255, 255, 0.74);
  transition: color 160ms ease, border-color 160ms ease, background 160ms ease;
}

.topbar-nav a:hover,
.topbar-nav a.router-link-active {
  border-color: rgba(255, 255, 255, 0.28);
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.brand {
  display: flex;
  align-items: center;
}

/* ===== 管理端内容区 ===== */
.page-body {
  width: min(100%, 1544px);
  margin: 0 auto;
  padding: 28px 32px 48px;
}

.admin-nav {
  display: flex;
  gap: 4px;
  padding: 12px 0 0;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 20px;
  overflow-x: auto;
}

.admin-nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: 10px 10px 0 0;
  color: #64748b;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 160ms, background 160ms;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}

.admin-nav-link:hover {
  color: var(--lingshan-green-deep);
  background: var(--lingshan-green-light);
}

.admin-nav-link.active {
  color: var(--lingshan-green-deep);
  background: var(--lingshan-green-light);
  border-bottom-color: var(--lingshan-gold);
}

.admin-nav-spacer {
  flex: 1;
}

.admin-nav-logout {
  cursor: pointer;
}

.admin-nav-logout:hover {
  color: #dc2626;
  background: #fef2f2;
}

@media (max-width: 900px) {
  .topbar {
    padding: 20px;
  }

  .page-body {
    padding: 20px;
  }
}

@media (max-width: 560px) {
  .topbar {
    align-items: flex-start;
    flex-direction: column;
    padding: 16px 18px;
  }

  .topbar h1 {
    font-size: 23px;
  }

  .topbar-nav {
    width: 100%;
  }

  .topbar-nav a {
    flex: 1;
    text-align: center;
  }

  .page-body {
    padding: 16px 14px 32px;
  }
}
```

---

## 第三步：`<script setup>` 无需改动

当前 `App.vue` 的 `<script setup>` 是正确的，**保持不动**。

```js
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { DataLine, Document, Warning, Monitor, UserFilled, PictureFilled } from "@element-plus/icons-vue";
import { useAuthStore } from "./stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const isAdminRoute = computed(() => route.path.startsWith("/admin"));
const isTouristRoute = computed(() => route.path.startsWith("/tourist") || route.path === "/");

const adminLinks = [
  { path: "/admin/dashboard", label: "总览", icon: DataLine },
  { path: "/admin/knowledge", label: "知识库", icon: Document },
  { path: "/admin/blind-spots", label: "知识盲区", icon: Warning },
  { path: "/admin/analytics", label: "数据大屏", icon: Monitor },
  { path: "/admin/avatar", label: "数字人配置", icon: UserFilled },
  { path: "/admin/assets", label: "资源替换", icon: PictureFilled },
];

function handleLogout() {
  authStore.logout();
  router.push("/admin/login");
}
```

---

## 不动的文件清单（绝对不要改）

以下文件已经在上一轮正确改造，**本次不要碰**：

| 文件 | 状态 |
|------|------|
| `style.css` | CSS 变量已更新，兼容原变量名，全局可用 |
| `views/HomePage.vue` | 新设计已生效 |
| `views/tourist/ModeSelectView.vue` | 新设计已生效 |
| `views/tourist/ChatView.vue` | 新设计已生效 |
| `views/admin/AdminLogin.vue` | 原样完好 |
| `views/admin/Dashboard.vue` | 原样完好 |
| `views/admin/KnowledgeManage.vue` | 原样完好 |
| `views/admin/BlindSpotManage.vue` | 原样完好 |
| `views/admin/AnalyticsReport.vue` | 原样完好 |
| `views/admin/AvatarConfig.vue` | 原样完好 |
| `views/admin/DisplayAssets.vue` | 原样完好 |
| `router/index.js` | 无需改动 |
| `components/ThreeAvatar.vue` | 无需改动 |

---

## 执行验证

修改 `App.vue` 后，运行 `npm run dev`，逐项检查：

- [ ] 打开首页 `/`：数字人居中 + 梵宫模糊背景 + 呼吸 CTA，**没有深绿色顶栏**（旅游端正确行为）
- [ ] 点击「开始游览」→ `/tourist/select`：数字人居中 + 选择卡片
- [ ] 选择后 → `/tourist`：数字人居中 + 对话 + 底部输入栏
- [ ] 打开 `/admin/dashboard`：**深绿色渐变顶栏** + 白色内容区 + admin-nav 导航
- [ ] 打开 `/admin/knowledge`：顶栏保持一致
- [ ] 打开 `/admin/login`：登录框正常显示
- [ ] 打开 `/admin/analytics`：数据大屏正常
- [ ] 从管理端顶栏点击「开始游览」→ 回到首页

---

*本修正方案只涉及 App.vue 一个文件，不影响其他任何已完成的改造。*
