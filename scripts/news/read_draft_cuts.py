#!/usr/bin/env python3
"""Lê os cortes de um projeto do CapCut (draft_info.json): trechos mantidos (segundos no ARQUIVO-FONTE, em ordem) e trechos removidos.
Uso: python read_draft_cuts.py <pasta do draft> [--json saida.json]
Serve de gabarito para a calibração do tipo NEWS (ver calibrate.py). Aceita só o formato novo: UMA trilha de vídeo, vídeo+áudio no mesmo clipe."""

import json, os, sys


def kept_segments(draft_dir):
    """[(início, fim)] em segundos no arquivo-fonte, na ordem da trilha de vídeo; avisa se a ordem NÃO é crescente."""
    d = json.load(open(os.path.join(draft_dir, "draft_info.json")))
    segs = []
    for t in d["tracks"]:
        if t["type"] == "video":
            for s in t["segments"]:
                a = s["source_timerange"]["start"] / 1e6
                segs.append((a, a + s["source_timerange"]["duration"] / 1e6, s["target_timerange"]["start"] / 1e6))
    segs.sort(key=lambda x: x[2])
    return [(a, b) for a, b, _ in segs], d


def removed(kept, dur):
    """Intervalos removidos entre os mantidos (e antes do primeiro / depois do último)."""
    out, cur = [], 0.0
    for a, b in kept:
        if a > cur + 1e-3:
            out.append((cur, a))
        cur = max(cur, b)
    if dur > cur + 1e-3:
        out.append((cur, dur))
    return out


if __name__ == "__main__":
    kept, d = kept_segments(sys.argv[1])
    dur = max(m["duration"] for m in d["materials"]["videos"]) / 1e6
    ordem = all(kept[i][0] < kept[i + 1][0] for i in range(len(kept) - 1))
    rem = removed(kept, dur)
    print(f"{len(kept)} trechos mantidos · {sum(b - a for a, b in kept):.1f}s de {dur:.1f}s ({100 * sum(b - a for a, b in kept) / dur:.0f}%) · ordem crescente: {ordem} · {len(rem)} remoções")
    if "--json" in sys.argv:
        json.dump(dict(kept=kept, removed=rem, dur=dur), open(sys.argv[sys.argv.index("--json") + 1], "w"))
