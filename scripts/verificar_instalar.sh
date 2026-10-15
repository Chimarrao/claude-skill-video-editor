#!/usr/bin/env bash
# Verifica (e opcionalmente instala) tudo o que a skill precisa. Uso:
#   scripts/verificar_instalar.sh            # só checa e mostra o que falta
#   scripts/verificar_instalar.sh --instalar # checa e instala o que faltar (Homebrew/uv/npm/pip); pede confirmação
#   scripts/verificar_instalar.sh --projeto  # também prepara o venv do projeto atual (pasta animacao/): faster-whisper, alinhador, opencv, CLIP
# Saída: ✅ ok · ❌ faltando (e o comando de instalação). Código de saída 1 se faltar algo obrigatório.
set -u
INSTALAR=0; PROJETO=0; for a in "$@"; do [ "$a" = "--instalar" ] && INSTALAR=1; [ "$a" = "--projeto" ] && PROJETO=1; done
FALTA=0; OPC=0
ok(){ printf "  ✅ %-22s %s\n" "$1" "$2"; }
nok(){ printf "  ❌ %-22s %s\n" "$1" "$2"; }
tem(){ command -v "$1" >/dev/null 2>&1; }
pergunta(){ [ "$INSTALAR" = 1 ] || return 1; read -r -p "     instalar '$1'? [s/N] " r; [ "$r" = "s" ] || [ "$r" = "S" ]; }
req(){ # nome comando instalador obrigatoria
  if tem "$2"; then ok "$1" "$($2 --version 2>&1 | head -1 | cut -c1-60)"; return; fi
  nok "$1" "instalar: $3"; [ "$4" = 1 ] && FALTA=1 || OPC=1
  if pergunta "$1"; then eval "$3" && ok "$1" "instalado"; fi
}
echo "== Sistema"; [ "$(uname)" = "Darwin" ] && ok "macOS" "$(sw_vers -productVersion)" || nok "macOS" "desenvolvido/testado no macOS (CapCut para Mac)"
echo "== Gerenciadores"
req "Homebrew" brew '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"' 0
req "uv (Python)" uv "brew install uv" 1
echo "== Ferramentas obrigatórias"
req "Node 18+" node "brew install node" 1
req "npm" npm "brew install node" 1
req "ffmpeg" ffmpeg "brew install ffmpeg" 1
req "ffprobe" ffprobe "brew install ffmpeg" 1
req "Python 3" python3 "brew install python" 1
echo "== Navegador (render/capturas headless)"
if [ -d "/Applications/Google Chrome.app" ]; then ok "Google Chrome" "/Applications/Google Chrome.app"; else nok "Google Chrome" "instalar: brew install --cask google-chrome"; FALTA=1; pergunta "Google Chrome" && brew install --cask google-chrome; fi
echo "== Opcionais"
req "tesseract (OCR)" tesseract "brew install tesseract tesseract-lang" 0
req "yt-dlp" yt-dlp "brew install yt-dlp" 0
if [ -d "/Applications/CapCut.app" ]; then ok "CapCut" "/Applications/CapCut.app"; else nok "CapCut" "opcional: https://www.capcut.com (gera/edita drafts)"; OPC=1; fi
if tem sqlite3; then ok "sqlite3" "$(sqlite3 --version | cut -d' ' -f1)"; else nok "sqlite3" "brew install sqlite"; OPC=1; fi
echo "== Banco de assets"
cd "$(dirname "$0")/.." || exit 1
if [ -f banco/assets.db ]; then ok "banco/assets.db" "$(sqlite3 banco/assets.db 'select count(*) from assets' 2>/dev/null) assets"; elif [ -f banco/assets.publico.db ]; then nok "banco/assets.db" "cp banco/assets.publico.db banco/assets.db"; if pergunta "copiar banco público"; then cp banco/assets.publico.db banco/assets.db && ok "banco/assets.db" "criado"; fi; fi
if [ "$PROJETO" = 1 ]; then
  echo "== Projeto atual ($(pwd -P | sed 's/.*\///' ) → use dentro de animacao/)"; cd "$OLDPWD" 2>/dev/null || true
  [ -f package.json ] || { nok "package.json" "rode dentro da pasta animacao/ do projeto"; exit 1; }
  [ -d node_modules ] && ok "node_modules" "ok" || { nok "node_modules" "npm install"; pergunta "npm install" && npm install --no-audit --no-fund && npm run postinstall; }
  [ -x venv/bin/python ] && ok "venv (whisper)" "ok" || { nok "venv" "uv venv --python 3.12 venv && uv pip install --python venv/bin/python faster-whisper pillow onnxruntime 'opencv-python-headless<4.11'"; pergunta "venv + faster-whisper" && uv venv --python 3.12 venv && uv pip install --python venv/bin/python faster-whisper pillow onnxruntime "opencv-python-headless<4.11"; }
  [ -x venv_align/bin/python ] && ok "venv_align" "ok" || { nok "venv_align" "uv venv --python 3.12 venv_align && uv pip install --python venv_align/bin/python torch torchaudio soundfile 'numpy<2' 'transformers<4.50' pillow 'opencv-python-headless<4.11'"; pergunta "venv_align (alinhador + CLIP)" && uv venv --python 3.12 venv_align && uv pip install --python venv_align/bin/python torch torchaudio soundfile "numpy<2" "transformers<4.50" pillow "opencv-python-headless<4.11"; }
  [ -d /tmp/pp/node_modules/puppeteer-core ] && ok "puppeteer-core" "/tmp/pp" || { nok "puppeteer-core" "mkdir -p /tmp/pp && cd /tmp/pp && npm i puppeteer-core"; pergunta "puppeteer-core" && (mkdir -p /tmp/pp && cd /tmp/pp && npm i puppeteer-core); }
fi
echo; [ "$FALTA" = 0 ] && echo "Tudo o que é obrigatório está instalado." || echo "Faltam itens obrigatórios (veja ❌). Rode com --instalar."
[ "$OPC" = 1 ] && echo "(itens opcionais ausentes não impedem o uso básico.)"
exit $FALTA
