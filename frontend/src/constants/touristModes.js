/**
 * 游客端统一页面的模式定义。
 * 原来的「模式选择页 + 四个独立页面」在这里合并为一份配置：
 * 四种模式共用同一个页面外壳，通过缩放切换在其中来回迁移。
 */
export const TOURIST_MODE_CONTEXT = Symbol("tourist-mode-context");

export const TOURIST_MODES = [
  {
    id: "guide",
    title: "数字人导游",
    description: "与虚拟导游实时对话 · AI 语音互动 · 身临其境的景点讲解与个性化导览服务",
    themeColor: "#c4964c",
    path: "/tourist",
  },
  {
    id: "explore",
    title: "景点探索",
    description: "热门景点一览 · 特色文化深度解读 · 拍照识景 · 发现景区每一个角落的故事",
    themeColor: "#2d8a6e",
    path: "/tourist/explore",
  },
  {
    id: "route",
    title: "智能路线",
    description: "基于你的时间与兴趣智能推荐后端预设路线 · 最优游览路径推荐 · 不错过每一处精华",
    themeColor: "#b84c3b",
    path: "/tourist/routes",
  },
  {
    id: "quiz",
    title: "智慧问答",
    description: "文化典故 · 建筑美学 · 历史知识 · 随问随答，满足你的每一份好奇心",
    themeColor: "#4a6d8c",
    path: "/tourist/quiz",
  },
];

export const DEFAULT_TOURIST_MODE = "guide";

export function modeIdFromPath(path) {
  const matched = TOURIST_MODES.find((mode) => mode.path === path);
  return matched ? matched.id : DEFAULT_TOURIST_MODE;
}

export function modeIndex(modeId) {
  const index = TOURIST_MODES.findIndex((mode) => mode.id === modeId);
  return index < 0 ? 0 : index;
}
