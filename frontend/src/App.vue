<template>
  <div class="app-shell" :class="{ 'tourist-mode': isTouristRoute }">
    <header v-if="!isTouristRoute && !isFullBleedRoute && !isAdminRoute" class="topbar">
      <h1>灵山胜境 AI 数字导游</h1>
      <nav class="topbar-nav">
        <RouterLink to="/">开始游览</RouterLink>
        <RouterLink to="/admin/dashboard">运营管理</RouterLink>
      </nav>
    </header>

    <div v-if="isAdminRoute && !isFullBleedRoute" class="admin-layout">
      <aside class="admin-sidebar">
        <div class="sidebar-brand">
          <div class="sidebar-eyebrow">AI DIGITAL GUIDE</div>
          <div class="sidebar-title">智能数字人导游</div>
          <div class="sidebar-subtitle">管 理 后 台</div>
        </div>
        <div class="sidebar-section-label">导航</div>
        <nav class="sidebar-nav">
          <RouterLink
            v-for="item in adminLinks"
            :key="item.path"
            :to="item.path"
            class="sidebar-nav-link"
            :class="{ active: route.path === item.path }"
          >
            <span class="sidebar-nav-icon">
              <el-icon><component :is="item.icon" /></el-icon>
            </span>
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>
        <div class="sidebar-footer">
          <RouterLink to="/" class="sidebar-back-link">
            <el-icon><ArrowLeft /></el-icon>
            <span>返回首页</span>
          </RouterLink>
          <div class="sidebar-status">
            <span class="sidebar-status-dot"></span>
            <span>运行中</span>
            <span class="sidebar-version">v3.2</span>
          </div>
          <div class="sidebar-user">
            <span class="sidebar-avatar">管</span>
            <div>
              <div class="sidebar-user-name">系统管理员</div>
              <div class="sidebar-user-email">admin@lingshan.com</div>
            </div>
          </div>
        </div>
      </aside>
      <main class="admin-main">
        <RouterView />
      </main>
    </div>

    <main v-else :class="isTouristRoute ? 'tourist-shell' : isFullBleedRoute ? 'fullbleed-shell' : 'page-body'">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { DataLine, Document, Warning, Monitor, UserFilled, PictureFilled, ArrowLeft } from "@element-plus/icons-vue";
import { useAuthStore } from "./stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const isAdminRoute = computed(() => route.path.startsWith("/admin"));
const isTouristRoute = computed(() => route.path.startsWith("/tourist") || route.path === "/");
const isFullBleedRoute = computed(() => route.path === "/" || route.path === "/admin/login");

const adminLinks = [
  { path: "/admin/dashboard", label: "总览", icon: DataLine },
  { path: "/admin/knowledge", label: "知识管理", icon: Document },
  { path: "/admin/blind-spots", label: "知识盲区", icon: Warning },
  { path: "/admin/analytics", label: "数据大屏", icon: Monitor },
  { path: "/admin/avatar", label: "数字人配置", icon: UserFilled },
  { path: "/admin/assets", label: "资源替换", icon: PictureFilled },
];

function handleLogout() {
  authStore.logout();
  router.push("/admin/login");
}
</script>

<style scoped>
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

.fullbleed-shell {
  padding: 0;
  width: 100%;
  max-width: none;
  margin: 0;
  min-height: 100vh;
}

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

.topbar h1 {
  margin: 0 0 4px;
  font-family: "STKaiti", "KaiTi", "FangSong", serif;
  font-size: 27px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.topbar p {
  margin: 0;
  color: rgba(255, 255, 255, 0.68);
  font-family: "FangSong", "STFangsong", serif;
  letter-spacing: 0.16em;
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
  text-decoration: none;
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

.admin-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.admin-sidebar {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  width: 240px;
  border-right: 1px solid #332b23;
  background: linear-gradient(180deg, #1e1813 0%, #1a1510 40%, #15110d 100%);
  position: relative;
  overflow: hidden;
}

.admin-sidebar::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.06;
  background:
    radial-gradient(ellipse 70% 30% at 50% 0%, #d9a441 0%, transparent 70%),
    radial-gradient(ellipse 50% 40% at 80% 100%, var(--lingshan-green) 0%, transparent 60%);
}

.sidebar-brand {
  position: relative;
  z-index: 1;
  padding: 16px 14px 10px;
  border-bottom: 1px solid rgba(217, 164, 65, 0.12);
  margin-bottom: 4px;
  text-align: center;
}

.sidebar-eyebrow {
  font-size: 9px;
  font-weight: 500;
  color: #d9a441;
  letter-spacing: 0.28em;
  margin-bottom: 6px;
  opacity: 0.7;
}

.sidebar-title {
  font-size: 19px;
  font-family: "STKaiti", "KaiTi", serif;
  font-weight: 700;
  color: #d9a441;
  letter-spacing: 0.06em;
  line-height: 1.15;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
}

.sidebar-subtitle {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 4px;
  letter-spacing: 0.18em;
}

.sidebar-section-label {
  padding: 4px 16px 4px;
  font-family: "Georgia", serif;
  font-weight: 700;
  font-size: 9px;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.4);
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 0 10px;
}

.sidebar-nav-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: 2px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  text-decoration: none;
  transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease;
}

.sidebar-nav-link:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.sidebar-nav-link.active {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(51, 43, 35, 0.28);
  color: #fff;
}

.sidebar-nav-link.active .sidebar-nav-icon {
  background: rgba(255, 255, 255, 0.12);
}

.sidebar-nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.06);
  font-size: 12px;
  flex-shrink: 0;
}

.sidebar-footer {
  margin-top: auto;
  margin: auto 10px 12px;
}

.sidebar-back-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin-bottom: 8px;
  border: 1px solid rgba(217, 164, 65, 0.16);
  border-radius: 2px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 11px;
  text-decoration: none;
  transition: background 0.16s, color 0.16s, border-color 0.16s;
}

.sidebar-back-link:hover {
  background: rgba(217, 164, 65, 0.1);
  border-color: rgba(217, 164, 65, 0.3);
  color: #d9a441;
}

.sidebar-back-link .el-icon {
  font-size: 14px;
}

.sidebar-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(51, 43, 35, 0.4);
  border-radius: 2px;
  border: 1px solid rgba(217, 164, 65, 0.14);
  background: rgba(255, 255, 255, 0.03);
}

.sidebar-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 2px;
  background: #2fa363;
  box-shadow: 0 0 6px #2fa363;
  flex-shrink: 0;
}

.sidebar-status > span:nth-child(2) {
  font-size: 9px;
  color: #2fa363;
  font-weight: 600;
  letter-spacing: 0.06em;
}

.sidebar-version {
  margin-left: auto;
  font-size: 8px;
  color: rgba(255, 255, 255, 0.4);
}

.sidebar-user {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
}

.sidebar-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 2px;
  background: #c8922c;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.sidebar-user-name {
  font-size: 10px;
  font-weight: 600;
  color: #fff;
}

.sidebar-user-email {
  font-size: 8px;
  color: rgba(255, 255, 255, 0.45);
  margin-top: 1px;
}

.admin-main {
  flex: 1;
  min-width: 0;
  overflow: auto;
  background: #f6efe4;
  padding: 20px;
}

@media (max-width: 900px) {
  .topbar {
    padding: 20px;
  }
  .page-body {
    padding: 20px;
  }

  .admin-layout {
    flex-direction: column;
  }

  .admin-sidebar {
    width: 100%;
    flex-direction: row;
    height: auto;
    padding: 6px 10px;
    background: linear-gradient(90deg, #1e1813 0%, #1a1510 50%, #15110d 100%);
  }

  .sidebar-brand,
  .sidebar-section-label,
  .sidebar-footer {
    display: none;
  }

  .sidebar-nav {
    flex-direction: row;
    overflow-x: auto;
    gap: 2px;
    padding: 0;
  }

  .sidebar-nav-link {
    padding: 7px 12px;
    white-space: nowrap;
  }

  .admin-main {
    padding: 14px;
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
</style>
