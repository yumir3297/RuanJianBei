from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass

from app.schemas.knowledge_workspace import ParsedSection


@dataclass(frozen=True, slots=True)
class ImportChange:
    kind: str
    incoming: ParsedSection | None = None
    previous: ParsedSection | None = None


def section_identity(section: ParsedSection) -> str:
    if section.stable_id:
        return f"id:{section.stable_id.strip().casefold()}"
    path = (section.section_path or "").strip().casefold()
    # Page and array offsets move after insertions, so they cannot safely identify
    # a changed section across source versions.
    if (path.startswith("第 ") and path.endswith(" 页")) or (
        path.startswith("条目 ") and path[3:].isdigit()
    ):
        return ""
    return f"path:{path}" if path else ""


def _content_hash(section: ParsedSection) -> str:
    return hashlib.sha256(section.content.encode("utf-8")).hexdigest()


def compare_sections(previous: list[ParsedSection], incoming: list[ParsedSection]) -> list[ImportChange]:
    """Compare source sections conservatively; possible removals never delete data."""
    old_counts = Counter(identity for section in previous if (identity := section_identity(section)))
    new_counts = Counter(identity for section in incoming if (identity := section_identity(section)))
    old_by_identity = {
        section_identity(section): section
        for section in previous
        if section_identity(section) and old_counts[section_identity(section)] == 1
    }
    new_by_identity = {
        section_identity(section): section
        for section in incoming
        if section_identity(section) and new_counts[section_identity(section)] == 1
    }

    changes: list[ImportChange] = []
    matched_old: set[int] = set()
    matched_new: set[int] = set()
    for identity in old_by_identity.keys() & new_by_identity.keys():
        old, new = old_by_identity[identity], new_by_identity[identity]
        matched_old.add(id(old))
        matched_new.add(id(new))
        changes.append(ImportChange("unchanged" if _content_hash(old) == _content_hash(new) else "modified", new, old))

    # Exact content is a safe fallback when the parser has no stable structural
    # identifier (common for plain PDF pages). It never guesses a changed match.
    old_hashes: dict[str, list[ParsedSection]] = {}
    new_hashes: dict[str, list[ParsedSection]] = {}
    for section in previous:
        if id(section) not in matched_old:
            old_hashes.setdefault(_content_hash(section), []).append(section)
    for section in incoming:
        if id(section) not in matched_new:
            new_hashes.setdefault(_content_hash(section), []).append(section)
    for digest in old_hashes.keys() & new_hashes.keys():
        if len(old_hashes[digest]) == len(new_hashes[digest]) == 1:
            old, new = old_hashes[digest][0], new_hashes[digest][0]
            matched_old.add(id(old))
            matched_new.add(id(new))
            changes.append(ImportChange("unchanged", new, old))

    for section in incoming:
        if id(section) not in matched_new:
            ambiguous = bool(section_identity(section)) and new_counts[section_identity(section)] > 1
            changes.append(ImportChange("conflict" if ambiguous else "added", section, None))
    for section in previous:
        if id(section) not in matched_old:
            changes.append(ImportChange("possibly_removed", None, section))
    return changes
