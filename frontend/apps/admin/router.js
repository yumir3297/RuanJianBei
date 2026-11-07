import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../../src/stores/auth.js";

const Dashboard = () => import("../../src/views/admin/Dashboard.vue");
const AdminLogin = () => import("../../src/views/admin/AdminLogin.vue");
const KnowledgeManage = () => import("../../src/views/admin/KnowledgeManage.vue");
const AvatarConfig = () => import("../../src/views/admin/AvatarConfig.vue");
const DisplayAssets = () => import("../../src/views/admin/DisplayAssets.vue");
const AnalyticsReport = () => import("../../src/views/admin/AnalyticsReport.vue");
const ExperienceReport = () => import("../../src/views/admin/ExperienceReport.vue");
const BlindSpotManage = () => import("../../src/views/admin/BlindSpotManage.vue");

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/", redirect: "/admin/dashboard" },
    { path: "/admin/login", name: "admin-login", component: AdminLogin, meta: { skipAuth: true } },
    { path: "/admin/dashboard", name: "dashboard", component: Dashboard },
    { path: "/admin/knowledge", name: "knowledge", component: KnowledgeManage },
    { path: "/admin/avatar", name: "avatar", component: AvatarConfig },
    { path: "/admin/assets", name: "assets", component: DisplayAssets },
    { path: "/admin/analytics", name: "analytics", component: AnalyticsReport },
    { path: "/admin/experience-report", name: "experience-report", component: ExperienceReport },
    { path: "/admin/blind-spots", name: "blind-spots", component: BlindSpotManage },
    { path: "/:pathMatch(.*)*", redirect: "/admin/dashboard" },
  ],
});

router.beforeEach((to) => {
  if (to.path.startsWith("/admin") && !to.meta.skipAuth && !useAuthStore().isAuthenticated) {
    return { name: "admin-login", query: { redirect: to.fullPath } };
  }
});

export default router;
