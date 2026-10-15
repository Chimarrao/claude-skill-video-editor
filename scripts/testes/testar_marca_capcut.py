#!/usr/bin/env python3
"""TESTE: a MARCA (música, avatar, propaganda, vinheta final) foi aplicada corretamente no draft do CapCut?
Monta o draft numa pasta TEMPORÁRIA (nada é escrito nos seus projetos) e confere:
  M1 integridade: todo material_id / extra_material_refs existe e não há IDs repetidos entre materiais
  M2 trilhas na ordem  preenchimento · clipes · overlay · avatar · final · narracao · musica
  M3 música cobre 0..fim sem buracos e termina junto com o vídeo
  M4 avatar ausente durante a propaganda e durante a vinheta final; presente no resto até a vinheta
  M5 propaganda (vídeo + áudio) começa no instante pedido e tem a duração do pacote; nada do overlay/B-roll/narração sobrepõe a propaganda
  M6 vinheta final nos últimos segundos, por cima do B-roll; B-roll e preenchimento chegam até o fim
  M7 nenhuma trilha tem segmentos sobrepostos
Rode em animacao/ (precisa de plano.json com propaganda_t, capcut_spec.json e o pacote privado). Sai 1 se algo falhar.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CAP = Path(__file__).resolve().parent.parent / "capcut"
spec_origem = Path("capcut_spec.json")
assert spec_origem.exists(), "rode `spec_do_plano.py` antes (capcut_spec.json) dentro de animacao/"
spec = json.load(open(spec_origem))
assert spec.get("marca"), "spec sem 'marca': defina PROPAGANDA_APOS no plano_dados.py (e extraia o pacote)"
tmp = Path(tempfile.mkdtemp(prefix="cc_marca_"))
drafts = tmp / "drafts"
drafts.mkdir()
spec["nome"] = "TESTE marca"
json.dump(spec, open(tmp / "spec.json", "w"))
env = dict(os.environ, CAPCUT_DRAFTS_DIR=str(drafts), CAPCUT_TESTE="1")
r = subprocess.run(
    [sys.executable, str(CAP / "montar_draft.py"), str(tmp / "spec.json"), "--forcar"],
    capture_output=True,
    text=True,
    env=env,
)
assert r.returncode == 0, r.stdout[-1200:] + r.stderr[-1200:]
info = json.load(open(drafts / "TESTE marca" / "draft_info.json"))
total = info["duration"] / 1e6
erros = []

# M1 integridade
ids = {}
for lista, itens in info["materials"].items():
    if isinstance(itens, list):
        for m in itens:
            if isinstance(m, dict) and "id" in m:
                if m["id"] in ids:
                    erros.append(f"M1: id repetido {m['id'][:8]} em {lista}/{ids[m['id']]}")
                ids[m["id"]] = lista
for t in info["tracks"]:
    for s in t["segments"]:
        for ref in [s["material_id"]] + s.get("extra_material_refs", []):
            if ref not in ids:
                erros.append(f"M1: referência inexistente {ref[:8]} na trilha {t.get('name')}")

# M2 ordem das trilhas
nomes = [t.get("name") for t in info["tracks"]]
esperado = ["preenchimento", "clipes", "overlay", "avatar", "final", "narracao", "musica"]
if nomes != esperado:
    erros.append(f"M2: ordem das trilhas {nomes} != {esperado}")
T = {t["name"]: t for t in info["tracks"]}
seg = lambda n: sorted(
    [
        (
            s["target_timerange"]["start"] / 1e6,
            (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6,
            s,
        )
        for s in T[n]["segments"]
    ],
    key=lambda x: x[0],
)

# M7 sobreposição por trilha
for n in esperado:
    s = seg(n)
    for (a0, a1, _), (b0, b1, _) in zip(s, s[1:]):
        if b0 < a1 - 0.034 and n not in ("narracao",):
            erros.append(f"M7: trilha {n} tem sobreposição {a0:.2f}-{a1:.2f} × {b0:.2f}-{b1:.2f}")

# M3 música
mus = seg("musica")
if abs(mus[0][0]) > 0.034:
    erros.append("M3: música não começa em 0")
for (a0, a1, _), (b0, b1, _) in zip(mus, mus[1:]):
    if abs(b0 - a1) > 0.034:
        erros.append(f"M3: buraco/sobreposição na música {a1:.2f}→{b0:.2f}")
if abs(mus[-1][1] - total) > 0.1:
    erros.append(f"M3: música termina em {mus[-1][1]:.2f}s, vídeo em {total:.2f}s")

# M5 propaganda
tp = spec["marca"]["propaganda_t"]
retoma = spec["marca"].get("propaganda_retoma", tp)
prop_v = [
    x
    for x in seg("clipes")
    if "predefin" in json.dumps(x[2].get("extra_material_refs", [])) or abs(x[0] - tp) < 0.05
]
prop_v = [x for x in seg("clipes") if abs(x[0] - tp) < 0.05]
if not prop_v:
    erros.append(f"M5: propaganda (vídeo) não começa em {tp}s")
    d_prop = 0
else:
    d_prop = prop_v[0][1] - prop_v[0][0]
if not any(abs(x[0] - tp) < 0.05 for x in seg("narracao")):
    erros.append("M5: áudio da propaganda não começa em T")
for n in ("clipes", "overlay"):
    for a0, a1, s in seg(n):
        if abs(a0 - tp) < 0.05 and n == "clipes":
            continue
        if a0 < tp + d_prop - 0.034 and a1 > tp + 0.034:
            erros.append(f"M5: {n} {a0:.2f}-{a1:.2f} SOBRE a propaganda ({tp:.1f}-{tp + d_prop:.1f})")
depois = [
    x
    for x in seg("narracao")
    if x[0] >= tp + d_prop - 0.05
    and "extract_music" in json.dumps(x[2].get("extra_material_refs", []))
    or x[0] >= tp + d_prop - 0.05
]
if depois:
    src0 = depois[0][2]["source_timerange"]["start"] / 1e6
    if abs(src0 - retoma) > 0.1:
        erros.append(
            f"M5: a narração retoma da fonte em {src0:.2f}s, esperado {retoma:.2f}s (o silêncio {tp:.1f}-{retoma:.1f}s deve ser removido)"
        )
for a0, a1, s in seg("narracao"):
    if a0 < tp + d_prop - 0.034 and a1 > tp + 0.034 and abs(a0 - tp) > 0.05:
        erros.append(f"M5: narração {a0:.2f}-{a1:.2f} sobre a propaganda")

# M4/M6 avatar e vinheta final
fin = seg("final")
if len(fin) != 1 or fin[0][1] < total - 0.1:
    erros.append(
        f"M6: vinheta final deveria terminar com o vídeo ({fin[0][1] if fin else None} vs {total:.2f})"
    )
else:
    f0, f1, _ = fin[0]
    for a0, a1, _ in seg("avatar"):
        if a1 > f0 + 0.034:
            erros.append(f"M4: avatar {a0:.2f}-{a1:.2f} aparece na vinheta final ({f0:.1f}s)")
        if a0 < tp + d_prop - 0.034 and a1 > tp + 0.034:
            erros.append(f"M4: avatar aparece durante a propaganda")
    av = seg("avatar")
    if abs(av[0][0]) > 0.034 or abs(av[-1][1] - f0) > 0.1:
        erros.append(
            f"M4: avatar deve ir de 0 até o início da vinheta ({f0:.1f}s): {[(round(a, 1), round(b, 1)) for a, b, _ in av]}"
        )
    # B-roll chega até o fim por baixo da vinheta
    cl = [x for x in seg("clipes") if abs(x[0] - tp) > 0.05]
    if not cl or cl[-1][1] < total - 0.1:
        erros.append(
            f"M6: B-roll termina em {cl[-1][1] if cl else None}, o vídeo em {total:.2f}s (B-roll precisa ir até o fim)"
        )
pre = seg("preenchimento")
if pre[-1][1] < total - 0.1:
    erros.append("M6: preenchimento não chega ao fim")
shutil.rmtree(tmp, ignore_errors=True)
print(f"trilhas {nomes} · total {total:.1f}s · propaganda em {tp:.1f}s ({d_prop:.1f}s)")
if erros:
    print("FALHOU:")
    [print("  -", e) for e in erros[:40]]
    sys.exit(1)
print("OK: marca aplicada (música/avatar/propaganda/vinheta) sem sobreposições nem buracos")
