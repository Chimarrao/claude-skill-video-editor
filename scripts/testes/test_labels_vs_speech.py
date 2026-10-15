#!/usr/bin/env python3
"""TESTE: os rótulos das peças batem com a FALA? (lição do "faltou 'instabilidade'": o roteiro enumera 5 critérios e a animação mostrava 4.)
Rode em animacao/ depois de plan.py. Para cada Stat/Fatos/Grafo (cenas.json) pega o tempo do evento (cena1.meta) e confere se alguma palavra
significativa (>= 6 letras, sem acento) do rótulo aparece na transcrição em [t-4, t+12 s]. Também mostra, para cada Grafo/peça, a frase falada na janela
para você conferir ENUMERAÇÕES ("A, B, C e D"): compare a quantidade de itens do rótulo com a quantidade de itens falados.
Sai 0 sempre (AVISOS) a menos que --strict."""

import json, os, re, sys, unicodedata

argv = sys.argv[1:]
strict = "--strict" in argv or "--estrito" in argv
normalize = lambda s: re.sub(
    r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
)
transcript = json.load(open("transcricao.json"))
words_index = [(normalize(w["word"]), w["start"]) for s in transcript["segments"] for w in s.get("words", [])]
meta = {e["name"]: e["targetTime"] for e in json.load(open("src/scenes/cena1.meta"))["timeEvents"]}
scenes = json.load(open("src/scenes/cenas.json"))
warnings = []
rows = []


def words(text):
    return [normalize(x) for x in re.findall(r"[A-Za-zÀ-ú0-9]{6,}", text)]


def speech(t0, t1):
    return " ".join(w for w, t in words_index if t0 <= t <= t1)


def sentence(t0, t1):
    return " ".join(
        w["word"].strip() for s in transcript["segments"] for w in s.get("words", []) if t0 <= w["start"] <= t1
    )


def check(scene_id, label, t, where):
    if t is None:
        return
    label_words = [p for p in words(label)]
    if not label_words:
        return
    window = speech(t - 4, t + 12)
    match = any(p[:6] in window or window.find(p[:5]) >= 0 for p in label_words)
    rows.append((scene_id, where, round(t, 1), label, match))
    if not match:
        warnings.append(
            f"[{scene_id}] {where} '{label}' em {t:.1f}s: nenhuma palavra do rótulo aparece na fala ({t - 4:.0f}-{t + 12:.0f}s): \"{sentence(t - 1, t + 8)[:110]}\""
        )


for scene in scenes:
    scene_id = scene["id"]
    for piece in scene.get("pecas", []) or []:
        t = meta.get(f"{scene_id}-{piece['beat']}") if piece.get("beat") else None
        props = piece["props"]
        if piece["tipo"] == "stat":
            check(scene_id, f"{props['valor']} {props['rotulo']}", t, "stat")
        elif piece["tipo"] == "fatos":
            for row in props["linhas"]:
                check(scene_id, row["texto"], t, "fato")
        elif piece["tipo"] == "grafo":
            for idx, item in enumerate(props["itens"]):
                if item.get("rotulo"):
                    event = (props.get("eventos") or [None] * 99)[idx]
                    check(scene_id, item["rotulo"], meta.get(event) if event else t, "grafo")
    if scene["tipo"] == "grafo":
        for idx, item in enumerate(scene["itens"]):
            if item.get("rotulo"):
                event = meta.get(f"{scene_id}-b{idx}") or meta.get(f"{scene_id}-in")
                check(scene_id, item["rotulo"], event, "grafo")
print(f"{len(rows)} rótulos conferidos, {len(warnings)} sem correspondência na fala")
for warning in warnings:
    print("AVISO", warning)
sys.exit(1 if (warnings and strict) else 0)
