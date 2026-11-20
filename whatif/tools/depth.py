"""Monocular depth maps (Depth Anything V2 Small, Apache-2.0) for 2.5D parallax of paintings.
Output: data/depth/<name>.npy (float16, 0 = far, 1 = near), same size as the source image."""
import sys, numpy as np, torch
from PIL import Image
from transformers import pipeline
pipe = pipeline('depth-estimation', model='depth-anything/Depth-Anything-V2-Small-hf', device='cpu')
for f in sys.argv[1:]:
    im = Image.open(f).convert('RGB')
    d = np.asarray(pipe(im)['predicted_depth'].squeeze().numpy(), np.float32)
    d = np.asarray(Image.fromarray(d).resize(im.size, Image.BICUBIC))
    d = (d - np.percentile(d, 1)) / (np.percentile(d, 99) - np.percentile(d, 1) + 1e-6)
    n = f.split('/')[-1].rsplit('.', 1)[0]
    np.save(f'data/depth/{n}.npy', np.clip(d, 0, 1).astype(np.float16))
    Image.fromarray((np.clip(d, 0, 1) * 255).astype(np.uint8)).save(f'data/depth/{n}.png')
    print(n, im.size)
