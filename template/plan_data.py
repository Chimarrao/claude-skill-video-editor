from plan import (
    Anchor, Phrase, GraphScene, Item, Impact, Empty, ListItem, Logo, People, Code, Stat, Facts, Graph, Title, Section, Timeline,
)

# Preencha SCENES (contíguas; primeira entrada 0.0). Veja examples/plan_data_template_list_with_broll.py (tipo lista) e
# examples/plan_data_template_webdoc_with_broll.py (tipo webdoc). Âncoras: Anchor(seg, 'palavra') ou Phrase('frase falada') (robusta a cortes).
COVERAGE = (88, 92)  # webdoc padrão 90%; lista/outros conforme o usuário responder
MAX_TITLES = 5  # % máx. de títulos de impacto
TITLE_STYLE = "monokai"  # 'monokai' (programação) | 'report' (webdoc sério)
MENU = []  # [(nome, id, cor)] — só tipo lista
SCENES = []

# ---- Lista COM B-roll: padrões definitivos (ver SKILL.md → "REGRAS DEFINITIVAS") ----
# HUD_ITEM = False                  # contador NN/10 removido em todos os tipos (o avatar do canal fica no canto inferior direito)
# MENU_EXTENSIONS = False           # extensões (.img/.py) só quando a lista é de ARQUIVOS
# TITLECARD_LOGO_REQUIRED = True    # ListItem(..., logo="logo_x") em todo item
# PIECES_REQUIRE_LOGO = True        # Stat/Facts ganham FreeLogo à esquerda (logo= da peça ou do item)
# GRAPH_SCALE = 1.5                 # grafo ampliado/recentralizado automaticamente (aviso se < 1.2x)
# ANIM_MAX = 0.35                   # teto de animação+vazio nos itens (meta real ~0.15)
# CLIP_LEAD = 0.4; CLIP_MARGIN = 0.15   # peças somem 0.4 s antes do clipe e entram 0.15 s depois
# MAX_CLIPS_PER_ITEM = 5
# BROLL = [(item, arquivo, in, out, vel 1.0-2.0, t_start_na_timeline), ...]   # item começa com vídeo (t_start >= início + 3.9 s)
# Exemplo de item: ListItem("haiku", Phrase("..."), 2, logo="logo_haiku_icon", sub="...", pieces=[
#     Graph([Item("ic:building", id="p", label="Palm compra a Be", h=140, at=("Palm", 149.8)), ...], at=("Palm", 149.8)),
#     Stat("25 anos", "de projeto rodando", at=("anos", 194.2)),            # FreeLogo automático à esquerda
#     Facts([("ic:puzzle", "Linux: peças de vários projetos")], at=("Linux", 239.5), logo="logo_tux")])

# ---- Webdoc COM B-roll (ver SKILL.md → "TIPO: Webdoc com B-roll"; esqueleto em examples/plan_data_template_webdoc_with_broll.py) ----
# VIDEO_KIND = "webdoc_broll"; TITLE_STYLE = "report"; COVERAGE = (60, 100.5); MENU = []
# SCENES: GraphScene(...) / Block(id, Phrase("..."), [peças]) / BrollWindow(id, Phrase("..."), label=, data=, logo=)
#         / ShortList(id, Phrase("..."), "Título", [("ic:x", "rótulo", "palavra")]) / Impact / Empty
# BROLL = [(id_da_janela_BrollWindow_ou_Empty, "../Assets/arquivo.mp4", in, out, vel 1.0-2.0, t_start)]    # vídeo só em BrollWindow/Empty
# Screenshot("asset:foto.jpg", "legenda curta") usa imagem da pasta Assets/ (nunca esticada).
