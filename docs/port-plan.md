# Port plan: Tsheh-tû → pyue

Rule: keep Tsheh-tû's files, names and structure wherever possible, so a fix in one repo can be carried to the other.
Only what is tied to Taigi changes.

## What changes
| Tsheh-tû | pyue |
|---|---|
| Tâi-lô above the characters (`tailo:` fields) | Jyutping (`jyutping:` fields), tone numbers shown as digits or superscript (setting) |
| MOE dictionary + iTaigi + 台華 (`taigi.db`) | rime-cantonese (CC BY 4.0) for words and readings, pycantonese / HKCanCor (CC BY) for frequency, CC-CEDICT (CC BY-SA) for the Mandarin side; French glosses written for the course in `course/glosses_fr.tsv` (+ optional non-commercial build with other dictionaries, like `make db-nc`) |
| `tools/sandhi.py`, tone-change drills | dropped; replaced by a **tone drill** (hear/see a word, pick its tone numbers) and a changed-tone (變音) note type |
| English UI and glosses | French UI and glosses (`tools/french.py` in place of `tools/english.py`) |
| "Around Taiwan" table (regional readings) | dropped (or later: common colloquial vs. reading pronunciations, e.g. 嘢, 冇) |
| Mandarin equivalent on every card (HSK, false friends) | kept: Mandarin equivalent, same-character cognate / false friend / Cantonese-only label |
| Lessons tab: grid 1–100, then 進修 P1–P70 | grid of P1–P70 public; the base 1–100 grid appears above it **only** on a device whose token reads pyue-private |
| Podcast / Video / Music tabs | TV (Cantonese series, official uploads in YouTube's player), Music (official MVs), Podcast later; transcripts and timed lyrics from the private module |
| Exam tab (private) | Private tab: the owner's books and base course, synced with his audio |

## Order of work
1. Scaffold, rules, notes (done 6 Nov 2026).
2. `data/fetch.sh` + `tools/build_db.py` → `data/build/yue.db`; `tools/lookup.py`; `tools/jyutping.py` (parse,
   validate, compare readings). **Done 6 Nov 2026.**
3. `tools/lint.py` (every word in the database, Jyutping syllables valid and matching the characters).
4. App: copy `app/index.template.html`, `tools/build_app.py`, `tools/cards.py`, `tools/site.py`, `app/pwa/`, the Pages
   workflow; swap Tâi-lô → Jyutping, English → French, drop sandhi; same look, same tabs.
5. Private module loader identical to Tsheh-tû's (`Exam` object, `exam/index.json`, cache by hash).
6. Syllabus P1–P70 (`course/syllabus.yaml`), written from the private analysis's lists of known words and grammar.
