# Models

| file | committed? | what it is |
|---|---|---|
| `best.pt` | **yes** (~22 MB) | The detection checkpoint the backend loads. A **YOLOv8s fine-tune** on the Zenodo sheep gate-crossing set (details below). Bundled so the repo runs straight after `git clone`. |
| `best.prev.pt` | no (`.gitignore`) | Previous `best.pt` (YOLOE-26s baseline). Local rollback copy. |
| `yolov8s.pt` | no | Fine-tune base weights. Ultralytics fetches it automatically when you run `training/`. |
| `mobileclip2_b.ts` | no | Text encoder for YOLOE open-vocabulary prompting. Not used by the shipped model. |

Class names are read from the model — no livestock class is hard-coded. If `MODEL_PATH`
points at a missing file the backend still starts, but the vision worker stays idle
(`/api/status` → `ai: IDLE`).

## Alternative / larger weights

`scripts/fetch_models.sh` (or `scripts\fetch_models.ps1`) pulls extra weights from a
release if you want to swap them in:

```bash
export SMART_QORA_MODELS_URL=https://github.com/RuslanHinizov/Smart-Qora/releases/download/models-v1
./scripts/fetch_models.sh
```

## Current `best.pt` — YOLOv8s sheep-gate fine-tune

- **Base:** `yolov8s.pt` (COCO), detection head re-mapped to `[sheep, cattle, goat, horse]`.
- **Data:** Zenodo record `12094356` (DOI `10.5281/zenodo.12094356`, CC BY 4.0) —
  639 top-down drone frames, ~14 k sheep boxes, 70/15/15 contiguous per-clip split.
  Cite: Helary, L., Okoye, K. N., Kolodziejczyk, M., Schewe, J., Philip, L.,
  Nicolas, E., & Lebreton, A. (2024). *Drone videos and their annotations of
  passing sheep (for counting purpose)* [Data set]. Zenodo.
- **Recipe:** `training/config.yaml` (freeze 10, imgsz 1024, batch 16, AdamW auto-lr,
  early-stopped at epoch 22 of a 60-epoch budget). Rebuild with
  `python training/prepare_dataset.py && python training/train.py`.
- **Pipeline commit:** `7971885` (add `training/`); early-stopped at epoch 22.

### Acceptance gate — all pass (`training/reports/`)

| metric | target | this model | shipped baseline (YOLOE-26s) |
|---|---|---|---|
| mAP50 (sheep), test split | ≥ 0.90 | **0.980** | — |
| mAP50-95 (all), test split | ≥ 0.60 | **0.726** | — |
| counting error % (4 clips, net) | ≤ 5% | **0.0%** (158/158) | 29.75% (111/158) |
| ID-switch ratio | ≤ 1.5× | **1.14×** | 2.23× |

> The counting numbers come from replaying the dataset's own clips, which also fed
> training, through the real `LineCrossingCounter`; they show the detector+tracker
> now reproduce the ground-truth crossings on this footage, not an unseen-site
> guarantee. The Zenodo set is one location and 100% IN — collect site footage
> (`training/extract_frames.py`), including an OUT clip, before a production claim.
> Only `sheep` was trained; `cattle`/`goat`/`horse` stay at the base model's level.

## Swapping in a new model

1. `cp models/best.pt models/best.prev.pt`
2. `cp runs/sheep-gate/weights/best.pt models/best.pt`
3. Update the table above with the new `training/reports/` numbers + training commit.
4. `POST /api/worker/restart` (or `docker compose restart backend`) to load it.
5. Publish the weights via the models release (`docs/RELEASE.md`) — `*.pt` is git-ignored.
