# HippoRAG System Specification

## Purpose

HippoRAG is a graph-based retrieval-augmented generation (RAG) system inspired by the hippocampal memory indexing theory from neuroscience. Instead of flat vector search, the system builds a knowledge graph from a document corpus and uses it as an explicit memory index. At query time, seed concepts are identified from the query, and a Personalized PageRank (PPR) walk over the graph retrieves relevant passages across multiple hops in a single step. A large language model then generates a final answer from the retrieved passages.

The system is designed to answer multi-hop questions that require connecting facts scattered across separate documents — a task where flat vector search consistently underperforms graph-based retrieval.

---

## Component Inventory

| Component | Module Path | Responsibility |
|---|---|---|
| KG Builder | `kg/builder.py` | Orchestrates knowledge graph construction from raw documents |
| Knowledge Graph | `kg/graph_store.py` | NetworkX DiGraph storing entity nodes, passage nodes, and edges |
| Embedding Engine | `kg/embeddings.py` | Encodes text using sentence-transformers; computes cosine similarity |
| LLM Client | `llm/llm_client.py` | HTTP calls to OpenAI-compatible LLM for triple extraction and answer generation |
| Triple Matcher | `retrieval/triple_matcher.py` | Finds triples semantically similar to a query via embedding similarity |
| Triple Filter | `retrieval/filter.py` | Uses LLM to select only relevant triples from candidates |
| Query Processor | `retrieval/query_processor.py` | Extracts named entities from a query string using the LLM |
| PPR Engine | `retrieval/ppr.py` | Runs Personalized PageRank over the knowledge graph from seed nodes |
| Retriever | `retrieval/retriever.py` | Ties the full retrieval pipeline together; exposes `retrieve()` and `query()` |
| Eval Metrics | `eval/metrics.py` | Computes Recall@k, Exact Match, and F1 score |
| Eval Dataset | `data/eval_dataset.py` | Multi-hop test corpus, questions, gold documents, and gold answers |
| Config Loader | `config/config_loader.py` | Loads `config/config.yaml` |
| Env Loader | `config/env_loader.py` | Loads `.env` file; validates required environment variables |
| API Server | `api/app.py` | FastAPI application exposing `/query` and `/health` endpoints |
| KG Build Script | `run_build_kg.py` | CLI entry point for building the knowledge graph |
| Query Script | `run_query.py` | CLI entry point for a single query |
| Eval Script | `run_eval.py` | CLI entry point for the full evaluation pipeline |

---

## Data Flow

### Indexing (Knowledge Graph Construction)

```
Raw documents (List[str])
    │
    ▼
LLMClient.extract_triples(doc)
    │  Prompt: extract JSON array of [subject, relation, object] triples
    ▼
KnowledgeGraph.add_triple(s, r, o, source_text)
    │  Adds entity nodes (type="entity")
    │  Adds passage node (type="passage", text=source_text)
    │  Adds directed edge s → o (relation=r)
    │  Adds edges s → passage, o → passage (relation="contains")
    ▼
EmbeddingEngine.encode(all_entity_node_names)
    │
    ▼
Pairwise cosine similarity → add undirected "similar" edges
    where similarity > config["kg"]["similarity_threshold"] (default 0.75)
    │
    ▼
KnowledgeGraph.save(path)  →  kg/graph.pkl
```

### Retrieval and Answer Generation

```
Query string
    │
    ├──► TripleMatcher.match(query)
    │        Embeds query; scores all stored triples by cosine similarity
    │        Returns top-K triples
    │
    ├──► TripleFilter.filter(query, triples)
    │        LLM selects relevant triple indices from numbered list
    │        Returns filtered subset
    │
    ├──► [triple subjects]  ──┐
    │                         ├──► seeds (union)
    ├──► QueryProcessor        │
    │    .extract_entities()  ─┤
    │    + _match_query_       │
    │      entities()         ─┘
    │        LLM extracts entity strings from query
    │        Embedding similarity maps them to graph nodes
    │
    ▼
run_ppr(graph, seeds, alpha, max_iter)
    │  NetworkX personalized_pagerank
    │  Seeds receive weight=1, all others 0
    ▼
Ranked nodes sorted by PPR score (descending)
    │
    ▼
Filter for type="passage" nodes → extract .text attribute
    Top-K passages collected
    │
    ▼
LLMClient.generate(prompt with passages + question)
    │
    ▼
Answer string
```

---

## Public Interfaces

### `kg/builder.py` — `KGBuilder`

```python
class KGBuilder:
    def __init__(self) -> None: ...
    def build(self, docs: List[str]) -> None:
        """
        Extract triples from each document, build the knowledge graph,
        link similar entity nodes by embedding, and save to disk.

        Args:
            docs: List of raw document strings.
        """
```

### `kg/graph_store.py` — `KnowledgeGraph`

```python
class KnowledgeGraph:
    def __init__(self) -> None: ...
    def add_triple(self, s: str, r: str, o: str, source_text: str = None) -> None:
        """Add a (subject, relation, object) triple and link to its source passage."""
    def save(self, path: str) -> None:
        """Serialize graph and triples to a pickle file."""
    def load(self, path: str) -> None:
        """Deserialize graph and triples from a pickle file."""
```

### `retrieval/retriever.py` — `HippoRAG`

```python
class HippoRAG:
    def __init__(self) -> None:
        """Load graph from disk, initialize all retrieval components."""

    def retrieve(self, query: str) -> List[str]:
        """
        Run the full retrieval pipeline.

        Args:
            query: Natural language question string.

        Returns:
            Ordered list of passage strings ranked by PPR score.
            Length <= config["retrieval"]["top_k"].
        """

    def query(self, query: str) -> str:
        """
        Retrieve relevant passages and generate an answer using the LLM.

        Args:
            query: Natural language question string.

        Returns:
            Generated answer string.
        """
```

### `eval/metrics.py`

```python
def recall_at_k(retrieved_docs: List[str], gold_docs: List[str], k: int) -> float:
    """Fraction of gold documents found in the top-k retrieved documents."""

def exact_match(predicted: str, gold_answers: List[str]) -> float:
    """1.0 if any gold answer token set is a subset of the predicted answer tokens."""

def f1_score(predicted: str, gold_answers: List[str]) -> float:
    """Best token-level F1 score across all gold answers."""
```

### `api/app.py` — FastAPI endpoints

```
GET  /health          → {"status": "ok"}
POST /query           → {"question": str} → {"answer": str, "passages": List[str], "request_id": str}
```

---

## Model and Prompt Selection

### Embedding Model

- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Source:** HuggingFace Hub (downloaded automatically on first run)
- **Use:** Encoding entity nodes, triple texts, and query strings for cosine similarity
- **Config key:** `embedding.model` in `config/config.yaml`

### LLM

- **Default model:** Configurable via `TEACHER_MODEL` environment variable (e.g. `llama-3.3-70b-instruct-awq` or `gpt-4o-mini`)
- **Endpoint:** `TEACHER_BASE_URL` — any OpenAI-compatible `/v1/chat/completions` endpoint
- **Temperature:** `0.0` (deterministic output)
- **Max tokens:** `512`
- **Config keys:** `llm.temperature`, `llm.max_tokens` in `config/config.yaml`

### Prompts

| Prompt | Location | Purpose |
|---|---|---|
| Triple extraction | `llm/llm_client.py:extract_triples()` | Extract `[[s, r, o]]` JSON from a document |
| Triple filtering | `retrieval/filter.py:filter()` | Select relevant triple indices from a numbered list |
| Entity extraction | `retrieval/query_processor.py:extract_entities()` | Extract key entities from a query string |
| Answer generation | `retrieval/retriever.py:query()` | Generate an answer given retrieved passages and the question |

### PPR Parameters

- **Alpha (damping):** `0.85` — probability of following a graph edge vs. teleporting to a seed
- **Max iterations:** `30`
- **Similarity threshold for synonymy edges:** `0.75`
- **Config keys:** `retrieval.ppr_alpha`, `retrieval.max_iter`, `kg.similarity_threshold`
