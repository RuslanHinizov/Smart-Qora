"""Build the `smartqora` dataset: pseudo-label the full ICAERUS video set with the
current model, then fold in the real hand-labelled Zenodo frames as the quality
anchor.

Pseudo-labels are NOT ground truth — they carry the current model's mistakes.
The real Zenodo frames (datasets/sheep-gate, 639 hand-labelled) keep "one tight
box per sheep" in the mix; a tuned NMS (iou 0.5) trims most split boxes at
generation time. Expect a modest gain on the new-domain clips, not perfection —
hand-labelling is still the gold standard.

    python training/pseudo_label.py               # -> datasets/smartqora/
    python training/train.py --data datasets/smartqora/data.yaml \
        --model models/best.pt --name smartqora --epochs 80
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import cv2
import yaml

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "datasets" / "smartqora"
ZENODO = REPO / "datasets" / "sheep-gate"
CANONICAL = ["sheep", "cattle", "goat", "horse"]
SPLITS = ("train", "val", "test")

# hold whole clips out of training so evaluation is honest
VAL_CLIPS = {"23.11.23-13", "23.11.23-6"}
TEST_CLIPS = {"23.11.23-16", "23.11.23-2", "23.11.23-8"}
SKIP = {"23.11.23-1ther"}  # thermal — different modality, too few frames to learn


def split_for(stem: str) -> str:
    if stem in TEST_CLIPS:
        return "test"
    if stem in VAL_CLIPS:
        return "val"
    return "train"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--videos", default="videos/sheep_videos", help="dir of source .MP4s")
    ap.add_argument("--per-video", type=int, default=40, help="frames to sample per video")
    ap.add_argument("--keep-empty", type=int, default=3, help="max no-detection frames to keep per video (as negatives)")
    ap.add_argument("--model", default="models/best.pt")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--iou", type=float, default=0.50)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if OUT.exists():
        if not args.force:
            print(f"{OUT.relative_to(REPO)} exists — pass --force", file=sys.stderr)
            return 1
        shutil.rmtree(OUT)
    for s in SPLITS:
        (OUT / "images" / s).mkdir(parents=True, exist_ok=True)
        (OUT / "labels" / s).mkdir(parents=True, exist_ok=True)

    from ultralytics import YOLO
    model = YOLO(str(REPO / args.model))

    vids = sorted({p for ext in ("*.MP4", "*.mp4") for p in (REPO / args.videos).glob(ext)})
    counts = {s: 0 for s in SPLITS}
    for video in vids:
        stem = video.stem
        if stem in SKIP:
            print(f"  skip {stem}")
            continue
        split = split_for(stem)
        cap = cv2.VideoCapture(str(video))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step = max(1, total // args.per_video)
        kept = empties = 0
        for fidx in range(0, total, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            res = model.predict(frame, conf=args.conf, iou=args.iou, imgsz=args.imgsz, verbose=False)[0]
            lines = []
            for box in (res.boxes or []):
                cls = 0  # everything the current model finds here is a sheep
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx, cy, bw, bh = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            if not lines:
                empties += 1
                if empties > args.keep_empty:
                    continue
            name = f"{stem}_f{fidx:06d}"
            cv2.imwrite(str(OUT / "images" / split / f"{name}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            (OUT / "labels" / split / f"{name}.txt").write_text("\n".join(lines) + ("\n" if lines else ""))
            counts[split] += 1
            kept += 1
        cap.release()
        print(f"  {stem:18} -> {split:5}  {kept} frames ({min(empties, args.keep_empty)} empty)")

    # fold in the real Zenodo frames (already split in datasets/sheep-gate)
    zen = {s: 0 for s in SPLITS}
    if ZENODO.exists():
        for s in SPLITS:
            for img in (ZENODO / "images" / s).glob("*.jpg"):
                lbl = ZENODO / "labels" / s / f"{img.stem}.txt"
                if not lbl.is_file():
                    continue
                shutil.copy2(img, OUT / "images" / s / f"zen_{img.name}")
                shutil.copy2(lbl, OUT / "labels" / s / f"zen_{lbl.name}")
                zen[s] += 1
        print(f"\n  folded in real Zenodo frames: {dict(zen)}")
    else:
        print("\n  (datasets/sheep-gate not found — run prepare_dataset.py first for the real anchor)")

    (OUT / "data.yaml").write_text(yaml.safe_dump({
        "path": OUT.relative_to(REPO).as_posix(),
        "train": "images/train", "val": "images/val", "test": "images/test",
        "names": {i: n for i, n in enumerate(CANONICAL)},
    }, sort_keys=False))

    tot = {s: counts[s] + zen[s] for s in SPLITS}
    print(f"\n  totals (pseudo + real): {tot}")
    print(f"  wrote {(OUT / 'data.yaml').relative_to(REPO)}")
    print("  NOTE: test clips (held out): " + ", ".join(sorted(TEST_CLIPS)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
