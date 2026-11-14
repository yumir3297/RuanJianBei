"""Compare the existing FAQ route and local GuideMatch on labelled pairs."""
import argparse
from collections import Counter
import json
import time

from app.services.qa.faq_matcher import FAQEntry, FAQMatcher
from app.services.qa.faq_path_resolver import resolve_faq_path_for_request
from app.services.qa.guidematch_gate import GuideMatchGate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--pairs", required=True)
    args = parser.parse_args()
    gate = GuideMatchGate(args.model_dir, device="cpu")
    counts = Counter()
    started = time.monotonic()
    with open(args.pairs, encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            matcher = FAQMatcher()
            matcher.add([FAQEntry("candidate", "general", [row["right"]["text"]], "synthetic answer", ["synthetic"])])
            kwargs = dict(audience=None, persona="guide", vision_present=False, scoped_attraction=False)
            before = resolve_faq_path_for_request(matcher, row["left"]["text"], **kwargs) is not None
            after = resolve_faq_path_for_request(matcher, row["left"]["text"], guidematch_gate=gate, **kwargs) is not None
            counts[(row["expected"], before, after)] += 1
    print(json.dumps({"counts": [{"expected": k[0], "before_reuse": k[1], "after_reuse": k[2], "count": v} for k, v in sorted(counts.items())], "seconds": round(time.monotonic() - started, 3)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
