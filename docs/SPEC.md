# System Specification

> This is the source of truth for the project. The TA will feed this document
> to an LLM during grading and verify that the generated code passes the user
> story tests. Write it as if it must be enough for someone (or an LLM) to
> implement the project from scratch with no other reference.

## 1. Purpose and Scope

HippoRAG is a graph-based retrieval-augmented generation (RAG) system inspired by the hippocampal memory indexing theory from neuroscience. Instead of flat vector search, the system builds a knowledge graph from a document corpus and uses it as an explicit memory index. At query time, seed concepts are identified from the query, and a Personalized PageRank (PPR) walk over the graph retrieves relevant passages across multiple hops in a single step. A large language model then generates a final answer from the retrieved passages.


This project is designed to make a specialized local RAG using the methods used in the HippoRAG paper. This program aims reproduce this specialized RAG in an attempt to reproduce the graphs and charts presented inside of said paper.     


## 2. Component Inventory


| Component | Module Path | Responsibility |
|---|---|---|
| KG Builder | `src/myproject/kg/builder.py` | Orchestrates knowledge graph construction from raw documents |
| Knowledge Graph | `src/myproject/kg/graph_store.py` | NetworkX DiGraph storing entity nodes, passage nodes, and edges |
| Embedding Engine | `src/myproject/kg/embeddings.py` | Encodes text using sentence-transformers; computes cosine similarity |
| LLM Client | `src/myproject/llm/llm_client.py` | HTTP calls to OpenAI-compatible LLM for triple extraction and answer generation |
| Triple Matcher | `src/myproject/retrieval/triple_matcher.py` | Finds triples semantically similar to a query via embedding similarity |
| Triple Filter | `src/myproject/retrieval/filter.py` | Uses LLM to select only relevant triples from candidates |
| Query Processor | `src/myproject/retrieval/query_processor.py` | Extracts named entities from a query string using the LLM |
| PPR Engine | `src/myproject/retrieval/ppr.py` | Runs Personalized PageRank over the knowledge graph from seed nodes |
| Retriever | `src/myproject/retrieval/retriever.py` | Ties the full retrieval pipeline together; exposes `retrieve()` and `query()` |
| Eval Metrics | `src/myproject/eval/metrics.py` | Computes Recall@k, Exact Match, and F1 score |
| Eval Dataset | `src/myproject/data/eval_dataset.py` | Multi-hop test corpus, questions, gold documents, and gold answers |
| Config Loader | `src/myproject/config/config_loader.py` | Loads `config/config.yaml` |
| Env Loader | `src/myproject/config/env_loader.py` | Loads `.env` file; validates required environment variables |
| API Server | `src/myproject/api/app.py` | FastAPI application exposing `/query` and `/health` endpoints |
| KG Build Script | `src/myproject/run_build_kg.py` | CLI entry point for building the knowledge graph |
| Query Script | `src/myproject/run_query.py` | CLI entry point for a single query |
| Eval Script | `src/myproject/run_eval.py` | CLI entry point for the full evaluation pipeline |
| GraphRAG | `src/myproject/GraphRAG` | This is designed to create and retrieve from a GraphRAG. This is not relevent for this project. It can be ignored. It is going to be used for future implimentation. |
| Evaluation Manual | `src/myproject/run_eval.sh` | Runs the application and serves as the backend. |
| Evaluation Manual 2 | `src/myproject/test_hotpot.sh` | Tests the hotpot2 model on the HotPotQA dataset. |




Every component listed here must map to a source module under `src/myproject/`.
The grading script verifies this mapping via `grading/traceability.yaml`.

| Component | Source module | Responsibility |
|---|---|---|
| QueryRouter | src/myproject/router.py | Route incoming queries to the right pipeline |
| Retriever | src/myproject/retriever.py | Semantic search over the document corpus |
| Generator | src/myproject/generator.py | Generate cited answers via LLM |
| API | src/myproject/api.py | FastAPI HTTP interface |

## 3. Data Flow

In this project, you are given a UI to test and use HippoRAGs. There are several prebuilt RAGs designed for TA testing. The project is broken into Query, evaluate and Train. The Query is designed to freely prompt an LLM. The LLM will use the HippoRAG currently loaded. The evaluate runs the json or default test on the loaded HippoRAG. The Train section is designed to make new HippoRAGs or load saved ones.

## 4. Public Interfaces

This section is the contract. The user story tests import these exact module
paths and call these exact function signatures. The regenerated code must
match these signatures or the tests will fail.

### 4.1 HTTP API

```
POST /api/query
Content-Type: application/json

Request body:
{
  "text": "string, the user's question",
  "max_results": "integer, optional, default 5"
}

Response 200:
{
  "answer": "string, the generated answer with citations",
  "citations": [{"doc_id": "string", "snippet": "string"}],
  "latency_ms": "integer"
}

Response 400 (empty input):
{
  "error": "input text is required"
}
```

### 4.2 Python interfaces

```python
# src/myproject/router.py
def route_query(text: str, max_results: int = 5) -> dict: ...

# src/myproject/retriever.py
class Retriever:
    def __init__(self, index_path: str) -> None: ...
    def search(self, query: str, k: int = 5) -> list[dict]: ...

# src/myproject/generator.py
def generate_answer(query: str, contexts: list[dict]) -> dict: ...
```

## 5. External Dependencies

| Dependency | Version | Purpose |
|---|---|---|
| Python | 3.11 | runtime |
| fastapi | 0.110.x | HTTP framework |
| anthropic | 0.40.x | LLM client |
| sentence-transformers | 2.7.x | embeddings |
| faiss-cpu | 1.8.x | vector search |
| pydantic | 2.x | request/response validation |

## 6. Configuration

The system reads configuration from environment variables. See `.env.example`
for the full list. Required keys: ANTHROPIC_API_KEY. Optional keys:
LOG_LEVEL (default INFO), MAX_CONTEXT_TOKENS (default 4000).

## 7. Model and Prompt Selection

[Justify your choice of model and prompting strategy. Why this model, why this
prompt structure, what alternatives you considered, and what known failure
modes you mitigate. This section directly informs the model card.]
