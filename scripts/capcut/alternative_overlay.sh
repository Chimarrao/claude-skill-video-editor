#!/usr/bin/env bash
# Plano B se o CapCut NÃO preservar a transparência do ProRes 4444 (fundo preto no overlay).
# Uso: ./alternative_overlay.sh input.mov [qtrle|png|webm]   -> input_<formato>.(mov|webm), 1920x1080 com alpha
# Ordem de tentativa sugerida: qtrle (Apple Animation, alpha nativo no QuickTime) -> png (MOV PNG, maior) -> webm (VP9 alpha; CapCut Mac costuma ignorar o alpha).
set -e
input="$1"; fmt="${2:-qtrle}"; base="${input%.*}"
case "$fmt" in
  qtrle) ffmpeg -y -i "$input" -vf scale=1920:1080 -c:v qtrle -pix_fmt argb "${base}_qtrle.mov" ;;
  png)   ffmpeg -y -i "$input" -vf scale=1920:1080 -c:v png  -pix_fmt rgba "${base}_png.mov" ;;
  webm)  ffmpeg -y -i "$input" -vf scale=1920:1080 -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 12M "${base}.webm" ;;
esac
