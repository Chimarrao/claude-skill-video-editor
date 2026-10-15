"""ESQUELETO do tipo "Webdoc com B-roll" (ainda não é de um vídeo real: substituir pelo plan_data.py do 1º vídeo quando terminar).
Montado e testado sobre uma narração de teste (blocos B + Block/Tela de asset + ShortList + Tx + V)."""

from plan import (
    Anchor,
    Phrase,
    GraphScene,
    Item,
    Empty,
    BrollWindow,
    Block,
    ShortList,
    Center,
    Logo,
    FreeLogo,
    Stat,
    Facts,
    Graph,
    Comparison,
    Screenshot,
    Title,
    Impact,
    Section,
    Timeline,
)

VIDEO_KIND = "webdoc_broll"  # liga as regras do tipo: vídeo só em B/V, sem menu/HUD, rótulo leve, resumo/stat do webdoc
TITLE_STYLE = "report"  # tom sério
COVERAGE = (60, 100.5)  # B-roll conta como coberto; ~90% nos trechos de animação
MAX_TITLES = 5  # % máx.; nunca antes de 30 s (TITLE_MIN_START)
MENU = []  # não é lista
MAX_CLIPS_PER_ITEM = 6
BROLL_PREVIEW = True  # prévia no editor; False antes do render final

SCENES = [
    # 0. gancho/abertura SEM B-roll (título/gancho nos primeiros segundos)
    GraphScene(
        "gancho",
        0.0,
        [
            Item("ic:ballot", id="u", label="Equipamento", h=200, at=("equipamento", 2.0)),
            Item("ic:shield-check", parent="u", label="Segurança", h=160, at=("segurança", 5.0)),
        ],
        dir="LR",
    ),
    # 1. TRECHO DE B-ROLL: vídeo da pasta Assets/ + rótulo leve no canto inferior ESQUERDO (≤ 6 s) ou nada
    BrollWindow("b_equip", Phrase("frase falada que abre o trecho"), label="Tema técnico", data="2009", logo=None),
    # 2. TRECHO DE ANIMAÇÃO: bloco sem menu; imagem da pasta como Tela (nunca esticada; legenda curta)
    Block(
        "an_fluxo",
        Phrase("frase do conceito abstrato"),
        [
            Center(
                Screenshot("asset:foto_da_pasta.jpg", "Legenda curta (<= 60)", width=900, at=("palavra", 60.0))
            ),
        ],
    ),
    # 3. LISTA CURTA no meio do vídeo (2–10 itens; entra um a um na fala; tema escuro do webdoc)
    ShortList(
        "lc_camadas",
        Phrase("frase que anuncia a lista"),
        "As 4 camadas de segurança",
        [
            ("ic:lock", "Assinatura digital", "assinatura"),
            ("ic:fingerprint", "Biometria", "biometria"),
            ("ic:file-certificate", "Boletim", "boletim"),
            ("ic:shield-check", "Auditoria", "auditoria"),
        ],
    ),
    Impact("t_impacto", Phrase("frase marcante depois de 30 s"), ["UMA FRASE", "DE *IMPACTO*"]),
    # 4. B-roll sem rótulo (só vídeo) e trecho que fica SÓ com preenchimento para o usuário completar
    BrollWindow("b_cerimonia", Phrase("frase da cerimônia")),
    Empty("sem_recurso", Phrase("frase sem B-roll nem animação")),
]

# BROLL = [(id_da_janela_B_ou_V, "../Assets/arquivo.mp4", in_s, out_s, velocidade 1.0–2.0, t_inicio_na_timeline), ...]
# Regras: clipe só dentro de B/V; >= 3 s; mudo (1.0x se tiver fala importante); trechos bons e corridos > picotados.
BROLL = [
    # ("b_equip", "../Assets/video.mp4", 12.0, 40.0, 2.0, 70.0),
]
