# make data      download open sources (data/raw)
# make db        build data/build/yue.db
# make lookup W=鍾意
PY = python3 -I
RAW = data/raw
OUT = data/build

.PHONY: data db lookup clean lint verify-all app coverage
data:
	sh data/fetch.sh
	sh data/fetch_fonts.sh

db: data
	mkdir -p $(OUT)
	$(PY) tools/build_db.py $(RAW) $(OUT)/yue.db

lookup:
	$(PY) tools/lookup.py $(OUT)/yue.db "$(W)"

clean:
	rm -rf $(OUT)

lint:
	$(PY) tools/lint.py
	$(PY) tools/verify_words.py

# suspects only; `make verify-all` also lists the accepted changed tones (變音)
verify-all:
	$(PY) tools/verify_words.py --all

app:
	$(PY) tools/build_app.py

coverage:
	$(PY) tools/coverage.py
