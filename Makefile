.PHONY: install test lint format schema run batch clean help

PYTHON ?= python

help:
	@echo "Signalpost Make targets:"
	@echo "  install   Install Python dependencies"
	@echo "  test      Run test suite with pytest"
	@echo "  lint      Run ruff linter"
	@echo "  format    Format code with ruff"
	@echo "  schema    Export company_profile.schema.json"
	@echo "  run       Run API & UI with docker compose"
	@echo "  batch     Run batch profiling on input file"
	@echo "  clean     Remove cache and temporary build files"

install:
	$(PYTHON) -m pip install -r requirements.txt

build:
	npm run build

test:
	$(PYTHON) -m pytest -v

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

schema:
	$(PYTHON) docs/export_schema.py

run:
	docker compose up --build

serve:
	$(PYTHON) -m signalpost serve --host 0.0.0.0 --port 8000

INPUT ?= data/orgnrs_1000.txt
OUT ?= out

batch:
	$(PYTHON) -m signalpost run --input $(INPUT) --out $(OUT)

clean:
	rm -rf cache out .pytest_cache .ruff_cache signalpost.db
