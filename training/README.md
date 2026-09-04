# Model training & counting-accuracy evaluation

The shipped `models/best.pt` (YOLOE-26s) is a general baseline. On top-down gate footage it
under-detects and confuses sheep ↔ goat ↔ cattle. This directory holds a reproducible
pipeline to fine-tune it on real gate video and prove the improvement in **counting**
terms, not just mAP.

> Status: outline. The scripts below are added in the model-training phase.

## Dataset

- **Zenodo sheep gate-crossing dataset** — record `12094356`
  (<https://zenodo.org/records/12094356>), CC BY 4.0. ~50 sheep through a gate, 4 clips,
  1440×1080, 9 fps, with YOLO + MOT labels. Attribution required — cite the DOI in
  `models/README.md` when a trained model ships.
- **Site footage** — sample frames from `videos/crop_23.11.23-*.MP4` at 2–3 fps, pre-label
  with the current `best.pt`, hand-correct in CVAT / Label Studio. Must include at least
  one **OUT-direction** clip (the sample set is 100% IN).

`datasets/**` is git-ignored except `data.yaml` + this README. Canonical class order:
`[sheep, cattle, goat, horse]` (matches `backend/app/vision/classes.py`).

## Pipeline (to be added)

| script | does |
|---|---|
| `prepare_dataset.py` | download + checksum + convert labels → `datasets/sheep-gate/{images,labels}/{train,val,test}` + `data.yaml` |
| `extract_frames.py` | sample + optionally auto-pre-label the site clips into a weighted `site` split |
| `train.py` | thin `YOLO(cfg.model).train(...)` wrapper driven by `config.yaml` (pinned: imgsz 1280, 100 epochs, patience 20, mosaic + close_mosaic, `device: 0`, `half: True`) → `runs/detect/trainN/weights/best.pt` |
| `eval.py` | `model.val(split="test")` → per-class mAP50 / mAP50-95 / P / R → `reports/detection_<ts>.json` |
| `counting_eval.py` | replays labelled clips through the **real** `LineCrossingCounter` + `CenterSmoother` from `backend/app/vision/`, compares emitted IN/OUT against `ground_truth/*.json` → `counting_error_pct`, per-direction MAE, ID-switch ratio |

## Acceptance gate (before swapping `best.pt`)

| metric | target |
|---|---|
| mAP50 (sheep) | ≥ 0.90 |
| mAP50-95 (all) | ≥ 0.60 |
| counting error % (net, per clip) | ≤ 5% |
| ID switches / true animal count | ≤ 1.5× |

Measure the shipped model first to record the baseline. If ID fragmentation dominates the
error, tune BoT-SORT (`track_buffer`, `match_thresh`, `new_track_thresh`) and/or add a
min-track-length gate in `counter.py` (config-flagged), then re-run `counting_eval.py`.

## Swap-in

```bash
cp runs/detect/trainN/weights/best.pt models/best.pt   # keep the old one as best.prev.pt
# update models/README.md with the eval report + dataset DOI + training commit
docker compose exec backend curl -s -XPOST localhost:8000/api/worker/restart -H "Authorization: Bearer $TOKEN"
```

No backend code change is needed unless the class list changed.
