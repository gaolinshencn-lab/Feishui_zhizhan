#!/bin/bash
# A single-file copy of the documentary small enough for capped uploads (under 400 MiB): two-pass x265 at
# 1.4 Mbps, AAC 128k, the same CC track.
#   ./doc_compact.sh [in.mp4] [out.mp4]
set -e
cd "${DOC_DIR:-$(dirname "$0")}"
IN=${1:-feishui-documentary.mp4}
OUT=${2:-feishui-documentary-hevc.mp4}
X="log-level=error:aq-mode=3:keyint=240:min-keyint=24"
ffmpeg -v error -stats -y -i "$IN" -map 0:v -c:v libx265 -preset medium -b:v 1400k -x265-params "$X:pass=1:stats=hevc2pass.log:no-slow-firstpass=1" -an -f null /dev/null
ffmpeg -v error -stats -y -i "$IN" -map 0:v -map 0:a -map 0:s -c:v libx265 -preset medium -b:v 1400k -x265-params "$X:pass=2:stats=hevc2pass.log" -tag:v hvc1 \
  -c:a aac -b:a 128k -c:s mov_text -metadata:s:a:0 language=chi -metadata:s:s:0 language=chi -disposition:s:0 default \
  -metadata "title=淝水之战 · 三维沙盘纪录片" -metadata "comment=解说为AI合成语音" -movflags +faststart ".$OUT"
mv ".$OUT" "$OUT"
rm -f hevc2pass.log hevc2pass.log.cutree
