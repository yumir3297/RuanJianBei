from __future__ import annotations

import re


def explicit_route_hours(query: str) -> int | None:
    """Return a whole-hour route budget only when the visitor stated one unambiguously."""
    numerals = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if re.search(r"至少|不少于|多于|(?<!不)超过|小时\s*(?:以?后|之后|以上|(?:又\s*)?[\d一二两三四五六七八九十]+\s*分)", query):
        return None
    if re.search(r"\d+\.\d+\s*(?:个)?小时|(?:\d+|[一二两三四五六七八九十])\s*(?:个)?小时半|(?:\d+|[一二两三四五六七八九十])\s*[-–—~～至到或]\s*(?:\d+|[一二两三四五六七八九十])\s*(?:个)?小时|[一二两三四五六七八九十]{2,}\s*(?:个)?小时", query):
        return None
    values = [numerals.get(token, int(token) if token.isdigit() else 0)
              for token in re.findall(r"(?<![\d.一二两三四五六七八九十])(\d{1,2}|[一二两三四五六七八九十])\s*(?:个)?小时", query)]
    if values and all(value == values[0] for value in values) and 1 <= values[0] <= 12:
        return values[0]
    return None
