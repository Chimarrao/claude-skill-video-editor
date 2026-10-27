# animacao-narracao — skill de edição de vídeo para o Claude Code

Uma **skill de edição de vídeo completa**: a partir de uma narração (`.wav`) e de uma pasta com vídeos/imagens de apoio, ela **transcreve, planeja, anima, escolhe o B-roll, renderiza o overlay e monta o projeto no CapCut** — tudo sincronizado com a fala e validado por testes automáticos.

> As regras, os padrões visuais e os aprendizados estão em **`SKILL.md`** (é o arquivo que o Claude Code carrega). Este README explica o que a skill faz e como instalar.

## O que ela faz (pipeline)

| Etapa | O que acontece | Onde |
|---|---|---|
| 1. Transcrição | `faster-whisper` (large-v3) com vocabulário do tema + **alinhamento forçado** palavra a palavra (wav2vec2, ~30 ms) | `template/transcribe.py`, `template/align.py` |
| 2. Plano | Você (ou o Claude) escreve `plan_data.py`; o motor resolve âncoras por frase falada, valida proporção, sobreposição, zonas proibidas e sincronia | `template/plan.py` |
| 3. Animações | Motion Canvas (TypeScript): grafos/árvores, logos, fotos, estatísticas, comparativos, linhas do tempo, listas curtas, menus de lista (explorador ou terminal `ls`) | `template/src/` |
| 4. B-roll | Análise de vídeos (cortes, movimento, OCR, CLIP, rostos), folhas de contato, escolha de trechos limpos, proxies de prévia | `scripts/broll/` |
| 5. Render | Overlay `.mov` ProRes 4444 com transparência (1080p ou 4K), com barra de progresso | `scripts/render.mjs`, `scripts/render_slices.sh` (em trechos, resiste a queda do Chrome), `scripts/progress.py` |
| 6. Montagem | Projeto novo no CapCut: preenchimento → B-roll (com buracos) → overlay recortado → narração (+ música, avatar, vinhetas via pacote de marca privado) | `scripts/capcut/` |
| 7. Testes | Regras estáticas, "teste dos testes" (mutações), overlay alpha por render de fatia, rótulos × fala, clipes sem pessoas, montagem do CapCut | `scripts/tests/` |
| 7b. Controle de qualidade | **Quality gates**: plano (ritmo, setas, imagens, janelas vazias), frames reais do render compostos sobre o B-roll com folhas de contato, folhas dos clipes, testes do motor | `scripts/quality/`, `scripts/tests/test_engine_geometry.py` |
| 7c. Biblioteca de imagens | Colheita da Wikipédia/Commons de **431 assuntos** (versões do Windows/Mac/Android, distros Linux, BSD, apps, empresas, pessoas, hardware) com várias proporções por assunto, catálogo com fonte/licença e busca | `scripts/images/`, `database/image_catalog.json` |
| 7e. Tipo Webdoc com rounds | Comparativo A × B em estilo ringue/versus: cartela de round, duelo com foco, selo de vencedor, barras de dados, cartas de perfil + resumo, placar final | `template/src/lib/rounds.tsx`, `scripts/tests/test_rounds.py`, `examples/plan_data_template_webdoc_rounds.py` |
| 7d. Tipo NEWS (só cortes) | "faça o news NN": funde o áudio tratado no vídeo bruto (GCC-PHAT, loudnorm), transcreve, decide os cortes (regravação, falso começo, comando, explicação refeita, pausas, início/fim) com revisão do agente, gera projeto CapCut de UMA trilha, prévia `PRONTO_auto.mp4` e `cortes.md`; validação de sincronia/corte limpo/repetido/perdido/tela; calibração contra cortes reais | `scripts/news/`, `scripts/tests/test_news.py` |
| 8. Memória | Banco SQLite de logos/ícones/variações de lista; transcrições e vídeos ficam só no banco local | `database/`, `scripts/assets_db.py` |

Tipos de vídeo suportados: **Lista sem B-roll · Webdoc sem B-roll · Lista de argumentos sem B-roll · Lista com B-roll · Webdoc com B-roll**, mais um catálogo de **14 estilos de lista** (pódio, terminal `ls`, metrô, tier list…).

## Instalar

```bash
# 1) copie a pasta para o diretório de skills do Claude Code
mkdir -p ~/.claude/skills && cp -R animacao-narracao ~/.claude/skills/
cd ~/.claude/skills/animacao-narracao

# 2) confira e instale os requisitos (macOS + Homebrew)
scripts/check_install.sh              # só verifica (✅/❌)
scripts/check_install.sh --install   # instala o que faltar, perguntando antes
scripts/check_install.sh --project    # (dentro de animacao/) prepara venvs, node_modules e puppeteer do projeto

# 3) banco de assets (logos/ícones/variações, sem dados pessoais)
cp database/assets.publico.db database/assets.db
```

Depois, no Claude Code, peça: *"crie as animações e o projeto do CapCut para este áudio"* — a skill pergunta o tipo de vídeo e segue o fluxo de ponta a ponta.

## Requisitos

- **Node 18+** (Motion Canvas 3.17, Vite 4), **Python 3.12** via `uv`, **ffmpeg/ffprobe**, **Google Chrome** (render e capturas por puppeteer).
- Transcrição: `faster-whisper` (large-v3) + alinhador forçado `wav2vec2` (venv separado `venv_align`, torch 2.2, numpy<2).
- Análise de B-roll: `tesseract` (OCR), `opencv-python-headless<4.11`, CLIP (via `transformers`).
- Opcional: **CapCut para Mac** (o gerador escreve o draft em `~/Movies/CapCut/User Data/Projects/com.lveditor.draft`), `yt-dlp` para baixar B-roll da internet.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `SKILL.md` | instruções e regras da skill |
| `template/` | projeto Motion Canvas base + `plan.py` (motor de plano/sincronia) |
| `scripts/` | transcrição, B-roll, CapCut, testes, banco (`assets_db.py`), requisitos (`check_install.sh`), publicação (`publish.sh`) |
| `examples/` | modelos de `plan_data.py` e código das 14 variações de lista |
| `assets/` | logos e fundos de preenchimento (o de 20 min **não** vai para o repositório) |
| `database/` | `assets.publico.db` (SQLite só com referências) + `public_images/` (arquivos das logos/miniaturas públicas) e `image_catalog.json` (fonte, licença e proporção de cada imagem colhida) |
| `library/` | **ignorada pelo git**: imagens colhidas (recriáveis com `scripts/images/harvest_images.py`) |
| `references/` | aprendizados de edições reais |
| `private/` | **ignorado pelo git**: pacote de marca do CapCut, assets de vídeos específicos |

## Pacote de marca (privado)
Música de fundo, avatar no canto, propaganda e vinheta final entram no CapCut a partir de um pacote extraído de um projeto seu (`scripts/capcut/extract_brand_pack.py`), guardado em `private/` e **nunca versionado**. Veja `SKILL.md`.

## Fundo de preenchimento de 20 min
`assets/background_filler_20min.mp4` (1,1 GB) não está no repositório. Sem ele o gerador usa `background_filler.mp4` (20 s) em cópias sequenciais. Para gerar o seu: repita um vídeo curto até 20 min com `ffmpeg -stream_loop`.

## Testes
```bash
python scripts/tests/test_list_broll_rules.py    # regras da Lista com B-roll
python scripts/tests/test_webdoc_broll_rules.py   # regras do Webdoc com B-roll
python scripts/tests/test_mutations.py              # teste dos testes (injeta defeitos)
python scripts/tests/test_capcut_overlay.py        # monta o draft em pasta temporária
python scripts/tests/test_overlay_alpha.py         # render de uma fatia e checagem do alfa
python scripts/tests/test_labels_vs_speech.py       # rótulos das animações × fala
python scripts/tests/test_clips_without_people.py    # clips de B-roll sem rostos
python scripts/tests/test_engine_geometry.py         # motor: ritmo, setas retas, fileira, último item, rótulos, ponta da seta (sem projeto)
python scripts/tests/test_gate_plan.py               # gate 1: P8 (clipe repetido/sobreposto) numa cópia do projeto
python scripts/tests/test_harvest_catalog.py         # colheita de imagens: merge nunca apaga arquivo catalogado
python scripts/tests/test_rounds.py                  # tipo Webdoc com rounds: DSL e peças
python scripts/tests/test_news.py                    # tipo NEWS: regras de corte com transcrição sintética (sem vídeo/rede)
scripts/quality/run_gates.sh [--frames]               # todos os gates em sequência (em animacao/)
```
(rodar dentro de `animacao/`, a pasta do projeto gerado)

## Observações
- Logos e fotos de terceiros pertencem aos respectivos donos; use conforme a licença/uso justo do seu canal.
- `scripts/publish.sh "mensagem"` faz commit + push e regenera o banco público sem dados pessoais.
