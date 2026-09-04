# Models

Weights are **not** committed to git (`.gitignore`). The backend needs:

| file | what it is |
|---|---|
| `best.pt` | Ultralytics detection/segmentation checkpoint. Class names are read from the model — no livestock class is hard-coded. Ships as YOLOE-26s; replaced by a site-tuned checkpoint after the training phase (`training/README.md`). |
| `mobileclip2_b.ts` | Text encoder used by YOLOE open-vocabulary prompting. Only needed if the detector is switched to prompt mode; kept for completeness. |

## Getting the weights

```bash
export SMART_QORA_MODELS_URL=https://github.com/<owner>/<repo>/releases/download/models-v1
./scripts/fetch_models.sh          # or scripts\fetch_models.ps1 on Windows
```

If `MODEL_PATH` points at a missing file the backend starts normally but the
vision worker stays idle (`/api/status` → `ai: IDLE`).

## When a trained model is swapped in

Keep the previous file as `best.prev.pt` (rollback). Record here: the eval
report (`training/reports/`), the dataset hash, the Zenodo DOI + CC BY 4.0
citation, and the training commit. Then `POST /api/worker/restart` to load it.
