#!/usr/bin/env python3
"""Banco SQLite de assets (base64) da skill: database/assets.db
Comandos:
  assets_db.py sync [pasta ...]   importa imagens (default: assets/ + ./src/images do projeto atual) sem duplicar (por name)
  assets_db.py list [filtro]            lista name, tipo, dimensões, categoria
  assets_db.py export <name|%pattern> [destino=src/images]   grava os arquivos decodificados
  assets_db.py open                      abre o sqlite3 interativo
  assets_db.py transcript-save <transcription.json> <audio> [--model large-v3] [--aligned] [--note "..."]   grava a transcrição (+modelo) no banco
  assets_db.py transcript-find <audio> [--output transcription.json] [--only-aligned]   reaproveita (por SHA-1 do áudio); sai 0 se achou, 3 se não
  assets_db.py video-register <arquivo> [--category video_filler] [--note ..]   registra SÓ a referência (caminho relativo, duração, resolução, fps, tamanho, sha256) — nunca base64
  assets_db.py video-list [categoria]
  assets_db.py transcript-list                lista as transcrições salvas
  assets_db.py variant-save <variations.tsx> [--thumbs pasta(VNN.png)] [--origin "..."]   salva as VARIAÇÕES DE LISTA (código de cada Vnn + helpers + miniatura) no banco
  assets_db.py variant-list                  lista id, name, usage, chosen
  assets_db.py variant-export <V07,V03|everything> [destino=src/scenes/variations.tsx]   remonta um .tsx executável só com as variações pedidas (+ exporta as imagens usadas)
  assets_db.py variant-choose <V07> [--note ".."]   marca uma variação como escolhida/em uso
Tabelas: list_variations(id PK, name, usage, description, code, thumb_base64, chosen, note, origin, created), variation_base(key PK: helpers|main, code), transcripts(sha1 PK, file, bytes, duration, model, aligned, aligner, language, created, note, json) e assets(name PK, ext, mime, bytes, width, height, category, origin, added, base64).
"""

import base64, glob, io, json, mimetypes, os, re, sqlite3, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "database", "assets.db")
os.makedirs(os.path.dirname(DB), exist_ok=True)


NEW_COLUMNS = dict(subject="TEXT", kind="TEXT", tags="TEXT", license="TEXT", source_url="TEXT", aspect="REAL", nonfree="INTEGER", quality="TEXT")
CATALOG = os.path.join(ROOT, "database", "image_catalog.json")
KIND_CATEGORY = dict(logo="logo", tela="screen", foto="photo", obj="object")


def connect():
    """Abre o banco (criando a tabela `assets`, o índice e as colunas de catálogo se faltarem)."""
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS assets(name TEXT PRIMARY KEY, ext TEXT, mime TEXT, bytes INTEGER,
        width INTEGER, height INTEGER, category TEXT, origin TEXT, added TEXT, base64 TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS i_cat ON assets(category)")
    have = {r[1] for r in c.execute("PRAGMA table_info(assets)")}
    for col, typ in NEW_COLUMNS.items():
        if col not in have:
            c.execute(f"ALTER TABLE assets ADD COLUMN {col} {typ}")
    return c


def catalog_meta():
    """Metadados da colheita (assunto, tipo, tags, licença, fonte…) por nome de arquivo, de database/image_catalog.json."""
    if not os.path.exists(CATALOG):
        return {}
    return json.load(open(CATALOG, encoding="utf8")).get("images", {})


def category(name):
    """Deduz a categoria do asset pelo prefixo do nome (logo_, foto_, tela_, ic-…); o padrão é `object`."""
    for prefix, cat in (
        ("logo_", "logo"),
        ("foto_", "person"),
        ("tela_", "screen"),
        ("ic-", "icon"),
        ("placeholder", "placeholder"),
    ):
        if name.startswith(prefix):
            return cat
    return "object"


def dimensions(path, ext):
    """Largura e altura em px (SVG: lê o viewBox); `(None, None)` se não der para medir."""
    try:
        if ext == "svg":
            m = re.search(
                r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', open(path, errors="ignore").read()
            )
            return (int(float(m.group(1))), int(float(m.group(2)))) if m else (None, None)
        from PIL import Image

        return Image.open(path).size
    except Exception:
        return (None, None)


def sync(folders):
    """Importa para o banco as imagens novas das pastas dadas (sem duplicar por nome; ignora `ic-*` e `*-mono`, que o plan.py gera)
    e grava os metadados do catálogo (assunto, tipo, tags, licença, fonte, proporção, qualidade) quando existirem."""
    conn = connect()
    meta = catalog_meta()
    new_count = 0
    for folder in folders:
        for file_path in sorted(glob.glob(os.path.join(folder, "*"))):
            basename = os.path.basename(file_path)
            name, ext = os.path.splitext(basename)
            ext = ext.lstrip(".").lower()
            if ext not in ("png", "jpg", "jpeg", "webp", "svg", "gif"):
                continue
            if name.endswith("-mono") or name.startswith("ic-"):
                continue  # gerados automaticamente pelo plan.py
            m = meta.get(name)
            extra = (
                (m["subject"], m["kind"], " ".join(m.get("tags", [])), m.get("license", ""), m.get("source_url", ""), m.get("aspect"), int(bool(m.get("nonfree"))), m.get("quality", "ok"))
                if m
                else (None, None, None, None, None, None, None, None)
            )
            if conn.execute("SELECT 1 FROM assets WHERE name=?", (name,)).fetchone():
                if m:
                    conn.execute("UPDATE assets SET subject=?, kind=?, tags=?, license=?, source_url=?, aspect=?, nonfree=?, quality=? WHERE name=?", extra + (name,))
                continue
            w, h = dimensions(file_path, ext)
            conn.execute(
                "INSERT INTO assets(name, ext, mime, bytes, width, height, category, origin, added, base64, subject, kind, tags, license, source_url, aspect, nonfree, quality) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    name,
                    ext,
                    mimetypes.guess_type(basename)[0] or "image/" + ext,
                    os.path.getsize(file_path),
                    w,
                    h,
                    KIND_CATEGORY.get(m["kind"]) if m else category(name),
                    os.path.relpath(folder),
                    time.strftime("%Y-%m-%d"),
                    base64.b64encode(open(file_path, "rb").read()).decode(),
                )
                + extra,
            )
            new_count += 1
    conn.commit()
    print(f"{new_count} novo(s); total {conn.execute('SELECT COUNT(*) FROM assets').fetchone()[0]}  -> {DB}")


def sha1(path):
    """SHA-1 do arquivo, lido em blocos de 1 MB (chave de cache das transcrições)."""
    import hashlib

    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ensure_transcript_table(conn):
    """Cria a tabela de transcrições (uma linha por áudio + modelo + alinhado ou não)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS transcripts(sha1 TEXT, model TEXT, aligned INTEGER, file TEXT, bytes INTEGER, duration REAL,
        aligner TEXT, language TEXT, created TEXT, note TEXT, json TEXT, PRIMARY KEY(sha1, model, aligned))"""
    )


def save_transcript(json_path, audio, model="large-v3", aligned=False, note=""):
    """Grava a transcrição (JSON completo) indexada pelo SHA-1 do áudio, com o modelo e se já está alinhada."""
    c = connect()
    ensure_transcript_table(c)
    d = json.load(open(json_path))
    c.execute(
        "INSERT OR REPLACE INTO transcripts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            sha1(audio),
            model,
            int(aligned),
            os.path.basename(audio),
            os.path.getsize(audio),
            d.get("duration"),
            "wav2vec2-large-xlsr-53-portuguese (CTC)" if aligned else None,
            "pt",
            time.strftime("%Y-%m-%d %H:%M"),
            note,
            open(json_path, encoding="utf-8").read(),
        ),
    )
    c.commit()
    print(
        f"transcrição salva (modelo {model}, {'aligned' if aligned else 'bruta'}) para {os.path.basename(audio)}"
    )


def find_transcript(audio, output="transcription.json", only_aligned=False):
    """Reaproveita uma transcrição salva: grava em `output` e devolve 0 se achou, 3 se não."""
    c = connect()
    ensure_transcript_table(c)
    q = (
        "SELECT json, model, aligned, created FROM transcripts WHERE sha1=?"
        + (" AND aligned=1" if only_aligned else "")
        + " ORDER BY aligned DESC, created DESC"
    )
    r = c.execute(q, (sha1(audio),)).fetchone()
    if not r:
        print("transcrição não encontrada no banco")
        return 3
    open(output, "w", encoding="utf-8").write(r[0])
    print(
        f"transcrição reaproveitada do banco ({r[1]}, {'aligned' if r[2] else 'bruta'}, {r[3]}) -> {output}"
    )
    return 0


def list_transcripts():
    """Lista as transcrições salvas (arquivo, modelo, alinhada, duração, data, SHA-1 curto)."""
    c = connect()
    ensure_transcript_table(c)
    for r in c.execute(
        "SELECT file, model, aligned, ROUND(duration), created, substr(sha1,1,8) FROM transcripts ORDER BY created"
    ):
        print(r)


def ensure_videos_table(conn):
    """Cria a tabela de referências a vídeos (só metadados e hash; nunca o vídeo em base64)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS videos(name TEXT PRIMARY KEY, path TEXT, category TEXT, duration REAL, width INTEGER, height INTEGER,
        fps REAL, bytes INTEGER, sha256 TEXT, codec TEXT, added TEXT, note TEXT)"""
    )


def sha256(path):
    """SHA-256 do arquivo, lido em blocos de 4 MB."""
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def register_video(file, category="video_filler", note=""):
    """Registra a referência de um vídeo (caminho relativo, duração, resolução, fps, tamanho, hash) lendo os dados com o ffprobe."""
    c = connect()
    ensure_videos_table(c)
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,codec_name:format=duration",
            "-of",
            "json",
            file,
        ],
        capture_output=True,
        text=True,
    )
    d = json.loads(r.stdout)
    st = d["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    rel = os.path.relpath(os.path.abspath(file), ROOT)  # relativo à pasta da skill
    c.execute(
        "INSERT OR REPLACE INTO videos VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            os.path.basename(file),
            rel,
            category,
            float(d["format"]["duration"]),
            st["width"],
            st["height"],
            round(float(num) / float(den), 3),
            os.path.getsize(file),
            sha256(file),
            st["codec_name"],
            time.strftime("%Y-%m-%d"),
            note,
        ),
    )
    c.commit()
    print(f"vídeo registrado (referência): {os.path.basename(file)} -> {rel}")


def list_videos(cat="%"):
    """Lista os vídeos registrados, filtrando pela categoria (aceita `%`)."""
    c = connect()
    ensure_videos_table(c)
    for r in c.execute(
        "SELECT name, category, path, ROUND(duration,2), width||'x'||height, fps, ROUND(bytes/1048576.0)||' MB', substr(sha256,1,12) FROM videos WHERE category LIKE ?",
        (cat,),
    ):
        print(r)


def ensure_variant_tables(conn):
    """Cria as tabelas do catálogo de variações de lista (código de cada variação + o código-base compartilhado)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS list_variations(id TEXT PRIMARY KEY, name TEXT, usage TEXT, description TEXT, code TEXT, thumb_base64 TEXT,
        chosen INTEGER DEFAULT 0, note TEXT, origin TEXT, created TEXT)"""
    )
    conn.execute("CREATE TABLE IF NOT EXISTS variation_base(key TEXT PRIMARY KEY, code TEXT)")


def save_variant(file, thumbs=None, origin=""):
    """Lê um `.tsx` de variações (marcadores `// ---------- Vnn: Nome ----------`) e salva o código de cada uma, os helpers e as miniaturas."""
    src = open(file, encoding="utf8").read()
    c = connect()
    ensure_variant_tables(c)
    markers = list(re.finditer(r"^// ---------- (V\d+): (.+?) ---------- *$", src, re.M))
    assert markers, "nenhum marcador '// ---------- Vnn: Nome ----------' no arquivo"
    vars_end = re.search(r"^const VARS", src, re.M).start()
    helpers = src[: markers[0].start()]
    rest = src[vars_end:]
    meta = {
        m.group(1): (m.group(2), m.group(3))
        for m in re.finditer(r"\['(V\d+)', '([^']*)', '([^']*)', v\d+\]", src)
    }
    c.execute("INSERT OR REPLACE INTO variation_base VALUES('helpers', ?)", (helpers,))
    main = src[src.index("export default makeScene2D") :]
    c.execute("INSERT OR REPLACE INTO variation_base VALUES('main', ?)", (main,))
    for k, m in enumerate(markers):
        end = markers[k + 1].start() if k + 1 < len(markers) else vars_end
        vid = m.group(1)
        name, usage = meta.get(vid, (m.group(2), ""))[:2]
        thumb = None
        if thumbs and os.path.exists(os.path.join(thumbs, vid + ".png")):
            thumb = base64.b64encode(open(os.path.join(thumbs, vid + ".png"), "rb").read()).decode()
        previous = c.execute("SELECT chosen, note FROM list_variations WHERE id=?", (vid,)).fetchone() or (
            0,
            "",
        )
        c.execute(
            "INSERT OR REPLACE INTO list_variations VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                vid,
                name,
                usage,
                m.group(2),
                src[m.start() : end].rstrip() + "\n",
                thumb,
                previous[0],
                previous[1],
                origin,
                time.strftime("%Y-%m-%d %H:%M"),
            ),
        )
    c.commit()
    print(f"{len(markers)} variações salvas em {DB}")


def list_variants():
    """Lista as variações (★ = escolhida) com nome, uso e nota."""
    c = connect()
    ensure_variant_tables(c)
    for r in c.execute(
        "SELECT id, name, usage, chosen, note, length(thumb_base64) IS NOT NULL FROM list_variations ORDER BY id"
    ):
        print(f"{r[0]}  {'★' if r[3] else ' '} {r[1]:28s} {r[2]}" + (f"  [{r[4]}]" if r[4] else ""))


def choose_variant(variant_id, note=""):
    """Marca uma variação como a escolhida/em uso, com uma nota opcional."""
    c = connect()
    ensure_variant_tables(c)
    c.execute("UPDATE list_variations SET chosen=1, note=? WHERE id=?", (note, variant_id))
    c.commit()
    print("marcada:", variant_id)


def export_variant(ids, destination="src/scenes/variations.tsx"):
    """Remonta um `.tsx` executável só com as variações pedidas (ou `everything`) e exporta as logos que elas usam."""
    c = connect()
    ensure_variant_tables(c)
    sel = (
        [r[0] for r in c.execute("SELECT id FROM list_variations ORDER BY id")]
        if ids == "everything"
        else [i.strip() for i in ids.split(",")]
    )
    helpers = c.execute("SELECT code FROM variation_base WHERE key='helpers'").fetchone()[0]
    main = c.execute("SELECT code FROM variation_base WHERE key='main'").fetchone()[0]
    body, variant_rows = "", []
    for vid in sel:
        r = c.execute("SELECT name, usage, code FROM list_variations WHERE id=?", (vid,)).fetchone()
        assert r, f"variação {vid} não existe"
        body += r[2] + "\n"
        variant_rows.append(f"  ['{vid}', '{r[0]}', '{r[1]}', v{vid[1:]}],")
    os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)
    open(destination, "w", encoding="utf8").write(
        helpers
        + body
        + "const VARS: [string, string, string, (r: Node) => ThreadGenerator][] = [\n"
        + "\n".join(variant_rows)
        + "\n];\n\n"
        + main
    )
    used = set(re.findall(r"logo_[a-z0-9_]+", body + helpers))
    print(f"gravado {destination} com {len(sel)} variações; imagens usadas: {sorted(used)}")
    (
        export_assets("logo_%", os.path.join(os.path.dirname(os.path.dirname(destination)) or ".", "images"))
        if os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(destination)) or ".", "images"))
        else None
    )


def list_assets(filter="%"):
    """Lista os assets do banco (categoria, nome, tipo, dimensões e tamanho) que casam com o filtro."""
    for r in connect().execute(
        "SELECT name, ext, width, height, category, ROUND(bytes/1024.0) FROM assets WHERE name LIKE ? ORDER BY category, name",
        (filter,),
    ):
        print(f"{r[4]:11} {r[0]:34} {r[1]:4} {r[2]}x{r[3]}  {int(r[5])} KB")


def export_assets(pattern, destination="src/images"):
    """Grava em `destination` os arquivos decodificados dos assets que casam com o padrão."""
    os.makedirs(destination, exist_ok=True)
    n = 0
    for name, ext, b64 in connect().execute("SELECT name, ext, base64 FROM assets WHERE name LIKE ?", (pattern,)):
        open(os.path.join(destination, f"{name}.{ext}"), "wb").write(base64.b64decode(b64))
        n += 1
    print(f"{n} arquivo(s) exportado(s) para {destination}")


if __name__ == "__main__":
    args = sys.argv[1:] or ["sync"]
    if args[0] == "sync":
        sync(args[1:] or [p for p in (os.path.join(ROOT, "assets"), "src/images") if os.path.isdir(p)])
    elif args[0] == "list":
        list_assets(args[1] if len(args) > 1 else "%")
    elif args[0] == "export":
        export_assets(args[1], args[2] if len(args) > 2 else "src/images")
    elif args[0] == "transcript-save":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("json")
        ap.add_argument("audio")
        ap.add_argument("--model", default="large-v3")
        ap.add_argument("--aligned", action="store_true")
        ap.add_argument("--note", default="")
        x = ap.parse_args(args[1:])
        save_transcript(x.json, x.audio, x.model, x.aligned, x.note)
    elif args[0] == "transcript-find":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("audio")
        ap.add_argument("--output", default="transcription.json")
        ap.add_argument("--only-aligned", action="store_true")
        x = ap.parse_args(args[1:])
        sys.exit(find_transcript(x.audio, x.output, x.only_aligned))
    elif args[0] == "transcript-list":
        list_transcripts()
    elif args[0] == "video-register":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("file")
        ap.add_argument("--category", default="video_filler")
        ap.add_argument("--note", default="")
        x = ap.parse_args(args[1:])
        register_video(x.file, x.category, x.note)
    elif args[0] == "video-list":
        list_videos(args[1] if len(args) > 1 else "%")
    elif args[0] == "variant-save":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("file")
        ap.add_argument("--thumbs")
        ap.add_argument("--origin", default="")
        x = ap.parse_args(args[1:])
        save_variant(x.file, x.thumbs, x.origin)
    elif args[0] == "variant-list":
        list_variants()
    elif args[0] == "variant-choose":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("id")
        ap.add_argument("--note", default="")
        x = ap.parse_args(args[1:])
        choose_variant(x.id, x.note)
    elif args[0] == "variant-export":
        export_variant(args[1], args[2] if len(args) > 2 else "src/scenes/variations.tsx")
    elif args[0] == "open":
        subprocess.run(["sqlite3", "-header", "-column", DB])
    else:
        print(__doc__)
