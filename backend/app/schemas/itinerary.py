from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ItineraryConstraints(StrictModel):
    companions: list[str] = Field(default_factory=list, max_length=12)
    available_minutes: int | None = Field(default=None, ge=1, le=720)
    interests: list[str] = Field(default_factory=list, max_length=20)
    required_spots: list[str] = Field(default_factory=list, max_length=50)
    excluded_spots: list[str] = Field(default_factory=list, max_length=50)
    unresolved_required_names: list[str] = Field(default_factory=list, max_length=50)
    unresolved_excluded_names: list[str] = Field(default_factory=list, max_length=50)
    walking_preference: str | None = Field(default=None, max_length=100)
    rest_every_minutes: int | None = Field(default=None, ge=15, le=240)


class EvidenceReference(StrictModel):
    evidence_type: Literal["published_content", "visitor_input", "estimate"]
    reference_id: str | None = Field(default=None, max_length=100)
    label: str = Field(default="", max_length=160)


class ItineraryStop(StrictModel):
    stop_id: UUID = Field(default_factory=uuid4)
    kind: Literal["visit", "rest"]
    spot_code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=160)
    source_entry_id: str | None = Field(default=None, max_length=100)
    source_revision_id: str | None = Field(default=None, max_length=100)
    legacy_spot_id: str | None = Field(default=None, max_length=100)
    legacy_content_version: str | None = Field(default=None, max_length=100)
    duration_minutes: int | None = Field(default=None, ge=1, le=720)
    duration_basis: Literal["source", "user", "estimate", "unknown"] = "unknown"
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=20)
    locked_fields: list[Literal["stop", "position", "name", "spot_code", "duration"]] = Field(
        default_factory=list, max_length=5
    )
    created_by: Literal["manual", "ai", "template", "demo_synthetic"] = "manual"

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("停留点名称不能为空")
        return value

    @model_validator(mode="after")
    def validate_kind_fields(self) -> ItineraryStop:
        if self.kind == "rest" and (self.spot_code or self.source_entry_id or self.source_revision_id):
            raise ValueError("休息点不能绑定景点或知识条目")
        if self.duration_minutes is None and self.duration_basis != "unknown":
            raise ValueError("缺少停留时长时，依据必须为 unknown")
        if self.duration_minutes is not None and self.duration_basis == "unknown":
            raise ValueError("已填写停留时长时，必须说明其依据")
        if self.source_revision_id and not self.source_entry_id:
            raise ValueError("发布修订引用必须同时包含知识条目引用")
        return self


class ItineraryLeg(StrictModel):
    from_stop_id: UUID
    to_stop_id: UUID
    duration_minutes: int | None = Field(default=None, ge=1, le=720)
    duration_basis: Literal["source", "estimate", "unknown"] = "unknown"
    evidence: list[EvidenceReference] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_duration_evidence(self) -> ItineraryLeg:
        if self.from_stop_id == self.to_stop_id:
            raise ValueError("路段起点和终点必须不同")
        if self.duration_minutes is None and self.duration_basis != "unknown":
            raise ValueError("缺少路段时长时，依据必须为 unknown")
        if self.duration_minutes is not None and self.duration_basis == "unknown":
            raise ValueError("已填写路段时长时，必须说明其依据")
        return self


class ItinerarySourceReference(StrictModel):
    source_type: Literal["preset_route", "recommendation", "published_content"]
    source_id: str = Field(min_length=1, max_length=100)
    label: str = Field(default="", max_length=160)
    content_version: str | None = Field(default=None, max_length=100)


class PublishedCatalogEntryRead(StrictModel):
    site_id: str
    spot_code: str
    entry_id: str
    published_revision_id: str
    title: str
    aliases: list[str] = Field(default_factory=list)
    source_label: str = ""
    latitude: float | None = None
    longitude: float | None = None
    coordinate_evidence_id: str | None = None
    coordinate_system: str | None = None
    environment: Literal["indoor", "outdoor", "mixed", "unknown"] = "unknown"
    environment_source_id: str | None = None


class PublishedCatalogResponse(StrictModel):
    site_id: str
    digest: str
    items: list[PublishedCatalogEntryRead]


class StartTourRequest(StrictModel):
    expected_version: int = Field(ge=1)


class UpgradeItineraryRequest(StrictModel):
    expected_version: int = Field(ge=1)


class TourSnapshotV2(StrictModel):
    schema_version: Literal[2] = 2
    constraints: ItineraryConstraints = Field(default_factory=ItineraryConstraints)
    stops: list[ItineraryStop] = Field(default_factory=list, max_length=50)
    legs: list[ItineraryLeg] = Field(default_factory=list, max_length=49)
    source: Literal["manual", "preset", "recommendation"] = "manual"
    source_references: list[ItinerarySourceReference] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_identity_and_legs(self) -> TourSnapshotV2:
        stop_ids = [stop.stop_id for stop in self.stops]
        if len(stop_ids) != len(set(stop_ids)):
            raise ValueError("stop_id 不能重复")
        known_ids = set(stop_ids)
        for leg in self.legs:
            if leg.from_stop_id not in known_ids or leg.to_stop_id not in known_ids:
                raise ValueError("路段必须引用当前快照中的停留点")
        return self


class SaveItineraryV2Request(StrictModel):
    expected_version: int = Field(ge=1)
    snapshot: TourSnapshotV2


class CreateItineraryProposalRequest(StrictModel):
    expected_version: int = Field(ge=1)
    progress_version: int = Field(default=0, ge=0)
    draft_digest: str = Field(min_length=64, max_length=64)
    draft_snapshot: TourSnapshotV2
    text: str = Field(min_length=2, max_length=1000)

    @field_validator("text")
    @classmethod
    def trim_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("修改需求不能为空")
        return value


class ApplyItineraryProposalRequest(StrictModel):
    expected_version: int = Field(ge=1)
    progress_version: int = Field(ge=0)
    draft_digest: str = Field(min_length=64, max_length=64)


class AddVisit(StrictModel):
    type: Literal["add_visit"]
    name: str = Field(min_length=1, max_length=160)
    spot_code: str | None = Field(default=None, min_length=1, max_length=100)
    before_stop_id: UUID | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=720)


class RemoveStop(StrictModel):
    type: Literal["remove_stop"]
    stop_id: UUID


class ReplaceVisit(StrictModel):
    type: Literal["replace_visit"]
    stop_id: UUID
    name: str = Field(min_length=1, max_length=160)
    spot_code: str | None = Field(default=None, min_length=1, max_length=100)


class MoveStop(StrictModel):
    type: Literal["move_stop"]
    stop_id: UUID
    before_stop_id: UUID | None = None


class SetDuration(StrictModel):
    type: Literal["set_duration"]
    stop_id: UUID
    duration_minutes: int | None = Field(default=None, ge=1, le=720)


class AddRest(StrictModel):
    type: Literal["add_rest"]
    name: str = Field(default="休息", min_length=1, max_length=160)
    before_stop_id: UUID | None = None
    duration_minutes: int = Field(ge=1, le=720)


class UpdateConstraints(StrictModel):
    type: Literal["update_constraints"]
    constraints: ItineraryConstraints


class SetLock(StrictModel):
    type: Literal["set_lock"]
    stop_id: UUID
    field: Literal["stop", "position", "name", "spot_code", "duration"]
    locked: bool


ItineraryOperation = Annotated[
    Union[AddVisit, RemoveStop, ReplaceVisit, MoveStop, SetDuration, AddRest, UpdateConstraints, SetLock],
    Field(discriminator="type"),
]


def upgrade_snapshot(raw: dict) -> TourSnapshotV2:
    """Adapt a W01 snapshot without treating legacy IDs or flags as verified facts."""
    constraints = raw.get("constraints") if isinstance(raw.get("constraints"), dict) else {}
    source = raw.get("source", "manual")
    if source not in {"manual", "preset", "recommendation"}:
        source = "manual"
    stops: list[dict] = []
    for old in raw.get("stops", []) if isinstance(raw.get("stops", []), list) else []:
        if not isinstance(old, dict):
            continue
        name = old.get("name")
        if not isinstance(name, str) or not name.strip():
            name = "未解析地点"
        stops.append({
            "stop_id": str(uuid4()), "kind": "visit", "spot_code": None, "name": name,
            "source_entry_id": None, "source_revision_id": None,
            "legacy_spot_id": str(old["spot_id"]) if old.get("spot_id") is not None else None,
            "legacy_content_version": str(old["published_content_version"])
            if old.get("published_content_version") is not None else None,
            "duration_minutes": None, "duration_basis": "unknown",
            "created_by": "template" if source != "manual" else "manual",
        })
    known_keys = set(ItineraryConstraints.model_fields)
    normalized_constraints = {key: value for key, value in constraints.items() if key in known_keys}
    # Legacy required/excluded labels have no stable code in W01; keep them explicit as unresolved names.
    for key in ("required_spots", "excluded_spots"):
        values = normalized_constraints.pop(key, [])
        unresolved_key = "unresolved_" + ("required_names" if key == "required_spots" else "excluded_names")
        normalized_constraints[unresolved_key] = [str(value) for value in values if value is not None]
    return TourSnapshotV2(
        constraints=normalized_constraints,
        stops=stops,
        source=source,
        source_references=raw.get("source_references", []) if isinstance(raw.get("source_references", []), list) else [],
    )
