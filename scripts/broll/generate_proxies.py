#!/usr/bin/env python3
"""Proxies leves (640x360, sem áudio, corte "cobrir" 16:9) SÓ dos trechos escolhidos, para a prévia do B-roll no editor do Motion Canvas.
Uso (na pasta animacao/): python generate_proxies.py   (lê src/scenes/broll.json; grava src/videos/clip_NN.mp4 e src/videos/preenchimento.mp4)
Não mexe nos vídeos originais nem na montagem do CapCut."""

import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

CLIPS = json.load(open("src/scenes/broll.json"))
os.makedirs("src/videos", exist_ok=True)
VF = "scale=640:360:force_original_aspect_ratio=increase,crop=640:360,fps=30"


def build_proxy(index):
    clip = CLIPS[index]
    output = f"src/videos/clip_{index+1:02d}.mp4"
    # a assinatura (arquivo, in, out) evita reaproveitar um proxy antigo quando o plano muda e o índice NN passa a apontar para outro trecho
    signature = f"{clip['arquivo']}|{clip['in']}|{clip['out']}"
    sig_file = output + ".src"
    if os.path.exists(output) and os.path.exists(sig_file) and open(sig_file).read() == signature:
        return output
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(clip["in"]),
            "-t",
            str(round(clip["out"] - clip["in"], 3)),
            "-i",
            clip["arquivo"],
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
            output,
        ],
        check=True,
    )
    open(sig_file, "w").write(signature)
    return output


def build_filler():
    current = os.path.abspath(".")
    while current != "/":
        asset = os.path.join(
            current, ".claude", "skills", "animacao-narracao", "assets", "fundo_preenchimento.mp4"
        )
        if os.path.exists(asset):
            break
        current = os.path.dirname(current)
    output = "src/videos/preenchimento.mp4"
    if not os.path.exists(output):
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                asset,
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
                output,
            ],
            check=True,
        )


with ThreadPoolExecutor(4) as executor:
    list(executor.map(build_proxy, range(len(CLIPS))))
build_filler()
print(
    f"{len(CLIPS)} proxies + preenchimento em src/videos/ ({sum(os.path.getsize('src/videos/'+f) for f in os.listdir('src/videos'))/1e6:.0f} MB)"
)
