#!/usr/bin/env bash
# Verifica (e opcionalmente instala) tudo o que a skill precisa. Uso:
#   scripts/check_install.sh            # só checa e mostra o que falta
#   scripts/check_install.sh --install # checa e instala o que faltar (Homebrew/uv/npm/pip); pede confirmação
#   scripts/check_install.sh --project  # também prepara o venv do projeto atual (pasta animacao/): faster-whisper, alinhador, opencv, CLIP
# Saída: ✅ ok · ❌ faltando (e o comando de instalação). Código de saída 1 se faltar algo obrigatório.
set -u
INSTALL=0; PROJECT=0; for arg in "$@"; do [ "$arg" = "--install" ] && INSTALL=1; [ "$arg" = "--project" ] && PROJECT=1; done
MISSING=0; OPTIONAL_MISSING=0
ok(){ printf "  ✅ %-22s %s\n" "$1" "$2"; }
nok(){ printf "  ❌ %-22s %s\n" "$1" "$2"; }
has_cmd(){ command -v "$1" >/dev/null 2>&1; }
ask(){ [ "$INSTALL" = 1 ] || return 1; read -r -p "     instalar '$1'? [s/N] " r; [ "$r" = "s" ] || [ "$r" = "S" ]; }
require(){ # nome comando instalador obrigatoria
  if has_cmd "$2"; then ok "$1" "$($2 --version 2>&1 | head -1 | cut -c1-60)"; return; fi
  nok "$1" "instalar: $3"; [ "$4" = 1 ] && MISSING=1 || OPTIONAL_MISSING=1
  if ask "$1"; then eval "$3" && ok "$1" "instalado"; fi
}
echo "== Sistema"; [ "$(uname)" = "Darwin" ] && ok "macOS" "$(sw_vers -productVersion)" || nok "macOS" "desenvolvido/testado no macOS (CapCut para Mac)"
echo "== Gerenciadores"
require "Homebrew" brew '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"' 0
require "uv (Python)" uv "brew install uv" 1
echo "== Ferramentas obrigatórias"
require "Node 18+" node "brew install node" 1
require "npm" npm "brew install node" 1
require "ffmpeg" ffmpeg "brew install ffmpeg" 1
require "ffprobe" ffprobe "brew install ffmpeg" 1
require "Python 3" python3 "brew install python" 1
echo "== Navegador (render/capturas headless)"
if [ -d "/Applications/Google Chrome.app" ]; then ok "Google Chrome" "/Applications/Google Chrome.app"; else nok "Google Chrome" "instalar: brew install --cask google-chrome"; MISSING=1; ask "Google Chrome" && brew install --cask google-chrome; fi
echo "== Opcionais"
require "tesseract (OCR)" tesseract "brew install tesseract tesseract-lang" 0
require "yt-dlp" yt-dlp "brew install yt-dlp" 0
if [ -d "/Applications/CapCut.app" ]; then ok "CapCut" "/Applications/CapCut.app"; else nok "CapCut" "opcional: https://www.capcut.com (gera/edita drafts)"; OPTIONAL_MISSING=1; fi
if has_cmd sqlite3; then ok "sqlite3" "$(sqlite3 --version | cut -d' ' -f1)"; else nok "sqlite3" "brew install sqlite"; OPTIONAL_MISSING=1; fi
echo "== Banco de assets"
cd "$(dirname "$0")/.." || exit 1
if [ -f database/assets.db ]; then ok "database/assets.db" "$(sqlite3 database/assets.db 'select count(*) from assets' 2>/dev/null) assets"; elif [ -f database/assets.publico.db ]; then nok "database/assets.db" "cp database/assets.publico.db database/assets.db"; if ask "copiar banco público"; then cp database/assets.publico.db database/assets.db && ok "database/assets.db" "criado"; fi; fi
if [ "$PROJECT" = 1 ]; then
  echo "== Projeto atual ($(pwd -P | sed 's/.*\///' ) → use dentro de animacao/)"; cd "$OLDPWD" 2>/dev/null || true
  [ -f package.json ] || { nok "package.json" "rode dentro da pasta animacao/ do projeto"; exit 1; }
  [ -d node_modules ] && ok "node_modules" "ok" || { nok "node_modules" "npm install"; ask "npm install" && npm install --no-audit --no-fund && npm run postinstall; }
  [ -x venv/bin/python ] && ok "venv (whisper)" "ok" || { nok "venv" "uv venv --python 3.12 venv && uv pip install --python venv/bin/python faster-whisper pillow onnxruntime 'opencv-python-headless<4.11'"; ask "venv + faster-whisper" && uv venv --python 3.12 venv && uv pip install --python venv/bin/python faster-whisper pillow onnxruntime "opencv-python-headless<4.11"; }
  [ -x venv_align/bin/python ] && ok "venv_align" "ok" || { nok "venv_align" "uv venv --python 3.12 venv_align && uv pip install --python venv_align/bin/python torch torchaudio soundfile 'numpy<2' 'transformers<4.50' pillow 'opencv-python-headless<4.11'"; ask "venv_align (alinhador + CLIP)" && uv venv --python 3.12 venv_align && uv pip install --python venv_align/bin/python torch torchaudio soundfile "numpy<2" "transformers<4.50" pillow "opencv-python-headless<4.11"; }
  [ -d /tmp/pp/node_modules/puppeteer-core ] && ok "puppeteer-core" "/tmp/pp" || { nok "puppeteer-core" "mkdir -p /tmp/pp && cd /tmp/pp && npm i puppeteer-core"; ask "puppeteer-core" && (mkdir -p /tmp/pp && cd /tmp/pp && npm i puppeteer-core); }
fi
echo; [ "$MISSING" = 0 ] && echo "Tudo o que é obrigatório está instalado." || echo "Faltam itens obrigatórios (veja ❌). Rode com --install."
[ "$OPTIONAL_MISSING" = 1 ] && echo "(itens opcionais ausentes não impedem o uso básico.)"
exit $MISSING
