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

# CC-CEDICT (CC BY-SA 4.0) as JSON: pinyin and English for the Mandarin equivalents shown in the app.
if [ ! -f raw/cedict/package/cedict.json ]; then
  mkdir -p raw/cedict
  (cd raw/cedict && npm pack cedict-json@1.3.20251213 --silent >/dev/null && tar xzf cedict-json-1.3.20251213.tgz)
fi
echo "ok  cedict-json @ 1.3.20251213"
