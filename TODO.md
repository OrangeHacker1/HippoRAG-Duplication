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
- [x] `docs/diagrams/architecture.png`
- [x] `docs/assets/stories/us_01_expected.png` through `us_06_expected.png`

### Design — Reproducibility Manifest (10 pts)
- [x] `grading/manifest.yaml` — Python version, seed, model IDs, dataset versions, expected metrics
- [x] `docs/DATA.md`
- [x] `docs/MODELS.md`
- [x] `docs/REPRODUCE.md` — hardware profile, expected runtime, metric tolerances
- [x] `requirements.txt` with pinned versions
- [x] `make reproduce`, `make download-data`, `make download-models` targets in Makefile
- [ ] Update `commit_sha` in `grading/manifest.yaml` to final commit before submission

### Deploy — Build and Deployment (6 pts)
- [x] `Dockerfile` — multi-stage, non-root user, health check (CPU-only torch)
- [x] `docker-compose.yml` — health checks on all services, dependency ordering
- [x] `.dockerignore` — excludes .venv, submodule, .git from build context
- [x] `.env.example` with required placeholders and comments
- [x] `.env` in `.gitignore`
- [x] Quick start in `README.md`

### Test — Verification and Automated Testing (12 pts)
- [x] `tests/unit/` — `test_metrics.py`, `test_graph_store.py`, `test_ppr.py`
- [x] `tests/integration/` — `test_api.py`
- [x] `tests/user_stories/` — `test_stories.py` with `@pytest.mark.user_story("US-NN")`
- [x] `scripts/demo.sh`
- [x] `reports/unit.xml`
- [x] `reports/integration.xml`
- [x] `reports/user_stories.xml`
- [x] `reports/coverage.xml` and `reports/coverage_html/`

### Test — Stress and Robustness (6 pts)
- [x] `tests/edge/test_edge_cases.py`
- [x] `tests/load/locustfile.py`
- [x] `docs/benchmarks.md`
- [ ] `reports/benchmarks.json` — run `make loadtest` against live system

### Implement — Code Quality and Responsible AI (6 pts)
- [x] `pyproject.toml` — ruff, black, mypy configured
- [x] `make lint` target
- [x] `docs/MODEL_CARD.md`
- [x] `reports/security.txt`

### Operate — Logging (5 pts)
- [x] Structured JSON logging in `api/logger.py`
- [x] `request_id` propagated through all components
- [x] `docs/LOGGING.md`

### Operate — Application Functionality and UI (20 pts)
- [x] `api/app.py` — FastAPI with query, evaluate, health endpoints
- [x] `api/templates/index.html` and `evaluate.html`
- [x] `docs/STORIES.md`
- [x] US-05 and US-06 are error path stories
- [x] `reports/walkthrough.md`
- [x] `docs/assets/stories/us_01_expected.png` through `us_06_expected.png`

### Operate — User Documentation (6 pts)
- [x] `README.md`
- [x] `docs/usage.md`
- [ ] `docs/assets/demo.gif` — record a short screen capture of the full flow

### Team — Contributions (4 pts)
- [x] `CONTRIBUTIONS.md`
- [x] `reports/git_contributions.txt`

---

## V2 Paper Table Replication (Professor Request)

The paper has 5 main evaluation tables. Goal: replicate as many as possible on a
MuSiQue subset (50–100 questions, 200–500 corpus passages) using our LLM endpoint.
Data is already available at `Official-HippoRAG-Repo/reproduce/dataset/`.

### Table 2 — QA Performance (F1 scores) ← most important
Paper reports F1 on: NQ, PopQA, MuSiQue, 2Wiki, HotpotQA, LV-Eval, NarrativeQA
We target: **MuSiQue subset only**

- [ ] Copy `musique.json` + `musique_corpus.json` from submodule to `data/`
- [ ] Write `scripts/run_musique_eval.py` — loads subset, builds KG, runs queries, reports F1
- [ ] Run the script (needs VPN + ~30–60 min)
- [ ] Add results to `REPORT.md` as Table 2 partial replication
- [ ] Note deviation: we use `all-MiniLM-L6-v2` instead of NV-Embed-v2, and UTSA LLM instead of Llama-3.3-70B

### Table 3 — Retrieval Performance (Recall@5) ← second priority
Paper reports Recall@5 for retrieved passages (not just answer F1)
We target: **MuSiQue subset only**

- [ ] Add Recall@5 passage metric to eval script (gold docs are in `musique.json` → `paragraphs`)
- [ ] Report Recall@5 alongside F1 in `REPORT.md`

### Table 4 — Ablation Study ← third priority (if time allows)
Paper tests: NER-to-node vs Query-to-node vs Query-to-triple linking methods
We target: compare our current approach (NER/entity matching) vs query-to-triple

- [ ] Implement query-to-triple linking variant in `retrieval/retriever.py`
- [ ] Run both variants on MuSiQue subset
- [ ] Report Recall@5 difference in `REPORT.md`

### Table 7 — Robustness to retrievers (MuSiQue subset) ← bonus if time allows
Paper uses: GTE-Qwen2-7B, GritLM-7B, NV-Embed-v2
We have: all-MiniLM-L6-v2 only — skip unless time permits

### Tables 5, 6, 8, 9 — Skip
Table 5: hyperparameter sweep (too expensive)
Table 6: qualitative examples (no code needed, low value)
Tables 8, 9: repeat of Table 2/3 with GPT-4o-mini (different LLM, out of scope)

---

## Remaining Manual Actions

1. [ ] **Make repo public** on GitHub (Settings → Change visibility → Public)
2. [ ] **Decide branch** — submit Samantha's-Branch URL or merge to main
3. [ ] **Run loadtest** — `docker compose up` then `make loadtest` → `reports/benchmarks.json`
4. [ ] **Update commit_sha** — final `git rev-parse HEAD` → `grading/manifest.yaml`
5. [ ] **Run MuSiQue eval** — needs VPN, 30–60 min runtime
6. [ ] **Record demo.gif** — optional but listed in rubric
