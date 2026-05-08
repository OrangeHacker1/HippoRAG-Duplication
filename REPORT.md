# HippoRAG Duplication — Project Report

**Course:** CS 6263 NLP and Agentic AI  
**Deadline:** May 10, 11:59 PM  
**Team:** Samantha Salas (60%), OrangeHacker1 (40%)

---

## 1. System Overview

HippoRAG is a graph-based Retrieval-Augmented Generation (RAG) system inspired by the hippocampal indexing theory of human long-term memory. Instead of flat vector search, it builds a Knowledge Graph (KG) from documents and uses Personalized PageRank (PPR) to retrieve relevant passages across multiple reasoning hops.

| Component | HippoRAG Concept |
|-----------|-----------------|
| Triple extraction | Hippocampal encoding |
| Knowledge Graph | Memory index |
| Personalized PageRank | Associative recall |
| Query entity seeds | Cue-triggered recall |
| LLM answer generation | Neocortex reasoning |

---

## 2. Implementation

### Architecture

```
Offline Indexing:
  Documents → LLM (extract_triples) → KG (entity + passage nodes)
  KG nodes → EmbeddingEngine (vectorized cosine similarity) → synonym edges

Online Retrieval:
  Query → TripleMatcher → TripleFilter (LLM) → triple seed nodes
  Query → QueryProcessor (LLM) → EmbeddingEngine → entity seed nodes
  Seeds → Personalized PageRank → Top-K passage nodes → LLM (answer)

API:
  FastAPI → POST /api/query → retrieve() + generate()
           → POST /api/evaluate → full eval pipeline
           → GET /health → {"status": "ok"}
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Knowledge Graph | NetworkX DiGraph |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| LLM | Any OpenAI-compatible endpoint (UTSA: llama-3.3-70b-instruct-awq) |
| Web API | FastAPI + Uvicorn |
| Containerization | Docker + Docker Compose |
| Testing | Pytest + pytest-cov (47/47 tests passing) |

### Implementation Gaps Fixed

The skeleton code contained 5 gaps that were identified and fixed:

| Gap | File | Fix |
|-----|------|-----|
| 1 | `retrieval/filter.py` | LLM-based triple filtering with regex index parsing |
| 2 | `retrieval/retriever.py` | Query entity extraction + embedding-based seed matching |
| 3 | `llm/llm_client.py` | JSON prompt + json.loads() replacing unsafe eval() |
| 4 | `retrieval/retriever.py` | Passage text context instead of raw node names |
| 5 | Missing entirely | Full evaluation pipeline (metrics, dataset, runner) |

---

## 3. Evaluation Results

### Internal Dataset (data/eval_dataset.py)

10 documents (Marie Curie, Einstein, Newton), 4 multi-hop questions.

| Metric | Value | Tolerance |
|--------|-------|-----------|
| Recall@1 | 0.50 | ± 0.20 |
| Recall@2 | 0.75 | ± 0.20 |
| Recall@5 | 0.90 | ± 0.15 |
| ExactMatch | 0.50 | ± 0.25 |
| F1 | 0.55 | ± 0.25 |

Tolerances are wide because results depend on the configured LLM.

---

### Partial Replication of HippoRAG v2 Tables 2 & 3 (MuSiQue)

We partially replicate Tables 2 (QA F1) and 3 (Retrieval Recall@5) from the HippoRAG v2 paper ("From RAG to Memory: Non-Parametric Continual Learning for Large Language Models", ICML 2025) on a 50-question subset of the MuSiQue multi-hop QA benchmark.

**Setup:**
- Dataset: MuSiQue validation set, 50 answerable questions, 932 corpus passages
- Embedder: sentence-transformers/all-MiniLM-L6-v2
- LLM: llama-3.3-70b-instruct-awq via UTSA endpoint
- KG: 9,728 nodes, 24,210 edges

**Results vs v2 Paper (Table 2 & 3 — MuSiQue column):**

| Metric | Ours (50 Qs) | v2 Paper (1,000 Qs) |
|--------|-------------|---------------------|
| Recall@1 | 0.1417 | — |
| Recall@2 | 0.3183 | — |
| Recall@5 | 0.4833 | 0.9450 |
| F1 | 0.4432 | 0.7820 |

**Analysis of gap vs paper:**

The performance gap is expected and attributable to three differences:

1. **Embedder size**: The paper uses NV-Embed-v2 (7B parameters), a state-of-the-art embedding model. We use all-MiniLM-L6-v2, which is ~22M parameters. Larger embedders produce significantly better entity matching and synonym detection in the KG.

2. **LLM capability**: The paper uses Llama-3.3-70B-Instruct for both triple extraction and answer generation. Our UTSA endpoint runs a quantized (AWQ) version of the same model, which may produce less precise triple extraction.

3. **Scale**: The paper evaluates on 1,000 questions with the full 11,656-passage corpus. Our subset of 50 questions draws from only 932 passages, limiting the KG's coverage of multi-hop reasoning paths.

Despite the gap, the system demonstrates the core HippoRAG behavior: multi-hop retrieval via PPR achieves non-trivial Recall@5 (48%) on questions that require connecting 2–3 reasoning steps across passages.

**Future work:** Replicating the full paper results would require NV-Embed-v2 as the retriever, the full MuSiQue corpus, and running all 1,000 validation questions. The v2 paper additionally introduces passage nodes integrated into PPR and query-to-triple linking (vs our NER-to-node approach), which account for much of the remaining gap.

---

## 4. Spec Regeneration Test

The no-vibe-coding test feeds `docs/SPEC.md` to Claude Opus (`claude-opus-4-5-20251101`, temperature=0) and runs user story acceptance tests against the regenerated code.

**Result: 6/6 user stories passed → 25/25 points**

This confirms the specification is precise enough to serve as the sole source of truth for system regeneration.

---

## 5. Project Structure

```
HippoRAG-Duplication/
├── api/               # FastAPI web application
├── config/            # YAML config and .env loader
├── data/              # Evaluation dataset
├── docs/              # SPEC, STORIES, MODEL_CARD, LOGGING, REPRODUCE, etc.
├── eval/              # Recall@k, ExactMatch, F1 metrics
├── grading/           # manifest.yaml, traceability.yaml
├── kg/                # KG builder, graph store, embeddings
├── llm/               # LLM HTTP client
├── reports/           # Generated test/coverage/audit/eval reports
├── retrieval/         # PPR, filter, matcher, query processor, retriever
├── scripts/           # preflight.sh, regenerate.sh, demo.sh, run_musique_eval.py
├── tests/             # unit, integration, user_stories, edge, load
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## 6. How to Reproduce

```bash
# Requires UTSA VPN

# Docker (recommended)
cp .env.example .env   # fill in credentials
docker compose up --build

# Manual
pip install -r requirements.txt
python run_build_kg.py
uvicorn api.app:app --host 0.0.0.0 --port 8000

# Tests
make test

# MuSiQue eval (v2 table replication)
python scripts/run_musique_eval.py --questions 50
```
