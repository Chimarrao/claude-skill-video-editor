#!/usr/bin/env python3
"""Planeja o B-roll na timeline a partir de broll_analise.json (com `item` e `nota` preenchidos olhando as folhas) + plano.json + transcricao.json.
Uso: python planejar_broll.py [--analise broll_analise.json] [--plano plano.json] [--transcricao transcricao.json] [--max-por-item 2] [--tl-max 12]
Regras: B-roll só dentro de itens (depois do menu/cartela); trechos com nota>=3 e sem avisos_visuais; 1 clipe por item (2 se houver trecho bom
e janela >= 30 s; 3 nunca automático); início/fim nos limites de frase da narração; cada clipe >= 3 s NA timeline (já com a aceleração);
sem sobreposição; item sem trecho bom = fica sem B-roll (listado no resumo). Saída: broll_plano.json e linhas `BROLL = [...]` para o plano_dados.py.
Campos opcionais por trecho: `melhor_in` (s da fonte onde começar), `velocidade_sugerida` (1/1.5/2)."""

import argparse, bisect, json, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analise", default="broll_analise.json")
    ap.add_argument("--plano", default="plano.json")
    ap.add_argument("--transcricao", default="transcricao.json")
    ap.add_argument("--max-por-item", type=int, default=2)
    ap.add_argument("--tl-max", type=float, default=12.0)
    ap.add_argument("--nota-min", type=int, default=3)
    a = ap.parse_args()
    an = json.load(open(a.analise))
    pl = json.load(open(a.plano))
    tr = json.load(open(a.transcricao))
    janelas, menu = pl["janelas"], pl.get("menu_duracao", 3.7)
    fronteiras = sorted({round(x, 2) for s in tr["segments"] for x in (s["start"], s["end"])})

    def prox(t):  # primeira fronteira >= t
        i = bisect.bisect_left(fronteiras, t)
        return fronteiras[i] if i < len(fronteiras) and fronteiras[i] - t <= 6 else t

    def ant(t):
        i = bisect.bisect_right(fronteiras, t) - 1
        return fronteiras[i] if i >= 0 and t - fronteiras[i] <= 3 else t

    por_item = {}
    for v in an:
        if v.get("tipo") != "video":
            continue
        for t in v["trechos"]:
            if t.get("item") and (t.get("nota") or 0) >= a.nota_min and not t.get("avisos_visuais"):
                por_item.setdefault(t["item"], []).append((t["nota"], v, t))
    plano, resumo, sem = [], [], []
    for item, (ini, fim, tipo) in janelas.items():
        if tipo != "item":
            continue
        lo, hi = ini + menu + 0.4, fim - 0.4
        cands = sorted(por_item.get(item, []), key=lambda x: -x[0])
        if hi - lo < 3.5 or not cands:
            sem.append((item, "janela curta" if hi - lo < 3.5 else "sem trecho bom (nota>=%d)" % a.nota_min))
            continue
        n = min(a.max_por_item, len(cands), 2 if hi - lo >= 30 else 1)
        usados = 0
        cursor = lo
        for k, (nota, v, t) in enumerate(cands[:n]):
            vel = float(t.get("velocidade_sugerida", 1.5))
            span = t["fim"] - t["inicio"]
            livre_ini = prox(cursor) if k == 0 else prox(max(cursor, lo + (hi - lo) * 0.45))
            if livre_ini >= hi - 3:
                break
            D = min(a.tl_max, (span - 0.5) / vel, hi - livre_ini)
            if D < 3.0:
                continue
            fim_tl = ant(livre_ini + D)
            fim_tl = fim_tl if fim_tl - livre_ini >= 3.0 else livre_ini + D
            D = fim_tl - livre_ini
            in_src = float(t.get("melhor_in", t["inicio"] + min(1.5, span * 0.2)))
            out_src = in_src + D * vel
            if out_src > t["fim"] + 0.05:  # recua o início para caber
                in_src = max(t["inicio"], t["fim"] - D * vel)
                out_src = in_src + D * vel
            plano.append((item, v["arquivo"], round(in_src, 2), round(out_src, 2), vel, round(livre_ini, 2)))
            resumo.append(
                f"{item:14} {livre_ini:7.1f}s +{D:4.1f}s  {vel}x  {v['arquivo'].split('/')[-1]} [{in_src:.1f}-{out_src:.1f}] nota {nota}"
            )
            cursor = fim_tl
            usados += 1
        if not usados:
            sem.append((item, "trechos não cabem (>=3 s) na janela"))
    json.dump(
        [
            dict(item=i, arquivo=f, **{"in": a_, "out": b}, velocidade=v, t_inicio=t)
            for i, f, a_, b, v, t in plano
        ],
        open("broll_plano.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    with open("broll_plano.py", "w") as f:
        f.write("BROLL = [\n" + "".join(f"    {tuple(p)!r},\n" for p in plano) + "]\n")
    print("\n".join(resumo))
    print(f"\n{len(plano)} clipes em {len({p[0] for p in plano})} itens; SEM B-roll: {sem or 'nenhum'}")
    print("-> broll_plano.json e broll_plano.py (cole BROLL no plano_dados.py e rode plano.py)")


if __name__ == "__main__":
    main()
