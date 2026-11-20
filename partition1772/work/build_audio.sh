#!/bin/sh
# Preview soundtrack: narration segments aligned to the scene timeline, with 25 ms edge fades.
N=/home/user/Claude-/partition1772/audio/narration.mp3
seg() { ffmpeg -loglevel error -y -ss $1 -to $2 -i $N -af "afade=t=in:d=0.025,afade=t=out:st=$(python3 -c "print($2-$1-0.06)"):d=0.06" -ar 48000 -ac 1 $3; }
sil() { ffmpeg -loglevel error -y -f lavfi -i anullsrc=r=48000:cl=mono -t $1 $2; }
mkdir -p a && cd a
sil 1.0 s1a.wav; seg 0 31.95 s1b.wav; sil 0.8 s1c.wav
sil 0.5 s2a.wav; seg 168.40 181.50 s2b.wav; seg 248.50 261.05 s2c.wav; sil 1.0 s2d.wav
sil 0.6 s3a.wav; seg 304.30 315.35 s3b.wav; sil 0.5 s3c.wav
seg 315.35 372.25 s4.wav
seg 372.25 388.0 s5a.wav; sil 1.6 s5b.wav
ls s1a.wav s1b.wav s1c.wav s2a.wav s2b.wav s2c.wav s2d.wav s3a.wav s3b.wav s3c.wav s4.wav s5a.wav s5b.wav | sed "s/^/file '/;s/$/'/" > list.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i list.txt -c:a pcm_s16le ../preview_audio.wav
ffprobe -v error -show_entries format=duration -of csv=p=0 ../preview_audio.wav
