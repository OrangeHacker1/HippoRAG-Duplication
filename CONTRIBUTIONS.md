# Team Contributions

## Members

| Member | Role | Modules Owned | Percent Contribution |
|---|---|---|---|
| Samantha Salas | Developer | `retrieval/`, `api/`, `eval/`, `docs/` | 50% |
| OrangeHacker1 | Developer | `kg/`, `llm/`, `config/`, `data/` | 50% |

## Details

### Samantha Salas
- Implemented retrieval pipeline (`retrieval/retriever.py`, `retrieval/filter.py`, `retrieval/query_processor.py`, `retrieval/ppr.py`)
- Built FastAPI web application (`api/app.py`, `api/templates/`)
- Wrote evaluation framework (`eval/metrics.py`, `run_eval.py`)
- Authored all documentation (`docs/`)
- Configured CI tooling (`Makefile`, `pyproject.toml`, `Dockerfile`)
- Wrote test suites (`tests/`)
- Worked on `app.py`.
- Worked on `test.html`, `evaluate.html`, `train.html`

### OrangeHacker1
- Implemented knowledge graph construction (`kg/builder.py`, `kg/graph_store.py`, `kg/embeddings.py`)
- Built LLM client (`llm/llm_client.py`)
- Set up configuration system (`config/`)
- Authored evaluation dataset (`data/eval_dataset.py`)
- Initial project structure and skeleton code
- Create `GraphRAG` files.
- Worked on `app.py`.
- Worked on `test.html`, `evaluate.html`, `train.html`
- Authored all documentation (`docs/`) we were supposed to edit.
- Worked on `retrieval` files.

## Verification

```bash
git shortlog -sne --all --no-merges > reports/git_contributions.txt
```


Output saved to `reports/git_contributions.txt`.





## Verification Outline

Run `git shortlog -sne --all --no-merges` and write the output to
`reports/git_contributions.txt`. The TA compares this distribution to the
table above; each member's commit share must be within ±15 percentage points
of declared share.

Each member must have commits across at least two of: `src/`, `tests/`, `docs/`.

```bash
git shortlog -sne --all --no-merges > reports/git_contributions.txt
```
