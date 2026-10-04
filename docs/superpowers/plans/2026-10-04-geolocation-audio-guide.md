# 靠近景点自动讲解（讲解机）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 游客在地图页开启「自动讲解」后，走进景点触发半径即自动弹出浮层并播放该景点的数字人语音讲解。

**Architecture:** 前端两个新 composable（`useGeolocation` 负责定位与纠偏、`useNarration` 负责测距与触发状态机）+ 一个展示组件 `SpotNarrationCard`，由 `MapView.vue` 装配；后端新增 `POST /api/guide/narration`，复用既有 `build_pipeline` 的 RAG+LLM 生成讲解词，再用其 `tts_service` 合成整段音频，按景点缓存并做 singleflight。后端不可用时降级为静态简介 + 浏览器朗读。

**Tech Stack:** Vue 3 `<script setup>`、Element Plus、Leaflet 1.9、axios；FastAPI + Pydantic + SQLAlchemy async + pytest；原生 `navigator.geolocation` 与 `AudioContext`。

**设计文档:** `docs/superpowers/specs/2026-10-04-geolocation-audio-guide-design.md`

---

## 关键前置事实（已核实，实现时不要再假设）

1. `useAudioPlayer.js` 是全局单例，**没有 pause/resume**。对外可用的只有 `enqueue(base64, durationMs, onEnded, text, onProgress, playbackOptions)`、`flush()`、`stop()`、`isPlaying`、`mouthEnergy`。浮层按钮只能是 **停止 / 重听 / 关闭**。
2. `QAPipeline` **只有 `stream_chat()`，没有非流式方法**。要拿讲解全文，必须消费 `stream_chat` 的 SSE 事件，累积 `type === "text"` 且 `data.is_complete === true` 的那一条（见 `backend/app/services/qa/pipeline.py:709`）。传 `text_only=True` 可让 pipeline 跳过它自带的 TTS/数字人，改由我们自行合成。
3. `ChatRequest`：`query`(1–1000 字)、`session_id`(1–100 字)、`text_only` 均为必填/可用字段（`backend/app/schemas/chat.py:37`）。
4. `SPOT_COORDS`（`frontend/src/constants/mapSpots.js`）是 **GCJ-02 近似坐标**；`navigator.geolocation` 返回 **WGS84**，必须纠偏后再比距离。
5. `MapView.vue` 已有 `busy` prop 与 `emit("ask")`；地图四角占用：左上 `.map-color-toggle`、右上 `.map-layer-switch`、左下 `.map-legend`、**右下是 Leaflet attribution**，浮层需 `bottom: 28px` 避让。
6. `frontend/package.json` 已设 `"type": "module"`，纯函数可用 Node ESM 直接 import 做验证。

---

## Task 1: 前端常量与纯几何函数 `narration.js`

**Files:**
- Create: `frontend/src/constants/narration.js`
- Test: `c:\Users\李洵\.trae-cn\work\6ac22bd113b8e2bd43ab3b35\verify_narration_geo.mjs`（临时验证脚本，不进入仓库）

- [ ] **Step 1: 写失败的验证脚本**

创建 `c:\Users\李洵\.trae-cn\work\6ac22bd113b8e2bd43ab3b35\verify_narration_geo.mjs`：

```js
import { pathToFileURL } from "node:url";

const target = pathToFileURL("d:\\桌面\\作品产出合计\\软件杯\\frontend\\src\\constants\\narration.js").href;
const mod = await import(target);

const { haversineMeters, wgs84ToGcj02, findNearestSpot, TRIGGER_RADIUS_M } = mod;
let failed = 0;
const check = (name, cond) => { if (!cond) { failed += 1; console.error("FAIL:", name); } else { console.log("ok:", name); } };

// 1. haversine：灵山中心 -> 灵山大佛（同点附近，几百米量级）
const center = { lat: 31.4285, lng: 120.0998 };
const buddha = { lat: 31.4328, lng: 120.0996 };
const d = haversineMeters(center, buddha);
check("haversine 约 478m", d > 400 && d < 560);

// 2. 纠偏：华东地区 GCJ-02 相对 WGS84 应「纬度减小、经度增大」，偏移数百米
const g = wgs84ToGcj02(center.lat, center.lng);
check("纠偏后纬度减小", g.lat < center.lat);
check("纠偏后经度增大", g.lng > center.lng);
const shift = haversineMeters(center, g);
check("纠偏偏移 200~1200m", shift > 200 && shift < 1200);

// 3. 境外不纠偏
const overseas = wgs84ToGcj02(48.8566, 2.3522);
check("境外原样返回", overseas.lat === 48.8566 && overseas.lng === 2.3522);

// 4. 最近景点
const spots = [{ name: "灵山大佛", lat: 31.4328, lng: 120.0996 }, { name: "五灯湖", lat: 31.4245, lng: 120.1025 }];
const near = findNearestSpot({ lat: 31.4327, lng: 120.0997 }, spots);
check("命中最近景点灵山大佛", near && near.spot.name === "灵山大佛");
check("触发半径常量为 80", TRIGGER_RADIUS_M === 80);
check("候选结果为 null 当空数组", findNearestSpot(center, []) === null);

if (failed) { console.error(`\n${failed} 项失败`); process.exit(1); }
console.log("\n全部通过");
```

- [ ] **Step 2: 运行确认失败**

Run: `node "c:\Users\李洵\.trae-cn\work\6ac22bd113b8e2bd43ab3b35\verify_narration_geo.mjs"`
Expected: FAIL（`narration.js` 不存在，ERR_MODULE_NOT_FOUND）

- [ ] **Step 3: 实现 `narration.js`**

创建 `frontend/src/constants/narration.js`：

```js
// 靠近景点自动讲解（讲解机）配置与纯几何工具。
// 坐标链路：浏览器 GPS 为 WGS84，景区坐标与高德底图均为 GCJ-02，比距离前必须纠偏。

export const TRIGGER_RADIUS_M = 80;      // 进入半径
export const EXIT_RADIUS_M = 120;        // 离开半径（滞回，防抖）
export const COOLDOWN_MS = 12000;        // 抖动冷却
export const OUT_OF_AREA_M = 4000;       // 距景区中心超出即判为不在景区
export const LOW_ACCURACY_M = 160;       // 精度差于此值不参与触发
export const SIM_TICK_MS = 1000;         // 模拟巡游插值步长
export const SIM_WALK_SPEED_MPS = 8;     // 模拟巡游速度（演示友好）
export const SIM_WALK_ON_ARRIVE = "loop"; // 到达终点：loop | stop

const EARTH_RADIUS_M = 6371008.8;

const toRad = (deg) => (deg * Math.PI) / 180;

/** 两点球面距离（米）。 */
export function haversineMeters(a, b) {
  if (!a || !b) return Infinity;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)));
}

const GCJ_A = 6378245.0;
const GCJ_EE = 0.00669342162296594323;

function outOfChina(lat, lng) {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271;
}

function transformLat(x, y) {
  let ret = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
  ret += ((20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2) / 3;
  ret += ((20 * Math.sin(y * Math.PI) + 40 * Math.sin((y / 3) * Math.PI)) * 2) / 3;
  ret += ((160 * Math.sin((y / 12) * Math.PI) + 320 * Math.sin((y * Math.PI) / 30)) * 2) / 3;
  return ret;
}

function transformLng(x, y) {
  let ret = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
  ret += ((20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2) / 3;
  ret += ((20 * Math.sin(x * Math.PI) + 40 * Math.sin((x / 3) * Math.PI)) * 2) / 3;
  ret += ((150 * Math.sin((x / 12) * Math.PI) + 300 * Math.sin((x * Math.PI) / 30)) * 2) / 3;
  return ret;
}

/** WGS84 -> GCJ-02（标准算法，中国大陆境内生效，境外原样返回）。 */
export function wgs84ToGcj02(lat, lng) {
  if (outOfChina(lat, lng)) return { lat, lng };
  let dLat = transformLat(lng - 105.0, lat - 35.0);
  let dLng = transformLng(lng - 105.0, lat - 35.0);
  const radLat = (lat / 180.0) * Math.PI;
  let magic = Math.sin(radLat);
  magic = 1 - GCJ_EE * magic * magic;
  const sqrtMagic = Math.sqrt(magic);
  dLat = (dLat * 180.0) / (((GCJ_A * (1 - GCJ_EE)) / (magic * sqrtMagic)) * Math.PI);
  dLng = (dLng * 180.0) / ((GCJ_A / sqrtMagic) * Math.cos(radLat) * Math.PI);
  return { lat: lat + dLat, lng: lng + dLng };
}

/** 在候选中找距离最近的一个景点，返回 { spot, distance }；空候选返回 null。 */
export function findNearestSpot(position, spots) {
  if (!position || !Array.isArray(spots) || spots.length === 0) return null;
  let best = null;
  for (const spot of spots) {
    const distance = haversineMeters(position, spot);
    if (!best || distance < best.distance) best = { spot, distance };
  }
  return best;
}
```

- [ ] **Step 4: 运行确认通过**

Run: `node "c:\Users\李洵\.trae-cn\work\6ac22bd113b8e2bd43ab3b35\verify_narration_geo.mjs"`
Expected: 全部通过

- [ ] **Step 5: 提交**

```bash
git add frontend/src/constants/narration.js
git commit -m "feat(guide): 新增讲解机配置常量与 WGS84 纠偏几何工具"
```

---

## Task 2: 后端讲解接口 `POST /api/guide/narration`

**Files:**
- Create: `backend/app/api/guide.py`
- Modify: `backend/app/api/router.py:3` 与文件末尾
- Test: `backend/app/tests/test_guide_narration_api.py`

- [ ] **Step 1: 写失败的测试**

创建 `backend/app/tests/test_guide_narration_api.py`：

```python
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import guide as guide_api
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.services.qa.stream_events import StreamEvent
from app.services.tts.base import TTSAudio


class _FakeTTS:
    async def synthesize(self, _text: str) -> TTSAudio:
        return TTSAudio(base64_audio="QUJD", duration_ms=1234, provider="fake")


class _FakePipeline:
    def __init__(self, *, text: str = "灵山大佛高88米，是灵山胜境的标志性景观。"):
        self._text = text
        self.tts_service = _FakeTTS()

    async def stream_chat(self, _payload):
        yield StreamEvent(type="status", data={"text": "..."})
        yield StreamEvent(type="text", data={"text": self._text, "is_complete": True})


def _build_client(monkeypatch, *, pipeline=None, fail_build: bool = False) -> TestClient:
    app = FastAPI()
    app.include_router(guide_api.router, prefix="/api/guide")

    async def override_session():
        return object()

    def override_settings() -> Settings:
        return Settings(llm_provider="stub", tts_provider="stub")

    async def fake_build_pipeline(*_args, **_kwargs):
        if fail_build:
            raise RuntimeError("build failed")
        return pipeline if pipeline is not None else _FakePipeline()

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_app_settings] = override_settings
    monkeypatch.setattr(guide_api, "build_pipeline", fake_build_pipeline)
    monkeypatch.setattr(guide_api, "_NARRATION_CACHE", {})
    return TestClient(app)


def test_narration_returns_text_and_audio(monkeypatch) -> None:
    client = _build_client(monkeypatch)
    response = client.post("/api/guide/narration", json={"attraction": "灵山大佛"})

    assert response.status_code == 200
    body = response.json()
    assert body["attraction"] == "灵山大佛"
    assert "88米" in body["text"]
    assert body["base64_audio"] == "QUJD"
    assert body["duration_ms"] == 1234
    assert body["available"] is True
    assert body["cached"] is False


def test_narration_second_call_is_cached(monkeypatch) -> None:
    pipeline = _FakePipeline()
    calls = {"n": 0}

    original = pipeline.stream_chat

    async def counting(_payload):
        calls["n"] += 1
        async for event in original(_payload):
            yield event

    pipeline.stream_chat = counting
    client = _build_client(monkeypatch, pipeline=pipeline)
    client.post("/api/guide/narration", json={"attraction": "灵山大佛"})
    second = client.post("/api/guide/narration", json={"attraction": "灵山大佛"})

    assert calls["n"] == 1
    assert second.json()["cached"] is True


def test_narration_degrades_without_5xx_on_pipeline_failure(monkeypatch) -> None:
    client = _build_client(monkeypatch, fail_build=True)
    response = client.post("/api/guide/narration", json={"attraction": "灵山大佛"})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["reason"] == "pipeline_unavailable"
    assert body["text"] == ""


def test_narration_degrades_when_llm_returns_empty(monkeypatch) -> None:
    client = _build_client(monkeypatch, pipeline=_FakePipeline(text=""))
    response = client.post("/api/guide/narration", json={"attraction": "灵山大佛"})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["reason"] == "llm_unavailable"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest backend/app/tests/test_guide_narration_api.py -v`（在项目根目录，需已激活后端虚拟环境）
Expected: FAIL — `ModuleNotFoundError: No module named 'app.api.guide'`

- [ ] **Step 3: 实现 `guide.py`**

创建 `backend/app/api/guide.py`：

```python
"""景点自动讲解接口。

复用既有 QA pipeline（RAG + LLM）生成讲解词，再用其 TTS 服务合成整段音频：

- 走 ``stream_chat(text_only=True)`` 累积全文，不新增非流式 pipeline 方法。
- 结果按 ``景点|音色|模型`` 缓存并做 singleflight，二次靠近秒返回。
- 任何失败都降级为 ``available=False``，不抛 5xx，由前端改用静态简介 + 浏览器朗读。
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.chat import build_pipeline
from app.core.config import Settings
from app.core.deps import get_app_settings, get_db_session
from app.schemas.chat import ChatRequest

router = APIRouter()
logger = logging.getLogger(__name__)

NARRATION_PROMPT = (
    "你是一名景区讲解员。请用口语化、亲切的讲解员口吻介绍景点「{name}」，"
    "控制在180字以内，只讲景点本身的历史、特色与看点，"
    "不要提客流与天气，不要提问，不要分点罗列。"
)

_CITATION_RE = re.compile(r"[\[【]\s*\d+\s*[\]】]")
_NARRATION_CACHE: dict[str, dict[str, Any]] = {}
_LOCK_REGISTRY: dict[str, asyncio.Lock] = {}


class NarrationRequest(BaseModel):
    attraction: str = Field(min_length=1, max_length=50)
    tts_voice: str | None = None


def _cache_key(attraction: str, voice: str, model: str) -> str:
    return f"{attraction}|{voice}|{model}"


def _get_lock(key: str) -> asyncio.Lock:
    lock = _LOCK_REGISTRY.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _LOCK_REGISTRY[key] = lock
    return lock


def _clean(text: str) -> str:
    cleaned = _CITATION_RE.sub("", text or "")
    cleaned = cleaned.replace("**", "").replace("##", "")
    return cleaned.strip()


def _degraded(attraction: str, reason: str) -> dict[str, Any]:
    return {
        "attraction": attraction,
        "text": "",
        "base64_audio": "",
        "duration_ms": 0,
        "provider": "",
        "cached": False,
        "available": False,
        "reason": reason,
    }


async def _generate(
    session: AsyncSession,
    settings: Settings,
    attraction: str,
    tts_voice: str | None,
) -> dict[str, Any]:
    try:
        pipeline = await build_pipeline(session, settings, tts_voice_preset=tts_voice)
    except Exception:
        logger.exception("Narration pipeline build failed for %s", attraction)
        return _degraded(attraction, "pipeline_unavailable")

    text = ""
    try:
        request = ChatRequest(
            query=NARRATION_PROMPT.format(name=attraction),
            session_id=f"narration-{attraction}",
            text_only=True,
        )
        async for event in pipeline.stream_chat(request):
            if event.type == "text" and event.data.get("is_complete"):
                text = event.data.get("text") or text
    except Exception:
        logger.exception("Narration generation failed for %s", attraction)

    text = _clean(text)
    if not text:
        return _degraded(attraction, "llm_unavailable")

    base64_audio = ""
    duration_ms = 0
    provider = ""
    try:
        audio = await pipeline.tts_service.synthesize(text)
        base64_audio = audio.base64_audio
        duration_ms = audio.duration_ms
        provider = audio.provider
    except Exception:
        logger.exception("Narration TTS failed for %s", attraction)

    return {
        "attraction": attraction,
        "text": text,
        "base64_audio": base64_audio,
        "duration_ms": duration_ms,
        "provider": provider,
        "cached": False,
        "available": True,
        "reason": "" if base64_audio else "tts_unavailable",
    }


@router.post("/narration", summary="生成景点自动讲解文本与语音")
async def create_narration(
    payload: NarrationRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    attraction = payload.attraction.strip()
    voice = payload.tts_voice or settings.tts_voice
    key = _cache_key(attraction, voice, settings.llm_model or "stub")

    cached = _NARRATION_CACHE.get(key)
    if cached is not None:
        return {**cached, "cached": True}

    async with _get_lock(key):
        cached = _NARRATION_CACHE.get(key)
        if cached is not None:
            return {**cached, "cached": True}
        result = await _generate(session, settings, attraction, payload.tts_voice)
        if result["available"]:
            _NARRATION_CACHE[key] = result
        return result
```

- [ ] **Step 4: 注册路由**

修改 `backend/app/api/router.py` 第 3 行，把 `guide` 加入导入：

```python
from app.api import admin, auth, chat, display_assets, guide, insights, knowledge, quick_select, recommend, vision, voice, weather
```

并在文件末尾（`weather` 之后）追加：

```python
api_router.include_router(guide.router, prefix="/guide", tags=["guide"])
```

- [ ] **Step 5: 运行测试确认通过**

Run: `python -m pytest backend/app/tests/test_guide_narration_api.py -v`
Expected: 4 passed

- [ ] **Step 6: 回归既有聊天接口测试，确认导入未破坏**

Run: `python -m pytest backend/app/tests/test_chat_stream_api.py -v`
Expected: 2 passed

- [ ] **Step 7: 提交**

```bash
git add backend/app/api/guide.py backend/app/api/router.py backend/app/tests/test_guide_narration_api.py
git commit -m "feat(guide): 新增景点自动讲解接口，复用 QA pipeline 并做缓存与降级"
```

---

## Task 3: 前端接口封装 `api/narration.js`

**Files:**
- Create: `frontend/src/api/narration.js`

- [ ] **Step 1: 实现**

创建 `frontend/src/api/narration.js`：

```js
import http from "./http";

/**
 * 获取景点自动讲解文本与语音（后端复用数字人链路，密钥不出服务端）。
 * 首次生成需 LLM + TTS 串行，超时放宽到 30s。
 * @param {string} attraction 景点名称
 * @param {string} [ttsVoice] 可选音色
 * @returns {Promise<{attraction:string,text:string,base64_audio:string,duration_ms:number,provider:string,cached:boolean,available:boolean,reason:string}>}
 */
export async function fetchSpotNarration(attraction, ttsVoice) {
  const payload = { attraction };
  if (ttsVoice) payload.tts_voice = ttsVoice;
  const { data } = await http.post("/guide/narration", payload, { timeout: 30000 });
  return data;
}
```

- [ ] **Step 2: 确认无语法错误**

Run: `npm --prefix frontend run build`
Expected: 构建成功（此时新文件尚未被引用，仅验证可被 Vite 解析；若构建耗时过长可跳过，改由 Task 7 的 dev server 验证）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/api/narration.js
git commit -m "feat(guide): 新增讲解接口前端封装"
```

---

## Task 4: 定位 composable `useGeolocation.js`

**Files:**
- Create: `frontend/src/composables/useGeolocation.js`
- 依赖: `frontend/src/constants/narration.js`、`frontend/src/constants/mapSpots.js`

- [ ] **Step 1: 实现**

创建 `frontend/src/composables/useGeolocation.js`：

```js
import { ref, shallowRef } from "vue";
import { LINGSHAN_CENTER } from "../constants/mapSpots";
import {
  haversineMeters,
  wgs84ToGcj02,
  OUT_OF_AREA_M,
  LOW_ACCURACY_M,
  SIM_TICK_MS,
  SIM_WALK_SPEED_MPS,
  SIM_WALK_ON_ARRIVE,
} from "../constants/narration";

const CENTER = { lat: LINGSHAN_CENTER[0], lng: LINGSHAN_CENTER[1] };

/**
 * 定位层：真实浏览器定位（WGS84 自动纠偏为 GCJ-02）+ 模拟巡游兜底。
 * mode: idle | real | sim | denied | unsupported | out_of_area | low_accuracy
 */
export function useGeolocation() {
  const position = ref(null);
  const mode = ref("idle");
  const error = ref("");
  const enabled = ref(false);
  const accuracyPoor = ref(false);

  let watchId = null;
  let walkTimer = null;
  let walkPath = [];
  let walkIndex = 0;
  let walkSegmentProgress = 0;

  function setPosition(lat, lng, accuracy = 0) {
    position.value = { lat, lng, accuracy, ts: Date.now() };
  }

  function setSimulated(lat, lng) {
    setPosition(lat, lng, 5);
  }

  function evaluate(raw) {
    const fixed = wgs84ToGcj02(raw.lat, raw.lng);
    const accuracy = Number(raw.accuracy) || 0;
    setPosition(fixed.lat, fixed.lng, accuracy);

    if (haversineMeters(fixed, CENTER) > OUT_OF_AREA_M) {
      accuracyPoor.value = false;
      mode.value = "out_of_area";
      error.value = "检测到你不在景区范围，已切换模拟巡游";
      return;
    }
    if (accuracy > LOW_ACCURACY_M) {
      accuracyPoor.value = true;
      mode.value = "low_accuracy";
      error.value = "定位精度不足，暂不触发讲解";
      return;
    }
    accuracyPoor.value = false;
    mode.value = "real";
    error.value = "";
  }

  function onSuccess(pos) {
    if (mode.value === "sim") return; // 手动切到模拟后忽略真实回调
    evaluate(pos.coords);
  }

  function onError(err) {
    if (mode.value === "sim") return;
    mode.value = err && err.code === 1 ? "denied" : "unsupported";
    error.value = mode.value === "denied" ? "定位权限被拒绝，已切换模拟巡游" : "当前环境不支持定位，已切换模拟巡游";
    startSimulated();
  }

  function startReal() {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      mode.value = "unsupported";
      error.value = "当前环境不支持定位，已切换模拟巡游";
      startSimulated();
      return;
    }
    stopWalk();
    mode.value = "real";
    watchId = navigator.geolocation.watchPosition(onSuccess, onError, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 5000,
    });
  }

  function startSimulated(lat, lng) {
    if (watchId !== null && typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
    mode.value = "sim";
    error.value = "";
    accuracyPoor.value = false;
    if (Number.isFinite(lat) && Number.isFinite(lng)) setSimulated(lat, lng);
    else if (!position.value) setSimulated(CENTER.lat, CENTER.lng);
  }

  function startWalk(spots) {
    stopWalk();
    const path = (spots || []).filter((s) => Number.isFinite(s.lat) && Number.isFinite(s.lng));
    if (path.length < 2) return;
    startSimulated(path[0].lat, path[0].lng);
    walkPath = path;
    walkIndex = 0;
    walkSegmentProgress = 0;
    walkTimer = setInterval(() => {
      const from = walkPath[walkIndex];
      const to = walkPath[walkIndex + 1];
      if (!to) { stopWalk(); return; }
      const total = haversineMeters(from, to);
      const stepMeters = SIM_WALK_SPEED_MPS * (SIM_TICK_MS / 1000);
      walkSegmentProgress += total > 0 ? stepMeters / total : 1;

      if (walkSegmentProgress >= 1) {
        walkIndex += 1;
        walkSegmentProgress = 0;
        if (walkIndex >= walkPath.length - 1) {
          if (SIM_WALK_ON_ARRIVE === "loop") walkIndex = 0;
          else { const last = walkPath[walkPath.length - 1]; setSimulated(last.lat, last.lng); stopWalk(); return; }
        }
        const nextFrom = walkPath[walkIndex];
        setSimulated(nextFrom.lat, nextFrom.lng);
        return;
      }
      setSimulated(from.lat + (to.lat - from.lat) * walkSegmentProgress, from.lng + (to.lng - from.lng) * walkSegmentProgress);
    }, SIM_TICK_MS);
  }

  function stopWalk() {
    if (walkTimer) { clearInterval(walkTimer); walkTimer = null; }
    walkPath = [];
    walkIndex = 0;
    walkSegmentProgress = 0;
  }

  function start() {
    enabled.value = true;
    startReal();
  }

  function stop() {
    enabled.value = false;
    if (watchId !== null && typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
    stopWalk();
    mode.value = "idle";
  }

  return { position, mode, error, enabled, accuracyPoor, start, stop, startSimulated, setSimulated, startWalk, stopWalk };
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/composables/useGeolocation.js
git commit -m "feat(guide): 新增定位 composable，含 WGS84 纠偏、在园判定与模拟巡游"
```

---

## Task 5: 触发状态机 `useNarration.js`

**Files:**
- Create: `frontend/src/composables/useNarration.js`
- 依赖: `narration.js`、可选注入 `isBusy`

- [ ] **Step 1: 实现**

创建 `frontend/src/composables/useNarration.js`：

```js
import { ref } from "vue";
import { haversineMeters, findNearestSpot, TRIGGER_RADIUS_M, EXIT_RADIUS_M, COOLDOWN_MS } from "../constants/narration";

/**
 * 触发状态机：进入 TRIGGER_RADIUS_M 触发，离开 EXIT_RADIUS_M 后才可重听。
 * 忙时不打断，记入 pendingSpot；空闲后补播前会重测距离，走远则丢弃。
 */
export function useNarration({ getPosition, getSpots, isBusy, onTrigger }) {
  const activeSpot = ref(null);
  const completed = ref([]);
  const status = ref("idle");
  const lastTriggeredAt = ref(0);

  let pendingSpot = null;
  let insideNames = new Set();

  function distanceTo(spot, position) {
    return haversineMeters(position, spot);
  }

  function update() {
    const position = getPosition();
    const spots = getSpots() || [];
    if (!position) return;

    const nearest = findNearestSpot(position, spots);
    const nearestDistance = nearest ? nearest.distance : Infinity;

    // 更新 inside 集合（滞回：进入用 TRIGGER，退出用 EXIT）
    // 走出 EXIT 半径时同时清除「已触发」标记，使再次进入可重听
    for (const spot of spots) {
      const d = distanceTo(spot, position);
      if (d <= TRIGGER_RADIUS_M) {
        insideNames.add(spot.name);
      } else if (d > EXIT_RADIUS_M) {
        insideNames.delete(spot.name);
        insideNames.delete(`${spot.name}__done`);
      }
    }

    if (activeSpot.value && insideNames.has(activeSpot.value.name)) {
      // 仍在当前景点范围内，保持
      return;
    }
    if (activeSpot.value && !insideNames.has(activeSpot.value.name)) {
      activeSpot.value = null;
      if (status.value === "playing") status.value = "idle";
    }

    if (!nearest || nearestDistance > TRIGGER_RADIUS_M) return;
    const spot = nearest.spot;
    if (insideNames.has(`${spot.name}__done`)) return; // 已在本轮区间内触发过

    const now = Date.now();
    if (now - lastTriggeredAt.value < COOLDOWN_MS) return;

    trigger(spot);
  }

  function trigger(spot) {
    insideNames.add(`${spot.name}__done`);
    lastTriggeredAt.value = Date.now();
    if (isBusy && isBusy()) {
      pendingSpot = spot;
      status.value = "pending";
      return;
    }
    fire(spot);
  }

  function fire(spot) {
    activeSpot.value = spot;
    if (!completed.value.includes(spot.name)) completed.value = [...completed.value, spot.name];
    status.value = "playing";
    Promise.resolve(onTrigger && onTrigger(spot)).finally(() => {
      if (status.value === "playing") status.value = "idle";
    });
  }

  /** 由外部在“忙 -> 空闲”时驱动。 */
  function drainPending() {
    if (!pendingSpot) return;
    if (isBusy && isBusy()) return;
    const spot = pendingSpot;
    const position = getPosition();
    pendingSpot = null;
    status.value = "idle";
    if (!position) return;
    if (haversineMeters(position, spot) > EXIT_RADIUS_M) return; // 已走远，丢弃
    fire(spot);
  }

  function reset() {
    activeSpot.value = null;
    completed.value = [];
    status.value = "idle";
    pendingSpot = null;
    insideNames = new Set();
    lastTriggeredAt.value = 0;
  }

  return { activeSpot, completed, status, update, drainPending, reset, fire, trigger };
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/composables/useNarration.js
git commit -m "feat(guide): 新增讲解触发状态机（滞回、冷却、忙时排队与补播重测）"
```

---

## Task 6: 浮层组件 `SpotNarrationCard.vue`

**Files:**
- Create: `frontend/src/components/SpotNarrationCard.vue`

- [ ] **Step 1: 实现**

创建 `frontend/src/components/SpotNarrationCard.vue`：

```vue
<template>
  <div class="narration-card" role="status">
    <div class="nc-head">
      <span class="nc-emoji">{{ spot.emoji }}</span>
      <div class="nc-title">
        <strong>{{ spot.name }}</strong>
        <small>{{ subtitle }}</small>
      </div>
      <button type="button" class="nc-close" aria-label="关闭讲解" @click="$emit('close')">×</button>
    </div>
    <p class="nc-desc">{{ text || spot.desc }}</p>
    <div class="nc-track"><div class="nc-fill" :style="{ width: `${Math.round(progress * 100)}%` }"></div></div>
    <div class="nc-actions">
      <button type="button" class="nc-btn" :disabled="loading" @click="$emit('replay')">
        {{ loading ? "讲解生成中…" : "重听" }}
      </button>
      <button type="button" class="nc-btn ghost" :disabled="!playing" @click="$emit('stop')">停止</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  spot: { type: Object, required: true },
  text: { type: String, default: "" },
  progress: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  playing: { type: Boolean, default: false },
  degraded: { type: Boolean, default: false },
});
defineEmits(["close", "replay", "stop"]);

const subtitle = computed(() => (props.degraded ? "离线讲解 · 浏览器朗读" : "数字人语音讲解"));
</script>

<style scoped>
.narration-card { position: absolute; right: 8px; bottom: 28px; z-index: 500; width: 240px; padding: 10px 11px; border-radius: 10px; border: 1px solid rgba(45, 90, 75, 0.18); background: rgba(255, 255, 255, 0.97); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.14); }
.nc-head { display: flex; align-items: center; gap: 8px; }
.nc-emoji { font-size: 20px; line-height: 1; }
.nc-title { display: flex; flex-direction: column; min-width: 0; flex: 1; }
.nc-title strong { font-size: 13px; color: #2c3a33; }
.nc-title small { font-size: 11px; color: #94a39c; }
.nc-close { border: 0; background: transparent; font-size: 16px; line-height: 1; color: #94a39c; cursor: pointer; }
.nc-desc { margin: 7px 0 8px; font-size: 12px; line-height: 1.6; color: #5a6b62; max-height: 54px; overflow: hidden; }
.nc-track { height: 4px; border-radius: 999px; background: #eaf0eb; overflow: hidden; margin-bottom: 8px; }
.nc-fill { height: 100%; background: linear-gradient(90deg, #4d7565, #2d5a4b); transition: width 0.2s linear; }
.nc-actions { display: flex; gap: 6px; }
.nc-btn { flex: 1; min-height: 28px; border-radius: 7px; border: 1px solid #2d5a4b; background: #2d5a4b; color: #f3f7f4; font-size: 12px; cursor: pointer; }
.nc-btn:disabled { opacity: 0.5; cursor: default; }
.nc-btn.ghost { background: transparent; color: #2d5a4b; }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/SpotNarrationCard.vue
git commit -m "feat(guide): 新增自动讲解浮层组件"
```

---

## Task 7: 地图页装配

**Files:**
- Modify: `frontend/src/views/tourist/MapView.vue`

- [ ] **Step 1: 模板：加开关、位置标记容器与浮层**

在 `MapView.vue` 的 `.map-stage` 内、`.map-color-toggle` 之后插入自动讲解开关与浮层（浮层用组件）：

```vue
      <button type="button" class="map-narrate-toggle" :class="{ active: narrateOn }" :aria-pressed="narrateOn" @click="toggleNarrate">
        {{ narrateOn ? "自动讲解中" : "开启自动讲解" }}
      </button>
      <div class="map-geo-tip" v-if="narrateOn && geo.error">{{ geo.error }}</div>
      <SpotNarrationCard
        v-if="narration.activeSpot.value"
        :spot="narration.activeSpot.value"
        :text="narrationText"
        :progress="narrationProgress"
        :loading="narrationLoading"
        :playing="audio.isPlaying.value"
        :degraded="narrationDegraded"
        @replay="playNarration(narration.activeSpot.value)"
        @stop="stopNarration"
        @close="closeNarration"
      />
```

在 `.map-live` 之前插入模拟巡游控制（演示用）：

```vue
    <div class="map-narrate-bar" v-if="narrateOn">
      <button type="button" @click="toggleWalk">{{ walking ? "停止巡游" : "模拟巡游" }}</button>
      <span>模式：{{ modeLabel }}</span>
    </div>
```

- [ ] **Step 2: 脚本：导入与装配**

在 `<script setup>` 顶部补充导入：

```js
import SpotNarrationCard from "../../components/SpotNarrationCard.vue";
import { useAudioPlayer } from "../../composables/useAudioPlayer";
import { useGeolocation } from "../../composables/useGeolocation";
import { useNarration } from "../../composables/useNarration";
import { fetchSpotNarration } from "../../api/narration";
```

在 `/* ---------- 交给数字人导游 ---------- */` 之前追加装配逻辑：

```js
/* ---------- 自动讲解（讲解机） ---------- */
const audio = useAudioPlayer();
const geo = useGeolocation();
const narrateOn = ref(false);
const narrationText = ref("");
const narrationProgress = ref(0);
const narrationLoading = ref(false);
const narrationDegraded = ref(false);

const narration = useNarration({
  getPosition: () => geo.position.value,
  getSpots: () => spots,
  isBusy: () => props.busy || audio.isPlaying.value,
  onTrigger: (spot) => playNarration(spot),
});

const modeLabel = computed(() => {
  const map = { real: "真实定位", sim: "模拟巡游", denied: "模拟（无权限）", unsupported: "模拟（不支持）", out_of_area: "模拟（不在景区）", low_accuracy: "精度不足", idle: "未定位" };
  return map[geo.mode.value] || geo.mode.value;
});
const walking = ref(false);

async function playNarration(spot) {
  if (!spot) return;
  narrationLoading.value = true;
  narrationDegraded.value = false;
  narrationText.value = spot.desc || "";
  narrationProgress.value = 0;

  let data = null;
  try {
    data = await fetchSpotNarration(spot.name);
  } catch {
    data = null;
  }

  narrationLoading.value = false;
  if (data && data.available) {
    narrationText.value = data.text || spot.desc || "";
    narrationDegraded.value = !data.base64_audio;
    audio.enqueue(data.base64_audio, data.duration_ms || 60000, () => finishNarration(), data.text, (p) => { narrationProgress.value = p; }, { allowBrowserSpeech: true });
  } else {
    narrationDegraded.value = true;
    const fallback = spot.desc || `${spot.name}`;
    narrationText.value = fallback;
    audio.enqueue("", Math.max(fallback.length * 180, 1200), () => finishNarration(), fallback, (p) => { narrationProgress.value = p; }, { allowBrowserSpeech: true });
  }
}

function finishNarration() {
  narrationProgress.value = 1;
  narration.status.value = "idle";
  narration.drainPending();
}

function stopNarration() {
  audio.stop();
  narrationProgress.value = 0;
  narration.status.value = "idle";
}

function closeNarration() {
  stopNarration();
  narration.activeSpot.value = null;
}

async function toggleNarrate() {
  narrateOn.value = !narrateOn.value;
  if (narrateOn.value) {
    // 用户手势内同步解锁 AudioContext，保证后续自动播放不被拦截
    try { await audio.flush(); audio.stop(); } catch {}
    geo.start();
  } else {
    geo.stop();
    closeNarration();
    narration.reset();
    walking.value = false;
  }
}

function toggleWalk() {
  if (walking.value) { geo.stopWalk(); walking.value = false; return; }
  const path = activeRoute.value ? activeRoute.value.spots.map(resolveSpot).filter(Boolean) : spots;
  geo.startWalk(path);
  walking.value = true;
}
```

- [ ] **Step 3: 监听驱动**

在 `onMounted` 中启动定时驱动（用 `setInterval` 而非 watch position，避免高频重算）：

```js
let narrateTimer = null;
```

在 `onMounted(() => { nextTick(initMap); })` 改为：

```js
onMounted(() => {
  nextTick(initMap);
  narrateTimer = setInterval(() => {
    if (!narrateOn.value) return;
    narration.update();
    narration.drainPending();
  }, 900);
});
```

在 `onBeforeUnmount` 中补充：

```js
  if (narrateTimer) { clearInterval(narrateTimer); narrateTimer = null; }
  geo.stop();
```

- [ ] **Step 4: 渲染“我的位置”标记**

在 `initMap()` 末尾（`renderColorOverlay();` 之后）追加一个 watch，跟随 geo.position 刷新标记：

```js
let meMarker = null;
watch(() => geo.position.value, (pos) => {
  if (!map || !pos) return;
  const latlng = [pos.lat, pos.lng];
  if (!meMarker) {
    meMarker = L.circleMarker(latlng, { radius: 7, color: "#fff", weight: 2, fillColor: "#2f7d7d", fillOpacity: 0.95 }).addTo(map);
  } else {
    meMarker.setLatLng(latlng);
  }
});
```

- [ ] **Step 5: 样式**

在 `<style scoped>` 末尾追加：

```css
.map-narrate-toggle { position: absolute; top: 48px; left: 8px; z-index: 400; min-height: 32px; padding: 4px 12px; border-radius: 6px; border: 1px solid rgba(45, 90, 75, 0.18); background: rgba(255, 255, 255, 0.94); box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); font-size: 12px; color: #6b7a72; }
.map-narrate-toggle.active { background: #c49b4c; border-color: #c49b4c; color: #fff; font-weight: 600; }
.map-geo-tip { position: absolute; top: 84px; left: 8px; z-index: 400; max-width: 60%; padding: 4px 9px; border-radius: 6px; background: rgba(180, 85, 45, 0.92); color: #fff; font-size: 11px; }
.map-narrate-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 12px; color: #6b7a72; }
.map-narrate-bar button { min-height: 28px; padding: 3px 12px; border-radius: 7px; border: 1px solid #2d5a4b; background: #fff; color: #2d5a4b; font-size: 12px; }
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/views/tourist/MapView.vue
git commit -m "feat(guide): 地图页装配自动讲解开关、位置标记、浮层与模拟巡游"
```

---

## Task 8: 端到端联调与降级验证

**Files:**
- 无新增（验证任务）

- [ ] **Step 1: 启动后端**

Run（后台）：`python -m uvicorn app.main:app --reload --port 8000`（cwd 设为 `backend`）
Expected: `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 2: 直接打讲解接口**

Run: `curl -X POST http://127.0.0.1:8000/api/guide/narration -H "Content-Type: application/json" -d "{\"attraction\":\"灵山大佛\"}"`
Expected: HTTP 200；未配置 LLM/TTS 时 `available=false` + `reason`；已配置时返回 `text` 与 `base64_audio`

- [ ] **Step 3: 启动前端并实测**

Run（后台）：`npm --prefix frontend run dev`
Expected: Vite 启动无编译错误

浏览器操作：
1. 进入地图页，点「开启自动讲解」
2. 点「模拟巡游」，选择任一含多景点的路线
3. 观察：靠近景点时右下角浮出卡片并播报；卡片显示进度；点「停止」中断；点「重听」重播；点「关闭」消失
4. 走远后再次靠近同一景点可重听；停留在范围内不重复播报

- [ ] **Step 4: 验证真实定位纠偏路径**

Chrome DevTools → Sensors → Location 选择 `Other`，填入 **WGS84** 坐标 `31.4285, 120.0998`（灵山中心），刷新后确认「模式：真实定位」，并逐步把纬度调到 `31.4328` 观察在大佛附近触发。

- [ ] **Step 5: 验证降级路径**

1. 停掉后端，重新开启自动讲解 → 卡片仍弹出，`degraded=true`，使用浏览器朗读
2. 在浏览器设置中拒绝定位权限 → 模式变为「模拟（无权限）」，功能可用
3. 填入远离景区的坐标（如北京）→ 模式变为「模拟（不在景区）」

- [ ] **Step 6: 回归既有功能**

确认地图页原有「景区颜色」色层开关、图层切换、路线绘制、`emit("ask")` 让导游讲解按钮均正常。

- [ ] **Step 7: 提交（如有修正）**

```bash
git add -A
git commit -m "fix(guide): 自动讲解端到端联调修正"
```

---

## 验收清单（对应设计文档 §10）

- [ ] 开启开关并授权后，走近景点（或开模拟巡游）自动弹浮层并播报数字人语音
- [ ] 正在对话/播放时不打断；空闲后补播；补播前走远则丢弃
- [ ] 同景点未离开范围不重复触发；离开再进入可重听
- [ ] 无权限/不支持/不在景区自动进模拟模式并提示
- [ ] 后端不可用时静态简介 + 浏览器朗读，浮层正常
- [ ] 关闭开关即停止监听与播报并复位状态
- [ ] 地图页原有功能无回归

## 实施偏差记录（实现时的事实修正）

实现与联调过程中发现三处需要偏离上文代码块的地方，**以本节为准**：

1. **讲解提示词改为简洁问法（Task 2）**
   原提示词（"你是一名景区讲解员…控制在180字以内…"）实测被 pipeline 的意图路由劫持，返回了**路线推荐**而不是景点讲解。
   改为 `NARRATION_PROMPT = "请介绍{name}"`：稳定命中 FAQ/检索路径，直接返回景点讲解词，且通常无需调用 LLM，延迟更低。
   同时 `_clean()` 增加前缀清理：pipeline 答案会带风格化前缀（"好的，让我为您道来——" / "来，咱们看看——" / "根据官方资料记载——"），统一用 `_LEAD_STYLER_RE = r"^[^。！？\n]{0,24}?——\s*"` 剥离；检索降级时会插入 "AI讲解服务暂时不可用，先为你展示检索到的官方资料：" 一行，用 `_DEGRADED_LEAD_RE` 去除。

2. **新增"排队等待上限"安全阀（Task 5）**
   实测发现：浏览器朗读兜底播放长文本时会长时间占用播放通道，`audio.isPlaying` 持续为真，导致 `isBusy()` 恒为真，后续景点只能排队、**永不播放**（功能表现为"走完全程只讲第一个景点"）。
   在 `useNarration` 中新增 `pendingSince` 与 `maxPendingWaitMs`（常量 `PENDING_MAX_WAIT_MS = 25000`）：排队超过上限即调用 `onInterrupt()` 中断当前播放并补播，避免功能被永久阻塞。`MapView` 传入 `onInterrupt: () => { if (!props.busy) audio.stop(); }`（用户正在对话时不打断会话）。

3. **降级朗读只念开头（Task 1 / Task 7）**
   新增 `BROWSER_SPEECH_MAX_CHARS = 80` 与纯函数 `speechText(text, maxChars)`：超长文本截到最近句读处并补省略号。
   卡片仍展示**完整**讲解词，仅浏览器朗读兜底只念开头，使降级路径的播放时长可控、不阻塞后续触发。

上述 1、3 的纯函数与常量行为已由 Node 验证脚本覆盖（含 `speechText` 截断断言）；2 由浏览器实测覆盖（沿路线连续触发 灵山大照壁 → 五明桥 → 佛足坛 → 五智门，无重复、无卡死）。

## 明确不做（YAGNI，见设计文档 §1）

后端实时推送 / WebSocket；室内定位与蓝牙信标；多语言；自定义讲解音色选择；改造共享音频播放器新增暂停能力。
