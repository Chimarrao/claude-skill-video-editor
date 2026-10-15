"""Remove fundo liso conectado às bordas (flood-fill). Uso: python crop_background.py entrada.png saida.png [tolerancia=14]"""

import sys, numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

src, dst = sys.argv[1], sys.argv[2]
tol = float(sys.argv[3]) if len(sys.argv) > 3 else 14
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(float)
bg = np.median(
    np.concatenate(
        [
            a[:6, :6].reshape(-1, 3),
            a[:6, -6:].reshape(-1, 3),
            a[-6:, :6].reshape(-1, 3),
            a[-6:, -6:].reshape(-1, 3),
        ]
    ),
    axis=0,
)
background = ~(np.sqrt(((a - bg) ** 2).sum(2)) > tol)
lab, n = ndimage.label(background)
border = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
border.discard(0)
alpha = (~np.isin(lab, list(border))).astype(float)
m = (
    Image.fromarray((alpha * 255).astype("uint8"))
    .filter(ImageFilter.MinFilter(3))
    .filter(ImageFilter.GaussianBlur(0.8))
)
out = im.convert("RGBA")
out.putalpha(m)
out = out.crop(out.getbbox())
out.save(dst)
print(out.size)
