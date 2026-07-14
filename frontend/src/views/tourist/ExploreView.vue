<template>
  <section class="tourist-page">
    <div class="scenic-bg" aria-hidden="true">
      <div class="scenic-bg-img" :style="{ backgroundImage: scenicBgUrl }"></div>
      <div class="scenic-bg-overlay"></div>
    </div>
    <button type="button" class="back-btn" @click="handleBack">← 返回</button>
    <div class="top-right"><span class="top-brand">{{ GUIDE_PERSONA.name }}</span>
      <div class="top-status-row">
        <span class="status-item"><span class="status-dot status-dot--ready"></span>人物模型</span>
        <span class="status-item"><span class="status-dot status-dot--live"></span>景点探索</span>
        <span class="status-item"><span class="status-dot status-dot--weather"></span>{{ chatStore.statusText }}</span>
      </div>
    </div>
    <div class="tourist-stage">
      <div class="chat-center">
        <div class="top-caption">
          <span class="crowd-indicator" data-level="green"><span class="crowd-dot"></span>当前景区人数：舒适</span>
          <span class="caption-kicker">{{ GUIDE_PERSONA.name }} · 景点探索</span>
          <span class="caption-weather">拍照识景 · 发现灵山</span>
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
          <span v-if="navLevel==='level1'">探索工具</span>
          <span v-else-if="navLevel==='level2'">{{ navTitle }}</span>
          <span v-else>{{ navTitle }}</span>
        </div>
        <div class="right-card-body">
          <div :class="['level1-view',{hidden:navLevel!=='level1'}]">
            <div class="service-grid">
              <button class="explore-card explore-card--scenic" @click="goLevel2('scenic')">
                <span class="explore-card-icon">🏯</span>
                <span class="explore-card-title">景点推荐</span>
                <span class="explore-card-desc">热门景点导览</span>
              </button>
              <button class="explore-card explore-card--area" @click="goLevel2('area')">
                <span class="explore-card-icon">🗺️</span>
                <span class="explore-card-title">按区域浏览</span>
                <span class="explore-card-desc">灵山景区分布</span>
              </button>
              <button class="explore-card explore-card--type" @click="goLevel2('type')">
                <span class="explore-card-icon">🏛️</span>
                <span class="explore-card-title">按类型浏览</span>
                <span class="explore-card-desc">分类发现景点</span>
              </button>
              <button class="explore-card explore-card--photo" @click="goLevel2('photo')">
                <span class="explore-card-icon">📸</span>
                <span class="explore-card-title">拍照识景</span>
                <span class="explore-card-desc">上传图片识别景点</span>
              </button>
            </div>
          </div>

          <div :class="['level2-view',{open:navLevel==='level2'}]">
            <div class="l2-back-row">
              <button class="l2-back-btn" @click="goLevel1"><span class="l2-back-arrow">←</span> 返回</button>
            </div>
            <div class="l2-scroll">
              <template v-if="navCategory==='area'">
                <div class="sub-nav-grid">
                  <button class="sub-nav-card" v-for="area in areaSubNav" :key="area.key" @click="goLevel3(area.key,area.label)">
                    <span class="sub-nav-card-icon">{{ area.icon }}</span>
                    <span class="sub-nav-card-title">{{ area.label }}</span>
                    <span class="sub-nav-card-count">{{ area.count }}个景点</span>
                  </button>
                </div>
              </template>
              <template v-else-if="navCategory==='type'">
                <div class="sub-nav-grid">
                  <button class="sub-nav-card" v-for="type in typeSubNav" :key="type.key" @click="goLevel3(type.key,type.label)">
                    <span class="sub-nav-card-icon">{{ type.icon }}</span>
                    <span class="sub-nav-card-title">{{ type.label }}</span>
                    <span class="sub-nav-card-count">{{ type.count }}个景点</span>
                  </button>
                </div>
              </template>
              <template v-else-if="navCategory==='photo'">
                <div class="photo-capture-area">
                  <button class="photo-capture-btn" @click="triggerPhotoInput">📷</button>
                  <span class="photo-capture-label">点击拍照或上传图片</span>
                </div>
                <input ref="photoInputRef" type="file" accept="image/jpeg,image/png,image/webp" class="file-hidden" @change="handlePhotoChange">
                <div v-if="photoPreview||photoError||visionResult||analyzingPhoto" class="photo-result-area">
                  <div v-if="photoPreview&&!visionResult" class="photo-preview-box">
                    <img :src="photoPreview" alt="preview">
                    <div class="photo-actions">
                      <button class="followup-btn" @click="sendPhoto" :disabled="analyzingPhoto">识别图片</button>
                      <button class="followup-btn" @click="resetPhoto">重选</button>
                    </div>
                  </div>
                  <p v-if="photoError" class="photo-error" role="alert">{{ photoError }}</p>
                  <p v-if="analyzingPhoto" class="photo-status">识别中…</p>
                  <div v-if="visionResult" class="vision-result-panel">
                    <p class="vision-summary">{{ visionResult.scene_summary || '暂未识别出明确场景。' }}</p>
                    <div class="photo-actions">
                      <button class="followup-btn" @click="askFromExploreImage" :disabled="!visionResult.retrieval_query||chatStore.streaming">向导游提问</button>
                      <button class="followup-btn" @click="resetPhoto">重新拍照</button>
                    </div>
                  </div>
                </div>
                <div class="photo-guide">
                  <div class="photo-guide-tip" v-for="tip in photoTips" :key="tip">
                    <span class="photo-guide-tip-icon">💡</span>{{ tip }}
                  </div>
                </div>
                <div class="share-section">
                  <div class="share-section-label">分享探索</div>
                  <div class="share-actions">
                    <button class="share-btn" @click="shareExplore"><span class="share-btn-icon">📋</span>复制链接</button>
                    <button class="share-btn" @click="shareExplore"><span class="share-btn-icon">💬</span>分享给朋友</button>
                  </div>
                </div>
              </template>
              <template v-else>
                <div v-for="section in currentLevel3Sections" :key="section.label">
                  <div class="scenic-section-divider">{{ section.label }}</div>
                  <button class="scenic-card" v-for="spot in section.spots" :key="spot.name" @click="askSpot(spot)">
                    <div class="scenic-card-img">
                      <img v-show="!failedImgNames.has(spot.name)" :src="spot.image" :alt="spot.name" @error="onImgError(spot.name)">
                      <span class="scenic-card-img-placeholder">{{ spot.emoji }}</span>
                    </div>
                    <div class="scenic-card-info">
                      <h4>{{ spot.name }}</h4>
                      <p>{{ spot.desc }}</p>
                    </div>
                    <div class="scenic-dot"></div>
                  </button>
                </div>
              </template>
            </div>
          </div>

          <div :class="['level3-view',{open:navLevel==='level3'}]">
            <div class="l2-back-row">
              <button class="l2-back-btn" @click="goLevel2(navCategory)"><span class="l2-back-arrow">←</span> 返回{{ navCategory==='area'?'区域':navCategory==='type'?'类型':'上级' }}</button>
            </div>
            <div class="l2-scroll">
              <div v-for="section in currentLevel3Sections" :key="section.label">
                <div class="scenic-section-divider">{{ section.label }}</div>
                <button class="scenic-card" v-for="spot in section.spots" :key="spot.name" @click="askSpot(spot)">
                  <div class="scenic-card-img">
                    <img v-show="!failedImgNames.has(spot.name)" :src="spot.image" :alt="spot.name" @error="onImgError(spot.name)">
                    <span class="scenic-card-img-placeholder">{{ spot.emoji }}</span>
                  </div>
                  <div class="scenic-card-info">
                    <h4>{{ spot.name }}</h4>
                    <p>{{ spot.desc }}</p>
                  </div>
                  <div class="scenic-dot"></div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
    <div class="input-row"><div class="input-container">
      <input v-model="inputText" type="text" class="input-field" placeholder="输入问题，探索灵山景点…" :disabled="chatStore.streaming" @keydown.enter="handleSend" />
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
import { analyzeImage } from "../../api/vision";
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
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

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
const photoInputRef = ref(null);
const photoPreview = ref("");
const photoFile = ref(null);
const analyzingPhoto = ref(false);
const photoError = ref("");
const visionResult = ref(null);

function handleAvatarLoaded() { avatarError.value = false; }
function handleAvatarLoadError() { avatarError.value = true; }

function askCard(query) { if (chatStore.streaming) return; chatStore.sendMessage(query, interactionStore.selectionPayload, sendOptions.base); }
function askRecommend() { goLevel2("scenic"); }
function askPhoto() { goLevel2("photo"); }
function askRoute() { goLevel2("area"); }
function askCulture() { goLevel2("type"); }

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

function handlePhotoChange(e) {
  const f = e.target.files?.[0]; photoError.value = ""; visionResult.value = null;
  if (!f) return;
  if (!f.type.startsWith("image/")) { photoError.value = "仅支持图片文件。"; e.target.value = ""; return; }
  if (f.size > MAX_IMAGE_BYTES) { photoError.value = "图片不能超过 5MB。"; e.target.value = ""; return; }
  photoFile.value = f;
  const r = new FileReader(); r.onload = ev => { photoPreview.value = ev.target.result; }; r.readAsDataURL(f);
}

async function sendPhoto() {
  if (!photoFile.value || analyzingPhoto.value) return;
  analyzingPhoto.value = true; photoError.value = ""; visionResult.value = null;
  try { visionResult.value = await analyzeImage(photoFile.value); }
  catch (err) { photoError.value = err?.message || "识别失败，请重试"; }
  finally { analyzingPhoto.value = false; }
}

function askFromExploreImage() {
  const q = visionResult.value?.retrieval_query?.trim(); if (!q) return;
  chatStore.sendMessage("请根据这张图片识别出的线索，基于官方资料介绍它最可能对应的景区景点。", interactionStore.selectionPayload, { ...sendOptions.base, visionContext: visionResult.value, displayQuery: q });
}

function resetPhoto() { photoPreview.value = ""; photoFile.value = null; if (photoInputRef.value) photoInputRef.value.value = ""; photoError.value = ""; visionResult.value = null; }

function handleBack() { chatStore.stopOutput(); audioPlayer.stop(); router.push("/tourist/select"); }

function triggerPhotoInput() { photoInputRef.value?.click(); }

function shareExplore() {
  navigator.clipboard?.writeText(window.location.href).catch(() => {});
}

const photoTips = [
  "拍摄完整建筑主体，识别更准确",
  "尽量避免逆光或大面积遮挡",
  "支持识别佛像、殿堂、塔等建筑",
  "识别结果仅供参考，以现场导览为准",
];

const scenicSpots = [
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

const areaSubNav = [
  { key: "qianshan", label: "前山区", icon: "⛰️", count: 5 },
  { key: "houshan", label: "后山区", icon: "🏔️", count: 5 },
  { key: "huqu", label: "湖区", icon: "🌊", count: 6 },
  { key: "guangchang", label: "广场区", icon: "🏛️", count: 6 },
];

const typeSubNav = [
  { key: "foxiang", label: "佛像建筑", icon: "🗿", count: 4 },
  { key: "ziran", label: "自然景观", icon: "🌳", count: 6 },
  { key: "simiao", label: "寺庙殿堂", icon: "🏯", count: 4 },
  { key: "wenhua", label: "文化展馆", icon: "🏛️", count: 8 },
];

const navLevel = ref("level1");
const navCategory = ref("");
const navSubCategory = ref("");
const failedImgNames = ref(new Set());

const navTitleLabelMap = {
  scenic: "景点推荐",
  area: "按区域浏览",
  type: "按类型浏览",
  photo: "拍照识景",
  qianshan: "前山区景点",
  houshan: "后山区景点",
  huqu: "湖区景点",
  guangchang: "广场区景点",
  foxiang: "佛像建筑",
  ziran: "自然景观",
  simiao: "寺庙殿堂",
  wenhua: "文化展馆",
};

const navTitle = computed(() => {
  if (navLevel.value === "level2") return navTitleLabelMap[navCategory.value] || "";
  if (navLevel.value === "level3") return navTitleLabelMap[navSubCategory.value] || "";
  return "探索工具";
});

function goLevel1() {
  navLevel.value = "level1";
  navCategory.value = "";
  navSubCategory.value = "";
}

function goLevel2(category) {
  navLevel.value = "level2";
  navCategory.value = category;
  navSubCategory.value = "";
  if (category === "scenic") {
    navSubCategory.value = "all";
  }
}

function goLevel3(subKey, subLabel) {
  navLevel.value = "level3";
  navSubCategory.value = subKey;
}

const currentLevel3Sections = computed(() => {
  const key = navSubCategory.value;
  if (!key) return [];

  if (key === "all" || key === "scenic") {
    const zoneOrder = ["qianshan", "houshan", "huqu", "guangchang"];
    const zoneLabels = { qianshan: "前山区", houshan: "后山区", huqu: "湖区", guangchang: "广场区" };
    return zoneOrder
      .map(z => ({
        label: zoneLabels[z],
        spots: scenicSpots.filter(s => s.zone === z),
      }))
      .filter(s => s.spots.length > 0);
  }

  if (["qianshan", "houshan", "huqu", "guangchang"].includes(key)) {
    const zoneLabels = { qianshan: "前山区", houshan: "后山区", huqu: "湖区", guangchang: "广场区" };
    return [{ label: zoneLabels[key], spots: scenicSpots.filter(s => s.zone === key) }];
  }

  if (["foxiang", "ziran", "simiao", "wenhua"].includes(key)) {
    const typeLabels = { foxiang: "佛像建筑", ziran: "自然景观", simiao: "寺庙殿堂", wenhua: "文化展馆" };
    return [{ label: typeLabels[key], spots: scenicSpots.filter(s => s.type === key) }];
  }

  return [];
});

function askSpot(spot) {
  if (chatStore.streaming) return;
  chatStore.sendMessage(`请详细介绍灵山景区的"${spot.name}"，包括历史背景、建筑特色和文化内涵。`, interactionStore.selectionPayload, sendOptions.base);
}

function onImgError(name) {
  failedImgNames.value.add(name);
  nextTick(() => {});
}

onMounted(() => { interactionStore.initialize(); loadAvatarConfig(); });
onBeforeUnmount(() => { chatStore.stopOutput(); audioPlayer.stop(); avatar.setState("idle"); });
</script>

<style scoped>
@import '../../assets/tourist-page.css';
</style>
