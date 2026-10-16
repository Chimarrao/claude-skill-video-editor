#!/usr/bin/env python3
"""Baixa arquivos ESPECÍFICOS do Wikimedia Commons (ou da Wikipédia) para a biblioteca de imagens e registra no catálogo.

Use quando a colheita por assunto (harvest_images.py) não trouxe a imagem exata de que o vídeo precisa — por exemplo, a tela azul
CLÁSSICA do Windows 9x em vez da moderna:
  python fetch_file.py --slug bsod_windows_9x --kind tela "File:Windows 9X BSOD.png" "File:Windows Me BSoD Windows 01.png"
  python fetch_file.py --slug beos --kind logo --host en.wikipedia.org "File:BeOS logo.png"
Saída: library/<tipo>_<slug>[_n].<ext> + entrada em database/image_catalog.json (mesmos metadados da colheita: licença, fonte, proporção).
Para achar o título certo: https://commons.wikimedia.org/w/index.php?search=...&ns6=1
"""

import argparse, hashlib, io, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harvest_images as H  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("titles", nargs="+", help='títulos dos arquivos, ex.: "File:Windows 9X BSOD.png"')
    ap.add_argument("--slug", required=True, help="assunto (ex.: bsod_windows_9x, beos)")
    ap.add_argument("--kind", choices=["logo", "tela", "foto", "obj"], required=True)
    ap.add_argument("--host", default="commons.wikimedia.org")
    ap.add_argument("--tags", default="", help="tags separadas por espaço")
    args = ap.parse_args()
    from PIL import Image

    cat = H.load_catalog()
    novos = 0
    for title in args.titles:
        d = H.api(args.host, action="query", titles=title, prop="imageinfo", iiprop="url|size|mime|extmetadata", iiurlwidth=1280)
        page = (d.get("query", {}).get("pages") or [{}])[0]
        it = H.info_to_item(page, args.host) if page and not page.get("missing") else None
        if not it:
            print(f"   ! não encontrei {title}")
            continue
        key = f"{it['host']}:{it['title']}"
        if key in {v["source_key"] for v in cat["images"].values()}:
            print(f"   = já está no catálogo: {title}")
            continue
        data, ext = H.download(it)
        if not data:
            print(f"   ! falhou o download de {title}")
            continue
        sha = hashlib.sha1(data).hexdigest()
        if sha in {v["sha1"] for v in cat["images"].values()}:
            print(f"   = conteúdo repetido: {title}")
            continue
        w, h = Image.open(io.BytesIO(data)).size
        n = sum(1 for v in cat["images"].values() if v["subject"] == args.slug and v["kind"] == args.kind) + 1
        name = f"{args.kind}_{args.slug}" + ("" if n == 1 else f"_{n}")
        os.makedirs(H.LIB, exist_ok=True)
        open(os.path.join(H.LIB, f"{name}.{ext}"), "wb").write(data)
        cat["images"][name] = dict(
            name=name, file=f"{name}.{ext}", subject=args.slug, kind=args.kind, tags=args.tags.split(), width=w, height=h,
            aspect=round(w / h, 3), aspect_class=H.aspect_class(w, h), bytes=len(data), sha1=sha, source_key=key,
            source_url=it["page"], license=it["license"], nonfree=it["nonfree"], artist=it["artist"],
        )
        print(f"   + {name}.{ext} {w}x{h} {args.kind}  ({it['license']})")
        novos += 1
    cat["subjects"].setdefault(args.slug, dict(done=time.strftime("%Y-%m-%d"), images=0))
    cat["subjects"][args.slug]["images"] = sum(1 for v in cat["images"].values() if v["subject"] == args.slug)
    H.save_catalog(cat)
    print(f"{novos} nova(s) imagem(ns); catálogo: {len(cat['images'])} imagens")


if __name__ == "__main__":
    main()
