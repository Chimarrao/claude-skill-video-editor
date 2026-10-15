"""Remove fundo de imagens. Uso: python remove_background.py entrada.png saida.png [modo]
modo 'color' : logo colorido sobre fundo claro/liso -> mantém pixels saturados (ex.: logo tema/Copilot)
modo 'flat'  : objeto fotografado sobre fundo liso -> remove pela distância à cor dos cantos (ex.: módulo de RAM)
"""

import sys, numpy as np
from PIL import Image, ImageFilter

input_path, output_path = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "flat"
image = Image.open(input_path).convert("RGB")
pixels = np.asarray(image).astype(float)
if mode == "color":
    mx, mn = pixels.max(2) / 255, pixels.min(2) / 255
    sat = (mx - mn) / (mx + 1e-6)
    alpha = np.clip((sat - 0.28) / 0.2, 0, 1)
else:
    corners = np.concatenate(
        [
            pixels[:15, :15].reshape(-1, 3),
            pixels[:15, -15:].reshape(-1, 3),
            pixels[-15:, :15].reshape(-1, 3),
            pixels[-15:, -15:].reshape(-1, 3),
        ]
    )
    d = np.sqrt(((pixels - np.median(corners, axis=0)) ** 2).sum(2))
    alpha = np.clip((d - 38) / 25, 0, 1)
mask = (
    Image.fromarray((alpha * 255).astype("uint8"))
    .filter(ImageFilter.MedianFilter(5))
    .filter(ImageFilter.MinFilter(3))
    .filter(ImageFilter.GaussianBlur(1.0))
)
large = image.resize((image.width * 3, image.height * 3), Image.LANCZOS) if mode == "color" else image
mask_large = mask.resize(large.size, Image.LANCZOS) if mode == "color" else mask
output = large.convert("RGBA")
output.putalpha(mask_large)
output = output.crop(output.getbbox())
output.save(output_path)
print(output.size)
