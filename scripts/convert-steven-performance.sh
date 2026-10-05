#!/usr/bin/env bash
set -euo pipefail

RVC_DIR="\${RVC_DIR:-$HOME/evez-rvc}"
MODEL="\${EVEZ_RVC_MODEL:-$RVC_DIR/assets/weights/steven-singing-v1.pth}"
INPUT="\${1:?usage: $0 INPUT_AUDIO OUTPUT_AUDIO}"
OUTPUT="\${2:?usage: $0 INPUT_AUDIO OUTPUT_AUDIO}"
PITCH="\${EVEZ_PITCH_SHIFT:-0}"
INDEX_RATE="\${EVEZ_INDEX_RATE:-0.75}"
PROTECT="\${EVEZ_PROTECT:-0.20}"

cd "$RVC_DIR"
test -f "$MODEL" || { echo "Missing RVC model: $MODEL"; exit 1; }
test -f "$INPUT" || { echo "Missing input: $INPUT"; exit 1; }

python3 infer/cli.py \
  --model "$MODEL" \
  --input "$INPUT" \
  --output "$OUTPUT" \
  --pitch "$PITCH" \
  --f0-method rmvpe \
  --index-rate "$INDEX_RATE" \
  --protect "$PROTECT" \
  --format wav \
  --overwrite

echo "Converted: $OUTPUT"
