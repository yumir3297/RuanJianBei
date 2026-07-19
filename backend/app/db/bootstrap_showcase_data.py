from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.chat_log import ChatLog
from app.models.faq import FAQEntryRecord
from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.models.visitor import VisitorProfile
from app.models.visitor_feedback import VisitorFeedback


SHOWCASE_SESSION_PREFIX = "showcase-visitor-"
SHOWCASE_FAQ_PREFIX = "showcase-faq-"
DAILY_COUNTS = tuple(12 + day_index // 3 for day_index in range(30))


@dataclass(frozen=True, slots=True)
class Scenario:
    key: str
    queries: tuple[str, ...]
    normalized_query: str
    answer: str
    hit_level: str
    source_title: str | None
    source_kind: str | None
    emotion: str
    weight: int


@dataclass(frozen=True, slots=True)
class ChatRecord:
    session_id: str
    raw_query: str
    normalized_query: str
    answer: str
    sources: tuple[dict[str, Any], ...]
    hit_level: str
    latency_ms: int
    input_mode: str
    text_emotion: str
    audio_emotion: str | None
    fused_emotion: str
    emotion_confidence: float
    emotion_intensity: float
    emotion_conflict: bool
    emotion_modalities: tuple[str, ...]
    response_strategy: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class VisitorRecord:
    session_id: str
    audience_type: str
    tags: tuple[str, ...]
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class BlindSpotRecord:
    normalized_query: str
    samples: tuple[str, ...]
    hit_count: int
    status: str
    category: str
    first_seen_at: datetime
    last_seen_at: datetime
    resolution_type: str | None = None
    resolved_faq_id: str | None = None
    resolved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FAQRecord:
    id: str
    category: str
    aliases: tuple[str, ...]
    answer: str
    sources: tuple[dict[str, str], ...]


@dataclass(frozen=True, slots=True)
class FeedbackRecord:
    log_index: int
    session_id: str
    rating: str
    reason_code: str | None
    comment: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ShowcaseDataset:
    chats: tuple[ChatRecord, ...]
    visitors: tuple[VisitorRecord, ...]
    blind_spots: tuple[BlindSpotRecord, ...]
    faqs: tuple[FAQRecord, ...]
    feedback: tuple[FeedbackRecord, ...]


SCENARIOS = (
    Scenario(
        key="opening-hours",
        queries=("景区几点开放？", "灵山胜境今天几点开门？"),
        normalized_query="景区开放时间",
        answer="开放时间可能随日期和活动安排调整，请以景区当天公告或官方票务页面为准；到园后也可在游客中心确认。",
        hit_level="faq_exact",
        source_title="游客服务信息",
        source_kind="faq_db",
        emotion="neutral",
        weight=8,
    ),
    Scenario(
        key="ticket-scope",
        queries=("梵宫需要另外买票吗？", "门票包含灵山梵宫吗？"),
        normalized_query="梵宫是否需要单独购票",
        answer="票种和包含项目可能随活动调整，购票前请核对官方票务页面中的当日票种说明，避免仅凭历史价格或旧攻略判断。",
        hit_level="faq_exact",
        source_title="票务服务说明",
        source_kind="faq_db",
        emotion="neutral",
        weight=7,
    ),
    Scenario(
        key="luggage",
        queries=("我带着两个箱子，哪里能寄存？", "行李太多了，游客中心能帮忙吗？"),
        normalized_query="景区行李寄存服务",
        answer="先别着急，建议先到游客中心服务台确认当天寄存位置、尺寸限制和领取时间，再开始游览。",
        hit_level="faq_fuzzy",
        source_title="游客中心",
        source_kind="faq_db",
        emotion="anxious",
        weight=5,
    ),
    Scenario(
        key="parking",
        queries=("停车到底怎么安排，绕了半天没找到。", "停车场入口在哪里？"),
        normalized_query="景区停车指引",
        answer="抱歉让您多走了路。请优先跟随现场停车指示牌和工作人员引导；收费、入口及余位以当天现场信息为准。",
        hit_level="faq_fuzzy",
        source_title="交通与停车指引",
        source_kind="faq_db",
        emotion="dissatisfied",
        weight=5,
    ),
    Scenario(
        key="family-route",
        queries=("带孩子半天怎么玩比较轻松？", "想要一条适合亲子的轻松路线。"),
        normalized_query="亲子半日轻松路线",
        answer="可以优先选择九龙灌浴、百子戏弥勒和灵山梵宫，并根据孩子体力减少连续台阶路段；具体开放情况以当日现场为准。",
        hit_level="faq_semantic",
        source_title="亲子游览建议",
        source_kind="faq_db",
        emotion="positive",
        weight=7,
    ),
    Scenario(
        key="accessible-route",
        queries=("老人腿脚不方便，我不知道该怎么选路线。", "轮椅游客怎么规划路线更合适？"),
        normalized_query="行动不便游客路线建议",
        answer="没关系，我先给您最重要的一步：入园后先到游客中心确认当日无障碍通行信息，再选择室内景点较多、折返较少的路线。",
        hit_level="faq_semantic",
        source_title="无障碍游览指引",
        source_kind="faq_db",
        emotion="confused",
        weight=5,
    ),
    Scenario(
        key="buddha-height",
        queries=("灵山大佛有多高？", "大佛高度是多少？"),
        normalized_query="灵山大佛高度",
        answer="灵山大佛通高 88 米。这个高频事实由缓存快速返回，同时保留对应景点来源，便于核验。",
        hit_level="cache",
        source_title="灵山大佛",
        source_kind="qa_cache",
        emotion="neutral",
        weight=12,
    ),
    Scenario(
        key="jiulong-meaning",
        queries=("九龙灌浴讲的是什么故事？", "九龙灌浴有什么寓意？"),
        normalized_query="九龙灌浴文化寓意",
        answer="九龙灌浴以佛诞典故为叙事核心，通过音乐、喷泉和动态装置呈现太子佛诞生的文化场景。",
        hit_level="cache",
        source_title="九龙灌浴",
        source_kind="qa_cache",
        emotion="positive",
        weight=8,
    ),
    Scenario(
        key="buddha-craft",
        queries=("灵山大佛的铸造工艺有什么特点？", "为什么大佛选择青铜材质？"),
        normalized_query="灵山大佛青铜铸造特点",
        answer="知识资料从材质耐久性、分块铸造与整体艺术表现三个角度介绍大佛工程；回答只组织已检索到的资料，不补写无出处细节。",
        hit_level="rag",
        source_title="灵山大佛",
        source_kind="knowledge_db",
        emotion="positive",
        weight=7,
    ),
    Scenario(
        key="palace-architecture",
        queries=("灵山梵宫的建筑风格为什么很特别？", "梵宫内部艺术有什么看点？"),
        normalized_query="灵山梵宫建筑艺术特点",
        answer="灵山梵宫将传统建筑语汇、穹顶空间和佛教艺术陈设结合起来，适合从建筑、绘画与空间叙事三个层次参观。",
        hit_level="rag",
        source_title="灵山梵宫",
        source_kind="knowledge_db",
        emotion="neutral",
        weight=6,
    ),
    Scenario(
        key="culture-route",
        queries=("我喜欢佛教艺术，四小时怎么安排？", "帮我规划一条文化深度路线。"),
        normalized_query="四小时佛教文化深度路线",
        answer="建议按灵山大佛、灵山梵宫、五印坛城组织四小时文化路线；系统会结合偏好与可用时长排序，现场再按开放状态微调。",
        hit_level="rag",
        source_title="灵山梵宫",
        source_kind="knowledge_db",
        emotion="positive",
        weight=6,
    ),
    Scenario(
        key="senior-comfort",
        queries=("老人走不动了，后面怎么安排才省体力？", "想少走路又能看主要景点。"),
        normalized_query="老人少走路舒适路线",
        answer="先别着急，建议先就近休息，再优先保留灵山大佛和室内场馆，减少台阶与来回折返；接驳信息请向现场工作人员确认。",
        hit_level="rag",
        source_title="舒适游览路线",
        source_kind="knowledge_db",
        emotion="anxious",
        weight=6,
    ),
    Scenario(
        key="vision-buddha",
        queries=("拍照识景提示可能是灵山大佛，这尊佛像有什么特点？", "我照片里的大佛是哪处景点？能简单介绍吗？"),
        normalized_query="拍照识景后介绍灵山大佛",
        answer="图像模型只提供‘灵山大佛’候选线索，系统再从官方知识资料中检索介绍；视觉判断本身不作为景区事实来源。",
        hit_level="rag",
        source_title="灵山大佛",
        source_kind="knowledge_db:vision_scoped",
        emotion="confused",
        weight=5,
    ),
    Scenario(
        key="route-clarification",
        queries=("我只有三小时，到底先看哪个？", "景点太多了，能按顺序说清楚吗？"),
        normalized_query="三小时游览顺序",
        answer="没关系，我换成三个步骤：先确认最想看的景点，再选择相邻景点，最后预留返程时间；默认不安排过多折返。",
        hit_level="rag",
        source_title="半日游路线",
        source_kind="knowledge_db",
        emotion="confused",
        weight=4,
    ),
    Scenario(
        key="lost-child",
        queries=("孩子刚刚走散了，我现在该怎么办？", "紧急！同行的小朋友找不到了。"),
        normalized_query="儿童走失紧急处置",
        answer="请先确保人身安全。立即联系身边的景区工作人员或游客中心，并留在最后确认见到孩子的位置附近；不要依赖系统编造电话或处置承诺。",
        hit_level="rag",
        source_title="游客安全指引",
        source_kind="knowledge_db",
        emotion="urgent",
        weight=3,
    ),
    Scenario(
        key="live-shuttle",
        queries=("今天无障碍接驳车几点发车？", "现在最近一班接驳车还有多久？"),
        normalized_query="今日无障碍接驳车实时班次",
        answer="先别着急，我目前没有检索到可核验的当日实时班次，因此不猜测时间；请以现场站牌或工作人员答复为准。这个问题已记录为知识盲区。",
        hit_level="rag_insufficient",
        source_title=None,
        source_kind=None,
        emotion="anxious",
        weight=4,
    ),
    Scenario(
        key="live-performance",
        queries=("今天九龙灌浴是不是临时停演了？", "为什么没有按攻略上的时间开始表演？"),
        normalized_query="九龙灌浴当日临时停演信息",
        answer="抱歉给您带来困扰。我没有检索到可核验的当日临时公告，不能沿用旧攻略作答；请查看现场公告或咨询工作人员。这个问题已进入盲区清单。",
        hit_level="rag_insufficient",
        source_title=None,
        source_kind=None,
        emotion="dissatisfied",
        weight=2,
    ),
)


AUDIENCE_BLUEPRINTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "family": (
        ("亲子", "九龙灌浴", "轻松路线"),
        ("亲子", "百子戏弥勒", "室内场馆"),
        ("老人同行", "少走路", "无障碍"),
    ),
    "culture": (
        ("佛教文化", "灵山大佛", "深度讲解"),
        ("建筑艺术", "灵山梵宫", "五印坛城"),
        ("历史典故", "祥符禅寺", "文化路线"),
    ),
    "leisure": (
        ("轻松游", "拍照", "室内场馆"),
        ("休闲", "素食", "香月花街"),
        ("摄影", "自然景观", "避开拥挤"),
    ),
    "free": (
        ("自由行", "半日游", "路线规划"),
        ("首次到访", "热门景点", "交通"),
        ("拍照识景", "灵山大佛", "即时问答"),
    ),
    "general": (
        ("综合导览", "游客服务", "实时信息"),
        ("语音咨询", "景点介绍", "路线规划"),
    ),
}

AUDIENCE_SEQUENCE = (
    *("family" for _ in range(12)),
    *("culture" for _ in range(10)),
    *("leisure" for _ in range(7)),
    *("free" for _ in range(7)),
    *("general" for _ in range(4)),
)

EMOTION_CONFIDENCE = {
    "positive": 0.88,
    "neutral": 0.82,
    "confused": 0.86,
    "dissatisfied": 0.9,
    "anxious": 0.89,
    "urgent": 0.94,
}

EMOTION_INTENSITY = {
    "positive": 0.62,
    "neutral": 0.22,
    "confused": 0.58,
    "dissatisfied": 0.72,
    "anxious": 0.76,
    "urgent": 0.93,
}

LATENCY_RANGES = {
    "faq_exact": (65, 105),
    "faq_fuzzy": (105, 165),
    "faq_semantic": (155, 235),
    "cache": (28, 58),
    "rag": (760, 1280),
    "rag_insufficient": (390, 680),
}


def _scenario_pool() -> tuple[Scenario, ...]:
    return tuple(scenario for scenario in SCENARIOS for _ in range(scenario.weight))


def _latency_for(hit_level: str, index: int) -> int:
    low, high = LATENCY_RANGES[hit_level]
    return low + ((index * 37 + 11) % (high - low + 1))


def _audio_emotion_for(emotion: str, conflict: bool) -> str:
    if not conflict:
        return emotion
    conflict_map = {
        "neutral": "anxious",
        "positive": "neutral",
        "confused": "anxious",
        "dissatisfied": "neutral",
        "anxious": "neutral",
        "urgent": "anxious",
    }
    return conflict_map[emotion]


def _build_chat_records(now: datetime) -> tuple[ChatRecord, ...]:
    pool = _scenario_pool()
    records: list[ChatRecord] = []
    global_index = 0

    for day_index, daily_count in enumerate(DAILY_COUNTS):
        day = now - timedelta(days=29 - day_index)
        for item_index in range(daily_count):
            scenario = pool[(global_index * 17 + day_index * 7) % len(pool)]
            query = scenario.queries[(global_index + day_index) % len(scenario.queries)]
            session_id = f"{SHOWCASE_SESSION_PREFIX}{((global_index * 7 + day_index) % len(AUDIENCE_SEQUENCE)) + 1:03d}"
            input_mode = "voice" if (global_index + day_index) % 20 in {1, 4, 7, 10, 13, 16, 18} else "text"
            conflict = input_mode == "voice" and (global_index + 3 * day_index) % 41 == 0
            audio_emotion = _audio_emotion_for(scenario.emotion, conflict) if input_mode == "voice" else None
            minute_of_day = 8 * 60 + ((item_index * 31 + day_index * 13) % (10 * 60))
            created_at = day.replace(
                hour=minute_of_day // 60,
                minute=minute_of_day % 60,
                second=(global_index * 19) % 60,
                microsecond=0,
            )
            if scenario.source_title:
                sources = (
                    {
                        "evidence_id": f"showcase-{scenario.key}",
                        "title": scenario.source_title,
                        "snippet": scenario.answer[:80],
                        "source": scenario.source_kind,
                        "score": round(0.84 + (global_index % 11) * 0.01, 2),
                    },
                )
            else:
                sources = ()

            confidence = EMOTION_CONFIDENCE[scenario.emotion] - (0.05 if conflict else 0)
            records.append(
                ChatRecord(
                    session_id=session_id,
                    raw_query=query,
                    normalized_query=scenario.normalized_query,
                    answer=scenario.answer,
                    sources=sources,
                    hit_level=scenario.hit_level,
                    latency_ms=_latency_for(scenario.hit_level, global_index),
                    input_mode=input_mode,
                    text_emotion=scenario.emotion,
                    audio_emotion=audio_emotion,
                    fused_emotion=scenario.emotion,
                    emotion_confidence=round(confidence, 2),
                    emotion_intensity=EMOTION_INTENSITY[scenario.emotion],
                    emotion_conflict=conflict,
                    emotion_modalities=("text", "audio") if input_mode == "voice" else ("text",),
                    response_strategy=scenario.emotion,
                    created_at=created_at,
                )
            )
            global_index += 1

    return tuple(records)


def _build_visitors(now: datetime) -> tuple[VisitorRecord, ...]:
    visitors = []
    for index, audience_type in enumerate(AUDIENCE_SEQUENCE):
        variants = AUDIENCE_BLUEPRINTS[audience_type]
        visitors.append(
            VisitorRecord(
                session_id=f"{SHOWCASE_SESSION_PREFIX}{index + 1:03d}",
                audience_type=audience_type,
                tags=variants[index % len(variants)],
                last_seen_at=now - timedelta(hours=index % 36),
            )
        )
    return tuple(visitors)


def _build_faqs() -> tuple[FAQRecord, ...]:
    demo_source = ({"title": "展示数据：游客服务口径", "source": "showcase_demo"},)
    return (
        FAQRecord(
            id=f"{SHOWCASE_FAQ_PREFIX}rainy-route",
            category="showcase_service",
            aliases=("雨天适合怎么游览", "下雨时有哪些室内路线"),
            answer="雨天可优先安排灵山梵宫、五印坛城等室内参观内容，并以当天开放公告为准。",
            sources=demo_source,
        ),
        FAQRecord(
            id=f"{SHOWCASE_FAQ_PREFIX}manual-guide",
            category="showcase_service",
            aliases=("如何申请人工讲解", "人工导游在哪里预约"),
            answer="请在游客中心确认当天人工讲解的场次、语言和预约方式，系统不使用历史信息代替当日安排。",
            sources=demo_source,
        ),
        FAQRecord(
            id=f"{SHOWCASE_FAQ_PREFIX}stroller",
            category="showcase_service",
            aliases=("婴儿车在哪里租借", "能不能借儿童推车"),
            answer="请到游客中心确认当天婴儿车服务点、库存和使用规则，以现场服务口径为准。",
            sources=demo_source,
        ),
    )


def _build_blind_spots(now: datetime) -> tuple[BlindSpotRecord, ...]:
    return (
        BlindSpotRecord(
            normalized_query="今日无障碍接驳车实时班次",
            samples=("今天无障碍接驳车几点发车？", "最近一班接驳车还有多久？"),
            hit_count=26,
            status="open",
            category="real_time_service",
            first_seen_at=now - timedelta(days=9),
            last_seen_at=now - timedelta(minutes=32),
        ),
        BlindSpotRecord(
            normalized_query="九龙灌浴当日临时停演信息",
            samples=("今天九龙灌浴是不是临时停演了？", "今天表演为什么没开始？"),
            hit_count=18,
            status="open",
            category="real_time_event",
            first_seen_at=now - timedelta(days=7),
            last_seen_at=now - timedelta(hours=2),
        ),
        BlindSpotRecord(
            normalized_query="婴儿车当日可借库存",
            samples=("现在还有婴儿车可以借吗？",),
            hit_count=14,
            status="open",
            category="real_time_service",
            first_seen_at=now - timedelta(days=6),
            last_seen_at=now - timedelta(hours=5),
        ),
        BlindSpotRecord(
            normalized_query="景区当前实时客流和排队时长",
            samples=("现在大佛排队多久？", "哪个景点当前人最少？"),
            hit_count=12,
            status="open",
            category="real_time_crowd",
            first_seen_at=now - timedelta(days=5),
            last_seen_at=now - timedelta(hours=4),
        ),
        BlindSpotRecord(
            normalized_query="失物招领处理进度查询",
            samples=("我提交的失物登记处理到哪一步了？",),
            hit_count=9,
            status="open",
            category="external_workflow",
            first_seen_at=now - timedelta(days=4),
            last_seen_at=now - timedelta(hours=8),
        ),
        BlindSpotRecord(
            normalized_query="雨天室内游览路线",
            samples=("雨天适合怎么游览？", "下雨时有哪些室内路线？"),
            hit_count=17,
            status="resolved",
            category="showcase_service",
            first_seen_at=now - timedelta(days=18),
            last_seen_at=now - timedelta(days=8),
            resolution_type="faq",
            resolved_faq_id=f"{SHOWCASE_FAQ_PREFIX}rainy-route",
            resolved_at=now - timedelta(days=8),
        ),
        BlindSpotRecord(
            normalized_query="人工讲解预约方式",
            samples=("如何申请人工讲解？", "人工导游在哪里预约？"),
            hit_count=13,
            status="resolved",
            category="showcase_service",
            first_seen_at=now - timedelta(days=16),
            last_seen_at=now - timedelta(days=6),
            resolution_type="faq",
            resolved_faq_id=f"{SHOWCASE_FAQ_PREFIX}manual-guide",
            resolved_at=now - timedelta(days=6),
        ),
        BlindSpotRecord(
            normalized_query="婴儿车租借地点和规则",
            samples=("婴儿车在哪里租借？", "能不能借儿童推车？"),
            hit_count=10,
            status="resolved",
            category="showcase_service",
            first_seen_at=now - timedelta(days=14),
            last_seen_at=now - timedelta(days=4),
            resolution_type="faq",
            resolved_faq_id=f"{SHOWCASE_FAQ_PREFIX}stroller",
            resolved_at=now - timedelta(days=4),
        ),
    )


def _build_feedback(chats: tuple[ChatRecord, ...]) -> tuple[FeedbackRecord, ...]:
    feedback: list[FeedbackRecord] = []
    negative_reasons = ("detail", "latency", "recommendation", "accuracy")
    positive_comments = (
        "回答给出了来源和下一步，信息很清楚。",
        "语音交互自然，路线建议符合同行人的体力。",
        "没有猜测实时信息，提醒我去现场确认。",
    )
    negative_comments = (
        "希望补充更实时的接驳信息。",
        "文化讲解可以再给一个简短版本。",
        "路线推荐还可以结合当前客流。",
        "等待知识检索的时间仍可继续优化。",
    )

    for feedback_index, log_index in enumerate(range(3, len(chats), 8)):
        chat = chats[log_index]
        is_negative = feedback_index % 6 == 5
        reason_code = negative_reasons[feedback_index % len(negative_reasons)] if is_negative else None
        comment_pool = negative_comments if is_negative else positive_comments
        feedback.append(
            FeedbackRecord(
                log_index=log_index,
                session_id=chat.session_id,
                rating="negative" if is_negative else "positive",
                reason_code=reason_code,
                comment=comment_pool[feedback_index % len(comment_pool)],
                created_at=chat.created_at + timedelta(minutes=2),
            )
        )
    return tuple(feedback)


def build_showcase_dataset(now: datetime | None = None) -> ShowcaseDataset:
    # Use the latest completed day so running the script in the morning never
    # creates same-day records whose generated clock time is still in the future.
    anchor = (
        (now or datetime.now(timezone.utc)).astimezone(timezone.utc) - timedelta(days=1)
    ).replace(microsecond=0)
    chats = _build_chat_records(anchor)
    return ShowcaseDataset(
        chats=chats,
        visitors=_build_visitors(anchor),
        blind_spots=_build_blind_spots(anchor),
        faqs=_build_faqs(),
        feedback=_build_feedback(chats),
    )


def summarize_showcase_dataset(dataset: ShowcaseDataset) -> dict[str, Any]:
    hit_levels = Counter(record.hit_level for record in dataset.chats)
    emotions = Counter(record.fused_emotion for record in dataset.chats)
    input_modes = Counter(record.input_mode for record in dataset.chats)
    status_counts = Counter(record.status for record in dataset.blind_spots)
    average_latency = sum(record.latency_ms for record in dataset.chats) / len(dataset.chats)
    positive_feedback = sum(record.rating == "positive" for record in dataset.feedback)
    return {
        "chat_logs": len(dataset.chats),
        "visitor_profiles": len(dataset.visitors),
        "blind_spots": dict(status_counts),
        "faq_entries": len(dataset.faqs),
        "feedback": len(dataset.feedback),
        "showcase_satisfaction_rate": round(positive_feedback / len(dataset.feedback) * 100, 1),
        "average_latency_ms": round(average_latency, 1),
        "hit_distribution": dict(hit_levels),
        "emotion_distribution": dict(emotions),
        "input_modes": dict(input_modes),
        "multimodal_emotion_count": sum(record.audio_emotion is not None for record in dataset.chats),
        "emotion_conflict_count": sum(record.emotion_conflict for record in dataset.chats),
        "date_range": [
            min(record.created_at for record in dataset.chats).isoformat(),
            max(record.created_at for record in dataset.chats).isoformat(),
        ],
    }


async def _existing_counts(session: AsyncSession) -> dict[str, int]:
    blind_queries = [record.normalized_query for record in _build_blind_spots(datetime.now(timezone.utc))]
    return {
        "chat_logs": int(
            (await session.execute(select(func.count(ChatLog.id)).where(ChatLog.session_id.like(f"{SHOWCASE_SESSION_PREFIX}%")))).scalar_one()
        ),
        "visitor_profiles": int(
            (await session.execute(select(func.count(VisitorProfile.id)).where(VisitorProfile.session_id.like(f"{SHOWCASE_SESSION_PREFIX}%")))).scalar_one()
        ),
        "blind_spots": int(
            (await session.execute(select(func.count(KnowledgeBlindSpot.id)).where(KnowledgeBlindSpot.normalized_query.in_(blind_queries)))).scalar_one()
        ),
        "faq_entries": int(
            (await session.execute(select(func.count(FAQEntryRecord.id)).where(FAQEntryRecord.id.like(f"{SHOWCASE_FAQ_PREFIX}%")))).scalar_one()
        ),
        "feedback": int(
            (await session.execute(select(func.count(VisitorFeedback.id)).where(VisitorFeedback.session_id.like(f"{SHOWCASE_SESSION_PREFIX}%")))).scalar_one()
        ),
    }


async def _delete_existing_showcase_data(session: AsyncSession, dataset: ShowcaseDataset) -> None:
    blind_queries = [record.normalized_query for record in dataset.blind_spots]
    await session.execute(delete(VisitorFeedback).where(VisitorFeedback.session_id.like(f"{SHOWCASE_SESSION_PREFIX}%")))
    await session.execute(delete(ChatLog).where(ChatLog.session_id.like(f"{SHOWCASE_SESSION_PREFIX}%")))
    await session.execute(delete(VisitorProfile).where(VisitorProfile.session_id.like(f"{SHOWCASE_SESSION_PREFIX}%")))
    await session.execute(delete(KnowledgeBlindSpot).where(KnowledgeBlindSpot.normalized_query.in_(blind_queries)))
    await session.execute(delete(FAQEntryRecord).where(FAQEntryRecord.id.like(f"{SHOWCASE_FAQ_PREFIX}%")))


async def _insert_showcase_data(
    session: AsyncSession,
    dataset: ShowcaseDataset,
    *,
    commit: bool = True,
) -> None:
    chat_models = [
        ChatLog(
            session_id=record.session_id,
            raw_query=record.raw_query,
            normalized_query=record.normalized_query,
            answer=record.answer,
            sources=json.dumps(record.sources, ensure_ascii=False),
            hit_level=record.hit_level,
            latency_ms=record.latency_ms,
            input_mode=record.input_mode,
            text_emotion=record.text_emotion,
            audio_emotion=record.audio_emotion,
            fused_emotion=record.fused_emotion,
            emotion_confidence=record.emotion_confidence,
            emotion_intensity=record.emotion_intensity,
            emotion_conflict=record.emotion_conflict,
            emotion_modalities=json.dumps(record.emotion_modalities, ensure_ascii=False),
            response_strategy=record.response_strategy,
            created_at=record.created_at,
        )
        for record in dataset.chats
    ]
    session.add_all(chat_models)
    await session.flush()

    session.add_all(
        VisitorProfile(
            session_id=record.session_id,
            preference_tags=json.dumps(record.tags, ensure_ascii=False),
            audience_type=record.audience_type,
            last_seen_at=record.last_seen_at,
        )
        for record in dataset.visitors
    )
    session.add_all(
        FAQEntryRecord(
            id=record.id,
            category=record.category,
            aliases_json=json.dumps(record.aliases, ensure_ascii=False),
            answer=record.answer,
            sources_json=json.dumps(record.sources, ensure_ascii=False),
        )
        for record in dataset.faqs
    )
    session.add_all(
        KnowledgeBlindSpot(
            normalized_query=record.normalized_query,
            raw_query_samples_json=json.dumps(record.samples, ensure_ascii=False),
            hit_count=record.hit_count,
            status=record.status,
            category=record.category,
            resolution_type=record.resolution_type,
            resolved_faq_id=record.resolved_faq_id,
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
            resolved_at=record.resolved_at,
        )
        for record in dataset.blind_spots
    )
    session.add_all(
        VisitorFeedback(
            chat_log_id=chat_models[record.log_index].id,
            session_id=record.session_id,
            rating=record.rating,
            reason_code=record.reason_code,
            comment=record.comment,
            is_demo=True,
            created_at=record.created_at,
        )
        for record in dataset.feedback
    )
    if commit:
        await session.commit()
    else:
        await session.flush()


async def bootstrap_showcase_data(*, replace: bool = False, dry_run: bool = False) -> dict[str, Any]:
    dataset = build_showcase_dataset()
    summary = summarize_showcase_dataset(dataset)
    if dry_run:
        return {"status": "dry-run", **summary}

    async with AsyncSessionLocal() as session:
        existing = await _existing_counts(session)
        if any(existing.values()) and not replace:
            return {
                "status": "skipped",
                "message": "已存在 showcase 展示数据；如需重建，请增加 --replace。",
                "existing": existing,
                "planned": summary,
            }
        if replace:
            await _delete_existing_showcase_data(session, dataset)
        await _insert_showcase_data(session, dataset)
        return {"status": "inserted", **summary}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成用于管理后台演示的确定性 showcase 数据。")
    parser.add_argument("--dry-run", action="store_true", help="仅预览数据规模和指标，不写数据库。")
    parser.add_argument("--replace", action="store_true", help="仅删除并重建 showcase 前缀的数据。")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = asyncio.run(bootstrap_showcase_data(replace=args.replace, dry_run=args.dry_run))
    print(json.dumps(result, ensure_ascii=False, indent=2))
