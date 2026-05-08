# HippoRAG Duplication — Full Project History

**Course:** CS 6263 NLP and Agentic AI  
**Deadline:** May 10, 11:59 PM  
**Team:** Samantha Salas (60%), OrangeHacker1 (40%)  
**Branch:** Samantha's-Branch  

---

## 1. Project Goal

Replicate HippoRAG — a graph-based Retrieval-Augmented Generation (RAG) system inspired by the hippocampal indexing theory of human long-term memory. The system builds a Knowledge Graph (KG) from documents, uses Personalized PageRank (PPR) for multi-hop retrieval, and generates answers via an LLM.

The assignment evaluates disciplined software engineering practices: spec-driven development, reproducibility, testing, deployment, logging, and documentation — not just whether the system works.

---

## 2. Starting Point

The skeleton code had 5 implementation gaps:

| Gap | File | Problem |
|-----|------|---------|
| 1 | `retrieval/filter.py` | Stub — returned all triples without filtering |
| 2 | `retrieval/retriever.py` | Seeds only came from triple subjects, not query entities |
| 3 | `llm/llm_client.py` | Used `eval()` to parse Python tuples — fragile and insecure |
| 4 | `retrieval/retriever.py` | Context used raw node names instead of actual passage text |
| 5 | Missing entirely | No evaluation pipeline, no metrics, no test dataset |

---

## 3. Implementation Gaps Fixed

### Gap 1 — `retrieval/filter.py`
**Problem:** Returned all triples regardless of relevance.  
**Fix:** LLM is prompted with numbered triples, returns indices of relevant ones. Parsed with regex. Falls back to all triples if LLM returns nothing.

```python
numbered = "\n".join(f"{i}: ({s}, {r}, {o})" for i, (s, r, o, _) in enumerate(triples))
indices = [int(x) for x in re.findall(r"\d+", output) if int(x) < len(triples)]
return [triples[i] for i in indices] if indices else triples
```

### Gap 2 — `retrieval/retriever.py` (seed extraction)
**Problem:** Seeds only came from triple subjects. Query entities were never matched to graph nodes.  
**Fix:** Added `QueryProcessor` + `EmbeddingEngine`. Seeds = union of triple subjects + LLM-extracted query entities matched to graph nodes via cosine similarity (threshold 0.75).

### Gap 3 — `llm/llm_client.py`
**Problem:** `eval()` on LLM output — unsafe and breaks on malformed output.  
**Fix:** Changed prompt to request JSON arrays. Parses with `json.loads()`. Falls back to bracket-slicing if the LLM wraps output in text.

```python
start = output.index("["); end = output.rindex("]") + 1
parsed = json.loads(output[start:end])
```

### Gap 4 — `retrieval/retriever.py` (passage context)
**Problem:** Context passed to LLM was raw node names like `"Marie Curie"`, not actual passage text.  
**Fix:** `retrieve()` now walks ranked PPR nodes, filters for `type == "passage"`, and returns `node_data["text"]` — the actual source sentence.

### Gap 5 — Evaluation pipeline
**Added:**
- `data/eval_dataset.py` — 10 documents (Marie Curie, Einstein, Newton), 4 multi-hop questions with gold docs and answers
- `eval/metrics.py` — `recall_at_k`, `exact_match`, `f1_score` (token-level)
- `run_eval.py` — samples 3 questions, runs retrieval + answer generation, reports aggregate metrics

---

## 4. Architecture

```
Offline Indexing:
  Documents → LLM (extract_triples) → KG (entity + passage nodes)
  KG nodes → EmbeddingEngine (vectorized cosine similarity) → synonym edges

Online Retrieval:
  Query → TripleMatcher (embed + score) → TripleFilter (LLM selects relevant)
  Query → QueryProcessor (LLM extracts entities) → EmbeddingEngine (match to KG)
  Seeds → PPR (Personalized PageRank) → Top-K passage nodes → LLM (generate answer)

API Layer:
  FastAPI → POST /api/query → retrieve() + generate()
           → POST /api/evaluate → run full eval pipeline
           → GET /health → {"status": "ok"}
```

**Key design choices:**
- `all-MiniLM-L6-v2` for embeddings (lightweight, no GPU needed)
- NetworkX DiGraph for the KG (entity nodes + passage nodes with `type` attribute)
- PPR alpha=0.85, max_iter=100 (increased from 30 to ensure convergence)
- Unknown seeds fall back to uniform PPR distribution

---

## 5. Files Created or Modified

### Core Implementation
| File | Status | What changed |
|------|--------|--------------|
| `retrieval/filter.py` | Modified | LLM-based triple filtering with regex index parsing |
| `retrieval/retriever.py` | Modified | Added QueryProcessor, entity seed matching, passage text context, split into retrieve() + query() |
| `llm/llm_client.py` | Modified | JSON prompt + json.loads() replacing eval() |
| `retrieval/ppr.py` | Modified | max_iter=100, graceful unknown seed handling |
| `kg/builder.py` | Modified | Vectorized cosine similarity (O(n²) → O(n) matrix op) |

### Evaluation
| File | Status | Description |
|------|--------|-------------|
| `data/eval_dataset.py` | New | 10-doc corpus, 4 multi-hop questions |
| `eval/metrics.py` | New | recall_at_k, exact_match, f1_score |
| `run_eval.py` | New | Evaluation runner |
| `scripts/run_musique_eval.py` | New | MuSiQue subset eval for v2 table replication |

### Web API
| File | Status | Description |
|------|--------|-------------|
| `api/app.py` | New | FastAPI app with /api/query, /api/evaluate, /health, / , /evaluate |
| `api/logger.py` | New | JSON structured logging with request_id propagation |
| `api/templates/index.html` | New | Query UI |
| `api/templates/evaluate.html` | New | Evaluation UI with metrics table |

### Testing
| File | Status | Description |
|------|--------|-------------|
| `tests/unit/test_metrics.py` | New | 12 tests for recall, EM, F1 |
| `tests/unit/test_graph_store.py` | New | 6 tests for KG node/edge structure |
| `tests/unit/test_ppr.py` | New | 5 tests for PPR convergence and edge cases |
| `tests/integration/test_api.py` | New | 7 tests for all API endpoints |
| `tests/user_stories/test_stories.py` | New | 6 user story acceptance tests |
| `tests/edge/test_edge_cases.py` | New | Empty, whitespace, long, non-ASCII, XSS, adversarial |
| `tests/load/locustfile.py` | New | Locust load test against /api/query and /health |

### Documentation
| File | Status | Description |
|------|--------|-------------|
| `docs/SPEC.md` | New | Full system specification (25-pt rubric category) |
| `docs/STORIES.md` | New | US-01 through US-06 with Given/When/Then |
| `docs/usage.md` | New | One section per user story |
| `docs/REPRODUCE.md` | New | Hardware profile, runtimes, metric tolerances |
| `docs/MODEL_CARD.md` | New | Intended use, limitations, risks, out of scope |
| `docs/LOGGING.md` | New | Worked example tracing request_id end-to-end |
| `docs/DATA.md` | New | Dataset documentation |
| `docs/MODELS.md` | New | Model documentation |
| `docs/benchmarks.md` | New | Load test methodology and headline numbers |
| `docs/diagrams/architecture.mmd` | New | Mermaid source for architecture diagram |
| `docs/diagrams/architecture.png` | New | Rendered architecture diagram |
| `docs/assets/stories/us_01_expected.png` through `us_06_expected.png` | New | UI screenshots per story |

### Infrastructure
| File | Status | Description |
|------|--------|-------------|
| `Dockerfile` | New | Multi-stage, non-root appuser, CPU-only torch, HEALTHCHECK |
| `docker-compose.yml` | New | app, build-kg, eval services with health checks |
| `.dockerignore` | New | Excludes .venv, submodule, .git (prevents SIGBUS crash) |
| `.env.example` | New | TEACHER_BASE_URL, TEACHER_MODEL, TEACHER_API_KEY |
| `Makefile` | New | test, lint, audit, reproduce, loadtest targets using .venv |
| `pyproject.toml` | New | ruff, black, mypy, pytest markers configured |
| `requirements.txt` | Modified | Added FastAPI, pytest, transformers==4.44.2 pin |

### Grading Artifacts
| File | Status | Description |
|------|--------|-------------|
| `grading/manifest.yaml` | New | Python version, seed, model IDs, commit_sha, expected metrics |
| `grading/traceability.yaml` | New | Maps US-01..US-06 to spec sections, modules, tests |
| `scripts/regenerate.sh` | New | Calls Claude Opus with SPEC.md, extracts code, runs story tests |
| `scripts/_regenerate_helper.py` | New | Python helper for regenerate.sh |
| `scripts/regenerate_prompt.md` | New | Prompt template for spec regeneration |
| `scripts/preflight.sh` | New | Runs all automated checks before submission |
| `scripts/demo.sh` | New | End-to-end demo script |
| `CONTRIBUTIONS.md` | New | Samantha 60%, OrangeHacker1 40% with roles |
| `reports/git_contributions.txt` | New | git shortlog output |
| `reports/walkthrough.md` | New | Template for TA manual walkthrough |

### Generated Reports
| File | How generated |
|------|---------------|
| `reports/unit.xml` | `make test` |
| `reports/integration.xml` | `make test` |
| `reports/user_stories.xml` | `make test` |
| `reports/coverage.xml` | `make test` |
| `reports/coverage_html/` | `make test` |
| `reports/security.txt` | `make audit` |

---

## 6. Test Results

```
Unit tests:          25 / 25 passed
Integration tests:    7 /  7 passed
User story tests:     6 /  6 passed
Edge case tests:      9 /  9 passed
Total:               47 / 47 passed
```

**Spec regeneration test (no-vibe-coding):**
- Fed `docs/SPEC.md` to Claude Opus (`claude-opus-4-5-20251101`, temperature=0)
- Claude regenerated 10 Python files from scratch
- Ran user story tests against regenerated code
- **Result: 6/6 stories passed → 25/25 points**

---

## 7. Docker Setup

**Problem encountered:** `docker compose up --build` crashed with `SIGBUS: bus error` because the build context was 5.34 GB (`.venv` + `Official-HippoRAG-Repo` submodule included).

**Fix:** Added `.dockerignore` excluding `.venv/`, `Official-HippoRAG-Repo/`, `.git/`.

**Second problem:** `pip install torch` inside Docker downloads the 2GB CUDA build and crashes WSL2 memory mapper.

**Fix:** Dockerfile now installs CPU-only torch first:
```dockerfile
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
```

**Result:** Build completes in ~5 minutes. All 3 services (app, build-kg, eval) start correctly.

---

## 8. Key Bugs Fixed

| Bug | Root cause | Fix |
|-----|-----------|-----|
| PPR `PowerIterationFailedConvergence` | `max_iter=30` too low | Increased to 100 |
| PPR crash on unknown seeds | All-zero personalization → ZeroDivisionError | Fall back to `personalization=None` (uniform) |
| `transformers` import error (`keras_nlp backend`) | Version 4.57.x incompatible with sentence-transformers 3.0.1 | Pinned `transformers==4.44.2` |
| `make test` failed with "Permission denied" | System `pytest` not in PATH, `.venv` not created | Makefile updated to use `.venv/bin/pytest` |
| Docker build SIGBUS | 5.34 GB build context | Added `.dockerignore` |
| Docker `pip install torch` SIGBUS | 2GB CUDA wheel overwhelms WSL2 | CPU-only torch install |
| KGBuilder O(n²) embedding loop | Per-pair `cosine_similarity()` calls on 932+ nodes | Replaced with batched `cosine_similarity(matrix)` |

---

## 9. V2 Paper Analysis

The professor requested partial replication of HippoRAG v2 tables.

**Paper:** "From RAG to Memory: Non-Parametric Continual Learning for Large Language Models" (ICML 2025)

**Key tables:**

| Table | Content | Our target |
|-------|---------|-----------|
| Table 2 | QA F1 on NQ, PopQA, MuSiQue, 2Wiki, HotpotQA, LV-Eval, NarrativeQA | MuSiQue subset (50 questions) |
| Table 3 | Retrieval Recall@5 on same datasets | MuSiQue subset |
| Table 4 | Ablation: NER-to-node vs Query-to-node vs Query-to-triple | If time allows |
| Tables 5,6,8,9 | Hyperparameter sweeps, qualitative examples | Skip |

**V2 improvements over V1 (what we implemented):**
1. Passage nodes integrated into PPR graph search (not just entity nodes)
2. Query-to-triple linking instead of NER-to-node
3. Online LLM re-ranking during retrieval (recognition memory)
4. Synonym detection via embedding similarity threshold

**Our deviations from v2:**
- Embedder: `all-MiniLM-L6-v2` vs NV-Embed-v2 (7B)
- LLM: UTSA endpoint vs Llama-3.3-70B-Instruct
- Scale: 50 questions vs 1,000
- No cross-encoder re-ranker

**MuSiQue eval script:** `scripts/run_musique_eval.py`  
**Data source:** `Official-HippoRAG-Repo/reproduce/dataset/musique.json` (1,000 questions, pre-downloaded)

---

## 10. Rubric Compliance Summary

| Category | Points | Status |
|----------|--------|--------|
| Spec Driven Development | 25 | Done — 6/6 stories pass regeneration |
| Reproducibility Manifest | 10 | Done — manifest.yaml, DATA.md, MODELS.md, REPRODUCE.md |
| Build and Deployment | 6 | Done — Dockerfile, docker-compose.yml, .dockerignore |
| Verification and Testing | 12 | Done — 47/47 tests, 3 XML reports, coverage |
| Stress and Robustness | 6 | Done — edge tests, locustfile.py; benchmarks.json pending |
| Code Quality + Responsible AI | 6 | Done — lint config, MODEL_CARD.md, security.txt |
| Logging | 5 | Done — JSON logging, request_id, LOGGING.md |
| Application Functionality and UI | 20 | Done — FastAPI UI, 6 stories, screenshots |
| User Documentation | 6 | Done — README, usage.md, screenshots |
| Team Contributions | 4 | Done — CONTRIBUTIONS.md, git_contributions.txt |
| **Total** | **100** | **~97 pending benchmarks.json + final push** |

---

## 11. Remaining Before Submission

1. **Make repo public** — GitHub Settings → Change visibility → Public
2. **Run MuSiQue eval** — `python scripts/run_musique_eval.py --questions 50` (VPN required, ~30 min)
3. **Add results to REPORT.md** — fill in Table 2/3 numbers once eval finishes
4. **Run loadtest** — `docker compose up` then `make loadtest` → `reports/benchmarks.json`
5. **Update commit_sha** — `git rev-parse HEAD` → `grading/manifest.yaml`
6. **Final push** — `git push origin "Samantha's-Branch"`
7. **Submit branch URL** to course submission system

---

## 12. How to Run

```bash
# Connect UTSA VPN first

# Option A: Docker (recommended)
cp .env.example .env   # fill in credentials
docker compose up --build

# Option B: Manual
pip install -r requirements.txt
python run_build_kg.py
uvicorn api.app:app --host 0.0.0.0 --port 8000

# Run tests
make test

# Run MuSiQue eval
python scripts/run_musique_eval.py --questions 50

# Spec regeneration test
export ANTHROPIC_API_KEY=sk-ant-...
bash scripts/regenerate.sh
```

App is available at `http://localhost:8000`.
