#!/usr/bin/env python3
"""TESTE ESTÁTICO do tipo "Webdoc com B-roll" (rode DEPOIS de `python plan.py`, em animacao/). Sai com 1 se alguma regra falhar.
W1 vídeo só em janelas B/V ou nas pausas de ShortList (animação e vídeo não disputam a tela)     W2 clipe >= 3 s e velocidade 1.0–2.0
W3 rótulo leve do B: <= 6 s, dentro da janela, curto, só canto esquerdo  W4 ShortList: 2–10 itens, rótulo <= 30, eventos espaçados, fim com folga
W5 títulos de impacto: nenhum antes de 30 s e <= 5% do vídeo           W6 sem cena de item/menu/HUD (não é lista)
W7 Tela: imagem existe e a largura exibida <= resolução (sem esticar)  W8 nada de peça fora das 'cenas' do webdoc (sem código)
W9 alternância (aviso): <= 3 cenas de animação seguidas e <= 2 janelas B seguidas sem outra coisa no meio"""

import json, os, re, sys

load_json = lambda p: json.load(open(p))
scenes = load_json("src/scenes/scenes.json")
plan = load_json("plan.json")
windows = plan["windows"]
broll = load_json("src/scenes/broll.json") if os.path.exists("src/scenes/broll.json") else []
meta = {e["name"]: e["targetTime"] for e in load_json("src/scenes/scene1.meta")["timeEvents"]}
duration = plan["duration"]
errors, passed, warnings = [], [], []


def rule(rule_id, condition, msg):
    """Registra o resultado de uma regra (passou ou falhou) com a mensagem."""
    (passed if condition else errors).append(f"{rule_id}: {msg}")


if plan.get("video_kind") != "webdoc_broll":
    warnings.append("plan.json sem video_kind=webdoc_broll (VIDEO_KIND no plan_data.py)")
for b in broll:
    t0, t1 = b["t_start"], b["t_end"]
    window = next(
        (
            (k, v)
            for k, v in windows.items()
            if v[2] in ("broll", "empty") and v[0] - 0.05 <= t0 and t1 <= v[1] + 0.06
        ),
        None,
    )
    if window is None:  # pausas de ShortList (a lista some, o B-roll roda, a lista volta)
        window = next(
            (
                (k, w)
                for k, ws in (plan.get("windows_video") or {}).items()
                for w in ws
                if w[0] - 0.05 <= t0 and t1 <= w[1] + 0.06
            ),
            None,
        )
    rule(
        "W1",
        window is not None,
        f"clipe {t0:.1f}-{t1:.1f}s ({os.path.basename(b['file'])[:25]}) dentro de janela B/V"
        + ("" if window else " — está sobre animação/overlay"),
    )
    rule(
        "W2",
        t1 - t0 >= 2.95 and 1.0 <= b["speed"] <= 2.0,
        f"clipe {t0:.1f}s: {t1 - t0:.1f}s a {b['speed']}x",
    )
light_overlay = {tuple(x) for x in plan.get("overlay_light", [])}
for c in scenes:
    scene_id = c["id"]
    if c["kind"] == "broll" and c.get("dur"):
        v0, v1, _ = windows[scene_id]
        light = next((x for x in light_overlay if v0 - 0.05 <= x[0] and x[1] <= v1 + 0.05), None)
        rule(
            "W3",
            light is not None and (light[1] - light[0]) <= 6.05 and len(c.get("label") or "") <= 40,
            f"[{scene_id}] rótulo leve {light} (<= 6 s, <= 40 caracteres)",
        )
    if c["kind"] == "shortlist":
        items = c["items"]
        rule(
            "W4",
            2 <= len(items) <= 10 and all(len(x["label"]) <= 30 for x in items),
            f"[{scene_id}] {len(items)} itens, rótulos <= 30",
        )
        times = [meta.get(f"{scene_id}-i{k}") for k in range(len(items))]
        rule(
            "W4",
            all(t is not None for t in times) and all(b - a >= 1.15 for a, b in zip(times, times[1:])),
            f"[{scene_id}] itens espaçados >= 1.2 s ({[round(t, 1) for t in times if t]})",
        )
        out_time = meta.get(f"{scene_id}-out")
        rule(
            "W4",
            out_time is not None and times[-1] is not None and out_time - times[-1] >= 1.55,
            (
                f"[{scene_id}] último item {out_time - times[-1]:.1f}s antes do fim da cena"
                if out_time and times[-1]
                else f"[{scene_id}] eventos"
            ),
        )
        for pause_idx, (pause_start, pause_end) in enumerate(c.get("pauses") or []):
            rule(
                "W4",
                pause_end - pause_start >= 3.9 and all(not (pause_start - 0.3 < t < pause_end + 0.5) for t in times if t is not None),
                f"[{scene_id}] pausa {pause_idx} {pause_start:.1f}-{pause_end:.1f}s sem item dentro",
            )
        rule(
            "W4",
            c.get("total") == len(items),
            f"[{scene_id}] total consistente (numeração zero à esquerda só acima de 9: total={c.get('total')})",
        )
    if c["kind"] == "item":
        errors.append(f"W6: [{scene_id}] cena de item/menu (isso é Lista, não Webdoc com B-roll)")
    for p in c.get("pieces", []) or []:
        if p["kind"] == "code":
            errors.append(f"W8: [{scene_id}] janela de código num webdoc")
        if p["kind"] == "screen":
            name = p["props"]["img"]
            file = next(
                (
                    f"src/images/{name}.{e}"
                    for e in ("png", "jpg", "webp")
                    if os.path.exists(f"src/images/{name}.{e}")
                ),
                None,
            )
            if file:
                from PIL import Image

                px = Image.open(file).size[0]
                rule(
                    "W7",
                    p["props"]["width"] <= px,
                    f"[{scene_id}] Tela {name}: largura {p['props']['width']} <= {px}px do arquivo",
                )
            else:
                errors.append(f"W7: [{scene_id}] imagem {name} não está em src/images")
impacts = [(k, v) for k, v in windows.items() if v[2] == "impact"]
rule(
    "W5",
    all(v[0] >= 30 for _, v in impacts),
    "nenhum título de impacto antes de 30 s"
    + ("" if all(v[0] >= 30 for _, v in impacts) else f" ({[k for k, v in impacts if v[0] < 30]})"),
)
rule(
    "W5",
    sum(v[1] - v[0] for _, v in impacts) <= 0.05 * duration + 0.01,
    f"títulos de impacto {sum(v[1] - v[0] for _, v in impacts):.0f}s <= 5% ({0.05 * duration:.0f}s)",
)
types = [v[2] for k, v in sorted(windows.items(), key=lambda kv: kv[1][0])]
anim_types = ("graph", "section", "timeline", "shortlist")
run = max_run = 0
run_b = max_b = 0
for t in types:
    run = run + 1 if t in anim_types else 0
    max_run = max(max_run, run)
    run_b = run_b + 1 if t == "broll" else 0
    max_b = max(max_b, run_b)
if max_run > 3:
    warnings.append(f"W9: {max_run} cenas de animação seguidas (alterne com B-roll)")
if max_b > 2:
    warnings.append(f"W9: {max_b} janelas B seguidas (alterne com animação/lista)")
results = {}
for line in passed + errors:
    results.setdefault(line.split(":")[0], [0, 0])[0 if line in passed else 1] += 1
for key in sorted(results, key=lambda x: int(x[1:])):
    print(f"{key:4s} ok={results[key][0]:3d} falhas={results[key][1]}")
for warning in warnings:
    print("WARNING", warning)
if errors:
    print("\nFALHAS:")
    [print("  -", e) for e in errors[:40]]
    sys.exit(1)
print("\nOK: todas as regras do Webdoc com B-roll passaram")
