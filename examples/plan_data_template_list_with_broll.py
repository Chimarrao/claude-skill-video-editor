"""MODELO — Lista com B-roll (menu em estilo terminal `ls`). Copie para animacao/plan_data.py e preencha.
Âncoras Phrase("frase falada") sobrevivem a cortes no áudio. Peças: Stat/Fatos sempre com logo do assunto; Grafo ≥ 1 logo real; sem código.
"""

from plan import Anchor, Phrase, GraphScene, Item, Empty, ListItem, Section, Block, Stat, Facts, Graph

MINIMUM_OVERLAY = False
COVERAGE = (0, 100.5)
MENU_TITLE = "itens"  # vira `~/itens` no terminal
MENU_STYLE = "terminal"  # "terminal" (lista ls) ou "explorador"
MENU = [("Item Um", "item-um", "#66d9ef"), ("Item Dois", "item-dois", "#a6e22e")]  # (nome, id, cor)
MENU_DETAILS = ["ano · detalhe", "ano · detalhe"]  # coluna à direita de cada linha do terminal
HUD_ITEM = False
MENU_EXTENSIONS = False
TITLECARD_LOGO_REQUIRED = True
PIECES_REQUIRE_LOGO = True
GRAPH_SCALE = 1.5
ANIM_MAX = 0.35

SCENES = [
    Section(
        "abertura",
        0.0,
        "INTRODUÇÃO",
        "Tema da lista",
        "subtítulo",
        ["logo_win11_icone", "logo_apple", "logo_google"],
    ),
    ListItem(
        "item1",
        Phrase("Frase falada quando o item 1 começa"),
        1,
        sub="ano · resumo",
        logo="logo_x",
        pieces=[
            Stat("1995", "rótulo curto", "#66d9ef", at=("palavra", 100.0), logo="logo_x"),
        ],
    ),
    ListItem("item2", Phrase("Frase falada quando o item 2 começa"), 2, sub="ano · resumo", logo="logo_y", pieces=[]),
    Section("fim", Phrase("Frase de encerramento"), "OBRIGADO", "Like e inscreva-se", "até o próximo vídeo", []),
]

# (item, arquivo, in_s, out_s, velocidade 1.0–2.0, t_inicio_na_timeline_s) — o item começa com vídeo (t_start >= início + 3.9 s)
BROLL = []
BROLL_PREVIEW = True
