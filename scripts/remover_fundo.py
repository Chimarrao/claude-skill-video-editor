"""Remove fundo de imagens. Uso: python remover_fundo.py entrada.png saida.png [modo]
modo 'cor'  : logo colorido sobre fundo claro/liso -> mantém pixels saturados (ex.: logo tema/Copilot)
modo 'liso' : objeto fotografado sobre fundo liso -> remove pela distância à cor dos cantos (ex.: módulo de RAM)
"""

import sys, numpy as np
from PIL import Image, ImageFilter

src, dst = sys.argv[1], sys.argv[2]
modo = sys.argv[3] if len(sys.argv) > 3 else "liso"
im = Image.open(src).convert("RGB")
a = np.asarray(im).astype(float)
if modo == "cor":
    mx, mn = a.max(2) / 255, a.min(2) / 255
    sat = (mx - mn) / (mx + 1e-6)
    alpha = np.clip((sat - 0.28) / 0.2, 0, 1)
else:
    cantos = np.concatenate(
        [
            a[:15, :15].reshape(-1, 3),
            a[:15, -15:].reshape(-1, 3),
            a[-15:, :15].reshape(-1, 3),
            a[-15:, -15:].reshape(-1, 3),
        ]
    )
    d = np.sqrt(((a - np.median(cantos, axis=0)) ** 2).sum(2))
    alpha = np.clip((d - 38) / 25, 0, 1)
m = (
    Image.fromarray((alpha * 255).astype("uint8"))
    .filter(ImageFilter.MedianFilter(5))
    .filter(ImageFilter.MinFilter(3))
    .filter(ImageFilter.GaussianBlur(1.0))
)
big = im.resize((im.width * 3, im.height * 3), Image.LANCZOS) if modo == "cor" else im
mm = m.resize(big.size, Image.LANCZOS) if modo == "cor" else m
out = big.convert("RGBA")
out.putalpha(mm)
out = out.crop(out.getbbox())
out.save(dst)
print(out.size)
