<template>
  <section class="tourist-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>
    <button type="button" class="back-btn" @click="handleBack">← 返回</button>
    <div class="top-right"><span class="top-brand">灵山智能导览系统</span>
    </div>
    <div class="tourist-stage">
      <div class="chat-center">
        <div class="top-caption">
          <span class="crowd-indicator" data-level="green"><span class="crowd-dot"></span>当前景区人数：舒适</span>
          <span class="caption-kicker">{{ avatarDisplaySubtitle }} · 路线规划</span>
          <span class="caption-weather" v-if="!weatherCaption">智能路线 · 灵山导览</span>
          <span class="caption-weather caption-weather-live" v-else>{{ weatherCaption }}</span>
        </div>
        <div class="avatar-stage">
          <ThreeAvatar v-if="!avatarError" :preset="avatarConfig.modelKey" :emotion="avatar.currentEmotion.value" :is-speaking="avatarState==='speaking'||avatarState==='happy'" :speech-progress="speechProgress" :speech-elapsed-ms="speechElapsedMs" :speech-duration-ms="speechDurationMs" :speech-sync-active="activeAudioSegments>0" :viseme-timeline="visemeTimeline" :avatar-state="avatarState" :action="avatar.currentAction.value" :action-key="avatar.actionKey.value" @loaded="handleAvatarLoaded" @error="handleAvatarLoadError" />
          <AvatarDisplay v-else :state="avatarState" :emotion="avatar.currentEmotion.value" />
        </div>
      </div>
      <aside class="side-card" :class="{speaking:chatStore.streaming}">
        <div class="side-card-head"><div class="side-card-tabs">
          <button :class="['side-card-tab',{active:activeTab==='chat'}]" @click="activeTab='chat'">对话</button>
          <button :class="['side-card-tab',{active:activeTab==='source'}]" @click="activeTab='source'">来源</button>
        </div></div>
        <div :class="['side-card-body',{hidden:activeTab!=='chat'}]" ref="messageListRef">
          <article v-for="(m,i) in chatStore.messages" :key="`${m.role}-${i}`" :class="['msg-item',m.role,{collapsed:m.role==='user'&&i<chatStore.messages.length-1&&chatStore.messages[i+1]?.role==='assistant'}]">
            <div v-if="m.role==='assistant'" class="msg-bubble" v-html="renderAnswer(m.content,i===chatStore.messages.length-1)" @click="handleCitationClick"></div>
            <div v-else class="msg-bubble">{{ m.content }}</div>
            <div v-if="m.role==='assistant' && m.content && !chatStore.streaming" class="answer-feedback" aria-label="回答评价">
              <span>这条讲解有帮助吗？</span>
              <button type="button" :class="{ active: m.feedbackRating === 'positive' }" :disabled="m.feedbackSubmitting" @click="chatStore.submitFeedback(m, 'positive')">👍 有帮助</button>
              <button type="button" :class="{ active: m.feedbackPendingRating === 'negative' || m.feedbackRating === 'negative' }" :disabled="m.feedbackSubmitting" @click="m.feedbackPendingRating = m.feedbackPendingRating === 'negative' ? null : 'negative'">👎 需改进</button>
              <div v-if="m.feedbackPendingRating === 'negative'" class="feedback-reasons">
                <span>请选择原因：</span>
                <button v-for="reason in feedbackReasons" :key="reason.value" type="button" :disabled="m.feedbackSubmitting" @click="chatStore.submitFeedback(m, 'negative', reason.value)">{{ reason.label }}</button>
              </div>
              <span v-if="m.feedbackError" class="feedback-error">{{ m.feedbackError }}</span>
            </div>
            <span v-if="m.role==='assistant'&&chatStore.streaming&&i===chatStore.messages.length-1&&m.content.length>0" class="typing-cursor">|</span>
          </article>
          <div v-if="chatStore.followups.length" class="followup-panel">
            <button v-for="(fu,i) in chatStore.followups" :key="i" class="followup-btn" @click="handleFollowup(fu)">{{ fu.query||fu.label||fu }}</button>
          </div>
          <div v-if="chatStore.userStopped&&!chatStore.streaming" class="stop-notice" role="status">已停止输出</div>
          <div v-if="chatStore.errorMessage&&!chatStore.streaming" class="error-notice" role="alert">{{ chatStore.errorMessage }}</div>
        </div>
        <div :class="['side-card-body',{hidden:activeTab!=='source'}]">
          <ul v-if="chatStore.sources.length" class="source-list">
            <li v-for="(s,i) in chatStore.sources" :key="i" :class="['source-item',{highlight:sourceHighlightIndex===i}]" :data-source-index="i">
              <h4><span class="source-num">{{ i+1 }}</span>{{ s.title }}</h4><p>{{ s.snippet }}</p><span class="source-meta">{{ s.source }}</span>
            </li>
          </ul>
          <div v-else class="source-empty">提问后这里会显示参考资料</div>
        </div>
      </aside>
      <aside class="right-card">
        <div class="right-card-head">
          <span>路线规划</span>
          <span class="right-card-head-status">
            <span :class="['status-inline-dot', avatarReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">数字人</span>
            <span :class="['status-inline-dot', voiceReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">语音</span>
            <span :class="['status-inline-dot', replyStatusClass.replace('status-pill--','status-inline-dot--')]">回答</span>
          </span>
        </div>
        <div class="right-card-body">
          <div :class="['level1-view', { hidden: currentLevel !== 1 }]">
            <div class="service-grid">
              <button class="explore-card explore-card--scenic" @click="navigateToLevel2('官方推荐')">
                <span class="explore-card-icon">🏯</span>
                <span class="explore-card-title">官方推荐</span>
                <span class="explore-card-desc">景区官方设计</span>
              </button>
              <button class="explore-card explore-card--area" @click="navigateToLevel2('半日精选')">
                <span class="explore-card-icon">☀️</span>
                <span class="explore-card-title">半日精选</span>
                <span class="explore-card-desc">时间紧也能玩好</span>
              </button>
              <button class="explore-card explore-card--type" @click="navigateToLevel2('主题体验')">
                <span class="explore-card-icon">🎨</span>
                <span class="explore-card-title">主题体验</span>
                <span class="explore-card-desc">按兴趣定制玩法</span>
              </button>
              <button class="explore-card explore-card--photo" @click="navigateToLevel2('特色路线')">
                <span class="explore-card-icon">⭐</span>
                <span class="explore-card-title">特色路线</span>
                <span class="explore-card-desc">不一样的灵山</span>
              </button>
            </div>
          </div>
          <div :class="['level2-view', { open: currentLevel === 2 }]">
            <div class="l2-back-row">
              <button class="l2-back-btn" @click="navigateToLevel1">
                <span class="l2-back-arrow">←</span> 返回路线分类
              </button>
            </div>
            <div class="route-preference-panel">
              <div class="route-preference-title">
                <strong>智能偏好</strong>
                <span>结合天气进行轻量调整</span>
              </div>
              <div class="route-preference-chips">
                <button
                  v-for="option in comfortPreferenceOptions"
                  :key="option.value"
                  type="button"
                  :class="['route-preference-chip', { active: comfortPreferences.includes(option.value) }]"
                  :aria-pressed="comfortPreferences.includes(option.value)"
                  @click="toggleComfortPreference(option.value)"
                >{{ option.label }}</button>
              </div>
            </div>
            <div class="l2-scroll">
              <div v-for="route in filteredRoutes" :key="route.id" class="route-card" @click="navigateToLevel3(route)">
                <h4>{{ route.title }}</h4>
                <div class="route-meta">{{ route.duration_label }}</div>
                <div class="route-tags">
                  <span v-for="tag in route.tags" :key="tag">{{ tag }}</span>
                </div>
              </div>
            </div>
          </div>
          <div :class="['level3-view', { open: currentLevel === 3 }]">
            <div class="l2-back-row">
              <button class="l2-back-btn" @click="navigateToLevel2(currentCategory)">
                <span class="l2-back-arrow">←</span> 返回路线列表
              </button>
            </div>
            <div class="l2-scroll">
              <div v-if="selectedRoute" class="route-detail-section route-spots">
                <h5>途经点列表</h5>
                <ul>
                  <li v-for="(spot, idx) in selectedRoute.spots" :key="idx">{{ spot }}</li>
                </ul>
              </div>
              <div v-if="selectedRoute" class="route-detail-section route-guide">
                <h5>讲解指南</h5>
                <p>{{ selectedRoute.guide }}</p>
              </div>
              <div v-if="selectedRoute" class="route-detail-section route-features">
                <h5>特色体验</h5>
                <p>{{ selectedRoute.features }}</p>
              </div>
              <button v-if="selectedRoute" class="route-start-btn" @click="startTour(selectedRoute)">开始导览</button>
            </div>
          </div>
          <div class="hotline-section">
            <div class="hotline-section-title">景区服务</div>
            <div class="hotline-grid">
              <button
                v-for="(h, key) in hotlineConfig"
                :key="key"
                class="hotline-card"
                @click="handleHotline(key)"
              >
                <span class="hotline-card-icon">{{ h.icon }}</span>
                <span class="hotline-card-label">{{ h.label }}</span>
              </button>
            </div>
          </div>
        </div>
      </aside>
    </div>
    <div class="input-row">
      <button class="image-btn" @click="goToChatView">拍照识景</button>
      <input v-model="inputText" type="text" class="input-field" placeholder="请问关于游览路线…" :disabled="chatStore.streaming" @keydown.enter="handleSend" />
      <button class="voice-btn" @click="goToChatView">语音提问</button>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import { useRouter } from "vue-router";
import { useChatStore } from "../../stores/chat";
import { useInteractionStore } from "../../stores/interaction";
import { GUIDE_PERSONA, useAvatar } from "../../composables/useAvatar";
import { renderMarkdown } from "../../composables/useMarkdown";
import { useAudioPlayer } from "../../composables/useAudioPlayer";
import { fetchAvatarConfig } from "../../api/admin";
import { normalizeAvatarPresetFromModelPath, DEFAULT_AVATAR_PRESET } from "../../utils/avatarConfig";
import { useScenicBackground } from "../../composables/useScenicBackground";
import { useWeather } from "../../composables/useWeather";
import ThreeAvatar from "../../components/ThreeAvatar.vue";
import AvatarDisplay from "../../components/AvatarDisplay.vue";
import { fetchRecommendations } from "../../api/recommend";
import { getSessionId } from "../../stores/chat";

const PRESET_ROUTES = [
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

const router = useRouter();
const chatStore = useChatStore();
const interactionStore = useInteractionStore();
const avatar = useAvatar();
const audioPlayer = useAudioPlayer();
const { scenicBgUrl } = useScenicBackground();
const { weather, displayText: weatherCaption, startPolling: startWeather, stopPolling: stopWeather } = useWeather();

const feedbackReasons = [
  { value: "accurate", label: "回答准确" },
  { value: "insufficient", label: "信息不足" },
  { value: "slow", label: "回复太慢" },
  { value: "irrelevant", label: "答非所问" },
  { value: "other", label: "其他原因" },
];

const hotlineConfig = {
  broadcast: { label: '广播找人', icon: '📢', desc: '寻人广播·游客中心', number: '0510-85688631' },
  complaint: { label: '景区投诉', icon: '📋', desc: '服务投诉建议', number: '400-168-0303转5' },
  emergency: { label: '医疗急救', icon: '🩺', desc: '紧急医疗救助', number: '0510-85688120' },
};

function handleHotline(type) {
  if (chatStore.streaming) return;
  const h = hotlineConfig[type];
  if (!h) return;
  chatStore.messages.push({ role: 'assistant', content: `【${h.label}】请拨打景区服务热线：${h.number}` });
}

const avatarConfig = ref({ modelKey: DEFAULT_AVATAR_PRESET, voiceType: "gentle-female" });

async function loadAvatarConfig() {
  try {
    const cfg = await fetchAvatarConfig();
    avatarConfig.value.modelKey = normalizeAvatarPresetFromModelPath(cfg?.model_path, DEFAULT_AVATAR_PRESET);
    avatarConfig.value.voiceType = cfg?.voice_type || "gentle-female";
  } catch { /* use defaults */ }
}

const ttsConfig = () => ({ voiceType: avatarConfig.value.voiceType, speechRate: 100, volume: 80 });
const sendOptions = {
  get base() {
    return {
      ttsConfig: ttsConfig(),
      onContext: (sel) => interactionStore.applyResolvedSelection(sel),
      onThinking: () => avatar.setState("thinking"),
      onAvatar: (p) => { try { avatar.handleAvatarEvent(p) } catch { avatarError.value = true } },
      onAudioStart: () => { activeAudioSegments.value++; avatar.setState("speaking") },
      onAudioEnded: () => { activeAudioSegments.value = Math.max(activeAudioSegments.value - 1, 0); if (activeAudioSegments.value === 0) { avatar.setState("idle"); speechProgress.value = 0; speechElapsedMs.value = 0; speechDurationMs.value = 0; visemeTimeline.value = null } },
      onSpeechProgress: (p, em, tl, ad) => { speechProgress.value = p; speechElapsedMs.value = em; speechDurationMs.value = ad; visemeTimeline.value = tl },
    };
  },
};

const activeTab = ref("chat");
const inputText = ref("");
const messageListRef = ref(null);
const sourceHighlightIndex = ref(-1);
const avatarState = avatar.currentState;
const avatarError = ref(false);
const speechProgress = ref(0);
const speechElapsedMs = ref(0);
const speechDurationMs = ref(0);
const activeAudioSegments = ref(0);
const visemeTimeline = ref(null);

const currentLevel = ref(1);

const AVATAR_MODEL_MAP = {
  monk: { name: "宁灵", subtitle: "宁灵 · 佛学文化导游" },
  hanfu: { name: "清岚", subtitle: "清岚 · 文化叙事导游" },
  modern: { name: "景行", subtitle: "景行 · 智能导览导游" },
};
const avatarDisplaySubtitle = computed(() => AVATAR_MODEL_MAP[avatarConfig.value.modelKey]?.subtitle || "清岚 · 数字人导游");

const avatarReady = computed(() => !avatarError.value);
const voiceReady = computed(() => true);
const replyStatusClass = computed(() => {
  if (chatStore.streaming) return 'status-pill--live';
  if (avatarState.value === 'thinking') return 'status-pill--loading';
  return 'status-pill--ready';
});
const replyStatusText = computed(() => {
  if (chatStore.streaming) return '正在回答';
  if (avatarState.value === 'thinking') return '思考中';
  return '等待提问';
});
const currentCategory = ref("官方推荐");
const selectedRoute = ref(null);

const filteredRoutes = computed(() => {
  if (recommendedRoutes.value.length > 0) return recommendedRoutes.value;
  return PRESET_ROUTES
    .filter((route) => route.category === currentCategory.value)
    .map((route) => ({ ...route, title: `[离线备选] ${route.title}` }));
});

const recommendedRoutes = ref([]);
const comfortPreferences = ref([]);
const comfortPreferenceOptions = [
  { value: "avoid_heat", label: "☀️ 避暑" },
  { value: "less_walking", label: "🚶 少走路" },
  { value: "family", label: "👨‍👩‍👧 亲子/老人" },
  { value: "rain", label: "🌧️ 雨天" },
];
let recommendationRequestId = 0;

function toggleComfortPreference(value) {
  comfortPreferences.value = comfortPreferences.value.includes(value)
    ? comfortPreferences.value.filter((item) => item !== value)
    : [...comfortPreferences.value, value];
  loadRecommendations(currentCategory.value);
}

function categoryPreferences(category) {
  if (category.includes("半日")) return { interests: ["轻松", "半日"], hours: 3 };
  if (category.includes("主题")) return { interests: ["摄影", "文化"], hours: 4 };
  if (category.includes("特色")) return { interests: ["自然", "文化"], hours: 4 };
  return { interests: ["历史", "文化"], hours: 6 };
}

function mapRecommendedRoute(item) {
  const spots = String(item.route_plan || "")
    .split(/\s*(?:→|->|—|－)\s*/)
    .map((spot) => spot.trim())
    .filter(Boolean);
  return {
    id: `recommended-${item.route_id}`,
    routeId: item.route_id,
    title: `[智能推荐] ${item.title}`,
    duration_label: item.duration_label || `${item.duration_hours || 2}小时`,
    tags: ["智能推荐", ...(item.comfort_tags || []), item.source || "官方资料"],
    spots,
    guide: [item.reason, ...(item.guide_points || [])].filter(Boolean).join("\n"),
    features: (item.experiences || []).join("；") || "可在导览过程中查看景点讲解与服务提示。",
  };
}

async function loadRecommendations(category) {
  const requestId = ++recommendationRequestId;
  const preference = categoryPreferences(category);
  recommendedRoutes.value = [];
  try {
    const data = await fetchRecommendations({
      session_id: getSessionId(), interests: preference.interests, available_hours: preference.hours,
      audience_type: "general", avoid_crowded: category.includes("特色"),
      comfort_preferences: comfortPreferences.value,
      weather_condition: weather.value?.description || null,
      temperature_c: Number.isFinite(weather.value?.temp) ? weather.value.temp : null,
    });
    if (requestId !== recommendationRequestId) return;
    recommendedRoutes.value = Array.isArray(data?.routes)
      ? data.routes.map(mapRecommendedRoute).filter((route) => route.spots.length > 0) : [];
  } catch {
    if (requestId === recommendationRequestId) recommendedRoutes.value = [];
  }
}

function navigateToLevel2(category) {
  currentCategory.value = category;
  currentLevel.value = 2;
  selectedRoute.value = null;
  loadRecommendations(category);
}

function navigateToLevel3(route) {
  selectedRoute.value = route;
  currentLevel.value = 3;
}

function navigateToLevel1() {
  currentLevel.value = 1;
  selectedRoute.value = null;
}

function startTour(route) {
  if (chatStore.streaming) return;
  if (route.routeId) interactionStore.selectRoute(route.routeId);
  avatar.triggerAction("departure_pose");
  chatStore.sendMessage(`请介绍${route.title}`, interactionStore.selectionPayload, sendOptions.base);
}

function handleAvatarLoaded() { avatarError.value = false; }
function handleAvatarLoadError() { avatarError.value = true; }

function handleSend() {
  const t = inputText.value.trim(); if (!t || chatStore.streaming) return;
  chatStore.sendMessage(t, interactionStore.selectionPayload, sendOptions.base);
  inputText.value = "";
}
function handleRetry() { chatStore.retryLastMessage(); }
function handleFollowup(fu) { chatStore.sendMessage(fu.query || fu.label || fu, interactionStore.selectionPayload, sendOptions.base); }

function handleCitationClick(e) {
  const cite = e.target?.closest(".citation");
  if (!cite) return;
  const evidenceId = cite.dataset.evidenceId;
  const index = chatStore.sources.findIndex(s => s.evidence_id === `证据${evidenceId}`);
  if (index >= 0) { activeTab.value = "source"; sourceHighlightIndex.value = index; nextTick(() => { document.querySelector(`[data-source-index="${index}"]`)?.scrollIntoView({ behavior: "smooth", block: "center" }); }); setTimeout(() => { sourceHighlightIndex.value = -1; }, 2000); }
}

function renderAnswer(content, isLastMessage) {
  return renderMarkdown(content, chatStore.sources, chatStore.streaming && isLastMessage);
}

function scrollToBottom() { nextTick(() => { if (messageListRef.value) messageListRef.value.scrollTop = messageListRef.value.scrollHeight; }); }
watch(() => chatStore.messages.length, () => scrollToBottom());
watch(() => { const msgs = chatStore.messages; return msgs.length > 0 ? msgs[msgs.length - 1].content : ""; }, () => scrollToBottom());

function handleBack() { chatStore.stopOutput(); audioPlayer.stop(); router.push("/tourist/select?index=2").catch(() => {}); }

function goToChatView() {
  router.push("/tourist").catch(() => {});
}

onMounted(() => { interactionStore.initialize(); loadAvatarConfig(); startWeather(); });
onBeforeUnmount(() => { chatStore.stopOutput(); audioPlayer.stop(); avatar.setState("idle"); stopWeather(); });
</script>

<style scoped>
/* ============================================================
   DARK THEME TOURIST PAGE - aligned to design-redesign spec
   ============================================================ */
.tourist-page {
  position: relative;
  width: 100%; height: 100vh; height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #1a1612;
  color: #f0ece5;
  color-scheme: dark;
}

.scenic-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
.scenic-bg-img {
  position: absolute; inset: 0;
  background-position: center; background-repeat: no-repeat; background-size: cover;
  filter: blur(10px) saturate(0.3) brightness(0.4);
  transform: scale(1.06);
}
.scenic-bg-overlay {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 60% 40% at 50% 35%, transparent 0%, rgba(20,16,10,0.55) 80%),
    radial-gradient(ellipse 80% 50% at 50% 100%, rgba(22,18,10,0.5) 0%, transparent 70%);
}

.back-btn {
  position: absolute; top: clamp(10px, 2vw, 32px); left: clamp(10px, 2vw, 32px); z-index: 25;
  display: inline-flex; align-items: center; gap: 6px;
  padding: clamp(8px, 0.9vw, 14px) clamp(16px, 1.8vw, 28px);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 999px;
  background: rgba(255,250,242,0.05);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  color: rgba(232,228,219,0.55);
  font-family: inherit; font-size: clamp(14px, 1.2vw, 20px);
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
  outline: none;
}
.back-btn:hover {
  border-color: rgba(255,250,242,0.19);
  background: rgba(255,255,255,0.09);
  color: rgba(232,228,219,0.85);
}
.back-btn:focus-visible { outline: 2px solid #d9a441; outline-offset: 3px; }

.top-right {
  position: absolute; top: clamp(10px, 2vw, 32px); right: clamp(10px, 2vw, 32px); z-index: 20;
  display: flex; flex-direction: column;
  align-items: flex-end; gap: 8px;
}
.top-brand {
  color: rgba(232,228,219,0.88);
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: clamp(24px, 2.8vw, 40px);
  font-weight: 400;
  letter-spacing: 0.12em;
  text-shadow: 0 0 30px rgba(217,164,65,0.1);
  line-height: 1.2;
}
.top-status-row {
  display: flex; flex-direction: column; gap: 5px;
}
.status-item {
  display: flex; align-items: center; gap: 8px;
  font-size: clamp(13px, 0.9vw, 17px); font-weight: 400;
  letter-spacing: 0.06em;
  color: rgba(232,228,219,0.55);
  font-family: system-ui, sans-serif;
}
.status-dot {
  width: 12px; height: 12px;
  border-radius: 50%; flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
}
.status-dot--ready  { background: #d9a441; box-shadow: 0 0 4px rgba(217,164,65,0.5); }
.status-dot--live   { background: #5ec9a4; box-shadow: 0 0 4px rgba(94,201,164,0.5); }
.status-dot--weather { background: #6bb8e8; box-shadow: 0 0 4px rgba(107,184,232,0.5); }

.tourist-stage {
  position: relative; z-index: 10;
  flex: 1; min-height: 0;
  display: grid;
  grid-template-columns: minmax(clamp(160px, 12vw, 260px), clamp(240px, 17vw, 350px)) 1fr minmax(clamp(160px, 12vw, 260px), clamp(240px, 17vw, 350px));
  gap: clamp(8px, 1vw, 16px);
  align-items: stretch;
  padding: 20px clamp(10px, 1.5vw, 24px) 0;
  margin-top: 0;
}

.chat-center {
  grid-column: 2; grid-row: 1;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  position: relative; z-index: 2;
  width: 100%; height: 100%;
  min-height: 0;
  padding: 0 8px;
}
.top-caption {
  position: absolute;
  top: 16px; left: 50%; transform: translateX(-50%);
  z-index: 20;
  display: flex; align-items: baseline; justify-content: center; gap: 12px;
  white-space: nowrap;
}
.caption-kicker {
  color: #f8e7bb;
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(18px, 2vw, 28px); font-weight: 700; letter-spacing: 0.1em;
  text-shadow: 0 0 20px rgba(217,164,65,0.15);
}
.caption-weather {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba(23,18,14,0.6);
  color: rgba(232,228,219,0.38);
  font-family: system-ui, sans-serif;
  font-size: clamp(12px, 0.8vw, 14px); font-weight: 400;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.caption-weather-live {
  color: rgba(232,228,219,0.55);
}
.crowd-indicator {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 14px;
  border-radius: 999px;
  background: rgba(23,18,14,0.6);
  font-size: 13px; font-weight: 400;
  color: rgba(232,228,219,0.55);
  letter-spacing: 0.04em;
  font-family: system-ui, sans-serif;
  white-space: nowrap;
  cursor: default;
}
.crowd-dot {
  width: 12px; height: 12px;
  border-radius: 50%; flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
}
.crowd-indicator[data-level="green"] .crowd-dot { background: #5ec9a4; }

.avatar-stage {
  position: relative; z-index: 2;
  width: min(clamp(360px, 34vw, 650px), 100vw);
  height: calc(min(clamp(360px, 42vh, 560px), 66vh) + 140px);
  padding-top: 140px;
  margin: -140px auto 0;
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  background: transparent;
  box-sizing: border-box;
}
.avatar-stage::after {
  content: "";
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 140px;
  z-index: 3;
  pointer-events: none;
  background: linear-gradient(to bottom, transparent 0%, #1a1612 100%);
}
.avatar-stage :deep(.three-wrapper),
.avatar-stage :deep(.avatar-display) {
  width: 100%; height: 100%;
  transform: translateY(8%);
}

.side-card {
  position: absolute;
  left: clamp(12px, 1.5vw, 28px); bottom: clamp(60px, 7vh, 120px);
  z-index: 15;
  width: clamp(260px, 17vw, 420px); height: clamp(340px, 52vh, 500px);
  background: rgba(23,18,14,0.88);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 10px;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.side-card.speaking {
  animation: card-breathe 3s ease-in-out infinite;
}
@keyframes card-breathe {
  0%, 100% { box-shadow: 0 0 0 rgba(217,164,65,0); }
  50% { box-shadow: 0 0 40px rgba(217,164,65,0.08); }
}
.side-card-head {
  flex-shrink: 0;
  position: relative;
}
.side-card-tabs {
  display: flex;
}
.side-card-tab {
  flex: 1;
  padding: 7px 0;
  border: none;
  background: transparent;
  color: rgba(232,228,219,0.35);
  font-family: inherit; font-size: clamp(14px, 0.9vw, 17px);
  font-weight: 600; letter-spacing: 0.06em;
  cursor: pointer;
  transition: color 0.25s ease;
  position: relative;
}
.side-card-tab:hover { color: rgba(232,228,219,0.7); }
.side-card-tab.active { color: rgba(232,228,219,0.75); }
.side-card-tab.active::after {
  content: "";
  position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 24px; height: 2px;
  border-radius: 1px;
  background: #d9a441;
}
.side-card-body {
  flex: 1; min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px 12px;
  display: flex; flex-direction: column;
  gap: 10px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.15) transparent;
}
.side-card-body.hidden { display: none; }
.side-card-body::-webkit-scrollbar { width: 4px; }
.side-card-body::-webkit-scrollbar-track { background: transparent; }
.side-card-body::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.15); border-radius: 2px; }
.side-card-body::-webkit-scrollbar-thumb:hover { background: rgba(217,164,65,0.25); }

.msg-item { display: flex; flex-direction: column; }
.msg-item.assistant { align-items: flex-start; }
.msg-item.user { align-items: flex-end; }
.msg-item.user.collapsed { gap: 4px; }
.msg-item.user.collapsed .msg-bubble {
  max-height: 24px; overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis;
  opacity: 0.45; font-size: 16px;
  padding: 4px 10px; border-radius: 6px;
  border-bottom-right-radius: 2px;
}
.msg-bubble {
  max-width: 90%;
  padding: 8px 12px;
  border-radius: 10px;
  font-size: 15px; line-height: 1.5;
  letter-spacing: 0.03em;
  word-break: break-word;
}
.msg-item.user .msg-bubble {
  background: rgba(217,164,65,0.12);
  border: none;
  color: rgba(232,228,219,0.9);
  border-bottom-right-radius: 4px;
}
.msg-item.assistant .msg-bubble {
  background: rgba(232,228,219,0.05);
  border: none;
  color: rgba(232,228,219,0.85);
  border-bottom-left-radius: 4px;
}
.typing-cursor {
  animation: blink 0.8s infinite;
  color: #d9a441;
  font-weight: 700; font-size: 16px; margin-left: 4px;
}
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

.followup-panel {
  display: flex; flex-wrap: wrap; gap: 8px;
  padding: 12px;
  border: 1px solid rgba(248,231,187,0.16);
  border-radius: 14px;
  background: rgba(255,248,232,0.06);
}
.followup-panel button {
  padding: 8px 14px;
  border: 1px solid rgba(248,231,187,0.2);
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  color: #f8e7bb; font-size: clamp(13px, 0.8vw, 15px);
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}
.followup-panel button:hover:not(:disabled) {
  background: rgba(255,255,255,0.16);
  border-color: rgba(248,231,187,0.42);
  transform: translateY(-1px);
}
.followup-panel button:disabled { opacity: 0.5; cursor: not-allowed; }

.source-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
.source-item {
  padding: 10px;
  border: 1px solid rgba(232,228,219,0.08);
  border-radius: 8px;
  background: rgba(232,228,219,0.04);
  transition: border-color 0.3s ease, background 0.3s ease;
}
.source-item:hover { border-color: rgba(232,228,219,0.20); background: rgba(232,228,219,0.08); }
.source-item.highlight {
  border-color: rgba(217,164,65,0.5);
  background: rgba(217,164,65,0.08);
}
.source-item h4 {
  display: flex; align-items: center; gap: 6px;
  margin: 0 0 5px;
  color: rgba(232,228,219,0.85); font-size: 18px; font-weight: 600;
}
.source-num {
  display: inline-flex; flex-shrink: 0;
  align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 50%;
  background: rgba(217,164,65,0.2);
  color: #d9a441; font-size: 13px; font-weight: 700;
}
.source-item p {
  margin: 0 0 3px;
  color: rgba(232,228,219,0.55); font-size: 14px; line-height: 1.5;
}
.source-meta { color: rgba(232,228,219,0.3); font-size: 13px; }
.source-empty { color: rgba(240,242,236,0.52); text-align: center; padding: 60px 0; font-size: 15px; }

.stop-notice { text-align: center; padding: 8px; color: rgba(248,231,187,0.6); font-size: 14px; }
.error-notice { text-align: center; padding: 8px; color: #f87171; font-size: 14px; }

.right-card {
  position: absolute;
  right: clamp(12px, 1.5vw, 28px); top: clamp(80px, 8vh, 130px); bottom: clamp(60px, 7vh, 120px);
  z-index: 15;
  width: clamp(270px, 18vw, 450px);
  background: rgba(23,18,14,0.88);
  border: 1px solid rgba(255,250,242,0.11);
  border-radius: 10px;
  overflow: hidden;
  display: flex; flex-direction: column;
}
.right-card-head {
  flex-shrink: 0;
  position: relative;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(232,228,219,0.06);
  color: rgba(232,228,219,0.5);
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(12px, 0.8vw, 14px); font-weight: 600;
  letter-spacing: 0.06em;
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
}
.right-card-body {
  flex: 1; min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px 12px;
  display: flex; flex-direction: column;
  gap: 6px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.15) transparent;
}
.right-card-body::-webkit-scrollbar { width: 4px; }
.right-card-body::-webkit-scrollbar-track { background: transparent; }
.right-card-body::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.15); border-radius: 2px; }
.right-card-body::-webkit-scrollbar-thumb:hover { background: rgba(217,164,65,0.25); }

.service-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 8px;
}
.explore-card {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: clamp(6px, 0.5vw, 10px);
  padding: clamp(10px, 1.2vw, 18px) clamp(6px, 0.8vw, 14px);
  border-radius: 8px;
  border: 1px solid rgba(232,228,219,0.10);
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  text-align: center; min-height: 0;
  transition: border-color 0.3s ease, background 0.3s ease;
  outline: none; position: relative; overflow: hidden;
  font-family: inherit; color: inherit;
}
.explore-card:hover {
  border-color: rgba(217,164,65,0.35);
  background: rgba(217,164,65,0.06);
}
.explore-card:active { transform: scale(0.96); }
.explore-card:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.explore-card-icon {
  width: clamp(44px, 3vw, 64px); height: clamp(44px, 3vw, 64px); border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: clamp(22px, 1.6vw, 32px); flex-shrink: 0;
  transition: transform 0.3s ease;
}
.explore-card:hover .explore-card-icon { transform: scale(1.1); }
.explore-card--scenic .explore-card-icon { background: rgba(217,164,65,0.15); color: #d9a441; }
.explore-card--area   .explore-card-icon { background: rgba(94,201,164,0.15); color: #5ec9a4; }
.explore-card--type   .explore-card-icon { background: rgba(107,184,232,0.15); color: #6bb8e8; }
.explore-card--photo  .explore-card-icon { background: rgba(232,168,64,0.15); color: #e8a840; }
.explore-card-title {
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: clamp(16px, 1.3vw, 24px); font-weight: 600;
  color: rgba(232,228,219,0.82);
  letter-spacing: 0.05em; line-height: 1.3;
}
.explore-card-desc {
  font-size: clamp(12px, 0.8vw, 15px); font-weight: 400;
  color: rgba(232,228,219,0.3);
  letter-spacing: 0.04em; line-height: 1.2;
  font-family: system-ui, sans-serif;
}

/* ---------- hotline section ---------- */
.hotline-section {
  margin-top: clamp(1px, 0.15vw, 4px);
  padding-top: clamp(8px, 0.8vw, 14px);
  border-top: 1px solid rgba(232,228,219,0.08);
}
.hotline-section-title {
  font-family: "STKaiti","KaiTi",serif;
  font-size: clamp(10px, 0.7vw, 13px); font-weight: 600;
  color: rgba(232,228,219,0.35);
  letter-spacing: 0.06em;
  margin-bottom: clamp(5px, 0.5vw, 10px);
  padding: 0 2px;
}
.hotline-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: clamp(4px, 0.4vw, 8px);
}
.hotline-card {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: clamp(2px, 0.2vw, 5px);
  padding: clamp(4px, 0.5vw, 10px) clamp(2px, 0.3vw, 6px);
  border-radius: clamp(6px, 0.5vw, 10px);
  border: 1px solid rgba(232,228,219,0.10);
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  transition: border-color 0.25s ease, background 0.25s ease;
  outline: none; min-width: 0;
  font-family: inherit; color: inherit;
}
.hotline-card:hover {
  border-color: rgba(248,113,113,0.35);
  background: rgba(248,113,113,0.06);
}
.hotline-card:active { transform: scale(0.96); }
.hotline-card:focus-visible { outline: 2px solid #f87171; outline-offset: 2px; }
.hotline-card-icon {
  font-size: clamp(14px, 1.2vw, 22px); flex-shrink: 0;
  transition: transform 0.25s ease;
}
.hotline-card:hover .hotline-card-icon { transform: scale(1.12); }
.hotline-card-label {
  font-size: clamp(9px, 0.6vw, 12px); font-weight: 500;
  color: rgba(232,228,219,0.6);
  letter-spacing: 0.03em;
  line-height: 1.2;
}

.input-row {
  position: absolute;
  bottom: clamp(24px, 2.5vh, 40px); left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  width: min(clamp(420px, 42vw, 800px), 88vw);
  display: flex; align-items: center; justify-content: center; gap: 12px;
}
.input-field {
  flex: 1;
  height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(16px, 1.5vw, 28px);
  border: 1px solid rgba(232,228,219,0.12);
  border-radius: 10px;
  background: rgba(23,18,14,0.78);
  color: rgba(232,228,219,0.82);
  font-family: inherit; font-size: clamp(16px, 1.2vw, 24px);
  letter-spacing: 0.03em;
  outline: none;
  transition: border-color 0.25s ease;
}
.input-field::placeholder { color: rgba(232,228,219,0.25); font-size: clamp(15px, 1.1vw, 22px); }
.input-field:focus { border-color: rgba(217,164,65,0.35); }
.input-field:disabled { opacity: 0.5; }

.image-btn {
  flex-shrink: 0; width: auto; height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(14px, 1.4vw, 28px);
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(94,201,164,0.25);
  border-radius: 999px;
  background: rgba(94,201,164,0.1);
  color: #5ec9a4;
  font-family: inherit; font-size: clamp(15px, 1.1vw, 22px); font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
  outline: none; white-space: nowrap;
}
.image-btn:hover {
  border-color: rgba(94,201,164,0.45);
  background: rgba(94,201,164,0.2);
  box-shadow: 0 0 20px rgba(94,201,164,0.15);
}
.image-btn:active { transform: scale(0.95); }
.image-btn:focus-visible { outline: 2px solid #5ec9a4; outline-offset: 3px; }

.voice-btn {
  flex-shrink: 0; width: auto; height: clamp(52px, 3.6vw, 72px);
  padding: 0 clamp(14px, 1.8vw, 32px);
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(217,164,65,0.3);
  border-radius: 999px;
  background: rgba(217,164,65,0.14);
  color: #d9a441;
  font-family: inherit; font-size: clamp(16px, 1.2vw, 24px); font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
  outline: none; white-space: nowrap;
}
.voice-btn:hover {
  border-color: rgba(217,164,65,0.45);
  background: rgba(217,164,65,0.2);
  box-shadow: 0 0 20px rgba(217,164,65,0.15);
}
.voice-btn:active { transform: scale(0.95); }
.voice-btn:focus-visible { outline: 2px solid #d9a441; outline-offset: 3px; }

@media (max-width: 720px) {
  .tourist-page { overflow: hidden; padding: 0; }
  .tourist-stage { display: flex; flex-direction: column; padding: 0; margin-top: 40px; gap: 0; flex: 1; min-height: 0; padding-bottom: 48px; }
  .side-card { position: relative; left: auto; bottom: auto; width: 100%; min-height: 200px; order: 3; }
  .right-card { position: relative; right: auto; top: auto; bottom: auto; width: 100%; min-height: 200px; order: 4; border-radius: 0; }
  .chat-center { flex: 1; padding: 0; min-height: 0; }
  .avatar-stage { width: min(52vh, 78vw); height: 100%; min-height: 0; flex: 1; }
  .avatar-stage :deep(.three-wrapper),
  .avatar-stage :deep(.avatar-display) { transform: translateY(10%); }
  .avatar-stage::after { height: 80px; }
  .input-row { position: absolute; bottom: 56px; left: 0; right: 0; transform: none; width: auto; gap: 6px; padding: 0 10px; margin: 0; }
  .input-field { height: 48px; font-size: 16px; padding: 0 14px; }
  .input-field::placeholder { font-size: 14px; }
  .back-btn { top: 6px; left: 6px; padding: 5px 12px; font-size: 14px; }
  .top-right { top: 6px; right: 6px; }
  .top-brand { font-size: 15px; }
  .top-caption { flex-wrap: wrap; gap: 4px; }
  .caption-kicker { font-size: 15px; }
  .caption-weather { font-size: 10px; padding: 3px 8px; }
  .crowd-indicator { font-size: 10px; padding: 3px 8px; }
  .service-grid { grid-template-columns: 1fr 1fr; gap: 8px; }
  .voice-btn { padding: 0 10px; height: 44px; font-size: 14px; }
  .image-btn { padding: 0 10px; height: 44px; font-size: 13px; }
  .explore-card { padding: 10px 6px; }
  .explore-card-icon { width: 40px; height: 40px; font-size: 22px; }
  .explore-card-title { font-size: 16px; }
  .explore-card-desc { font-size: 12px; }
}

@media (prefers-reduced-motion: reduce) {
  .side-card.speaking { animation: none; }
}

/* ---- status inline dots ---- */
.status-inline-dot {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 400;
  letter-spacing: 0.03em;
  color: rgba(232,228,219,0.45);
  font-family: system-ui, "Noto Sans SC", sans-serif;
  white-space: nowrap;
}
.status-inline-dot::before {
  content: "";
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 1px solid rgba(255,250,242,0.16);
  transition: background 0.3s ease, box-shadow 0.3s ease;
}
.status-inline-dot--ready::before { background: #5ec9a4; box-shadow: 0 0 5px rgba(94,201,164,0.35); }
.status-inline-dot--loading::before { background: #e8a840; box-shadow: 0 0 5px rgba(232,168,64,0.35); animation: dot-pulse 1.6s ease-in-out infinite; }
.status-inline-dot--live::before { background: #d9a441; box-shadow: 0 0 5px rgba(217,164,65,0.35); }
.right-card-head-status {
  display: inline-flex; align-items: center; gap: 10px;
  flex-shrink: 0;
}
.answer-feedback { display: flex; flex-wrap: nowrap; align-items: center; gap: 6px; margin-top: 8px; color: rgba(232,228,219,.62); font-size: 11px; }
.answer-feedback button { border: 1px solid rgba(232,228,219,.2); border-radius: 999px; background: rgba(255,255,255,.04); color: rgba(255,250,242,.82); padding: 4px 7px; font-size: 11px; cursor: pointer; }
.answer-feedback button:hover, .answer-feedback button.active { border-color: rgba(94,201,164,.75); background: rgba(94,201,164,.14); color: #b8f1dd; }
.answer-feedback button:disabled { cursor: wait; opacity: .55; }
.feedback-reasons { display: flex; flex-basis: 100%; flex-wrap: wrap; align-items: center; gap: 6px; padding-top: 2px; }
.feedback-error { flex-basis: 100%; color: #ffb4a8; }
@keyframes dot-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }

/* ===== RouteView-specific: level navigation ===== */
.level1-view {
  display: flex; flex: 1; min-height: 0; flex-direction: column;
}
.level1-view.hidden { display: none; }
.level2-view {
  display: none;
  flex: 1; min-height: 0;
  flex-direction: column;
}
.level2-view.open { display: flex; }
.level3-view {
  display: none;
  flex: 1; min-height: 0;
  flex-direction: column;
}
.level3-view.open { display: flex; }
.l2-back-row {
  flex-shrink: 0;
  padding: 0 12px 8px;
}
.l2-back-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 0;
  border: none; background: transparent;
  color: rgba(232,228,219,0.4);
  font-family: inherit; font-size: 16px; cursor: pointer;
  transition: color 0.25s ease;
}
.l2-back-btn:hover { color: #d9a441; }
.l2-back-arrow { font-size: 18px; transition: transform 0.3s ease; }
.l2-back-btn:hover .l2-back-arrow { transform: translateX(-2px); }
.l2-scroll {
  flex: 1; min-height: 0;
  overflow-y: auto; padding: 0 12px 8px;
  display: flex; flex-direction: column; gap: 8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232,228,219,0.1) transparent;
}
.l2-scroll::-webkit-scrollbar { width: 3px; }
.l2-scroll::-webkit-scrollbar-thumb { background: rgba(232,228,219,0.1); border-radius: 2px; }
.l2-scroll::-webkit-scrollbar-track { background: transparent; }

/* ===== RouteView-specific: route cards ===== */
.route-preference-panel {
  margin: 0 0 10px;
  padding: 10px 12px;
  border: 1px solid rgba(94, 201, 164, 0.2);
  border-radius: 12px;
  background: rgba(94, 201, 164, 0.07);
}
.route-preference-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  color: rgba(255,255,255,0.88);
  font-size: 13px;
}
.route-preference-title span {
  color: rgba(255,255,255,0.45);
  font-size: 11px;
}
.route-preference-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.route-preference-chip {
  padding: 5px 9px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  background: rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.68);
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}
.route-preference-chip.active {
  border-color: rgba(94, 201, 164, 0.58);
  background: rgba(94, 201, 164, 0.2);
  color: #8ce2c4;
}
.route-card {
  display: flex; flex-direction: column; gap: 4px;
  padding: 10px 12px;
  border: 1px solid rgba(232,228,219,0.10);
  border-radius: 8px;
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease;
}
.route-card:hover {
  border-color: rgba(217,164,65,0.35);
  background: rgba(217,164,65,0.05);
}
.route-card:active { transform: scale(0.97); }
.route-card:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.route-card h4 {
  margin: 0;
  color: rgba(232,228,219,0.82); font-size: 18px; font-weight: 600;
  letter-spacing: 0.04em;
}
.route-card .route-meta {
  color: rgba(232,228,219,0.33); font-size: 14px;
  letter-spacing: 0.03em;
}
.route-card .route-tags {
  display: flex; flex-wrap: wrap; gap: 4px;
}
.route-card .route-tags span {
  padding: 2px 8px;
  border: 1px solid rgba(217,164,65,0.2);
  border-radius: 999px;
  font-size: 12px; color: rgba(217,164,65,0.65);
  font-family: system-ui, sans-serif;
}
.route-detail-section {
  margin-top: 6px;
  padding: 8px 12px;
  border: 1px solid rgba(232,228,219,0.08);
  border-radius: 8px;
  background: rgba(232,228,219,0.02);
}
.route-detail-section h5 {
  margin: 0 0 6px;
  color: rgba(232,228,219,0.5); font-size: 14px; font-weight: 600;
  letter-spacing: 0.04em;
}
.route-detail-section ul {
  list-style: none; padding: 0; margin: 0;
  display: flex; flex-direction: column; gap: 4px;
}
.route-detail-section ul li {
  display: flex; align-items: center; gap: 6px;
  color: rgba(232,228,219,0.45); font-size: 14px;
  letter-spacing: 0.03em;
}
.route-detail-section ul li::before {
  content: "";
  width: 6px; height: 6px; border-radius: 2px;
  background: rgba(217,164,65,0.5);
  flex-shrink: 0;
}
.route-detail-section p {
  margin: 0; color: rgba(232,228,219,0.45); font-size: 14px;
  line-height: 1.5; letter-spacing: 0.03em;
}

.route-start-btn {
  padding: 12px 24px;
  margin-top: 8px;
  border: 1px solid rgba(217,164,65,0.35);
  border-radius: 999px;
  background: rgba(217,164,65,0.14);
  color: #d9a441;
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
  outline: none;
}
.route-start-btn:hover {
  border-color: rgba(217,164,65,0.5);
  background: rgba(217,164,65,0.22);
  box-shadow: 0 0 20px rgba(217,164,65,0.2);
}
.route-start-btn:active { transform: scale(0.96); }
.route-start-btn:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }

</style>
