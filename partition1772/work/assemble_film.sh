#!/bin/sh
cd /home/user/Claude-/partition1772/work
awk '{printf "file '\''%s'\''\n",$3}' film_jobs.txt > film_concat.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i film_concat.txt -c copy film_video.mp4
# master (visually lossless) and upload version (high bitrate, TikTok-friendly H.264 High@4.2, AAC 48 kHz)
ffmpeg -loglevel error -y -i film_video.mp4 -i film_audio.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart ../render/partition1772_FINAL_master.mp4
ffmpeg -loglevel error -y -i film_video.mp4 -i film_audio.wav -map 0:v -map 1:a -c:v libx264 -preset slow -crf 17 -profile:v high -level 4.2 -pix_fmt yuv420p \
  -maxrate 20M -bufsize 40M -tune film -c:a aac -b:a 256k -ar 48000 -shortest -movflags +faststart ../render/partition1772_FINAL_tiktok.mp4
ls -la ../render
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,duration,bit_rate -of compact ../render/partition1772_FINAL_tiktok.mp4
