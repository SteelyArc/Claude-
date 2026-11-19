"""Parallel frame rendering → H.264 (yuv420p, 30 fps) segments → lossless concat."""
import os, subprocess, multiprocessing as mp, time, shutil
import numpy as np

FPS = 30
X264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-level", "4.2", "-r", str(FPS), "-g", "60", "-bf", "2", "-movflags", "+faststart"]

def _worker(args):
    render_fn_path, frames, seg_path, W, H = args
    mod_name, fn_name = render_fn_path
    import importlib
    fn = getattr(importlib.import_module(mod_name), fn_name)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-"] + X264 + [seg_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for i, f in enumerate(frames):
        arr = fn(f)
        p.stdin.write(arr.tobytes())
    p.stdin.close(); p.wait()
    return seg_path, len(frames), time.time() - t0

def render(render_fn_path, frame_ids, out_path, workers=4, W=1080, H=1920, tmp=None):
    """render_fn_path = ('module', 'function') taking a global frame index → RGBA uint8 array (H, W, 4)."""
    tmp = tmp or out_path + ".parts"
    os.makedirs(tmp, exist_ok=True)
    n = len(frame_ids)
    chunk = (n + workers - 1) // workers
    jobs = [(render_fn_path, frame_ids[i * chunk:(i + 1) * chunk], os.path.join(tmp, f"seg{i:02d}.mp4"), W, H)
            for i in range(workers) if frame_ids[i * chunk:(i + 1) * chunk]]
    t0 = time.time()
    ctx = mp.get_context("fork")
    with ctx.Pool(len(jobs)) as pool:
        for seg, k, dt in pool.imap_unordered(_worker, jobs):
            print(f"  {os.path.basename(seg)}: {k} frames in {dt:.0f}s", flush=True)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(j[2])}'\n" for j in jobs))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out_path], check=True)
    shutil.rmtree(tmp)
    print(f"video: {n} frames in {time.time() - t0:.0f}s → {out_path}")

def mux(video, audio, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out],
                   check=True)
