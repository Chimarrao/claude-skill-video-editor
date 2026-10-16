#!/usr/bin/env python3
"""QUALITY GATE 2 (frames reais): extrai quadros do overlay RENDERIZADO, compõe sobre o B-roll/preenchimento como ficará no CapCut,
mede cada quadro e monta folhas de contato para OLHAR antes de entregar.

Roda em animacao/ depois do render (output/project.mov) e do spec_from_plan.py (capcut_spec.json).
Amostras: 1,3 s depois de cada entrada de item (eventos *-g*, *-b*), meio de cada clipe, entrada/saída de cada cena e a cada 20 s.
Verificações automáticas por quadro:
 F1 corte na borda     conteúdo do overlay encostando na borda do quadro (item cortado)
 F2 gigante            componente do overlay > 70% da largura ou > 60% da altura (fora de título/seção)
 F3 zona do avatar     conteúdo > 200 px no canto inferior direito (reservado ao avatar)
 F4 animação sobre clipe  overlay visível (> 0,5%) dentro de um clipe de B-roll (salvo rótulo leve)
 F5 janela vazia       sem overlay e sem clipe onde o plano diz que há animação
 F6 base preta/lisa    clipe de B-roll preto ou sem informação (interface escura COM texto passa; ver frame_rules.py)
 F7 entrada brusca     item que já está 100% visível 0,04 s depois do evento (pop-in sem animação)
 F8 último item        o ÚLTIMO item de cada grafo precisa realmente aparecer (bug do Motion Canvas: filho cancelado quando enter() termina)
Saída: qa/frames/*.png (composites 1280x720), qa/sheet_NN.png (folhas 4x3 com o tempo), qa/gate_frames.json. Sai com 1 se houver ERRO.
AGORA OLHE AS FOLHAS (Read nas PNGs): os números não substituem os olhos — recomece do zero se a edição estiver ruim.
Uso: python gate_frames.py [--overlay output/project.mov] [--spec capcut_spec.json] [--step 20] [--max-frames 400]
"""

import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

cwd = Path.cwd()
ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument("--overlay", default="output/project.mov")
ap.add_argument("--spec", default="capcut_spec.json")
ap.add_argument("--step", type=float, default=20.0)
ap.add_argument("--max-frames", type=int, default=400)
ap.add_argument("--delay", type=float, default=1.3, help="segundos depois do evento para amostrar")
args = ap.parse_args()
W, H = 1920, 1080
OUT = cwd / "qa"
(OUT / "frames").mkdir(parents=True, exist_ok=True)
for f in (OUT / "frames").glob("*.png"):
    f.unlink()
plan = json.load(open(cwd / "plan.json"))
meta = json.load(open(cwd / "src/scenes/scene1.meta"))
scenes = {c["id"]: c for c in json.load(open(cwd / "src/scenes/scenes.json"))}
spec = json.load(open(cwd / args.spec))
clips = sorted(spec.get("clips", []), key=lambda c: c["t_start"])
filler = Path(spec.get("filler") or ROOT / "assets" / "background_filler.mp4")
events = {e["name"]: e["targetTime"] for e in meta["timeEvents"]}
light = [tuple(x) for x in plan.get("overlay_light", [])]


def dur_clip(c):
    return (c["out"] - c["in"]) / c["speed"]


def clip_at(t):
    for c in clips:
        if c["t_start"] <= t < c["t_start"] + dur_clip(c):
            return c
    return None


def ff_frame(path, t, scale=None, rgba=False):
    """Um quadro do arquivo no instante t (s) como imagem PIL."""
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "f.png"
        vf = f"scale={scale}" if scale else "null"
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{max(t, 0):.3f}", "-i", str(path), "-frames:v", "1", "-vf", vf]
        if rgba:
            cmd += ["-pix_fmt", "rgba"]
        subprocess.run(cmd + [str(out)], check=False)
        return Image.open(out).convert("RGBA" if rgba else "RGB").copy() if out.exists() else None


# ---------- instantes de amostra ----------
amostras = {}
for n, t in events.items():
    if re.search(r"-g\d+_|-b\d+$", n):
        amostras[round(t + args.delay, 2)] = f"ev {n}"
    elif n.endswith("-in") or n.endswith("-out"):
        amostras[round(t + (0.8 if n.endswith("-in") else -0.5), 2)] = f"ev {n}"
for c in clips:
    amostras[round(c["t_start"] + dur_clip(c) / 2, 2)] = f"clip {os.path.basename(c['file'])[:24]}"
t = 5.0
while t < plan["duration"]:
    amostras.setdefault(round(t, 2), "regular")
    t += args.step
ts = sorted(x for x in amostras if 0 < x < plan["duration"] - 0.1)
fil = []
for x in ts:  # no máximo 1 amostra a cada 0,8 s
    if not fil or x - fil[-1] >= 0.8:
        fil.append(x)
ts = fil
if len(ts) > args.max_frames:
    passo = len(ts) / args.max_frames
    ts = [ts[int(i * passo)] for i in range(args.max_frames)]
print(f"{len(ts)} quadros para analisar…", flush=True)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_rules import base_vazia, cartela_do_item  # noqa: E402

errors, warns, rows = [], [], []
erro = lambda t, m: errors.append(f"{t:7.1f}s  {m}")
aviso = lambda t, m: warns.append(f"{t:7.1f}s  {m}")
AV = (1680, 840, W, H)  # zona do avatar (px) = AVATAR_ZONE do plan.py (x > 960+720, y > 540+300)


def comps(mask):
    """Maior componente conexa da máscara: (largura da bbox, altura da bbox, fração de área preenchida do quadro)."""
    try:
        import cv2

        m = cv2.resize(mask.astype(np.uint8), (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        n, lab, st, _ = cv2.connectedComponentsWithStats((m > 0).astype(np.uint8), connectivity=8)
        if n <= 1:
            return 0, 0, 0.0
        big = max(range(1, n), key=lambda i: st[i, 4])
        return st[big, 2] * 4, st[big, 3] * 4, st[big, 4] / float(m.shape[0] * m.shape[1])
    except Exception:
        ys, xs = np.where(mask)
        return (xs.max() - xs.min(), ys.max() - ys.min(), float(mask.mean())) if len(xs) else (0, 0, 0.0)


def kind_at(t):
    for i, w in plan["windows"].items():
        if w[0] <= t < w[1] + 0.3:
            return i, w[2]
    return None, None


def cartela_at(t, tipo):
    """Instante dentro da cartela de abertura de um item (F2 não vale ali)."""
    return any(cartela_do_item(t, w, tipo, plan.get("menu_duration", 3.7)) for w in plan["windows"].values() if w[0] <= t < w[1] + 0.3)


for k, t in enumerate(ts):
    ov = ff_frame(args.overlay, t, rgba=True)
    if ov is None:
        aviso(t, "overlay sem quadro neste instante")
        continue
    a = np.asarray(ov)[:, :, 3]
    vis = a > 16
    cover = float(vis.mean())
    cena, tipo = kind_at(t)
    clip = clip_at(t)
    leve = any(x0 <= t <= x1 for x0, x1 in light)
    base = None
    if clip:
        base = ff_frame(clip["file"], clip["in"] + (t - clip["t_start"]) * clip["speed"], scale=f"{W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}")
    elif filler.exists():
        base = ff_frame(filler, t % 18.0, scale=f"{W}:{H}")
    if base is None:
        base = Image.new("RGB", (W, H), (8, 20, 12))
    comp = base.convert("RGBA")
    comp.alpha_composite(ov)
    comp = comp.convert("RGB")
    # F1 borda / F2 gigante / F3 avatar
    if cover > 0.0005:
        ys, xs = np.where(vis)
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        if tipo not in ("impact", "section", "broll") and (x0 < 6 or y0 < 6 or x1 > W - 7 or y1 > H - 7) and cover < 0.6:
            erro(t, f"F1 conteúdo encostando/cortado na borda do quadro (cena {cena}, bbox {x0},{y0}-{x1},{y1})")
        cw, ch, area = comps(vis)
        if tipo not in ("impact", "section", "broll") and area > 0.22 and not cartela_at(t, tipo):
            erro(t, f"F2 componente gigante: um elemento ocupa {area * 100:.0f}% do quadro ({cw}x{ch}px; cena {cena})")
        n_av = int(vis[AV[1] : AV[3], AV[0] : AV[2]].sum())
        if n_av > 200:
            erro(t, f"F3 conteúdo na zona do avatar ({n_av}px; cena {cena})")
    # F4 animação sobre clipe
    if clip and cover > 0.005 and not leve:
        erro(t, f"F4 animação sobre o clipe de B-roll ({cover * 100:.1f}% do quadro; cena {cena})")
    # F5 janela vazia
    life = plan.get("life", {}).get(cena or "", [])
    if not clip and cena and tipo not in ("empty", "broll") and cover < 0.003 and any(a0 + 0.2 <= t <= b0 - 0.2 for a0, b0 in life):
        erro(t, f"F5 janela vazia: o plano diz que há animação em {cena}, mas o quadro está sem overlay")
    # F6 base preta/lisa em clipe
    if clip:
        g = np.asarray(base.convert("L").resize((192, 108)), dtype=np.float32)
        if base_vazia(g):
            erro(t, f"F6 clipe com quadro preto/liso ({os.path.basename(clip['file'])[:30]}, média {g.mean():.0f}, desvio {g.std():.1f})")
    rows.append(dict(t=t, why=amostras.get(t, ""), cover=round(cover, 4), cena=cena, clip=bool(clip)))
    comp.resize((1280, 720)).save(OUT / "frames" / f"f_{t:08.2f}.png")
    if (k + 1) % 25 == 0:
        print(f"  {k + 1}/{len(ts)}", flush=True)

# F7 entrada brusca: item já 100% visível 0,04 s depois do evento do item
pops = 0
amostra_ev = [(n, t) for n, t in events.items() if re.search(r"-g\d+_", n)][:60]
for n, t in amostra_ev:
    o1, o2 = ff_frame(args.overlay, t + 0.04, rgba=True), ff_frame(args.overlay, t + 0.7, rgba=True)
    if o1 is None or o2 is None:
        continue
    a1, a2 = int((np.asarray(o1)[:, :, 3] > 16).sum()), int((np.asarray(o2)[:, :, 3] > 16).sum())
    novo = a2 - int((np.asarray(ff_frame(args.overlay, t - 0.05, rgba=True))[:, :, 3] > 16).sum())
    nov1 = a1 - int((np.asarray(ff_frame(args.overlay, t - 0.05, rgba=True))[:, :, 3] > 16).sum())
    if novo > 3000 and nov1 > 0.8 * novo:
        pops += 1
        aviso(t, f"F7 entrada brusca (pop-in sem animação) em {n}")
if pops > 6:
    erro(0, f"F7 {pops} entradas bruscas (sem animação de entrada)")

# F8: o último item de cada grafo aparece de verdade? (compara a área do overlay antes e depois do evento do último item)
def ultimos_eventos():
    for sid, c in scenes.items():
        if c["kind"] == "graph":
            beats = [i.get("beat") for i in c["items"] if i.get("beat")]
            if len(beats) >= 2 and f"{sid}-{beats[-1]}" in events:
                yield sid, events[f"{sid}-{beats[-1]}"], plan["windows"].get(sid, [0, 0])[1]
        for p in c.get("pieces", []):
            if p["kind"] == "graph":
                evs = [e for e in (p["props"].get("events") or []) if e]
                if len(evs) >= 2 and evs[-1] in events:
                    yield sid + "/graph", events[evs[-1]], plan["windows"].get(sid, [0, 0])[1]


falta = 0
for sid, te, fim in ultimos_eventos():
    if te + 1.2 > fim or clip_at(te + 1.2) or clip_at(te):
        continue
    o1, o2 = ff_frame(args.overlay, te - 0.15, rgba=True), ff_frame(args.overlay, te + 1.2, rgba=True)
    if o1 is None or o2 is None:
        continue
    a1, a2 = int((np.asarray(o1)[:, :, 3] > 16).sum()), int((np.asarray(o2)[:, :, 3] > 16).sum())
    if a2 - a1 < 600:
        falta += 1
        erro(te, f"F8 o último item de {sid} não apareceu (área do overlay {a1}→{a2}px): item/seta cancelados")
print(f"F8: {falta} grafos com último item ausente")

# folhas de contato
fr = sorted((OUT / "frames").glob("f_*.png"))
for f in OUT.glob("sheet_*.png"):
    f.unlink()
for s0 in range(0, len(fr), 12):
    grupo = fr[s0 : s0 + 12]
    sheet = Image.new("RGB", (3 * 640, 4 * 360), (20, 20, 20))
    for i, f in enumerate(grupo):
        im = Image.open(f).resize((640, 360))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 118, 22], fill=(0, 0, 0))
        d.text((6, 5), f.stem[2:].lstrip("0") + "s", fill=(255, 255, 0))
        d.rectangle([AV[0] / 3, AV[1] / 3, W / 3 - 1, H / 3 - 1], outline=(255, 60, 60))
        sheet.paste(im, ((i % 3) * 640, (i // 3) * 360))
    sheet.save(OUT / f"sheet_{s0 // 12:02d}.png")
json.dump(dict(errors=errors, warnings=warns, frames=rows), open(OUT / "gate_frames.json", "w"), ensure_ascii=False, indent=1)
for w in warns[:60]:
    print("AVISO ", w)
for e in errors[:120]:
    print("ERRO  ", e)
print(f"\nGATE 2 (frames): {'FALHOU' if errors else 'OK'} — {len(errors)} erro(s), {len(warns)} aviso(s) em {len(rows)} quadros; folhas: {OUT}/sheet_*.png")
sys.exit(1 if errors else 0)
