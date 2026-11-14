#!/usr/bin/env python3
"""Validate and evaluate the frozen GuideLoop pilot fixtures."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_COUNTS = {"pairs_dev": 20, "pairs_test": 40, "replay": 18, "notices": 3}
EXPECTED_TEST = {"reuse": 20, "distinct": 12, "clarify": 8}
PAIR_FILES = {"pairs_dev": "pairs_dev.jsonl", "pairs_test": "pairs_test.jsonl"}


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path.name}: {exc}") from exc


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read {path.name}: {exc}") from exc
    for number, line in enumerate(lines, 1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{number}: invalid JSON: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}:{number}: row must be an object")
        rows.append(item)
    return rows


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_fixtures(root: Path) -> dict[str, Any]:
    root = Path(root)
    manifest = _json(root / "manifest.json")
    _require(manifest.get("schema_version") == 1, "manifest schema_version must be 1")
    _require(manifest.get("review_status") == "fixture_author_reviewed", "manifest review_status missing")
    datasets = {**{name: _jsonl(root / filename) for name, filename in PAIR_FILES.items()},
                "replay": _jsonl(root / "replay.jsonl"), "notices": _json(root / "notices.json")}
    _require(isinstance(datasets["notices"], list), "notices must be a list")
    ids: set[str] = set()
    families: dict[str, set[str]] = {}
    labels = {"reuse", "distinct", "clarify"}
    pair_fields = {"case_id", "family_id", "left", "right", "expected", "reason", "origin"}
    context_fields = {"text"}
    for split in ("pairs_dev", "pairs_test"):
        for row in datasets[split]:
            _require(pair_fields <= row.keys(), f"{split}: missing required fields {sorted(pair_fields-row.keys())}")
            cid = row["case_id"]
            _require(cid not in ids, f"duplicate case_id {cid}")
            ids.add(cid)
            _require(row["expected"] in labels, f"{cid}: invalid expected label")
            _require(bool(row["family_id"]), f"{cid}: family_id is required")
            _require(row["origin"] in {"synthetic_case", "public_source_derived"}, f"{cid}: invalid origin")
            for side in ("left", "right"):
                ctx = row[side]
                _require(isinstance(ctx, dict) and context_fields <= ctx.keys(), f"{cid}: {side}.text is required")
                _require(bool(str(ctx.get("text", "")).strip()), f"{cid}: {side}.text is empty")
            if row["expected"] == "distinct" and row["reason"] == "cross_object":
                left, right = row["left"], row["right"]
                _require(bool(left.get("poi_id")) and bool(right.get("poi_id")), f"{cid}: cross_object requires poi_id on both sides")
                _require((left.get("poi_id"), left.get("target_id")) != (right.get("poi_id"), right.get("target_id")), f"{cid}: cross_object scopes must differ")
            if row["expected"] == "distinct" and row["reason"] == "temporal_conflict":
                left, right = row["left"], row["right"]
                _require(bool(left.get("queried_date")) and bool(right.get("queried_date")), f"{cid}: temporal_conflict requires queried_date on both sides")
                _require(left.get("queried_date") != right.get("queried_date"), f"{cid}: temporal_conflict dates must differ")
        families[split] = {row["family_id"] for row in datasets[split]}
    overlap = families["pairs_dev"] & families["pairs_test"]
    _require(not overlap, f"family_id leakage across splits: {sorted(overlap)}")
    dev_texts = {side["text"] for row in datasets["pairs_dev"] for side in (row["left"], row["right"])}
    test_texts = {side["text"] for row in datasets["pairs_test"] for side in (row["left"], row["right"])}
    text_leakage = dev_texts & test_texts
    _require(not text_leakage, f"question text leakage across splits: {sorted(text_leakage)}")
    dist = Counter(row["expected"] for row in datasets["pairs_test"])
    _require(len(datasets["pairs_dev"]) == EXPECTED_COUNTS["pairs_dev"], "pairs_dev must contain 20 rows")
    _require(len(datasets["pairs_test"]) == EXPECTED_COUNTS["pairs_test"], "pairs_test must contain 40 rows")
    _require(dict(dist) == EXPECTED_TEST, f"pairs_test distribution must be {EXPECTED_TEST}, got {dict(dist)}")
    distinct = [row for row in datasets["pairs_test"] if row["expected"] == "distinct"]
    _require(sum(row["reason"] == "cross_object" for row in distinct) >= 6, "test split requires at least 6 cross_object negatives")
    _require(sum(row["reason"] == "temporal_conflict" for row in distinct) >= 4, "test split requires at least 4 temporal_conflict negatives")
    replay = datasets["replay"]
    _require(len(replay) == EXPECTED_COUNTS["replay"], "replay must contain 18 rows")
    replay_ids = set()
    replay_fields = {"case_id", "family_id", "version", "poi_id", "question", "queried_date", "expected", "scenario", "origin"}
    expected_fields = {"decision", "required_claims", "forbidden_claims", "source_ids", "expected_revision"}
    for row in replay:
        _require(replay_fields <= row.keys(), f"replay row missing fields: {sorted(replay_fields-row.keys())}")
        _require(row["case_id"] not in replay_ids, f"duplicate replay case_id {row['case_id']}")
        replay_ids.add(row["case_id"])
        _require(expected_fields <= row["expected"].keys(), f"{row['case_id']}: missing expected fields")
        _require(row["origin"] == "synthetic_replay", f"{row['case_id']}: replay origin must be synthetic_replay")
    _require(Counter(row["version"] for row in replay) == {"V1":6,"V2":6,"V3":6}, "replay must have 6 rows each for V1/V2/V3")
    notices = datasets["notices"]
    _require(len(notices) == EXPECTED_COUNTS["notices"], "notices must contain 3 snapshots")
    notice_ids = set()
    for row in notices:
        _require(bool(row.get("notice_id")), "notice_id is required")
        _require(bool(row.get("origin")), f"{row['notice_id']}: origin is required")
        _require(bool(row.get("label")) and "模拟" in row["label"], f"{row['notice_id']}: notice must be labeled as simulated")
        _require(row.get("origin") == "synthetic_notice", f"{row['notice_id']}: expected synthetic_notice origin")
        notice_ids.add(row["version"])
    _require(notice_ids == {"V1","V2","V3"}, "notices must include V1/V2/V3")
    hashes = manifest.get("sha256", {})
    for name in ("pairs_dev.jsonl", "pairs_test.jsonl", "replay.jsonl", "notices.json"):
        expected = hashes.get(name)
        _require(bool(expected), f"manifest missing sha256 for {name}")
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        _require(actual == expected, f"sha256 mismatch for {name}: expected {expected}, got {actual}")
    for name, count in EXPECTED_COUNTS.items():
        _require(len(datasets[name]) == count, f"manifest count mismatch: {name}")
    return {"pairs_dev":len(datasets["pairs_dev"]),"pairs_test":len(datasets["pairs_test"]),"replay":len(replay),"notices":len(notices),"test_expected":dict(dist),"sha256":hashes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--fixtures", required=True, type=Path)
    pairs = sub.add_parser("pairs")
    pairs.add_argument("--variant", choices=("rules",), required=True)
    pairs.add_argument("--fixtures", required=True, type=Path)
    pairs.add_argument("--out", required=True, type=Path)
    replay = sub.add_parser("replay")
    replay.add_argument("--base-url", required=True)
    replay.add_argument("--fixtures", required=True, type=Path)
    replay.add_argument("--out", required=True, type=Path)
    replay.add_argument("--admin-password", default="admin123")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            report = validate_fixtures(args.fixtures)
            print(json.dumps({"status":"valid","counts":{k:report[k] for k in ("pairs_dev","pairs_test","replay","notices")},"test_expected":report["test_expected"],"sha256":report["sha256"]},ensure_ascii=False,indent=2,sort_keys=True))
            return 0
        if args.command == "pairs":
            validate_fixtures(args.fixtures)
            metrics, _ = evaluate_pairs(args.fixtures, args.out, args.variant)
            print(json.dumps(metrics,ensure_ascii=False,indent=2,sort_keys=True))
            return 0 if metrics["passed"] else 1
        if args.command == "replay":
            validate_fixtures(args.fixtures)
            metrics = replay_live(args.base_url,args.fixtures,args.out,args.admin_password)
            print(json.dumps(metrics,ensure_ascii=False,indent=2,sort_keys=True))
            return 0 if metrics["all_passed"] else 1
    except ValueError as exc:
        print(f"fixture error: {exc}",file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"environment error: {exc}",file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"environment error: {exc}",file=sys.stderr)
        return 2
    return 2


def evaluate_pairs(fixtures: Path, out: Path, variant: str = "rules") -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Score pair decisions with the configured local Chinese embedder and hard scope rules."""
    import sys
    backend = Path(__file__).resolve().parents[2] / "backend"
    sys.path.insert(0, str(backend))
    from app.core.config import get_settings
    from app.schemas.guide_loop import QuestionContext
    from app.services.guide_loop.matching import match_pair
    from app.services.rag.embedder import SentenceTransformerEmbedder

    settings = get_settings()
    embedder = SentenceTransformerEmbedder(settings.embedding_model_name, cache_dir=settings.model_cache_root, local_files_only=True)
    def load(name):
        return _jsonl(fixtures / name)
    dev, test = load("pairs_dev.jsonl"), load("pairs_test.jsonl")
    texts = list(dict.fromkeys(row[side]["text"] for row in dev + test for side in ("left", "right")))
    vectors = embedder.embed_texts(texts)
    vector_by_text = dict(zip(texts, vectors))
    from app.services.guide_loop.matching import _cosine
    dev_scores = [_cosine(vector_by_text[r["left"]["text"]], vector_by_text[r["right"]["text"]]) for r in dev]
    candidates = sorted({0.0, 1.0, *dev_scores, *(min(1.0, score + 1e-6) for score in dev_scores)})
    def decide(row, threshold):
        left, right = row["left"], row["right"]
        score = _cosine(vector_by_text[left["text"]], vector_by_text[right["text"]])
        result = match_pair(QuestionContext(**left), QuestionContext(**right), score, threshold)
        return score, result.decision
    # Choose the development threshold minimizing total label errors; ties prefer the higher threshold.
    threshold = max(candidates, key=lambda t: (-sum(decide(r, t)[1] != r["expected"] for r in dev), t))
    predictions = []
    for row in test:
        score, predicted = decide(row, threshold)
        predictions.append({"case_id":row["case_id"],"family_id":row["family_id"],"expected":row["expected"],"predicted":predicted,"score":score,"threshold":threshold,"reason":row["reason"],"origin":row["origin"]})
    confusion = {label:{target:sum(p["expected"]==label and p["predicted"]==target for p in predictions) for target in ("reuse","distinct","clarify")} for label in ("reuse","distinct","clarify")}
    correct_reuse = confusion["reuse"]["reuse"]
    false_merges = confusion["distinct"]["reuse"]
    clarify_correct = confusion["clarify"]["clarify"]
    actual_merges = sum(row["predicted"] == "reuse" for row in predictions)
    metrics = {"variant":variant,"embedder":embedder.model_name,"threshold_from_dev":threshold,"test_count":len(test),"confusion":confusion,"correct_reuse":correct_reuse,"false_merges":false_merges,"clarify_correct":clarify_correct,"merge_precision":correct_reuse/actual_merges if actual_merges else 0.0,"acceptance":{"recall_at_least_16_of_20":correct_reuse>=16,"false_merge_zero_of_12":false_merges==0,"clarify_8_of_8":clarify_correct==8},"passed":correct_reuse>=16 and false_merges==0 and clarify_correct==8}
    out.mkdir(parents=True,exist_ok=True)
    (out/"metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n")
    (out/"predictions.jsonl").write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in predictions))
    return metrics,predictions


def _request_json(url: str, payload: dict, token: str | None = None) -> dict:
    import urllib.request
    data = json.dumps(payload, ensure_ascii=False).encode()
    headers = {"Content-Type":"application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


def _chat_sse(base_url: str, payload: dict) -> tuple[str, list[dict], dict | None]:
    import urllib.request
    request = urllib.request.Request(base_url.rstrip("/")+"/api/chat/stream",data=json.dumps(payload,ensure_ascii=False).encode(),headers={"Content-Type":"application/json","Accept":"text/event-stream"},method="POST")
    text_parts, sources, context = [], [], None
    with urllib.request.urlopen(request,timeout=90) as response:
        block=[]
        for raw in response:
            line=raw.decode("utf-8").rstrip("\r\n")
            if not line:
                if block:
                    event="message"; data=[]
                    for item in block:
                        if item.startswith("event:"): event=item[6:].strip()
                        elif item.startswith("data:"): data.append(item[5:].strip())
                    try: obj=json.loads("\n".join(data)) if data else {}
                    except json.JSONDecodeError: obj={}
                    if event=="text": text_parts.append(obj.get("text",""))
                    elif event=="sources": sources.extend(obj.get("docs",[]))
                    elif event=="context": context=obj.get("guide_loop")
                    elif event=="error": raise RuntimeError(obj.get("message","SSE error"))
                    block=[]
            elif not line.startswith(":"):
                block.append(line)
    return "".join(text_parts),sources,context


def replay_live(base_url: str, fixtures: Path, out: Path, admin_password: str) -> dict[str, Any]:
    from urllib.error import HTTPError
    base=base_url.rstrip("/")
    token=_request_json(base+"/api/auth/login",{"password":admin_password})["token"]
    def post(path,payload): return _request_json(base+path,payload,token)
    def observe(cluster, suffix, text, poi, target, queried_date=None):
        payload={"event_id":f"{cluster}-{suffix}","session_key":f"session-{suffix}","cluster_id":cluster,"text":text,"poi_id":poi,"target_id":target,"evidence_ids":[],"result_code":"unanswered","category":"retrieval_gap","replay_id":suffix,"origin":"synthetic"}
        if queried_date is not None: payload["queried_date"]=queried_date
        return post("/api/admin/guide-loop/observations",payload)
    def publish(cluster, scope_poi,target,action,alias,answer,source,evidence,base_revision,effective_from="2026-11-10T00:00:00+08:00",effective_until=None):
        draft=post(f"/api/admin/guide-loop/cases/{cluster}/draft",{"base_revision":base_revision,"action":action,"poi_id":scope_poi,"target_id":target,"alias":alias,"answer":answer,"evidence":{"evidence_id":evidence,"source_ref":source},"effective_from":effective_from,"effective_until":effective_until})
        verified=post(f"/api/admin/guide-loop/cases/{cluster}/verify",{"draft_id":draft["draft_id"]})
        if not verified.get("passed"): raise RuntimeError(f"server verification failed for {cluster}")
        return post(f"/api/admin/guide-loop/cases/{cluster}/publish",{"draft_id":draft["draft_id"],"base_revision":base_revision,"source_reviewed":True})
    observe("pilot-alias","seed","莲花里的人物是谁？","bathing","prince")
    alias_revision=publish("pilot-alias","bathing","prince","add_alias","谁在莲花里？|花里的小孩是谁？|莲花里是谁？","莲花里有太子佛立像。","无锡方志办公室公开资料","wuxi_gazetteer_bathing_20130305","0")["revision_id"]
    observe("pilot-notice","seed","今天演出时间？","bathing","bath_show","2026-11-10")
    notice_revision="0"
    notice_revisions={}
    rows=_jsonl(fixtures/"replay.jsonl")
    notices=_json(fixtures/"notices.json")
    notice_by_version={row["version"]:row for row in notices}
    predictions=[]
    for version in ("V1","V2","V3"):
        notice=notice_by_version[version]
        action="add_alias" if version=="V1" else "replace_fact" if version=="V2" else "withdraw"
        published=publish("pilot-notice","bathing","bath_show",action,"那旧公告的时间还算吗？|今天下一场几点？",notice.get("claim") or "",notice["label"],"notice_bathing_show",notice_revision,notice["effective_from"],notice.get("effective_until"))
        notice_revision=published["revision_id"]
        notice_revisions[version]=notice_revision
        for row in (r for r in rows if r["version"]==version):
            text,sources,context=_chat_sse(base,{"query":row["question"],"session_id":"gl-replay-"+row["case_id"],"text_only":True,"guide_loop":{"poi_id":row["poi_id"]}})
            expected=row["expected"]
            checks={"decision":bool(context and context.get("decision")==expected["decision"]),"required_claims":all(claim in text for claim in expected["required_claims"]),"forbidden_claims":not any(claim in text for claim in expected["forbidden_claims"]),"source_ids":set(expected["source_ids"]) <= {source.get("evidence_id") for source in sources}}
            revision_expectation=expected.get("expected_revision")
            expected_revision=alias_revision if revision_expectation=="active_alias" else notice_revisions[version] if revision_expectation=="active_notice" else None
            checks["revision_matches"] = (context.get("revision_id") if context else None) == expected_revision
            predictions.append({"case_id":row["case_id"],"version":version,"queried_date":row["queried_date"],"expected":expected,"actual":{"decision":context.get("decision") if context else None,"revision_id":context.get("revision_id") if context else None,"text":text,"source_ids":[s.get("evidence_id") for s in sources]},"checks":checks,"passed":all(checks.values())})
    out.mkdir(parents=True,exist_ok=True)
    (out/"predictions.jsonl").write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in predictions))
    metrics={"case_count":len(predictions),"passed":sum(row["passed"] for row in predictions),"failed":sum(not row["passed"] for row in predictions),"alias_revision":alias_revision,"notice_revisions":notice_revisions,"all_passed":all(row["passed"] for row in predictions)}
    (out/"replay_metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n")
    return metrics


if __name__ == "__main__":
    raise SystemExit(main())
