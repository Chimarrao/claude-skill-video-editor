#!/usr/bin/env python3
"""TESTE: os rótulos das peças batem com a FALA? (lição do "faltou 'instabilidade'": o roteiro enumera 5 critérios e a animação mostrava 4.)
Rode em animacao/ depois de plano.py. Para cada Stat/Fatos/Grafo (cenas.json) pega o tempo do evento (cena1.meta) e confere se alguma palavra
significativa (>= 6 letras, sem acento) do rótulo aparece na transcrição em [t-4, t+12 s]. Também mostra, para cada Grafo/peça, a frase falada na janela
para você conferir ENUMERAÇÕES ("A, B, C e D"): compare a quantidade de itens do rótulo com a quantidade de itens falados.
Sai 0 sempre (AVISOS) a menos que --estrito."""

import json, os, re, sys, unicodedata

ap = sys.argv[1:]
estrito = "--estrito" in ap
norm = lambda s: re.sub(
    r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
)
T = json.load(open("transcricao.json"))
W = [(norm(w["word"]), w["start"]) for s in T["segments"] for w in s.get("words", [])]
meta = {e["name"]: e["targetTime"] for e in json.load(open("src/scenes/cena1.meta"))["timeEvents"]}
cenas = json.load(open("src/scenes/cenas.json"))
avisos = []
linhas = []


def palavras(txt):
    return [norm(x) for x in re.findall(r"[A-Za-zÀ-ú0-9]{6,}", txt)]


def fala(t0, t1):
    return " ".join(w for w, t in W if t0 <= t <= t1)


def frase(t0, t1):
    return " ".join(
        w["word"].strip() for s in T["segments"] for w in s.get("words", []) if t0 <= w["start"] <= t1
    )


def checar(cid, rot, t, onde):
    if t is None:
        return
    ps = [p for p in palavras(rot)]
    if not ps:
        return
    janela = fala(t - 4, t + 12)
    ok = any(p[:6] in janela or janela.find(p[:5]) >= 0 for p in ps)
    linhas.append((cid, onde, round(t, 1), rot, ok))
    if not ok:
        avisos.append(
            f"[{cid}] {onde} '{rot}' em {t:.1f}s: nenhuma palavra do rótulo aparece na fala ({t - 4:.0f}-{t + 12:.0f}s): \"{frase(t - 1, t + 8)[:110]}\""
        )


for c in cenas:
    cid = c["id"]
    for p in c.get("pecas", []) or []:
        t = meta.get(f"{cid}-{p['beat']}") if p.get("beat") else None
        pr = p["props"]
        if p["tipo"] == "stat":
            checar(cid, f"{pr['valor']} {pr['rotulo']}", t, "stat")
        elif p["tipo"] == "fatos":
            for l in pr["linhas"]:
                checar(cid, l["texto"], t, "fato")
        elif p["tipo"] == "grafo":
            for k, it in enumerate(pr["itens"]):
                if it.get("rotulo"):
                    ev = (pr.get("eventos") or [None] * 99)[k]
                    checar(cid, it["rotulo"], meta.get(ev) if ev else t, "grafo")
    if c["tipo"] == "grafo":
        for k, it in enumerate(c["itens"]):
            if it.get("rotulo"):
                ev = meta.get(f"{cid}-b{k}") or meta.get(f"{cid}-in")
                checar(cid, it["rotulo"], ev, "grafo")
print(f"{len(linhas)} rótulos conferidos, {len(avisos)} sem correspondência na fala")
for a in avisos:
    print("AVISO", a)
sys.exit(1 if (avisos and estrito) else 0)
