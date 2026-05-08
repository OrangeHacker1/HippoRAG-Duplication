# Reproducing Results

## Hardware Profile

| Component | Specification |
|---|---|
| OS | Ubuntu 22.04 / WSL2 |
| Python | 3.11 |
| RAM | 8 GB minimum |
| Disk | 2 GB free (for model cache and graph) |
| GPU | Not required (CPU inference for embeddings) |
| Network | Required for LLM endpoint and model download |

## Expected Runtime

| Step | Expected Time |
|---|---|
| `make download-models` | 1–2 min (90 MB embedding model) |
| `make build-kg` | 2–5 min (depends on LLM endpoint latency) |
| `make test` | 30–60 sec |
| `make reproduce` | 10–15 min total |

## One-Command Full Replay

```bash
make reproduce
```

This runs: `docker compose build` → build KG → run eval → report metrics.

## Expected Metric Values

Run against the bundled `data/eval_dataset.py` corpus (10 docs, 4 multi-hop questions):

| Metric | Expected | Tolerance |
|---|---|---|
| Recall@1 | 0.50 | ± 0.20 |
| Recall@2 | 0.75 | ± 0.20 |
| Recall@5 | 0.90 | ± 0.15 |
| ExactMatch | 0.50 | ± 0.25 |
| F1 | 0.55 | ± 0.25 |

Tolerances are wide because results depend on the configured LLM. The embedding model (`all-MiniLM-L6-v2`) is deterministic.

## Step-by-Step Manual Reproduction

```bash
# 1. Clone and configure
git clone <repo-url>
cd HippoRAG-Duplication
cp .env.example .env
# Fill in TEACHER_BASE_URL, TEACHER_MODEL, TEACHER_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download embedding model
make download-models

# 4. Build the knowledge graph
make build-kg

# 5. Run tests
make test

# 6. Run evaluation
python run_eval.py

# 7. Or run everything via Docker
make reproduce
```
