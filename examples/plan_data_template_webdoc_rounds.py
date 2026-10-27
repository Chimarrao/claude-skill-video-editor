"""Esqueleto do tipo "Webdoc com rounds" (comparativo A × B). Substitua pelos nomes/âncoras reais depois de transcrever o áudio.
Âncoras: at=("palavra falada", segundos aproximados) ou Phrase("frase"). Cada peça `center` substitui a anterior; deixe >= 2,5 s entre peças."""

from plan import Block, Side, Round, Duel, Verdict, Bars, Profile, ProfileRow, ScoreStrip, Stat, Graph, Item, BrollWindow, Empty

COVERAGE = (60, 100.5)
MAX_TITLES = 5
VIDEO_KIND = "webdoc_rounds"
TITLE_STYLE = "report"
MENU = []

# Lados do duelo: cor própria (A quente, B frio por padrão), logo real da biblioteca (find_image.py) e até 4 chips curtos.
A = Side("Cinnamon", "logo_cinnamon", "#ff7b3a", ["Moderno e polido", "Visual familiar", "Efeitos e animações"])
B = Side("XFCE", "logo_xfce_2", "#3fa3ff", ["Leve e direto", "Minimalista", "Modular"])

# Perfis do veredito (criados uma vez; ProfileRow reaproveita as mesmas cartas no resumo).
P1 = Profile(1, "O Iniciante ou Migrante", ["Quer interface bonita e familiar", "PC dos últimos anos"], "Cinnamon", "#ff7b3a", "logo_cinnamon", tag="Iniciante")
P2 = Profile(2, "O Herói das Máquinas Antigas", ["2 GB ou 4 GB de RAM", "Quer dar vida nova à máquina"], "XFCE", "#3fa3ff", "logo_xfce_2", tag="Máquina antiga")

SCENES = [
    # gancho (B-roll/animação conforme o roteiro) …
    Empty("gancho", 0.0),
    # Round: cartela → duelo com foco no lado que está sendo descrito → [B-roll do lado A / lado B] → selo de vencedor
    Block("r1", 60.0, [
        Round(1, "Visual", A, B, at=("Round", 61.0)),   # cartela enxuta: número + tema curto
        Duel(A, B, "A", at=("Cinnamon", 75.0)),   # foco: o painel não muda, só o conteúdo do outro lado esmaece
        Duel(A, B, "B", at=("XFCE", 120.0)),
        Verdict("ROUND 1 · VISUAL", "EMPATE", "#cfd3dc", "É puro gosto pessoal", at=("decisão", 165.0)),
    ]),
    Block("r2", 170.0, [
        Round(2, "Duelo do Desempenho", A, B, "Performance & Recursos", at=("Round", 171.0)),
        Bars("RAM em repouso", [("XFCE", 600, "~600 MB", "#3fa3ff", "logo_xfce_2"), ("Cinnamon", 950, "~900 MB – 1 GB", "#ff7b3a", "logo_cinnamon")], "MB (exemplo típico)", note="Varia com hardware e versão", at=("RAM", 185.0)),
        Verdict("ROUND 2 · DESEMPENHO", "XFCE VENCE", "#3fa3ff", "Menos RAM e CPU", "logo_xfce_2", at=("veredito", 230.0)),
    ]),
    Block("perfis", 900.0, [
        Profile(1, "O Iniciante ou Migrante", ["Quer interface bonita e familiar", "PC dos últimos anos"], "Cinnamon", "#ff7b3a", "logo_cinnamon", tag="Iniciante", at=("Perfil", 905.0)),
        ProfileRow([P1, P2], at=("resumindo", 1000.0)),
        ScoreStrip([("Visual", "EMPATE", "#cfd3dc"), ("Desempenho", "XFCE", "#3fa3ff")], at=("placar", 1010.0)),
    ]),
]
