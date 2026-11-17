# Project notes (state as of 17 Nov 2026)

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

- **Pacing** of P1–P70: Tsheh-tû's 進修 plus published perfectionnement volumes the owner provides (kept in the
  private repo); where they disagree, the published volumes win. Only counts and pacing ideas come from them.

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
  - Word card: Cantonese only / Used differently in Mandarin / Same; English (order in `tools/english.py`); Mandarin
    with pinyin; other readings of the characters with their share.
  - **Cantonese dictionaries** (17 Nov 2026, from the cross-app review): `make db` adds CC-Canto (CC BY-SA 3.0, GitHub
    mirror of the 2017 release, plus its Jyutping for CC-CEDICT entries) and words.hk 粵典 (Non-Commercial Open Data
    License 1.0, the daily Yomitan build pinned by date) in their own tables (`tools/yue_dicts.py`); rime stays the
    word list that cuts lines. Card English: course > `glosses_en.tsv` > words.hk > CC-Canto > CC-CEDICT by Jyutping
    (a single character: CC-CEDICT, CC-Canto, then words.hk) > via the Mandarin word > parts. Words through the
    Mandarin detour went from 1,894 to 42. Cards also show up to 4 words.hk senses and one example with English, and
    a trust label (✓ Reading in CC-Canto · words.hk, or rime only, or course word). Owner's choice: words.hk is shown
    in the public app, labelled non-commercial on each card, so the published app as a whole is for non-commercial use.
  - **Reading verifier** (17 Nov 2026): `tools/verify_words.py`, run by `make lint` after `lint.py` (never fails the
    build): new words not confirmed by CC-Canto/words.hk/CC-CEDICT, and line readings no dictionary has or that rime
    gives under 5 %; changed tones (tone 1/2 of a listed reading) accepted (`make verify-all` lists them). The private
    module runs the same `Verifier` on the base course (`pyue-private/tools/verify_base.py`). First run on P1–P70:
    13 unknown, 4 rare, 21 unconfirmed (proverbs and phrases), 2 changed tones.
  - **Lessons › 粵字** (17 Nov 2026, owner's request): a sub-tab beside the lesson grid listing the 69 characters that
    only written Cantonese uses (佢 嘅 咗 冇 喺 嘢 瞓 攰…), grouped by use (`course/yuezi.yaml`): Jyutping always shown,
    English, Mandarin counterpart, one example and the 進修 words that contain it. The example is a lesson line
    (picked by `build_app.py`); the 6 known only from the base course (嘞 嘥 乸 髀 踭 噚) have new sentences written for
    the list. A last, borderline group (38) holds characters Mandarin also writes daily but Cantonese uses with
    another meaning or job (係, 食, 企, 喇…); 曳, 晏 and 呃 'cheat' have sentences written for the list.
    Then (17 Nov 2026, owner: "I want them ALL") 432 more Cantonese-only characters not in the lessons yet (`more:` in
    the yaml; how they were chosen is in its header), grouped by words.hk part of speech (verbs, nouns, describing,
    measure words, particles, function words, only inside words, vulgar, folded): reading, English, example and words
    from words.hk at build time, labelled non-commercial. 175 rare ones have no words.hk example; their words show use.
    Same day, for size and speed: part (b) is no longer in index.html (it had grown it from 7.6 to 9.7 MB and made 粵字
    take ~1 s to open). `build_app.py` writes it to `app/dist/yuezi-more.json` (~1 MB: its groups, the word cards only
    it uses — full for the word buttons, light for words that are only tokens of an example — and, as @font-face CSS,
    the glyphs only it needs); index.html keeps each of its groups' name and count. The page fetches the file the
    first time 粵字 is opened (`YZ.load` in the template; the name carries a content hash; `site.py` copies it,
    `sw.js` keeps it, so it works offline after that), and quietly at start if a list or the review deck holds one of
    its words. Cards are made as they come near the screen (IntersectionObserver); a jump makes its target first.
    Characters words.hk has no example for take one from `course/yuezi_examples.yaml` (optional), labelled "written
    for this list · not checked by a native speaker".
  - Practice › Drills: a tone drill (pick the tones of a word shown without them) in place of tone changes.
  - Settings: no accent presets or review audio.
  - Dialogue audio (10 Nov 2026): synthetic Azure zh-HK voices, as in sy-zy (`tools/tts.py`, `course/voices.tsv`,
    workflow `audio.yml`; README › Lesson audio). Made once the `AZURE_SPEECH_KEY` secret is set.
  - **Fonts identical to Tsheh-tû and sy-zy** (6 Nov 2026, owner's request): Iansui for characters, Tsheh-tû's
    embedded Noto Sans ('TailoSans') for Jyutping, Atkinson Hyperlegible for the interface. Characters Iansui lacks
    (哋, 咗…) come from LXGW WenKai TC ('PyueExt'), same Klee One design, subset and embedded, as sy-zy does with
    LXGW WenKai; `sh data/fetch_fonts.sh` (pinned, run by `make data`).
  - `PYUE_FIXTURES=1 make app` adds `tools/fixtures/01.yaml`, a sample lesson for checking the app (not published).
  - Not ported yet: `record.html` (native-speaker recording), Podcast/Video/Music content, themes, grammar sheets.

## Open items
- Readings the verifier flagged in P1–P70, all settled (17 Nov 2026): P57 食物 sik6 mat6; P61 講 → 唱; P04/P07
  做到隻積咁 → 做到隻狗咁 ('work like a dog'; 隻積 was not a real expression); P58 鐳 lui1 → leoi1 (words.hk,
  Southeast Asian Cantonese 'money'); P64 怕醜 ceu2 → cau2; P44 艘 sau1 → sau2 (dictionary reading, note says many
  say sou1/sau1). Kept on purpose, listed with reasons in `course/verify_ok.tsv`: 呃 e2 (hesitation), 經紀 ging1 kei2
  (spoken form, P47 note), 哦 o6. What `make lint` still lists: 21 set phrases found in rime only.
- Mandarin tap (pinyin on any Mandarin text): wait for Tsheh-tû's shared component (branch `dict-pinyin`) to reach its
  `main`, then port it for the "vs Mandarin" notes and the card's Mandarin section (owner, 17 Nov 2026).
- Not ported yet: themes, grammar sheets, recording page (fine until needed).
- Native-speaker check of P1–P70.
