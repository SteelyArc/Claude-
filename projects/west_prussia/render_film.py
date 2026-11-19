"""Render the full documentary → output/West_Prussia_TikTok_1080x1920.mp4"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine.video import render, mux
from projects.west_prussia import film as F

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if __name__ == "__main__":
    F.warm()
    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    vid = os.path.join(ROOT, "build/film_video.mp4")
    render(("projects.west_prussia.film", "frame_at"), list(range(F.n_frames())), vid, workers=4)
    wav = os.path.join(ROOT, "build/audio_film.wav")
    if not os.path.exists(wav):
        from projects.west_prussia.audio_film import build
        build(wav)
    out = os.path.join(ROOT, "output/West_Prussia_TikTok_1080x1920.mp4")
    mux(vid, wav, out)
    print("done", out, flush=True)
