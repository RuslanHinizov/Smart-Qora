"""Fine-tune a YOLO detector on the sheep-gate dataset.

Thin wrapper around Ultralytics driven by training/config.yaml so a run is
reproducible. Everything under the `eval:` / `gate:` / `split:` keys is ignored
here; the rest is forwarded straight to `YOLO(...).train(**kwargs)`.

    python training/prepare_dataset.py      # once
    python training/train.py                # -> runs/sheep-gate*/weights/best.pt
    python training/train.py --epochs 5     # quick pipeline smoke test
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from ultralytics import YOLO

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / "training" / "config.yaml"
NON_TRAIN_KEYS = {"eval", "gate", "split"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--epochs", type=int, help="override config.yaml epochs (for a smoke run)")
    ap.add_argument("--model", help="override the base weights")
    ap.add_argument("--device", help="override device, e.g. cpu or 0")
    args = ap.parse_args()

    cfg = {k: v for k, v in yaml.safe_load(CONFIG.read_text()).items() if k not in NON_TRAIN_KEYS}
    if args.epochs is not None:
        cfg["epochs"] = args.epochs
    if args.model:
        cfg["model"] = args.model
    if args.device is not None:
        cfg["device"] = args.device

    base = cfg.pop("model")
    data = cfg.pop("data")
    data_path = (REPO / data)
    if not data_path.is_file():
        raise SystemExit(f"{data} not found - run training/prepare_dataset.py first")

    # Force outputs under the repo. Ultralytics resolves a relative `project`
    # against its global settings `runs_dir`, which may point elsewhere.
    project = Path(cfg.get("project", "runs"))
    cfg["project"] = str(project if project.is_absolute() else REPO / project)

    print(f"base weights : {base}")
    print(f"dataset      : {data}")
    print(f"key params   : imgsz={cfg.get('imgsz')} epochs={cfg.get('epochs')} "
          f"batch={cfg.get('batch')} freeze={cfg.get('freeze')} lr0={cfg.get('lr0')}")

    model = YOLO(base)
    results = model.train(data=str(data_path), **cfg)

    save_dir = Path(results.save_dir)
    best = save_dir / "weights" / "best.pt"
    print(f"\ntrained weights: {best}")
    print("next: python training/eval.py --weights", best)
    print("      python training/counting_eval.py --weights", best)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
