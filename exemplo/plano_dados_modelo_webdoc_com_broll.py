"""ESQUELETO do tipo "Webdoc com B-roll" (ainda não é de um vídeo real: substituir pelo plano_dados.py do 1º vídeo quando terminar).
Montado e testado sobre uma narração de teste (blocos B + Bloco/Tela de asset + ListaCurta + Tx + V)."""

from plano import (
    A,
    F,
    G,
    I,
    V,
    B,
    Bloco,
    ListaCurta,
    Centro,
    Logo,
    LogoSolto,
    Stat,
    Fatos,
    Grafo,
    Comparativo,
    Tela,
    Titulo,
    Tx,
    Secao,
    Tempo,
)

TIPO_VIDEO = "webdoc_broll"  # liga as regras do tipo: vídeo só em B/V, sem menu/HUD, rótulo leve, resumo/stat do webdoc
ESTILO_TITULO = "reportagem"  # tom sério
COBERTURA = (60, 100.5)  # B-roll conta como coberto; ~90% nos trechos de animação
TITULOS_MAX = 5  # % máx.; nunca antes de 30 s (TITULO_MIN_INICIO)
MENU = []  # não é lista
MAX_CLIPES_ITEM = 6
PREVIA_BROLL = True  # prévia no editor; False antes do render final

CENAS = [
    # 0. gancho/abertura SEM B-roll (título/gancho nos primeiros segundos)
    G(
        "gancho",
        0.0,
        [
            I("ic:ballot", id="u", rotulo="Equipamento", h=200, em=("equipamento", 2.0)),
            I("ic:shield-check", pai="u", rotulo="Segurança", h=160, em=("segurança", 5.0)),
        ],
        dir="LR",
    ),
    # 1. TRECHO DE B-ROLL: vídeo da pasta Assets/ + rótulo leve no canto inferior ESQUERDO (≤ 6 s) ou nada
    B("b_equip", F("frase falada que abre o trecho"), rotulo="Tema técnico", data="2009", logo=None),
    # 2. TRECHO DE ANIMAÇÃO: bloco sem menu; imagem da pasta como Tela (nunca esticada; legenda curta)
    Bloco(
        "an_fluxo",
        F("frase do conceito abstrato"),
        [
            Centro(
                Tela("asset:foto_da_pasta.jpg", "Legenda curta (<= 60)", largura=900, em=("palavra", 60.0))
            ),
        ],
    ),
    # 3. LISTA CURTA no meio do vídeo (2–10 itens; entra um a um na fala; tema escuro do webdoc)
    ListaCurta(
        "lc_camadas",
        F("frase que anuncia a lista"),
        "As 4 camadas de segurança",
        [
            ("ic:lock", "Assinatura digital", "assinatura"),
            ("ic:fingerprint", "Biometria", "biometria"),
            ("ic:file-certificate", "Boletim", "boletim"),
            ("ic:shield-check", "Auditoria", "auditoria"),
        ],
    ),
    Tx("t_impacto", F("frase marcante depois de 30 s"), ["UMA FRASE", "DE *IMPACTO*"]),
    # 4. B-roll sem rótulo (só vídeo) e trecho que fica SÓ com preenchimento para o usuário completar
    B("b_cerimonia", F("frase da cerimônia")),
    V("sem_recurso", F("frase sem B-roll nem animação")),
]

# BROLL = [(id_da_janela_B_ou_V, "../Assets/arquivo.mp4", in_s, out_s, velocidade 1.0–2.0, t_inicio_na_timeline), ...]
# Regras: clipe só dentro de B/V; >= 3 s; mudo (1.0x se tiver fala importante); trechos bons e corridos > picotados.
BROLL = [
    # ("b_equip", "../Assets/video.mp4", 12.0, 40.0, 2.0, 70.0),
]
