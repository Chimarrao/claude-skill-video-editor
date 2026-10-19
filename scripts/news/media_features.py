#!/usr/bin/env python3
"""NEWS — extrai do arquivo fundido as características usadas pelo editor automático: energia do áudio (dB a cada 10 ms) e miniaturas
em cinza do vídeo (10 quadros/s, 96×54) para medir MOVIMENTO da tela e CONTINUIDADE visual entre dois pontos de corte.
Uso: python media_features.py <fundido.mov> <saida.npz>   (≈ 2–4 min para 13 min de vídeo 1440p)"""

import subprocess, sys

import numpy as np

W, H, FPS = 96, 54, 10


def energia_db(path, sr=16000, hop=160):
    """dB (RMS) por janela de `hop` amostras (10 ms em 16 kHz)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "a:0", "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    n = len(a) // hop
    r = np.sqrt((a[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    return (20 * np.log10(r + 1e-9)).astype(np.float32)


def miniaturas(path):
    """Quadros em cinza WxH a FPS quadros/s: array (N, H, W) uint8."""
    p = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", path, "-map", "v:0", "-vf", f"fps={FPS},scale={W}:{H}:flags=area,format=gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE
    )
    buf = p.stdout.read()
    p.wait()
    return np.frombuffer(buf, dtype=np.uint8).reshape(-1, H, W)


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    e = energia_db(src)
    fr = miniaturas(src)
    mov = np.abs(np.diff(fr.astype(np.int16), axis=0)).mean(axis=(1, 2)).astype(np.float32)
    np.savez_compressed(dst, energy_db=e, frames=fr, motion=mov, fps=FPS)
    print(f"energia {len(e)} janelas de 10 ms · {len(fr)} quadros a {FPS} fps · movimento médio {mov.mean():.2f}")
