"""实时天气与景区风险颜色聚合接口。

聚合和风天气（QWeather）三个开放接口，归一化后统一返回给前端：

- 实时天气 ``/v7/weather/now``
- 气象预警 ``/weatheralert/v1/current/{lat}/{lon}``
- 空气质量 ``/airquality/v1/current/{lat}/{lon}``

设计要点：

- API KEY 只保存在服务端（``settings.qweather_api_key``），前端不接触密钥。
- 未配置 KEY 或上游异常时安全降级，返回 ``available=False``，不抛 5xx。
- 结果按 ``settings.qweather_cache_ttl_seconds`` 做进程内缓存，避免高频轮询消耗配额。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query

from app.core.config import Settings
from app.core.deps import get_app_settings

router = APIRouter()

# 和风天气图标代码 -> emoji（覆盖常见 1xx/3xx/4xx/5xx）
QW_ICON_EMOJI: dict[str, str] = {
    "100": "\u2600\uFE0F",
    "101": "\u26C5",
    "102": "\uD83C\uDF24\uFE0F",
    "103": "\u26C5",
    "104": "\u2601\uFE0F",
    "150": "\uD83C\uDF19",
    "151": "\uD83C\uDF19",
    "152": "\uD83C\uDF19",
    "153": "\uD83C\uDF19",
    "300": "\uD83C\uDF26\uFE0F",
    "301": "\uD83C\uDF27\uFE0F",
    "302": "\u26C8\uFE0F",
    "303": "\u26C8\uFE0F",
    "304": "\u26C8\uFE0F",
    "305": "\uD83C\uDF27\uFE0F",
    "306": "\uD83C\uDF27\uFE0F",
    "307": "\uD83C\uDF27\uFE0F",
    "308": "\uD83C\uDF27\uFE0F",
    "309": "\uD83C\uDF26\uFE0F",
    "310": "\uD83C\uDF27\uFE0F",
    "311": "\uD83C\uDF27\uFE0F",
    "312": "\uD83C\uDF27\uFE0F",
    "313": "\uD83C\uDF27\uFE0F",
    "314": "\uD83C\uDF27\uFE0F",
    "315": "\uD83C\uDF27\uFE0F",
    "316": "\uD83C\uDF27\uFE0F",
    "317": "\uD83C\uDF27\uFE0F",
    "318": "\uD83C\uDF27\uFE0F",
    "399": "\uD83C\uDF27\uFE0F",
    "400": "\uD83C\uDF28\uFE0F",
    "401": "\uD83C\uDF28\uFE0F",
    "402": "\u2744\uFE0F",
    "403": "\u2744\uFE0F",
    "404": "\uD83C\uDF28\uFE0F",
    "405": "\uD83C\uDF28\uFE0F",
    "406": "\uD83C\uDF28\uFE0F",
    "407": "\uD83C\uDF28\uFE0F",
    "408": "\uD83C\uDF28\uFE0F",
    "409": "\u2744\uFE0F",
    "410": "\u2744\uFE0F",
    "499": "\u2744\uFE0F",
    "500": "\uD83C\uDF2B\uFE0F",
    "501": "\uD83C\uDF2B\uFE0F",
    "502": "\uD83C\uDF2B\uFE0F",
    "503": "\uD83C\uDF2B\uFE0F",
    "504": "\uD83C\uDF2B\uFE0F",
    "505": "\uD83C\uDF2B\uFE0F",
    "506": "\uD83C\uDF2B\uFE0F",
    "507": "\uD83C\uDF2B\uFE0F",
    "508": "\uD83C\uDF2A\uFE0F",
    "509": "\uD83C\uDF2A\uFE0F",
    "510": "\uD83C\uDF2A\uFE0F",
    "511": "\uD83C\uDF2B\uFE0F",
    "512": "\uD83C\uDF2B\uFE0F",
    "513": "\uD83C\uDF2B\uFE0F",
    "514": "\uD83C\uDF2B\uFE0F",
    "515": "\uD83C\uDF2B\uFE0F",
    "900": "\uD83D\uDD25",
    "901": "\u2744\uFE0F",
}

# 预警/空气质量颜色代码兜底色值（上游未给出 RGB 时使用）
QW_COLOR_HEX: dict[str, str] = {
    "white": "#FFFFFF",
    "gray": "#9E9E9E",
    "grey": "#9E9E9E",
    "green": "#4CAF50",
    "blue": "#2196F3",
    "yellow": "#FFEB3B",
    "amber": "#FFC107",
    "orange": "#FF9800",
    "red": "#F44336",
    "purple": "#9C27B0",
    "black": "#000000",
}

_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _to_int(value: Any) -> int | None:
    """和风天气数值字段多为字符串，统一转 int，失败返回 None。"""
    try:
        if value is None or value == "":
            return None
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _to_float(value: Any, digits: int = 1) -> float | None:
    try:
        if value is None or value == "":
            return None
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _hex_from_rgb(color: Any, fallback_code: str = "") -> str | None:
    """把和风天气的 {red,green,blue} 颜色对象转成 #RRGGBB。"""
    if isinstance(color, dict):
        red, green, blue = color.get("red"), color.get("green"), color.get("blue")
        if all(isinstance(channel, int) for channel in (red, green, blue)):
            return f"#{red:02X}{green:02X}{blue:02X}"
        code = str(color.get("code") or "").lower()
        if code in QW_COLOR_HEX:
            return QW_COLOR_HEX[code]
    if fallback_code and fallback_code.lower() in QW_COLOR_HEX:
        return QW_COLOR_HEX[fallback_code.lower()]
    return None


async def _safe_get(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any] | None:
    """单个上游请求失败不影响整体聚合，返回 None 由调用方降级。"""
    try:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None
    except Exception:  # noqa: BLE001 - 上游任何异常都降级处理
        return None


def _normalize_now(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    now = payload.get("now")
    if not isinstance(now, dict):
        return None
    icon_code = str(now.get("icon") or "")
    return {
        "iconCode": icon_code,
        "icon": QW_ICON_EMOJI.get(icon_code, "\U0001F321\uFE0F"),
        "temp": _to_int(now.get("temp")),
        "feelsLike": _to_int(now.get("feelsLike")),
        "description": now.get("text") or "",
        "humidity": _to_int(now.get("humidity")),
        "windSpeed": _to_float(now.get("windSpeed")),  # km/h
        "windDir": now.get("windDir") or "",
        "windScale": now.get("windScale") or "",
        "precip": _to_float(now.get("precip")),
        "pressure": _to_int(now.get("pressure")),
        "vis": _to_int(now.get("vis")),
        "cloud": _to_int(now.get("cloud")),
        "dew": _to_int(now.get("dew")),
        "obsTime": now.get("obsTime"),
        "cityName": "\u7075\u5c71\u80dc\u5883",
    }


def _normalize_alert(payload: dict[str, Any] | None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        alerts = payload.get("alerts")
        if isinstance(alerts, list):
            for alert in alerts:
                if not isinstance(alert, dict):
                    continue
                color = alert.get("color") if isinstance(alert.get("color"), dict) else None
                event = alert.get("eventType") if isinstance(alert.get("eventType"), dict) else {}
                severity_color = str(alert.get("severityColor") or "")
                items.append(
                    {
                        "id": alert.get("id"),
                        "severity": alert.get("severity"),
                        "colorCode": (color or {}).get("code") or severity_color,
                        "color": _hex_from_rgb(color, severity_color),
                        "eventType": event.get("name") or "",
                        "eventCode": event.get("code") or "",
                        "headline": alert.get("headline") or "",
                        "description": alert.get("description") or "",
                        "instruction": alert.get("instruction") or "",
                        "pubTime": alert.get("pubTime"),
                    }
                )
    return {"hasAlert": len(items) > 0, "items": items}


def _normalize_air(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    indexes = payload.get("indexes")
    if not isinstance(indexes, list) or not indexes:
        return None
    chosen: dict[str, Any] | None = None
    for index in indexes:
        if isinstance(index, dict) and str(index.get("code")) == "cn-mee":
            chosen = index
            break
    if chosen is None:
        chosen = next((index for index in indexes if isinstance(index, dict)), None)
    if chosen is None:
        return None
    color = chosen.get("color") if isinstance(chosen.get("color"), dict) else None
    pollutant = chosen.get("primaryPollutant") if isinstance(chosen.get("primaryPollutant"), dict) else {}
    return {
        "aqi": _to_int(chosen.get("aqi")),
        "level": str(chosen.get("level") or ""),
        "category": chosen.get("category") or "",
        "color": _hex_from_rgb(color),
        "primaryPollutant": pollutant.get("name") or "",
    }


def _base_response(lat: float, lon: float, now_ts: int) -> dict[str, Any]:
    return {
        "available": False,
        "reason": "",
        "message": "",
        "source": "\u548c\u98ce\u5929\u6c14 QWeather",
        "updatedAt": now_ts,
        "location": {"lat": lat, "lon": lon},
        "weather": None,
        "alert": None,
        "air": None,
    }


@router.get("/current", summary="实时天气 + 景区预警颜色 + 空气质量")
async def get_current_weather(
    lat: float | None = Query(default=None, ge=-90.0, le=90.0, description="纬度，缺省用景区默认坐标"),
    lon: float | None = Query(default=None, ge=-180.0, le=180.0, description="经度，缺省用景区默认坐标"),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    """聚合和风天气实时天气、预警颜色与空气质量，供前端天气面板与地图颜色图层使用。"""

    latitude = lat if lat is not None else settings.qweather_default_lat
    longitude = lon if lon is not None else settings.qweather_default_lon
    now_ts = int(time.time())

    result = _base_response(latitude, longitude, now_ts)

    if not settings.qweather_api_key:
        result["reason"] = "not_configured"
        result["message"] = "\u672a\u914d\u7f6e\u548c\u98ce\u5929\u6c14 API KEY\uff08QWEATHER_API_KEY\uff09\uff0c\u5929\u6c14\u4e0e\u666f\u533a\u989c\u8272\u6682\u4e0d\u53ef\u7528\u3002"
        return result

    cache_key = f"{latitude:.4f},{longitude:.4f}"
    cached = _CACHE.get(cache_key)
    if cached and now_ts - cached[0] < settings.qweather_cache_ttl_seconds:
        return cached[1]

    base_url = f"https://{settings.qweather_api_host}"
    headers = {"X-QW-Api-Key": settings.qweather_api_key}
    lang = settings.qweather_lang

    try:
        async with asyncio.timeout(settings.qweather_timeout_seconds):
            async with httpx.AsyncClient(timeout=settings.qweather_timeout_seconds) as client:
                now_payload, alert_payload, air_payload = await asyncio.gather(
                    _safe_get(
                        client,
                        f"{base_url}/v7/weather/now",
                        {"location": f"{longitude},{latitude}", "lang": lang},
                        headers,
                    ),
                    _safe_get(
                        client,
                        f"{base_url}/weatheralert/v1/current/{latitude}/{longitude}",
                        {"lang": lang},
                        headers,
                    ),
                    _safe_get(
                        client,
                        f"{base_url}/airquality/v1/current/{latitude}/{longitude}",
                        {"lang": lang},
                        headers,
                    ),
                )
    except Exception:  # noqa: BLE001 - 超时/网络异常统一降级
        now_payload = alert_payload = air_payload = None

    weather = _normalize_now(now_payload)
    result["weather"] = weather
    result["alert"] = _normalize_alert(alert_payload)
    result["air"] = _normalize_air(air_payload)

    if weather is not None:
        result["available"] = True
    else:
        result["reason"] = "upstream_error"
        result["message"] = "\u548c\u98ce\u5929\u6c14\u63a5\u53e3\u6682\u65e0\u8fd4\u56de\uff08KEY \u65e0\u6548\u6216\u7f51\u7edc\u5f02\u5e38\uff09\u3002"

    _CACHE[cache_key] = (now_ts, result)
    return result
