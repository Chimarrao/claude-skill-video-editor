#!/usr/bin/env python3
"""Lê (SEM EDITAR) o draft do CapCut depois que o usuário mexeu e compara com o que o skill gerou (capcut_spec.json).
Objetivo: aprender o gosto do usuário — o que ele CORTOU (animações removidas), ESTICOU (B-roll estendido/lentidão), TROCOU (outra fonte),
ACRESCENTOU (logos/fotos/vídeos novos, posição/escala), AMPLIOU (zoom no overlay) — para refinar regras e planos futuros.
Uso:  python analisar_edicao_usuario.py <pasta_do_draft | draft_info.json> [--spec animacao/capcut_spec.json] [--md saida.md] [--json saida.json]
Dica: copie o draft para /tmp antes (o CapCut regrava os arquivos); o script só abre arquivos para leitura.
Tempo: tudo é convertido para o TEMPO ORIGINAL do plano (descontando vinhetas/inserções do usuário) usando os trechos da narração.
"""

import argparse, json, os, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("draft")
ap.add_argument("--spec", default="capcut_spec.json")
ap.add_argument("--md")
ap.add_argument("--json")
a = ap.parse_args()
p = Path(a.draft)
p = p / "draft_info.json" if p.is_dir() else p
j = json.load(open(p))
spec = json.load(open(a.spec)) if os.path.exists(a.spec) else {}
S = lambda us: us / 1e6
mats = {m["id"]: m for k in ("videos", "audios") for m in j["materials"].get(k, [])}
base = (
    lambda m: os.path.basename((m.get("path") or "").replace("\\", "/"))
    or m.get("material_name")
    or m.get("name")
    or "?"
)
tracks = [(t.get("name") or "", t["type"], t["segments"]) for t in j["tracks"]]
# --- mapa de tempo usuário -> original, pela narração (voz_narracao.wav) ---
voz = [
    (
        S(s["target_timerange"]["start"]),
        S(s["target_timerange"]["start"] + s["target_timerange"]["duration"]),
        S(s["source_timerange"]["start"]),
    )
    for n, ty, segs in tracks
    if ty == "audio"
    for s in segs
    if "voz_narracao" in base(mats.get(s["material_id"], {}))
]
voz.sort()


def orig(t):
    for t0, t1, s0 in voz:
        if t0 - 1e-3 <= t <= t1 + 1e-3:
            return round(s0 + (t - t0), 3)
    return None


ins = []  # inserções do usuário (vãos entre trechos da narração)
for (a0, a1, s0), (b0, b1, s1) in zip(voz, voz[1:]):
    if b0 - a1 > 0.5 or abs((b0 - s1) - (a0 - s0)) > 0.5:
        ins.append(
            dict(
                no_tempo_do_usuario=[round(a1, 2), round(b0, 2)],
                duracao=round(b0 - a1, 2),
                narracao_pulada=round(s1 - (s0 + a1 - a0), 2),
            )
        )
clip_esp = {}  # (arquivo, in, out) planejados
for c in spec.get("clipes", []):
    clip_esp.setdefault(os.path.basename(c["arquivo"]), []).append(c)
rel = dict(
    insercoes=ins,
    clipes=[],
    logos_fotos=[],
    overlay_mantido=[],
    overlay_removido=[],
    overlay_zoom=[],
    faixas_extras=[],
    videos_novos=[],
)
for nome, ty, segs in tracks:
    if ty != "video":
        if nome not in ("narracao", "") or len(segs):
            rel["faixas_extras"].append(
                dict(
                    tipo=ty,
                    nome=nome,
                    segmentos=len(segs),
                    arquivos=sorted({base(mats.get(s["material_id"], {})) for s in segs})[:4],
                )
            )
        continue
    for s in segs:
        m = mats.get(s["material_id"], {})
        b = base(m)
        t0 = S(s["target_timerange"]["start"])
        d = S(s["target_timerange"]["duration"])
        o0 = orig(t0)
        o1 = orig(t0 + d - 1e-3)
        clp = s.get("clip") or {}
        esc = (clp.get("scale") or {}).get("x")
        tx = clp.get("transform") or {}
        sr = s.get("source_timerange") or {}
        sp = s.get("speed")
        if nome == "overlay" or "project.mov" in b:
            ini = S(sr.get("start", 0))
            rel["overlay_mantido"].append([round(ini, 2), round(ini + d, 2)])
            if esc and abs(esc - 1) > 0.02:
                rel["overlay_zoom"].append(
                    dict(
                        overlay=[round(ini, 2), round(ini + d, 2)],
                        escala=round(esc, 2),
                        pos=[round(tx.get("x", 0), 3), round(tx.get("y", 0), 3)],
                    )
                )
            continue
        if nome == "preenchimento" or "fundo_preench" in b:
            continue
        if m.get("type") == "photo" or b.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".svg")):
            rel["logos_fotos"].append(
                dict(
                    arquivo=b,
                    tempo_original=[o0, o1] if o0 is not None else None,
                    duracao=round(d, 2),
                    escala=round(esc or 1, 3),
                    pos=[round(tx.get("x", 0), 3), round(tx.get("y", 0), 3)],
                )
            )
            continue
        if b.startswith("Minhas ") or "predefini" in b or o0 is None:
            rel["faixas_extras"].append(
                dict(
                    tipo="video",
                    nome=nome or "(sem nome)",
                    arquivo=b,
                    no_tempo_do_usuario=[round(t0, 1), round(t0 + d, 1)],
                    escala=round(esc or 1, 2),
                    pos=[round(tx.get("x", 0), 2), round(tx.get("y", 0), 2)],
                )
            )
            continue
        esp = clip_esp.get(b, [])
        achou = next((c for c in esp if abs(c["in"] - S(sr.get("start", 0))) < 0.6), None)
        if not esp:
            rel["videos_novos"].append(
                dict(
                    arquivo=b,
                    tempo_original=[o0, round(o0 + d, 2)],
                    fonte=[
                        round(S(sr.get("start", 0)), 1),
                        round(S(sr.get("start", 0) + sr.get("duration", 0)), 1),
                    ],
                    velocidade=round(sp or 1, 2),
                )
            )
            continue
        rel["clipes"].append(
            dict(
                arquivo=b,
                tempo_original=[o0, round(o0 + d, 2)],
                fonte=[
                    round(S(sr.get("start", 0)), 2),
                    round(S(sr.get("start", 0) + sr.get("duration", 0)), 2),
                ],
                velocidade=round(sp or 1, 2),
                planejado=(
                    dict(
                        t=[
                            round(achou["t_inicio"], 1),
                            round(achou["t_inicio"] + (achou["out"] - achou["in"]) / achou["velocidade"], 1),
                        ],
                        vel=achou["velocidade"],
                    )
                    if achou
                    else None
                ),
                mudanca=(
                    "igual"
                    if achou
                    and abs(d - (achou["out"] - achou["in"]) / achou["velocidade"]) < 0.3
                    and abs((sp or 1) - achou["velocidade"]) < 0.05
                    else ("ESTICADO/ENCURTADO" if achou else "TROCA DE TRECHO/NOVO")
                ),
            )
        )
rel["overlay_mantido"].sort()
cur = 0.0
dur_ov = max((x[1] for x in rel["overlay_mantido"]), default=0)
for x0, x1 in rel["overlay_mantido"]:
    if x0 - cur > 0.3:
        rel["overlay_removido"].append([round(cur, 2), round(x0, 2)])
    cur = max(cur, x1)
# overlay_removido que o spec já deixava sem overlay (janelas de clipe) não é "corte do usuário": filtra pelos segmentos planejados
plan = spec.get("overlay_segmentos")
if plan:
    rem = []
    for x0, x1 in rel["overlay_removido"]:
        for p0, p1 in plan:  # só o que cai em janela que EXISTIA no plano
            lo, hi = max(x0, p0), min(x1, p1)
            if hi - lo > 0.3:
                rem.append([round(lo, 2), round(hi, 2)])
    rel["overlay_removido_vs_plano"] = rem
# --- relatório ---
L = [
    f"# Edição do usuário — {j.get('name')}",
    "",
    (
        f"- duração no CapCut: {S(j['duration']):.1f}s · narração planejada: {spec.get('janelas') and max(v[1] for v in spec['janelas'].values()):.1f}s"
        if spec.get("janelas")
        else f"- duração no CapCut: {S(j['duration']):.1f}s"
    ),
]
for i_ in ins:
    L.append(
        f"- INSERÇÃO do usuário em {i_['no_tempo_do_usuario']} ({i_['duracao']}s; narração pulada {i_['narracao_pulada']}s) — todos os tempos abaixo já descontam isso"
    )
L += ["", "## Overlay (animações) — CORTADO pelo usuário (tempo original)", ""]
for x in rel.get("overlay_removido_vs_plano", rel["overlay_removido"]):
    jn = next((k for k, v in (spec.get("janelas") or {}).items() if v[0] <= x[0] < v[1]), "")
    L.append(f"- {x[0]}–{x[1]}s ({x[1]-x[0]:.1f}s) {jn}")
L += ["", "## Overlay AMPLIADO (zoom manual)", ""] + [
    f"- {z['overlay']} escala {z['escala']}× pos {z['pos']}" for z in rel["overlay_zoom"]
]
L += ["", "## Logos/fotos que o usuário acrescentou na trilha de clipes", ""] + [
    f"- {l['arquivo']} em {l['tempo_original']} ({l['duracao']}s) escala {l['escala']} pos {l['pos']}"
    for l in rel["logos_fotos"]
]
L += ["", "## B-roll alterado", ""] + [
    f"- {c['mudanca']}: {c['arquivo'][:50]} {c['tempo_original']} fonte {c['fonte']} {c['velocidade']}x"
    + (f" (plano {c['planejado']['t']} {c['planejado']['vel']}x)" if c["planejado"] else "")
    for c in rel["clipes"]
    if c["mudanca"] != "igual"
]
L += ["", "## Vídeos novos (fora do plano)", ""] + [
    f"- {v['arquivo']} em {v['tempo_original']} fonte {v['fonte']} {v['velocidade']}x"
    for v in rel["videos_novos"]
]
L += ["", "## Faixas/vinhetas extras do usuário", ""] + [f"- {f}" for f in rel["faixas_extras"]]
md = "\n".join(L)
if a.md:
    open(a.md, "w").write(md)
if a.json:
    json.dump(rel, open(a.json, "w"), ensure_ascii=False, indent=1)
print(md)
