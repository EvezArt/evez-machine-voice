#!/usr/bin/env bash
set -euo pipefail

RVC_DIR="\${RVC_DIR:-$HOME/evez-rvc}"
DATASET="\${EVEZ_VOICE_DATASET:-$HOME/evez-voice-dataset}"
EXPERIMENT="\${EVEZ_RVC_EXPERIMENT:-steven-singing-v1}"
GPU="\${RVC_GPU:-0}"
WORKERS="\${RVC_WORKERS:-4}"

echo "[1/7] Clone/update RVC"
if [[ ! -d "$RVC_DIR/.git" ]]; then
  git clone https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git "$RVC_DIR"
else
  git -C "$RVC_DIR" pull --ff-only
fi

cd "$RVC_DIR"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

hf download lj1995/VoiceConversionWebUI --revision main \
  --include "hubert_base/*" --local-dir assets
hf download lj1995/VoiceConversionWebUI rmvpe.pt --revision main \
  --local-dir assets/rmvpe
hf download lj1995/VoiceConversionWebUI --revision main \
  --include "pretrained_v2/*" --local-dir assets

test -d "$DATASET" || { echo "Missing dataset: $DATASET"; exit 1; }

python3 train/preprocess.py "$DATASET" 40000 "$WORKERS" "$EXPERIMENT" false 3.7
python3 train/dataset/extract_f0.py cpu "logs/$EXPERIMENT" "$WORKERS" rmvpe
python3 train/extract_feature_print.py cpu 0 0 "logs/$EXPERIMENT" v2 true

python3 train/train.py \
  -e "$EXPERIMENT" \
  -sr 40k \
  -f0 1 \
  -bs 4 \
  -g "$GPU" \
  -te 600 \
  -se 50 \
  -pg assets/pretrained_v2/f0G40k.pth \
  -pd assets/pretrained_v2/f0D40k.pth \
  -l 0 \
  -c 0 \
  -sw 1 \
  -v v2

echo
echo "Training complete."
echo "Build the retrieval index:"
echo "python3 train/train_index.py $EXPERIMENT v2 assets/indices $WORKERS single"
echo "Keep the .pth and .index files private."
