# HippoRAG TODO

## Implementation Gaps (All Done)

- [x] Gap 1 — Fix `retrieval/filter.py` stub — LLM now parses and returns relevant triple indices
- [x] Gap 2 — Wire `query_processor.py` into `retriever.py` to extract seeds from the query
- [x] Gap 3 — Fix `llm/llm_client.py` — replace `eval()` with JSON-format prompt and structured parsing
- [x] Gap 4 — Fix context in `retrieval/retriever.py` — pull actual passage text from graph nodes instead of node names
- [x] Gap 5 — Add evaluation
  - [x] Gap 5a — Build a multi-hop test corpus (`data/eval_dataset.py`)
  - [x] Gap 5b — Write test questions with gold answers (`data/eval_dataset.py`)
  - [x] Gap 5c — Implement Recall@k metric (`eval/metrics.py`)
  - [x] Gap 5d — Implement Exact Match and F1 score metrics (`eval/metrics.py`)
  - [x] Gap 5e — Write evaluation runner script (`run_eval.py`)

---

## Rubric Checklist (Deadline: May 10, 11:59 PM)

### Plan — Specification Driven Development (25 pts)
- [x] `docs/SPEC.md` — Purpose, Component Inventory, Data Flow, Public Interfaces, Model & Prompt Selection, Config structure
- [x] `docs/STORIES.md` — US-01 through US-06 with Given/When/Then and numbered steps
- [x] `grading/traceability.yaml` — maps each story to spec section, modules, and tests
- [x] `scripts/regenerate.sh` and `scripts/regenerate_prompt.md`
- [ ] `docs/diagrams/architecture.png` — render `docs/diagrams/architecture.mmd` at mermaid.live and save as PNG
- [ ] `docs/assets/stories/us_01_expected.png` through `us_06_expected.png` — screenshots of live UI per story

### Design — Reproducibility Manifest (10 pts)
- [x] `grading/manifest.yaml` — Python version, seed, model IDs, dataset versions, expected metrics
- [x] `docs/DATA.md`
- [x] `docs/MODELS.md`
- [x] `docs/REPRODUCE.md` — hardware profile, expected runtime, metric tolerances
- [x] `requirements.txt` with pinned versions
- [x] `make reproduce`, `make download-data`, `make download-models` targets in Makefile
- [ ] Update `commit_sha` in `grading/manifest.yaml` to final commit before submission

### Deploy — Build and Deployment (6 pts)
- [x] `Dockerfile` — multi-stage, non-root user, health check
- [x] `docker-compose.yml` — health checks on all services, dependency ordering
- [x] `.env.example` with required placeholders and comments
- [x] `.env` in `.gitignore`
- [x] Quick start in `README.md`

### Test — Verification and Automated Testing (12 pts)
- [x] `tests/unit/` — `test_metrics.py`, `test_graph_store.py`, `test_ppr.py`
- [x] `tests/integration/` — `test_api.py`
- [x] `tests/user_stories/` — `test_stories.py` with `@pytest.mark.user_story("US-NN")`
- [x] `scripts/demo.sh`
- [ ] `reports/unit.xml` — run `make test`
- [ ] `reports/integration.xml` — run `make test`
- [ ] `reports/user_stories.xml` — run `make test`
- [ ] `reports/coverage.xml` — run `make test`
- [ ] `reports/coverage_html/` — run `make test`

### Test — Stress and Robustness (6 pts)
- [x] `tests/edge/test_edge_cases.py` — empty, whitespace, very long, non-ASCII, multilingual, adversarial, XSS
- [x] `tests/load/locustfile.py`
- [x] `docs/benchmarks.md`
- [ ] `reports/benchmarks.json` — run `make loadtest` against live system

### Implement — Code Quality and Responsible AI (6 pts)
- [x] `pyproject.toml` — ruff, black, mypy configured
- [x] `make lint` target
- [x] `docs/MODEL_CARD.md` — Intended Use, Limitations, Risks, Out of Scope
- [ ] `reports/security.txt` — run `make audit`

### Operate — Logging (5 pts)
- [x] Structured JSON logging in `api/logger.py` — timestamp, level, module, request_id
- [x] `request_id` generated per request and propagated through all log lines
- [x] `docs/LOGGING.md` — worked example with captured request_id and log lines

### Operate — Application Functionality and UI (20 pts)
- [x] `api/app.py` — FastAPI web app with query, evaluate, health endpoints
- [x] `api/templates/index.html` — query page
- [x] `api/templates/evaluate.html` — evaluation page
- [x] `docs/STORIES.md` — followable by human without reading source
- [x] US-05 and US-06 are error path stories with documented expected messages
- [x] `reports/walkthrough.md` — template ready for TA
- [ ] `docs/assets/stories/us_01_expected.png` through `us_06_expected.png` — **take screenshots of live UI**

### Operate — User Documentation (6 pts)
- [x] `README.md` — title, description, tech stack, quick start, results, source layout
- [x] `docs/usage.md` — one section per story
- [ ] `docs/assets/stories/us_NN_expected.png` — same screenshots needed above
- [ ] `docs/assets/demo.gif` — record a short screen capture of the full flow

### Team — Contributions (4 pts)
- [x] `CONTRIBUTIONS.md` — roles, modules owned, percentages summing to 100
- [x] `reports/git_contributions.txt` — generated from `git shortlog`

---

## Remaining Manual Actions (need a human)

1. **Run the UI** — `python run_build_kg.py` then `uvicorn api.app:app --port 8000`
2. **Take 6 screenshots** — one per story, save to `docs/assets/stories/us_NN_expected.png`
3. **Render architecture diagram** — paste `docs/diagrams/architecture.mmd` into mermaid.live → export as `docs/diagrams/architecture.png`
4. **Record demo.gif** — short screen capture of query → answer flow, save to `docs/assets/demo.gif`
5. **Run generated reports** — `make test`, `make audit`, `make loadtest`
6. **Update commit_sha** — run `git rev-parse HEAD` and paste into `grading/manifest.yaml` before final push

> NER before triple extraction is the one simplification vs. the official repo — add later if needed.
