"""Monocular depth (Depth Anything V2 Small, Apache-2.0, ONNX) for subtle 2.5D parallax on archival photos.
The depth map only drives a small geometric camera parallax; image pixels are never generated or altered."""
import os, numpy as np, cv2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, "cache", "models", "da2s", "onnx", "model.onnx")

def depth_map(img_rgb, cache_path=None, size=518):
    if cache_path and os.path.exists(cache_path):
        return np.load(cache_path)
    import onnxruntime as ort
    sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    h, w = img_rgb.shape[:2]
    s = size / max(h, w)
    nh, nw = int(round(h * s / 14) * 14), int(round(w * s / 14) * 14)
    x = cv2.resize(img_rgb, (nw, nh), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]   # relative inverse depth (near = high)
    d = cv2.resize(out, (w, h), interpolation=cv2.INTER_CUBIC)
    d = (d - np.percentile(d, 2)) / (np.percentile(d, 98) - np.percentile(d, 2) + 1e-6)
    d = cv2.GaussianBlur(np.clip(d, 0, 1).astype(np.float32), (0, 0), max(h, w) / 300)
    if cache_path:
        np.save(cache_path, d)
    return d
