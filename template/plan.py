"""Gera scenes.json (layout + tempos), .meta (timeEvents) e PLAN.md a partir de transcription.json + plan_data.py.

Cenas contíguas cobrem 100% do áudio: cada cena vai da sua entrada até a entrada da próxima (a saída
acontece 0.3s antes). Dois tipos: G (grafo/árvore de imagens) e T (texto de impacto, sem imagens).
Âncora de tempo: Anchor(segundos_aprox, 'palavra', 'start'|'end') -> timestamp real da palavra.
"""

import warnings

warnings.filterwarnings("ignore")
import glob, json, os, re, unicodedata, urllib.request
from PIL import Image

T = json.load(open(os.environ.get("TRANSCRIPTION", "transcription.json")))
WORDS = [w for s in T["segments"] for w in s["words"]]
DUR = T["duration"]
LEAD = float(
    os.environ.get("LEAD", "0.15")
)  # imagens entram um pouco ANTES da palavra (padrão de edição profissional)
EXIT_TIME = 0.3  # saída termina quando a próxima cena entra
LOGOS_PLATE = set()
AVATAR_ZONE = (
    720,
    300,
)  # (x, y) em coords do centro: canto inferior direito reservado ao avatar do canal (sticker do criador)
MENU_DURATION = 3.7  # tempo ocupado pelo menu na troca de item (as peças só entram depois)
TIPS = []  # sugestões não bloqueantes (impressas no fim)
LIFE_PIECES = {}  # id da cena -> [(entra, some)] das peças (para checar cobertura)
PROMO_T = [
    None,
    None,
]  # (para, retoma): segundo em que a propaganda do CapCut entra (fronteira de cena); gravado em plan.json
TITLES_PIECES = []  # (tempo, duração) dos títulos sobrepostos em itens
WINDOWS_VIDEO = {}  # id de ShortList -> janelas [ini, fim] (pausas) onde o B-roll é permitido
OVERLAY_LIGHT = (
    []
)  # [t0, t1] dos rótulos leves sobre B-roll (webdoc com B-roll): o CapCut mantém overlay só aí e nas janelas sem clipe
JC = {}  # item -> [(t_ini, t_end)] janelas de B-roll (preenchido no main)
CFG = dict(
    HUD=False,
    EXT=False,
    LOGO_TITLECARD=False,
    ANIM_MAX=0.35,
    CLIP_LEAD=0.4,
    CLIP_MARGIN=0.15,
    GRAPH_ZOOM=1.5,
    REQUIRE_LOGO=False,
)  # sobrescrito por plan_data.py
TITLE_STYLE = [
    "monokai"
]  # 'monokai' (terminal, canal de programação) ou 'reportagem' (webdoc); mude com TITLE_STYLE no plan_data
MENU = []  # preenchido por plan_data.py: [(nome, arquivo, cor)]
MIN_DWELL = 1.8  # o último item de cada cena fica pelo menos isso na tela (nada de "piscar")
MIN_INTERVAL = 0.4  # espaçamento mínimo entre itens quando o beat precisa ser antecipado
COLORS = {
    None: "#ffffff",
    "red": "#ff5a5f",
    "amber": "#ffb020",
    "green": "#3ddc97",
    "dark": "#222222",
    "gray": "#75715e",
    "blue": "#66d9ef",
    "yellow": "#e6db74",
}


def ensure_icon(name, color):
    """Ícone de linha Tabler (MIT) recolorido -> src/images/ic-<nome>[-<cor>].svg (baixa e cacheia em icons_base/)."""
    base = f"icons_base/{name}.svg"
    if not os.path.exists(base):
        os.makedirs("icons_base", exist_ok=True)
        url = f"https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{name}.svg"
        try:
            open(base, "wb").write(urllib.request.urlopen(url).read())
        except Exception as e:
            raise SystemExit(f"icone tabler '{name}' nao existe ({e})")
    svg = open(base).read()
    svg = (
        re.sub(r"<!--.*?-->", "", svg, flags=re.S)
        .replace("currentColor", COLORS[color])
        .replace('stroke-width="2"', 'stroke-width="1.6"')
    )
    name_file = f"ic-{name}" + (f"-{color}" if color else "")
    open(f"src/images/{name_file}.svg", "w").write(svg)
    return name_file


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def Anchor(approx, word, side="start"):
    p = norm(word)
    cands = [w for w in WORDS if norm(w["word"]).startswith(p) and abs(w["start"] - approx) < 6]
    if not cands:
        raise SystemExit(f"ancora nao encontrada: {approx} {word}")
    w = min(cands, key=lambda w: abs(w["start"] - approx))
    return round(w[side] - (LEAD if side == "start" else 0), 2)


# ---------- DSL ----------
def Item(
    img,
    label=None,
    at=None,
    id=None,
    parent=None,
    parents=None,
    h=240,
    plate=False,
    circular=False,
    over=None,
    dx=0,
    dy=0,
    highlight=False,
    target=None,
    color=None,
    bezel=None,
    mono=False,
):
    """Item de grafo. em: None (mesmo instante do anterior) | 'palavra' (próxima ocorrência) | ('palavra', seg_aprox).
    pai/pais: id(s) dos itens de onde saem setas. sobre: id do item sobre o qual esta imagem é sobreposta (dx,dy px).
    img 'ic:nome' = ícone de linha Tabler dentro de disco escuro (cor: None/'vermelho'/'ambar'/'verde'); outras = arquivo em src/images.
    """
    if parent:
        parents = [parent]
    if isinstance(img, str) and img.startswith("asset:"):
        img = bring_asset(img)
    return dict(
        img=img,
        label=label,
        at=at,
        id=id,
        parents=parents or [],
        h=h,
        plate=plate,
        circular=circular,
        over=over,
        dx=dx,
        dy=dy,
        highlight=highlight,
        target=target,
        color=color,
        bezel_forced=bezel,
        mono=mono,
    )


def GraphScene(id, entry, items, dir="LR", links=()):
    """Grafo/árvore. dir: LR (esquerda→direita) ou TB (cima→baixo; raízes ficam lado a lado, sem setas = fileira)."""
    return dict(kind="graph", id=id, entry=entry, items=items, dir=dir, links=list(links))


def Phrase(phrase):
    """Âncora por FRASE (robusta a cortes no áudio): primeira ocorrência das palavras seguidas, depois da cena anterior."""
    return dict(_phrase=phrase)


def resolve_phrase(phrase, after):
    toks = [norm(t) for t in phrase.split()]
    for i in range(len(WORDS)):
        if WORDS[i]["start"] < after + 0.05:
            continue
        if all(
            i + k < len(WORDS) and norm(WORDS[i + k]["word"]).startswith(toks[k]) for k in range(len(toks))
        ):
            return round(WORDS[i]["start"] - LEAD, 2)
    raise SystemExit(f"frase nao encontrada apos {after:.1f}s: '{phrase}'")


# --- peças das cenas compostas (item de lista / seção / linha do tempo) ---
def Logo(logo, name, year, color, acronym=None, at=None):
    return dict(
        slot="logo", kind="logo", at=at, props=dict(logo=logo, name=name, year=year, color=color, acronym=acronym)
    )


def FreeLogo(logo, at=None, h=250, plate=None):
    """Logo grande à esquerda (centro-esquerda), SEM cartão quando tem transparência (padrão que o usuário aplicava à mão no CapCut).
    Use o logo do ASSUNTO da animação ao lado (ex.: Tux para uma comparação com Linux), não só o do sistema do item.
    """
    return dict(slot="left", kind="freelogo", at=at, props=dict(logo=logo, h=h, plate_forced=plate))


def People(people, at=None, group=False):
    """pessoas: [(foto|None, nome, papel)]. foto = nome do arquivo em src/images sem extensão (ex.: 'foto_guido_van_rossum')."""
    return dict(
        slot="people",
        kind="people",
        at=at,
        props=dict(people=[dict(photo=f, name=n, role=p) for f, n, p in people], group=group),
    )


def Code(id, at=None):
    return dict(slot="dir", kind="code", at=at, props=dict(id=id))


def Stat(value, label, color="#a6e22e", pct=None, at=None, logo=None):
    if len(str(value)) > 9 or len(label) > 38:
        raise SystemExit(
            f"Stat '{value}' / '{label}': valor <= 9 caracteres e rotulo <= 38 (menos texto, mais imagem)"
        )
    return dict(
        slot="dir", kind="stat", at=at, logo=logo, props=dict(value=value, label=label, color=color, pct=pct)
    )


def Facts(lines, at=None, logo=None):
    """linhas: [('ic:nome', 'texto curto')]"""
    if len(lines) > 3 or any(len(t) > 34 for _, t in lines):
        raise SystemExit(f"Fatos {lines}: no maximo 3 linhas de ate 34 caracteres (muito texto)")
    return dict(
        slot="dir",
        kind="facts",
        at=at,
        logo=logo,
        props=dict(lines=[dict(icon=i, text=t) for i, t in lines]),
    )


def Graph(items, dir="LR", links=(), at=None):
    for _it in items:
        if _it.get("label") and len(_it["label"]) > 26:
            raise SystemExit(f"Grafo: rotulo '{_it['label']}' > 26 caracteres (sobrepoe o vizinho); encurte")
    """Peça de grafo/árvore dentro de um item de lista (região da direita, ~1060x640); os itens aparecem em sequência."""
    return dict(slot="dir", kind="graph", at=at, props=dict(items=items, dir=dir, links=list(links)))


def Comparison(columns, lines, at=None):
    """colunas: [(logo|None, 'Windows 7', '#66d9ef')]; linhas: [('Processador', ('1 GHz','1 GHz · 2 núcleos'), 0|1|None)] (vencedor opcional)."""
    return dict(
        slot="dir",
        kind="comparison",
        at=at,
        props=dict(
            columns=[dict(logo=l, label=r, color=c) for l, r, c in columns],
            lines=[dict(label=a, values=list(b), wins=c) for a, b, c in lines],
        ),
    )


def Screenshot(img, caption, width=900, at=None):
    """Captura de tela/foto grande com moldura e legenda (região da direita). img = nome em src/images OU 'asset:arquivo.jpg' (da pasta Assets/).
    Nunca é esticada além da resolução do arquivo e fica parada (sem zoom lento de enchimento)."""
    if img.startswith("asset:"):
        img = bring_asset(img)
    for e_ in ("png", "jpg", "webp"):
        if os.path.exists(f"src/images/{img}.{e_}"):
            width = min(width, Image.open(f"src/images/{img}.{e_}").size[0])
            break
    if len(caption) > 60:
        raise SystemExit(f"Tela '{img}': legenda > 60 caracteres (curta!)")
    return dict(slot="dir", kind="screen", at=at, props=dict(img=img, caption=caption, width=width))


def Title(lines, dur=3.2, tag="", at=None):
    """Título de impacto (terminal Monokai) sobreposto no topo de um item, sem apagar o resto; some sozinho após `dur` s."""
    return dict(slot="overlay", kind="title", at=at, props=dict(lines=lines, tag=tag, dur=dur))


def ListItem(id, entry, idx, pieces, menu=True, sub="", logo=None):
    """Item da lista: o menu (explorador) aparece na troca de item; depois logo, criadores e código/estatísticas.
    logo: imagem (src/images, sem extensão) do assunto do item — aparece na cartela do item e, por padrão, à esquerda de Stat/Fatos.
    """
    return dict(kind="item", id=id, entry=entry, idx=idx, pieces=pieces, menu=menu, sub=sub, logo=logo)


def expand_logos(scenes):
    """Chamada no main (depois de ler os flags do plan_data): insere FreeLogo antes de cada Stat/Fatos; exige logo quando REQUIRE_LOGO."""
    for c in scenes:
        if c.get("kind") != "item":
            continue
        new = []
        last = None  # (logo, segundos aprox.) do último FreeLogo
        for p in c["pieces"]:
            if p["kind"] in ("stat", "facts"):
                lg = p.get("logo") or c.get("logo")
                if lg:
                    t_ap = p["at"][1] if isinstance(p["at"], tuple) else None
                    same_window = (
                        last
                        and t_ap is not None
                        and last[0] == lg
                        and last[1] is not None
                        and not any(last[1] < a_ and a_ < t_ap for a_, _ in JC.get(c["id"], []))
                    )
                    if not same_window:
                        new.append(FreeLogo(lg, at=p["at"]))
                        last = (lg, t_ap)
                elif CFG["REQUIRE_LOGO"]:
                    raise SystemExit(
                        f"item '{c['id']}': {p['kind']} sem logo (passe logo= na peça ou ListItem(..., logo=...)): quadro só com texto à direita fica vazio"
                    )
            new.append(p)
        c["pieces"] = new


def Section(id, entry, tag, title, sub, logos=()):
    return dict(
        kind="section",
        id=id,
        entry=entry,
        pieces=[
            dict(
                slot="center",
                kind="section",
                at=None,
                props=dict(tag=tag, title=title, sub=sub, logos=list(logos)),
            )
        ],
    )


def Timeline(id, entry, items, milestones):
    """itens: [dict(ano, nome, logo|None, cor, sigla)]; marcos: [(indice_do_item, 'palavra' | None)] em ordem de fala."""
    return dict(kind="timeline", id=id, entry=entry, items=items, milestones=milestones)


def bring_asset(ref):
    """'asset:foto.jpg' -> copia (<= 1800 px) de ../Assets/foto.jpg para src/images/tela_asset_<slug>.<ext> e devolve o nome sem extensão.
    Arquivos da pasta Assets/ do usuário (ou imagens baixadas por você — autorizado, informar no relatório).
    """
    file = ref[6:]
    for folder in ("../Assets", "../assets", "Assets", "assets"):
        src = os.path.join(folder, file)
        if os.path.exists(src):
            break
    else:
        raise SystemExit(f"asset '{file}' nao esta em ../Assets/")
    slug = re.sub(r"[^a-z0-9]+", "_", os.path.splitext(file)[0].lower()).strip("_")[:40]
    ext = os.path.splitext(file)[1].lower().lstrip(".")
    ext = "jpg" if ext in ("jpg", "jpeg") else ("webp" if ext == "webp" else "png")
    name = f"tela_asset_{slug}"
    dst = f"src/images/{name}.{ext}"
    if not os.path.exists(dst):
        im = Image.open(src)
        im.thumbnail((1800, 1800))
        if ext == "jpg":
            im = im.convert("RGB")
        im.save(dst)
    return name


def Center(piece):
    """Move uma peça (Screenshot, Comparison, Graph...) para o centro da tela num Block (por padrão ficam à direita)."""
    return dict(piece, slot="center")


def Block(id, entry, pieces):
    """Cena composta do webdoc SEM menu/cartela de item: as mesmas peças dos itens (Logo, FreeLogo, People, Stat, Facts, Graph, Comparison, Screenshot, Title)
    sobre o preenchimento. Use para o trecho de ANIMAÇÃO do webdoc com B-roll."""
    return dict(kind="section", id=id, entry=entry, pieces=pieces)


def BrollWindow(id, entry, label=None, data=None, logo=None, dur_label=5.0):
    """Janela de B-roll (Webdoc com B-roll): o vídeo da pasta Assets/ roda aqui (BROLL = [(id, arquivo, in, out, vel, t_start)]).
    Overlay LEVE por cima: só um rótulo/data/logo pequeno no canto inferior ESQUERDO (o direito é do avatar), ou nada.
    """
    if label and len(label) > 40:
        raise SystemExit(f"B '{id}': rotulo > 40 caracteres")
    if isinstance(logo, str) and logo.startswith("asset:"):
        logo = bring_asset(logo)
    return dict(
        kind="broll", id=id, entry=entry, label=label, data=data, logo=logo, dur_label=dur_label
    )


def ShortList(id, entry, title, items, color="#66d9ef", pauses=None):
    """Lista curta DENTRO do vídeo (ex.: 'as 8 camadas de segurança'): cartões numerados que entram um a um na fala.
    itens: [('ic:nome', 'rótulo curto', 'palavra' | ('palavra', seg_aprox) | None)]. 2–10 itens, rótulo <= 30 caracteres.
    Tema escuro sério do webdoc (NÃO usa menu explorador nem HUD). Numeração: zero à esquerda só acima de 9 itens.
    pausas: [(em_ini, em_fim), ...] — janelas em que a lista SOME (fade) para rodar B-roll e VOLTA inteira (cartões já vistos) no fim; âncoras como nos itens
    ('palavra' | ('palavra', seg) | seg numérico). Nenhum item pode entrar dentro de uma pausa; o BROLL dessa cena só vale dentro das pausas.
    """
    if not 2 <= len(items) <= 10:
        raise SystemExit(f"ShortList '{id}': use de 2 a 10 itens (tem {len(items)})")
    for ic, label, _ in items:
        if len(label) > 30:
            raise SystemExit(f"ShortList '{id}': rotulo '{label}' > 30 caracteres")
    return dict(
        kind="shortlist",
        id=id,
        entry=entry,
        title=title,
        items=items,
        color=color,
        pauses=list(pauses or []),
    )


def Empty(id, entry):
    """Vazio: nenhuma animação (tela transparente) a partir daqui até a próxima cena."""
    return dict(kind="empty", id=id, entry=entry)


def Impact(id, entry, lines, tag="atenção", style=None):
    """Título de impacto (terminal Monokai). Cores: *rosa*, *v:verde*, *a:azul*, *l:laranja*, *y:amarelo*, *r:roxo*."""
    return dict(kind="impact", id=id, entry=entry, lines=lines, tag=tag, style=style)


# ---------- layout ----------
def _library():
    d = os.path.abspath(".")
    while d != "/":
        c = os.path.join(d, ".claude", "skills", "animacao-narracao", "assets")
        if os.path.isdir(c):
            return c
        d = os.path.dirname(d)
    return None


def pull_asset(name):
    """Reaproveita imagens entre projetos: se src/images/<nome>.* não existe, copia da biblioteca da skill (assets/)."""
    lib = _library()
    if not lib:
        return False
    for ext in ("png", "jpg", "webp", "svg"):
        f = os.path.join(lib, f"{name}.{ext}")
        if os.path.exists(f):
            import shutil

            shutil.copy(f, f"src/images/{name}.{ext}")
            return True
    return False


def has_alpha(img):
    """True se a imagem tem transparência real (logo solto sem cartão); svg conta como transparente."""
    if not any(os.path.exists(f"src/images/{img}.{e}") for e in ("png", "jpg", "webp", "svg")):
        pull_asset(img)
    if any(os.path.exists(f"src/images/{img}.{e}") for e in ("svg",)):
        return True
    for ext in ("png", "webp"):
        p = f"src/images/{img}.{ext}"
        if os.path.exists(p):
            im = Image.open(p)
            if im.mode in ("RGBA", "LA") or "transparency" in im.info:
                a = im.convert("RGBA").getchannel("A")
                return a.getextrema()[0] < 250
            return False
    return False


def needs_plate(img):
    """Logo vai em cartão branco quando é opaco OU escuro demais para o fundo escuro (texto preto sobre transparência some)."""
    if not has_alpha(img):
        return True
    if (
        img in LOGOS_PLATE
    ):  # logos cujo texto/traço é cinza/escuro e some no fundo escuro (plan_data: LOGOS_WITH_PLATE)
        return True
    for ext in ("png", "webp"):
        p = f"src/images/{img}.{ext}"
        if os.path.exists(p):
            im = Image.open(p).convert("RGBA")
            px = [q for q in list(im.resize((64, 64)).getdata()) if q[3] > 128]
            if not px:
                return True
            lum = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b, _ in px) / len(px)
            dark = sum(1 for r, g, b, _ in px if 0.2126 * r + 0.7152 * g + 0.0722 * b < 60) / len(px)
            return lum < 90 or dark > 0.10  # texto preto sobre transparência some no fundo escuro
    return False


def aspect(img):
    if not any(os.path.exists(f"src/images/{img}.{e}") for e in ("png", "jpg", "webp", "svg")):
        pull_asset(img)
    for ext in ("png", "jpg", "webp"):
        p = f"src/images/{img}.{ext}"
        if os.path.exists(p):
            w, h = Image.open(p).size
            return w / h
    if os.path.exists(f"src/images/{img}.svg"):
        m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', open(f"src/images/{img}.svg").read())
        return float(m.group(1)) / float(m.group(2)) if m else 1.0
    raise SystemExit(f"imagem nao encontrada: {img}")


PLATE_K = 1.35  # altura da placa = h * PLATE_K (h = "tamanho nominal" do logo)
SIZE_LABEL = 36


def geom(it):
    """Geometria final do item em px (antes da escala do layout): placa (pw,ph), imagem (iw,ih), caixa total (w,h)."""
    h = it["h"]
    if it["circular"] or it.get("bezel"):
        w_, h_ = h, h
        g = dict(pw=None, ph=None, iw=h, ih=h)
    elif it["plate"]:
        a = aspect(it["img"])
        ph = h * PLATE_K
        ih = ph * 0.62
        iw = ih * a
        if iw > ph * 2.4:
            iw = ph * 2.4
            ih = iw / a
        if a < 1:  # logos altos: limita pela largura
            iw = min(iw, ph * 0.62)
            ih = iw / a
            ih = min(ih, ph * 0.7)
            iw = ih * a
        pw = max(ph, iw + 0.34 * ph)
        g = dict(pw=pw, ph=ph, iw=iw, ih=ih)
        w_, h_ = pw, ph
    else:
        a = aspect(it["img"])
        g = dict(pw=None, ph=None, iw=h * a, ih=h)
        w_, h_ = h * a, h
    if it["label"]:
        h_ += 2 * (SIZE_LABEL * 1.35) + 8  # espaçador simétrico + rótulo
        w_ = max(w_, len(it["label"]) * SIZE_LABEL * 0.58)
    g["w"], g["h"] = w_, h_
    return g


def box(it):
    g = geom(it)
    return g["w"], g["h"]


def scale_geom(it, s):
    if not it["img"]:
        return {}
    g = geom(it)
    return {k: (round(v * s, 1) if v else None) for k, v in g.items() if k in ("pw", "ph", "iw", "ih")}


def rectangle(it, o):
    g = geom(it)
    s = o["h"] / it["h"] if it["h"] else 1
    w, h = g["w"] * s, g["h"] * s
    return o["x"] - w / 2, o["y"] - h / 2, o["x"] + w / 2, o["y"] + h / 2


def check_proportion(items, out, s, where):
    """Sobreposição entre itens independentes (não 'sobre') e desproporção entre irmãos (mesma altura nominal esperada)."""
    base = [i for i, it in enumerate(items) if it["img"] and not it["over"]]
    errors = []
    for ia in range(len(base)):
        for ib in range(ia + 1, len(base)):
            a, b = base[ia], base[ib]
            ra, rb = rectangle(items[a], out[a]), rectangle(items[b], out[b])
            ox = min(ra[2], rb[2]) - max(ra[0], rb[0])
            oy = min(ra[3], rb[3]) - max(ra[1], rb[1])
            if ox > 4 and oy > 4:
                errors.append(f"{items[a]['img']} x {items[b]['img']} sobrepostos ({ox:.0f}x{oy:.0f}px)")
    for i in base:
        r = rectangle(items[i], out[i])
        if r[0] < -960 or r[2] > 960 or r[1] < -540 or r[3] > 540:
            errors.append(f"{items[i]['img']} fora da tela")
    groups = {}
    for i in base:
        if out[i].get("ph"):
            groups.setdefault(tuple(items[i]["parents"]), []).append((out[i]["ph"], items[i]["img"]))
    for g in groups.values():  # irmãos (mesmos pais) devem ter placas de altura parecida
        if len(g) > 1 and max(p for p, _ in g) > 1.35 * min(p for p, _ in g):
            errors.append("irmãos com placas desproporcionais: " + ", ".join(f"{n}={p:.0f}" for p, n in g))
    if errors:
        WARNINGS.append(f"[{where}] " + "; ".join(errors))


WARNINGS = []
WARNINGS_GAP = []
WARNINGS_BROLL = []
EV_G = []  # eventos de itens de grafo (palavra a palavra)
EMPTIES = set()


def layout(items, dir_, W=1760, H=940, smax=1.5):
    idx = {it["id"]: i for i, it in enumerate(items) if it["id"]}
    n = len(items)
    base = [i for i, it in enumerate(items) if not it["over"] and it["img"]]
    parents = {i: [idx[p] for p in items[i]["parents"]] for i in base}
    depth = {}
    for _ in range(n + 1):
        for i in base:
            depth[i] = 0 if not parents[i] else max(depth.get(p, 0) for p in parents[i]) + 1
    levels = {}
    for i in base:
        levels.setdefault(depth[i], []).append(i)
    LR = dir_ == "LR"
    extent = {i: box(items[i]) for i in base}
    width = lambda i: extent[i][1] if LR else extent[i][0]  # extensão na direção da "largura" (transversal)
    along = lambda i: extent[i][0] if LR else extent[i][1]  # extensão ao longo da profundidade
    GAPB, GAPD = 70, 230
    pos = {}

    def spread(level, desired):
        order = sorted(level, key=lambda i: (desired[i], i))
        for k, i in enumerate(order):
            pos[i] = desired[i]
            if k:
                j = order[k - 1]
                pos[i] = max(pos[i], pos[j] + (width(i) + width(j)) / 2 + GAPB)
        shift = sum(pos[i] - desired[i] for i in order) / len(order)
        for i in order:
            pos[i] -= shift
        # recompõe espaçamento mínimo após o shift
        for k, i in enumerate(order[1:], 1):
            j = order[k - 1]
            pos[i] = max(pos[i], pos[j] + (width(i) + width(j)) / 2 + GAPB)

    children = {i: [c for c in base if i in parents[c]] for i in base}
    ListItem = max(levels)
    for step in range(3):
        for d in range(ListItem + 1):
            level = levels[d]
            if d == 0 and step == 0:
                des, acc = {}, 0
                for i in level:
                    des[i] = acc + width(i) / 2
                    acc += width(i) + GAPB
            elif d == 0:
                des = {
                    i: (sum(pos[c] for c in children[i]) / len(children[i])) if children[i] else pos[i]
                    for i in level
                }
            else:
                des = {i: sum(pos[p] for p in parents[i]) / len(parents[i]) for i in level}
            spread(level, des)
        for d in range(ListItem - 1, -1, -1):
            des = {
                i: (sum(pos[c] for c in children[i]) / len(children[i])) if children[i] else pos[i]
                for i in levels[d]
            }
            spread(levels[d], des)
    # ALINHAMENTO PELO ÍCONE (não pelo texto): irmãos de um mesmo nível ficam com passo uniforme entre os CENTROS dos ícones,
    # usando o maior item do grupo como medida. Sem isso o rótulo mais longo empurra os vizinhos e os ícones ficam desalinhados.
    for d, level in levels.items():
        groups = {}
        for i in level:
            groups.setdefault(tuple(sorted(parents[i])), []).append(i)
        if (
            len(groups) == 1 and len(level) > 1
        ):  # um único grupo no nível (fileira ou leque): centraliza com passo igual
            step = max(width(i) for i in level) + GAPB
            center = sum(pos[i] for i in level) / len(level)
            for k, i in enumerate(sorted(level, key=lambda i: pos[i])):
                pos[i] = center + (k - (len(level) - 1) / 2) * step
    # coordenada de profundidade
    thickness = {d: max(along(i) for i in levels[d]) for d in levels}
    cd, c = {}, 0
    for d in range(ListItem + 1):
        if d:
            c += thickness[d - 1] / 2 + GAPD + thickness[d] / 2
        cd[d] = c
    ext_along = cd[ListItem] + thickness[ListItem] / 2 + thickness[0] / 2
    lo = min(pos[i] - width(i) / 2 for i in base)
    hi = max(pos[i] + width(i) / 2 for i in base)
    ext_width = hi - lo
    ext_x, ext_y = (ext_along, ext_width) if LR else (ext_width, ext_along)
    s = min(smax, W / ext_x, H / ext_y)  # amplia até `smax` para ocupar a tela
    cl = (lo + hi) / 2
    cp = (cd[0] - thickness[0] / 2 + cd[ListItem] + thickness[ListItem] / 2) / 2
    out = {}
    for i in base:
        a, b = (cd[depth[i]] - cp) * s, (pos[i] - cl) * s
        out[i] = (a, b) if LR else (b, a)
    return out, s, depth


def ensure_mono(img):
    """Logo SVG recolorido em cinza-escuro uniforme (para grupos de logos com cores incoerentes: branco/amarelo/preto)."""
    dst = f"{img}-mono"
    src = f"src/images/{img}.svg"
    if not os.path.exists(src):
        raise SystemExit(f"mono: {img}.svg nao existe (use logo SVG do Simple Icons)")
    svg = open(src).read()
    svg = re.sub(r'fill="#[0-9A-Fa-f]{3,8}"', 'fill="#222222"', svg, count=1)
    open(f"src/images/{dst}.svg", "w").write(svg)
    return dst


def resolve_image(it):
    it["bezel"] = False
    if it["img"] and it["img"].startswith("ic:"):
        parts = it["img"][3:].split(":")
        it["img"] = ensure_icon(parts[0], parts[1] if len(parts) > 1 else it["color"])
        it["bezel"] = it["bezel_forced"] is not False
    elif it["img"] and it.get("mono"):
        it["img"] = ensure_mono(it["img"])


def bus_edges(items, out, pairs, LR):
    """Coordenada comum da dobra dos conectores em cotovelo: leques/convergências usam o mesmo 'barramento' (nada de setas cruzando)."""
    rects = {i: rectangle(items[i], out[i]) for i in {x for p in pairs for x in p}}
    children, parents = {}, {}
    for a, b in pairs:
        children.setdefault(a, []).append(b)
        parents.setdefault(b, []).append(a)
    output = {}
    for a, b in pairs:
        ra, rb = rects[a], rects[b]
        if len(children[a]) > 1:  # leque
            end_a = ra[2] if LR else ra[3]
            begin_b = min((rects[c][0] if LR else rects[c][1]) for c in children[a])
            output[(a, b)] = round((end_a + begin_b) / 2, 1)
        else:  # convergência (ou 1-1)
            end_a = max((rects[p][2] if LR else rects[p][3]) for p in parents[b])
            begin_b = rb[0] if LR else rb[1]
            output[(a, b)] = round((end_a + begin_b) / 2, 1)
    return output


def build_graph(c, t0, t1):
    items = c["items"]
    for it in items:
        resolve_image(it)
    idx = {it["id"]: i for i, it in enumerate(items) if it["id"]}
    pos, s, depth = layout(items, c["dir"])
    # tempos
    cur, names, times = t0, {t0: "in"}, []
    for it in items:
        at = it["at"]
        if at is None:
            t = cur
        else:
            if isinstance(at, tuple):
                t = Anchor(at[1], at[0])
            else:
                p = norm(at)
                cand = [
                    w
                    for w in WORDS
                    if w["start"] >= cur + 0.05 and norm(w["word"]).startswith(p) and w["start"] < t1 - 0.4
                ]
                if not cand:
                    raise SystemExit(f"{c['id']}: palavra '{at}' nao achada entre {cur:.1f} e {t1:.1f}")
                t = round(cand[0]["start"] - LEAD, 2)
        t = max(t, cur)
        times.append(t)
        cur = t
    # permanência mínima: antecipa os últimos beats (de trás para frente) para nada "piscar"
    out_t = t1 - EXIT_TIME
    beats = sorted(set(times))
    new, ceiling = {}, out_t - MIN_DWELL
    for b in reversed(beats):
        new[b] = min(b, ceiling)
        ceiling = new[b] - MIN_INTERVAL
    ant = t0
    for b in beats:  # piso: nunca antes do início da cena; mantém ordem
        new[b] = max(new[b], ant)
        ant = new[b]
    times = [round(new[t], 2) for t in times]
    names = {t0: "in"}
    for t in times:
        if t not in names:
            names[t] = f"b{len(names)}"
    out_items = []
    for i, it in enumerate(items):
        if not it["img"]:
            x, y, h = 0, 0, 0
        elif it["over"]:
            bx, by = pos[idx[it["over"]]]
            x, y, h = bx + it["dx"] * s, by + it["dy"] * s, it["h"] * s
        else:
            x, y = pos[i]
            h = it["h"] * s
        out_items.append(
            dict(
                img=it["img"],
                x=round(x, 1),
                y=round(y, 1),
                h=round(h, 1),
                plate=it["plate"],
                bezel=it["bezel"],
                circular=it["circular"],
                label=it["label"],
                beat=names[times[i]],
                highlight=it["highlight"],
                target=idx[it["target"]] if it["target"] else None,
                **scale_geom(it, s),
            )
        )
    check_proportion(items, out_items, s, c["id"])
    # arestas
    LR = c["dir"] == "LR"
    sides = ("right", "left") if LR else ("bottom", "top")
    edges, seen = [], set()
    pairs = [(idx[p], i) for i, it in enumerate(items) for p in it["parents"]] + [
        (idx[a], idx[b]) for a, b in c["links"]
    ]
    pairs = list(dict.fromkeys(pairs))
    bars = bus_edges(items, out_items, pairs, LR)
    for a, b in pairs:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        dy = abs(out_items[a]["y"] - out_items[b]["y"]) if LR else abs(out_items[a]["x"] - out_items[b]["x"])
        when = (
            a if times[a] > times[b] else b
        )  # a seta se desenha quando o último dos dois extremos aparece
        edges.append(
            dict(
                src=a,
                dst=b,
                when=when,
                sides=list(sides),
                style="straight" if dy < 8 else "elbow",
                bus=bars[(a, b)],
            )
        )
    ev = [(f"{c['id']}-{names[t]}", t) for t in sorted(names)]
    return dict(kind="graph", id=c["id"], items=out_items, edges=edges), ev


def bbox_real(items, out):
    """Caixa que envolve TODOS os itens desenhados (placa + rótulo, com a largura real do logo): (x0, y0, x1, y1) em px."""
    rs = [rectangle(items[i], out[i]) for i in range(len(items)) if items[i]["img"]]
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))


def graph_static(items, dir_, links, W, H):
    """Layout de um grafo/árvore dentro de uma região WxH (para peças de cenas compostas). Revelação sequencial no TS."""
    for it in items:
        resolve_image(it)
    idx = {it["id"]: i for i, it in enumerate(items) if it["id"]}
    pos, s, depth = layout(
        items, dir_, W, H, smax=1.0
    )  # a ampliação final (GRAPH_SCALE) é feita depois, com o bbox real
    out = []
    for i, it in enumerate(items):
        if it["over"]:
            bx, by = pos[idx[it["over"]]]
            x, y, h = bx + it["dx"] * s, by + it["dy"] * s, it["h"] * s
        else:
            x, y = pos[i]
            h = it["h"] * s
        out.append(
            dict(
                img=it["img"],
                x=round(x, 1),
                y=round(y, 1),
                h=round(h, 1),
                plate=it["plate"],
                bezel=it["bezel"],
                circular=it["circular"],
                label=it["label"],
                highlight=False,
                target=None,
                **scale_geom(it, s),
            )
        )
    check_proportion(items, out, s, "peça-grafo")
    LR = dir_ == "LR"
    sides = ("right", "left") if LR else ("bottom", "top")
    edges, seen = [], set()
    pairs = [(idx[p], i) for i, it in enumerate(items) for p in it["parents"]] + [
        (idx[a], idx[b]) for a, b in links
    ]
    pairs = list(dict.fromkeys(pairs))
    bars = bus_edges(items, out, pairs, LR)
    for a, b in pairs:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        dy = abs(out[a]["y"] - out[b]["y"]) if LR else abs(out[a]["x"] - out[b]["x"])
        edges.append(
            dict(
                src=a,
                dst=b,
                when=max(a, b),
                sides=list(sides),
                style="straight" if dy < 8 else "elbow",
                bus=bars[(a, b)],
            )
        )
    bbox = bbox_real(items, out)
    return out, edges, bbox


def build_text(c, t0, t1):
    lines = c["lines"]
    mx = max(len(re.sub(r"\*([a-z]:)?", "", l)) for l in lines) + 2
    style = c.get("style") or TITLE_STYLE[0]
    if style == "report":
        size = int(max(70, min(140, 1600 / (max(len(re.sub(r"\*([a-z]:)?", "", l)) for l in lines) * 0.72))))
    else:
        size = int(max(54, min(96, 1500 / (mx * 0.61))))
    return dict(
        kind="impact", id=c["id"], lines=lines, size=size, tag=c.get("tag", "atenção"), style=style
    ), [(f"{c['id']}-in", t0)]


def resolve_times_pieces(c, pieces, t0, t1, piso):
    """Resolve beats das peças (palavra seguinte à anterior), aplica piso (menu) e permanência mínima."""
    cur = max(t0, piso)
    search = t0
    times = []
    for p in pieces:
        at = p["at"]
        if at is None:
            t = cur
        elif isinstance(at, tuple):
            t = Anchor(at[1], at[0])
            search = t
        else:
            pp = norm(at)
            cand = [
                w
                for w in WORDS
                if w["start"] >= search + 0.05 and norm(w["word"]).startswith(pp) and w["start"] < t1 - 0.4
            ]
            if not cand:
                raise SystemExit(f"{c['id']}: palavra '{at}' nao achada entre {search:.1f} e {t1:.1f}")
            t = round(cand[0]["start"] - LEAD, 2)
            search = t
        t = max(t, cur, piso)
        times.append(t)
        cur = t
    out_t = t1 - EXIT_TIME
    beats = sorted(set(times))
    new, ceiling = {}, out_t - MIN_DWELL
    for b in reversed(beats):
        new[b] = min(b, ceiling)
        ceiling = new[b] - MIN_INTERVAL
    ant = max(t0, piso)
    for b in beats:
        new[b] = max(new[b], ant)
        ant = new[b]
    times = [round(new[t], 2) for t in times]
    # peças NÃO podem aparecer durante um clipe de B-roll: empurra para o fim da janela
    for k, t in enumerate(times):
        for a, b in JC.get(c["id"], []):
            if a - CFG["CLIP_LEAD"] - 0.05 <= t < b + CFG["CLIP_MARGIN"]:
                WARNINGS_BROLL.append(
                    f"[{c['id']}] peça {pieces[k]['kind']} em {t:.1f}s cai dentro do clipe {a:.1f}-{b:.1f}: movida para {b:.1f}s"
                )
                times[k] = round(b + CFG["CLIP_MARGIN"], 2)
    names = {t0: "in"}
    for t in times:
        if t not in names:
            names[t] = f"b{len(names)}"
    return times, names


def build_composite(c, t0, t1):
    pieces = c["pieces"]
    piso = t0 + (MENU_DURATION if c.get("menu") else 0)
    times, names = resolve_times_pieces(c, pieces, t0, t1, piso)
    # GUARDA: peça precisa caber ENTRE clipes (>= 2.5 s de exibição antes do próximo clipe / da próxima peça do mesmo slot); senão é descartada
    manter = []
    for k, (p, t) in enumerate(zip(pieces, times)):
        end = t1 - EXIT_TIME
        for a_, b_ in JC.get(c["id"], []):
            if a_ > t + 0.05:
                end = min(end, a_ - CFG["CLIP_LEAD"] - 0.1)
        if p["slot"] == "dir":
            for p2, t2 in zip(pieces[k + 1 :], times[k + 1 :]):
                if p2["slot"] == "dir" and t2 > t + 0.05:
                    end = min(end, t2)
                    break
        if end - t < 2.5 and p["kind"] != "title":
            WARNINGS_BROLL.append(
                f"[{c['id']}] peça {p['kind']} em {t:.1f}s DESCARTADA: só {max(end - t, 0):.1f}s livres antes do próximo clipe/peça"
            )
        else:
            manter.append(k)
    pieces = [pieces[k] for k in manter]
    times = [times[k] for k in manter]
    out = []
    for p, t in zip(pieces, times):
        props = dict(p["props"])
        if p["kind"] == "logo":
            props["asp"] = round(aspect(props["logo"]), 3) if props.get("logo") else 1
        if p["kind"] == "freelogo":
            props["asp"] = round(aspect(props["logo"]), 3)
            props["plate"] = (
                needs_plate(props["logo"])
                if props.get("plate_forced") is None
                else bool(props["plate_forced"])
            )
        if p["kind"] == "facts":
            props["lines"] = [
                dict(icon=resolve_icon(l["icon"]), text=l["text"]) for l in props["lines"]
            ]
        if p["kind"] == "section":
            props["logos"] = list(props["logos"])
            for _lg in props[
                "logos"
            ]:  # logos da Section: todos do MESMO tamanho (quadrados 96px); logo largo (> 1.3:1) deforma — use o ícone/versão quadrada
                if aspect(_lg) > 1.3 or aspect(_lg) < 0.77:
                    WARNINGS.append(
                        f"[{c['id']}] logo '{_lg}' da Section não é quadrado ({aspect(_lg):.2f}:1): use a versão quadrada/ícone (ex.: logo_win11_icone em vez de logo_microsoft)"
                    )
        if p["kind"] == "graph":
            ats = [it.get("at") for it in props["items"]]
            items_g, edges_g, bbox_g = graph_static(
                props["items"], props["dir"], props["links"], 1700, 800
            )
            events_g, search_g = [], t
            for k_, at_ in enumerate(ats):
                if at_ is None:
                    events_g.append(None)
                    continue
                if isinstance(at_, tuple):
                    tg = Anchor(at_[1], at_[0])
                else:
                    cand = [
                        w
                        for w in WORDS
                        if w["start"] >= search_g + 0.05
                        and norm(w["word"]).startswith(norm(at_))
                        and w["start"] < t1 - 0.4
                    ]
                    if not cand:
                        raise SystemExit(
                            f"{c['id']}: palavra de item de grafo '{at_}' nao achada apos {search_g:.1f}s"
                        )
                    tg = round(cand[0]["start"] - LEAD, 2)
                tg = max(tg, search_g + 0.05)
                for a_, b_ in JC.get(c["id"], []):
                    if a_ - CFG["CLIP_LEAD"] - 0.05 <= tg < b_ + CFG["CLIP_MARGIN"]:
                        WARNINGS.append(
                            f"[{c['id']}] item de grafo em {tg:.1f}s cai dentro do clipe {a_:.1f}-{b_:.1f}: ajuste a janela do clipe/âncora (com STRICT=0 o item é empurrado para depois do clipe, fora de sincronia)"
                        )
                        tg = round(b_ + CFG["CLIP_MARGIN"], 2)
                search_g = tg
                name_g = f"g{len(EV_G)}_{c['id']}"
                EV_G.append((f"{c['id']}-{name_g}", tg))
                events_g.append(f"{c['id']}-{name_g}")
            # o grafo COMPLETO (último item) precisa ficar visível >= 2.5 s antes de um clipe escondê-lo (>= 1.5 s antes do fim da cena)
            _last = max([e[1] for e in EV_G if e[0].startswith(c["id"] + "-")] + [t])
            _clips = [a_ - CFG["CLIP_LEAD"] for a_, _ in JC.get(c["id"], []) if a_ - CFG["CLIP_LEAD"] > t]
            _hides = min(_clips + [t1 - EXIT_TIME])
            _minimum = 2.5 if _clips and min(_clips) < t1 - EXIT_TIME else 1.5
            if _hides - _last < _minimum:
                WARNINGS.append(
                    f"[{c['id']}] grafo de {t:.1f}s não completa: último item em {_last:.1f}s e some em {_hides:.1f}s (< {_minimum} s completo); "
                    f"antecipe os itens, encurte o grafo ou mova o clipe (animação 'só de um lado' é proibida)"
                )
            props = dict(items=items_g, edges=edges_g, events=events_g, zoom=CFG["GRAPH_ZOOM"])
            # Ampliação automática com o bbox REAL (largura de logos incluída): até GRAPH_SCALE, limitada pelo que cabe no quadro (±900 × ±480),
            # recentralizada, e fora da zona do avatar do canal (canto inferior direito).
            if items_g:
                rx0, ry0, rx1, ry1 = bbox_g
                e_ = round(min(CFG["GRAPH_ZOOM"], 1800 / max(rx1 - rx0, 1), 960 / max(ry1 - ry0, 1)), 2)
                props["zoom"] = e_
                cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2  # recentraliza o grafo
                props["dx"], props["dy"] = round(-cx * e_, 1), round(-cy * e_, 1)
                x0, x1, y0, y1 = (rx0 - cx) * e_, (rx1 - cx) * e_, (ry0 - cy) * e_, (ry1 - cy) * e_
                for _k, _g in enumerate(
                    items_g
                ):  # nenhum elemento pode ser gigante (placa larga de logo cortada na borda)
                    _w = max(_g.get("pw") or 0, _g.get("iw") or 0, _g["h"]) * e_
                    _h = max(_g.get("ph") or 0, _g["h"]) * e_
                    if _w > 720 or _h > 520:
                        WARNINGS.append(
                            f"[{c['id']}] item {_k + 1} do grafo ({_g['img']}) fica gigante ({_w:.0f}x{_h:.0f}px): diminua `h` ou use logo mais compacto"
                        )
                if e_ < 1.2:
                    WARNINGS.append(
                        f"[{c['id']}] grafo só cabe ampliado {e_}x (< 1.2x: pequeno demais, o usuário dá zoom à mão): menos itens/ramos"
                    )
                # zona do avatar: só importa se um ITEM (não o canto vazio da caixa) encosta no retângulo do avatar
                for _k, _it in enumerate(props["items"]):
                    if not _it["img"]:
                        continue
                    _r = rectangle(_it, items_g[_k])
                    _rx0, _rx1 = _r[0] * e_ + props["dx"], _r[2] * e_ + props["dx"]
                    _ry0, _ry1 = _r[1] * e_ + props["dy"], _r[3] * e_ + props["dy"]
                    if _rx1 > AVATAR_ZONE[0] and _ry1 > AVATAR_ZONE[1]:
                        WARNINGS.append(
                            f"[{c['id']}] item {_k + 1} do grafo ({_it['img']}) invade a zona do avatar (canto inferior direito): até {_rx1:.0f},{_ry1:.0f}"
                        )
                n_ic = sum(1 for it in props["items"] if str(it["img"]).startswith("ic-"))
                if len(props["items"]) >= 2 and n_ic == len(props["items"]) and not CFG.get("WEBDOC"):
                    TIPS.append(
                        f"[{c['id']}] grafo só com ícones genéricos: se a fala cita produtos/empresas/pessoas, use as logos/fotos reais"
                    )
        if p["kind"] == "title":
            # duração de permanência = o que sobra até o próximo beat (menos entrada digitada, saída e retorno do resto)
            words_t = [w for l in props["lines"] for w in re.sub(r"\*([a-z]:)?", "", l).split()]
            typing = 0.7 + sum(max(0.07, len(w) * 0.028) + 0.04 for w in words_t)
            next_ = [x for x in times if x > t + 0.05] + [t1 - EXIT_TIME]
            margin = min(next_) - t - typing - 0.8
            props["dur"] = round(max(0.6, min(props["dur"], margin)), 2)
            if margin < 0.6:
                WARNINGS.append(
                    f"[{c['id']}] título curto demais antes do próximo beat (folga {margin:.1f}s): mova o título ou o beat seguinte"
                )
            TITLES_PIECES.append((t, props["dur"] + typing))
            mx = max(len(re.sub(r"\*([a-z]:)?", "", l)) for l in props["lines"]) + 2
            props["size"] = int(max(56, min(84, 1500 / (mx * 0.61))))
        out.append(dict(slot=p["slot"], kind=p["kind"], props=props, beat=names[t]))
    LIFE_PIECES[c["id"]] = []
    for _p, _t in zip(pieces, times):
        _some = min(
            [a_ - CFG["CLIP_LEAD"] for a_, _ in JC.get(c["id"], []) if a_ - CFG["CLIP_LEAD"] > _t]
            + [t1 - EXIT_TIME]
        )
        if _p["kind"] != "title":
            LIFE_PIECES[c["id"]].append((_t, _some))
    js = dict(kind="section" if c["kind"] == "section" else "item", id=c["id"], pieces=out)
    if c["kind"] == "item":
        i = c["idx"]
        js.update(
            idx=i,
            total=len(MENU),
            name=MENU[i - 1][0],
            color=MENU[i - 1][2],
            menu=dict(src=i - 2, dst=i - 1) if c.get("menu") else None,
            sub=c.get("sub", ""),
            hud=bool(CFG["HUD"]),
            logo=c.get("logo"),
            logo_plate=bool(c.get("logo") and needs_plate(c["logo"])),
            logo_asp=round(aspect(c["logo"]), 3) if c.get("logo") else 1,
        )
    ev = [(f"{c['id']}-{names[t]}", t) for t in sorted(names)]
    ev += [e for e in EV_G if e[0].startswith(c["id"] + "-")]
    EV_G[:] = [e for e in EV_G if not e[0].startswith(c["id"] + "-")]
    # janelas de B-roll: o motor esconde as peças no início de cada clipe (evento <id>-vaK)
    for k_, (a_, b_) in enumerate(JC.get(c["id"], [])):
        ev.append(
            (f"{c['id']}-va{k_}", round(a_ - CFG["CLIP_LEAD"], 2))
        )  # peças somem ANTES do clipe (nunca vazam alguns frames sobre o B-roll)
    js["nva"] = len(JC.get(c["id"], []))
    ev.sort(key=lambda e: e[1])
    return js, ev


def build_shortlist(c, t0, t1):
    """ShortList: cartões numerados entrando um a um na fala. Eventos <id>-in, <id>-i0..iN, <id>-out."""
    out_t = t1 - EXIT_TIME
    cur = t0 + 0.9
    search = t0
    ev = [(f"{c['id']}-in", t0)]
    items_js = []
    for k, (ic, label, at) in enumerate(c["items"]):
        if at is None:
            t = cur
        elif isinstance(at, tuple):
            t = Anchor(at[1], at[0])
        else:
            pp = norm(at)
            cand = [
                w
                for w in WORDS
                if w["start"] >= search + 0.05 and norm(w["word"]).startswith(pp) and w["start"] < t1 - 0.4
            ]
            if not cand:
                raise SystemExit(
                    f"{c['id']}: palavra '{at}' do item {k + 1} nao achada entre {search:.1f} e {t1:.1f}"
                )
            t = round(cand[0]["start"] - LEAD, 2)
        t = round(max(t, cur), 2)
        if k and t < ev[-1][1] + 1.2 - 1e-6:
            WARNINGS.append(
                f"[{c['id']}] itens {k} e {k + 1} da lista a {t - ev[-1][1]:.1f}s (< 1.2 s): cartões entrando colados"
            )
        ev.append((f"{c['id']}-i{k}", t))
        cur = t + 1.2
        search = t
        parts = ic[3:].split(":") if ic.startswith("ic:") else None
        if not parts:
            raise SystemExit(f"ShortList '{c['id']}': icone '{ic}' deve ser 'ic:nome'")
        items_js.append(
            dict(
                icon=ensure_icon(parts[0], parts[1] if len(parts) > 1 else None), label=label, num=k + 1
            )
        )
    if out_t - ev[-1][1] < 1.6:
        raise SystemExit(
            f"{c['id']}: o ultimo item da lista entra a {out_t - ev[-1][1]:.1f}s do fim da cena (< 1.6 s): estenda a cena ou antecipe o item"
        )
    # pausas: a lista some (fade 0.3 s) para o B-roll e volta inteira; vídeo só vale em [ini+0.35, fim-0.05]
    item_ts = [t for n_, t in ev if "-i" in n_ and not n_.endswith("-in")]
    search_p = t0
    pauses_js = []
    for j, (pa, pb) in enumerate(c.get("pauses") or []):
        tt = []
        for at in (pa, pb):
            if isinstance(at, (int, float)):
                tt.append(float(at))
                continue
            if isinstance(at, tuple):
                tt.append(Anchor(at[1], at[0]))
                continue
            pp = norm(at)
            cand = [
                w
                for w in WORDS
                if w["start"] >= search_p + 0.05 and norm(w["word"]).startswith(pp) and w["start"] < t1 - 0.4
            ]
            if not cand:
                raise SystemExit(f"{c['id']}: palavra '{at}' da pausa {j} nao achada apos {search_p:.1f}s")
            tt.append(round(cand[0]["start"] - LEAD, 2))
        ta, tb = tt
        search_p = tb
        if tb - ta < 4.0:
            raise SystemExit(f"{c['id']}: pausa {j} de {tb - ta:.1f}s (< 4 s: não vale um B-roll)")
        if ta < t0 + 1.0 or tb > out_t - 0.5:
            raise SystemExit(f"{c['id']}: pausa {j} ({ta:.1f}-{tb:.1f}s) fora da cena")
        for ti in item_ts:
            if ta - 0.3 < ti < tb + 0.5:
                raise SystemExit(
                    f"{c['id']}: item da lista a {ti:.1f}s cai dentro da pausa {j} ({ta:.1f}-{tb:.1f}s) (o próximo item precisa entrar >= 0.5 s depois da volta)"
                )
        ev.append((f"{c['id']}-p{j}a", round(ta, 2)))
        ev.append((f"{c['id']}-p{j}b", round(tb, 2)))
        pauses_js.append([round(ta, 2), round(tb, 2)])
        WINDOWS_VIDEO.setdefault(c["id"], []).append([round(ta + 0.35, 2), round(tb - 0.05, 2)])
    ev.sort(key=lambda e: e[1])
    return (
        dict(
            kind="shortlist",
            id=c["id"],
            title=c["title"],
            color=c["color"],
            total=len(c["items"]),
            items=items_js,
            pauses=pauses_js,
        ),
        ev,
    )


def build_broll(c, t0, t1):
    """Janela de B-roll: overlay leve (rótulo/data/logo no canto inferior esquerdo) por ~dur_label s, ou nada."""
    dur = min(float(c["dur_label"]), (t1 - EXIT_TIME - t0) - 1.6)
    has = bool(c.get("label") or c.get("data") or c.get("logo"))
    light = None
    if has and dur >= 1.5:
        light = [round(t0 + 0.6, 2), round(t0 + 0.6 + dur, 2)]
        OVERLAY_LIGHT.append(light)
    elif has:
        print(f"AVISO B-ROLL: [{c['id']}] janela curta demais para o rótulo ({t1 - t0:.1f}s): rótulo omitido")
    js = dict(
        kind="broll",
        id=c["id"],
        label=c.get("label") if light else None,
        data=c.get("data") if light else None,
        dur=round(dur, 2) if light else 0,
        logo=c.get("logo") if light else None,
        logo_asp=round(aspect(c["logo"]), 3) if (light and c.get("logo")) else 1,
        logo_plate=bool(light and c.get("logo") and needs_plate(c["logo"])),
    )
    if light and c.get("data"):
        ensure_icon("calendar", None)
    return js, [(f"{c['id']}-in", t0)]


def build_time(c, t0, t1):
    times = []
    cur = t0
    for i, at in c["milestones"]:
        if at is None:
            t = cur
        else:
            pp = norm(at)
            cand = [
                w
                for w in WORDS
                if w["start"] >= cur + 0.05 and norm(w["word"]).startswith(pp) and w["start"] < t1 - 0.4
            ]
            if not cand:
                raise SystemExit(f"{c['id']}: palavra '{at}' nao achada entre {cur:.1f} e {t1:.1f}")
            t = round(cand[0]["start"] - LEAD, 2)
        times.append(t)
        cur = t
    out_t = t1 - EXIT_TIME
    beats = sorted(set(times))
    new, ceiling = {}, out_t - MIN_DWELL
    for b in reversed(beats):
        new[b] = min(b, ceiling)
        ceiling = new[b] - MIN_INTERVAL
    ant = t0
    for b in beats:
        new[b] = max(new[b], ant)
        ant = new[b]
    times = [round(new[t], 2) for t in times]
    names = {t0: "in"}
    for t in times:
        if t not in names:
            names[t] = f"b{len(names)}"
    items = []
    for it in c["items"]:
        items.append(dict(it))
    milestones = [dict(beat=names[t], i=i) for (i, _), t in zip(c["milestones"], times)]
    js = dict(
        kind="timeline",
        id=c["id"],
        pieces=[dict(slot="center", kind="timeline", props=dict(items=items, milestones=milestones), beat="in")],
    )
    ev = [(f"{c['id']}-{names[t]}", t) for t in sorted(names)]
    return js, ev


def resolve_icon(ref):
    """'ic:nome[:cor]' -> stem do arquivo em src/images (gera o svg)."""
    if ref.startswith("ic:"):
        parts = ref[3:].split(":")
        return ensure_icon(parts[0], parts[1] if len(parts) > 1 else None)
    return ref


def fmt(t):
    return f"{int(t//60):02d}:{t%60:05.2f}"


def phrase(begin, end):
    return " ".join(w["word"].strip() for w in WORDS if w["start"] >= begin - 0.05 and w["end"] <= end + 0.3)


if __name__ == "__main__":
    import importlib

    _pd = importlib.import_module(os.environ.get("PLAN_DATA", "plan_data"))
    SCENES = _pd.SCENES
    LOGOS_PLATE.update(getattr(_pd, "LOGOS_WITH_PLATE", []))
    CFG.update(
        WEBDOC=getattr(_pd, "VIDEO_KIND", "") == "webdoc_broll",
        HUD=bool(getattr(_pd, "HUD_ITEM", False)),
        EXT=bool(getattr(_pd, "MENU_EXTENSIONS", False)),
        LOGO_TITLECARD=bool(getattr(_pd, "TITLECARD_LOGO_REQUIRED", False)),
        ANIM_MAX=float(getattr(_pd, "ANIM_MAX", 0.35)),
        REQUIRE_LOGO=bool(getattr(_pd, "PIECES_REQUIRE_LOGO", False)),
        GRAPH_ZOOM=float(getattr(_pd, "GRAPH_SCALE", 1.5)),
        CLIP_LEAD=float(getattr(_pd, "CLIP_LEAD", 0.4)),
        CLIP_MARGIN=float(getattr(_pd, "CLIP_MARGIN", 0.15)),
    )
    for _c in SCENES:
        if _c.get("kind") == "item" and CFG["LOGO_TITLECARD"] and not _c.get("logo"):
            raise SystemExit(
                f"item '{_c['id']}': cartela sem logo (ListItem(..., logo='logo_x')): o quadro da cartela fica vazio sem a logo do sistema"
            )
    try:
        COVERAGE = _pd.COVERAGE
    except AttributeError:
        COVERAGE = (88, 92)  # padrão: ~90%

    TITLE_STYLE[0] = getattr(_pd, "TITLE_STYLE", "monokai")
    try:
        MENU[:] = _pd.MENU
    except AttributeError:
        pass
    import re as _re

    for _n in set(
        _re.findall(
            r'"((?:logo|foto|tela|ic)_[a-z0-9_]+|microsoft|windows11|logo_exemplo|ram_modulo)"',
            open(os.environ.get("PLAN_DATA", "plan_data") + ".py").read(),
        )
    ):
        if not any(os.path.exists(f"src/images/{_n}.{e}") for e in ("png", "jpg", "webp", "svg")):
            pull_asset(_n)
    if getattr(_pd, "MINIMUM_OVERLAY", False):
        # Lista com B-roll: overlay SÓ com menu+cartela, HUD, e cartela/Section na abertura e no fim. Nada de grafos/setas/fatos/etc.
        for c in SCENES:
            if c["kind"] in ("graph", "impact", "timeline"):
                raise SystemExit(
                    f"MINIMUM_OVERLAY: cena '{c['id']}' do tipo {c['kind']} nao e permitida na Lista com B-roll (use ListItem(..., pieces=[]), Section ou V)"
                )
            if c["kind"] == "item" and c["pieces"]:
                raise SystemExit(
                    f"MINIMUM_OVERLAY: item '{c['id']}' tem pecas; neste tipo o item fica so com B-roll (pieces=[])"
                )
    for _it, _file, _i0, _i1, _speed, _t0 in getattr(_pd, "BROLL", []):
        JC.setdefault(_it, []).append((_t0, _t0 + (_i1 - _i0) / _speed))
    expand_logos(SCENES)
    ins, prev = [], 0.0
    for c in SCENES:
        e = c["entry"]
        if isinstance(e, dict):
            e = resolve_phrase(e["_phrase"], prev)
        ins.append(e)
        prev = e
    for fixed in ("files", "search", "git-branch"):
        ensure_icon(fixed, "gray")
    ensure_icon("user", None)
    assert ins == sorted(ins) and ins[0] == 0.0, [i for i, (a, b) in enumerate(zip(ins, ins[1:])) if b < a]
    # Propaganda do CapCut: a fala PARA numa pausa depois do gancho e RETOMA na entrada de uma cena (fronteira de cena: nenhuma animação é
    # cortada ao meio). PROMO_AFTER = Phrase("frase") da cena que retoma; o silêncio entre o fim da fala anterior e a retomada é removido.
    PROMO_T[0] = PROMO_T[1] = None
    _prop = getattr(_pd, "PROMO_AFTER", None)
    if _prop is not None:
        _tr = resolve_phrase(_prop["_phrase"], 0.0) if isinstance(_prop, dict) else float(_prop)
        if not any(abs(_tr - x) < 0.06 for x in ins):
            raise SystemExit(
                f"PROMO_AFTER ({_tr:.2f}s) não coincide com o início de uma cena: use Phrase('frase') igual à entrada de uma cena "
                f"(cenas: {[round(x, 1) for x in ins[:12]]}...)"
            )
        _end_speech = max((w["end"] for w in WORDS if w["end"] <= _tr + 0.05), default=_tr)
        _tp = min(_end_speech + 0.65, _tr - 0.2)  # para um pouco depois da última palavra
        if _tr - _tp < 0.2:
            _tp = _tr  # sem pausa útil: não há silêncio a remover
        PROMO_T[0], PROMO_T[1] = round(_tp, 2), round(_tr, 2)
    ERRORS = []
    scenes_json, events, md_rows = [], [], []
    tot_img = tot_txt = tot_empty = 0
    first_title = None
    for k, c in enumerate(SCENES):
        t0 = ins[k]
        t1 = ins[k + 1] if k + 1 < len(SCENES) else DUR
        out_t = round(t1 - EXIT_TIME, 2)  # a última cena sai 0.3s antes do fim do áudio
        if c["kind"] == "empty":
            EMPTIES.add(c["id"])
            tot_empty += t1 - t0
            md_rows.append(
                f"| {k+1} | `{c['id']}` | vazio | {fmt(t0)}–{fmt(t1)} | {t1-t0:.1f}s | {phrase(t0, t1)[:90]} | (tela transparente) |"
            )
            continue
        try:
            if c["kind"] == "graph":
                js, ev = build_graph(c, t0, t1)
            elif c["kind"] == "impact":
                js, ev = build_text(c, t0, t1)
            elif c["kind"] in ("item", "section"):
                js, ev = build_composite(c, t0, t1)
            elif c["kind"] == "timeline":
                js, ev = build_time(c, t0, t1)
            elif c["kind"] == "shortlist":
                js, ev = build_shortlist(c, t0, t1)
            elif c["kind"] == "broll":
                js, ev = build_broll(c, t0, t1)
                EMPTIES.add(c["id"])  # vídeo conta como coberto; sem aviso de ">5 s sem evento"
            else:
                raise SystemExit("tipo desconhecido " + c["kind"])
        except SystemExit as e:
            ERRORS.append(f"{e}  [{t0:.1f}-{t1:.1f}]")
            continue
        assert all(t < out_t for _, t in ev), f"{c['id']}: evento depois da saida"
        events += ev + [(f"{c['id']}-out", out_t)]
        scenes_json.append(js)
        if c["kind"] == "impact":
            tot_txt += t1 - t0
            first_title = t0 if first_title is None else first_title
        else:
            tot_img += t1 - t0
        if c["kind"] == "graph":
            o = " + ".join(it["img"] for it in c["items"] if it["img"])
        elif c["kind"] == "impact":
            o = " / ".join(c["lines"])
        elif c["kind"] == "shortlist":
            o = f"lista curta ({len(c['items'])}): " + " · ".join(i[1] for i in c["items"])
        elif c["kind"] == "broll":
            o = "B-roll" + (f" · rótulo: {c['label']}" if c.get("label") else "")
        else:
            o = (
                c["kind"] + ": " + ", ".join(p["kind"] for p in c.get("pieces", []))
                if c["kind"] != "timeline"
                else "linha do tempo"
            )
        md_rows.append(
            f"| {k+1} | `{c['id']}` | {c['kind']} | {fmt(t0)}–{fmt(t1)} | {t1-t0:.1f}s | {phrase(t0, t1)[:90]} | {o} |"
        )
    if WARNINGS:
        print("\n".join("AVISO PROPORÇÃO: " + a for a in WARNINGS))
        if os.environ.get("STRICT", "1") == "1":
            ERRORS.append(f"{len(WARNINGS)} problema(s) de proporção/sobreposição (STRICT=0 ignora)")
    if ERRORS:
        raise SystemExit("\n".join(ERRORS))
    events.append(("end", round(DUR, 2)))
    # regra: no máximo ~5 s sem animação (a "respiração" cobre pequenos buracos; avisa o que passar disso)
    LIM = 5.0
    order_ev = sorted(events, key=lambda e: e[1])
    for (n1, t1_), (n2, t2_) in zip(order_ev, order_ev[1:]):
        if t2_ - t1_ > LIM and not n1.split("-")[0] in EMPTIES and n2 != "end":
            WARNINGS_GAP.append(f"{n1} -> {n2}: {t2_ - t1_:.1f}s")
    if WARNINGS_GAP and not getattr(_pd, "MINIMUM_OVERLAY", False):
        print(
            "AVISO >5s SEM EVENTO (trecho parado é aceito; só adicione beat se houver conteúdo legítimo):\n  "
            + "\n  ".join(WARNINGS_GAP)
        )
    names = [n for n, _ in events]
    assert len(names) == len(set(names))
    ts = [t for _, t in events]
    ruins = [(n, t) for (n, t), p in zip(events, [0] + ts) if t < p]
    assert not ruins, ruins
    pct_cob = 100 * (tot_img + tot_txt) / DUR  # cobertura (títulos de peças já estão dentro dos itens)
    for _t, _d in TITLES_PIECES:
        tot_txt += _d
        first_title = _t if first_title is None else min(first_title, _t)
    pct_txt = 100 * tot_txt / DUR
    tmax = getattr(_pd, "MAX_TITLES", 5)
    tmin = getattr(_pd, "TITLE_MIN_START", 30)
    assert pct_txt <= tmax, f"textos de impacto devem ficar em ate {tmax}% (estao em {pct_txt:.1f}%)"
    assert (
        first_title is None or first_title >= tmin
    ), f"nunca coloque titulo no comeco do video (>={tmin}s)"
    assert (
        COVERAGE[0] <= pct_cob <= COVERAGE[1]
    ), f"cobertura deve ficar entre {COVERAGE[0]}% e {COVERAGE[1]}% (esta em {pct_cob:.1f}%)"
    # ---- B-roll (tipo "Lista com B-roll"): BROLL = [(item_id, arquivo, in, out, velocidade, t_inicio_timeline), ...] ----
    broll = list(getattr(_pd, "BROLL", []))
    windows = {
        c["id"]: (ins[k], (ins[k + 1] if k + 1 < len(SCENES) else DUR) - EXIT_TIME, c["kind"])
        for k, c in enumerate(SCENES)
    }
    por_item, end_previous = {}, 0.0
    webdoc = getattr(_pd, "VIDEO_KIND", "") == "webdoc_broll"
    for item, file, i0, i1, speed, t0 in sorted(broll, key=lambda b: b[5]):
        if webdoc:
            if item in WINDOWS_VIDEO:
                if not any(
                    a_ - 0.03 <= t0 and t0 + (i1 - i0) / speed <= b_ + 0.03 for a_, b_ in WINDOWS_VIDEO[item]
                ):
                    raise SystemExit(
                        f"BROLL: clipe {t0:.1f}s de '{item}' fora das pausas da lista {WINDOWS_VIDEO[item]} (a lista só some dentro de ShortList(..., pauses=[...]))"
                    )
            elif item not in windows or windows[item][2] not in ("broll", "empty"):
                raise SystemExit(
                    f"BROLL: '{item}' nao e uma janela BrollWindow(...)/Empty(...) (no webdoc com B-roll o vídeo só roda em B/V ou nas pausas de uma ShortList; animação e vídeo não disputam a tela)"
                )
        elif item not in windows or windows[item][2] not in ("item", "section", "empty"):
            raise SystemExit(
                f"BROLL: '{item}' nao e uma cena de item/Section/Block/V (B-roll não roda em G/Tx; use Block(...) no gancho e V/Section no encerramento)"
            )
        begin, end, _ = windows[item]
        dur_tl = (i1 - i0) / speed
        if webdoc and item in WINDOWS_VIDEO:
            begin = min(a_ for a_, _ in WINDOWS_VIDEO[item])
        if not webdoc:
            _scene = next(c_ for c_ in SCENES if c_["id"] == item)
            _has_card = any(
                p_["kind"] == "section" for p_ in _scene.get("pieces", []) or []
            )  # Section(...) tem cartão; Block(...) não
            _piso = MENU_DURATION if windows[item][2] == "item" else (3.0 if _has_card else 0.0)
            assert (
                t0 >= begin + _piso - 0.05
            ), f"BROLL {item}: comeca antes do fim da cartela/animação inicial ({begin + _piso:.1f}s)"
        else:
            assert t0 >= begin - 0.05, f"BROLL {item}: comeca antes da janela ({begin:.1f}s)"
        assert t0 + dur_tl <= end + 0.05, f"BROLL {item}: passa do fim do item ({end:.1f}s)"
        assert (
            1.0 <= speed <= 2.0
        ), f"BROLL {item}: velocidade {speed} (entre 1.0 e 2.0; o usuário estica o clipe com 1.3-1.9x ao remover animações)"
        assert t0 >= end_previous - 0.01, f"BROLL {item}: sobrepoe o clipe anterior"
        if por_item.get(
            item
        ):  # vão entre dois clipes da MESMA janela: ou 0 ou uma janela de animação de verdade (>= 4 s)
            _gap = t0 - por_item[item][-1]["t_end"]
            if 0.05 < _gap < 4.0:
                WARNINGS.append(
                    f"[{item}] vão de {_gap:.1f}s entre dois clipes ({por_item[item][-1]['t_end']:.1f}→{t0:.1f}s): pequeno demais para uma animação; "
                    f"estenda o clipe anterior até {t0:.1f}s (ou abra um vão >= 4 s com animação)"
                )
        if dur_tl < 3.0:
            print(
                "AVISO B-ROLL:",
                f"[broll {item}] clipe de {dur_tl:.1f}s na timeline (< 3 s: evite pisca-pisca)",
            )
        por_item.setdefault(item, []).append(
            dict(
                file=file,
                **{"in": i0, "out": i1},
                speed=speed,
                t_start=round(t0, 2),
                t_end=round(t0 + dur_tl, 2),
            )
        )
        end_previous = t0 + dur_tl
    for d_ in TIPS:
        print("DICA:", d_)
    for a_ in WARNINGS_BROLL:
        print("AVISO PEÇA×B-ROLL:", a_)
    if broll and not webdoc:
        # COVERAGE: nenhum trecho >= 2 s pode ficar só com o fundo e a fala (sem clipe E sem animação visível).
        free_ok = set(getattr(_pd, "ALLOWED_EMPTIES", []))
        for it_id, (begin_, end_, tp_) in windows.items():
            if tp_ not in ("item", "section", "empty") or it_id in free_ok:
                continue
            a0 = begin_ + (MENU_DURATION if tp_ == "item" else 0.0)  # a cartela do item conta como conteúdo
            busy = [(x["t_start"], x["t_end"]) for x in por_item.get(it_id, [])] + [
                (a, b) for a, b in LIFE_PIECES.get(it_id, [])
            ]
            if tp_ == "section" and not LIFE_PIECES.get(it_id):
                busy.append((begin_, begin_ + 3.0))
            if (
                PROMO_T[0] is not None
            ):  # o silêncio depois do gancho é removido no CapCut (entra a propaganda)
                busy.append((PROMO_T[0], PROMO_T[1]))
            cur = a0
            for a, b in sorted(busy):
                if a - cur >= 2.0:
                    WARNINGS.append(
                        f"[{it_id}] {cur:.1f}–{a:.1f}s ({a - cur:.1f}s) só com fundo e fala: falta animação ou B-roll"
                    )
                cur = max(cur, b)
            if end_ - cur >= 2.0:
                WARNINGS.append(
                    f"[{it_id}] {cur:.1f}–{end_:.1f}s ({end_ - cur:.1f}s) só com fundo e fala: falta animação ou B-roll"
                )

        # proporção vídeo × animação (o usuário corta animação e estica B-roll: o padrão é VÍDEO; animação é tempero)
        tot_it = tot_cl = 0.0
        viol = []
        for it_id, (begin_, end_, tp_) in windows.items():
            if tp_ != "item":
                continue
            ut = end_ - (begin_ + MENU_DURATION)
            cl = sum(x["t_end"] - x["t_start"] for x in por_item.get(it_id, []))
            tot_it += ut
            tot_cl += cl
            if ut > 0 and (ut - cl) / ut > 0.5:
                viol.append(f"{it_id} {(ut - cl) / ut * 100:.0f}%")
        r_an = (tot_it - tot_cl) / tot_it if tot_it else 0
        print(
            f"Animação/vazio nos itens: {r_an * 100:.1f}% (máx. {CFG['ANIM_MAX'] * 100:.0f}%)"
            + (f" · itens > 50%: {', '.join(viol)}" if viol else "")
        )
        if r_an > CFG["ANIM_MAX"] and os.environ.get("STRICT", "1") == "1":
            raise SystemExit(
                f"animação+vazio = {r_an * 100:.1f}% do tempo dos itens (> {CFG['ANIM_MAX'] * 100:.0f}%): mais B-roll, menos animação (ou STRICT=0)"
            )
    if webdoc:
        t_b = sum(x["t_end"] - x["t_start"] for l in por_item.values() for x in l)
        t_an = sum(
            j[1] - j[0] for k_, j in windows.items() if j[2] in ("graph", "section", "timeline", "shortlist")
        )
        t_li = sum(j[1] - j[0] for j in windows.values() if j[2] == "shortlist")
        t_ti = sum(j[1] - j[0] for j in windows.values() if j[2] == "impact")
        print(
            f"Webdoc com B-roll: B-roll {t_b:.0f}s ({100 * t_b / DUR:.0f}%) · animação {t_an - t_li:.0f}s ({100 * (t_an - t_li) / DUR:.0f}%) · listas curtas {t_li:.0f}s ({100 * t_li / DUR:.0f}%) · títulos {t_ti:.0f}s · só preenchimento (completar à mão) {max(0, DUR - t_b - t_an - t_ti):.0f}s"
        )
    for c_ in SCENES:
        for p_ in c_.get("pieces", []):
            if p_["kind"] == "people" and any(x["foto"] is None for x in p_["props"]["people"]):
                print(
                    "AVISO:",
                    f"[{c_['id']}] Pessoas sem foto (silhueta genérica fica feia): use foto real ou remova a peça",
                )
    for item, l in por_item.items():
        if len(l) > getattr(_pd, "MAX_CLIPS_PER_ITEM", 6 if webdoc else 2):
            print(
                "AVISO B-ROLL:",
                f"[broll {item}] {len(l)} clipes no mesmo item (o padrao e 1-2; 3 so em caso raro)",
            )
    for js in scenes_json:
        js["light"] = False  # overlay NÃO é mais "leve": só HUD sobre o B-roll; animações completas nos vazios
    list_broll = sorted([c for l in por_item.values() for c in l], key=lambda c: c["t_start"])
    json.dump(list_broll, open("src/scenes/broll.json", "w"), ensure_ascii=False, indent=1)
    # prévia no editor (Motion Canvas): preenchimento + clipes (proxies 640x360 em src/videos/, gerados por scripts/broll/generate_proxies.py).
    # Liga/desliga por BROLL_PREVIEW no plan_data.py (padrão True); NO RENDER FINAL fica desligada (o motor também a ignora ao renderizar).
    json.dump(
        dict(
            active=bool(getattr(_pd, "BROLL_PREVIEW", True)) and bool(list_broll),
            duration=DUR,
            clips=[
                dict(
                    video=f"clip_{i+1:02d}",
                    t0=c["t_start"],
                    dur=round(c["t_end"] - c["t_start"], 3),
                    speed=c["speed"],
                    srcdur=round(c["out"] - c["in"], 3),
                )
                for i, c in enumerate(list_broll)
            ],
        ),
        open("src/scenes/preview.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    if broll:
        cob = sum(c["t_end"] - c["t_start"] for l in por_item.values() for c in l)
        print(
            f"B-roll: {len(broll)} clipes em {len(por_item)} itens, {cob:.1f}s ({100*cob/DUR:.1f}% do video)"
        )
    json.dump(scenes_json, open("src/scenes/scenes.json", "w"), ensure_ascii=False, indent=1)
    json.dump(
        dict(title=getattr(_pd, "MENU_TITLE", "ITEMS"), style=getattr(_pd, "MENU_STYLE", "explorer")),
        open("src/scenes/list.json", "w"),
    )
    _det = list(getattr(_pd, "MENU_DETAILS", []))
    json.dump(
        [
            dict(
                label=n, file=(a if CFG["EXT"] else n), color=c, detail=(_det[k] if k < len(_det) else "")
            )
            for k, (n, a, c) in enumerate(MENU)
        ],
        open("src/scenes/menu.json", "w"),
        ensure_ascii=False,
    )  # extensão só quando a lista é de ARQUIVOS (MENU_EXTENSIONS=True)
    import subprocess

    subprocess.run(["node", "scripts/tokenize.mjs"], check=True)
    meta_path = "src/scenes/scene1.meta"
    try:
        seed = json.load(open(meta_path)).get("seed", 1)
    except Exception:
        seed = 1
    json.dump(
        {"version": 0, "timeEvents": [{"name": n, "targetTime": t} for n, t in events], "seed": seed},
        open(meta_path, "w"),
        indent=2,
    )
    md = [
        "# Plano de animações\n",
        f"Duração do áudio: {DUR:.2f}s — cobertura {pct_cob:.1f}% ({len(SCENES)} blocos; vazio {tot_empty:.1f}s)\n",
        f"Imagens/grafos: {tot_img:.1f}s ({100*tot_img/DUR:.1f}%) · Texto de impacto: {tot_txt:.1f}s ({pct_txt:.1f}%)\n",
        "| # | id | tipo | início–fim | dur | trecho da fala | o que aparece |",
        "|---|---|---|---|---|---|---|",
    ] + md_rows
    open("PLAN.md", "w").write("\n".join(md) + "\n")
    json.dump(
        {
            "duration": DUR,
            "events": events,
            "windows": {
                c["id"]: [
                    round(ins[k], 2),
                    round((ins[k + 1] if k + 1 < len(SCENES) else DUR) - EXIT_TIME, 2),
                    c["kind"],
                ]
                for k, c in enumerate(SCENES)
            },
            "menu_duration": MENU_DURATION,
            "promo_t": PROMO_T[0],
            "promo_resume": PROMO_T[1],
            "final_before_end": getattr(_pd, "FINAL_BEFORE_END", 6.9),
            "overlay_light": OVERLAY_LIGHT,
            "windows_video": WINDOWS_VIDEO,
            "video_kind": getattr(_pd, "VIDEO_KIND", ""),
        },
        open("plan.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    print(
        f"{len(SCENES)} blocos, cobertura {pct_cob:.1f}%, texto {tot_txt:.1f}s ({pct_txt:.1f}%), eventos {len(events)}"
    )
