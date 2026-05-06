.PHONY: install build-kg run test lint audit reproduce download-data download-models demo loadtest

install:
	pip install -r requirements.txt

build-kg:
	python run_build_kg.py

run:
	uvicorn api.app:app --host 0.0.0.0 --port 8000

test:
	pytest tests/ \
		--junitxml=reports/unit.xml \
		--cov=kg --cov=retrieval --cov=llm --cov=api \
		--cov-report=xml:reports/coverage.xml \
		--cov-report=html:reports/coverage_html \
		-v

lint:
	ruff check .
	black --check .
	mypy kg/ retrieval/ llm/ api/ --ignore-missing-imports

audit:
	pip-audit -o reports/security.txt || true

reproduce:
	docker compose build
	docker compose run --rm build-kg
	docker compose run --rm eval

download-data:
	@echo "Eval dataset is bundled in data/eval_dataset.py — no download required."

download-models:
	python -c "from kg.embeddings import EmbeddingEngine; EmbeddingEngine()"

demo:
	bash scripts/demo.sh

loadtest:
	locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 60s \
		--host http://localhost:8000 \
		--json > reports/benchmarks.json
