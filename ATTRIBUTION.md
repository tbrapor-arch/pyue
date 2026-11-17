# Data sources

Downloaded by `data/fetch.sh` at pinned versions; nothing is redistributed in this repo.

| Source | Use | Licence |
|---|---|---|
| rime-cantonese (https://github.com/rime/rime-cantonese) | words, Jyutping readings, character readings | CC BY 4.0 |
| PyCantonese / HKCanCor (https://github.com/jacksonllee/pycantonese) | word frequency in spoken Cantonese | MIT (code), CC BY 4.0 (corpus) |
| CC-CEDICT | Mandarin equivalents, pinyin | CC BY-SA 4.0 |
| CC-Canto (Pleco; mirror https://github.com/amadeusine/cc-canto-data) | English for Cantonese words; Jyutping for CC-CEDICT entries | CC BY-SA 3.0 |
| words.hk 粵典 (https://words.hk; via https://github.com/MarvNC/wordshk-yomitan) | senses in Cantonese and English, example sentences | Non-Commercial Open Data License 1.0 (https://words.hk/base/hoifong/) |

**Non-commercial:** words.hk's data may be used only for non-commercial purposes. The published app shows it on word
cards (marked there), so the app as published is for non-commercial use. The course text itself stays CC BY-SA 4.0;
to make a commercial build, drop `words.hk` from `data/fetch.sh` (the build then uses CC-Canto and CC-CEDICT only).
