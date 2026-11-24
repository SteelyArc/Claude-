#!/usr/bin/env python3
"""Prepare a video for Claude to "watch": key frames, contact sheets, transcript.

Usage: python3 watch.py <video> [--out DIR] [--model small] [--lang de] [--max-frames 48] [--no-audio]

Writes into DIR (default: ./watch-<name>/):
  frames/f_<seconds>.jpg   key frames (scene changes + one every few seconds)
  sheet_N.png              contact sheets, 4x3 frames each, timestamps burned in
  transcript.txt           "[mm:ss - mm:ss] text" lines (if the video has audio)
  report.md                metadata, frame list, transcript - the starting point for analysis
"""
import argparse, json, os, re, shutil, subprocess, sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    info = json.loads(r.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    num, den = (v.get("r_frame_rate", "0/1").split("/") + ["1"])[:2]
    return {
        "duration": float(info["format"].get("duration", 0)),
        "width": v.get("width"), "height": v.get("height"),
        "fps": round(float(num) / float(den or 1), 2) if float(den or 1) else None,
        "has_audio": a is not None,
    }


def mmss(t):
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


def scene_times(path, threshold):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"])
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def pick_times(duration, scenes, max_frames):
    # Scene changes plus a steady sample, so slow morphs without hard cuts are still covered.
    step = max(1.0, duration / max(8, max_frames // 2))
    times = set(round(t, 2) for t in scenes)
    t = 0.3
    while t < duration:
        times.add(round(t, 2)); t += step
    times.add(round(max(0, duration - 0.2), 2))
    times = sorted(times)
    # drop near-duplicates (< 0.4 s apart)
    out = []
    for t in times:
        if not out or t - out[-1] >= 0.4:
            out.append(t)
    if len(out) > max_frames:  # thin evenly
        k = len(out) / max_frames
        out = [out[int(i * k)] for i in range(max_frames)]
    return out


def extract(path, times, fdir, width):
    os.makedirs(fdir, exist_ok=True)
    files = []
    for t in times:
        f = os.path.join(fdir, f"f_{t:07.2f}.jpg")
        run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", path, "-frames:v", "1",
             "-vf", f"scale={width}:-2", "-q:v", "3", f])
        if os.path.exists(f):
            files.append((t, f))
    return files


def sheets(files, out, cols=4, rows=3, cell=360):
    made = []
    per = cols * rows
    for n in range(0, len(files), per):
        chunk = files[n:n + per]
        tmp = os.path.join(out, "_sheet_tmp"); os.makedirs(tmp, exist_ok=True)
        for i, (t, f) in enumerate(chunk):
            run(["ffmpeg", "-loglevel", "error", "-y", "-i", f, "-vf",
                 f"scale={cell}:{cell}:force_original_aspect_ratio=decrease,pad={cell}:{cell}:(ow-iw)/2:(oh-ih)/2:black,"
                 f"drawtext=text='{mmss(t).replace(':', chr(92) + ':')}':x=8:y=8:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=4",
                 os.path.join(tmp, f"c{i:03d}.png")])
        for i in range(len(chunk), per):  # pad the grid
            run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=black:s={cell}x{cell}", "-frames:v", "1",
                 os.path.join(tmp, f"c{i:03d}.png")])
        s = os.path.join(out, f"sheet_{n // per + 1}.png")
        run(["ffmpeg", "-loglevel", "error", "-y", "-i", os.path.join(tmp, "c%03d.png"),
             "-vf", f"tile={cols}x{rows}:padding=4:color=gray", "-frames:v", "1", s])
        shutil.rmtree(tmp, ignore_errors=True)
        if os.path.exists(s):
            made.append((s, chunk[0][0], chunk[-1][0]))
    return made


def audio_level(path):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"])
    m = re.search(r"mean_volume: ([-0-9.]+) dB", r.stderr)
    return float(m.group(1)) if m else None


def transcribe(path, model_name, lang):
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # xet CDN is often blocked by proxies; plain HTTPS works
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None, "faster-whisper not installed (pip install faster-whisper)"
    try:
        import numpy as np
        # Decode with ffmpeg (16 kHz mono float) - avoids PyAV version mismatches inside faster-whisper.
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000",
                              "-f", "f32le", "-"], capture_output=True).stdout
        audio = np.frombuffer(raw, dtype=np.float32)
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segs, info = model.transcribe(audio, language=lang, vad_filter=True, beam_size=5)
        lines = [(s.start, s.end, s.text.strip()) for s in segs if s.text.strip()]
        return {"language": info.language, "prob": round(info.language_probability, 2), "lines": lines}, None
    except Exception as e:  # model download blocked, etc.
        return None, f"transcription failed: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out")
    ap.add_argument("--model", default="small")
    ap.add_argument("--lang", default=None)
    ap.add_argument("--max-frames", type=int, default=48)
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--no-audio", action="store_true")
    a = ap.parse_args()

    video = os.path.abspath(a.video)
    name = re.sub(r"[^A-Za-z0-9_-]+", "-", os.path.splitext(os.path.basename(video))[0])[:40]
    out = os.path.abspath(a.out or f"watch-{name}")
    os.makedirs(out, exist_ok=True)

    meta = probe(video)
    scenes = scene_times(video, a.threshold)
    times = pick_times(meta["duration"], scenes, a.max_frames)
    files = extract(video, times, os.path.join(out, "frames"), 720)
    made = sheets(files, out)

    tr, err, level = None, None, None
    if meta["has_audio"] and not a.no_audio:
        level = audio_level(video)
        tr, err = transcribe(video, a.model, a.lang)
        if tr:
            with open(os.path.join(out, "transcript.txt"), "w") as f:
                for s, e, t in tr["lines"]:
                    f.write(f"[{mmss(s)} - {mmss(e)}] {t}\n")

    r = [f"# Watch report: {os.path.basename(video)}", "",
         f"- Duration: {meta['duration']:.2f} s · {meta['width']}x{meta['height']} · {meta['fps']} fps",
         f"- Audio: {'yes' if meta['has_audio'] else 'no'}" + (f" (mean {level} dB)" if level is not None else ""),
         f"- Scene changes detected (threshold {a.threshold}): {len(scenes)}"
         + (" at " + ", ".join(mmss(t) for t in scenes[:40]) if scenes else ""),
         f"- Frames extracted: {len(files)}", "", "## Contact sheets", ""]
    r += [f"- `{s}` ({mmss(t0)} → {mmss(t1)})" for s, t0, t1 in made]
    r += ["", "## Transcript", ""]
    if tr:
        r.append(f"Language: {tr['language']} (p={tr['prob']}), model `{a.model}`")
        r.append("")
        r += [f"- [{mmss(s)}] {t}" for s, e, t in tr["lines"]] or ["_(no speech detected — likely music only)_"]
    else:
        r.append(f"_{err or 'no audio track'}_")
    with open(os.path.join(out, "report.md"), "w") as f:
        f.write("\n".join(r) + "\n")
    print(os.path.join(out, "report.md"))


if __name__ == "__main__":
    sys.exit(main())
