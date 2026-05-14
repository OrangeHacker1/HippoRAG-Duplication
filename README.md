# HippoRAG Duplication

A graph-based Retrieval-Augmented Generation (RAG) system inspired by the hippocampal memory indexing theory from neuroscience. Instead of flat vector search, HippoRAG builds a knowledge graph from a document corpus and uses Personalized PageRank to retrieve relevant passages across multiple reasoning hops. This project replicates the core HippoRAG architecture and evaluates results against the HippoRAG v2 paper on HotpotQA and MuSiQue multi-hop QA benchmarks.

## Tech Stack

- Python 3.11
- FastAPI + Uvicorn
- Any OpenAI-compatible LLM endpoint (UTSA: llama-3.3-70b-instruct-awq)
- NetworkX (knowledge graph), sentence-transformers (embeddings)
- Docker + Docker Compose

## Quick Start

The TA will run exactly these commands. Make sure they work on a fresh clone with no extra setup.

```bash
git clone https://github.com/OrangeHacker1/HippoRAG-Duplication.git
cd HippoRAG-Duplication
cp .env.example .env
# edit .env and fill in TEACHER_BASE_URL, TEACHER_MODEL, TEACHER_API_KEY (REQUIRED)
docker compose build --no-cache
docker compose up
```

Wait for the app service to report healthy. The application will be available at http://localhost:8080.

Estimated time from `docker compose up` to running app: **under 10 minutes** on a clean machine (requires UTSA VPN for LLM access).

## Results

### HippoRAG vs Dense Baseline — HotpotQA (hotpot2 KG, 50 questions)

| Metric | HippoRAG | Dense Baseline |
|---|---|---|
| ExactMatch | **0.70** | 0.68 |
| F1 | **0.255** | 0.180 |

HippoRAG outperforms the dense baseline on both metrics. Recall@k is 0 on both due to a known passage-format mismatch between stored KG passages (title-prepended) and gold doc strings; the EM/F1 comparison remains valid.

### Large-Scale Eval (500 questions per dataset)

| Dataset | Model | ExactMatch | F1 |
|---|---|---|---|
| HotpotQA | HippoRAG (hotpotqa1) | 0.341 | 0.062 |
| MuSiQue | HippoRAG (hotpotqa1) | 0.093 | 0.018 |

Full reproducibility procedure: see [docs/REPRODUCE.md](docs/REPRODUCE.md).

## Documentation

- [docs/SPEC.md](docs/SPEC.md) — system specification
- [docs/STORIES.md](docs/STORIES.md) — user stories with manual walkthrough steps
- [docs/usage.md](docs/usage.md) — full usage guide
- [docs/MODEL_CARD.md](docs/MODEL_CARD.md) — model card and limitations
- [docs/REPRODUCE.md](docs/REPRODUCE.md) — reproducibility procedure
- [docs/DATA.md](docs/DATA.md) — datasets and provenance
- [docs/MODELS.md](docs/MODELS.md) — model checkpoints and provenance
- [docs/benchmarks.md](docs/benchmarks.md) — performance benchmarks
- [docs/LOGGING.md](docs/LOGGING.md) — log format and request tracing example

## Contributors

See [CONTRIBUTIONS.md](CONTRIBUTIONS.md).

## License

MIT
