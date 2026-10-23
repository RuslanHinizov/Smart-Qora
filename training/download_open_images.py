"""Fetch a small, labelled Open Images V7 livestock subset.

This avoids the unusable 9-million-image full download shown in the web page.
Open Images' official selection API still fetches a roughly 4.8 GB global
metadata index before it can select a handful of images, so that cost is made
explicit instead of happening by surprise. The exported YOLO data stays in
datasets/ and is never committed to Git.

Example:
    pip install -r training/requirements-data.txt
    python training/download_open_images.py --per-class 1200
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DESTINATION = REPO / "datasets" / "_downloads" / "open-images-v7"
# Dog is intentionally included as a negative class.  It is exported in the
# staging dataset so review can ensure a dog never becomes a sheep label.
CLASSES = ("Sheep", "Cattle", "Goat", "Horse", "Dog")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-class", type=int, default=1200,
                        help="maximum labelled images per selected class (default: 1200)")
    parser.add_argument("--split", default="train", choices=("train", "validation", "test"))
    parser.add_argument("--allow-large-metadata", action="store_true",
                        help="confirm the one-time ~4.8 GB official metadata download")
    args = parser.parse_args()
    if args.per_class < 1:
        parser.error("--per-class must be positive")
    if not args.allow_large_metadata:
        print(
            "Open Images needs a one-time ~4.8 GB metadata download even for a small subset. "
            "Re-run with --allow-large-metadata to confirm.",
            file=sys.stderr,
        )
        return 2

    try:
        import fiftyone as fo
        import fiftyone.zoo as foz
    except ImportError:
        print("missing FiftyOne. Run: pip install -r training/requirements-data.txt", file=sys.stderr)
        return 1

    # max_samples bounds storage. The zoo returns only images with official
    # detection annotations for one of the requested classes.
    dataset = foz.load_zoo_dataset(
        "open-images-v7",
        split=args.split,
        label_types=["detections"],
        classes=list(CLASSES),
        max_samples=args.per_class * len(CLASSES),
        dataset_name="smart-qora-open-images-v7",
    )
    DESTINATION.mkdir(parents=True, exist_ok=True)
    dataset.export(
        export_dir=str(DESTINATION),
        dataset_type=fo.types.YOLOv5Dataset,
        label_field="ground_truth",
        classes=list(CLASSES),
    )
    print(f"exported {len(dataset)} images to {DESTINATION.relative_to(REPO)}")
    print("Next: review labels, remove Dog labels to make dog-only negative frames, then merge the four livestock classes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
