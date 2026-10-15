#!/usr/bin/env python3
"""TESTE: os rótulos das peças batem com a FALA? (lição do "faltou 'instabilidade'": o roteiro enumera 5 critérios e a animação mostrava 4.)
Rode em animacao/ depois de plan.py. Para cada Stat/Fatos/Grafo (scenes.json) pega o tempo do evento (scene1.meta) e confere se alguma palavra
significativa (>= 6 letras, sem acento) do rótulo aparece na transcrição em [t-4, t+12 s]. Também mostra, para cada Grafo/peça, a frase falada na janela
para você conferir ENUMERAÇÕES ("A, B, C e D"): compare a quantidade de itens do rótulo com a quantidade de itens falados.
Sai 0 sempre (WARNINGS) a menos que --strict."""

import json, os, re, sys, unicodedata

argv = sys.argv[1:]
strict = "--strict" in argv or "--estrito" in argv
normalize = lambda s: re.sub(
    r"[^a-z0-9]", "", unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
)
transcript = json.load(open("transcription.json"))
words_index = [(normalize(w["word"]), w["start"]) for s in transcript["segments"] for w in s.get("words", [])]
meta = {e["name"]: e["targetTime"] for e in json.load(open("src/scenes/scene1.meta"))["timeEvents"]}
scenes = json.load(open("src/scenes/scenes.json"))
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
    for piece in scene.get("pieces", []) or []:
        t = meta.get(f"{scene_id}-{piece['beat']}") if piece.get("beat") else None
        props = piece["props"]
        if piece["kind"] == "stat":
            check(scene_id, f"{props['value']} {props['label']}", t, "stat")
        elif piece["kind"] == "facts":
            for row in props["lines"]:
                check(scene_id, row["text"], t, "fact")
        elif piece["kind"] == "graph":
            for idx, item in enumerate(props["items"]):
                if item.get("label"):
                    event = (props.get("events") or [None] * 99)[idx]
                    check(scene_id, item["label"], meta.get(event) if event else t, "graph")
    if scene["kind"] == "graph":
        for idx, item in enumerate(scene["items"]):
            if item.get("label"):
                event = meta.get(f"{scene_id}-b{idx}") or meta.get(f"{scene_id}-in")
                check(scene_id, item["label"], event, "graph")
print(f"{len(rows)} rótulos conferidos, {len(warnings)} sem correspondência na fala")
for warning in warnings:
    print("WARNING", warning)
sys.exit(1 if (warnings and strict) else 0)
