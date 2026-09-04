# Model training & counting-accuracy evaluation

`models/best.pt` ships as a YOLOv8s **sheep-gate fine-tune** (this pipeline's output). It
replaced a general YOLOE-26s baseline that under-detected and confused sheep ↔ goat ↔ cattle
on top-down gate footage. This directory is the reproducible pipeline that produced it —
and how you retrain on your own gate video, proving the gain in **counting** terms, not
just mAP.

```bash
pip install -r training/requirements.txt          # + a CUDA torch build for GPU

# 1. dataset  (needs datasets/_downloads/sheep_gate.zip from Zenodo 12094356)
python training/prepare_dataset.py

# 2. baseline — measure the shipped model before changing anything
python training/eval.py           --weights models/best.pt
python training/counting_eval.py  --weights models/best.pt

# 3. fine-tune
python training/train.py                                   # full run
python training/train.py --epochs 5 --device cpu           # pipeline smoke test

# 4. score the candidate against the acceptance gate
python training/eval.py           --weights runs/sheep-gate/weights/best.pt
python training/counting_eval.py  --weights runs/sheep-gate/weights/best.pt --baseline models/best.pt
```

Config (base weights, hyper-parameters, eval settings, gate thresholds, split ratios) lives
in [`config.yaml`](config.yaml).

## Dataset

- **Zenodo sheep gate-crossing dataset** — record `12094356`
  (<https://zenodo.org/records/12094356>), CC BY 4.0. Download
  `Sheep_video_annotations_datasets.zip` to `datasets/_downloads/sheep_gate.zip`
  (md5 `1ec2048d4975f5d68e04c3229cb03d40`). 4 top-down drone clips, 1440×1080, 9 fps,
  **every frame** YOLO-labelled (639 frames, ~14 k sheep boxes) plus MOT tracks.
  `prepare_dataset.py` decodes the labelled frames out of the `.MP4`s and writes a
  70/15/15 contiguous per-clip split. Attribution required — cite the DOI in
  `models/README.md` and `NOTICE` when a trained model ships.
- **Site footage** — the 4 sample clips in `videos/` *are* this Zenodo set. For a real
  deployment use `extract_frames.py` on footage from the actual gate, pre-label with the
  current model, hand-correct in CVAT / Label Studio, and fold into
  `datasets/sheep-gate/{images,labels}/train`. Must include at least one
  **OUT-direction** clip — the Zenodo set is 100% IN.

`datasets/` is git-ignored apart from `data.yaml` and small text (`_downloads/`, `images/`,
`labels/` never committed). Canonical class order: `[sheep, cattle, goat, horse]` (matches
`backend/app/vision/classes.py`). The Zenodo labels are sheep-only, so a fine-tune from this
set alone sharpens **sheep** and leaves cattle/goat/horse at the base model's level — add
per-species data before relying on them. `eval.py` averages mAP only over classes with test
instances, so the gate below is effectively a sheep gate.

## Pipeline

| script | does |
|---|---|
| `prepare_dataset.py` | checksum the Zenodo zip, unpack the nested YOLO + MOT zips, decode every labelled frame from the `.MP4`, write `datasets/sheep-gate/{images,labels}/{train,val,test}` + `data.yaml` (70/15/15 contiguous per-clip split) + `ground_truth/<clip>.json` |
| `extract_frames.py` | thin a *new* site recording to a labelling-friendly frame rate, optionally pre-label with a model, into `datasets/_staging/<name>` |
| `train.py` | thin `YOLO(cfg.model).train(...)` wrapper driven by `config.yaml` (imgsz 1280, freeze 10, low LR, mosaic + close_mosaic, `device: 0`, `half: True`) → `runs/sheep-gate*/weights/best.pt` |
| `eval.py` | `model.val(split="test")` → per-class mAP50 / mAP50-95 / P / R → `reports/detection_<ts>.json`, exits non-zero if the mAP gate is missed |
| `counting_eval.py` | replays labelled clips through the **real** `LineCrossingCounter` + `CenterSmoother` from `backend/app/vision/`, compares emitted IN/OUT against `ground_truth/*.json` → `counting_error_pct`, per-direction MAE, ID-switch ratio; `--baseline` scores a second model alongside |

## Acceptance gate (before swapping `best.pt`)

| metric | target |
|---|---|
| mAP50 (sheep) | ≥ 0.90 |
| mAP50-95 (all) | ≥ 0.60 |
| counting error % (net, per clip) | ≤ 5% |
| ID switches / true animal count | ≤ 1.5× |

Measure the shipped model first to record the baseline.

### If ID fragmentation dominates the error

The `LineCrossingCounter` already absorbs a lot of it (per-track state + cooldown +
`crossing_sequence` dedup) — on the ICAERUS clips a ~7× ID-fragmentation ratio still
lands the count within ~±5%. Levers, in order of payoff:

1. **Fine-tune on the real footage** — the biggest one. Domain gap (resolution, fps,
   flock density) is what fragments tracks in the first place.
2. `COUNT_MIN_TRACK_UPDATES` (env, default 3) — a crossing is ignored until the track
   has that many detections, so a 2-3 frame blob at the line is not counted. A gated
   crossing re-fires once the track matures.
3. `COUNT_ENTRY_ZONE="x1,y1,x2,y2"` (env) — only count tracks whose centre was inside
   this box at some point. Filters edge-of-frame flicker.
4. `TRACKER=botsort_reid.yaml` — appearance ReID; needs a real ReID model
   (`model:` → osnet path) to actually help, `model: auto` did not on the test clips.
5. Tune `track_buffer` / `match_thresh` / `new_track_thresh` in a custom tracker yaml.

`python scripts/count_video.py <clip> --line x1,y1,x2,y2 --inside UP` runs the exact
pipeline offline for quick before/after checks.

## Adding a species (cattle, goat, horse, camel, …)

Nothing is sheep-specific — class names are read from the model and `animal_type` is a
free string end to end. To add e.g. camel:

1. `backend/app/vision/classes.py` — add `"camel"` to `CANONICAL` and to `SYNONYMS`
   (`"camel": "camel", "deve": "camel", "dromedary": "camel"`).
2. Train with the species in `names:` (`prepare_dataset.py` → `train.py`), using clips
   that contain it. Camel has no COCO base class, so it needs its own labelled data;
   cattle/goat/horse can start from the COCO-pretrained `yolov8s.pt` head.
3. Frontend: add `"camel"` to `ANIMALS` in `pages/Events.tsx`, `camel: t.animalCamel`
   in `lib/format.ts`, and an `animalCamel` key in all four languages of
   `i18n/translations.ts`. An unmapped species already falls back to its raw name.

Per the per-site model, each customer's box can carry its own `best.pt` fine-tuned on
that site's animals — no code change to swap it in unless the class list grew.

## Swap-in

```bash
cp models/best.pt models/best.prev.pt
cp runs/sheep-gate/weights/best.pt models/best.pt
# update models/README.md + NOTICE with the eval report + dataset DOI + training commit
docker compose exec backend curl -s -XPOST localhost:8000/api/worker/restart \
  -H "Authorization: Bearer $TOKEN"
```

No backend code change is needed unless the class list changed. `models/*.pt` is
git-ignored — publish the new weights via the models release (see
`scripts/fetch_models.sh` and `docs/RELEASE.md`).
