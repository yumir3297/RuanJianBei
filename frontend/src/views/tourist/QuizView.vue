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
          <span class="caption-kicker">{{ avatarDisplaySubtitle }} · 文化问答</span>
          <span class="caption-weather" v-if="!weatherCaption">随问随答 · 智慧灵山</span>
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
          <span>{{ rightCardTitle }}</span>
          <span class="right-card-head-status">
            <span :class="['status-inline-dot', avatarReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">数字人</span>
            <span :class="['status-inline-dot', voiceReady ? 'status-inline-dot--ready' : 'status-inline-dot--loading']">语音</span>
            <span :class="['status-inline-dot', replyStatusClass.replace('status-pill--','status-inline-dot--')]">回答</span>
          </span>
        </div>
        <div class="right-card-body">
          <div :class="['level1-view', { hidden: navLevel !== 1 }]">
            <div class="service-grid">
              <button class="explore-card explore-card--scenic" @click="goToLevel2('scenic')">
                <span class="explore-card-icon">🏯</span>
                <span class="explore-card-title">景点介绍</span>
                <span class="explore-card-desc">探索灵山胜境</span>
              </button>
              <button class="explore-card explore-card--photo" @click="goToLevel2('photo')">
                <span class="explore-card-icon">📸</span>
                <span class="explore-card-title">趣味竞答</span>
                <span class="explore-card-desc">灵山知识挑战</span>
              </button>
              <button class="explore-card explore-card--area" @click="goToLevel2('area')">
                <span class="explore-card-icon">☀️</span>
                <span class="explore-card-title">游览贴士</span>
                <span class="explore-card-desc">实用游览信息</span>
              </button>
              <button class="explore-card explore-card--type" @click="goToLevel2('type')">
                <span class="explore-card-icon">🗺️</span>
                <span class="explore-card-title">景区概况</span>
                <span class="explore-card-desc">了解灵山全貌</span>
              </button>
            </div>
          </div>
          <div :class="['level2-view', { open: navLevel === 2 }]">
            <div class="l2-back-row">
              <button class="l2-back-btn" @click="goToLevel1()">
                <span class="l2-back-arrow">←</span> 返回分类
              </button>
            </div>
            <div class="l2-scroll">
              <div class="sub-nav-grid">
                <button v-for="sub in currentSubNav" :key="sub.key" class="sub-nav-card" @click="goToLevel3(sub.key)">
                  <span class="sub-nav-card-icon">{{ sub.icon }}</span>
                  <span class="sub-nav-card-title">{{ sub.label }}</span>
                  <span class="sub-nav-card-count">{{ sub.count }}个问题</span>
                </button>
              </div>
            </div>
          </div>
          <div :class="['level3-view', { open: navLevel === 3 }]">
            <div class="l2-back-row">
              <button class="l2-back-btn" @click="goToLevel2(currentCategory)">
                <span class="l2-back-arrow">←</span> 返回子分类
              </button>
            </div>
            <div class="l2-scroll">
              <button v-for="(card, i) in currentCards" :key="i" class="scenic-card" @click="askQuestion(card.query)">
                <div class="scenic-card-img">
                  <span class="scenic-card-img-placeholder">{{ card.icon }}</span>
                </div>
                <div class="scenic-card-info">
                  <h4>{{ card.title }}</h4>
                  <p>{{ card.desc }}</p>
                </div>
              </button>
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
      <input v-model="inputText" type="text" class="input-field" placeholder="随时问我关于灵山的问题…" :disabled="chatStore.streaming" @keydown.enter="handleSend" />
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

const router = useRouter();
const chatStore = useChatStore();
const interactionStore = useInteractionStore();
const feedbackReasons = [
  { value: "accurate", label: "回答准确" },
  { value: "insufficient", label: "信息不足" },
  { value: "slow", label: "回复太慢" },
  { value: "irrelevant", label: "答非所问" },
  { value: "other", label: "其他原因" },
];
const avatar = useAvatar();
const audioPlayer = useAudioPlayer();
const { scenicBgUrl } = useScenicBackground();
const { displayText: weatherCaption, startPolling: startWeather, stopPolling: stopWeather } = useWeather();

const avatarConfig = ref({ modelKey: DEFAULT_AVATAR_PRESET, voiceType: "gentle-female" });

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

const navLevel = ref(1);
const currentCategory = ref("");
const currentSubCategory = ref("");

const QUESTION_DATA = {
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
    label: "趣味竞答",
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

const rightCardTitle = computed(() => {
  if (navLevel.value === 1) return "文化问答";
  if (navLevel.value === 2) return QUESTION_DATA[currentCategory.value]?.label || "";
  if (navLevel.value === 3) {
    const sub = QUESTION_DATA[currentCategory.value]?.subs[currentSubCategory.value];
    return sub ? sub.label : "";
  }
  return "文化问答";
});

const currentSubNav = computed(() => {
  if (navLevel.value !== 2 || !currentCategory.value) return [];
  const category = QUESTION_DATA[currentCategory.value];
  if (!category) return [];
  return Object.entries(category.subs).map(([key, sub]) => ({
    key,
    label: sub.label,
    icon: sub.icon,
    count: sub.cards.length,
  }));
});

const currentCards = computed(() => {
  if (navLevel.value !== 3 || !currentCategory.value || !currentSubCategory.value) return [];
  return QUESTION_DATA[currentCategory.value]?.subs[currentSubCategory.value]?.cards || [];
});

function goToLevel1() {
  navLevel.value = 1;
  currentCategory.value = "";
  currentSubCategory.value = "";
}

function goToLevel2(category) {
  navLevel.value = 2;
  currentCategory.value = category;
  currentSubCategory.value = "";
}

function goToLevel3(subCategory) {
  navLevel.value = 3;
  currentSubCategory.value = subCategory;
}

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

function askQuestion(query) {
  if (chatStore.streaming) return;
  chatStore.sendMessage(query, interactionStore.selectionPayload, sendOptions.base);
}

function handleAvatarLoaded() { avatarError.value = false; }
function handleAvatarLoadError() { avatarError.value = true; }

function askCard(topic) { if (chatStore.streaming) return; chatStore.sendMessage(`请介绍灵山关于【${topic}】的内容`, interactionStore.selectionPayload, sendOptions.base); }

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

function handleBack() { chatStore.stopOutput(); audioPlayer.stop(); router.push("/tourist/select?index=3").catch(() => {}); }

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
  filter: blur(10px) saturate(0.4) brightness(0.55);
  transform: scale(1.06);
}
.scenic-bg-overlay {
  position: absolute; inset: 0;
  background:
    radial-gradient(ellipse 60% 40% at 50% 35%, transparent 0%, rgba(20,16,10,0.38) 80%),
    radial-gradient(ellipse 80% 50% at 50% 100%, rgba(22,18,10,0.32) 0%, transparent 70%);
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

/* ---------- level navigation ---------- */
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

/* ---------- sub-nav grid ---------- */
.sub-nav-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 4px 8px;
  flex: 1;
  align-content: start;
}
.sub-nav-card {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 6px;
  padding: 12px 8px;
  border-radius: 8px;
  border: 1px solid rgba(232,228,219,0.10);
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  text-align: center;
  min-height: 72px;
  transition: border-color 0.3s ease, background 0.3s ease;
  outline: none;
  font-family: inherit; color: inherit;
}
.sub-nav-card:hover {
  border-color: rgba(217,164,65,0.35);
  background: rgba(217,164,65,0.06);
}
.sub-nav-card:active { transform: scale(0.96); }
.sub-nav-card:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.sub-nav-card-icon { font-size: 32px; line-height: 1; }
.sub-nav-card-title {
  font-family: "STKaiti","KaiTi","STSong",serif;
  font-size: 20px; font-weight: 600;
  color: rgba(232,228,219,0.82);
  letter-spacing: 0.05em; line-height: 1.2;
}
.sub-nav-card-count {
  font-size: 14px; font-weight: 400;
  color: rgba(232,228,219,0.3);
  letter-spacing: 0.04em;
  font-family: system-ui, sans-serif;
}

/* ---------- scenic card ---------- */
.scenic-card {
  display: flex; align-items: center; gap: 10px;
  padding: 8px;
  border: 1px solid rgba(232,228,219,0.10);
  border-radius: 8px;
  background: rgba(232,228,219,0.03);
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease;
}
.scenic-card:hover {
  border-color: rgba(217,164,65,0.35);
  background: rgba(217,164,65,0.05);
}
.scenic-card:active { transform: scale(0.97); }
.scenic-card:focus-visible { outline: 2px solid #d9a441; outline-offset: 2px; }
.scenic-card-img {
  width: 58px; height: 58px;
  flex-shrink: 0;
  border-radius: 6px;
  border: 1px solid rgba(217,164,65,0.25);
  background: rgba(232,228,219,0.04);
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  position: relative;
}
.scenic-card-img img {
  width: 100%; height: 100%;
  object-fit: cover; display: block;
}
.scenic-card-img-placeholder {
  color: rgba(217,164,65,0.25);
  font-size: 12px; font-weight: 600;
  font-family: system-ui, sans-serif;
  letter-spacing: 0.03em;
}
.scenic-card-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.scenic-card-info h4 {
  margin: 0;
  color: rgba(232,228,219,0.82); font-size: 18px; font-weight: 600;
  letter-spacing: 0.04em; line-height: 1.3;
}
.scenic-card-info p {
  margin: 0; color: rgba(232,228,219,0.33);
  font-size: 14px; line-height: 1.4;
  letter-spacing: 0.03em;
}

/* ---- status inline dots (scoped override) ---- */
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

/* ---------- responsive ---------- */
@media (max-width: 720px) {
  .tourist-page { overflow: hidden; padding: 0; }
  .tourist-stage { display: flex; flex-direction: column; padding: 0; margin-top: 40px; gap: 0; flex: 1; min-height: 0; padding-bottom: 48px; }
  .side-card { display: none; }
  .right-card { display: none; }
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
  .explore-card { padding: 10px 6px; }
  .explore-card-icon { width: 40px; height: 40px; font-size: 22px; }
  .explore-card-title { font-size: 16px; }
  .explore-card-desc { font-size: 12px; }
  .voice-btn { padding: 0 10px; height: 44px; font-size: 14px; }
  .image-btn { padding: 0 10px; height: 44px; font-size: 13px; }
}

@media (prefers-reduced-motion: reduce) {
  .side-card.speaking { animation: none; }
}
</style>
