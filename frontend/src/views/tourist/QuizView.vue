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
          <span class="caption-weather">随问随答 · 智慧灵山</span>
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
        </div>
      </aside>
    </div>
    <div class="input-row"><div class="input-container">
      <input v-model="inputText" type="text" class="input-field" placeholder="随时问我关于灵山的问题…" :disabled="chatStore.streaming" @keydown.enter="handleSend" />
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

const router = useRouter();
const chatStore = useChatStore();
const interactionStore = useInteractionStore();
const avatar = useAvatar();
const audioPlayer = useAudioPlayer();
const { scenicBgUrl } = useScenicBackground();

const avatarConfig = ref({ modelKey: DEFAULT_AVATAR_PRESET, voiceType: "gentle-female" });

const AVATAR_MODEL_MAP = {
  monk: { name: "明彻法师", subtitle: "明彻法师 · 佛学文化导游" },
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
          { icon: "🚗", title: "出行方式", desc: "多种方式到达灵山", query: "从无锡市区如何到达灵山景区，有哪些交通方式" },
          { icon: "🅿️", title: "停车指南", desc: "自驾停车全攻略", query: "灵山景区的停车设施和收费标准是什么" },
        ],
      },
      tips: {
        label: "游览须知",
        icon: "📋",
        cards: [
          { icon: "📋", title: "开放时间", desc: "景区营业时间", query: "灵山景区的开放时间和各场馆开放时段是什么" },
          { icon: "🎫", title: "门票须知", desc: "价格和优惠政策", query: "灵山景区的门票价格和各类优惠政策是什么" },
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

function handleBack() { chatStore.stopOutput(); audioPlayer.stop(); router.push("/tourist/select"); }

onMounted(() => { interactionStore.initialize(); loadAvatarConfig(); });
onBeforeUnmount(() => { chatStore.stopOutput(); audioPlayer.stop(); avatar.setState("idle"); });
</script>

<style scoped>
@import '../../assets/tourist-page.css';
</style>
