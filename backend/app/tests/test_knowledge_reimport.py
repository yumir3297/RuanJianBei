from app.schemas.knowledge_workspace import ParsedSection
from app.services.knowledge.import_diff import compare_sections


def test_reimport_matches_stable_ids_across_reorder_and_marks_insertions() -> None:
    previous = [
        ParsedSection(title="入口", content="入口信息", stable_id="entry"),
        ParsedSection(title="展厅", content="旧展厅内容", stable_id="hall"),
    ]
    incoming = [
        ParsedSection(title="新序言", content="新增序言", stable_id="preface"),
        ParsedSection(title="展厅", content="新展厅内容", stable_id="hall"),
        ParsedSection(title="入口", content="入口信息", stable_id="entry"),
    ]

    changes = compare_sections(previous, incoming)
    assert sorted(change.kind for change in changes) == ["added", "modified", "unchanged"]
    modified = next(change for change in changes if change.kind == "modified")
    assert modified.previous and modified.previous.content == "旧展厅内容"
    assert modified.incoming and modified.incoming.content == "新展厅内容"


def test_reimport_does_not_use_page_number_as_identity_or_remove_missing_content() -> None:
    previous = [ParsedSection(title="第一章", content="原内容", section_path="第 1 页")]
    incoming = [
        ParsedSection(title="新增插页", content="插入内容", section_path="第 1 页"),
        ParsedSection(title="第一章", content="原内容", section_path="第 2 页"),
    ]

    changes = compare_sections(previous, incoming)
    assert sum(change.kind == "added" for change in changes) == 1
    assert sum(change.kind == "unchanged" for change in changes) == 1
    assert not any(change.kind == "possibly_removed" for change in changes)
