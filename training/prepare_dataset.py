"""Build the YOLO fine-tuning dataset from the Zenodo sheep gate-crossing archive.

Zenodo record 12094356 ships 4 top-down drone clips (1440x1080, 9 fps) with a
YOLO label for *every* frame plus MOT tracking ground truth. This script:

  1. checksums datasets/_downloads/sheep_gate.zip
  2. unpacks the nested YOLO + MOT zips
  3. decodes each labelled frame straight out of the .MP4
  4. writes datasets/sheep-gate/{images,labels}/{train,val,test} + data.yaml
     (contiguous per-clip split so near-identical neighbouring frames do not
     leak across splits)
  5. writes training/ground_truth/<clip>.json from the MOT tracks, used by
     counting_eval.py as the reference IN/OUT tally

Run from the repo root:  python training/prepare_dataset.py
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

import cv2
import yaml

REPO = Path(__file__).resolve().parents[1]
ARCHIVE = REPO / "datasets" / "_downloads" / "sheep_gate.zip"
EXPECTED_MD5 = "1ec2048d4975f5d68e04c3229cb03d40"
OUT_ROOT = REPO / "datasets" / "sheep-gate"
GT_DIR = REPO / "training" / "ground_truth"
CLIPS = [8, 10, 12, 13]
CANONICAL = ["sheep", "cattle", "goat", "horse"]  # matches backend/app/vision/classes.py
SPLITS = ("train", "val", "test")

# obj.names label -> canonical class name (Zenodo annotates everything as "sheep")
NAME_TO_CANON = {"sheep": "sheep", "cow": "cattle", "cattle": "cattle", "goat": "goat", "horse": "horse"}


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frame_index(name: str) -> int:
    return int(re.search(r"(\d+)", Path(name).name).group(1))


def open_nested(outer: zipfile.ZipFile, folder: str, clip: int) -> zipfile.ZipFile:
    # archive naming is inconsistent (e.g. "YOLO.1.1_crop..." vs "YOLO1.1_crop..."),
    # so anchor on the folder and the "-<clip>.zip" suffix.
    suffix = f"crop_23.11.23-{clip}.zip"
    hits = [n for n in outer.namelist() if f"/{folder}/" in n and n.endswith(suffix)]
    if len(hits) != 1:
        raise RuntimeError(f"expected one {folder} zip for clip {clip}, got {hits}")
    return zipfile.ZipFile(io.BytesIO(outer.read(hits[0])))


def load_yolo_labels(outer: zipfile.ZipFile, clip: int) -> tuple[dict[int, str], list[str]]:
    """Return {frame_idx: label_text_remapped_to_canonical_ids} and the raw class names."""
    zz = open_nested(outer, "YOLO1.1", clip)
    names = [n for n in zz.namelist() if n.endswith("obj.names")]
    raw_names = zz.read(names[0]).decode().split() if names else ["sheep"]
    remap = {i: CANONICAL.index(NAME_TO_CANON[n.strip().lower()]) for i, n in enumerate(raw_names)}

    labels: dict[int, str] = {}
    for entry in zz.namelist():
        if not (entry.startswith("obj_train_data/") and entry.endswith(".txt")):
            continue
        lines = []
        for line in zz.read(entry).decode().splitlines():
            parts = line.split()
            if len(parts) != 5:
                continue
            cls = remap[int(parts[0])]
            lines.append(" ".join([str(cls), *parts[1:]]))
        labels[frame_index(entry)] = "\n".join(lines)
    return labels, raw_names


def load_mot_tracks(outer: zipfile.ZipFile, clip: int) -> dict[int, list[list[float]]]:
    """Return {track_id: [[frame, cx, cy], ...]} sorted by frame, from MOT gt.txt."""
    zz = open_nested(outer, "MOT1.1", clip)
    gt = [n for n in zz.namelist() if n.endswith("gt.txt")][0]
    tracks: dict[int, list[list[float]]] = {}
    for line in zz.read(gt).decode().splitlines():
        f = line.split(",")
        if len(f) < 6:
            continue
        frame, tid, x, y, w, h = (float(v) for v in f[:6])
        tracks.setdefault(int(tid), []).append(
            [int(frame), round(x + w / 2.0, 1), round(y + h / 2.0, 1)])
    for pts in tracks.values():
        pts.sort(key=lambda p: p[0])
    return tracks


def resolve_video(outer: zipfile.ZipFile, clip: int, tmp: Path) -> Path:
    local = REPO / "videos" / f"crop_23.11.23-{clip}.MP4"
    if local.is_file():
        return local
    hits = [n for n in outer.namelist() if n.endswith(f"crop_23.11.23-{clip}.MP4")]
    if not hits:
        raise RuntimeError(f"clip {clip}: no video in videos/ or in the archive")
    dest = tmp / f"crop_23.11.23-{clip}.MP4"
    dest.write_bytes(outer.read(hits[0]))
    return dest


def split_of(idx: int, total: int, ratios: dict[str, float]) -> str:
    train_end = round(total * ratios["train"])
    val_end = train_end + round(total * ratios["val"])
    return "train" if idx < train_end else ("val" if idx < val_end else "test")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="overwrite an existing datasets/sheep-gate")
    ap.add_argument("--jpeg-quality", type=int, default=92)
    args = ap.parse_args()

    cfg = yaml.safe_load((REPO / "training" / "config.yaml").read_text())
    ratios = cfg["split"]
    assert abs(sum(ratios.values()) - 1.0) < 1e-6, "split ratios must sum to 1.0"

    if not ARCHIVE.is_file():
        print(f"missing {ARCHIVE.relative_to(REPO)} - download it from "
              "https://zenodo.org/records/12094356 first", file=sys.stderr)
        return 1
    print(f"checksum {ARCHIVE.name} ...", end=" ", flush=True)
    got = md5(ARCHIVE)
    if got != EXPECTED_MD5:
        print(f"FAIL\n  expected {EXPECTED_MD5}\n  got      {got}", file=sys.stderr)
        return 1
    print("ok")

    if OUT_ROOT.exists():
        if not args.force:
            print(f"{OUT_ROOT.relative_to(REPO)} exists - pass --force to rebuild", file=sys.stderr)
            return 1
        shutil.rmtree(OUT_ROOT)
    for split in SPLITS:
        (OUT_ROOT / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUT_ROOT / "labels" / split).mkdir(parents=True, exist_ok=True)
    GT_DIR.mkdir(parents=True, exist_ok=True)

    tmp = OUT_ROOT / "_tmp_video"
    tmp.mkdir(exist_ok=True)
    counts = {s: 0 for s in SPLITS}
    per_clip_summary = []

    with zipfile.ZipFile(ARCHIVE) as outer:
        for clip in CLIPS:
            labels, raw_names = load_yolo_labels(outer, clip)
            tracks = load_mot_tracks(outer, clip)
            video = resolve_video(outer, clip, tmp)
            cap = cv2.VideoCapture(str(video))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 9.0

            ordered = sorted(labels)
            wanted = {fidx: split_of(pos, len(ordered), ratios) for pos, fidx in enumerate(ordered)}
            stem = f"clip{clip:02d}"
            clip_counts = {s: 0 for s in SPLITS}
            # sequential decode (every labelled frame is contiguous) - far faster
            # and more reliable than per-frame CAP_PROP_POS_FRAMES seeking.
            fidx = -1
            while wanted:
                ok, frame = cap.read()
                if not ok:
                    print(f"  clip {clip}: stream ended, {len(wanted)} frames unread", file=sys.stderr)
                    break
                fidx += 1
                split = wanted.pop(fidx, None)
                if split is None:
                    continue
                name = f"{stem}_frame{fidx:06d}"
                cv2.imwrite(str(OUT_ROOT / "images" / split / f"{name}.jpg"), frame,
                            [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])
                (OUT_ROOT / "labels" / split / f"{name}.txt").write_text(labels[fidx] + "\n")
                counts[split] += 1
                clip_counts[split] += 1
            cap.release()

            # horizontal reference line across the middle of the frame; direction
            # cancels out in counting_eval (GT and prediction use the same line).
            line = [[0, height // 2], [width, height // 2]]
            video_ref = video.relative_to(REPO).as_posix() if video.is_relative_to(REPO) else str(video)
            (GT_DIR / f"{stem}.json").write_text(json.dumps({
                "clip": clip,
                "video": video_ref,
                "width": width, "height": height, "fps": round(fps, 3),
                "labelled_frames": len(ordered),
                "line": line, "inside_direction": "DOWN",
                "tracks": {str(tid): pts for tid, pts in sorted(tracks.items())},
            }, separators=(",", ":")))
            per_clip_summary.append((clip, len(ordered), len(tracks), raw_names, clip_counts))

    shutil.rmtree(tmp, ignore_errors=True)

    data_yaml = OUT_ROOT / "data.yaml"
    data_yaml.write_text(yaml.safe_dump({
        "path": OUT_ROOT.relative_to(REPO).as_posix(),
        "train": "images/train", "val": "images/val", "test": "images/test",
        "names": {i: n for i, n in enumerate(CANONICAL)},
    }, sort_keys=False))

    print("\nper-clip:")
    for clip, nframes, ntracks, raw_names, cc in per_clip_summary:
        print(f"  clip {clip:2d}: {nframes:3d} frames  {ntracks:3d} MOT tracks  "
              f"classes={raw_names}  split={dict(cc)}")
    print(f"\ntotal images: train={counts['train']}  val={counts['val']}  test={counts['test']}")
    print(f"wrote {data_yaml.relative_to(REPO)}")
    print(f"wrote {len(CLIPS)} ground-truth files under {GT_DIR.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
