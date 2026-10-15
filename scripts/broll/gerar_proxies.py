#!/usr/bin/env python3
"""Proxies leves (640x360, sem áudio, corte "cobrir" 16:9) SÓ dos trechos escolhidos, para a prévia do B-roll no editor do Motion Canvas.
Uso (na pasta animacao/): python gerar_proxies.py   (lê src/scenes/broll.json; grava src/videos/clip_NN.mp4 e src/videos/preenchimento.mp4)
Não mexe nos vídeos originais nem na montagem do CapCut."""

import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

B = json.load(open("src/scenes/broll.json"))
os.makedirs("src/videos", exist_ok=True)
VF = "scale=640:360:force_original_aspect_ratio=increase,crop=640:360,fps=30"


def go(i):
    c = B[i]
    out = f"src/videos/clip_{i+1:02d}.mp4"
    if os.path.exists(out):
        return out
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(c["in"]),
            "-t",
            str(round(c["out"] - c["in"], 3)),
            "-i",
            c["arquivo"],
            "-an",
            "-vf",
            VF,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-g",
            "30",
            out,
        ],
        check=True,
    )
    return out


def filler():
    d = os.path.abspath(".")
    while d != "/":
        f = os.path.join(d, ".claude", "skills", "animacao-narracao", "assets", "fundo_preenchimento.mp4")
        if os.path.exists(f):
            break
        d = os.path.dirname(d)
    out = "src/videos/preenchimento.mp4"
    if not os.path.exists(out):
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                f,
                "-an",
                "-vf",
                VF,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "30",
                "-pix_fmt",
                "yuv420p",
                "-g",
                "30",
                out,
            ],
            check=True,
        )


with ThreadPoolExecutor(4) as ex:
    list(ex.map(go, range(len(B))))
filler()
print(
    f"{len(B)} proxies + preenchimento em src/videos/ ({sum(os.path.getsize('src/videos/'+f) for f in os.listdir('src/videos'))/1e6:.0f} MB)"
)
