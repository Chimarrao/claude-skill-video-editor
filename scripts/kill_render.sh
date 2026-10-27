#!/usr/bin/env bash
# mata o que sobrou de render/vite/chrome headless (os padrões ficam neste arquivo, não na linha de comando que o chama)
pkill -9 -f "render_slice[s]"
pkill -9 -f "render_on[e]"
pkill -9 -f "render_db[g]"
pkill -9 -f "Google Chrom[e].*headless"
pkill -9 -f "ffmpeg-installe[r]"
pkill -f "bin/vi[t]e"
pkill -f "npm star[t]"
sleep 3
echo "restantes: $(pgrep -f 'render_on[e]|render_slice[s]|bin/vi[t]e' | wc -l)"
