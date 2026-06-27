from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.scripts.e2e_eval_core import load_cases, validate_cases  # noqa: E402

OUTPUT_PATH = PROJECT_ROOT / "eval" / "testset" / "e2e_qa_100.json"

EXPECTED_DISTRIBUTION = {
    "fact_qa": 30,
    "history_culture": 15,
    "attraction_detail": 15,
    "route_planning": 10,
    "practical_info": 10,
    "guided_selection": 8,
    "followup_context": 6,
    "blind_spot_refusal": 6,
}


def answer_case(
    *,
    case_id: str,
    category: str,
    query: str,
    expected_sources: list[str],
    required_facts: list[str],
    forbidden_facts: list[str] | None = None,
    selection: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "id": case_id,
        "category": category,
        "query": query,
        "selection": selection,
        "context": context,
        "expected_sources": expected_sources,
        "required_facts": required_facts,
        "forbidden_facts": forbidden_facts or [],
        "expected_behavior": "answer_with_evidence",
        "notes": notes,
    }


def refusal_case(
    *,
    case_id: str,
    query: str,
    forbidden_facts: list[str],
    notes: str,
    selection: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "category": "blind_spot_refusal",
        "query": query,
        "selection": selection,
        "context": context,
        "expected_sources": [],
        "required_facts": [],
        "forbidden_facts": forbidden_facts,
        "expected_behavior": "refuse_without_evidence",
        "notes": notes,
    }


def build_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    fact_cases = [
        ("001", "灵山大照壁有多大？", ["灵山大照壁"], ["39.8", "7"], "大照壁尺寸"),
        ("002", "五明桥有几座石拱桥？", ["五明桥"], ["5", "汉白玉"], "五明桥结构"),
        ("003", "佛足坛的佛足印尺寸是多少？", ["佛足坛"], ["1.2", "0.6", "青铜"], "佛足坛参数"),
        ("004", "五智门有多高多宽？", ["五智门"], ["16.8", "35"], "五智门参数"),
        ("005", "菩提大道大概有多长？", ["菩提大道"], ["250", "10"], "菩提大道尺度"),
        ("006", "九龙灌浴的太子佛有多高？", ["九龙灌浴"], ["7.2", "12吨"], "九龙灌浴参数"),
        ("007", "降魔浮雕的尺寸是多少？", ["降魔浮雕"], ["26", "4.6"], "降魔浮雕参数"),
        ("008", "阿育王柱有多高？", ["阿育王柱"], ["16.9", "180吨"], "阿育王柱参数"),
        ("009", "百子戏弥勒有多大？", ["百子戏弥勒"], ["3m", "7.8m", "9吨"], "百子戏弥勒参数"),
        ("010", "祥符禅寺占地大约多少？", ["祥符禅寺"], ["30亩", "12.8吨"], "祥符禅寺参数"),
        ("011", "灵山大佛有多高？", ["灵山大佛"], ["88", "79", "9"], "灵山大佛参数"),
        ("012", "佛教文化博览馆有几层？", ["佛教文化博览馆"], ["三层", "10000"], "博览馆参数"),
        ("013", "灵山梵宫建筑面积和高度是多少？", ["灵山梵宫"], ["72000", "66.5"], "梵宫参数"),
        ("014", "五印坛城大约多高？", ["五印坛城"], ["30", "5000"], "坛城参数"),
        ("015", "曼飞龙塔由几座塔组成？", ["曼飞龙塔"], ["主塔", "八座", "16.9"], "曼飞龙塔参数"),
        ("016", "无尽意斋占地多大？", ["无尽意斋"], ["600", "四合院"], "无尽意斋参数"),
        ("017", "拈花广场中央雕塑有多高？", ["拈花广场"], ["12", "拈花微笑"], "拈花广场参数"),
        ("018", "梵天花海面积和步道长度是多少？", ["梵天花海"], ["30000", "1500"], "梵天花海参数"),
        ("019", "香月花街大概多长多宽？", ["香月花街"], ["800", "8"], "香月花街参数"),
        ("020", "拈花堂开放到几点？", ["拈花堂"], ["9:30", "19:00"], "拈花堂开放"),
        ("021", "五灯湖湖面面积大约是多少？", ["五灯湖"], ["5000", "灯光秀"], "五灯湖参数"),
        ("022", "鹿鸣谷有什么自然特点？", ["鹿鸣谷"], ["20000", "90%"], "鹿鸣谷参数"),
        ("023", "灵山胜境坐落在哪里？", ["景区概况与千年历史渊源"], ["无锡", "太湖", "马山"], "景区位置"),
        ("024", "灵山胜境占地面积约多少？", ["景区概况与千年历史渊源"], ["30万", "5A"], "景区概况"),
        ("025", "九龙灌浴平日有哪些演出时间？", ["九龙灌浴"], ["10:00", "11:30", "13:30", "15:00"], "演出时间"),
        ("026", "灵山梵宫的吉祥颂演出多长时间？", ["灵山梵宫"], ["20分钟", "10:35"], "梵宫演出"),
        ("027", "五印坛城藏香体验什么时候有？", ["五印坛城"], ["10:00", "14:00", "40分钟"], "坛城体验"),
        ("028", "拈花广场开园仪式什么时候举行？", ["拈花广场"], ["9:30", "14:30"], "开园仪式"),
        ("029", "五灯湖灯光秀每天几点开始？", ["五灯湖"], ["19:00", "20:00", "30分钟"], "五灯湖演艺"),
        ("030", "其他实用建议里导游服务多少钱起？", ["其他实用建议"], ["300", "导游"], "导游服务"),
    ]
    for suffix, query, sources, facts, notes in fact_cases:
        cases.append(
            answer_case(
                case_id=f"B2_FACT_{suffix}",
                category="fact_qa",
                query=query,
                expected_sources=sources,
                required_facts=facts,
                notes=notes,
            )
        )

    history_cases = [
        ("001", "灵山胜境为什么被称为东方佛国？", ["景区概况与千年历史渊源"], ["东方佛国", "太湖佛国"], "景区定位"),
        ("002", "玄奘为什么把马山命名为小灵山？", ["小灵山的佛教缘起"], ["印度灵鹫山", "大般若经", "小灵山"], "小灵山缘起"),
        ("003", "祥符禅寺名称和北宋有什么关系？", ["祥符禅寺的千年兴衰"], ["北宋", "大中祥符", "宋真宗"], "祥符禅寺得名"),
        ("004", "现代灵山胜境是怎样一步步建成的？", ["现代灵山胜境的崛起"], ["1994", "1997", "2009"], "现代建设历程"),
        ("005", "灵山大佛和五方五佛理念有什么关系？", ["佛教文化的深度传承"], ["五方五佛", "赵朴初"], "五方五佛"),
        ("006", "灵山梵宫为什么能体现传统艺术和现代科技融合？", ["传统艺术与现代科技的完美融合"], ["东阳木雕", "敦煌壁画", "现代科技"], "梵宫工艺"),
        ("007", "九龙灌浴和祈福文化有什么关系？", ["祈福文化的特色体验"], ["九龙灌浴", "吉祥平安"], "祈福文化"),
        ("008", "灵山胜境和世界佛教论坛有什么关系？", ["世界佛教文化的交流平台"], ["世界佛教论坛", "永久会址"], "论坛会址"),
        ("009", "赵朴初先生与灵山大照壁有什么关系？", ["灵山大照壁"], ["赵朴初", "题写", "小灵山"], "赵朴初题字"),
        ("010", "五明桥里的五明是什么意思？", ["五明桥"], ["声明", "因明", "内明"], "五明文化"),
        ("011", "佛足坛为什么被看作佛教圣迹？", ["佛足坛"], ["佛足", "32种", "吉祥"], "佛足文化"),
        ("012", "五智门的五门和六柱分别象征什么？", ["五智门"], ["五方五佛", "六度波罗蜜"], "五智门象征"),
        ("013", "降魔浮雕讲述了什么佛教故事？", ["降魔浮雕"], ["魔王波旬", "觉悟成佛"], "降魔成道"),
        ("014", "阿育王柱象征什么佛教精神？", ["阿育王柱"], ["和平", "包容", "佛法"], "阿育王柱象征"),
        ("015", "拈花堂的文化内涵来自什么典故？", ["拈花堂"], ["拈花悟禅", "静心"], "拈花堂文化"),
    ]
    for suffix, query, sources, facts, notes in history_cases:
        cases.append(
            answer_case(
                case_id=f"B2_HISTORY_{suffix}",
                category="history_culture",
                query=query,
                expected_sources=sources,
                required_facts=facts,
                notes=notes,
            )
        )

    detail_cases = [
        ("001", "灵山大照壁适合怎么游玩？", ["灵山大照壁"], ["打卡", "合影"], "大照壁玩法"),
        ("002", "菩提大道有什么禅意体验？", ["菩提大道"], ["菩提树", "禅意"], "菩提大道体验"),
        ("003", "九龙灌浴表演有什么看点？", ["九龙灌浴"], ["花开见佛", "九条飞龙"], "九龙灌浴看点"),
        ("004", "百子戏弥勒为什么适合亲子互动？", ["百子戏弥勒"], ["百名", "孩童", "亲子"], "百子戏弥勒亲子"),
        ("005", "祥符禅寺里有哪些历史遗存？", ["祥符禅寺"], ["六角井", "千年古银杏"], "祥符禅寺遗存"),
        ("006", "灵山大佛有什么核心看点？", ["灵山大佛"], ["手印", "216级台阶"], "大佛看点"),
        ("007", "佛教文化博览馆主要展示什么？", ["佛教文化博览馆"], ["五方五佛", "万佛殿"], "博览馆展示"),
        ("008", "灵山梵宫为什么被称为东方卢浮宫？", ["灵山梵宫"], ["东方卢浮宫", "艺术"], "梵宫艺术"),
        ("009", "五印坛城有哪些藏式建筑特色？", ["五印坛城"], ["藏式", "白墙红边", "鎏金铜瓦"], "坛城建筑"),
        ("010", "曼飞龙塔为什么体现南传佛教特色？", ["曼飞龙塔"], ["南传佛教", "白塔", "傣族"], "曼飞龙塔特色"),
        ("011", "无尽意斋有什么纪念意义？", ["无尽意斋"], ["赵朴初", "故居", "书法"], "无尽意斋纪念"),
        ("012", "拈花广场的核心景观是什么？", ["拈花广场"], ["拈花微笑", "雕塑"], "拈花广场景观"),
        ("013", "梵天花海适合看什么？", ["梵天花海"], ["格桑花", "波斯菊", "木质步道"], "花海游玩"),
        ("014", "香月花街有哪些体验？", ["香月花街"], ["禅意文创", "非遗手作", "素面"], "花街体验"),
        ("015", "五灯湖夜间有什么特色？", ["五灯湖"], ["灯光秀", "水雾", "禅行"], "五灯湖夜景"),
    ]
    for suffix, query, sources, facts, notes in detail_cases:
        cases.append(
            answer_case(
                case_id=f"B2_ATTRACTION_{suffix}",
                category="attraction_detail",
                query=query,
                expected_sources=sources,
                required_facts=facts,
                notes=notes,
            )
        )

    route_cases = [
        ("001", "历史文化爱好者应该怎么游览灵山胜境？", ["历史文化爱好者路线"], ["祥符禅寺", "灵山大佛", "五印坛城"], "历史路线"),
        ("002", "自然风光爱好者适合走哪条路线？", ["自然风光爱好者路线"], ["佛足坛", "菩提大道", "曼飞龙塔"], "自然路线"),
        ("003", "带孩子游览灵山胜境怎么安排比较轻松？", ["亲子家庭路线"], ["九龙灌浴", "百子戏弥勒", "梵宫"], "亲子路线"),
        ("004", "想深度了解佛教文化，路线里应重点看哪些点？", ["历史文化爱好者路线"], ["祥符禅寺", "灵山梵宫", "三圣殿"], "文化深度路线"),
        ("005", "半天时间想看核心景观，应该优先哪些地方？", ["亲子家庭路线"], ["九龙灌浴", "佛手广场", "五印坛城"], "半日核心路线"),
        ("006", "喜欢太湖和园林景观，灵山胜境怎么走？", ["自然风光爱好者路线"], ["太湖", "灵山精舍", "梵宫广场"], "自然全景路线"),
        ("007", "第一次来灵山胜境，怎样安排不容易错过重点？", ["历史文化爱好者路线"], ["灵山大照壁", "灵山大佛", "灵山梵宫"], "首次游览"),
        ("008", "亲子游为什么推荐九龙灌浴和百子戏弥勒？", ["亲子家庭路线"], ["动态表演", "亲子互动"], "亲子原因"),
        ("009", "历史文化路线为什么会安排祥符禅寺？", ["历史文化爱好者路线"], ["千年古刹", "历史讲解"], "祥符禅寺路线价值"),
        ("010", "自然风光路线为什么会安排菩提大道？", ["自然风光爱好者路线"], ["太湖风光", "自然环境"], "菩提大道路线价值"),
    ]
    for suffix, query, sources, facts, notes in route_cases:
        cases.append(
            answer_case(
                case_id=f"B2_ROUTE_{suffix}",
                category="route_planning",
                query=query,
                expected_sources=sources,
                required_facts=facts,
                notes=notes,
            )
        )

    practical_cases = [
        ("001", "灵山胜境什么时候游览比较合适？", ["最佳游览时间"], ["春秋", "3-5月", "9-11月"], "最佳季节"),
        ("002", "灵山胜境建议几点前入园？", ["最佳游览时间"], ["9点前", "人流高峰"], "入园时间"),
        ("003", "九龙灌浴表演需要提前多久到？", ["九龙灌浴"], ["提前10分钟", "占位"], "演出占位"),
        ("004", "灵山胜境里面吃素斋大概要多少钱？", ["餐饮"], ["50", "35"], "餐饮价格"),
        ("005", "灵山精舍适合什么样的游客？", ["住宿"], ["禅意酒店", "早课体验"], "住宿体验"),
        ("006", "游览灵山胜境穿什么比较合适？", ["其他实用建议"], ["运动鞋", "防晒", "保暖"], "穿着建议"),
        ("007", "去灵山胜境建议带哪些物品？", ["其他实用建议"], ["相机", "充电宝", "雨伞"], "携带物品"),
        ("008", "灵山胜境导游服务适合哪些游客？", ["其他实用建议"], ["导游服务", "300元"], "导游建议"),
        ("009", "在灵山胜境游览时有哪些文明礼仪？", ["其他实用建议"], ["保持安静", "尊重宗教信仰"], "文明礼仪"),
        ("010", "五印坛城参观时有什么注意事项？", ["五印坛城"], ["禁止触摸", "禁止大声喧哗"], "坛城注意事项"),
    ]
    for suffix, query, sources, facts, notes in practical_cases:
        cases.append(
            answer_case(
                case_id=f"B2_PRACTICAL_{suffix}",
                category="practical_info",
                query=query,
                expected_sources=sources,
                required_facts=facts,
                notes=notes,
            )
        )

    guided_cases = [
        ("001", "它有什么特色？", 13, ["灵山大佛"], ["灵山大佛"], ["五印坛城"], "主动选择灵山大佛"),
        ("002", "这里适合孩子玩吗？", 11, ["百子戏弥勒"], ["孩童", "亲子"], ["灵山大佛"], "主动选择百子戏弥勒"),
        ("003", "这个地方看表演要注意什么？", 8, ["九龙灌浴"], ["演出", "提前"], ["五灯湖"], "主动选择九龙灌浴"),
        ("004", "它的建筑风格是什么？", 16, ["五印坛城"], ["藏式", "白墙"], ["灵山梵宫"], "主动选择五印坛城"),
        ("005", "这里有什么艺术价值？", 15, ["灵山梵宫"], ["艺术", "东方卢浮宫"], ["五明桥"], "主动选择灵山梵宫"),
        ("006", "这个景点适合拍照吗？", 3, ["灵山大照壁"], ["打卡", "合影"], ["祥符禅寺"], "主动选择大照壁"),
        ("007", "它和佛教智慧有什么关系？", 4, ["五明桥"], ["五明", "智慧"], ["九龙灌浴"], "主动选择五明桥"),
        ("008", "这里晚上有什么看点？", 23, ["五灯湖"], ["灯光秀", "夜间"], ["梵天花海"], "主动选择五灯湖"),
    ]
    for suffix, query, attraction_id, sources, facts, forbidden, notes in guided_cases:
        cases.append(
            answer_case(
                case_id=f"B2_GUIDED_{suffix}",
                category="guided_selection",
                query=query,
                selection={"mode": "attraction", "attraction_id": attraction_id},
                expected_sources=sources,
                required_facts=facts,
                forbidden_facts=forbidden,
                notes=notes,
            )
        )

    followup_cases = [
        ("001", "它适合拍照吗？", "灵山大照壁", ["灵山大照壁"], ["打卡", "合影"], ["灵山大佛"], "大照壁追问"),
        ("002", "它为什么适合亲子？", "百子戏弥勒", ["百子戏弥勒"], ["孩童", "亲子"], ["五印坛城"], "百子戏弥勒追问"),
        ("003", "这里的表演什么时候看？", "九龙灌浴", ["九龙灌浴"], ["10:00", "11:30"], ["五灯湖"], "九龙灌浴追问"),
        ("004", "这里有哪些工艺？", "灵山梵宫", ["灵山梵宫"], ["东阳木雕", "景泰蓝"], ["五明桥"], "梵宫追问"),
        ("005", "它的藏式特色体现在哪里？", "五印坛城", ["五印坛城"], ["藏式", "转经筒"], ["灵山大佛"], "五印坛城追问"),
        ("006", "这里适合晚上去吗？", "五灯湖", ["五灯湖"], ["夜间", "灯光秀"], ["菩提大道"], "五灯湖追问"),
    ]
    for suffix, query, subject, sources, facts, forbidden, notes in followup_cases:
        cases.append(
            answer_case(
                case_id=f"B2_FOLLOWUP_{suffix}",
                category="followup_context",
                query=query,
                context={"last_subject": subject},
                expected_sources=sources,
                required_facts=facts,
                forbidden_facts=forbidden,
                notes=notes,
            )
        )

    blind_cases = [
        ("001", "明天灵山胜境会不会下雨？", ["一定下雨", "一定不下雨"], "实时天气盲区"),
        ("002", "现在厕所排队要多久？", ["5分钟", "10分钟", "半小时"], "实时排队盲区"),
        ("003", "今天下午景区停车场还有多少空位？", ["100个", "还有空位", "已经满了"], "实时停车盲区"),
        ("004", "现在九龙灌浴这一场还剩几个座位？", ["还剩", "座位"], "实时座位盲区"),
        ("005", "明天门票会不会涨价？", ["一定涨价", "不会涨价"], "实时票价盲区"),
        ("006", "现在灵山梵宫里面人多不多？", ["不多", "很多", "不用排队"], "实时客流盲区"),
    ]
    for suffix, query, forbidden, notes in blind_cases:
        cases.append(
            refusal_case(
                case_id=f"B2_BLIND_{suffix}",
                query=query,
                forbidden_facts=forbidden,
                notes=notes,
            )
        )

    return cases


def assert_distribution(cases: list[dict[str, Any]]) -> None:
    actual = Counter(case["category"] for case in cases)
    if actual != EXPECTED_DISTRIBUTION:
        raise RuntimeError(
            f"Unexpected distribution: expected={EXPECTED_DISTRIBUTION}, actual={dict(actual)}"
        )
    if len(cases) != 100:
        raise RuntimeError(f"Expected 100 cases, got {len(cases)}.")


def main() -> int:
    cases = build_cases()
    assert_distribution(cases)
    OUTPUT_PATH.write_text(
        json.dumps(cases, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    loaded_cases = load_cases(OUTPUT_PATH)
    errors = validate_cases(loaded_cases)
    if errors:
        raise RuntimeError("\n".join(errors))

    print(
        json.dumps(
            {
                "ok": True,
                "output": str(OUTPUT_PATH),
                "case_count": len(cases),
                "distribution": dict(Counter(case["category"] for case in cases)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
