#!/usr/bin/env bash
# DTwin — reproducible ingest→frames→COLMAP SfM pipeline for ANY captured video.
# Usage:  scripts/process_video.sh <source.mp4> <deploy> [fps]
#   <source.mp4>  absolute or relative path to the capture (originals stay sacred;
#                 this script ONLY READS it and writes under frames/ + train/)
#   <deploy>      deployment name, e.g. sample, mall, port, dam
#   [fps]         frame-extraction rate (default 2)
#
# Chains: ffprobe metadata → ffmpeg @fps → COLMAP auto SfM (feature extract+match
#   + mapper) → assemble train/<deploy>/ dataset (images_8 + sparse/0). The MLX
#   training step (references/local-3dgs-training-mlx.md) consumes that dataset.
#
# Requires: ffmpeg, ffprobe, colmap (brew install ffmpeg colmap).
# VERIFIED SHAPE: produced 83/83 registered frames + 70499-pt sparse model for the
# "sample" deployment from ~/Desktop/DJI/testdji.mp4 on this Mac.
set -euo pipefail

SRC="${1:?usage: process_video.sh <source.mp4> <deploy> [fps]}"
DEPLOY="${2:?usage: process_video.sh <source.mp4> <deploy> [fps]}"
FPS="${3:-2}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"   # repo root ~/DTwin
FRAME_DIR="$ROOT/frames/$DEPLOY"
TRAIN_DIR="$ROOT/train/$DEPLOY"
SFM_DIR="$FRAME_DIR/sfm"

echo "== DTwin pipeline: deploy=$DEPLOY  src=$SRC  fps=$FPS"
[ -f "$SRC" ] || { echo "ERROR: source not found: $SRC"; exit 1; }

# 0. ingest (sacred — copy original read-only, never write into ingest/)
mkdir -p "$ROOT/ingest/$DEPLOY"
cp -n "$SRC" "$ROOT/ingest/$DEPLOY/" && echo "ingest: copied original (read-only copy)"

# 1. metadata
echo "== ffprobe =="
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$SRC"

# 2. extract frames @ fps
mkdir -p "$FRAME_DIR"
echo "== ffmpeg: extracting frames @ ${FPS}fps =="
ffmpeg -y -i "$SRC" -vf "fps=$FPS" -q:v 2 "$FRAME_DIR/frame_%05d.jpg" -loglevel error
N=$(ls "$FRAME_DIR"/*.jpg | wc -l | tr -d ' ')
echo "frames: $N"

# 3. COLMAP auto SfM
echo "== COLMAP: feature extract =="
colmap feature_extractor \
  --database_path "$SFM_DIR/db.db" \
  --image_path "$FRAME_DIR" \
  --ImageReader.single_camera 1
echo "== COLMAP: exhaustive match =="
colmap exhaustive_matcher --database_path "$SFM_DIR/db.db"
mkdir -p "$SFM_DIR/sparse/0"
echo "== COLMAP: mapper =="
colmap mapper \
  --database_path "$SFM_DIR/db.db" \
  --image_path "$FRAME_DIR" \
  --output_path "$SFM_DIR/sparse"
REG=$(ls "$SFM_DIR/sparse/0"/*.bin 2>/dev/null | wc -l | tr -d ' ')
echo "sparse model files present: $REG (expect cameras/images/points3D = 3)"

# 4. assemble training dataset (frame names MUST match COLMAP records)
mkdir -p "$TRAIN_DIR/images_8" "$TRAIN_DIR/sparse/0"
cp "$FRAME_DIR"/frame_*.jpg "$TRAIN_DIR/images_8/"
cp "$SFM_DIR"/sparse/0/* "$TRAIN_DIR/sparse/0/"
echo "== dataset ready: $TRAIN_DIR (images_8 + sparse/0) =="
echo "Next: run the MLX training step (references/local-3dgs-training-mlx.md)."
echo "Remember: MLX venv/pip install is GATED — confirm with the user first."
