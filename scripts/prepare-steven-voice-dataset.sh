#!/usr/bin/env bash
set -euo pipefail

INPUT="\${1:?usage: $0 INPUT_DIR OUTPUT_DIR}"
OUTPUT="\${2:?usage: $0 INPUT_DIR OUTPUT_DIR}"
TARGET_SR="\${EVEZ_VOICE_SR:-40000}"

mkdir -p "$OUTPUT"

find "$INPUT" -type f \
  \( -iname '*.wav' -o -iname '*.flac' -o -iname '*.mp3' -o -iname '*.m4a' \) \
  -print0 |
while IFS= read -r -d '' src; do
  base="$(basename "\${src%.*}")"
  dst="$OUTPUT/\${base}.wav"

  ffmpeg -hide_banner -loglevel error -y \
    -i "$src" \
    -ac 1 \
    -ar "$TARGET_SR" \
    -sample_fmt s16 \
    -af "highpass=f=55,lowpass=f=18000,loudnorm=I=-18:TP=-2:LRA=9" \
    "$dst"

  echo "prepared: $dst"
done

echo
echo "Dataset ready at: $OUTPUT"
echo "Use only recordings of the consenting voice owner."
echo "Keep this directory outside Git."
