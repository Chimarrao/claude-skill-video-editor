#!/usr/bin/env python3
"""TESTE ESTÁTICO do tipo "Webdoc com B-roll" (rode DEPOIS de `python plano.py`, em animacao/). Sai com 1 se alguma regra falhar.
W1 vídeo só em janelas B/V ou nas pausas de ListaCurta (animação e vídeo não disputam a tela)     W2 clipe >= 3 s e velocidade 1.0–2.0
W3 rótulo leve do B: <= 6 s, dentro da janela, curto, só canto esquerdo  W4 ListaCurta: 2–10 itens, rótulo <= 30, eventos espaçados, fim com folga
W5 títulos de impacto: nenhum antes de 30 s e <= 5% do vídeo           W6 sem cena de item/menu/HUD (não é lista)
W7 Tela: imagem existe e a largura exibida <= resolução (sem esticar)  W8 nada de peça fora das 'cenas' do webdoc (sem código)
W9 alternância (aviso): <= 3 cenas de animação seguidas e <= 2 janelas B seguidas sem outra coisa no meio"""

import json, os, re, sys

J = lambda p: json.load(open(p))
cenas = J("src/scenes/cenas.json")
plano = J("plano.json")
jan = plano["janelas"]
broll = J("src/scenes/broll.json") if os.path.exists("src/scenes/broll.json") else []
meta = {e["name"]: e["targetTime"] for e in J("src/scenes/cena1.meta")["timeEvents"]}
dur = plano["duracao"]
erros, ok, avisos = [], [], []


def regra(n, cond, msg):
    (ok if cond else erros).append(f"{n}: {msg}")


if plano.get("tipo_video") != "webdoc_broll":
    avisos.append("plano.json sem tipo_video=webdoc_broll (TIPO_VIDEO no plano_dados.py)")
for b in broll:
    t0, t1 = b["t_inicio"], b["t_fim"]
    janela = next(
        (
            (k, v)
            for k, v in jan.items()
            if v[2] in ("broll", "vazio") and v[0] - 0.05 <= t0 and t1 <= v[1] + 0.06
        ),
        None,
    )
    if janela is None:  # pausas de ListaCurta (a lista some, o B-roll roda, a lista volta)
        janela = next(
            (
                (k, w)
                for k, ws in (plano.get("janelas_video") or {}).items()
                for w in ws
                if w[0] - 0.05 <= t0 and t1 <= w[1] + 0.06
            ),
            None,
        )
    regra(
        "W1",
        janela is not None,
        f"clipe {t0:.1f}-{t1:.1f}s ({os.path.basename(b['arquivo'])[:25]}) dentro de janela B/V"
        + ("" if janela else " — está sobre animação/overlay"),
    )
    regra(
        "W2",
        t1 - t0 >= 2.95 and 1.0 <= b["velocidade"] <= 2.0,
        f"clipe {t0:.1f}s: {t1 - t0:.1f}s a {b['velocidade']}x",
    )
leve = {tuple(x) for x in plano.get("overlay_leve", [])}
for c in cenas:
    i = c["id"]
    if c["tipo"] == "broll" and c.get("dur"):
        v0, v1, _ = jan[i]
        l = next((x for x in leve if v0 - 0.05 <= x[0] and x[1] <= v1 + 0.05), None)
        regra(
            "W3",
            l is not None and (l[1] - l[0]) <= 6.05 and len(c.get("rotulo") or "") <= 40,
            f"[{i}] rótulo leve {l} (<= 6 s, <= 40 caracteres)",
        )
    if c["tipo"] == "listacurta":
        its = c["itens"]
        regra(
            "W4",
            2 <= len(its) <= 10 and all(len(x["rotulo"]) <= 30 for x in its),
            f"[{i}] {len(its)} itens, rótulos <= 30",
        )
        ts = [meta.get(f"{i}-i{k}") for k in range(len(its))]
        regra(
            "W4",
            all(t is not None for t in ts) and all(b - a >= 1.15 for a, b in zip(ts, ts[1:])),
            f"[{i}] itens espaçados >= 1.2 s ({[round(t, 1) for t in ts if t]})",
        )
        out_t = meta.get(f"{i}-out")
        regra(
            "W4",
            out_t is not None and ts[-1] is not None and out_t - ts[-1] >= 1.55,
            (
                f"[{i}] último item {out_t - ts[-1]:.1f}s antes do fim da cena"
                if out_t and ts[-1]
                else f"[{i}] eventos"
            ),
        )
        for j_, (pa, pb) in enumerate(c.get("pausas") or []):
            regra(
                "W4",
                pb - pa >= 3.9 and all(not (pa - 0.3 < t < pb + 0.5) for t in ts if t is not None),
                f"[{i}] pausa {j_} {pa:.1f}-{pb:.1f}s sem item dentro",
            )
        regra(
            "W4",
            c.get("total") == len(its),
            f"[{i}] total consistente (numeração zero à esquerda só acima de 9: total={c.get('total')})",
        )
    if c["tipo"] == "item":
        erros.append(f"W6: [{i}] cena de item/menu (isso é Lista, não Webdoc com B-roll)")
    for p in c.get("pecas", []) or []:
        if p["tipo"] == "codigo":
            erros.append(f"W8: [{i}] janela de código num webdoc")
        if p["tipo"] == "tela":
            nome = p["props"]["img"]
            arq = next(
                (
                    f"src/images/{nome}.{e}"
                    for e in ("png", "jpg", "webp")
                    if os.path.exists(f"src/images/{nome}.{e}")
                ),
                None,
            )
            if arq:
                from PIL import Image

                px = Image.open(arq).size[0]
                regra(
                    "W7",
                    p["props"]["largura"] <= px,
                    f"[{i}] Tela {nome}: largura {p['props']['largura']} <= {px}px do arquivo",
                )
            else:
                erros.append(f"W7: [{i}] imagem {nome} não está em src/images")
imp = [(k, v) for k, v in jan.items() if v[2] == "impacto"]
regra(
    "W5",
    all(v[0] >= 30 for _, v in imp),
    "nenhum título de impacto antes de 30 s"
    + ("" if all(v[0] >= 30 for _, v in imp) else f" ({[k for k, v in imp if v[0] < 30]})"),
)
regra(
    "W5",
    sum(v[1] - v[0] for _, v in imp) <= 0.05 * dur + 0.01,
    f"títulos de impacto {sum(v[1] - v[0] for _, v in imp):.0f}s <= 5% ({0.05 * dur:.0f}s)",
)
tipos = [v[2] for k, v in sorted(jan.items(), key=lambda kv: kv[1][0])]
an = ("grafo", "secao", "tempo", "listacurta")
run = mx = 0
runb = mxb = 0
for t in tipos:
    run = run + 1 if t in an else 0
    mx = max(mx, run)
    runb = runb + 1 if t == "broll" else 0
    mxb = max(mxb, runb)
if mx > 3:
    avisos.append(f"W9: {mx} cenas de animação seguidas (alterne com B-roll)")
if mxb > 2:
    avisos.append(f"W9: {mxb} janelas B seguidas (alterne com animação/lista)")
res = {}
for l in ok + erros:
    res.setdefault(l.split(":")[0], [0, 0])[0 if l in ok else 1] += 1
for k in sorted(res, key=lambda x: int(x[1:])):
    print(f"{k:4s} ok={res[k][0]:3d} falhas={res[k][1]}")
for a in avisos:
    print("AVISO", a)
if erros:
    print("\nFALHAS:")
    [print("  -", e) for e in erros[:40]]
    sys.exit(1)
print("\nOK: todas as regras do Webdoc com B-roll passaram")
