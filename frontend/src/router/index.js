import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";

const LandingPage = () => import("../views/LandingPage.vue");
const HomePage = () => import("../views/HomePage.vue");
const ChatView = () => import("../views/tourist/ChatView.vue");
const ModeSelectView = () => import("../views/tourist/ModeSelectView.vue");
const Dashboard = () => import("../views/admin/Dashboard.vue");
const AdminLogin = () => import("../views/admin/AdminLogin.vue");
const KnowledgeManage = () => import("../views/admin/KnowledgeManage.vue");
const AvatarConfig = () => import("../views/admin/AvatarConfig.vue");
const DisplayAssets = () => import("../views/admin/DisplayAssets.vue");
const AnalyticsReport = () => import("../views/admin/AnalyticsReport.vue");
const BlindSpotManage = () => import("../views/admin/BlindSpotManage.vue");

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 };
  },
  routes: [
    {
      path: "/",
      name: "home",
      component: LandingPage,
    },
    {
      path: "/tourist/welcome",
      name: "tourist-welcome",
      component: HomePage,
    },
    {
      path: "/tourist/select",
      name: "tourist-mode-select",
      component: ModeSelectView,
    },
    {
      path: "/tourist",
      name: "chat",
      component: ChatView,
    },
    {
      path: "/admin/login",
      name: "admin-login",
      component: AdminLogin,
      meta: { skipAuth: true },
    },
    {
      path: "/admin/dashboard",
      name: "dashboard",
      component: Dashboard,
    },
    {
      path: "/admin/knowledge",
      name: "knowledge",
      component: KnowledgeManage,
    },
    {
      path: "/admin/avatar",
      name: "avatar",
      component: AvatarConfig,
    },
    {
      path: "/admin/assets",
      name: "assets",
      component: DisplayAssets,
    },
    {
      path: "/admin/analytics",
      name: "analytics",
      component: AnalyticsReport,
    },
    {
      path: "/admin/blind-spots",
      name: "blind-spots",
      component: BlindSpotManage,
    },
  ],
});

router.beforeEach((to, _from, next) => {
  if (to.path.startsWith("/admin") && !to.meta.skipAuth) {
    const authStore = useAuthStore();
    if (!authStore.isAuthenticated) {
      return next({ name: "admin-login", query: { redirect: to.fullPath } });
    }
  }
  next();
});

export default router;
