#!/usr/bin/env python3
"""Barra de progresso TUI para processos longos (render, transcrição, alinhamento...).

Uso:
  progress.py file ARQ --total-mb 2200 [--label render]   # % = tamanho atual / esperado
  progress.py frames ARQ.mov --total 27263                    # % = frames (ffprobe, aproximado por duração)
  progress.py log LOG [--regex '(\\d+(?:\\.\\d+)?)%']          # % = último número casado no log
  progress.py ... --once     # imprime uma linha e sai (para o agente colar no chat)
Mostra: barra, %, velocidade, tempo decorrido e ETA. Ctrl+C sai.
"""

import argparse, os, re, subprocess, sys, time


def format_duration(seconds):
    seconds = int(max(0, seconds))
    return f"{seconds//3600:d}:{seconds%3600//60:02d}:{seconds%60:02d}"


def file_pct(args):
    return os.path.getsize(args) / (args.total_mb * 1048576) if os.path.exists(args.target) else 0.0


def frames_pct(args):
    if not os.path.exists(args.target):
        return 0.0
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", args.target],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip()) * args.fps / args.total
    except ValueError:
        return 0.0


def log_pct(args):
    if not os.path.exists(args.target):
        return 0.0
    txt = open(args.target, errors="ignore").read()[-20000:]
    m = re.findall(args.regex, txt)
    return float(m[-1]) / 100 if m else 0.0


def bar(progress, width=40):
    progress = min(max(progress, 0), 1)
    n = int(progress * width)
    return "█" * n + "░" * (width - n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["file", "frames", "log"])
    ap.add_argument("target")
    ap.add_argument("--total-mb", type=float, default=2200)
    ap.add_argument("--total", type=float, default=0)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--regex", default=r"(\d+(?:\.\d+)?)\s*%")
    ap.add_argument("--label", default="progress")
    ap.add_argument("--interval", type=float, default=5)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.mode == "file":
        args.total_mb = args.total_mb
        f = lambda a: os.path.getsize(a.target) / (a.total_mb * 1048576) if os.path.exists(a.target) else 0.0
    else:
        f = frames_pct if args.mode == "frames" else log_pct
    t0 = time.time()
    last = (t0, 0.0)
    while True:
        p = min(f(args), 0.99 if args.mode == "file" else 1.0)
        now = time.time()
        dt = now - t0
        eta = dt * (1 - p) / p if p > 0.005 else 0
        line = f"{args.label} [{bar(p)}] {p*100:5.1f}%  decorrido {format_duration(dt)}  ETA {format_duration(eta) if eta else '--:--:--'}"
        if args.once:
            print(line)
            return
        sys.stdout.write("\r" + line + "  ")
        sys.stdout.flush()
        if p >= 1:
            print()
            return
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
