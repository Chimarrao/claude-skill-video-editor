#!/usr/bin/env python3
"""Gera um vídeo-placeholder (fundo escuro + texto) para trechos SEM B-roll aproveitável, para o usuário trocar à mão no CapCut.
Uso: gerar_placeholder.py "<Assunto>" --saida ../Assets/_placeholders/ph_x.mp4 [--dur 60] [--detalhe "o que colocar aqui"]
No plano_dados.py use como clipe normal: ('item', '<saida>', 0, <dur_do_trecho>, 1.0, <t_inicio>)."""

import argparse, os, subprocess
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("assunto")
ap.add_argument("--saida", required=True)
ap.add_argument("--dur", type=float, default=60)
ap.add_argument("--detalhe", default="")
a = ap.parse_args()
os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
img = Image.new("RGB", (1920, 1080), (46, 20, 20))
d = ImageDraw.Draw(img)


def fonte(n):
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, n)
    return ImageFont.load_default()


d.rectangle((60, 60, 1860, 1020), outline=(249, 38, 114), width=8)
d.text((960, 380), "B-ROLL MANUAL", font=fonte(120), fill=(249, 38, 114), anchor="mm")
d.text((960, 540), a.assunto, font=fonte(72), fill=(255, 255, 255), anchor="mm")
if a.detalhe:
    d.text((960, 650), a.detalhe, font=fonte(44), fill=(200, 200, 200), anchor="mm")
d.text(
    (960, 900), "substitua este trecho por um vídeo seu", font=fonte(40), fill=(150, 150, 150), anchor="mm"
)
png = a.saida + ".png"
img.save(png)
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-framerate",
        "30",
        "-t",
        str(a.dur),
        "-i",
        png,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        a.saida,
    ],
    capture_output=True,
    check=True,
)
os.remove(png)
print(a.saida)
