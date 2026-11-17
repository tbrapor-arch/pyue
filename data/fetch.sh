#!/bin/sh
# Download the open data sources into data/raw at pinned versions.
# Nothing in data/raw is committed to this repo (see .gitignore and ATTRIBUTION.md).
set -e
cd "$(dirname "$0")"
mkdir -p raw
fetch() { # name url commit
  if [ ! -d "raw/$1/.git" ]; then
    git clone --quiet --filter=blob:none "$2" "raw/$1"
  fi
  git -C "raw/$1" fetch --quiet --depth 1 origin "$3" 2>/dev/null || true
  git -C "raw/$1" -c advice.detachedHead=false checkout --quiet "$3"
  echo "ok  $1 @ $(git -C "raw/$1" rev-parse --short HEAD)"
}
# rime-cantonese (CC BY 4.0): words, character readings with their share, word frequencies (essay-cantonese.txt)
fetch rime-cantonese https://github.com/rime/rime-cantonese.git 259f0e48bba840c3a2e0d117539e96937f3d89bc

# CC-Canto (Pleco, CC BY-SA 3.0): English for Cantonese words, and Jyutping readings for CC-CEDICT's entries.
# cantonese.org itself is often unreachable from build machines; this GitHub mirror holds the 2017-02-02 release.
fetch cc-canto https://github.com/amadeusine/cc-canto-data.git a687e46

# words.hk 粵典 (Non-Commercial Open Data License 1.0, https://words.hk/base/hoifong/): Cantonese and English
# definitions with example sentences. Taken from the daily Yomitan build (MarvNC/wordshk-yomitan) at a pinned date.
# Non-commercial only: see ATTRIBUTION.md.
WORDSHK_TAG=2026-11-17
WORDSHK_FILE=Words.hk.2026-11-16.zip
if [ ! -f "raw/wordshk/$WORDSHK_FILE" ]; then
  mkdir -p raw/wordshk
  curl -sSfL -o "raw/wordshk/$WORDSHK_FILE" \
    "https://github.com/MarvNC/wordshk-yomitan/releases/download/$WORDSHK_TAG/$WORDSHK_FILE"
fi
echo "ok  words.hk @ $(basename "$WORDSHK_FILE" .zip | sed 's/^Words\.hk\.//')"

# CC-CEDICT (CC BY-SA 4.0) as JSON: pinyin and English for the Mandarin equivalents shown in the app.
if [ ! -f raw/cedict/package/cedict.json ]; then
  mkdir -p raw/cedict
  (cd raw/cedict && npm pack cedict-json@1.3.20251213 --silent >/dev/null && tar xzf cedict-json-1.3.20251213.tgz)
fi
echo "ok  cedict-json @ 1.3.20251213"

# Plangothic (SIL OFL 1.1) webfont chunks: glyphs for Cantonese characters common fonts lack (𠝹, 𨋢…).
# build_app.py embeds only the glyphs the app uses.
if [ ! -d raw/plangothic/package ]; then
  mkdir -p raw/plangothic
  (cd raw/plangothic && npm pack @free-fonts/plangothic@1.0.0 --silent >/dev/null && tar xzf free-fonts-plangothic-1.0.0.tgz)
fi
echo "ok  plangothic @ 1.0.0"
