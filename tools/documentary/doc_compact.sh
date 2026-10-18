#!/bin/bash
# One playable file small enough for capped uploads (under 400 MiB): two-pass x264 (slow) at 1.4 Mbps,
# AAC 128k, the same CC track. H.264 plays everywhere, Windows' own player and every browser included.
#   ./doc_compact.sh [in.mp4] [out.mp4]
set -e
cd "${DOC_DIR:-$(dirname "$0")}"
IN=${1:-feishui-documentary.mp4}
OUT=${2:-feishui-documentary-1080p.mp4}
LOG=x264pass-$$  # named per run, so two runs never share their statistics
ffmpeg -v error -stats -y -i "$IN" -map 0:v -c:v libx264 -preset slow -b:v 1400k -pass 1 -passlogfile $LOG -an -f null /dev/null
ffmpeg -v error -stats -y -i "$IN" -map 0:v -map 0:a -map 0:s -c:v libx264 -preset slow -b:v 1400k -pass 2 -passlogfile $LOG \
  -profile:v high -level 4.1 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -c:s mov_text -metadata:s:v:0 language=chi -metadata:s:a:0 language=chi -metadata:s:s:0 language=chi -disposition:s:0 default \
  -metadata "title=淝水之战 · 三维沙盘纪录片" -metadata "comment=解说为AI合成语音" -movflags +faststart ".$OUT"
mv ".$OUT" "$OUT"
rm -f $LOG-0.log $LOG-0.log.mbtree
