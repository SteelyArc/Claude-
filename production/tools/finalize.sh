#!/bin/bash
# Wait for archive downloads, render the full film, mux narration + score, run technical QC.
cd "$(dirname "$0")/.."
while pgrep -f "fetch_from_candidates.py assets/archive" >/dev/null; do sleep 30; done
echo "downloads finished $(date)"; ls assets/archive
python3 tools/film.py render 4 2>&1 | grep -vE "Fontconfig"
OUT=previews/final/Partitions_of_Poland-Lithuania_1793-1795_vertical.mp4
python3 tools/music_mix.py mux previews/final/chunks/video.mp4 audio/narration_original.mp3 audio/music/original_score.wav "$OUT" --full 419.5 --music-offset 0
ffprobe -v error -show_entries format=duration,size,bit_rate:stream=codec_name,profile,width,height,r_frame_rate,pix_fmt,sample_rate,channels -of compact "$OUT"
echo "FINALIZE DONE $(date)"
