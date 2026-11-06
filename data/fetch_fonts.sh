#!/bin/sh
# Fonts for the app, at pinned commits (SIL OFL 1.1), into data/raw/fonts (not committed).
# build_app.py embeds only the glyphs the app needs; without these files the app still builds
# (characters Iansui lacks then fall back to Noto Sans TC). Same fonts and method as sy-zy.
#   Iansui 芫荽 — the Hàn-jī font of Tsheh-tû; used here only to know which characters it has.
#   LXGW WenKai TC 霞鶩文楷 TC — the same handwriting design (both are made from Klee One), traditional with Hong Kong
#   characters: it supplies the glyphs Iansui lacks (哋, 咗, 嘢, 冚…), so every character looks like Tsheh-tû's.
set -e
cd "$(dirname "$0")"
mkdir -p raw/fonts
fetch() { # name url commit path-in-repo
  out="raw/fonts/$(basename "$4")"
  [ -f "$out" ] && { echo "ok  $1 (cached)"; return; }
  tmp="raw/fonts/.$1"
  rm -rf "$tmp"
  git clone --quiet --no-checkout --filter=blob:none --depth 1 "$2" "$tmp" 2>/dev/null || git clone --quiet --no-checkout --filter=blob:none "$2" "$tmp"
  git -C "$tmp" fetch --quiet --depth 1 --filter=blob:none origin "$3"
  git -C "$tmp" sparse-checkout set --no-cone "/$4"
  git -C "$tmp" -c advice.detachedHead=false checkout --quiet "$3"
  mv "$tmp/$4" "$out" && rm -rf "$tmp"
  echo "ok  $1 @ $(echo "$3" | cut -c1-7)"
}
fetch iansui     https://github.com/ButTaiwan/iansui.git   9d9a8e68bf1e138dd91e562eeff28d95bca33196 fonts/ttf/Iansui-Regular.ttf
fetch lxgwwenkaitc https://github.com/lxgw/LxgwWenkaiTC.git 63f8decf15c684ebc389174c5c4cc381bc4daf9e fonts/TTF/LXGWWenKaiTC-Regular.ttf
