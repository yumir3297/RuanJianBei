from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.chat_log import ChatLog
from app.models.knowledge_blind_spot import KnowledgeBlindSpot
from app.models.visitor import VisitorProfile


FAQ_QUESTIONS = [
    ("灵山大佛有多高", "灵山大佛通高88米，其中佛体高79米，莲花座高9米，是世界上最高的青铜立佛。"),
    ("九龙灌浴表演时间", "九龙灌浴每天定时表演，上午10:00、11:30，下午14:00、15:30各一场，每场约15分钟。"),
    ("灵山门票多少钱", "灵山胜境成人票210元，优待票105元（适用于老人、儿童、学生）。"),
    ("景区开放时间", "灵山胜境每日开放时间为7:00-17:30，夏季延长至18:00。"),
    ("怎么去灵山", "可乘坐无锡地铁2号线至梅园开原寺站换乘88路公交直达，或自驾导航灵山胜境停车场。"),
    ("梵宫要另外买票吗", "梵宫已包含在灵山胜境门票内，无需另行购票。"),
    ("有行李寄存吗", "游客中心提供免费行李寄存服务，大件行李也可寄存。"),
    ("可以带宠物吗", "为保障景区环境与游客安全，灵山胜境暂不允许携带宠物入内。"),
    ("停车场怎么收费", "景区停车场小车10元/次，大车20元/次。"),
    ("附近有住宿吗", "景区附近的灵山精舍、马山太湖度假区有多家酒店和民宿可供选择。"),
    ("有什么美食推荐", "灵山景区内有素斋馆、梵宫素斋、五印坛城茶馆等，推荐品尝灵山素面和禅茶。"),
    ("五印坛城是什么地方", "五印坛城是灵山胜境内的藏传佛教文化展示馆，展示了丰富的唐卡和坛城艺术。"),
    ("祥符禅寺历史多久了", "祥符禅寺始建于唐贞观年间，距今已有1300余年历史，是灵山佛教文化的重要源头。"),
    ("大照壁上面的字是什么", "灵山大照壁上镌刻着赵朴初题写的'湖光万顷净琉璃'七个大字。"),
    ("阿育王柱有什么寓意", "阿育王柱是古印度佛教标志性建筑，灵山景区的阿育王柱象征佛法广布四方。"),
    ("百子戏弥勒有什么讲究", "百子戏弥勒取自民间'多子多福'寓意，百名童子围绕弥勒嬉戏，象征吉祥欢乐。"),
    ("菩提大道有多少级台阶", "菩提大道共216级台阶，寓意人生六根、六尘、六识共十八界去除烦恼的修行之路。"),
    ("九龙灌浴有什么寓意", "九龙灌浴再现佛陀诞生时九龙吐水沐浴的场景，是佛教'佛诞'典故的宏大呈现。"),
    ("梵天花海什么时候最美", "梵天花海每年3-5月和9-11月为最佳观赏期，种植了波斯菊、薰衣草等多种花卉。"),
    ("带孩子去灵山合适吗", "非常适合，九龙灌浴表演、百子戏弥勒、梵天花海等都很适合亲子游览。"),
]

RAG_QUESTIONS = [
    ("灵山大佛的青铜材质有什么特点", "灵山大佛采用锡青铜铸造，总用铜量约700吨，具有良好的耐腐蚀性和庄严的色泽。"),
    ("梵宫的建筑风格有什么独特之处", "灵山梵宫融合了汉传佛教建筑与传统宫殿建筑风格，内部金碧辉煌，被誉为'东方卢浮宫'。"),
    ("降魔浮雕讲述了什么故事", "降魔浮雕再现了佛陀在菩提树下降服魔军、证悟成道的场景，是佛教艺术的重要题材。"),
    ("曼飞龙塔的建筑特征是什么", "曼飞龙塔是典型的南传佛教塔群建筑，由一座主塔和八座小塔组成，洁白典雅。"),
    ("五明桥的五明指什么", "五明桥的五明指佛教中的声明、工巧明、医方明、因明、内明五种学问。"),
    ("五智门有什么象征意义", "五智门代表佛教的五种智慧：法界体性智、大圆镜智、平等性智、妙观察智、成所作智。"),
    ("佛教文化博览馆有哪些展品", "佛教文化博览馆展出历代佛像、法器、经卷等珍贵文物，系统展示佛教文化发展历程。"),
    ("拈花堂的拈花一笑是什么意思", "拈花一笑源自佛陀拈花示众、迦叶破颜微笑的禅宗公案，象征以心传心的禅悟境界。"),
    ("鹿鸣谷名字的由来是什么", "鹿鸣谷取自诗经'呦呦鹿鸣，食野之苹'，营造了人与自然和谐共处的禅意空间。"),
    ("灵山梵宫内部有哪些主要殿堂", "灵山梵宫内部主要包括大雄宝殿、万佛殿、五百罗汉堂、佛教艺术馆等核心区域。"),
    ("九龙灌浴的水幕多高", "九龙灌浴广场中央的太子佛像在表演时从莲花中升起，水幕高达30余米，气势磅礴。"),
    ("五印坛城的坛城是什么意思", "坛城是藏传佛教中描绘佛国净土的图案，五印坛城展示了精美的立体坛城艺术。"),
    ("佛教文化博览馆镇馆之宝是什么", "佛教文化博览馆的镇馆之宝包括明代铜鎏金佛像和清代贝叶经等珍贵文物。"),
    ("香月花街有什么特色", "香月花街是灵山景区的一条禅意商业街，沿街有素斋、茶道、香道、手工艺品等体验项目。"),
    ("五灯湖的名字有什么典故", "五灯湖取名自禅宗'五灯会元'，湖面如镜倒映五智门的灯火，夜景尤为迷人。"),
    ("禅修体验一般多久", "灵山景区提供的禅修体验项目通常为1-2小时，包括坐禅、抄经、茶道等环节。"),
    ("降魔浮雕和九龙灌浴在同一个区域吗", "降魔浮雕位于灵山大佛脚下广场，九龙灌浴位于景区入口区域，两个景点相距约1公里。"),
    ("无尽意斋是做什么的", "无尽意斋是灵山景区内的禅意茶空间，游客可以品茶、抄经、体验禅修文化。"),
    ("灵山大佛内部能进去吗", "灵山大佛内部设有佛教文化展馆，游客可以进入参观，了解大佛的建造历程。"),
    ("佛足坛的脚印有什么说法", "佛足坛展示了佛陀的足印石刻，足底刻有法轮图案，象征佛法的传播与传承。"),
]

BLIND_SPOT_QUERIES = [
    "灵山有没有VIP导览服务",
    "景区内可以飞无人机吗",
    "灵山大佛的建造花了多少钱",
    "有没有多语言导游服务",
    "景区内可以使用轮椅吗",
    "灵山有无障碍通道吗",
    "下雨天九龙灌浴还会表演吗",
    "景区WiFi密码是什么",
    "可以提前在网上买票吗有没有优惠",
    "灵山有没有年卡或套票",
]

SESSION_IDS = [
    "demo-visitor-001", "demo-visitor-002", "demo-visitor-003",
    "demo-visitor-004", "demo-visitor-005", "demo-visitor-006",
    "demo-visitor-007", "demo-visitor-008", "demo-visitor-009",
    "demo-visitor-010", "demo-visitor-011", "demo-visitor-012",
    "demo-visitor-013", "demo-visitor-014", "demo-visitor-015",
    "demo-visitor-016", "demo-visitor-017", "demo-visitor-018",
    "demo-visitor-019", "demo-visitor-020", "demo-visitor-021",
    "demo-visitor-022", "demo-visitor-023", "demo-visitor-024",
]

VISITOR_PROFILES = [
    {"session_id": "demo-visitor-001", "audience_type": "family", "tags": ["灵山大佛", "九龙灌浴", "亲子"]},
    {"session_id": "demo-visitor-002", "audience_type": "culture", "tags": ["梵宫", "五印坛城", "祥符禅寺"]},
    {"session_id": "demo-visitor-003", "audience_type": "leisure", "tags": ["梵天花海", "香月花街", "鹿鸣谷"]},
    {"session_id": "demo-visitor-004", "audience_type": "free", "tags": ["灵山大佛", "菩提大道", "五智门"]},
    {"session_id": "demo-visitor-005", "audience_type": "family", "tags": ["九龙灌浴", "百子戏弥勒", "亲子"]},
    {"session_id": "demo-visitor-006", "audience_type": "culture", "tags": ["五印坛城", "佛教文化博览馆", "降魔浮雕"]},
    {"session_id": "demo-visitor-007", "audience_type": "leisure", "tags": ["香月花街", "美食", "拈花堂"]},
    {"session_id": "demo-visitor-008", "audience_type": "family", "tags": ["灵山大佛", "梵天花海", "亲子"]},
    {"session_id": "demo-visitor-009", "audience_type": "culture", "tags": ["佛教文化博览馆", "曼飞龙塔", "阿育王柱"]},
    {"session_id": "demo-visitor-010", "audience_type": "free", "tags": ["菩提大道", "五明桥", "佛足坛"]},
    {"session_id": "demo-visitor-011", "audience_type": "family", "tags": ["九龙灌浴", "灵山梵宫", "亲子"]},
    {"session_id": "demo-visitor-012", "audience_type": "culture", "tags": ["祥符禅寺", "降魔浮雕", "无尽意斋"]},
    {"session_id": "demo-visitor-013", "audience_type": "leisure", "tags": ["鹿鸣谷", "五灯湖", "梵天花海"]},
    {"session_id": "demo-visitor-014", "audience_type": "family", "tags": ["百子戏弥勒", "九龙灌浴", "亲子"]},
    {"session_id": "demo-visitor-015", "audience_type": "culture", "tags": ["灵山梵宫", "五印坛城", "阿育王柱"]},
    {"session_id": "demo-visitor-016", "audience_type": "free", "tags": ["大照壁", "菩提大道", "灵山大佛"]},
    {"session_id": "demo-visitor-017", "audience_type": "family", "tags": ["梵天花海", "九龙灌浴", "餐饮"]},
    {"session_id": "demo-visitor-018", "audience_type": "culture", "tags": ["佛教文化博览馆", "五智门", "降魔浮雕"]},
    {"session_id": "demo-visitor-019", "audience_type": "leisure", "tags": ["香月花街", "拈花堂", "购物"]},
    {"session_id": "demo-visitor-020", "audience_type": "culture", "tags": ["曼飞龙塔", "祥符禅寺", "灵山梵宫"]},
    {"session_id": "demo-visitor-021", "audience_type": "family", "tags": ["九龙灌浴", "亲子", "五灯湖"]},
    {"session_id": "demo-visitor-022", "audience_type": "free", "tags": ["鹿鸣谷", "梵天花海", "灵山大佛"]},
    {"session_id": "demo-visitor-023", "audience_type": "culture", "tags": ["降魔浮雕", "阿育王柱", "大照壁"]},
    {"session_id": "demo-visitor-024", "audience_type": "leisure", "tags": ["香月花街", "鹿鸣谷", "五印坛城"]},
]


def _random_date_within_days(days_back: int) -> datetime:
    seconds_back = random.randint(0, days_back * 24 * 3600)
    return datetime.now(timezone.utc) - timedelta(seconds=seconds_back)


async def seed_chat_logs(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).select_from(ChatLog).where(ChatLog.session_id.like("demo-visitor-%"))
    )
    existing = result.scalar_one()
    if existing > 0:
        return 0

    count = 0
    for i in range(14):
        day_offset = 13 - i
        date_anchor = datetime.now(timezone.utc) - timedelta(days=day_offset)
        queries_per_day = random.randint(8, 18)

        for _ in range(queries_per_day):
            pick = random.random()
            if pick < 0.30:
                query, answer = random.choice(FAQ_QUESTIONS)
                hit_level = random.choice(["faq_exact", "faq_fuzzy", "faq_semantic"])
                sources = json.dumps(
                    [{"evidence_id": "证据1", "title": "FAQ", "snippet": answer[:60], "source": "faq_db"}],
                    ensure_ascii=False,
                )
            elif pick < 0.48:
                query, answer = random.choice(RAG_QUESTIONS)
                hit_level = "rag"
                sources = json.dumps(
                    [{"evidence_id": "证据1", "title": "知识库", "snippet": answer[:60], "source": "knowledge_db"}],
                    ensure_ascii=False,
                )
            elif pick < 0.54:
                query = random.choice(BLIND_SPOT_QUERIES)
                answer = "抱歉，我目前还无法准确回答这个问题。建议您咨询景区工作人员获取最新信息。"
                hit_level = "rag_insufficient"
                sources = "[]"
            else:
                faq_query, answer = random.choice(FAQ_QUESTIONS)
                query = faq_query
                hit_level = "cache"
                sources = json.dumps(
                    [{"evidence_id": "证据1", "title": "缓存", "snippet": answer[:60], "source": "qa_cache"}],
                    ensure_ascii=False,
                )

            hour = random.randint(7, 17)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            created_at = date_anchor.replace(hour=hour, minute=minute, second=second)

            session_id = random.choice(SESSION_IDS)

            log = ChatLog(
                session_id=session_id,
                raw_query=query,
                normalized_query=query.strip(),
                answer=answer,
                sources=sources,
                hit_level=hit_level,
                latency_ms=random.randint(200, 2800),
                created_at=created_at,
            )
            session.add(log)
            count += 1

    await session.commit()
    return count


async def seed_visitor_profiles(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count()).select_from(VisitorProfile).where(
            VisitorProfile.session_id.like("demo-visitor-%")
        )
    )
    existing = result.scalar_one()
    if existing > 0:
        return 0

    count = 0
    for profile in VISITOR_PROFILES:
        vp = VisitorProfile(
            session_id=profile["session_id"],
            preference_tags=json.dumps(profile["tags"], ensure_ascii=False),
            audience_type=profile["audience_type"],
        )
        session.add(vp)
        count += 1

    await session.commit()
    return count


async def seed_blind_spots(session: AsyncSession) -> int:
    result = await session.execute(select(KnowledgeBlindSpot).limit(1))
    existing = result.scalars().first()
    if existing is not None:
        return 0

    count = 0
    for i, query_text in enumerate(BLIND_SPOT_QUERIES):
        now = datetime.now(timezone.utc)
        seen_at = now - timedelta(days=random.randint(1, 10))
        hit_count = random.randint(3, 15)
        spot = KnowledgeBlindSpot(
            normalized_query=query_text.strip(),
            raw_query_samples_json=json.dumps([query_text], ensure_ascii=False),
            hit_count=hit_count,
            status="open",
            category="rag_no_docs",
            first_seen_at=seen_at,
            last_seen_at=now,
        )
        session.add(spot)
        count += 1

    await session.commit()
    return count


async def bootstrap_demo_data() -> dict:
    async with AsyncSessionLocal() as session:
        logs = await seed_chat_logs(session)
        visitors = await seed_visitor_profiles(session)
        blind_spots = await seed_blind_spots(session)
        return {"chat_logs": logs, "visitor_profiles": visitors, "blind_spots": blind_spots}


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(bootstrap_demo_data())
    print(f"演示数据已注入完成:")
    print(f"  问答日志: {result['chat_logs']} 条")
    print(f"  游客画像: {result['visitor_profiles']} 条")
    print(f"  知识盲区: {result['blind_spots']} 条")
