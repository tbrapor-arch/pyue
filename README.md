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

## Licences
Code: MIT (`LICENSE`). Course content: CC BY-SA 4.0 (`LICENSE-CONTENT.md`). Data sources keep their own licences
(`ATTRIBUTION.md`); they are downloaded, not redistributed.
