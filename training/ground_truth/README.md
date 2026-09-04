# Counting ground truth

One JSON per clip, written by [`../prepare_dataset.py`](../prepare_dataset.py) from
the Zenodo MOT tracking labels and read by
[`../counting_eval.py`](../counting_eval.py).

## Schema

```jsonc
{
  "clip": 10,                       // Zenodo mission number
  "video": "videos/crop_23.11.23-10.MP4",
  "width": 1440,
  "height": 1080,
  "fps": 9.0,
  "labelled_frames": 297,
  "line": [[0, 540], [1440, 540]],  // counting line, source-image pixels
  "inside_direction": "DOWN",       // UP | DOWN | LEFT | RIGHT
  "tracks": {                       // MOT ground-truth trajectories
    "1": [[0, 608.5, 781.9], [1, 610.2, 770.4], ...],   // [frame, cx, cy]
    "2": [...]
  }
}
```

`cx, cy` are bbox centres (`x + w/2`, `y + h/2`), matching the centre the backend
worker feeds into `CenterSmoother`.

## How the reference tally is derived

`counting_eval.py` does **not** trust a hand-written IN/OUT number. It streams the
`tracks` above through the *same* `LineCrossingCounter` + `CenterSmoother` the
production worker uses, with a simulated clock (`frame / fps`), and whatever that
emits is the ground truth. The prediction pass runs the model through the real
`LivestockDetector.track()` over the video and streams its boxes through the same
counter. Because both passes share `line` + `inside_direction` + the clock, the
line geometry cancels and the delta is purely detection + tracking error.

Consequence: `line` only has to be a sane cut across the gate corridor. The mid
-frame horizontal line the preparer writes is fine for these top-down clips; edit
it here if a clip's gate runs vertically.

## Adding a hand-labelled clip

1. Label the clip in MOT format (frame, id, x, y, w, h, ...), or export tracks
   from CVAT.
2. Write a JSON file here following the schema (`tracks` keyed by string id,
   points sorted by frame).
3. Drop the matching video under `videos/` and point `video` at it.
4. `python training/counting_eval.py --weights <model>` picks it up automatically.
