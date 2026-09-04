"""Run the real vision pipeline (detector + tracker + line-crossing counter) over
one or more video files and print the IN / OUT tally — the same code the live
worker uses, so it's a faithful offline check of a model / line / tracker setup.

    python scripts/count_video.py videos/23.11.10-1.MP4 --line 0,570,1920,660 --inside UP
    python scripts/count_video.py "videos/sheep_videos/*.MP4" --frame-skip 2
"""

from __future__ import annotations

import argparse
import glob
import sys
import time
from pathlib import Path

import cv2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.vision.counter import LineCrossingCounter  # noqa: E402
from app.vision.detector import LivestockDetector  # noqa: E402
from app.vision.tracker import CenterSmoother  # noqa: E402


def run(video: Path, args) -> dict:
    det = LivestockDetector(
        str(REPO / args.model), args.device, args.conf, args.iou, args.imgsz,
        args.tracker, ["sheep", "cattle", "goat", "horse"], require_cuda=False, half_precision=True)
    det.reset_tracker()
    counter = LineCrossingCounter(
        (args.line[0], args.line[1]), (args.line[2], args.line[3]), args.inside,
        min_track_updates=args.min_track_updates,
        line2=((args.line2[0], args.line2[1]), (args.line2[2], args.line2[3])) if args.line2 else None)
    smoother = CenterSmoother()

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    ins = outs = 0
    cross_ids: set[int] = set()
    all_ids: set[int] = set()
    by_class: dict[str, int] = {}
    fidx = -1
    t0 = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        fidx += 1
        if args.frame_skip and fidx % (args.frame_skip + 1):
            continue
        res = det.track(frame)
        if res.boxes is None:
            continue
        for box in res.boxes:
            if box.id is None:
                continue
            tid = int(box.id.item())
            all_ids.add(tid)
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            c = smoother.update(tid, ((x1 + x2) // 2, (y1 + y2) // 2))
            ev = counter.update(tid, c, now=fidx / fps)
            if ev:
                cross_ids.add(tid)
                cls = res.names[int(box.cls.item())]
                by_class[cls] = by_class.get(cls, 0) + 1
                ins += ev.direction == "IN"
                outs += ev.direction == "OUT"
        counter.prune(now=fidx / fps)
    cap.release()
    return {
        "video": video.name, "frames": fidx + 1, "seconds": round(time.time() - t0, 1),
        "in": ins, "out": outs, "net": ins - outs,
        "crossing_tracks": len(cross_ids), "total_tracks": len(all_ids),
        "id_fragmentation": round(len(all_ids) / max(len(cross_ids), 1), 1),
        "by_class": by_class,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+", help="paths or globs")
    ap.add_argument("--model", default="models/best.pt")
    ap.add_argument("--line", default="0,570,1920,660", help="x1,y1,x2,y2")
    ap.add_argument("--line2", default="", help="x1,y1,x2,y2 — second tripwire (dual-line mode)")
    ap.add_argument("--inside", default="UP", choices=["UP", "DOWN", "LEFT", "RIGHT"])
    ap.add_argument("--frame-skip", type=int, default=2)
    ap.add_argument("--min-track-updates", type=int, default=3)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--iou", type=float, default=0.70)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--device", default="0")
    ap.add_argument("--tracker", default="botsort_reid.yaml")
    args = ap.parse_args()
    args.line = [int(v) for v in args.line.split(",")]
    args.line2 = [int(v) for v in args.line2.split(",")] if args.line2 else None

    paths: list[Path] = []
    for pattern in args.videos:
        hits = [Path(p) for p in glob.glob(pattern)] or [Path(pattern)]
        paths.extend(p if p.is_absolute() else REPO / p for p in hits)

    print(f"model={args.model} tracker={args.tracker} line={args.line} inside={args.inside} "
          f"skip={args.frame_skip} min_track_updates={args.min_track_updates}\n")
    print(f"  {'video':24} {'in':>4} {'out':>4} {'net':>4} {'xtracks':>8} {'alltracks':>10} {'frag':>6}")
    tot_in = tot_out = 0
    for path in paths:
        if not path.is_file():
            print(f"  {path.name:24}  (missing)")
            continue
        r = run(path, args)
        tot_in += r["in"]; tot_out += r["out"]
        print(f"  {r['video']:24} {r['in']:>4} {r['out']:>4} {r['net']:>4} "
              f"{r['crossing_tracks']:>8} {r['total_tracks']:>10} {r['id_fragmentation']:>6}"
              + (f"   {r['by_class']}" if len(r["by_class"]) > 1 else ""))
    print(f"\n  {'TOTAL':24} {tot_in:>4} {tot_out:>4} {tot_in - tot_out:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
