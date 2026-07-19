from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, ValidationError

# 调试用：保存 Coze 原始响应到文件
_COZE_DEBUG_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".coze_debug"


class CozeRoutePlannerError(RuntimeError):
    pass


class CozeRouteStop(BaseModel):
    attraction_id: str = ""
    reason: str = ""
    name: str = ""
    suggested_duration: str = ""
    highlights: list[str] = Field(default_factory=list)


class CozeRoutePlanResponse(BaseModel):
    answer: str = Field(min_length=1)
    route_stops: list[CozeRouteStop] = Field(default_factory=list)
    adjustments: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    warning: str = ""
    live_data_timestamp: str = ""


@dataclass(frozen=True, slots=True)
class CozeRoutePlan:
    answer: str
    route_stops: list[dict]
    adjustments: list[str]
    sources: list[str]
    warning: str
    live_data_timestamp: str
    raw_payload: dict


class CozeRoutePlanner:
    def __init__(
        self,
        *,
        run_url: str,
        token: str,
        timeout_seconds: float = 12.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.run_url = run_url.strip()
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds
        self._client = http_client

    @property
    def is_configured(self) -> bool:
        return bool(self.run_url and self.token)

    async def run(self, payload: dict[str, str]) -> CozeRoutePlan:
        if not self.is_configured:
            raise CozeRoutePlannerError("Coze route planner is not configured.")

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.post(
                self.run_url,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise CozeRoutePlannerError(f"Coze request failed: {exc}") from exc
        finally:
            if owns_client:
                await client.aclose()

        try:
            outer_payload = response.json()
        except ValueError as exc:
            raise CozeRoutePlannerError("Coze response is not valid JSON.") from exc

        # 调试：保存原始响应到文件
        _dump_coze_response(outer_payload)

        result_payload: dict
        parse_path = "dict"
        if isinstance(outer_payload.get("result_json"), dict):
            result_payload = outer_payload["result_json"]
        elif isinstance(outer_payload.get("result_json"), str):
            raw = outer_payload["result_json"]
            try:
                result_payload = json.loads(raw)
                parse_path = "json.loads"
            except ValueError:
                fixed = _try_fix_common_llm_json_errors(raw)
                try:
                    result_payload = json.loads(fixed)
                    parse_path = "fix+json.loads"
                except ValueError:
                    result_payload = _extract_route_plan_with_regex(raw)
                    parse_path = "regex"
                    if not result_payload.get("answer"):
                        raise CozeRoutePlannerError(
                            f"Coze result_json is not valid JSON after fix + regex.\n"
                            f"First 300 chars: {raw[:300]}"
                        )
        else:
            result_payload = outer_payload
        if not isinstance(result_payload, dict):
            raise CozeRoutePlannerError("Coze result payload must be a JSON object.")

        route_stops = result_payload.get("route_stops") or (result_payload.get("route") or {}).get("route_stops") or []
        # 过滤掉没有 attraction_id 的无效 stop（正则兜底可能产生空对象）
        if isinstance(route_stops, list):
            route_stops = [s for s in route_stops if isinstance(s, dict) and s.get("attraction_id")]
        try:
            validated = CozeRoutePlanResponse.model_validate(
                {
                    "answer": str(result_payload.get("answer", "")).strip(),
                    "route_stops": route_stops,
                    "adjustments": result_payload.get("adjustments") or [],
                    "sources": result_payload.get("sources") or [],
                    "warning": str(result_payload.get("warning", "") or ""),
                    "live_data_timestamp": str(result_payload.get("live_data_timestamp", "") or ""),
                }
            )
        except ValidationError as exc:
            raise CozeRoutePlannerError(f"Coze result violates route contract: {exc}") from exc

        print(f"[COZE] parse_path={parse_path}, stops={len(validated.route_stops)}, answer_len={len(validated.answer)}", flush=True)

        return CozeRoutePlan(
            answer=validated.answer,
            route_stops=[stop.model_dump() for stop in validated.route_stops],
            adjustments=validated.adjustments,
            sources=validated.sources,
            warning=validated.warning,
            live_data_timestamp=validated.live_data_timestamp,
            raw_payload=result_payload,
        )


def _dump_coze_response(payload: dict) -> None:
    """将 Coze 原始响应保存到 .coze_debug/ 目录，便于分析 JSON 解析失败模式。"""
    try:
        _COZE_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = _COZE_DEBUG_DIR / f"coze_resp_{ts}_{int(time.time() * 1000) % 10000}.json"
        fname.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass  # 调试用途，不影响主流程


def _try_fix_common_llm_json_errors(raw: str) -> str:
    """修复 LLM 生成 JSON 时的常见错误，返回修复后的字符串（仍可能不是合法 JSON，需兜底）。"""
    import re

    text = raw.strip()

    # 1. 去掉 markdown 代码块包裹
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # 2. 修复 "highlights": ["..."]  被写成 "highlights":"["..."]"
    text = re.sub(r'"(highlights|adjustments|sources)"\s*:\s*"(\[.*?\])"', r'"\1": \2', text)

    # 3. 修复尾部多余逗号（e.g. "answer": "...", ... ,}）
    text = re.sub(r",(\s*[}\]])", r"\1", text)

    # 4. 修复单引号 JSON（LLM 有时会用单引号）
    # 简单处理：替换键值对中能用双引号的单引号
    if '"' not in text and "'" in text:
        text = text.replace("'", '"')

    return text


def _extract_route_plan_with_regex(text: str) -> dict:
    """当 LLM 生成的 JSON 无法解析时，用正则提取关键字段。
    
    核心思路：先找到 "route_stops": [ 的位置，然后用花括号深度计数
    找到匹配的结束 ]，而非简单的 .*? 匹配（会被内嵌数组的 ] 截断）。
    """
    import re

    result: dict = {}

    # ---- answer ----
    m = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if m:
        result["answer"] = m.group(1).replace('\\"', '"').replace("\\n", "\n")

    # ---- route_stops（深度匹配外层数组） ----
    stops: list[dict] = []
    array_match = re.search(r'"route_stops"\s*:\s*\[', text)
    if array_match:
        array_start = array_match.end() - 1  # 指向 '['
        depth = 0
        array_end = -1
        for i in range(array_start, len(text)):
            ch = text[i]
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    array_end = i
                    break
        if array_end > array_start:
            inner = text[array_start + 1 : array_end]
            # 逐个解析 { ... } 对象
            obj_depth = 0
            obj_start = -1
            in_string = False
            escape = False
            for i, ch in enumerate(inner):
                if escape:
                    escape = False
                    continue
                if ch == "\\":
                    escape = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    if obj_depth == 0:
                        obj_start = i
                    obj_depth += 1
                elif ch == "}":
                    obj_depth -= 1
                    if obj_depth == 0 and obj_start >= 0:
                        obj_text = inner[obj_start : i + 1]
                        stop = _parse_route_stop_obj(obj_text)
                        if stop.get("attraction_id"):
                            stops.append(stop)
                        obj_start = -1
    result["route_stops"] = stops

    # ---- adjustments ----
    m = re.search(r'"adjustments"\s*:\s*\[', text)
    if m:
        arr_start = m.end() - 1
        arr_end = _find_closing_bracket(text, arr_start)
        if arr_end > arr_start:
            adj_text = text[arr_start + 1 : arr_end]
            result["adjustments"] = re.findall(r'"((?:[^"\\]|\\.)*)"', adj_text)
    if "adjustments" not in result:
        result["adjustments"] = []

    # ---- sources ----
    m = re.search(r'"sources"\s*:\s*\[', text)
    if m:
        arr_start = m.end() - 1
        arr_end = _find_closing_bracket(text, arr_start)
        if arr_end > arr_start:
            src_text = text[arr_start + 1 : arr_end]
            result["sources"] = re.findall(r'"((?:[^"\\]|\\.)*)"', src_text)
    if "sources" not in result:
        result["sources"] = []

    # ---- warning ----
    m = re.search(r'"warning"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if m:
        result["warning"] = m.group(1).replace('\\"', '"')
    else:
        result["warning"] = ""

    # ---- live_data_timestamp ----
    m = re.search(r'"live_data_timestamp"\s*:\s*"([^"]*)"', text)
    if m:
        result["live_data_timestamp"] = m.group(1)
    else:
        result["live_data_timestamp"] = ""

    return result


def _find_closing_bracket(text: str, start: int) -> int:
    """从 text[start] 的 '[' 开始，用深度计数找到匹配的 ']'。返回索引，失败返回 -1。"""
    if start >= len(text) or text[start] != "[":
        return -1
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _parse_route_stop_obj(obj_text: str) -> dict:
    """从 route_stop 的 JSON 对象文本中提取字段。"""
    import re
    stop: dict = {}
    if m := re.search(r'"attraction_id"\s*:\s*"([^"]*)"', obj_text):
        stop["attraction_id"] = m.group(1)
    if m := re.search(r'"name"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_text):
        stop["name"] = m.group(1).replace('\\"', '"')
    if m := re.search(r'"reason"\s*:\s*"((?:[^"\\]|\\.)*)"', obj_text):
        stop["reason"] = m.group(1).replace('\\"', '"')
    if m := re.search(r'"suggested_duration"\s*:\s*"([^"]*)"', obj_text):
        stop["suggested_duration"] = m.group(1)
    if m := re.search(r'"highlights"\s*:\s*\[(.*?)\]', obj_text, re.DOTALL):
        highlights = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
        stop["highlights"] = [h.replace('\\"', '"') for h in highlights]
    return stop
