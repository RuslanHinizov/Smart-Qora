#!/usr/bin/env bash
# Download the model weights that are kept out of git (see .gitignore).
# Set SMART_QORA_MODELS_URL to the base URL of a release that hosts the files,
# e.g. https://github.com/<owner>/<repo>/releases/download/models-v1
set -euo pipefail

BASE_URL="${SMART_QORA_MODELS_URL:-}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/models"
FILES=(best.pt mobileclip2_b.ts)

if [[ -z "$BASE_URL" ]]; then
  echo "Set SMART_QORA_MODELS_URL to where the weights are hosted, then re-run." >&2
  echo "  export SMART_QORA_MODELS_URL=https://github.com/<owner>/<repo>/releases/download/models-v1" >&2
  exit 1
fi

mkdir -p "$DEST"
for f in "${FILES[@]}"; do
  if [[ -f "$DEST/$f" ]]; then
    echo "✓ $f already present"
    continue
  fi
  echo "↓ $f"
  curl -fL --retry 3 -o "$DEST/$f" "$BASE_URL/$f"
  if curl -fsL -o "$DEST/$f.sha256" "$BASE_URL/$f.sha256" 2>/dev/null; then
    (cd "$DEST" && sha256sum -c "$f.sha256") && echo "  checksum ok"
  fi
done
echo "Models ready in $DEST"
