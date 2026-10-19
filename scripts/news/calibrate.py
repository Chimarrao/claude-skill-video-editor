#!/usr/bin/env python3
"""NEWS — CALIBRAÇÃO: compara os cortes do editor automático (work/cuts.json) com os cortes REAIS do usuário (projeto do CapCut).
Uso: python calibrate.py "<pasta do episódio>" "<pasta do draft do CapCut>" [--tol 0.3] [--verbose]
Pontos de corte = bordas de cada trecho removido (exceto 0 e o fim do arquivo). Reproduzido = há ponto automático a ≤ tol s.
Mostra: % dos pontos do usuário reproduzidos; remoções iguais / só do usuário (perdidas) / só automáticas (extras), com o texto removido; cortes dentro de palavra."""

import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read_draft_cuts import kept_segments, removed as rem_from_kept

ap = argparse.ArgumentParser()
ap.add_argument("pasta")
ap.add_argument("draft")
ap.add_argument("--tol", type=float, default=0.3)
ap.add_argument("--verbose", action="store_true")
ap.add_argument("--json")
args = ap.parse_args()
work = os.path.join(os.path.abspath(args.pasta), "work")
mine = json.load(open(os.path.join(work, "cuts.json")))
tr = json.load(open(os.path.join(work, "transcription.json")))
words = [(w["start"], w["end"], w["word"].strip()) for sg in tr["segments"] for w in sg["words"] if w["word"].strip()]
dur = mine["stats"]["dur_s"]
gk, d = kept_segments(args.draft)
G = rem_from_kept(gk, max(m["duration"] for m in d["materials"]["videos"]) / 1e6)
M = [(r["start"], r["end"]) for r in mine["removed"]]


def pts(R, dur):
    """Bordas internas das remoções."""
    return [t for a, b in R for t in (a, b) if 0.01 < t < dur - 0.05]


def txt(a, b):
    """Palavras que começam dentro de [a, b]."""
    return " ".join(w for s, e, w in words if s >= a - 0.05 and e <= b + 0.05)


def dentro_palavra(t):
    """Distância (s) até a palavra mais próxima; 0 se o ponto cai dentro de uma palavra."""
    return min((0.0 if s <= t <= e else min(abs(t - s), abs(t - e))) for s, e, _ in words)


gp, mp = pts(G, dur), pts(M, dur)
rec = [min(abs(t - u) for u in mp) <= args.tol for t in gp] if mp else [False] * len(gp)
pre = [min(abs(t - u) for u in gp) <= args.tol for t in mp] if gp else [False] * len(mp)
print(f"USUÁRIO: {len(G)} remoções, {sum(b - a for a, b in G):.0f}s removidos ({100 * (1 - sum(b - a for a, b in G) / dur):.0f}% mantido)")
print(f"AUTO   : {len(M)} remoções, {sum(b - a for a, b in M):.0f}s removidos ({100 * mine['stats']['kept_s'] / dur:.0f}% mantido)")
print(f"RECALL (pontos do usuário reproduzidos ±{args.tol}s): {sum(rec)}/{len(gp)} = {100 * sum(rec) / max(1, len(gp)):.0f}%")
print(f"PRECISÃO (pontos automáticos que o usuário também fez): {sum(pre)}/{len(mp)} = {100 * sum(pre) / max(1, len(mp)):.0f}%")


def casa(r, R):
    """Remoção r tem par em R com as DUAS bordas ≤ tol?"""
    return any(abs(r[0] - q[0]) <= args.tol and abs(r[1] - q[1]) <= args.tol for q in R)


def palavras_removidas(R):
    """Índices das palavras cujo MEIO cai dentro de alguma remoção."""
    return {i for i, (s_, e_, _) in enumerate(words) if any(a <= (s_ + e_) / 2 <= b for a, b in R)}


gw, mw = palavras_removidas(G), palavras_removidas(M)
inter = len(gw & mw)
print(f"PALAVRAS removidas — usuário {len(gw)} · skill {len(mw)} · em comum {inter}: recall {100 * inter / max(1, len(gw)):.0f}% · precisão {100 * inter / max(1, len(mw)):.0f}%")
iguais = [r for r in G if casa(r, M)]
perdidas = [r for r in G if not casa(r, M)]
extras = [r for r in M if not casa(r, G) and r[0] > 0.01 and r[1] < dur - 0.05]
print(f"\nREMOÇÕES iguais: {len(iguais)} · SÓ DO USUÁRIO (perdidas): {len(perdidas)} · SÓ AUTOMÁTICAS (extras): {len(extras)}")
print("\n--- PERDIDAS (usuário cortou, a skill não) ---")
for a, b in perdidas:
    print(f"  {a:7.2f}–{b:7.2f} ({b - a:5.1f}s) «{txt(a, b)[:150]}»")
print("\n--- EXTRAS (a skill cortou, o usuário não) ---")
for a, b in extras:
    motivo = next((r["reason"] for r in mine["removed"] if abs(r["start"] - a) < 1e-6), "?")
    print(f"  {a:7.2f}–{b:7.2f} ({b - a:5.1f}s) [{motivo}] «{txt(a, b)[:150]}»")
dp = [(t, dentro_palavra(t)) for t in mp]
ruins = [(t, m) for t, m in dp if m < 0.08]
print(f"\nCORTES AUTOMÁTICOS a < 80 ms de palavra: {len(ruins)}/{len(mp)} {[(round(t, 2), round(m * 1000)) for t, m in ruins][:10]}")
dpg = [(t, dentro_palavra(t)) for t in gp]
print(f"(referência: cortes do usuário a < 80 ms de palavra: {sum(1 for _, m in dpg if m < 0.08)}/{len(gp)})")
if args.json:
    json.dump(dict(recall=sum(rec) / max(1, len(gp)), precision=sum(pre) / max(1, len(mp)), perdidas=perdidas, extras=extras, iguais=iguais, cortes_em_palavra=len(ruins)), open(args.json, "w"), indent=1)
