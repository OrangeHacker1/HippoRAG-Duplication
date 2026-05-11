# HippoRAG Duplication — TODO

Current branch: **main**
Code lives in: **`src/myproject/`** (package name `myproject` is pinned by course template)
Grader script: **`grading/grade.py`** (course-issued, do not modify)

---

## Critical — Breaks grade.py scoring

- [ ] **`src/myproject/data/eval_dataset.py` missing** — `app.py` imports `from myproject.data.eval_dataset import QUESTIONS` but only a `__pycache__` exists. App will crash on startup. Copy from `Samantha's-Branch:src/myproject/data/eval_dataset.py`.

- [ ] **`src/myproject/router.py` missing** — `tests/user_stories/test_us_01.py` imports `from myproject.router import route_query`. Module doesn't exist → test fails → `reports/user_stories.xml` scores zero for regen.

- [ ] **`tests/user_stories/test_us_01.py` broken** — calls `route_query()` and expects `{answer, citations, latency_ms}`. Once `router.py` exists, the return shape must match.

- [ ] **`tests/user_stories/test_us_02.py` broken** — sends `{"text": ""}` but API takes `{"question": ""}`.

- [ ] **`reports/edge.xml` missing** — grade.py reads this for Stress & Robustness (6 pts). Run edge tests: `pytest tests/edge/ --junitxml=reports/edge.xml`.

- [ ] **`reports/regenerated_user_stories.xml` missing** — grade.py reads this for Spec Driven Development (25 pts). Requires running `scripts/regenerate.sh` with `ANTHROPIC_API_KEY` set.

- [ ] **`grading/manifest.yaml` incomplete** — `commit_sha: ""` is empty. Also lists wrong model (`claude-opus-4-5-20251101` for QA) and wrong dataset (`nist_csrc_pubs`). Fix all three fields, then fill `commit_sha` on the final commit.

---

## Important — Affects Docker / TA walkthrough

- [x] **`.dockerignore` deleted** — restored on `finalize-wip`

- [x] **Dockerfile CMD on port 8080, STORIES.md says 8000** — fixed two stray 8000 refs in STORIES.md to 8080

- [ ] **`reports/benchmarks.json` missing** — not checked by grade.py but listed in rubric under Stress & Robustness. Generate with: start server → `make loadtest`. (Low priority vs items above.)

---

## Nice to Have

- [x] **`grading/manifest.yaml` model_ids** — corrected to UTSA LLM + MiniLM-L6-v2, datasets updated to hipporag-eval-multihop and musique-validation-subset

- [ ] **`commit_sha`** — update to final HEAD after all other changes are committed and pushed.

- [ ] **`docs/assets/demo.gif`** — optional per rubric, listed under User Documentation (6 pts).

---

## Already Done (on main)

- [x] `grading/grade.py` — course-issued grader copied in
- [x] `reports/unit.xml`, `integration.xml`, `user_stories.xml`, `coverage.xml` — restored
- [x] `reports/security.txt`, `git_contributions.txt` — restored
- [x] `reports/walkthrough.md` — exists
- [x] `scripts/regenerate_prompt.md` — course-issued version present
- [x] `scripts/regenerate.sh` — present
- [x] `docs/STORIES.md` — updated with correct HippoRAG stories
- [x] `Dockerfile` — multi-stage, non-root, CPU-only torch, health check
- [x] `docker-compose.yml` — Qdrant removed, build-kg service added
- [x] `myproject` package installed (`pip install -e .`)
- [x] `README.md` — filled in
