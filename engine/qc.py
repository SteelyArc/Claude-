"""Technical QC for a rendered MP4: format, frame rate, black/frozen frames, loudness, review contact sheets."""
import json, os, re, subprocess, sys

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(r.stdout)

def qc(path, expect_w=1080, expect_h=1920, fps="30/1", sheet_every=1.5, sheet_dir=None):
    p = probe(path)
    v = [s for s in p["streams"] if s["codec_type"] == "video"][0]
    a = [s for s in p["streams"] if s["codec_type"] == "audio"]
    rep = {"file": path, "duration": float(p["format"]["duration"]),
           "video": {"codec": v["codec_name"], "profile": v.get("profile"), "w": v["width"], "h": v["height"],
                     "pix_fmt": v["pix_fmt"], "r_frame_rate": v["r_frame_rate"], "avg_frame_rate": v["avg_frame_rate"],
                     "frames": int(v.get("nb_frames", 0)), "bitrate_kbps": int(int(v.get("bit_rate", 0)) / 1000)},
           "audio": {"codec": a[0]["codec_name"], "sr": a[0]["sample_rate"], "ch": a[0]["channels"]} if a else None}
    checks = {
        "resolution 1080x1920": (v["width"], v["height"]) == (expect_w, expect_h),
        "H.264": v["codec_name"] == "h264", "yuv420p": v["pix_fmt"] == "yuv420p",
        "30 fps constant": v["r_frame_rate"] == fps and v["avg_frame_rate"] == fps,
        "AAC audio": bool(a) and a[0]["codec_name"] == "aac",
    }
    bd = run(["ffmpeg", "-v", "info", "-i", path, "-vf", "blackdetect=d=0.1:pix_th=0.06", "-an", "-f", "null", "-"]).stderr
    rep["black_segments"] = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd)
    fz = run(["ffmpeg", "-v", "info", "-i", path, "-vf", "freezedetect=n=0.0005:d=2.5", "-an", "-f", "null", "-"]).stderr
    rep["frozen_segments"] = re.findall(r"freeze_start: ([\d.]+)", fz)
    lo = run(["ffmpeg", "-v", "info", "-i", path, "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"]).stderr
    m = re.search(r"I:\s+(-?[\d.]+) LUFS.*?LRA:\s+([\d.]+) LU.*?Peak:\s+(-?[\d.]+) dBFS", lo, re.S)
    if m:
        rep["loudness"] = {"integrated_LUFS": float(m.group(1)), "LRA": float(m.group(2)), "true_peak_dBTP": float(m.group(3))}
        checks["true peak ≤ -1 dBTP"] = float(m.group(3)) <= -1.0
    rep["checks"] = checks
    if sheet_dir:
        os.makedirs(sheet_dir, exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf",
             f"fps=1/{sheet_every},scale=270:480,tile=8x3:padding=4:color=white", os.path.join(sheet_dir, "sheet_%02d.png")])
    return rep

if __name__ == "__main__":
    r = qc(sys.argv[1], sheet_dir=sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps(r, indent=1, ensure_ascii=False))
