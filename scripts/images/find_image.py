#!/usr/bin/env python3
"""Procura imagens no catálogo da biblioteca (assuntos, tags, tipo, proporção) para usar nas animações.

Uso:
  python find_image.py windows xp                      # tudo que casa com as palavras (assunto, nome, tags)
  python find_image.py linux --kind logo --aspect square
  python find_image.py beos --sheet /tmp/beos.png       # também gera a folha de contato para OLHAR
  python find_image.py --subjects                       # lista os assuntos (slug) e quantas imagens cada um tem
Qualidade: `check` = pode estar fora do assunto (confira na folha); `low` fica oculto (--all mostra). Filtros: --kind logo|tela|foto|obj · --aspect tall|square|wide|ultrawide · --min-width N · --all (inclui qualidade `low`).
Saída: nome do arquivo (use sem extensão em Item("nome"…)), dimensões, tipo, licença. Nomes: logo_<assunto>[_n], tela_…, foto_…, obj_….
Imagens com `nonfree` (uso justo da Wikipédia) servem como ilustração, mas confira a fonte (source_url) se for monetizar com destaque.
"""

import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAT = os.path.join(ROOT, "database", "image_catalog.json")
ap = argparse.ArgumentParser()
ap.add_argument("palavras", nargs="*")
ap.add_argument("--kind")
ap.add_argument("--aspect")
ap.add_argument("--min-width", type=int, default=0)
ap.add_argument("--all", action="store_true", help="inclui imagens low (descartadas)")
ap.add_argument("--strict", action="store_true", help="só imagens verificadas (ok), sem as marcadas check")
ap.add_argument("--sheet")
ap.add_argument("--subjects", action="store_true")
a = ap.parse_args()
cat = json.load(open(CAT, encoding="utf8"))
if a.subjects:
    cont = {}
    for v in cat["images"].values():
        if a.all or not v.get("quality", "ok").startswith("low"):
            cont[v["subject"]] = cont.get(v["subject"], 0) + 1
    for s in sorted(cont):
        print(f"{s:34} {cont[s]}")
    sys.exit(0)
toks = [t.lower() for t in a.palavras]
res = []
for name, v in cat["images"].items():
    q = v.get("quality", "ok")
    if not a.all and q.startswith("low"):
        continue
    if a.strict and q != "ok":
        continue
    if a.kind and v["kind"] != a.kind:
        continue
    if a.aspect and v["aspect_class"] != a.aspect:
        continue
    if v["width"] < a.min_width:
        continue
    hay = " ".join([v["subject"].replace("_", " "), name.replace("_", " "), " ".join(v.get("tags", []))]).lower()
    if all(t in hay for t in toks):
        res.append(v)
res.sort(key=lambda v: (v["subject"], v["kind"], v["name"]))
for v in res:
    q = v.get("quality", "ok")
    print(f"{v['name']:38} {v['width']:>5}x{v['height']:<5} {v['kind']:5} {v['aspect_class']:9} {'CONFIRA ' if q.startswith('check') else ''}{'USO-JUSTO ' if v['nonfree'] else ''}{v['license'][:28]}")
print(f"\n{len(res)} imagem(ns)")
if a.sheet and res:
    pats = ",".join(v["name"] + ".*" for v in res[:60])
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "sheet.py"), pats, a.sheet])
