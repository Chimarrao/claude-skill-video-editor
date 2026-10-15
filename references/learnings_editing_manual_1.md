# O que o editor fez à mão no CapCut depois da 1ª geração automática (Lista com B-roll) — e o que a skill aprendeu

Fonte: leitura SEM edição do `draft_info.json` do projeto editado (`scripts/capcut/analyze_user_edits.py`) + comentários do editor.

## Comentários do editor → regra implementada
| Comentário | Regra |
|---|---|
| Cartela do item sem imagem ("tem que ter a logo do sistema") | `ListItem(..., logo=)`; `TITLECARD_LOGO_REQUIRED` |
| Trecho sem sentido, sem animação | Stat/Fatos sempre com logo do assunto; se não faz sentido, remove-se e estende-se o B-roll |
| Animação pequena demais (ele dava zoom 1,4–1,7×) | grafo ampliado automaticamente (`GRAPH_SCALE`), recentralizado; aviso < 1,2× |
| Animação aparece por milésimos junto do B-roll | peças somem 0,4 s antes do clipe e voltam 0,15 s depois; overlay recortado no CapCut |
| Contador NN/N "horrível" | `HUD_ITEM = False` em todos os tipos |
| Elementos sob o avatar do canal | zona do avatar reservada (canto inferior direito, 240×240) |
| Extensões sem sentido no menu | `MENU_EXTENSIONS = False` (só lista de arquivos) |

## Decisões dele na timeline
- Inseriu vinheta própria depois da abertura, vinheta final, música de fundo, avatar sobre o vídeo todo.
- Cortou o overlay em ~22 pedaços e esticou o B-roll (1,3–1,9×) onde removeu animações.
- Manteve animações **informativas, grandes e com imagem real**; removeu texto solto sem imagem, ícone genérico pequeno, árvore pequena, pessoa sem foto.
- Colocou logos transparentes à esquerda (~250 px, sem cartão) em janelas com Stat/Fatos.
- Trocou ~40% do B-roll escolhido: preferiu tela do sistema rodando (2×), trechos longos e corridos; descartou câmera filmando monitor, foto de hardware com anotações, site cheio de texto, teclado/mascote.
- Placeholders "B-ROLL MANUAL" funcionaram: baixou vídeo próprio e usou um clipe contínuo longo.
