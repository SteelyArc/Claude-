#!/usr/bin/env bash
# Encode rendered frames + soundtrack into the final TikTok MP4 (1080x1920, 30 fps, H.264 + AAC).
# Usage: ./assemble.sh <frames_dir> [out.mp4]
set -euo pipefail
FRAMES="$1"; OUT="${2:-$(dirname "$0")/SUN_tiktok_1080x1920.mp4}"
DUR=$(python3 -c "print(89*60/86)")
ffmpeg -loglevel error -y -framerate 30 -i "$FRAMES/f%05d.jpg" -i "$(dirname "$0")/music.wav" \
  -map 0:v -map 1:a -t "$DUR" \
  -c:v libx264 -preset slow -crf 16 -profile:v high -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 256k -ar 48000 -af "loudnorm=I=-14:TP=-1.5:LRA=9" \
  -movflags +faststart "$OUT"
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration -of compact "$OUT"
