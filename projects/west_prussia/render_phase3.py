"""Render the Phase 3 animation preview → previews/animation/phase3_preview_versailles.mp4"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine.video import render, mux
from projects.west_prussia import seq_versailles as S
from projects.west_prussia.audio_versailles import build

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if __name__ == "__main__":
    S.assets()   # load photo/depth/document once before forking
    vid = os.path.join(ROOT, "build/phase3_video.mp4")
    render(("projects.west_prussia.seq_versailles", "frame_at"), list(range(S.n_frames())), vid, workers=4)
    wav = build(os.path.join(ROOT, "build/audio_versailles.wav"))
    out = os.path.join(ROOT, "previews/animation/phase3_preview_versailles.mp4")
    mux(vid, wav, out)
    print("done", out)
