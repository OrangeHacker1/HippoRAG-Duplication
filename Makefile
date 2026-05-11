.PHONY: install build-kg run test lint audit reproduce download-data download-models demo loadtest

PYTHON := .venv/bin/python
PYTEST  := .venv/bin/pytest
PIP     := .venv/bin/pip

install:
	$(PIP) install -r requirements.txt
	$(PIP) install -e . --no-deps

build-kg:
	$(PYTHON) EXTRA/run_build_kg.py

run:
	.venv/bin/uvicorn myproject.api.app:app --host 0.0.0.0 --port 8000

test:
	mkdir -p reports
	$(PYTEST) tests/unit/ \
		--junitxml=reports/unit.xml \
		-v
	$(PYTEST) tests/integration/ \
		--junitxml=reports/integration.xml \
		-v
	$(PYTEST) tests/user_stories/ \
		--junitxml=reports/user_stories.xml \
		-v
	$(PYTEST) tests/ \
		--cov=myproject \
		--cov-report=xml:reports/coverage.xml \
		--cov-report=html:reports/coverage_html \
		-q

lint:
	.venv/bin/ruff check .
	.venv/bin/black --check .
	.venv/bin/mypy src/myproject/ --ignore-missing-imports

audit:
	$(PIP) install pip-audit -q
	mkdir -p reports
	.venv/bin/pip-audit 2>&1 | tee reports/security.txt || true

reproduce:
	docker compose build
	docker compose run --rm build-kg
	docker compose run --rm eval

download-data:
	@echo "Eval dataset is bundled in src/myproject/data/eval_dataset.py — no download required."

download-models:
	$(PYTHON) -c "from myproject.kg.embeddings import EmbeddingEngine; EmbeddingEngine()"

demo:
	bash scripts/demo.sh

loadtest:
	.venv/bin/locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 60s \
		--host http://localhost:8000 \
		--json > reports/benchmarks.json
