---
name: watch
description: Watch a video file and report what happens in it - scenes, on-screen text, narration/transcript, timing, style, and (on request) a reusable prompt to make something similar. Use when the user shares a video (.mp4/.mov/.webm) or says /watch, "watch this", "analyse this video", "what happens in this video".
---

# Watch

You cannot play video, so turn it into things you can read: key frames, contact sheets and a transcript.

## 1. Prepare

```bash
pip install -q faster-whisper 2>/dev/null   # once per session; model downloads from huggingface.co on first use
python3 .claude/skills/watch/scripts/watch.py "<video>" --out "<scratchpad>/watch-<name>"
```

Options: `--model small` (default; `base` is faster, `medium` more accurate), `--lang de` to force a language, `--max-frames 48`, `--no-audio`.
It prints the path of `report.md`. If transcription fails (model host blocked, no speech), say so - never invent narration.

## 2. Look

1. Read `report.md` (metadata, scene-change times, transcript).
2. Read every `sheet_N.png` in order. Each cell has its timestamp burned in.
3. For small text, charts or details you can't read on a sheet, Read the single frame in `frames/`.

## 3. Report

Answer the user's question. If they just said "watch", give:

- **Overview** - one or two sentences: what it is, length, format, audio (speech / music only / silent).
- **Timeline** - a table `time | what's on screen | text/narration`, one row per beat.
- **On-screen text** - quote exactly; note where you could not read it.
- **Style** (for creative videos) - layout, typography, colour, camera, transitions, pacing.
- **Claims** - flag facts that look wrong or uncertain.

Mark what you inferred vs saw. Only describe what the frames and transcript show.

If asked for a **prompt** or **skill**, turn the analysis into a reusable, fill-in-the-blanks prompt that captures format and style without copying the creator's branding, handle or exact script.
