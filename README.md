# pyue

A Cantonese perfectionnement course in English, with an open vocabulary database behind it.
Romanisation: **Jyutping** (LSHK). Script: written Cantonese (係、嘅、咗、佢), traditional characters.

Built on the same layout as Tsheh-tû (https://github.com/tbrapor-arch/tsehtu): same folders, same app, same tabs.
Everything (docs, course, app) is in English, like Tsheh-tû.

## Layout
```
course/        perfectionnement lessons P1–P70, themes, syllabus (YAML), original content — CC BY-SA 4.0
app/           reader app template; `make app` writes app/dist/index.html
tools/         database build + lookup scripts — MIT
audio/         synthetic dialogue audio made by tools/tts.py (Azure, zh-HK voices) — CC BY-SA 4.0
data/fetch.sh  downloads open data sources at pinned commits (nothing committed)
data/build/    generated: yue.db, core_vocab.csv (git-ignored)
reference/     your local, git-ignored reference material
```

## Build the database
```sh
make db                 # → data/build/yue.db
make lookup W=鍾意       # characters
make lookup W=zung1ji3  # Jyutping; no tone number = any tone
```

## Writing and checking lessons
```sh
make lint               # every word in course/**/*.yaml must exist in the database, Jyutping must match
make coverage           # how much of the core vocabulary the lessons cover, and what to teach next
make app                # build the reader app: app/dist/index.html, one self-contained page
```
Project state: `PROJECT_NOTES.md`; port plan from Tsheh-tû: `docs/port-plan.md`.

## The app
`make app` writes `app/dist/index.html`, one self-contained page (works offline, progress kept in the browser).
On every push to `main`, `.github/workflows/pages.yml` rebuilds everything and publishes on GitHub Pages.
An optional private module (loaded with the owner's token) adds material that cannot be public; see
`docs/sync-and-private-module.md`.

## Lesson audio (synthetic)
Every dialogue line of P1–P70 can have a ▶ button, and each lesson a "Listen to the dialogue" button. The audio is
made by `tools/tts.py` with Microsoft's three Hong Kong Cantonese neural voices on the **Azure Speech API**
(`zh-HK-HiuMaanNeural`, `zh-HK-HiuGaaiNeural`, `zh-HK-WanLungNeural`), the same pipeline as sy-zy.

- Setup: create a Speech resource in the Azure portal (free tier F0: 500,000 characters a month; the whole course is
  about 40,000), then add the repository secrets `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`. The **Lesson audio**
  workflow (`.github/workflows/audio.yml`) then makes the audio for new or changed lines whenever a lesson changes,
  commits `audio/` and rebuilds the site. Run it once by hand (Actions › Lesson audio › Run workflow) for the first batch.
  Locally: `AZURE_SPEECH_KEY=… AZURE_SPEECH_REGION=… python3 tools/tts.py` (`--dry-run` shows what would be sent).
- `course/voices.tsv` gives each speaker a voice, pitch and speed (one male voice, so the men differ by pitch);
  `NN:speaker` rows set who reads a letter, a menu or a broadcast in lesson NN. Stage directions （…） are not read.
- `course/tts_fix.tsv` respells words the voice reads wrongly. The voice uses its own readings, not the lesson's
  Jyutping: it is a guide to rhythm and melody, labelled as synthetic in the app, and may miss changed tones.
- A line edited after its audio was made goes silent until the audio is made again (`audio/index.json` keeps the text).

## Licences
Code: MIT (`LICENSE`). Course content: CC BY-SA 4.0 (`LICENSE-CONTENT.md`). Data sources keep their own licences
(`ATTRIBUTION.md`); they are downloaded, not redistributed.
