from __future__ import annotations

import json
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, Field, ValidationError


class CozeRoutePlannerError(RuntimeError):
    pass


class CozeRouteStop(BaseModel):
    attraction_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    name: str = ""
    suggested_duration: str = ""
    highlights: list[str] = Field(default_factory=list)


class CozeRoutePlanResponse(BaseModel):
    answer: str = Field(min_length=1)
    route_stops: list[CozeRouteStop] = Field(min_length=1)
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

        result_payload = outer_payload.get("result_json", outer_payload)
        if isinstance(result_payload, str):
            try:
                result_payload = json.loads(result_payload)
            except ValueError as exc:
                raise CozeRoutePlannerError("Coze result_json is not valid JSON.") from exc
        if not isinstance(result_payload, dict):
            raise CozeRoutePlannerError("Coze result payload must be a JSON object.")

        route_stops = result_payload.get("route_stops") or (result_payload.get("route") or {}).get("route_stops") or []
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

        return CozeRoutePlan(
            answer=validated.answer,
            route_stops=[stop.model_dump() for stop in validated.route_stops],
            adjustments=validated.adjustments,
            sources=validated.sources,
            warning=validated.warning,
            live_data_timestamp=validated.live_data_timestamp,
            raw_payload=result_payload,
        )
