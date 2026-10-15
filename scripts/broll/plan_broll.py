#!/usr/bin/env python3
"""Planeja o B-roll na timeline a partir de broll_analise.json (com `item` e `nota` preenchidos olhando as folhas) + plano.json + transcricao.json.
Uso: python plan_broll.py [--analysis broll_analise.json] [--plan plano.json] [--transcript transcricao.json] [--max-per-item 2] [--tl-max 12]
Regras: B-roll só dentro de itens (depois do menu/cartela); trechos com nota>=3 e sem avisos_visuais; 1 clipe por item (2 se houver trecho bom
e janela >= 30 s; 3 nunca automático); início/fim nos limites de frase da narração; cada clipe >= 3 s NA timeline (já com a aceleração);
sem sobreposição; item sem trecho bom = fica sem B-roll (listado no resumo). Saída: broll_plano.json e linhas `BROLL = [...]` para o plan_data.py.
Campos opcionais por trecho: `melhor_in` (s da fonte onde começar), `velocidade_sugerida` (1/1.5/2)."""

import argparse, bisect, json, sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", "--analise", default="broll_analise.json")
    parser.add_argument("--plan", "--plano", default="plano.json")
    parser.add_argument("--transcript", "--transcricao", default="transcricao.json")
    parser.add_argument("--max-per-item", "--max-por-item", type=int, default=2)
    parser.add_argument("--tl-max", type=float, default=12.0)
    parser.add_argument("--min-score", "--nota-min", type=int, default=3)
    args = parser.parse_args()
    analysis = json.load(open(args.analysis))
    plan = json.load(open(args.plan))
    transcript = json.load(open(args.transcript))
    windows, menu_duration = plan["janelas"], plan.get("menu_duracao", 3.7)
    boundaries = sorted({round(x, 2) for s in transcript["segments"] for x in (s["start"], s["end"])})

    def next_boundary(t):  # primeira fronteira >= t
        i = bisect.bisect_left(boundaries, t)
        return boundaries[i] if i < len(boundaries) and boundaries[i] - t <= 6 else t

    def prev_boundary(t):
        i = bisect.bisect_right(boundaries, t) - 1
        return boundaries[i] if i >= 0 and t - boundaries[i] <= 3 else t

    by_item = {}
    for v in analysis:
        if v.get("tipo") != "video":
            continue
        for t in v["trechos"]:
            if t.get("item") and (t.get("nota") or 0) >= args.min_score and not t.get("avisos_visuais"):
                by_item.setdefault(t["item"], []).append((t["nota"], v, t))
    plan_out, summary, skipped = [], [], []
    for item, (start, end, type) in windows.items():
        if type != "item":
            continue
        lo, hi = start + menu_duration + 0.4, end - 0.4
        candidates = sorted(by_item.get(item, []), key=lambda x: -x[0])
        if hi - lo < 3.5 or not candidates:
            skipped.append((item, "janela curta" if hi - lo < 3.5 else "sem trecho bom (nota>=%d)" % args.min_score))
            continue
        n = min(args.max_per_item, len(candidates), 2 if hi - lo >= 30 else 1)
        used = 0
        cursor = lo
        for k, (score, v, t) in enumerate(candidates[:n]):
            speed = float(t.get("velocidade_sugerida", 1.5))
            span = t["fim"] - t["inicio"]
            free_start = next_boundary(cursor) if k == 0 else next_boundary(max(cursor, lo + (hi - lo) * 0.45))
            if free_start >= hi - 3:
                break
            duration = min(args.tl_max, (span - 0.5) / speed, hi - free_start)
            if duration < 3.0:
                continue
            tl_end = prev_boundary(free_start + duration)
            tl_end = tl_end if tl_end - free_start >= 3.0 else free_start + duration
            duration = tl_end - free_start
            src_in = float(t.get("melhor_in", t["inicio"] + min(1.5, span * 0.2)))
            src_out = src_in + duration * speed
            if src_out > t["fim"] + 0.05:  # recua o início para caber
                src_in = max(t["inicio"], t["fim"] - duration * speed)
                src_out = src_in + duration * speed
            plan_out.append((item, v["arquivo"], round(src_in, 2), round(src_out, 2), speed, round(free_start, 2)))
            summary.append(
                f"{item:14} {free_start:7.1f}s +{duration:4.1f}s  {speed}x  {v['arquivo'].split('/')[-1]} [{src_in:.1f}-{src_out:.1f}] nota {score}"
            )
            cursor = tl_end
            used += 1
        if not used:
            skipped.append((item, "trechos não cabem (>=3 s) na janela"))
    json.dump(
        [
            dict(item=i, arquivo=f, **{"in": a_, "out": b}, velocidade=v, t_inicio=t)
            for i, f, a_, b, v, t in plan_out
        ],
        open("broll_plano.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    with open("broll_plano.py", "w") as f:
        f.write("BROLL = [\n" + "".join(f"    {tuple(p)!r},\n" for p in plan_out) + "]\n")
    print("\n".join(summary))
    print(f"\n{len(plan_out)} clipes em {len({p[0] for p in plan_out})} itens; SEM B-roll: {skipped or 'nenhum'}")
    print("-> broll_plano.json e broll_plano.py (cole BROLL no plano_dados.py e rode plan.py)")


if __name__ == "__main__":
    main()
