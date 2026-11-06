# Project notes (state as of 6 Nov 2026)

Started 6 Nov 2026 as a Cantonese counterpart of Tsheh-tû (https://github.com/tbrapor-arch/tsehtu), same layout.
Private companion: `tbrapor-arch/pyue-private`.

## Goal
- A **perfectionnement** course in Cantonese, in English: 70 longer lessons in varied genres (P1–P70), every 7th a
  review, for a learner who has finished a 100-lesson beginner method. Public, original, CC BY-SA 4.0.
- Around it, the same app as Tsheh-tû: Lessons, Practice (vocabulary by theme, grammar, drills, cards), TV, Music,
  Settings, plus a hidden tab from the private module (the owner's own books and base course, transcripts).

## Decisions (6 Nov 2026, with the owner)
- Romanisation **Jyutping**. Translation and UI language **English** (decided 6 Nov 2026; French was the first answer, then changed). Text in **written Cantonese**
  (係/嘅/咗/佢/唔/冇…, traditional characters), not standard written Chinese.
- Layout, look and tabs **identical to Tsheh-tû** (notebook look, Mainichi-style lesson grid, second wave, cards).
- The base course of 100 lessons that P1–P70 continue lives **only** in the private module (the owner's own copy,
  for syncing with his audio). The public repo never names that method and never contains its text, storylines or
  romanisation; only counts and pacing ideas may leave `reference/`.
- The perfectionnement's starting level is set by an analysis of those 100 lessons done in the private repo; only
  the resulting **word list and grammar inventory** (what is already known) may be used here, as plain lists.

## Repository rules
- Public repo: no transcripts, recordings, scans, book text or text derived from them. Those live in pyue-private.
- `reference/` (git-ignored): only counts and pacing ideas may leave it, never text or storylines.
- Never commit generated data (`data/raw`, `data/build`, `app/dist`, `*.db`).
- The Cantonese is not native-checked unless a lesson says so.

## Status
- Scaffold and port plan: `docs/port-plan.md`.
- **Database** (6 Nov 2026): `make db` → `data/build/yue.db`, 137k entries from rime-cantonese (words, character readings
  with their share), frequency rank from rime's essay list, CC-CEDICT for the Mandarin side. Each word is labelled
  `same` (ordinary Mandarin word: 我), `partial` (Mandarin has the characters, Cantonese use differs: 係, 睇) or
  `different` (Cantonese-only: 佢, 嘢, 冇 → 沒有). `make lookup W=…` takes characters or Jyutping (no tones = any tone).
- **App ported** (6 Nov 2026): Tsheh-tû's template, tabs and notebook look, with Jyutping, a 粵 icon, separate
  storage keys (`pyue:`) and sync gist (`pyue-progress.json`), since both apps share the github.io origin.
  - Lessons tab: lesson 0 (reading Jyutping), then the 進修 cover and the P1–P70 grid. The base 1–100 grid is drawn
    only when the private module supplies those lessons.
  - Lines are cut into words by PyCantonese's segmenter, each piece checked against the database with the line's own
    reading (a piece it lacks is cut again by frequency). Hyphens in a line's Jyutping override the cut.
  - Word card: Cantonese only / Used differently in Mandarin / Same; English (course, `course/glosses_en.tsv`, else
    automatic via the Mandarin word in CC-CEDICT); Mandarin with pinyin; other readings of the characters with their share.
  - Practice › Drills: a tone drill (pick the tones of a word shown without them) in place of tone changes.
  - Settings: no accent presets or review audio (no recordings yet).
  - `PYUE_FIXTURES=1 make app` adds `tools/fixtures/01.yaml`, a sample lesson for checking the app (not published).
  - Not ported yet: `record.html` (native-speaker recording), Podcast/Video/Music content, themes, grammar sheets.

## Open items
- GitHub Pages: Settings › Pages › Source: GitHub Actions (one time), then every push to `main` publishes.
- Base-course transcription and analysis in pyue-private.
- Syllabus for P1–P70 once the analysis is done.
