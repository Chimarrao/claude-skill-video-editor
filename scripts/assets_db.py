#!/usr/bin/env python3
"""Banco SQLite de assets (base64) da skill: banco/assets.db
Comandos:
  assets_db.py sincronizar [pasta ...]   importa imagens (default: assets/ + ./src/images do projeto atual) sem duplicar (por nome)
  assets_db.py listar [filtro]            lista nome, tipo, dimensões, categoria
  assets_db.py exportar <nome|%padrao> [destino=src/images]   grava os arquivos decodificados
  assets_db.py abrir                      abre o sqlite3 interativo
  assets_db.py trans-salvar <transcricao.json> <audio> [--modelo large-v3] [--alinhado] [--nota "..."]   grava a transcrição (+modelo) no banco
  assets_db.py trans-buscar <audio> [--saida transcricao.json] [--so-alinhada]   reaproveita (por SHA-1 do áudio); sai 0 se achou, 3 se não
  assets_db.py video-registrar <arquivo> [--categoria video_preenchimento] [--nota ..]   registra SÓ a referência (caminho relativo, duração, resolução, fps, tamanho, sha256) — nunca base64
  assets_db.py video-listar [categoria]
  assets_db.py trans-listar                lista as transcrições salvas
  assets_db.py var-salvar <variacoes.tsx> [--thumbs pasta(VNN.png)] [--origem "..."]   salva as VARIAÇÕES DE LISTA (código de cada Vnn + helpers + miniatura) no banco
  assets_db.py var-listar                  lista id, nome, uso, escolhida
  assets_db.py var-exportar <V07,V03|tudo> [destino=src/scenes/variacoes.tsx]   remonta um .tsx executável só com as variações pedidas (+ exporta as imagens usadas)
  assets_db.py var-escolher <V07> [--nota ".."]   marca uma variação como escolhida/em uso
Tabelas: variacoes_lista(id PK, nome, uso, descricao, codigo, thumb_base64, escolhida, nota, origem, criado), variacoes_base(chave PK: helpers|main, codigo), transcricoes(sha1 PK, arquivo, bytes, duracao, modelo, alinhado, alinhador, idioma, criado, nota, json) e assets(nome PK, ext, mime, bytes, largura, altura, categoria, origem, adicionado, base64).
"""

import base64, glob, io, json, mimetypes, os, re, sqlite3, subprocess, sys, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(RAIZ, "banco", "assets.db")
os.makedirs(os.path.dirname(DB), exist_ok=True)


def con():
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS assets(nome TEXT PRIMARY KEY, ext TEXT, mime TEXT, bytes INTEGER,
        largura INTEGER, altura INTEGER, categoria TEXT, origem TEXT, adicionado TEXT, base64 TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS i_cat ON assets(categoria)")
    return c


def categoria(n):
    for p, c in (
        ("logo_", "logo"),
        ("foto_", "pessoa"),
        ("tela_", "tela"),
        ("ic-", "icone"),
        ("placeholder", "placeholder"),
    ):
        if n.startswith(p):
            return c
    return "objeto"


def dims(path, ext):
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


def sincronizar(pastas):
    c = con()
    novos = 0
    for pasta in pastas:
        for f in sorted(glob.glob(os.path.join(pasta, "*"))):
            b = os.path.basename(f)
            nome, ext = os.path.splitext(b)
            ext = ext.lstrip(".").lower()
            if ext not in ("png", "jpg", "jpeg", "webp", "svg", "gif"):
                continue
            if nome.endswith("-mono") or nome.startswith("ic-"):
                continue  # gerados automaticamente pelo plano.py
            if c.execute("SELECT 1 FROM assets WHERE nome=?", (nome,)).fetchone():
                continue
            w, h = dims(f, ext)
            c.execute(
                "INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    nome,
                    ext,
                    mimetypes.guess_type(b)[0] or "image/" + ext,
                    os.path.getsize(f),
                    w,
                    h,
                    categoria(nome),
                    os.path.relpath(pasta),
                    time.strftime("%Y-%m-%d"),
                    base64.b64encode(open(f, "rb").read()).decode(),
                ),
            )
            novos += 1
    c.commit()
    print(f"{novos} novo(s); total {c.execute('SELECT COUNT(*) FROM assets').fetchone()[0]}  -> {DB}")


def sha1(path):
    import hashlib

    h = hashlib.sha1()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def trans_tabela(c):
    c.execute(
        """CREATE TABLE IF NOT EXISTS transcricoes(sha1 TEXT, modelo TEXT, alinhado INTEGER, arquivo TEXT, bytes INTEGER, duracao REAL,
        alinhador TEXT, idioma TEXT, criado TEXT, nota TEXT, json TEXT, PRIMARY KEY(sha1, modelo, alinhado))"""
    )


def trans_salvar(jpath, audio, modelo="large-v3", alinhado=False, nota=""):
    c = con()
    trans_tabela(c)
    d = json.load(open(jpath))
    c.execute(
        "INSERT OR REPLACE INTO transcricoes VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            sha1(audio),
            modelo,
            int(alinhado),
            os.path.basename(audio),
            os.path.getsize(audio),
            d.get("duration"),
            "wav2vec2-large-xlsr-53-portuguese (CTC)" if alinhado else None,
            "pt",
            time.strftime("%Y-%m-%d %H:%M"),
            nota,
            open(jpath, encoding="utf-8").read(),
        ),
    )
    c.commit()
    print(
        f"transcrição salva (modelo {modelo}, {'alinhada' if alinhado else 'bruta'}) para {os.path.basename(audio)}"
    )


def trans_buscar(audio, saida="transcricao.json", so_alinhada=False):
    c = con()
    trans_tabela(c)
    q = (
        "SELECT json, modelo, alinhado, criado FROM transcricoes WHERE sha1=?"
        + (" AND alinhado=1" if so_alinhada else "")
        + " ORDER BY alinhado DESC, criado DESC"
    )
    r = c.execute(q, (sha1(audio),)).fetchone()
    if not r:
        print("transcrição não encontrada no banco")
        return 3
    open(saida, "w", encoding="utf-8").write(r[0])
    print(
        f"transcrição reaproveitada do banco ({r[1]}, {'alinhada' if r[2] else 'bruta'}, {r[3]}) -> {saida}"
    )
    return 0


def trans_listar():
    c = con()
    trans_tabela(c)
    for r in c.execute(
        "SELECT arquivo, modelo, alinhado, ROUND(duracao), criado, substr(sha1,1,8) FROM transcricoes ORDER BY criado"
    ):
        print(r)


def videos_tabela(c):
    c.execute(
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


def video_registrar(arq, categoria="video_preenchimento", nota=""):
    c = con()
    videos_tabela(c)
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
            arq,
        ],
        capture_output=True,
        text=True,
    )
    d = json.loads(r.stdout)
    st = d["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    rel = os.path.relpath(os.path.abspath(arq), RAIZ)  # relativo à pasta da skill
    c.execute(
        "INSERT OR REPLACE INTO videos VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            os.path.basename(arq),
            rel,
            categoria,
            float(d["format"]["duration"]),
            st["width"],
            st["height"],
            round(float(num) / float(den), 3),
            os.path.getsize(arq),
            sha256(arq),
            st["codec_name"],
            time.strftime("%Y-%m-%d"),
            nota,
        ),
    )
    c.commit()
    print(f"vídeo registrado (referência): {os.path.basename(arq)} -> {rel}")


def video_listar(cat="%"):
    c = con()
    videos_tabela(c)
    for r in c.execute(
        "SELECT nome, categoria, caminho, ROUND(duracao,2), largura||'x'||altura, fps, ROUND(bytes/1048576.0)||' MB', substr(sha256,1,12) FROM videos WHERE categoria LIKE ?",
        (cat,),
    ):
        print(r)


def var_tabelas(c):
    c.execute(
        """CREATE TABLE IF NOT EXISTS variacoes_lista(id TEXT PRIMARY KEY, nome TEXT, uso TEXT, descricao TEXT, codigo TEXT, thumb_base64 TEXT,
        escolhida INTEGER DEFAULT 0, nota TEXT, origem TEXT, criado TEXT)"""
    )
    c.execute("CREATE TABLE IF NOT EXISTS variacoes_base(chave TEXT PRIMARY KEY, codigo TEXT)")


def var_salvar(arq, thumbs=None, origem=""):
    src = open(arq, encoding="utf8").read()
    c = con()
    var_tabelas(c)
    marcas = list(re.finditer(r"^// ---------- (V\d+): (.+?) ---------- *$", src, re.M))
    assert marcas, "nenhum marcador '// ---------- Vnn: Nome ----------' no arquivo"
    fim_vars = re.search(r"^const VARS", src, re.M).start()
    helpers = src[: marcas[0].start()]
    resto = src[fim_vars:]
    meta = {
        m.group(1): (m.group(2), m.group(3))
        for m in re.finditer(r"\['(V\d+)', '([^']*)', '([^']*)', v\d+\]", src)
    }
    c.execute("INSERT OR REPLACE INTO variacoes_base VALUES('helpers', ?)", (helpers,))
    main = src[src.index("export default makeScene2D") :]
    c.execute("INSERT OR REPLACE INTO variacoes_base VALUES('main', ?)", (main,))
    for k, m in enumerate(marcas):
        fim = marcas[k + 1].start() if k + 1 < len(marcas) else fim_vars
        vid = m.group(1)
        nome, uso = meta.get(vid, (m.group(2), ""))[:2]
        thumb = None
        if thumbs and os.path.exists(os.path.join(thumbs, vid + ".png")):
            thumb = base64.b64encode(open(os.path.join(thumbs, vid + ".png"), "rb").read()).decode()
        ant = c.execute("SELECT escolhida, nota FROM variacoes_lista WHERE id=?", (vid,)).fetchone() or (
            0,
            "",
        )
        c.execute(
            "INSERT OR REPLACE INTO variacoes_lista VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                vid,
                nome,
                uso,
                m.group(2),
                src[m.start() : fim].rstrip() + "\n",
                thumb,
                ant[0],
                ant[1],
                origem,
                time.strftime("%Y-%m-%d %H:%M"),
            ),
        )
    c.commit()
    print(f"{len(marcas)} variações salvas em {DB}")


def var_listar():
    c = con()
    var_tabelas(c)
    for r in c.execute(
        "SELECT id, nome, uso, escolhida, nota, length(thumb_base64) IS NOT NULL FROM variacoes_lista ORDER BY id"
    ):
        print(f"{r[0]}  {'★' if r[3] else ' '} {r[1]:28s} {r[2]}" + (f"  [{r[4]}]" if r[4] else ""))


def var_escolher(vid, nota=""):
    c = con()
    var_tabelas(c)
    c.execute("UPDATE variacoes_lista SET escolhida=1, nota=? WHERE id=?", (nota, vid))
    c.commit()
    print("marcada:", vid)


def var_exportar(ids, destino="src/scenes/variacoes.tsx"):
    c = con()
    var_tabelas(c)
    sel = (
        [r[0] for r in c.execute("SELECT id FROM variacoes_lista ORDER BY id")]
        if ids == "tudo"
        else [i.strip() for i in ids.split(",")]
    )
    helpers = c.execute("SELECT codigo FROM variacoes_base WHERE chave='helpers'").fetchone()[0]
    main = c.execute("SELECT codigo FROM variacoes_base WHERE chave='main'").fetchone()[0]
    corpo, vars_ = "", []
    for vid in sel:
        r = c.execute("SELECT nome, uso, codigo FROM variacoes_lista WHERE id=?", (vid,)).fetchone()
        assert r, f"variação {vid} não existe"
        corpo += r[2] + "\n"
        vars_.append(f"  ['{vid}', '{r[0]}', '{r[1]}', v{vid[1:]}],")
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    open(destino, "w", encoding="utf8").write(
        helpers
        + corpo
        + "const VARS: [string, string, string, (r: Node) => ThreadGenerator][] = [\n"
        + "\n".join(vars_)
        + "\n];\n\n"
        + main
    )
    usadas = set(re.findall(r"logo_[a-z0-9_]+", corpo + helpers))
    print(f"gravado {destino} com {len(sel)} variações; imagens usadas: {sorted(usadas)}")
    (
        exportar("logo_%", os.path.join(os.path.dirname(os.path.dirname(destino)) or ".", "images"))
        if os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(destino)) or ".", "images"))
        else None
    )


def listar(filtro="%"):
    for r in con().execute(
        "SELECT nome, ext, largura, altura, categoria, ROUND(bytes/1024.0) FROM assets WHERE nome LIKE ? ORDER BY categoria, nome",
        (filtro,),
    ):
        print(f"{r[4]:11} {r[0]:34} {r[1]:4} {r[2]}x{r[3]}  {int(r[5])} KB")


def exportar(padrao, destino="src/images"):
    os.makedirs(destino, exist_ok=True)
    n = 0
    for nome, ext, b64 in con().execute("SELECT nome, ext, base64 FROM assets WHERE nome LIKE ?", (padrao,)):
        open(os.path.join(destino, f"{nome}.{ext}"), "wb").write(base64.b64decode(b64))
        n += 1
    print(f"{n} arquivo(s) exportado(s) para {destino}")


if __name__ == "__main__":
    a = sys.argv[1:] or ["sincronizar"]
    if a[0] == "sincronizar":
        sincronizar(a[1:] or [p for p in (os.path.join(RAIZ, "assets"), "src/images") if os.path.isdir(p)])
    elif a[0] == "listar":
        listar(a[1] if len(a) > 1 else "%")
    elif a[0] == "exportar":
        exportar(a[1], a[2] if len(a) > 2 else "src/images")
    elif a[0] == "trans-salvar":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("json")
        ap.add_argument("audio")
        ap.add_argument("--modelo", default="large-v3")
        ap.add_argument("--alinhado", action="store_true")
        ap.add_argument("--nota", default="")
        x = ap.parse_args(a[1:])
        trans_salvar(x.json, x.audio, x.modelo, x.alinhado, x.nota)
    elif a[0] == "trans-buscar":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("audio")
        ap.add_argument("--saida", default="transcricao.json")
        ap.add_argument("--so-alinhada", action="store_true")
        x = ap.parse_args(a[1:])
        sys.exit(trans_buscar(x.audio, x.saida, x.so_alinhada))
    elif a[0] == "trans-listar":
        trans_listar()
    elif a[0] == "video-registrar":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("arq")
        ap.add_argument("--categoria", default="video_preenchimento")
        ap.add_argument("--nota", default="")
        x = ap.parse_args(a[1:])
        video_registrar(x.arq, x.categoria, x.nota)
    elif a[0] == "video-listar":
        video_listar(a[1] if len(a) > 1 else "%")
    elif a[0] == "var-salvar":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("arq")
        ap.add_argument("--thumbs")
        ap.add_argument("--origem", default="")
        x = ap.parse_args(a[1:])
        var_salvar(x.arq, x.thumbs, x.origem)
    elif a[0] == "var-listar":
        var_listar()
    elif a[0] == "var-escolher":
        import argparse

        ap = argparse.ArgumentParser()
        ap.add_argument("id")
        ap.add_argument("--nota", default="")
        x = ap.parse_args(a[1:])
        var_escolher(x.id, x.nota)
    elif a[0] == "var-exportar":
        var_exportar(a[1], a[2] if len(a) > 2 else "src/scenes/variacoes.tsx")
    elif a[0] == "abrir":
        subprocess.run(["sqlite3", "-header", "-column", DB])
    else:
        print(__doc__)
