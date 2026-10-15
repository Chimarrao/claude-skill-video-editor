"""MODELO — Lista com B-roll (menu em estilo terminal `ls`). Copie para animacao/plano_dados.py e preencha.
Âncoras F("frase falada") sobrevivem a cortes no áudio. Peças: Stat/Fatos sempre com logo do assunto; Grafo ≥ 1 logo real; sem código.
"""

from plano import A, F, G, I, V, L, Secao, Bloco, Stat, Fatos, Grafo

OVERLAY_MINIMO = False
COBERTURA = (0, 100.5)
TITULO_MENU = "itens"  # vira `~/itens` no terminal
MENU_ESTILO = "terminal"  # "terminal" (lista ls) ou "explorador"
MENU = [("Item Um", "item-um", "#66d9ef"), ("Item Dois", "item-dois", "#a6e22e")]  # (nome, id, cor)
MENU_DETALHES = ["ano · detalhe", "ano · detalhe"]  # coluna à direita de cada linha do terminal
HUD_ITEM = False
MENU_EXTENSOES = False
CARTELA_LOGO_OBRIGATORIA = True
PECAS_EXIGEM_LOGO = True
ESCALA_GRAFO = 1.5
ANIM_MAX = 0.35

CENAS = [
    Secao(
        "abertura",
        0.0,
        "INTRODUÇÃO",
        "Tema da lista",
        "subtítulo",
        ["logo_win11_icone", "logo_apple", "logo_google"],
    ),
    L(
        "item1",
        F("Frase falada quando o item 1 começa"),
        1,
        sub="ano · resumo",
        logo="logo_x",
        pecas=[
            Stat("1995", "rótulo curto", "#66d9ef", em=("palavra", 100.0), logo="logo_x"),
        ],
    ),
    L("item2", F("Frase falada quando o item 2 começa"), 2, sub="ano · resumo", logo="logo_y", pecas=[]),
    Secao("fim", F("Frase de encerramento"), "OBRIGADO", "Like e inscreva-se", "até o próximo vídeo", []),
]

# (item, arquivo, in_s, out_s, velocidade 1.0–2.0, t_inicio_na_timeline_s) — o item começa com vídeo (t_inicio >= início + 3.9 s)
BROLL = []
PREVIA_BROLL = True
