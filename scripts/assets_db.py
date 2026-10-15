#!/usr/bin/env python3
"""Banco SQLite de assets (base64) da skill: banco/assets.db
Comandos (nomes antigos em pt mantidos como apelido por compatibilidade):
  assets_db.py sync [pasta ...]   importa imagens (default: assets/ + ./src/images do projeto atual) sem duplicar (por nome)
  assets_db.py list [filtro]            lista nome, tipo, dimensões, categoria
  assets_db.py export <nome|%padrao> [destino=src/images]   grava os arquivos decodificados
  assets_db.py open                      abre o sqlite3 interativo
  assets_db.py transcript-save <transcricao.json> <audio> [--model large-v3] [--aligned] [--note "..."]   grava a transcrição (+modelo) no banco
  assets_db.py transcript-find <audio> [--output transcricao.json] [--only-aligned]   reaproveita (por SHA-1 do áudio); sai 0 se achou, 3 se não
  assets_db.py video-register <arquivo> [--category video_preenchimento] [--note ..]   registra SÓ a referência (caminho relativo, duração, resolução, fps, tamanho, sha256) — nunca base64
  assets_db.py video-list [categoria]
  assets_db.py transcript-list                lista as transcrições salvas
  assets_db.py variant-save <variacoes.tsx> [--thumbs pasta(VNN.png)] [--origin "..."]   salva as VARIAÇÕES DE LISTA (código de cada Vnn + helpers + miniatura) no banco
  assets_db.py variant-list                  lista id, nome, uso, escolhida
  assets_db.py variant-export <V07,V03|tudo> [destino=src/scenes/variacoes.tsx]   remonta um .tsx executável só com as variações pedidas (+ exporta as imagens usadas)
  assets_db.py variant-choose <V07> [--note ".."]   marca uma variação como escolhida/em uso
Tabelas: variacoes_lista(id PK, nome, uso, descricao, codigo, thumb_base64, escolhida, nota, origem, criado), variacoes_base(chave PK: helpers|main, codigo), transcricoes(sha1 PK, arquivo, bytes, duracao, modelo, alinhado, alinhador, idioma, criado, nota, json) e assets(nome PK, ext, mime, bytes, largura, altura, categoria, origem, adicionado, base64).
"""

import base64, glob, io, json, mimetypes, os, re, sqlite3, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "banco", "assets.db")
os.makedirs(os.path.dirname(DB), exist_ok=True)


def connect():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS assets(nome TEXT PRIMARY KEY, ext TEXT, mime TEXT, bytes INTEGER,
        largura INTEGER, altura INTEGER, categoria TEXT, origem TEXT, adicionado TEXT, base64 TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS i_cat ON assets(categoria)")
    return c


def category(name):
    for prefix, cat in (
        ("logo_", "logo"),
        ("foto_", "pessoa"),
        ("tela_", "tela"),
        ("ic-", "icone"),
        ("placeholder", "placeholder"),
    ):
        if name.startswith(prefix):
            return cat
    return "objeto"


def dimensions(path, ext):
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
    conn = connect()
    new_count = 0
    for folder in folders:
        for file_path in sorted(glob.glob(os.path.join(folder, "*"))):
            basename = os.path.basename(file_path)
            name, ext = os.path.splitext(basename)
            ext = ext.lstrip(".").lower()
            if ext not in ("png", "jpg", "jpeg", "webp", "svg", "gif"):
                continue
            if name.endswith("-mono") or name.startswith("ic-"):
                continue  # gerados automaticamente pelo plano.py
            if conn.execute("SELECT 1 FROM assets WHERE nome=?", (name,)).fetchone():
                continue
            w, h = dimensions(file_path, ext)
            conn.execute(
                "INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    name,
                    ext,
                    mimetypes.guess_type(basename)[0] or "image/" + ext,
                    os.path.getsize(file_path),
                    w,
                    h,
                    category(name),
                    os.path.relpath(folder),
                    time.strftime("%Y-%m-%d"),
                    base64.b64encode(open(file_path, "rb").read()).decode(),
                ),
            )
            new_count += 1
    conn.commit()
    print(f"{new_count} novo(s); total {conn.execute('SELECT COUNT(*) FROM assets').fetchone()[0]}  -> {DB}")


def sha1(path):
    import hashlib

    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ensure_transcript_table(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS transcricoes(sha1 TEXT, modelo TEXT, alinhado INTEGER, arquivo TEXT, bytes INTEGER, duracao REAL,
        alinhador TEXT, idioma TEXT, criado TEXT, nota TEXT, json TEXT, PRIMARY KEY(sha1, modelo, alinhado))"""
    )


def save_transcript(json_path, audio, model="large-v3", aligned=False, note=""):
    c = connect()
    ensure_transcript_table(c)
    d = json.load(open(json_path))
    c.execute(
        "INSERT OR REPLACE INTO transcricoes VALUES(?,?,?,?,?,?,?,?,?,?,?)",
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
        f"transcrição salva (modelo {model}, {'alinhada' if aligned else 'bruta'}) para {os.path.basename(audio)}"
    )


def find_transcript(audio, output="transcricao.json", only_aligned=False):
    c = connect()
    ensure_transcript_table(c)
    q = (
        "SELECT json, modelo, alinhado, criado FROM transcricoes WHERE sha1=?"
        + (" AND alinhado=1" if only_aligned else "")
        + " ORDER BY alinhado DESC, criado DESC"
    )
    r = c.execute(q, (sha1(audio),)).fetchone()
    if not r:
        print("transcrição não encontrada no banco")
        return 3
    open(output, "w", encoding="utf-8").write(r[0])
    print(
        f"transcrição reaproveitada do banco ({r[1]}, {'alinhada' if r[2] else 'bruta'}, {r[3]}) -> {output}"
    )
    return 0


def list_transcripts():
    c = connect()
    ensure_transcript_table(c)
    for r in c.execute(
        "SELECT arquivo, modelo, alinhado, ROUND(duracao), criado, substr(sha1,1,8) FROM transcricoes ORDER BY criado"
    ):
        print(r)


def ensure_videos_table(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS videos(nome TEXT PRIMARY KEY, caminho TEXT, categoria TEXT, duracao REAL, largura INTEGER, altura INTEGER,
        fps REAL, bytes INTEGER, sha256 TEXT, codec TEXT, adicionado TEXT, nota TEXT)"""
    )


def sha256(path):
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def register_video(file, category="video_preenchimento", note=""):
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
    c = connect()
    ensure_videos_table(c)
    for r in c.execute(
        "SELECT nome, categoria, caminho, ROUND(duracao,2), largura||'x'||altura, fps, ROUND(bytes/1048576.0)||' MB', substr(sha256,1,12) FROM videos WHERE categoria LIKE ?",
        (cat,),
    ):
        print(r)


def ensure_variant_tables(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS variacoes_lista(id TEXT PRIMARY KEY, nome TEXT, uso TEXT, descricao TEXT, codigo TEXT, thumb_base64 TEXT,
        escolhida INTEGER DEFAULT 0, nota TEXT, origem TEXT, criado TEXT)"""
    )
    conn.execute("CREATE TABLE IF NOT EXISTS variacoes_base(chave TEXT PRIMARY KEY, codigo TEXT)")


def save_variant(file, thumbs=None, origin=""):
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
    c.execute("INSERT OR REPLACE INTO variacoes_base VALUES('helpers', ?)", (helpers,))
    main = src[src.index("export default makeScene2D") :]
    c.execute("INSERT OR REPLACE INTO variacoes_base VALUES('main', ?)", (main,))
    for k, m in enumerate(markers):
        end = markers[k + 1].start() if k + 1 < len(markers) else vars_end
        vid = m.group(1)
        name, usage = meta.get(vid, (m.group(2), ""))[:2]
        thumb = None
        if thumbs and os.path.exists(os.path.join(thumbs, vid + ".png")):
            thumb = base64.b64encode(open(os.path.join(thumbs, vid + ".png"), "rb").read()).decode()
        previous = c.execute("SELECT escolhida, nota FROM variacoes_lista WHERE id=?", (vid,)).fetchone() or (
            0,
            "",
        )
        c.execute(
            "INSERT OR REPLACE INTO variacoes_lista VALUES(?,?,?,?,?,?,?,?,?,?)",
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
    c = connect()
    ensure_variant_tables(c)
    for r in c.execute(
        "SELECT id, nome, uso, escolhida, nota, length(thumb_base64) IS NOT NULL FROM variacoes_lista ORDER BY id"
    ):
        print(f"{r[0]}  {'★' if r[3] else ' '} {r[1]:28s} {r[2]}" + (f"  [{r[4]}]" if r[4] else ""))


def choose_variant(variant_id, note=""):
    c = connect()
    ensure_variant_tables(c)
    c.execute("UPDATE variacoes_lista SET escolhida=1, nota=? WHERE id=?", (note, variant_id))
    c.commit()
    print("marcada:", variant_id)


def export_variant(ids, destination="src/scenes/variacoes.tsx"):
    c = connect()
    ensure_variant_tables(c)
    sel = (
        [r[0] for r in c.execute("SELECT id FROM variacoes_lista ORDER BY id")]
        if ids == "tudo"
        else [i.strip() for i in ids.split(",")]
    )
    helpers = c.execute("SELECT codigo FROM variacoes_base WHERE chave='helpers'").fetchone()[0]
    main = c.execute("SELECT codigo FROM variacoes_base WHERE chave='main'").fetchone()[0]
    body, variant_rows = "", []
    for vid in sel:
        r = c.execute("SELECT nome, uso, codigo FROM variacoes_lista WHERE id=?", (vid,)).fetchone()
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
    for r in connect().execute(
        "SELECT nome, ext, largura, altura, categoria, ROUND(bytes/1024.0) FROM assets WHERE nome LIKE ? ORDER BY categoria, nome",
        (filter,),
    ):
        print(f"{r[4]:11} {r[0]:34} {r[1]:4} {r[2]}x{r[3]}  {int(r[5])} KB")


def export_assets(pattern, destination="src/images"):
    os.makedirs(destination, exist_ok=True)
    n = 0
    for name, ext, b64 in connect().execute("SELECT nome, ext, base64 FROM assets WHERE nome LIKE ?", (pattern,)):
        open(os.path.join(destination, f"{name}.{ext}"), "wb").write(base64.b64decode(b64))
        n += 1
    print(f"{n} arquivo(s) exportado(s) para {destination}")


if __name__ == "__main__":
    args = sys.argv[1:] or ["sync"]
    # Compatibilidade: apelidos antigos em pt para os subcomandos novos em en.
    _aliases = {
        "sincronizar": "sync",
        "listar": "list",
        "exportar": "export",
        "abrir": "open",
        "trans-salvar": "transcript-save",
        "trans-buscar": "transcript-find",
        "trans-listar": "transcript-list",
        "video-registrar": "video-register",
        "video-listar": "video-list",
        "var-salvar": "variant-save",
        "var-listar": "variant-list",
        "var-exportar": "variant-export",
        "var-escolher": "variant-choose",
    }
    args[0] = _aliases.get(args[0], args[0])
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
        ap.add_argument("--output", default="transcricao.json")
        ap.add_argument("--only-aligned", action="store_true")
        x = ap.parse_args(args[1:])
        sys.exit(find_transcript(x.audio, x.output, x.only_aligned))
    elif args[0] == "transcript-list":
        list_transcripts()
    elif args[0] == "video-register":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("file")
        ap.add_argument("--category", default="video_preenchimento")
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
        export_variant(args[1], args[2] if len(args) > 2 else "src/scenes/variacoes.tsx")
    elif args[0] == "open":
        subprocess.run(["sqlite3", "-header", "-column", DB])
    else:
        print(__doc__)
