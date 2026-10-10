import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";

// Every visitor entry opens one persistent guide; legacy routes open its tools.
const TouristView = () => import("../views/tourist/TouristView.vue");
const Dashboard = () => import("../views/admin/Dashboard.vue");
const AdminLogin = () => import("../views/admin/AdminLogin.vue");
const KnowledgeManage = () => import("../views/admin/KnowledgeManage.vue");
const AvatarConfig = () => import("../views/admin/AvatarConfig.vue");
const DisplayAssets = () => import("../views/admin/DisplayAssets.vue");
const AnalyticsReport = () => import("../views/admin/AnalyticsReport.vue");
const ExperienceReport = () => import("../views/admin/ExperienceReport.vue");
const BlindSpotManage = () => import("../views/admin/BlindSpotManage.vue");

function guideRedirect(to, tool) {
  const query = { ...to.query };
  delete query.selector;
  delete query.index;
  if (tool) query.tool = tool;
  else delete query.tool;
  return { path: "/tourist", query };
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 };
  },
  routes: [
    {
      path: "/",
      name: "home",
      redirect: "/tourist",
    },
    {
      path: "/tourist/welcome",
      name: "tourist-welcome",
      redirect: (to) => guideRedirect(to),
    },
    {
      path: "/tourist/select",
      name: "tourist-mode-select",
      redirect: (to) => guideRedirect(to),
    },
    {
      path: "/tourist",
      name: "chat",
      component: TouristView,
    },
    {
      path: "/tourist/explore",
      name: "tourist-explore",
      redirect: (to) => guideRedirect(to, "explore"),
    },
    {
      path: "/tourist/map",
      name: "tourist-map",
      redirect: (to) => guideRedirect(to, "map"),
    },
    {
      path: "/tourist/routes",
      name: "tourist-routes",
      redirect: (to) => guideRedirect(to, "route"),
    },
    {
      path: "/tourist/quiz",
      name: "tourist-quiz",
      redirect: (to) => guideRedirect(to, "quiz"),
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
      path: "/admin/experience-report",
      name: "experience-report",
      component: ExperienceReport,
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
