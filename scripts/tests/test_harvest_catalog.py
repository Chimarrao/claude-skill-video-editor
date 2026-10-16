#!/usr/bin/env python3
"""TESTE da colheita de imagens (sem rede): o merge dos workers NUNCA pode apagar um arquivo já catalogado, e o worker só grava o que acrescentou.
 H1 worker grava apenas o novo (não copia o catálogo principal)      H2 merge com shard que repete o principal não apaga arquivos
 H3 duplicata por SHA-1 com OUTRO nome é descartada (e só o arquivo dela)   H4 reparo lista exatamente o que falta em library/
"""

import json, os, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "images"))
import harvest_images as h  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="harv_"))
h.LIB = str(tmp / "library")
h.CATALOG = str(tmp / "database" / "image_catalog.json")
os.makedirs(h.LIB)
os.makedirs(tmp / "database")


def img(name, sha, subject="x"):
    (Path(h.LIB) / f"{name}.png").write_bytes(b"x" * 10)
    return dict(name=name, file=f"{name}.png", subject=subject, kind="logo", sha1=sha, source_key=f"en:File:{name}")


ok, falhas = [], []
teste = lambda n, c, m="": (ok if c else falhas).append(n if c else f"{n}: {m}")

main = {"images": {"logo_a": img("logo_a", "A"), "logo_b": img("logo_b", "B")}, "subjects": {"x": dict(images=2)}}
json.dump(main, open(h.CATALOG, "w"))
base = h.load_catalog()
# worker: acrescenta C e só salva o novo
cat = h.load_catalog("1")
cat["images"]["logo_c"] = img("logo_c", "C", "y")
cat["subjects"]["y"] = dict(images=1)
h.save_catalog(cat, "1", base)
shard = json.load(open(h.shard_path("1")))
teste("H1 shard só com o novo", list(shard["images"]) == ["logo_c"], str(list(shard["images"])))
# shard "ruim" (formato antigo): repete A e B com os mesmos nomes
ruim = {"images": {**main["images"], "logo_d": img("logo_d", "A", "z")}, "subjects": {"x": dict(images=2)}}
json.dump(ruim, open(h.shard_path("2"), "w"))
h.merge_shards()
files = set(os.listdir(h.LIB))
teste("H2 merge não apaga arquivos já catalogados", {"logo_a.png", "logo_b.png", "logo_c.png"} <= files, str(sorted(files)))
teste("H3 duplicata com outro nome some", "logo_d.png" not in files and "logo_d" not in json.load(open(h.CATALOG))["images"])
os.remove(Path(h.LIB) / "logo_b.png")
cat = h.load_catalog()
faltam = sorted(k for k, v in cat["images"].items() if v["file"] not in set(os.listdir(h.LIB)))
teste("H4 reparo enxerga o que falta", faltam == ["logo_b"], str(faltam))

print("\n".join(f"  ok    {n}" for n in ok))
if falhas:
    print("\nFALHOU:\n  - " + "\n  - ".join(falhas))
    sys.exit(1)
print(f"\nOK: {len(ok)} verificações da colheita passaram")
