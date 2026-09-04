"""Sample frames from a site recording for hand-labelling.

The Zenodo set is 100% IN-direction and one location. Before a real deployment,
grab clips from the actual gate (especially at least one OUT-direction pass),
run this to thin them to a labelling-friendly frame rate, optionally pre-label
with the current model, then correct in CVAT / Label Studio and fold the result
into datasets/sheep-gate/{images,labels}/train.

    python training/extract_frames.py --video videos/gate_out_01.MP4 --fps 2
    python training/extract_frames.py --video videos/gate_out_01.MP4 --fps 2 \
        --prelabel models/best.pt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--fps", type=float, default=2.0, help="target sampling rate")
    ap.add_argument("--out", type=Path, help="output dir (default: datasets/_staging/<video stem>)")
    ap.add_argument("--prelabel", help="weights to write draft YOLO labels with")
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--jpeg-quality", type=int, default=92)
    args = ap.parse_args()

    video = args.video if args.video.is_absolute() else REPO / args.video
    if not video.is_file():
        print(f"no such video: {video}", file=sys.stderr)
        return 1
    out = args.out or REPO / "datasets" / "_staging" / video.stem
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "labels").mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, round(src_fps / args.fps))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"{video.name}: {src_fps:.1f} fps, {total} frames -> every {step}th frame")

    model = None
    if args.prelabel:
        from ultralytics import YOLO
        model = YOLO(args.prelabel)

    kept = 0
    for fidx in range(0, total, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
        ok, frame = cap.read()
        if not ok:
            continue
        stem = f"{video.stem}_frame{fidx:06d}"
        cv2.imwrite(str(out / "images" / f"{stem}.jpg"), frame,
                    [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])
        label_path = out / "labels" / f"{stem}.txt"
        if model is not None:
            res = model.predict(frame, conf=args.conf, verbose=False)[0]
            lines = []
            h, w = frame.shape[:2]
            for box in (res.boxes or []):
                cls = int(box.cls.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                cx, cy, bw, bh = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h, (x2 - x1) / w, (y2 - y1) / h
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            label_path.write_text("\n".join(lines) + ("\n" if lines else ""))
        else:
            label_path.touch()
        kept += 1
    cap.release()
    print(f"wrote {kept} frames to {out.relative_to(REPO)}")
    if model is not None:
        print("pre-labels are DRAFTS - correct them before training")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
