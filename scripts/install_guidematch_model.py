"""Install the locally supplied GuideMatch seed-13 handoff without overwriting it."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile


FILES = {
    "encoder_config/config.json": "b7b2c2363bb604a6ff5b037b15de4ae91b5aad6393b11e6f66ad707dd7e7310a",
    "guidematch_config.json": "d936c93063bb84dd67827947b06a722b956c102b185f5053d0cb61c755dbaadf",
    "model.pt": "c999999e8f78149bdfdbb9830a4590b43046c0e47e79c05a363cf2c0a0d0842e",
    "source_metrics.json": "c30b8b7141713e26beee4987ce1fd1bc0bd2e20d955873a58f50ef8c74691446",
    "tokenizer/special_tokens_map.json": "5aa43c2f985a25296d5a5ce621c2f77376ca8091a47993c492fd5460b895b140",
    "tokenizer/tokenizer.json": "b0d34f6f7b3287af74acab7a7023dea7140d249981c7dd20f4f0d5f89bc265b8",
    "tokenizer/tokenizer_config.json": "cbe004ed102fc7d706925907e6772aeca04fbe3d90d56a95a09ed75b3f30e7e9",
    "tokenizer/vocab.txt": "45bbac6b341c319adc98a532532882e91a9cefc0329aa57bac9ae761c27b291c",
}


def verify(root):
    for name, expected in FILES.items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or linked model file: {name}")
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != expected:
            raise ValueError(f"model hash mismatch: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="trusted handoff models/guidematch_final directory")
    parser.add_argument("--destination", type=Path, default=Path(__file__).resolve().parents[1] / ".cache/guidematch/seed13")
    args = parser.parse_args()
    verify(args.source)
    if args.destination.exists():
        verify(args.destination)
        print(f"Already installed and verified: {args.destination}")
        return
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".guidematch-install-", dir=args.destination.parent) as temp:
        staged = Path(temp) / "model"
        for name in FILES:
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.source / name, target)
        verify(staged)
        # Refuse a concurrent installation instead of replacing any data.
        if args.destination.exists():
            raise FileExistsError(args.destination)
        staged.rename(args.destination)
    print(f"Installed and verified: {args.destination}")


if __name__ == "__main__":
    main()
