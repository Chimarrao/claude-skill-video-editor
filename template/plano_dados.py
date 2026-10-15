from plano import A, F, G, I, Tx, V, L, Logo, Pessoas, Codigo, Stat, Fatos, Grafo, Titulo, Secao, Tempo

# Preencha CENAS (contíguas; primeira entrada 0.0). Veja exemplo/plano_dados_modelo_lista_com_broll.py (tipo lista) e
# exemplo/plano_dados_modelo_webdoc_com_broll.py (tipo webdoc). Âncoras: A(seg,'palavra') ou F('frase falada') (robusta a cortes).
COBERTURA = (88, 92)  # webdoc padrão 90%; lista/outros conforme o usuário responder
TITULOS_MAX = 5  # % máx. de títulos de impacto
ESTILO_TITULO = "monokai"  # 'monokai' (programação) | 'reportagem' (webdoc sério)
MENU = []  # [(nome, arquivo, cor)] — só tipo lista
CENAS = []

# ---- Lista COM B-roll: padrões definitivos (ver SKILL.md → "REGRAS DEFINITIVAS") ----
# HUD_ITEM = False             # contador NN/10 removido em todos os tipos (o avatar do canal fica no canto inferior direito)
# MENU_EXTENSOES = False       # extensões (.img/.py) só quando a lista é de ARQUIVOS
# CARTELA_LOGO_OBRIGATORIA = True   # L(..., logo="logo_x") em todo item
# PECAS_EXIGEM_LOGO = True     # Stat/Fatos ganham LogoSolto à esquerda (logo= da peça ou do item)
# ESCALA_GRAFO = 1.5           # grafo ampliado/recentralizado automaticamente (aviso se < 1.2x)
# ANIM_MAX = 0.35              # teto de animação+vazio nos itens (meta real ~0.15)
# LEAD_CLIPE = 0.4; FOLGA_CLIPE = 0.15   # peças somem 0.4 s antes do clipe e entram 0.15 s depois
# MAX_CLIPES_ITEM = 5
# BROLL = [(item, arquivo, in, out, vel 1.0-2.0, t_inicio_timeline), ...]   # item começa com vídeo (t_inicio >= início + 3.9 s)
# Exemplo de item: L("haiku", F("..."), 2, logo="logo_haiku_icon", sub="...", pecas=[
#     Grafo([I("ic:building", id="p", rotulo="Palm compra a Be", h=140, em=("Palm", 149.8)), ...], em=("Palm", 149.8)),
#     Stat("25 anos", "de projeto rodando", em=("anos", 194.2)),            # LogoSolto automático à esquerda
#     Fatos([("ic:puzzle", "Linux: peças de vários projetos")], em=("Linux", 239.5), logo="logo_tux")])

# ---- Webdoc COM B-roll (ver SKILL.md → "TIPO: Webdoc com B-roll"; esqueleto em exemplo/plano_dados_modelo_webdoc_com_broll.py) ----
# TIPO_VIDEO = "webdoc_broll"; ESTILO_TITULO = "reportagem"; COBERTURA = (60, 100.5); MENU = []
# CENAS: G(...) / Bloco(id, F("..."), [peças]) / B(id, F("..."), rotulo=, data=, logo=) / ListaCurta(id, F("..."), "Título", [("ic:x","rótulo","palavra")]) / Tx / V
# BROLL = [(id_da_janela_B_ou_V, "../Assets/arquivo.mp4", in, out, vel 1.0-2.0, t_inicio)]    # vídeo só em B/V
# Tela("asset:foto.jpg", "legenda curta") usa imagem da pasta Assets/ (nunca esticada).
