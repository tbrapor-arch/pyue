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

-- English for a Cantonese word, matched by characters + reading (tools/yue_dicts.py).
-- src: cccanto (CC-Canto's own entries) | cedict (a CC-CEDICT entry with CC-Canto's Jyutping for it)
CREATE TABLE canto(trad TEXT, jkey TEXT, english TEXT, src TEXT);
CREATE INDEX canto_key ON canto(trad, jkey);

-- words.hk 粵典 (non-commercial licence): one row per headword spelling + reading, senses and examples by entry id
CREATE TABLE wordshk(id INT, hanzi TEXT, jkey TEXT, pos TEXT);
CREATE INDEX wordshk_key ON wordshk(hanzi, jkey);
CREATE TABLE wordshk_sense(id INT, n INT, en TEXT, yue TEXT);
CREATE INDEX wordshk_sense_id ON wordshk_sense(id);
CREATE TABLE wordshk_ex(id INT, n INT, hanzi TEXT, jyutping TEXT, en TEXT, kind TEXT);
CREATE INDEX wordshk_ex_id ON wordshk_ex(id);
