#!/usr/bin/env bash
set -euo pipefail

GUIDE="\${1:?usage: $0 GUIDE_AUDIO OUTPUT_AUDIO [PRESET]}"
OUTPUT="\${2:?usage: $0 GUIDE_AUDIO OUTPUT_AUDIO [PRESET]}"
PRESET="\${3:-vocaloid}"

RVC_CONVERT="\${EVEZ_RVC_CONVERTER:-$HOME/evez-machine-voice/scripts/convert-steven-performance.sh}"
WORK="\${EVEZ_AUDIO_WORK:-$HOME/evez-hermes-work}"

mkdir -p "$WORK"
TIMBRE="$WORK/steven-timbre.wav"

"$RVC_CONVERT" "$GUIDE" "$TIMBRE"

case "$PRESET" in
  beatbox)
    FILTER='highpass=f=55,acompressor=threshold=-18dB:ratio=3:attack=4:release=90,asoftclip=type=tanh'
    ;;
  rap)
    FILTER='highpass=f=65,equalizer=f=250:t=q:w=1:g=-2,equalizer=f=3500:t=q:w=1.2:g=3,acompressor=threshold=-16dB:ratio=3:attack=5:release=70,asoftclip=type=tanh'
    ;;
  rasp)
    FILTER='highpass=f=70,equalizer=f=800:t=q:w=1:g=3,equalizer=f=3200:t=q:w=1.2:g=2,asoftclip=type=tanh,acompressor=threshold=-20dB:ratio=4:attack=6:release=110'
    ;;
  sustain)
    FILTER='highpass=f=65,equalizer=f=180:t=q:w=1:g=1,acompressor=threshold=-20dB:ratio=2.2:attack=18:release=150'
    ;;
  *)
    FILTER='highpass=f=65,acompressor=threshold=-18dB:ratio=2.5:attack=8:release=100'
    ;;
esac

ffmpeg -y -i "$TIMBRE" \
  -af "$FILTER,loudnorm=I=-15:TP=-1.5:LRA=11" \
  -ar 48000 -ac 2 "$OUTPUT"

echo "Hermes performance rendered: $OUTPUT"
