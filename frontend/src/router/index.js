import { createRouter, createWebHistory } from "vue-router";

import LandingPage from "../views/LandingPage.vue";
import HomePage from "../views/HomePage.vue";
import ChatView from "../views/tourist/ChatView.vue";
import ModeSelectView from "../views/tourist/ModeSelectView.vue";
import KnowledgeManage from "../views/admin/KnowledgeManage.vue";
import AvatarConfig from "../views/admin/AvatarConfig.vue";
import DisplayAssets from "../views/admin/DisplayAssets.vue";
import AnalyticsReport from "../views/admin/AnalyticsReport.vue";
import BlindSpotManage from "../views/admin/BlindSpotManage.vue";

import { useAuthStore } from "../stores/auth";

const Dashboard = () => import("../views/admin/Dashboard.vue");
const AdminLogin = () => import("../views/admin/AdminLogin.vue");

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
