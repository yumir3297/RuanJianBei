import { createRouter, createWebHistory } from "vue-router";

const TouristView = () => import("../../src/views/tourist/TouristView.vue");

function guideRedirect(to, tool) {
  const query = { ...to.query };
  delete query.selector;
  delete query.index;
  if (tool) query.tool = tool;
  else delete query.tool;
  return { path: "/tourist", query };
}

export default createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/", redirect: "/tourist" },
    { path: "/tourist/welcome", redirect: (to) => guideRedirect(to) },
    { path: "/tourist/select", redirect: (to) => guideRedirect(to) },
    { path: "/tourist", name: "chat", component: TouristView },
    { path: "/tourist/explore", redirect: (to) => guideRedirect(to, "explore") },
    { path: "/tourist/map", redirect: (to) => guideRedirect(to, "map") },
    { path: "/tourist/routes", redirect: (to) => guideRedirect(to, "route") },
    { path: "/tourist/quiz", redirect: (to) => guideRedirect(to, "quiz") },
    { path: "/:pathMatch(.*)*", redirect: "/tourist" },
  ],
});
