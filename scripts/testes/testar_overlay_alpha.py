#!/usr/bin/env python3
"""TESTE DE RENDER (fatia): renderiza só um trecho do overlay (padrão: ~25 s com clipes e animações) e mede o canal alfa quadro a quadro.
Prova que: (1) durante cada clipe de B-roll o overlay é 100% transparente (nenhuma animação/HUD vaza nem por 1 quadro);
           (2) fora dos clipes há conteúdo (o trecho renderizou de verdade).
Rode em animacao/ com o vite parado. NÃO mexe no output/project.mov original (guarda em output/_backup_fatia e restaura) nem no project.meta.
Uso: python testar_overlay_alpha.py [--de 146 --ate 170]    (escolha um trecho que contenha uma borda animação→clipe e clipe→animação)
"""

import argparse, json, os, re, shutil, signal, subprocess, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SC = AQUI.parent
ap = argparse.ArgumentParser()
ap.add_argument("--de", type=float, default=146)
ap.add_argument("--ate", type=float, default=170)
ap.add_argument("--escala", type=float, default=0.5)
a = ap.parse_args()
cwd = Path.cwd()
FPS = 30
assert (cwd / "src/project.meta").exists(), "rode dentro de animacao/"
meta_p = cwd / "src/project.meta"
meta0 = meta_p.read_text()
ev_p = cwd / "src/scenes/cena1.meta"
ev0 = ev_p.read_text()
pv_p = cwd / "src/scenes/previa.json"
pv0 = pv_p.read_text() if pv_p.exists() else None
out = cwd / "output"
bk = out / "_backup_fatia"
pp = Path("/tmp/pp")
pp.mkdir(exist_ok=True)
if not (pp / "node_modules/puppeteer-core").exists():
    subprocess.run(["npm", "i", "puppeteer-core"], cwd=pp, capture_output=True)
shutil.copy(SC / "render.mjs", pp / "render_fatia.mjs")
for f in ("render.stop",):
    (pp / f).unlink(missing_ok=True)
vite = None
chrome_antes = subprocess.run(
    ["pgrep", "-f", "Google Chrome.*headless"], capture_output=True, text=True
).stdout.split()
try:
    bk.mkdir(parents=True, exist_ok=True)
    if (out / "project.mov").exists():
        shutil.move(str(out / "project.mov"), bk / "project.mov")
    if (
        pv0
    ):  # a prévia do B-roll NÃO pode estar no render (vira vídeo opaco); o teste a desliga e restaura depois
        pv = json.loads(pv0)
        pv["ativa"] = False
        pv_p.write_text(json.dumps(pv))
    m = json.loads(meta0)
    m["shared"]["range"] = [a.de, a.ate]
    m["rendering"]["resolutionScale"] = 1
    meta_p.write_text(json.dumps(m, indent=2))
    vite = subprocess.Popen(
        ["npx", "vite", "--port", "9000"],
        cwd=cwd,
        stdout=open("/tmp/pp/vite_fatia.log", "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    time.sleep(10)
    env = dict(os.environ, OUT=str(out))
    rend = subprocess.Popen(
        ["node", str(pp / "render_fatia.mjs")],
        cwd=cwd,
        env=env,
        stdout=open("/tmp/pp/render_fatia.log", "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    alvo = out / "project.mov"
    esperado = a.ate - a.de
    t0 = time.time()
    ok = False
    while time.time() - t0 < 900:
        time.sleep(5)
        if alvo.exists():
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(alvo)],
                capture_output=True,
                text=True,
            )
            try:
                d = float(r.stdout.strip())
                if abs(d - esperado) < 1.0:
                    ok = True
                    break
            except ValueError:
                pass
    assert ok, "render da fatia não terminou em 15 min (ver /tmp/pp/render_fatia.log)"
    (pp / "render.stop").touch()
    time.sleep(3)
    # alfa por quadro: máximo do canal alfa
    r = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(alvo),
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
    TR = 258
    nq = len(ymax)
    assert nq >= int(esperado * FPS) - 2, f"{nq} quadros (esperado ~{int(esperado*FPS)})"
    broll = json.load(open("src/scenes/broll.json"))
    LEAD = 0.0
    erros = []
    vazio_ok = 0
    leve = (
        json.load(open("plano.json")).get("overlay_leve") or []
    )  # Webdoc com B-roll: rótulo leve PODE ficar sobre o clipe
    for b in broll:
        if b["t_fim"] < a.de or b["t_inicio"] > a.ate:
            continue
        i0 = max(0, int(round((b["t_inicio"] - a.de) * FPS)))
        i1 = min(nq, int(round((b["t_fim"] - a.de) * FPS)))
        permitido = lambda i: any(l0 - 0.1 <= a.de + i / FPS <= l1 + 0.1 for l0, l1 in leve)
        sujos = [i for i in range(i0, i1) if ymax[i] > TR and not permitido(i)]
        if sujos:
            erros.append(
                f"clipe {b['t_inicio']:.2f}-{b['t_fim']:.2f}: {len(sujos)} quadros com alfa>0 (1º em {a.de + sujos[0] / FPS:.2f}s, YMAX={ymax[sujos[0]]:.0f})"
            )
        else:
            vazio_ok += 1
    cobertos = set()
    for b in broll:
        for i in range(int(round((b["t_inicio"] - a.de) * FPS)), int(round((b["t_fim"] - a.de) * FPS))):
            cobertos.add(i)
    fora = [i for i in range(nq) if i not in cobertos]
    com_conteudo = sum(1 for i in fora if ymax[i] > TR)
    print(f"alfa YMAX min={min(ymax):.0f} max={max(ymax):.0f}")
    print(
        f"fatia {a.de}-{a.ate}s: {nq} quadros; clipes na fatia: {vazio_ok + len(erros)}; quadros fora de clipes: {len(fora)} (com conteúdo: {com_conteudo})"
    )
    if fora and com_conteudo == 0:
        erros.append("nenhum conteúdo fora dos clipes: o render parece vazio")
    if erros:
        print("FALHOU:")
        [print("  -", e) for e in erros]
        sys.exit(1)
    print(
        "OK: overlay 100% transparente durante todos os clipes da fatia e com conteúdo nas janelas de animação"
    )
finally:
    meta_p.write_text(meta0)
    for p in (pp / "render.stop",):
        p.touch()
    if vite:
        try:
            os.killpg(vite.pid, signal.SIGTERM)
        except Exception:
            pass
    try:
        os.killpg(rend.pid, signal.SIGTERM)
    except Exception:
        pass
    time.sleep(1)
    subprocess.run(
        ["pkill", "-f", "Google Chrome.*headless"], capture_output=True
    )  # chrome órfão reescreve cena1.meta
    ev_p.write_text(ev0)  # garante timeEvents intactos
    if pv0:
        pv_p.write_text(pv0)
    if (bk / "project.mov").exists():
        if (out / "project.mov").exists():
            (out / "project.mov").unlink()
        shutil.move(str(bk / "project.mov"), out / "project.mov")
    shutil.rmtree(bk, ignore_errors=True)
