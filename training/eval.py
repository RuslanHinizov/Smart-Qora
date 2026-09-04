"""Detection metrics on the held-out test split.

    python training/eval.py --weights runs/sheep-gate/weights/best.pt
    python training/eval.py --weights models/best.pt        # baseline (shipped model)

Writes training/reports/detection_<timestamp>.json and prints a gate table.
Exits non-zero if the mAP targets in config.yaml `gate:` are missed.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import yaml
from ultralytics import YOLO

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "training" / "config.yaml"
REPORTS = REPO / "training" / "reports"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weights", default="models/best.pt")
    ap.add_argument("--split", default="test", choices=["train", "val", "test"])
    ap.add_argument("--data", default="datasets/sheep-gate/data.yaml")
    args = ap.parse_args()

    cfg = yaml.safe_load(CONFIG.read_text())
    ev, gate = cfg["eval"], cfg["gate"]
    data_path = REPO / args.data
    if not data_path.is_file():
        raise SystemExit(f"{args.data} not found - run training/prepare_dataset.py first")

    model = YOLO(args.weights)
    metrics = model.val(data=str(data_path), split=args.split, imgsz=ev["imgsz"],
                        conf=ev["conf"], iou=ev["iou"], half=ev["half"], device=ev["device"],
                        project=str(REPO / "runs" / "val"), name=f"eval_{args.split}", exist_ok=True,
                        verbose=True)

    names = model.names
    per_class = {}
    for i, cls_idx in enumerate(metrics.box.ap_class_index):
        p, r, ap50, ap = metrics.box.class_result(i)
        per_class[names[int(cls_idx)]] = {
            "precision": round(float(p), 4), "recall": round(float(r), 4),
            "map50": round(float(ap50), 4), "map50_95": round(float(ap), 4),
        }

    overall = {
        "map50": round(float(metrics.box.map50), 4),
        "map50_95": round(float(metrics.box.map), 4),
        "precision": round(float(metrics.box.mp), 4),
        "recall": round(float(metrics.box.mr), 4),
    }

    sheep_map50 = per_class.get("sheep", {}).get("map50", 0.0)
    checks = [
        ("mAP50 (sheep)", sheep_map50, gate["map50_sheep"], sheep_map50 >= gate["map50_sheep"]),
        ("mAP50-95 (all)", overall["map50_95"], gate["map5095_all"], overall["map50_95"] >= gate["map5095_all"]),
    ]

    ts = time.strftime("%Y%m%d-%H%M%S")
    REPORTS.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": ts, "weights": args.weights, "split": args.split,
        "eval_settings": ev, "overall": overall, "per_class": per_class,
        "gate": {name: {"value": round(val, 4), "target": tgt, "pass": ok} for name, val, tgt, ok in checks},
        "pass": all(ok for *_, ok in checks),
    }
    out = REPORTS / f"detection_{ts}.json"
    out.write_text(json.dumps(report, indent=2))

    print("\n" + "=" * 60)
    print(f"{'metric':<22}{'value':>10}{'target':>10}   result")
    for name, val, tgt, ok in checks:
        print(f"{name:<22}{val:>10.4f}{tgt:>10.2f}   {'PASS' if ok else 'FAIL'}")
    print("=" * 60)
    print(f"report: {out.relative_to(REPO)}")
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
