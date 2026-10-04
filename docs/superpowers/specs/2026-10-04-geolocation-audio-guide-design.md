# 靠近景点自动讲解（讲解机）功能设计

- 日期：2026-10-04
- 状态：已评审通过，待转实现计划
- 关联模块：景区地图页（`MapView.vue`）、数字人语音链路（`chat.py` / `tts`）、景点数据（`mapSpots.js` / `touristCatalog.js`）

## 1. 目标与范围

游客在景区地图页开启「自动讲解」后，系统持续获取其位置；当走进某景点触发半径内，地图页右下角自动浮出讲解卡片，并播放该景点的数字人语音讲解，模拟真实景区讲解机体验。

**范围内（本期做）**
- 地图页内的自动定位与就近触发播报
- 真实浏览器定位（含 WGS84→GCJ-02 纠偏）+ 模拟巡游兜底
- 复用现有数字人链路生成讲解文本与语音（后端一次性接口）
- 空闲时才触发、不打断用户当前对话/播放
- 后端不可用或 TTS 未配置时的降级播报

**范围外（YAGNI，本期不做）**
- 后端实时推送 / WebSocket
- 室内定位、蓝牙信标等硬件对接
- 多语言讲解
- 自定义讲解音色选择
- 与真实景区定位系统的对接
- 改造共享音频播放器新增暂停能力（见 §5.2）

## 2. 现状与关键约束（已核实）

| 项 | 结论 |
|---|---|
| 坐标体系 | `mapSpots.js` 的 `SPOT_COORDS` 为高德底图使用的 GCJ-02 近似坐标；浏览器 GPS 返回 WGS84，直接比对存在百米级偏移 |
| 音频播放器 | `useAudioPlayer.js` 为全局单例，对外仅有 `enqueue/flush/stop/isPlaying/mouthEnergy` 等；**无 pause/resume**（内部 `resume()` 是 AudioContext 唤醒，非播放暂停） |
| 空闲判定 | `MapView` 已有 `busy` prop（对话忙）；空闲 = `props.busy || audioPlayer.isPlaying === false` |
| 地图四角 | 左上=色层开关 `.map-color-toggle`，右上=图层切换 `.map-layer-switch`，左下=图例 `.map-legend`，**右下为 Leaflet attribution 默认位** |
| 讲解生成 | 后端有 `chat.py` 的 `build_pipeline`（RAG+LLM）与 `tts_service`；`welcome_cache.py` 提供了"文本+音频缓存"的可复用范式 |
| 定位协议门槛 | 非 localhost 的 HTTP 环境下 `navigator.geolocation` 为 `undefined`；自动播放需用户手势解锁 AudioContext |

## 3. 总体架构与新增单元

| 单元 | 位置 | 职责 | 依赖 |
|---|---|---|---|
| `useGeolocation` | `frontend/src/composables/useGeolocation.js` | 定位：真实 GPS + WGS84→GCJ-02 纠偏 + 模拟兜底 + 精度筛选 | `mapSpots.js` |
| `useNarration` | `frontend/src/composables/useNarration.js` | 测距 geofence + 触发状态机 + 空闲判定 + 补播重测 | `useGeolocation`、`useAudioPlayer` |
| `SpotNarrationCard` | `frontend/src/components/SpotNarrationCard.vue` | 浮层卡片：景点名/简介/进度/停止·重听·关闭 | 纯展示 |
| `guide.py` | `backend/app/api/guide.py` | 讲解生成接口，复用 RAG+LLM+TTS，按景点缓存 + singleflight | `build_pipeline`、`tts_service` |
| `narration.js` | `frontend/src/constants/narration.js` | 触发半径/冷却/巡游/兜底等配置常量 | 无 |

划分原则：每个单元单一职责、接口清晰、可独立测试。`MapView.vue` 只做"装配 + 渲染位置标记 + 挂浮层"，不塞业务逻辑。

## 4. 定位层 `useGeolocation`

```js
// 返回
{
  position: { lat, lng, accuracy, ts } | null,
  mode: 'idle' | 'real' | 'sim' | 'denied' | 'unsupported' | 'out_of_area' | 'low_accuracy',
  enabled, error,
  start(), stop(),
  setSimulated(lat, lng),
  startWalk(spotNames[]), stopWalk()
}
```

- **真实模式**：`navigator.geolocation.watchPosition({ enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 })`，拿到 WGS84 坐标后经内置 `wgs84ToGcj02()`（标准算法，无第三方依赖）转为 GCJ-02，与 `SPOT_COORDS` 对齐。
- **出区门槛**：若距 `LINGSHAN_CENTER` 超过 `OUT_OF_AREA_M`（默认 4000m），进入 `out_of_area` 状态，提示"检测到你不在景区范围，已切换模拟巡游"，并默认切模拟模式（可一键切回真实定位）。**这是演示可用性的关键**：答辩机位 GPS 通常正常但人在数百公里外，缺此门槛真实模式将永不触发。
- **精度门槛**：`accuracy > LOW_ACCURACY_M`（默认 160m）时进入 `low_accuracy` 状态，不参与触发判定，界面提示"定位精度不足"，避免桌面 WiFi 定位误触发。
- **模拟模式**：默认落在 `LINGSHAN_CENTER`；支持地图上手拖"我的位置"点；`startWalk(spotNames)` 沿给定景点折线插值巡游（默认取某条 `PRESET_ROUTES` 的景点序列），速度取 `SIM_WALK_SPEED_MPS`。
- **降级自动切换**：`unsupported` / `denied` / `out_of_area` 均自动切模拟模式并给出明确文案，保证演示不中断。
- **生命周期**：`MapView` unmount 时调用 `stop()`（内部 `clearWatch`）与 `stopWalk()`。

## 5. 触发状态机 `useNarration`

输入：`position`、`spots`、`isBusy()`。核心参数见 §7。

```js
{
  activeSpot,        // 当前浮层展示的景点
  completed,         // 已讲解景点集合
  status,            // 'idle' | 'pending_generation' | 'playing' | 'error'
  onTrigger,         // 触发回调（由 MapView 提供，负责请求讲解并播放）
  reset()
}
```

### 5.1 判定流程
1. 位置更新 → 用 haversine 找 `TRIGGER_RADIUS_M`（默认 80m）内最近景点。
2. 命中后若 `isBusy()` 为真：记入 `pendingSpot` 排队，**不打断**当前对话/播放。
3. 一旦空闲立即处理 `pendingSpot`，但**补播前必须重测距离**：若该景点已超出 `EXIT_RADIUS_M` 则丢弃，避免"过期播报"。
4. 未命中时，离开 `EXIT_RADIUS_M`（默认 120m）外则清除 `activeSpot`。

### 5.2 重复触发规则（消除自相矛盾）
- 采用**"离开才能重听"**语义：景点触发过一次后，只要未走出 `EXIT_RADIUS_M` 就不再触发；离开后再次进入即可重听。
- 另设 `COOLDOWN_MS`（默认 12000ms）小防抖，专门抑制 GPS 抖动导致的来回触发。
- 关闭「自动讲解」开关时整体 `reset()`：清 `activeSpot`/`pendingSpot`/`completed`，并停监听与播报。

### 5.3 卡片控制（与播放器能力对齐）
`useAudioPlayer` 无 pause/resume，故卡片按钮为 **停止 / 重听 / 关闭**，不承诺"暂停"。

## 6. 后端讲解接口 `/api/guide/narration`

```
POST /api/guide/narration
  body: { attraction: string }
  → {
      attraction, text,
      base64_audio, duration_ms, provider,
      cached, available, sources
    }
```

- **生成**：复用 `chat.py` 的 `build_pipeline`（RAG 检索 + LLM）生成 120–200 字讲解词，再用 `tts_service.synthesize(text)` 合成**整段音频**返回 base64。**不走 SSE**——整段音频便于浮层做停止/重听。
- **缓存**：按 `attraction + voice + model` 缓存（内存 + 可选磁盘，套用 `welcome_cache` 范式），二次靠近秒返回。
- **singleflight**：同一景点并发请求复用同一次生成，避免重复打 LLM/TTS。
- **预热（可选增强）**：服务启动后台任务预热 22 个景点缓存（有 Bailian 配额前提下），保证演示"秒开"。冷启动首次仍需等待，故前端必须有加载态（见 §8）。
- **降级不抛 5xx**：失败时返回 `available:false` 且尽量给 `text`（退化用 `touristCatalog.desc`），前端据此走浏览器朗读。
- **鉴权**：与其他游客端接口保持一致（复用同一依赖）。
- **性能要点**：确认 `build_pipeline` 存在非流式调用路径；pipeline 实例应复用而**非每请求重建**。

## 7. 配置常量 `narration.js`

| 常量 | 默认值 | 说明 |
|---|---|---|
| `TRIGGER_RADIUS_M` | 80 | 进入半径 |
| `EXIT_RADIUS_M` | 120 | 离开半径（滞回） |
| `COOLDOWN_MS` | 12000 | 抖动防抖冷却 |
| `OUT_OF_AREA_M` | 4000 | 距景区中心超出即判为不在景区 |
| `LOW_ACCURACY_M` | 160 | 精度差于此值不参与触发 |
| `SIM_WALK_SPEED_MPS` | 8 | 模拟巡游速度（演示友好，可倍速） |
| `SIM_WALK_ON_ARRIVE` | `'loop'` | 到达终点行为：`loop` / `stop` |
| `SIM_START_POINT` | `LINGSHAN_CENTER` | 模拟默认起点 |

## 8. 地图集成与浮层 UI

- **开关**：`MapView` 新增「开启自动讲解」按钮，同时作为解锁音频播放的用户手势与总开关；其 click 处理函数内**同步**调用 AudioContext resume（否则后续自动播放仍可能被拦）。
- **位置标记**：渲染"我的位置"标记（`L.circleMarker`）；模拟模式可拖动更新位置。
- **浮层**：`SpotNarrationCard` 停靠地图右下角，**`bottom: 28px` 抬高以避让 Leaflet attribution**。内容：景点 emoji + 名称 + 一句简介 + 进度条 + 停止 / 重听 / 关闭。
- **加载态**：首次生成期间卡片显示"讲解生成中…"，axios 超时设为 **30000ms**（高于默认 12s）。
- **播放**：统一走 `useAudioPlayer.enqueue(base64, durationMs, onEnded, text, onProgress, { allowBrowserSpeech: true })`。
- **不改动**：现有天气色层（`showColor` / `renderColorOverlay`）与 `emit("ask")` 链路保持不动。

## 9. 降级与错误处理

| 场景 | 处理 |
|---|---|
| geolocation 为 `undefined`（HTTP/非 localhost） | 进 `unsupported`，自动切模拟模式 + 提示 |
| 无定位权限 | 进 `denied`，自动切模拟模式 + 提示 |
| 定位成功但人不在景区（> `OUT_OF_AREA_M`） | 进 `out_of_area`，提示并默认切模拟，可切回 |
| 定位精度不足（> `LOW_ACCURACY_M`） | 进 `low_accuracy`，暂停触发判定 + 提示 |
| 后端 / TTS 不可用 | 浮层照常弹出，静态简介 + 浏览器朗读（`available:false`） |
| 浏览器拦截自动播放 | 开关本身即用户手势；仍失败则卡片给"点击播放" |
| 定位漂移抖动 | 进入/离开双半径滞回 + `COOLDOWN_MS` 防抖 |
| 忙时排队后走远 | 空闲补播前重测距离，超出 `EXIT_RADIUS_M` 即丢弃 |

## 10. 测试与验收标准

**功能验收**
1. 开启开关并授权后，走近景点（或开模拟巡游）能自动弹出浮层并播报数字人语音。
2. 正在对话 / 有语音播放时不打断；空闲后补播；补播前若已走远则不播。
3. 同景点在未离开范围内不重复触发；离开后再进入可重听。
4. 无权限 / 不支持 / 不在景区时自动进模拟模式并给出明确提示。
5. 后端不可用时改用静态简介 + 浏览器朗读，浮层正常。
6. 关闭开关即停止监听与播报并复位状态。

**技术验证手段**
- 后端：`fastapi.testclient` 打 `POST /api/guide/narration`，校验正常返回与 `available:false` 降级返回。
- 前端：Vite HMR 无编译错误。
- 真实定位路径：Chrome DevTools → Sensors 面板注入灵山附近的 **WGS84** 坐标，端到端验证纠偏算法与触发。
- 模拟路径：浏览器实测模拟巡游全链路。

## 11. 实施顺序建议

1. `narration.js` 常量 + `useGeolocation`（含纠偏与模拟兜底）
2. 后端 `guide.py` 接口 + 缓存 + singleflight + 注册到 `router.py`
3. `useNarration` 状态机
4. `SpotNarrationCard` 浮层组件
5. `MapView` 装配（开关 + 位置标记 + 浮层 + 加载态）
6. 降级路径与端到端验证
