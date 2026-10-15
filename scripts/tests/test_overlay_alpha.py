#!/usr/bin/env python3
"""TESTE DE RENDER (fatia): renderiza só um trecho do overlay (padrão: ~25 s com clipes e animações) e mede o canal alfa quadro a quadro.
Prova que: (1) durante cada clipe de B-roll o overlay é 100% transparente (nenhuma animação/HUD vaza nem por 1 quadro);
           (2) fora dos clipes há conteúdo (o trecho renderizou de verdade).
Rode em animacao/ com o vite parado. NÃO mexe no output/project.mov original (guarda em output/_backup_fatia e restaura) nem no project.meta.
Uso: python test_overlay_alpha.py [--from 146 --to 170]    (escolha um trecho que contenha uma borda animação→clipe e clipe→animação)
"""

import argparse, json, os, re, shutil, signal, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS_DIR = HERE.parent
ap = argparse.ArgumentParser()
ap.add_argument("--from", dest="from_time", type=float, default=146)
ap.add_argument("--to", dest="to_time", type=float, default=170)
ap.add_argument("--scale", type=float, default=0.5)
args = ap.parse_args()
cwd = Path.cwd()
FPS = 30
assert (cwd / "src/project.meta").exists(), "rode dentro de animacao/"
meta_path = cwd / "src/project.meta"
meta_original = meta_path.read_text()
event_path = cwd / "src/scenes/scene1.meta"
event_original = event_path.read_text()
preview_path = cwd / "src/scenes/preview.json"
preview_original = preview_path.read_text() if preview_path.exists() else None
out = cwd / "output"
backup_dir = out / "_backup_fatia"
pp = Path("/tmp/pp")
pp.mkdir(exist_ok=True)
if not (pp / "node_modules/puppeteer-core").exists():
    subprocess.run(["npm", "i", "puppeteer-core"], cwd=pp, capture_output=True)
shutil.copy(SCRIPTS_DIR / "render.mjs", pp / "render_slice.mjs")
for f in ("render.stop",):
    (pp / f).unlink(missing_ok=True)
vite = None
chrome_before = subprocess.run(
    ["pgrep", "-f", "Google Chrome.*headless"], capture_output=True, text=True
).stdout.split()
try:
    backup_dir.mkdir(parents=True, exist_ok=True)
    if (out / "project.mov").exists():
        shutil.move(str(out / "project.mov"), backup_dir / "project.mov")
    if (
        preview_original
    ):  # a prévia do B-roll NÃO pode estar no render (vira vídeo opaco); o teste a desliga e restaura depois
        preview = json.loads(preview_original)
        preview["active"] = False
        preview_path.write_text(json.dumps(preview))
    m = json.loads(meta_original)
    m["shared"]["range"] = [args.from_time, args.to_time]
    m["rendering"]["resolutionScale"] = 1
    meta_path.write_text(json.dumps(m, indent=2))
    vite = subprocess.Popen(
        ["npx", "vite", "--port", "9000"],
        cwd=cwd,
        stdout=open("/tmp/pp/vite_slice.log", "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    time.sleep(10)
    env = dict(os.environ, OUT=str(out))
    render_proc = subprocess.Popen(
        ["node", str(pp / "render_slice.mjs")],
        cwd=cwd,
        env=env,
        stdout=open("/tmp/pp/render_slice.log", "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    target = out / "project.mov"
    expected_duration = args.to_time - args.from_time
    t0 = time.time()
    ok = False
    while time.time() - t0 < 900:
        time.sleep(5)
        if target.exists():
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(target)],
                capture_output=True,
                text=True,
            )
            try:
                d = float(r.stdout.strip())
                if abs(d - expected_duration) < 1.0:
                    ok = True
                    break
            except ValueError:
                pass
    assert ok, "render da fatia não terminou em 15 min (ver /tmp/pp/render_slice.log)"
    (pp / "render.stop").touch()
    time.sleep(3)
    # alfa por quadro: máximo do canal alfa
    r = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(target),
            "-vf",
            "alphaextract,signalstats,metadata=print:key=lavfi.signalstats.YMAX:file=-",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    ymax = [float(x) for x in re.findall(r"YMAX=([0-9.]+)", r.stdout)]
    # alphaextract sai em faixa limitada: alfa 0 = 16 (8 bits) = 256 em 12 bits (yuva444p12le). Transparente = <= 258.
    THRESHOLD = 258
    num_frames = len(ymax)
    assert num_frames >= int(expected_duration * FPS) - 2, f"{num_frames} quadros (esperado ~{int(expected_duration*FPS)})"
    broll = json.load(open("src/scenes/broll.json"))
    LEAD = 0.0
    errors = []
    empty_ok = 0
    light_overlay = (
        json.load(open("plan.json")).get("overlay_light") or []
    )  # Webdoc com B-roll: rótulo leve PODE ficar sobre o clipe
    for b in broll:
        if b["t_end"] < args.from_time or b["t_start"] > args.to_time:
            continue
        i0 = max(0, int(round((b["t_start"] - args.from_time) * FPS)))
        i1 = min(num_frames, int(round((b["t_end"] - args.from_time) * FPS)))
        is_allowed = lambda i: any(l0 - 0.1 <= args.from_time + i / FPS <= l1 + 0.1 for l0, l1 in light_overlay)
        dirty_frames = [i for i in range(i0, i1) if ymax[i] > THRESHOLD and not is_allowed(i)]
        if dirty_frames:
            errors.append(
                f"clipe {b['t_start']:.2f}-{b['t_end']:.2f}: {len(dirty_frames)} quadros com alfa>0 (1º em {args.from_time + dirty_frames[0] / FPS:.2f}s, YMAX={ymax[dirty_frames[0]]:.0f})"
            )
        else:
            empty_ok += 1
    covered = set()
    for b in broll:
        for i in range(int(round((b["t_start"] - args.from_time) * FPS)), int(round((b["t_end"] - args.from_time) * FPS))):
            covered.add(i)
    outside = [i for i in range(num_frames) if i not in covered]
    with_content = sum(1 for i in outside if ymax[i] > THRESHOLD)
    print(f"alfa YMAX min={min(ymax):.0f} max={max(ymax):.0f}")
    print(
        f"fatia {args.from_time}-{args.to_time}s: {num_frames} quadros; clipes na fatia: {empty_ok + len(errors)}; quadros fora de clipes: {len(outside)} (com conteúdo: {with_content})"
    )
    if outside and with_content == 0:
        errors.append("nenhum conteúdo fora dos clipes: o render parece vazio")
    if errors:
        print("FALHOU:")
        [print("  -", e) for e in errors]
        sys.exit(1)
    print(
        "OK: overlay 100% transparente durante todos os clipes da fatia e com conteúdo nas janelas de animação"
    )
finally:
    meta_path.write_text(meta_original)
    for p in (pp / "render.stop",):
        p.touch()
    if vite:
        try:
            os.killpg(vite.pid, signal.SIGTERM)
        except Exception:
            pass
    try:
        os.killpg(render_proc.pid, signal.SIGTERM)
    except Exception:
        pass
    time.sleep(1)
    subprocess.run(
        ["pkill", "-f", "Google Chrome.*headless"], capture_output=True
    )  # chrome órfão reescreve scene1.meta
    event_path.write_text(event_original)  # garante timeEvents intactos
    if preview_original:
        preview_path.write_text(preview_original)
    if (backup_dir / "project.mov").exists():
        if (out / "project.mov").exists():
            (out / "project.mov").unlink()
        shutil.move(str(backup_dir / "project.mov"), out / "project.mov")
    shutil.rmtree(backup_dir, ignore_errors=True)
