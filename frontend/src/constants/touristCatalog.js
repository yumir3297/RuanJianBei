// Existing scenic, route, and question content shared by the in-page guide tools.

export const scenicSpots = [
  { name: "灵山大佛", emoji: "🗿", desc: "88米高青铜释迦牟尼佛像，灵山景区标志", zone: "qianshan", type: "foxiang", image: "/assets/slides/灵山大佛.png" },
  { name: "九龙灌浴", emoji: "🐉", desc: "大型动态音乐群雕，再现佛祖诞生盛景", zone: "qianshan", type: "foxiang", image: "/assets/slides/九龙灌浴.png" },
  { name: "降魔浮雕", emoji: "🪨", desc: "青铜浮雕艺术长墙，讲述佛陀修行故事", zone: "qianshan", type: "wenhua", image: "/assets/slides/降魔浮雕.png" },
  { name: "阿育王柱", emoji: "🪷", desc: "古印度风格石柱，铭刻阿育王经文", zone: "qianshan", type: "wenhua", image: "/assets/slides/阿育王柱_1.png" },
  { name: "百子戏弥勒", emoji: "😊", desc: "大型青铜雕塑群，弥勒与百名童子嬉戏", zone: "qianshan", type: "foxiang", image: "/assets/slides/百子戏弥勒.png" },
  { name: "灵山梵宫", emoji: "🏰", desc: "佛教艺术殿堂，世界佛教论坛永久会址", zone: "houshan", type: "simiao", image: "/assets/slides/灵山梵宫.png" },
  { name: "五印坛城", emoji: "🏔️", desc: "藏传佛教风格建筑，金顶辉煌庄严", zone: "houshan", type: "simiao", image: "/assets/slides/五印坛城.png" },
  { name: "曼飞龙塔", emoji: "🕌", desc: "南传佛教风格白塔群，异域风情浓郁", zone: "houshan", type: "wenhua", image: "/assets/slides/曼飞龙塔.png" },
  { name: "无尽意斋", emoji: "🍵", desc: "禅意茶道空间，静心品味人生", zone: "houshan", type: "simiao", image: "/assets/slides/无尽意斋.png" },
  { name: "佛教文化博览馆", emoji: "🔔", desc: "动态升降佛塔，佛教科技艺术融合", zone: "houshan", type: "wenhua", image: "/assets/slides/佛教文化博览馆.png" },
  { name: "菩提大道", emoji: "🌳", desc: "景观步道，两侧菩提树绿荫如盖", zone: "huqu", type: "ziran", image: "/assets/slides/菩提大道.png" },
  { name: "五灯湖", emoji: "🌊", desc: "风景如画的湖面，波光粼粼", zone: "huqu", type: "ziran", image: "/assets/slides/五灯湖.png" },
  { name: "拈花广场", emoji: "🌸", desc: "湖畔集散广场，莲花造型铺装", zone: "huqu", type: "ziran", image: "/assets/slides/沾化广场.png" },
  { name: "香月花街", emoji: "🏘️", desc: "古色古香的商业步行街", zone: "huqu", type: "ziran", image: "/assets/slides/香月花街.png" },
  { name: "梵天花海", emoji: "🌺", desc: "壮观的花海景观，四季换景", zone: "huqu", type: "ziran", image: "/assets/slides/梵天花海_1.png" },
  { name: "鹿鸣谷", emoji: "🦌", desc: "生态自然谷地，鹿鸣声声", zone: "huqu", type: "ziran", image: "/assets/slides/鹿鸣谷.png" },
  { name: "灵山大照壁", emoji: "🧱", desc: "入口照壁浮雕，镌刻灵山胜境四字", zone: "guangchang", type: "wenhua", image: "/assets/slides/灵山大照壁.png" },
  { name: "佛足坛", emoji: "🦶", desc: "佛足迹石刻，信众朝拜祈福之地", zone: "guangchang", type: "wenhua", image: "/assets/slides/佛足坛.png" },
  { name: "五智门", emoji: "🚪", desc: "牌坊式山门，五门象征五智", zone: "guangchang", type: "wenhua", image: "/assets/slides/五智门.png" },
  { name: "五明桥", emoji: "🌉", desc: "汉白玉石拱桥，横跨香水海", zone: "guangchang", type: "foxiang", image: "/assets/slides/五明桥.png" },
  { name: "祥符禅寺", emoji: "🏯", desc: "千年古刹，灵山佛教文化发源地", zone: "guangchang", type: "simiao", image: "/assets/slides/祥符禅寺.png" },
  { name: "拈花堂", emoji: "⛩️", desc: "景区入口广场，开启灵山之旅", zone: "guangchang", type: "wenhua", image: "/assets/slides/拈花堂.png" },
];

export const areaSubNav = [
  { key: "qianshan", label: "前山区", icon: "⛰️", count: 5 },
  { key: "houshan", label: "后山区", icon: "🏔️", count: 5 },
  { key: "huqu", label: "湖区", icon: "🌊", count: 6 },
  { key: "guangchang", label: "广场区", icon: "🏛️", count: 6 },
];

export const typeSubNav = [
  { key: "foxiang", label: "佛像建筑", icon: "🗿", count: 4 },
  { key: "ziran", label: "自然景观", icon: "🌳", count: 6 },
  { key: "simiao", label: "寺庙殿堂", icon: "🏯", count: 4 },
  { key: "wenhua", label: "文化展馆", icon: "🏛️", count: 8 },
];

export const PRESET_ROUTES = [
  {
    id: "history-culture",
    title: "历史文化爱好者路线",
    category: "官方推荐",
    duration_label: "6小时深度游",
    tags: ["历史文化", "深度体验", "佛教艺术"],
    spots: ["南门入园", "灵山大照壁（华夏第一壁）", "胜境广场", "佛手广场（天下第一掌）", "祥符禅寺（千年古刹历史讲解）", "杏坛广场", "佛前广场", "灵山大佛（佛教造像艺术解析）", "灵山梵宫（佛教艺术殿堂深度游）", "五印坛城（藏传佛教文化体验）", "三圣殿（佛教历史文化展示）", "出口"],
    guide: "灵山大照壁全长39.8米，最高处7米，由深浮雕花岗石拼块贴面而成，中间是一幅以\u201C灵山胜境\u201D为主题的大型浮雕。祥符禅寺重点讲解玄奘法师与\u201C小灵山\u201D的渊源，古井与银杏的历史故事，江南第一钟的文化意义。灵山大佛解析佛像手印的佛教含义，216级台阶的文化寓意（108烦恼与108愿望），青铜铸造工艺的历史与现代科技的结合。",
    features: "在祥符禅寺参与撞钟祈福，聆听12.8吨重的江南第一钟敲响，感受佛教文化的庄严与神圣。在梵宫欣赏《吉祥颂》演出，体验全息投影、水雾等现代科技与佛教文化的完美融合。"
  },
  {
    id: "nature-scenery",
    title: "自然风光爱好者路线",
    category: "官方推荐",
    duration_label: "5小时全景游",
    tags: ["自然风光", "太湖景观", "园林艺术"],
    spots: ["南门入园", "佛足坛", "九龙灌浴（观赏表演）", "菩提大道（欣赏太湖风光）", "灵山大佛（登顶俯瞰全景）", "曼飞龙塔（园林景观）", "灵山精舍（禅意园林）", "梵宫广场", "出口"],
    guide: "菩提大道两侧近百棵从印度引进的正宗菩提树形成天然拱廊，介绍两侧景观植物的佛教文化意义。灵山大佛重点讲解选址的地理优势，俯瞰太湖、马山半岛的绝佳视角，感受人与自然的完美统一。曼飞龙塔介绍傣族佛教建筑风格，园林景观设计理念。",
    features: "在九龙灌浴接取祈福圣水，寓意吉祥安康，同时欣赏水幕与阳光交织出的七彩佛光。在灵山大佛平台拍摄太湖日落，金色阳光洒在大佛身上，佛光普照，与太湖波光粼粼的水面交相辉映。"
  },
  {
    id: "family-kids",
    title: "亲子家庭路线",
    category: "官方推荐",
    duration_label: "4小时轻松游",
    tags: ["亲子互动", "轻松体验", "寓教于乐"],
    spots: ["南门入园", "九龙灌浴（观赏动态表演）", "佛手广场（摸\u201C天下第一掌\u201D）", "百子戏弥勒（亲子互动）", "梵宫（欣赏艺术作品）", "五印坛城（体验藏式文化）", "出口"],
    guide: "九龙灌浴用生动语言讲述释迦牟尼诞生的故事，让孩子理解佛教文化中的慈悲精神，解释\u201C九龙吐水\u201D的传说与\u201C花开见佛\u201D的仪式感。百子戏弥勒介绍雕塑中孩童的不同形态，引导孩子感受\u201C皆大欢喜\u201D的生活态度。梵宫简化艺术术语，重点介绍色彩、造型等直观元素，激发孩子的艺术兴趣。",
    features: "参与\u201C抱佛脚\u201D亲子活动，让孩子在家长的陪伴下登顶大佛，感受大佛的宏伟气势，培养勇气与探索精神。在梵宫圣坛观看互动表演《吉祥颂》，通过全息投影、水雾等现代科技，让孩子直观感受佛陀修行成佛的故事。"
  },
  {
    id: "quick-tour",
    title: "省力快捷游",
    category: "半日精选",
    duration_label: "2-2.5小时速览",
    tags: ["省力", "快捷", "核心景点"],
    spots: ["灵山大照壁", "五明桥", "佛足坛", "五智门", "九龙灌浴", "灵山大佛", "佛教文化博览馆", "灵山梵宫"],
    guide: "介绍照壁全长39.8米、赵朴初题字由来，在此快速合影后继续前行。简单解说五门六柱象征五方五佛与六度波罗蜜，穿过此门意味着正式踏入禅意圣地。讲解释迦牟尼诞生时花开见佛、九龙沐浴的故事，景观总高27.2米，太子佛鎏金高7.2米。",
    features: "在五智门下拍摄大佛与中轴线同框照；观赏九龙灌浴表演，接取九龙圣水祈求吉祥安康。聚焦入口区、九龙灌浴、大佛和梵宫四大核心，全程步行距离约2-3公里。"
  },
  {
    id: "half-day-elite",
    title: "半日精华游",
    category: "半日精选",
    duration_label: "3.5-4小时全景",
    tags: ["半日游", "精华覆盖", "灵活节奏"],
    spots: ["灵山大照壁", "五明桥", "佛足坛", "五智门", "菩提大道", "九龙灌浴", "降魔浮雕", "阿育王柱", "百子戏弥勒", "祥符禅寺", "灵山大佛", "佛教文化博览馆", "灵山梵宫", "五印坛城", "曼飞龙塔"],
    guide: "大照壁的赵朴初题字奠定佛教基调，五明桥的五种智慧引导游客从凡俗踏入禅境。长约250米的朝圣步道，两侧近百棵菩提树形成天然拱廊。九龙灌浴是全景区最震撼的动态景观，大型音乐群雕总高27.2米。",
    features: "在菩提大道林荫拱廊中漫步，感受佛陀悟道之地的氛围。在九龙灌浴观赏震撼表演后，接取祈福圣水。以灵活节奏串联入口区、中轴区、大佛区、滨湖区四大区域各取精华。"
  },
  {
    id: "photo-tour",
    title: "拍照出片游",
    category: "主题体验",
    duration_label: "3小时精选",
    tags: ["摄影", "拍照打卡", "视觉体验"],
    spots: ["灵山大照壁", "五明桥", "佛足坛", "九龙灌浴", "降魔浮雕", "百子戏弥勒", "灵山大佛", "灵山梵宫", "五印坛城", "曼飞龙塔"],
    guide: "全长39.8米、高7米的青石照壁，清晨光线从太湖方向斜射，鎏金大字在晨光中熠熠生辉。五座汉白玉石拱桥并列横跨香水海，可利用多桥并列的纵深层次拍摄。九龙灌浴莲花铜雕缓缓绽放、九条飞龙同时喷出数十米水柱，注意拍摄设备防水。",
    features: "清晨入园，利用晨光在灵山大照壁拍摄第一帧。在九龙灌浴抓拍花开见佛与九龙喷水的震撼瞬间。灵山胜境汇集汉传、藏传、南传三大语系佛教建筑，一处拍摄三种风格。"
  },
  {
    id: "sunset-zen",
    title: "夕阳禅意游",
    category: "特色路线",
    duration_label: "2.5小时落日线",
    tags: ["夕阳", "禅意", "光影"],
    spots: ["灵山梵宫", "五印坛城", "曼飞龙塔", "无尽意斋", "灵山大佛", "祥符禅寺", "百子戏弥勒", "阿育王柱", "降魔浮雕", "九龙灌浴", "菩提大道", "五智门", "佛足坛", "五明桥", "灵山大照壁"],
    guide: "下午入园后先从梵宫开始，此时上午团队游客基本离开，场馆内部人流较少。从梵宫步行至香水海湖心岛的五印坛城，108个纯铜转经筒构成小布达拉宫的独特视觉。无尽意斋是隐藏在山林间的赵朴初先生纪念馆，以其北京西城区故居为原型复刻。",
    features: "下午入园后先参观梵宫，避开上午人流高峰。在无尽意斋了解赵朴初先生与灵山的深厚渊源。一反常规游览顺序，日落前抵达灵山大佛，暮色中的景区静谧深远。"
  }
];

export const QUESTION_DATA = {
  scenic: {
    label: "景点介绍",
    subs: {
      buddha_statues: {
        label: "佛像建筑",
        icon: "🗿",
        cards: [
          { icon: "🗿", title: "灵山大佛", desc: "世界上最高的青铜立佛", query: "请介绍灵山大佛的高度、建造年份和工艺特色" },
          { icon: "🐉", title: "九龙灌浴", desc: "大型动态群雕表演", query: "请介绍灵山九龙灌浴的寓意和表演内容" },
          { icon: "🪨", title: "阿育王柱", desc: "灵山标志性建筑", query: "请介绍灵山阿育王柱的历史由来和象征意义" },
          { icon: "🕌", title: "五印坛城", desc: "藏传佛教艺术圣殿", query: "请介绍灵山五印坛城的设计风格和建筑特色" },
        ],
      },
      nature: {
        label: "自然景观",
        icon: "🌿",
        cards: [
          { icon: "⛰️", title: "灵山胜境", desc: "太湖畔的佛教圣境", query: "灵山胜境有哪些著名的自然景观值得游览" },
          { icon: "🌊", title: "太湖风光", desc: "山水相依的绝美景致", query: "灵山与太湖的地理关系是怎样的，有哪些观景点" },
          { icon: "🌸", title: "灵山花海", desc: "四季花卉美景", query: "灵山景区有哪些特色花卉和园林景观" },
        ],
      },
      temples: {
        label: "寺庙殿堂",
        icon: "🏛️",
        cards: [
          { icon: "🏯", title: "祥符禅寺", desc: "千年古刹的历史传承", query: "请介绍祥符禅寺的历史沿革和重要地位" },
          { icon: "🛕", title: "大雄宝殿", desc: "灵山核心礼佛场所", query: "灵山大雄宝殿供奉了哪些佛像，有什么建筑特色" },
          { icon: "📚", title: "藏经楼", desc: "珍藏佛经的宝库", query: "灵山藏经楼收藏了哪些珍贵佛教经典和文物" },
        ],
      },
      exhibitions: {
        label: "文化展馆",
        icon: "🏤",
        cards: [
          { icon: "🏤", title: "灵山梵宫", desc: "佛教艺术殿堂", query: "灵山梵宫的建筑风格和内部艺术装饰有什么特点" },
          { icon: "🖼️", title: "佛教博物馆", desc: "佛教文化艺术展示", query: "灵山佛教博物馆展示了哪些珍贵文物和艺术品" },
          { icon: "🎭", title: "曼飞龙塔", desc: "南传佛教风格地标", query: "请介绍灵山曼飞龙塔的建筑风格和文化内涵" },
        ],
      },
    },
  },
  photo: {
    label: "文化典故",
    subs: {
      buddhism: {
        label: "佛教文化",
        icon: "🙏",
        cards: [
          { icon: "🙏", title: "佛教东传", desc: "佛教入华的历史", query: "佛教是什么时候传入中国的，经历了怎样的传播过程" },
          { icon: "🪷", title: "释迦牟尼", desc: "佛祖一生的事迹", query: "释迦牟尼佛一生的主要事迹和成道经过是什么" },
          { icon: "🧘", title: "禅宗智慧", desc: "禅宗文化精髓", query: "中国禅宗的核心思想和发展历史是怎样的" },
          { icon: "📿", title: "菩萨信仰", desc: "四大菩萨道场", query: "中国佛教四大菩萨分别代表什么，道场在哪里" },
        ],
      },
      history: {
        label: "历史人文",
        icon: "📜",
        cards: [
          { icon: "📜", title: "玄奘西行", desc: "大唐高僧取经之路", query: "玄奘法师西行取经的路线和主要贡献是什么" },
          { icon: "🏔️", title: "灵山溯源", desc: "灵山佛教名山地位", query: "灵山在中国佛教历史上的地位和渊源是什么" },
          { icon: "👤", title: "鉴真东渡", desc: "中日文化交流使者", query: "鉴真大师东渡日本弘扬佛法的经历和影响是什么" },
        ],
      },
      architecture: {
        label: "建筑艺术",
        icon: "🏗️",
        cards: [
          { icon: "🏗️", title: "佛塔形制", desc: "中国佛塔的建筑演变", query: "中国佛塔有哪几种经典形制，各有什么特点" },
          { icon: "🗿", title: "石刻艺术", desc: "中国石窟造像艺术", query: "中国四大石窟是什么，各有什么艺术特色" },
          { icon: "🏛️", title: "寺庙布局", desc: "汉传佛寺的空间规划", query: "传统汉传佛教寺庙的轴线布局和空间规划是怎样的" },
        ],
      },
      general: {
        label: "综合问答",
        icon: "🎯",
        cards: [
          { icon: "🎯", title: "灵山之最", desc: "灵山顶尖纪录盘点", query: "灵山景区获得了哪些国家级和世界级荣誉" },
          { icon: "🏅", title: "世界纪录", desc: "灵山创下的世界纪录", query: "灵山大佛创下了哪些世界纪录和行业认证" },
          { icon: "🧩", title: "趣味冷知识", desc: "灵山鲜为人知的趣闻", query: "灵山景区有哪些鲜为人知的趣味冷知识和传说故事" },
        ],
      },
    },
  },
  area: {
    label: "游览贴士",
    subs: {
      best_time: {
        label: "最佳时间",
        icon: "📅",
        cards: [
          { icon: "📅", title: "最佳季节", desc: "什么时候来最美", query: "灵山景区的最佳游览季节是什么时候，各季节有什么特色" },
          { icon: "🎆", title: "特色活动", desc: "季节性节庆活动", query: "灵山有哪些特色的季节性活动和节庆庆典" },
          { icon: "🌅", title: "朝暮胜景", desc: "日出日落的灵山", query: "灵山景区什么时间段游览效果最好，有什么推荐路线" },
        ],
      },
      transport: {
        label: "交通指南",
        icon: "🚗",
        cards: [
          { icon: "🚌", title: "公交出行", desc: "88路·乐游2号线", query: "从无锡火车站乘坐88路公交车到灵山胜境怎么走；乐游2号线从无锡中央车站到灵山胜境经过哪些站点（龙观路-吟苑公园-河坪口-荣巷-梅园-华藏-拈花湾-灵山胜境）" },
          { icon: "🅿️", title: "停车指南", desc: "自驾停车全攻略", query: "灵山景区的停车设施和收费标准是什么，自驾从高速陆区马山收费口如何到达" },
          { icon: "🛣️", title: "自驾路线", desc: "上海·南京·杭州方向", query: "自驾到灵山胜境怎么走：上海出发走沪宁高速-无锡北枢纽-锡宜高速-陆区马山收费口；南京出发走沪宁高速-无锡北枢纽-锡宜高速-陆区马山收费口；杭州出发走宁杭高速-锡宜高速-陆区马山收费口" },
        ],
      },
      tips: {
        label: "游览须知",
        icon: "📋",
        cards: [
          { icon: "📋", title: "开放时间", desc: "夏令时·冬令时", query: "灵山景区各场馆开放时间：夏令时（5.1-10.31）售票7:00-17:30，梵宫9:00-18:00，珍宝馆9:30-16:30，五印坛城9:00-18:00(16:30后仅开放一楼)，无尽意斋/香积厨9:00-16:30，佛博馆8:30-17:30，万佛殿8:30-16:30；冬令时（11.1-次年4.30）售票7:00-17:00，梵宫9:00-17:30，珍宝馆9:30-16:30，五印坛城9:00-17:30(16:30后仅开放一楼)，无尽意斋/香积厨9:00-16:30，佛博馆8:30-17:00，万佛殿8:30-16:30" },
          { icon: "🎫", title: "门票须知", desc: "价格和优惠政策", query: "灵山景区门票价格：成人当天票¥160(1名成人)，双人当天票¥320(2名成人)，亲子当天票¥240(1大1小)，家庭当天票¥400(2大1小)。半价票适用条件：身高1.4米以上、6周岁(不含)-18周岁(含)儿童、60-69周岁老年人凭身份证、全日制本科在校生凭学生证。未成年人无身份证可用家长身份证购票，入园携带户口本或照片核验。入园需携带购票时使用的本人二代身份证原件刷证入园" },
          { icon: "🧥", title: "参观礼仪", desc: "佛门礼仪指南", query: "参观佛教圣地灵山有什么着装要求和文化礼仪" },
        ],
      },
      experience: {
        label: "特色体验",
        icon: "✨",
        cards: [
          { icon: "🍜", title: "素斋体验", desc: "佛门素食文化", query: "灵山素斋有什么特色菜品和饮食文化" },
          { icon: "✍️", title: "禅修体验", desc: "静心修行活动", query: "灵山有没有抄经、禅修等静心体验项目" },
          { icon: "🛍️", title: "文创纪念", desc: "灵山特色文创", query: "灵山有哪些特色文创产品和纪念品可以购买" },
        ],
      },
    },
  },
  type: {
    label: "景区概况",
    subs: {
      history: {
        label: "历史沿革",
        icon: "📖",
        cards: [
          { icon: "📖", title: "建寺溯源", desc: "灵山寺的历史起源", query: "灵山寺始建于哪个朝代，经历了怎样的兴衰变迁" },
          { icon: "🏗️", title: "景区建设", desc: "灵山大佛景区发展", query: "灵山大佛景区是什么时候规划建设的，开发历程是怎样的" },
          { icon: "🔔", title: "重大纪事", desc: "灵山的重要历史时刻", query: "灵山景区建设发展过程中有哪些重大历史事件和里程碑" },
        ],
      },
      location: {
        label: "地理位置",
        icon: "📍",
        cards: [
          { icon: "📍", title: "地理坐标", desc: "灵山具体位置", query: "灵山景区位于无锡市的哪个位置，周边交通如何" },
          { icon: "📐", title: "规模数据", desc: "景区占地面积", query: "灵山景区的总占地面积和主要场馆分布是怎样的" },
        ],
      },
      honors: {
        label: "荣誉成就",
        icon: "🏆",
        cards: [
          { icon: "🏆", title: "5A级景区", desc: "国家最高等级认证", query: "灵山景区是什么时候被评为国家5A级旅游景区的" },
          { icon: "🌟", title: "城市名片", desc: "无锡文化符号", query: "灵山被称为无锡的什么文化名片，有哪些代表性荣誉" },
        ],
      },
      culture: {
        label: "文化价值",
        icon: "💎",
        cards: [
          { icon: "💎", title: "佛教地位", desc: "中国佛教名山地位", query: "灵山在中国当代佛教界有什么重要地位和影响力" },
          { icon: "🌏", title: "国际影响", desc: "世界佛教交流平台", query: "灵山在国际佛教文化交流中扮演什么角色" },
        ],
      },
    },
  },
};
