"""Download the CC BY 4.0 AUTH-Sheep aerial-video dataset with checksums.

The data is intentionally kept out of Git.  It contains four frame-annotated
UAV videos of sheep, goats and horses, plus stable track identifiers.  This is
the closest public source to Smart Qora's top-down gate camera footage.

Run from the repository root:

    python training/download_auth_sheep.py

It is safe to run again after an interrupted download: completed files whose
MD5 matches the Zenodo record are skipped.  Files are stored under
``datasets/_downloads/auth-sheep`` and are ignored by Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
DESTINATION = REPO / "datasets" / "_downloads" / "auth-sheep"
RECORD_API = "https://zenodo.org/api/records/13843376"


def checksum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_record() -> dict:
    with urllib.request.urlopen(RECORD_API, timeout=60) as response:
        return json.load(response)


def download(url: str, target: Path, expected_md5: str, expected_size: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size == expected_size and checksum(target) == expected_md5:
        print(f"ok  {target.name}")
        return

    partial = target.with_suffix(target.suffix + ".part")
    print(f"get {target.name}", flush=True)
    for attempt in range(1, 9):
        try:
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                # Servers may ignore Range.  In that case restart rather than append a
                # full file to the previous partial content.
                append = offset > 0 and response.status == 206
                if not append and partial.exists():
                    partial.unlink()
                mode = "ab" if append else "wb"
                with partial.open(mode) as stream:
                    while chunk := response.read(1024 * 1024):
                        stream.write(chunk)
            size = partial.stat().st_size
            if size != expected_size:
                print(f"  {size / 1_000_000:.1f}/{expected_size / 1_000_000:.1f} MB; resuming", flush=True)
                time.sleep(2)
                continue
            actual = checksum(partial)
            if actual != expected_md5:
                # A same-size corrupt response cannot be resumed safely.
                partial.unlink(missing_ok=True)
                raise RuntimeError(f"checksum failed for {target.name}: {actual} != {expected_md5}")
            partial.replace(target)
            print(f"ok  {target.name}")
            return
        except urllib.error.URLError as exc:
            if attempt == 8:
                raise
            wait = attempt * 10
            print(f"  source error ({exc}); retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"download exhausted retries for {target.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true", help="show the remote files without downloading")
    parser.add_argument("--video", choices=("1", "2", "3", "4"), action="append",
                        help="download only a selected video; repeat the option as needed")
    args = parser.parse_args()

    record = fetch_record()
    wanted = set(args.video or ("1", "2", "3", "4"))
    files = {item["key"]: item for item in record["files"]}
    selected: list[str] = []
    for number in sorted(wanted):
        selected.extend([f"video{number}.mp4", f"video{number}_annotations_hbb.json"])

    print("AUTH-Sheep — Zenodo 13843376 — CC BY 4.0")
    for name in selected:
        item = files[name]
        print(f"  {name}: {item['size'] / 1_000_000:.1f} MB")
    if args.metadata_only:
        return 0

    for name in selected:
        item = files[name]
        # The API-content endpoint occasionally returns 504 for large files;
        # Zenodo's public download endpoint is the stable resumable endpoint.
        public_url = (
            "https://zenodo.org/records/13843376/files/"
            f"{urllib.parse.quote(name)}?download=1"
        )
        download(
            public_url,
            DESTINATION / name,
            item["checksum"].removeprefix("md5:"),
            item["size"],
        )
    print(f"ready: {DESTINATION.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        print(f"download failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
