"""Gera cenas.json (layout + tempos), .meta (timeEvents) e PLANO.md a partir de transcricao.json + plano_dados.py.

Cenas contíguas cobrem 100% do áudio: cada cena vai da sua entrada até a entrada da próxima (a saída
acontece 0.3s antes). Dois tipos: G (grafo/árvore de imagens) e T (texto de impacto, sem imagens).
Âncora de tempo: A(segundos_aprox, 'palavra', 'start'|'end') -> timestamp real da palavra.
"""

import warnings

warnings.filterwarnings("ignore")
import glob, json, os, re, unicodedata, urllib.request
from PIL import Image

T = json.load(open(os.environ.get("TRANSCRICAO", "transcricao.json")))
WORDS = [w for s in T["segments"] for w in s["words"]]
DUR = T["duration"]
LEAD = float(
    os.environ.get("LEAD", "0.15")
)  # imagens entram um pouco ANTES da palavra (padrão de edição profissional)
SAIDA = 0.3  # saída termina quando a próxima cena entra
LOGOS_PLACA = set()
ZONA_AVATAR = (
    720,
    300,
)  # (x, y) em coords do centro: canto inferior direito reservado ao avatar do canal (sticker do criador)
MENU_DURACAO = 3.7  # tempo ocupado pelo menu na troca de item (as peças só entram depois)
PROPAGANDA_T = [
    None,
    None,
]  # (para, retoma): segundo em que a propaganda do CapCut entra (fronteira de cena); gravado em plano.json
TITULOS_PECAS = []  # (tempo, duração) dos títulos sobrepostos em itens
JANELAS_VIDEO = {}  # id de ListaCurta -> janelas [ini, fim] (pausas) onde o B-roll é permitido
OVERLAY_LEVE = (
    []
)  # [t0, t1] dos rótulos leves sobre B-roll (webdoc com B-roll): o CapCut mantém overlay só aí e nas janelas sem clipe
JC = {}  # item -> [(t_ini, t_fim)] janelas de B-roll (preenchido no main)
CFG = dict(
    HUD=False,
    EXT=False,
    LOGO_CARTELA=False,
    ANIM_MAX=0.35,
    LEAD_CLIPE=0.4,
    FOLGA_CLIPE=0.15,
    ESC_GRAFO=1.5,
    EXIGE_LOGO=False,
)  # sobrescrito por plano_dados.py
ESTILO_TITULO = [
    "monokai"
]  # 'monokai' (terminal, canal de programação) ou 'reportagem' (webdoc); mude com ESTILO_TITULO no plano_dados
MENU = []  # preenchido por plano_dados.py: [(nome, arquivo, cor)]
MIN_PERMANENCIA = 1.8  # o último item de cada cena fica pelo menos isso na tela (nada de "piscar")
MIN_INTERVALO = 0.4  # espaçamento mínimo entre itens quando o beat precisa ser antecipado
CORES = {
    None: "#ffffff",
    "vermelho": "#ff5a5f",
    "ambar": "#ffb020",
    "verde": "#3ddc97",
    "escuro": "#222222",
    "cinza": "#75715e",
    "azul": "#66d9ef",
    "amarelo": "#e6db74",
}


def garantir_icone(nome, cor):
    """Ícone de linha Tabler (MIT) recolorido -> src/images/ic-<nome>[-<cor>].svg (baixa e cacheia em icones_base/)."""
    base = f"icones_base/{nome}.svg"
    if not os.path.exists(base):
        os.makedirs("icones_base", exist_ok=True)
        url = f"https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{nome}.svg"
        try:
            open(base, "wb").write(urllib.request.urlopen(url).read())
        except Exception as e:
            raise SystemExit(f"icone tabler '{nome}' nao existe ({e})")
    svg = open(base).read()
    svg = (
        re.sub(r"<!--.*?-->", "", svg, flags=re.S)
        .replace("currentColor", CORES[cor])
        .replace('stroke-width="2"', 'stroke-width="1.6"')
    )
    nome_arq = f"ic-{nome}" + (f"-{cor}" if cor else "")
    open(f"src/images/{nome_arq}.svg", "w").write(svg)
    return nome_arq


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def A(approx, palavra, lado="start"):
    p = norm(palavra)
    cands = [w for w in WORDS if norm(w["word"]).startswith(p) and abs(w["start"] - approx) < 6]
    if not cands:
        raise SystemExit(f"ancora nao encontrada: {approx} {palavra}")
    w = min(cands, key=lambda w: abs(w["start"] - approx))
    return round(w[lado] - (LEAD if lado == "start" else 0), 2)


# ---------- DSL ----------
def I(
    img,
    rotulo=None,
    em=None,
    id=None,
    pai=None,
    pais=None,
    h=240,
    placa=False,
    redondo=False,
    sobre=None,
    dx=0,
    dy=0,
    destaque=False,
    alvo=None,
    cor=None,
    moldura=None,
    mono=False,
):
    """Item de grafo. em: None (mesmo instante do anterior) | 'palavra' (próxima ocorrência) | ('palavra', seg_aprox).
    pai/pais: id(s) dos itens de onde saem setas. sobre: id do item sobre o qual esta imagem é sobreposta (dx,dy px).
    img 'ic:nome' = ícone de linha Tabler dentro de disco escuro (cor: None/'vermelho'/'ambar'/'verde'); outras = arquivo em src/images.
    """
    if pai:
        pais = [pai]
    if isinstance(img, str) and img.startswith("asset:"):
        img = trazer_asset(img)
    return dict(
        img=img,
        rotulo=rotulo,
        em=em,
        id=id,
        pais=pais or [],
        h=h,
        placa=placa,
        redondo=redondo,
        sobre=sobre,
        dx=dx,
        dy=dy,
        destaque=destaque,
        alvo=alvo,
        cor=cor,
        moldura_forcada=moldura,
        mono=mono,
    )


def G(id, entrada, itens, dir="LR", liga=()):
    """Grafo/árvore. dir: LR (esquerda→direita) ou TB (cima→baixo; raízes ficam lado a lado, sem setas = fileira)."""
    return dict(tipo="grafo", id=id, entrada=entrada, itens=itens, dir=dir, liga=list(liga))


def F(frase):
    """Âncora por FRASE (robusta a cortes no áudio): primeira ocorrência das palavras seguidas, depois da cena anterior."""
    return dict(_frase=frase)


def resolver_frase(frase, depois):
    toks = [norm(t) for t in frase.split()]
    for i in range(len(WORDS)):
        if WORDS[i]["start"] < depois + 0.05:
            continue
        if all(
            i + k < len(WORDS) and norm(WORDS[i + k]["word"]).startswith(toks[k]) for k in range(len(toks))
        ):
            return round(WORDS[i]["start"] - LEAD, 2)
    raise SystemExit(f"frase nao encontrada apos {depois:.1f}s: '{frase}'")


# --- peças das cenas compostas (item de lista / seção / linha do tempo) ---
def Logo(logo, nome, ano, cor, sigla=None, em=None):
    return dict(
        slot="logo", tipo="logo", em=em, props=dict(logo=logo, nome=nome, ano=ano, cor=cor, sigla=sigla)
    )


def LogoSolto(logo, em=None, h=250, placa=None):
    """Logo grande à esquerda (centro-esquerda), SEM cartão quando tem transparência (padrão que o usuário aplicava à mão no CapCut).
    Use o logo do ASSUNTO da animação ao lado (ex.: Tux para uma comparação com Linux), não só o do sistema do item.
    """
    return dict(slot="esq", tipo="logosolto", em=em, props=dict(logo=logo, h=h, placa_forcada=placa))


def Pessoas(pessoas, em=None, grupo=False):
    """pessoas: [(foto|None, nome, papel)]. foto = nome do arquivo em src/images sem extensão (ex.: 'foto_guido_van_rossum')."""
    return dict(
        slot="pessoas",
        tipo="pessoas",
        em=em,
        props=dict(pessoas=[dict(foto=f, nome=n, papel=p) for f, n, p in pessoas], grupo=grupo),
    )


def Codigo(id, em=None):
    return dict(slot="dir", tipo="codigo", em=em, props=dict(id=id))


def Stat(valor, rotulo, cor="#a6e22e", pct=None, em=None, logo=None):
    if len(str(valor)) > 9 or len(rotulo) > 38:
        raise SystemExit(
            f"Stat '{valor}' / '{rotulo}': valor <= 9 caracteres e rotulo <= 38 (menos texto, mais imagem)"
        )
    return dict(
        slot="dir", tipo="stat", em=em, logo=logo, props=dict(valor=valor, rotulo=rotulo, cor=cor, pct=pct)
    )


def Fatos(linhas, em=None, logo=None):
    """linhas: [('ic:nome', 'texto curto')]"""
    if len(linhas) > 3 or any(len(t) > 34 for _, t in linhas):
        raise SystemExit(f"Fatos {linhas}: no maximo 3 linhas de ate 34 caracteres (muito texto)")
    return dict(
        slot="dir",
        tipo="fatos",
        em=em,
        logo=logo,
        props=dict(linhas=[dict(icone=i, texto=t) for i, t in linhas]),
    )


def Grafo(itens, dir="LR", liga=(), em=None):
    for _it in itens:
        if _it.get("rotulo") and len(_it["rotulo"]) > 22:
            raise SystemExit(f"Grafo: rotulo '{_it['rotulo']}' > 22 caracteres (sobrepoe o vizinho); encurte")
    """Peça de grafo/árvore dentro de um item de lista (região da direita, ~1060x640); os itens aparecem em sequência."""
    return dict(slot="dir", tipo="grafo", em=em, props=dict(itens=itens, dir=dir, liga=list(liga)))


def Comparativo(colunas, linhas, em=None):
    """colunas: [(logo|None, 'Windows 7', '#66d9ef')]; linhas: [('Processador', ('1 GHz','1 GHz · 2 núcleos'), 0|1|None)] (vencedor opcional)."""
    return dict(
        slot="dir",
        tipo="comparativo",
        em=em,
        props=dict(
            colunas=[dict(logo=l, rotulo=r, cor=c) for l, r, c in colunas],
            linhas=[dict(rotulo=a, valores=list(b), vence=c) for a, b, c in linhas],
        ),
    )


def Tela(img, legenda, largura=900, em=None):
    """Captura de tela/foto grande com moldura e legenda (região da direita). img = nome em src/images OU 'asset:arquivo.jpg' (da pasta Assets/).
    Nunca é esticada além da resolução do arquivo e fica parada (sem zoom lento de enchimento)."""
    if img.startswith("asset:"):
        img = trazer_asset(img)
    for e_ in ("png", "jpg", "webp"):
        if os.path.exists(f"src/images/{img}.{e_}"):
            largura = min(largura, Image.open(f"src/images/{img}.{e_}").size[0])
            break
    if len(legenda) > 60:
        raise SystemExit(f"Tela '{img}': legenda > 60 caracteres (curta!)")
    return dict(slot="dir", tipo="tela", em=em, props=dict(img=img, legenda=legenda, largura=largura))


def Titulo(linhas, dur=3.2, tag="", em=None):
    """Título de impacto (terminal Monokai) sobreposto no topo de um item, sem apagar o resto; some sozinho após `dur` s."""
    return dict(slot="overlay", tipo="titulo", em=em, props=dict(linhas=linhas, tag=tag, dur=dur))


def L(id, entrada, idx, pecas, menu=True, sub="", logo=None):
    """Item da lista: o menu (explorador) aparece na troca de item; depois logo, criadores e código/estatísticas.
    logo: imagem (src/images, sem extensão) do assunto do item — aparece na cartela do item e, por padrão, à esquerda de Stat/Fatos.
    """
    return dict(tipo="item", id=id, entrada=entrada, idx=idx, pecas=pecas, menu=menu, sub=sub, logo=logo)


def expandir_logos(cenas):
    """Chamada no main (depois de ler os flags do plano_dados): insere LogoSolto antes de cada Stat/Fatos; exige logo quando EXIGE_LOGO."""
    for c in cenas:
        if c.get("tipo") != "item":
            continue
        novo = []
        ult = None  # (logo, segundos aprox.) do último LogoSolto
        for p in c["pecas"]:
            if p["tipo"] in ("stat", "fatos"):
                lg = p.get("logo") or c.get("logo")
                if lg:
                    t_ap = p["em"][1] if isinstance(p["em"], tuple) else None
                    mesma_janela = (
                        ult
                        and t_ap is not None
                        and ult[0] == lg
                        and ult[1] is not None
                        and not any(ult[1] < a_ and a_ < t_ap for a_, _ in JC.get(c["id"], []))
                    )
                    if not mesma_janela:
                        novo.append(LogoSolto(lg, em=p["em"]))
                        ult = (lg, t_ap)
                elif CFG["EXIGE_LOGO"]:
                    raise SystemExit(
                        f"item '{c['id']}': {p['tipo']} sem logo (passe logo= na peça ou L(..., logo=...)): quadro só com texto à direita fica vazio"
                    )
            novo.append(p)
        c["pecas"] = novo


def Secao(id, entrada, tag, titulo, sub, logos=()):
    return dict(
        tipo="secao",
        id=id,
        entrada=entrada,
        pecas=[
            dict(
                slot="centro",
                tipo="secao",
                em=None,
                props=dict(tag=tag, titulo=titulo, sub=sub, logos=list(logos)),
            )
        ],
    )


def Tempo(id, entrada, itens, marcos):
    """itens: [dict(ano, nome, logo|None, cor, sigla)]; marcos: [(indice_do_item, 'palavra' | None)] em ordem de fala."""
    return dict(tipo="tempo", id=id, entrada=entrada, itens=itens, marcos=marcos)


def trazer_asset(ref):
    """'asset:foto.jpg' -> copia (<= 1800 px) de ../Assets/foto.jpg para src/images/tela_asset_<slug>.<ext> e devolve o nome sem extensão.
    Só use arquivos que o USUÁRIO deixou na pasta Assets/ (webdoc com B-roll); nada de baixar imagem de contexto da internet.
    """
    arq = ref[6:]
    for pasta in ("../Assets", "../assets", "Assets", "assets"):
        src = os.path.join(pasta, arq)
        if os.path.exists(src):
            break
    else:
        raise SystemExit(f"asset '{arq}' nao esta em ../Assets/")
    slug = re.sub(r"[^a-z0-9]+", "_", os.path.splitext(arq)[0].lower()).strip("_")[:40]
    ext = os.path.splitext(arq)[1].lower().lstrip(".")
    ext = "jpg" if ext in ("jpg", "jpeg") else ("webp" if ext == "webp" else "png")
    nome = f"tela_asset_{slug}"
    dst = f"src/images/{nome}.{ext}"
    if not os.path.exists(dst):
        im = Image.open(src)
        im.thumbnail((1800, 1800))
        if ext == "jpg":
            im = im.convert("RGB")
        im.save(dst)
    return nome


def Centro(peca):
    """Move uma peça (Tela, Comparativo, Grafo...) para o centro da tela num Bloco (por padrão ficam à direita)."""
    return dict(peca, slot="centro")


def Bloco(id, entrada, pecas):
    """Cena composta do webdoc SEM menu/cartela de item: as mesmas peças dos itens (Logo, LogoSolto, Pessoas, Stat, Fatos, Grafo, Comparativo, Tela, Titulo)
    sobre o preenchimento. Use para o trecho de ANIMAÇÃO do webdoc com B-roll."""
    return dict(tipo="secao", id=id, entrada=entrada, pecas=pecas)


def B(id, entrada, rotulo=None, data=None, logo=None, dur_rotulo=5.0):
    """Janela de B-roll (Webdoc com B-roll): o vídeo da pasta Assets/ roda aqui (BROLL = [(id, arquivo, in, out, vel, t_inicio)]).
    Overlay LEVE por cima: só um rótulo/data/logo pequeno no canto inferior ESQUERDO (o direito é do avatar), ou nada.
    """
    if rotulo and len(rotulo) > 40:
        raise SystemExit(f"B '{id}': rotulo > 40 caracteres")
    if isinstance(logo, str) and logo.startswith("asset:"):
        logo = trazer_asset(logo)
    return dict(
        tipo="broll", id=id, entrada=entrada, rotulo=rotulo, data=data, logo=logo, dur_rotulo=dur_rotulo
    )


def ListaCurta(id, entrada, titulo, itens, cor="#66d9ef", pausas=None):
    """Lista curta DENTRO do vídeo (ex.: 'as 8 camadas de segurança'): cartões numerados que entram um a um na fala.
    itens: [('ic:nome', 'rótulo curto', 'palavra' | ('palavra', seg_aprox) | None)]. 2–10 itens, rótulo <= 30 caracteres.
    Tema escuro sério do webdoc (NÃO usa menu explorador nem HUD). Numeração: zero à esquerda só acima de 9 itens.
    pausas: [(em_ini, em_fim), ...] — janelas em que a lista SOME (fade) para rodar B-roll e VOLTA inteira (cartões já vistos) no fim; âncoras como nos itens
    ('palavra' | ('palavra', seg) | seg numérico). Nenhum item pode entrar dentro de uma pausa; o BROLL dessa cena só vale dentro das pausas.
    """
    if not 2 <= len(itens) <= 10:
        raise SystemExit(f"ListaCurta '{id}': use de 2 a 10 itens (tem {len(itens)})")
    for ic, rot, _ in itens:
        if len(rot) > 30:
            raise SystemExit(f"ListaCurta '{id}': rotulo '{rot}' > 30 caracteres")
    return dict(
        tipo="listacurta",
        id=id,
        entrada=entrada,
        titulo=titulo,
        itens=itens,
        cor=cor,
        pausas=list(pausas or []),
    )


def V(id, entrada):
    """Vazio: nenhuma animação (tela transparente) a partir daqui até a próxima cena."""
    return dict(tipo="vazio", id=id, entrada=entrada)


def Tx(id, entrada, linhas, tag="atenção", estilo=None):
    """Título de impacto (terminal Monokai). Cores: *rosa*, *v:verde*, *a:azul*, *l:laranja*, *y:amarelo*, *r:roxo*."""
    return dict(tipo="impacto", id=id, entrada=entrada, linhas=linhas, tag=tag, estilo=estilo)


# ---------- layout ----------
def _biblioteca():
    d = os.path.abspath(".")
    while d != "/":
        c = os.path.join(d, ".claude", "skills", "animacao-narracao", "assets")
        if os.path.isdir(c):
            return c
        d = os.path.dirname(d)
    return None


def puxar_asset(nome):
    """Reaproveita imagens entre projetos: se src/images/<nome>.* não existe, copia da biblioteca da skill (assets/)."""
    lib = _biblioteca()
    if not lib:
        return False
    for ext in ("png", "jpg", "webp", "svg"):
        f = os.path.join(lib, f"{nome}.{ext}")
        if os.path.exists(f):
            import shutil

            shutil.copy(f, f"src/images/{nome}.{ext}")
            return True
    return False


def tem_alfa(img):
    """True se a imagem tem transparência real (logo solto sem cartão); svg conta como transparente."""
    if not any(os.path.exists(f"src/images/{img}.{e}") for e in ("png", "jpg", "webp", "svg")):
        puxar_asset(img)
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


def precisa_placa(img):
    """Logo vai em cartão branco quando é opaco OU escuro demais para o fundo escuro (texto preto sobre transparência some)."""
    if not tem_alfa(img):
        return True
    if (
        img in LOGOS_PLACA
    ):  # logos cujo texto/traço é cinza/escuro e some no fundo escuro (plano_dados: LOGOS_COM_PLACA)
        return True
    for ext in ("png", "webp"):
        p = f"src/images/{img}.{ext}"
        if os.path.exists(p):
            im = Image.open(p).convert("RGBA")
            px = [q for q in list(im.resize((64, 64)).getdata()) if q[3] > 128]
            if not px:
                return True
            lum = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b, _ in px) / len(px)
            escuros = sum(1 for r, g, b, _ in px if 0.2126 * r + 0.7152 * g + 0.0722 * b < 60) / len(px)
            return lum < 90 or escuros > 0.10  # texto preto sobre transparência some no fundo escuro
    return False


def aspecto(img):
    if not any(os.path.exists(f"src/images/{img}.{e}") for e in ("png", "jpg", "webp", "svg")):
        puxar_asset(img)
    for ext in ("png", "jpg", "webp"):
        p = f"src/images/{img}.{ext}"
        if os.path.exists(p):
            w, h = Image.open(p).size
            return w / h
    if os.path.exists(f"src/images/{img}.svg"):
        m = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', open(f"src/images/{img}.svg").read())
        return float(m.group(1)) / float(m.group(2)) if m else 1.0
    raise SystemExit(f"imagem nao encontrada: {img}")


PLACA_K = 1.35  # altura da placa = h * PLACA_K (h = "tamanho nominal" do logo)
TAM_ROTULO = 36


def geom(it):
    """Geometria final do item em px (antes da escala do layout): placa (pw,ph), imagem (iw,ih), caixa total (w,h)."""
    h = it["h"]
    if it["redondo"] or it.get("moldura"):
        w_, h_ = h, h
        g = dict(pw=None, ph=None, iw=h, ih=h)
    elif it["placa"]:
        a = aspecto(it["img"])
        ph = h * PLACA_K
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
        a = aspecto(it["img"])
        g = dict(pw=None, ph=None, iw=h * a, ih=h)
        w_, h_ = h * a, h
    if it["rotulo"]:
        h_ += 2 * (TAM_ROTULO * 1.35) + 8  # espaçador simétrico + rótulo
        w_ = max(w_, len(it["rotulo"]) * TAM_ROTULO * 0.58)
    g["w"], g["h"] = w_, h_
    return g


def caixa(it):
    g = geom(it)
    return g["w"], g["h"]


def escala_geom(it, s):
    if not it["img"]:
        return {}
    g = geom(it)
    return {k: (round(v * s, 1) if v else None) for k, v in g.items() if k in ("pw", "ph", "iw", "ih")}


def retangulo(it, o):
    g = geom(it)
    s = o["h"] / it["h"] if it["h"] else 1
    w, h = g["w"] * s, g["h"] * s
    return o["x"] - w / 2, o["y"] - h / 2, o["x"] + w / 2, o["y"] + h / 2


def checar_proporcao(itens, out, s, onde):
    """Sobreposição entre itens independentes (não 'sobre') e desproporção entre irmãos (mesma altura nominal esperada)."""
    base = [i for i, it in enumerate(itens) if it["img"] and not it["sobre"]]
    erros = []
    for ia in range(len(base)):
        for ib in range(ia + 1, len(base)):
            a, b = base[ia], base[ib]
            ra, rb = retangulo(itens[a], out[a]), retangulo(itens[b], out[b])
            ox = min(ra[2], rb[2]) - max(ra[0], rb[0])
            oy = min(ra[3], rb[3]) - max(ra[1], rb[1])
            if ox > 4 and oy > 4:
                erros.append(f"{itens[a]['img']} x {itens[b]['img']} sobrepostos ({ox:.0f}x{oy:.0f}px)")
    for i in base:
        r = retangulo(itens[i], out[i])
        if r[0] < -960 or r[2] > 960 or r[1] < -540 or r[3] > 540:
            erros.append(f"{itens[i]['img']} fora da tela")
    grupos = {}
    for i in base:
        if out[i].get("ph"):
            grupos.setdefault(tuple(itens[i]["pais"]), []).append((out[i]["ph"], itens[i]["img"]))
    for g in grupos.values():  # irmãos (mesmos pais) devem ter placas de altura parecida
        if len(g) > 1 and max(p for p, _ in g) > 1.35 * min(p for p, _ in g):
            erros.append("irmãos com placas desproporcionais: " + ", ".join(f"{n}={p:.0f}" for p, n in g))
    if erros:
        AVISOS.append(f"[{onde}] " + "; ".join(erros))


AVISOS = []
AVISOS_GAP = []
AVISOS_BROLL = []
EV_G = []  # eventos de itens de grafo (palavra a palavra)
VAZIOS = set()


def layout(itens, dir_, W=1760, H=940, smax=1.5):
    idx = {it["id"]: i for i, it in enumerate(itens) if it["id"]}
    n = len(itens)
    base = [i for i, it in enumerate(itens) if not it["sobre"] and it["img"]]
    pais = {i: [idx[p] for p in itens[i]["pais"]] for i in base}
    depth = {}
    for _ in range(n + 1):
        for i in base:
            depth[i] = 0 if not pais[i] else max(depth.get(p, 0) for p in pais[i]) + 1
    niveis = {}
    for i in base:
        niveis.setdefault(depth[i], []).append(i)
    LR = dir_ == "LR"
    esp = {i: caixa(itens[i]) for i in base}
    larg = lambda i: esp[i][1] if LR else esp[i][0]  # extensão na direção da "largura" (transversal)
    prof = lambda i: esp[i][0] if LR else esp[i][1]  # extensão ao longo da profundidade
    GAPB, GAPD = 70, 230
    pos = {}

    def espalha(nivel, desejado):
        ordem = sorted(nivel, key=lambda i: (desejado[i], i))
        for k, i in enumerate(ordem):
            pos[i] = desejado[i]
            if k:
                j = ordem[k - 1]
                pos[i] = max(pos[i], pos[j] + (larg(i) + larg(j)) / 2 + GAPB)
        shift = sum(pos[i] - desejado[i] for i in ordem) / len(ordem)
        for i in ordem:
            pos[i] -= shift
        # recompõe espaçamento mínimo após o shift
        for k, i in enumerate(ordem[1:], 1):
            j = ordem[k - 1]
            pos[i] = max(pos[i], pos[j] + (larg(i) + larg(j)) / 2 + GAPB)

    filhos = {i: [c for c in base if i in pais[c]] for i in base}
    L = max(niveis)
    for passo in range(3):
        for d in range(L + 1):
            nivel = niveis[d]
            if d == 0 and passo == 0:
                des, acc = {}, 0
                for i in nivel:
                    des[i] = acc + larg(i) / 2
                    acc += larg(i) + GAPB
            elif d == 0:
                des = {
                    i: (sum(pos[c] for c in filhos[i]) / len(filhos[i])) if filhos[i] else pos[i]
                    for i in nivel
                }
            else:
                des = {i: sum(pos[p] for p in pais[i]) / len(pais[i]) for i in nivel}
            espalha(nivel, des)
        for d in range(L - 1, -1, -1):
            des = {
                i: (sum(pos[c] for c in filhos[i]) / len(filhos[i])) if filhos[i] else pos[i]
                for i in niveis[d]
            }
            espalha(niveis[d], des)
    # ALINHAMENTO PELO ÍCONE (não pelo texto): irmãos de um mesmo nível ficam com passo uniforme entre os CENTROS dos ícones,
    # usando o maior item do grupo como medida. Sem isso o rótulo mais longo empurra os vizinhos e os ícones ficam desalinhados.
    for d, nivel in niveis.items():
        grupos = {}
        for i in nivel:
            grupos.setdefault(tuple(sorted(pais[i])), []).append(i)
        if len(grupos) == 1 and len(nivel) > 1:  # um único grupo no nível (fileira ou leque): centraliza com passo igual
            passo = max(larg(i) for i in nivel) + GAPB
            centro = sum(pos[i] for i in nivel) / len(nivel)
            for k, i in enumerate(sorted(nivel, key=lambda i: pos[i])):
                pos[i] = centro + (k - (len(nivel) - 1) / 2) * passo
    # coordenada de profundidade
    espessura = {d: max(prof(i) for i in niveis[d]) for d in niveis}
    cd, c = {}, 0
    for d in range(L + 1):
        if d:
            c += espessura[d - 1] / 2 + GAPD + espessura[d] / 2
        cd[d] = c
    ext_prof = cd[L] + espessura[L] / 2 + espessura[0] / 2
    lo = min(pos[i] - larg(i) / 2 for i in base)
    hi = max(pos[i] + larg(i) / 2 for i in base)
    ext_larg = hi - lo
    ext_x, ext_y = (ext_prof, ext_larg) if LR else (ext_larg, ext_prof)
    s = min(smax, W / ext_x, H / ext_y)  # amplia até `smax` para ocupar a tela
    cl = (lo + hi) / 2
    cp = (cd[0] - espessura[0] / 2 + cd[L] + espessura[L] / 2) / 2
    out = {}
    for i in base:
        a, b = (cd[depth[i]] - cp) * s, (pos[i] - cl) * s
        out[i] = (a, b) if LR else (b, a)
    return out, s, depth


def garantir_mono(img):
    """Logo SVG recolorido em cinza-escuro uniforme (para grupos de logos com cores incoerentes: branco/amarelo/preto)."""
    dst = f"{img}-mono"
    src = f"src/images/{img}.svg"
    if not os.path.exists(src):
        raise SystemExit(f"mono: {img}.svg nao existe (use logo SVG do Simple Icons)")
    svg = open(src).read()
    svg = re.sub(r'fill="#[0-9A-Fa-f]{3,8}"', 'fill="#222222"', svg, count=1)
    open(f"src/images/{dst}.svg", "w").write(svg)
    return dst


def resolver_imagem(it):
    it["moldura"] = False
    if it["img"] and it["img"].startswith("ic:"):
        partes = it["img"][3:].split(":")
        it["img"] = garantir_icone(partes[0], partes[1] if len(partes) > 1 else it["cor"])
        it["moldura"] = it["moldura_forcada"] is not False
    elif it["img"] and it.get("mono"):
        it["img"] = garantir_mono(it["img"])


def bus_arestas(itens, out, pares, LR):
    """Coordenada comum da dobra dos conectores em cotovelo: leques/convergências usam o mesmo 'barramento' (nada de setas cruzando)."""
    rects = {i: retangulo(itens[i], out[i]) for i in {x for p in pares for x in p}}
    filhos, pais = {}, {}
    for a, b in pares:
        filhos.setdefault(a, []).append(b)
        pais.setdefault(b, []).append(a)
    saida = {}
    for a, b in pares:
        ra, rb = rects[a], rects[b]
        if len(filhos[a]) > 1:  # leque
            fim_a = ra[2] if LR else ra[3]
            ini_b = min((rects[c][0] if LR else rects[c][1]) for c in filhos[a])
            saida[(a, b)] = round((fim_a + ini_b) / 2, 1)
        else:  # convergência (ou 1-1)
            fim_a = max((rects[p][2] if LR else rects[p][3]) for p in pais[b])
            ini_b = rb[0] if LR else rb[1]
            saida[(a, b)] = round((fim_a + ini_b) / 2, 1)
    return saida


def montar_grafo(c, t0, t1):
    itens = c["itens"]
    for it in itens:
        resolver_imagem(it)
    idx = {it["id"]: i for i, it in enumerate(itens) if it["id"]}
    pos, s, depth = layout(itens, c["dir"])
    # tempos
    cur, nomes, tempos = t0, {t0: "in"}, []
    for it in itens:
        em = it["em"]
        if em is None:
            t = cur
        else:
            if isinstance(em, tuple):
                t = A(em[1], em[0])
            else:
                p = norm(em)
                cand = [
                    w
                    for w in WORDS
                    if w["start"] >= cur + 0.05 and norm(w["word"]).startswith(p) and w["start"] < t1 - 0.4
                ]
                if not cand:
                    raise SystemExit(f"{c['id']}: palavra '{em}' nao achada entre {cur:.1f} e {t1:.1f}")
                t = round(cand[0]["start"] - LEAD, 2)
        t = max(t, cur)
        tempos.append(t)
        cur = t
    # permanência mínima: antecipa os últimos beats (de trás para frente) para nada "piscar"
    out_t = t1 - SAIDA
    beats = sorted(set(tempos))
    novo, teto = {}, out_t - MIN_PERMANENCIA
    for b in reversed(beats):
        novo[b] = min(b, teto)
        teto = novo[b] - MIN_INTERVALO
    ant = t0
    for b in beats:  # piso: nunca antes do início da cena; mantém ordem
        novo[b] = max(novo[b], ant)
        ant = novo[b]
    tempos = [round(novo[t], 2) for t in tempos]
    nomes = {t0: "in"}
    for t in tempos:
        if t not in nomes:
            nomes[t] = f"b{len(nomes)}"
    out_items = []
    for i, it in enumerate(itens):
        if not it["img"]:
            x, y, h = 0, 0, 0
        elif it["sobre"]:
            bx, by = pos[idx[it["sobre"]]]
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
                placa=it["placa"],
                moldura=it["moldura"],
                redondo=it["redondo"],
                rotulo=it["rotulo"],
                beat=nomes[tempos[i]],
                destaque=it["destaque"],
                alvo=idx[it["alvo"]] if it["alvo"] else None,
                **escala_geom(it, s),
            )
        )
    checar_proporcao(itens, out_items, s, c["id"])
    # arestas
    LR = c["dir"] == "LR"
    lados = ("right", "left") if LR else ("bottom", "top")
    arestas, vistos = [], set()
    pares = [(idx[p], i) for i, it in enumerate(itens) for p in it["pais"]] + [
        (idx[a], idx[b]) for a, b in c["liga"]
    ]
    pares = list(dict.fromkeys(pares))
    barras = bus_arestas(itens, out_items, pares, LR)
    for a, b in pares:
        if (a, b) in vistos:
            continue
        vistos.add((a, b))
        dy = abs(out_items[a]["y"] - out_items[b]["y"]) if LR else abs(out_items[a]["x"] - out_items[b]["x"])
        quando = (
            a if tempos[a] > tempos[b] else b
        )  # a seta se desenha quando o último dos dois extremos aparece
        arestas.append(
            dict(
                de=a,
                para=b,
                quando=quando,
                lados=list(lados),
                estilo="reta" if dy < 8 else "cotovelo",
                bus=barras[(a, b)],
            )
        )
    ev = [(f"{c['id']}-{nomes[t]}", t) for t in sorted(nomes)]
    return dict(tipo="grafo", id=c["id"], itens=out_items, arestas=arestas), ev


def bbox_real(itens, out):
    """Caixa que envolve TODOS os itens desenhados (placa + rótulo, com a largura real do logo): (x0, y0, x1, y1) em px."""
    rs = [retangulo(itens[i], out[i]) for i in range(len(itens)) if itens[i]["img"]]
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))


def grafo_estatico(itens, dir_, liga, W, H):
    """Layout de um grafo/árvore dentro de uma região WxH (para peças de cenas compostas). Revelação sequencial no TS."""
    for it in itens:
        resolver_imagem(it)
    idx = {it["id"]: i for i, it in enumerate(itens) if it["id"]}
    pos, s, depth = layout(itens, dir_, W, H, smax=1.0)  # a ampliação final (ESCALA_GRAFO) é feita depois, com o bbox real
    out = []
    for i, it in enumerate(itens):
        if it["sobre"]:
            bx, by = pos[idx[it["sobre"]]]
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
                placa=it["placa"],
                moldura=it["moldura"],
                redondo=it["redondo"],
                rotulo=it["rotulo"],
                destaque=False,
                alvo=None,
                **escala_geom(it, s),
            )
        )
    checar_proporcao(itens, out, s, "peça-grafo")
    LR = dir_ == "LR"
    lados = ("right", "left") if LR else ("bottom", "top")
    arestas, vistos = [], set()
    pares = [(idx[p], i) for i, it in enumerate(itens) for p in it["pais"]] + [
        (idx[a], idx[b]) for a, b in liga
    ]
    pares = list(dict.fromkeys(pares))
    barras = bus_arestas(itens, out, pares, LR)
    for a, b in pares:
        if (a, b) in vistos:
            continue
        vistos.add((a, b))
        dy = abs(out[a]["y"] - out[b]["y"]) if LR else abs(out[a]["x"] - out[b]["x"])
        arestas.append(
            dict(
                de=a,
                para=b,
                quando=max(a, b),
                lados=list(lados),
                estilo="reta" if dy < 8 else "cotovelo",
                bus=barras[(a, b)],
            )
        )
    bbox = bbox_real(itens, out)
    return out, arestas, bbox


def montar_texto(c, t0, t1):
    linhas = c["linhas"]
    mx = max(len(re.sub(r"\*([a-z]:)?", "", l)) for l in linhas) + 2
    estilo = c.get("estilo") or ESTILO_TITULO[0]
    if estilo == "reportagem":
        tam = int(max(70, min(140, 1600 / (max(len(re.sub(r"\*([a-z]:)?", "", l)) for l in linhas) * 0.72))))
    else:
        tam = int(max(54, min(96, 1500 / (mx * 0.61))))
    return dict(
        tipo="impacto", id=c["id"], linhas=linhas, tam=tam, tag=c.get("tag", "atenção"), estilo=estilo
    ), [(f"{c['id']}-in", t0)]


def resolver_tempos_pecas(c, pecas, t0, t1, piso):
    """Resolve beats das peças (palavra seguinte à anterior), aplica piso (menu) e permanência mínima."""
    cur = max(t0, piso)
    busca = t0
    tempos = []
    for p in pecas:
        em = p["em"]
        if em is None:
            t = cur
        elif isinstance(em, tuple):
            t = A(em[1], em[0])
            busca = t
        else:
            pp = norm(em)
            cand = [
                w
                for w in WORDS
                if w["start"] >= busca + 0.05 and norm(w["word"]).startswith(pp) and w["start"] < t1 - 0.4
            ]
            if not cand:
                raise SystemExit(f"{c['id']}: palavra '{em}' nao achada entre {busca:.1f} e {t1:.1f}")
            t = round(cand[0]["start"] - LEAD, 2)
            busca = t
        t = max(t, cur, piso)
        tempos.append(t)
        cur = t
    out_t = t1 - SAIDA
    beats = sorted(set(tempos))
    novo, teto = {}, out_t - MIN_PERMANENCIA
    for b in reversed(beats):
        novo[b] = min(b, teto)
        teto = novo[b] - MIN_INTERVALO
    ant = max(t0, piso)
    for b in beats:
        novo[b] = max(novo[b], ant)
        ant = novo[b]
    tempos = [round(novo[t], 2) for t in tempos]
    # peças NÃO podem aparecer durante um clipe de B-roll: empurra para o fim da janela
    for k, t in enumerate(tempos):
        for a, b in JC.get(c["id"], []):
            if a - CFG["LEAD_CLIPE"] - 0.05 <= t < b + CFG["FOLGA_CLIPE"]:
                AVISOS_BROLL.append(
                    f"[{c['id']}] peça {pecas[k]['tipo']} em {t:.1f}s cai dentro do clipe {a:.1f}-{b:.1f}: movida para {b:.1f}s"
                )
                tempos[k] = round(b + CFG["FOLGA_CLIPE"], 2)
    nomes = {t0: "in"}
    for t in tempos:
        if t not in nomes:
            nomes[t] = f"b{len(nomes)}"
    return tempos, nomes


def montar_composta(c, t0, t1):
    pecas = c["pecas"]
    piso = t0 + (MENU_DURACAO if c.get("menu") else 0)
    tempos, nomes = resolver_tempos_pecas(c, pecas, t0, t1, piso)
    # GUARDA: peça precisa caber ENTRE clipes (>= 2.5 s de exibição antes do próximo clipe / da próxima peça do mesmo slot); senão é descartada
    manter = []
    for k, (p, t) in enumerate(zip(pecas, tempos)):
        fim = t1 - SAIDA
        for a_, b_ in JC.get(c["id"], []):
            if a_ > t + 0.05:
                fim = min(fim, a_ - CFG["LEAD_CLIPE"] - 0.1)
        if p["slot"] == "dir":
            for p2, t2 in zip(pecas[k + 1 :], tempos[k + 1 :]):
                if p2["slot"] == "dir" and t2 > t + 0.05:
                    fim = min(fim, t2)
                    break
        if fim - t < 2.5 and p["tipo"] != "titulo":
            AVISOS_BROLL.append(
                f"[{c['id']}] peça {p['tipo']} em {t:.1f}s DESCARTADA: só {max(fim - t, 0):.1f}s livres antes do próximo clipe/peça"
            )
        else:
            manter.append(k)
    pecas = [pecas[k] for k in manter]
    tempos = [tempos[k] for k in manter]
    out = []
    for p, t in zip(pecas, tempos):
        props = dict(p["props"])
        if p["tipo"] == "logo":
            props["asp"] = round(aspecto(props["logo"]), 3) if props.get("logo") else 1
        if p["tipo"] == "logosolto":
            props["asp"] = round(aspecto(props["logo"]), 3)
            props["placa"] = (
                precisa_placa(props["logo"])
                if props.get("placa_forcada") is None
                else bool(props["placa_forcada"])
            )
        if p["tipo"] == "fatos":
            props["linhas"] = [
                dict(icone=resolver_icone(l["icone"]), texto=l["texto"]) for l in props["linhas"]
            ]
        if p["tipo"] == "secao":
            props["logos"] = list(props["logos"])
            for _lg in props[
                "logos"
            ]:  # logos da Secao: todos do MESMO tamanho (quadrados 96px); logo largo (> 1.3:1) deforma — use o ícone/versão quadrada
                if aspecto(_lg) > 1.3 or aspecto(_lg) < 0.77:
                    AVISOS.append(
                        f"[{c['id']}] logo '{_lg}' da Secao não é quadrado ({aspecto(_lg):.2f}:1): use a versão quadrada/ícone (ex.: logo_win11_icone em vez de logo_microsoft)"
                    )
        if p["tipo"] == "grafo":
            ems = [it.get("em") for it in props["itens"]]
            itens_g, arestas_g, bbox_g = grafo_estatico(props["itens"], props["dir"], props["liga"], 1700, 800)
            eventos_g, busca_g = [], t
            for k_, em_ in enumerate(ems):
                if em_ is None:
                    eventos_g.append(None)
                    continue
                if isinstance(em_, tuple):
                    tg = A(em_[1], em_[0])
                else:
                    cand = [
                        w
                        for w in WORDS
                        if w["start"] >= busca_g + 0.05
                        and norm(w["word"]).startswith(norm(em_))
                        and w["start"] < t1 - 0.4
                    ]
                    if not cand:
                        raise SystemExit(
                            f"{c['id']}: palavra de item de grafo '{em_}' nao achada apos {busca_g:.1f}s"
                        )
                    tg = round(cand[0]["start"] - LEAD, 2)
                tg = max(tg, busca_g + 0.05)
                for a_, b_ in JC.get(c["id"], []):
                    if a_ - CFG["LEAD_CLIPE"] - 0.05 <= tg < b_ + CFG["FOLGA_CLIPE"]:
                        AVISOS.append(
                            f"[{c['id']}] item de grafo em {tg:.1f}s cai dentro do clipe {a_:.1f}-{b_:.1f}: ajuste a janela do clipe/âncora (com STRICT=0 o item é empurrado para depois do clipe, fora de sincronia)"
                        )
                        tg = round(b_ + CFG["FOLGA_CLIPE"], 2)
                busca_g = tg
                nome_g = f"g{len(EV_G)}_{c['id']}"
                EV_G.append((f"{c['id']}-{nome_g}", tg))
                eventos_g.append(f"{c['id']}-{nome_g}")
            # o grafo COMPLETO (último item) precisa ficar visível >= 2.5 s antes de o próximo clipe/fim da cena escondê-lo
            _ult = max([e[1] for e in EV_G if e[0].startswith(c["id"] + "-")] + [t])
            _esconde = min([a_ - CFG["LEAD_CLIPE"] for a_, _ in JC.get(c["id"], []) if a_ - CFG["LEAD_CLIPE"] > t] + [t1 - SAIDA])
            if _esconde - _ult < 2.5:
                AVISOS.append(
                    f"[{c['id']}] grafo de {t:.1f}s não completa: último item em {_ult:.1f}s e some em {_esconde:.1f}s (< 2.5 s completo); "
                    f"antecipe os itens, encurte o grafo ou mova o clipe (animação 'só de um lado' é proibida)"
                )
            props = dict(itens=itens_g, arestas=arestas_g, eventos=eventos_g, esc=CFG["ESC_GRAFO"])
            # Ampliação automática com o bbox REAL (largura de logos incluída): até ESCALA_GRAFO, limitada pelo que cabe no quadro (±900 × ±480),
            # recentralizada, e fora da zona do avatar do canal (canto inferior direito).
            if itens_g:
                rx0, ry0, rx1, ry1 = bbox_g
                e_ = round(min(CFG["ESC_GRAFO"], 1800 / max(rx1 - rx0, 1), 960 / max(ry1 - ry0, 1)), 2)
                props["esc"] = e_
                cx, cy = (rx0 + rx1) / 2, (ry0 + ry1) / 2  # recentraliza o grafo
                props["dx"], props["dy"] = round(-cx * e_, 1), round(-cy * e_, 1)
                x0, x1, y0, y1 = (rx0 - cx) * e_, (rx1 - cx) * e_, (ry0 - cy) * e_, (ry1 - cy) * e_
                for _k, _g in enumerate(itens_g):  # nenhum elemento pode ser gigante (placa larga de logo cortada na borda)
                    _w = max(_g.get("pw") or 0, _g.get("iw") or 0, _g["h"]) * e_
                    _h = max(_g.get("ph") or 0, _g["h"]) * e_
                    if _w > 720 or _h > 520:
                        AVISOS.append(
                            f"[{c['id']}] item {_k + 1} do grafo ({_g['img']}) fica gigante ({_w:.0f}x{_h:.0f}px): diminua `h` ou use logo mais compacto"
                        )
                if e_ < 1.2:
                    AVISOS.append(
                        f"[{c['id']}] grafo só cabe ampliado {e_}x (< 1.2x: pequeno demais, o usuário dá zoom à mão): menos itens/ramos"
                    )
                if x1 > ZONA_AVATAR[0] and y1 > ZONA_AVATAR[1]:
                    AVISOS.append(
                        f"[{c['id']}] grafo invade a zona do avatar (canto inferior direito): {x1:.0f},{y1:.0f}"
                    )
                n_ic = sum(1 for it in props["itens"] if str(it["img"]).startswith("ic-"))
                if len(props["itens"]) >= 2 and n_ic == len(props["itens"]) and not CFG.get("WEBDOC"):
                    AVISOS.append(
                        f"[{c['id']}] grafo só com ícones genéricos: use ao menos uma logo/foto real do assunto"
                    )
        if p["tipo"] == "titulo":
            # duração de permanência = o que sobra até o próximo beat (menos entrada digitada, saída e retorno do resto)
            palavras_t = [w for l in props["linhas"] for w in re.sub(r"\*([a-z]:)?", "", l).split()]
            digitando = 0.7 + sum(max(0.07, len(w) * 0.028) + 0.04 for w in palavras_t)
            prox = [x for x in tempos if x > t + 0.05] + [t1 - SAIDA]
            folga = min(prox) - t - digitando - 0.8
            props["dur"] = round(max(0.6, min(props["dur"], folga)), 2)
            if folga < 0.6:
                AVISOS.append(
                    f"[{c['id']}] título curto demais antes do próximo beat (folga {folga:.1f}s): mova o título ou o beat seguinte"
                )
            TITULOS_PECAS.append((t, props["dur"] + digitando))
            mx = max(len(re.sub(r"\*([a-z]:)?", "", l)) for l in props["linhas"]) + 2
            props["tam"] = int(max(56, min(84, 1500 / (mx * 0.61))))
        out.append(dict(slot=p["slot"], tipo=p["tipo"], props=props, beat=nomes[t]))
    VIDA_PECAS[c["id"]] = []
    for _p, _t in zip(pecas, tempos):
        _some = min([a_ - CFG["LEAD_CLIPE"] for a_, _ in JC.get(c["id"], []) if a_ - CFG["LEAD_CLIPE"] > _t] + [t1 - SAIDA])
        if _p["tipo"] != "titulo":
            VIDA_PECAS[c["id"]].append((_t, _some))
    js = dict(tipo="secao" if c["tipo"] == "secao" else "item", id=c["id"], pecas=out)
    if c["tipo"] == "item":
        i = c["idx"]
        js.update(
            idx=i,
            total=len(MENU),
            nome=MENU[i - 1][0],
            cor=MENU[i - 1][2],
            menu=dict(de=i - 2, para=i - 1) if c.get("menu") else None,
            sub=c.get("sub", ""),
            hud=bool(CFG["HUD"]),
            logo=c.get("logo"),
            logo_placa=bool(c.get("logo") and precisa_placa(c["logo"])),
            logo_asp=round(aspecto(c["logo"]), 3) if c.get("logo") else 1,
        )
    ev = [(f"{c['id']}-{nomes[t]}", t) for t in sorted(nomes)]
    ev += [e for e in EV_G if e[0].startswith(c["id"] + "-")]
    EV_G[:] = [e for e in EV_G if not e[0].startswith(c["id"] + "-")]
    # janelas de B-roll: o motor esconde as peças no início de cada clipe (evento <id>-vaK)
    for k_, (a_, b_) in enumerate(JC.get(c["id"], [])):
        ev.append(
            (f"{c['id']}-va{k_}", round(a_ - CFG["LEAD_CLIPE"], 2))
        )  # peças somem ANTES do clipe (nunca vazam alguns frames sobre o B-roll)
    js["nva"] = len(JC.get(c["id"], []))
    ev.sort(key=lambda e: e[1])
    return js, ev


def montar_listacurta(c, t0, t1):
    """ListaCurta: cartões numerados entrando um a um na fala. Eventos <id>-in, <id>-i0..iN, <id>-out."""
    out_t = t1 - SAIDA
    cur = t0 + 0.9
    busca = t0
    ev = [(f"{c['id']}-in", t0)]
    itens_js = []
    for k, (ic, rot, em) in enumerate(c["itens"]):
        if em is None:
            t = cur
        elif isinstance(em, tuple):
            t = A(em[1], em[0])
        else:
            pp = norm(em)
            cand = [
                w
                for w in WORDS
                if w["start"] >= busca + 0.05 and norm(w["word"]).startswith(pp) and w["start"] < t1 - 0.4
            ]
            if not cand:
                raise SystemExit(
                    f"{c['id']}: palavra '{em}' do item {k + 1} nao achada entre {busca:.1f} e {t1:.1f}"
                )
            t = round(cand[0]["start"] - LEAD, 2)
        t = round(max(t, cur), 2)
        if k and t < ev[-1][1] + 1.2 - 1e-6:
            AVISOS.append(
                f"[{c['id']}] itens {k} e {k + 1} da lista a {t - ev[-1][1]:.1f}s (< 1.2 s): cartões entrando colados"
            )
        ev.append((f"{c['id']}-i{k}", t))
        cur = t + 1.2
        busca = t
        partes = ic[3:].split(":") if ic.startswith("ic:") else None
        if not partes:
            raise SystemExit(f"ListaCurta '{c['id']}': icone '{ic}' deve ser 'ic:nome'")
        itens_js.append(
            dict(
                icone=garantir_icone(partes[0], partes[1] if len(partes) > 1 else None), rotulo=rot, num=k + 1
            )
        )
    if out_t - ev[-1][1] < 1.6:
        raise SystemExit(
            f"{c['id']}: o ultimo item da lista entra a {out_t - ev[-1][1]:.1f}s do fim da cena (< 1.6 s): estenda a cena ou antecipe o item"
        )
    # pausas: a lista some (fade 0.3 s) para o B-roll e volta inteira; vídeo só vale em [ini+0.35, fim-0.05]
    item_ts = [t for n_, t in ev if "-i" in n_ and not n_.endswith("-in")]
    busca_p = t0
    pausas_js = []
    for j, (pa, pb) in enumerate(c.get("pausas") or []):
        tt = []
        for em in (pa, pb):
            if isinstance(em, (int, float)):
                tt.append(float(em))
                continue
            if isinstance(em, tuple):
                tt.append(A(em[1], em[0]))
                continue
            pp = norm(em)
            cand = [
                w
                for w in WORDS
                if w["start"] >= busca_p + 0.05 and norm(w["word"]).startswith(pp) and w["start"] < t1 - 0.4
            ]
            if not cand:
                raise SystemExit(f"{c['id']}: palavra '{em}' da pausa {j} nao achada apos {busca_p:.1f}s")
            tt.append(round(cand[0]["start"] - LEAD, 2))
        ta, tb = tt
        busca_p = tb
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
        pausas_js.append([round(ta, 2), round(tb, 2)])
        JANELAS_VIDEO.setdefault(c["id"], []).append([round(ta + 0.35, 2), round(tb - 0.05, 2)])
    ev.sort(key=lambda e: e[1])
    return (
        dict(
            tipo="listacurta",
            id=c["id"],
            titulo=c["titulo"],
            cor=c["cor"],
            total=len(c["itens"]),
            itens=itens_js,
            pausas=pausas_js,
        ),
        ev,
    )


def montar_broll(c, t0, t1):
    """Janela de B-roll: overlay leve (rótulo/data/logo no canto inferior esquerdo) por ~dur_rotulo s, ou nada."""
    dur = min(float(c["dur_rotulo"]), (t1 - SAIDA - t0) - 1.6)
    tem = bool(c.get("rotulo") or c.get("data") or c.get("logo"))
    leve = None
    if tem and dur >= 1.5:
        leve = [round(t0 + 0.6, 2), round(t0 + 0.6 + dur, 2)]
        OVERLAY_LEVE.append(leve)
    elif tem:
        print(f"AVISO B-ROLL: [{c['id']}] janela curta demais para o rótulo ({t1 - t0:.1f}s): rótulo omitido")
    js = dict(
        tipo="broll",
        id=c["id"],
        rotulo=c.get("rotulo") if leve else None,
        data=c.get("data") if leve else None,
        dur=round(dur, 2) if leve else 0,
        logo=c.get("logo") if leve else None,
        logo_asp=round(aspecto(c["logo"]), 3) if (leve and c.get("logo")) else 1,
        logo_placa=bool(leve and c.get("logo") and precisa_placa(c["logo"])),
    )
    if leve and c.get("data"):
        garantir_icone("calendar", None)
    return js, [(f"{c['id']}-in", t0)]


def montar_tempo(c, t0, t1):
    tempos = []
    cur = t0
    for i, em in c["marcos"]:
        if em is None:
            t = cur
        else:
            pp = norm(em)
            cand = [
                w
                for w in WORDS
                if w["start"] >= cur + 0.05 and norm(w["word"]).startswith(pp) and w["start"] < t1 - 0.4
            ]
            if not cand:
                raise SystemExit(f"{c['id']}: palavra '{em}' nao achada entre {cur:.1f} e {t1:.1f}")
            t = round(cand[0]["start"] - LEAD, 2)
        tempos.append(t)
        cur = t
    out_t = t1 - SAIDA
    beats = sorted(set(tempos))
    novo, teto = {}, out_t - MIN_PERMANENCIA
    for b in reversed(beats):
        novo[b] = min(b, teto)
        teto = novo[b] - MIN_INTERVALO
    ant = t0
    for b in beats:
        novo[b] = max(novo[b], ant)
        ant = novo[b]
    tempos = [round(novo[t], 2) for t in tempos]
    nomes = {t0: "in"}
    for t in tempos:
        if t not in nomes:
            nomes[t] = f"b{len(nomes)}"
    itens = []
    for it in c["itens"]:
        itens.append(dict(it))
    marcos = [dict(beat=nomes[t], i=i) for (i, _), t in zip(c["marcos"], tempos)]
    js = dict(
        tipo="tempo",
        id=c["id"],
        pecas=[dict(slot="centro", tipo="tempo", props=dict(itens=itens, marcos=marcos), beat="in")],
    )
    ev = [(f"{c['id']}-{nomes[t]}", t) for t in sorted(nomes)]
    return js, ev


def resolver_icone(ref):
    """'ic:nome[:cor]' -> stem do arquivo em src/images (gera o svg)."""
    if ref.startswith("ic:"):
        partes = ref[3:].split(":")
        return garantir_icone(partes[0], partes[1] if len(partes) > 1 else None)
    return ref


def fmt(t):
    return f"{int(t//60):02d}:{t%60:05.2f}"


def frase(ini, fim):
    return " ".join(w["word"].strip() for w in WORDS if w["start"] >= ini - 0.05 and w["end"] <= fim + 0.3)


if __name__ == "__main__":
    import importlib

    _pd = importlib.import_module(os.environ.get("PLANO_DADOS", "plano_dados"))
    CENAS = _pd.CENAS
    LOGOS_PLACA.update(getattr(_pd, "LOGOS_COM_PLACA", []))
    CFG.update(
        WEBDOC=getattr(_pd, "TIPO_VIDEO", "") == "webdoc_broll",
        HUD=bool(getattr(_pd, "HUD_ITEM", False)),
        EXT=bool(getattr(_pd, "MENU_EXTENSOES", False)),
        LOGO_CARTELA=bool(getattr(_pd, "CARTELA_LOGO_OBRIGATORIA", False)),
        ANIM_MAX=float(getattr(_pd, "ANIM_MAX", 0.35)),
        EXIGE_LOGO=bool(getattr(_pd, "PECAS_EXIGEM_LOGO", False)),
        ESC_GRAFO=float(getattr(_pd, "ESCALA_GRAFO", 1.5)),
        LEAD_CLIPE=float(getattr(_pd, "LEAD_CLIPE", 0.4)),
        FOLGA_CLIPE=float(getattr(_pd, "FOLGA_CLIPE", 0.15)),
    )
    for _c in CENAS:
        if _c.get("tipo") == "item" and CFG["LOGO_CARTELA"] and not _c.get("logo"):
            raise SystemExit(
                f"item '{_c['id']}': cartela sem logo (L(..., logo='logo_x')): o quadro da cartela fica vazio sem a logo do sistema"
            )
    try:
        COBERTURA = _pd.COBERTURA
    except AttributeError:
        COBERTURA = (88, 92)  # padrão: ~90%

    ESTILO_TITULO[0] = getattr(_pd, "ESTILO_TITULO", "monokai")
    try:
        MENU[:] = _pd.MENU
    except AttributeError:
        pass
    import re as _re

    for _n in set(
        _re.findall(
            r'"((?:logo|foto|tela|ic)_[a-z0-9_]+|microsoft|windows11|logo_exemplo|ram_modulo)"',
            open(os.environ.get("PLANO_DADOS", "plano_dados") + ".py").read(),
        )
    ):
        if not any(os.path.exists(f"src/images/{_n}.{e}") for e in ("png", "jpg", "webp", "svg")):
            puxar_asset(_n)
    if getattr(_pd, "OVERLAY_MINIMO", False):
        # Lista com B-roll: overlay SÓ com menu+cartela, HUD, e cartela/Secao na abertura e no fim. Nada de grafos/setas/fatos/etc.
        for c in CENAS:
            if c["tipo"] in ("grafo", "impacto", "tempo"):
                raise SystemExit(
                    f"OVERLAY_MINIMO: cena '{c['id']}' do tipo {c['tipo']} nao e permitida na Lista com B-roll (use L(..., pecas=[]), Secao ou V)"
                )
            if c["tipo"] == "item" and c["pecas"]:
                raise SystemExit(
                    f"OVERLAY_MINIMO: item '{c['id']}' tem pecas; neste tipo o item fica so com B-roll (pecas=[])"
                )
    for _it, _arq, _i0, _i1, _vel, _t0 in getattr(_pd, "BROLL", []):
        JC.setdefault(_it, []).append((_t0, _t0 + (_i1 - _i0) / _vel))
    expandir_logos(CENAS)
    ins, prev = [], 0.0
    for c in CENAS:
        e = c["entrada"]
        if isinstance(e, dict):
            e = resolver_frase(e["_frase"], prev)
        ins.append(e)
        prev = e
    for fixo in ("files", "search", "git-branch"):
        garantir_icone(fixo, "cinza")
    garantir_icone("user", None)
    assert ins == sorted(ins) and ins[0] == 0.0, [i for i, (a, b) in enumerate(zip(ins, ins[1:])) if b < a]
    # Propaganda do CapCut: a fala PARA numa pausa depois do gancho e RETOMA na entrada de uma cena (fronteira de cena: nenhuma animação é
    # cortada ao meio). PROPAGANDA_APOS = F("frase") da cena que retoma; o silêncio entre o fim da fala anterior e a retomada é removido.
    PROPAGANDA_T[0] = PROPAGANDA_T[1] = None
    _prop = getattr(_pd, "PROPAGANDA_APOS", None)
    if _prop is not None:
        _tr = resolver_frase(_prop["_frase"], 0.0) if isinstance(_prop, dict) else float(_prop)
        if not any(abs(_tr - x) < 0.06 for x in ins):
            raise SystemExit(
                f"PROPAGANDA_APOS ({_tr:.2f}s) não coincide com o início de uma cena: use F('frase') igual à entrada de uma cena "
                f"(cenas: {[round(x, 1) for x in ins[:12]]}...)"
            )
        _fim_fala = max((w["end"] for w in WORDS if w["end"] <= _tr + 0.05), default=_tr)
        _tp = min(_fim_fala + 0.65, _tr - 0.2)  # para um pouco depois da última palavra
        if _tr - _tp < 0.2:
            _tp = _tr  # sem pausa útil: não há silêncio a remover
        PROPAGANDA_T[0], PROPAGANDA_T[1] = round(_tp, 2), round(_tr, 2)
    ERROS = []
    cenas_json, eventos, md_rows = [], [], []
    tot_img = tot_txt = tot_vazio = 0
    primeiro_titulo = None
    for k, c in enumerate(CENAS):
        t0 = ins[k]
        t1 = ins[k + 1] if k + 1 < len(CENAS) else DUR
        out_t = round(t1 - SAIDA, 2)  # a última cena sai 0.3s antes do fim do áudio
        if c["tipo"] == "vazio":
            VAZIOS.add(c["id"])
            tot_vazio += t1 - t0
            md_rows.append(
                f"| {k+1} | `{c['id']}` | vazio | {fmt(t0)}–{fmt(t1)} | {t1-t0:.1f}s | {frase(t0, t1)[:90]} | (tela transparente) |"
            )
            continue
        try:
            if c["tipo"] == "grafo":
                js, ev = montar_grafo(c, t0, t1)
            elif c["tipo"] == "impacto":
                js, ev = montar_texto(c, t0, t1)
            elif c["tipo"] in ("item", "secao"):
                js, ev = montar_composta(c, t0, t1)
            elif c["tipo"] == "tempo":
                js, ev = montar_tempo(c, t0, t1)
            elif c["tipo"] == "listacurta":
                js, ev = montar_listacurta(c, t0, t1)
            elif c["tipo"] == "broll":
                js, ev = montar_broll(c, t0, t1)
                VAZIOS.add(c["id"])  # vídeo conta como coberto; sem aviso de ">5 s sem evento"
            else:
                raise SystemExit("tipo desconhecido " + c["tipo"])
        except SystemExit as e:
            ERROS.append(f"{e}  [{t0:.1f}-{t1:.1f}]")
            continue
        assert all(t < out_t for _, t in ev), f"{c['id']}: evento depois da saida"
        eventos += ev + [(f"{c['id']}-out", out_t)]
        cenas_json.append(js)
        if c["tipo"] == "impacto":
            tot_txt += t1 - t0
            primeiro_titulo = t0 if primeiro_titulo is None else primeiro_titulo
        else:
            tot_img += t1 - t0
        if c["tipo"] == "grafo":
            o = " + ".join(it["img"] for it in c["itens"] if it["img"])
        elif c["tipo"] == "impacto":
            o = " / ".join(c["linhas"])
        elif c["tipo"] == "listacurta":
            o = f"lista curta ({len(c['itens'])}): " + " · ".join(i[1] for i in c["itens"])
        elif c["tipo"] == "broll":
            o = "B-roll" + (f" · rótulo: {c['rotulo']}" if c.get("rotulo") else "")
        else:
            o = (
                c["tipo"] + ": " + ", ".join(p["tipo"] for p in c.get("pecas", []))
                if c["tipo"] != "tempo"
                else "linha do tempo"
            )
        md_rows.append(
            f"| {k+1} | `{c['id']}` | {c['tipo']} | {fmt(t0)}–{fmt(t1)} | {t1-t0:.1f}s | {frase(t0, t1)[:90]} | {o} |"
        )
    if AVISOS:
        print("\n".join("AVISO PROPORÇÃO: " + a for a in AVISOS))
        if os.environ.get("STRICT", "1") == "1":
            ERROS.append(f"{len(AVISOS)} problema(s) de proporção/sobreposição (STRICT=0 ignora)")
    if ERROS:
        raise SystemExit("\n".join(ERROS))
    eventos.append(("fim", round(DUR, 2)))
    # regra: no máximo ~5 s sem animação (a "respiração" cobre pequenos buracos; avisa o que passar disso)
    LIM = 5.0
    ordem_ev = sorted(eventos, key=lambda e: e[1])
    for (n1, t1_), (n2, t2_) in zip(ordem_ev, ordem_ev[1:]):
        if t2_ - t1_ > LIM and not n1.split("-")[0] in VAZIOS and n2 != "fim":
            AVISOS_GAP.append(f"{n1} -> {n2}: {t2_ - t1_:.1f}s")
    if AVISOS_GAP and not getattr(_pd, "OVERLAY_MINIMO", False):
        print(
            "AVISO >5s SEM EVENTO (trecho parado é aceito; só adicione beat se houver conteúdo legítimo):\n  "
            + "\n  ".join(AVISOS_GAP)
        )
    nomes = [n for n, _ in eventos]
    assert len(nomes) == len(set(nomes))
    ts = [t for _, t in eventos]
    ruins = [(n, t) for (n, t), p in zip(eventos, [0] + ts) if t < p]
    assert not ruins, ruins
    pct_cob = 100 * (tot_img + tot_txt) / DUR  # cobertura (títulos de peças já estão dentro dos itens)
    for _t, _d in TITULOS_PECAS:
        tot_txt += _d
        primeiro_titulo = _t if primeiro_titulo is None else min(primeiro_titulo, _t)
    pct_txt = 100 * tot_txt / DUR
    tmax = getattr(_pd, "TITULOS_MAX", 5)
    tmin = getattr(_pd, "TITULO_MIN_INICIO", 30)
    assert pct_txt <= tmax, f"textos de impacto devem ficar em ate {tmax}% (estao em {pct_txt:.1f}%)"
    assert (
        primeiro_titulo is None or primeiro_titulo >= tmin
    ), f"nunca coloque titulo no comeco do video (>={tmin}s)"
    assert (
        COBERTURA[0] <= pct_cob <= COBERTURA[1]
    ), f"cobertura deve ficar entre {COBERTURA[0]}% e {COBERTURA[1]}% (esta em {pct_cob:.1f}%)"
    # ---- B-roll (tipo "Lista com B-roll"): BROLL = [(item_id, arquivo, in, out, velocidade, t_inicio_timeline), ...] ----
    broll = list(getattr(_pd, "BROLL", []))
    janelas = {
        c["id"]: (ins[k], (ins[k + 1] if k + 1 < len(CENAS) else DUR) - SAIDA, c["tipo"])
        for k, c in enumerate(CENAS)
    }
    por_item, fim_anterior = {}, 0.0
    webdoc = getattr(_pd, "TIPO_VIDEO", "") == "webdoc_broll"
    for item, arq, i0, i1, vel, t0 in sorted(broll, key=lambda b: b[5]):
        if webdoc:
            if item in JANELAS_VIDEO:
                if not any(
                    a_ - 0.03 <= t0 and t0 + (i1 - i0) / vel <= b_ + 0.03 for a_, b_ in JANELAS_VIDEO[item]
                ):
                    raise SystemExit(
                        f"BROLL: clipe {t0:.1f}s de '{item}' fora das pausas da lista {JANELAS_VIDEO[item]} (a lista só some dentro de ListaCurta(..., pausas=[...]))"
                    )
            elif item not in janelas or janelas[item][2] not in ("broll", "vazio"):
                raise SystemExit(
                    f"BROLL: '{item}' nao e uma janela B(...)/V(...) (no webdoc com B-roll o vídeo só roda em B/V ou nas pausas de uma ListaCurta; animação e vídeo não disputam a tela)"
                )
        elif item not in janelas or janelas[item][2] not in ("item", "secao", "vazio"):
            raise SystemExit(
                f"BROLL: '{item}' nao e uma cena de item/Secao/Bloco/V (B-roll não roda em G/Tx; use Bloco(...) no gancho e V/Secao no encerramento)"
            )
        ini, fim, _ = janelas[item]
        dur_tl = (i1 - i0) / vel
        if webdoc and item in JANELAS_VIDEO:
            ini = min(a_ for a_, _ in JANELAS_VIDEO[item])
        if not webdoc:
            _piso = MENU_DURACAO if janelas[item][2] == "item" else (3.0 if janelas[item][2] == "secao" else 0.0)
            assert t0 >= ini + _piso - 0.05, f"BROLL {item}: comeca antes do fim da cartela/animação inicial ({ini + _piso:.1f}s)"
        else:
            assert t0 >= ini - 0.05, f"BROLL {item}: comeca antes da janela ({ini:.1f}s)"
        assert t0 + dur_tl <= fim + 0.05, f"BROLL {item}: passa do fim do item ({fim:.1f}s)"
        assert (
            1.0 <= vel <= 2.0
        ), f"BROLL {item}: velocidade {vel} (entre 1.0 e 2.0; o usuário estica o clipe com 1.3-1.9x ao remover animações)"
        assert t0 >= fim_anterior - 0.01, f"BROLL {item}: sobrepoe o clipe anterior"
        if por_item.get(item):  # vão entre dois clipes da MESMA janela: ou 0 ou uma janela de animação de verdade (>= 4 s)
            _gap = t0 - por_item[item][-1]["t_fim"]
            if 0.05 < _gap < 4.0:
                AVISOS.append(
                    f"[{item}] vão de {_gap:.1f}s entre dois clipes ({por_item[item][-1]['t_fim']:.1f}→{t0:.1f}s): pequeno demais para uma animação; "
                    f"estenda o clipe anterior até {t0:.1f}s (ou abra um vão >= 4 s com animação)"
                )
        if dur_tl < 3.0:
            print(
                "AVISO B-ROLL:",
                f"[broll {item}] clipe de {dur_tl:.1f}s na timeline (< 3 s: evite pisca-pisca)",
            )
        por_item.setdefault(item, []).append(
            dict(
                arquivo=arq,
                **{"in": i0, "out": i1},
                velocidade=vel,
                t_inicio=round(t0, 2),
                t_fim=round(t0 + dur_tl, 2),
            )
        )
        fim_anterior = t0 + dur_tl
    for a_ in AVISOS_BROLL:
        print("AVISO PEÇA×B-ROLL:", a_)
    if broll and not webdoc:
        # COBERTURA: nenhum trecho >= 2 s pode ficar só com o fundo e a fala (sem clipe E sem animação visível).
        livres_ok = set(getattr(_pd, "VAZIOS_PERMITIDOS", []))
        for it_id, (ini_, fim_, tp_) in janelas.items():
            if tp_ not in ("item", "secao", "vazio") or it_id in livres_ok:
                continue
            a0 = ini_ + (MENU_DURACAO if tp_ == "item" else 0.0)  # a cartela do item conta como conteúdo
            ocupado = [(x["t_inicio"], x["t_fim"]) for x in por_item.get(it_id, [])] + [
                (a, b) for a, b in VIDA_PECAS.get(it_id, [])
            ]
            if tp_ == "secao" and not VIDA_PECAS.get(it_id):
                ocupado.append((ini_, ini_ + 3.0))
            cur = a0
            for a, b in sorted(ocupado):
                if a - cur >= 2.0:
                    AVISOS.append(f"[{it_id}] {cur:.1f}–{a:.1f}s ({a - cur:.1f}s) só com fundo e fala: falta animação ou B-roll")
                cur = max(cur, b)
            if fim_ - cur >= 2.0:
                AVISOS.append(f"[{it_id}] {cur:.1f}–{fim_:.1f}s ({fim_ - cur:.1f}s) só com fundo e fala: falta animação ou B-roll")

        # proporção vídeo × animação (o usuário corta animação e estica B-roll: o padrão é VÍDEO; animação é tempero)
        tot_it = tot_cl = 0.0
        viol = []
        for it_id, (ini_, fim_, tp_) in janelas.items():
            if tp_ != "item":
                continue
            ut = fim_ - (ini_ + MENU_DURACAO)
            cl = sum(x["t_fim"] - x["t_inicio"] for x in por_item.get(it_id, []))
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
        t_b = sum(x["t_fim"] - x["t_inicio"] for l in por_item.values() for x in l)
        t_an = sum(
            j[1] - j[0] for k_, j in janelas.items() if j[2] in ("grafo", "secao", "tempo", "listacurta")
        )
        t_li = sum(j[1] - j[0] for j in janelas.values() if j[2] == "listacurta")
        t_ti = sum(j[1] - j[0] for j in janelas.values() if j[2] == "impacto")
        print(
            f"Webdoc com B-roll: B-roll {t_b:.0f}s ({100 * t_b / DUR:.0f}%) · animação {t_an - t_li:.0f}s ({100 * (t_an - t_li) / DUR:.0f}%) · listas curtas {t_li:.0f}s ({100 * t_li / DUR:.0f}%) · títulos {t_ti:.0f}s · só preenchimento (completar à mão) {max(0, DUR - t_b - t_an - t_ti):.0f}s"
        )
    for c_ in CENAS:
        for p_ in c_.get("pecas", []):
            if p_["tipo"] == "pessoas" and any(x["foto"] is None for x in p_["props"]["pessoas"]):
                print(
                    "AVISO:",
                    f"[{c_['id']}] Pessoas sem foto (silhueta genérica fica feia): use foto real ou remova a peça",
                )
    for item, l in por_item.items():
        if len(l) > getattr(_pd, "MAX_CLIPES_ITEM", 6 if webdoc else 2):
            print(
                "AVISO B-ROLL:",
                f"[broll {item}] {len(l)} clipes no mesmo item (o padrao e 1-2; 3 so em caso raro)",
            )
    for js in cenas_json:
        js["leve"] = False  # overlay NÃO é mais "leve": só HUD sobre o B-roll; animações completas nos vazios
    lista_broll = sorted([c for l in por_item.values() for c in l], key=lambda c: c["t_inicio"])
    json.dump(lista_broll, open("src/scenes/broll.json", "w"), ensure_ascii=False, indent=1)
    # prévia no editor (Motion Canvas): preenchimento + clipes (proxies 640x360 em src/videos/, gerados por scripts/broll/gerar_proxies.py).
    # Liga/desliga por PREVIA_BROLL no plano_dados.py (padrão True); NO RENDER FINAL fica desligada (o motor também a ignora ao renderizar).
    json.dump(
        dict(
            ativa=bool(getattr(_pd, "PREVIA_BROLL", True)) and bool(lista_broll),
            duracao=DUR,
            clipes=[
                dict(
                    video=f"clip_{i+1:02d}",
                    t0=c["t_inicio"],
                    dur=round(c["t_fim"] - c["t_inicio"], 3),
                    vel=c["velocidade"],
                    srcdur=round(c["out"] - c["in"], 3),
                )
                for i, c in enumerate(lista_broll)
            ],
        ),
        open("src/scenes/previa.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    if broll:
        cob = sum(c["t_fim"] - c["t_inicio"] for l in por_item.values() for c in l)
        print(
            f"B-roll: {len(broll)} clipes em {len(por_item)} itens, {cob:.1f}s ({100*cob/DUR:.1f}% do video)"
        )
    json.dump(cenas_json, open("src/scenes/cenas.json", "w"), ensure_ascii=False, indent=1)
    json.dump(
        dict(titulo=getattr(_pd, "TITULO_MENU", "ITENS"), estilo=getattr(_pd, "MENU_ESTILO", "explorador")),
        open("src/scenes/lista.json", "w"),
    )
    _det = list(getattr(_pd, "MENU_DETALHES", []))
    json.dump(
        [
            dict(
                rotulo=n, arquivo=(a if CFG["EXT"] else n), cor=c, detalhe=(_det[k] if k < len(_det) else "")
            )
            for k, (n, a, c) in enumerate(MENU)
        ],
        open("src/scenes/menu.json", "w"),
        ensure_ascii=False,
    )  # extensão só quando a lista é de ARQUIVOS (MENU_EXTENSOES=True)
    import subprocess

    subprocess.run(["node", "scripts/tokenizar.mjs"], check=True)
    meta_path = "src/scenes/cena1.meta"
    try:
        seed = json.load(open(meta_path)).get("seed", 1)
    except Exception:
        seed = 1
    json.dump(
        {"version": 0, "timeEvents": [{"name": n, "targetTime": t} for n, t in eventos], "seed": seed},
        open(meta_path, "w"),
        indent=2,
    )
    md = [
        "# Plano de animações\n",
        f"Duração do áudio: {DUR:.2f}s — cobertura {pct_cob:.1f}% ({len(CENAS)} blocos; vazio {tot_vazio:.1f}s)\n",
        f"Imagens/grafos: {tot_img:.1f}s ({100*tot_img/DUR:.1f}%) · Texto de impacto: {tot_txt:.1f}s ({pct_txt:.1f}%)\n",
        "| # | id | tipo | início–fim | dur | trecho da fala | o que aparece |",
        "|---|---|---|---|---|---|---|",
    ] + md_rows
    open("PLANO.md", "w").write("\n".join(md) + "\n")
    json.dump(
        {
            "duracao": DUR,
            "eventos": eventos,
            "janelas": {
                c["id"]: [
                    round(ins[k], 2),
                    round((ins[k + 1] if k + 1 < len(CENAS) else DUR) - SAIDA, 2),
                    c["tipo"],
                ]
                for k, c in enumerate(CENAS)
            },
            "menu_duracao": MENU_DURACAO,
            "propaganda_t": PROPAGANDA_T[0],
            "propaganda_retoma": PROPAGANDA_T[1],
            "final_antes_do_fim": getattr(_pd, "FINAL_ANTES_DO_FIM", 6.9),
            "overlay_leve": OVERLAY_LEVE,
            "janelas_video": JANELAS_VIDEO,
            "tipo_video": getattr(_pd, "TIPO_VIDEO", ""),
        },
        open("plano.json", "w"),
        ensure_ascii=False,
        indent=1,
    )
    print(
        f"{len(CENAS)} blocos, cobertura {pct_cob:.1f}%, texto {tot_txt:.1f}s ({pct_txt:.1f}%), eventos {len(eventos)}"
    )
