<template>
  <div class="app-shell" :class="{ 'tourist-mode': isTouristRoute }">
    <header v-if="!isTouristRoute && !isFullBleedRoute" class="topbar">
      <h1>灵山胜境 AI 数字导游</h1>
      <nav class="topbar-nav">
        <RouterLink to="/">开始游览</RouterLink>
        <RouterLink to="/admin/dashboard">运营管理</RouterLink>
      </nav>
    </header>

    <main :class="isTouristRoute ? 'tourist-shell' : isFullBleedRoute ? 'fullbleed-shell' : 'page-body'">
      <nav v-if="isAdminRoute && !isTouristRoute && !isFullBleedRoute" class="admin-nav">
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
        <button type="button" class="admin-nav-link admin-nav-logout" @click="handleLogout">
          <span>退出</span>
        </button>
      </nav>
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink, RouterView, useRoute, useRouter } from "vue-router";
import { DataLine, Document, Warning, Monitor, UserFilled, PictureFilled } from "@element-plus/icons-vue";
import { useAuthStore } from "./stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const isAdminRoute = computed(() => route.path.startsWith("/admin"));
const isTouristRoute = computed(() => route.path.startsWith("/tourist") || route.path === "/");
const isFullBleedRoute = computed(() => route.path === "/" || route.path === "/admin/login");

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
  min-height: 44px;
  white-space: nowrap;
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
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  font: inherit;
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

  .admin-nav-spacer {
    display: none;
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
