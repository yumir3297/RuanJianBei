from __future__ import annotations

import argparse
import json
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion

from common import LABELS, metrics_from_predictions, read_jsonl, root_dir, write_json


def pair_text(row: dict) -> str:
    left, right = sorted([row["left"]["text"], row["right"]["text"]])
    return f"左问：{left} [PAIR] 右问：{right}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    root = root_dir()
    output = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    train = read_jsonl(root / "data/splits/train.jsonl")
    dev = read_jsonl(root / "data/splits/dev.jsonl")

    features = FeatureUnion(
        [
            ("char", TfidfVectorizer(analyzer="char", ngram_range=(2, 5), min_df=2, max_features=30000)),
            ("word", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, max_features=12000)),
        ]
    )
    x_train = features.fit_transform([pair_text(row) for row in train])
    x_dev = features.transform([pair_text(row) for row in dev])
    classifier = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=args.seed,
        C=2.0,
    )
    classifier.fit(x_train, [row["expected"] for row in train])
    predicted = classifier.predict(x_dev).tolist()
    metrics = metrics_from_predictions([row["expected"] for row in dev], predicted, LABELS)
    metrics.update({"model": "tfidf_logistic_regression", "seed": args.seed})
    write_json(output / "metrics.json", metrics)
    with (output / "predictions.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row, guess in zip(dev, predicted):
            handle.write(
                json.dumps(
                    {"case_id": row["case_id"], "expected": row["expected"], "predicted": guess},
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"TF-IDF baseline macro-F1={metrics['macro_f1']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
