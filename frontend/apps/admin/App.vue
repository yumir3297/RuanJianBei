<template>
  <div class="admin-app">
    <aside v-if="!route.path.startsWith('/admin/login')" class="admin-sidebar">
      <div class="sidebar-brand">
        <div class="sidebar-eyebrow">AI DIGITAL GUIDE</div>
        <div class="sidebar-title">智能数字人导游</div>
        <div class="sidebar-subtitle">管 理 后 台</div>
      </div>
      <div class="sidebar-section-label">导航</div>
      <nav class="sidebar-nav">
        <RouterLink v-for="item in adminLinks" :key="item.path" :to="item.path" class="sidebar-nav-link">
          <el-icon><component :is="item.icon" /></el-icon><span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <footer class="sidebar-footer">
        <a v-if="touristAppUrl" class="sidebar-back-link" :href="touristAppUrl" target="_blank" rel="noopener noreferrer">打开游客端</a>
        <div class="sidebar-status"><span class="sidebar-status-dot"></span><span>管理端</span><span class="sidebar-version">独立应用</span></div>
      </footer>
    </aside>
    <main class="admin-main"><RouterView /></main>
  </div>
</template>

<script setup>
import { RouterLink, RouterView, useRoute } from "vue-router";
import { DataLine, Document, Warning, Monitor, UserFilled, PictureFilled, TrendCharts } from "@element-plus/icons-vue";
import { touristAppUrl } from "../../src/utils/appLinks.js";

const adminLinks = [
  { path: "/admin/dashboard", label: "总览", icon: DataLine },
  { path: "/admin/knowledge", label: "知识管理", icon: Document },
  { path: "/admin/blind-spots", label: "知识盲区", icon: Warning },
  { path: "/admin/analytics", label: "数据大屏", icon: Monitor },
  { path: "/admin/experience-report", label: "感受度报告", icon: TrendCharts },
  { path: "/admin/avatar", label: "数字人配置", icon: UserFilled },
  { path: "/admin/assets", label: "资源替换", icon: PictureFilled },
];
const route = useRoute();
</script>

<style scoped>
.admin-app{display:flex;min-height:100vh;background:#f6efe4}.admin-sidebar{position:sticky;top:0;display:flex;flex:0 0 240px;flex-direction:column;height:100vh;padding:16px 10px 12px;overflow:auto;background:linear-gradient(180deg,#1e1813,#15110d);color:#fff}.sidebar-brand{padding:10px 8px 16px;text-align:center;border-bottom:1px solid #d9a44133}.sidebar-eyebrow{font-size:9px;letter-spacing:.28em;color:#d9a441}.sidebar-title{margin-top:6px;font-family:serif;font-size:19px;color:#d9a441}.sidebar-subtitle{margin-top:4px;font-size:10px;color:#ffffff66;letter-spacing:.18em}.sidebar-section-label{padding:14px 8px 6px;color:#ffffff66;font-size:10px}.sidebar-nav{display:grid;gap:3px}.sidebar-nav-link{display:flex;align-items:center;gap:10px;padding:10px;color:#ffffffbd;text-decoration:none;font-size:13px;border-radius:4px}.sidebar-nav-link:hover,.sidebar-nav-link.router-link-active{background:#ffffff17;color:white}.sidebar-footer{margin-top:auto}.sidebar-back-link{display:block;padding:9px 10px;color:#d9a441;text-decoration:none;font-size:12px}.sidebar-status{display:flex;align-items:center;gap:7px;padding:10px;border:1px solid #d9a44124;font-size:10px;color:#62c487}.sidebar-status-dot{width:7px;height:7px;border-radius:50%;background:#2fa363}.sidebar-version{margin-left:auto;color:#ffffff66}.admin-main{flex:1;min-width:0;overflow:auto;padding:20px}@media(max-width:900px){.admin-sidebar{flex-basis:190px}.admin-main{padding:14px}}@media(max-width:640px){.admin-app{display:block}.admin-sidebar{position:static;width:100%;height:auto;padding:8px}.sidebar-brand,.sidebar-section-label,.sidebar-footer{display:none}.sidebar-nav{display:flex;overflow:auto}.sidebar-nav-link{flex:0 0 auto;padding:8px}}
</style>
