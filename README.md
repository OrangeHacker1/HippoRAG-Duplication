# HippoRAG

A graph-based retrieval-augmented generation (RAG) system inspired by the hippocampal memory indexing theory from neuroscience. Instead of flat vector search, HippoRAG builds a knowledge graph from a document corpus and uses Personalized PageRank to retrieve relevant passages across multiple hops.

## Tech Stack

| Layer | Technology |
|---|---|
| Knowledge Graph | NetworkX DiGraph |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| LLM | Any OpenAI-compatible endpoint |
| Web API | FastAPI + Uvicorn |
| Containerization | Docker + Docker Compose |
| Testing | Pytest + pytest-cov |
| Linting | Ruff + Black + Mypy |

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url>
cd HippoRAG-Duplication

# 2. Configure environment
cp .env.example .env
# Edit .env and fill in TEACHER_BASE_URL, TEACHER_MODEL, TEACHER_API_KEY

# 3. Start with Docker Compose
docker compose up
```

The app is available at `http://localhost:8000`.

> `docker compose up` will build the knowledge graph automatically before starting the web server.

## Manual Setup (without Docker)

```bash
pip install -r requirements.txt
python run_build_kg.py
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

## Source Layout

```
HippoRAG-Duplication/
├── api/               # FastAPI web application
├── config/            # YAML config and .env loader
├── data/              # Evaluation dataset
├── docs/              # Project documentation
├── eval/              # Evaluation metrics
├── grading/           # Manifest and traceability
├── kg/                # Knowledge graph construction
├── llm/               # LLM HTTP client
├── retrieval/         # Retrieval pipeline (PPR, filter, matcher)
├── scripts/           # preflight.sh, demo.sh, regenerate.sh
├── tests/             # Unit, integration, user story, edge, load tests
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pyproject.toml
```

## Running Tests

```bash
make test
```

## Results

Evaluated on the bundled multi-hop dataset (`data/eval_dataset.py`): 10 documents, 4 questions requiring 2–3 hop reasoning.

| Metric | Value | Tolerance |
|---|---|---|
| Recall@1 | 0.50 | ± 0.20 |
| Recall@2 | 0.75 | ± 0.20 |
| Recall@5 | 0.90 | ± 0.15 |
| ExactMatch | 0.50 | ± 0.25 |
| F1 | 0.55 | ± 0.25 |

Tolerances are wide because results depend on the configured LLM. See `docs/REPRODUCE.md` for full reproduction instructions.

## Documentation

- [docs/SPEC.md](docs/SPEC.md) — System specification
- [docs/STORIES.md](docs/STORIES.md) — User stories with acceptance criteria
- [docs/usage.md](docs/usage.md) — Usage guide per story
- [docs/REPRODUCE.md](docs/REPRODUCE.md) — Reproduction instructions
- [docs/MODEL_CARD.md](docs/MODEL_CARD.md) — Model card
- [docs/LOGGING.md](docs/LOGGING.md) — Logging and request tracing
- [docs/DATA.md](docs/DATA.md) — Dataset documentation
- [docs/MODELS.md](docs/MODELS.md) — Model documentation
