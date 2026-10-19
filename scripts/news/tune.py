#!/usr/bin/env python3
"""NEWS — varre parâmetros do editor contra os cortes reais (gabarito) e mostra recall/precisão/F1. Uso: python tune.py "<pasta ep>" "<draft>" [--grid '{"pause_max_s":[0.8,1,1.3]}'] [--set '{"x":1}']"""

import argparse, itertools, json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan_cuts as pc
from news_cuts import constroi
from news_detect import detecta
from read_draft_cuts import kept_segments, removed as rem_from_kept


def carrega(pasta):
    """(palavras, features) de um episódio."""
    work = os.path.join(pasta, "work")
    tr = json.load(open(os.path.join(work, "transcription.json")))
    z = np.load(os.path.join(work, "features.npz"))
    return pc.carrega_palavras(tr), {k: z[k] for k in z.files}


def gabarito(draft, dur):
    """Remoções do usuário [(a, b)]."""
    kept, d = kept_segments(draft)
    return rem_from_kept(kept, max(m["duration"] for m in d["materials"]["videos"]) / 1e6)


def roda(words, feats, P):
    """Cortes automáticos [(a, b)] + resultado completo."""
    utts = pc.enunciados(words, P["utterance_gap_s"])
    res = constroi(words, detecta(words, utts, feats, P), feats, P)
    return [(r["start"], r["end"]) for r in res["removed"]], res


def metricas(M, G, dur, tol=0.3):
    """recall/precisão por PONTOS (bordas internas) e por remoção (duas bordas)."""
    pts = lambda R: [t for a, b in R for t in (a, b) if 0.01 < t < dur - 0.05]
    gp, mp = pts(G), pts(M)
    rec = sum(1 for t in gp if mp and min(abs(t - u) for u in mp) <= tol) / max(1, len(gp))
    pre = sum(1 for t in mp if gp and min(abs(t - u) for u in gp) <= tol) / max(1, len(mp))
    f1 = 2 * rec * pre / max(1e-9, rec + pre)
    return rec, pre, f1


def metricas_palavras(M, G, words):
    """recall/precisão/F1 no nível de PALAVRAS removidas (o que foi cortado de FALA, ignorando onde caem as bordas)."""
    pr = lambda R: {i for i, w in enumerate(words) if any(a <= (w["s"] + w["e"]) / 2 <= b for a, b in R)}
    g, m = pr(G), pr(M)
    c = len(g & m)
    r, p = c / max(1, len(g)), c / max(1, len(m))
    return r, p, 2 * r * p / max(1e-9, r + p)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pastas_drafts", nargs="+", help="pasta1 draft1 [pasta2 draft2 ...]")
    ap.add_argument("--grid", default="{}")
    ap.add_argument("--set", default="{}")
    ap.add_argument("--sort", choices=["pontos", "palavras"], default="pontos")
    a = ap.parse_args()
    P0 = json.load(open(os.path.join(HERE, "news_params.json")))
    P0.update(json.loads(a.set))
    eps = []
    for pasta, draft in zip(a.pastas_drafts[::2], a.pastas_drafts[1::2]):
        w, f = carrega(pasta)
        dur = len(f["energy_db"]) * 0.01
        eps.append((w, f, gabarito(draft, dur), dur))
    grid = json.loads(a.grid)
    chaves = list(grid)
    linhas = []
    for combo in itertools.product(*[grid[k] for k in chaves]) if chaves else [()]:
        P = dict(P0, **dict(zip(chaves, combo)))
        ms = [roda(w, f, P)[0] for w, f, G, dur in eps]
        rs = [metricas(m, G, dur) for m, (w, f, G, dur) in zip(ms, eps)]
        ws = [metricas_palavras(m, G, w) for m, (w, f, G, dur) in zip(ms, eps)]
        r, p, f1 = (float(np.mean([x[i] for x in rs])) for i in range(3))
        wr, wp, wf = (float(np.mean([x[i] for x in ws])) for i in range(3))
        linhas.append((f1, r, p, dict(zip(chaves, combo)), [round(x[0], 2) for x in rs], wr, wp, wf))
    for f1, r, p, c, per, wr, wp, wf in sorted(linhas, key=lambda x: -(x[0] if a.sort == "pontos" else x[7]))[:12]:
        print(f"PONTOS F1 {f1:.2f} recall {r:.2f} prec {p:.2f} por ep {per} | PALAVRAS recall {wr:.2f} prec {wp:.2f} F1 {wf:.2f} | {c}")
