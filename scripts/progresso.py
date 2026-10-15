#!/usr/bin/env python3
"""Barra de progresso TUI para processos longos (render, transcrição, alinhamento...).

Uso:
  progresso.py arquivo ARQ --total-mb 2200 [--rotulo render]   # % = tamanho atual / esperado
  progresso.py frames ARQ.mov --total 27263                    # % = frames (ffprobe, aproximado por duração)
  progresso.py log LOG [--regex '(\\d+(?:\\.\\d+)?)%']          # % = último número casado no log
  progresso.py ... --uma-vez     # imprime uma linha e sai (para o agente colar no chat)
Mostra: barra, %, velocidade, tempo decorrido e ETA. Ctrl+C sai.
"""

import argparse, os, re, subprocess, sys, time


def fmt(s):
    s = int(max(0, s))
    return f"{s//3600:d}:{s%3600//60:02d}:{s%60:02d}"


def pct_arquivo(a):
    return os.path.getsize(a) / (a.total_mb * 1048576) if os.path.exists(a.alvo) else 0.0


def pct_frames(a):
    if not os.path.exists(a.alvo):
        return 0.0
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.alvo],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip()) * a.fps / a.total
    except ValueError:
        return 0.0


def pct_log(a):
    if not os.path.exists(a.alvo):
        return 0.0
    txt = open(a.alvo, errors="ignore").read()[-20000:]
    m = re.findall(a.regex, txt)
    return float(m[-1]) / 100 if m else 0.0


def barra(p, larg=40):
    p = min(max(p, 0), 1)
    n = int(p * larg)
    return "█" * n + "░" * (larg - n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modo", choices=["arquivo", "frames", "log"])
    ap.add_argument("alvo")
    ap.add_argument("--total-mb", type=float, default=2200)
    ap.add_argument("--total", type=float, default=0)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--regex", default=r"(\d+(?:\.\d+)?)\s*%")
    ap.add_argument("--rotulo", default="progresso")
    ap.add_argument("--intervalo", type=float, default=5)
    ap.add_argument("--uma-vez", action="store_true")
    a = ap.parse_args()
    if a.modo == "arquivo":
        a.total_mb = a.total_mb
        f = lambda a: os.path.getsize(a.alvo) / (a.total_mb * 1048576) if os.path.exists(a.alvo) else 0.0
    else:
        f = pct_frames if a.modo == "frames" else pct_log
    t0 = time.time()
    ult = (t0, 0.0)
    while True:
        p = min(f(a), 0.99 if a.modo == "arquivo" else 1.0)
        agora = time.time()
        dt = agora - t0
        eta = dt * (1 - p) / p if p > 0.005 else 0
        linha = f"{a.rotulo} [{barra(p)}] {p*100:5.1f}%  decorrido {fmt(dt)}  ETA {fmt(eta) if eta else '--:--:--'}"
        if a.uma_vez:
            print(linha)
            return
        sys.stdout.write("\r" + linha + "  ")
        sys.stdout.flush()
        if p >= 1:
            print()
            return
        time.sleep(a.intervalo)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
