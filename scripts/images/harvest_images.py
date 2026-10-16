#!/usr/bin/env python3
"""Colhe imagens (logos, telas, fotos, hardware) da Wikipédia/Wikimedia Commons para a biblioteca da skill.

Uso (qualquer pasta):
  python harvest_images.py                      # colhe todos os assuntos de subjects.py que ainda não foram colhidos
  python harvest_images.py --only windows_xp,beos   # só estes assuntos (slugs)
  python harvest_images.py --list                # lista os assuntos e quantas imagens cada um já tem
  python harvest_images.py --refresh slug        # recolhe um assunto do zero

Como funciona (por assunto):
  1. lê as imagens dos ARTIGOS da Wikipédia listados em `wiki` (en e pt) — onde estão as logos e capturas de tela mais relevantes
     (inclui arquivos de "uso justo" que não estão no Commons, como a logo do BeOS);
  2. complementa com a busca do Commons (`commons`), exigindo as palavras do assunto no título;
  3. classifica cada arquivo (logo / tela / foto / objeto) pelo nome, descarta ícones de interface, bandeiras e miniaturas;
  4. baixa em `library/` (ignorada pelo git) com o nome `<tipo>_<assunto>[_n].<ext>` e grava os metadados (fonte, licença,
     autor, dimensões, proporção) em `database/image_catalog.json` (este SIM vai para o git).
Os arquivos ficam em `library/`; o banco privado (`assets_db.py sync library`) guarda a cópia em base64.
Educado com os servidores: 1 requisição por vez, pausas e retentativa com espera crescente em caso de 429.
"""

import argparse, hashlib, html, io, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LIB = os.path.join(ROOT, "library")
CATALOG = os.path.join(ROOT, "database", "image_catalog.json")
UA = "animacao-narracao-skill/1.0 (https://github.com/Chimarrao/claude-skill-video-editor; catalogo de imagens para video educativo) python-urllib"
sys.path.insert(0, HERE)

LOGO_WORDS = ("logo", "wordmark", "icon", "emblem", "symbol", "badge", "mascot", "brand")
SCREEN_WORDS = ("screenshot", "desktop", "screen", "interface", "gui", "boot", "login", "installer", "setup", "session", "shell", "terminal")
OBJECT_WORDS = ("box", "packaging", "retail", "floppy", "disk", "disc", "cd-rom", "cdrom", "chip", "motherboard", "keyboard", "mouse", "monitor", "crt", "computer", "laptop", "tablet", "phone", "device", "hardware", "board", "cartridge")
SKIP_WORDS = (
    "commons-logo", "wikiquote", "wiktionary", "wikibooks", "wikisource", "wikiversity", "wikinews", "wikidata", "wikimedia", "wikipedia",
    "flag_of", "flag of", "map_of", "map of", "ambox", "edit-", "ooui", "oojs", "padlock", "question_book", "symbol_", "stub", "increase", "decrease",
    "red_pog", "crystal_", "nuvola", "portal", "folder_hexagonal", "blue_pencil", "cscr", "disambig", "searchtool", "magnify", "speaker_icon",
    "text-x-", "gnome-", "emblem-", "dialog-", "document-", "office-book", "unbalanced", "merge-", "split-", "info_circle", "ambox", "check_mark",
    "lock-", "semi-protection", "pp-", "star_full", "star_empty", "bluelink", "redirect", "transparent_square", "p_vip", "loudspeaker",
)
MIN_SIDE = dict(logo=120, tela=480, foto=360, obj=300)


def http(url, tries=4, binary=False):
    """GET com User-Agent identificável e retentativa: respeita o `Retry-After` do servidor em 429/5xx (espera crescente)."""
    espera = 4.0
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            return data if binary else data.decode("utf8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                retry = e.headers.get("Retry-After")
                pausa = min(float(retry), 90) if retry and retry.replace(".", "").isdigit() else espera
                print(f"   (http {e.code}; espera {pausa:.0f}s) {url[:80]}", flush=True)
                time.sleep(pausa)
                espera *= 2
                continue
            if e.code == 404:
                return None
            raise
        except Exception:
            time.sleep(espera)
            espera *= 2
    return None


def api(host, **params):
    """Chama a API MediaWiki e devolve o JSON (ou {})."""
    params.update(format="json", formatversion="2")
    txt = http(f"https://{host}/w/api.php?" + urllib.parse.urlencode(params))
    time.sleep(0.5)
    try:
        return json.loads(txt) if txt else {}
    except json.JSONDecodeError:
        return {}


def plain(s):
    """Texto simples a partir de um trecho HTML dos metadados."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s if s is not None else "")))).strip()


def classify(title, mime, w, h):
    """Tipo da imagem pelo nome do arquivo: logo, tela, obj, foto ou None (descartar)."""
    t = title.lower().replace("file:", "").replace("arquivo:", "")
    t = re.sub(r"[_\-.]+", " ", t)
    if any(x.replace("_", " ") in t for x in SKIP_WORDS):
        return None
    if mime in ("image/svg+xml",) or any(re.search(rf"\b{x}\b", t) for x in LOGO_WORDS):
        return "logo"
    if any(re.search(rf"\b{x}\b", t) for x in SCREEN_WORDS):
        return "tela"
    if any(re.search(rf"\b{x}\b", t) for x in OBJECT_WORDS):
        return "obj"
    if mime in ("image/jpeg", "image/png", "image/webp") and w and h:
        return "foto" if mime == "image/jpeg" else "tela"
    return None


def info_to_item(page, host):
    """Converte uma página 'File:' da API em um dicionário com url, tamanho, licença e autor (ou None)."""
    ii = (page.get("imageinfo") or [None])[0]
    if not ii:
        return None
    meta = {k: plain((v or {}).get("value", "")) for k, v in (ii.get("extmetadata") or {}).items()}
    lic = meta.get("LicenseShortName") or meta.get("UsageTerms") or ""
    mime = ii.get("mime", "")
    if not mime.startswith("image/") or mime in ("image/gif", "image/vnd.djvu", "image/tiff"):
        return None
    w, h = ii.get("width") or 0, ii.get("height") or 0
    title = page.get("title", "")
    return dict(
        title=title,
        host=host,
        mime=mime,
        width=w,
        height=h,
        url=ii.get("url"),
        thumb=ii.get("thumburl"),
        page=ii.get("descriptionurl"),
        license=lic,
        nonfree=bool(re.search(r"non-free|fair use|uso justo|nonfree", lic + " " + meta.get("Restrictions", ""), re.I)),
        artist=meta.get("Artist", "")[:120],
    )


def article_images(host, title):
    """Imagens de um artigo (com url, tamanho e licença)."""
    out, cont = [], {}
    for _ in range(3):
        d = api(host, action="query", generator="images", titles=title, gimlimit=80, prop="imageinfo",
                iiprop="url|size|mime|extmetadata", iiurlwidth=1280, **cont)
        for p in (d.get("query", {}).get("pages") or []):
            it = info_to_item(p, host)
            if it:
                out.append(it)
        if "continue" not in d:
            break
        cont = d["continue"]
    return out


def commons_search(query, limit=25):
    """Busca arquivos de imagem no Commons."""
    d = api("commons.wikimedia.org", action="query", generator="search", gsrsearch=query + " filetype:bitmap|drawing",
            gsrnamespace=6, gsrlimit=limit, prop="imageinfo", iiprop="url|size|mime|extmetadata", iiurlwidth=1280)
    out = []
    for p in (d.get("query", {}).get("pages") or []):
        it = info_to_item(p, "commons.wikimedia.org")
        if it:
            out.append(it)
    return out


def norm_tokens(s):
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]


def shard_path(shard):
    """Arquivo do catálogo de um worker (colheita em paralelo: cada worker grava o seu e `--merge` junta tudo)."""
    return CATALOG if not shard else CATALOG.replace(".json", f".{shard}.json")


def load_catalog(shard=None):
    """Catálogo principal; com `shard`, soma o arquivo do worker (para saber o que já foi colhido e evitar duplicatas)."""
    cat = json.load(open(CATALOG, encoding="utf8")) if os.path.exists(CATALOG) else {"images": {}, "subjects": {}}
    if shard and os.path.exists(shard_path(shard)):
        extra = json.load(open(shard_path(shard), encoding="utf8"))
        cat["images"].update(extra["images"])
        cat["subjects"].update(extra["subjects"])
    return cat


def save_catalog(cat, shard=None):
    os.makedirs(os.path.dirname(CATALOG), exist_ok=True)
    path = shard_path(shard)
    tmp = path + ".tmp"
    json.dump(cat, open(tmp, "w", encoding="utf8"), ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def merge_shards():
    """Junta os catálogos dos workers no principal (descarta imagens repetidas pelo SHA-1 e apaga os arquivos extras)."""
    cat = load_catalog()
    vistos = {v["sha1"] for v in cat["images"].values()}
    base = os.path.dirname(CATALOG)
    for f in sorted(os.listdir(base)):
        if re.match(r"image_catalog\.\d+\.json$", f):
            extra = json.load(open(os.path.join(base, f), encoding="utf8"))
            for k, v in extra["images"].items():
                if v["sha1"] in vistos:
                    for g in os.listdir(LIB):
                        if g.startswith(k + "."):
                            os.remove(os.path.join(LIB, g))
                    continue
                vistos.add(v["sha1"])
                cat["images"][k] = v
            cat["subjects"].update(extra["subjects"])
            os.remove(os.path.join(base, f))
    save_catalog(cat)
    print(f"catálogo unido: {len(cat['images'])} imagens, {len(cat['subjects'])} assuntos")


def aspect_class(w, h):
    """Classe de proporção para escolher a imagem certa em cada layout: tall, square, wide (até 2,2:1) ou ultrawide."""
    r = w / h if h else 1
    if r < 0.85:
        return "tall"
    if r <= 1.18:
        return "square"
    return "wide" if r <= 2.2 else "ultrawide"


def download(it):
    """Baixa o arquivo (original se for raster pequeno, miniatura de 1280 px para SVG/grandes) e devolve (bytes, ext)."""
    svg = it["mime"] == "image/svg+xml"
    big = max(it["width"], it["height"]) > 2600
    url = (it["thumb"] if (svg or big) and it["thumb"] else it["url"]).split("?")[0]
    data = http(url, binary=True)
    time.sleep(1.3)
    if not data:
        return None, None
    ext = "png" if (svg or url == it.get("thumb") and it["mime"] == "image/png") else {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(it["mime"], "png")
    if url == it.get("thumb") and it["mime"] == "image/jpeg":
        ext = "jpg"
    return data, ext


def harvest(subject, cat, quotas):
    """Colhe um assunto e atualiza o catálogo; devolve quantas imagens novas gravou."""
    slug = subject["slug"]
    tokens = norm_tokens(subject.get("match") or slug.replace("_", " "))
    cands = []
    for page in subject.get("wiki", []):
        host, _, title = page.partition(":") if page[:3] in ("en:", "pt:") else ("en", ":", page)
        cands += article_images(f"{host}.wikipedia.org", title.split("#")[0])
    for q in subject.get("commons", []):
        for it in commons_search(q):
            tl = norm_tokens(it["title"])
            if all(any(tok in w for w in tl) for tok in tokens):
                cands.append(it)
    seen_t, ranked = set(), []
    for it in cands:
        if it["title"] in seen_t:
            continue
        seen_t.add(it["title"])
        kind = classify(it["title"], it["mime"], it["width"], it["height"])
        if not kind:
            continue
        if min(it["width"], it["height"]) < MIN_SIDE[kind] and it["mime"] != "image/svg+xml":
            continue
        score = (0 if it["mime"] == "image/svg+xml" else 1, -(it["width"] * it["height"]))
        if kind == "logo" and any(tok in norm_tokens(it["title"]) for tok in tokens):
            score = (-1,) + score
        ranked.append((kind, score, it))
    n_new, count = 0, {}
    for kind, _, it in sorted(ranked, key=lambda x: (x[0], x[1])):
        if count.get(kind, 0) >= quotas.get(kind, 3):
            continue
        key = f"{it['host']}:{it['title']}"
        if key in {v["source_key"] for v in cat["images"].values()}:
            count[kind] = count.get(kind, 0) + 1
            continue
        data, ext = download(it)
        if not data or len(data) < 800:
            continue
        sha = hashlib.sha1(data).hexdigest()
        if sha in {v["sha1"] for v in cat["images"].values()}:
            continue
        try:
            from PIL import Image

            im = Image.open(io.BytesIO(data))
            w, h = im.size
        except Exception:
            continue
        if min(w, h) < (MIN_SIDE[kind] if kind != "logo" else 100):
            continue
        n = sum(1 for v in cat["images"].values() if v["subject"] == slug and v["kind"] == kind) + 1
        name = f"{kind}_{slug}" + ("" if n == 1 else f"_{n}")
        os.makedirs(LIB, exist_ok=True)
        open(os.path.join(LIB, f"{name}.{ext}"), "wb").write(data)
        cat["images"][name] = dict(
            name=name, file=f"{name}.{ext}", subject=slug, kind=kind, tags=subject.get("tags", []), width=w, height=h,
            aspect=round(w / h, 3), aspect_class=aspect_class(w, h), bytes=len(data), sha1=sha, source_key=key,
            source_url=it["page"], license=it["license"], nonfree=it["nonfree"], artist=it["artist"],
        )
        count[kind] = count.get(kind, 0) + 1
        n_new += 1
        print(f"   + {name}.{ext} {w}x{h} {kind}", flush=True)
    cat["subjects"][slug] = dict(done=time.strftime("%Y-%m-%d"), images=sum(1 for v in cat["images"].values() if v["subject"] == slug))
    return n_new


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="slugs separados por vírgula")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--refresh", help="slug a recolher do zero")
    ap.add_argument("--shard", help="K/N: este worker colhe os assuntos de índice K (mod N); use vários em paralelo e depois --merge")
    ap.add_argument("--merge", action="store_true", help="junta os catálogos dos workers")
    ap.add_argument("--max-logo", type=int, default=3)
    ap.add_argument("--max-tela", type=int, default=4)
    ap.add_argument("--max-foto", type=int, default=2)
    ap.add_argument("--max-obj", type=int, default=2)
    args = ap.parse_args()
    from subjects import SUBJECTS

    if args.merge:
        merge_shards()
        return
    shard = None
    k, n = 0, 1
    if args.shard:
        k, n = (int(x) for x in args.shard.split("/"))
        shard = str(k)
    cat = load_catalog(shard)
    if args.list:
        for s in SUBJECTS:
            print(f"{s['slug']:28} {cat['subjects'].get(s['slug'], {}).get('images', '-')}")
        return
    quotas = dict(logo=args.max_logo, tela=args.max_tela, foto=args.max_foto, obj=args.max_obj)
    only = set((args.only or args.refresh or "").split(",")) - {""}
    for pos, s in enumerate(SUBJECTS):
        if pos % n != k:
            continue
        if only and s["slug"] not in only:
            continue
        if not only and s["slug"] in cat["subjects"]:
            continue
        if args.refresh:
            for key in [key for key, v in cat["images"].items() if v["subject"] == s["slug"]]:
                for f in os.listdir(LIB):
                    if f.startswith(key + "."):
                        os.remove(os.path.join(LIB, f))
                del cat["images"][key]
        print(f"== {s['slug']}", flush=True)
        try:
            harvest(s, cat, quotas)
        except Exception as e:  # um assunto ruim não derruba a colheita
            print(f"   ! erro em {s['slug']}: {e}", flush=True)
        save_catalog(cat, shard)
    print(f"catálogo: {len(cat['images'])} imagens, {len(cat['subjects'])} assuntos")


if __name__ == "__main__":
    main()
