<template>
  <div class="admin-layout" :class="{ 'login-layout': isLogin }">
    <aside v-if="!isLogin" class="admin-sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-title">灵山胜境</div>
        <div class="sidebar-subtitle">景区运营工作台</div>
      </div>
      <nav class="sidebar-nav" aria-label="管理端导航">
        <div v-for="group in adminLinkGroups" :key="group.label" class="sidebar-nav-group">
          <div class="sidebar-section-label">{{ group.label }}</div>
          <RouterLink v-for="item in group.items" :key="item.path" :to="item.path"
            class="sidebar-nav-link" :class="{ active: route.path === item.path }"
            :aria-current="route.path === item.path ? 'page' : undefined">
            <span class="sidebar-nav-icon"><el-icon><component :is="item.icon" /></el-icon></span>
            <span>{{ item.label }}</span>
          </RouterLink>
        </div>
      </nav>
      <footer v-if="touristAppUrl" class="sidebar-footer">
        <a class="sidebar-back-link" :href="touristAppUrl" target="_blank" rel="noopener noreferrer">
          <el-icon><ArrowLeft /></el-icon><span>打开游客端</span>
        </a>
      </footer>
    </aside>
    <main class="admin-main" id="admin-main"><RouterView /></main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import { DataLine, Document, Warning, Monitor, UserFilled, PictureFilled, ArrowLeft, TrendCharts } from "@element-plus/icons-vue";
import { touristAppUrl } from "../../src/utils/appLinks.js";

const route = useRoute();
const isLogin = computed(() => route.path === "/admin/login");
const adminLinkGroups = [
  { label: "工作台", items: [{ path: "/admin/dashboard", label: "总览", icon: DataLine }] },
  { label: "内容运营", items: [
    { path: "/admin/knowledge", label: "知识管理", icon: Document },
    { path: "/admin/blind-spots", label: "知识盲区", icon: Warning },
  ] },
  { label: "游客体验", items: [
    { path: "/admin/avatar", label: "数字人配置", icon: UserFilled },
    { path: "/admin/assets", label: "页面与素材", icon: PictureFilled },
  ] },
  { label: "运营分析", items: [
    { path: "/admin/analytics", label: "问答分析", icon: Monitor },
    { path: "/admin/experience-report", label: "游客反馈", icon: TrendCharts },
  ] },
];
</script>

<style scoped>
.admin-layout { display: flex; min-height: 100dvh; }
.admin-sidebar { flex: 0 0 216px; display: flex; flex-direction: column; height: 100dvh; box-sizing: border-box; }
.sidebar-nav { display: flex; flex-direction: column; }
.sidebar-nav-link, .sidebar-back-link { align-items: center; text-decoration: none; }
.sidebar-nav-icon { display: inline-flex; align-items: center; justify-content: center; flex: none; }
.sidebar-back-link { display: flex; gap: 8px; padding: 9px 10px; }
.admin-main { flex: 1; min-width: 0; overflow: auto; }
.login-layout .admin-main { padding: 0; }
@media (max-width: 900px) {
  .admin-layout { flex-direction: column; }
  .admin-sidebar { flex: 0 0 auto; height: auto; }
  .sidebar-nav { flex-direction: row; overflow-x: auto; }
  .sidebar-nav-group { display: contents; }
  .sidebar-footer { display: none; }
  .admin-main { overflow-x: hidden; }
}
</style>
