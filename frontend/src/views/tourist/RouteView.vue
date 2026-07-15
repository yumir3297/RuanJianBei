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
          <span class="caption-kicker">{{ GUIDE_PERSONA.name }} · 路线规划</span>
          <span class="caption-weather">智能路线 · 灵山导览</span>
        </div>
        <div class="avatar-stage">
          <ThreeAvatar v-if="!avatarError" :preset="avatarConfig.modelKey" :emotion="avatar.currentEmotion.value" :is-speaking="avatarState==='speaking'||avatarState==='happy'" :speech-progress="speechProgress" :speech-elapsed-ms="speechElapsedMs" :speech-duration-ms="speechDurationMs" :speech-sync-active="activeAudioSegments>0" :viseme-timeline="visemeTimeline" @loaded="handleAvatarLoaded" @error="handleAvatarLoadError" />
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
        </div>
      </aside>
    </div>
    <div class="input-row"><div class="input-container">
      <input v-model="inputText" type="text" class="input-field" placeholder="请问关于游览路线…" :disabled="chatStore.streaming" @keydown.enter="handleSend" />
      <button class="input-send-btn" :disabled="!inputText.trim()||chatStore.streaming" @click="handleSend">→</button>
      <button v-if="chatStore.streaming" class="input-stop-btn" @click="chatStore.stopOutput()">■</button>
      <button v-if="chatStore.errorMessage&&!chatStore.streaming" class="input-retry-btn" @click="handleRetry">重试</button>
    </div></div>
    <div class="voice-hint">当前页暂仅支持文字提问；语音提问请使用数字人导游页。</div>
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
import ThreeAvatar from "../../components/ThreeAvatar.vue";
import AvatarDisplay from "../../components/AvatarDisplay.vue";

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
  return PRESET_ROUTES.filter(r => r.category === currentCategory.value);
});

function navigateToLevel2(category) {
  currentCategory.value = category;
  currentLevel.value = 2;
  selectedRoute.value = null;
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

function handleBack() { chatStore.stopOutput(); audioPlayer.stop(); router.push("/tourist/select"); }

onMounted(() => { interactionStore.initialize(); loadAvatarConfig(); });
onBeforeUnmount(() => { chatStore.stopOutput(); audioPlayer.stop(); avatar.setState("idle"); });
</script>

<style scoped>
@import '../../assets/tourist-page.css';
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
