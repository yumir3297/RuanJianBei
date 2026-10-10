// 地图模块数据：景点演示坐标（GCJ-02 近似，非测绘数据）与热度模型输入。
// 正式版应通过高德地理编码/POI 检索替换坐标，客流接腾讯位置大数据 MCP。

export const LINGSHAN_CENTER = [31.4285, 120.0998];

export const MAP_ZONES = {
  qianshan: { label: "前山区", color: "#2d5a4b", capacity: 5200 },
  houshan: { label: "后山区", color: "#7a5230", capacity: 4800 },
  huqu: { label: "湖区", color: "#2f7d7d", capacity: 3000 },
  guangchang: { label: "广场区", color: "#8b6d2b", capacity: 4600 },
};

export const SPOT_COORDS = {
  灵山大佛: { lat: 31.4328, lng: 120.0996, heat: 95 },
  九龙灌浴: { lat: 31.429, lng: 120.0994, heat: 92 },
  降魔浮雕: { lat: 31.4298, lng: 120.0992, heat: 60 },
  阿育王柱: { lat: 31.4306, lng: 120.099, heat: 56 },
  百子戏弥勒: { lat: 31.4278, lng: 120.0998, heat: 64 },
  灵山梵宫: { lat: 31.43, lng: 120.1045, heat: 88 },
  五印坛城: { lat: 31.431, lng: 120.1058, heat: 78 },
  曼飞龙塔: { lat: 31.432, lng: 120.1048, heat: 54 },
  无尽意斋: { lat: 31.429, lng: 120.1052, heat: 45 },
  佛教文化博览馆: { lat: 31.4282, lng: 120.104, heat: 58 },
  菩提大道: { lat: 31.4258, lng: 120.101, heat: 62 },
  五灯湖: { lat: 31.4245, lng: 120.1025, heat: 66 },
  拈花广场: { lat: 31.4235, lng: 120.1015, heat: 58 },
  香月花街: { lat: 31.4228, lng: 120.103, heat: 52 },
  梵天花海: { lat: 31.4265, lng: 120.1035, heat: 55 },
  鹿鸣谷: { lat: 31.4275, lng: 120.1022, heat: 42 },
  灵山大照壁: { lat: 31.4218, lng: 120.0965, heat: 72 },
  佛足坛: { lat: 31.4244, lng: 120.0978, heat: 66 },
  五智门: { lat: 31.4256, lng: 120.0984, heat: 68 },
  五明桥: { lat: 31.4232, lng: 120.0972, heat: 70 },
  祥符禅寺: { lat: 31.4272, lng: 120.099, heat: 74 },
  拈花堂: { lat: 31.4208, lng: 120.0975, heat: 60 },
};

// 路线口语化节点 → 可定位景点映射
export const ROUTE_ALIASES = {
  南门入园: "拈花堂",
  胜境广场: "灵山大照壁",
  佛手广场: "佛足坛",
  杏坛广场: "祥符禅寺",
  佛前广场: "九龙灌浴",
  三圣殿: "佛教文化博览馆",
  灵山精舍: "无尽意斋",
  梵宫广场: "灵山梵宫",
  梵宫: "灵山梵宫",
  出口: "拈花堂",
};
