#!/bin/sh
cd /home/user/Claude-/partition1772/work
mkdir -p ../render
awk '{printf "file '\''seg/%s_%05.2f.mp4'\''\n",$1,$2}' jobs.txt > concat.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i concat.txt -c copy video_only.mp4
ffmpeg -loglevel error -y -i video_only.mp4 -i preview_audio.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart ../render/partition1772_preview_1080x1920.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,duration -of compact ../render/partition1772_preview_1080x1920.mp4
