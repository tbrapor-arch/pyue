CREATE TABLE source(id TEXT PRIMARY KEY, name TEXT, year TEXT, license TEXT, commercial_ok INT, note TEXT);

-- One row per (characters, reading) per source. Romanisation is always Jyutping.
CREATE TABLE entry(
  id INTEGER PRIMARY KEY,
  source TEXT REFERENCES source(id),
  hanzi TEXT,             -- traditional characters
  jyutping TEXT,          -- 'zung1 ji3'
  jkey TEXT,              -- 'zung1-ji3'
  toneless TEXT,          -- 'zung-ji'
  kind TEXT,              -- word | char
  share INT,              -- for a single character: % of its uses with this reading (rime), else NULL
  french TEXT,            -- course gloss (course/glosses_fr.tsv), filled by build_app, not here
  -- learner layers (filled by enrich step)
  freq INT,               -- weight in rime's essay-cantonese word list
  freq_rank INT,
  mandarin_best TEXT,     -- same characters in CC-CEDICT, else NULL
  hsk_new INT,
  cognate TEXT,           -- same (characters are a Mandarin word) | different (Cantonese-only) | n/a
  core INT
);
CREATE INDEX entry_jkey ON entry(jkey);
CREATE INDEX entry_hanzi ON entry(hanzi);
CREATE INDEX entry_toneless ON entry(toneless);

CREATE TABLE cedict(trad TEXT, simp TEXT, pinyin TEXT, english TEXT);
CREATE INDEX cedict_trad ON cedict(trad);
