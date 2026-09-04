"""Counting-accuracy evaluation: does the model actually count animals right?

Replays each labelled clip through the **real** line-crossing logic the backend
worker uses (`app.vision.counter.LineCrossingCounter` + `CenterSmoother`), twice:

  * ground truth  - MOT tracks from training/ground_truth/<clip>.json
  * prediction    - `LivestockDetector(weights).track()` frame by frame

Both passes share the same counting line and a simulated clock (frame / fps), so
the line geometry cancels out and the delta is pure detection + tracking error.

    python training/counting_eval.py --weights runs/sheep-gate/weights/best.pt
    python training/counting_eval.py --weights models/best.pt --baseline models/best.pt

Writes training/reports/counting_<timestamp>.json. Exits non-zero if the
`gate:` targets in config.yaml are missed.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import warnings
from pathlib import Path

import cv2
import yaml

warnings.filterwarnings("ignore", message=".*'half' is deprecated.*")
logging.getLogger("ultralytics").setLevel(logging.ERROR)

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

from app.vision.classes import canonical  # noqa: E402
from app.vision.counter import LineCrossingCounter  # noqa: E402
from app.vision.tracker import CenterSmoother  # noqa: E402

CONFIG = REPO / "training" / "config.yaml"
GT_DIR = REPO / "training" / "ground_truth"
REPORTS = REPO / "training" / "reports"


def tally_from_stream(events, line, inside):
    """events: iterable of (frame_idx, track_id, (cx, cy), now). Returns dict."""
    counter = LineCrossingCounter(tuple(line[0]), tuple(line[1]), inside)
    smoother = CenterSmoother()
    result = {"IN": 0, "OUT": 0, "crossing_ids": set(), "track_ids": set()}
    for fidx, tid, center, now in events:
        result["track_ids"].add(tid)
        smoothed = smoother.update(tid, (int(center[0]), int(center[1])))
        crossing = counter.update(tid, smoothed, now=now)
        counter.prune(now=now)
        if crossing:
            result[crossing.direction] += 1
            result["crossing_ids"].add(tid)
    return result


def gt_events(gt: dict):
    fps = gt["fps"]
    rows = []
    for tid_str, pts in gt["tracks"].items():
        tid = int(tid_str)
        for frame, cx, cy in pts:
            rows.append((int(frame), tid, (cx, cy), frame / fps))
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def pred_events(weights: str, gt: dict, ev: dict):
    from app.vision.detector import LivestockDetector

    logging.getLogger("ultralytics").setLevel(logging.ERROR)  # ultralytics resets it on import

    detector = LivestockDetector(
        weights, str(ev["device"]), ev["conf"], ev["iou"], ev["imgsz"],
        ev["tracker"], list(ev["allowed_classes"]), require_cuda=False, half_precision=ev["half"],
    )
    detector.reset_tracker()
    video = REPO / gt["video"]
    fps = gt["fps"]
    skip = ev.get("frame_skip", 0)
    cap = cv2.VideoCapture(str(video))
    rows, per_class = [], {}
    fidx = -1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        fidx += 1
        if skip and fidx % (skip + 1):
            continue
        res = detector.track(frame)
        if res.boxes is None:
            continue
        for box in res.boxes:
            if box.id is None:
                continue
            tid = int(box.id.item())
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
            rows.append((fidx, tid, ((x1 + x2) // 2, (y1 + y2) // 2), fidx / fps))
            cls = canonical(res.names[int(box.cls.item())]) or "?"
            per_class[cls] = per_class.get(cls, 0) + 1
    cap.release()
    return rows, per_class


def eval_weights(weights: str, ev: dict, clips: list[Path]) -> dict:
    per_clip, agg = [], {"gt_in": 0, "gt_out": 0, "pred_in": 0, "pred_out": 0,
                         "abs_in": 0, "abs_out": 0, "gt_total": 0,
                         "gt_tracks": 0, "pred_tracks": 0}
    for path in clips:
        gt = json.loads(path.read_text())
        line, inside = gt["line"], gt["inside_direction"]
        g = tally_from_stream(gt_events(gt), line, inside)
        prows, per_class = pred_events(weights, gt, ev)
        p = tally_from_stream(prows, line, inside)

        gt_net, pred_net = g["IN"] - g["OUT"], p["IN"] - p["OUT"]
        gt_total = g["IN"] + g["OUT"]
        row = {
            "clip": gt["clip"],
            "gt": {"in": g["IN"], "out": g["OUT"], "net": gt_net, "crossing_tracks": len(g["crossing_ids"])},
            "pred": {"in": p["IN"], "out": p["OUT"], "net": pred_net,
                     "crossing_tracks": len(p["crossing_ids"]), "total_tracks": len(p["track_ids"])},
            "net_error": abs(pred_net - gt_net),
            "counting_error_pct": round(abs(pred_net - gt_net) / max(gt_total, 1) * 100, 2),
            "dir_abs_error": {"in": abs(p["IN"] - g["IN"]), "out": abs(p["OUT"] - g["OUT"])},
            "id_switch_ratio": round(len(p["track_ids"]) / max(len(g["track_ids"]), 1), 2),
            "pred_class_mix": per_class,
        }
        per_clip.append(row)
        agg["gt_in"] += g["IN"]; agg["gt_out"] += g["OUT"]
        agg["pred_in"] += p["IN"]; agg["pred_out"] += p["OUT"]
        agg["abs_in"] += row["dir_abs_error"]["in"]; agg["abs_out"] += row["dir_abs_error"]["out"]
        agg["gt_total"] += gt_total
        agg["gt_tracks"] += len(g["track_ids"]); agg["pred_tracks"] += len(p["track_ids"])

    n = len(per_clip)
    overall = {
        "counting_error_pct": round(abs((agg["pred_in"] - agg["pred_out"]) - (agg["gt_in"] - agg["gt_out"]))
                                    / max(agg["gt_total"], 1) * 100, 2),
        "mae_in": round(agg["abs_in"] / n, 2),
        "mae_out": round(agg["abs_out"] / n, 2),
        "id_switch_ratio": round(agg["pred_tracks"] / max(agg["gt_tracks"], 1), 2),
        "gt_totals": {"in": agg["gt_in"], "out": agg["gt_out"]},
        "pred_totals": {"in": agg["pred_in"], "out": agg["pred_out"]},
    }
    return {"weights": weights, "per_clip": per_clip, "overall": overall}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", default="models/best.pt", help="model under test")
    ap.add_argument("--baseline", help="also evaluate this model for side-by-side comparison")
    ap.add_argument("--clips", nargs="*", type=int, help="restrict to these clip numbers")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text())
    ev, gate = cfg["eval"], cfg["gate"]

    clips = sorted(GT_DIR.glob("clip*.json"))
    if args.clips:
        clips = [p for p in clips if int(p.stem.replace("clip", "")) in args.clips]
    if not clips:
        raise SystemExit(f"no ground-truth files in {GT_DIR.relative_to(REPO)} - run prepare_dataset.py")

    main_result = eval_weights(args.weights, ev, clips)
    baseline_result = eval_weights(args.baseline, ev, clips) if args.baseline else None

    o = main_result["overall"]
    checks = [
        ("counting error %", o["counting_error_pct"], gate["counting_error_pct"],
         o["counting_error_pct"] <= gate["counting_error_pct"]),
        ("ID switch ratio", o["id_switch_ratio"], gate["id_switch_ratio"],
         o["id_switch_ratio"] <= gate["id_switch_ratio"]),
    ]

    ts = time.strftime("%Y%m%d-%H%M%S")
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": ts, "eval_settings": ev,
        "result": main_result, "baseline": baseline_result,
        "gate": {name: {"value": val, "target": tgt, "pass": ok} for name, val, tgt, ok in checks},
        "pass": all(ok for *_, ok in checks),
    }
    out = REPORTS / f"counting_{ts}.json"
    out.write_text(json.dumps(report, indent=2, default=str))

    print("\nper-clip (model under test):")
    print(f"  {'clip':>4}  {'gt in/out':>10}  {'pred in/out':>12}  {'err %':>7}  {'id ratio':>9}")
    for r in main_result["per_clip"]:
        print(f"  {r['clip']:>4}  {r['gt']['in']:>4}/{r['gt']['out']:<5}  "
              f"{r['pred']['in']:>5}/{r['pred']['out']:<6}  {r['counting_error_pct']:>7.2f}  "
              f"{r['id_switch_ratio']:>9.2f}")
    if baseline_result:
        b = baseline_result["overall"]
        print(f"\nbaseline {args.baseline}: err%={b['counting_error_pct']}  "
              f"id_ratio={b['id_switch_ratio']}  mae_in={b['mae_in']}  mae_out={b['mae_out']}")

    print("\n" + "=" * 60)
    print(f"{'metric':<20}{'value':>10}{'target':>10}   result")
    for name, val, tgt, ok in checks:
        print(f"{name:<20}{val:>10.2f}{tgt:>10.2f}   {'PASS' if ok else 'FAIL'}")
    print("=" * 60)
    print(f"report: {out.relative_to(REPO)}")
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
