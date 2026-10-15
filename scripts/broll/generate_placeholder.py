#!/usr/bin/env python3
"""Gera um vídeo-placeholder (fundo escuro + texto) para trechos SEM B-roll aproveitável, para o usuário trocar à mão no CapCut.
Uso: generate_placeholder.py "<subject>" --output ../Assets/_placeholders/ph_x.mp4 [--duration 60] [--detail "o que colocar aqui"]
No plan_data.py use como clipe normal: ('item', '<saida>', 0, <dur_do_trecho>, 1.0, <t_start>)."""

import argparse, os, subprocess
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument("subject")
parser.add_argument("--output", required=True)
parser.add_argument("--duration", type=float, default=60)
parser.add_argument("--detail", default="")
args = parser.parse_args()
os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
img = Image.new("RGB", (1920, 1080), (46, 20, 20))
draw = ImageDraw.Draw(img)


def load_font(size):
    # procura fonte do sistema para o texto ficar legível
    """Procura uma fonte do sistema para o texto ficar legível."""
    for f in ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


draw.rectangle((60, 60, 1860, 1020), outline=(249, 38, 114), width=8)
draw.text((960, 380), "B-ROLL MANUAL", font=load_font(120), fill=(249, 38, 114), anchor="mm")
draw.text((960, 540), args.subject, font=load_font(72), fill=(255, 255, 255), anchor="mm")
if args.detail:
    draw.text((960, 650), args.detail, font=load_font(44), fill=(200, 200, 200), anchor="mm")
draw.text(
    (960, 900), "substitua este trecho por um vídeo seu", font=load_font(40), fill=(150, 150, 150), anchor="mm"
)
png_path = args.output + ".png"
img.save(png_path)
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-framerate",
        "30",
        "-t",
        str(args.duration),
        "-i",
        png_path,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        args.output,
    ],
    capture_output=True,
    check=True,
)
os.remove(png_path)
print(args.output)
